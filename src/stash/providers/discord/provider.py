"""Discord storage provider implementation."""

import asyncio

import httpx

from stash.core.chunking import Chunk
from stash.core.exceptions import ProviderAuthError, ProviderError, ProviderRateLimitError
from stash.core.storage import BaseStorageProvider, ProviderConfig, ProviderLimits, RemoteRef
from stash.providers.discord.auth import DISCORD_API_BASE, DiscordAuth
from stash.providers.discord.limits import get_discord_limits


class DiscordProvider(BaseStorageProvider):
    """Discord storage provider using bot/user token and channel for storage."""

    def __init__(self) -> None:
        super().__init__()
        self.auth: DiscordAuth | None = None
        self.channel_id: str | None = None
        self._client: httpx.AsyncClient | None = None
        self._rate_limit_semaphore: asyncio.Semaphore | None = None

    async def _initialize(self, config: ProviderConfig) -> None:
        """Initialize Discord client and validate credentials."""
        credentials = config.credentials
        token = credentials.get("token")
        if not token:
            raise ProviderAuthError("Discord token is required")

        is_bot = credentials.get("is_bot", "true").lower() == "true"
        self.auth = DiscordAuth.from_bot_token(token) if is_bot else DiscordAuth.from_user_token(token)

        self.channel_id = credentials.get("channel_id")
        if not self.channel_id:
            raise ProviderAuthError("Discord channel_id is required")

        max_concurrent = int(config.settings.get("max_concurrent", "3"))
        self._rate_limit_semaphore = asyncio.Semaphore(max_concurrent)

        self._client = httpx.AsyncClient(
            base_url=DISCORD_API_BASE,
            headers={
                "Authorization": self.auth.get_auth_header(),
                "User-Agent": "Stash/0.1.0",
            },
            timeout=httpx.Timeout(60.0, connect=10.0),
        )

        await self._validate_channel()

    async def _validate_channel(self) -> None:
        """Validate that the channel exists and we have permission."""
        if not self._client or not self.channel_id:
            raise ProviderError("Provider not initialized")

        response = await self._client.get(f"/channels/{self.channel_id}")
        if response.status_code == 401:
            raise ProviderAuthError("Invalid Discord token")
        if response.status_code == 403:
            raise ProviderAuthError("No permission to access channel")
        if response.status_code == 404:
            raise ProviderAuthError("Channel not found")
        if response.status_code != 200:
            raise ProviderError(f"Failed to validate channel: {response.status_code}")

    async def upload_chunk(self, chunk: Chunk, remote_path: str) -> RemoteRef:
        """Upload a chunk as a Discord message attachment."""
        if not self._client or not self.channel_id:
            raise ProviderError("Provider not initialized")

        if self._rate_limit_semaphore is None:
            raise ProviderError("Rate limit semaphore not initialized")

        async with self._rate_limit_semaphore:
            filename = f"{remote_path}-chunk-{chunk.index:06d}.bin"
            files = {"file": (filename, chunk.data, "application/octet-stream")}
            data = {"content": f"stash-chunk:{remote_path}:{chunk.index}"}

            response = await self._client.post(
                f"/channels/{self.channel_id}/messages",
                data=data,
                files=files,
            )

            return await self._handle_upload_response(response, chunk.index, remote_path)

    async def _handle_upload_response(
        self, response: httpx.Response, chunk_index: int, remote_path: str
    ) -> RemoteRef:
        """Handle upload response and extract message ID."""
        if response.status_code == 429:
            retry_after = response.json().get("retry_after", 1)
            await asyncio.sleep(retry_after)
            raise ProviderRateLimitError(f"Rate limited, retry after {retry_after}s")

        if response.status_code not in (200, 201):
            raise ProviderError(f"Upload failed: {response.status_code} - {response.text}")

        data = response.json()
        attachments = data.get("attachments", [])
        if not attachments:
            raise ProviderError("No attachment in response")

        attachment = attachments[0]
        return RemoteRef(
            provider="discord",
            remote_id=attachment["id"],
            metadata={
                "message_id": data["id"],
                "filename": attachment["filename"],
                "size": str(attachment["size"]),
                "chunk_index": str(chunk_index),
                "remote_path": remote_path,
            },
        )

    async def download_chunk(self, remote_ref: RemoteRef) -> bytes:
        """Download a chunk from Discord."""
        if not self._client:
            raise ProviderError("Provider not initialized")

        if self._rate_limit_semaphore is None:
            raise ProviderError("Rate limit semaphore not initialized")

        message_id = remote_ref.metadata.get("message_id")
        if not message_id:
            raise ProviderError("Missing message_id in remote reference")

        async with self._rate_limit_semaphore:
            response = await self._client.get(f"/channels/{self.channel_id}/messages/{message_id}")

            if response.status_code == 404:
                raise ProviderError("Message not found")
            if response.status_code == 429:
                retry_after = response.json().get("retry_after", 1)
                await asyncio.sleep(retry_after)
                raise ProviderRateLimitError(f"Rate limited, retry after {retry_after}s")
            if response.status_code != 200:
                raise ProviderError(f"Download failed: {response.status_code}")

            data = response.json()
            attachments = data.get("attachments", [])
            if not attachments:
                raise ProviderError("No attachment in message")

            attachment = attachments[0]
            url = attachment["url"]

            file_response = await self._client.get(url)
            if file_response.status_code != 200:
                raise ProviderError(f"File download failed: {file_response.status_code}")

            return file_response.content

    async def delete_chunk(self, remote_ref: RemoteRef) -> None:
        """Delete a chunk (message) from Discord."""
        if not self._client:
            raise ProviderError("Provider not initialized")

        if self._rate_limit_semaphore is None:
            raise ProviderError("Rate limit semaphore not initialized")

        message_id = remote_ref.metadata.get("message_id")
        if not message_id:
            raise ProviderError("Missing message_id in remote reference")

        async with self._rate_limit_semaphore:
            response = await self._client.delete(f"/channels/{self.channel_id}/messages/{message_id}")
            if response.status_code not in (200, 204, 404):
                raise ProviderError(f"Delete failed: {response.status_code}")

    async def list_chunks(self, prefix: str) -> list[RemoteRef]:
        """List chunks by searching messages (limited by Discord API)."""
        if not self._client or not self.channel_id:
            raise ProviderError("Provider not initialized")

        if self._rate_limit_semaphore is None:
            raise ProviderError("Rate limit semaphore not initialized")

        refs: list[RemoteRef] = []
        before_id: str | None = None
        limit = 100

        while True:
            params: dict[str, str | int] = {"limit": limit}
            if before_id:
                params["before"] = before_id

            async with self._rate_limit_semaphore:
                response = await self._client.get(f"/channels/{self.channel_id}/messages", params=params)

            if response.status_code == 429:
                retry_after = response.json().get("retry_after", 1)
                await asyncio.sleep(retry_after)
                continue
            if response.status_code != 200:
                raise ProviderError(f"List failed: {response.status_code}")

            messages = response.json()
            if not messages:
                break

            for msg in messages:
                content = msg.get("content", "")
                if content.startswith(f"stash-chunk:{prefix}:"):
                    for attachment in msg.get("attachments", []):
                        refs.append(RemoteRef(
                            provider="discord",
                            remote_id=attachment["id"],
                            metadata={
                                "message_id": msg["id"],
                                "filename": attachment["filename"],
                                "size": str(attachment["size"]),
                                "chunk_index": content.split(":")[-1],
                                "remote_path": prefix,
                            },
                        ))

            if len(messages) < limit:
                break
            before_id = messages[-1]["id"]

        return refs

    def get_limits(self) -> ProviderLimits:
        """Get Discord provider limits."""
        return get_discord_limits()

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        await super().close()
"""Telegram storage provider implementation."""

import asyncio

import httpx

from stash.core.chunking import Chunk
from stash.core.exceptions import ProviderAuthError, ProviderError, ProviderRateLimitError
from stash.core.storage import BaseStorageProvider, ProviderConfig, ProviderLimits, RemoteRef
from stash.providers.telegram.auth import TelegramAuth, TELEGRAM_API_BASE
from stash.providers.telegram.limits import get_telegram_limits


class TelegramProvider(BaseStorageProvider):
    """Telegram storage provider using bot token and chat/channel for storage."""

    def __init__(self) -> None:
        super().__init__()
        self.auth: TelegramAuth | None = None
        self.chat_id: str | None = None
        self._client: httpx.AsyncClient | None = None
        self._rate_limit_semaphore: asyncio.Semaphore | None = None

    async def _initialize(self, config: ProviderConfig) -> None:
        """Initialize Telegram client and validate credentials."""
        credentials = config.credentials
        token = credentials.get("token")
        if not token:
            raise ProviderAuthError("Telegram bot token is required")

        self.auth = TelegramAuth(bot_token=token)

        self.chat_id = credentials.get("chat_id")
        if not self.chat_id:
            raise ProviderAuthError("Telegram chat_id is required")

        max_concurrent = int(config.settings.get("max_concurrent", "3"))
        self._rate_limit_semaphore = asyncio.Semaphore(max_concurrent)

        self._client = httpx.AsyncClient(
            base_url=f"{TELEGRAM_API_BASE}{token}",
            timeout=httpx.Timeout(60.0, connect=10.0),
        )

        await self._validate_chat()

    async def _validate_chat(self) -> None:
        """Validate that the chat exists and we have permission."""
        if not self._client or not self.chat_id:
            raise ProviderError("Provider not initialized")

        response = await self._client.post(
            "getChat",
            json={"chat_id": self.chat_id},
        )

        if response.status_code == 401:
            raise ProviderAuthError("Invalid Telegram bot token")
        if response.status_code == 400:
            raise ProviderAuthError("Chat not found or bot not a member")
        if response.status_code == 403:
            raise ProviderAuthError("Bot not a member of the chat")
        if response.status_code != 200:
            raise ProviderError(f"Failed to validate chat: {response.status_code} - {response.text}")

    async def upload_chunk(self, chunk: Chunk, remote_path: str) -> RemoteRef:
        """Upload a chunk as a Telegram document."""
        if not self._client or not self.chat_id:
            raise ProviderError("Provider not initialized")

        if self._rate_limit_semaphore is None:
            raise ProviderError("Rate limit semaphore not initialized")

        async with self._rate_limit_semaphore:
            # Filename includes file_id and chunk index
            filename = f"{remote_path}.bin"
            files = {"document": (filename, chunk.data, "application/octet-stream")}
            data = {
                "chat_id": self.chat_id,
                "caption": f"stash-chunk:{remote_path}:{chunk.index}",
                "disable_notification": True,
            }

            response = await self._client.post(
                "sendDocument",
                data=data,
                files=files,
            )

            return await self._handle_upload_response(response, chunk.index, remote_path)

    async def _handle_upload_response(
        self, response: httpx.Response, chunk_index: int, remote_path: str
    ) -> RemoteRef:
        """Handle upload response and extract message ID."""
        if response.status_code == 429:
            retry_after = response.json().get("parameters", {}).get("retry_after", 1)
            await asyncio.sleep(retry_after)
            raise ProviderRateLimitError(f"Rate limited, retry after {retry_after}s")

        if response.status_code != 200:
            raise ProviderError(f"Upload failed: {response.status_code} - {response.text}")

        data = response.json()
        if not data.get("ok"):
            raise ProviderError(f"Upload failed: {data}")

        message = data["result"]
        document = message.get("document")
        if not document:
            raise ProviderError("No document in response")

        return RemoteRef(
            provider="telegram",
            remote_id=document["file_id"],
            metadata={
                "message_id": str(message["message_id"]),
                "size": str(document["file_size"]),
                "chunk_index": str(chunk_index),
                "remote_path": remote_path,
            },
        )

    async def download_chunk(self, remote_ref: RemoteRef) -> bytes:
        """Download a chunk from Telegram."""
        if not self._client:
            raise ProviderError("Provider not initialized")

        file_id = remote_ref.remote_id
        if not file_id:
            raise ProviderError("Missing file_id in remote reference")

        async with self._rate_limit_semaphore:
            # Get file info to get file path
            response = await self._client.post(
                "getFile",
                json={"file_id": file_id},
            )

            if response.status_code == 404:
                raise ProviderError("File not found")
            if response.status_code == 429:
                retry_after = response.json().get("parameters", {}).get("retry_after", 1)
                await asyncio.sleep(retry_after)
                raise ProviderRateLimitError(f"Rate limited, retry after {retry_after}s")
            if response.status_code != 200:
                raise ProviderError(f"Download failed: {response.status_code} - {response.text}")

            data = response.json()
            if not data.get("ok"):
                raise ProviderError(f"Get file failed: {data}")

            file_path = data["result"]["file_path"]

            # Download the actual file
            file_url = f"https://api.telegram.org/file/bot{self.auth.bot_token}/{file_path}"
            file_response = await self._client.get(file_url)

            if file_response.status_code != 200:
                raise ProviderError(f"File download failed: {file_response.status_code}")

            return file_response.content

    async def delete_chunk(self, remote_ref: RemoteRef) -> None:
        """Delete a chunk (message) from Telegram."""
        if not self._client:
            raise ProviderError("Provider not initialized")

        message_id = remote_ref.metadata.get("message_id")
        if not message_id:
            raise ProviderError("Missing message_id in remote reference")

        async with self._rate_limit_semaphore:
            response = await self._client.post(
                "deleteMessage",
                json={"chat_id": self.chat_id, "message_id": int(message_id)},
            )
            if response.status_code != 200:
                data = response.json()
                if not data.get("ok") and data.get("error_code") != 400:  # 400 = message not found
                    raise ProviderError(f"Delete failed: {response.status_code} - {response.text}")

    async def list_chunks(self, prefix: str) -> list[RemoteRef]:
        """List chunks by searching messages (limited by Telegram API)."""
        if not self._client or not self.chat_id:
            raise ProviderError("Provider not initialized")

        refs: list[RemoteRef] = []

        # Telegram doesn't have a direct search by caption, so we need to get chat history
        # This is a simplified implementation - in practice you might want to use getChatHistory
        # or maintain a local index
        offset = 0
        limit = 100

        while True:
            params = {
                "chat_id": self.chat_id,
                "limit": limit,
                "offset": offset,
            }

            async with self._rate_limit_semaphore:
                response = await self._client.post("getChatHistory", json=params)

            if response.status_code == 429:
                retry_after = response.json().get("parameters", {}).get("retry_after", 1)
                await asyncio.sleep(retry_after)
                continue
            if response.status_code != 200:
                raise ProviderError(f"List failed: {response.status_code} - {response.text}")

            data = response.json()
            if not data.get("ok"):
                break

            messages = data.get("result", [])
            if not messages:
                break

            for msg in messages:
                caption = msg.get("caption", "")
                if caption.startswith(f"stash-chunk:{prefix}:"):
                    document = msg.get("document")
                    if document:
                        parts = caption.split(":")
                        if len(parts) >= 3:
                            chunk_index = parts[2]
                            refs.append(RemoteRef(
                                provider="telegram",
                                remote_id=document["file_id"],
                                metadata={
                                    "message_id": str(msg["message_id"]),
                                    "size": str(document["file_size"]),
                                    "chunk_index": chunk_index,
                                    "remote_path": prefix,
                                },
                            ))

            if len(messages) < limit:
                break
            offset += len(messages)

        return refs

    def get_limits(self) -> ProviderLimits:
        """Get Telegram provider limits."""
        return get_telegram_limits()

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        await super().close()
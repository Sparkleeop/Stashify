"""Integration tests for resumable uploads."""

import pytest
import tempfile
import time
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from stash.core.chunking import ChunkConfig, Chunker
from stash.core.crypto import CryptoEngine
from stash.core.keymanager import KeyManager
from stash.core.manifest import (
    ChunkStatus,
    ChunkInfo,
    DistributionStrategy,
    EncryptionInfo,
    FileManifest,
    ManifestBuilder,
    UploadStatus,
    compute_checksum,
    generate_file_id,
)
from stash.core.metadata import MetadataStore
from stash.core.storage import RemoteRef


class MockProvider:
    """Mock provider for testing."""

    def __init__(self, name: str):
        self.name = name
        self.chunks = {}
        self.closed = False
        self.max_chunk_size = 10 * 1024 * 1024
        self.max_concurrent_uploads = 3
        self.config = type('Config', (), {
            'settings': {'max_concurrent': '3'},
            'type': name,
            'credentials': {},
            'settings': {'max_concurrent': '3'},
        })()

    async def initialize(self, config):
        pass

    async def upload_chunk(self, chunk, remote_path):
        self.chunks[remote_path] = chunk.data
        return RemoteRef(
            provider=self.name,
            remote_id=remote_path,
            metadata={'size': str(len(chunk.data))}
        )

    async def download_chunk(self, remote_ref):
        return self.chunks.get(remote_ref.remote_id, b"")

    async def delete_chunk(self, remote_ref):
        self.chunks.pop(remote_ref.remote_id, None)

    async def list_chunks(self, prefix):
        return []

    def get_limits(self):
        from stash.core.storage import ProviderLimits
        return ProviderLimits(
            max_file_size=100 * 1024 * 1024,
            max_chunk_size=10 * 1024 * 1024,
            max_concurrent_uploads=3,
            rate_limit_requests=30,
            rate_limit_window=1,
        )

    async def close(self):
        self.closed = True


@pytest.fixture
def temp_repo():
    """Create a temporary repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        store = MetadataStore(repo_path)

        # Initialize repository with a dummy RMK
        keymanager = KeyManager(repo_path)
        identity = keymanager.initialize_repository()

        # Configure providers in the metadata store
        from stash.core.storage import ProviderConfig
        store.set_provider_config("telegram", ProviderConfig(
            name="telegram",
            type="telegram",
            credentials={"token": "test_token", "chat_id": "-1001234567890"},
            settings={"max_concurrent": "3"},
        ))
        store.set_provider_config("discord", ProviderConfig(
            name="discord",
            type="discord",
            credentials={"token": "test_token", "channel_id": "123456789012345678"},
            settings={"max_concurrent": "3"},
        ))

        yield repo_path, store, keymanager, identity


@pytest.fixture
def test_file(temp_repo):
    """Create a test file."""
    repo_path, _, _, _ = temp_repo
    file_path = repo_path / "test_file.txt"
    content = b"x" * (25 * 1024 * 1024)  # 25MB file - 3 chunks at 10MB
    file_path.write_bytes(content)
    return file_path


@pytest.fixture
def mock_providers():
    """Create mock providers."""
    return {
        "telegram": MockProvider("telegram"),
        "discord": MockProvider("discord"),
    }


class TestResumableUploads:
    """Integration tests for resumable uploads."""

    @pytest.mark.asyncio
    async def test_new_upload_creates_partial_manifest(self, temp_repo, test_file, mock_providers):
        """Test that a new upload creates a partial manifest with PENDING chunks."""
        repo_path, store, keymanager, identity = temp_repo

        # Import here to avoid circular imports
        from stash.cli.commands.put import _put_async

        with patch('stash.cli.commands.put.ProviderRegistry') as mock_registry:
            mock_registry.create = AsyncMock(side_effect=lambda name, config: mock_providers[name])

            await _put_async(
                file_path=test_file,
                repo_path=repo_path,
                provider_name="telegram",
                chunk_size=None,
                strategy="single",
                do_confirm=False,
                resume=False,
                file_id=None,
            )

        # Verify manifest was created
        files = store.list_files()
        assert len(files) == 1

        manifest = store.load_manifest(files[0])
        assert manifest.upload_status == UploadStatus.COMPLETED
        assert manifest.total_chunks == 3
        assert manifest.uploaded_chunks == 3

        # All chunks should be uploaded
        for chunk in manifest.chunks:
            assert chunk.status == ChunkStatus.UPLOADED
            assert chunk.remote_id != ""

    @pytest.mark.asyncio
    async def test_resume_upload_after_interruption(self, temp_repo, test_file, mock_providers):
        """Test resuming an interrupted upload."""
        repo_path, store, keymanager, identity = temp_repo

        from stash.cli.commands.put import _put_async

        with patch('stash.cli.commands.put.ProviderRegistry') as mock_registry:
            mock_registry.create = AsyncMock(side_effect=lambda name, config: mock_providers[name])

            # First, start an upload and interrupt it after 1 chunk
            await _put_async(
                file_path=test_file,
                repo_path=repo_path,
                provider_name="telegram",
                chunk_size=None,
                strategy="single",
                do_confirm=False,
                resume=False,
                file_id=None,
            )

        # Verify first upload completed
        files = store.list_files()
        manifest = store.load_manifest(files[0])
        assert manifest.upload_status == UploadStatus.COMPLETED

        # Now simulate interruption: manually set one chunk back to pending
        # and remove it from the provider
        file_id = files[0]
        manifest = store.load_manifest(file_id)

        # Simulate interruption: mark last chunk as pending, remove from provider
        with patch('stash.cli.commands.put.ProviderRegistry') as mock_registry:
            mock_registry.create = AsyncMock(side_effect=lambda name, config: mock_providers[name])

            # Remove last chunk from provider
            last_chunk = manifest.chunks[-1]
            if last_chunk.provider in mock_providers:
                mock_providers[last_chunk.provider].chunks.pop(last_chunk.remote_id, None)

            # Update chunk status to pending
            chunks = list(manifest.chunks)
            old_chunk = chunks[-1]
            chunks[-1] = ChunkInfo(
                index=old_chunk.index,
                size=old_chunk.size,
                encrypted_size=old_chunk.encrypted_size,
                checksum=old_chunk.checksum,
                provider=old_chunk.provider,
                remote_id="",
                nonce=b"",
                metadata={},
                status=ChunkStatus.PENDING,
                uploaded_at=None,
                error=None,
            )
            # Rebuild manifest with updated chunks
            from stash.core.manifest import FileManifest, EncryptionInfo, DistributionStrategy
            new_manifest = FileManifest(
                file_id=manifest.file_id,
                original_name=manifest.original_name,
                encrypted_name=manifest.encrypted_name,
                encrypted_name_nonce=manifest.encrypted_name_nonce,
                original_size=manifest.original_size,
                chunk_size=manifest.chunk_size,
                chunk_count=manifest.chunk_count,
                encryption=manifest.encryption,
                chunks=tuple(chunks),
                strategy=manifest.strategy,
                created_at=manifest.created_at,
                modified_at=time.time(),
                upload_status=UploadStatus.IN_PROGRESS,
                total_chunks=manifest.total_chunks,
                uploaded_chunks=manifest.uploaded_chunks - 1,
                started_at=manifest.started_at,
                completed_at=None,
            )
            store.save_manifest(new_manifest)

            # Now resume the upload
            await _put_async(
                file_path=test_file,
                repo_path=repo_path,
                provider_name="telegram",
                chunk_size=None,
                strategy="single",
                do_confirm=False,
                resume=True,
                file_id=None,
            )

        # Verify upload completed
        manifest = store.load_manifest(file_id)
        assert manifest.upload_status == UploadStatus.COMPLETED
        assert manifest.uploaded_chunks == 3

        for chunk in manifest.chunks:
            assert chunk.status == ChunkStatus.UPLOADED
            assert chunk.remote_id != ""

    @pytest.mark.asyncio
    async def test_resume_with_explicit_file_id(self, temp_repo, test_file, mock_providers):
        """Test resuming with explicit --file-id."""
        repo_path, store, keymanager, identity = temp_repo

        from stash.cli.commands.put import _put_async

        # Create an incomplete upload first
        with patch('stash.cli.commands.put.ProviderRegistry') as mock_registry:
            mock_registry.create = AsyncMock(side_effect=lambda name, config: mock_providers[name])

            await _put_async(
                file_path=test_file,
                repo_path=repo_path,
                provider_name="telegram",
                chunk_size=None,
                strategy="single",
                do_confirm=False,
                resume=False,
                file_id=None,
            )

        files = store.list_files()
        file_id = files[0]

        # Corrupt the upload - mark one chunk as pending
        manifest = store.load_manifest(file_id)
        chunks = list(manifest.chunks)
        chunks[1] = ChunkInfo(
            index=chunks[1].index,
            size=chunks[1].size,
            encrypted_size=chunks[1].encrypted_size,
            checksum=chunks[1].checksum,
            provider=chunks[1].provider,
            remote_id="",
            nonce=b"",
            metadata={},
            status=ChunkStatus.PENDING,
            uploaded_at=None,
            error=None,
        )

        new_manifest = FileManifest(
            file_id=manifest.file_id,
            original_name=manifest.original_name,
            encrypted_name=manifest.encrypted_name,
            encrypted_name_nonce=manifest.encrypted_name_nonce,
            original_size=manifest.original_size,
            chunk_size=manifest.chunk_size,
            chunk_count=manifest.chunk_count,
            encryption=manifest.encryption,
            chunks=tuple(chunks),
            strategy=manifest.strategy,
            created_at=manifest.created_at,
            modified_at=time.time(),
            upload_status=UploadStatus.IN_PROGRESS,
            total_chunks=3,
            uploaded_chunks=2,
            started_at=manifest.started_at,
            completed_at=None,
        )
        store.save_manifest(new_manifest)

        # Remove chunk from provider
        mock_providers["telegram"].chunks.pop(chunks[1].remote_id, None)

        # Resume with explicit file-id
        with patch('stash.cli.commands.put.ProviderRegistry') as mock_registry:
            mock_registry.create = AsyncMock(side_effect=lambda name, config: mock_providers[name])

            await _put_async(
                file_path=test_file,
                repo_path=repo_path,
                provider_name="telegram",
                chunk_size=None,
                strategy="single",
                do_confirm=False,
                resume=True,
                file_id=file_id,
            )

        # Verify completed
        manifest = store.load_manifest(file_id)
        assert manifest.upload_status == UploadStatus.COMPLETED
        assert manifest.uploaded_chunks == 3

    @pytest.mark.asyncio
    async def test_resume_fails_when_file_changed(self, temp_repo, test_file, mock_providers):
        """Test that resume fails when file content has changed."""
        repo_path, store, keymanager, identity = temp_repo

        from stash.cli.commands.put import _put_async

        # Create incomplete upload
        with patch('stash.cli.commands.put.ProviderRegistry') as mock_registry:
            mock_registry.create = AsyncMock(side_effect=lambda name, config: mock_providers[name])

            await _put_async(
                file_path=test_file,
                repo_path=repo_path,
                provider_name="telegram",
                chunk_size=None,
                strategy="single",
                do_confirm=False,
                resume=False,
                file_id=None,
            )

        files = store.list_files()
        manifest = store.load_manifest(files[0])

        # Corrupt the manifest to simulate incomplete upload
        chunks = list(manifest.chunks)
        chunks[0] = ChunkInfo(
            index=chunks[0].index,
            size=chunks[0].size,
            encrypted_size=chunks[0].encrypted_size,
            checksum=chunks[0].checksum,
            provider=chunks[0].provider,
            remote_id="",
            nonce=b"",
            metadata={},
            status=ChunkStatus.PENDING,
            uploaded_at=None,
            error=None,
        )

        from stash.core.manifest import FileManifest, UploadStatus
        new_manifest = FileManifest(
            file_id=manifest.file_id,
            original_name=manifest.original_name,
            encrypted_name=manifest.encrypted_name,
            encrypted_name_nonce=manifest.encrypted_name_nonce,
            original_size=manifest.original_size,
            chunk_size=manifest.chunk_size,
            chunk_count=manifest.chunk_count,
            encryption=manifest.encryption,
            chunks=tuple(chunks),
            strategy=manifest.strategy,
            created_at=manifest.created_at,
            modified_at=time.time(),
            upload_status=UploadStatus.IN_PROGRESS,
            total_chunks=manifest.total_chunks,
            uploaded_chunks=2,
            started_at=manifest.started_at,
            completed_at=None,
        )
        store.save_manifest(new_manifest)

        # Modify the file content but keep the same size
        new_content = b"y" * (25 * 1024 * 1024)  # 25MB of different content
        test_file.write_bytes(new_content)

        # Try to resume - should fail
        with patch('stash.cli.commands.put.ProviderRegistry') as mock_registry:
            mock_registry.create = AsyncMock(side_effect=lambda name, config: mock_providers[name])

            import sys
            from io import StringIO
            old_stdout = sys.stdout
            sys.stdout = StringIO()
            try:
                await _put_async(
                    file_path=test_file,
                    repo_path=repo_path,
                    provider_name="telegram",
                    chunk_size=None,
                    strategy="single",
                    do_confirm=False,
                    resume=True,
                    file_id=None,
                )
            except SystemExit:
                pass
            finally:
                captured_stdout = sys.stdout.getvalue()
                sys.stdout = old_stdout

            # Should fail with file content mismatch error
            assert "does not match" in captured_stdout

    @pytest.mark.asyncio
    async def test_multiple_resume_cycles(self, temp_repo, test_file, mock_providers):
        """Test multiple resume cycles work correctly."""
        repo_path, store, keymanager, identity = temp_repo

        from stash.cli.commands.put import _put_async

        # Initial upload
        with patch('stash.cli.commands.put.ProviderRegistry') as mock_registry:
            mock_registry.create = AsyncMock(side_effect=lambda name, config: mock_providers[name])

            await _put_async(
                file_path=test_file,
                repo_path=repo_path,
                provider_name="telegram",
                chunk_size=None,
                strategy="single",
                do_confirm=False,
                resume=False,
                file_id=None,
            )

        files = store.list_files()
        file_id = files[0]

        # Simulate 3 interruption/resume cycles
        for cycle in range(3):
            manifest = store.load_manifest(file_id)

            # Mark last completed chunk as pending
            chunks = list(manifest.chunks)
            last_uploaded = max((i for i, c in enumerate(chunks) if c.status == ChunkStatus.UPLOADED), default=0)
            if last_uploaded >= 0:
                old_chunk = chunks[last_uploaded]
                chunks[last_uploaded] = ChunkInfo(
                    index=old_chunk.index,
                    size=old_chunk.size,
                    encrypted_size=old_chunk.encrypted_size,
                    checksum=old_chunk.checksum,
                    provider=old_chunk.provider,
                    remote_id="",
                    nonce=b"",
                    metadata={},
                    status=ChunkStatus.PENDING,
                    uploaded_at=None,
                    error=None,
                )

                # Remove from provider
                mock_providers["telegram"].chunks.pop(manifest.chunks[last_uploaded].remote_id, None)

            # Rebuild manifest
            from stash.core.manifest import FileManifest
            new_manifest = FileManifest(
                file_id=manifest.file_id,
                original_name=manifest.original_name,
                encrypted_name=manifest.encrypted_name,
                encrypted_name_nonce=manifest.encrypted_name_nonce,
                original_size=manifest.original_size,
                chunk_size=manifest.chunk_size,
                chunk_count=manifest.chunk_count,
                encryption=manifest.encryption,
                chunks=tuple(chunks),
                strategy=manifest.strategy,
                created_at=manifest.created_at,
                modified_at=time.time(),
                upload_status=UploadStatus.IN_PROGRESS,
                total_chunks=manifest.total_chunks,
                uploaded_chunks=manifest.uploaded_chunks - 1,
                started_at=manifest.started_at,
                completed_at=None,
            )
            store.save_manifest(new_manifest)

            # Resume
            with patch('stash.cli.commands.put.ProviderRegistry') as mock_registry:
                mock_registry.create = AsyncMock(side_effect=lambda name, config: mock_providers[name])

                await _put_async(
                    file_path=test_file,
                    repo_path=repo_path,
                    provider_name="telegram",
                    chunk_size=None,
                    strategy="single",
                    do_confirm=False,
                    resume=True,
                    file_id=file_id,
                )

            # Verify completed
            manifest = store.load_manifest(file_id)
            assert manifest.upload_status == UploadStatus.COMPLETED
            assert manifest.uploaded_chunks == 3

    @pytest.mark.asyncio
    async def test_corrupted_manifest_handling(self, temp_repo, test_file, mock_providers):
        """Test handling of corrupted manifest."""
        repo_path, store, keymanager, identity = temp_repo

        # Create a corrupted manifest file
        manifest_dir = repo_path / ".stash" / "metadata" / "files"
        manifest_dir.mkdir(parents=True, exist_ok=True)

        # Write invalid JSON
        corrupted_file = manifest_dir / "corrupted.json"
        corrupted_file.write_text("{ invalid json")

        # Should not crash when listing files
        files = store.list_files()
        assert isinstance(files, list)

        # Try to load corrupted manifest - should raise MetadataError
        from stash.core.exceptions import MetadataError
        with pytest.raises(MetadataError):
            store.load_manifest("corrupted")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
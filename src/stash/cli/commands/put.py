"""CLI command: put - Store a file."""

import asyncio
import time
from pathlib import Path

import click

from stash.cli.output import confirm as confirm_prompt
from stash.cli.output import create_progress, format_size, print_error, print_info, print_success
from stash.core.chunking import ChunkConfig, Chunker
from stash.core.crypto import CryptoEngine
from stash.core.jobs import JobConfig
from stash.core.keymanager import KeyManager
from stash.core.manifest import (
    ChunkInfo,
    ChunkStatus,
    DistributionStrategy,
    EncryptionInfo,
    ManifestBuilder,
    UploadStatus,
    compute_checksum,
    generate_file_id,
)
from stash.core.metadata import MetadataStore
from stash.providers import ProviderRegistry


@click.command()
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
@click.option("--provider", help="Specific provider to use (default: first available)")
@click.option("--chunk-size", type=int, help="Chunk size in bytes (default: provider limit)")
@click.option("--strategy", type=click.Choice(["single", "split", "balanced", "replicated"]), default="single", help="Distribution strategy")
@click.option("--resume", is_flag=True, help="Resume an incomplete upload")
@click.option("--file-id", help="File ID to resume (required with --resume if multiple incomplete uploads exist)")
@click.option("--confirm/--no-confirm", default=True, help="Confirm before upload")
@click.pass_context
def put_cmd(ctx: click.Context, file_path: Path, provider: str | None, chunk_size: int | None, strategy: str, resume: bool, file_id: str | None, confirm: bool) -> None:
    """Store a file in Stash."""
    asyncio.run(_put_async(file_path, ctx.obj["repo"], provider, chunk_size, strategy, confirm, resume, file_id))


async def _put_async(
    file_path: Path,
    repo_path: Path,
    provider_name: str | None,
    chunk_size: int | None,
    strategy: str,
    do_confirm: bool,
    resume: bool,
    file_id: str | None,
) -> None:
    repo = repo_path.resolve()
    store = MetadataStore(repo)
    keymanager = KeyManager(repo)

    providers = store.list_providers()
    if not providers:
        print_error("No providers configured. Run: stash provider add discord")
        return

    if provider_name:
        if provider_name not in providers:
            print_error(f"Provider '{provider_name}' not found")
            return
        provider_names = [provider_name]
    else:
        provider_names = providers

    if not file_path.exists():
        print_error(f"File not found: {file_path}")
        return

    file_size = file_path.stat().st_size
    if file_size == 0:
        print_error("Cannot store empty file")
        return

    if do_confirm and not confirm_prompt(f"Store '{file_path.name}' ({format_size(file_size)})?"):
        print_info("Cancelled")
        return

    # Get RMK from keyring
    try:
        rmk = keymanager.get_rmk()
    except Exception as e:
        print_error(f"Failed to retrieve RMK: {e}")
        print_info("Run 'stash unlock' if this is a new device")
        return

    crypto = CryptoEngine()

    # Handle resume logic
    existing_manifest = None
    file_id = None
    file_key = None
    encrypted_name = None
    encrypted_name_nonce = None
    file_size = file_path.stat().st_size

    if resume:
        # Find existing incomplete manifest
        if file_id:
            # Explicit file ID provided
            if not store.file_exists(file_id):
                print_error(f"File with ID '{file_id}' not found")
                return
            existing_manifest = store.load_manifest(file_id)
        else:
            # Auto-detect by filename
            for fid in store.list_files():
                manifest = store.load_manifest(fid)
                if manifest.original_name == file_path.name and manifest.upload_status != UploadStatus.COMPLETED:
                    existing_manifest = manifest
                    break

        if existing_manifest is None:
            print_error("No incomplete upload found to resume")
            print_info("Run 'stash put' without --resume to start a new upload")
            return

        # Verify file matches
        if existing_manifest.original_size != file_path.stat().st_size:
            print_error("File size does not match the incomplete upload")
            raise SystemExit(1)

        # Verify file content matches (check first chunk checksum if available)
        if existing_manifest.chunks:
            chunker = Chunker(ChunkConfig(chunk_size=existing_manifest.chunk_size))
            first_chunk_data = next(chunker.chunk_file(file_path)).data
            first_checksum = compute_checksum(first_chunk_data)
            if existing_manifest.chunks[0].checksum != first_checksum:
                print_error("File content does not match the incomplete upload")
                raise SystemExit(1)

        file_id = existing_manifest.file_id
        file_key = crypto.derive_file_key_from_rmk(rmk, file_id.encode())
        
        # Restore encrypted filename info
        encrypted_name = existing_manifest.encrypted_name
        encrypted_name_nonce = existing_manifest.encrypted_name_nonce
        
        print_info(f"Resuming upload of '{existing_manifest.original_name}' ({existing_manifest.file_id})")
        print_info(f"Progress: {existing_manifest.uploaded_chunks}/{existing_manifest.total_chunks} chunks uploaded")
    else:
        # New upload - generate new file_id and file_key
        file_id = generate_file_id()
        file_key = crypto.generate_file_key(rmk)
        
        # Encrypt the filename using the file key
        encrypted_name_ciphertext, encrypted_name_nonce = crypto.encrypt_filename(
            file_path.name.encode(), file_key
        )
        encrypted_name = encrypted_name_ciphertext.hex()

    crypto = CryptoEngine()
    if not file_key:
        file_key = crypto.generate_file_key(rmk)

    # Encrypt the filename using the file key
    if encrypted_name is None:
        encrypted_name_ciphertext, encrypted_name_nonce = crypto.encrypt_filename(
            file_path.name.encode(), file_key
        )
        encrypted_name = encrypted_name_ciphertext.hex()

    provider_configs = {}
    for name in provider_names:
        config = store.get_provider_config(name)
        if not config:
            print_error(f"Provider config not found: {name}")
            return
        provider_configs[name] = config

    provider_instances = {}
    for name, config in provider_configs.items():
        instance = await ProviderRegistry.create(config.type, config)
        provider_instances[name] = instance

    limits = {name: p.get_limits() for name, p in provider_instances.items()}
    max_chunk = min(l.max_chunk_size for l in limits.values())
    effective_chunk_size = min(chunk_size or max_chunk, max_chunk)

    chunker = Chunker(ChunkConfig(chunk_size=effective_chunk_size))
    num_chunks = chunker.get_num_chunks(file_size)

    dist_strategy = DistributionStrategy(strategy)

    # Initialize manifest builder
    if resume and existing_manifest:
        # Resume existing manifest - keep existing chunks, update status
        file_id = existing_manifest.file_id
        encryption_info = existing_manifest.encryption
        builder = ManifestBuilder(
            file_id=existing_manifest.file_id,
            original_name=existing_manifest.original_name,
            encrypted_name=existing_manifest.encrypted_name,
            encrypted_name_nonce=existing_manifest.encrypted_name_nonce,
            original_size=existing_manifest.original_size,
            chunk_size=existing_manifest.chunk_size,
            encryption=existing_manifest.encryption,
            strategy=DistributionStrategy(existing_manifest.strategy),
        )
        # Pre-populate with existing chunks
        for chunk in existing_manifest.chunks:
            builder.add_chunk(
                index=chunk.index,
                size=chunk.size,
                encrypted_size=chunk.encrypted_size,
                checksum=chunk.checksum,
                provider=chunk.provider,
                remote_id=chunk.remote_id,
                nonce=chunk.nonce,
                metadata=chunk.metadata,
                status=chunk.status,
                uploaded_at=chunk.uploaded_at,
                error=chunk.error,
            )
    else:
        # New upload
        file_id = generate_file_id()
        file_key = crypto.generate_file_key(rmk)
        
        # Encrypt the filename using the file key
        encrypted_name_ciphertext, encrypted_name_nonce = crypto.encrypt_filename(
            file_path.name.encode(), file_key
        )
        encrypted_name = encrypted_name_ciphertext.hex()

        encryption_info = EncryptionInfo(
            algorithm="AES-256-GCM",
            key_size=32,
            nonce_size=12,
            chunk_key_derivation="HKDF-SHA256",
            file_key_salt=file_key.salt,
            file_key_wrapped=None,
        )

        builder = ManifestBuilder(
            file_id=file_id,
            original_name=file_path.name,
            encrypted_name=encrypted_name,
            encrypted_name_nonce=encrypted_name_nonce,
            original_size=file_size,
            chunk_size=effective_chunk_size,
            encryption=encryption_info,
            strategy=dist_strategy,
        )
        # Pre-populate all chunks as PENDING
        for i in range(num_chunks):
            builder.add_chunk(
                index=i,
                size=0,  # Will be updated when chunk is uploaded
                encrypted_size=0,
                checksum="",
                provider="",
                remote_id="",
                nonce=b"",
                status=ChunkStatus.PENDING,
            )

    provider_configs = {}
    for name in provider_names:
        config = store.get_provider_config(name)
        if not config:
            print_error(f"Provider config not found: {name}")
            return
        provider_configs[name] = config

    provider_instances = {}
    for name, config in provider_configs.items():
        instance = await ProviderRegistry.create(config.type, config)
        provider_instances[name] = instance

    limits = {name: p.get_limits() for name, p in provider_instances.items()}
    max_chunk = min(l.max_chunk_size for l in limits.values())
    effective_chunk_size = min(chunk_size or max_chunk, max_chunk)

    chunker = Chunker(ChunkConfig(chunk_size=effective_chunk_size))
    num_chunks = chunker.get_num_chunks(file_size)

    dist_strategy = DistributionStrategy(strategy)

    # Save initial manifest (PENDING state)
    manifest = builder.build()
    store.save_manifest(manifest)

    if not resume:
        print_info(f"Processing {num_chunks} chunks...")

    JobConfig(max_workers=min(4, num_chunks))

    semaphores = {name: asyncio.Semaphore(int(p.config.settings.get("max_concurrent", "3"))) for name, p in provider_instances.items()}

    progress = create_progress()
    task = progress.add_task("Uploading", total=num_chunks)

    # Track which chunks are already uploaded (for resume)
    uploaded_indices = set()
    if resume and existing_manifest:
        for chunk in existing_manifest.chunks:
            if chunk.status == ChunkStatus.UPLOADED:
                uploaded_indices.add(chunk.index)

    async def upload_chunk(chunk_data: bytes, chunk_index: int, provider_name: str) -> tuple[bytes, dict[str, str]]:
        """Encrypt and upload a single chunk."""
        async with semaphores[provider_name]:
            encrypted = crypto.encrypt_chunk(chunk_data, file_key, chunk_index)
            remote_path = f"{file_id}/chunk-{chunk_index:06d}"
            from stash.core.chunking import Chunk
            encrypted_chunk = Chunk(
                index=chunk_index,
                data=encrypted.ciphertext,
                offset=0,
                size=len(encrypted.ciphertext),
                is_last=False,
            )
            remote_ref = await provider_instances[provider_name].upload_chunk(encrypted_chunk, remote_path)
            # Return nonce and a dict with remote_id and metadata
            return encrypted.nonce, {"remote_id": remote_ref.remote_id, "metadata": remote_ref.metadata}  # type: ignore[dict-item]

    progress = create_progress()
    task = progress.add_task("Uploading", total=num_chunks)

    # Update progress for already uploaded chunks
    for _ in uploaded_indices:
        progress.advance(task)

    for c in chunker.chunk_file(file_path):
        if c.index in uploaded_indices:
            print_info(f"Chunk {c.index} already uploaded, skipping")
            progress.advance(task)
            continue

        checksum = compute_checksum(c.data)

        if dist_strategy == DistributionStrategy.SINGLE:
            target = provider_names[0]
        elif dist_strategy == DistributionStrategy.SPLIT:
            target = provider_names[c.index % len(provider_names)]
        else:
            target = provider_names[0]

        # Mark chunk as uploading
        builder.chunks[c.index] = ChunkInfo(
            index=c.index,
            size=c.size,
            encrypted_size=0,
            checksum=checksum,
            provider=target,
            remote_id="",
            nonce=b"",
            metadata={},
            status=ChunkStatus.UPLOADING,
        )
        store.save_manifest(builder.build())

        nonce, upload_result = await upload_chunk(c.data, c.index, target)
        remote_id: str = upload_result["remote_id"]
        metadata: dict[str, str] = upload_result["metadata"]  # type: ignore[assignment]

        # Update chunk as uploaded
        builder.chunks[c.index] = ChunkInfo(
            index=c.index,
            size=c.size,
            encrypted_size=len(metadata.get("size", "0")),
            checksum=checksum,
            provider=target,
            remote_id=remote_id,
            nonce=nonce,
            metadata=metadata,
            status=ChunkStatus.UPLOADED,
            uploaded_at=time.time(),
            error=None,
        )
        manifest = builder.build()
        store.save_manifest(manifest)

        progress.advance(task)

    # Final manifest build and save
    manifest = builder.build()
    store.save_manifest(manifest)

    for instance in provider_instances.values():
        await instance.close()

    print_success(f"Stored '{file_path.name}' as {manifest.file_id}")
    print_info(f"Chunks: {manifest.chunk_count}, Size: {format_size(manifest.original_size)}")


put_commands = put_cmd
"""CLI command: put - Store a file."""

import asyncio
from pathlib import Path

import click

from stash.cli.output import confirm as confirm_prompt
from stash.cli.output import create_progress, format_size, print_error, print_info, print_success
from stash.core.chunking import ChunkConfig, Chunker
from stash.core.crypto import CryptoEngine
from stash.core.jobs import JobConfig
from stash.core.keymanager import KeyManager
from stash.core.manifest import (
    DistributionStrategy,
    EncryptionInfo,
    ManifestBuilder,
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
@click.option("--confirm/--no-confirm", default=True, help="Confirm before upload")
@click.pass_context
def put_cmd(ctx: click.Context, file_path: Path, provider: str | None, chunk_size: int | None, strategy: str, confirm: bool) -> None:
    """Store a file in Stash."""
    asyncio.run(_put_async(file_path, ctx.obj["repo"], provider, chunk_size, strategy, confirm))


async def _put_async(
    file_path: Path,
    repo_path: Path,
    provider_name: str | None,
    chunk_size: int | None,
    strategy: str,
    do_confirm: bool,
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
    file_id = generate_file_id()
    file_key = crypto.generate_file_key(rmk)

    # Encrypt the filename using the file key
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
        original_size=file_path.stat().st_size,
        chunk_size=effective_chunk_size,
        encryption=encryption_info,
        strategy=dist_strategy,
    )

    print_info(f"Processing {num_chunks} chunks...")

    JobConfig(max_workers=min(4, num_chunks))

    semaphores = {name: asyncio.Semaphore(int(p.config.settings.get("max_concurrent", "3"))) for name, p in provider_instances.items()}

    progress = create_progress()
    task = progress.add_task("Uploading", total=num_chunks)

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
            return encrypted.nonce, remote_ref.metadata

    progress = create_progress()
    task = progress.add_task("Uploading", total=num_chunks)

    for chunk in chunker.chunk_file(file_path):
        checksum = compute_checksum(chunk.data)

        if dist_strategy == DistributionStrategy.SINGLE:
            target = provider_names[0]
        elif dist_strategy == DistributionStrategy.SPLIT:
            target = provider_names[chunk.index % len(provider_names)]
        else:
            target = provider_names[0]

        nonce, metadata = await upload_chunk(chunk.data, chunk.index, target)

        builder.add_chunk(
            index=chunk.index,
            size=chunk.size,
            encrypted_size=len(metadata.get("size", "0")),
            checksum=checksum,
            provider=target,
            remote_id=metadata.get("remote_id", ""),
            nonce=nonce,
            metadata=metadata,
        )
        progress.advance(task)

    manifest = builder.build()
    store.save_manifest(manifest)

    for instance in provider_instances.values():
        await instance.close()

    print_success(f"Stored '{file_path.name}' as {manifest.file_id}")
    print_info(f"Chunks: {manifest.chunk_count}, Size: {format_size(manifest.original_size)}")


put_commands = put_cmd
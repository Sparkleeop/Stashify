"""CLI command: put - Store a file."""

import asyncio
from pathlib import Path

import click

from stash.cli.output import confirm as confirm_prompt
from stash.cli.output import create_progress, format_size, print_error, print_info, print_success
from stash.core.chunking import ChunkConfig, Chunker
from stash.core.crypto import CryptoEngine
from stash.core.jobs import JobConfig
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
@click.option("--password", prompt=True, hide_input=True, help="Encryption password")
@click.option("--confirm/--no-confirm", default=True, help="Confirm before upload")
@click.pass_context
def put_cmd(ctx: click.Context, file_path: Path, provider: str | None, chunk_size: int | None, strategy: str, password: str, confirm: bool) -> None:
    """Store a file in Stash."""
    asyncio.run(_put_async(file_path, ctx.obj["repo"], provider, chunk_size, strategy, password, confirm))


async def _put_async(
    file_path: Path,
    repo_path: Path,
    provider_name: str | None,
    chunk_size: int | None,
    strategy: str,
    password: str,
    do_confirm: bool,
) -> None:
    repo = repo_path.resolve()
    store = MetadataStore(repo)

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

    crypto = CryptoEngine()
    file_key = crypto.generate_file_key()
    wrapped_key = crypto.encrypt_file_key(file_key, password)

    # Encrypt the filename
    encrypted_name_chunk = crypto.encrypt_chunk(file_path.name.encode(), file_key, -1)
    encrypted_name = encrypted_name_chunk.ciphertext.hex()
    encrypted_name_nonce = encrypted_name_chunk.nonce

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
        file_key_wrapped=wrapped_key,
    )

    builder = ManifestBuilder(
        file_id=generate_file_id(),
        original_name=file_path.name,
        encrypted_name=encrypted_name,
        encrypted_name_nonce=encrypted_name_nonce,
        original_size=file_size,
        chunk_size=effective_chunk_size,
        encryption=encryption_info,
        strategy=dist_strategy,
    )

    print_info(f"Processing {num_chunks} chunks ({format_size(effective_chunk_size)} each)...")

    JobConfig(max_workers=min(4, num_chunks))

    semaphores = {name: asyncio.Semaphore(int(p.config.settings.get("max_concurrent", "3"))) for name, p in provider_instances.items()}

    progress = create_progress()
    task = progress.add_task("Uploading", total=num_chunks)

    from stash.core.chunking import Chunk

    async def upload_chunk(chunk: Chunk, provider_name: str) -> None:
        async with semaphores[provider_name]:
            # Use opaque identifier: file_id + chunk index (no filename)
            remote_path = f"{builder.file_id}/chunk-{chunk.index:06d}"
            remote_ref = await provider_instances[provider_name].upload_chunk(chunk, remote_path)
            checksum = compute_checksum(chunk.data)
            builder.add_chunk(
                index=chunk.index,
                size=chunk.size,
                encrypted_size=len(remote_ref.metadata.get("size", "0")),
                checksum=checksum,
                provider=provider_name,
                remote_id=remote_ref.remote_id,
                nonce=encrypted.nonce,
                metadata=remote_ref.metadata,
            )
            progress.advance(task)

    with progress:
        for chunk in chunker.chunk_file(file_path):
            encrypted = crypto.encrypt_chunk(chunk.data, file_key, chunk.index)
            encrypted_chunk = type(chunk)(
                index=chunk.index,
                data=encrypted.ciphertext,
                offset=chunk.offset,
                size=len(encrypted.ciphertext),
                is_last=chunk.is_last,
            )

            if dist_strategy == DistributionStrategy.SINGLE:
                target = provider_names[0]
            elif dist_strategy == DistributionStrategy.SPLIT:
                target = provider_names[chunk.index % len(provider_names)]
            else:
                target = provider_names[0]

            await upload_chunk(encrypted_chunk, target)

    manifest = builder.build()
    store.save_manifest(manifest)

    for instance in provider_instances.values():
        await instance.close()

    print_success(f"Stored '{file_path.name}' as {manifest.file_id}")
    print_info(f"Chunks: {manifest.chunk_count}, Size: {format_size(manifest.original_size)}")


put_commands = put_cmd
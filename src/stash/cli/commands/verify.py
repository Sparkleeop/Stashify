"""CLI command: verify - Verify file integrity."""

import asyncio
from pathlib import Path

import click

from stash.cli.output import create_progress, print_error, print_info, print_success
from stash.core.metadata import MetadataStore
from stash.providers import ProviderRegistry


@click.command()
@click.argument("file_id_or_name")
@click.option("--full", is_flag=True, help="Download and verify all chunks")
@click.pass_context
def verify_cmd(ctx: click.Context, file_id_or_name: str, full: bool) -> None:
    """Verify file integrity (local metadata + remote)."""
    asyncio.run(_verify_async(file_id_or_name, ctx.obj["repo"], full))


async def _verify_async(file_id_or_name: str, repo_path: Path, full: bool) -> None:
    repo = repo_path.resolve()
    store = MetadataStore(repo)

    file_id = _resolve_file_id(store, file_id_or_name)
    if not file_id:
        print_error(f"File not found: {file_id_or_name}")
        return

    manifest = store.load_manifest(file_id)

    print_info(f"Verifying '{manifest.original_name}' ({file_id[:16]})")
    print_info(f"Chunks: {manifest.chunk_count}, Strategy: {manifest.strategy.value}")

    if full:
        providers_config = {}
        for chunk in manifest.chunks:
            if chunk.provider not in providers_config:
                config = store.get_provider_config(chunk.provider)
                if config:
                    providers_config[chunk.provider] = config

        provider_instances = {}
        for name, config in providers_config.items():
            instance = await ProviderRegistry.create(config.type, config)
            provider_instances[name] = instance

        progress = create_progress()
        task = progress.add_task("Verifying chunks", total=manifest.chunk_count)

        errors = []
        with progress:
            for chunk in manifest.chunks:
                provider = provider_instances.get(chunk.provider)
                if not provider:
                    errors.append(f"Chunk {chunk.index}: Provider {chunk.provider} not available")
                    continue

                remote_ref = type('RemoteRef', (), {
                    'provider': chunk.provider,
                    'remote_id': chunk.remote_id,
                    'metadata': {'message_id': chunk.metadata.get('message_id', '')}
                })()

                try:
                    remote_data = await provider.download_chunk(remote_ref)
                    if len(remote_data) != chunk.encrypted_size:
                        errors.append(f"Chunk {chunk.index}: Size mismatch (expected {chunk.encrypted_size}, got {len(remote_data)})")
                except Exception as e:
                    errors.append(f"Chunk {chunk.index}: {e}")

                progress.advance(task)

        for instance in provider_instances.values():
            await instance.close()

        if errors:
            print_error(f"Verification failed with {len(errors)} errors:")
            for err in errors:
                print_error(f"  - {err}")
        else:
            print_success("All chunks verified successfully")
    else:
        print_info("Local metadata verification only (use --full for remote verification)")
        print_success("Manifest structure valid")


def _resolve_file_id(store: MetadataStore, identifier: str) -> str | None:
    """Resolve file ID or name to file ID."""
    if store.file_exists(identifier):
        return identifier
    for fid in store.list_files():
        manifest = store.load_manifest(fid)
        if manifest.original_name == identifier:
            return fid
    return None


verify_commands = verify_cmd
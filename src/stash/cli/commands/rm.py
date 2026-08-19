"""CLI command: rm - Remove a stored file."""

import asyncio
from pathlib import Path

import click

from stash.cli.output import confirm, print_error, print_info, print_success
from stash.core.metadata import MetadataStore
from stash.providers import ProviderRegistry


@click.command()
@click.argument("file_id_or_name")
@click.option("--force", "-f", is_flag=True, help="Force removal without confirmation")
@click.option("--remote/--local-only", default=True, help="Also delete from remote providers")
@click.pass_context
def rm_cmd(ctx: click.Context, file_id_or_name: str, force: bool, remote: bool) -> None:
    """Remove a stored file."""
    asyncio.run(_rm_async(file_id_or_name, ctx.obj["repo"], force, remote))


async def _rm_async(file_id_or_name: str, repo_path: Path, force: bool, remote: bool) -> None:
    repo = repo_path.resolve()
    store = MetadataStore(repo)

    file_id = _resolve_file_id(store, file_id_or_name)
    if not file_id:
        print_error(f"File not found: {file_id_or_name}")
        return

    manifest = store.load_manifest(file_id)

    if not force and not confirm(f"Remove '{manifest.original_name}' ({file_id[:16]})?"):
        print_info("Cancelled")
        return

    if remote:
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

        for chunk in manifest.chunks:
            provider = provider_instances.get(chunk.provider)
            if provider:
                try:
                    remote_ref = type('RemoteRef', (), {
                        'provider': chunk.provider,
                        'remote_id': chunk.remote_id,
                        'metadata': {'message_id': chunk.metadata.get('message_id', '')}
                    })()
                    await provider.delete_chunk(remote_ref)
                except Exception as e:
                    print_info(f"Warning: Failed to delete chunk {chunk.index} from {chunk.provider}: {e}")

        for instance in provider_instances.values():
            await instance.close()

    store.delete_manifest(file_id)
    print_success(f"Removed '{manifest.original_name}' ({file_id[:16]})")


def _resolve_file_id(store: MetadataStore, identifier: str) -> str | None:
    """Resolve file ID or name to file ID."""
    if store.file_exists(identifier):
        return identifier
    for fid in store.list_files():
        manifest = store.load_manifest(fid)
        if manifest.original_name == identifier:
            return fid
    return None


rm_commands = rm_cmd
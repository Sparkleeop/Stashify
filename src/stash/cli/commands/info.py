"""CLI command: info - Show file metadata."""


import click

from stash.cli.output import print_error, print_file_info
from stash.core.metadata import MetadataStore


@click.command()
@click.argument("file_id_or_name")
@click.pass_context
def info_cmd(ctx: click.Context, file_id_or_name: str) -> None:
    """Show detailed file metadata."""
    repo = ctx.obj["repo"].resolve()
    store = MetadataStore(repo)

    file_id = _resolve_file_id(store, file_id_or_name)
    if not file_id:
        print_error(f"File not found: {file_id_or_name}")
        return

    manifest = store.load_manifest(file_id)

    providers = {}
    for name in store.list_providers():
        config = store.get_provider_config(name)
        if config:
            providers[name] = config

    print_file_info(manifest, providers)


def _resolve_file_id(store: MetadataStore, identifier: str) -> str | None:
    """Resolve file ID or name to file ID."""
    if store.file_exists(identifier):
        return identifier
    for fid in store.list_files():
        manifest = store.load_manifest(fid)
        if manifest.original_name == identifier:
            return fid
    return None


info_commands = info_cmd
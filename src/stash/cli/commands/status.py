"""CLI command: status - Show overall repository status."""

from pathlib import Path

import click

from stash.cli.output import format_size, print_info, print_table
from stash.core.metadata import MetadataStore


@click.command()
@click.pass_context
def status_cmd(ctx: click.Context) -> None:
    """Show overall repository status."""
    repo = ctx.obj["repo"].resolve()
    store = MetadataStore(repo)

    config = store.load_config()
    providers = store.list_providers()
    files = store.list_files()

    print_info(f"Repository: {repo}")
    print_info(f"Version: {config.get('version', 'unknown')}")

    if providers:
        rows = []
        for name in providers:
            pconfig = store.get_provider_config(name)
            ptype = pconfig.type if pconfig else "unknown"
            channel = pconfig.credentials.get("channel_id", "unknown") if pconfig else "unknown"
            rows.append([name, ptype, channel])
        print_table("Providers", ["Name", "Type", "Channel"], rows)
    else:
        print_info("No providers configured")

    total_size = 0
    total_chunks = 0
    for fid in files:
        manifest = store.load_manifest(fid)
        total_size += manifest.original_size
        total_chunks += manifest.chunk_count

    print_info(f"Files: {len(files)}")
    print_info(f"Total size: {format_size(total_size)}")
    print_info(f"Total chunks: {total_chunks}")


status_commands = status_cmd
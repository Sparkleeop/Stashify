"""CLI command: ls - List stored files."""

from pathlib import Path

import click

from stash.cli.output import format_size, format_timestamp, print_info, print_table
from stash.core.metadata import MetadataStore


@click.command()
@click.option("--long", "-l", is_flag=True, help="Show detailed information")
@click.pass_context
def ls_cmd(ctx: click.Context, long: bool) -> None:
    """List stored files."""
    repo = ctx.obj["repo"].resolve()
    store = MetadataStore(repo)

    files = store.list_files()
    if not files:
        print_info("No files stored")
        return

    if long:
        rows = []
        for fid in files:
            manifest = store.load_manifest(fid)
            rows.append([
                fid[:16],
                manifest.original_name,
                format_size(manifest.original_size),
                str(manifest.chunk_count),
                format_timestamp(manifest.created_at),
            ])
        print_table("Stored Files", ["File ID", "Name", "Size", "Chunks", "Created"], rows)
    else:
        for fid in files:
            manifest = store.load_manifest(fid)
            print_info(f"{fid[:16]}  {manifest.original_name}  ({format_size(manifest.original_size)})")


ls_commands = ls_cmd
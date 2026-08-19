"""CLI command: init - Initialize a new Stash repository."""


import click

from stash.cli.output import print_error, print_info, print_success
from stash.core.metadata import MetadataStore


@click.command()
@click.option("--force", "-f", is_flag=True, help="Overwrite existing repository")
@click.pass_context
def init_cmd(ctx: click.Context, force: bool) -> None:
    """Initialize a new Stash repository."""
    repo_path = ctx.obj["repo"]
    metadata_dir = repo_path / ".stash" / "metadata"

    if metadata_dir.exists() and not force:
        print_error(f"Repository already exists at {repo_path}")
        print_info("Use --force to overwrite")
        return

    store = MetadataStore(repo_path)
    store.save_config({
        "version": 1,
        "created_at": __import__("time").time(),
        "providers": {},
    })

    print_success(f"Initialized Stash repository at {repo_path}")
    print_info("Add a provider with: stash provider add discord")


init_commands = init_cmd
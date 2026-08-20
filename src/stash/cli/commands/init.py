"""CLI command: init - Initialize a new Stash repository."""

import click

from stash.cli.output import print_error, print_info, print_success, print_warning
from stash.core.keymanager import KeyManager


@click.command()
@click.option("--force", "-f", is_flag=True, help="Overwrite existing repository")
@click.pass_context
def init_cmd(ctx: click.Context, force: bool) -> None:
    """Initialize a new Stash repository."""
    repo_path = ctx.obj["repo"]
    keymanager = KeyManager(repo_path)

    if keymanager.has_repository_identity() and not force:
        print_error(f"Repository already initialized at {repo_path}")
        print_info("Use --force to reinitialize")
        return

    if force:
        keymanager.lock_repository()

    try:
        identity = keymanager.initialize_repository()
    except Exception as e:
        print_error(f"Failed to initialize repository: {e}")
        return

    print_success(f"Initialized Stash repository at {repo_path}")
    print_info(f"Repository ID: {identity.repository_id}")
    print_warning("Store this recovery key securely!")
    print_info(f"Recovery key (RMK): {keymanager.get_rmk().hex()}")
    print_warning("This key can unlock the repository on any device")
    print_info("Add a provider with: stash provider add discord")


init_commands = init_cmd
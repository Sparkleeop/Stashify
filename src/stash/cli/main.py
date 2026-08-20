"""Stash CLI main entry point."""

from pathlib import Path

import click

from stash import __version__
from stash.cli.commands.get import get_commands
from stash.cli.commands.info import info_commands
from stash.cli.commands.init import init_commands
from stash.cli.commands.key import key_commands
from stash.cli.commands.ls import ls_commands
from stash.cli.commands.provider import provider_commands
from stash.cli.commands.put import put_commands
from stash.cli.commands.rm import rm_commands
from stash.cli.commands.status import status_commands
from stash.cli.commands.verify import verify_commands


@click.group(invoke_without_command=True)
@click.version_option(version=__version__)
@click.option("--repo", "-r", type=click.Path(path_type=Path), help="Repository path")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.pass_context
def main(ctx: click.Context, repo: Path | None, verbose: bool) -> None:
    """Stash - Privacy-focused CLI storage using third-party platforms."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["repo"] = repo.resolve() if repo else Path.cwd()


main.add_command(init_commands)
main.add_command(provider_commands)
main.add_command(put_commands)
main.add_command(get_commands)
main.add_command(ls_commands)
main.add_command(info_commands)
main.add_command(rm_commands)
main.add_command(verify_commands)
main.add_command(status_commands)
main.add_command(key_commands)


if __name__ == "__main__":
    main()
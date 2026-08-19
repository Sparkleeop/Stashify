"""CLI commands package."""

from stash.cli.commands.get import get_commands
from stash.cli.commands.info import info_commands
from stash.cli.commands.init import init_commands
from stash.cli.commands.ls import ls_commands
from stash.cli.commands.provider import provider_commands
from stash.cli.commands.put import put_commands
from stash.cli.commands.rm import rm_commands
from stash.cli.commands.status import status_commands
from stash.cli.commands.verify import verify_commands

__all__ = [
    "init_commands",
    "provider_commands",
    "put_commands",
    "get_commands",
    "ls_commands",
    "info_commands",
    "rm_commands",
    "verify_commands",
    "status_commands",
]
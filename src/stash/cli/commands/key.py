"""CLI commands: key management - lock, unlock, status."""

import click

from stash.cli.output import print_error, print_info, print_success, print_warning
from stash.core.keymanager import KeyManager


@click.group()
def key_commands() -> None:
    """Repository key management."""
    pass


@key_commands.command("lock")
@click.pass_context
def lock_cmd(ctx: click.Context) -> None:
    """Lock the repository by removing RMK from keyring."""
    repo = ctx.obj["repo"].resolve()
    keymanager = KeyManager(repo)

    if not keymanager.get_repository_identity():
        print_info("Repository not initialized")
        return

    keymanager.lock_repository()
    print_success("Repository locked (RMK removed from keyring)")
    print_info("Run 'stash unlock' to restore access")


@key_commands.command("unlock")
@click.option("--recovery-key", help="Recovery key (hex) to restore RMK")
@click.pass_context
def unlock_cmd(ctx: click.Context, recovery_key: str | None) -> None:
    """Unlock the repository on a new device using a recovery key."""
    repo = ctx.obj["repo"].resolve()
    keymanager = KeyManager(repo)

    if keymanager.has_repository_identity():
        print_info("Repository already unlocked")
        return

    if not recovery_key:
        print_error("Recovery key required. Provide --recovery-key <hex>")
        print_info("The recovery key is the RMK hex that was generated during 'stash init'")
        return

    try:
        rmk_bytes = bytes.fromhex(recovery_key)
    except ValueError:
        print_error("Invalid recovery key format (must be hex)")
        return

    if len(rmk_bytes) != 32:
        print_error("Recovery key must be 32 bytes (64 hex characters)")
        return

    try:
        identity = keymanager.unlock_repository(rmk_bytes)
        print_success("Repository unlocked successfully")
        print_info(f"Repository ID: {identity.repository_id}")
    except Exception as e:
        print_error(f"Failed to unlock repository: {e}")


@key_commands.command("status")
@click.pass_context
def key_status_cmd(ctx: click.Context) -> None:
    """Show key management status."""
    repo = ctx.obj["repo"].resolve()
    keymanager = KeyManager(repo)

    identity = keymanager.get_repository_identity()
    if identity is None:
        print_warning("Repository not initialized or locked")
        return

    try:
        keymanager.get_rmk()
        print_success("Repository unlocked")
        print_info(f"Repository ID: {identity.repository_id}")
        print_info(f"Created: {identity.created_at:.0f}")
    except Exception as e:
        print_warning(f"Repository locked or key unavailable: {e}")


@key_commands.command("recovery")
@click.pass_context
def recovery_cmd(ctx: click.Context) -> None:
    """Show the recovery key (RMK) for backup purposes."""
    repo = ctx.obj["repo"].resolve()
    keymanager = KeyManager(repo)

    identity = keymanager.get_repository_identity()
    if identity is None:
        print_error("Repository not initialized")
        return

    try:
        rmk = keymanager.get_rmk()
        print_warning("Store this recovery key securely!")
        print_info(f"Recovery key (RMK): {rmk.hex()}")
        print_warning("This key can unlock the repository on any device")
        print_warning("Anyone with this key can access all files in this repository")
    except Exception as e:
        print_error(f"Failed to retrieve RMK: {e}")
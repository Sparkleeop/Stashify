"""CLI commands for provider management."""


import click

from stash.cli.output import confirm, print_error, print_info, print_success
from stash.core.metadata import MetadataStore
from stash.core.storage import ProviderConfig
from stash.providers import ProviderRegistry


@click.command()
@click.argument("name")
@click.option("--type", "provider_type", type=click.Choice(["discord", "telegram"]), help="Provider type")
@click.option("--token", prompt=True, hide_input=True, help="Bot token")
@click.option("--channel-id", help="Discord channel ID for storage")
@click.option("--chat-id", help="Telegram chat ID for storage")
@click.option("--is-bot/--is-user", default=True, help="Discord: token type (default: bot)")
@click.option("--max-concurrent", default=3, help="Max concurrent uploads")
@click.pass_context
def provider_add_cmd(
    ctx: click.Context,
    name: str,
    provider_type: str | None,
    token: str,
    channel_id: str | None,
    chat_id: str | None,
    is_bot: bool,
    max_concurrent: int,
) -> None:
    """Add a storage provider."""
    repo_path = ctx.obj["repo"]
    store = MetadataStore(repo_path)

    if name in store.list_providers():
        print_error(f"Provider '{name}' already exists")
        return

    if provider_type is None:
        provider_type = name.lower()

    if provider_type not in ProviderRegistry.list_providers():
        print_error(f"Unknown provider type: {provider_type}")
        print_info(f"Available types: {', '.join(ProviderRegistry.list_providers())}")
        return

    credentials: dict[str, str] = {"token": token}
    if provider_type == "discord":
        if not channel_id:
            channel_id = click.prompt("Discord channel ID", type=str)
        credentials["channel_id"] = channel_id
        credentials["is_bot"] = str(is_bot).lower()
    elif provider_type == "telegram":
        if not chat_id:
            chat_id = click.prompt("Telegram chat ID", type=str)
        credentials["chat_id"] = chat_id

    config = ProviderConfig(
        name=name,
        type=provider_type,
        credentials=credentials,
        settings={
            "max_concurrent": str(max_concurrent),
        },
    )

    store.set_provider_config(name, config)
    print_success(f"Added provider '{name}' ({provider_type})")


@click.command(name="list")
@click.pass_context
def provider_list_cmd(ctx: click.Context) -> None:
    """List configured providers."""
    repo_path = ctx.obj["repo"]
    store = MetadataStore(repo_path)

    providers = store.list_providers()
    if not providers:
        print_info("No providers configured")
        print_info("Add one with: stash provider add --type discord <name>")
        return

    from stash.cli.output import print_table
    rows = []
    for name in providers:
        config = store.get_provider_config(name)
        ptype = config.type if config else "unknown"
        if ptype == "discord":
            channel = config.credentials.get("channel_id", "unknown") if config else "unknown"
        elif ptype == "telegram":
            channel = config.credentials.get("chat_id", "unknown") if config else "unknown"
        else:
            channel = "unknown"
        rows.append([name, ptype, channel])
    print_table("Configured Providers", ["Name", "Type", "Channel/Chat ID"], rows)


@click.command()
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Force removal")
@click.pass_context
def provider_remove_cmd(ctx: click.Context, name: str, force: bool) -> None:
    """Remove a storage provider."""
    repo_path = ctx.obj["repo"]
    store = MetadataStore(repo_path)

    if name not in store.list_providers():
        print_error(f"Provider '{name}' not found")
        return

    if not force and not confirm(f"Remove provider '{name}'?"):
        print_info("Cancelled")
        return

    store.remove_provider_config(name)
    print_success(f"Removed provider '{name}'")


provider_commands = click.Group("provider", commands={
    "add": provider_add_cmd,
    "list": provider_list_cmd,
    "remove": provider_remove_cmd,
})
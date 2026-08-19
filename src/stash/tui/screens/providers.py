"""Providers Screen."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Select, Static

if TYPE_CHECKING:
    from stash.core.metadata import MetadataStore
    from stash.providers import ProviderRegistry


class ProviderCard(Static):
    """A provider card widget."""

    DEFAULT_CSS = """
    ProviderCard {
        background: #333f58;
        border: solid #4a7a96;
        margin: 1 0;
        padding: 1;
        height: auto;
    }

    ProviderCard.connected {
        border: solid #4a7a96;
    }

    ProviderCard.disconnected {
        border: solid #ee8695;
    }

    .provider-header {
        layout: horizontal;
        height: 3;
        margin-bottom: 1;
    }

    .provider-name {
        color: #fbbbad;
        text-style: bold;
        width: 30;
        content-align: left middle;
    }

    .provider-status {
        width: 20;
        content-align: center middle;
    }

    .provider-status.connected {
        color: #4a7a96;
    }

    .provider-status.disconnected {
        color: #ee8695;
    }

    .provider-type {
        color: #888888;
        width: 1fr;
        content-align: left middle;
    }

    .provider-details {
        color: #888888;
        margin: 1 0;
    }

    .provider-actions {
        height: 3;
        margin-top: 1;
        layout: horizontal;
    }

    .provider-button {
        width: 1fr;
        margin: 0 1;
        background: #292831;
        color: #e8e8e8;
        border: solid #4a7a96;
    }

    .provider-button:hover {
        background: #333f58;
        border: solid #ee8695;
    }
    """

    def __init__(self, name: str, config, connected: bool = True) -> None:
        super().__init__(classes=f"provider-card {'connected' if connected else 'disconnected'}")
        self.name = name
        self.config = config
        self.connected = connected
        self.border_title = name

    def compose(self) -> ComposeResult:
        with Horizontal(classes="provider-header"):
            yield Static(self.name, classes="provider-name")
            yield Static(
                "● Connected" if self.connected else "○ Disconnected",
                classes=f"provider-status {'connected' if self.connected else 'disconnected'}"
            )
            yield Static(self.config.type.upper(), classes="provider-type")

        yield Static(f"Channel: {self.config.credentials.get('channel_id', 'unknown')}", classes="provider-details")
        yield Static(f"Type: {self.config.type} | Max concurrent: {self.config.settings.get('max_concurrent', '3')}", classes="provider-details")

        with Horizontal(classes="provider-actions"):
            yield Button("Test", variant="default", id=f"test-{self.name}")
            yield Button("Reconfigure", variant="default", id=f"reconfig-{self.name}")
            yield Button("Remove", variant="error", id=f"remove-{self.name}")


class ProvidersScreen(Screen[None]):
    """Provider management screen."""

    DEFAULT_CSS = """
    ProvidersScreen {
        background: #292831;
        padding: 2;
    }

    .screen-title {
        color: #fbbbad;
        text-style: bold;
        margin-bottom: 2;
        border-bottom: solid #4a7a96;
        padding-bottom: 1;
    }

    .provider-list {
        width: 100%;
        margin-bottom: 2;
    }

    .add-provider-form {
        background: #333f58;
        border: solid #4a7a96;
        padding: 2;
        margin-top: 2;
    }

    .form-row {
        height: 3;
        layout: horizontal;
        margin: 1 0;
    }

    .form-label {
        color: #e8e8e8;
        width: 20;
        content-align: right middle;
        padding-right: 2;
    }

    .form-input {
        width: 1fr;
        background: #292831;
        color: #e8e8e8;
        border: solid #4a7a96;
    }

    .form-input:focus {
        border: solid #ee8695;
    }

    .form-select {
        width: 1fr;
        background: #292831;
        color: #e8e8e8;
        border: solid #4a7a96;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._metadata_store: MetadataStore | None = None
        self._provider_registry: ProviderRegistry | None = None

    def compose(self) -> ComposeResult:
        yield Static("PROVIDERS", classes="screen-title")
        yield Static("No providers configured. Add one below.", id="no-providers", classes="provider-list")
        with Vertical(classes="add-provider-form"):
            yield Static("Add Provider", classes="help-section-title")
            with Horizontal(classes="form-row"):
                yield Static("Type:", classes="form-label")
                yield Select([
                    ("Discord", "discord"),
                    ("Telegram", "telegram"),
                    ("S3", "s3"),
                ], id="provider-type-select")
            with Horizontal(classes="form-row"):
                yield Static("Name:", classes="form-label")
                yield Input(placeholder="provider name", id="provider-name-input")
            with Horizontal(classes="form-row"):
                yield Static("Token:", classes="form-label")
                yield Input(placeholder="bot/user token", password=True, id="provider-token-input")
            with Horizontal(classes="form-row"):
                yield Static("Channel ID:", classes="form-label")
                yield Input(placeholder="channel id", id="provider-channel-input")
            with Horizontal(classes="form-row"):
                yield Static("Is Bot:", classes="form-label")
                yield Select([("Yes", "true"), ("No", "false")], value="true", id="provider-is-bot-select")
            yield Button("Add Provider", variant="primary", id="add-provider-btn")

    def on_mount(self) -> None:
        """Initialize the screen."""
        self._refresh_providers()

    def _refresh_providers(self) -> None:
        """Refresh provider list."""
        try:
            no_providers = self.query_one("#no-providers", Static)
        except Exception:
            return

        if not self._metadata_store:
            no_providers.display = True
            return

        providers = self._metadata_store.list_providers()
        if not providers:
            no_providers.display = True
            return

        no_providers.display = False

        # Remove existing provider cards
        for child in list(self.children):
            if isinstance(child, ProviderCard):
                child.remove()

        for name in providers:
            config = self._metadata_store.get_provider_config(name)
            if not config:
                continue

            connected = True  # Could check actual connection
            card = ProviderCard(name, config, connected)
            self.mount(card, before="#no-providers")

    @on(Button.Pressed, "#add-provider-btn")
    def on_add_provider(self, event: Button.Pressed) -> None:
        """Add a new provider."""
        try:
            name = self.query_one("#provider-name-input", Input).value
            ptype = self.query_one("#provider-type-select", Select).value
            token = self.query_one("#provider-token-input", Input).value
            channel = self.query_one("#provider-channel-input", Input).value
            is_bot = self.query_one("#provider-is-bot-select", Select).value
        except Exception:
            self.notify("Please fill all fields", severity="error")
            return

        if not all([name, ptype, token, channel]):
            self.notify("Please fill all fields", severity="error")
            return

        if not self._metadata_store:
            self.notify("No repository initialized", severity="error")
            return

        if name in self._metadata_store.list_providers():
            self.notify(f"Provider '{name}' already exists", severity="error")
            return

        from stash.core.storage import ProviderConfig
        config = ProviderConfig(
            name=name,
            type=ptype,
            credentials={
                "token": token,
                "channel_id": channel,
                "is_bot": is_bot,
            },
            settings={
                "max_concurrent": "3",
            },
        )

        self._metadata_store.set_provider_config(name, config)
        self.notify(f"Added provider '{name}'", severity="information")

        # Clear form
        self.query_one("#provider-name-input", Input).value = ""
        self.query_one("#provider-token-input", Input).value = ""
        self.query_one("#provider-channel-input", Input).value = ""

        self._refresh_providers()

    @on(Button.Pressed)
    def on_provider_action(self, event: Button.Pressed) -> None:
        """Handle provider action buttons."""
        if not event.button.id:
            return

        if event.button.id.startswith("test-"):
            name = event.button.id[5:]
            self.notify(f"Testing connection to {name}...", severity="information")
        elif event.button.id.startswith("reconfig-"):
            name = event.button.id[9:]
            self.notify(f"Reconfigure {name} - not implemented yet", severity="warning")
        elif event.button.id.startswith("remove-"):
            name = event.button.id[7:]
            self._remove_provider(name)

    def _remove_provider(self, name: str) -> None:
        """Remove a provider."""
        if self._metadata_store:
            self._metadata_store.remove_provider_config(name)
            self.notify(f"Removed provider '{name}'", severity="information")
            self._refresh_providers()

    def on_screen_resume(self) -> None:
        """Refresh when screen resumes."""
        self._refresh_providers()
"""Home Screen - Welcome/landing page."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Middle, Vertical
from textual.screen import Screen
from textual.widgets import Button, Static


class HomeScreen(Screen[None]):
    """Initial home/welcome screen."""

    DEFAULT_CSS = """
    HomeScreen {
        background: #292831;
        align: center middle;
    }

    .home-container {
        width: 70;
        max-width: 90%;
        padding: 2;
    }

    .home-title {
        color: #fbbbad;
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }

    .home-subtitle {
        color: #4a7a96;
        text-align: center;
        margin-bottom: 3;
    }

    .home-description {
        color: #888888;
        text-align: center;
        margin-bottom: 3;
    }

    .home-buttons {
        layout: vertical;
        margin-top: 2;
    }

    .home-button {
        width: 100%;
        margin: 1 0;
        height: 4;
    }

    .home-button-primary {
        background: #ee8695;
        color: #292831;
        border: solid #ee8695;
    }

    .home-button-primary:hover {
        background: #fbbbad;
    }

    .home-button-secondary {
        background: #292831;
        color: #e8e8e8;
        border: solid #4a7a96;
    }

    .home-button-secondary:hover {
        background: #333f58;
        border: solid #ee8695;
    }

    .provider-status {
        color: #888888;
        text-align: center;
        margin-top: 2;
        padding-top: 1;
        border-top: solid #333f58;
    }

    .shortcuts-hint {
        color: #4a7a96;
        text-align: center;
        margin-top: 1;
        text-style: italic;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._metadata_store = None
        self._provider_registry = None

    def compose(self) -> ComposeResult:
        with Center():
            with Middle():
                with Vertical(classes="home-container"):
                    yield Static("STASH", classes="home-title")
                    yield Static("Encrypted Multi-Provider Storage", classes="home-subtitle")
                    yield Static(
                        "Your files. Your keys. Your choice of storage.\n\n"
                        "Stash encrypts files locally and distributes encrypted chunks\n"
                        "across Telegram, Discord, and other storage providers.",
                        classes="home-description"
                    )

                    with Vertical(classes="home-buttons"):
                        yield Button("Launch Dashboard", id="launch-btn", classes="home-button-primary")
                        yield Button("Providers", id="providers-btn", classes="home-button-secondary")
                        yield Button("Settings", id="settings-btn", classes="home-button-secondary")
                        yield Button("Help", id="help-btn", classes="home-button-secondary")

                    yield Static("", classes="provider-status", id="provider-status")
                    yield Static("Press ? for keyboard shortcuts", classes="shortcuts-hint")

    def on_mount(self) -> None:
        """Initialize the home screen."""
        self._update_provider_status()

    def _update_provider_status(self) -> None:
        """Update provider status display."""
        try:
            status_widget = self.query_one("#provider-status", Static)
        except Exception:
            return

        if self._metadata_store:
            providers = self._metadata_store.list_providers()
            if providers:
                provider_str = ", ".join(providers)
                status_widget.update(f"Configured: {provider_str}")
            else:
                status_widget.update("No providers configured. Press 'P' to add one.")
        else:
            status_widget.update("No repository initialized.")

    @on(Button.Pressed, "#launch-btn")
    def on_launch(self, event: Button.Pressed) -> None:
        """Launch the main dashboard."""
        self.app.switch_screen("dashboard")

    @on(Button.Pressed, "#providers-btn")
    def on_providers(self, event: Button.Pressed) -> None:
        """Open providers screen."""
        self.app.push_screen("providers")

    @on(Button.Pressed, "#settings-btn")
    def on_settings(self, event: Button.Pressed) -> None:
        """Open settings screen."""
        self.app.push_screen("settings")

    @on(Button.Pressed, "#help-btn")
    def on_help(self, event: Button.Pressed) -> None:
        """Open help overlay."""
        try:
            app = self.app
            help_overlay = app.query_one("#help-overlay")
            help_overlay.show()
        except Exception:
            pass

    def on_screen_resume(self) -> None:
        """Update when returning to home."""
        self._update_provider_status()
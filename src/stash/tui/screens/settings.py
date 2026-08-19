"""Settings Screen."""

from __future__ import annotations
from pathlib import Path

from textual import on
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Select, Static, Switch


class SettingsScreen(Screen):
    """Settings configuration screen."""

    DEFAULT_CSS = """
    SettingsScreen {
        background: #292831;
        padding: 2;
        overflow-y: auto;
    }

    .screen-title {
        color: #fbbbad;
        text-style: bold;
        margin-bottom: 2;
        border-bottom: solid #4a7a96;
        padding-bottom: 1;
    }

    .settings-section {
        background: #333f58;
        border: solid #4a7a96;
        padding: 1;
        margin: 1 0;
    }

    .settings-section-title {
        color: #fbbbad;
        text-style: bold;
        margin-bottom: 1;
        border-bottom: solid #4a7a96;
        padding-bottom: 1;
    }

    .setting-row {
        height: 3;
        layout: horizontal;
        padding: 0 1;
        margin: 1 0;
    }

    .setting-label {
        color: #e8e8e8;
        width: 30;
        content-align: right middle;
        padding-right: 2;
    }

    .setting-input {
        width: 1fr;
        background: #292831;
        color: #e8e8e8;
        border: solid #4a7a96;
    }

    .setting-input:focus {
        border: solid #ee8695;
    }

    .setting-select {
        width: 1fr;
        background: #292831;
        color: #e8e8e8;
        border: solid #4a7a96;
    }

    .setting-switch {
        width: auto;
        margin-top: 0;
    }

    .save-button {
        margin-top: 2;
        width: 20;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("SETTINGS", classes="screen-title")

        # General Section
        with Vertical(classes="settings-section"):
            yield Static("General", classes="settings-section-title")

            with Horizontal(classes="setting-row"):
                yield Static("Default Download Directory:", classes="setting-label")
                yield Input(placeholder=str(Path.home() / "Downloads"), id="download-dir-input", classes="setting-input")

            with Horizontal(classes="setting-row"):
                yield Static("Show Hidden Files:", classes="setting-label")
                yield Switch(value=False, id="hidden-files-switch", classes="setting-switch")

        # Storage Section
        with Vertical(classes="settings-section"):
            yield Static("Storage", classes="settings-section-title")

            with Horizontal(classes="setting-row"):
                yield Static("Default Provider:", classes="setting-label")
                yield Select([("Auto", "auto"), ("Discord", "discord"), ("Telegram", "telegram")], value="auto", id="default-provider-select", classes="setting-select")

            with Horizontal(classes="setting-row"):
                yield Static("Default Chunk Size:", classes="setting-label")
                yield Select([
                    ("1 MB", "1048576"),
                    ("5 MB", "5242880"),
                    ("10 MB", "10485760"),
                    ("25 MB", "26214400"),
                    ("50 MB", "52428800"),
                ], value="26214400", id="chunk-size-select", classes="setting-select")

            with Horizontal(classes="setting-row"):
                yield Static("Replication Factor:", classes="setting-label")
                yield Select([("None (1x)", "1"), ("2x", "2"), ("3x", "3")], value="1", id="replication-select", classes="setting-select")

        # Transfers Section
        with Vertical(classes="settings-section"):
            yield Static("Transfers", classes="settings-section-title")

            with Horizontal(classes="setting-row"):
                yield Static("Upload Concurrency:", classes="setting-label")
                yield Select([("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"), ("5", "5")], value="3", id="upload-concurrency-select", classes="setting-select")

            with Horizontal(classes="setting-row"):
                yield Static("Download Concurrency:", classes="setting-label")
                yield Select([("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"), ("5", "5")], value="3", id="download-concurrency-select", classes="setting-select")

            with Horizontal(classes="setting-row"):
                yield Static("Retry Count:", classes="setting-label")
                yield Select([("0", "0"), ("1", "1"), ("2", "2"), ("3", "3"), ("5", "5")], value="3", id="retry-count-select", classes="setting-select")

            with Horizontal(classes="setting-row"):
                yield Static("Retry Backoff (seconds):", classes="setting-label")
                yield Input(value="1", id="retry-backoff-input", classes="setting-input")

        # Security Section
        with Vertical(classes="settings-section"):
            yield Static("Security", classes="settings-section-title")

            with Horizontal(classes="setting-row"):
                yield Static("Auto-lock on Inactivity:", classes="setting-label")
                yield Switch(value=False, id="auto-lock-switch", classes="setting-switch")

            with Horizontal(classes="setting-row"):
                yield Static("Lock Timeout (minutes):", classes="setting-label")
                yield Input(value="15", id="lock-timeout-input", classes="setting-input")

        # UI Section
        with Vertical(classes="settings-section"):
            yield Static("UI", classes="settings-section-title")

            with Horizontal(classes="setting-row"):
                yield Static("Compact Mode:", classes="setting-label")
                yield Switch(value=False, id="compact-mode-switch", classes="setting-switch")

            with Horizontal(classes="setting-row"):
                yield Static("Animations:", classes="setting-label")
                yield Switch(value=True, id="animations-switch", classes="setting-switch")

            with Horizontal(classes="setting-row"):
                yield Static("Progress Display:", classes="setting-label")
                yield Select([("Bar", "bar"), ("Percentage", "pct"), ("Both", "both")], value="both", id="progress-display-select", classes="setting-select")

        # Save Button
        yield Button("Save Settings", variant="primary", id="save-settings-btn", classes="save-button")

    @on(Button.Pressed, "#save-settings-btn")
    def on_save_settings(self, event: Button.Pressed) -> None:
        """Save settings."""
        self.notify("Settings saved (not persisted yet)", severity="information")
"""Status Bar Widget."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Horizontal
from textual.widgets import Static

if TYPE_CHECKING:
    pass


class StatusBar(Horizontal):
    """Bottom status bar."""

    DEFAULT_CSS = """
    StatusBar {
        height: 2;
        background: #333f58;
        color: #e8e8e8;
        padding: 0 1;
        layout: horizontal;
    }

    StatusBar > Static {
        margin-right: 2;
    }

    .status-provider {
        color: #4a7a96;
    }

    .status-provider.connected {
        color: #4a7a96;
    }

    .status-provider.disconnected {
        color: #ee8695;
    }

    .status-transfers {
        color: #fbbbad;
    }

    .status-speed {
        color: #4a7a96;
    }

    .status-stored {
        color: #888888;
    }

    .status-help {
        color: #4a7a96;
        text-style: italic;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._providers: list[str] = []
        self._transfers_active = 0
        self._transfer_speed = 0
        self._total_stored = 0

    def compose(self) -> ComposeResult:
        yield Static("", classes="status-provider", id="status-providers")
        yield Static("", classes="status-transfers", id="status-transfers")
        yield Static("", classes="status-speed", id="status-speed")
        yield Static("", classes="status-stored", id="status-stored")
        yield Static("[?] Help", classes="status-help", id="status-help")

    def update_providers(self, providers: list[str]) -> None:
        """Update provider list."""
        self._providers = providers
        self._refresh()

    def update_transfers(self, active: int, speed: float) -> None:
        """Update transfer info."""
        self._transfers_active = active
        self._transfer_speed = speed
        self._refresh()

    def update_stored(self, total: int) -> None:
        """Update stored size."""
        self._total_stored = total
        self._refresh()

    def _refresh(self) -> None:
        """Refresh all status elements."""
        try:
            providers_widget = self.query_one("#status-providers", Static)
            transfers_widget = self.query_one("#status-transfers", Static)
            speed_widget = self.query_one("#status-speed", Static)
            stored_widget = self.query_one("#status-stored", Static)
        except Exception:
            return

        if self._providers:
            provider_str = "  ".join([f"{p} ●" for p in self._providers])
            providers_widget.update(f"Providers: {provider_str}")
            providers_widget.classes = "status-provider connected"
        else:
            providers_widget.update("No providers")
            providers_widget.classes = "status-provider disconnected"

        if self._transfers_active > 0:
            transfers_widget.update(f"Transfers: {self._transfers_active}")
        else:
            transfers_widget.update("No transfers")

        if self._transfer_speed > 0:
            speed_widget.update(f"{self._format_speed(self._transfer_speed)}")
        else:
            speed_widget.update("0 B/s")

        if self._total_stored > 0:
            stored_widget.update(f"Stored: {self._format_size(self._total_stored)}")
        else:
            stored_widget.update("Empty")

    def _format_size(self, size: int) -> str:
        """Format file size."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    def _format_speed(self, speed: float) -> str:
        """Format transfer speed."""
        if speed == 0:
            return "0 B/s"
        return self._format_size(int(speed)) + "/s"
"""Stash TUI Application."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import TYPE_CHECKING

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.css.query import NoMatches
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from stash.tui.widgets.local_explorer import LocalFileExplorer
from stash.tui.widgets.remote_explorer import RemoteFileExplorer
from stash.tui.widgets.transfer_list import TransferList
from stash.tui.widgets.status_bar import StatusBar
from stash.tui.widgets.command_palette import CommandPalette
from stash.tui.widgets.help_overlay import HelpOverlay
from stash.tui.screens.home import HomeScreen
from stash.tui.screens.providers import ProvidersScreen
from stash.tui.screens.settings import SettingsScreen
from stash.tui.screens.transfers import TransfersScreen
from stash.tui.screens.file_info import FileInfoScreen

if TYPE_CHECKING:
    from stash.core.metadata import MetadataStore
    from stash.providers import ProviderRegistry
    from textual.app import ComposeResult


class DashboardScreen(Screen):
    """Main dashboard with dual explorers."""

    DEFAULT_CSS = """
    DashboardScreen {
        background: #292831;
    }

    #main-container {
        layout: horizontal;
        height: 1fr;
    }

    #left-pane {
        width: 50%;
        border-right: solid #333f58;
        background: #292831;
    }

    #right-pane {
        width: 50%;
        background: #292831;
    }

    .pane-header {
        height: 3;
        background: #333f58;
        color: #fbbbad;
        text-style: bold;
        padding: 0 1;
        border-bottom: solid #4a7a96;
    }

    #local-explorer {
        height: 1fr;
        background: #292831;
        border: none;
    }

    #remote-explorer {
        height: 1fr;
        background: #292831;
        border: none;
    }

    #transfers-panel {
        height: 12;
        background: #333f58;
        border-top: solid #4a7a96;
        padding: 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._focus_left = True

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="main-container"):
            with Vertical(id="left-pane"):
                yield Static("LOCAL FILES", classes="pane-header")
                yield LocalFileExplorer(id="local-explorer", path=Path.home())
            with Vertical(id="right-pane"):
                yield Static("REMOTE STORAGE", classes="pane-header")
                yield RemoteFileExplorer(id="remote-explorer")
            yield TransferList(id="transfers-panel")
        yield StatusBar(id="status-bar")
        yield CommandPalette(id="command-palette")
        yield HelpOverlay(id="help-overlay")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the dashboard."""
        app = self.app
        if hasattr(app, '_metadata_store') and app._metadata_store:
            self._initialize_explorers(app)

    def _initialize_explorers(self, app) -> None:
        """Initialize explorers with core services."""
        try:
            local_explorer = self.query_one("#local-explorer", LocalFileExplorer)
            remote_explorer = self.query_one("#remote-explorer", RemoteFileExplorer)

            local_explorer.metadata_store = app._metadata_store
            remote_explorer.metadata_store = app._metadata_store
            remote_explorer.provider_registry = app._provider_registry

            self.call_later(self._refresh_explorers)
        except Exception as e:
            self.notify(f"Failed to initialize explorers: {e}", severity="error")

    async def _refresh_explorers(self) -> None:
        """Refresh both file explorers."""
        try:
            local_explorer = self.query_one("#local-explorer", LocalFileExplorer)
            remote_explorer = self.query_one("#remote-explorer", RemoteFileExplorer)

            await local_explorer.refresh_directory()
            await remote_explorer.refresh_directory()
        except Exception as e:
            self.notify(f"Failed to refresh: {e}", severity="error")

    def action_switch_pane(self) -> None:
        """Switch focus between left and right panes."""
        self._focus_left = not self._focus_left
        if self._focus_left:
            self.query_one("#local-explorer", LocalFileExplorer).focus()
        else:
            self.query_one("#remote-explorer", RemoteFileExplorer).focus()

    def action_upload(self) -> None:
        """Upload selected local files."""
        local_explorer = self.query_one("#local-explorer", LocalFileExplorer)
        selected = local_explorer.get_selected_files()
        if selected:
            self._start_upload(selected)

    def action_download(self) -> None:
        """Download selected remote files."""
        remote_explorer = self.query_one("#remote-explorer", RemoteFileExplorer)
        selected = remote_explorer.get_selected_files()
        if selected:
            self._start_download(selected)

    def action_refresh(self) -> None:
        """Refresh current explorer."""
        self.call_later(self._refresh_explorers)

    def action_toggle_select(self) -> None:
        """Toggle selection on focused explorer."""
        if self._focus_left:
            explorer = self.query_one("#local-explorer", LocalFileExplorer)
        else:
            explorer = self.query_one("#remote-explorer", RemoteFileExplorer)
        explorer.toggle_selection()

    def action_search(self) -> None:
        """Open search overlay."""
        try:
            palette = self.query_one("#command-palette", CommandPalette)
            palette.show_search()
        except Exception:
            pass

    def action_command_palette(self) -> None:
        """Open command palette."""
        try:
            palette = self.query_one("#command-palette", CommandPalette)
            palette.show()
        except Exception:
            pass

    def action_providers(self) -> None:
        """Open providers screen."""
        self.app.push_screen("providers")

    def action_settings(self) -> None:
        """Open settings screen."""
        self.app.push_screen("settings")

    def action_transfers(self) -> None:
        """Open transfers screen."""
        self.app.push_screen("transfers")

    def action_help(self) -> None:
        """Show help overlay."""
        try:
            help_overlay = self.query_one("#help-overlay", HelpOverlay)
            help_overlay.show()
        except Exception:
            pass

    def action_close_overlays(self) -> None:
        """Close any open overlays."""
        try:
            palette = self.query_one("#command-palette", CommandPalette)
            if palette.visible:
                palette.hide()
        except NoMatches:
            pass
        try:
            help_overlay = self.query_one("#help-overlay", HelpOverlay)
            if help_overlay.visible:
                help_overlay.hide()
        except NoMatches:
            pass

    def _start_upload(self, files: list[Path]) -> None:
        """Start upload for selected files."""
        self.notify(f"Uploading {len(files)} file(s)...", severity="information")
        try:
            transfer_list = self.query_one("#transfers-panel", TransferList)
            for file_path in files:
                transfer_list.add_transfer(
                    filename=file_path.name,
                    operation="upload",
                    total_size=file_path.stat().st_size,
                )
        except Exception:
            pass

    def _start_download(self, files: list[dict]) -> None:
        """Start download for selected files."""
        self.notify(f"Downloading {len(files)} file(s)...", severity="information")
        try:
            transfer_list = self.query_one("#transfers-panel", TransferList)
            for file_data in files:
                transfer_list.add_transfer(
                    filename=file_data.get("name", "unknown"),
                    operation="download",
                    total_size=file_data.get("size", 0),
                )
        except Exception:
            pass

    @work(exclusive=True, thread=True)
    def _simulate_upload(self, transfer_id: str) -> None:
        """Simulate upload progress for demo."""
        import time
        try:
            transfer_list = self.query_one("#transfers-panel", TransferList)
            for i in range(101):
                time.sleep(0.05)
                self.app.call_from_thread(transfer_list.update_progress, transfer_id, i)
            self.app.call_from_thread(transfer_list.complete_transfer, transfer_id, True)
        except Exception:
            pass

    @work(exclusive=True, thread=True)
    def _simulate_download(self, transfer_id: str) -> None:
        """Simulate download progress for demo."""
        import time
        try:
            transfer_list = self.query_one("#transfers-panel", TransferList)
            for i in range(101):
                time.sleep(0.05)
                self.app.call_from_thread(transfer_list.update_progress, transfer_id, i)
            self.app.call_from_thread(transfer_list.complete_transfer, transfer_id, True)
        except Exception:
            pass

    def on_local_file_explorer_selection_changed(self, event: LocalFileExplorer.SelectionChanged) -> None:
        """Handle local file selection change."""
        pass

    def on_remote_file_explorer_selection_changed(self, event: RemoteFileExplorer.SelectionChanged) -> None:
        """Handle remote file selection change."""
        pass

    def on_transfer_list_transfer_added(self, event: TransferList.TransferAdded) -> None:
        """Handle new transfer added."""
        if event.operation == "upload":
            self._simulate_upload(event.transfer_id)
        elif event.operation == "download":
            self._simulate_download(event.transfer_id)


class TUIMessages:
    """Internal TUI messages."""

    class RefreshExplorers(Message):
        """Request to refresh both explorers."""

    class UploadSelected(Message):
        """Request to upload selected local files."""

    class DownloadSelected(Message):
        """Request to download selected remote files."""

    class SwitchPane(Message):
        """Switch focus between left/right panes."""

    class ShowFileInfo(Message):
        """Show file info panel."""
        def __init__(self, file_data: dict, is_local: bool) -> None:
            self.file_data = file_data
            self.is_local = is_local
            super().__init__()

    class ProviderStatusChanged(Message):
        """Provider connection status changed."""
        def __init__(self, provider_name: str, connected: bool) -> None:
            self.provider_name = provider_name
            self.connected = connected
            super().__init__()


class StashApp(App):
    """Main Stash TUI Application."""

    TITLE = "Stash"
    SUB_TITLE = "Encrypted Multi-Provider Storage"
    CSS_PATH = "styles/app.tcss"
    BINDINGS = [
        Binding("tab", "switch_pane", "Switch Pane", show=True),
        Binding("u", "upload", "Upload", show=True),
        Binding("d", "download", "Download", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("space", "toggle_select", "Select", show=True),
        Binding("/", "search", "Search", show=True),
        Binding(":", "command_palette", "Commands", show=True),
        Binding("p", "providers", "Providers", show=True),
        Binding("s", "settings", "Settings", show=True),
        Binding("t", "transfers", "Transfers", show=True),
        Binding("?", "help", "Help", show=True),
        Binding("q", "quit", "Quit", show=True),
        Binding("escape", "close_overlays", "Close", show=False),
    ]

    SCREENS = {
        "home": HomeScreen,
        "dashboard": DashboardScreen,
        "providers": ProvidersScreen,
        "settings": SettingsScreen,
        "transfers": TransfersScreen,
    }

    def __init__(self) -> None:
        super().__init__()
        self._metadata_store: MetadataStore | None = None
        self._provider_registry: ProviderRegistry | None = None
        self._current_local_path = Path.home()
        self._current_remote_path = ""
        self._selected_local_files: set[str] = set()
        self._selected_remote_files: set[str] = set()

    def compose(self) -> ComposeResult:
        # The app itself doesn't compose widgets - screens do
        yield CommandPalette(id="command-palette")
        yield HelpOverlay(id="help-overlay")

    def on_mount(self) -> None:
        """Initialize the application."""
        self._initialize_core()
        # Start with home screen
        self.push_screen("home")

    def _initialize_core(self) -> None:
        """Initialize core Stash services."""
        try:
            from stash.core.metadata import MetadataStore
            from stash.providers import ProviderRegistry

            repo_path = Path.cwd()
            self._metadata_store = MetadataStore(repo_path)
            self._provider_registry = ProviderRegistry
        except Exception as e:
            self.notify(f"Failed to initialize core: {e}", severity="error")

    def on_screen_change(self, event) -> None:
        """Handle screen changes."""
        if hasattr(event, 'screen') and getattr(event.screen, 'name', '') == "dashboard":
            # Initialize dashboard when switched to
            dashboard = self.get_screen("dashboard")
            if dashboard and hasattr(self, '_metadata_store') and self._metadata_store:
                dashboard._initialize_explorers(self)

    def action_switch_pane(self) -> None:
        """Switch focus between left and right panes."""
        # Forward to current screen if it's dashboard
        screen = self.screen
        if hasattr(screen, 'action_switch_pane'):
            screen.action_switch_pane()

    def action_upload(self) -> None:
        """Upload selected local files."""
        screen = self.screen
        if hasattr(screen, 'action_upload'):
            screen.action_upload()

    def action_download(self) -> None:
        """Download selected remote files."""
        screen = self.screen
        if hasattr(screen, 'action_download'):
            screen.action_download()

    def action_refresh(self) -> None:
        """Refresh current explorer."""
        screen = self.screen
        if hasattr(screen, 'action_refresh'):
            screen.action_refresh()

    def action_toggle_select(self) -> None:
        """Toggle selection on focused explorer."""
        screen = self.screen
        if hasattr(screen, 'action_toggle_select'):
            screen.action_toggle_select()

    def action_search(self) -> None:
        """Open search overlay."""
        try:
            palette = self.query_one("#command-palette", CommandPalette)
            palette.show_search()
        except NoMatches:
            pass

    def action_command_palette(self) -> None:
        """Open command palette."""
        try:
            palette = self.query_one("#command-palette", CommandPalette)
            palette.show()
        except NoMatches:
            pass

    def action_providers(self) -> None:
        """Open providers screen."""
        self.push_screen("providers")

    def action_settings(self) -> None:
        """Open settings screen."""
        self.push_screen("settings")

    def action_transfers(self) -> None:
        """Open transfers screen."""
        self.push_screen("transfers")

    def action_help(self) -> None:
        """Show help overlay."""
        try:
            help_overlay = self.query_one("#help-overlay", HelpOverlay)
            help_overlay.show()
        except NoMatches:
            pass

    def action_close_overlays(self) -> None:
        """Close any open overlays."""
        try:
            palette = self.query_one("#command-palette", CommandPalette)
            if palette.visible:
                palette.hide()
        except NoMatches:
            pass
        try:
            help_overlay = self.query_one("#help-overlay", HelpOverlay)
            if help_overlay.visible:
                help_overlay.hide()
        except NoMatches:
            pass

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()
        return None


def run_tui() -> None:
    """Run the TUI application."""
    app = StashApp()
    app.run()


if __name__ == "__main__":
    run_tui()
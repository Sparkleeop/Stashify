"""Command Palette Widget."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual import on
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Input, ListView, ListItem, Static

if TYPE_CHECKING:
    pass


class CommandPalette(Vertical):
    """Command palette for quick actions."""

    DEFAULT_CSS = """
    CommandPalette {
        background: #333f58;
        border: solid #4a7a96;
        padding: 1;
        width: 60%;
        height: auto;
        max-height: 50%;
        display: none;
        layer: overlay;
        offset-x: 20%;
        offset-y: 10%;
    }

    #palette-input {
        background: #292831;
        color: #fbbbad;
        border: solid #4a7a96;
        margin-bottom: 1;
    }

    #palette-input:focus {
        border: solid #ee8695;
    }

    #palette-results {
        background: #292831;
        border: none;
        max-height: 40;
    }

    .palette-item {
        padding: 0 1;
        color: #e8e8e8;
        height: 3;
    }

    .palette-item:hover {
        background: #333f58;
        color: #fbbbad;
    }

    .palette-item.--highlight {
        background: #333f58;
        color: #fbbbad;
    }
    """

    class CommandSelected(Message):
        """Command selected from palette."""
        def __init__(self, command: str) -> None:
            self.command = command
            super().__init__()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._commands = [
            ("Upload files", "upload"),
            ("Download selected", "download"),
            ("Search files", "search"),
            ("Refresh", "refresh"),
            ("Open providers", "providers"),
            ("Open settings", "settings"),
            ("View transfers", "transfers"),
            ("Verify file", "verify"),
            ("Repair file", "repair"),
            ("Quit", "quit"),
        ]
        self._filtered_commands = self._commands
        self._selected_index = 0

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Type command...", id="palette-input")
        yield ListView(id="palette-results")

    def on_mount(self) -> None:
        """Initialize the palette."""
        self._populate_results()

    def show(self) -> None:
        """Show the command palette."""
        self.display = True
        self.query_one("#palette-input", Input).focus()
        self._populate_results()

    def show_search(self) -> None:
        """Show palette in search mode."""
        self.display = True
        self.query_one("#palette-input", Input).focus()
        self._populate_results()

    def hide(self) -> None:
        """Hide the command palette."""
        self.display = False
        self.query_one("#palette-input", Input).value = ""
        self._filtered_commands = self._commands
        self._selected_index = 0

    def _populate_results(self) -> None:
        """Populate the results list."""
        try:
            results = self.query_one("#palette-results", ListView)
        except Exception:
            return

        results.clear()
        for i, (label, cmd) in enumerate(self._filtered_commands):
            item = ListItem(Static(label), classes="palette-item")
            item.id = f"cmd-{cmd}"
            results.append(item)

    @on(Input.Changed, "#palette-input")
    def on_input_changed(self, event: Input.Changed) -> None:
        """Filter commands based on input."""
        query = event.value.lower()
        if query:
            self._filtered_commands = [
                (label, cmd) for label, cmd in self._commands
                if query in label.lower() or query in cmd.lower()
            ]
        else:
            self._filtered_commands = self._commands
        self._populate_results()

    @on(ListView.Selected, "#palette-results")
    def on_selected(self, event: ListView.Selected) -> None:
        """Handle command selection."""
        if event.item and event.item.id:
            cmd = event.item.id.replace("cmd-", "")
            self.post_message(self.CommandSelected(cmd))
            self.hide()

    def on_key(self, event) -> None:
        """Handle key events."""
        if event.key == "escape":
            self.hide()
            event.stop()
        elif event.key == "enter":
            try:
                results = self.query_one("#palette-results", ListView)
                if results.highlighted_child:
                    item = results.highlighted_child
                    if item and item.id:
                        cmd = item.id.replace("cmd-", "")
                        self.post_message(self.CommandSelected(cmd))
                        self.hide()
            except Exception:
                pass
            event.stop()
"""Help Overlay Widget."""

from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import Static


class HelpOverlay(Vertical):
    """Help overlay showing keyboard shortcuts."""

    DEFAULT_CSS = """
    HelpOverlay {
        background: #333f58;
        border: solid #4a7a96;
        padding: 2;
        width: 60%;
        height: auto;
        max-height: 70%;
        display: none;
        layer: overlay;
        offset-x: 20%;
        offset-y: 10%;
        overflow-y: auto;
    }

    .help-section {
        margin: 1 0;
    }

    .help-section-title {
        color: #fbbbad;
        text-style: bold;
        margin-bottom: 1;
    }

    .help-binding {
        color: #e8e8e8;
        layout: horizontal;
        height: 2;
    }

    .help-key {
        color: #4a7a96;
        text-style: bold;
        width: 20;
        content-align: right middle;
        padding-right: 2;
    }

    .help-description {
        color: #e8e8e8;
        width: 1fr;
        content-align: left middle;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._bindings = [
            ("Navigation", [
                ("↑ / ↓", "Navigate"),
                ("Tab", "Switch pane"),
                ("Enter", "Open directory/file"),
                ("Backspace", "Parent directory"),
                ("Space", "Select file"),
                ("Esc", "Close overlay"),
            ]),
            ("Actions", [
                ("U", "Upload selected"),
                ("D", "Download selected"),
                ("X", "Delete selected"),
                ("R", "Refresh"),
                ("V", "Verify file"),
            ]),
            ("Global", [
                ("/", "Search"),
                (":", "Command palette"),
                ("P", "Providers screen"),
                ("S", "Settings"),
                ("T", "Transfers"),
                ("?", "Help"),
                ("Q", "Quit"),
            ]),
        ]

    def compose(self) -> ComposeResult:
        yield Static("KEYBOARD SHORTCUTS", classes="help-section-title")
        for section_name, bindings in self._bindings:
            yield Static(section_name, classes="help-section-title")
            for key, desc in bindings:
                with Static(classes="help-binding"):
                    yield Static(key, classes="help-key")
                    yield Static(desc, classes="help-description")

    def show(self) -> None:
        """Show the help overlay."""
        self.display = True
        self.focus()

    def hide(self) -> None:
        """Hide the help overlay."""
        self.display = False

    def on_key(self, event) -> None:
        """Handle key events."""
        if event.key in ("escape", "?"):
            self.hide()
            event.stop()
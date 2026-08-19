"""Local File Explorer Widget."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from textual import on, work
from textual.containers import Container, Vertical
from textual.message import Message
from textual.widgets import DataTable, DirectoryTree, Input, Static

if TYPE_CHECKING:
    from stash.core.metadata import MetadataStore


class LocalFileExplorer(Vertical):
    """Local filesystem explorer widget."""

    DEFAULT_CSS = """
    LocalFileExplorer {
        height: 1fr;
        border: none;
    }

    #path-bar {
        height: 3;
        background: #333f58;
        border-bottom: solid #4a7a96;
        padding: 0 1;
        layout: horizontal;
    }

    #path-input {
        width: 1fr;
        background: #292831;
        color: #e8e8e8;
        border: solid #4a7a96;
    }

    #path-input:focus {
        border: solid #ee8695;
    }

    #refresh-btn {
        width: 10;
        margin-left: 1;
        background: #292831;
        color: #e8e8e8;
        border: solid #4a7a96;
    }

    #refresh-btn:hover {
        background: #333f58;
        border: solid #ee8695;
    }

    #tree-container {
        height: 1fr;
        background: #292831;
    }

    #file-table {
        height: 1fr;
        background: #292831;
        border: none;
    }

    #empty-state {
        height: 1fr;
        background: #292831;
        content-align: center middle;
        color: #888888;
    }
    """

    class SelectionChanged(Message):
        """Selection changed in the explorer."""
        def __init__(self, selected_paths: set[str]) -> None:
            self.selected_paths = selected_paths
            super().__init__()

    def __init__(self, path: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self._current_path = path
        self._metadata_store: MetadataStore | None = None
        self._selected_files: set[str] = set()
        self._show_hidden = False

    def compose(self) -> ComposeResult:
        with Container(id="path-bar"):
            yield Input(placeholder=str(self._current_path), id="path-input")
            yield Static("🔄", id="refresh-btn")
        yield Static("Loading...", id="empty-state")

    def on_mount(self) -> None:
        """Initialize the explorer."""
        self._load_directory()

    @property
    def metadata_store(self) -> MetadataStore | None:
        return self._metadata_store

    @metadata_store.setter
    def metadata_store(self, value: MetadataStore | None) -> None:
        self._metadata_store = value

    @work(exclusive=True, thread=True)
    def _load_directory(self) -> None:
        """Load directory contents."""
        try:
            files = []
            dirs = []

            for entry in os.scandir(self._current_path):
                if entry.name.startswith(".") and not self._show_hidden:
                    continue
                try:
                    stat = entry.stat()
                    if entry.is_dir():
                        dirs.append({
                            "name": entry.name + "/",
                            "size": "",
                            "type": "DIR",
                            "path": entry.path,
                            "is_dir": True,
                        })
                    else:
                        files.append({
                            "name": entry.name,
                            "size": self._format_size(stat.st_size),
                            "type": self._get_file_type(entry.name),
                            "path": entry.path,
                            "is_dir": False,
                        })
                except (OSError, PermissionError):
                    continue

            dirs.sort(key=lambda x: x["name"].lower())
            files.sort(key=lambda x: x["name"].lower())

            all_items = dirs + files

            self.app.call_from_thread(self._populate_table, all_items)
            self.app.call_from_thread(self._update_path_input)

        except Exception as e:
            self.app.call_from_thread(self._show_error, str(e))

    def _format_size(self, size: int) -> str:
        """Format file size."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    def _get_file_type(self, filename: str) -> str:
        """Get file type from extension."""
        ext = Path(filename).suffix.lower()
        if ext:
            return ext[1:].upper()
        return "FILE"

    def _populate_table(self, items: list[dict]) -> None:
        """Populate the file table."""
        try:
            table = self.query_one("#file-table", DataTable)
        except Exception:
            table = DataTable(id="file-table", cursor_type="row")
            self.mount(table, after="#path-bar")

        table.clear(columns=True)
        table.add_columns("NAME", "SIZE", "TYPE")
        table.zebra_stripes = True

        for item in items:
            row_style = "DirectoryRow" if item["is_dir"] else "FileRow"
            table.add_row(
                item["name"],
                item["size"],
                item["type"],
                key=item["path"],
            )

        self.query_one("#empty-state", Static).display = len(items) == 0

    def _update_path_input(self) -> None:
        """Update path input with current path."""
        try:
            path_input = self.query_one("#path-input", Input)
            path_input.value = str(self._current_path)
            path_input.placeholder = str(self._current_path)
        except Exception:
            pass

    def _show_error(self, error: str) -> None:
        """Show error in the explorer."""
        self.query_one("#empty-state", Static).update(f"Error: {error}")

    async def refresh_directory(self) -> None:
        """Refresh the current directory."""
        self._load_directory()

    def get_selected_files(self) -> list[Path]:
        """Get currently selected files."""
        return [Path(p) for p in self._selected_files]

    def toggle_selection(self) -> None:
        """Toggle selection of current row."""
        try:
            table = self.query_one("#file-table", DataTable)
            if table.cursor_row >= 0:
                row_key = table.get_row_at(table.cursor_row).key
                path = str(row_key)
                if path in self._selected_files:
                    self._selected_files.remove(path)
                else:
                    self._selected_files.add(path)
                self.post_message(self.SelectionChanged(self._selected_files.copy()))
        except Exception:
            pass

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection (Enter key)."""
        try:
            table = self.query_one("#file-table", DataTable)
            row = table.get_row_at(event.cursor_row)
            path = str(row.key)
            p = Path(path)
            if p.is_dir():
                self._current_path = p
                self._load_directory()
            else:
                self._selected_files.add(path)
                self.post_message(self.SelectionChanged(self._selected_files.copy()))
        except Exception:
            pass

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle row highlight."""
        pass

    @on(Input.Submitted, "#path-input")
    def on_path_submitted(self, event: Input.Submitted) -> None:
        """Handle path input submission."""
        new_path = Path(event.value).expanduser().resolve()
        if new_path.exists() and new_path.is_dir():
            self._current_path = new_path
            self._load_directory()
        else:
            self.notify(f"Invalid path: {new_path}", severity="error")

    def on_click(self, event) -> None:
        """Handle click on refresh button."""
        if event.widget and event.widget.id == "refresh-btn":
            self._load_directory()

    def action_go_up(self) -> None:
        """Go to parent directory."""
        parent = self._current_path.parent
        if parent != self._current_path:
            self._current_path = parent
            self._load_directory()

    def action_toggle_hidden(self) -> None:
        """Toggle hidden files visibility."""
        self._show_hidden = not self._show_hidden
        self._load_directory()
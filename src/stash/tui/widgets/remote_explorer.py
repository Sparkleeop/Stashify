"""Remote File Explorer Widget."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual import on, work
from textual.containers import Container, Vertical
from textual.message import Message
from textual.widgets import DataTable, Input, Static

if TYPE_CHECKING:
    from stash.core.metadata import MetadataStore
    from stash.providers import ProviderRegistry


class RemoteFileExplorer(Vertical):
    """Remote Stash storage explorer widget."""

    DEFAULT_CSS = """
    RemoteFileExplorer {
        height: 1fr;
        border: none;
    }

    #remote-path-bar {
        height: 3;
        background: #333f58;
        border-bottom: solid #4a7a96;
        padding: 0 1;
        layout: horizontal;
    }

    #remote-path-input {
        width: 1fr;
        background: #292831;
        color: #e8e8e8;
        border: solid #4a7a96;
    }

    #remote-path-input:focus {
        border: solid #ee8695;
    }

    #remote-refresh-btn {
        width: 10;
        margin-left: 1;
        background: #292831;
        color: #e8e8e8;
        border: solid #4a7a96;
    }

    #remote-refresh-btn:hover {
        background: #333f58;
        border: solid #ee8695;
    }

    #remote-file-table {
        height: 1fr;
        background: #292831;
        border: none;
    }

    #remote-empty-state {
        height: 1fr;
        background: #292831;
        content-align: center middle;
        color: #888888;
    }
    """

    class SelectionChanged(Message):
        """Selection changed in the remote explorer."""
        def __init__(self, selected_paths: set[str]) -> None:
            self.selected_paths = selected_paths
            super().__init__()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._metadata_store: MetadataStore | None = None
        self._provider_registry: ProviderRegistry | None = None
        self._current_remote_path = ""
        self._selected_files: set[str] = set()
        self._files_cache: list[dict] = []

    def compose(self) -> ComposeResult:
        with Container(id="remote-path-bar"):
            yield Input(placeholder="Stash Storage", id="remote-path-input")
            yield Static("🔄", id="remote-refresh-btn")
        yield Static("Loading remote storage...", id="remote-empty-state")

    @property
    def metadata_store(self) -> MetadataStore | None:
        return self._metadata_store

    @metadata_store.setter
    def metadata_store(self, value: MetadataStore | None) -> None:
        self._metadata_store = value

    @property
    def provider_registry(self) -> ProviderRegistry | None:
        return self._provider_registry

    @provider_registry.setter
    def provider_registry(self, value: ProviderRegistry | None) -> None:
        self._provider_registry = value

    @work(exclusive=True, thread=False)
    async def _load_remote_files(self) -> None:
        """Load remote files from Stash metadata."""
        try:
            if not self._metadata_store:
                self._show_empty("No repository initialized")
                return

            file_ids = self._metadata_store.list_files()
            if not file_ids:
                self._show_empty("No files stored yet.\nUpload files from the local explorer.")
                return

            files = []
            for fid in file_ids:
                try:
                    manifest = self._metadata_store.load_manifest(fid)
                    providers = set()
                    for chunk in manifest.chunks:
                        providers.add(chunk.provider)

                    provider_str = "+".join(sorted(providers))[:10]
                    files.append({
                        "name": manifest.original_name,
                        "size": self._format_size(manifest.original_size),
                        "providers": provider_str,
                        "file_id": fid,
                        "chunk_count": manifest.chunk_count,
                        "providers_list": list(providers),
                        "is_dir": False,
                    })
                except Exception:
                    continue

            files.sort(key=lambda x: x["name"].lower())
            self._files_cache = files
            self._populate_table(files)

        except Exception as e:
            self._show_error(str(e))

    def _format_size(self, size: int) -> str:
        """Format file size."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    def _populate_table(self, files: list[dict]) -> None:
        """Populate the remote file table."""
        try:
            table = self.query_one("#remote-file-table", DataTable)
        except Exception:
            table = DataTable(id="remote-file-table", cursor_type="row")
            self.mount(table, after="#remote-path-bar")

        table.clear(columns=True)
        table.add_columns("NAME", "SIZE", "PROVIDERS")
        table.zebra_stripes = True

        for file_data in files:
            table.add_row(
                file_data["name"],
                file_data["size"],
                file_data["providers"],
                key=file_data["file_id"],
            )

        self.query_one("#remote-empty-state", Static).display = len(files) == 0

    def _show_empty(self, message: str) -> None:
        """Show empty state."""
        self.query_one("#remote-empty-state", Static).update(message)
        self.query_one("#remote-empty-state", Static).display = True

    def _show_error(self, error: str) -> None:
        """Show error."""
        self.query_one("#remote-empty-state", Static).update(f"Error: {error}")

    async def refresh_directory(self) -> None:
        """Refresh remote files."""
        await self._load_remote_files()

    def get_selected_files(self) -> list[dict]:
        """Get currently selected files."""
        return [f for f in self._files_cache if f["file_id"] in self._selected_files]

    def toggle_selection(self) -> None:
        """Toggle selection of current row."""
        try:
            table = self.query_one("#remote-file-table", DataTable)
            if table.cursor_row >= 0:
                row_key = table.get_row_at(table.cursor_row).key
                if row_key in self._selected_files:
                    self._selected_files.remove(row_key)
                else:
                    self._selected_files.add(row_key)
                self.post_message(self.SelectionChanged(self._selected_files.copy()))
        except Exception:
            pass

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection."""
        row = event.row
        file_id = str(row.key)
        self._selected_files.add(file_id)
        self.post_message(self.SelectionChanged(self._selected_files.copy()))

    @on(Input.Submitted, "#remote-path-input")
    def on_path_submitted(self, event: Input.Submitted) -> None:
        """Handle path input (not used for remote yet)."""
        pass

    def on_click(self, event) -> None:
        """Handle click on refresh button."""
        if event.widget and event.widget.id == "remote-refresh-btn":
            self.call_later(self._load_remote_files)

    def action_refresh(self) -> None:
        """Refresh remote files."""
        self.call_later(self._load_remote_files)
"""Transfers Screen."""

from __future__ import annotations

from textual import on
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Static


class TransfersScreen(Screen):
    """Transfer/jobs management screen."""

    DEFAULT_CSS = """
    TransfersScreen {
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

    .transfers-table {
        height: 1fr;
        background: #292831;
        border: solid #4a7a96;
    }

    .toolbar {
        height: 3;
        margin: 1 0;
        layout: horizontal;
    }

    .toolbar-button {
        width: auto;
        margin-right: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("TRANSFERS", classes="screen-title")

        with Horizontal(classes="toolbar"):
            yield Button("Pause All", variant="default", id="pause-all-btn", classes="toolbar-button")
            yield Button("Resume All", variant="default", id="resume-all-btn", classes="toolbar-button")
            yield Button("Clear Completed", variant="default", id="clear-completed-btn", classes="toolbar-button")
            yield Button("Retry Failed", variant="default", id="retry-failed-btn", classes="toolbar-button")

        yield Static("No active transfers", id="empty-transfers")
        table = DataTable(id="transfers-table", cursor_type="row")
        table.add_columns("FILENAME", "OP", "PROGRESS", "SPEED", "ETA", "STATUS", "PROVIDER")
        table.zebra_stripes = True
        table.display = False
        yield table

    def on_mount(self) -> None:
        """Initialize the screen."""
        # Could load transfers from app state
        pass

    def add_transfer(self, filename: str, operation: str, total_size: int, provider: str = "") -> str:
        """Add a new transfer to the table."""
        import uuid
        transfer_id = str(uuid.uuid4())[:8]

        try:
            table = self.query_one("#transfers-table", DataTable)
            empty = self.query_one("#empty-transfers", Static)
        except Exception:
            return ""

        table.display = True
        self.query_one("#empty-transfers", Static).display = False

        table.add_row(
            filename,
            "↑" if operation == "upload" else "↓",
            "0%",
            "--",
            "--:--",
            "QUEUED",
            provider,
            key=transfer_id,
        )
        return transfer_id

    def update_progress(self, transfer_id: str, progress: int, speed: float = 0, eta: str = "--:--") -> None:
        """Update transfer progress."""
        try:
            table = self.query_one("#transfers-table", DataTable)
        except Exception:
            return

        try:
            speed_str = self._format_speed(speed)
            table.update_cell(transfer_id, "PROGRESS", f"{progress}%")
            table.update_cell(transfer_id, "SPEED", speed_str)
            table.update_cell(transfer_id, "ETA", eta)
            if progress == 100:
                table.update_cell(transfer_id, "STATUS", "COMPLETED")
        except Exception:
            pass

    def complete_transfer(self, transfer_id: str, success: bool) -> None:
        """Mark transfer as complete."""
        try:
            table = self.query_one("#transfers-table", DataTable)
            table.update_cell(transfer_id, "STATUS", "COMPLETED" if success else "FAILED")
            table.update_cell(transfer_id, "PROGRESS", "100%")
        except Exception:
            pass

    def _format_speed(self, speed: float) -> str:
        """Format transfer speed."""
        if speed == 0:
            return "--"
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if speed < 1024:
                return f"{speed:.1f} {unit}/s"
            speed /= 1024
        return f"{speed:.1f} TB/s"

    @on(Button.Pressed, "#pause-all-btn")
    def on_pause_all(self, event: Button.Pressed) -> None:
        """Pause all transfers."""
        self.notify("Pause all - not implemented", severity="warning")

    @on(Button.Pressed, "#resume-all-btn")
    def on_resume_all(self, event: Button.Pressed) -> None:
        """Resume all transfers."""
        self.notify("Resume all - not implemented", severity="warning")

    @on(Button.Pressed, "#clear-completed-btn")
    def on_clear_completed(self, event: Button.Pressed) -> None:
        """Clear completed transfers."""
        try:
            table = self.query_one("#transfers-table", DataTable)
            empty = self.query_one("#empty-transfers", Static)
        except Exception:
            return

        # Remove completed/failed rows
        completed_keys = []
        for row_key in list(table.rows.keys()):
            try:
                status = table.get_cell(row_key, "STATUS")
                if status in ("COMPLETED", "FAILED"):
                    completed_keys.append(row_key)
            except Exception:
                pass

        for key in completed_keys:
            try:
                table.remove_row(key)
            except Exception:
                pass

        if not table.rows:
            table.display = False
            self.query_one("#empty-transfers", Static).display = True

        self.notify(f"Cleared {len(completed_keys)} completed transfers", severity="information")

    @on(Button.Pressed, "#retry-failed-btn")
    def on_retry_failed(self, event: Button.Pressed) -> None:
        """Retry failed transfers."""
        self.notify("Retry failed - not implemented", severity="warning")
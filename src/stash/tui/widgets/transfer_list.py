"""Transfer List Widget."""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING

from textual import on, work
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import DataTable, Label, ProgressBar, Static

if TYPE_CHECKING:
    pass


class TransferList(Vertical):
    """Transfer/jobs list widget."""

    DEFAULT_CSS = """
    TransferList {
        height: 12;
        background: #333f58;
        border-top: solid #4a7a96;
        padding: 1;
    }

    #transfers-header {
        height: 2;
        color: #fbbbad;
        text-style: bold;
        padding: 0 1;
        border-bottom: solid #4a7a96;
    }

    #transfers-table {
        height: 1fr;
        background: #292831;
        border: none;
    }

    .transfer-row {
        height: 3;
    }
    """

    class TransferAdded(Message):
        """Transfer added to the list."""
        def __init__(self, transfer_id: str, operation: str) -> None:
            self.transfer_id = transfer_id
            self.operation = operation
            super().__init__()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._transfers: dict[str, dict] = {}
        self._next_id = 0

    def compose(self) -> ComposeResult:
        yield Label("ACTIVE TRANSFERS", id="transfers-header")
        yield Static("No active transfers", id="empty-transfers")
        table = DataTable(id="transfers-table", cursor_type="row")
        table.add_columns("FILENAME", "OP", "PROGRESS", "SPEED", "ETA", "STATUS")
        table.zebra_stripes = True
        table.display = False
        yield table

    def add_transfer(self, filename: str, operation: str, total_size: int) -> str:
        """Add a new transfer."""
        transfer_id = str(uuid.uuid4())[:8]
        self._transfers[transfer_id] = {
            "filename": filename,
            "operation": operation,
            "total_size": total_size,
            "progress": 0,
            "speed": 0,
            "eta": "--:--",
            "status": "running",
            "start_time": time.time(),
        }

        self._update_table()
        self.post_message(self.TransferAdded(transfer_id, operation))
        return transfer_id

    def update_progress(self, transfer_id: str, progress: int, speed: float = 0) -> None:
        """Update transfer progress."""
        if transfer_id in self._transfers:
            self._transfers[transfer_id]["progress"] = progress
            if speed > 0:
                self._transfers[transfer_id]["speed"] = speed
            elapsed = time.time() - self._transfers[transfer_id]["start_time"]
            if progress > 0 and elapsed > 0:
                remaining = (elapsed / progress) * (100 - progress)
                self._transfers[transfer_id]["eta"] = self._format_time(remaining)
            self._update_table()

    def complete_transfer(self, transfer_id: str, success: bool) -> None:
        """Mark transfer as complete."""
        if transfer_id in self._transfers:
            self._transfers[transfer_id]["progress"] = 100
            self._transfers[transfer_id]["status"] = "completed" if success else "failed"
            self._update_table()

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
            return "--"
        return self._format_size(int(speed)) + "/s"

    def _format_time(self, seconds: float) -> str:
        """Format time as MM:SS or HH:MM:SS."""
        if seconds < 60:
            return f"{int(seconds):02d}s"
        elif seconds < 3600:
            m = int(seconds // 60)
            s = int(seconds % 60)
            return f"{m:02d}:{s:02d}"
        else:
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            return f"{h:02d}:{m:02d}"

    def _update_table(self) -> None:
        """Update the transfers table."""
        try:
            table = self.query_one("#transfers-table", DataTable)
            empty = self.query_one("#empty-transfers", Static)
        except Exception:
            return

        if not self._transfers:
            table.display = False
            empty.display = True
            return

        table.display = True
        empty.display = False

        current_keys = set(table.rows.keys())
        new_keys = set(self._transfers.keys())

        for key in current_keys - new_keys:
            try:
                table.remove_row(key)
            except Exception:
                pass

        for transfer_id, transfer in self._transfers.items():
            speed_str = self._format_speed(transfer["speed"])
            if transfer_id not in current_keys:
                table.add_row(
                    transfer["filename"],
                    "↑" if transfer["operation"] == "upload" else "↓",
                    f"{transfer['progress']}%",
                    speed_str,
                    transfer["eta"],
                    transfer["status"].upper(),
                    key=transfer_id,
                )
            else:
                try:
                    table.update_cell(transfer_id, "PROGRESS", f"{transfer['progress']}%")
                    table.update_cell(transfer_id, "SPEED", speed_str)
                    table.update_cell(transfer_id, "ETA", transfer["eta"])
                    table.update_cell(transfer_id, "STATUS", transfer["status"].upper())
                except Exception:
                    pass

    def clear_completed(self) -> None:
        """Remove completed transfers."""
        completed = [k for k, v in self._transfers.items() if v["status"] in ("completed", "failed")]
        for k in completed:
            del self._transfers[k]
        self._update_table()
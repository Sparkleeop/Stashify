"""File Info Screen."""

from __future__ import annotations

from textual import on
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Static


class FileInfoScreen(Screen):
    """File information detail screen."""

    DEFAULT_CSS = """
    FileInfoScreen {
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

    .file-info-panel {
        background: #333f58;
        border: solid #4a7a96;
        padding: 1;
        margin-bottom: 1;
    }

    .file-info-title {
        color: #fbbbad;
        text-style: bold;
        margin-bottom: 1;
        border-bottom: solid #4a7a96;
        padding-bottom: 1;
    }

    .file-info-row {
        height: 2;
        layout: horizontal;
        padding: 0 1;
    }

    .file-info-label {
        color: #4a7a96;
        width: 20;
        content-align: right middle;
        padding-right: 2;
    }

    .file-info-value {
        color: #e8e8e8;
        width: 1fr;
        content-align: left middle;
    }

    .provider-distribution {
        margin-top: 1;
    }

    .provider-dist-row {
        height: 2;
        layout: horizontal;
        padding: 0 1;
    }

    .provider-dist-name {
        color: #e8e8e8;
        width: 15;
        content-align: right middle;
        padding-right: 1;
    }

    .provider-dist-bar {
        width: 1fr;
        height: 1;
        background: #292831;
        margin: 0 1;
    }

    .provider-dist-bar--telegram {
        background: #0088cc;
    }

    .provider-dist-bar--discord {
        background: #5865f2;
    }

    .provider-dist-bar--s3 {
        background: #ff9900;
    }

    .provider-dist-value {
        color: #888888;
        width: 10;
        content-align: right middle;
    }

    .close-button {
        margin-top: 2;
        width: 20;
    }
    """

    def __init__(self, file_data: dict = None, is_local: bool = False) -> None:
        super().__init__()
        self._file_data = file_data or {}
        self._is_local = is_local

    def compose(self) -> ComposeResult:
        yield Static(f"FILE INFO {'(LOCAL)' if self._is_local else '(REMOTE)'}", classes="screen-title")

        with Vertical(classes="file-info-panel"):
            yield Static("FILE DETAILS", classes="file-info-title")

            for label, value in self._get_basic_info():
                with Static(classes="file-info-row"):
                    yield Static(label, classes="file-info-label")
                    yield Static(value, classes="file-info-value")

        if not self._is_local:
            with Vertical(classes="file-info-panel"):
                yield Static("PROVIDER DISTRIBUTION", classes="file-info-title")

                for name, count, total, color_class in self._get_provider_distribution():
                    with Static(classes="provider-dist-row"):
                        yield Static(name, classes="provider-dist-name")
                        bar = Static(classes=f"provider-dist-bar {color_class}")
                        bar.styles.width = f"{int(count/total*100)}%"
                        yield bar
                        yield Static(f"{count}/{total}", classes="provider-dist-value")

        yield Button("Close", variant="default", id="close-btn", classes="close-button")

    def _get_basic_info(self) -> list[tuple[str, str]]:
        """Get basic file info rows."""
        info = []
        if self._is_local:
            info.append(("Name", self._file_data.get("name", "unknown")))
            info.append(("Path", self._file_data.get("path", "unknown")))
            info.append(("Size", self._file_data.get("size", "unknown")))
            info.append(("Type", self._file_data.get("type", "unknown")))
            info.append(("Modified", self._file_data.get("modified", "unknown")))
        else:
            info.append(("Name", self._file_data.get("name", "unknown")))
            info.append(("File ID", self._file_data.get("file_id", "unknown")[:16]))
            info.append(("Size", self._file_data.get("size", "unknown")))
            info.append(("Chunks", str(self._file_data.get("chunk_count", "unknown"))))
            info.append(("Providers", self._file_data.get("providers", "unknown")))
            info.append(("Status", "✓ Complete" if self._file_data.get("complete", True) else "✗ Incomplete"))
        return info

    def _get_provider_distribution(self) -> list[tuple[str, int, int, str]]:
        """Get provider distribution for bar chart."""
        providers = self._file_data.get("providers_list", [])
        if not providers:
            return []

        total_chunks = self._file_data.get("chunk_count", len(providers))
        dist = []
        for p in providers:
            count = total_chunks // len(providers)
            color_class = {
                "discord": "provider-dist-bar--discord",
                "telegram": "provider-dist-bar--telegram",
                "s3": "provider-dist-bar--s3",
            }.get(p.lower(), "")
            dist.append((p.capitalize(), count, total_chunks, color_class))
        return dist

    @on(Button.Pressed, "#close-btn")
    def on_close(self, event: Button.Pressed) -> None:
        """Close the screen."""
        self.app.pop_screen()
"""Search Screen/Overlay."""

from __future__ import annotations

from textual import on
from textual.containers import Vertical
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Input, ListView, ListItem, Static


class SearchScreen(Screen):
    """Search overlay for finding files."""

    DEFAULT_CSS = """
    SearchScreen {
        background: #333f58;
        border: solid #4a7a96;
        padding: 1;
        width: 70%;
        height: auto;
        max-height: 60%;
        layer: overlay;
        offset-x: 15%;
        offset-y: 15%;
    }

    .search-header {
        color: #fbbbad;
        text-style: bold;
        margin-bottom: 1;
        border-bottom: solid #4a7a96;
        padding-bottom: 1;
    }

    .search-input {
        background: #292831;
        color: #fbbbad;
        border: solid #4a7a96;
        margin-bottom: 1;
    }

    .search-input:focus {
        border: solid #ee8695;
    }

    .search-results {
        background: #292831;
        border: none;
        max-height: 40;
    }

    .search-result {
        padding: 0 1;
        color: #e8e8e8;
        height: 3;
    }

    .search-result:hover {
        background: #333f58;
        color: #fbbbad;
    }

    .search-result.--highlight {
        background: #333f58;
        color: #fbbbad;
    }
    """

    class SearchResultSelected(Message):
        """Search result selected."""
        def __init__(self, result: dict) -> None:
            self.result = result
            super().__init__()

    def __init__(self, search_scope: str = "all", **kwargs) -> None:
        super().__init__(**kwargs)
        self._search_scope = search_scope  # "local", "remote", "all"
        self._results: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Static(f"SEARCH ({self._search_scope.upper()})", classes="search-header")
        yield Input(placeholder="Search files...", id="search-input", classes="search-input")
        yield ListView(id="search-results")

    def on_mount(self) -> None:
        """Initialize the search screen."""
        self.query_one("#search-input", Input).focus()

    @on(Input.Changed, "#search-input")
    def on_input_changed(self, event: Input.Changed) -> None:
        """Filter results based on input."""
        query = event.value.lower()
        self._filter_results(query)

    def _filter_results(self, query: str) -> None:
        """Filter and display results."""
        try:
            results_view = self.query_one("#search-results", ListView)
        except Exception:
            return

        results_view.clear()

        if not query:
            return

        filtered = [
            r for r in self._results
            if query in r.get("name", "").lower()
        ]

        for result in filtered[:50]:
            item = ListItem(Static(result.get("name", "unknown")), classes="search-result")
            item.data = result
            results_view.append(item)

    @on(ListView.Selected, "#search-results")
    def on_selected(self, event: ListView.Selected) -> None:
        """Handle result selection."""
        if event.item and hasattr(event.item, 'data'):
            self.post_message(self.SearchResultSelected(event.item.data))
            self.app.pop_screen()

    def set_results(self, results: list[dict]) -> None:
        """Set search results."""
        self._results = results
        if self.query_one("#search-input", Input).value:
            self._filter_results(self.query_one("#search-input", Input).value)

    def on_key(self, event) -> None:
        """Handle key events."""
        if event.key == "escape":
            self.app.pop_screen()
            event.stop()
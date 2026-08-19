"""CLI output formatting."""

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table

console = Console()


def print_success(message: str) -> None:
    """Print success message."""
    console.print(f"[green]OK[/green] {message}")


def print_error(message: str) -> None:
    """Print error message."""
    console.print(f"[red]ERROR[/red] {message}")


def print_warning(message: str) -> None:
    """Print warning message."""
    console.print(f"[yellow]WARN[/yellow] {message}")


def print_info(message: str) -> None:
    """Print info message."""
    console.print(f"[blue]INFO[/blue] {message}")


def create_progress() -> Progress:
    """Create a progress bar."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
    )


def print_table(title: str, columns: list[str], rows: list[list[str]]) -> None:
    """Print a formatted table."""
    table = Table(title=title, show_header=True, header_style="bold cyan")
    for col in columns:
        table.add_column(col)
    for row in rows:
        table.add_row(*row)
    console.print(table)


from stash.core.manifest import FileManifest


def print_file_info(manifest: FileManifest, providers: dict[str, Any]) -> None:
    """Print detailed file information."""
    panel = Panel.fit(
        f"[bold]File ID:[/bold] {manifest.file_id}\n"
        f"[bold]Name:[/bold] {manifest.original_name}\n"
        f"[bold]Size:[/bold] {format_size(manifest.original_size)}\n"
        f"[bold]Chunks:[/bold] {manifest.chunk_count}\n"
        f"[bold]Chunk Size:[/bold] {format_size(manifest.chunk_size)}\n"
        f"[bold]Strategy:[/bold] {manifest.strategy.value}\n"
        f"[bold]Encryption:[/bold] {manifest.encryption.algorithm}\n"
        f"[bold]Created:[/bold] {format_timestamp(manifest.created_at)}\n"
        f"[bold]Modified:[/bold] {format_timestamp(manifest.modified_at)}",
        title="File Information",
        border_style="cyan",
    )
    console.print(panel)

    if manifest.chunks:
        rows = []
        for chunk in manifest.chunks:
            provider_name = chunk.provider
            providers.get(provider_name, {})
            rows.append([
                str(chunk.index),
                format_size(chunk.size),
                format_size(chunk.encrypted_size),
                provider_name,
                chunk.remote_id[:20] + "...",
                chunk.checksum[:16] + "...",
            ])
        print_table("Chunks", ["Index", "Size", "Encrypted", "Provider", "Remote ID", "Checksum"], rows)


def format_size(size: int) -> str:
    """Format bytes as human-readable string."""
    size_float = float(size)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_float < 1024:
            return f"{size_float:.1f} {unit}"
        size_float /= 1024
    return f"{size_float:.1f} PB"


from datetime import datetime


def format_timestamp(ts: float) -> str:
    """Format timestamp as readable string."""
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def confirm(message: str, default: bool = False) -> bool:
    """Ask for confirmation."""
    suffix = " (y/n)"
    response = console.input(f"{message} (y/n): ").strip().lower()
    if not response:
        return default
    return response in ("y", "yes")
"""JSON-based local metadata storage."""

import json
import time
from pathlib import Path
from typing import Any

from stash.core.exceptions import MetadataError
from stash.core.manifest import FileManifest
from stash.core.storage import ProviderConfig


class MetadataStore:
    """JSON file-based metadata storage."""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.metadata_dir = repo_path / ".stash" / "metadata"
        self.files_dir = self.metadata_dir / "files"
        self.config_file = self.metadata_dir / "config.json"
        self._config_cache: dict[str, Any] | None = None
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Create metadata directories."""
        self.files_dir.mkdir(parents=True, exist_ok=True)

    def _file_path(self, file_id: str) -> Path:
        """Get path for a file's manifest."""
        return self.files_dir / f"{file_id}.json"

    def _load_json(self, path: Path) -> dict[str, Any]:
        """Load JSON from file."""
        try:
            with path.open("r") as f:
                return json.load(f)  # type: ignore[no-any-return]
        except json.JSONDecodeError as e:
            raise MetadataError(f"Invalid JSON in {path}: {e}") from e
        except OSError as e:
            raise MetadataError(f"Failed to read {path}: {e}") from e

    def _save_json(self, path: Path, data: dict[str, Any]) -> None:
        """Save JSON to file atomically."""
        temp_path = path.with_suffix(".tmp")
        try:
            with temp_path.open("w") as f:
                json.dump(data, f, separators=(",", ":"))
            temp_path.replace(path)
        except OSError as e:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise MetadataError(f"Failed to write {path}: {e}") from e

    def save_manifest(self, manifest: FileManifest) -> None:
        """Save a file manifest."""
        path = self._file_path(manifest.file_id)
        self._save_json(path, json.loads(manifest.to_json()))

    def load_manifest(self, file_id: str) -> FileManifest:
        """Load a file manifest."""
        path = self._file_path(file_id)
        if not path.exists():
            raise MetadataError(f"Manifest not found: {file_id}")
        return FileManifest.from_json(json.dumps(self._load_json(path)))

    def delete_manifest(self, file_id: str) -> None:
        """Delete a file manifest."""
        path = self._file_path(file_id)
        if path.exists():
            path.unlink()

    def list_files(self) -> list[str]:
        """List all file IDs."""
        return [f.stem for f in self.files_dir.glob("*.json")]

    def file_exists(self, file_id: str) -> bool:
        """Check if a file manifest exists."""
        return self._file_path(file_id).exists()

    def save_config(self, config: dict[str, Any]) -> None:
        """Save repository configuration."""
        config["updated_at"] = time.time()
        self._save_json(self.config_file, config)
        self._config_cache = config

    def load_config(self) -> dict[str, Any]:
        """Load repository configuration."""
        if self._config_cache is not None:
            return self._config_cache
        if not self.config_file.exists():
            return {}
        self._config_cache = self._load_json(self.config_file)
        return self._config_cache

    def get_provider_config(self, name: str) -> ProviderConfig | None:
        """Get configuration for a specific provider."""
        config = self.load_config()
        provider_data = config.get("providers", {}).get(name)
        if provider_data is None:
            return None
        return ProviderConfig(
            name=name,
            type=provider_data["type"],
            credentials=provider_data["credentials"],
            settings=provider_data.get("settings", {}),
        )

    def set_provider_config(self, name: str, config: ProviderConfig) -> None:
        """Set configuration for a provider."""
        full_config = self.load_config()
        if "providers" not in full_config:
            full_config["providers"] = {}
        full_config["providers"][name] = {
            "type": config.type,
            "credentials": config.credentials,
            "settings": config.settings,
        }
        self.save_config(full_config)

    def remove_provider_config(self, name: str) -> None:
        """Remove a provider configuration."""
        full_config = self.load_config()
        if "providers" in full_config and name in full_config["providers"]:
            del full_config["providers"][name]
            self.save_config(full_config)

    def list_providers(self) -> list[str]:
        """List configured provider names."""
        config = self.load_config()
        return list(config.get("providers", {}).keys())
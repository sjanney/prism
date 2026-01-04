"""Loader registry for dataset format auto-discovery and registration."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Type

from backend.ingestion.base import DatasetLoader

logger = logging.getLogger(__name__)


class LoaderRegistry:
    """Registry for dataset loaders with auto-discovery."""

    def __init__(self):
        """Initialize the registry."""
        self._loaders: Dict[str, Type[DatasetLoader]] = {}

    def register_loader(self, name: str, loader_class: Type[DatasetLoader]) -> None:
        """
        Register a dataset loader.

        Args:
            name: Format name (e.g., "nuscenes", "csv", "json")
            loader_class: Loader class that implements DatasetLoader
        """
        if not issubclass(loader_class, DatasetLoader):
            raise ValueError(f"Loader class must inherit from DatasetLoader")
        self._loaders[name] = loader_class
        logger.debug(f"Registered loader: {name} -> {loader_class.__name__}")

    def get_loader(self, name: str) -> Optional[Type[DatasetLoader]]:
        """
        Get a registered loader class by name.

        Args:
            name: Format name

        Returns:
            Loader class or None if not found
        """
        return self._loaders.get(name)

    def list_available(self) -> List[str]:
        """
        List all available loader names.

        Returns:
            List of registered format names
        """
        return list(self._loaders.keys())

    def detect_format(self, path: Path) -> Optional[str]:
        """
        Auto-detect dataset format from directory structure.

        Args:
            path: Path to dataset directory

        Returns:
            Format name if detected, None otherwise
        """
        path = Path(path)
        
        if not path.exists():
            return None

        # Check for nuScenes format
        nuscenes_path = path / "data" / "sets" / "nuscenes"
        if nuscenes_path.exists():
            if (nuscenes_path / "v1.0-mini").exists() or (nuscenes_path / "v1.0").exists():
                return "nuscenes"

        # Check for config-based format
        config_files = ["prism_config.yaml", "prism_config.yml", "prism_config.json"]
        for config_file in config_files:
            config_path = path / config_file
            if config_path.exists():
                # Load config to determine actual format
                try:
                    import yaml
                    import json
                    with open(config_path, "r", encoding="utf-8") as f:
                        if config_path.suffix in [".yaml", ".yml"]:
                            config = yaml.safe_load(f) or {}
                        else:
                            config = json.load(f)
                    format_type = config.get("format", "").lower()
                    if format_type in ["csv", "json"]:
                        return f"config:{format_type}"
                except Exception:
                    pass
                return "config"

        # Check for CSV files
        csv_files = list(path.rglob("*.csv"))
        if csv_files:
            return "csv"

        # Check for JSON files (look for common patterns)
        json_files = list(path.rglob("*.json"))
        if json_files:
            # Check if it's a directory of JSON files (not nuScenes structure)
            if len(json_files) > 1 and not nuscenes_path.exists():
                return "json"

        return None

    def create_loader(self, name: str, dataset_path: str) -> Optional[DatasetLoader]:
        """
        Create an instance of a registered loader.

        Args:
            name: Format name
            dataset_path: Path to dataset directory

        Returns:
            Loader instance or None if not found
        """
        loader_class = self.get_loader(name)
        if loader_class is None:
            return None
        
        try:
            return loader_class(dataset_path)
        except Exception as e:
            logger.error(f"Failed to create loader {name}: {e}")
            return None


# Global registry instance
_registry = LoaderRegistry()


def get_registry() -> LoaderRegistry:
    """Get the global loader registry."""
    return _registry


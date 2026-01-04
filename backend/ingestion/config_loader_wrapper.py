"""Wrapper for loading datasets from configuration files."""

import logging
from pathlib import Path
from typing import Optional

from backend.ingestion.base import DatasetLoader, FrameMetadata
from backend.ingestion.csv_loader import CSVLoader
from backend.ingestion.json_loader import JSONLoader

logger = logging.getLogger(__name__)


def create_loader_from_config(config_path: str, dataset_path: Optional[str] = None) -> DatasetLoader:
    """
    Create an appropriate loader based on configuration file.

    Args:
        config_path: Path to configuration file
        dataset_path: Optional override for dataset path

    Returns:
        DatasetLoader instance (CSVLoader or JSONLoader)
    """
    config_path_obj = Path(config_path)
    if not config_path_obj.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # Load config to determine format
    import yaml
    import json

    with open(config_path_obj, "r", encoding="utf-8") as f:
        if config_path_obj.suffix in [".yaml", ".yml"]:
            config = yaml.safe_load(f) or {}
        else:
            config = json.load(f)

    format_type = config.get("format", "").lower()

    if format_type == "csv":
        return CSVLoader(config_path, dataset_path)
    elif format_type == "json":
        return JSONLoader(config_path, dataset_path)
    else:
        raise ValueError(f"Unsupported format '{format_type}' in config. Must be 'csv' or 'json'")


"""JSON dataset loader with configuration support."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.ingestion.config_loader import ConfigLoader
from backend.ingestion.base import FrameMetadata

logger = logging.getLogger(__name__)


class JSONLoader(ConfigLoader):
    """Loader for JSON datasets with configuration-driven field mapping."""

    def load_metadata(self, path: Optional[str] = None) -> List[FrameMetadata]:
        """
        Load metadata from JSON file(s).

        Args:
            path: Optional override for dataset path (uses config path if None)

        Returns:
            List of FrameMetadata objects
        """
        if path:
            self.dataset_path = Path(path)

        input_config = self.config.get("input", {})
        input_path = input_config.get("path", str(self.dataset_path))
        pattern = input_config.get("pattern", "*.json")
        recursive = input_config.get("recursive", False)
        array_field = input_config.get("array_field")  # Field path to array of records

        # Resolve input path
        input_path_obj = Path(input_path)
        if not input_path_obj.is_absolute():
            input_path_obj = self.dataset_path / input_path_obj

        # Find JSON files
        if input_path_obj.is_file():
            json_files = [input_path_obj]
        elif input_path_obj.is_dir():
            if recursive:
                json_files = list(input_path_obj.rglob(pattern))
            else:
                json_files = list(input_path_obj.glob(pattern))
        else:
            raise FileNotFoundError(f"Input path does not exist: {input_path_obj}")

        if not json_files:
            raise FileNotFoundError(f"No JSON files found matching pattern '{pattern}' in {input_path_obj}")

        logger.info(f"Found {len(json_files)} JSON file(s)")

        all_frames: List[FrameMetadata] = []

        for json_file in json_files:
            logger.info(f"Processing JSON file: {json_file}")
            frames = self._load_json_file(json_file, array_field)
            all_frames.extend(frames)
            logger.info(f"Loaded {len(frames)} frames from {json_file.name}")

        logger.info(f"Total frames loaded: {len(all_frames)}")
        return all_frames

    def _load_json_file(self, json_path: Path, array_field: Optional[str] = None) -> List[FrameMetadata]:
        """Load frames from a single JSON file."""
        frames: List[FrameMetadata] = []

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Extract array of records
            if array_field:
                # Navigate to array field (e.g., "data.frames")
                records = self._get_field_value(data, array_field)
                if not isinstance(records, list):
                    logger.warning(f"Array field '{array_field}' is not a list in {json_path}")
                    return []
            elif isinstance(data, list):
                records = data
            elif isinstance(data, dict):
                # Single record
                records = [data]
            else:
                logger.warning(f"Unexpected JSON structure in {json_path}")
                return []

            # Process each record
            for row_index, record in enumerate(records):
                if not isinstance(record, dict):
                    logger.warning(f"Row {row_index}: Record is not a dictionary, skipping")
                    continue

                frame_metadata = self._map_row_to_frame_metadata(record, row_index)
                if frame_metadata:
                    # Verify file exists
                    frame_path_obj = Path(frame_metadata.frame_path)
                    if not frame_path_obj.exists():
                        logger.debug(f"Row {row_index}: File not found: {frame_metadata.frame_path}, skipping")
                        continue
                    frames.append(frame_metadata)

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in file {json_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error reading JSON file {json_path}: {e}")
            raise

        return frames


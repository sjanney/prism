"""Base class for configuration-driven dataset loaders."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from backend.ingestion.base import DatasetLoader, FrameMetadata

logger = logging.getLogger(__name__)


class ConfigLoader(DatasetLoader):
    """Base class for configuration-driven dataset loaders."""

    def __init__(self, config_path: str, dataset_path: Optional[str] = None):
        """
        Initialize config loader.

        Args:
            config_path: Path to YAML/JSON configuration file
            dataset_path: Optional override for dataset path (defaults to config file directory)
        """
        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        # Load configuration
        self.config = self._load_config(config_path)

        # Determine dataset path
        if dataset_path:
            self.dataset_path = Path(dataset_path)
        else:
            # Default to config file directory
            self.dataset_path = self.config_path.parent

        # Validate configuration
        self._validate_config()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML or JSON file."""
        path = Path(config_path)
        with open(path, "r", encoding="utf-8") as f:
            if path.suffix in [".yaml", ".yml"]:
                return yaml.safe_load(f) or {}
            elif path.suffix == ".json":
                return json.load(f)
            else:
                # Try YAML first, then JSON
                try:
                    f.seek(0)
                    return yaml.safe_load(f) or {}
                except Exception:
                    f.seek(0)
                    return json.load(f)

    def _validate_config(self) -> None:
        """Validate configuration structure."""
        if "format" not in self.config:
            raise ValueError("Config must specify 'format' field")

        if "mapping" not in self.config:
            raise ValueError("Config must specify 'mapping' field")

        # Validate required mappings
        required_fields = ["frame_path", "timestamp", "camera_angle"]
        for field in required_fields:
            if field not in self.config["mapping"]:
                raise ValueError(f"Config mapping must include '{field}' field")

    def _get_field_value(self, row: Dict[str, Any], field_path: str) -> Any:
        """
        Get field value from row using dot-notation path.

        Args:
            row: Data row (dict or object)
            field_path: Field path (e.g., "nested.field" or "simple_field")

        Returns:
            Field value or None if not found
        """
        if not field_path:
            return None

        # Handle nested paths (e.g., "metadata.timestamp")
        parts = field_path.split(".")
        value = row
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
            if value is None:
                return None

        return value

    def _parse_timestamp(self, value: Any) -> datetime:
        """
        Parse timestamp value to datetime.

        Args:
            value: Timestamp value (string, int, float, or datetime)

        Returns:
            Datetime object
        """
        if isinstance(value, datetime):
            return value

        if isinstance(value, (int, float)):
            # Assume Unix timestamp (seconds or milliseconds)
            if value > 1e12:  # Milliseconds
                return datetime.fromtimestamp(value / 1000)
            else:  # Seconds
                return datetime.fromtimestamp(value)

        if isinstance(value, str):
            # Try parsing with format if specified
            timestamp_format = self.config.get("timestamp_format")
            if timestamp_format:
                try:
                    return datetime.strptime(value, timestamp_format)
                except ValueError:
                    pass

            # Try ISO format
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                pass

            # Try common formats
            for fmt in [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y/%m/%d %H:%M:%S",
            ]:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue

        raise ValueError(f"Unable to parse timestamp: {value}")

    def _map_row_to_frame_metadata(self, row: Dict[str, Any], row_index: int = 0) -> Optional[FrameMetadata]:
        """
        Map a data row to FrameMetadata using configuration mapping.

        Args:
            row: Data row (dict)
            row_index: Row index for error reporting

        Returns:
            FrameMetadata object or None if mapping fails
        """
        mapping = self.config["mapping"]

        try:
            # Extract frame_path (required)
            frame_path_field = mapping.get("frame_path")
            if not frame_path_field:
                logger.warning(f"Row {row_index}: Missing frame_path mapping")
                return None

            frame_path_value = self._get_field_value(row, frame_path_field)
            if not frame_path_value:
                logger.warning(f"Row {row_index}: frame_path is empty")
                return None

            # Resolve path (handle relative paths)
            frame_path = Path(frame_path_value)
            if not frame_path.is_absolute():
                frame_path = self.dataset_path / frame_path
            frame_path = str(frame_path.resolve())

            # Extract timestamp (required)
            timestamp_field = mapping.get("timestamp")
            if not timestamp_field:
                logger.warning(f"Row {row_index}: Missing timestamp mapping")
                return None

            timestamp_value = self._get_field_value(row, timestamp_field)
            if timestamp_value is None:
                logger.warning(f"Row {row_index}: timestamp is empty")
                return None

            timestamp = self._parse_timestamp(timestamp_value)

            # Extract camera_angle (required)
            camera_angle_field = mapping.get("camera_angle")
            if not camera_angle_field:
                logger.warning(f"Row {row_index}: Missing camera_angle mapping")
                return None

            camera_angle_value = self._get_field_value(row, camera_angle_field)
            if camera_angle_value is None:
                # Allow default value
                camera_angle = mapping.get("camera_angle_default", "UNKNOWN")
            else:
                camera_angle = str(camera_angle_value)

            # Extract optional fields
            gps_lat = None
            if "gps_lat" in mapping and mapping["gps_lat"]:
                lat_value = self._get_field_value(row, mapping["gps_lat"])
                if lat_value is not None:
                    try:
                        gps_lat = float(lat_value)
                    except (ValueError, TypeError):
                        pass

            gps_lon = None
            if "gps_lon" in mapping and mapping["gps_lon"]:
                lon_value = self._get_field_value(row, mapping["gps_lon"])
                if lon_value is not None:
                    try:
                        gps_lon = float(lon_value)
                    except (ValueError, TypeError):
                        pass

            weather = None
            if "weather" in mapping and mapping["weather"]:
                weather_value = self._get_field_value(row, mapping["weather"])
                if weather_value is not None:
                    weather = str(weather_value)

            sensor_type = mapping.get("sensor_type", "camera")
            if isinstance(sensor_type, str) and sensor_type.startswith("$"):
                # Dynamic field path
                sensor_type_value = self._get_field_value(row, sensor_type[1:])
                if sensor_type_value is not None:
                    sensor_type = str(sensor_type_value)
            else:
                sensor_type = str(sensor_type)

            original_path = None
            if "original_path" in mapping and mapping["original_path"]:
                original_path_value = self._get_field_value(row, mapping["original_path"])
                if original_path_value is not None:
                    original_path = str(original_path_value)

            return FrameMetadata(
                frame_id=None,  # Will be set when inserted into DB
                frame_path=frame_path,
                timestamp=timestamp,
                gps_lat=gps_lat,
                gps_lon=gps_lon,
                weather=weather,
                camera_angle=camera_angle,
                sensor_type=sensor_type,
                original_path=original_path,
            )

        except Exception as e:
            logger.warning(f"Row {row_index}: Failed to map row to FrameMetadata: {e}")
            return None

    def get_frame_path(self, frame_id: int) -> str:
        """
        Return filesystem path to frame image.

        Note: This requires database query. Implementation should query DB.

        Args:
            frame_id: Frame ID from database

        Returns:
            File system path to frame image
        """
        raise NotImplementedError(
            "get_frame_path requires database query. Use Frame model to retrieve frame_path by id."
        )


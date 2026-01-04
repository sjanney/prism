"""
Example custom dataset loader plugin for Prism.

This example shows how to create a custom loader for your dataset format.
Place this file in one of these directories:
  - ~/.prism/loaders/  (user plugins)
  - ./loaders/           (project plugins)

The loader class name (without "Loader" suffix, lowercased) becomes the plugin name.
This example creates a plugin named "custom".
"""

from backend.ingestion import DatasetLoader, FrameMetadata
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class CustomLoader(DatasetLoader):
    """
    Custom dataset loader example.
    
    This loader demonstrates how to implement a custom dataset format.
    Adjust the logic to match your dataset structure.
    """

    def __init__(self, dataset_path: str):
        """
        Initialize the custom loader.

        Args:
            dataset_path: Path to dataset directory
        """
        self.dataset_path = Path(dataset_path)
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Dataset path does not exist: {dataset_path}")

    def load_metadata(self, path: Optional[str] = None) -> List[FrameMetadata]:
        """
        Load metadata from your custom dataset format.

        Args:
            path: Optional override for dataset path (uses self.dataset_path if None)

        Returns:
            List of FrameMetadata objects
        """
        if path:
            self.dataset_path = Path(path)

        frames: List[FrameMetadata] = []

        # Example: Load metadata from a custom JSON structure
        metadata_file = self.dataset_path / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, "r") as f:
                metadata_list = json.load(f)

            for idx, item in enumerate(metadata_list):
                try:
                    # Parse timestamp (adjust format to match your data)
                    timestamp_str = item.get("timestamp", "")
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

                    # Construct frame path (adjust to match your structure)
                    frame_path = self.dataset_path / item["file_path"]

                    # Create FrameMetadata object
                    frame = FrameMetadata(
                        frame_id=None,  # Will be set when inserted into DB
                        frame_path=str(frame_path),
                        timestamp=timestamp,
                        gps_lat=item.get("gps_lat"),
                        gps_lon=item.get("gps_lon"),
                        weather=item.get("weather"),
                        camera_angle=item.get("camera_angle", "FRONT"),
                        sensor_type=item.get("sensor_type", "camera"),
                        original_path=None,
                    )

                    frames.append(frame)

                except Exception as e:
                    logger.warning(f"Skipping item {idx}: {e}")
                    continue

        # Alternative example: Iterate through image files
        # for image_file in self.dataset_path.glob("*.jpg"):
        #     # Extract metadata from filename, sidecar files, or database
        #     frame = FrameMetadata(
        #         frame_id=None,
        #         frame_path=str(image_file),
        #         timestamp=datetime.now(),  # Parse from your metadata source
        #         gps_lat=None,
        #         gps_lon=None,
        #         weather=None,
        #         camera_angle="FRONT",
        #         sensor_type="camera",
        #         original_path=None,
        #     )
        #     frames.append(frame)

        logger.info(f"Loaded {len(frames)} frames from custom dataset")
        return frames

    def get_frame_path(self, frame_id: int) -> str:
        """
        Return filesystem path to frame image.

        Note: This typically requires querying the database.
        For custom loaders, this is usually not needed during ingestion.

        Args:
            frame_id: Frame ID from database

        Returns:
            File system path to frame image
        """
        raise NotImplementedError(
            "get_frame_path requires database query. Use Frame model to retrieve frame_path by id."
        )


# Usage:
# 1. Save this file as loaders/my_custom_loader.py
# 2. Adjust the load_metadata() method to match your dataset format
# 3. Run: prism ingest --path data/my_dataset --format plugin:custom


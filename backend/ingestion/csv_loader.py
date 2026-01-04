"""CSV dataset loader with configuration support."""

import csv
import logging
from pathlib import Path
from typing import List, Optional

from backend.ingestion.config_loader import ConfigLoader
from backend.ingestion.base import FrameMetadata

logger = logging.getLogger(__name__)


class CSVLoader(ConfigLoader):
    """Loader for CSV datasets with configuration-driven field mapping."""

    def load_metadata(self, path: Optional[str] = None) -> List[FrameMetadata]:
        """
        Load metadata from CSV file(s).

        Args:
            path: Optional override for dataset path (uses config path if None)

        Returns:
            List of FrameMetadata objects
        """
        if path:
            self.dataset_path = Path(path)

        input_config = self.config.get("input", {})
        input_path = input_config.get("path", str(self.dataset_path))
        pattern = input_config.get("pattern", "*.csv")
        recursive = input_config.get("recursive", False)

        # Resolve input path
        input_path_obj = Path(input_path)
        if not input_path_obj.is_absolute():
            input_path_obj = self.dataset_path / input_path_obj

        # Find CSV files
        if input_path_obj.is_file():
            csv_files = [input_path_obj]
        elif input_path_obj.is_dir():
            if recursive:
                csv_files = list(input_path_obj.rglob(pattern))
            else:
                csv_files = list(input_path_obj.glob(pattern))
        else:
            raise FileNotFoundError(f"Input path does not exist: {input_path_obj}")

        if not csv_files:
            raise FileNotFoundError(f"No CSV files found matching pattern '{pattern}' in {input_path_obj}")

        logger.info(f"Found {len(csv_files)} CSV file(s)")

        all_frames: List[FrameMetadata] = []

        for csv_file in csv_files:
            logger.info(f"Processing CSV file: {csv_file}")
            frames = self._load_csv_file(csv_file)
            all_frames.extend(frames)
            logger.info(f"Loaded {len(frames)} frames from {csv_file.name}")

        logger.info(f"Total frames loaded: {len(all_frames)}")
        return all_frames

    def _load_csv_file(self, csv_path: Path) -> List[FrameMetadata]:
        """Load frames from a single CSV file."""
        frames: List[FrameMetadata] = []

        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                # Try to detect delimiter
                sample = f.read(1024)
                f.seek(0)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter

                reader = csv.DictReader(f, delimiter=delimiter)
                for row_index, row in enumerate(reader):
                    frame_metadata = self._map_row_to_frame_metadata(row, row_index)
                    if frame_metadata:
                        # Verify file exists
                        frame_path_obj = Path(frame_metadata.frame_path)
                        if not frame_path_obj.exists():
                            logger.debug(f"Row {row_index}: File not found: {frame_metadata.frame_path}, skipping")
                            continue
                        frames.append(frame_metadata)

        except Exception as e:
            logger.error(f"Error reading CSV file {csv_path}: {e}")
            raise

        return frames


"""NuScenes dataset loader implementation."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from backend.ingestion.base import DatasetLoader, FrameMetadata

logger = logging.getLogger(__name__)


class NuScenesLoader(DatasetLoader):
    """Loader for nuScenes dataset format."""

    # Camera channel mapping: nuScenes channel name -> simplified camera_angle
    CAMERA_CHANNELS = {
        "CAM_FRONT": "FRONT",
        "CAM_FRONT_LEFT": "FRONT_LEFT",
        "CAM_FRONT_RIGHT": "FRONT_RIGHT",
        "CAM_BACK": "BACK",
        "CAM_BACK_LEFT": "BACK_LEFT",
        "CAM_BACK_RIGHT": "BACK_RIGHT",
    }
    
    # LiDAR channel (nuScenes has one top-mounted LiDAR)
    LIDAR_CHANNELS = {
        "LIDAR_TOP": "TOP",
    }
    
    # Radar channel mapping
    RADAR_CHANNELS = {
        "RADAR_FRONT": "FRONT",
        "RADAR_FRONT_LEFT": "FRONT_LEFT",
        "RADAR_FRONT_RIGHT": "FRONT_RIGHT",
        "RADAR_BACK_LEFT": "BACK_LEFT",
        "RADAR_BACK_RIGHT": "BACK_RIGHT",
    }

    def __init__(self, dataset_path: str):
        """
        Initialize NuScenesLoader.

        Args:
            dataset_path: Path to nuScenes dataset root directory
        """
        self.dataset_path = Path(dataset_path)
        # Auto-detect version by checking which directory exists
        base_path = self.dataset_path / "data" / "sets" / "nuscenes"
        if (base_path / "v1.0-mini").exists():
            self.version = "v1.0-mini"
        elif (base_path / "v1.0").exists():
            self.version = "v1.0"
        else:
            # Default to v1.0-mini for mini dataset
            self.version = "v1.0-mini"
        self.metadata_path = base_path / self.version

    def _load_json(self, filename: str):
        """Load and parse JSON file from metadata directory."""
        file_path = self.metadata_path / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Required file not found: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _parse_timestamp(self, timestamp_us: int) -> datetime:
        """Convert nuScenes timestamp (microseconds) to datetime."""
        # nuScenes timestamps are in microseconds since epoch
        return datetime.fromtimestamp(timestamp_us / 1_000_000)

    def _get_scene_metadata(self, scene_token: str, scenes_data: List[dict]) -> dict:
        """Get scene metadata by scene_token."""
        for scene in scenes_data:
            if scene.get("token") == scene_token:
                return scene
        return {}

    def _get_location_metadata(self, location_token: str, log_data: List[dict]) -> dict:
        """Get location/GPS metadata from log data."""
        for log in log_data:
            if log.get("token") == location_token:
                return log
        return {}

    def load_metadata(self, path: Optional[str] = None) -> List[FrameMetadata]:
        """
        Parse nuScenes dataset and return list of frames with metadata.

        Args:
            path: Optional override for dataset path (uses self.dataset_path if None)

        Returns:
            List of FrameMetadata objects, one per camera frame
        """
        if path:
            self.dataset_path = Path(path)
            self.metadata_path = self.dataset_path / "data" / "sets" / "nuscenes" / self.version

        logger.info(f"Loading nuScenes metadata from {self.metadata_path}")

        # Load required JSON files (these are lists of dictionaries)
        try:
            logger.info("Loading scene.json...")
            scenes_data = self._load_json("scene.json")
            logger.info(f"Loaded {len(scenes_data) if isinstance(scenes_data, list) else 1} scenes")
            
            logger.info("Loading sample.json...")
            samples_data = self._load_json("sample.json")
            logger.info(f"Loaded {len(samples_data) if isinstance(samples_data, list) else 1} samples")
            
            logger.info("Loading sample_data.json (this may take a moment, file is ~15MB)...")
            sample_data_list = self._load_json("sample_data.json")
            logger.info(f"Loaded {len(sample_data_list) if isinstance(sample_data_list, list) else 1} sample_data entries")
            
            logger.info("Loading log.json...")
            log_data = self._load_json("log.json")
            logger.info(f"Loaded {len(log_data) if isinstance(log_data, list) else 1} logs")
        except FileNotFoundError as e:
            logger.error(f"Failed to load required JSON file: {e}")
            raise

        # Ensure we have lists (nuScenes JSON files are lists)
        if not isinstance(scenes_data, list):
            scenes_data = [scenes_data] if isinstance(scenes_data, dict) else []
        if not isinstance(samples_data, list):
            samples_data = [samples_data] if isinstance(samples_data, dict) else []
        if not isinstance(sample_data_list, list):
            sample_data_list = [sample_data_list] if isinstance(sample_data_list, dict) else []
        if not isinstance(log_data, list):
            log_data = [log_data] if isinstance(log_data, dict) else []

        # Build lookup dictionaries for efficient access
        scenes_by_token = {scene["token"]: scene for scene in scenes_data}
        logs_by_token = {log["token"]: log for log in log_data}
        sample_data_by_token = {sd["token"]: sd for sd in sample_data_list}
        
        # Group sample_data by sample_token for efficient lookup
        sample_data_by_sample_token = {}
        for sd in sample_data_list:
            sample_token = sd.get("sample_token")
            if sample_token:
                if sample_token not in sample_data_by_sample_token:
                    sample_data_by_sample_token[sample_token] = []
                sample_data_by_sample_token[sample_token].append(sd)

        frames: List[FrameMetadata] = []
        samples_by_scene = {}
        
        # Statistics for reporting
        stats = {
            "total_sample_data": len(sample_data_list),
            "skipped_non_keyframe": 0,
            "skipped_no_filename": 0,
            "skipped_unknown_sensor": 0,
            "skipped_missing_file": 0,
            "skipped_lidar_failed": 0,
            "processed_camera": 0,
            "processed_lidar": 0,
            "processed_radar": 0,
        }

        logger.info(f"Grouping {len(samples_data)} samples by scene...")
        # Group samples by scene
        for sample in samples_data:
            scene_token = sample.get("scene_token")
            if scene_token not in samples_by_scene:
                samples_by_scene[scene_token] = []
            samples_by_scene[scene_token].append(sample)

        logger.info(f"Processing {len(samples_by_scene)} scenes...")
        # Process each scene
        scene_count = 0
        for scene_token, scene_samples in samples_by_scene.items():
            scene_count += 1
            if scene_count % 10 == 0:
                logger.info(f"Processing scene {scene_count}/{len(samples_by_scene)}... ({len(frames)} frames found so far)")
            scene = scenes_by_token.get(scene_token, {})
            log_token = scene.get("log_token")
            log = logs_by_token.get(log_token, {}) if log_token else {}

            # Extract scene-level metadata
            # Weather is typically in scene description or attributes
            # For MVP, we'll try to extract from scene name or use a default
            weather = None
            scene_name = scene.get("name", "")
            scene_description = scene.get("description", "")
            
            # Try to extract weather from description or name
            if "rain" in scene_description.lower() or "rain" in scene_name.lower():
                weather = "rain"
            elif "snow" in scene_description.lower() or "snow" in scene_name.lower():
                weather = "snow"
            elif "fog" in scene_description.lower() or "fog" in scene_name.lower():
                weather = "fog"
            else:
                weather = "clear"  # Default assumption

            # Process each sample in the scene
            sample_count = 0
            for sample in scene_samples:
                sample_count += 1
                sample_token = sample.get("token")
                sample_timestamp = sample.get("timestamp")

                if not sample_timestamp:
                    logger.warning(f"Sample {sample_token} missing timestamp, skipping")
                    continue

                # Find all sensor data for this sample via sample_token
                sample_data_list_for_sample = sample_data_by_sample_token.get(sample_token, [])
                
                for sample_data in sample_data_list_for_sample:
                    # Only process key frames (samples directory) to avoid duplicates
                    # sweeps are intermediate frames, samples are key frames
                    if not sample_data.get("is_key_frame", False):
                        stats["skipped_non_keyframe"] += 1
                        continue
                    
                    filename = sample_data.get("filename", "")
                    if not filename:
                        stats["skipped_no_filename"] += 1
                        continue
                    
                    # Determine sensor type and channel
                    sensor_type = None
                    channel = None
                    sensor_angle = None
                    path_parts = filename.split("/")
                    
                    # Check for camera
                    for part in path_parts:
                        if part in self.CAMERA_CHANNELS:
                            sensor_type = "camera"
                            channel = part
                            sensor_angle = self.CAMERA_CHANNELS[channel]
                            break
                        elif part in self.LIDAR_CHANNELS:
                            sensor_type = "lidar"
                            channel = part
                            sensor_angle = self.LIDAR_CHANNELS[channel]
                            break
                        elif part in self.RADAR_CHANNELS:
                            sensor_type = "radar"
                            channel = part
                            sensor_angle = self.RADAR_CHANNELS[channel]
                            break
                    
                    if not sensor_type or not channel:
                        stats["skipped_unknown_sensor"] += 1
                        continue  # Skip unknown sensors

                    # Construct full path to original sensor data
                    original_path = self.dataset_path / filename
                    
                    # Verify original file exists
                    if not original_path.exists():
                        stats["skipped_missing_file"] += 1
                        logger.debug(f"Sensor file not found: {original_path}, skipping")
                        continue
                    
                    # For LiDAR: Convert to image for CLIP processing
                    # For Camera: Use directly
                    # For Radar: Store metadata only (no semantic search yet)
                    frame_path = str(original_path)
                    original_path_str = str(original_path)
                    
                    if sensor_type == "lidar":
                        # Convert LiDAR point cloud to BEV image
                        try:
                            from backend.lidar_utils import lidar_to_image
                            
                            # Create visualization cache directory
                            viz_cache_dir = self.dataset_path / ".edgevlm_cache" / "lidar_viz"
                            viz_cache_dir.mkdir(parents=True, exist_ok=True)
                            
                            # Generate cache filename
                            pcd_file = Path(filename)
                            viz_filename = f"{pcd_file.stem}_bev.jpg"
                            viz_path = viz_cache_dir / viz_filename
                            
                            # Convert if not already cached
                            if not viz_path.exists():
                                viz_result = lidar_to_image(
                                    str(original_path),
                                    str(viz_path),
                                    visualization_type="bev"
                                )
                                if viz_result:
                                    frame_path = viz_result
                                else:
                                    stats["skipped_lidar_failed"] += 1
                                    logger.warning(f"Failed to convert LiDAR {original_path}, skipping")
                                    continue
                            else:
                                frame_path = str(viz_path)
                        except Exception as e:
                            stats["skipped_lidar_failed"] += 1
                            logger.warning(f"Error processing LiDAR {original_path}: {e}, skipping")
                            continue
                    elif sensor_type == "radar":
                        # For now, just index metadata (no visualization)
                        # Future: Could visualize range-Doppler maps
                        frame_path = str(original_path)  # Keep original path
                    
                    # Update statistics
                    if sensor_type == "camera":
                        stats["processed_camera"] += 1
                    elif sensor_type == "lidar":
                        stats["processed_lidar"] += 1
                    elif sensor_type == "radar":
                        stats["processed_radar"] += 1
                    
                    # Extract GPS if available
                    gps_lat = None
                    gps_lon = None

                    # Create FrameMetadata
                    frame_metadata = FrameMetadata(
                        frame_id=None,  # Will be set when inserted into DB
                        frame_path=frame_path,
                        timestamp=self._parse_timestamp(sample_timestamp),
                        gps_lat=gps_lat,
                        gps_lon=gps_lon,
                        weather=weather,
                        camera_angle=sensor_angle,  # Reusing field name for compatibility
                        sensor_type=sensor_type,
                        original_path=original_path_str if sensor_type != "camera" else None,
                    )

                    frames.append(frame_metadata)
                    
                    # Log progress every 100 frames
                    if len(frames) % 100 == 0:
                        logger.info(f"Processed {len(frames)} frames so far...")

        logger.info(f"Loaded {len(frames)} frames from nuScenes dataset")
        
        # Log statistics
        logger.info("=" * 60)
        logger.info("Ingestion Statistics:")
        logger.info(f"  Total sample_data entries processed: {stats['total_sample_data']}")
        logger.info(f"  Successfully processed:")
        logger.info(f"    - Camera frames: {stats['processed_camera']}")
        logger.info(f"    - LiDAR frames: {stats['processed_lidar']}")
        logger.info(f"    - Radar frames: {stats['processed_radar']}")
        logger.info(f"  Skipped (expected):")
        logger.info(f"    - Non-keyframe (sweeps): {stats['skipped_non_keyframe']} (intermediate frames, not indexed)")
        logger.info(f"    - No filename: {stats['skipped_no_filename']}")
        logger.info(f"  Skipped (may indicate issues):")
        logger.info(f"    - Unknown sensor type: {stats['skipped_unknown_sensor']}")
        logger.info(f"    - Missing file on disk: {stats['skipped_missing_file']}")
        if stats['skipped_lidar_failed'] > 0:
            logger.warning(f"    - LiDAR conversion failed: {stats['skipped_lidar_failed']}")
        logger.info("=" * 60)
        
        return frames

    def get_frame_path(self, frame_id: int) -> str:
        """
        Return filesystem path to frame image.

        Note: For nuScenes, we need to query the database to get the frame_path.
        This method is a placeholder - actual implementation would query the DB.

        Args:
            frame_id: Frame ID from database

        Returns:
            File system path to frame image
        """
        # This would typically query the database for the frame_path
        # For now, return a placeholder
        raise NotImplementedError(
            "get_frame_path requires database query. Use Frame model to retrieve frame_path by id."
        )


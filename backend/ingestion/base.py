"""Base classes for dataset loaders."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class FrameMetadata(BaseModel):
    """Pydantic model for frame metadata extracted from datasets."""

    frame_id: Optional[int] = Field(None, description="Optional frame ID from dataset")
    frame_path: str = Field(..., description="File system path to frame image or sensor data")
    timestamp: datetime = Field(..., description="Timestamp when frame was captured")
    gps_lat: Optional[float] = Field(None, description="GPS latitude")
    gps_lon: Optional[float] = Field(None, description="GPS longitude")
    weather: Optional[str] = Field(None, description="Weather condition")
    camera_angle: str = Field(..., description="Camera angle (FRONT, FRONT_LEFT, etc.) or sensor type")
    sensor_type: str = Field("camera", description="Sensor type: camera, lidar, or radar")
    original_path: Optional[str] = Field(None, description="Original sensor data path (for LiDAR/Radar)")

    class Config:
        """Pydantic config."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class DatasetLoader(ABC):
    """Abstract base class for dataset loaders."""

    @abstractmethod
    def load_metadata(self, path: Optional[str] = None) -> List[FrameMetadata]:
        """
        Parse dataset and return list of frames with metadata.

        Args:
            path: Optional path to dataset directory (implementation-specific default if None)

        Returns:
            List of FrameMetadata objects
        """
        pass

    @abstractmethod
    def get_frame_path(self, frame_id: int) -> str:
        """
        Return filesystem path to frame image.

        Args:
            frame_id: Frame identifier

        Returns:
            File system path to frame image
        """
        pass


"""SQLAlchemy ORM models for EdgeVLM database."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    Index,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Frame(Base):
    """Frame metadata model for storing indexed camera frames."""

    __tablename__ = "frames"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset = Column(String(50), nullable=False, index=True)
    frame_path = Column(String(500), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    gps_lat = Column(Float, nullable=True)
    gps_lon = Column(Float, nullable=True)
    weather = Column(String(50), nullable=True, index=True)
    camera_angle = Column(String(20), nullable=False, index=True)  # Reused for sensor angle/type
    sensor_type = Column(String(20), nullable=False, default="camera", index=True)  # camera, lidar, radar
    original_path = Column(String(500), nullable=True)  # Original sensor data path (for LiDAR/Radar)
    indexed_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Composite index for common query patterns
    __table_args__ = (
        Index("idx_dataset_camera", "dataset", "camera_angle"),
        Index("idx_timestamp_weather", "timestamp", "weather"),
        Index("idx_sensor_type", "sensor_type"),
        Index("idx_dataset_sensor", "dataset", "sensor_type"),
    )

    def __repr__(self) -> str:
        return f"<Frame(id={self.id}, dataset={self.dataset}, camera={self.camera_angle})>"


class Collection(Base):
    """Collection model for storing saved search results."""

    __tablename__ = "collections"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(200), nullable=False)
    query = Column(Text, nullable=False)
    result_ids = Column(JSON, nullable=False)  # Array of frame IDs
    collection_metadata = Column(JSON, nullable=True)  # Stats like avg_confidence, weather_distribution (renamed from 'metadata' to avoid SQLAlchemy conflict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    creator_email = Column(String(100), nullable=True)

    def __repr__(self) -> str:
        return f"<Collection(id={self.id}, name={self.name}, results={len(self.result_ids) if self.result_ids else 0})>"


class SearchJob(Base):
    """Search job model for persistent job storage."""

    __tablename__ = "search_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    query = Column(Text, nullable=False)
    status = Column(String(20), nullable=False)  # processing, complete, failed
    progress = Column(JSON, nullable=True)  # {frames_processed, frames_total, matches_found}
    results = Column(JSON, nullable=True)  # Array of SearchResultItem dicts
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<SearchJob(id={self.id}, status={self.status}, query={self.query[:50]}...)>"


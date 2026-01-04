"""FastAPI application for EdgeVLM semantic search API."""

import asyncio
import csv
import io
import json
import logging
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from PIL import Image

from backend.config import settings
from backend.database import get_session
from backend.ingestion import FrameMetadata
from backend.models import Collection, Frame, SearchJob
from backend.search_engine import search

logger = logging.getLogger(__name__)

app = FastAPI(
    title="EdgeVLM API",
    description="Semantic search API for autonomous vehicle datasets",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class JobStatus(str, Enum):
    """Job status enumeration."""

    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


# Pydantic Models for Request/Response

class SearchRequest(BaseModel):
    """Request model for search endpoint."""

    query: str = Field(..., description="Natural language search query")
    dataset: Optional[str] = Field("nuscenes", description="Dataset name")
    filters: Optional[dict] = Field(None, description="Optional filters (weather, time_of_day, etc.)")
    max_results: Optional[int] = Field(50, description="Maximum number of results to return")
    confidence_threshold: Optional[float] = Field(0.0, description="Minimum confidence score (0-100)")


class SearchResponse(BaseModel):
    """Response model for search job creation."""

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status")
    estimated_time_seconds: Optional[int] = Field(None, description="Estimated processing time")
    poll_url: str = Field(..., description="URL to poll for results")


class SearchResultItem(BaseModel):
    """Individual search result item."""

    frame_id: Optional[int]
    confidence: float
    timestamp: Optional[str] = None
    thumbnail_url: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class SearchStatusResponse(BaseModel):
    """Response model for search status polling."""

    job_id: str
    status: str
    progress: Optional[dict] = None
    results: Optional[List[SearchResultItem]] = None
    error: Optional[str] = None


class CreateCollectionRequest(BaseModel):
    """Request model for creating a collection."""

    name: str = Field(..., description="Collection name", max_length=200)
    query: str = Field(..., description="Search query that generated results")
    result_ids: List[int] = Field(..., description="List of frame IDs in collection")
    metadata: Optional[dict] = Field(None, description="Additional metadata")


class CollectionResponse(BaseModel):
    """Response model for collection."""

    id: str
    name: str
    query: str
    result_ids: List[int]
    metadata: Optional[dict] = None
    created_at: str
    creator_email: Optional[str] = None


class CollectionListItem(BaseModel):
    """Collection list item (summary)."""

    id: str
    name: str
    query: str
    total_results: int
    created_at: str


# Helper Functions

async def load_frames_from_db() -> List[FrameMetadata]:
    """Load all frames from database and convert to FrameMetadata."""
    async with get_session() as session:
        result = await session.execute(select(Frame))
        frames = result.scalars().all()
        
        frame_metadata_list = []
        for frame in frames:
            frame_meta = FrameMetadata(
                frame_id=frame.id,
                frame_path=frame.frame_path,
                timestamp=frame.timestamp,
                gps_lat=frame.gps_lat,
                gps_lon=frame.gps_lon,
                weather=frame.weather,
                camera_angle=frame.camera_angle,
                sensor_type=getattr(frame, "sensor_type", "camera"),
                original_path=getattr(frame, "original_path", None),
            )
            frame_metadata_list.append(frame_meta)
        return frame_metadata_list


async def execute_search_job(job_id: str, query: str, max_results: int, confidence_threshold: float):
    """Execute search in background and update job in database."""
    try:
        # Update job status to processing
        async with get_session() as session:
            result = await session.execute(select(SearchJob).where(SearchJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                logger.error(f"Job {job_id} not found in database")
                return
            
            job.status = JobStatus.PROCESSING
            job.progress = {
                "frames_processed": 0,
                "frames_total": 0,
                "matches_found": 0,
            }
            job.updated_at = datetime.utcnow()
            await session.commit()
        
        # Load frames from database
        frame_metadata_list = await load_frames_from_db()
        
        if not frame_metadata_list:
            async with get_session() as session:
                result = await session.execute(select(SearchJob).where(SearchJob.id == job_id))
                job = result.scalar_one_or_none()
                if job:
                    job.status = JobStatus.FAILED
                    job.error = "No frames found in database. Please ingest a dataset first using: python -m cli.main ingest --path <dataset_path>"
                    job.updated_at = datetime.utcnow()
                    await session.commit()
            return
        
        # Update progress with total frames
        async with get_session() as session:
            result = await session.execute(select(SearchJob).where(SearchJob.id == job_id))
            job = result.scalar_one_or_none()
            if job:
                job.progress = {
                    "frames_processed": 0,
                    "frames_total": len(frame_metadata_list),
                    "matches_found": 0,
                }
                job.updated_at = datetime.utcnow()
                await session.commit()
        
        # Run search (this is synchronous but CPU-bound, so we run in executor)
        # Convert confidence_threshold (0-100) to min_similarity (0-1)
        min_similarity = confidence_threshold / 100.0 if confidence_threshold > 0 else settings.clip_min_similarity
        
        # Progress callback for logging (API updates job progress at completion)
        def log_search_progress(current_batch: int, total_batches: int):
            """Log search progress (API job progress updated at completion)."""
            if current_batch % 10 == 0 or current_batch == total_batches:
                logger.debug(f"Search progress: {current_batch}/{total_batches} batches processed")
        
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: search(query, frame_metadata_list, min_similarity, log_search_progress),
        )
        
        # Limit results
        results = results[:max_results]
        
        # Convert to API response format
        result_items = []
        for result in results:
            thumbnail_url = f"/thumbnails/{result.frame_id}" if result.frame_id else None
            result_items.append(
                SearchResultItem(
                    frame_id=result.frame_id,
                    confidence=result.confidence,
                    timestamp=result.timestamp,
                    thumbnail_url=thumbnail_url,
                    metadata={
                        "gps": [result.gps_lat, result.gps_lon] if result.gps_lat and result.gps_lon else None,
                        "weather": result.weather,
                        "camera_angle": result.camera_angle,
                        "sensor_type": getattr(result, "sensor_type", "camera"),
                        "original_path": getattr(result, "original_path", None),
                        "reasoning": result.reasoning,
                    },
                )
            )
        
        # Save results to database
        async with get_session() as session:
            result = await session.execute(select(SearchJob).where(SearchJob.id == job_id))
            job = result.scalar_one_or_none()
            if job:
                job.status = JobStatus.COMPLETE
                job.progress = {
                    "frames_processed": len(frame_metadata_list),
                    "frames_total": len(frame_metadata_list),
                    "matches_found": len(result_items),
                }
                # Convert Pydantic models to dicts for JSON storage
                job.results = [item.model_dump() for item in result_items]
                job.updated_at = datetime.utcnow()
                await session.commit()
        
    except Exception as e:
        logger.exception(f"Search job {job_id} failed")
        async with get_session() as session:
            result = await session.execute(select(SearchJob).where(SearchJob.id == job_id))
            job = result.scalar_one_or_none()
            if job:
                job.status = JobStatus.FAILED
                job.error = str(e)
                job.updated_at = datetime.utcnow()
                await session.commit()


# API Endpoints

@app.post("/search", response_model=SearchResponse, status_code=202)
async def create_search_job(request: SearchRequest, background_tasks: BackgroundTasks):
    """
    Create a new search job.
    
    Returns a job ID that can be used to poll for results.
    """
    job_id = str(uuid.uuid4())
    
    # Create job in database
    async with get_session() as session:
        job = SearchJob(
            id=job_id,
            query=request.query,
            status=JobStatus.PROCESSING,
            progress={
                "frames_processed": 0,
                "frames_total": 0,
                "matches_found": 0,
            },
        )
        session.add(job)
        await session.commit()
    
    # Estimate time (rough: CLIP processes ~100 images/second)
    # For 1000 frames -> ~10 seconds
    estimated_time = 30  # Conservative estimate
    
    # Start background task
    background_tasks.add_task(
        execute_search_job,
        job_id,
        request.query,
        request.max_results or 50,
        request.confidence_threshold or 0.0,
    )
    
    return SearchResponse(
        job_id=job_id,
        status=JobStatus.PROCESSING,
        estimated_time_seconds=estimated_time,
        poll_url=f"/search/{job_id}",
    )


@app.get("/search/{job_id}", response_model=SearchStatusResponse)
async def get_search_status(job_id: str):
    """
    Poll for search job status and results.
    
    Returns job status and results when complete.
    """
    async with get_session() as session:
        result = await session.execute(select(SearchJob).where(SearchJob.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Convert stored results from dicts back to Pydantic models
        results = None
        if job.results:
            results = [SearchResultItem(**item) for item in job.results]
        
        response = SearchStatusResponse(
            job_id=job.id,
            status=job.status,
            progress=job.progress,
            results=results,
            error=job.error,
        )
        
        return response


@app.post("/collections", response_model=CollectionResponse, status_code=201)
async def create_collection(request: CreateCollectionRequest):
    """
    Save a search result as a collection.
    """
    async with get_session() as session:
        # Calculate metadata if not provided
        metadata = request.metadata or {}
        if "total_results" not in metadata:
            metadata["total_results"] = len(request.result_ids)
        
        # Calculate statistics from frames
        if request.result_ids:
            frames_result = await session.execute(
                select(Frame).where(Frame.id.in_(request.result_ids))
            )
            frames = frames_result.scalars().all()
            
            if frames:
                # Weather distribution
                weather_counts = {}
                for frame in frames:
                    weather = frame.weather or "unknown"
                    weather_counts[weather] = weather_counts.get(weather, 0) + 1
                
                # Date range
                timestamps = [f.timestamp for f in frames if f.timestamp]
                date_range = None
                if timestamps:
                    min_date = min(timestamps)
                    max_date = max(timestamps)
                    date_range = {
                        "start": min_date.isoformat(),
                        "end": max_date.isoformat(),
                    }
                
                # Camera angle distribution
                camera_counts = {}
                for frame in frames:
                    camera = frame.camera_angle or "unknown"
                    camera_counts[camera] = camera_counts.get(camera, 0) + 1
                
                # Add statistics to metadata
                metadata["weather_distribution"] = weather_counts
                metadata["camera_distribution"] = camera_counts
                metadata["date_range"] = date_range
                metadata["total_frames"] = len(frames)
        
        collection = Collection(
            name=request.name,
            query=request.query,
            result_ids=request.result_ids,
            collection_metadata=metadata,
        )
        
        session.add(collection)
        await session.commit()
        await session.refresh(collection)
        
        return CollectionResponse(
            id=collection.id,
            name=collection.name,
            query=collection.query,
            result_ids=collection.result_ids,
            metadata=collection.collection_metadata,  # Map to 'metadata' in API response
            created_at=collection.created_at.isoformat(),
            creator_email=collection.creator_email,
        )


@app.get("/collections", response_model=List[CollectionListItem])
async def list_collections():
    """
    List all saved collections.
    """
    async with get_session() as session:
        result = await session.execute(select(Collection).order_by(Collection.created_at.desc()))
        collections = result.scalars().all()
        
        return [
            CollectionListItem(
                id=col.id,
                name=col.name,
                query=col.query,
                total_results=len(col.result_ids) if col.result_ids else 0,
                created_at=col.created_at.isoformat(),
            )
            for col in collections
        ]


@app.get("/collections/{collection_id}", response_model=CollectionResponse)
async def get_collection(collection_id: str):
    """
    Get details of a specific collection.
    """
    async with get_session() as session:
        result = await session.execute(select(Collection).where(Collection.id == collection_id))
        collection = result.scalar_one_or_none()
        
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")
        
        return CollectionResponse(
            id=collection.id,
            name=collection.name,
            query=collection.query,
            result_ids=collection.result_ids,
            metadata=collection.collection_metadata,  # Map to 'metadata' in API response
            created_at=collection.created_at.isoformat(),
            creator_email=collection.creator_email,
        )


@app.get("/export/{collection_id}")
async def export_collection(
    collection_id: str,
    format: str = Query("json", regex="^(csv|json)$", description="Export format: csv or json")
):
    """
    Export a collection in CSV or JSON format.
    
    CSV format includes: frame_id, timestamp, confidence, file_path, gps_lat, gps_lon
    JSON format follows the schema defined in FR-5.2.
    """
    async with get_session() as session:
        # Load collection
        result = await session.execute(select(Collection).where(Collection.id == collection_id))
        collection = result.scalar_one_or_none()
        
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")
        
        if not collection.result_ids:
            raise HTTPException(status_code=400, detail="Collection has no results to export")
        
        # Load all frames referenced in collection
        frames_result = await session.execute(
            select(Frame).where(Frame.id.in_(collection.result_ids))
        )
        frames = frames_result.scalars().all()
        
        # Create a mapping of frame_id -> frame for quick lookup
        frames_by_id = {frame.id: frame for frame in frames}
        
        # Get confidence scores from metadata if available
        # Metadata might have a confidence map: {frame_id: confidence}
        confidence_map = {}
        if collection.collection_metadata and isinstance(collection.collection_metadata, dict):
            confidence_map = collection.collection_metadata.get("confidence_map", {})
        
        if format == "csv":
            # Generate CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(["frame_id", "timestamp", "confidence", "file_path", "gps"])
            
            # Write rows
            for frame_id in collection.result_ids:
                frame = frames_by_id.get(frame_id)
                if not frame:
                    continue
                
                # Get confidence from map or metadata, default to None
                confidence = confidence_map.get(frame_id) or collection.collection_metadata.get("avg_confidence") if collection.collection_metadata else None
                if confidence is None:
                    confidence = ""
                
                # Format GPS as "lat,lon" or empty string
                if frame.gps_lat is not None and frame.gps_lon is not None:
                    gps = f"{frame.gps_lat},{frame.gps_lon}"
                else:
                    gps = ""
                
                # Format timestamp
                timestamp_str = frame.timestamp.isoformat() if frame.timestamp else ""
                
                writer.writerow([
                    frame.id,
                    timestamp_str,
                    confidence,
                    frame.frame_path,
                    gps,
                ])
            
            # Convert to bytes for streaming
            csv_content = output.getvalue()
            csv_bytes = io.BytesIO(csv_content.encode("utf-8"))
            
            return StreamingResponse(
                csv_bytes,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f'attachment; filename="{collection.name}_export.csv"',
                    "Cache-Control": "no-cache",
                },
            )
        
        else:  # JSON format
            # Build results array following FR-5.2 schema
            results = []
            for frame_id in collection.result_ids:
                frame = frames_by_id.get(frame_id)
                if not frame:
                    continue
                
                # Get confidence
                confidence = confidence_map.get(frame_id) or collection.collection_metadata.get("avg_confidence") if collection.collection_metadata else None
                
                # Build metadata object
                metadata = {
                    "gps": [frame.gps_lat, frame.gps_lon] if frame.gps_lat is not None and frame.gps_lon is not None else None,
                    "weather": frame.weather,
                    "camera": frame.camera_angle,
                }
                
                result_item = {
                    "frame_id": frame.id,
                    "confidence": confidence if confidence is not None else 0.0,
                    "timestamp": frame.timestamp.isoformat() if frame.timestamp else None,
                    "file_path": frame.frame_path,
                    "metadata": metadata,
                }
                results.append(result_item)
            
            # Build JSON response following FR-5.2 schema
            export_data = {
                "collection_name": collection.name,
                "query": collection.query,
                "total_results": len(results),
                "results": results,
            }
            
            # Convert to JSON string
            json_content = json.dumps(export_data, indent=2, ensure_ascii=False)
            json_bytes = io.BytesIO(json_content.encode("utf-8"))
            
            return StreamingResponse(
                json_bytes,
                media_type="application/json",
                headers={
                    "Content-Disposition": f'attachment; filename="{collection.name}_export.json"',
                    "Cache-Control": "no-cache",
                },
            )


@app.get("/thumbnails/{frame_id}")
async def get_thumbnail(frame_id: int):
    """
    Serve a resized thumbnail image for a given frame ID.
    
    Images are resized to 512x512px for performance.
    """
    async with get_session() as session:
        result = await session.execute(select(Frame).where(Frame.id == frame_id))
        frame = result.scalar_one_or_none()
        
        if not frame:
            raise HTTPException(status_code=404, detail="Frame not found")
        
        frame_path = Path(frame.frame_path)
        if not frame_path.exists():
            raise HTTPException(status_code=404, detail="Frame file not found")
        
        try:
            # Load and resize image
            img = Image.open(frame_path).convert("RGB")
            img.thumbnail((512, 512), Image.Resampling.LANCZOS)
            
            # Convert to bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format="JPEG", quality=85)
            img_bytes.seek(0)
            
            return StreamingResponse(
                io.BytesIO(img_bytes.read()),
                media_type="image/jpeg",
                headers={"Cache-Control": "public, max-age=3600"},
            )
        except Exception as e:
            logger.error(f"Error serving thumbnail for frame {frame_id}: {e}")
            raise HTTPException(status_code=500, detail="Error processing image")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/stats")
async def get_stats():
    """Get database statistics."""
    async with get_session() as session:
        # Count total frames
        frame_count_result = await session.execute(select(func.count(Frame.id)))
        frame_count = frame_count_result.scalar() or 0
        
        # Count total collections
        collection_count_result = await session.execute(select(func.count(Collection.id)))
        collection_count = collection_count_result.scalar() or 0
        
        return {
            "total_frames": frame_count,
            "total_collections": collection_count,
            "has_data": frame_count > 0,
        }


"""Semantic search engine with CLIP-based similarity search."""

import logging
import os
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import torch
from PIL import Image
from pydantic import BaseModel
from transformers import CLIPModel, CLIPProcessor

from backend.config import settings
from backend.ingestion import FrameMetadata

logger = logging.getLogger(__name__)


class SearchResult(BaseModel):
    """Search result model with confidence score and metadata."""

    frame_id: Optional[int]
    frame_path: str
    confidence: float  # 0-100 (converted from CLIP similarity 0-1)
    reasoning: Optional[str] = None
    timestamp: Optional[str] = None
    gps_lat: Optional[float] = None
    gps_lon: Optional[float] = None
    weather: Optional[str] = None
    camera_angle: Optional[str] = None
    sensor_type: Optional[str] = "camera"  # camera, lidar, radar
    original_path: Optional[str] = None  # Original sensor data path


class CLIPFilter:
    """CLIP-based semantic search with singleton pattern for model reuse."""

    _instance = None
    _model = None
    _processor = None
    _device = None

    def __new__(cls):
        """Singleton pattern - return same instance on every call."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_model()
        return cls._instance

    def _load_model(self):
        """Load CLIP model once (called only on first instantiation)."""
        if self._model is None:
            logger.info(f"Loading CLIP model (first time only): {settings.clip_model_name}")
            self._model = CLIPModel.from_pretrained(settings.clip_model_name)
            self._processor = CLIPProcessor.from_pretrained(settings.clip_model_name)
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            self._model.to(self._device)
            self._model.eval()
            logger.info(f"CLIP model loaded on {self._device}")

    @property
    def model(self):
        """Get CLIP model."""
        return self._model

    @property
    def processor(self):
        """Get CLIP processor."""
        return self._processor

    @property
    def device(self):
        """Get device (cuda or cpu)."""
        return self._device

    def get_similarities(
        self, query: str, frame_metadata_list: List[FrameMetadata], progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Tuple[FrameMetadata, float]]:
        """
        Compute CLIP similarity scores for all frames.

        Args:
            query: Text query string
            frame_metadata_list: List of FrameMetadata objects to search
            progress_callback: Optional callback function(current, total) for progress updates

        Returns:
            List of tuples (FrameMetadata, similarity_score) where similarity is 0-1
        """
        if not frame_metadata_list:
            return []

        logger.info(f"Computing CLIP similarities for {len(frame_metadata_list)} frames")

        # Embed query text (done once)
        text_inputs = self.processor(text=[query], return_tensors="pt", padding=True, truncation=True)
        text_inputs = {k: v.to(self.device) for k, v in text_inputs.items()}
        
        with torch.no_grad():
            text_embedding = self.model.get_text_features(**text_inputs)
            text_embedding = text_embedding / text_embedding.norm(dim=-1, keepdim=True)

        # Process images in batches for efficiency
        # Increased batch size for better GPU/CPU utilization
        batch_size = 64
        results = []
        total_batches = (len(frame_metadata_list) + batch_size - 1) // batch_size

        for batch_idx, i in enumerate(range(0, len(frame_metadata_list), batch_size)):
            batch = frame_metadata_list[i : i + batch_size]
            batch_paths = [fm.frame_path for fm in batch]
            
            # Load and process images - check file existence first
            images = []
            valid_indices = []
            for idx, path in enumerate(batch_paths):
                # Check file existence before attempting to load
                if not os.path.exists(path):
                    logger.debug(f"Frame file not found: {path}, skipping")
                    continue
                
                try:
                    img = Image.open(path).convert("RGB")
                    images.append(img)
                    valid_indices.append(i + idx)
                except Exception as e:
                    logger.debug(f"Failed to load image {path}: {e}")
                    continue

            if not images:
                # Update progress even if batch had no valid images
                if progress_callback:
                    progress_callback(batch_idx + 1, total_batches)
                continue

            # Process images through CLIP
            image_inputs = self.processor(images=images, return_tensors="pt", padding=True)
            image_inputs = {k: v.to(self.device) for k, v in image_inputs.items()}

            with torch.no_grad():
                image_embeddings = self.model.get_image_features(**image_inputs)
                image_embeddings = image_embeddings / image_embeddings.norm(dim=-1, keepdim=True)

                # Compute cosine similarity
                batch_similarities = torch.cosine_similarity(
                    text_embedding, image_embeddings, dim=-1
                ).cpu()

                # Store results with corresponding frame metadata
                for j, sim in enumerate(batch_similarities.tolist()):
                    frame_idx = valid_indices[j]
                    results.append((frame_metadata_list[frame_idx], float(sim)))
            
            # Update progress
            if progress_callback:
                progress_callback(batch_idx + 1, total_batches)

        logger.info(f"Computed similarities for {len(results)} frames")
        return results


def search(
    query: str,
    frame_metadata_list: Optional[List[FrameMetadata]] = None,
    min_similarity: Optional[float] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> List[SearchResult]:
    """
    CLIP-only semantic search using cosine similarity.

    Args:
        query: Natural language search query
        frame_metadata_list: List of FrameMetadata objects to search
        min_similarity: Minimum similarity threshold (0-1), defaults to config value
        progress_callback: Optional callback function(current, total) for progress updates

    Returns:
        List of SearchResult objects sorted by confidence (descending)
    """
    if min_similarity is None:
        min_similarity = settings.clip_min_similarity
    
    logger.info(f"Starting CLIP semantic search for query: '{query}' (min_similarity={min_similarity})")

    if frame_metadata_list is None:
        raise ValueError("frame_metadata_list is required. Load frames from database first.")

    if not frame_metadata_list:
        logger.info("No frames to search")
        return []

    # Pre-filter frames with missing files before CLIP processing
    # This significantly reduces processing time by skipping invalid frames early
    valid_frames = []
    missing_count = 0
    for frame_meta in frame_metadata_list:
        if os.path.exists(frame_meta.frame_path):
            valid_frames.append(frame_meta)
        else:
            missing_count += 1
    
    if missing_count > 0:
        logger.debug(f"Filtered out {missing_count} frames with missing files (out of {len(frame_metadata_list)} total)")
    
    if not valid_frames:
        logger.warning("No valid frames found (all files are missing)")
        return []

    logger.info(f"Processing {len(valid_frames)} valid frames (skipped {missing_count} missing files)")

    # Get CLIP similarity scores for all valid frames
    clip_filter = CLIPFilter()
    similarities = clip_filter.get_similarities(query, valid_frames, progress_callback=progress_callback)

    # Filter by minimum similarity threshold and convert to SearchResult
    results = []
    for frame_metadata, similarity in similarities:
        if similarity >= min_similarity:
            # Convert similarity (0-1) to confidence (0-100%)
            confidence = similarity * 100.0
            
            results.append(SearchResult(
                frame_id=frame_metadata.frame_id,
                frame_path=frame_metadata.frame_path,
                confidence=confidence,
                reasoning=f"CLIP similarity: {similarity:.3f}",
                timestamp=frame_metadata.timestamp.isoformat() if frame_metadata.timestamp else None,
                gps_lat=frame_metadata.gps_lat,
                gps_lon=frame_metadata.gps_lon,
                weather=frame_metadata.weather,
                camera_angle=frame_metadata.camera_angle,
                sensor_type=getattr(frame_metadata, "sensor_type", "camera"),
                original_path=getattr(frame_metadata, "original_path", None),
            ))

    # Sort by confidence (descending)
    results.sort(key=lambda x: x.confidence, reverse=True)

    logger.info(f"Search complete: {len(results)} matches found (from {len(valid_frames)} valid frames, {len(frame_metadata_list)} total in database)")
    return results


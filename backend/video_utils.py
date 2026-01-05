"""
Video Frame Extraction Utilities for Prism

Provides efficient frame extraction from video files using OpenCV.
Designed to balance coverage with performance.
"""

import cv2
import logging
from PIL import Image
from typing import Generator, Tuple, Optional

logger = logging.getLogger(__name__)


def extract_frames(
    video_path: str,
    fps: float = 1.0,
    max_frames: int = 300,
    min_interval: float = 0.5
) -> Generator[Tuple[Image.Image, float, str], None, None]:
    """
    Extract frames from a video file at specified intervals.

    Args:
        video_path: Path to the video file
        fps: Target frames per second to extract (default: 1.0)
        max_frames: Maximum number of frames to extract (default: 300)
        min_interval: Minimum interval between frames in seconds (default: 0.5)

    Yields:
        Tuple of (PIL.Image, timestamp_seconds, virtual_path)
        virtual_path format: "/path/to/video.mp4#t=12.5"
    """
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        logger.error(f"Failed to open video: {video_path}")
        return
    
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / video_fps if video_fps > 0 else 0
    
    logger.info(f"Video: {video_path} | FPS: {video_fps:.1f} | Duration: {duration:.1f}s | Total frames: {total_frames}")
    
    # Calculate frame interval
    interval = max(1.0 / fps, min_interval)
    frame_interval = int(video_fps * interval)
    
    if frame_interval < 1:
        frame_interval = 1
    
    extracted_count = 0
    frame_number = 0
    
    try:
        while extracted_count < max_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            
            if not ret:
                break
            
            # Calculate timestamp
            timestamp = frame_number / video_fps if video_fps > 0 else 0
            
            # Convert BGR to RGB and create PIL Image
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)
            
            # Create virtual path with timestamp
            virtual_path = f"{video_path}#t={timestamp:.2f}"
            
            yield pil_image, timestamp, virtual_path
            
            extracted_count += 1
            frame_number += frame_interval
            
            if frame_number >= total_frames:
                break
                
    finally:
        cap.release()
    
    logger.info(f"Extracted {extracted_count} frames from {video_path}")


def get_video_info(video_path: str) -> Optional[dict]:
    """
    Get basic information about a video file.

    Returns:
        Dictionary with fps, duration, total_frames, width, height
        or None if video cannot be opened
    """
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        return None
    
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = total_frames / fps if fps > 0 else 0
        
        return {
            "fps": fps,
            "duration": duration,
            "total_frames": total_frames,
            "width": width,
            "height": height
        }
    finally:
        cap.release()


def is_video_file(path: str) -> bool:
    """Check if a path is a supported video file."""
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.m4v'}
    ext = path.lower().rsplit('.', 1)[-1] if '.' in path else ''
    return f'.{ext}' in video_extensions

"""LiDAR visualization utilities for converting point clouds to images for CLIP processing."""

import logging
import os
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def load_point_cloud(pcd_path: str) -> Optional[np.ndarray]:
    """
    Load point cloud from nuScenes .pcd.bin file.
    
    nuScenes LiDAR format: Binary file with float32 points (x, y, z, intensity)
    Each point is 4 floats = 16 bytes
    
    Args:
        pcd_path: Path to .pcd.bin file
        
    Returns:
        Numpy array of shape (N, 4) where columns are [x, y, z, intensity], or None if error
    """
    try:
        if not os.path.exists(pcd_path):
            logger.debug(f"Point cloud file not found: {pcd_path}")
            return None
        
        # Read binary file
        with open(pcd_path, "rb") as f:
            data = f.read()
        
        # nuScenes point clouds are float32 arrays
        # Each point is 4 floats: x, y, z, intensity
        num_points = len(data) // (4 * 4)  # 4 floats * 4 bytes each
        points = np.frombuffer(data, dtype=np.float32).reshape(num_points, 4)
        
        return points
    except Exception as e:
        logger.warning(f"Failed to load point cloud {pcd_path}: {e}")
        return None


def create_bev_image(
    points: np.ndarray,
    resolution: float = 0.1,
    image_size: Tuple[int, int] = (512, 512),
    max_range: float = 50.0,
) -> Image.Image:
    """
    Create Bird's Eye View (BEV) image from point cloud.
    
    Args:
        points: Point cloud array (N, 4) with [x, y, z, intensity]
        resolution: Meters per pixel (default 0.1m = 10cm resolution)
        image_size: Output image size (width, height) in pixels
        max_range: Maximum range to visualize (meters)
        
    Returns:
        PIL Image in RGB format
    """
    if points is None or len(points) == 0:
        # Return blank image
        return Image.new("RGB", image_size, color=(0, 0, 0))
    
    # Extract x, y, z, intensity
    x = points[:, 0]
    y = points[:, 1]
    z = points[:, 2]
    intensity = points[:, 3] if points.shape[1] >= 4 else np.ones(len(points))
    
    # Filter by range
    range_mask = np.sqrt(x**2 + y**2) <= max_range
    x = x[range_mask]
    y = y[range_mask]
    z = z[range_mask]
    intensity = intensity[range_mask]
    
    if len(x) == 0:
        return Image.new("RGB", image_size, color=(0, 0, 0))
    
    # Convert to pixel coordinates
    # Center at (0, 0) and scale
    pixel_x = ((x / resolution) + image_size[0] / 2).astype(int)
    pixel_y = ((y / resolution) + image_size[1] / 2).astype(int)
    
    # Filter to image bounds
    valid = (pixel_x >= 0) & (pixel_x < image_size[0]) & (pixel_y >= 0) & (pixel_y < image_size[1])
    pixel_x = pixel_x[valid]
    pixel_y = pixel_y[valid]
    z = z[valid]
    intensity = intensity[valid]
    
    # Create image
    img_array = np.zeros((image_size[1], image_size[0], 3), dtype=np.uint8)
    
    # Color mapping: height (z) for green channel, intensity for red channel
    # Normalize z to 0-255 (assuming z range -5 to 5 meters)
    z_normalized = np.clip((z + 5) / 10 * 255, 0, 255).astype(np.uint8)
    intensity_normalized = np.clip(intensity * 255, 0, 255).astype(np.uint8)
    
    # Set colors: Red = intensity, Green = height, Blue = constant
    img_array[pixel_y, pixel_x, 0] = intensity_normalized  # Red
    img_array[pixel_y, pixel_x, 1] = z_normalized  # Green
    img_array[pixel_y, pixel_x, 2] = 128  # Blue (constant)
    
    return Image.fromarray(img_array)


def create_range_image(
    points: np.ndarray,
    image_size: Tuple[int, int] = (512, 512),
    fov_horizontal: float = 360.0,
    fov_vertical: float = 40.0,
) -> Image.Image:
    """
    Create range image (spherical projection) from point cloud.
    
    Args:
        points: Point cloud array (N, 4) with [x, y, z, intensity]
        image_size: Output image size (width, height) in pixels
        fov_horizontal: Horizontal field of view in degrees (default 360 for full rotation)
        fov_vertical: Vertical field of view in degrees
        
    Returns:
        PIL Image in RGB format
    """
    if points is None or len(points) == 0:
        return Image.new("RGB", image_size, color=(0, 0, 0))
    
    x = points[:, 0]
    y = points[:, 1]
    z = points[:, 2]
    intensity = points[:, 3] if points.shape[1] >= 4 else np.ones(len(points))
    
    # Convert to spherical coordinates
    range_vals = np.sqrt(x**2 + y**2 + z**2)
    azimuth = np.arctan2(y, x) * 180 / np.pi  # -180 to 180 degrees
    elevation = np.arcsin(z / (range_vals + 1e-6)) * 180 / np.pi  # -90 to 90 degrees
    
    # Convert to pixel coordinates
    pixel_x = ((azimuth + 180) / fov_horizontal * image_size[0]).astype(int)
    pixel_y = ((elevation + fov_vertical / 2) / fov_vertical * image_size[1]).astype(int)
    
    # Filter to image bounds
    valid = (pixel_x >= 0) & (pixel_x < image_size[0]) & (pixel_y >= 0) & (pixel_y < image_size[1])
    pixel_x = pixel_x[valid]
    pixel_y = pixel_y[valid]
    range_vals = range_vals[valid]
    intensity = intensity[valid]
    
    # Create image
    img_array = np.zeros((image_size[1], image_size[0], 3), dtype=np.uint8)
    
    # Normalize range (0-100m) and intensity
    range_normalized = np.clip(range_vals / 100.0 * 255, 0, 255).astype(np.uint8)
    intensity_normalized = np.clip(intensity * 255, 0, 255).astype(np.uint8)
    
    # Color mapping: Red = range, Green = intensity, Blue = constant
    img_array[pixel_y, pixel_x, 0] = range_normalized
    img_array[pixel_y, pixel_x, 1] = intensity_normalized
    img_array[pixel_y, pixel_x, 2] = 128
    
    return Image.fromarray(img_array)


def lidar_to_image(
    pcd_path: str,
    output_path: Optional[str] = None,
    visualization_type: str = "bev",
) -> Optional[str]:
    """
    Convert LiDAR point cloud to image for CLIP processing.
    
    Args:
        pcd_path: Path to .pcd.bin file
        output_path: Optional path to save image (if None, saves next to pcd file)
        visualization_type: "bev" (bird's eye view) or "range" (spherical projection)
        
    Returns:
        Path to saved image, or None if conversion failed
    """
    points = load_point_cloud(pcd_path)
    if points is None:
        return None
    
    # Create visualization
    if visualization_type == "bev":
        img = create_bev_image(points)
    elif visualization_type == "range":
        img = create_range_image(points)
    else:
        logger.warning(f"Unknown visualization type: {visualization_type}, using BEV")
        img = create_bev_image(points)
    
    # Determine output path
    if output_path is None:
        pcd_file = Path(pcd_path)
        output_path = str(pcd_file.parent / f"{pcd_file.stem}_viz.jpg")
    
    # Save image
    try:
        img.save(output_path, "JPEG", quality=85)
        return output_path
    except Exception as e:
        logger.error(f"Failed to save LiDAR visualization: {e}")
        return None


import os
import logging
from typing import Generator, Union, Tuple
from plugins import IngestionSource, plugin_manager
from video_utils import extract_frames

logger = logging.getLogger(__name__)


class LocalFileIngestor(IngestionSource):
    @property
    def name(self) -> str:
        return "Local File System"

    @property
    def description(self) -> str:
        return "Ingests images and videos from a local directory recursively."

    def can_handle(self, path: str) -> bool:
        """Returns True if path exists locally."""
        return os.path.exists(path)

    def discover_files(self, root_path: str, max_files: int = 0) -> Generator[Union[str, Tuple[str, float, str]], None, None]:
        """
        Discover image and video files in a directory.

        For images: yields the file path (str)
        For videos: yields tuples of (virtual_path, timestamp, original_path)
                    where virtual_path is like "video.mp4#t=12.5"
        """
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'}
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.m4v'}
        count = 0
        
        for root, dirs, files in os.walk(root_path):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                full_path = os.path.join(root, file)
                
                if ext in image_extensions:
                    # Standard image file
                    yield full_path
                    count += 1
                    if max_files > 0 and count >= max_files:
                        return
                        
                elif ext in video_extensions:
                    # Video file - extract frames
                    logger.info(f"Extracting frames from video: {file}")
                    try:
                        for pil_image, timestamp, virtual_path in extract_frames(
                            full_path,
                            fps=1.0,
                            max_frames=300
                        ):
                            # Yield video frame as tuple for special handling
                            yield (virtual_path, pil_image)
                            count += 1
                            if max_files > 0 and count >= max_files:
                                return
                    except Exception as e:
                        logger.error(f"Failed to extract frames from {file}: {e}")


def register():
    """Register this plugin."""
    plugin_manager.register_ingestion_source(LocalFileIngestor())

import os
import logging
from typing import Generator
from plugins import IngestionSource, plugin_manager

logger = logging.getLogger(__name__)

class LocalFileIngestor(IngestionSource):
    @property
    def name(self) -> str:
        return "Local File System"

    @property
    def description(self) -> str:
        return "Ingests images from a local directory recursively."

    def can_handle(self, path: str) -> bool:
        """Returns True if path exists locally."""
        # Simple check: if it looks like a path and exists (or could exist)
        # We might be stricter, but specific protocols (s3://) will be handled by others.
        return os.path.exists(path)

    def discover_files(self, root_path: str, max_files: int = 0) -> Generator[str, None, None]:
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'}
        count = 0
        
        for root, dirs, files in os.walk(root_path):
            for file in files:
                if os.path.splitext(file)[1].lower() in image_extensions:
                    yield os.path.join(root, file)
                    count += 1
                    if max_files > 0 and count >= max_files:
                        return

def register():
    """Register this plugin."""
    plugin_manager.register_ingestion_source(LocalFileIngestor())

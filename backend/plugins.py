import logging
from abc import ABC, abstractmethod
from typing import List, Generator

logger = logging.getLogger(__name__)

class IngestionSource(ABC):
    """Abstract base class for data ingestion sources."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def can_handle(self, path: str) -> bool:
        """Return True if this source can handle the given path/URI."""
        pass

    @abstractmethod
    def discover_files(self, path: str, max_files: int = 0) -> Generator[str, None, None]:
        """
        Yields file paths/URIs found in the given path.
        Should respect max_files limit if > 0.
        """
        pass

class PluginManager:
    def __init__(self):
        self.ingestion_sources: List[IngestionSource] = []
        self._pro_enabled = False

    def load_plugins(self):
        """Attempts to load the prism_pro module and register its components."""
        try:
            import prism_pro
            self._pro_enabled = True
            logger.info("Prism Pro plugin loaded successfully.")
            
            # Assuming prism_pro has a register_plugins function or exposes classes
            if hasattr(prism_pro, 'register_plugins'):
                prism_pro.register_plugins(self)
                
        except ImportError:
            logger.info("Prism Pro plugin not found. Running in Community Mode.")
            self._pro_enabled = False

    def register_ingestion_source(self, source: IngestionSource):
        self.ingestion_sources.append(source)
        logger.info(f"Registered ingestion source: {source.name}")

    def get_ingestion_source_for_path(self, path: str) -> IngestionSource:
        """Finds the first registered source that can handle the path."""
        for source in self.ingestion_sources:
            if source.can_handle(path):
                return source
        return None

    @property
    def is_pro(self) -> bool:
        return self._pro_enabled

# Global singleton
plugin_manager = PluginManager()

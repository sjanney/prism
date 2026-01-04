"""Dataset ingestion package with loader registry and implementations."""

# Export base classes for backward compatibility and plugin development
from backend.ingestion.base import DatasetLoader, FrameMetadata

# Export registry
from backend.ingestion.registry import LoaderRegistry, get_registry

# Import and register built-in loaders
from backend.ingestion.nuscenes import NuScenesLoader
from backend.ingestion.csv_loader import CSVLoader
from backend.ingestion.json_loader import JSONLoader
from backend.ingestion.config_loader import ConfigLoader

# Register built-in loaders
_registry = get_registry()
_registry.register_loader("nuscenes", NuScenesLoader)
_registry.register_loader("csv", CSVLoader)
_registry.register_loader("json", JSONLoader)

# Discover and register plugins
try:
    from backend.ingestion.plugin_loader import register_plugins
    register_plugins(_registry)
except Exception as e:
    # Plugin loading is optional, don't fail if it errors
    import logging
    logging.getLogger(__name__).debug(f"Plugin discovery failed (non-fatal): {e}")

# Export for convenience
__all__ = [
    "DatasetLoader",
    "FrameMetadata",
    "LoaderRegistry",
    "get_registry",
    "NuScenesLoader",
    "CSVLoader",
    "JSONLoader",
    "ConfigLoader",
]


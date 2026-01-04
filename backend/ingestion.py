"""Backward compatibility shim for ingestion module.

This module maintains backward compatibility by re-exporting
from the new backend.ingestion package structure.
"""

# Re-export for backward compatibility
from backend.ingestion import (
    DatasetLoader,
    FrameMetadata,
    NuScenesLoader,
)

__all__ = [
    "DatasetLoader",
    "FrameMetadata",
    "NuScenesLoader",
]

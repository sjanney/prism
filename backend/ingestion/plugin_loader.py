"""Plugin system for loading custom dataset loaders."""

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Type

from backend.ingestion.base import DatasetLoader
from backend.ingestion.registry import LoaderRegistry, get_registry

logger = logging.getLogger(__name__)


def discover_plugins(plugin_dirs: Optional[List[Path]] = None) -> Dict[str, Type[DatasetLoader]]:
    """
    Discover and load plugin loaders from specified directories.

    Args:
        plugin_dirs: List of directories to search for plugins.
                     If None, searches default locations:
                     - ~/.prism/loaders/
                     - ./loaders/

    Returns:
        Dictionary mapping plugin names to loader classes
    """
    if plugin_dirs is None:
        # Default plugin directories
        home_dir = Path.home()
        plugin_dirs = [
            home_dir / ".prism" / "loaders",
            Path.cwd() / "loaders",
        ]

    plugins: Dict[str, Type[DatasetLoader]] = {}

    for plugin_dir in plugin_dirs:
        plugin_dir = Path(plugin_dir)
        if not plugin_dir.exists():
            continue

        logger.debug(f"Scanning plugin directory: {plugin_dir}")

        # Find Python files (excluding __init__.py)
        py_files = [
            f for f in plugin_dir.iterdir()
            if f.is_file() and f.suffix == ".py" and f.stem != "__init__"
        ]

        for py_file in py_files:
            try:
                loader_class = _load_plugin_file(py_file)
                if loader_class:
                    # Use class name (without "Loader" suffix if present) as plugin name
                    plugin_name = loader_class.__name__
                    if plugin_name.endswith("Loader"):
                        plugin_name = plugin_name[:-6]  # Remove "Loader" suffix
                    plugin_name = plugin_name.lower()

                    plugins[plugin_name] = loader_class
                    logger.info(f"Loaded plugin: {plugin_name} from {py_file.name}")

            except Exception as e:
                logger.warning(f"Failed to load plugin from {py_file}: {e}")

    return plugins


def _load_plugin_file(file_path: Path) -> Optional[Type[DatasetLoader]]:
    """
    Load a DatasetLoader class from a Python file.

    Args:
        file_path: Path to Python file

    Returns:
        Loader class or None if not found/invalid
    """
    try:
        # Create a unique module name
        module_name = f"prism_plugin_{file_path.stem}"

        # Load module from file
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # Find DatasetLoader subclasses in the module
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, DatasetLoader)
                and attr is not DatasetLoader
            ):
                return attr

        return None

    except Exception as e:
        logger.debug(f"Error loading plugin file {file_path}: {e}")
        return None


def register_plugins(registry: Optional[LoaderRegistry] = None) -> None:
    """
    Discover and register all plugins with the loader registry.

    Args:
        registry: Registry to register plugins with. If None, uses global registry.
    """
    if registry is None:
        registry = get_registry()

    plugins = discover_plugins()

    for plugin_name, loader_class in plugins.items():
        try:
            registry.register_loader(plugin_name, loader_class)
            logger.info(f"Registered plugin loader: {plugin_name}")
        except Exception as e:
            logger.warning(f"Failed to register plugin {plugin_name}: {e}")


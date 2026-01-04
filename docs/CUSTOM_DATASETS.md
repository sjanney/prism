# Custom Dataset Ingestion Guide

Prism supports ingesting custom datasets through two approaches:

1. **Configuration-based ingestion** (for CSV/JSON formats) - No coding required
2. **Plugin-based ingestion** (for complex formats) - Write a Python loader class

## Configuration-Based Ingestion

The easiest way to ingest your own dataset is using a YAML/JSON configuration file. This works for CSV and JSON data formats.

### Quick Start

1. Generate a template configuration:
   ```bash
   prism ingest --create-template csv
   # or
   prism ingest --create-template json
   ```

2. Edit the generated `prism_config_csv.yaml` file to match your dataset structure

3. Place the config file in your dataset directory (or use `--config` flag)

4. Run ingestion:
   ```bash
   prism ingest --path data/my_dataset --config prism_config_csv.yaml
   ```

### Configuration File Format

Configuration files use YAML or JSON format. Here's the structure:

```yaml
format: csv  # or json
input:
  path: "data/my_dataset"        # Relative or absolute path
  pattern: "*.csv"                # Glob pattern for file matching
  recursive: true                 # Search subdirectories

mapping:
  frame_path: "file_path"         # CSV column name or JSON field path
  timestamp: "capture_time"       # Timestamp field
  gps_lat: "latitude"             # GPS latitude (optional)
  gps_lon: "longitude"            # GPS longitude (optional)
  camera_angle: "sensor_name"     # Camera/sensor angle
  sensor_type: "camera"           # Sensor type (camera/lidar/radar) or field path
  weather: null                   # Weather field (optional)

timestamp_format: "%Y-%m-%d %H:%M:%S"  # Optional: timestamp parsing format
```

### CSV Configuration Example

For a CSV file with columns: `file_path`, `timestamp`, `lat`, `lon`, `camera`:

```yaml
format: csv
input:
  path: "data/my_dataset"
  pattern: "frames.csv"
  recursive: false

mapping:
  frame_path: "file_path"
  timestamp: "timestamp"
  gps_lat: "lat"
  gps_lon: "lon"
  camera_angle: "camera"
  sensor_type: "camera"
  weather: null

timestamp_format: "%Y-%m-%d %H:%M:%S"
```

### JSON Configuration Example

For JSON files with nested structure:

```yaml
format: json
input:
  path: "data/my_dataset"
  pattern: "*.json"
  recursive: true
  array_field: "frames"  # Field path to array of records (optional)

mapping:
  frame_path: "metadata.file_path"      # Nested field path
  timestamp: "metadata.timestamp"
  gps_lat: "location.lat"
  gps_lon: "location.lon"
  camera_angle: "sensor.angle"
  sensor_type: "camera"
  weather: "metadata.weather"

timestamp_format: "%Y-%m-%d %H:%M:%S"
```

### Field Mapping

#### Required Fields

- `frame_path`: Path to image file (relative to dataset directory or absolute)
- `timestamp`: Timestamp when frame was captured
- `camera_angle`: Camera/sensor angle identifier

#### Optional Fields

- `gps_lat`, `gps_lon`: GPS coordinates (floats)
- `weather`: Weather condition (string)
- `sensor_type`: Sensor type - "camera", "lidar", or "radar" (default: "camera")
- `original_path`: Original sensor data path (for LiDAR/Radar)

#### Field Paths

For JSON files, use dot notation for nested fields:
- `metadata.timestamp` - accesses `data["metadata"]["timestamp"]`
- `location.lat` - accesses `data["location"]["lat"]`

For CSV files, use column names directly.

#### Dynamic Field Mapping

You can use `$field_path` syntax for dynamic field mapping:
```yaml
sensor_type: "$sensor.type"  # Reads value from sensor.type field
```

### Timestamp Formats

Supported timestamp formats:
- ISO format: `2024-01-15T10:30:00` or `2024-01-15T10:30:00Z`
- Custom format: Specify in `timestamp_format` (Python strptime format)
- Unix timestamp: Automatically detected (seconds or milliseconds)

Common formats:
- `"%Y-%m-%d %H:%M:%S"` - `2024-01-15 10:30:00`
- `"%Y/%m/%d %H:%M:%S"` - `2024/01/15 10:30:00`
- `"%Y-%m-%dT%H:%M:%S"` - `2024-01-15T10:30:00`

## Plugin-Based Ingestion

For complex dataset formats or custom processing logic, you can write a Python plugin.

### Plugin Structure

Create a Python file in one of these locations:
- `~/.prism/loaders/` (user plugins)
- `./loaders/` (project plugins)

Example plugin file: `loaders/my_custom_loader.py`

```python
from backend.ingestion import DatasetLoader, FrameMetadata
from pathlib import Path
from typing import List, Optional
from datetime import datetime

class MyCustomLoader(DatasetLoader):
    """Custom loader for my dataset format."""
    
    def __init__(self, dataset_path: str):
        """Initialize loader with dataset path."""
        self.dataset_path = Path(dataset_path)
    
    def load_metadata(self, path: Optional[str] = None) -> List[FrameMetadata]:
        """
        Load metadata from your dataset.
        
        Returns:
            List of FrameMetadata objects
        """
        frames = []
        
        # Your custom logic here
        # Example: iterate through files, parse metadata, etc.
        for image_file in self.dataset_path.glob("*.jpg"):
            frame = FrameMetadata(
                frame_id=None,
                frame_path=str(image_file),
                timestamp=datetime.now(),  # Parse from your metadata
                gps_lat=None,
                gps_lon=None,
                weather=None,
                camera_angle="FRONT",  # Extract from your data
                sensor_type="camera",
                original_path=None,
            )
            frames.append(frame)
        
        return frames
    
    def get_frame_path(self, frame_id: int) -> str:
        """
        Return filesystem path for a frame ID.
        
        Note: This typically requires database query.
        """
        raise NotImplementedError("Use database query to get frame path")
```

### Using Plugins

1. Create your plugin file in `loaders/my_custom_loader.py`
2. Run ingestion with plugin format:
   ```bash
   prism ingest --path data/my_dataset --format plugin:mycustom
   ```

Plugin names are derived from class names (without "Loader" suffix, lowercased).

### Plugin Discovery

Plugins are automatically discovered on startup. You can check available plugins:
```bash
prism ingest --list-formats
```

## Troubleshooting

### Common Issues

**"Config file not found"**
- Ensure config file exists at the specified path
- Use `--config` flag to specify config file location
- Or place `prism_config.yaml` in dataset directory

**"Format not detected"**
- Specify format explicitly with `--format`
- Check that dataset directory structure matches expected format
- For CSV/JSON, ensure config file is present

**"Field mapping failed"**
- Verify field names in config match your data
- For JSON, check field paths use correct dot notation
- Check that required fields (frame_path, timestamp, camera_angle) are mapped

**"File not found" errors**
- Ensure frame_path values in data are correct (relative to dataset directory)
- Check file permissions
- Verify paths are not absolute when they should be relative (or vice versa)

**"Timestamp parsing failed"**
- Specify correct `timestamp_format` in config
- Check timestamp values match the format
- Try ISO format or Unix timestamps (auto-detected)

### Getting Help

1. Check format detection:
   ```bash
   prism ingest --path data/my_dataset  # Will show auto-detected format
   ```

2. List available formats:
   ```bash
   prism ingest --list-formats
   ```

3. Generate template and inspect structure:
   ```bash
   prism ingest --create-template csv
   cat prism_config_csv.yaml
   ```

4. Enable debug logging:
   ```bash
   export EDGEVLM_LOG_LEVEL=DEBUG
   prism ingest --path data/my_dataset --config config.yaml
   ```

## Examples

See `examples/configs/` and `examples/loaders/` for complete examples.


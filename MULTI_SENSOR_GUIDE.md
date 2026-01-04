# Multi-Sensor Support Guide

Prism now supports **Camera, LiDAR, and Radar** data from nuScenes datasets!

## Overview

### What's Supported

1. **Camera Images** (Original)
   - All 6 camera angles (FRONT, FRONT_LEFT, FRONT_RIGHT, BACK, BACK_LEFT, BACK_RIGHT)
   - Direct semantic search using CLIP

2. **LiDAR Point Clouds** (NEW!)
   - Automatically converted to Bird's Eye View (BEV) images
   - Semantic search works on visualizations
   - Original .pcd.bin files preserved and linked

3. **Radar Data** (NEW!)
   - Metadata indexed (timestamp, location, sensor type)
   - Original files preserved
   - *Note: Semantic search on Radar not yet implemented (future enhancement)*

## How It Works

### LiDAR Processing

When you ingest a dataset, LiDAR point clouds are automatically:
1. **Loaded** from `.pcd.bin` files
2. **Converted** to BEV (Bird's Eye View) images
3. **Cached** in `.prism_cache/lidar_viz/` directory
4. **Indexed** for semantic search

The BEV visualization shows:
- **Red channel**: Intensity (reflectivity)
- **Green channel**: Height (elevation)
- **Blue channel**: Constant (for contrast)

### Example Queries for LiDAR

- "dense traffic" - Finds crowded scenes in point cloud
- "open road" - Finds clear highway sections
- "parked vehicles" - Detects stationary objects
- "tall objects" - Finds buildings, signs, etc.

## Usage

### Ingesting Multi-Sensor Data

The ingestion process automatically detects and processes all sensor types:

```bash
prism ingest --path data/nuscenes
```

This will:
- Index all camera images (as before)
- Convert and index LiDAR point clouds
- Index Radar metadata

### Searching with Sensor Filters

In interactive mode:

```bash
prism interactive
# Select "1" for Search
# Choose sensor filter:
#   1 - All sensors (default)
#   2 - Camera only
#   3 - LiDAR only
#   4 - Radar only
```

### Viewing Results

Results now show:
- **Sensor Type**: CAMERA, LIDAR, or RADAR
- **Original Path**: Link to raw sensor data (for LiDAR/Radar)
- **Visualization Path**: Processed image (for LiDAR BEV)

For LiDAR results, you can:
- View the BEV visualization image
- Access the original `.pcd.bin` file
- Open file location in file manager

## Database Schema

New columns added to `frames` table:
- `sensor_type`: "camera", "lidar", or "radar"
- `original_path`: Path to original sensor data file

## Migration

If you have an existing database, run the migration:

```bash
python scripts/migrate_add_sensors.py
```

This adds the new columns without losing existing data.

## Technical Details

### LiDAR Visualization

- **Resolution**: 0.1 meters per pixel (10cm)
- **Image Size**: 512x512 pixels
- **Range**: 50 meters (configurable)
- **Format**: JPEG, 85% quality

### Performance

- LiDAR conversion: ~0.5 seconds per point cloud
- Cached visualizations: Instant (no re-conversion)
- Storage: ~50KB per LiDAR visualization

### Limitations

1. **Radar**: Currently metadata-only (no semantic search)
   - Future: Range-Doppler map visualizations
   
2. **LiDAR**: Only BEV visualization supported
   - Future: Range images, intensity images

3. **Point Cloud Viewers**: Original `.pcd.bin` files need external viewers
   - Recommended: CloudCompare, Open3D, or nuScenes devkit

## Example Workflow

```bash
# 1. Ingest dataset (includes all sensors)
prism ingest --path data/nuscenes

# 2. Search across all sensors
prism interactive
# Query: "dense traffic"
# Sensor filter: All sensors

# 3. View LiDAR result
# Select result #5 (LiDAR)
# Choose "1" to view BEV visualization
# Or "2" to see original .pcd.bin path

# 4. Open original point cloud
# Use CloudCompare or nuScenes devkit to view .pcd.bin
```

## Benefits for AV Teams

1. **Multi-Modal Edge Cases**: Find scenarios visible in LiDAR but not cameras
   - Example: "pedestrians in fog" (LiDAR sees through fog)

2. **Spatial Understanding**: BEV shows 3D relationships
   - Example: "vehicles in intersection" (see spatial layout)

3. **Sensor Correlation**: Link camera + LiDAR + Radar for same timestamp
   - Future: Cross-sensor queries ("show me camera + LiDAR for this scene")

4. **Complete Coverage**: Index all sensor data, not just cameras
   - Better dataset utilization
   - More edge cases discoverable

## Future Enhancements

- [ ] Radar range-Doppler visualizations
- [ ] LiDAR range image projections
- [ ] Cross-sensor queries (find scenes with matching camera + LiDAR)
- [ ] 3D point cloud viewer integration
- [ ] Sensor fusion visualization


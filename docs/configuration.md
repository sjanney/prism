# Prism Configuration

Prism can be configured via a YAML file at `~/.prism/config.yaml`.

## Configuration File Location

| OS | Path |
|----|------|
| macOS | `~/.prism/config.yaml` |
| Linux | `~/.prism/config.yaml` |
| Windows | `C:\Users\<you>\.prism\config.yaml` |

The directory and file are created automatically on first run.

---

## Configuration Options

```yaml
# ~/.prism/config.yaml

# License key for Prism Pro (optional)
license_key: null  # or "PRISM-PRO-XXXX-XXXX"

# Maximum images for free version
max_free_images: 5000

# Backend gRPC port
backend_port: 50051

# Default database path
default_db: ~/.prism/prism.db

# Compute device: auto, cuda, mps, cpu
device: auto

# Model configuration
models:
  yolo: yolov8m.pt    # Options: yolov8n.pt, yolov8s.pt, yolov8m.pt, yolov8l.pt
  siglip: google/siglip-so400m-patch14-384
```

---

## Option Details

### `license_key`

Your Prism Pro license key. Set this to unlock unlimited indexing and Pro features.

```yaml
license_key: PRISM-PRO-ABCD-1234
```

### `max_free_images`

The maximum number of images that can be indexed in the free version. Default is 5,000.

### `backend_port`

The port the gRPC backend listens on. Change this if 50051 is already in use.

```yaml
backend_port: 50052
```

### `default_db`

Path to the default SQLite database. You can change this to use a specific database.

```yaml
default_db: /path/to/my/project.db
```

### `device`

Force a specific compute device:

| Value | Description |
|-------|-------------|
| `auto` | Auto-detect (CUDA → MPS → CPU) |
| `cuda` | Force NVIDIA GPU |
| `mps` | Force Apple Metal |
| `cpu` | Force CPU (slow but always works) |

### `models.yolo`

YOLOv8 model variant:

| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| `yolov8n.pt` | 6 MB | Fastest | Lower |
| `yolov8s.pt` | 22 MB | Fast | Good |
| `yolov8m.pt` | 50 MB | Medium | Better |
| `yolov8l.pt` | 87 MB | Slow | Best |

### `models.siglip`

SigLIP model for semantic embeddings. The default is the 400M parameter version.

---

## Environment Variables

You can also set some options via environment variables:

| Variable | Description |
|----------|-------------|
| `PRISM_DB_PATH` | Override default database path |
| `CUDA_VISIBLE_DEVICES` | Control GPU visibility |
| `HF_HOME` | HuggingFace model cache directory |

Example:
```bash
CUDA_VISIBLE_DEVICES="" ./run_prism.sh  # Force CPU
```

---

## Resetting Configuration

To reset to defaults, delete the config file:

```bash
rm ~/.prism/config.yaml
```

A new one will be created on next run.

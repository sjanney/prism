# Prism Architecture

This document explains how Prism works under the hood.

## High-Level Overview

```
+------------------------------------------------------------------+
|                         Prism TUI (Go)                           |
|   [Dashboard] [Search] [Index] [Settings] [Pro]                  |
+--------------------------------+---------------------------------+
                                 | gRPC (localhost:50051)
                                 v
+------------------------------------------------------------------+
|                      Prism Backend (Python)                       |
|  +--------------+  +--------------+  +--------------------------+ |
|  |   YOLOv8     |  |   SigLIP     |  |      SQLite + Numpy      | |
|  |  Detection   |  |  Embeddings  |  |      Vector Storage      | |
|  +--------------+  +--------------+  +--------------------------+ |
+------------------------------------------------------------------+
```

## Components

### 1. TUI Frontend (Go)

**Location:** `frontend/`

The terminal user interface is built with:
- **[Bubbletea](https://github.com/charmbracelet/bubbletea)**: Elm-inspired TUI framework
- **[Lipgloss](https://github.com/charmbracelet/lipgloss)**: CSS-like styling for terminals
- **[Bubbles](https://github.com/charmbracelet/bubbles)**: Pre-built components (inputs, spinners, progress bars)

Key files:
- `main.go`: Application logic, state management, message handling
- `styles.go`: All visual styling and the gradient banner

### 2. AI Backend (Python)

**Location:** `backend/`

The Python backend handles all AI inference:

| File | Purpose |
|------|---------|
| `server.py` | gRPC server, routes requests to engine |
| `engine.py` | YOLOv8 + SigLIP inference, search logic |
| `database.py` | SQLite operations, embedding storage |
| `plugins.py` | **[NEW]** Plugin Manager for dynamic extensions |
| `local_ingestion.py` | **[NEW]** Default local file crawler |
| `config.py` | Configuration management, Pro license |
| `errors.py` | Structured error codes |

### 3. Communication (gRPC)

**Location:** `proto/prism.proto`

The frontend and backend communicate via gRPC. Key RPCs:

| RPC | Description |
|-----|-------------|
| `Index` | Streaming RPC for indexing a folder |
| `Search` | Unary RPC for semantic search |
| `GetStats` | Get dataset statistics |
| `GetSystemInfo` | Get device, model, memory info |
| `ActivateLicense` | Activate Prism Pro |
| `PickFolder` | Open native file picker |

---

## Data Flow

### Indexing

```
1. User selects folder
2. Backend walks directory, finds images
3. For each image:
   a. Run YOLOv8 -> detect objects
   b. Compute SigLIP embedding (full image)
   c. Compute SigLIP embedding (each detected crop)
   d. Store embeddings in SQLite as numpy blobs
4. Stream progress back to TUI
```

### Searching

```
1. User enters query text
2. Backend computes text embedding via SigLIP
3. Load all image embeddings from cache (or SQLite)
4. Compute cosine similarity (vectorized numpy)
5. Sort and return top 20 results
6. TUI displays results with confidence scores
```

---

## Database Schema

### `frames` Table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| frame_path | TEXT | Absolute path to image |
| width | INTEGER | Image width |
| height | INTEGER | Image height |
| indexed_at | DATETIME | When the frame was indexed |

### `embeddings` Table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| frame_id | INTEGER | Foreign key to frames |
| embedding_type | TEXT | "full_image" or "object_crop" |
| object_class | TEXT | YOLO class name (if object_crop) |
| bbox | TEXT | JSON bounding box [x1,y1,x2,y2] |
| vector | BLOB | 1152-dim numpy float32 array |

---

## Performance Considerations

1. **Lazy Loading**: Models are only loaded when first needed.
2. **Embedding Cache**: After first search, all embeddings are cached in RAM.
3. **Vectorized Similarity**: Uses numpy for fast batch cosine similarity.
4. **MPS/CUDA**: Automatically uses GPU if available.

---

## Next Steps

- [Configuration](configuration.md) - Customize paths and models
- [Error Codes](error-codes.md) - Troubleshoot issues

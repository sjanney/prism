# Prism CLI Usage Guide

## Quick Start

The CLI tool is located in `cli/main.py` and can be run using Python's module syntax.

### Basic Command Format

```bash
.venv/bin/python3 -m cli.main [COMMAND] [OPTIONS]
```

## Available Commands

### 1. Initialize Database

Creates the SQLite database and required tables.

```bash
.venv/bin/python3 -m cli.main init
```

**When to use:** Run this once before first ingestion, or if you need to reset the database.

---

### 2. Ingest Dataset

Loads frames from a nuScenes dataset directory and indexes them in the database.

```bash
.venv/bin/python3 -m cli.main ingest --path data/nuscenes
```

**Options:**
- `--path` / `-p` (required): Path to nuScenes dataset directory

**Example:**
```bash
.venv/bin/python3 -m cli.main ingest --path data/nuscenes
```

**What it does:**
- Parses nuScenes metadata JSON files
- Extracts camera frames (key frames only)
- Indexes frames with metadata (timestamp, camera angle, weather, GPS)
- Skips duplicates automatically
- Shows progress bar during indexing

**Note:** The ingestion process is optimized to check for duplicates efficiently, so re-running on the same dataset is fast.

---

### 3. Search Dataset

Performs semantic search on the indexed dataset using natural language queries.

```bash
.venv/bin/python3 -m cli.main search "your query here" [OPTIONS]
```

**Options:**
- `--save` / `-s` (optional): Save results as a collection with this name
- `--limit` / `-l` (optional): Maximum number of results (default: 50)

**Examples:**

Basic search:
```bash
.venv/bin/python3 -m cli.main search "car on the road"
```

Search with limit:
```bash
.venv/bin/python3 -m cli.main search "pedestrian crossing" --limit 10
```

Search and save as collection:
```bash
.venv/bin/python3 -m cli.main search "rainy weather" --save "rainy_scenes" --limit 20
```

**What it does:**
- Loads all frames from the database
- Uses CLIP model to compute semantic similarity between query and frames
- Returns results sorted by confidence score
- Displays results in a formatted table
- Optionally saves results as a collection for later reference

**Note:** The first search may take longer as the CLIP model loads. Subsequent searches are faster.

---

## Example Workflow

### Complete workflow from scratch:

```bash
# 1. Initialize database
.venv/bin/python3 -m cli.main init

# 2. Ingest dataset
.venv/bin/python3 -m cli.main ingest --path data/nuscenes

# 3. Search for specific scenarios
.venv/bin/python3 -m cli.main search "vehicle in intersection" --limit 10

# 4. Save interesting results
.venv/bin/python3 -m cli.main search "night time driving" --save "night_scenes" --limit 25
```

---

## Tips

1. **First-time setup:** Always run `init` before your first `ingest`
2. **Re-ingestion:** Safe to run `ingest` multiple times - duplicates are automatically skipped
3. **Search performance:** First search loads CLIP model (~30 seconds), subsequent searches are faster
4. **Query examples:**
   - "car on highway"
   - "pedestrian crossing street"
   - "rainy weather"
   - "vehicle turning left"
   - "traffic light"
   - "parked cars"
   - "construction zone"

---

## Troubleshooting

### "No frames found in database"
- Run `ingest` first to index frames

### "Dataset not found"
- Check that the path to your nuScenes dataset is correct
- Ensure the dataset has the expected structure: `data/sets/nuscenes/v1.0-mini/`

### Search takes a long time
- First search loads the CLIP model (one-time cost)
- Large databases (10k+ frames) may take 1-2 minutes per search
- This is normal - CLIP processes each frame

### "Module not found" errors
- Ensure your virtual environment is activated: `.venv/bin/activate`
- Or use the full path: `.venv/bin/python3 -m cli.main ...`


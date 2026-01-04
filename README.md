# Prism - Semantic Search for Autonomous Vehicle Data

Semantic search platform that lets AV teams query their driving data using natural language, powered by CLIP (Contrastive Language-Image Pre-training).

## Quick Start

**New to Prism?** See [QUICKSTART.md](QUICKSTART.md) for a step-by-step guide.

### 1. Install Dependencies

**Backend:**
```bash
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend && npm install && cd ..
```

### 2. Initialize Database

```bash
python -m cli.main init
```

### 3. Get Test Data

Download nuScenes mini dataset (see [QUICKSTART.md](QUICKSTART.md) for details):
```bash
./scripts/setup_test_data.sh
```

### 4. Ingest Dataset

```bash
python -m cli.main ingest --path data/nuscenes
```

### 5. Start Servers

**Option A: Use startup script**
```bash
./scripts/start_dev.sh
```

**Option B: Manual start**

Terminal 1 (Backend):
```bash
uvicorn backend.api:app --reload --port 8000
```

Terminal 2 (Frontend):
```bash
cd frontend && npm run dev
```

### 6. Access Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Project Structure

```
.
├── backend/          # Core backend logic
│   ├── api.py        # FastAPI application
│   ├── database.py   # Database setup
│   ├── ingestion.py  # Dataset loaders
│   ├── models.py     # SQLAlchemy models
│   └── search_engine.py  # CLIP semantic search
├── cli/              # Command-line interface
│   └── main.py       # Click CLI commands
├── data/             # Dataset storage (user-provided)
├── requirements.txt  # Python dependencies
└── TESTING.md        # Comprehensive testing guide
```

## Features

- **Semantic Search**: Natural language queries using CLIP (no API keys required)
- **Dataset Support**: nuScenes dataset loader (extensible to others)
- **CLI Tool**: Command-line interface for data engineers
- **REST API**: FastAPI endpoints for web integration
- **Collections**: Save and version control search results
- **Export**: CSV and JSON export formats

## CLI Commands

```bash
# Initialize database
python -m cli.main init

# Ingest dataset
python -m cli.main ingest --path /path/to/nuscenes

# Search
python -m cli.main search "query here"

# Search and save collection
python -m cli.main search "query" --save "CollectionName"
```

## API Endpoints

Start the server:
```bash
uvicorn backend.api:app --reload
```

- `POST /search` - Create search job
- `GET /search/{job_id}` - Poll for results
- `POST /collections` - Save collection
- `GET /collections` - List collections
- `GET /export/{id}?format=csv|json` - Export collection
- `GET /thumbnails/{frame_id}` - Get thumbnail image

See `TESTING.md` for detailed API examples.

## Testing

See [TESTING.md](TESTING.md) for comprehensive testing instructions.

Quick test:
```bash
./test_quick.sh
```

## Requirements

- Python 3.10+
- nuScenes dataset (mini split sufficient for testing)
- ~2GB disk space for dependencies (includes CLIP model)
- PostgreSQL (optional, SQLite used by default for development)

## License

MIT

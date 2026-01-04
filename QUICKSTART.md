# Prism Quick Start Guide

Get Prism up and running in 5 minutes!

## Prerequisites

- Python 3.10+
- Node.js 18+ (for frontend)
- ~5GB free disk space (for dataset + dependencies)

## Step 1: Install Dependencies

### Backend
```bash
pip install -r requirements.txt
```

### Frontend
```bash
cd frontend
npm install
cd ..
```

## Step 2: Initialize Database

```bash
python -m cli.main init
```

## Step 3: Get Test Data

The nuScenes mini dataset is required for testing. You have two options:

### Option A: Use Setup Script (Recommended)
```bash
./scripts/setup_test_data.sh
```

This will guide you through downloading the dataset.

### Option B: Manual Download

1. Visit https://www.nuscenes.org/download
2. Create a free account
3. Download "nuScenes mini" (v1.0-mini) - ~3.3GB
4. Extract the archive
5. Move contents to `data/nuscenes/` so the structure is:
   ```
   data/nuscenes/
     ├── data/sets/nuscenes/v1.0-mini/
     │   ├── scene.json
     │   ├── sample.json
     │   ├── sample_data.json
     │   └── log.json
     └── samples/ (camera images)
   ```

## Step 4: Ingest Dataset

```bash
python -m cli.main ingest --path data/nuscenes
```

This will index all frames in the database. Expect ~400 frames for the mini dataset.

## Step 5: Start Servers

### Option A: Use Startup Script (Recommended)
```bash
./scripts/start_dev.sh
```

This starts both backend and frontend automatically.

### Option B: Manual Start

**Terminal 1 - Backend:**
```bash
uvicorn backend.api:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

## Step 6: Access the Application

- **Frontend UI**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Testing

### Test via CLI
```bash
python -m cli.main search "pedestrians"
```

### Test via Web UI
1. Open http://localhost:3000
2. Enter a search query like "pedestrians" or "vehicles"
3. Adjust confidence threshold (default: 25%)
4. Click "Search"
5. View results in the thumbnail grid

## Troubleshooting

### Backend won't start
- Check if port 8000 is already in use: `lsof -i :8000`
- Ensure database is initialized: `python -m cli.main init`

### Frontend can't connect to backend
- Ensure backend is running on port 8000
- Check browser console for CORS errors
- Verify `frontend/vite.config.ts` proxy settings

### No search results
- Ensure dataset is ingested: `python -m cli.main ingest --path data/nuscenes`
- Try lowering the confidence threshold
- Check backend logs for errors

### Dataset not found
- Verify dataset path structure matches expected format
- Check that `scene.json` exists at: `data/nuscenes/data/sets/nuscenes/v1.0-mini/scene.json`

## Next Steps

- Read [README.md](README.md) for full documentation
- Check [TESTING.md](TESTING.md) for detailed testing instructions
- Explore the API at http://localhost:8000/docs


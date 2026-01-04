# Prism Testing Guide

This guide will help you test the Prism semantic search system.

## Prerequisites

1. **Python 3.10+** installed
2. **nuScenes dataset** (mini split is sufficient for testing)
3. **Google Gemini API key** (for VLM search)

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up API Key

Create a `.env` file in the project root:

```bash
echo "GEMINI_API_KEY=your_api_key_here" > .env
```

Or set as environment variable:
```bash
export GEMINI_API_KEY=your_api_key_here
```

### 3. Download nuScenes Dataset (Mini Split)

For testing, the nuScenes mini split is sufficient (~400 frames):

```bash
# Download from nuScenes website
# Extract to data/nuscenes/ directory
# Structure should be:
# data/nuscenes/
#   ├── data/sets/nuscenes/v1.0-mini/
#   │   ├── scene.json
#   │   ├── sample.json
#   │   ├── sample_data.json
#   │   └── log.json
#   └── samples/ (camera images)
```

## Testing the CLI

### Step 1: Initialize Database

```bash
python -m cli.main init
```

Expected output:
```
✓ Database initialized successfully!
```

### Step 2: Ingest Dataset

```bash
python -m cli.main ingest --path data/nuscenes
```

Expected output:
```
Ingesting dataset from: data/nuscenes
Loading metadata...
Loaded 400 frames
Indexing frames...
✓ Successfully indexed 400 frames!
```

### Step 3: Run a Search

```bash
python -m cli.main search "pedestrians"
```

This will:
1. Load frames from database
2. Run CLIP pre-filtering
3. Verify with Gemini Vision API
4. Display results in a table

Expected output:
```
Searching for: 'pedestrians'
Loaded 400 frames from database
Running semantic search (this may take a few minutes)...
┌──────────┬────────────┬─────────────────────┬──────────┬──────────┬──────────────┐
│ Frame ID │ Confidence │ Timestamp           │ Camera   │ Weather  │ Path         │
├──────────┼────────────┼─────────────────────┼──────────┼──────────┼──────────────┤
│ 123      │ 92.5%      │ 2024-03-15T22:34:12 │ FRONT    │ clear    │ samples/...  │
└──────────┴────────────┴─────────────────────┴──────────┴──────────┴──────────────┘
Found 5 matches
```

### Step 4: Save a Collection

```bash
python -m cli.main search "pedestrians" --save "PedestrianCollection"
```

This will save the search results as a named collection.

## Testing the API

### Step 1: Start the API Server

```bash
uvicorn backend.api:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

### Step 2: Check Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy", "timestamp": "2024-01-03T10:00:00"}
```

### Step 3: Create a Search Job

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "pedestrians at night",
    "max_results": 50,
    "confidence_threshold": 70.0
  }'
```

Expected response:
```json
{
  "job_id": "abc-123-def",
  "status": "processing",
  "estimated_time_seconds": 120,
  "poll_url": "/search/abc-123-def"
}
```

### Step 4: Poll for Results

```bash
curl "http://localhost:8000/search/abc-123-def"
```

While processing:
```json
{
  "job_id": "abc-123-def",
  "status": "processing",
  "progress": {
    "frames_processed": 50,
    "frames_total": 400,
    "matches_found": 0
  }
}
```

When complete:
```json
{
  "job_id": "abc-123-def",
  "status": "complete",
  "progress": {
    "frames_processed": 400,
    "frames_total": 400,
    "matches_found": 5
  },
  "results": [
    {
      "frame_id": 123,
      "confidence": 92.5,
      "timestamp": "2024-03-15T22:34:12Z",
      "thumbnail_url": "/thumbnails/123",
      "metadata": {
        "gps": [42.3601, -71.0589],
        "weather": "clear",
        "camera_angle": "FRONT"
      }
    }
  ]
}
```

### Step 5: Save a Collection

```bash
curl -X POST "http://localhost:8000/collections" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Night Pedestrians",
    "query": "pedestrians at night",
    "result_ids": [123, 456, 789],
    "metadata": {
      "avg_confidence": 85.5,
      "total_results": 3
    }
  }'
```

### Step 6: List Collections

```bash
curl "http://localhost:8000/collections"
```

### Step 7: Export Collection

**CSV Export:**
```bash
curl "http://localhost:8000/export/{collection_id}?format=csv" -o export.csv
```

**JSON Export:**
```bash
curl "http://localhost:8000/export/{collection_id}?format=json" -o export.json
```

### Step 8: Get Thumbnail

```bash
curl "http://localhost:8000/thumbnails/123" -o thumbnail.jpg
```

## Testing Checklist

### CLI Testing
- [ ] `init` command creates database
- [ ] `ingest` command loads frames from nuScenes
- [ ] `search` command returns results
- [ ] `search --save` creates collection
- [ ] Progress bars display correctly
- [ ] Error messages are clear

### API Testing
- [ ] Health endpoint responds
- [ ] POST /search creates job
- [ ] GET /search/{job_id} returns status
- [ ] Search job completes successfully
- [ ] POST /collections saves collection
- [ ] GET /collections lists collections
- [ ] GET /export/{id}?format=csv downloads CSV
- [ ] GET /export/{id}?format=json downloads JSON
- [ ] GET /thumbnails/{id} serves image

### Integration Testing
- [ ] CLI ingest → API search works
- [ ] API search → save collection → export works
- [ ] Thumbnails load correctly
- [ ] CSV export has correct columns
- [ ] JSON export matches schema

## Troubleshooting

### Database Issues
```bash
# If database is corrupted, delete and reinitialize
rm prism.db
python -m cli.main init
```

### API Key Issues
- Verify `.env` file exists and has correct key
- Check environment variable: `echo $GEMINI_API_KEY`
- Ensure key has Gemini Vision API access enabled

### Missing Frames
- Verify nuScenes dataset path is correct
- Check that `samples/` directory contains images
- Ensure frame paths in database match actual file locations

### Search Takes Too Long
- CLIP pre-filtering reduces API calls by ~90%
- For testing, use smaller dataset (nuScenes mini)
- Check Gemini API quota/rate limits

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

## Performance Benchmarks

Expected performance on nuScenes mini (400 frames):
- **CLIP pre-filtering**: ~5-10 seconds
- **Gemini verification** (top 10%): ~20-40 seconds
- **Total search time**: ~30-50 seconds

For full dataset (40,000 frames):
- **CLIP pre-filtering**: ~2-3 minutes
- **Gemini verification** (top 10%): ~5-10 minutes
- **Total search time**: ~7-13 minutes

## Next Steps

Once basic testing passes:
1. Test with different query types
2. Test error handling (invalid queries, missing data)
3. Test with larger datasets
4. Verify export formats are correct
5. Test thumbnail serving performance


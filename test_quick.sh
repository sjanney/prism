#!/bin/bash
# Quick test script for Prism

set -e

echo "🧪 Prism Quick Test Script"
echo "============================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found. Create one with GEMINI_API_KEY"
    echo "   Example: echo 'GEMINI_API_KEY=your_key' > .env"
    echo ""
fi

# Check Python version
echo "📋 Checking Python version..."
python3 --version
echo ""

# Check if database exists
if [ ! -f prism.db ]; then
    echo "🗄️  Initializing database..."
    python3 -m cli.main init
    echo ""
fi

# Check if data directory exists
if [ ! -d "data/nuscenes" ]; then
    echo "⚠️  Warning: data/nuscenes directory not found"
    echo "   Please download nuScenes mini dataset and extract to data/nuscenes/"
    echo "   Then run: python3 -m cli.main ingest --path data/nuscenes"
    echo ""
    exit 1
fi

# Test database connection
echo "✅ Database initialized"
echo ""

# Test API server (in background)
echo "🚀 Starting API server..."
uvicorn backend.api:app --port 8000 &
API_PID=$!
sleep 3

# Test health endpoint
echo "🏥 Testing health endpoint..."
curl -s http://localhost:8000/health | python3 -m json.tool
echo ""

# Cleanup
echo "🛑 Stopping API server..."
kill $API_PID 2>/dev/null || true

echo ""
echo "✅ Quick test complete!"
echo ""
echo "Next steps:"
echo "  1. Run: python3 -m cli.main ingest --path data/nuscenes"
echo "  2. Run: python3 -m cli.main search 'pedestrians'"
echo "  3. Start API: uvicorn backend.api:app --reload"


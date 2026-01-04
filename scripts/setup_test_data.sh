#!/bin/bash
# Setup script for Prism test data
# Downloads nuScenes mini dataset for testing

set -e

echo "🔧 Prism Test Data Setup"
echo "=========================="
echo ""

DATA_DIR="data/nuscenes"
MINI_DIR="$DATA_DIR/data/sets/nuscenes/v1.0-mini"

# Check if data already exists
if [ -d "$MINI_DIR" ] && [ -f "$MINI_DIR/scene.json" ]; then
    echo "✅ nuScenes mini dataset already exists at $MINI_DIR"
    echo "   Skipping download..."
    exit 0
fi

echo "📦 This script will help you download the nuScenes mini dataset"
echo ""
echo "The nuScenes mini dataset is ~3.3GB and contains:"
echo "  - 10 scenes"
echo "  - ~400 camera frames"
echo "  - Perfect for testing"
echo ""

# Check for required tools
if ! command -v wget &> /dev/null && ! command -v curl &> /dev/null; then
    echo "❌ Error: wget or curl is required to download the dataset"
    exit 1
fi

# Create data directory
mkdir -p "$DATA_DIR"

echo "📥 Downloading nuScenes mini dataset..."
echo ""
echo "⚠️  Note: You need to:"
echo "   1. Create a free account at https://www.nuscenes.org/"
echo "   2. Download the 'nuScenes mini' dataset"
echo "   3. Extract it to $DATA_DIR/"
echo ""
echo "Expected structure after extraction:"
echo "  $DATA_DIR/"
echo "    ├── data/sets/nuscenes/v1.0-mini/"
echo "    │   ├── scene.json"
echo "    │   ├── sample.json"
echo "    │   ├── sample_data.json"
echo "    │   └── log.json"
echo "    └── samples/ (camera images)"
echo ""

read -p "Have you downloaded and extracted the dataset? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "📋 Manual download instructions:"
    echo "   1. Visit: https://www.nuscenes.org/download"
    echo "   2. Sign up for a free account"
    echo "   3. Download 'nuScenes mini' (v1.0-mini)"
    echo "   4. Extract the archive"
    echo "   5. Move the contents to $DATA_DIR/"
    echo ""
    echo "   The extracted folder should contain 'data' and 'samples' directories"
    echo "   Move them so the structure matches: $DATA_DIR/data/ and $DATA_DIR/samples/"
    echo ""
    exit 0
fi

# Verify structure
if [ ! -f "$MINI_DIR/scene.json" ]; then
    echo "❌ Error: Dataset not found at expected location"
    echo "   Expected: $MINI_DIR/scene.json"
    echo ""
    echo "Please ensure the dataset is extracted correctly."
    echo "The structure should be:"
    echo "  $DATA_DIR/data/sets/nuscenes/v1.0-mini/scene.json"
    exit 1
fi

echo ""
echo "✅ Dataset found!"
echo ""
echo "Next steps:"
echo "  1. Initialize database: python -m cli.main init"
echo "  2. Ingest dataset: python -m cli.main ingest --path $DATA_DIR"
echo "  3. Start backend: uvicorn backend.api:app --reload"
echo "  4. Start frontend: cd frontend && npm run dev"
echo ""


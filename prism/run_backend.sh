#!/bin/bash
set -e

# Ensure strict python usage
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

echo "--- 📦 Installing Dependencies ---"
$PYTHON_CMD -m pip install -r prism/backend/requirements.txt

echo "--- 🔄 Generatng Code ---"
./prism/codegen.sh

echo "--- 🚀 Starting Backend Server ---"
echo "Server running on port 50051. Press Ctrl+C to stop."
$PYTHON_CMD prism/backend/server.py

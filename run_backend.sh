#!/bin/bash
set -e

# Ensure strict python usage
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

# We assume dependencies are installed via Makefile or install script for production
# But we keep a check for the core file existence
if [ ! -f "backend/server.py" ]; then
    echo "Error: backend/server.py not found. Please run from project root."
    exit 1
fi

echo "--- 🔄 Generating Code ---"
./codegen.sh

echo "--- 🚀 Starting Backend Server ---"
$PYTHON_CMD backend/server.py

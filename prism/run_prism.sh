#!/bin/bash
set -e

# Ensure we are in the project root (parent of this script)
cd "$(dirname "$0")/.."

# Kill any existing backend process on port 50051
lsof -ti:50051 | xargs kill -9 2>/dev/null || true

# Start Backend in Background (Suppressed Output)
./prism/run_backend.sh > backend.log 2>&1 &
BACKEND_PID=$!

# Trap Ctrl+C to kill backend
trap "kill $BACKEND_PID 2>/dev/null" EXIT INT TERM

# Start Frontend immediately (It handles connecting spinner)
./prism/run_frontend.sh


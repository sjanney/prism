#!/bin/bash
set -e

# Ensure we are in the project root
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# Kill any existing backend process on port 50051
lsof -ti:50051 | xargs kill -9 2>/dev/null || true

# Start Backend in Background (Suppressed Output)
# Ensure requirements are met (optional check here or in install)
./run_backend.sh > backend.log 2>&1 &
BACKEND_PID=$!

# Trap Ctrl+C to kill backend
trap "kill $BACKEND_PID 2>/dev/null" EXIT INT TERM

# Start Frontend immediately
./run_frontend.sh


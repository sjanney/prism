#!/bin/bash
# Development startup script for Prism
# Starts both backend and frontend servers

set -e

echo "🚀 Starting Prism Development Servers"
echo "========================================"
echo ""

# Check if backend dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "❌ Backend dependencies not installed"
    echo "   Run: pip install -r requirements.txt"
    exit 1
fi

# Check if database is initialized
if [ ! -f "prism.db" ]; then
    echo "⚠️  Database not initialized. Initializing now..."
    python -m cli.main init
    echo ""
fi

# Check if frontend dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo "⚠️  Frontend dependencies not installed"
    echo "   Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
    echo ""
fi

# Start backend in background
echo "🔧 Starting backend server on http://localhost:8000"
uvicorn backend.api:app --reload --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Check if backend started successfully
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ Backend failed to start"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

echo "✅ Backend server running (PID: $BACKEND_PID)"
echo ""

# Start frontend
echo "🎨 Starting frontend server on http://localhost:3000"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Both servers are running!"
echo ""
echo "📍 URLs:"
echo "   Frontend: http://localhost:3000"
echo "   Backend API: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "🛑 To stop servers, press Ctrl+C or run:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo ""

# Wait for user interrupt
trap "echo ''; echo '🛑 Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

wait


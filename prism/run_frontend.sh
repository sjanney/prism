#!/bin/bash

# Ensure we are in the project root
cd "$(dirname "$0")"

echo "--- 🚀 Launching Prism TUI ---"
cd frontend
go run .

#!/bin/bash
cd "$(dirname "$0")/backend"
source ~/.venv/bin/activate 2>/dev/null || python3 -m venv ~/.venv && source ~/.venv/bin/activate
pip install -q -r requirements.txt 2>/dev/null || true
python server.py

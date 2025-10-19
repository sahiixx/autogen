#!/bin/bash

# Start AutoGen Studio
cd /workspace/python

# Activate virtual environment
export PATH="$HOME/.local/bin:$PATH"
source .venv/bin/activate

# Start the server
echo "Starting AutoGen Studio on http://localhost:8081"
echo "Press Ctrl+C to stop the server"
autogenstudio ui --host 0.0.0.0 --port 8081

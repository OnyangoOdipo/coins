#!/usr/bin/env bash

# Navigate to the backend directory
cd "$(dirname "$0")/backend" || exit 1

# Activate the virtual environment
if [ -f venv/bin/activate ]; then
    # shellcheck disable=SC1091
    source venv/bin/activate
else
    echo "Virtual environment not found. Please create one first."
    exit 1
fi

# Start the FastAPI server with uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

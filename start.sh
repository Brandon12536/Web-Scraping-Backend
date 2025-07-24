#!/bin/bash

# Set default port if not provided
PORT=${PORT:-8000}

# Check if running in a Docker container
if [ -f /.dockerenv ] || [ -f /run/.containerenv ]; then
    echo "Running inside a Docker container"
    
    # Install any additional system dependencies if needed
    # apt-get update && apt-get install -y --no-install-recommends some-dependency
    
    # Run database migrations if needed
    # python -m alembic upgrade head
    
    # Start the application
    exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2
else
    echo "Running in development mode"
    
    # Use the Python from the virtual environment
    if [ -d "venv" ]; then
        source venv/bin/activate
    elif [ -d ".venv" ]; then
        source .venv/bin/activate
    fi
    
    # Install dependencies if needed
    pip install -r requirements.txt
    
    # Start the application with auto-reload for development
    exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --reload
fi

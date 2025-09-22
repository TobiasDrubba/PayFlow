#!/bin/bash

# WeAli Payment Overview Startup Script
echo "Starting WeAli Payment Overview..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create data directory
mkdir -p data

# Run the application
echo "Starting FastAPI server..."
python main.py
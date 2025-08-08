#!/bin/bash

# Check if database exists
if [ ! -f "../data-prep/perseus_texts_full.db" ]; then
    echo "Error: Database file not found at ../data-prep/perseus_texts_full.db"
    echo "Please ensure the database has been created before running the web app."
    exit 1
fi

echo "Starting Classics Viewer Web App..."
echo "The app will be available at http://localhost:3000"
echo ""

# Build and run with docker-compose
docker-compose up --build

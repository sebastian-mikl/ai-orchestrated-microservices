#!/bin/bash

# Setup script for "The Network" proof of concept

echo "Setting up The Network - 3 Node Proof of Concept"



# Create node directories
mkdir -p nodes/echo-node
mkdir -p nodes/transform-node
mkdir -p nodes/storage-node
mkdir -p orchestrator

# Copy requirements.txt to each directory
cp requirements.txt nodes/echo-node/
cp requirements.txt nodes/transform-node/
cp requirements.txt nodes/storage-node/
cp requirements.txt orchestrator/

# Copy Dockerfile to each directory
cp Dockerfile nodes/echo-node/
cp Dockerfile nodes/transform-node/
cp Dockerfile nodes/storage-node/
cp Dockerfile orchestrator/

# Copy app files (you'll need to copy the app.py files manually)
echo "📁 Directory structure created!"
echo ""
echo "Next steps:"
echo "1. Copy the app.py files to their respective directories:"
echo "   - echo-node/app.py"
echo "   - transform-node/app.py"
echo "   - storage-node/app.py"
echo "   - orchestrator/app.py"
echo ""
echo "2. Run: docker-compose up --build"
echo ""
echo "3. Test the network:"
echo "   curl http://localhost:8000/nodes"
echo "   curl -X POST http://localhost:8000/test"

# Make the script executable
chmod +x setup.sh
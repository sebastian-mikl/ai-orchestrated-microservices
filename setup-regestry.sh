#!/bin/bash

# Setup script for Service Registry

echo "Setting up Service Registry with LangChain RAG orchestration"

# Create service registry directory
mkdir -p service-registry

# Copy requirements and Dockerfile
cp requirements.txt service-registry/
cp Dockerfile service-registry/

# Create environment file for API keys
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOF
CLAUDE_API_KEY=your_claude_api_key_here
EOF
    echo "Please edit .env file with your actual Claude API key"
fi

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your Claude API key"
echo "2. Copy the service-registry app.py file"
echo "3. Run: docker-compose down && docker-compose up --build"
echo "4. Test with: ./test_registry.sh"
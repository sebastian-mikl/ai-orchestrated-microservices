# AI-Orchestrated Microservices

A distributed microservice platform that uses AI-powered natural language processing to dynamically orchestrate service workflows. Built with LangChain, Docker, and Claude API for intelligent service composition.

## Overview

This system transforms natural language commands into executable microservice workflows. Instead of manually coding service integrations, users can describe what they want in plain English and the system automatically discovers, chains, and executes the appropriate services.

**Example:**
```
Input: "transform this text to uppercase and store it"
System: Discovers transform-node and storage-node, skips unnecessary echo-node
Output: "hello world" → "HELLO WORLD" → stored with ID item_123
```

## Architecture

The platform consists of containerized microservices that communicate through a central AI-powered registry:

```
User Command → Service Registry (AI Orchestrator) → Optimal Service Chain
                        ↓
              [Echo Node] [Transform Node] [Storage Node]
```

### Core Components

- **Service Registry**: LangChain-powered RAG system for service discovery and orchestration
- **Echo Node**: Data passthrough service for workflow connectivity
- **Transform Node**: Text processing service (uppercase transformation)
- **Storage Node**: Persistent data storage with retrieval capabilities
- **Original Orchestrator**: Fallback hardcoded workflow coordinator

## Key Features

- **Natural Language Processing**: Convert plain English to executable workflows
- **Intelligent Chain Optimization**: AI skips unnecessary services and optimizes execution paths
- **Semantic Service Discovery**: Vector-based capability matching using FAISS embeddings
- **Auto-Service Registration**: Nodes automatically register their capabilities on startup
- **Pattern-Based Architecture**: 16 fundamental interaction patterns for universal service compatibility
- **Real-time Orchestration**: Sub-second command processing and execution

## Technology Stack

- **Orchestration**: LangChain with Claude 3.5 Sonnet
- **Service Discovery**: FAISS vector database with HuggingFace embeddings
- **Runtime**: Docker Compose with FastAPI microservices
- **Languages**: Python 3.11+
- **APIs**: REST with automatic OpenAPI documentation

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Claude API key from Anthropic
- 8GB+ RAM recommended for vector operations

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/your-username/ai-orchestrated-microservices.git
cd ai-orchestrated-microservices
```

2. **Configure environment**
```bash
cp .env.example .env
# Edit .env and add your Claude API key:
# CLAUDE_API_KEY=your_claude_api_key_here
```

3. **Start the platform**
```bash
docker-compose up --build
```

4. **Verify installation**
```bash
# Check service health
curl http://localhost:8004/health

# List registered services
curl http://localhost:8004/services
```

## Usage Examples

### Basic Service Orchestration
```bash
# Transform and store text
curl -X POST http://localhost:8004/execute \
  -H "Content-Type: application/json" \
  -d '{"command": "make this text uppercase and save it", "data": "hello world"}'
```

### Natural Language Variations
```bash
# All of these work the same way:
"transform text to uppercase and store it"
"I want to make this all caps and then save it"
"convert to uppercase then persist the data"
"make it ALL CAPS and store the result"
```

### Service Discovery
```bash
# Find services for text processing
curl "http://localhost:8004/services/search/transform%20text"

# Find storage capabilities
curl "http://localhost:8004/services/search/save%20data"
```

### Check Results
```bash
# View stored data
curl http://localhost:8003/storage/list
```

## API Endpoints

### Service Registry (Port 8004)
- `GET /health` - System health check
- `GET /services` - List all registered services
- `GET /services/search/{query}` - Semantic service search
- `POST /orchestrate` - Generate execution plan only
- `POST /execute` - Generate and execute workflow
- `POST /register` - Register new service

### Individual Services
- **Echo Node (8001)**: Simple data passthrough
- **Transform Node (8002)**: Text transformation operations
- **Storage Node (8003)**: Persistent data storage
- **Original Orchestrator (8000)**: Fallback hardcoded workflows

## Development

### Adding New Services

Services auto-register by implementing the standard interface:

```python
@app.get("/info")
async def node_info():
    return {
        "node_id": "my-service",
        "capabilities": ["capability1", "capability2"],
        "description": "What this service does",
        "input_format": "expected_input_type",
        "output_format": "output_type"
    }

@app.post("/process")
async def process_data(request: NodeRequest):
    # Process the data
    return NodeResponse(data=result, status="success")
```

### Testing

Run the test suite to verify functionality:

```bash
chmod +x test_registry.sh
./test_registry.sh
```

### Architecture Patterns

The system supports 16 fundamental interaction patterns:

**Data Patterns**: Synchronous, Asynchronous, Streaming, Event-Driven
**State Patterns**: Stateless, Session-Based, Persistent, Shared-State

Services declare their pattern (e.g., `synchronous_stateless`) for proper orchestration.

## Performance

- **Chain Generation**: Sub-second command processing
- **Service Discovery**: Vector search across service capabilities
- **Confidence Scoring**: AI-generated confidence levels for execution plans
- **Auto-Optimization**: Removes unnecessary services from workflows

## Project Status

### Current Capabilities
- ✅ Working AI orchestration with natural language commands
- ✅ Automatic service discovery and registration
- ✅ Optimized workflow generation
- ✅ Docker containerization with health monitoring
- ✅ RESTful API with auto-documentation

### Planned Features
- 🔄 Full 16-pattern interface implementation
- 🔄 Kubernetes deployment
- 🔄 Multi-modal data support (images, files, streams)
- 🔄 Advanced error recovery and circuit breakers
- 🔄 Cross-service transaction management

## Use Cases

- **DevOps Automation**: "deploy this app with monitoring and logging"
- **Data Pipeline Creation**: "process these CSV files and generate reports"
- **API Workflow Composition**: "get data from service A, transform it, send to service B"
- **Dynamic Application Assembly**: Build applications from existing service components

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add your service following the standard interface
4. Test with the existing orchestration system
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Contact

For questions about this project or collaboration opportunities, please open an issue or contact [your-email].

---

This project demonstrates modern distributed systems architecture with AI-powered orchestration, showcasing skills in Docker, microservices, LangChain, vector databases, and natural language processing.
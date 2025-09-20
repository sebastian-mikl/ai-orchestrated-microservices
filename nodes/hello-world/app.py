# nodes/hello-world/app.py

from fastapi import FastAPI
from pydantic import BaseModel
import requests
import asyncio
import time
from contextlib import asynccontextmanager
from typing import Optional

# Replace the lifespan function in hello-world with this threading approach:

import threading


def delayed_registration():
    """Run registration in a separate thread after server starts"""
    time.sleep(5)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(register_with_service_registry())
    loop.close()


async def register_with_service_registry():
    """Register this service with the service registry"""
    try:
        await asyncio.sleep(5)

        info_response = requests.get("http://localhost:8000/info", timeout=5)
        if info_response.status_code == 200:
            info_data = info_response.json()

            registration_data = {
                "node_id": info_data["node_id"],
                "url": f"http://{info_data['node_id']}:8000",
                "capabilities": [
                    {
                        "name": cap,
                        "description": f"Service capability: {cap}",
                        "input_format": info_data.get("input_format", "string"),
                        "output_format": info_data.get("output_format", "string"),
                        "examples": []
                    } for cap in info_data.get("capabilities", [])
                ],
                "description": info_data.get("description", "Hello World service"),
                "tags": info_data.get("tags", []),
                "interaction_patterns": info_data.get("interaction_patterns", [])
            }

            registry_response = requests.post(
                "http://service-registry:8000/register",
                json=registration_data,
                timeout=10
            )

            if registry_response.status_code == 200:
                print("Successfully registered hello-world with service registry")
            else:
                print(f"Failed to register: {registry_response.status_code}")

    except Exception as e:
        print(f"Registration failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Hello World service starting up...")
    registration_thread = threading.Thread(target=delayed_registration, daemon=True)
    registration_thread.start()
    yield
    print("Hello World service shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Hello World Service",
    description="Simple greeting service for testing",
    lifespan=lifespan
)


# Models
class NodeRequest(BaseModel):
    data: str
    next_node: Optional[str] = None
    metadata: dict = {}


class NodeResponse(BaseModel):
    node_id: str = "hello-world"
    data: str
    status: str
    metadata: dict = {}


# Endpoints
@app.get("/health")
async def health_check():
    return {"status": "healthy", "node_type": "hello_world"}


@app.get("/info")
async def node_info():
    return {
        "node_id": "hello-world",
        "version": "1.0.0",
        "status": "healthy",
        "description": "Simple hello world service that greets users",
        "capabilities": [
            "greeting",
            "hello_world",
            "simple_response"
        ],
        "tags": ["greeting", "test", "simple"],
        "input_format": "string",
        "output_format": "string",
        "supported_operations": ["greet"],
        "interaction_patterns": ["synchronous_stateless"],
        "pattern_interfaces": {
            "synchronous_stateless": {
                "inputs": {"text": "string"},
                "outputs": {"text": "string"},
                "parameters": {}
            }
        },
        "endpoints": {
            "health": "/health",
            "process": "/process",
            "execute": "/execute",
            "contract": "/contract",
            "info": "/info"
        },
        "dependencies": [],
        "provides_to": ["any"],
        "resource_requirements": {
            "cpu": "low",
            "memory": "10MB",
            "disk": "none"
        },
        "scaling": {
            "can_scale_horizontal": True,
            "max_instances": 100,
            "startup_time": "2s"
        },
        "processing_type": "greeting",
        "data_transformation": "text_greeting",
        "typical_use_cases": [
            "Testing service registration",
            "Simple greetings",
            "System verification"
        ]
    }


@app.get("/contract")
async def get_contract():
    return {
        "service_metadata": {
            "service_id": "hello-world",
            "version": "1.0.0",
            "pattern": "synchronous_stateless",
            "description": "Simple greeting service for testing purposes",
            "maintainer": "system",
            "cost_per_execution": 0.0001
        },
        "interface_contract": {
            "inputs": {
                "text": {
                    "type": "string",
                    "constraints": {
                        "max_length": 1000,
                        "encoding": "utf-8",
                        "required": True
                    },
                    "description": "Input text to create greeting for"
                }
            },
            "outputs": {
                "text": {
                    "type": "string",
                    "constraints": {
                        "encoding": "utf-8"
                    },
                    "description": "Greeting message"
                },
                "metadata": {
                    "type": "object",
                    "properties": {
                        "processed_by": {"type": "string"},
                        "greeting_type": {"type": "string"}
                    }
                }
            }
        },
        "behavioral_guarantees": {
            "deterministic": True,
            "side_effects": False,
            "idempotent": True,
            "data_preservation": "greeting_transformation",
            "execution_safety": "always_safe"
        },
        "resource_requirements": {
            "max_execution_time": "5ms",
            "memory_limit": "5MB",
            "cpu_intensive": False,
            "network_calls": False
        },
        "compatibility_rules": {
            "can_chain_to": ["any"],
            "cannot_chain_to": [],
            "requires_preprocessing": [],
            "output_compatible_with": ["string_consumers"],
            "input_compatible_with": ["string_producers"]
        },
        "error_handling": {
            "failure_modes": ["invalid_input"],
            "recovery_strategy": "default_greeting",
            "rollback_capable": True
        }
    }


@app.post("/process")
async def process_data(request: NodeRequest):
    print(f"Hello World service received: {request.data}")

    # Create greeting
    greeting = f"Hello, {request.data}! Greetings from the Hello World service."

    response = NodeResponse(
        data=greeting,
        status="success",
        metadata={
            "processed_by": "hello-world",
            "pattern_used": "synchronous_stateless",
            "greeting_type": "simple",
            **request.metadata
        }
    )

    return response


@app.post("/execute")
async def execute_greeting(inputs: dict, parameters: dict = {}):
    """Direct pattern-based execution"""
    if "text" not in inputs:
        return {"error": "Missing required input: text", "pattern": "synchronous_stateless"}

    text = inputs["text"]
    greeting = f"Hello, {text}! Greetings from the Hello World service."

    return {
        "outputs": {"text": greeting},
        "metadata": {
            "node_id": "hello-world",
            "pattern": "synchronous_stateless",
            "operation": "greeting",
            "execution_time": "< 1ms"
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
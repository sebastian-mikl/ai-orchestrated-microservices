from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ValidationError
from typing import Dict, Any, Optional, List
import requests

import threading
import asyncio
import time
from contextlib import asynccontextmanager


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
                        "input_format": info_data.get("input_format", "any_data"),
                        "output_format": info_data.get("output_format", "result"),
                        "examples": []
                    } for cap in info_data.get("capabilities", [])
                ],
                "description": info_data.get("description", "Auto-registered service"),
                "tags": info_data.get("tags", []),
                "interaction_patterns": info_data.get("interaction_patterns", [])
            }

            registry_response = requests.post(
                "http://service-registry:8000/register",
                json=registration_data,
                timeout=10
            )

            if registry_response.status_code == 200:
                print(f"Successfully registered echo-node with service registry")
            else:
                print(f"Failed to register: {registry_response.status_code}")

    except Exception as e:
        print(f"Registration failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Echo Node starting up...")
    registration_thread = threading.Thread(target=delayed_registration, daemon=True)
    registration_thread.start()
    yield
    print("Echo Node shutting down...")


app = FastAPI(
    title="echo node",
    description="prints text",
    lifespan=lifespan
)


# Modelsstartup
class NodeRequest(BaseModel):
    data: str
    next_node: Optional[str] = None
    metadata: dict = {}

class NodeResponse(BaseModel):
    node_id: str = "echo-node"
    data: str
    status: str
    metadata: dict = {}

# Endpoints
@app.get("/health")
async def health_check():
    return {"status": "healthy", "node_type": "echo"}

@app.get("/contract")
async def get_contract():
    return {
        "service_metadata": {
            "service_id": "echo-node",
            "version": "1.0.0",
            "pattern": "synchronous_stateless",
            "description": "Passes data through unchanged - useful for testing and debugging chains",
            "maintainer": "system",
            "cost_per_execution": 0.0001
        },
        "interface_contract": {
            "inputs": {
                "text": {
                    "type": "string",
                    "constraints": {
                        "max_length": 100000,
                        "encoding": "utf-8",
                        "required": True
                    },
                    "description": "Any text input that will be echoed unchanged"
                }
            },
            "outputs": {
                "text": {
                    "type": "string",
                    "constraints": {
                        "encoding": "utf-8",
                        "preserves_input": True
                    },
                    "description": "Exact copy of input text"
                },
                "metadata": {
                    "type": "object",
                    "properties": {
                        "processed_by": {"type": "string"},
                        "original_length": {"type": "integer"},
                        "pattern_used": {"type": "string"}
                    }
                }
            }
        },
        "behavioral_guarantees": {
            "deterministic": True,
            "side_effects": False,
            "idempotent": True,
            "data_preservation": "exact_copy",
            "execution_safety": "always_safe"
        },
        "resource_requirements": {
            "max_execution_time": "10ms",
            "memory_limit": "10MB",
            "cpu_intensive": False,
            "network_calls": False
        },
        "compatibility_rules": {
            "can_chain_to": ["any"],
            "cannot_chain_to": [],
            "requires_preprocessing": [],
            "output_compatible_with": ["string_consumers", "text_processors", "storage_services"],
            "input_compatible_with": ["string_producers", "text_generators"]
        },
        "error_handling": {
            "failure_modes": ["network_timeout", "invalid_input"],
            "recovery_strategy": "immediate_retry",
            "rollback_capable": True
        }
    }

@app.get("/info")
async def node_info():
    """Standardized service discovery information for Echo Node"""
    return {
        "node_id": "echo-node",
        "version": "1.0.0",
        "status": "healthy",
        "description": "Receives input and forwards data unchanged - useful for testing and debugging chains",
        "capabilities": [
            "passthrough",
            "echo",
            "forward",
            "receive",
            "chain_testing"
        ],
        "tags": ["utility", "passthrough", "testing", "debugging"],
        "input_format": "string",
        "output_format": "string",
        "supported_operations": ["echo", "passthrough"],
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
            "info": "/info",
            "patterns": "/patterns"
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
        "processing_type": "passthrough",
        "data_transformation": "none",
        "typical_use_cases": [
            "Chain testing",
            "Data forwarding",
            "Workflow debugging",
            "Simple passthrough operations"
        ]
    }

@app.post("/process")
async def process_data(request: NodeRequest):
    print(f"Echo Node received: {request.data}")

    processed_data = request.data

    response = NodeResponse(
        data=processed_data,
        status="success",
        metadata={
            "processed_by": "echo-node",
            "pattern_used": "synchronous_stateless",
            "original_length": len(request.data),
            **request.metadata
        }
    )

    if request.next_node:
        try:
            forward_request = NodeRequest(
                data=processed_data,
                next_node=None,
                metadata=response.metadata
            )

            next_url = f"http://{request.next_node}:8000/process"
            print(f"Forwarding to: {next_url}")

            forward_response = requests.post(
                next_url,
                json=forward_request.model_dump(),
                timeout=10
            )

            if forward_response.status_code == 200:
                return forward_response.json()
            else:
                response.status = "forward_failed"
                response.metadata["forward_error"] = forward_response.text

        except Exception as e:
            print(f"Forward failed: {e}")
            response.status = "forward_failed"
            response.metadata["forward_error"] = str(e)

    return response

@app.post("/execute")
async def execute_synchronous_stateless(inputs: dict, parameters: dict = {}):
    """Direct pattern-based execution for synchronous_stateless"""
    if "text" not in inputs:
        return {"error": "Missing required input: text", "pattern": "synchronous_stateless"}

    text = inputs["text"]

    return {
        "outputs": {"text": text},
        "metadata": {
            "node_id": "echo-node",
            "pattern": "synchronous_stateless",
            "operation": "passthrough",
            "execution_time": "< 1ms"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
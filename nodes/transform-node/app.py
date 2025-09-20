from fastapi import FastAPI
from pydantic import BaseModel
import asyncio
import requests
from contextlib import asynccontextmanager

# Add this to ANY service's app.py (at the top after imports, before app = FastAPI())

import asyncio
import requests
import time
from contextlib import asynccontextmanager

# Add this to ANY service's app.py (at the top after imports, before app = FastAPI())

import asyncio
import requests
import time
from contextlib import asynccontextmanager

# At the top of transform-node app.py, replace everything before class NodeRequest with:

from fastapi import FastAPI
from pydantic import BaseModel
import requests
import asyncio
import time
from contextlib import asynccontextmanager


async def register_with_service_registry():
    """Register this service with the service registry"""
    try:
        for i in range(30):
            try:
                response = requests.get("http://service-registry:8000/health", timeout=5)
                if response.status_code == 200:
                    print("Service registry is ready")
                    break
            except:
                pass
            print(f"Waiting for service registry... ({i + 1}/30)")
            await asyncio.sleep(2)
        else:
            print("WARNING: Service registry not available")
            return False

        await asyncio.sleep(5)

        info_response = requests.get("http://localhost:8000/info", timeout=5)
        if info_response.status_code != 200:
            print(f"Failed to get service info: {info_response.status_code}")
            return False

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
            "description": info_data.get("description", "Transform service"),
            "tags": info_data.get("tags", []),
            "interaction_patterns": info_data.get("interaction_patterns", [])
        }

        registry_response = requests.post(
            "http://service-registry:8000/register",
            json=registration_data,
            timeout=10
        )

        if registry_response.status_code == 200:
            print(f"Successfully registered transform-node with service registry")
            return True
        else:
            print(f"Failed to register: {registry_response.status_code}")
            return False

    except Exception as e:
        print(f"Registration failed: {e}")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Transform Node starting up...")
    registration_success = await register_with_service_registry()
    if not registration_success:
        print("WARNING: Failed to register")
    yield
    print("Transform Node shutting down...")


app = FastAPI(
    title="Transform Node",
    description="Transforms text data in various ways",
    lifespan=lifespan
)



class NodeRequest(BaseModel):
    data: str
    next_node: str = None
    metadata: dict = {}


class NodeResponse(BaseModel):
    node_id: str = "transform-node"
    data: str
    status: str
    metadata: dict = {}


class PatternCapability(BaseModel):
    pattern_id: str
    inputs: dict
    outputs: dict
    parameters: dict = {}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "node_type": "transform"}


@app.get("/contract")
async def get_contract():
    return {
        "service_metadata": {
            "service_id": "transform-node",
            "version": "1.0.0",
            "pattern": "synchronous_stateless",
            "description": "Transforms text using various string operations",
            "maintainer": "system",
            "cost_per_execution": 0.002
        },
        "interface_contract": {
            "inputs": {
                "text": {
                    "type": "string",
                    "constraints": {
                        "max_length": 10000,
                        "min_length": 1,
                        "encoding": "utf-8",
                        "required": True
                    },
                    "description": "Text to be transformed"
                },
                "operation": {
                    "type": "enum",
                    "values": ["uppercase", "lowercase", "reverse"],
                    "default": "uppercase",
                    "required": False,
                    "description": "Type of transformation to apply"
                }
            },
            "outputs": {
                "text": {
                    "type": "string",
                    "constraints": {
                        "encoding": "utf-8",
                        "preserves_length": "depends_on_operation"
                    },
                    "description": "Transformed text according to specified operation"
                },
                "metadata": {
                    "type": "object",
                    "properties": {
                        "processed_by": {"type": "string"},
                        "pattern_used": {"type": "string"},
                        "transform_info": {
                            "type": "object",
                            "properties": {
                                "original": {"type": "string"},
                                "transformation": {"type": "string"},
                                "length_change": {"type": "integer"}
                            }
                        }
                    }
                }
            }
        },
        "behavioral_guarantees": {
            "deterministic": True,
            "side_effects": False,
            "idempotent": True,
            "data_preservation": "content_preserving",
            "execution_safety": "always_safe"
        },
        "resource_requirements": {
            "max_execution_time": "100ms",
            "memory_limit": "50MB",
            "cpu_intensive": False,
            "network_calls": False
        },
        "compatibility_rules": {
            "can_chain_to": ["storage_services", "text_processors", "validation_services"],
            "cannot_chain_to": ["streaming_services", "binary_processors"],
            "requires_preprocessing": [],
            "output_compatible_with": ["string_consumers", "storage_services"],
            "input_compatible_with": ["string_producers", "text_generators", "echo_services"]
        },
        "capabilities": {
            "transformations": ["uppercase", "lowercase", "reverse"],
            "input_formats": ["plain_text"],
            "output_formats": ["plain_text"],
            "quality_guarantees": ["no_data_loss", "consistent_encoding"]
        },
        "error_handling": {
            "failure_modes": ["invalid_operation", "text_too_long", "encoding_error"],
            "recovery_strategy": "graceful_degradation",
            "rollback_capable": True
        }
    }


# Replace the /info endpoint in nodes/transform-node/app.py

@app.get("/info")
async def node_info():
    """Standardized service discovery information for Transform Node"""
    return {
        # REQUIRED FIELDS
        "node_id": "transform-node",
        "version": "1.0.0",
        "status": "healthy",
        "description": "Transforms text data using various string operations including uppercase, lowercase, and reverse",

        # CAPABILITY DISCOVERY
        "capabilities": [
            "text_transformation",
            "uppercase_conversion",
            "lowercase_conversion",
            "text_reversal",
            "string_manipulation"
        ],
        "tags": ["text", "transformation", "processing", "string"],

        # DATA CONTRACTS
        "input_format": "string",
        "output_format": "string",
        "supported_operations": ["uppercase", "lowercase", "reverse"],

        # INTERACTION PATTERNS
        "interaction_patterns": ["synchronous_stateless"],
        "pattern_interfaces": {
            "synchronous_stateless": {
                "inputs": {"text": "string"},
                "outputs": {"text": "string"},
                "parameters": {
                    "transformation": {
                        "type": "string",
                        "options": ["uppercase", "lowercase", "reverse"],
                        "default": "uppercase"
                    }
                }
            }
        },

        # SERVICE METADATA
        "endpoints": {
            "health": "/health",
            "process": "/process",
            "execute": "/execute",
            "contract": "/contract",
            "info": "/info",
            "patterns": "/patterns"
        },
        "dependencies": [],  # No dependencies
        "provides_to": ["storage-services", "text-processors", "validation-services"],

        # OPERATIONAL INFO
        "resource_requirements": {
            "cpu": "low",
            "memory": "50MB",
            "disk": "none"
        },
        "scaling": {
            "can_scale_horizontal": True,
            "max_instances": 50,
            "startup_time": "3s"
        },

        # PROCESSING CHARACTERISTICS
        "processing_type": "transformation",
        "data_transformation": "text_modification",
        "typical_use_cases": [
            "Text case conversion",
            "String manipulation",
            "Data preprocessing",
            "Format standardization"
        ],
        "performance": {
            "typical_response_time": "< 100ms",
            "max_text_length": 10000,
            "concurrent_requests": 100
        }
    }


@app.get("/patterns")
async def get_supported_patterns():
    """New endpoint to explicitly expose pattern support"""
    return {
        "node_id": "transform-node",
        "supported_patterns": ["synchronous_stateless"],
        "pattern_details": {
            "synchronous_stateless": {
                "description": "Simple transform: input → process → output",
                "interface": "function_call",
                "typical_duration": "seconds",
                "inputs": {"text": "string"},
                "outputs": {"text": "string"},
                "parameters": {
                    "transformation": ["uppercase", "lowercase", "reverse"]
                }
            }
        }
    }


@app.post("/process")
async def process_data(request: NodeRequest):
    print(f"Transform Node received: {request.data}")

    # Extract transformation parameter from metadata if provided
    transformation = request.metadata.get("transformation", "uppercase")

    # Transform the data based on the transformation parameter
    if transformation == "lowercase":
        processed_data = request.data.lower()
    elif transformation == "reverse":
        processed_data = request.data[::-1]
    else:  # default to uppercase
        processed_data = request.data.upper()

    # Add some processing metadata
    transform_info = {
        "original": request.data,
        "transformation": transformation,
        "length_change": len(processed_data) - len(request.data)
    }

    response = NodeResponse(
        data=processed_data,
        status="success",
        metadata={
            "processed_by": "transform-node",
            "pattern_used": "synchronous_stateless",
            "transform_info": transform_info,
            **request.metadata
        }
    )

    # Forward to next node if specified
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
                json=forward_request.dict(),
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


# NEW: Pattern-specific endpoint for synchronous_stateless
@app.post("/execute")
async def execute_synchronous_stateless(
        inputs: dict,
        parameters: dict = {}
):
    """Direct pattern-based execution for synchronous_stateless"""

    if "text" not in inputs:
        return {"error": "Missing required input: text", "pattern": "synchronous_stateless"}

    transformation = parameters.get("transformation", "uppercase")
    text = inputs["text"]

    if transformation == "lowercase":
        result = text.lower()
    elif transformation == "reverse":
        result = text[::-1]
    else:
        result = text.upper()

    return {
        "outputs": {"text": result},
        "metadata": {
            "node_id": "transform-node",
            "pattern": "synchronous_stateless",
            "transformation": transformation,
            "execution_time": "< 1s"
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os

app = FastAPI(title="Echo Node", description="Receives input and can forward to next node")


class NodeRequest(BaseModel):
    data: str
    next_node: str = None
    metadata: dict = {}


class NodeResponse(BaseModel):
    node_id: str = "echo-node"
    data: str
    status: str
    metadata: dict = {}


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
    return {
        "node_id": "echo-node",
        "capabilities": ["receive", "forward", "passthrough"],
        "description": "Echoes input data and forwards to next node",
        "input_format": "string",
        "output_format": "string",
        # NEW: Pattern declaration
        "interaction_patterns": ["synchronous_stateless"],
        "pattern_interfaces": {
            "synchronous_stateless": {
                "inputs": {"text": "string"},
                "outputs": {"text": "string"},
                "parameters": {}
            }
        }
    }


@app.get("/patterns")
async def get_supported_patterns():
    """New endpoint to explicitly expose pattern support"""
    return {
        "node_id": "echo-node",
        "supported_patterns": ["synchronous_stateless"],
        "pattern_details": {
            "synchronous_stateless": {
                "description": "Simple passthrough: input → echo → output",
                "interface": "function_call",
                "typical_duration": "milliseconds",
                "inputs": {"text": "string"},
                "outputs": {"text": "string"},
                "parameters": {}
            }
        }
    }


@app.post("/process")
async def process_data(request: NodeRequest):
    print(f"Echo Node received: {request.data}")

    # Process the data (in this case, just echo it)
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

    # If there's a next node, forward the data
    if request.next_node:
        try:
            forward_request = NodeRequest(
                data=processed_data,
                next_node=None,  # Let the orchestrator handle chaining
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

    text = inputs["text"]

    # Echo the text unchanged
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
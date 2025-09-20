import json
import os
import time
from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel
import requests
from typing import Optional
import asyncio
import time
import requests
import threading
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
                        "input_format": info_data.get("input_format", "string"),
                        "output_format": info_data.get("output_format", "storage_id"),
                        "examples": []
                    } for cap in info_data.get("capabilities", [])
                ],
                "description": info_data.get("description", "Storage service"),
                "tags": info_data.get("tags", []),
                "interaction_patterns": info_data.get("interaction_patterns", [])
            }

            registry_response = requests.post(
                "http://service-registry:8000/register",
                json=registration_data,
                timeout=10
            )

            if registry_response.status_code == 200:
                print("Successfully registered storage-node with service registry")
            else:
                print(f"Failed to register: {registry_response.status_code}")

    except Exception as e:
        print(f"Registration failed: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Storage Node service starting up...")
    registration_thread = threading.Thread(target=delayed_registration, daemon=True)
    registration_thread.start()
    yield
    print("Storage Node service shutting down...")

app = FastAPI(
    title="storage-node",
    description="Persistent storage service",
    lifespan=lifespan
)



class NodeRequest(BaseModel):
    data: str
    next_node: Optional[str] = None
    metadata: dict = {}


class NodeResponse(BaseModel):
    node_id: str = "storage-node"
    data: str
    status: str
    metadata: dict = {}


class StoredItem(BaseModel):
    id: str
    data: str
    timestamp: str
    metadata: dict


# Simple in-memory storage (in production, use a real database)
storage = []
storage_file = "/app/data/storage.json"


def load_storage():
    """Load storage from file"""
    global storage
    try:
        if os.path.exists(storage_file):
            with open(storage_file, 'r') as f:
                storage = json.load(f)
    except Exception as e:
        print(f"Error loading storage: {e}")
        storage = []


def save_storage():
    """Save storage to file"""
    try:
        os.makedirs(os.path.dirname(storage_file), exist_ok=True)
        with open(storage_file, 'w') as f:
            json.dump(storage, f, indent=2)
    except Exception as e:
        print(f"Error saving storage: {e}")


# Load storage on startup
load_storage()


@app.get("/health")
async def health_check():
    return {"status": "healthy", "node_type": "storage"}


# Replace the /info endpoint in nodes/storage-node/app.py

@app.get("/info")
async def node_info():
    """Standardized service discovery information for Storage Node"""
    return {
        # REQUIRED FIELDS
        "node_id": "storage-node",
        "version": "1.0.0",
        "status": "healthy",
        "description": "Provides persistent storage with metadata and retrieval capabilities using file-based JSON storage",

        # CAPABILITY DISCOVERY
        "capabilities": [
            "persistent_storage",
            "data_persistence",
            "data_retrieval",
            "metadata_storage",
            "search_functionality",
            "data_indexing"
        ],
        "tags": ["storage", "persistence", "database", "retrieval"],

        # DATA CONTRACTS
        "input_format": "string",
        "output_format": "storage_id",
        "supported_operations": ["store", "retrieve", "search", "list"],

        # INTERACTION PATTERNS
        "interaction_patterns": ["synchronous_persistent"],
        "pattern_interfaces": {
            "synchronous_persistent": {
                "inputs": {"data": "string"},
                "outputs": {"storage_id": "string", "confirmation": "string"},
                "parameters": {
                    "operation": {
                        "type": "string",
                        "options": ["store", "retrieve", "search", "list"],
                        "default": "store"
                    },
                    "search_query": {
                        "type": "string",
                        "required_for": ["search"]
                    },
                    "item_id": {
                        "type": "string",
                        "required_for": ["retrieve"]
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
            "patterns": "/patterns",
            "storage/list": "/storage/list",
            "storage/search": "/storage/search/{query}",
            "storage/clear": "/storage/clear"
        },
        "dependencies": [],  # No dependencies
        "provides_to": ["notification-services", "reporting-services"],

        # OPERATIONAL INFO
        "resource_requirements": {
            "cpu": "low",
            "memory": "100MB",
            "disk": "persistent"
        },
        "scaling": {
            "can_scale_horizontal": False,  # Shared storage limitation
            "max_instances": 1,
            "startup_time": "5s"
        },

        # PROCESSING CHARACTERISTICS
        "processing_type": "persistence",
        "data_transformation": "metadata_enrichment",
        "typical_use_cases": [
            "Data archival",
            "Session storage",
            "Audit logging",
            "Result caching"
        ],
        "storage_characteristics": {
            "storage_type": "file_based_json",
            "persistence": "durable",
            "backup_strategy": "local_file",
            "search_capability": "substring_search",
            "max_storage_size": "unlimited",
            "data_retention": "indefinite"
        }
    }

@app.get("/contract")
async def get_contract():
    return {
        "service_metadata": {
            "service_id": "storage-node",
            "version": "1.0.0",
            "pattern": "synchronous_persistent",
            "description": "Provides persistent storage with metadata and retrieval capabilities",
            "maintainer": "system",
            "cost_per_execution": 0.005
        },
        "interface_contract": {
            "inputs": {
                "data": {
                    "type": "string",
                    "constraints": {
                        "max_length": 100000,
                        "encoding": "utf-8",
                        "required": True
                    },
                    "description": "Data to be stored persistently"
                },
                "metadata": {
                    "type": "object",
                    "required": False,
                    "description": "Additional metadata to store with the data"
                },
                "operation": {
                    "type": "enum",
                    "values": ["store", "retrieve", "search", "list"],
                    "default": "store",
                    "required": False,
                    "description": "Storage operation to perform"
                },
                "item_id": {
                    "type": "string",
                    "required": False,
                    "description": "Required for retrieve operation"
                },
                "search_query": {
                    "type": "string",
                    "required": False,
                    "description": "Required for search operation"
                }
            },
            "outputs": {
                "storage_id": {
                    "type": "string",
                    "format": "uuid_like",
                    "description": "Unique identifier for stored item"
                },
                "confirmation": {
                    "type": "string",
                    "description": "Human-readable confirmation message"
                },
                "data": {
                    "type": "string",
                    "description": "Retrieved data (for retrieve operations)"
                },
                "results": {
                    "type": "array",
                    "description": "Search results (for search operations)"
                },
                "metadata": {
                    "type": "object",
                    "properties": {
                        "processed_by": {"type": "string"},
                        "pattern_used": {"type": "string"},
                        "stored_id": {"type": "string"},
                        "storage_size": {"type": "integer"},
                        "timestamp": {"type": "string"}
                    }
                }
            }
        },
        "behavioral_guarantees": {
            "deterministic": False,  # Storage IDs are unique/random
            "side_effects": True,    # Modifies persistent storage
            "idempotent": False,     # Multiple stores create multiple records
            "data_preservation": "durable_storage",
            "execution_safety": "data_consistent"
        },
        "resource_requirements": {
            "max_execution_time": "200ms",
            "memory_limit": "100MB",
            "cpu_intensive": False,
            "network_calls": False,
            "disk_space": True
        },
        "compatibility_rules": {
            "can_chain_to": ["validation_services", "notification_services"],
            "cannot_chain_to": ["streaming_services"],
            "requires_preprocessing": [],
            "output_compatible_with": ["string_consumers", "id_processors"],
            "input_compatible_with": ["string_producers", "text_processors", "transform_services"]
        },
        "persistence_guarantees": {
            "durability": "file_system_backed",
            "consistency": "immediate",
            "backup_strategy": "local_json",
            "data_retention": "indefinite"
        },
        "capabilities": {
            "operations": ["store", "retrieve", "search", "list"],
            "storage_types": ["text", "metadata"],
            "query_types": ["exact_match", "substring_search"],
            "indexing": "basic_text_search"
        },
        "error_handling": {
            "failure_modes": ["disk_full", "permission_error", "item_not_found", "invalid_search"],
            "recovery_strategy": "transaction_rollback",
            "rollback_capable": True
        }
    }



@app.get("/patterns")
async def get_supported_patterns():
    """New endpoint to explicitly expose pattern support"""
    return {
        "node_id": "storage-node",
        "supported_patterns": ["synchronous_persistent"],
        "pattern_details": {
            "synchronous_persistent": {
                "description": "Database-like operations with immediate response",
                "interface": "persistent_api",
                "typical_duration": "milliseconds",
                "inputs": {"data": "string"},
                "outputs": {"storage_id": "string", "confirmation": "string"},
                "operations": ["store", "retrieve", "search", "list"],
                "persistence": "file_based_json"
            }
        }
    }


@app.post("/process")
async def process_data(request: NodeRequest):
    print(f"Storage Node received: {request.data}")

    # Generate unique ID
    item_id = f"item_{len(storage) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Create storage item
    stored_item = StoredItem(
        id=item_id,
        data=request.data,
        timestamp=datetime.now().isoformat(),
        metadata=request.metadata
    )

    # Store the item
    storage.append(stored_item.dict())
    save_storage()

    response = NodeResponse(
        data=f"Stored as {item_id}",
        status="success",
        metadata={
            "processed_by": "storage-node",
            "pattern_used": "synchronous_persistent",
            "stored_id": item_id,
            "storage_size": len(storage),
            **request.metadata
        }
    )

    print(f"Stored item {item_id}, total items: {len(storage)}")
    return response


# NEW: Pattern-specific endpoint for synchronous_persistent
@app.post("/execute")
async def execute_synchronous_persistent(
        inputs: dict,
        parameters: dict = {}
):
    """Direct pattern-based execution for synchronous_persistent"""

    operation = parameters.get("operation", "store")

    if operation == "store":
        if "data" not in inputs:
            return {"error": "Missing required input: data", "pattern": "synchronous_persistent"}

        # Generate unique ID
        item_id = f"item_{len(storage) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Create storage item
        stored_item = StoredItem(
            id=item_id,
            data=inputs["data"],
            timestamp=datetime.now().isoformat(),
            metadata=parameters.get("metadata", {})
        )

        # Store the item
        storage.append(stored_item.dict())
        save_storage()

        return {
            "outputs": {
                "storage_id": item_id,
                "confirmation": f"Data stored successfully as {item_id}"
            },
            "metadata": {
                "node_id": "storage-node",
                "pattern": "synchronous_persistent",
                "operation": "store",
                "storage_size": len(storage),
                "execution_time": "< 10ms"
            }
        }

    elif operation == "retrieve":
        item_id = parameters.get("item_id")
        if not item_id:
            return {"error": "Missing required parameter: item_id", "pattern": "synchronous_persistent"}

        for item in storage:
            if item["id"] == item_id:
                return {
                    "outputs": {
                        "data": item["data"],
                        "storage_id": item["id"]
                    },
                    "metadata": {
                        "node_id": "storage-node",
                        "pattern": "synchronous_persistent",
                        "operation": "retrieve",
                        "timestamp": item["timestamp"]
                    }
                }

        return {"error": f"Item {item_id} not found", "pattern": "synchronous_persistent"}

    elif operation == "search":
        search_query = parameters.get("search_query")
        if not search_query:
            return {"error": "Missing required parameter: search_query", "pattern": "synchronous_persistent"}

        results = []
        for item in storage:
            if search_query.lower() in item["data"].lower():
                results.append({
                    "storage_id": item["id"],
                    "data": item["data"],
                    "timestamp": item["timestamp"]
                })

        return {
            "outputs": {
                "results": results,
                "count": len(results)
            },
            "metadata": {
                "node_id": "storage-node",
                "pattern": "synchronous_persistent",
                "operation": "search",
                "search_query": search_query
            }
        }

    elif operation == "list":
        return {
            "outputs": {
                "items": storage,
                "count": len(storage)
            },
            "metadata": {
                "node_id": "storage-node",
                "pattern": "synchronous_persistent",
                "operation": "list",
                "total_items": len(storage)
            }
        }

    else:
        return {"error": f"Unknown operation: {operation}", "pattern": "synchronous_persistent"}


@app.get("/storage/list")
async def list_stored_items():
    """List all stored items"""
    return {
        "total_items": len(storage),
        "items": storage
    }


@app.get("/storage/{item_id}")
async def get_stored_item(item_id: str):
    """Retrieve a specific stored item"""
    for item in storage:
        if item["id"] == item_id:
            return item
    return {"error": "Item not found"}


@app.get("/storage/search/{query}")
async def search_storage(query: str):
    """Search stored items"""
    results = []
    for item in storage:
        if query.lower() in item["data"].lower():
            results.append(item)

    return {
        "query": query,
        "results_count": len(results),
        "results": results
    }


@app.delete("/storage/clear")
async def clear_storage():
    """Clear all storage (for testing)"""
    global storage
    storage = []
    save_storage()
    return {"status": "cleared", "remaining_items": len(storage)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
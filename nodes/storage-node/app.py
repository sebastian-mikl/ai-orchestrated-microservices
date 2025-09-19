from fastapi import FastAPI
from pydantic import BaseModel
import json
import os
from datetime import datetime
from typing import List
from typing import List, Optional

app = FastAPI(title="Storage Node", description="Stores data and provides retrieval")


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


@app.get("/info")
async def node_info():
    return {
        "node_id": "storage-node",
        "capabilities": ["store", "retrieve", "list", "search"],
        "description": "Stores data with metadata and provides retrieval capabilities",
        "input_format": "string",
        "output_format": "string",
        "storage_count": len(storage)
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
            "stored_id": item_id,
            "storage_size": len(storage),
            **request.metadata
        }
    )

    print(f"Stored item {item_id}, total items: {len(storage)}")
    return response


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
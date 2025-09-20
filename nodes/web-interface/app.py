# nodes/web-interface/app.py
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import threading
import asyncio
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
import requests
import asyncio
import time
from contextlib import asynccontextmanager
from typing import Optional


# === STEP 1: Add these functions at the TOP of your app.py (after imports) ===

async def wait_for_service_registry(max_wait_time: int = 60) -> bool:
    """Wait for service registry to be available"""
    start_time = time.time()

    while time.time() - start_time < max_wait_time:
        try:
            response = requests.get("http://service-registry:8000/health", timeout=5)
            if response.status_code == 200:
                print("Service registry is ready")
                return True
        except requests.exceptions.RequestException:
            pass

        print("Waiting for service registry...")
        await asyncio.sleep(2)

    print("Service registry not available after waiting")
    return False


async def register_with_service_registry():
    """Register this service with the service registry"""
    if not await wait_for_service_registry():
        print("WARNING: Service registry not available, skipping registration")
        return False

    try:
        # Get our own service info
        info_response = requests.get("http://localhost:8000/info", timeout=5)
        if info_response.status_code != 200:
            print(f"Failed to get service info: {info_response.status_code}")
            return False

        info_data = info_response.json()

        # Create registration payload
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

        # Register with service registry
        registry_response = requests.post(
            "http://service-registry:8000/register",
            json=registration_data,
            timeout=10
        )

        if registry_response.status_code == 200:
            print(f"Successfully registered {info_data['node_id']} with service registry")
            return True
        else:
            print(f"Failed to register: {registry_response.status_code}")
            print(f"Response: {registry_response.text}")
            return False

    except Exception as e:
        print(f"Registration failed: {e}")
        return False


async def unregister_from_service_registry():
    """Unregister this service on shutdown"""
    try:
        info_response = requests.get("http://localhost:8000/info", timeout=5)
        if info_response.status_code == 200:
            info_data = info_response.json()
            requests.delete(
                f"http://service-registry:8000/unregister/{info_data['node_id']}",
                timeout=5
            )
            print(f"Unregistered {info_data['node_id']}")
    except Exception as e:
        print(f"Unregistration failed: {e}")

app = FastAPI()

@app.get("/")
async def serve_index():
    return FileResponse("index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
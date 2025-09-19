from fastapi import FastAPI
from pydantic import BaseModel
import requests
import asyncio
from typing import List, Dict, Optional

app = FastAPI(title="Network Orchestrator", description="Orchestrates node communication")


class OrchestrationRequest(BaseModel):
    command: str
    data: str
    chain: Optional[List[str]] = None


class NodeInfo(BaseModel):
    node_id: str
    url: str
    capabilities: List[str]
    status: str


# Registry of available nodes
node_registry = {
    "echo": {"url": "http://echo-node:8000", "capabilities": ["receive", "forward"]},
    "transform": {"url": "http://transform-node:8000", "capabilities": ["transform", "uppercase"]},
    "storage": {"url": "http://storage-node:8000", "capabilities": ["store", "retrieve"]}
}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "orchestrator"}


@app.get("/nodes")
async def list_nodes():
    """List all registered nodes with their status"""
    node_status = {}

    for node_id, node_info in node_registry.items():
        try:
            response = requests.get(f"{node_info['url']}/health", timeout=5)
            if response.status_code == 200:
                status_data = response.json()
                node_status[node_id] = {
                    "url": node_info["url"],
                    "status": "healthy",
                    "capabilities": node_info["capabilities"],
                    "details": status_data
                }
            else:
                node_status[node_id] = {"status": "unhealthy", "url": node_info["url"]}
        except Exception as e:
            node_status[node_id] = {"status": "unreachable", "url": node_info["url"], "error": str(e)}

    return node_status


@app.get("/nodes/{node_id}/info")
async def get_node_info(node_id: str):
    """Get detailed info about a specific node"""
    if node_id not in node_registry:
        return {"error": "Node not found"}

    try:
        node_url = node_registry[node_id]["url"]
        response = requests.get(f"{node_url}/info", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": "Node info unavailable"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/execute")
async def execute_command(request: OrchestrationRequest):
    """Execute a command by orchestrating nodes"""
    print(f"Orchestrator received command: {request.command}")
    print(f"Data: {request.data}")

    # Simple command parsing (this is where NL2Command would go later)
    if request.chain:
        # Use explicit chain
        chain = request.chain
    else:
        # Parse command to determine chain
        chain = parse_command(request.command)

    if not chain:
        return {"error": "Could not parse command", "command": request.command}

    print(f"Executing chain: {chain}")

    # Execute the chain
    result = await execute_chain(chain, request.data)

    return {
        "command": request.command,
        "chain": chain,
        "result": result,
        "status": "completed"
    }


def parse_command(command: str) -> List[str]:
    """Simple command parser - this is where AI would go later"""
    command = command.lower()

    # Predefined patterns
    if "echo" in command and "store" in command:
        return ["echo", "storage"]
    elif "transform" in command and "store" in command:
        return ["echo", "transform", "storage"]
    elif "process" in command and "save" in command:
        return ["echo", "transform", "storage"]
    elif "uppercase" in command:
        return ["echo", "transform", "storage"]
    elif "store" in command or "save" in command:
        return ["echo", "storage"]
    elif "transform" in command:
        return ["echo", "transform"]
    else:
        # Default: just echo
        return ["echo"]


async def execute_chain(chain: List[str], data: str) -> Dict:
    """Execute a chain of nodes"""
    current_data = data
    results = []

    for i, node_id in enumerate(chain):
        if node_id not in node_registry:
            return {"error": f"Unknown node: {node_id}", "step": i}

        node_url = node_registry[node_id]["url"]

        # Determine next node
        next_node = chain[i + 1] if i + 1 < len(chain) else None

        try:
            payload = {
                "data": current_data,
                "next_node": next_node,
                "metadata": {
                    "chain_position": i,
                    "chain_length": len(chain),
                    "orchestrator": "network-orchestrator"
                }
            }

            print(f"Calling {node_id} at {node_url}/process")
            response = requests.post(
                f"{node_url}/process",
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                results.append({
                    "node": node_id,
                    "status": "success",
                    "result": result
                })
                current_data = result.get("data", current_data)

                # If this node forwarded to the next one, we're done
                if next_node and result.get("status") == "success":
                    print(f"Node {node_id} successfully forwarded to {next_node}")
                    break

            else:
                return {
                    "error": f"Node {node_id} failed",
                    "status_code": response.status_code,
                    "response": response.text,
                    "step": i
                }

        except Exception as e:
            return {
                "error": f"Failed to call {node_id}",
                "exception": str(e),
                "step": i
            }

    return {
        "final_data": current_data,
        "steps": results,
        "chain_completed": True
    }


@app.post("/test")
async def test_simple_chain():
    """Test endpoint to verify the basic chain works"""
    test_request = OrchestrationRequest(
        command="process this text and save it",
        data="hello world test",
        chain=["echo", "transform", "storage"]
    )

    return await execute_command(test_request)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
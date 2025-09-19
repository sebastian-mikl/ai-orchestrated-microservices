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


@app.get("/info")
async def node_info():
    return {
        "node_id": "echo-node",
        "capabilities": ["receive", "forward"],
        "description": "Echoes input data and forwards to next node",
        "input_format": "string",
        "output_format": "string"
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os

app = FastAPI(title="Transform Node", description="Transforms text data")


class NodeRequest(BaseModel):
    data: str
    next_node: str = None
    metadata: dict = {}


class NodeResponse(BaseModel):
    node_id: str = "transform-node"
    data: str
    status: str
    metadata: dict = {}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "node_type": "transform"}


@app.get("/info")
async def node_info():
    return {
        "node_id": "transform-node",
        "capabilities": ["transform", "uppercase", "lowercase", "reverse"],
        "description": "Transforms text data in various ways",
        "input_format": "string",
        "output_format": "string"
    }


@app.post("/process")
async def process_data(request: NodeRequest):
    print(f"Transform Node received: {request.data}")

    # Transform the data (uppercase + add timestamp)
    processed_data = request.data.upper()

    # Add some processing metadata
    transform_info = {
        "original": request.data,
        "transformation": "uppercase",
        "length_change": len(processed_data) - len(request.data)
    }

    response = NodeResponse(
        data=processed_data,
        status="success",
        metadata={
            "processed_by": "transform-node",
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


@app.post("/process/custom")
async def process_custom(request: NodeRequest, transformation: str = "uppercase"):
    """Custom transformation endpoint"""
    print(f"Transform Node custom processing: {transformation}")

    if transformation == "uppercase":
        processed_data = request.data.upper()
    elif transformation == "lowercase":
        processed_data = request.data.lower()
    elif transformation == "reverse":
        processed_data = request.data[::-1]
    else:
        processed_data = request.data  # No transformation

    return NodeResponse(
        data=processed_data,
        status="success",
        metadata={
            "processed_by": "transform-node",
            "transformation": transformation,
            **request.metadata
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
# Keep only these imports at the top:
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import csv
import xml.etree.ElementTree as ET
import base64
import io
from typing import List, Dict, Any, Optional
import threading
import asyncio
import time
import requests
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
                        "output_format": info_data.get("output_format", "json_response"),
                        "examples": []
                    } for cap in info_data.get("capabilities", [])
                ],
                "description": info_data.get("description", "File Processor service"),  # Not External API service
                "tags": info_data.get("tags", []),
                "interaction_patterns": info_data.get("interaction_patterns", [])
            }

            registry_response = requests.post(
                "http://service-registry:8000/register",
                json=registration_data,
                timeout=10
            )

            if registry_response.status_code == 200:
                # In register_with_service_registry(), change this line:
                print(
                    "Successfully registered file-processor with service registry")  # Not external-api
            else:
                print(f"Failed to register: {registry_response.status_code}")

    except Exception as e:
        print(f"Registration failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("File Processor service starting up...")  # Not External API
    registration_thread = threading.Thread(target=delayed_registration, daemon=True)
    registration_thread.start()
    yield
    print("File Processor service shutting down...")

# Update FastAPI app initialization
app = FastAPI(
    title="file-processor",  # Not external-api
    description="processes and converts files",
    lifespan=lifespan
)

class NodeRequest(BaseModel):
    data: str
    next_node: Optional[str] = None
    metadata: dict = {}


class NodeResponse(BaseModel):
    node_id: str = "file-processor"
    data: str
    status: str
    metadata: dict = {}


class FileProcessRequest(BaseModel):
    file_content: str  # base64 encoded
    input_format: str
    output_format: str = "json"


@app.get("/health")
async def health_check():
    return {"status": "healthy", "node_type": "file_processor"}


@app.get("/contract")
async def get_contract():
    return {
        "service_metadata": {
            "service_id": "file-processor",
            "version": "1.0.0",
            "pattern": "synchronous_stateless",
            "description": "Processes files and converts between CSV, JSON, and XML formats",
            "maintainer": "system",
            "cost_per_execution": 0.003
        },
        "interface_contract": {
            "inputs": {
                "file_content": {
                    "type": "string",
                    "constraints": {
                        "encoding": "base64",
                        "max_size": "10MB",
                        "required": True
                    },
                    "description": "Base64 encoded file content"
                },
                "input_format": {
                    "type": "enum",
                    "values": ["csv", "json", "xml", "txt"],
                    "required": True,
                    "description": "Format of the input file"
                },
                "output_format": {
                    "type": "enum",
                    "values": ["json", "csv", "structured_data"],
                    "default": "json",
                    "required": False,
                    "description": "Desired output format"
                }
            },
            "outputs": {
                "parsed_data": {
                    "type": "json_array",
                    "description": "Processed file data as structured JSON"
                },
                "row_count": {
                    "type": "integer",
                    "description": "Number of data rows processed"
                },
                "validation_errors": {
                    "type": "array",
                    "description": "List of any parsing errors encountered"
                },
                "metadata": {
                    "type": "object",
                    "properties": {
                        "original_format": {"type": "string"},
                        "output_format": {"type": "string"},
                        "file_size": {"type": "integer"}
                    }
                }
            }
        },
        "behavioral_guarantees": {
            "deterministic": True,
            "side_effects": False,
            "idempotent": True,
            "data_preservation": "structured_conversion",
            "execution_safety": "validates_input"
        },
        "resource_requirements": {
            "max_execution_time": "5s",
            "memory_limit": "256MB",
            "cpu_intensive": True,
            "network_calls": False
        },
        "compatibility_rules": {
            "can_chain_to": ["validation_services", "storage_services", "api_services"],
            "cannot_chain_to": ["binary_processors"],
            "requires_preprocessing": [],
            "output_compatible_with": ["json_consumers", "data_processors"],
            "input_compatible_with": ["file_uploaders", "base64_encoders"]
        },
        "capabilities": {
            "file_formats": ["csv", "json", "xml", "txt"],
            "operations": ["parse", "convert", "validate", "structure"],
            "output_formats": ["json_array", "structured_data"]
        },
        "error_handling": {
            "failure_modes": ["invalid_base64", "unsupported_format", "malformed_file", "file_too_large"],
            "recovery_strategy": "partial_processing",
            "rollback_capable": True
        }
    }


# Replace the /info endpoint in nodes/file-processor/app.py

@app.get("/info")
async def node_info():
    """Standardized service discovery information for File Processor"""
    return {
        # REQUIRED FIELDS
        "node_id": "file-processor",
        "version": "1.0.0",
        "status": "healthy",
        "description": "Processes and converts files between CSV, JSON, XML, and TXT formats with validation",

        # CAPABILITY DISCOVERY
        "capabilities": [
            "file_processing",
            "format_conversion",
            "csv_parsing",
            "json_parsing",
            "xml_parsing",
            "text_parsing",
            "data_structuring"
        ],
        "tags": ["file", "conversion", "parsing", "data", "format"],

        # DATA CONTRACTS
        "input_format": "base64_file",
        "output_format": "structured_data",
        "supported_operations": ["parse", "convert", "validate", "structure"],

        # INTERACTION PATTERNS
        "interaction_patterns": ["synchronous_stateless"],
        "pattern_interfaces": {
            "synchronous_stateless": {
                "inputs": {
                    "file_content": "string",
                    "input_format": "string",
                    "output_format": "string"
                },
                "outputs": {
                    "parsed_data": "json_array",
                    "row_count": "integer",
                    "validation_errors": "array"
                },
                "parameters": {
                    "input_format": {
                        "type": "string",
                        "options": ["csv", "json", "xml", "txt"],
                        "default": "csv"
                    },
                    "output_format": {
                        "type": "string",
                        "options": ["json", "csv", "structured_data"],
                        "default": "json"
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
            "process/csv": "/process/csv"
        },
        "dependencies": [],  # No dependencies
        "provides_to": ["validation-services", "storage-services", "api-services"],

        # OPERATIONAL INFO
        "resource_requirements": {
            "cpu": "high",
            "memory": "256MB",
            "disk": "temporary"
        },
        "scaling": {
            "can_scale_horizontal": True,
            "max_instances": 10,
            "startup_time": "6s"
        },

        # PROCESSING CHARACTERISTICS
        "processing_type": "conversion",
        "data_transformation": "structured_conversion",
        "typical_use_cases": [
            "File format conversion",
            "Data import/export",
            "Legacy data migration",
            "Batch file processing"
        ],
        "file_capabilities": {
            "supported_input_formats": ["csv", "json", "xml", "txt"],
            "supported_output_formats": ["json_array", "structured_data"],
            "max_file_size": "10MB",
            "encoding_support": ["utf-8"],
            "validation_included": True,
            "error_reporting": "detailed"
        }
    }


@app.post("/process")
async def process_data(request: NodeRequest):
    try:
        # Extract file processing parameters from metadata
        input_format = request.metadata.get("input_format", "csv")
        output_format = request.metadata.get("output_format", "json")

        # Process the file content
        result = process_file_content(request.data, input_format, output_format)

        response = NodeResponse(
            data=json.dumps(result["parsed_data"]),
            status="success",
            metadata={
                "processed_by": "file-processor",
                "pattern_used": "synchronous_stateless",
                "row_count": result["row_count"],
                "validation_errors": result["validation_errors"],
                "original_format": input_format,
                "output_format": output_format,
                **request.metadata
            }
        )

        return response

    except Exception as e:
        return NodeResponse(
            data="",
            status="failed",
            metadata={
                "processed_by": "file-processor",
                "error": str(e),
                **request.metadata
            }
        )


@app.post("/execute")
async def execute_file_processing(inputs: dict, parameters: dict = {}):
    """Direct pattern-based execution for file processing"""

    if "file_content" not in inputs:
        return {"error": "Missing required input: file_content", "pattern": "synchronous_stateless"}

    input_format = inputs.get("input_format", parameters.get("input_format", "csv"))
    output_format = parameters.get("output_format", "json")

    try:
        # Decode base64 content
        file_content = base64.b64decode(inputs["file_content"]).decode('utf-8')

        result = process_file_content(file_content, input_format, output_format)

        return {
            "outputs": {
                "parsed_data": result["parsed_data"],
                "row_count": result["row_count"],
                "validation_errors": result["validation_errors"]
            },
            "metadata": {
                "node_id": "file-processor",
                "pattern": "synchronous_stateless",
                "original_format": input_format,
                "output_format": output_format,
                "execution_time": "< 5s"
            }
        }

    except Exception as e:
        return {"error": str(e), "pattern": "synchronous_stateless"}


def process_file_content(content: str, input_format: str, output_format: str) -> Dict[str, Any]:
    """Process file content based on input and output formats"""

    validation_errors = []
    parsed_data = []
    row_count = 0

    try:
        if input_format.lower() == "csv":
            parsed_data, row_count, errors = parse_csv(content)
            validation_errors.extend(errors)

        elif input_format.lower() == "json":
            parsed_data, row_count, errors = parse_json(content)
            validation_errors.extend(errors)

        elif input_format.lower() == "xml":
            parsed_data, row_count, errors = parse_xml(content)
            validation_errors.extend(errors)

        elif input_format.lower() == "txt":
            parsed_data, row_count, errors = parse_txt(content)
            validation_errors.extend(errors)

        else:
            raise ValueError(f"Unsupported input format: {input_format}")

    except Exception as e:
        validation_errors.append(f"Processing error: {str(e)}")

    return {
        "parsed_data": parsed_data,
        "row_count": row_count,
        "validation_errors": validation_errors
    }


def parse_csv(content: str) -> tuple:
    """Parse CSV content"""
    errors = []
    data = []

    try:
        csv_file = io.StringIO(content)
        reader = csv.DictReader(csv_file)

        for i, row in enumerate(reader):
            if row:  # Skip empty rows
                # Clean up row data
                cleaned_row = {k.strip(): v.strip() if v else None for k, v in row.items() if k}
                data.append(cleaned_row)

    except Exception as e:
        errors.append(f"CSV parsing error: {str(e)}")

    return data, len(data), errors


def parse_json(content: str) -> tuple:
    """Parse JSON content"""
    errors = []
    data = []

    try:
        json_data = json.loads(content)

        if isinstance(json_data, list):
            data = json_data
        elif isinstance(json_data, dict):
            data = [json_data]
        else:
            data = [{"value": json_data}]

    except json.JSONDecodeError as e:
        errors.append(f"JSON parsing error: {str(e)}")

    return data, len(data), errors


def parse_xml(content: str) -> tuple:
    """Parse XML content"""
    errors = []
    data = []

    try:
        root = ET.fromstring(content)

        # Convert XML to dictionary format
        for child in root:
            item = {}
            if child.text and child.text.strip():
                item[child.tag] = child.text.strip()

            for attr_name, attr_value in child.attrib.items():
                item[f"{child.tag}_{attr_name}"] = attr_value

            if item:
                data.append(item)

    except ET.ParseError as e:
        errors.append(f"XML parsing error: {str(e)}")

    return data, len(data), errors


def parse_txt(content: str) -> tuple:
    """Parse plain text content"""
    errors = []

    # Split into lines and create simple structure
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    data = [{"line_number": i + 1, "content": line} for i, line in enumerate(lines)]

    return data, len(data), errors


@app.post("/process/csv")
async def process_csv_file(request: FileProcessRequest):
    """Endpoint specifically for CSV processing"""
    try:
        file_content = base64.b64decode(request.file_content).decode('utf-8')
        result = process_file_content(file_content, request.input_format, request.output_format)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
# nodes/data-validator/app.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ValidationError
import re
import json
import jsonschema
from typing import Dict, Any, Optional, List
from datetime import datetime
import phonenumbers
from email_validator import validate_email, EmailNotValidError
import requests
import asyncio
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - register with service registry
    await register_with_service_registry()
    yield
    # Shutdown - could add unregistration here


async def register_with_service_registry():
    """Register this service with the service registry"""
    try:
        # Wait a bit for service registry to be ready
        await asyncio.sleep(5)

        # Get our own service info
        info_response = requests.get("http://localhost:8000/info", timeout=5)
        if info_response.status_code == 200:
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
                        "output_format": info_data.get("output_format", "validation_result"),
                        "examples": []
                    } for cap in info_data.get("capabilities", [])
                ],
                "description": info_data.get("description", "Auto-registered service"),
                "tags": ["validation", "data", "verification"],
                "interaction_patterns": info_data.get("interaction_patterns", [])
            }

            # Register with service registry
            registry_response = requests.post(
                "http://service-registry:8000/register",
                json=registration_data,
                timeout=10
            )

            if registry_response.status_code == 200:
                print(f"Successfully registered data-validator with service registry")
            else:
                print(f"Failed to register: {registry_response.status_code}")

    except Exception as e:
        print(f"Registration failed: {e}")


app = FastAPI(
    title="Data Validator Service",
    description="Validates data formats, schemas, and business rules",
    lifespan=lifespan
)


class NodeRequest(BaseModel):
    data: str
    next_node: Optional[str] = None
    metadata: dict = {}


class NodeResponse(BaseModel):
    node_id: str = "data-validator"
    data: str
    status: str
    metadata: dict = {}


class ValidationRequest(BaseModel):
    data: Any
    validation_type: str
    schema: Optional[dict] = None
    rules: Optional[dict] = None


@app.get("/health")
async def health_check():
    return {"status": "healthy", "node_type": "data_validator"}


@app.get("/contract")
async def get_contract():
    return {
        "service_metadata": {
            "service_id": "data-validator",
            "version": "1.0.0",
            "pattern": "synchronous_stateless",
            "description": "Validates data against formats, schemas, and business rules with detailed error reporting",
            "maintainer": "system",
            "cost_per_execution": 0.002
        },
        "interface_contract": {
            "inputs": {
                "data": {
                    "type": "any",
                    "required": True,
                    "description": "Data to be validated (string, object, array, etc.)"
                },
                "validation_type": {
                    "type": "enum",
                    "values": ["email", "phone", "json_schema", "business_rules", "format", "range"],
                    "required": True,
                    "description": "Type of validation to perform"
                },
                "schema": {
                    "type": "object",
                    "required": False,
                    "description": "JSON schema for validation (required for json_schema type)"
                },
                "rules": {
                    "type": "object",
                    "required": False,
                    "description": "Business rules configuration"
                }
            },
            "outputs": {
                "is_valid": {
                    "type": "boolean",
                    "description": "Whether the data passed validation"
                },
                "validation_errors": {
                    "type": "array",
                    "description": "List of validation errors found"
                },
                "cleaned_data": {
                    "type": "any",
                    "description": "Data after cleaning/normalization"
                },
                "validation_score": {
                    "type": "float",
                    "description": "Validation score from 0.0 to 1.0"
                },
                "metadata": {
                    "type": "object",
                    "properties": {
                        "validation_type": {"type": "string"},
                        "records_processed": {"type": "integer"},
                        "error_count": {"type": "integer"}
                    }
                }
            }
        },
        "behavioral_guarantees": {
            "deterministic": True,
            "side_effects": False,
            "idempotent": True,
            "data_preservation": "validation_with_cleaning",
            "execution_safety": "validates_input"
        },
        "resource_requirements": {
            "max_execution_time": "2s",
            "memory_limit": "128MB",
            "cpu_intensive": False,
            "network_calls": False
        },
        "compatibility_rules": {
            "can_chain_to": ["storage_services", "file_processors", "notification_services"],
            "cannot_chain_to": ["streaming_services"],
            "requires_preprocessing": [],
            "output_compatible_with": ["boolean_consumers", "validation_result_processors"],
            "input_compatible_with": ["any_data_producers", "file_processors", "api_services"]
        },
        "capabilities": {
            "validation_types": ["email", "phone", "json_schema", "business_rules", "format", "range"],
            "operations": ["validate", "clean", "normalize", "score"],
            "formats": ["email", "phone", "date", "url", "credit_card"]
        },
        "error_handling": {
            "failure_modes": ["invalid_schema", "malformed_data", "unsupported_validation"],
            "recovery_strategy": "partial_validation",
            "rollback_capable": True
        }
    }


@app.get("/info")
async def node_info():
    return {
        "node_id": "data-validator",
        "capabilities": ["email_validation", "phone_validation", "schema_validation", "business_rules",
                         "format_validation", "range_validation"],
        "description": "Validates data against various formats and business rules",
        "input_format": "any_data",
        "output_format": "validation_result",
        "interaction_patterns": ["synchronous_stateless"],
        "supported_validations": ["email", "phone", "json_schema", "business_rules", "format", "range"],
        "tags": ["validation", "data", "verification"]
    }


@app.post("/process")
async def process_data(request: NodeRequest):
    try:
        # Extract validation parameters from metadata
        validation_type = request.metadata.get("validation_type", "format")
        schema = request.metadata.get("schema")
        rules = request.metadata.get("rules", {})

        # Attempt to parse data as JSON if it's a string
        try:
            data_to_validate = json.loads(request.data) if isinstance(request.data, str) else request.data
        except json.JSONDecodeError:
            data_to_validate = request.data

        # Perform validation
        result = validate_data(data_to_validate, validation_type, schema, rules)

        response = NodeResponse(
            data=json.dumps(result["cleaned_data"]) if result["cleaned_data"] is not None else request.data,
            status="success" if result["is_valid"] else "validation_failed",
            metadata={
                "processed_by": "data-validator",
                "pattern_used": "synchronous_stateless",
                "is_valid": result["is_valid"],
                "validation_errors": result["validation_errors"],
                "validation_score": result["validation_score"],
                "validation_type": validation_type,
                "error_count": len(result["validation_errors"]),
                **request.metadata
            }
        )

        return response

    except Exception as e:
        return NodeResponse(
            data=request.data,
            status="failed",
            metadata={
                "processed_by": "data-validator",
                "error": str(e),
                **request.metadata
            }
        )


@app.post("/execute")
async def execute_validation(inputs: dict, parameters: dict = {}):
    """Direct pattern-based execution for data validation"""

    if "data" not in inputs:
        return {"error": "Missing required input: data", "pattern": "synchronous_stateless"}

    validation_type = inputs.get("validation_type", parameters.get("validation_type", "format"))
    schema = inputs.get("schema", parameters.get("schema"))
    rules = inputs.get("rules", parameters.get("rules", {}))

    try:
        result = validate_data(inputs["data"], validation_type, schema, rules)

        return {
            "outputs": {
                "is_valid": result["is_valid"],
                "validation_errors": result["validation_errors"],
                "cleaned_data": result["cleaned_data"],
                "validation_score": result["validation_score"]
            },
            "metadata": {
                "node_id": "data-validator",
                "pattern": "synchronous_stateless",
                "validation_type": validation_type,
                "error_count": len(result["validation_errors"]),
                "execution_time": "< 2s"
            }
        }

    except Exception as e:
        return {"error": str(e), "pattern": "synchronous_stateless"}


def validate_data(data: Any, validation_type: str, schema: dict = None, rules: dict = None) -> Dict[str, Any]:
    """Main validation function"""

    validation_errors = []
    cleaned_data = data
    is_valid = True
    validation_score = 1.0

    try:
        if validation_type == "email":
            result = validate_email_format(data)
        elif validation_type == "phone":
            result = validate_phone_format(data)
        elif validation_type == "json_schema":
            result = validate_json_schema(data, schema)
        elif validation_type == "business_rules":
            result = validate_business_rules(data, rules)
        elif validation_type == "format":
            result = validate_general_format(data)
        elif validation_type == "range":
            result = validate_range(data, rules)
        else:
            raise ValueError(f"Unsupported validation type: {validation_type}")

        validation_errors = result["errors"]
        cleaned_data = result.get("cleaned_data", data)
        is_valid = len(validation_errors) == 0
        validation_score = result.get("score", 1.0 if is_valid else 0.0)

    except Exception as e:
        validation_errors.append(f"Validation error: {str(e)}")
        is_valid = False
        validation_score = 0.0

    return {
        "is_valid": is_valid,
        "validation_errors": validation_errors,
        "cleaned_data": cleaned_data,
        "validation_score": validation_score
    }


def validate_email_format(data: Any) -> Dict[str, Any]:
    """Validate email addresses"""
    errors = []
    cleaned_data = data
    score = 1.0

    if isinstance(data, str):
        try:
            valid = validate_email(data)
            cleaned_data = valid.email
        except EmailNotValidError as e:
            errors.append(f"Invalid email: {str(e)}")
            score = 0.0
    elif isinstance(data, list):
        cleaned_emails = []
        valid_count = 0
        for email in data:
            try:
                valid = validate_email(email)
                cleaned_emails.append(valid.email)
                valid_count += 1
            except EmailNotValidError as e:
                errors.append(f"Invalid email '{email}': {str(e)}")
                cleaned_emails.append(email)

        cleaned_data = cleaned_emails
        score = valid_count / len(data) if data else 0.0
    else:
        errors.append("Email validation requires string or list of strings")
        score = 0.0

    return {"errors": errors, "cleaned_data": cleaned_data, "score": score}


def validate_phone_format(data: Any) -> Dict[str, Any]:
    """Validate phone numbers"""
    errors = []
    cleaned_data = data
    score = 1.0

    if isinstance(data, str):
        try:
            parsed = phonenumbers.parse(data, None)
            if phonenumbers.is_valid_number(parsed):
                cleaned_data = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
            else:
                errors.append(f"Invalid phone number: {data}")
                score = 0.0
        except phonenumbers.NumberParseException as e:
            errors.append(f"Phone parsing error: {str(e)}")
            score = 0.0
    elif isinstance(data, list):
        cleaned_phones = []
        valid_count = 0
        for phone in data:
            try:
                parsed = phonenumbers.parse(phone, None)
                if phonenumbers.is_valid_number(parsed):
                    cleaned_phones.append(
                        phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL))
                    valid_count += 1
                else:
                    errors.append(f"Invalid phone number: {phone}")
                    cleaned_phones.append(phone)
            except phonenumbers.NumberParseException as e:
                errors.append(f"Phone parsing error for '{phone}': {str(e)}")
                cleaned_phones.append(phone)

        cleaned_data = cleaned_phones
        score = valid_count / len(data) if data else 0.0
    else:
        errors.append("Phone validation requires string or list of strings")
        score = 0.0

    return {"errors": errors, "cleaned_data": cleaned_data, "score": score}


def validate_json_schema(data: Any, schema: dict) -> Dict[str, Any]:
    """Validate data against JSON schema"""
    errors = []

    if not schema:
        errors.append("JSON schema validation requires a schema")
        return {"errors": errors, "cleaned_data": data, "score": 0.0}

    try:
        jsonschema.validate(data, schema)
        return {"errors": [], "cleaned_data": data, "score": 1.0}
    except jsonschema.ValidationError as e:
        errors.append(f"Schema validation error: {e.message}")
        return {"errors": errors, "cleaned_data": data, "score": 0.0}
    except jsonschema.SchemaError as e:
        errors.append(f"Invalid schema: {e.message}")
        return {"errors": errors, "cleaned_data": data, "score": 0.0}


def validate_business_rules(data: Any, rules: dict) -> Dict[str, Any]:
    """Validate data against business rules"""
    errors = []
    cleaned_data = data
    score = 1.0

    if not rules:
        return {"errors": [], "cleaned_data": data, "score": 1.0}

    # Example business rules
    if "min_age" in rules and isinstance(data, dict) and "age" in data:
        if data["age"] < rules["min_age"]:
            errors.append(f"Age {data['age']} is below minimum {rules['min_age']}")

    if "required_fields" in rules and isinstance(data, dict):
        for field in rules["required_fields"]:
            if field not in data or data[field] is None or data[field] == "":
                errors.append(f"Required field '{field}' is missing or empty")

    if "max_length" in rules and isinstance(data, str):
        if len(data) > rules["max_length"]:
            errors.append(f"Text length {len(data)} exceeds maximum {rules['max_length']}")
            cleaned_data = data[:rules["max_length"]]

    if "allowed_values" in rules:
        if isinstance(data, dict):
            for field, allowed in rules["allowed_values"].items():
                if field in data and data[field] not in allowed:
                    errors.append(f"Field '{field}' value '{data[field]}' not in allowed values: {allowed}")
        elif data not in rules["allowed_values"]:
            errors.append(f"Value '{data}' not in allowed values: {rules['allowed_values']}")

    score = 1.0 if len(errors) == 0 else max(0.0, 1.0 - (len(errors) * 0.2))

    return {"errors": errors, "cleaned_data": cleaned_data, "score": score}


def validate_general_format(data: Any) -> Dict[str, Any]:
    """Validate general data formats"""
    errors = []
    cleaned_data = data

    if isinstance(data, str):
        # URL validation - simplified pattern
        url_pattern = re.compile(r'^https?://[^\s/$.?#].[^\s]*$', re.IGNORECASE)

        if data.startswith(('http://', 'https://')):
            if not url_pattern.match(data):
                errors.append(f"Invalid URL format: {data}")

        # Date validation (simple)
        date_patterns = [
            r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
            r'^\d{2}/\d{2}/\d{4}$',  # MM/DD/YYYY
            r'^\d{2}-\d{2}-\d{4}$'  # DD-MM-YYYY
        ]

        if any(re.match(pattern, data) for pattern in date_patterns):
            try:
                # Try to parse as date
                if '-' in data and len(data) == 10 and data.count('-') == 2:
                    if data[4] == '-':  # YYYY-MM-DD format
                        datetime.strptime(data, '%Y-%m-%d')
                    else:  # DD-MM-YYYY format
                        datetime.strptime(data, '%d-%m-%Y')
                elif '/' in data:
                    datetime.strptime(data, '%m/%d/%Y')
            except ValueError:
                errors.append(f"Invalid date format: {data}")

    return {"errors": errors, "cleaned_data": cleaned_data, "score": 1.0 if len(errors) == 0 else 0.0}


def validate_range(data: Any, rules: dict) -> Dict[str, Any]:
    """Validate numeric ranges"""
    errors = []

    if not rules:
        return {"errors": [], "cleaned_data": data, "score": 1.0}

    try:
        if isinstance(data, str):
            data = float(data)

        if not isinstance(data, (int, float)):
            errors.append("Range validation requires numeric data")
            return {"errors": errors, "cleaned_data": data, "score": 0.0}

        if "min" in rules and data < rules["min"]:
            errors.append(f"Value {data} is below minimum {rules['min']}")

        if "max" in rules and data > rules["max"]:
            errors.append(f"Value {data} is above maximum {rules['max']}")

    except (ValueError, TypeError):
        errors.append(f"Cannot convert '{data}' to numeric value for range validation")

    return {"errors": errors, "cleaned_data": data, "score": 1.0 if len(errors) == 0 else 0.0}


@app.get("/validation-types")
async def list_validation_types():
    """List all available validation types"""
    return {
        "validation_types": {
            "email": {
                "description": "Validate email address format",
                "input_type": "string or array",
                "example": "user@example.com"
            },
            "phone": {
                "description": "Validate and format phone numbers",
                "input_type": "string or array",
                "example": "+1-555-123-4567"
            },
            "json_schema": {
                "description": "Validate data against JSON schema",
                "input_type": "any",
                "requires": "schema parameter"
            },
            "business_rules": {
                "description": "Validate against custom business rules",
                "input_type": "any",
                "requires": "rules parameter"
            },
            "format": {
                "description": "General format validation (URLs, dates, etc.)",
                "input_type": "string",
                "example": "https://example.com"
            },
            "range": {
                "description": "Validate numeric ranges",
                "input_type": "number",
                "requires": "rules with min/max"
            }
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
# nodes/external-api/app.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import json
import time
from typing import Dict, Any, Optional

app = FastAPI(title="External API Service", description="Calls external APIs for weather, currency, and other data")


class NodeRequest(BaseModel):
    data: str
    next_node: Optional[str] = None
    metadata: dict = {}


class NodeResponse(BaseModel):
    node_id: str = "external-api"
    data: str
    status: str
    metadata: dict = {}


class APIRequest(BaseModel):
    api_endpoint: str
    query_params: dict = {}
    location: Optional[str] = None


@app.get("/health")
async def health_check():
    return {"status": "healthy", "node_type": "external_api"}


@app.get("/contract")
async def get_contract():
    return {
        "service_metadata": {
            "service_id": "external-api",
            "version": "1.0.0",
            "pattern": "synchronous_stateless",
            "description": "Calls external APIs for weather, currency rates, stock prices, and other real-time data",
            "maintainer": "system",
            "cost_per_execution": 0.01
        },
        "interface_contract": {
            "inputs": {
                "api_endpoint": {
                    "type": "enum",
                    "values": ["weather", "currency", "stock_price", "random_quote", "cat_fact"],
                    "required": True,
                    "description": "Which external API to call"
                },
                "query_params": {
                    "type": "object",
                    "required": False,
                    "description": "Parameters for the API call"
                },
                "location": {
                    "type": "string",
                    "required": False,
                    "description": "Location for weather queries (city name)"
                }
            },
            "outputs": {
                "api_response": {
                    "type": "json_object",
                    "description": "Response data from the external API"
                },
                "status_code": {
                    "type": "integer",
                    "description": "HTTP status code from the API call"
                },
                "response_time": {
                    "type": "float",
                    "description": "API response time in seconds"
                },
                "metadata": {
                    "type": "object",
                    "properties": {
                        "api_called": {"type": "string"},
                        "success": {"type": "boolean"},
                        "timestamp": {"type": "string"}
                    }
                }
            }
        },
        "behavioral_guarantees": {
            "deterministic": False,  # External APIs return different data
            "side_effects": True,  # Makes external network calls
            "idempotent": False,  # Multiple calls may return different data
            "data_preservation": "external_dependency",
            "execution_safety": "handles_failures"
        },
        "resource_requirements": {
            "max_execution_time": "10s",
            "memory_limit": "128MB",
            "cpu_intensive": False,
            "network_calls": True
        },
        "compatibility_rules": {
            "can_chain_to": ["storage_services", "validation_services", "file_processors"],
            "cannot_chain_to": ["streaming_services"],
            "requires_preprocessing": [],
            "output_compatible_with": ["json_consumers", "data_processors"],
            "input_compatible_with": ["string_producers", "parameter_generators"]
        },
        "capabilities": {
            "api_types": ["weather", "currency", "stock_price", "random_quote", "cat_fact"],
            "operations": ["fetch", "query", "retrieve"],
            "data_sources": ["external_rest_apis"],
            "response_formats": ["json"]
        },
        "error_handling": {
            "failure_modes": ["api_timeout", "invalid_endpoint", "rate_limit", "network_error"],
            "recovery_strategy": "graceful_degradation",
            "rollback_capable": True
        }
    }


@app.get("/info")
async def node_info():
    return {
        "node_id": "external-api",
        "capabilities": ["weather_api", "currency_api", "stock_api", "general_apis"],
        "description": "Calls external APIs and returns structured data",
        "input_format": "api_parameters",
        "output_format": "json_response",
        "interaction_patterns": ["synchronous_stateless"],
        "supported_apis": ["weather", "currency", "stock_price", "random_quote", "cat_fact"]
    }


@app.post("/process")
async def process_data(request: NodeRequest):
    try:
        # Extract API parameters from metadata
        api_endpoint = request.metadata.get("api_endpoint", "weather")
        query_params = request.metadata.get("query_params", {})
        location = request.metadata.get("location", request.data)

        # Call the external API
        result = await call_external_api(api_endpoint, query_params, location)

        response = NodeResponse(
            data=json.dumps(result["api_response"]),
            status="success",
            metadata={
                "processed_by": "external-api",
                "pattern_used": "synchronous_stateless",
                "api_called": api_endpoint,
                "status_code": result["status_code"],
                "response_time": result["response_time"],
                "success": result.get("success", True),
                **request.metadata
            }
        )

        return response

    except Exception as e:
        return NodeResponse(
            data="",
            status="failed",
            metadata={
                "processed_by": "external-api",
                "error": str(e),
                **request.metadata
            }
        )


@app.post("/execute")
async def execute_api_call(inputs: dict, parameters: dict = {}):
    """Direct pattern-based execution for API calls"""

    if "api_endpoint" not in inputs:
        return {"error": "Missing required input: api_endpoint", "pattern": "synchronous_stateless"}

    api_endpoint = inputs["api_endpoint"]
    query_params = inputs.get("query_params", parameters.get("query_params", {}))
    location = inputs.get("location", parameters.get("location"))

    try:
        result = await call_external_api(api_endpoint, query_params, location)

        return {
            "outputs": {
                "api_response": result["api_response"],
                "status_code": result["status_code"],
                "response_time": result["response_time"]
            },
            "metadata": {
                "node_id": "external-api",
                "pattern": "synchronous_stateless",
                "api_called": api_endpoint,
                "success": result.get("success", True),
                "execution_time": f"{result['response_time']:.2f}s"
            }
        }

    except Exception as e:
        return {"error": str(e), "pattern": "synchronous_stateless"}


async def call_external_api(api_endpoint: str, query_params: dict, location: str = None) -> Dict[str, Any]:
    """Call external APIs based on endpoint type"""

    start_time = time.time()

    try:
        if api_endpoint == "weather":
            response = await call_weather_api(location or "London")
        elif api_endpoint == "currency":
            response = await call_currency_api(query_params)
        elif api_endpoint == "stock_price":
            response = await call_stock_api(query_params)
        elif api_endpoint == "random_quote":
            response = await call_quote_api()
        elif api_endpoint == "cat_fact":
            response = await call_cat_fact_api()
        else:
            raise ValueError(f"Unsupported API endpoint: {api_endpoint}")

        response_time = time.time() - start_time

        return {
            "api_response": response["data"],
            "status_code": response["status_code"],
            "response_time": response_time,
            "success": True
        }

    except Exception as e:
        response_time = time.time() - start_time
        return {
            "api_response": {"error": str(e)},
            "status_code": 500,
            "response_time": response_time,
            "success": False
        }


async def call_weather_api(location: str) -> Dict[str, Any]:
    """Call weather API (using a free service)"""
    try:
        # Using wttr.in which doesn't require API key
        url = f"http://wttr.in/{location}?format=j1"
        response = requests.get(url, timeout=8)

        if response.status_code == 200:
            weather_data = response.json()

            # Simplify the response
            current = weather_data.get("current_condition", [{}])[0]
            simplified = {
                "location": location,
                "temperature_c": current.get("temp_C"),
                "temperature_f": current.get("temp_F"),
                "humidity": current.get("humidity"),
                "description": current.get("weatherDesc", [{}])[0].get("value"),
                "wind_speed": current.get("windspeedKmph"),
                "timestamp": weather_data.get("current_condition", [{}])[0].get("observation_time")
            }

            return {"data": simplified, "status_code": 200}
        else:
            return {"data": {"error": "Weather service unavailable"}, "status_code": response.status_code}

    except Exception as e:
        return {"data": {"error": f"Weather API error: {str(e)}"}, "status_code": 500}


async def call_currency_api(query_params: dict) -> Dict[str, Any]:
    """Call currency exchange API (mock implementation)"""
    try:
        # Mock currency data (in production, use real API like exchangerate-api.com)
        base_currency = query_params.get("base", "USD")
        target_currency = query_params.get("target", "EUR")

        # Mock exchange rates
        mock_rates = {
            "USD": {"EUR": 0.85, "GBP": 0.75, "JPY": 110.0, "CAD": 1.25},
            "EUR": {"USD": 1.18, "GBP": 0.88, "JPY": 129.0, "CAD": 1.47},
            "GBP": {"USD": 1.33, "EUR": 1.14, "JPY": 146.0, "CAD": 1.67}
        }

        rate = mock_rates.get(base_currency, {}).get(target_currency, 1.0)

        result = {
            "base_currency": base_currency,
            "target_currency": target_currency,
            "exchange_rate": rate,
            "amount": query_params.get("amount", 1),
            "converted_amount": float(query_params.get("amount", 1)) * rate,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        return {"data": result, "status_code": 200}

    except Exception as e:
        return {"data": {"error": f"Currency API error: {str(e)}"}, "status_code": 500}


async def call_stock_api(query_params: dict) -> Dict[str, Any]:
    """Call stock price API (mock implementation)"""
    try:
        symbol = query_params.get("symbol", "AAPL")

        # Mock stock data
        import random
        mock_price = round(random.uniform(100, 200), 2)
        mock_change = round(random.uniform(-5, 5), 2)

        result = {
            "symbol": symbol.upper(),
            "price": mock_price,
            "change": mock_change,
            "change_percent": round((mock_change / mock_price) * 100, 2),
            "volume": random.randint(1000000, 10000000),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "note": "Mock data for demonstration"
        }

        return {"data": result, "status_code": 200}

    except Exception as e:
        return {"data": {"error": f"Stock API error: {str(e)}"}, "status_code": 500}


async def call_quote_api() -> Dict[str, Any]:
    """Call random quote API"""
    try:
        # Using quotable.io - a free quote API
        url = "http://api.quotable.io/random"
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            quote_data = response.json()
            result = {
                "quote": quote_data.get("content"),
                "author": quote_data.get("author"),
                "tags": quote_data.get("tags", []),
                "length": quote_data.get("length")
            }
            return {"data": result, "status_code": 200}
        else:
            return {"data": {"error": "Quote service unavailable"}, "status_code": response.status_code}

    except Exception as e:
        return {"data": {"error": f"Quote API error: {str(e)}"}, "status_code": 500}


async def call_cat_fact_api() -> Dict[str, Any]:
    """Call cat facts API"""
    try:
        # Using catfact.ninja - a free cat facts API
        url = "https://catfact.ninja/fact"
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            fact_data = response.json()
            result = {
                "fact": fact_data.get("fact"),
                "length": fact_data.get("length"),
                "category": "cat_facts"
            }
            return {"data": result, "status_code": 200}
        else:
            return {"data": {"error": "Cat facts service unavailable"}, "status_code": response.status_code}

    except Exception as e:
        return {"data": {"error": f"Cat facts API error: {str(e)}"}, "status_code": 500}


@app.get("/apis")
async def list_available_apis():
    """List all available API endpoints"""
    return {
        "available_apis": {
            "weather": {
                "description": "Get weather data for a location",
                "required_params": ["location"],
                "example": {"location": "London"}
            },
            "currency": {
                "description": "Get currency exchange rates",
                "required_params": ["base", "target"],
                "example": {"base": "USD", "target": "EUR", "amount": 100}
            },
            "stock_price": {
                "description": "Get stock price information",
                "required_params": ["symbol"],
                "example": {"symbol": "AAPL"}
            },
            "random_quote": {
                "description": "Get a random inspirational quote",
                "required_params": [],
                "example": {}
            },
            "cat_fact": {
                "description": "Get a random cat fact",
                "required_params": [],
                "example": {}
            }
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any, Set
import requests
import json
import os
from datetime import datetime
import uuid

# LangChain imports - kept for fallback scenarios
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain.prompts import PromptTemplate
from langchain.schema import Document

# Pattern framework import
import sys

sys.path.append('/app')

try:
    from interaction_patterns import INTERACTION_PATTERNS, PatternRegistry
except ImportError:
    print("Warning: interaction_patterns.py not found, using basic pattern support")
    INTERACTION_PATTERNS = {}

app = FastAPI(title="Service Registry", description="Contract-based service discovery and orchestration")


# Models
class ServiceCapability(BaseModel):
    name: str
    description: str
    input_format: str
    output_format: str
    examples: List[str] = []


class ServiceRegistration(BaseModel):
    node_id: str
    url: str
    capabilities: List[ServiceCapability]
    description: str
    tags: List[str] = []
    health_endpoint: str = "/health"
    process_endpoint: str = "/process"
    contract_endpoint: str = "/contract"
    interaction_patterns: List[str] = []
    pattern_interfaces: Dict[str, Dict] = {}


class OrchestrationRequest(BaseModel):
    command: str
    data: Any
    context: Dict = {}


class GeneratedChain(BaseModel):
    chain_id: str
    command: str
    nodes: List[str]
    reasoning: str
    confidence: float
    verification_result: Dict = {}


class ServiceContract(BaseModel):
    service_metadata: Dict
    interface_contract: Dict
    behavioral_guarantees: Dict
    resource_requirements: Dict
    compatibility_rules: Dict


class ContractRegistry:
    """Manages service contracts and compatibility verification"""

    def __init__(self):
        self.contracts = {}
        self.compatibility_cache = {}
        self.type_compatibility_rules = {
            "string": ["string", "text", "any"],
            "integer": ["integer", "number", "any"],
            "object": ["object", "dict", "any"],
            "array": ["array", "list", "any"],
            "any": ["string", "integer", "object", "array", "any"]
        }

    def register_contract(self, service_id: str, contract: Dict) -> bool:
        """Register a service contract and validate its structure"""
        try:
            # Validate required fields
            required_sections = ["service_metadata", "interface_contract", "behavioral_guarantees"]
            for section in required_sections:
                if section not in contract:
                    raise ValueError(f"Missing required section: {section}")

            # Store contract
            self.contracts[service_id] = contract

            # Clear compatibility cache when new service added
            self.compatibility_cache.clear()

            print(f"Registered contract for {service_id}")
            return True

        except Exception as e:
            print(f"Error registering contract for {service_id}: {e}")
            return False

    def get_contract(self, service_id: str) -> Optional[Dict]:
        """Get contract for a specific service"""
        return self.contracts.get(service_id)

    def verify_chain_compatibility(self, service_chain: List[str]) -> Dict:
        """Verify that a chain of services can work together"""
        if len(service_chain) < 2:
            return {"compatible": True, "reasoning": "Single service, no chaining needed"}

        verification_result = {
            "compatible": True,
            "reasoning": "",
            "type_checks": [],
            "pattern_checks": [],
            "resource_estimates": {},
            "errors": []
        }

        total_execution_time = 0
        total_memory = 0

        for i in range(len(service_chain) - 1):
            current_service = service_chain[i]
            next_service = service_chain[i + 1]

            current_contract = self.contracts.get(current_service)
            next_contract = self.contracts.get(next_service)

            if not current_contract or not next_contract:
                verification_result["compatible"] = False
                verification_result["errors"].append(f"Missing contract for {current_service} or {next_service}")
                continue

            # Type compatibility check
            type_check = self._check_type_compatibility(current_contract, next_contract)
            verification_result["type_checks"].append({
                "from": current_service,
                "to": next_service,
                "compatible": type_check["compatible"],
                "details": type_check
            })

            if not type_check["compatible"]:
                verification_result["compatible"] = False
                verification_result["errors"].append(f"Type incompatibility: {current_service} → {next_service}")

            # Pattern compatibility check
            pattern_check = self._check_pattern_compatibility(current_contract, next_contract)
            verification_result["pattern_checks"].append({
                "from": current_service,
                "to": next_service,
                "compatible": pattern_check["compatible"],
                "details": pattern_check
            })

            if not pattern_check["compatible"]:
                verification_result["compatible"] = False
                verification_result["errors"].append(f"Pattern incompatibility: {current_service} → {next_service}")

            # Resource estimation
            if "resource_requirements" in current_contract:
                resources = current_contract["resource_requirements"]
                if "max_execution_time" in resources:
                    time_str = resources["max_execution_time"]
                    time_ms = self._parse_time_to_ms(time_str)
                    total_execution_time += time_ms

                if "memory_limit" in resources:
                    memory_str = resources["memory_limit"]
                    memory_mb = self._parse_memory_to_mb(memory_str)
                    total_memory = max(total_memory, memory_mb)  # Peak memory usage

        verification_result["resource_estimates"] = {
            "total_execution_time_ms": total_execution_time,
            "peak_memory_mb": total_memory
        }

        if verification_result["compatible"]:
            verification_result["reasoning"] = f"Chain verified: {len(service_chain)} services compatible"
        else:
            verification_result["reasoning"] = f"Chain verification failed: {len(verification_result['errors'])} errors"

        return verification_result

    def _check_type_compatibility(self, current_contract: Dict, next_contract: Dict) -> Dict:
        """Check if output types of current service match input types of next service"""
        current_outputs = current_contract.get("interface_contract", {}).get("outputs", {})
        next_inputs = next_contract.get("interface_contract", {}).get("inputs", {})

        # Find primary output (usually 'text', 'data', or first output)
        primary_output_key = None
        primary_output_type = None

        for key, output_spec in current_outputs.items():
            if key in ["text", "data", "result"]:  # Prioritize common output names
                primary_output_key = key
                primary_output_type = output_spec.get("type")
                break

        if not primary_output_key and current_outputs:
            # Take first output if no preferred name found
            primary_output_key = list(current_outputs.keys())[0]
            primary_output_type = current_outputs[primary_output_key].get("type")

        # Find primary input (usually 'text', 'data', or first required input)
        primary_input_key = None
        primary_input_type = None

        for key, input_spec in next_inputs.items():
            if input_spec.get("constraints", {}).get("required", True):
                if key in ["text", "data", "input"]:
                    primary_input_key = key
                    primary_input_type = input_spec.get("type")
                    break

        if not primary_input_key and next_inputs:
            # Take first required input if no preferred name found
            for key, input_spec in next_inputs.items():
                if input_spec.get("constraints", {}).get("required", True):
                    primary_input_key = key
                    primary_input_type = input_spec.get("type")
                    break

        # Check compatibility
        compatible = False
        reasoning = ""

        if not primary_output_type or not primary_input_type:
            compatible = False
            reasoning = "Missing type information"
        else:
            # Check if types are compatible
            output_compatible_types = self.type_compatibility_rules.get(primary_output_type, [primary_output_type])
            if primary_input_type in output_compatible_types or primary_input_type == "any":
                compatible = True
                reasoning = f"Output {primary_output_type} compatible with input {primary_input_type}"
            else:
                compatible = False
                reasoning = f"Output {primary_output_type} incompatible with input {primary_input_type}"

        return {
            "compatible": compatible,
            "reasoning": reasoning,
            "output_type": primary_output_type,
            "input_type": primary_input_type,
            "output_key": primary_output_key,
            "input_key": primary_input_key
        }

    def _check_pattern_compatibility(self, current_contract: Dict, next_contract: Dict) -> Dict:
        """Check if interaction patterns can be chained together"""
        current_pattern = current_contract.get("service_metadata", {}).get("pattern")
        next_pattern = next_contract.get("service_metadata", {}).get("pattern")

        # Pattern compatibility rules
        pattern_compatibility = {
            "synchronous_stateless": ["synchronous_stateless", "synchronous_persistent", "synchronous_session_based"],
            "synchronous_persistent": ["synchronous_stateless", "synchronous_persistent"],
            "synchronous_session_based": ["synchronous_stateless", "synchronous_persistent",
                                          "synchronous_session_based"],
            "asynchronous_stateless": ["synchronous_stateless", "synchronous_persistent"],
            "streaming_stateless": ["streaming_stateless", "synchronous_stateless"],
            "event_driven_stateless": ["synchronous_stateless", "event_driven_stateless"]
        }

        compatible_patterns = pattern_compatibility.get(current_pattern, [])
        compatible = next_pattern in compatible_patterns

        return {
            "compatible": compatible,
            "reasoning": f"Pattern {current_pattern} → {next_pattern}: {'✓' if compatible else '✗'}",
            "current_pattern": current_pattern,
            "next_pattern": next_pattern
        }

    def _parse_time_to_ms(self, time_str: str) -> int:
        """Parse time strings like '100ms', '1s' to milliseconds"""
        if time_str.endswith("ms"):
            return int(time_str[:-2])
        elif time_str.endswith("s"):
            return int(time_str[:-1]) * 1000
        else:
            return 1000  # Default 1 second

    def _parse_memory_to_mb(self, memory_str: str) -> int:
        """Parse memory strings like '50MB', '1GB' to megabytes"""
        if memory_str.endswith("MB"):
            return int(memory_str[:-2])
        elif memory_str.endswith("GB"):
            return int(memory_str[:-2]) * 1024
        else:
            return 100  # Default 100MB

    def find_services_by_capability(self, capability_requirements: List[str]) -> List[str]:
        """Find services that meet specific capability requirements"""
        matching_services = []

        for service_id, contract in self.contracts.items():
            service_capabilities = self._extract_capabilities(contract)

            # Check if service has all required capabilities
            if all(req in service_capabilities for req in capability_requirements):
                matching_services.append(service_id)

        return matching_services

    def _extract_capabilities(self, contract: Dict) -> Set[str]:
        """Extract capabilities from a service contract"""
        capabilities = set()

        # Extract from metadata description
        description = contract.get("service_metadata", {}).get("description", "").lower()

        # Extract from explicit capabilities section
        if "capabilities" in contract:
            for cap_list in contract["capabilities"].values():
                if isinstance(cap_list, list):
                    capabilities.update(cap_list)

        # Extract from interface operations
        interface = contract.get("interface_contract", {})
        inputs = interface.get("inputs", {})

        if "operation" in inputs:
            operation_spec = inputs["operation"]
            if "values" in operation_spec:
                capabilities.update(operation_spec["values"])

        # Infer capabilities from patterns and descriptions
        if "transform" in description:
            capabilities.add("text_transformation")
        if "store" in description or "storage" in description:
            capabilities.add("persistent_storage")
        if "echo" in description or "pass" in description:
            capabilities.add("passthrough")

        return capabilities


# Global variables
embeddings = None
vectorstore = None
llm = None
service_registry = {}
contract_registry = ContractRegistry()
vector_store_path = "service_registry_vectorstore"
pattern_registry = PatternRegistry() if 'PatternRegistry' in globals() else None


def initialize_rag_system():
    """Initialize the RAG system for fallback scenarios"""
    global embeddings, vectorstore, llm

    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        cache_folder="./models"
    )

    llm = ChatAnthropic(
        model="claude-3-5-sonnet-20241022",
        anthropic_api_key=os.getenv("CLAUDE_API_KEY"),
        temperature=0.1,
        max_tokens=1000
    )


def generate_contract_based_chain(command: str, available_services: List[str]) -> GeneratedChain:
    """Generate service chain using contract-based reasoning"""

    # Parse command to extract required capabilities
    required_capabilities = parse_command_requirements(command)

    # Find services that match capabilities
    matching_services = []
    for service_id in available_services:
        contract = contract_registry.get_contract(service_id)
        if contract:
            service_capabilities = contract_registry._extract_capabilities(contract)
            capability_match_score = len(required_capabilities.intersection(service_capabilities))
            if capability_match_score > 0:
                matching_services.append((service_id, capability_match_score))

    # Sort by capability match score
    matching_services.sort(key=lambda x: x[1], reverse=True)

    # Try to build a chain
    if not matching_services:
        return GeneratedChain(
            chain_id=str(uuid.uuid4()),
            command=command,
            nodes=[],
            reasoning="No services found matching required capabilities",
            confidence=0.0
        )

    # Simple chain building: try different combinations
    best_chain = None
    best_verification = None
    best_confidence = 0.0

    # Try single service
    for service_id, score in matching_services:
        chain = [service_id]
        verification = contract_registry.verify_chain_compatibility(chain)
        confidence = 0.7 if verification["compatible"] else 0.0

        if confidence > best_confidence:
            best_chain = chain
            best_verification = verification
            best_confidence = confidence

    # Try two-service chains for complex commands
    if len(required_capabilities) > 1:
        for i, (service1, score1) in enumerate(matching_services[:3]):
            for j, (service2, score2) in enumerate(matching_services[:3]):
                if i != j:
                    chain = [service1, service2]
                    verification = contract_registry.verify_chain_compatibility(chain)
                    confidence = 0.9 if verification["compatible"] else 0.0

                    if confidence > best_confidence:
                        best_chain = chain
                        best_verification = verification
                        best_confidence = confidence

    reasoning = best_verification["reasoning"] if best_verification else "No compatible chain found"

    return GeneratedChain(
        chain_id=str(uuid.uuid4()),
        command=command,
        nodes=best_chain or [],
        reasoning=reasoning,
        confidence=best_confidence,
        verification_result=best_verification or {}
    )


def parse_command_requirements(command: str) -> Set[str]:
    """Parse natural language command to extract required capabilities"""
    command_lower = command.lower()
    requirements = set()

    # Text transformation keywords
    if any(word in command_lower for word in ["uppercase", "lowercase", "transform", "convert", "change"]):
        requirements.add("text_transformation")

    # Storage keywords
    if any(word in command_lower for word in ["store", "save", "persist", "keep"]):
        requirements.add("persistent_storage")

    # Passthrough keywords
    if any(word in command_lower for word in ["echo", "pass", "forward"]):
        requirements.add("passthrough")

    return requirements


async def fetch_service_contract(service_url: str, contract_endpoint: str = "/contract") -> Optional[Dict]:
    """Fetch contract from a service"""
    try:
        contract_url = f"{service_url}{contract_endpoint}"
        response = requests.get(contract_url, timeout=10)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to fetch contract from {contract_url}: {response.status_code}")
            return None

    except Exception as e:
        print(f"Error fetching contract from {service_url}: {e}")
        return None


# Initialize on startup
initialize_rag_system()


# API Endpoints
@app.on_event("startup")
async def startup_event():
    """Register default services and fetch their contracts"""

    default_services = [
        ServiceRegistration(
            node_id="echo-node",
            url="http://echo-node:8000",
            description="Receives and forwards data without modification",
            capabilities=[
                ServiceCapability(
                    name="echo",
                    description="Passes data through unchanged",
                    input_format="string",
                    output_format="string",
                    examples=["echo hello world", "pass through this text"]
                )
            ],
            tags=["utility", "passthrough"],
            interaction_patterns=["synchronous_stateless"]
        ),
        ServiceRegistration(
            node_id="transform-node",
            url="http://transform-node:8000",
            description="Transforms text data in various ways",
            capabilities=[
                ServiceCapability(
                    name="uppercase",
                    description="Converts text to uppercase",
                    input_format="string",
                    output_format="string",
                    examples=["make this uppercase", "convert to caps", "transform text"]
                )
            ],
            tags=["text", "transformation"],
            interaction_patterns=["synchronous_stateless"]
        ),
        ServiceRegistration(
            node_id="storage-node",
            url="http://storage-node:8000",
            description="Stores data with metadata and provides retrieval",
            capabilities=[
                ServiceCapability(
                    name="store",
                    description="Saves data to persistent storage",
                    input_format="string",
                    output_format="storage_id",
                    examples=["save this data", "store text", "persist information"]
                )
            ],
            tags=["storage", "persistence", "database"],
            interaction_patterns=["synchronous_persistent"]
        )
    ]

    # Register each service and fetch its contract
    for service in default_services:
        service_registry[service.node_id] = service.dict()

        # Fetch and register contract
        contract = await fetch_service_contract(service.url)
        if contract:
            contract_registry.register_contract(service.node_id, contract)
        else:
            print(f"Warning: Could not fetch contract for {service.node_id}")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "service-registry",
        "registered_services": len(service_registry),
        "registered_contracts": len(contract_registry.contracts)
    }


@app.get("/contracts")
async def list_contracts():
    """List all registered service contracts"""
    return {
        "contracts": contract_registry.contracts,
        "count": len(contract_registry.contracts)
    }


@app.get("/contracts/{service_id}")
async def get_service_contract(service_id: str):
    """Get contract for a specific service"""
    contract = contract_registry.get_contract(service_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


@app.post("/orchestrate/contract-based")
async def orchestrate_with_contracts(request: OrchestrationRequest):
    """Generate orchestration chain using contract-based reasoning"""

    available_services = list(contract_registry.contracts.keys())

    if not available_services:
        return {
            "error": "No services with contracts available",
            "command": request.command
        }

    # Generate chain using contract-based reasoning
    chain = generate_contract_based_chain(request.command, available_services)

    return {
        "chain_id": chain.chain_id,
        "command": request.command,
        "generated_chain": chain.nodes,
        "reasoning": chain.reasoning,
        "confidence": chain.confidence,
        "verification_result": chain.verification_result,
        "method": "contract_based"
    }


@app.post("/execute/contract-verified")
async def execute_contract_verified_chain(request: OrchestrationRequest):
    """Execute chain with full contract verification"""

    # Generate the chain
    orchestration_result = await orchestrate_with_contracts(request)

    if "error" in orchestration_result:
        return orchestration_result

    if orchestration_result["confidence"] < 0.5:
        return {
            "error": "Low confidence in generated chain",
            "details": orchestration_result
        }

    # Verify the chain before execution
    verification = contract_registry.verify_chain_compatibility(orchestration_result["generated_chain"])

    if not verification["compatible"]:
        return {
            "error": "Chain failed contract verification",
            "verification_details": verification,
            "orchestration": orchestration_result
        }

    # Execute the verified chain
    valid_nodes = orchestration_result["generated_chain"]
    current_data = request.data
    execution_results = []

    for node_id in valid_nodes:
        try:
            service_info = service_registry[node_id]
            node_url = f"{service_info['url']}{service_info.get('process_endpoint', '/process')}"

            payload = {
                "data": current_data,
                "metadata": {
                    "chain_id": orchestration_result["chain_id"],
                    "step": len(execution_results),
                    "total_steps": len(valid_nodes),
                    "orchestrated_by": "contract-verified-registry",
                    "verification_passed": True
                }
            }

            response = requests.post(node_url, json=payload, timeout=30)

            if response.status_code == 200:
                result = response.json()
                execution_results.append({
                    "node": node_id,
                    "status": "success",
                    "result": result
                })
                current_data = result.get("data", current_data)
            else:
                execution_results.append({
                    "node": node_id,
                    "status": "failed",
                    "error": f"HTTP {response.status_code}: {response.text}"
                })
                break

        except Exception as e:
            execution_results.append({
                "node": node_id,
                "status": "failed",
                "error": str(e)
            })
            break

    return {
        "chain_id": orchestration_result["chain_id"],
        "command": request.command,
        "orchestration": orchestration_result,
        "verification": verification,
        "execution_results": execution_results,
        "final_data": current_data,
        "status": "completed" if all(r["status"] == "success" for r in execution_results) else "failed"
    }


# Keep existing endpoints for backward compatibility
@app.get("/services")
async def list_services():
    """List all registered services"""
    return {"services": service_registry, "count": len(service_registry)}


@app.post("/orchestrate")
async def orchestrate_command(request: OrchestrationRequest):
    """Legacy orchestration endpoint - redirects to contract-based"""
    return await orchestrate_with_contracts(request)


@app.post("/execute")
async def execute_orchestrated_chain(request: OrchestrationRequest):
    """Legacy execution endpoint - redirects to contract-verified"""
    return await execute_contract_verified_chain(request)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
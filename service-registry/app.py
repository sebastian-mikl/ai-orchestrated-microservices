from contextlib import asynccontextmanager

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    print("Service Registry starting up...")
    print("Waiting for services to auto-register...")

    # Remove all the hardcoded service registration code
    # Services will now register themselves

    print("Service Registry ready - services will register automatically")
    yield

    # Shutdown
    print("Service Registry shutting down...")

app = FastAPI(
    title="Service Registry",
    description="Contract-based service discovery and orchestration",
    lifespan=lifespan)
# Add this /info endpoint to service-registry/app.py

@app.get("/info")
async def node_info():
    """Standardized service discovery information for Service Registry"""
    return {
        # REQUIRED FIELDS
        "node_id": "service-registry",
        "version": "1.0.0",
        "status": "healthy",
        "description": "AI-powered service discovery and orchestration using LangChain RAG with contract-based verification",

        # CAPABILITY DISCOVERY
        "capabilities": [
            "service_discovery",
            "ai_orchestration",
            "contract_verification",
            "chain_generation",
            "rag_search",
            "service_registration"
        ],
        "tags": ["registry", "orchestration", "ai", "discovery", "contracts"],

        # DATA CONTRACTS
        "input_format": "natural_language_command",
        "output_format": "execution_result",
        "supported_operations": ["orchestrate", "execute", "search", "register"],

        # INTERACTION PATTERNS
        "interaction_patterns": ["synchronous_stateless", "asynchronous_stateless"],
        "pattern_interfaces": {
            "synchronous_stateless": {
                "inputs": {
                    "command": "string",
                    "data": "any"
                },
                "outputs": {
                    "generated_chain": "array",
                    "execution_results": "array",
                    "final_data": "any"
                },
                "parameters": {
                    "method": {
                        "type": "string",
                        "options": ["contract_based", "rag_based"],
                        "default": "contract_based"
                    }
                }
            }
        },

        # SERVICE METADATA
        "endpoints": {
            "health": "/health",
            "orchestrate": "/orchestrate",
            "execute": "/execute",
            "register": "/register",
            "unregister": "/unregister/{service_id}",
            "services": "/services",
            "contracts": "/contracts",
            "services/health": "/services/health",
            "services/cleanup": "/services/cleanup",
            "info": "/info"
        },
        "dependencies": ["claude_api", "huggingface_embeddings"],
        "provides_to": ["all_services"],  # Central orchestrator

        # OPERATIONAL INFO
        "resource_requirements": {
            "cpu": "high",
            "memory": "1GB",  # For vector embeddings
            "disk": "persistent"  # For vector store
        },
        "scaling": {
            "can_scale_horizontal": False,  # Central registry
            "max_instances": 1,
            "startup_time": "30s"  # Vector loading time
        },

        # PROCESSING CHARACTERISTICS
        "processing_type": "orchestration",
        "data_transformation": "command_to_execution_chain",
        "typical_use_cases": [
            "Natural language command processing",
            "Service chain orchestration",
            "Dynamic service discovery",
            "Contract-based verification"
        ],
        "ai_capabilities": {
            "nlp_model": "claude-3-5-sonnet",
            "embedding_model": "all-MiniLM-L6-v2",
            "vector_store": "FAISS",
            "confidence_scoring": True,
            "semantic_search": True,
            "contract_verification": True
        },
        "registry_stats": {
            "registered_services": len(service_registry),
            "registered_contracts": len(contract_registry.contracts) if 'contract_registry' in globals() else 0,
            "total_orchestrations": 0,  # Could track this
            "average_confidence": 0.85  # Could calculate this
        }
    }

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


# Add these endpoints to service-registry/app.py

@app.delete("/unregister/{service_id}")
async def unregister_service(service_id: str):
    """Unregister a service"""
    if service_id in service_registry:
        del service_registry[service_id]

        # Also remove from contract registry
        if service_id in contract_registry.contracts:
            del contract_registry.contracts[service_id]
            contract_registry.compatibility_cache.clear()

        print(f"Unregistered service: {service_id}")
        return {"status": "unregistered", "service_id": service_id}
    else:
        raise HTTPException(status_code=404, detail="Service not found")


@app.get("/services/health")
async def check_all_services_health():
    """Check health status of all registered services"""
    health_status = {}

    for service_id, service_info in service_registry.items():
        try:
            service_url = service_info["url"]
            health_endpoint = service_info.get("health_endpoint", "/health")

            response = requests.get(
                f"{service_url}{health_endpoint}",
                timeout=5
            )

            if response.status_code == 200:
                health_status[service_id] = {
                    "status": "healthy",
                    "response_time": response.elapsed.total_seconds(),
                    "details": response.json()
                }
            else:
                health_status[service_id] = {
                    "status": "unhealthy",
                    "http_status": response.status_code,
                    "url": f"{service_url}{health_endpoint}"
                }

        except Exception as e:
            health_status[service_id] = {
                "status": "unreachable",
                "error": str(e),
                "url": service_info.get("url", "unknown")
            }

    # Remove unreachable services after multiple failures
    unreachable_services = [
        service_id for service_id, status in health_status.items()
        if status["status"] == "unreachable"
    ]

    return {
        "total_services": len(service_registry),
        "healthy_services": len([s for s in health_status.values() if s["status"] == "healthy"]),
        "unhealthy_services": len([s for s in health_status.values() if s["status"] == "unhealthy"]),
        "unreachable_services": len(unreachable_services),
        "details": health_status,
        "unreachable_will_be_removed": unreachable_services
    }


@app.post("/services/cleanup")
async def cleanup_unreachable_services():
    """Remove services that are no longer reachable"""
    health_check = await check_all_services_health()
    removed_services = []

    for service_id, status in health_check["details"].items():
        if status["status"] == "unreachable":
            if service_id in service_registry:
                del service_registry[service_id]
                removed_services.append(service_id)

            if service_id in contract_registry.contracts:
                del contract_registry.contracts[service_id]

    contract_registry.compatibility_cache.clear()

    return {
        "removed_services": removed_services,
        "remaining_services": len(service_registry)
    }


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


# Replace the /register endpoint in service-registry/app.py

@app.post("/register")
async def register_service(service: ServiceRegistration):
    """Services auto-register on startup"""
    print(f"Registering service: {service.node_id}")

    # Store service info
    service_registry[service.node_id] = service.model_dump()

    # Fetch contract from the service
    contract = await fetch_service_contract(service.url)
    if contract:
        success = contract_registry.register_contract(service.node_id, contract)
        if success:
            print(f"Successfully registered contract for {service.node_id}")
        else:
            print(f"Failed to register contract for {service.node_id}")
    else:
        print(f"Warning: Could not fetch contract for {service.node_id}")

    print(f"Service registry now has {len(service_registry)} services")
    print(f"Contract registry now has {len(contract_registry.contracts)} contracts")

    return {"status": "registered", "node_id": service.node_id}


# Also add this debug endpoint to check what's happening:

@app.get("/debug/registration")
async def debug_registration():
    """Debug endpoint to see registration status"""
    return {
        "services_registered": len(service_registry),
        "contracts_registered": len(contract_registry.contracts),
        "service_list": list(service_registry.keys()),
        "contract_list": list(contract_registry.contracts.keys()),
        "service_details": service_registry,
        "contract_details": {k: "contract_exists" for k in contract_registry.contracts.keys()}
    }

@app.delete("/unregister/{service_id}")
async def unregister_service(service_id: str):
    """Remove services dynamically"""
    # Cleanup logic


# API Endpoints



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
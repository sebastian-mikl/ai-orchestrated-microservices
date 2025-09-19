from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import requests
import json
import os
from datetime import datetime
import uuid

# LangChain imports
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.schema import Document

app = FastAPI(title="Service Registry", description="RAG-powered service discovery and orchestration")


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


# Global variables
embeddings = None
vectorstore = None
llm = None
service_registry = {}
vector_store_path = "service_registry_vectorstore"


def initialize_rag_system():
    """Initialize the RAG system for service discovery"""
    global embeddings, vectorstore, llm

    # Initialize embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        cache_folder="./models"
    )

    # Initialize LLM
    llm = ChatAnthropic(
        model="claude-3-5-sonnet-20241022",
        anthropic_api_key=os.getenv("CLAUDE_API_KEY"),
        temperature=0.1,
        max_tokens=1000
    )

    # Load existing vector store or create empty one
    load_or_create_vectorstore()


def load_or_create_vectorstore():
    """Load existing vector store or create a new one"""
    global vectorstore

    if os.path.exists(vector_store_path):
        try:
            vectorstore = FAISS.load_local(
                vector_store_path,
                embeddings,
                allow_dangerous_deserialization=True
            )
            print("Loaded existing service registry vector store")
        except Exception as e:
            print(f"Error loading vector store: {e}, creating new one")
            create_empty_vectorstore()
    else:
        create_empty_vectorstore()


def create_empty_vectorstore():
    """Create an empty vector store with a placeholder document"""
    global vectorstore

    placeholder_doc = Document(
        page_content="Service registry placeholder",
        metadata={"type": "placeholder"}
    )
    vectorstore = FAISS.from_documents([placeholder_doc], embeddings)
    vectorstore.save_local(vector_store_path)


def create_service_document(service: ServiceRegistration) -> Document:
    """Convert service registration to a searchable document"""

    # Create comprehensive text description
    capabilities_text = "\n".join([
        f"- {cap.name}: {cap.description} (input: {cap.input_format}, output: {cap.output_format})"
        for cap in service.capabilities
    ])

    examples_text = "\n".join([
        f"Example: {example}"
        for cap in service.capabilities
        for example in cap.examples
    ])

    document_content = f"""
Service: {service.node_id}
Description: {service.description}
URL: {service.url}
Tags: {', '.join(service.tags)}

Capabilities:
{capabilities_text}

{examples_text}
    """.strip()

    metadata = {
        "node_id": service.node_id,
        "url": service.url,
        "tags": service.tags,
        "capability_names": [cap.name for cap in service.capabilities]
    }

    return Document(page_content=document_content, metadata=metadata)


def update_vectorstore_with_service(service: ServiceRegistration):
    """Add or update a service in the vector store"""
    global vectorstore

    # Remove existing documents for this service
    if service.node_id in service_registry:
        # For now, we'll recreate the whole vector store
        # In production, you'd want incremental updates
        rebuild_vectorstore()
    else:
        # Add new service document
        service_doc = create_service_document(service)
        vectorstore.add_documents([service_doc])
        vectorstore.save_local(vector_store_path)


def rebuild_vectorstore():
    """Rebuild the entire vector store from current service registry"""
    global vectorstore

    if not service_registry:
        create_empty_vectorstore()
        return

    # Create documents for all registered services
    documents = []
    for service_data in service_registry.values():
        service = ServiceRegistration(**service_data)
        documents.append(create_service_document(service))

    # Recreate vector store
    vectorstore = FAISS.from_documents(documents, embeddings)
    vectorstore.save_local(vector_store_path)


def find_relevant_services(query: str, k: int = 5) -> List[Dict]:
    """Find services relevant to the given query using RAG"""

    if not vectorstore:
        return []

    try:
        # Search for relevant services
        docs = vectorstore.similarity_search(query, k=k)

        relevant_services = []
        for doc in docs:
            if doc.metadata.get("type") == "placeholder":
                continue

            node_id = doc.metadata.get("node_id")
            if node_id and node_id in service_registry:
                service_data = service_registry[node_id].copy()
                service_data["relevance_content"] = doc.page_content[:200]
                relevant_services.append(service_data)

        return relevant_services

    except Exception as e:
        print(f"Error in service search: {e}")
        return []


def generate_orchestration_chain(command: str, available_services: List[Dict]) -> GeneratedChain:
    """Use LLM to generate an orchestration chain from available services"""

    # Prepare service descriptions for the prompt
    service_descriptions = []
    for service in available_services:
        caps = ", ".join([cap["name"] for cap in service["capabilities"]])
        service_descriptions.append(f"- {service['node_id']}: {service['description']} (capabilities: {caps})")

    services_text = "\n".join(service_descriptions)

    prompt_template = PromptTemplate(
        input_variables=["command", "services"],
        template="""
You are an AI orchestrator that creates execution chains from available microservices.

User Command: {command}

Available Services:
{services}

Create an execution chain to fulfill the user's command. Consider:
1. What steps are needed to complete the task?
2. Which services can handle each step?
3. What order should they execute in?
4. Are all required capabilities available?

Respond in this exact JSON format:
{{
    "nodes": ["service1", "service2", "service3"],
    "reasoning": "Explanation of why this chain was chosen",
    "confidence": 0.85,
    "missing_capabilities": ["capability1", "capability2"] or []
}}

If the command cannot be fulfilled with available services, set confidence to 0.0 and explain in reasoning.
"""
    )

    try:
        # Generate the chain
        chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
            return_source_documents=False
        )

        # Use the prompt directly with LLM
        formatted_prompt = prompt_template.format(
            command=command,
            services=services_text
        )

        response = llm.invoke(formatted_prompt)

        # Parse the response
        try:
            # Extract JSON from response
            response_text = response.content if hasattr(response, 'content') else str(response)

            # Find JSON in the response
            start = response_text.find('{')
            end = response_text.rfind('}') + 1

            if start != -1 and end != -1:
                json_str = response_text[start:end]
                parsed_response = json.loads(json_str)

                return GeneratedChain(
                    chain_id=str(uuid.uuid4()),
                    command=command,
                    nodes=parsed_response.get("nodes", []),
                    reasoning=parsed_response.get("reasoning", "No reasoning provided"),
                    confidence=parsed_response.get("confidence", 0.0)
                )
            else:
                raise ValueError("No valid JSON found in response")

        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error parsing LLM response: {e}")
            return GeneratedChain(
                chain_id=str(uuid.uuid4()),
                command=command,
                nodes=[],
                reasoning=f"Error parsing orchestration response: {e}",
                confidence=0.0
            )

    except Exception as e:
        print(f"Error generating orchestration chain: {e}")
        return GeneratedChain(
            chain_id=str(uuid.uuid4()),
            command=command,
            nodes=[],
            reasoning=f"Error in chain generation: {e}",
            confidence=0.0
        )


# Initialize on startup
initialize_rag_system()


# API Endpoints
@app.on_event("startup")
async def startup_event():
    """Register default services on startup"""

    # Register existing services from your network
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
            tags=["utility", "passthrough"]
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
            tags=["text", "transformation"]
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
                ),
                ServiceCapability(
                    name="retrieve",
                    description="Retrieves stored data by ID",
                    input_format="storage_id",
                    output_format="string",
                    examples=["get stored data", "retrieve by id", "fetch information"]
                )
            ],
            tags=["storage", "persistence", "database"]
        )
    ]

    # Register each service
    for service in default_services:
        service_registry[service.node_id] = service.dict()

    # Rebuild vector store with all services
    rebuild_vectorstore()


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "service-registry", "registered_services": len(service_registry)}


@app.post("/register")
async def register_service(service: ServiceRegistration):
    """Register a new service with the registry"""

    # Store service registration
    service_registry[service.node_id] = service.dict()

    # Update vector store
    update_vectorstore_with_service(service)

    return {
        "status": "registered",
        "node_id": service.node_id,
        "message": f"Service {service.node_id} registered successfully"
    }


@app.delete("/unregister/{node_id}")
async def unregister_service(node_id: str):
    """Remove a service from the registry"""

    if node_id not in service_registry:
        raise HTTPException(status_code=404, detail="Service not found")

    del service_registry[node_id]

    # Rebuild vector store without this service
    rebuild_vectorstore()

    return {"status": "unregistered", "node_id": node_id}


@app.get("/services")
async def list_services():
    """List all registered services"""
    return {"services": service_registry, "count": len(service_registry)}


@app.get("/services/search/{query}")
async def search_services(query: str, limit: int = 5):
    """Search for services using natural language"""

    relevant_services = find_relevant_services(query, k=limit)

    return {
        "query": query,
        "found": len(relevant_services),
        "services": relevant_services
    }


@app.post("/orchestrate")
async def orchestrate_command(request: OrchestrationRequest):
    """Generate and optionally execute an orchestration chain"""

    # Find relevant services for this command
    relevant_services = find_relevant_services(request.command, k=10)

    if not relevant_services:
        return {
            "error": "No relevant services found",
            "command": request.command,
            "available_services": len(service_registry)
        }

    # Generate orchestration chain
    chain = generate_orchestration_chain(request.command, relevant_services)

    # Validate that all nodes in chain exist
    valid_nodes = []
    invalid_nodes = []

    for node_id in chain.nodes:
        if node_id in service_registry:
            valid_nodes.append(node_id)
        else:
            invalid_nodes.append(node_id)

    return {
        "chain_id": chain.chain_id,
        "command": request.command,
        "generated_chain": chain.nodes,
        "valid_nodes": valid_nodes,
        "invalid_nodes": invalid_nodes,
        "reasoning": chain.reasoning,
        "confidence": chain.confidence,
        "relevant_services_found": len(relevant_services)
    }


@app.post("/execute")
async def execute_orchestrated_chain(request: OrchestrationRequest):
    """Generate and execute an orchestration chain"""

    # First generate the chain
    orchestration_result = await orchestrate_command(request)

    if "error" in orchestration_result:
        return orchestration_result

    if orchestration_result["confidence"] < 0.5:
        return {
            "error": "Low confidence in generated chain",
            "details": orchestration_result
        }

    if orchestration_result["invalid_nodes"]:
        return {
            "error": "Chain contains invalid nodes",
            "details": orchestration_result
        }

    # Execute the valid chain
    valid_nodes = orchestration_result["valid_nodes"]

    if not valid_nodes:
        return {
            "error": "No valid nodes to execute",
            "details": orchestration_result
        }

    # Execute chain step by step
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
                    "orchestrated_by": "service-registry"
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
        "execution_results": execution_results,
        "final_data": current_data,
        "status": "completed" if all(r["status"] == "success" for r in execution_results) else "failed"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
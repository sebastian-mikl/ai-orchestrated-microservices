#!/usr/bin/env python3
"""
Integrated LLM + Analyzer Script
Combines your working analyzer with LLM enhancements
"""

import json
import requests
from typing import Dict, List, Optional
import sys
import os


# Add this at the top of your enhanced_analyzer.py or run after it
class OllamaServiceAnalyzer:
    """Use Ollama LLM for better service analysis"""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.1"):
        self.base_url = base_url
        self.model = model
        self.available = self._check_availability()

        if self.available:
            print(f"✅ Ollama available with model: {self.model}")
        else:
            print("⚠️ Ollama/model not available. Using fallback analysis.")

    def _check_availability(self) -> bool:
        """Check if Ollama is running and model is available"""
        try:
            # Check if Ollama is running
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                return False

            # Check if our model is available
            models = response.json().get('models', [])
            model_names = [model.get('name', '').split(':')[0] for model in models]

            return any(self.model in name for name in model_names)

        except Exception:
            return False

    def analyze_service_purpose(self, service_contract: Dict) -> Dict[str, str]:
        """Use LLM to analyze service purpose and domain"""

        if not self.available:
            return self._fallback_analysis(service_contract)

        prompt = f"""
        Analyze this microservice and classify it:

        Service Contract:
        {json.dumps(service_contract, indent=2)}

        Return JSON with:
        1. semantic_purpose: ONE of [validation, transformation, storage, communication, passthrough, computation, routing, monitoring]
        2. domain_context: list of relevant domains from [email, weather, file, database, api, text, image, user, payment, notification, general]
        3. business_intent: one clear sentence

        JSON only:
        """

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1}
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "").strip()

                # Extract JSON from response
                try:
                    start = response_text.find('{')
                    end = response_text.rfind('}') + 1

                    if start >= 0 and end > start:
                        json_str = response_text[start:end]
                        analysis = json.loads(json_str)

                        if self._validate_analysis(analysis):
                            return analysis

                except json.JSONDecodeError:
                    pass

        except Exception as e:
            print(f"  LLM analysis failed: {e}")

        return self._fallback_analysis(service_contract)

    def _validate_analysis(self, analysis: Dict) -> bool:
        """Validate LLM response"""
        valid_purposes = {
            "validation", "transformation", "storage", "communication",
            "passthrough", "computation", "routing", "monitoring"
        }

        if not isinstance(analysis, dict):
            return False

        purpose = analysis.get("semantic_purpose", "")
        return purpose in valid_purposes

    def _fallback_analysis(self, service_contract: Dict) -> Dict[str, str]:
        """Improved fallback analysis when LLM not available"""
        metadata = service_contract.get('service_metadata', {})
        description = metadata.get('description', '').lower()
        service_id = metadata.get('service_id', '').lower()

        all_text = description + " " + service_id

        # Better keyword-based classification
        if any(word in all_text for word in ['validat', 'verify', 'check']) or 'validator' in service_id:
            return {
                "semantic_purpose": "validation",
                "domain_context": ["validation"],
                "business_intent": "Validates input data for correctness"
            }
        elif any(word in all_text for word in ['stor', 'save', 'persist', 'database']) or 'storage' in service_id:
            return {
                "semantic_purpose": "storage",
                "domain_context": ["database"],
                "business_intent": "Stores data persistently"
            }
        elif any(word in all_text for word in ['api', 'external', 'request', 'fetch']) or 'api' in service_id:
            return {
                "semantic_purpose": "communication",
                "domain_context": ["api"],
                "business_intent": "Communicates with external services"
            }
        elif any(word in all_text for word in ['file', 'process', 'csv', 'upload']) or 'processor' in service_id:
            return {
                "semantic_purpose": "transformation",
                "domain_context": ["file"],
                "business_intent": "Processes and transforms file data"
            }
        elif any(word in all_text for word in ['echo', 'pass', 'hello', 'forward']) or any(
                name in service_id for name in ['echo', 'hello']):
            return {
                "semantic_purpose": "passthrough",
                "domain_context": ["general"],
                "business_intent": "Passes data through unchanged for testing"
            }
        else:
            return {
                "semantic_purpose": "processing",
                "domain_context": ["general"],
                "business_intent": "Processes data"
            }


def enhance_analyzer_with_llm():
    """Run your analyzer with LLM enhancements"""

    print("LLM-Enhanced Service Analyzer")
    print("=" * 40)

    # Initialize LLM
    llm_analyzer = OllamaServiceAnalyzer()

    # Import your analyzer functions
    try:
        from enhanced_analyzer import analyze_your_services, ComputationalVectorSpace
        print("✅ Imported analyzer functions")
    except ImportError:
        print("❌ Could not import enhanced_analyzer.py")
        print("Make sure enhanced_analyzer.py is in the same directory")
        return

    print("\n1. Running service analysis...")
    signatures, vector_space = analyze_your_services()

    if not signatures:
        print("No services found. Make sure Docker services are running.")
        return

    print(f"\n2. Enhancing {len(signatures)} services with LLM...")

    # Re-analyze each service with LLM
    enhanced_signatures = {}

    for service_id, signature in signatures.items():
        print(f"\nEnhancing {service_id}...")
        print(f"  Original: {signature.semantic_purpose}")

        # Create contract for LLM analysis
        mock_contract = {
            "service_metadata": {
                "service_id": signature.service_id,
                "description": signature.business_intent,
                "pattern": signature.interaction_pattern
            },
            "interface_contract": {
                "inputs": signature.input_schema,
                "outputs": signature.output_schema
            }
        }

        # Get LLM analysis
        llm_analysis = llm_analyzer.analyze_service_purpose(mock_contract)

        # Update signature
        enhanced_signature = signature
        enhanced_signature.semantic_purpose = llm_analysis["semantic_purpose"]
        enhanced_signature.domain_context = llm_analysis["domain_context"]
        enhanced_signature.business_intent = llm_analysis["business_intent"]

        enhanced_signatures[service_id] = enhanced_signature

        print(f"  Enhanced: {llm_analysis['semantic_purpose']}")
        print(f"  Intent: {llm_analysis['business_intent']}")

    print(f"\n3. Rebuilding vector space with enhanced classifications...")

    # Rebuild vector space
    new_vector_space = ComputationalVectorSpace()
    for service_id, signature in enhanced_signatures.items():
        new_vector_space.add_service(signature)

    print(f"✅ Enhanced analysis complete!")

    # Show comparison
    print(f"\n" + "=" * 60)
    print("BEFORE vs AFTER COMPARISON")
    print("=" * 60)

    for service_id in signatures.keys():
        original = signatures[service_id].semantic_purpose
        enhanced = enhanced_signatures[service_id].semantic_purpose
        status = "✅ IMPROVED" if original != enhanced else "✓ Confirmed"
        print(f"  {service_id}: {original} → {enhanced} {status}")

    # Run enhanced semantic search
    print(f"\n" + "=" * 60)
    print("ENHANCED SEMANTIC SEARCH RESULTS")
    print("=" * 60)

    search_queries = [
        "validate data",
        "store information",
        "process files",
        "communicate with external services"
    ]

    for query in search_queries:
        print(f"\nQuery: '{query}'")
        try:
            results = new_vector_space.semantic_search(query, top_k=3)
            for service_id, similarity in results:
                enhanced_sig = enhanced_signatures[service_id]
                print(f"  → {service_id} ({enhanced_sig.semantic_purpose}): {similarity:.3f}")
        except Exception as e:
            print(f"  Search failed: {e}")

    # Save enhanced results
    print(f"\n💾 Saving enhanced results...")

    # Save enhanced signatures
    for service_id, signature in enhanced_signatures.items():
        filename = f"{service_id}_enhanced_signature.json"
        with open(filename, 'w') as f:
            json.dump({
                'service_id': signature.service_id,
                'semantic_purpose': signature.semantic_purpose,
                'domain_context': signature.domain_context,
                'business_intent': signature.business_intent,
                'interaction_pattern': signature.interaction_pattern,
                'estimated_latency_ms': signature.estimated_latency_ms,
                'memory_usage_mb': signature.memory_usage_mb
            }, f, indent=2)

    print(f"Enhanced signatures saved as *_enhanced_signature.json")

    return enhanced_signatures, new_vector_space


if __name__ == "__main__":
    enhance_analyzer_with_llm()
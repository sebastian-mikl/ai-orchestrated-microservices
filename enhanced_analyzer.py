#!/usr/bin/env python3
"""
Complete Computational Signature Analyzer with Vector Space Integration
Analyzes microservices and builds both compatibility matrix and navigable vector space
"""

import ast
import json
import re
import requests
from typing import Dict, List, Set, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
from datetime import datetime
from enum import Enum
from collections import Counter

# Import your interaction patterns (make sure this file is in the same directory)
try:
    from interaction_patterns import INTERACTION_PATTERNS, PatternRegistry, DataPattern, StatePattern
except ImportError:
    print("Warning: interaction_patterns.py not found. Some features may be limited.")
    INTERACTION_PATTERNS = {}

# Optional dependencies with fallbacks
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    print("Note: sentence-transformers not available. Using fallback embeddings.")
    print("Install with: pip install sentence-transformers")
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.manifold import TSNE
    from sklearn.decomposition import PCA
    SKLEARN_AVAILABLE = True
except ImportError:
    print("Note: scikit-learn not available. Some features limited.")
    print("Install with: pip install scikit-learn")
    SKLEARN_AVAILABLE = False


@dataclass
class ComputationalSignature:
    """Complete computational signature for a service"""

    # Service Identity
    service_id: str
    version: str
    analyzed_at: str

    # Semantic Understanding (from code analysis)
    semantic_purpose: str
    domain_context: List[str]
    business_intent: str
    transformation_type: str

    # Technical Interface (from contracts)
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    interaction_pattern: str
    endpoint_patterns: List[str]

    # Computational Behavior (from code analysis)
    algorithm_complexity: str
    side_effects: List[str]
    external_dependencies: List[str]
    error_modes: List[str]
    data_flow_pattern: str

    # Compatibility Information (enhanced)
    compatible_inputs: List[str]
    compatible_outputs: List[str]
    chainable_before: List[str]
    chainable_after: List[str]
    pattern_compatibility: Dict[str, bool]

    # Performance Characteristics (from contract/code)
    estimated_latency_ms: Optional[float]
    memory_usage_mb: Optional[float]
    cpu_intensity: str

    # Code Metrics
    lines_of_code: int
    cyclomatic_complexity: int
    external_api_calls: int

    # Extracted Keywords (for search)
    semantic_keywords: List[str]
    technical_keywords: List[str]


@dataclass
class VectorizedService:
    """A service represented in vector space"""
    service_id: str
    signature: ComputationalSignature
    vector: np.ndarray
    metadata: Dict

    def similarity_to(self, other: 'VectorizedService') -> float:
        """Compute cosine similarity to another service"""
        if SKLEARN_AVAILABLE:
            return cosine_similarity([self.vector], [other.vector])[0][0]
        else:
            # Fallback cosine similarity implementation
            dot_product = np.dot(self.vector, other.vector)
            norms = np.linalg.norm(self.vector) * np.linalg.norm(other.vector)
            return dot_product / norms if norms > 0 else 0.0


class ComputationalVectorSpace:
    """
    Vector space for computational signatures
    Enables semantic navigation and similarity search
    """

    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        self.services: Dict[str, VectorizedService] = {}
        self.dimension = 445  # Total vector dimension

        # Initialize embedding model if available
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer(embedding_model)
                self.semantic_dim = 384  # all-MiniLM-L6-v2 dimension
                print(f"✅ Loaded embedding model: {embedding_model}")
            except Exception as e:
                print(f"Warning: Could not load embedding model: {e}")
                self.embedding_model = None
                self.semantic_dim = 50  # Fallback dimension
        else:
            self.embedding_model = None
            self.semantic_dim = 50  # Fallback dimension

        # Adjust total dimension based on semantic dimension
        self.dimension = self.semantic_dim + 61  # semantic + technical + domain + performance + compatibility

    def add_service(self, signature: ComputationalSignature) -> VectorizedService:
        """Add a service signature to the vector space"""

        # Convert signature to vector
        vector = self._signature_to_vector(signature)

        # Create metadata for filtering/search
        metadata = self._extract_searchable_metadata(signature)

        # Create vectorized service
        vectorized = VectorizedService(
            service_id=signature.service_id,
            signature=signature,
            vector=vector,
            metadata=metadata
        )

        self.services[signature.service_id] = vectorized

        return vectorized

    def _signature_to_vector(self, sig: ComputationalSignature) -> np.ndarray:
        """Convert computational signature to dense vector"""

        # 1. Semantic Embedding
        semantic_vector = self._get_semantic_embedding(sig)

        # 2. Technical Features (15D)
        technical_features = self._extract_technical_features(sig)

        # 3. Domain Features (20D)
        domain_features = self._extract_domain_features(sig)

        # 4. Performance Features (6D)
        performance_features = self._extract_performance_features(sig)

        # 5. Compatibility Features (20D)
        compatibility_features = self._extract_compatibility_features(sig)

        # Combine all features
        full_vector = np.concatenate([
            semantic_vector,        # Variable D (384 or 50)
            technical_features,     # 15D
            domain_features,        # 20D
            performance_features,   # 6D
            compatibility_features  # 20D
        ])

        return full_vector

    def _get_semantic_embedding(self, sig: ComputationalSignature) -> np.ndarray:
        """Get semantic embedding for the service"""
        # Build semantic text
        components = [
            sig.semantic_purpose,
            sig.business_intent,
            sig.transformation_type,
            ' '.join(sig.domain_context),
            ' '.join(sig.semantic_keywords[:5]),  # Top 5 keywords
        ]
        semantic_text = ' '.join(filter(None, components))

        if self.embedding_model:
            try:
                return self.embedding_model.encode(semantic_text)
            except Exception as e:
                print(f"Warning: Embedding failed: {e}")

        # Fallback: simple text-based features
        return self._simple_text_embedding(semantic_text)

    def _simple_text_embedding(self, text: str) -> np.ndarray:
        """Simple fallback embedding when sentence-transformers unavailable"""
        # Create simple hash-based features
        features = np.zeros(self.semantic_dim)

        words = text.lower().split()
        for i, word in enumerate(words[:self.semantic_dim]):
            # Simple hash-based encoding
            hash_val = hash(word) % self.semantic_dim
            features[hash_val] += 1.0

        # Normalize
        norm = np.linalg.norm(features)
        if norm > 0:
            features = features / norm

        return features

    def _extract_technical_features(self, sig: ComputationalSignature) -> np.ndarray:
        """Extract technical features (15D)"""
        features = np.zeros(15)

        # Interaction pattern (one-hot, 7D)
        pattern_mapping = {
            'synchronous_stateless': 0,
            'synchronous_persistent': 1,
            'synchronous_session_based': 2,
            'asynchronous_stateless': 3,
            'asynchronous_persistent': 4,
            'streaming_stateless': 5,
            'event_driven_stateless': 6
        }
        pattern_idx = pattern_mapping.get(sig.interaction_pattern, 0)
        features[pattern_idx] = 1.0

        # Complexity (1D)
        complexity_mapping = {'O(1)': 1, 'O(log n)': 2, 'O(n)': 3, 'O(n^2)': 4}
        features[7] = complexity_mapping.get(sig.algorithm_complexity, 1)

        # Side effects count (1D)
        features[8] = len(sig.side_effects)

        # External dependencies count (1D)
        features[9] = len(sig.external_dependencies)

        # Lines of code (normalized, 1D)
        features[10] = min(sig.lines_of_code / 1000.0, 1.0) if sig.lines_of_code else 0.0

        # Cyclomatic complexity (normalized, 1D)
        features[11] = min(sig.cyclomatic_complexity / 20.0, 1.0) if sig.cyclomatic_complexity else 0.0

        # API calls count (1D)
        features[12] = min(sig.external_api_calls / 10.0, 1.0) if sig.external_api_calls else 0.0

        # Has error handling (1D)
        features[13] = 1.0 if sig.error_modes else 0.0

        # Data flow type (1D)
        flow_mapping = {'passthrough': 1, 'transform': 2, 'consumer': 3, 'producer': 4}
        features[14] = flow_mapping.get(sig.data_flow_pattern, 0)

        return features

    def _extract_domain_features(self, sig: ComputationalSignature) -> np.ndarray:
        """Extract domain context features (20D)"""
        features = np.zeros(20)

        # Common domains (one-hot encoding)
        domains = [
            'email', 'weather', 'file', 'database', 'api',
            'text', 'image', 'user', 'payment', 'notification',
            'validation', 'transformation', 'storage', 'communication',
            'monitoring', 'security', 'analytics', 'workflow', 'testing', 'general'
        ]

        for i, domain in enumerate(domains):
            if domain in sig.domain_context:
                features[i] = 1.0

        return features

    def _extract_performance_features(self, sig: ComputationalSignature) -> np.ndarray:
        """Extract performance characteristics (6D)"""
        features = np.zeros(6)

        # Latency (normalized to 0-1, where 1000ms = 1.0)
        features[0] = min((sig.estimated_latency_ms or 100) / 1000.0, 1.0)

        # Memory (normalized to 0-1, where 1GB = 1.0)
        features[1] = min((sig.memory_usage_mb or 50) / 1024.0, 1.0)

        # CPU intensity
        cpu_mapping = {'low': 0.2, 'medium': 0.5, 'high': 1.0, 'unknown': 0.3}
        features[2] = cpu_mapping.get(sig.cpu_intensity, 0.3)

        # Has network dependencies
        features[3] = 1.0 if any('network' in dep for dep in sig.external_dependencies) else 0.0

        # Has disk dependencies
        features[4] = 1.0 if any('disk' in effect or 'file' in effect for effect in sig.side_effects) else 0.0

        # Scalability indicator (inverse of complexity * dependencies)
        complexity_score = len(sig.external_dependencies) + len(sig.side_effects)
        features[5] = max(0.1, 1.0 - (complexity_score / 10.0))

        return features

    def _extract_compatibility_features(self, sig: ComputationalSignature) -> np.ndarray:
        """Extract type compatibility features (20D)"""
        features = np.zeros(20)

        # Input types (one-hot)
        input_types = ['string', 'integer', 'float', 'boolean', 'object', 'array', 'email', 'url', 'file', 'any']
        for i, type_name in enumerate(input_types):
            if type_name in sig.compatible_inputs:
                features[i] = 1.0

        # Output types (one-hot)
        output_types = ['string', 'integer', 'float', 'boolean', 'object', 'array', 'email', 'url', 'file', 'any']
        for i, type_name in enumerate(output_types):
            if type_name in sig.compatible_outputs:
                features[i + 10] = 1.0

        return features

    def _extract_searchable_metadata(self, sig: ComputationalSignature) -> Dict:
        """Extract metadata for filtering and search"""
        return {
            'semantic_purpose': sig.semantic_purpose,
            'interaction_pattern': sig.interaction_pattern,
            'domain_context': sig.domain_context,
            'input_types': sig.compatible_inputs,
            'output_types': sig.compatible_outputs,
            'side_effects': sig.side_effects,
            'external_dependencies': sig.external_dependencies,
            'performance_category': self._categorize_performance(sig),
            'complexity_category': self._categorize_complexity(sig)
        }

    def _categorize_performance(self, sig: ComputationalSignature) -> str:
        """Categorize performance for filtering"""
        latency = sig.estimated_latency_ms or 100
        if latency < 50:
            return 'fast'
        elif latency < 500:
            return 'medium'
        else:
            return 'slow'

    def _categorize_complexity(self, sig: ComputationalSignature) -> str:
        """Categorize algorithmic complexity"""
        if sig.algorithm_complexity in ['O(1)', 'O(log n)']:
            return 'simple'
        elif sig.algorithm_complexity == 'O(n)':
            return 'linear'
        else:
            return 'complex'

    def find_similar_services(self,
                            query_service_id: str,
                            top_k: int = 5,
                            exclude_self: bool = True) -> List[Tuple[str, float]]:
        """Find services similar to the query service"""

        if query_service_id not in self.services:
            raise ValueError(f"Service {query_service_id} not found")

        query_service = self.services[query_service_id]
        similarities = []

        for service_id, service in self.services.items():
            if exclude_self and service_id == query_service_id:
                continue

            similarity = query_service.similarity_to(service)
            similarities.append((service_id, similarity))

        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    def semantic_search(self,
                       query_text: str,
                       top_k: int = 5,
                       filters: Dict = None) -> List[Tuple[str, float]]:
        """Search services using natural language query"""

        # Get query embedding
        if self.embedding_model:
            try:
                query_vector = self.embedding_model.encode(query_text)
            except Exception:
                query_vector = self._simple_text_embedding(query_text)
        else:
            query_vector = self._simple_text_embedding(query_text)

        similarities = []

        for service_id, service in self.services.items():
            # Apply filters if provided
            if filters and not self._matches_filters(service, filters):
                continue

            # Compute similarity (focus on semantic part)
            service_semantic = service.vector[:len(query_vector)]

            if SKLEARN_AVAILABLE:
                semantic_similarity = cosine_similarity([query_vector], [service_semantic])[0][0]
            else:
                # Fallback cosine similarity
                dot_product = np.dot(query_vector, service_semantic)
                norms = np.linalg.norm(query_vector) * np.linalg.norm(service_semantic)
                semantic_similarity = dot_product / norms if norms > 0 else 0.0

            similarities.append((service_id, semantic_similarity))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    def _matches_filters(self, service: VectorizedService, filters: Dict) -> bool:
        """Check if service matches filter criteria"""
        metadata = service.metadata

        for key, value in filters.items():
            if key in metadata:
                if isinstance(value, list):
                    if not any(v in metadata[key] for v in value):
                        return False
                else:
                    if metadata[key] != value:
                        return False

        return True

    def visualize_space(self, method: str = 'pca') -> Dict:
        """Generate 2D visualization of the service space"""
        if len(self.services) < 2:
            return {'error': 'Need at least 2 services for visualization'}

        if not SKLEARN_AVAILABLE:
            return {'error': 'scikit-learn required for visualization'}

        vectors = np.array([service.vector for service in self.services.values()])
        service_ids = list(self.services.keys())

        # Dimensionality reduction
        if method == 'tsne':
            reducer = TSNE(n_components=2, random_state=42, perplexity=min(30, len(self.services)-1))
        else:  # PCA
            reducer = PCA(n_components=2)

        try:
            coords_2d = reducer.fit_transform(vectors)

            return {
                'coordinates': coords_2d.tolist(),
                'service_ids': service_ids,
                'metadata': [self.services[sid].metadata for sid in service_ids]
            }
        except Exception as e:
            return {'error': f'Visualization failed: {e}'}

    def get_space_statistics(self) -> Dict:
        """Get statistics about the vector space"""
        if not self.services:
            return {'error': 'No services in space'}

        # Collect statistics
        semantic_purposes = [s.metadata['semantic_purpose'] for s in self.services.values()]
        patterns = [s.metadata['interaction_pattern'] for s in self.services.values()]
        performance_cats = [s.metadata['performance_category'] for s in self.services.values()]

        return {
            'total_services': len(self.services),
            'vector_dimension': self.dimension,
            'semantic_purposes': dict(Counter(semantic_purposes)),
            'interaction_patterns': dict(Counter(patterns)),
            'performance_categories': dict(Counter(performance_cats)),
            'embedding_model': 'sentence-transformers' if self.embedding_model else 'fallback'
        }


class DataType(Enum):
    """Standard data types with automatic compatibility rules"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    EMAIL = "email"
    URL = "url"
    FILE = "file"
    JSON = "json"
    ANY = "any"


class PatternCompatibilityEngine:
    """Automatically determines service compatibility based on patterns"""

    def __init__(self):
        # Type compatibility matrix (automatic)
        self.type_compatibility = {
            DataType.STRING: {DataType.STRING, DataType.EMAIL, DataType.URL, DataType.JSON, DataType.ANY},
            DataType.EMAIL: {DataType.STRING, DataType.EMAIL, DataType.ANY},
            DataType.URL: {DataType.STRING, DataType.URL, DataType.ANY},
            DataType.INTEGER: {DataType.INTEGER, DataType.FLOAT, DataType.STRING, DataType.ANY},
            DataType.FLOAT: {DataType.FLOAT, DataType.INTEGER, DataType.STRING, DataType.ANY},
            DataType.BOOLEAN: {DataType.BOOLEAN, DataType.STRING, DataType.ANY},
            DataType.OBJECT: {DataType.OBJECT, DataType.JSON, DataType.STRING, DataType.ANY},
            DataType.ARRAY: {DataType.ARRAY, DataType.JSON, DataType.STRING, DataType.ANY},
            DataType.FILE: {DataType.FILE, DataType.STRING, DataType.ANY},
            DataType.JSON: {DataType.JSON, DataType.OBJECT, DataType.ARRAY, DataType.STRING, DataType.ANY},
            DataType.ANY: {dt for dt in DataType}  # ANY accepts everything
        }

        # Pattern compatibility matrix based on your interaction patterns
        self.pattern_compatibility = {
            "synchronous_stateless": {
                "synchronous_stateless",
                "synchronous_persistent",
                "synchronous_session_based"
            },
            "synchronous_persistent": {
                "synchronous_stateless",
                "synchronous_persistent"
            },
            "synchronous_session_based": {
                "synchronous_stateless",
                "synchronous_persistent",
                "synchronous_session_based"
            },
            "asynchronous_stateless": {
                "synchronous_stateless",  # Async can call sync
                "synchronous_persistent"
            },
            "asynchronous_persistent": {
                "synchronous_stateless",
                "synchronous_persistent"
            },
            "streaming_stateless": {
                "streaming_stateless",
                "synchronous_stateless"  # Can process stream chunks
            },
            "event_driven_stateless": {
                "synchronous_stateless",
                "event_driven_stateless"
            }
        }

    def can_chain_services(self, service_a: ComputationalSignature, service_b: ComputationalSignature) -> bool:
        """
        Determine if service A can chain to service B
        Based on type compatibility + pattern compatibility + semantic compatibility
        """

        # 1. Type compatibility check
        type_compatible = self._check_type_compatibility(service_a, service_b)

        # 2. Pattern compatibility check
        pattern_compatible = self._check_pattern_compatibility(service_a, service_b)

        # 3. Semantic compatibility check
        semantic_compatible = self._check_semantic_compatibility(service_a, service_b)

        # 4. Side effect compatibility
        side_effect_compatible = self._check_side_effect_compatibility(service_a, service_b)

        return (type_compatible and
                pattern_compatible and
                semantic_compatible and
                side_effect_compatible)

    def _check_type_compatibility(self, service_a: ComputationalSignature, service_b: ComputationalSignature) -> bool:
        """Check if output type can feed into input type"""

        # Get primary output type from service A
        output_types = service_a.compatible_outputs or ["string"]
        input_types = service_b.compatible_inputs or ["string"]

        # Convert to DataType enums
        def to_data_type(type_str: str) -> DataType:
            type_mapping = {
                "string": DataType.STRING,
                "integer": DataType.INTEGER,
                "float": DataType.FLOAT,
                "boolean": DataType.BOOLEAN,
                "object": DataType.OBJECT,
                "array": DataType.ARRAY,
                "email": DataType.EMAIL,
                "url": DataType.URL,
                "file": DataType.FILE,
                "json": DataType.JSON,
                "any": DataType.ANY
            }
            return type_mapping.get(type_str.lower(), DataType.STRING)

        # Check if any output type is compatible with any input type
        for output_type_str in output_types:
            output_type = to_data_type(output_type_str)
            compatible_types = self.type_compatibility.get(output_type, {DataType.STRING})

            for input_type_str in input_types:
                input_type = to_data_type(input_type_str)
                if input_type in compatible_types:
                    return True

        return False

    def _check_pattern_compatibility(self, service_a: ComputationalSignature, service_b: ComputationalSignature) -> bool:
        """Check if interaction patterns can be chained"""
        pattern_a = service_a.interaction_pattern
        pattern_b = service_b.interaction_pattern

        compatible_patterns = self.pattern_compatibility.get(pattern_a, set())
        return pattern_b in compatible_patterns

    def _check_semantic_compatibility(self, service_a: ComputationalSignature, service_b: ComputationalSignature) -> bool:
        """Check if the semantic flow makes sense"""

        # Define semantic flow rules based on your services
        semantic_flows = {
            "passthrough": {"validation", "transformation", "storage", "communication", "routing", "processing"},
            "validation": {"storage", "transformation", "communication", "routing", "processing"},
            "transformation": {"validation", "storage", "communication", "routing", "processing"},
            "storage": {"communication", "routing"},  # Storage usually ends chains
            "retrieval": {"validation", "transformation", "communication", "routing", "processing"},
            "communication": {"storage", "routing", "processing"},  # Communication often ends chains
            "computation": {"validation", "transformation", "storage", "communication", "routing", "processing"},
            "routing": {"validation", "transformation", "storage", "communication", "processing"},
            "monitoring": {"validation", "transformation", "storage", "communication", "routing", "processing"},  # Monitoring can go anywhere
            "processing": {"validation", "transformation", "storage", "communication", "routing", "processing"},  # Generic processing
            "unknown": {"validation", "transformation", "storage", "communication", "routing", "processing"}  # Unknown can go most places
        }

        # Get compatible semantic purposes for service A
        compatible_purposes = semantic_flows.get(service_a.semantic_purpose, set())

        # Check if service B's purpose is compatible
        is_compatible = (
            service_b.semantic_purpose in compatible_purposes or
            service_a.semantic_purpose == "passthrough" or  # Passthrough goes anywhere
            service_b.semantic_purpose == "monitoring" or   # Monitoring accepts anything
            service_a.semantic_purpose == "unknown" or      # Unknown can try to go anywhere
            service_b.semantic_purpose == "unknown"         # Unknown can accept anything
        )

        return is_compatible

    def _check_side_effect_compatibility(self, service_a: ComputationalSignature, service_b: ComputationalSignature) -> bool:
        """Check if side effects are compatible"""

        # Some side effects make chaining problematic
        problematic_combinations = [
            # Don't chain two services that both do heavy network calls
            ({"network_call"}, {"network_call"}),
            # Don't chain two file writers (could conflict)
            ({"file_write"}, {"file_write"}),
        ]

        a_effects = set(service_a.side_effects)
        b_effects = set(service_b.side_effects)

        for prob_a, prob_b in problematic_combinations:
            if prob_a.issubset(a_effects) and prob_b.issubset(b_effects):
                return False

        return True


class ServiceCodeAnalyzer:
    """Analyzes service source code to extract computational patterns"""

    def __init__(self):
        self.semantic_patterns = {
            'validation': ['validate', 'verify', 'check', 'confirm', 'test'],
            'transformation': ['transform', 'convert', 'change', 'modify', 'process'],
            'storage': ['store', 'save', 'persist', 'write', 'insert'],
            'retrieval': ['get', 'fetch', 'read', 'load', 'retrieve'],
            'communication': ['send', 'post', 'email', 'notify', 'message'],
            'computation': ['calculate', 'compute', 'analyze', 'generate'],
            'routing': ['route', 'forward', 'dispatch', 'redirect'],
            'monitoring': ['monitor', 'track', 'log', 'audit', 'measure']
        }

    def analyze_code(self, code_content: str, file_path: str = None) -> Dict[str, Any]:
        """Main code analysis pipeline"""
        try:
            tree = ast.parse(code_content)

            analysis = {
                'semantic_purpose': self._extract_semantic_purpose(code_content, tree),
                'domain_context': self._extract_domain_context(code_content),
                'business_intent': self._extract_business_intent(code_content),
                'transformation_type': self._classify_transformation(tree, code_content),
                'algorithm_complexity': 'O(1)',  # Simplified
                'side_effects': self._detect_side_effects(tree),
                'external_dependencies': self._find_external_dependencies(tree),
                'error_modes': ['general_error'],  # Simplified
                'data_flow_pattern': 'transform',  # Simplified
                'endpoint_patterns': self._extract_endpoints(tree),
                'lines_of_code': len(code_content.split('\n')),
                'cyclomatic_complexity': 3,  # Simplified
                'external_api_calls': self._count_api_calls(tree),
                'semantic_keywords': self._extract_semantic_keywords(code_content),
                'technical_keywords': self._extract_technical_keywords(tree)
            }

            return analysis

        except Exception as e:
            return {'error': f"Code analysis failed: {str(e)}"}

    def _extract_semantic_purpose(self, code: str, tree: ast.AST) -> str:
        """Determine the main semantic purpose of the service"""
        code_lower = code.lower()

        # Look for explicit purpose indicators in code
        for purpose, keywords in self.semantic_patterns.items():
            if any(keyword in code_lower for keyword in keywords):
                return purpose

        # Analyze function/method names
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_name = node.name.lower()
                for purpose, keywords in self.semantic_patterns.items():
                    if any(keyword in func_name for keyword in keywords):
                        return purpose

        # Look in app titles and descriptions
        if 'validator' in code_lower or 'validate' in code_lower:
            return 'validation'
        elif 'transform' in code_lower:
            return 'transformation'
        elif 'store' in code_lower or 'storage' in code_lower:
            return 'storage'
        elif 'echo' in code_lower or 'pass' in code_lower:
            return 'passthrough'

        return 'processing'  # Default fallback

    def _extract_domain_context(self, code: str) -> List[str]:
        """Extract domain-specific context clues"""
        code_lower = code.lower()
        domains = []

        domain_indicators = {
            'email': ['email', 'smtp', '@', 'address', 'recipient'],
            'weather': ['weather', 'temperature', 'forecast', 'climate'],
            'file': ['file', 'upload', 'download', 'csv', 'json', 'xml'],
            'database': ['sql', 'query', 'table', 'database', 'db'],
            'api': ['api', 'rest', 'endpoint', 'http', 'request'],
            'text': ['text', 'string', 'char', 'word', 'sentence'],
        }

        for domain, indicators in domain_indicators.items():
            if any(indicator in code_lower for indicator in indicators):
                domains.append(domain)

        return domains or ['general']

    def _extract_business_intent(self, code: str) -> str:
        """Extract human-readable business intent from comments/docstrings"""
        lines = code.split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith('"""') or line.startswith("'''"):
                return line.strip('"\'').strip()
            elif line.startswith('#') and any(word in line.lower() for word in ['purpose', 'does', 'handles']):
                return line.strip('#').strip()

        return "Service functionality not clearly documented"

    def _classify_transformation(self, tree: ast.AST, code: str) -> str:
        """Classify the type of data transformation performed"""
        code_lower = code.lower()

        if any(word in code_lower for word in ['upper()', 'lower()', 'replace(', 'strip(']):
            return 'text_transformation'
        elif any(word in code_lower for word in ['json.loads', 'json.dumps', 'parse']):
            return 'format_conversion'
        elif any(word in code_lower for word in ['save', 'store', 'persist', 'write']):
            return 'persistence'
        elif 'requests.' in code_lower:
            return 'api_integration'

        return 'processing'

    def _detect_side_effects(self, tree: ast.AST) -> List[str]:
        """Detect side effects in the code"""
        side_effects = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = ''
                if hasattr(node.func, 'attr'):
                    func_name = node.func.attr
                elif hasattr(node.func, 'id'):
                    func_name = node.func.id

                if func_name in ['post', 'get', 'put', 'delete', 'patch']:
                    side_effects.append('network_call')
                elif func_name == 'print':
                    side_effects.append('logging')
                elif func_name in ['open', 'write', 'read']:
                    side_effects.append('file_io')

        return list(set(side_effects))

    def _find_external_dependencies(self, tree: ast.AST) -> List[str]:
        """Find external service dependencies"""
        dependencies = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in ['requests', 'urllib', 'httpx']:
                        dependencies.append('http_client')
                    elif alias.name in ['sqlite3', 'psycopg2', 'pymongo']:
                        dependencies.append('database')
            elif isinstance(node, ast.ImportFrom):
                if node.module in ['requests', 'urllib', 'httpx']:
                    dependencies.append('http_client')

        return list(set(dependencies))

    def _extract_endpoints(self, tree: ast.AST) -> List[str]:
        """Extract API endpoint patterns"""
        endpoints = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if any(d.id == 'app' for d in node.decorator_list if hasattr(d, 'id')):
                    endpoints.append(f"/{node.name}")

        return endpoints

    def _count_api_calls(self, tree: ast.AST) -> int:
        """Count external API calls"""
        count = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and hasattr(node.func, 'attr'):
                if node.func.attr in ['get', 'post', 'put', 'delete', 'patch']:
                    count += 1

        return count

    def _extract_semantic_keywords(self, code: str) -> List[str]:
        """Extract semantic keywords from code and comments"""
        keywords = []

        for line in code.split('\n'):
            line = line.strip()
            if line.startswith('#') or '"""' in line or "'''" in line:
                words = re.findall(r'\b[a-z]+\b', line.lower())
                keywords.extend([w for w in words if len(w) > 3])

        return list(set(keywords))

    def _extract_technical_keywords(self, tree: ast.AST) -> List[str]:
        """Extract technical keywords from imports and function calls"""
        keywords = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    keywords.append(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                keywords.append(node.module)

        return list(set(keywords))


class ContractAnalyzer:
    """Analyzes service contracts to extract interface information"""

    def analyze_contract(self, contract_data: Dict) -> Dict[str, Any]:
        """Extract structured information from service contract"""
        try:
            analysis = {
                'input_schema': self._extract_input_schema(contract_data),
                'output_schema': self._extract_output_schema(contract_data),
                'interaction_pattern': self._extract_pattern(contract_data),
                'compatible_inputs': self._extract_compatible_inputs(contract_data),
                'compatible_outputs': self._extract_compatible_outputs(contract_data),
                'chainable_before': [],  # Now computed dynamically
                'chainable_after': [],  # Now computed dynamically
                'pattern_compatibility': self._extract_pattern_compatibility(contract_data),
                'estimated_latency_ms': self._extract_latency(contract_data),
                'memory_usage_mb': self._extract_memory_usage(contract_data),
                'cpu_intensity': self._extract_cpu_intensity(contract_data),
                'semantic_purpose': self._extract_semantic_purpose_from_contract(contract_data),
                'business_intent': self._extract_business_intent_from_contract(contract_data),
                'domain_context': self._extract_domain_context_from_contract(contract_data)
            }

            return analysis

        except Exception as e:
            return {'error': f"Contract analysis failed: {str(e)}"}

    def _extract_input_schema(self, contract: Dict) -> Dict[str, Any]:
        """Extract input schema from contract"""
        interface = contract.get('interface_contract', {})
        return interface.get('inputs', {})

    def _extract_output_schema(self, contract: Dict) -> Dict[str, Any]:
        """Extract output schema from contract"""
        interface = contract.get('interface_contract', {})
        return interface.get('outputs', {})

    def _extract_pattern(self, contract: Dict) -> str:
        """Extract interaction pattern"""
        metadata = contract.get('service_metadata', {})
        return metadata.get('pattern', 'synchronous_stateless')

    def _extract_compatible_inputs(self, contract: Dict) -> List[str]:
        """Extract compatible input types (automatically inferred)"""
        inputs = self._extract_input_schema(contract)
        input_types = []

        for input_name, input_spec in inputs.items():
            input_type = input_spec.get('type', 'string')
            input_types.append(input_type)

            # Add semantic type inference
            if 'email' in input_name.lower():
                input_types.append('email')
            elif 'url' in input_name.lower():
                input_types.append('url')
            elif 'file' in input_name.lower():
                input_types.append('file')

        return input_types or ['string']

    def _extract_compatible_outputs(self, contract: Dict) -> List[str]:
        """Extract compatible output types (automatically inferred)"""
        outputs = self._extract_output_schema(contract)
        output_types = []

        for output_name, output_spec in outputs.items():
            output_type = output_spec.get('type', 'string')
            output_types.append(output_type)

            # Add semantic type inference
            if 'email' in output_name.lower():
                output_types.append('email')
            elif 'url' in output_name.lower():
                output_types.append('url')
            elif 'file' in output_name.lower():
                output_types.append('file')

        return output_types or ['string']

    def _extract_pattern_compatibility(self, contract: Dict) -> Dict[str, bool]:
        """Extract pattern compatibility information"""
        pattern = self._extract_pattern(contract)

        return {
            'async_compatible': 'async' in pattern or 'stateless' in pattern,
            'streaming_compatible': 'streaming' in pattern,
            'persistent_compatible': 'persistent' in pattern
        }

    def _extract_latency(self, contract: Dict) -> Optional[float]:
        """Extract estimated latency from contract"""
        resources = contract.get('resource_requirements', {})
        exec_time = resources.get('max_execution_time', '')

        if 'ms' in exec_time:
            return float(exec_time.replace('ms', ''))
        elif 's' in exec_time:
            return float(exec_time.replace('s', '')) * 1000

        return None

    def _extract_memory_usage(self, contract: Dict) -> Optional[float]:
        """Extract memory usage from contract"""
        resources = contract.get('resource_requirements', {})
        memory = resources.get('memory_limit', '')

        if 'MB' in memory:
            return float(memory.replace('MB', ''))
        elif 'GB' in memory:
            return float(memory.replace('GB', '')) * 1024

        return None

    def _extract_cpu_intensity(self, contract: Dict) -> str:
        """Extract CPU intensity estimation"""
        resources = contract.get('resource_requirements', {})
        cpu_intensive = resources.get('cpu_intensive', False)

        return 'high' if cpu_intensive else 'low'

    def _extract_semantic_purpose_from_contract(self, contract: Dict) -> str:
        """Extract semantic purpose from contract description and metadata"""

        metadata = contract.get('service_metadata', {})
        description = metadata.get('description', '').lower()
        service_id = metadata.get('service_id', '').lower()

        # Check for validation keywords
        if any(word in description for word in ['validat', 'verify', 'check', 'confirm']):
            return 'validation'
        if any(word in service_id for word in ['validat', 'verify', 'check']):
            return 'validation'

        # Check for transformation keywords
        if any(word in description for word in ['transform', 'convert', 'change', 'modify', 'process']):
            return 'transformation'
        if any(word in service_id for word in ['transform', 'convert', 'process']):
            return 'transformation'

        # Check for storage keywords
        if any(word in description for word in ['stor', 'save', 'persist', 'database', 'cache']):
            return 'storage'
        if any(word in service_id for word in ['stor', 'save', 'persist', 'database']):
            return 'storage'

        # Check for API/external keywords
        if any(word in description for word in ['api', 'external', 'fetch', 'request', 'call']):
            return 'communication'
        if any(word in service_id for word in ['api', 'external', 'fetch']):
            return 'communication'

        # Check for file processing
        if any(word in description for word in ['file', 'upload', 'download', 'csv', 'document']):
            return 'transformation'
        if any(word in service_id for word in ['file', 'processor', 'upload']):
            return 'transformation'

        # Check for passthrough/echo
        if any(word in description for word in ['echo', 'pass', 'forward', 'unchanged', 'through']):
            return 'passthrough'
        if any(word in service_id for word in ['echo', 'hello', 'pass']):
            return 'passthrough'

        return 'processing'  # Default fallback

    def _extract_business_intent_from_contract(self, contract: Dict) -> str:
        """Extract business intent from contract"""
        metadata = contract.get('service_metadata', {})
        description = metadata.get('description', '')

        if description:
            return description

        service_id = metadata.get('service_id', '')
        return f"Handles {service_id.replace('-', ' ')} operations"

    def _extract_domain_context_from_contract(self, contract: Dict) -> List[str]:
        """Extract domain context from contract"""
        domains = []

        all_text = ' '.join([
            contract.get('service_metadata', {}).get('description', ''),
            contract.get('service_metadata', {}).get('service_id', '')
        ]).lower()

        domain_indicators = {
            'email': ['email', 'address', 'smtp'],
            'weather': ['weather', 'forecast', 'climate'],
            'file': ['file', 'upload', 'csv', 'document'],
            'api': ['api', 'external', 'http', 'rest'],
            'database': ['storage', 'database', 'persist', 'save'],
            'validation': ['valid', 'check', 'verify'],
            'text': ['text', 'string', 'transform'],
            'communication': ['hello', 'message', 'notification']
        }

        for domain, indicators in domain_indicators.items():
            if any(indicator in all_text for indicator in indicators):
                domains.append(domain)

        return domains or ['general']


class ComputationalSignatureAnalyzer:
    """Main analyzer that combines code and contract analysis"""

    def __init__(self):
        self.code_analyzer = ServiceCodeAnalyzer()
        self.contract_analyzer = ContractAnalyzer()

    def analyze_service(self,
                        service_id: str,
                        code_content: str = None,
                        code_file: str = None,
                        contract_data: Dict = None,
                        contract_url: str = None) -> ComputationalSignature:
        """Analyze a service and generate computational signature"""

        # Get code content
        if code_file and not code_content:
            with open(code_file, 'r') as f:
                code_content = f.read()

        # Get contract data
        if contract_url and not contract_data:
            try:
                response = requests.get(contract_url, timeout=10)
                contract_data = response.json()
            except Exception as e:
                print(f"Failed to fetch contract from {contract_url}: {e}")
                contract_data = {}

        # Analyze code
        code_analysis = {}
        if code_content:
            code_analysis = self.code_analyzer.analyze_code(code_content)

        # Analyze contract
        contract_analysis = {}
        if contract_data:
            contract_analysis = self.contract_analyzer.analyze_contract(contract_data)

        # Combine analyses into signature
        signature = ComputationalSignature(
            service_id=service_id,
            version=contract_data.get('service_metadata', {}).get('version', '1.0.0') if contract_data else '1.0.0',
            analyzed_at=datetime.now().isoformat(),

            # From code analysis (with fallbacks from contract)
            semantic_purpose=code_analysis.get('semantic_purpose',
                                               contract_analysis.get('semantic_purpose', 'processing')),
            domain_context=code_analysis.get('domain_context', contract_analysis.get('domain_context', ['general'])),
            business_intent=code_analysis.get('business_intent',
                                              contract_analysis.get('business_intent', 'Service functionality')),
            transformation_type=code_analysis.get('transformation_type', 'unknown'),
            algorithm_complexity=code_analysis.get('algorithm_complexity', 'O(1)'),
            side_effects=code_analysis.get('side_effects', []),
            external_dependencies=code_analysis.get('external_dependencies', []),
            error_modes=code_analysis.get('error_modes', []),
            data_flow_pattern=code_analysis.get('data_flow_pattern', 'unknown'),
            endpoint_patterns=code_analysis.get('endpoint_patterns', []),
            lines_of_code=code_analysis.get('lines_of_code', 0),
            cyclomatic_complexity=code_analysis.get('cyclomatic_complexity', 1),
            external_api_calls=code_analysis.get('external_api_calls', 0),
            semantic_keywords=code_analysis.get('semantic_keywords', []),
            technical_keywords=code_analysis.get('technical_keywords', []),

            # From contract analysis
            input_schema=contract_analysis.get('input_schema', {}),
            output_schema=contract_analysis.get('output_schema', {}),
            interaction_pattern=contract_analysis.get('interaction_pattern', 'synchronous_stateless'),
            compatible_inputs=contract_analysis.get('compatible_inputs', ['string']),
            compatible_outputs=contract_analysis.get('compatible_outputs', ['string']),
            chainable_before=contract_analysis.get('chainable_before', []),
            chainable_after=contract_analysis.get('chainable_after', []),
            pattern_compatibility=contract_analysis.get('pattern_compatibility', {}),
            estimated_latency_ms=contract_analysis.get('estimated_latency_ms'),
            memory_usage_mb=contract_analysis.get('memory_usage_mb'),
            cpu_intensity=contract_analysis.get('cpu_intensity', 'unknown')
        )

        return signature

    def save_signature(self, signature: ComputationalSignature, output_file: str):
        """Save signature to JSON file"""
        with open(output_file, 'w') as f:
            json.dump(asdict(signature), f, indent=2)

    def load_signature(self, input_file: str) -> ComputationalSignature:
        """Load signature from JSON file"""
        with open(input_file, 'r') as f:
            data = json.load(f)
        return ComputationalSignature(**data)


def can_chain_services(service_a: ComputationalSignature,
                       service_b: ComputationalSignature) -> bool:
    """Check if service A can chain to service B using pattern-based logic"""
    engine = PatternCompatibilityEngine()
    return engine.can_chain_services(service_a, service_b)


def find_potential_chains(signatures: Dict[str, ComputationalSignature]) -> List[List[str]]:
    """Find potential 2-3 service chains using pattern-based compatibility"""
    chains = []
    engine = PatternCompatibilityEngine()

    # Find 2-service chains
    for service_a_id, service_a in signatures.items():
        for service_b_id, service_b in signatures.items():
            if service_a_id != service_b_id and engine.can_chain_services(service_a, service_b):
                chains.append([service_a_id, service_b_id])

    # Find 3-service chains by extending 2-service chains
    three_chains = []
    for chain in chains:
        service_b_id = chain[1]
        service_b = signatures[service_b_id]

        for service_c_id, service_c in signatures.items():
            if service_c_id not in chain and engine.can_chain_services(service_b, service_c):
                three_chains.append(chain + [service_c_id])

    return chains + three_chains


def analyze_your_services(registry_url: str = "http://localhost:8004"):
    """Analyze all services from your docker setup and build vector space"""
    analyzer = ComputationalSignatureAnalyzer()
    signatures = {}

    # Initialize vector space
    vector_space = ComputationalVectorSpace()

    try:
        # Get list of services from your registry
        response = requests.get(f"{registry_url}/services")
        services = response.json().get('services', {})

        print(f"Found {len(services)} services in registry:")
        for service_id in services.keys():
            print(f"  - {service_id}")

        # Analyze each service
        for service_id, service_info in services.items():
            try:
                print(f"\nAnalyzing {service_id}...")

                # Fix URL - convert Docker hostname to localhost
                service_url = service_info['url']
                if '://' in service_url:
                    protocol, rest = service_url.split('://', 1)
                    hostname, port_part = rest.split(':')
                    # Map docker service names to localhost ports
                    port_mapping = {
                        'echo-node': '8001',
                        'data-validator': '8002',
                        'external-api': '8003',
                        'storage-node': '8005',
                        'file-processor': '8006',
                        'hello-world': '8007'
                    }

                    if hostname in port_mapping:
                        service_url = f"http://localhost:{port_mapping[hostname]}"
                    else:
                        service_url = f"http://localhost:{port_part}"

                print(f"  Connecting to: {service_url}")

                # Fetch contract
                contract_response = requests.get(f"{service_url}/contract", timeout=10)

                if contract_response.status_code == 200:
                    contract_data = contract_response.json()

                    # Analyze service
                    signature = analyzer.analyze_service(
                        service_id=service_id,
                        contract_data=contract_data
                    )

                    signatures[service_id] = signature

                    # Add to vector space
                    vectorized_service = vector_space.add_service(signature)

                    # Save individual signature
                    analyzer.save_signature(signature, f"{service_id}_signature.json")

                    print(f"  ✅ {service_id}: {signature.semantic_purpose} ({signature.interaction_pattern})")
                    print(f"     Vector: {vectorized_service.vector.shape} dimensions")
                else:
                    print(f"  ❌ {service_id}: Failed to fetch contract ({contract_response.status_code})")

            except Exception as e:
                print(f"  ❌ {service_id}: Analysis failed - {e}")

        # Create enhanced analysis summary with vector space
        create_enhanced_analysis_summary(signatures, vector_space)

        return signatures, vector_space

    except Exception as e:
        print(f"Failed to connect to service registry: {e}")
        print("Make sure your docker services are running!")
        print("Try: curl http://localhost:8004/services")
        return {}, None


def create_analysis_summary(signatures: Dict[str, ComputationalSignature]):
    """Create a summary analysis of all services with debugging"""
    if not signatures:
        print("No signatures to analyze")
        return

    print("\n" + "=" * 60)
    print("COMPUTATIONAL SPACE ANALYSIS SUMMARY")
    print("=" * 60)

    # Group by semantic purpose
    by_purpose = {}
    for sig in signatures.values():
        purpose = sig.semantic_purpose
        if purpose not in by_purpose:
            by_purpose[purpose] = []
        by_purpose[purpose].append(sig.service_id)

    print(f"\nServices by Semantic Purpose:")
    for purpose, services in by_purpose.items():
        print(f"  {purpose}: {services}")

    # Group by interaction pattern
    by_pattern = {}
    for sig in signatures.values():
        pattern = sig.interaction_pattern
        if pattern not in by_pattern:
            by_pattern[pattern] = []
        by_pattern[pattern].append(sig.service_id)

    print(f"\nServices by Interaction Pattern:")
    for pattern, services in by_pattern.items():
        print(f"  {pattern}: {services}")

    # Analyze compatibility
    print(f"\nCompatibility Analysis:")
    for service_id, sig in signatures.items():
        compatible_with = []
        for other_id, other_sig in signatures.items():
            if service_id != other_id:
                if can_chain_services(sig, other_sig):
                    compatible_with.append(other_id)

        print(f"  {service_id} can chain to: {compatible_with}")

    # Performance characteristics
    print(f"\nPerformance Characteristics:")
    for service_id, sig in signatures.items():
        latency = sig.estimated_latency_ms or "unknown"
        memory = sig.memory_usage_mb or "unknown"
        complexity = sig.algorithm_complexity
        print(f"  {service_id}: {latency}ms, {memory}MB, {complexity}")

    # Potential chains
    print(f"\nSuggested Service Chains:")
    chains = find_potential_chains(signatures)
    if chains:
        for i, chain in enumerate(chains[:5]):  # Top 5 chains
            chain_desc = " → ".join([f"{svc}({signatures[svc].semantic_purpose})" for svc in chain])
            print(f"  Chain {i + 1}: {chain_desc}")
    else:
        print("  No compatible chains found")


def create_enhanced_analysis_summary(signatures: Dict[str, ComputationalSignature],
                                     vector_space: ComputationalVectorSpace):
    """Create enhanced analysis summary with vector space capabilities"""
    if not signatures:
        print("No signatures to analyze")
        return

    print("\n" + "=" * 70)
    print("ENHANCED COMPUTATIONAL SPACE ANALYSIS")
    print("=" * 70)

    # Original compatibility analysis
    create_analysis_summary(signatures)

    # Vector space analysis
    if vector_space and len(vector_space.services) > 1:
        print("\n" + "=" * 50)
        print("VECTOR SPACE ANALYSIS")
        print("=" * 50)

        # Space statistics
        stats = vector_space.get_space_statistics()
        print(f"\nVector Space Statistics:")
        print(f"  Total Services: {stats['total_services']}")
        print(f"  Vector Dimension: {stats['vector_dimension']}")
        print(f"  Embedding Model: {stats['embedding_model']}")

        print(f"\nSemantic Purpose Distribution:")
        for purpose, count in stats['semantic_purposes'].items():
            print(f"  {purpose}: {count}")

        print(f"\nPerformance Categories:")
        for category, count in stats['performance_categories'].items():
            print(f"  {category}: {count}")

        # Demonstrate semantic search
        print(f"\nSemantic Search Examples:")

        search_queries = [
            "validate data",
            "store information",
            "process files",
            "communicate with external services"
        ]

        for query in search_queries:
            try:
                results = vector_space.semantic_search(query, top_k=3)
                if results:
                    print(f"\n  Query: '{query}'")
                    for service_id, similarity in results:
                        print(f"    {service_id}: {similarity:.3f} similarity")
            except Exception as e:
                print(f"  Search failed for '{query}': {e}")

        # Demonstrate similarity search
        print(f"\nService Similarity Analysis:")

        service_ids = list(vector_space.services.keys())
        if len(service_ids) >= 2:
            try:
                for service_id in service_ids[:3]:  # Test first 3 services
                    similar = vector_space.find_similar_services(service_id, top_k=2)
                    if similar:
                        print(f"\n  Services similar to {service_id}:")
                        for sim_id, similarity in similar:
                            print(f"    {sim_id}: {similarity:.3f} similarity")
            except Exception as e:
                print(f"  Similarity analysis failed: {e}")

        # Vector space visualization
        print(f"\nVector Space Visualization:")
        try:
            viz_data = vector_space.visualize_space(method='pca')
            if 'error' not in viz_data:
                print(f"  ✅ Generated 2D visualization with {len(viz_data['service_ids'])} services")
                print(f"  Coordinates shape: {len(viz_data['coordinates'])}x2")

                # Save visualization data
                with open('vector_space_visualization.json', 'w') as f:
                    json.dump(viz_data, f, indent=2)
                print(f"  💾 Saved visualization data to vector_space_visualization.json")
            else:
                print(f"  ❌ Visualization failed: {viz_data['error']}")
        except Exception as e:
            print(f"  ❌ Visualization error: {e}")
    else:
        print("\n⚠️  Vector space not available or insufficient services")
        if not SENTENCE_TRANSFORMERS_AVAILABLE or not SKLEARN_AVAILABLE:
            print("Install dependencies: pip install sentence-transformers scikit-learn")


def demo_vector_space_navigation(vector_space: ComputationalVectorSpace):
    """Demo advanced vector space navigation capabilities"""
    if not vector_space or len(vector_space.services) < 2:
        print("⚠️  Need at least 2 services for navigation demo")
        return

    print("\n" + "=" * 50)
    print("VECTOR SPACE NAVIGATION DEMO")
    print("=" * 50)

    # Demo natural language queries
    print("\n🔍 Natural Language Service Discovery:")

    nl_queries = [
        "I need to validate user input",
        "Store data permanently",
        "Transform file contents",
        "Send notifications to users",
        "Fast processing with low latency"
    ]

    for query in nl_queries:
        try:
            results = vector_space.semantic_search(query, top_k=2)
            print(f"\nQuery: '{query}'")
            if results:
                for service_id, score in results:
                    service = vector_space.services[service_id]
                    purpose = service.signature.semantic_purpose
                    latency = service.signature.estimated_latency_ms or 'unknown'
                    print(f"  → {service_id} ({purpose}) - {score:.3f} match, {latency}ms")
            else:
                print(f"  → No matches found")
        except Exception as e:
            print(f"  → Search error: {e}")

    # Demo service chain suggestions
    print(f"\n🔗 Intelligent Service Chain Suggestions:")

    try:
        # Find chains for common workflows
        workflows = [
            ("validation", "storage"),
            ("transformation", "communication"),
            ("passthrough", "validation")
        ]

        for start_purpose, end_purpose in workflows:
            start_services = [
                sid for sid, service in vector_space.services.items()
                if service.signature.semantic_purpose == start_purpose
            ]
            end_services = [
                sid for sid, service in vector_space.services.items()
                if service.signature.semantic_purpose == end_purpose
            ]

            if start_services and end_services:
                start_id = start_services[0]
                end_id = end_services[0]

                print(f"\nWorkflow: {start_purpose} → {end_purpose}")
                print(f"  Suggested chain: {start_id} → {end_id}")

                # Check compatibility
                start_sig = vector_space.services[start_id].signature
                end_sig = vector_space.services[end_id].signature

                engine = PatternCompatibilityEngine()
                compatible = engine.can_chain_services(start_sig, end_sig)

                print(f"  Compatibility: {'✅' if compatible else '❌'}")

                if compatible:
                    similarity = vector_space.services[start_id].similarity_to(vector_space.services[end_id])
                    print(f"  Semantic similarity: {similarity:.3f}")

    except Exception as e:
        print(f"Chain suggestion error: {e}")

    print("\n🎯 Vector space navigation complete!")


def save_vector_space_data(vector_space: ComputationalVectorSpace, filename: str = "computational_vector_space.json"):
    """Save vector space data for future use"""
    if not vector_space:
        return

    try:
        # Prepare data for serialization
        space_data = {
            'metadata': {
                'dimension': vector_space.dimension,
                'semantic_dim': vector_space.semantic_dim,
                'total_services': len(vector_space.services),
                'created_at': datetime.now().isoformat()
            },
            'services': {},
            'statistics': vector_space.get_space_statistics()
        }

        # Save service data (signatures + metadata, vectors are too large for JSON)
        for service_id, vectorized in vector_space.services.items():
            space_data['services'][service_id] = {
                'signature': asdict(vectorized.signature),
                'metadata': vectorized.metadata,
                'vector_shape': list(vectorized.vector.shape),
                'vector_norm': float(np.linalg.norm(vectorized.vector))
            }

        # Save to file
        with open(filename, 'w') as f:
            json.dump(space_data, f, indent=2)

        print(f"💾 Vector space data saved to {filename}")

    except Exception as e:
        print(f"Failed to save vector space data: {e}")


def test_with_sample_services():
    """Test analyzer with sample service definitions"""
    analyzer = ComputationalSignatureAnalyzer()

    # Sample email validator service
    email_validator_code = '''
import re
from fastapi import FastAPI

app = FastAPI(title="email validator", description="validates email addresses")

@app.post("/process")
async def validate_email(request):
    email = request.data
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}#!/usr/bin/env python3
"""
Complete Computational Signature Analyzer with Vector Space Integration
Analyzes microservices and builds both compatibility matrix and navigable vector space
"""

import ast
import json
import re
import requests
from typing import Dict, List, Set, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
from datetime import datetime
from enum import Enum
from collections import Counter

# Import your interaction patterns (make sure this file is in the same directory)
try:
    from interaction_patterns import INTERACTION_PATTERNS, PatternRegistry, DataPattern, StatePattern
except ImportError:
    print("Warning: interaction_patterns.py not found. Some features may be limited.")
    INTERACTION_PATTERNS = {}

# Optional dependencies with fallbacks
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    print("Note: sentence-transformers not available. Using fallback embeddings.")
    print("Install with: pip install sentence-transformers")
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.manifold import TSNE
    from sklearn.decomposition import PCA
    SKLEARN_AVAILABLE = True
except ImportError:
    print("Note: scikit-learn not available. Some features limited.")
    print("Install with: pip install scikit-learn")
    SKLEARN_AVAILABLE = False


@dataclass
class ComputationalSignature:
    """Complete computational signature for a service"""

    # Service Identity
    service_id: str
    version: str
    analyzed_at: str

    # Semantic Understanding (from code analysis)
    semantic_purpose: str
    domain_context: List[str]
    business_intent: str
    transformation_type: str

    # Technical Interface (from contracts)
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    interaction_pattern: str
    endpoint_patterns: List[str]

    # Computational Behavior (from code analysis)
    algorithm_complexity: str
    side_effects: List[str]
    external_dependencies: List[str]
    error_modes: List[str]
    data_flow_pattern: str

    # Compatibility Information (enhanced)
    compatible_inputs: List[str]
    compatible_outputs: List[str]
    chainable_before: List[str]
    chainable_after: List[str]
    pattern_compatibility: Dict[str, bool]

    # Performance Characteristics (from contract/code)
    estimated_latency_ms: Optional[float]
    memory_usage_mb: Optional[float]
    cpu_intensity: str

    # Code Metrics
    lines_of_code: int
    cyclomatic_complexity: int
    external_api_calls: int

    # Extracted Keywords (for search)
    semantic_keywords: List[str]
    technical_keywords: List[str]


@dataclass 
class VectorizedService:
    """A service represented in vector space"""
    service_id: str
    signature: ComputationalSignature
    vector: np.ndarray
    metadata: Dict

    def similarity_to(self, other: 'VectorizedService') -> float:
        """Compute cosine similarity to another service"""
        if SKLEARN_AVAILABLE:
            return cosine_similarity([self.vector], [other.vector])[0][0]
        else:
            # Fallback cosine similarity implementation
            dot_product = np.dot(self.vector, other.vector)
            norms = np.linalg.norm(self.vector) * np.linalg.norm(other.vector)
            return dot_product / norms if norms > 0 else 0.0


class ComputationalVectorSpace:
    """
    Vector space for computational signatures
    Enables semantic navigation and similarity search
    """

    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        self.services: Dict[str, VectorizedService] = {}
        self.dimension = 445  # Total vector dimension

        # Initialize embedding model if available
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer(embedding_model)
                self.semantic_dim = 384  # all-MiniLM-L6-v2 dimension
                print(f"✅ Loaded embedding model: {embedding_model}")
            except Exception as e:
                print(f"Warning: Could not load embedding model: {e}")
                self.embedding_model = None
                self.semantic_dim = 50  # Fallback dimension
        else:
            self.embedding_model = None
            self.semantic_dim = 50  # Fallback dimension

        # Adjust total dimension based on semantic dimension
        self.dimension = self.semantic_dim + 61  # semantic + technical + domain + performance + compatibility

    def add_service(self, signature: ComputationalSignature) -> VectorizedService:
        """Add a service signature to the vector space"""

        # Convert signature to vector
        vector = self._signature_to_vector(signature)

        # Create metadata for filtering/search
        metadata = self._extract_searchable_metadata(signature)

        # Create vectorized service
        vectorized = VectorizedService(
            service_id=signature.service_id,
            signature=signature,
            vector=vector,
            metadata=metadata
        )

        self.services[signature.service_id] = vectorized

        return vectorized

    def _signature_to_vector(self, sig: ComputationalSignature) -> np.ndarray:
        """Convert computational signature to dense vector"""

        # 1. Semantic Embedding
        semantic_vector = self._get_semantic_embedding(sig)

        # 2. Technical Features (15D)
        technical_features = self._extract_technical_features(sig)

        # 3. Domain Features (20D) 
        domain_features = self._extract_domain_features(sig)

        # 4. Performance Features (6D)
        performance_features = self._extract_performance_features(sig)

        # 5. Compatibility Features (20D)
        compatibility_features = self._extract_compatibility_features(sig)

        # Combine all features
        full_vector = np.concatenate([
            semantic_vector,        # Variable D (384 or 50)
            technical_features,     # 15D
            domain_features,        # 20D  
            performance_features,   # 6D
            compatibility_features  # 20D
        ])

        return full_vector

    def _get_semantic_embedding(self, sig: ComputationalSignature) -> np.ndarray:
        """Get semantic embedding for the service"""
        # Build semantic text
        components = [
            sig.semantic_purpose,
            sig.business_intent,
            sig.transformation_type,
            ' '.join(sig.domain_context),
            ' '.join(sig.semantic_keywords[:5]),  # Top 5 keywords
        ]
        semantic_text = ' '.join(filter(None, components))

        if self.embedding_model:
            try:
                return self.embedding_model.encode(semantic_text)
            except Exception as e:
                print(f"Warning: Embedding failed: {e}")

        # Fallback: simple text-based features
        return self._simple_text_embedding(semantic_text)

    def _simple_text_embedding(self, text: str) -> np.ndarray:
        """Simple fallback embedding when sentence-transformers unavailable"""
        # Create simple hash-based features
        features = np.zeros(self.semantic_dim)

        words = text.lower().split()
        for i, word in enumerate(words[:self.semantic_dim]):
            # Simple hash-based encoding
            hash_val = hash(word) % self.semantic_dim
            features[hash_val] += 1.0

        # Normalize
        norm = np.linalg.norm(features)
        if norm > 0:
            features = features / norm

        return features

    def _extract_technical_features(self, sig: ComputationalSignature) -> np.ndarray:
        """Extract technical features (15D)"""
        features = np.zeros(15)

        # Interaction pattern (one-hot, 7D)
        pattern_mapping = {
            'synchronous_stateless': 0,
            'synchronous_persistent': 1, 
            'synchronous_session_based': 2,
            'asynchronous_stateless': 3,
            'asynchronous_persistent': 4,
            'streaming_stateless': 5,
            'event_driven_stateless': 6
        }
        pattern_idx = pattern_mapping.get(sig.interaction_pattern, 0)
        features[pattern_idx] = 1.0

        # Complexity (1D)
        complexity_mapping = {'O(1)': 1, 'O(log n)': 2, 'O(n)': 3, 'O(n^2)': 4}
        features[7] = complexity_mapping.get(sig.algorithm_complexity, 1)

        # Side effects count (1D)
        features[8] = len(sig.side_effects)

        # External dependencies count (1D)  
        features[9] = len(sig.external_dependencies)

        # Lines of code (normalized, 1D)
        features[10] = min(sig.lines_of_code / 1000.0, 1.0) if sig.lines_of_code else 0.0

        # Cyclomatic complexity (normalized, 1D)
        features[11] = min(sig.cyclomatic_complexity / 20.0, 1.0) if sig.cyclomatic_complexity else 0.0

        # API calls count (1D)
        features[12] = min(sig.external_api_calls / 10.0, 1.0) if sig.external_api_calls else 0.0

        # Has error handling (1D)
        features[13] = 1.0 if sig.error_modes else 0.0

        # Data flow type (1D)
        flow_mapping = {'passthrough': 1, 'transform': 2, 'consumer': 3, 'producer': 4}
        features[14] = flow_mapping.get(sig.data_flow_pattern, 0)

        return features

    def _extract_domain_features(self, sig: ComputationalSignature) -> np.ndarray:
        """Extract domain context features (20D)"""
        features = np.zeros(20)

        # Common domains (one-hot encoding)
        domains = [
            'email', 'weather', 'file', 'database', 'api', 
            'text', 'image', 'user', 'payment', 'notification',
            'validation', 'transformation', 'storage', 'communication',
            'monitoring', 'security', 'analytics', 'workflow', 'testing', 'general'
        ]

        for i, domain in enumerate(domains):
            if domain in sig.domain_context:
                features[i] = 1.0

        return features

    def _extract_performance_features(self, sig: ComputationalSignature) -> np.ndarray:
        """Extract performance characteristics (6D)"""
        features = np.zeros(6)

        # Latency (normalized to 0-1, where 1000ms = 1.0)
        features[0] = min((sig.estimated_latency_ms or 100) / 1000.0, 1.0)

        # Memory (normalized to 0-1, where 1GB = 1.0)
        features[1] = min((sig.memory_usage_mb or 50) / 1024.0, 1.0)

        # CPU intensity
        cpu_mapping = {'low': 0.2, 'medium': 0.5, 'high': 1.0, 'unknown': 0.3}
        features[2] = cpu_mapping.get(sig.cpu_intensity, 0.3)

        # Has network dependencies
        features[3] = 1.0 if any('network' in dep for dep in sig.external_dependencies) else 0.0

        # Has disk dependencies  
        features[4] = 1.0 if any('disk' in effect or 'file' in effect for effect in sig.side_effects) else 0.0

        # Scalability indicator (inverse of complexity * dependencies)
        complexity_score = len(sig.external_dependencies) + len(sig.side_effects)
        features[5] = max(0.1, 1.0 - (complexity_score / 10.0))

        return features

    def _extract_compatibility_features(self, sig: ComputationalSignature) -> np.ndarray:
        """Extract type compatibility features (20D)"""
        features = np.zeros(20)

        # Input types (one-hot)
        input_types = ['string', 'integer', 'float', 'boolean', 'object', 'array', 'email', 'url', 'file', 'any']
        for i, type_name in enumerate(input_types):
            if type_name in sig.compatible_inputs:
                features[i] = 1.0

        # Output types (one-hot)  
        output_types = ['string', 'integer', 'float', 'boolean', 'object', 'array', 'email', 'url', 'file', 'any']
        for i, type_name in enumerate(output_types):
            if type_name in sig.compatible_outputs:
                features[i + 10] = 1.0

        return features

    def _extract_searchable_metadata(self, sig: ComputationalSignature) -> Dict:
        """Extract metadata for filtering and search"""
        return {
            'semantic_purpose': sig.semantic_purpose,
            'interaction_pattern': sig.interaction_pattern, 
            'domain_context': sig.domain_context,
            'input_types': sig.compatible_inputs,
            'output_types': sig.compatible_outputs,
            'side_effects': sig.side_effects,
            'external_dependencies': sig.external_dependencies,
            'performance_category': self._categorize_performance(sig),
            'complexity_category': self._categorize_complexity(sig)
        }

    def _categorize_performance(self, sig: ComputationalSignature) -> str:
        """Categorize performance for filtering"""
        latency = sig.estimated_latency_ms or 100
        if latency < 50:
            return 'fast'
        elif latency < 500:
            return 'medium'
        else:
            return 'slow'

    def _categorize_complexity(self, sig: ComputationalSignature) -> str:
        """Categorize algorithmic complexity"""
        if sig.algorithm_complexity in ['O(1)', 'O(log n)']:
            return 'simple'
        elif sig.algorithm_complexity == 'O(n)':
            return 'linear'
        else:
            return 'complex'

    def find_similar_services(self, 
                            query_service_id: str, 
                            top_k: int = 5,
                            exclude_self: bool = True) -> List[Tuple[str, float]]:
        """Find services similar to the query service"""

        if query_service_id not in self.services:
            raise ValueError(f"Service {query_service_id} not found")

        query_service = self.services[query_service_id]
        similarities = []

        for service_id, service in self.services.items():
            if exclude_self and service_id == query_service_id:
                continue

            similarity = query_service.similarity_to(service)
            similarities.append((service_id, similarity))

        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    def semantic_search(self, 
                       query_text: str, 
                       top_k: int = 5,
                       filters: Dict = None) -> List[Tuple[str, float]]:
        """Search services using natural language query"""

        # Get query embedding
        if self.embedding_model:
            try:
                query_vector = self.embedding_model.encode(query_text)
            except Exception:
                query_vector = self._simple_text_embedding(query_text)
        else:
            query_vector = self._simple_text_embedding(query_text)

        similarities = []

        for service_id, service in self.services.items():
            # Apply filters if provided
            if filters and not self._matches_filters(service, filters):
                continue

            # Compute similarity (focus on semantic part)
            service_semantic = service.vector[:len(query_vector)]

            if SKLEARN_AVAILABLE:
                semantic_similarity = cosine_similarity([query_vector], [service_semantic])[0][0]
            else:
                # Fallback cosine similarity
                dot_product = np.dot(query_vector, service_semantic)
                norms = np.linalg.norm(query_vector) * np.linalg.norm(service_semantic)
                semantic_similarity = dot_product / norms if norms > 0 else 0.0

            similarities.append((service_id, semantic_similarity))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    def _matches_filters(self, service: VectorizedService, filters: Dict) -> bool:
        """Check if service matches filter criteria"""
        metadata = service.metadata

        for key, value in filters.items():
            if key in metadata:
                if isinstance(value, list):
                    if not any(v in metadata[key] for v in value):
                        return False
                else:
                    if metadata[key] != value:
                        return False

        return True

    def visualize_space(self, method: str = 'pca') -> Dict:
        """Generate 2D visualization of the service space"""
        if len(self.services) < 2:
            return {'error': 'Need at least 2 services for visualization'}

        if not SKLEARN_AVAILABLE:
            return {'error': 'scikit-learn required for visualization'}

        vectors = np.array([service.vector for service in self.services.values()])
        service_ids = list(self.services.keys())

        # Dimensionality reduction
        if method == 'tsne':
            reducer = TSNE(n_components=2, random_state=42, perplexity=min(30, len(self.services)-1))
        else:  # PCA
            reducer = PCA(n_components=2)

        try:
            coords_2d = reducer.fit_transform(vectors)

            return {
                'coordinates': coords_2d.tolist(),
                'service_ids': service_ids,
                'metadata': [self.services[sid].metadata for sid in service_ids]
            }
        except Exception as e:
            return {'error': f'Visualization failed: {e}'}

    def get_space_statistics(self) -> Dict:
        """Get statistics about the vector space"""
        if not self.services:
            return {'error': 'No services in space'}

        # Collect statistics
        semantic_purposes = [s.metadata['semantic_purpose'] for s in self.services.values()]
        patterns = [s.metadata['interaction_pattern'] for s in self.services.values()]
        performance_cats = [s.metadata['performance_category'] for s in self.services.values()]

        return {
            'total_services': len(self.services),
            'vector_dimension': self.dimension,
            'semantic_purposes': dict(Counter(semantic_purposes)),
            'interaction_patterns': dict(Counter(patterns)),
            'performance_categories': dict(Counter(performance_cats)),
            'embedding_model': 'sentence-transformers' if self.embedding_model else 'fallback'
        }


class DataType(Enum):
    """Standard data types with automatic compatibility rules"""
    STRING = "string"
    INTEGER = "integer" 
    FLOAT = "float"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    EMAIL = "email"
    URL = "url"
    FILE = "file"
    JSON = "json"
    ANY = "any"


class PatternCompatibilityEngine:
    """Automatically determines service compatibility based on patterns"""

    def __init__(self):
        # Type compatibility matrix (automatic)
        self.type_compatibility = {
            DataType.STRING: {DataType.STRING, DataType.EMAIL, DataType.URL, DataType.JSON, DataType.ANY},
            DataType.EMAIL: {DataType.STRING, DataType.EMAIL, DataType.ANY},
            DataType.URL: {DataType.STRING, DataType.URL, DataType.ANY},
            DataType.INTEGER: {DataType.INTEGER, DataType.FLOAT, DataType.STRING, DataType.ANY},
            DataType.FLOAT: {DataType.FLOAT, DataType.INTEGER, DataType.STRING, DataType.ANY},
            DataType.BOOLEAN: {DataType.BOOLEAN, DataType.STRING, DataType.ANY},
            DataType.OBJECT: {DataType.OBJECT, DataType.JSON, DataType.STRING, DataType.ANY},
            DataType.ARRAY: {DataType.ARRAY, DataType.JSON, DataType.STRING, DataType.ANY},
            DataType.FILE: {DataType.FILE, DataType.STRING, DataType.ANY},
            DataType.JSON: {DataType.JSON, DataType.OBJECT, DataType.ARRAY, DataType.STRING, DataType.ANY},
            DataType.ANY: {dt for dt in DataType}  # ANY accepts everything
        }

        # Pattern compatibility matrix based on your interaction patterns
        self.pattern_compatibility = {
            "synchronous_stateless": {
                "synchronous_stateless",
                "synchronous_persistent", 
                "synchronous_session_based"
            },
            "synchronous_persistent": {
                "synchronous_stateless",
                "synchronous_persistent"
            },
            "synchronous_session_based": {
                "synchronous_stateless",
                "synchronous_persistent",
                "synchronous_session_based"
            },
            "asynchronous_stateless": {
                "synchronous_stateless",  # Async can call sync
                "synchronous_persistent"
            },
            "asynchronous_persistent": {
                "synchronous_stateless",
                "synchronous_persistent"
            },
            "streaming_stateless": {
                "streaming_stateless",
                "synchronous_stateless"  # Can process stream chunks
            },
            "event_driven_stateless": {
                "synchronous_stateless",
                "event_driven_stateless"
            }
        }

    def can_chain_services(self, service_a: ComputationalSignature, service_b: ComputationalSignature) -> bool:
        """
        Determine if service A can chain to service B
        Based on type compatibility + pattern compatibility + semantic compatibility
        """

        # 1. Type compatibility check
        type_compatible = self._check_type_compatibility(service_a, service_b)

        # 2. Pattern compatibility check  
        pattern_compatible = self._check_pattern_compatibility(service_a, service_b)

        # 3. Semantic compatibility check
        semantic_compatible = self._check_semantic_compatibility(service_a, service_b)

        # 4. Side effect compatibility
        side_effect_compatible = self._check_side_effect_compatibility(service_a, service_b)

        return (type_compatible and 
                pattern_compatible and 
                semantic_compatible and 
                side_effect_compatible)

    def _check_type_compatibility(self, service_a: ComputationalSignature, service_b: ComputationalSignature) -> bool:
        """Check if output type can feed into input type"""

        # Get primary output type from service A
        output_types = service_a.compatible_outputs or ["string"]
        input_types = service_b.compatible_inputs or ["string"]

        # Convert to DataType enums
        def to_data_type(type_str: str) -> DataType:
            type_mapping = {
                "string": DataType.STRING,
                "integer": DataType.INTEGER,
                "float": DataType.FLOAT,
                "boolean": DataType.BOOLEAN,
                "object": DataType.OBJECT,
                "array": DataType.ARRAY,
                "email": DataType.EMAIL,
                "url": DataType.URL,
                "file": DataType.FILE,
                "json": DataType.JSON,
                "any": DataType.ANY
            }
            return type_mapping.get(type_str.lower(), DataType.STRING)

        # Check if any output type is compatible with any input type
        for output_type_str in output_types:
            output_type = to_data_type(output_type_str)
            compatible_types = self.type_compatibility.get(output_type, {DataType.STRING})

            for input_type_str in input_types:
                input_type = to_data_type(input_type_str)
                if input_type in compatible_types:
                    return True

        return False

    def _check_pattern_compatibility(self, service_a: ComputationalSignature, service_b: ComputationalSignature) -> bool:
        """Check if interaction patterns can be chained"""
        pattern_a = service_a.interaction_pattern
        pattern_b = service_b.interaction_pattern

        compatible_patterns = self.pattern_compatibility.get(pattern_a, set())
        return pattern_b in compatible_patterns

    def _check_semantic_compatibility(self, service_a: ComputationalSignature, service_b: ComputationalSignature) -> bool:
        """Check if the semantic flow makes sense"""

        # Define semantic flow rules based on your services
        semantic_flows = {
            "passthrough": {"validation", "transformation", "storage", "communication", "routing", "processing"},
            "validation": {"storage", "transformation", "communication", "routing", "processing"}, 
            "transformation": {"validation", "storage", "communication", "routing", "processing"},
            "storage": {"communication", "routing"},  # Storage usually ends chains
            "retrieval": {"validation", "transformation", "communication", "routing", "processing"},
            "communication": {"storage", "routing", "processing"},  # Communication often ends chains
            "computation": {"validation", "transformation", "storage", "communication", "routing", "processing"},
            "routing": {"validation", "transformation", "storage", "communication", "processing"},
            "monitoring": {"validation", "transformation", "storage", "communication", "routing", "processing"},  # Monitoring can go anywhere
            "processing": {"validation", "transformation", "storage", "communication", "routing", "processing"},  # Generic processing
            "unknown": {"validation", "transformation", "storage", "communication", "routing", "processing"}  # Unknown can go most places
        }

        # Get compatible semantic purposes for service A
        compatible_purposes = semantic_flows.get(service_a.semantic_purpose, set())

        # Check if service B's purpose is compatible
        is_compatible = (
            service_b.semantic_purpose in compatible_purposes or
            service_a.semantic_purpose == "passthrough" or  # Passthrough goes anywhere
            service_b.semantic_purpose == "monitoring" or   # Monitoring accepts anything
            service_a.semantic_purpose == "unknown" or      # Unknown can try to go anywhere
            service_b.semantic_purpose == "unknown"         # Unknown can accept anything
        )

        return is_compatible

    def _check_side_effect_compatibility(self, service_a: ComputationalSignature, service_b: ComputationalSignature) -> bool:
        """Check if side effects are compatible"""

        # Some side effects make chaining problematic
        problematic_combinations = [
            # Don't chain two services that both do heavy network calls
            ({"network_call"}, {"network_call"}),
            # Don't chain two file writers (could conflict)
            ({"file_write"}, {"file_write"}),
        ]

        a_effects = set(service_a.side_effects)
        b_effects = set(service_b.side_effects)

        for prob_a, prob_b in problematic_combinations:
            if prob_a.issubset(a_effects) and prob_b.issubset(b_effects):
                return False

        return True


class ServiceCodeAnalyzer:
    """Analyzes service source code to extract computational patterns"""

    def __init__(self):
        self.semantic_patterns = {
            'validation': ['validate', 'verify', 'check', 'confirm', 'test'],
            'transformation': ['transform', 'convert', 'change', 'modify', 'process'],
            'storage': ['store', 'save', 'persist', 'write', 'insert'],
            'retrieval': ['get', 'fetch', 'read', 'load', 'retrieve'],
            'communication': ['send', 'post', 'email', 'notify', 'message'],
            'computation': ['calculate', 'compute', 'analyze', 'generate'],
            'routing': ['route', 'forward', 'dispatch', 'redirect'],
            'monitoring': ['monitor', 'track', 'log', 'audit', 'measure']
        }

    def analyze_code(self, code_content: str, file_path: str = None) -> Dict[str, Any]:
        """Main code analysis pipeline"""
        try:
            tree = ast.parse(code_content)

            analysis = {
                'semantic_purpose': self._extract_semantic_purpose(code_content, tree),
                'domain_context': self._extract_domain_context(code_content),
                'business_intent': self._extract_business_intent(code_content),
                'transformation_type': self._classify_transformation(tree, code_content),
                'algorithm_complexity': 'O(1)',  # Simplified
                'side_effects': self._detect_side_effects(tree),
                'external_dependencies': self._find_external_dependencies(tree),
                'error_modes': ['general_error'],  # Simplified
                'data_flow_pattern': 'transform',  # Simplified
                'endpoint_patterns': self._extract_endpoints(tree),
                'lines_of_code': len(code_content.split('\n')),
                'cyclomatic_complexity': 3,  # Simplified
                'external_api_calls': self._count_api_calls(tree),
                'semantic_keywords': self._extract_semantic_keywords(code_content),
                'technical_keywords': self._extract_technical_keywords(tree)
            }

            return analysis

        except Exception as e:
            return {'error': f"Code analysis failed: {str(e)}"}

    def _extract_semantic_purpose(self, code: str, tree: ast.AST) -> str:
        """Determine the main semantic purpose of the service"""
        code_lower = code.lower()

        # Look for explicit purpose indicators in code
        for purpose, keywords in self.semantic_patterns.items():
            if any(keyword in code_lower for keyword in keywords):
                return purpose

    if re.match(pattern, email):
        return {"data": email, "valid": True, "status": "success"}
    else:
        return {"data": email, "valid": False, "status": "invalid_email"}
'''

    email_validator_contract = {
        "service_metadata": {
            "service_id": "email-validator",
            "pattern": "synchronous_stateless",
            "description": "Validates email address format using regex patterns"
        },
        "interface_contract": {
            "inputs": {"email": {"type": "string"}},
            "outputs": {"validation_result": {"type": "object"}}
        },
        "resource_requirements": {"max_execution_time": "50ms", "memory_limit": "5MB"}
    }

    # Sample text transformer service
    text_transformer_code = '''
from fastapi import FastAPI

app = FastAPI(title="text transformer", description="transforms text case")

@app.post("/process")  
async def transform_text(request):
    text = request.data
    operation = request.metadata.get("operation", "uppercase")

    if operation == "uppercase":
        result = text.upper()
    elif operation == "lowercase":
        result = text.lower()
    else:
        result = text

    return {"data": result, "status": "success"}
'''

    text_transformer_contract = {
        "service_metadata": {
            "service_id": "text-transformer",
            "pattern": "synchronous_stateless",
            "description": "Transforms text to uppercase or lowercase"
        },
        "interface_contract": {
            "inputs": {"text": {"type": "string"}},
            "outputs": {"text": {"type": "string"}}
        },
        "resource_requirements": {"max_execution_time": "20ms", "memory_limit": "8MB"}
    }

    # Analyze both services
    email_sig = analyzer.analyze_service(
        "email-validator", email_validator_code, None, email_validator_contract
    )

    transformer_sig = analyzer.analyze_service(
        "text-transformer", text_transformer_code, None, text_transformer_contract
    )

    signatures = {
        "email-validator": email_sig,
        "text-transformer": transformer_sig
    }

    print("=== SAMPLE SERVICES ANALYSIS ===")
    create_analysis_summary(signatures)

    return signatures


def main():
    """Enhanced main function with vector space integration"""
    print("Enhanced Computational Signature Analyzer with Vector Space")
    print("=" * 60)

    # Test with sample services first
    print("\n1. Testing with sample services...")
    test_signatures = test_with_sample_services()

    # Try to analyze your actual services
    print("\n\n2. Analyzing your Docker services...")
    real_signatures, vector_space = analyze_your_services()

    if real_signatures:
        print(f"\n✅ Successfully analyzed {len(real_signatures)} services!")
        print("📁 Individual signature files saved for each service.")

        # Save vector space data
        save_vector_space_data(vector_space)

        # Demo vector space navigation
        if vector_space and len(vector_space.services) > 1:
            demo_vector_space_navigation(vector_space)

        print("\n🎉 ANALYSIS COMPLETE!")
        print("\nWhat you now have:")
        print("  • Rich computational signatures for each service")
        print("  • Pattern-based compatibility matrix")
        print("  • Navigable vector space for semantic search")
        print("  • Service similarity analysis")
        print("  • Natural language query capabilities")
        print("  • Intelligent service chain suggestions")

        print("\n🚀 Next steps:")
        print("  • Try semantic queries: 'find services that validate data'")
        print("  • Explore service similarities and clustering")
        print("  • Build AI orchestration using the vector space")
        print("  • Visualize the computational space")

    else:
        print("\n❌ Could not connect to your service registry.")
        print("Make sure Docker services are running:")
        print("  docker-compose up -d")
        print("  curl http://localhost:8004/services")

        print("\n📋 What was demonstrated:")
        print("  • Sample service analysis working")
        print("  • Pattern-based compatibility detection")
        print("  • Vector space construction (with fallbacks)")

    print("\n" + "=" * 60)
    print("Computational Space Navigation System Ready! 🧭")


if __name__ == "__main__":
    main()  # !/usr/bin/env python3
"""
Complete Computational Signature Analyzer with Vector Space Integration
Analyzes microservices and builds both compatibility matrix and navigable vector space
"""

import ast
import json
import re
import requests
from typing import Dict, List, Set, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
from datetime import datetime
from enum import Enum
from collections import Counter

# Import your interaction patterns (make sure this file is in the same directory)
try:
    from interaction_patterns import INTERACTION_PATTERNS, PatternRegistry, DataPattern, StatePattern
except ImportError:
    print("Warning: interaction_patterns.py not found. Some features may be limited.")
    INTERACTION_PATTERNS = {}

# Optional dependencies with fallbacks
try:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    print("Note: sentence-transformers not available. Using fallback embeddings.")
    print("Install with: pip install sentence-transformers")
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.manifold import TSNE
    from sklearn.decomposition import PCA

    SKLEARN_AVAILABLE = True
except ImportError:
    print("Note: scikit-learn not available. Some features limited.")
    print("Install with: pip install scikit-learn")
    SKLEARN_AVAILABLE = False


@dataclass
class ComputationalSignature:
    """Complete computational signature for a service"""

    # Service Identity
    service_id: str
    version: str
    analyzed_at: str

    # Semantic Understanding (from code analysis)
    semantic_purpose: str
    domain_context: List[str]
    business_intent: str
    transformation_type: str

    # Technical Interface (from contracts)
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    interaction_pattern: str
    endpoint_patterns: List[str]

    # Computational Behavior (from code analysis)
    algorithm_complexity: str
    side_effects: List[str]
    external_dependencies: List[str]
    error_modes: List[str]
    data_flow_pattern: str

    # Compatibility Information (enhanced)
    compatible_inputs: List[str]
    compatible_outputs: List[str]
    chainable_before: List[str]
    chainable_after: List[str]
    pattern_compatibility: Dict[str, bool]

    # Performance Characteristics (from contract/code)
    estimated_latency_ms: Optional[float]
    memory_usage_mb: Optional[float]
    cpu_intensity: str

    # Code Metrics
    lines_of_code: int
    cyclomatic_complexity: int
    external_api_calls: int

    # Extracted Keywords (for search)
    semantic_keywords: List[str]
    technical_keywords: List[str]


@dataclass
class VectorizedService:
    """A service represented in vector space"""
    service_id: str
    signature: ComputationalSignature
    vector: np.ndarray
    metadata: Dict

    def similarity_to(self, other: 'VectorizedService') -> float:
        """Compute cosine similarity to another service"""
        if SKLEARN_AVAILABLE:
            return cosine_similarity([self.vector], [other.vector])[0][0]
        else:
            # Fallback cosine similarity implementation
            dot_product = np.dot(self.vector, other.vector)
            norms = np.linalg.norm(self.vector) * np.linalg.norm(other.vector)
            return dot_product / norms if norms > 0 else 0.0


class ComputationalVectorSpace:
    """
    Vector space for computational signatures
    Enables semantic navigation and similarity search
    """

    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        self.services: Dict[str, VectorizedService] = {}
        self.dimension = 445  # Total vector dimension

        # Initialize embedding model if available
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer(embedding_model)
                self.semantic_dim = 384  # all-MiniLM-L6-v2 dimension
                print(f"✅ Loaded embedding model: {embedding_model}")
            except Exception as e:
                print(f"Warning: Could not load embedding model: {e}")
                self.embedding_model = None
                self.semantic_dim = 50  # Fallback dimension
        else:
            self.embedding_model = None
            self.semantic_dim = 50  # Fallback dimension

        # Adjust total dimension based on semantic dimension
        self.dimension = self.semantic_dim + 61  # semantic + technical + domain + performance + compatibility

    def add_service(self, signature: ComputationalSignature) -> VectorizedService:
        """Add a service signature to the vector space"""

        # Convert signature to vector
        vector = self._signature_to_vector(signature)

        # Create metadata for filtering/search
        metadata = self._extract_searchable_metadata(signature)

        # Create vectorized service
        vectorized = VectorizedService(
            service_id=signature.service_id,
            signature=signature,
            vector=vector,
            metadata=metadata
        )

        self.services[signature.service_id] = vectorized

        return vectorized

    def _signature_to_vector(self, sig: ComputationalSignature) -> np.ndarray:
        """Convert computational signature to dense vector"""

        # 1. Semantic Embedding
        semantic_vector = self._get_semantic_embedding(sig)

        # 2. Technical Features (15D)
        technical_features = self._extract_technical_features(sig)

        # 3. Domain Features (20D)
        domain_features = self._extract_domain_features(sig)

        # 4. Performance Features (6D)
        performance_features = self._extract_performance_features(sig)

        # 5. Compatibility Features (20D)
        compatibility_features = self._extract_compatibility_features(sig)

        # Combine all features
        full_vector = np.concatenate([
            semantic_vector,  # Variable D (384 or 50)
            technical_features,  # 15D
            domain_features,  # 20D
            performance_features,  # 6D
            compatibility_features  # 20D
        ])

        return full_vector

    def _get_semantic_embedding(self, sig: ComputationalSignature) -> np.ndarray:
        """Get semantic embedding for the service"""
        # Build semantic text
        components = [
            sig.semantic_purpose,
            sig.business_intent,
            sig.transformation_type,
            ' '.join(sig.domain_context),
            ' '.join(sig.semantic_keywords[:5]),  # Top 5 keywords
        ]
        semantic_text = ' '.join(filter(None, components))

        if self.embedding_model:
            try:
                return self.embedding_model.encode(semantic_text)
            except Exception as e:
                print(f"Warning: Embedding failed: {e}")

        # Fallback: simple text-based features
        return self._simple_text_embedding(semantic_text)

    def _simple_text_embedding(self, text: str) -> np.ndarray:
        """Simple fallback embedding when sentence-transformers unavailable"""
        # Create simple hash-based features
        features = np.zeros(self.semantic_dim)

        words = text.lower().split()
        for i, word in enumerate(words[:self.semantic_dim]):
            # Simple hash-based encoding
            hash_val = hash(word) % self.semantic_dim
            features[hash_val] += 1.0

        # Normalize
        norm = np.linalg.norm(features)
        if norm > 0:
            features = features / norm

        return features

    def _extract_technical_features(self, sig: ComputationalSignature) -> np.ndarray:
        """Extract technical features (15D)"""
        features = np.zeros(15)

        # Interaction pattern (one-hot, 7D)
        pattern_mapping = {
            'synchronous_stateless': 0,
            'synchronous_persistent': 1,
            'synchronous_session_based': 2,
            'asynchronous_stateless': 3,
            'asynchronous_persistent': 4,
            'streaming_stateless': 5,
            'event_driven_stateless': 6
        }
        pattern_idx = pattern_mapping.get(sig.interaction_pattern, 0)
        features[pattern_idx] = 1.0

        # Complexity (1D)
        complexity_mapping = {'O(1)': 1, 'O(log n)': 2, 'O(n)': 3, 'O(n^2)': 4}
        features[7] = complexity_mapping.get(sig.algorithm_complexity, 1)

        # Side effects count (1D)
        features[8] = len(sig.side_effects)

        # External dependencies count (1D)
        features[9] = len(sig.external_dependencies)

        # Lines of code (normalized, 1D)
        features[10] = min(sig.lines_of_code / 1000.0, 1.0) if sig.lines_of_code else 0.0

        # Cyclomatic complexity (normalized, 1D)
        features[11] = min(sig.cyclomatic_complexity / 20.0, 1.0) if sig.cyclomatic_complexity else 0.0

        # API calls count (1D)
        features[12] = min(sig.external_api_calls / 10.0, 1.0) if sig.external_api_calls else 0.0

        # Has error handling (1D)
        features[13] = 1.0 if sig.error_modes else 0.0

        # Data flow type (1D)
        flow_mapping = {'passthrough': 1, 'transform': 2, 'consumer': 3, 'producer': 4}
        features[14] = flow_mapping.get(sig.data_flow_pattern, 0)

        return features

    def _extract_domain_features(self, sig: ComputationalSignature) -> np.ndarray:
        """Extract domain context features (20D)"""
        features = np.zeros(20)

        # Common domains (one-hot encoding)
        domains = [
            'email', 'weather', 'file', 'database', 'api',
            'text', 'image', 'user', 'payment', 'notification',
            'validation', 'transformation', 'storage', 'communication',
            'monitoring', 'security', 'analytics', 'workflow', 'testing', 'general'
        ]

        for i, domain in enumerate(domains):
            if domain in sig.domain_context:
                features[i] = 1.0

        return features

    def _extract_performance_features(self, sig: ComputationalSignature) -> np.ndarray:
        """Extract performance characteristics (6D)"""
        features = np.zeros(6)

        # Latency (normalized to 0-1, where 1000ms = 1.0)
        features[0] = min((sig.estimated_latency_ms or 100) / 1000.0, 1.0)

        # Memory (normalized to 0-1, where 1GB = 1.0)
        features[1] = min((sig.memory_usage_mb or 50) / 1024.0, 1.0)

        # CPU intensity
        cpu_mapping = {'low': 0.2, 'medium': 0.5, 'high': 1.0, 'unknown': 0.3}
        features[2] = cpu_mapping.get(sig.cpu_intensity, 0.3)

        # Has network dependencies
        features[3] = 1.0 if any('network' in dep for dep in sig.external_dependencies) else 0.0

        # Has disk dependencies
        features[4] = 1.0 if any('disk' in effect or 'file' in effect for effect in sig.side_effects) else 0.0

        # Scalability indicator (inverse of complexity * dependencies)
        complexity_score = len(sig.external_dependencies) + len(sig.side_effects)
        features[5] = max(0.1, 1.0 - (complexity_score / 10.0))

        return features

    def _extract_compatibility_features(self, sig: ComputationalSignature) -> np.ndarray:
        """Extract type compatibility features (20D)"""
        features = np.zeros(20)

        # Input types (one-hot)
        input_types = ['string', 'integer', 'float', 'boolean', 'object', 'array', 'email', 'url', 'file', 'any']
        for i, type_name in enumerate(input_types):
            if type_name in sig.compatible_inputs:
                features[i] = 1.0

        # Output types (one-hot)
        output_types = ['string', 'integer', 'float', 'boolean', 'object', 'array', 'email', 'url', 'file', 'any']
        for i, type_name in enumerate(output_types):
            if type_name in sig.compatible_outputs:
                features[i + 10] = 1.0

        return features

    def _extract_searchable_metadata(self, sig: ComputationalSignature) -> Dict:
        """Extract metadata for filtering and search"""
        return {
            'semantic_purpose': sig.semantic_purpose,
            'interaction_pattern': sig.interaction_pattern,
            'domain_context': sig.domain_context,
            'input_types': sig.compatible_inputs,
            'output_types': sig.compatible_outputs,
            'side_effects': sig.side_effects,
            'external_dependencies': sig.external_dependencies,
            'performance_category': self._categorize_performance(sig),
            'complexity_category': self._categorize_complexity(sig)
        }

    def _categorize_performance(self, sig: ComputationalSignature) -> str:
        """Categorize performance for filtering"""
        latency = sig.estimated_latency_ms or 100
        if latency < 50:
            return 'fast'
        elif latency < 500:
            return 'medium'
        else:
            return 'slow'

    def _categorize_complexity(self, sig: ComputationalSignature) -> str:
        """Categorize algorithmic complexity"""
        if sig.algorithm_complexity in ['O(1)', 'O(log n)']:
            return 'simple'
        elif sig.algorithm_complexity == 'O(n)':
            return 'linear'
        else:
            return 'complex'

    def find_similar_services(self,
                              query_service_id: str,
                              top_k: int = 5,
                              exclude_self: bool = True) -> List[Tuple[str, float]]:
        """Find services similar to the query service"""

        if query_service_id not in self.services:
            raise ValueError(f"Service {query_service_id} not found")

        query_service = self.services[query_service_id]
        similarities = []

        for service_id, service in self.services.items():
            if exclude_self and service_id == query_service_id:
                continue

            similarity = query_service.similarity_to(service)
            similarities.append((service_id, similarity))

        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    def semantic_search(self,
                        query_text: str,
                        top_k: int = 5,
                        filters: Dict = None) -> List[Tuple[str, float]]:
        """Search services using natural language query"""

        # Get query embedding
        if self.embedding_model:
            try:
                query_vector = self.embedding_model.encode(query_text)
            except Exception:
                query_vector = self._simple_text_embedding(query_text)
        else:
            query_vector = self._simple_text_embedding(query_text)

        similarities = []

        for service_id, service in self.services.items():
            # Apply filters if provided
            if filters and not self._matches_filters(service, filters):
                continue

            # Compute similarity (focus on semantic part)
            service_semantic = service.vector[:len(query_vector)]

            if SKLEARN_AVAILABLE:
                semantic_similarity = cosine_similarity([query_vector], [service_semantic])[0][0]
            else:
                # Fallback cosine similarity
                dot_product = np.dot(query_vector, service_semantic)
                norms = np.linalg.norm(query_vector) * np.linalg.norm(service_semantic)
                semantic_similarity = dot_product / norms if norms > 0 else 0.0

            similarities.append((service_id, semantic_similarity))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    def _matches_filters(self, service: VectorizedService, filters: Dict) -> bool:
        """Check if service matches filter criteria"""
        metadata = service.metadata

        for key, value in filters.items():
            if key in metadata:
                if isinstance(value, list):
                    if not any(v in metadata[key] for v in value):
                        return False
                else:
                    if metadata[key] != value:
                        return False

        return True

    def visualize_space(self, method: str = 'pca') -> Dict:
        """Generate 2D visualization of the service space"""
        if len(self.services) < 2:
            return {'error': 'Need at least 2 services for visualization'}

        if not SKLEARN_AVAILABLE:
            return {'error': 'scikit-learn required for visualization'}

        vectors = np.array([service.vector for service in self.services.values()])
        service_ids = list(self.services.keys())

        # Dimensionality reduction
        if method == 'tsne':
            reducer = TSNE(n_components=2, random_state=42, perplexity=min(30, len(self.services) - 1))
        else:  # PCA
            reducer = PCA(n_components=2)

        try:
            coords_2d = reducer.fit_transform(vectors)

            return {
                'coordinates': coords_2d.tolist(),
                'service_ids': service_ids,
                'metadata': [self.services[sid].metadata for sid in service_ids]
            }
        except Exception as e:
            return {'error': f'Visualization failed: {e}'}

    def get_space_statistics(self) -> Dict:
        """Get statistics about the vector space"""
        if not self.services:
            return {'error': 'No services in space'}

        # Collect statistics
        semantic_purposes = [s.metadata['semantic_purpose'] for s in self.services.values()]
        patterns = [s.metadata['interaction_pattern'] for s in self.services.values()]
        performance_cats = [s.metadata['performance_category'] for s in self.services.values()]

        return {
            'total_services': len(self.services),
            'vector_dimension': self.dimension,
            'semantic_purposes': dict(Counter(semantic_purposes)),
            'interaction_patterns': dict(Counter(patterns)),
            'performance_categories': dict(Counter(performance_cats)),
            'embedding_model': 'sentence-transformers' if self.embedding_model else 'fallback'
        }


class DataType(Enum):
    """Standard data types with automatic compatibility rules"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    EMAIL = "email"
    URL = "url"
    FILE = "file"
    JSON = "json"
    ANY = "any"


class PatternCompatibilityEngine:
    """Automatically determines service compatibility based on patterns"""

    def __init__(self):
        # Type compatibility matrix (automatic)
        self.type_compatibility = {
            DataType.STRING: {DataType.STRING, DataType.EMAIL, DataType.URL, DataType.JSON, DataType.ANY},
            DataType.EMAIL: {DataType.STRING, DataType.EMAIL, DataType.ANY},
            DataType.URL: {DataType.STRING, DataType.URL, DataType.ANY},
            DataType.INTEGER: {DataType.INTEGER, DataType.FLOAT, DataType.STRING, DataType.ANY},
            DataType.FLOAT: {DataType.FLOAT, DataType.INTEGER, DataType.STRING, DataType.ANY},
            DataType.BOOLEAN: {DataType.BOOLEAN, DataType.STRING, DataType.ANY},
            DataType.OBJECT: {DataType.OBJECT, DataType.JSON, DataType.STRING, DataType.ANY},
            DataType.ARRAY: {DataType.ARRAY, DataType.JSON, DataType.STRING, DataType.ANY},
            DataType.FILE: {DataType.FILE, DataType.STRING, DataType.ANY},
            DataType.JSON: {DataType.JSON, DataType.OBJECT, DataType.ARRAY, DataType.STRING, DataType.ANY},
            DataType.ANY: {dt for dt in DataType}  # ANY accepts everything
        }

        # Pattern compatibility matrix based on your interaction patterns
        self.pattern_compatibility = {
            "synchronous_stateless": {
                "synchronous_stateless",
                "synchronous_persistent",
                "synchronous_session_based"
            },
            "synchronous_persistent": {
                "synchronous_stateless",
                "synchronous_persistent"
            },
            "synchronous_session_based": {
                "synchronous_stateless",
                "synchronous_persistent",
                "synchronous_session_based"
            },
            "asynchronous_stateless": {
                "synchronous_stateless",  # Async can call sync
                "synchronous_persistent"
            },
            "asynchronous_persistent": {
                "synchronous_stateless",
                "synchronous_persistent"
            },
            "streaming_stateless": {
                "streaming_stateless",
                "synchronous_stateless"  # Can process stream chunks
            },
            "event_driven_stateless": {
                "synchronous_stateless",
                "event_driven_stateless"
            }
        }

    def can_chain_services(self, service_a: ComputationalSignature, service_b: ComputationalSignature) -> bool:
        """
        Determine if service A can chain to service B
        Based on type compatibility + pattern compatibility + semantic compatibility
        """

        # 1. Type compatibility check
        type_compatible = self._check_type_compatibility(service_a, service_b)

        # 2. Pattern compatibility check
        pattern_compatible = self._check_pattern_compatibility(service_a, service_b)

        # 3. Semantic compatibility check
        semantic_compatible = self._check_semantic_compatibility(service_a, service_b)

        # 4. Side effect compatibility
        side_effect_compatible = self._check_side_effect_compatibility(service_a, service_b)

        return (type_compatible and
                pattern_compatible and
                semantic_compatible and
                side_effect_compatible)

    def _check_type_compatibility(self, service_a: ComputationalSignature, service_b: ComputationalSignature) -> bool:
        """Check if output type can feed into input type"""

        # Get primary output type from service A
        output_types = service_a.compatible_outputs or ["string"]
        input_types = service_b.compatible_inputs or ["string"]

        # Convert to DataType enums
        def to_data_type(type_str: str) -> DataType:
            type_mapping = {
                "string": DataType.STRING,
                "integer": DataType.INTEGER,
                "float": DataType.FLOAT,
                "boolean": DataType.BOOLEAN,
                "object": DataType.OBJECT,
                "array": DataType.ARRAY,
                "email": DataType.EMAIL,
                "url": DataType.URL,
                "file": DataType.FILE,
                "json": DataType.JSON,
                "any": DataType.ANY
            }
            return type_mapping.get(type_str.lower(), DataType.STRING)

        # Check if any output type is compatible with any input type
        for output_type_str in output_types:
            output_type = to_data_type(output_type_str)
            compatible_types = self.type_compatibility.get(output_type, {DataType.STRING})

            for input_type_str in input_types:
                input_type = to_data_type(input_type_str)
                if input_type in compatible_types:
                    return True

        return False

    def _check_pattern_compatibility(self, service_a: ComputationalSignature,
                                     service_b: ComputationalSignature) -> bool:
        """Check if interaction patterns can be chained"""
        pattern_a = service_a.interaction_pattern
        pattern_b = service_b.interaction_pattern

        compatible_patterns = self.pattern_compatibility.get(pattern_a, set())
        return pattern_b in compatible_patterns

    def _check_semantic_compatibility(self, service_a: ComputationalSignature,
                                      service_b: ComputationalSignature) -> bool:
        """Check if the semantic flow makes sense"""

        # Define semantic flow rules based on your services
        semantic_flows = {
            "passthrough": {"validation", "transformation", "storage", "communication", "routing", "processing"},
            "validation": {"storage", "transformation", "communication", "routing", "processing"},
            "transformation": {"validation", "storage", "communication", "routing", "processing"},
            "storage": {"communication", "routing"},  # Storage usually ends chains
            "retrieval": {"validation", "transformation", "communication", "routing", "processing"},
            "communication": {"storage", "routing", "processing"},  # Communication often ends chains
            "computation": {"validation", "transformation", "storage", "communication", "routing", "processing"},
            "routing": {"validation", "transformation", "storage", "communication", "processing"},
            "monitoring": {"validation", "transformation", "storage", "communication", "routing", "processing"},
            # Monitoring can go anywhere
            "processing": {"validation", "transformation", "storage", "communication", "routing", "processing"},
            # Generic processing
            "unknown": {"validation", "transformation", "storage", "communication", "routing", "processing"}
            # Unknown can go most places
        }

        # Get compatible semantic purposes for service A
        compatible_purposes = semantic_flows.get(service_a.semantic_purpose, set())

        # Check if service B's purpose is compatible
        is_compatible = (
                service_b.semantic_purpose in compatible_purposes or
                service_a.semantic_purpose == "passthrough" or  # Passthrough goes anywhere
                service_b.semantic_purpose == "monitoring" or  # Monitoring accepts anything
                service_a.semantic_purpose == "unknown" or  # Unknown can try to go anywhere
                service_b.semantic_purpose == "unknown"  # Unknown can accept anything
        )

        return is_compatible

    def _check_side_effect_compatibility(self, service_a: ComputationalSignature,
                                         service_b: ComputationalSignature) -> bool:
        """Check if side effects are compatible"""

        # Some side effects make chaining problematic
        problematic_combinations = [
            # Don't chain two services that both do heavy network calls
            ({"network_call"}, {"network_call"}),
            # Don't chain two file writers (could conflict)
            ({"file_write"}, {"file_write"}),
        ]

        a_effects = set(service_a.side_effects)
        b_effects = set(service_b.side_effects)

        for prob_a, prob_b in problematic_combinations:
            if prob_a.issubset(a_effects) and prob_b.issubset(b_effects):
                return False

        return True


class ServiceCodeAnalyzer:
    """Analyzes service source code to extract computational patterns"""

    def __init__(self):
        self.semantic_patterns = {
            'validation': ['validate', 'verify', 'check', 'confirm', 'test'],
            'transformation': ['transform', 'convert', 'change', 'modify', 'process'],
            'storage': ['store', 'save', 'persist', 'write', 'insert'],
            'retrieval': ['get', 'fetch', 'read', 'load', 'retrieve'],
            'communication': ['send', 'post', 'email', 'notify', 'message'],
            'computation': ['calculate', 'compute', 'analyze', 'generate'],
            'routing': ['route', 'forward', 'dispatch', 'redirect'],
            'monitoring': ['monitor', 'track', 'log', 'audit', 'measure']
        }

    def analyze_code(self, code_content: str, file_path: str = None) -> Dict[str, Any]:
        """Main code analysis pipeline"""
        try:
            tree = ast.parse(code_content)

            analysis = {
                'semantic_purpose': self._extract_semantic_purpose(code_content, tree),
                'domain_context': self._extract_domain_context(code_content),
                'business_intent': self._extract_business_intent(code_content),
                'transformation_type': self._classify_transformation(tree, code_content),
                'algorithm_complexity': 'O(1)',  # Simplified
                'side_effects': self._detect_side_effects(tree),
                'external_dependencies': self._find_external_dependencies(tree),
                'error_modes': ['general_error'],  # Simplified
                'data_flow_pattern': 'transform',  # Simplified
                'endpoint_patterns': self._extract_endpoints(tree),
                'lines_of_code': len(code_content.split('\n')),
                'cyclomatic_complexity': 3,  # Simplified
                'external_api_calls': self._count_api_calls(tree),
                'semantic_keywords': self._extract_semantic_keywords(code_content),
                'technical_keywords': self._extract_technical_keywords(tree)
            }

            return analysis

        except Exception as e:
            return {'error': f"Code analysis failed: {str(e)}"}

    def _extract_semantic_purpose(self, code: str, tree: ast.AST) -> str:
        """Determine the main semantic purpose of the service"""
        code_lower = code.lower()

        # Look for explicit purpose indicators in code
        for purpose, keywords in self.semantic_patterns.items():
            if any(keyword in code_lower for keyword in keywords):
                return purpose



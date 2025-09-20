#!/usr/bin/env python3
"""
Computational Signature Analyzer - Prototype
Analyzes your microservices to extract computational signatures
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

# Import your interaction patterns
from interaction_patterns import INTERACTION_PATTERNS, PatternRegistry, DataPattern, StatePattern


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

    def can_chain_services(self, service_a: 'ComputationalSignature', service_b: 'ComputationalSignature') -> bool:
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

    def _check_type_compatibility(self, service_a: 'ComputationalSignature',
                                  service_b: 'ComputationalSignature') -> bool:
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

    def _check_pattern_compatibility(self, service_a: 'ComputationalSignature',
                                     service_b: 'ComputationalSignature') -> bool:
        """Check if interaction patterns can be chained"""
        pattern_a = service_a.interaction_pattern
        pattern_b = service_b.interaction_pattern

        compatible_patterns = self.pattern_compatibility.get(pattern_a, set())
        return pattern_b in compatible_patterns

    def _check_semantic_compatibility(self, service_a: 'ComputationalSignature',
                                      service_b: 'ComputationalSignature') -> bool:
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

    def _check_side_effect_compatibility(self, service_a: 'ComputationalSignature',
                                         service_b: 'ComputationalSignature') -> bool:
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

        self.complexity_indicators = {
            'O(1)': ['direct', 'constant', 'lookup', 'hash'],
            'O(log n)': ['binary', 'search', 'tree', 'sorted'],
            'O(n)': ['iterate', 'loop', 'scan', 'linear'],
            'O(n^2)': ['nested', 'matrix', 'quadratic', 'bubble']
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
                'algorithm_complexity': self._estimate_complexity(tree, code_content),
                'side_effects': self._detect_side_effects(tree),
                'external_dependencies': self._find_external_dependencies(tree),
                'error_modes': self._identify_error_patterns(tree),
                'data_flow_pattern': self._analyze_data_flow(tree),
                'endpoint_patterns': self._extract_endpoints(tree),
                'lines_of_code': len(code_content.split('\n')),
                'cyclomatic_complexity': self._calculate_cyclomatic_complexity(tree),
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

        return 'unknown'  # Default for unclear cases

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
            'image': ['image', 'photo', 'picture', 'jpeg', 'png'],
            'user': ['user', 'customer', 'person', 'profile', 'account'],
            'payment': ['payment', 'billing', 'charge', 'invoice'],
            'notification': ['notify', 'alert', 'message', 'push']
        }

        for domain, indicators in domain_indicators.items():
            if any(indicator in code_lower for indicator in indicators):
                domains.append(domain)

        return domains or ['general']

    def _extract_business_intent(self, code: str) -> str:
        """Extract human-readable business intent from comments/docstrings"""
        # Look for docstrings and comments that explain business purpose
        lines = code.split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith('"""') or line.startswith("'''"):
                # Found docstring, extract intent
                return line.strip('"\'').strip()
            elif line.startswith('#') and any(word in line.lower() for word in ['purpose', 'does', 'handles']):
                return line.strip('#').strip()

        # Fallback: try to infer from class/function names
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and 'app' not in node.name.lower():
                    return f"Handles {node.name.replace('_', ' ').lower()} operations"
        except:
            pass

        return "Service functionality not clearly documented"

    def _classify_transformation(self, tree: ast.AST, code: str) -> str:
        """Classify the type of data transformation performed"""
        code_lower = code.lower()

        # Look for assignment patterns that indicate transformation type
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if hasattr(node.value, 'attr') and node.value.attr == 'data':
                    # Direct assignment: data passthrough
                    return 'identity'
                elif isinstance(node.value, ast.Call):
                    func_name = ''
                    if hasattr(node.value.func, 'attr'):
                        func_name = node.value.func.attr
                    elif hasattr(node.value.func, 'id'):
                        func_name = node.value.func.id

                    func_name = func_name.lower()
                    if any(word in func_name for word in ['upper', 'lower', 'replace', 'strip']):
                        return 'text_transformation'
                    elif any(word in func_name for word in ['validate', 'check', 'verify']):
                        return 'validation'

        # Check for common transformation patterns in the code
        if any(word in code_lower for word in ['upper()', 'lower()', 'replace(', 'strip(']):
            return 'text_transformation'
        elif any(word in code_lower for word in ['json.loads', 'json.dumps', 'parse']):
            return 'format_conversion'
        elif any(word in code_lower for word in ['save', 'store', 'persist', 'write']):
            return 'persistence'
        elif 'requests.' in code_lower:
            return 'api_integration'

        return 'processing'

    def _estimate_complexity(self, tree: ast.AST, code: str) -> str:
        """Estimate algorithmic complexity from code patterns"""
        code_lower = code.lower()

        # Count nested loops
        loop_depth = self._count_max_loop_depth(tree)

        if loop_depth >= 2:
            return 'O(n^2)'
        elif loop_depth == 1:
            return 'O(n)'
        elif any(indicator in code_lower for indicator in self.complexity_indicators['O(log n)']):
            return 'O(log n)'
        else:
            return 'O(1)'

    def _count_max_loop_depth(self, tree: ast.AST) -> int:
        """Count maximum nesting depth of loops"""
        max_depth = 0

        def count_depth(node, current_depth=0):
            nonlocal max_depth
            if isinstance(node, (ast.For, ast.While)):
                current_depth += 1
                max_depth = max(max_depth, current_depth)

            for child in ast.iter_child_nodes(node):
                count_depth(child, current_depth)

        count_depth(tree)
        return max_depth

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

                # Network calls
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
                    elif alias.name in ['smtplib', 'email']:
                        dependencies.append('email_service')

            elif isinstance(node, ast.ImportFrom):
                if node.module in ['requests', 'urllib', 'httpx']:
                    dependencies.append('http_client')
                elif node.module in ['sqlite3', 'psycopg2', 'pymongo']:
                    dependencies.append('database')

        return list(set(dependencies))

    def _identify_error_patterns(self, tree: ast.AST) -> List[str]:
        """Identify common error handling patterns"""
        error_modes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type:
                    if hasattr(node.type, 'id'):
                        exc_type = node.type.id
                        if 'Timeout' in exc_type:
                            error_modes.append('timeout_error')
                        elif 'Connection' in exc_type:
                            error_modes.append('connection_error')
                        elif 'Validation' in exc_type:
                            error_modes.append('validation_error')
                        else:
                            error_modes.append('general_error')

        return list(set(error_modes)) or ['unhandled_errors']

    def _analyze_data_flow(self, tree: ast.AST) -> str:
        """Analyze how data flows through the service"""
        has_input = False
        has_output = False
        has_transformation = False

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if 'process' in node.name or 'execute' in node.name:
                    if node.args.args:
                        has_input = True
                    if any(isinstance(child, ast.Return) for child in ast.walk(node)):
                        has_output = True
                    if any(isinstance(child, ast.Assign) for child in ast.walk(node)):
                        has_transformation = True

        if has_input and has_output and has_transformation:
            return 'transform'
        elif has_input and has_output:
            return 'passthrough'
        elif has_input:
            return 'consumer'
        elif has_output:
            return 'producer'
        else:
            return 'unknown'

    def _extract_endpoints(self, tree: ast.AST) -> List[str]:
        """Extract API endpoint patterns"""
        endpoints = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and hasattr(node.func, 'attr'):
                if node.func.attr in ['get', 'post', 'put', 'delete']:
                    endpoints.append(f"{node.func.attr.upper()}_endpoint")

            if isinstance(node, ast.FunctionDef):
                decorators = [d.id for d in node.decorator_list if hasattr(d, 'id')]
                if 'app' in str(decorators):  # FastAPI decorators
                    endpoints.append(f"/{node.name}")

        return endpoints

    def _calculate_cyclomatic_complexity(self, tree: ast.AST) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1  # Base complexity

        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1

        return complexity

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

        # Extract from comments and docstrings
        for line in code.split('\n'):
            line = line.strip()
            if line.startswith('#') or '"""' in line or "'''" in line:
                words = re.findall(r'\b[a-z]+\b', line.lower())
                keywords.extend([w for w in words if len(w) > 3])

        # Extract from function/class names
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    name_parts = node.name.replace('_', ' ').split()
                    keywords.extend([part.lower() for part in name_parts if len(part) > 2])
        except:
            pass

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
            elif isinstance(node, ast.Call) and hasattr(node.func, 'attr'):
                keywords.append(node.func.attr)

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
                'chainable_before': self._extract_chainable_before(contract_data),
                'chainable_after': self._extract_chainable_after(contract_data),
                'pattern_compatibility': self._extract_pattern_compatibility(contract_data),
                'estimated_latency_ms': self._extract_latency(contract_data),
                'memory_usage_mb': self._extract_memory_usage(contract_data),
                'cpu_intensity': self._extract_cpu_intensity(contract_data),
                # Add semantic analysis from contract
                'semantic_purpose': self._extract_semantic_purpose_from_contract(contract_data),
                'business_intent': self._extract_business_intent_from_contract(contract_data),
                'domain_context': self._extract_domain_context_from_contract(contract_data)
            }

            return analysis

        except Exception as e:
            return {'error': f"Contract analysis failed: {str(e)}"}

    def _extract_semantic_purpose_from_contract(self, contract: Dict) -> str:
        """Extract semantic purpose from contract description and metadata"""

        # Check service metadata description
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
            return 'transformation'  # File processing is a type of transformation
        if any(word in service_id for word in ['file', 'processor', 'upload']):
            return 'transformation'

        # Check for passthrough/echo
        if any(word in description for word in ['echo', 'pass', 'forward', 'unchanged', 'through']):
            return 'passthrough'
        if any(word in service_id for word in ['echo', 'hello', 'pass']):
            return 'passthrough'

        # Check interface for more clues
        interface = contract.get('interface_contract', {})
        inputs = interface.get('inputs', {})
        outputs = interface.get('outputs', {})

        # If it takes files and returns processed data, it's transformation
        if any('file' in inp_name.lower() for inp_name in inputs.keys()):
            return 'transformation'

        # If it has validation-related outputs
        if any(out_name.lower() in ['valid', 'validation', 'result', 'status'] for out_name in outputs.keys()):
            return 'validation'

        return 'processing'  # Default fallback, not 'unknown'

    def _extract_business_intent_from_contract(self, contract: Dict) -> str:
        """Extract business intent from contract"""
        metadata = contract.get('service_metadata', {})
        description = metadata.get('description', '')

        if description:
            return description

        # Fallback to service ID interpretation
        service_id = metadata.get('service_id', '')
        return f"Handles {service_id.replace('-', ' ')} operations"

    def _extract_domain_context_from_contract(self, contract: Dict) -> List[str]:
        """Extract domain context from contract"""
        domains = []

        # Check in description and service ID
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
        return metadata.get('pattern', 'unknown')

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

    def _extract_chainable_before(self, contract: Dict) -> List[str]:
        """Extract services this can chain before (automatically determined)"""
        # This is now automatically determined by the PatternCompatibilityEngine
        # Return empty list - compatibility is computed dynamically
        return []

    def _extract_chainable_after(self, contract: Dict) -> List[str]:
        """Extract services this can chain after (automatically determined)"""
        # This is now automatically determined by the PatternCompatibilityEngine
        # Return empty list - compatibility is computed dynamically
        return []

    def _extract_pattern_compatibility(self, contract: Dict) -> Dict[str, bool]:
        """Extract pattern compatibility information"""
        # This would be enhanced based on pattern rules
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
        """
        Analyze a service and generate computational signature

        Args:
            service_id: Unique service identifier
            code_content: Service source code as string
            code_file: Path to service source file
            contract_data: Contract JSON data
            contract_url: URL to fetch contract from
        """

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
            version=contract_data.get('service_metadata', {}).get('version', '1.0.0'),
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

    def analyze_service_from_registry(self, service_id: str, registry_base_url: str) -> ComputationalSignature:
        """Analyze a service by fetching from service registry"""
        try:
            # Get service info from registry
            services_response = requests.get(f"{registry_base_url}/services")
            services = services_response.json().get('services', {})

            if service_id not in services:
                raise ValueError(f"Service {service_id} not found in registry")

            service_info = services[service_id]
            service_url = service_info['url']

            # Fetch contract
            contract_response = requests.get(f"{service_url}/contract")
            contract_data = contract_response.json()

            # For now, we can't fetch source code automatically
            # But we can analyze based on the contract
            return self.analyze_service(
                service_id=service_id,
                contract_data=contract_data
            )

        except Exception as e:
            raise Exception(f"Failed to analyze service from registry: {e}")

    def save_signature(self, signature: ComputationalSignature, output_file: str):
        """Save signature to JSON file"""
        with open(output_file, 'w') as f:
            json.dump(asdict(signature), f, indent=2)

    def load_signature(self, input_file: str) -> ComputationalSignature:
        """Load signature from JSON file"""
        with open(input_file, 'r') as f:
            data = json.load(f)
        return ComputationalSignature(**data)


# Example usage and testing
def main():
    """Example usage of the analyzer"""
    analyzer = ComputationalSignatureAnalyzer()

    # Example: Analyze your echo-node
    echo_node_code = '''
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ValidationError
from typing import Dict, Any, Optional, List
import requests

app = FastAPI(title="echo node", description="prints text")

class NodeRequest(BaseModel):
    data: str
    next_node: Optional[str] = None
    metadata: dict = {}

class NodeResponse(BaseModel):
    node_id: str = "echo-node"
    data: str
    status: str
    metadata: dict = {}

@app.post("/process")
async def process_data(request: NodeRequest):
    print(f"Echo Node received: {request.data}")
    processed_data = request.data

    response = NodeResponse(
        data=processed_data,
        status="success",
        metadata={
            "processed_by": "echo-node",
            "pattern_used": "synchronous_stateless",
            "original_length": len(request.data),
            **request.metadata
        }
    )

    if request.next_node:
        try:
            forward_request = NodeRequest(
                data=processed_data,
                next_node=None,
                metadata=response.metadata
            )

            next_url = f"http://{request.next_node}:8000/process"
            forward_response = requests.post(
                next_url,
                json=forward_request.model_dump(),
                timeout=10
            )

            if forward_response.status_code == 200:
                return forward_response.json()
            else:
                response.status = "forward_failed"

        except Exception as e:
            response.status = "forward_failed"
            response.metadata["forward_error"] = str(e)

    return response
'''

    echo_contract = {
        "service_metadata": {
            "service_id": "echo-node",
            "version": "1.0.0",
            "pattern": "synchronous_stateless",
            "description": "Passes data through unchanged - useful for testing and debugging chains"
        },
        "interface_contract": {
            "inputs": {
                "text": {
                    "type": "string",
                    "constraints": {"max_length": 100000, "required": True}
                }
            },
            "outputs": {
                "text": {
                    "type": "string",
                    "constraints": {"encoding": "utf-8"}
                }
            }
        },
        "resource_requirements": {
            "max_execution_time": "10ms",
            "memory_limit": "10MB",
            "cpu_intensive": False
        },
        "compatibility_rules": {
            "can_chain_to": ["any"],
            "output_compatible_with": ["string_consumers", "text_processors"]
        }
    }

    # Analyze the service
    signature = analyzer.analyze_service(
        service_id="echo-node",
        code_content=echo_node_code,
        contract_data=echo_contract
    )

    # Print analysis results
    print("=== Computational Signature Analysis ===")
    print(f"Service ID: {signature.service_id}")
    print(f"Semantic Purpose: {signature.semantic_purpose}")
    print(f"Domain Context: {signature.domain_context}")
    print(f"Business Intent: {signature.business_intent}")
    print(f"Transformation Type: {signature.transformation_type}")
    print(f"Algorithm Complexity: {signature.algorithm_complexity}")
    print(f"Side Effects: {signature.side_effects}")
    print(f"External Dependencies: {signature.external_dependencies}")
    print(f"Data Flow Pattern: {signature.data_flow_pattern}")
    print(f"Interaction Pattern: {signature.interaction_pattern}")
    print(f"Compatible Inputs: {signature.compatible_inputs}")
    print(f"Compatible Outputs: {signature.compatible_outputs}")
    print(f"Estimated Latency: {signature.estimated_latency_ms}ms")
    print(f"Memory Usage: {signature.memory_usage_mb}MB")
    print(f"Lines of Code: {signature.lines_of_code}")
    print(f"Cyclomatic Complexity: {signature.cyclomatic_complexity}")
    print(f"Semantic Keywords: {signature.semantic_keywords}")
    print(f"Technical Keywords: {signature.technical_keywords}")

    # Save to file
    analyzer.save_signature(signature, "echo_node_signature.json")
    print("\nSignature saved to echo_node_signature.json")

    return signature


def analyze_your_services(registry_url: str = "http://localhost:8004"):
    """Analyze all services from your docker setup"""
    analyzer = ComputationalSignatureAnalyzer()
    signatures = {}

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
                # Convert docker hostnames to localhost for external access
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
                        # Try to extract port from original URL
                        service_url = f"http://localhost:{port_part}"

                print(f"  Connecting to: {service_url}")

                # Fetch contract
                contract_response = requests.get(f"{service_url}/contract", timeout=10)

                if contract_response.status_code == 200:
                    contract_data = contract_response.json()

                    # Analyze service (contract only for now)
                    signature = analyzer.analyze_service(
                        service_id=service_id,
                        contract_data=contract_data
                    )

                    signatures[service_id] = signature

                    # Save individual signature
                    analyzer.save_signature(signature, f"{service_id}_signature.json")

                    print(f"  ✅ {service_id}: {signature.semantic_purpose} ({signature.interaction_pattern})")
                else:
                    print(f"  ❌ {service_id}: Failed to fetch contract ({contract_response.status_code})")

            except Exception as e:
                print(f"  ❌ {service_id}: Analysis failed - {e}")

        # Create summary analysis
        create_analysis_summary(signatures)

        return signatures

    except Exception as e:
        print(f"Failed to connect to service registry: {e}")
        print("Make sure your docker services are running!")
        print("Try: curl http://localhost:8004/services")
        return {}


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

    # DEBUG: Add detailed compatibility analysis
    debug_compatibility_analysis(signatures)

    # Analyze compatibility with debugging
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
        print("  No compatible chains found - check debug output above")


def debug_compatibility_analysis(signatures: Dict[str, ComputationalSignature]):
    """Debug why services aren't chaining to each other"""
    engine = PatternCompatibilityEngine()

    print("\n" + "=" * 60)
    print("DEBUG: COMPATIBILITY ANALYSIS")
    print("=" * 60)

    # Check each service's extracted data
    print("\nService Data Extraction:")
    for service_id, sig in signatures.items():
        print(f"\n{service_id}:")
        print(f"  Semantic Purpose: '{sig.semantic_purpose}'")
        print(f"  Interaction Pattern: '{sig.interaction_pattern}'")
        print(f"  Compatible Inputs: {sig.compatible_inputs}")
        print(f"  Compatible Outputs: {sig.compatible_outputs}")
        print(f"  Side Effects: {sig.side_effects}")

    # Test one specific pair in detail
    services_list = list(signatures.items())
    if len(services_list) >= 2:
        service_a_id, service_a = services_list[0]
        service_b_id, service_b = services_list[1]

        print(f"\n--- Detailed Test: {service_a_id} → {service_b_id} ---")

        # Test each compatibility check individually
        type_compatible = engine._check_type_compatibility(service_a, service_b)
        pattern_compatible = engine._check_pattern_compatibility(service_a, service_b)
        semantic_compatible = engine._check_semantic_compatibility(service_a, service_b)
        side_effect_compatible = engine._check_side_effect_compatibility(service_a, service_b)

        overall_compatible = engine.can_chain_services(service_a, service_b)

        print(f"  Type Compatible: {type_compatible}")
        print(f"    A outputs: {service_a.compatible_outputs}")
        print(f"    B inputs: {service_b.compatible_inputs}")
        print(f"  Pattern Compatible: {pattern_compatible}")
        print(f"    A pattern: {service_a.interaction_pattern}")
        print(f"    B pattern: {service_b.interaction_pattern}")
        print(f"  Semantic Compatible: {semantic_compatible}")
        print(f"    A purpose: {service_a.semantic_purpose}")
        print(f"    B purpose: {service_b.semantic_purpose}")
        print(f"  Side Effect Compatible: {side_effect_compatible}")
        print(f"  OVERALL: {overall_compatible}")

        if not overall_compatible:
            failures = []
            if not type_compatible:
                failures.append("TYPE")
            if not pattern_compatible:
                failures.append("PATTERN")
            if not semantic_compatible:
                failures.append("SEMANTIC")
            if not side_effect_compatible:
                failures.append("SIDE_EFFECT")
            print(f"  FAILED ON: {failures}")


def can_chain_services(service_a: ComputationalSignature,
                       service_b: ComputationalSignature) -> bool:
    """Check if service A can chain to service B using pattern-based logic"""

    # Use the integrated pattern-based compatibility engine
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


def find_potential_chains(signatures: Dict[str, ComputationalSignature]) -> List[List[str]]:
    """Find potential 2-3 service chains"""
    chains = []

    # Find 2-service chains
    for service_a_id, service_a in signatures.items():
        for service_b_id, service_b in signatures.items():
            if service_a_id != service_b_id and can_chain_services(service_a, service_b):
                chains.append([service_a_id, service_b_id])

    # Find 3-service chains by extending 2-service chains
    three_chains = []
    for chain in chains:
        service_b_id = chain[1]
        service_b = signatures[service_b_id]

        for service_c_id, service_c in signatures.items():
            if service_c_id not in chain and can_chain_services(service_b, service_c):
                three_chains.append(chain + [service_c_id])

    return chains + three_chains


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
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}

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


if __name__ == "__main__":
    print("Computational Signature Analyzer - Prototype")
    print("=" * 50)

    # Test with sample services first
    print("\n1. Testing with sample services...")
    test_signatures = test_with_sample_services()

    # Try to analyze your actual services
    print("\n\n2. Analyzing your Docker services...")
    real_signatures = analyze_your_services()

    if real_signatures:
        print(f"\nSuccessfully analyzed {len(real_signatures)} services!")
        print("Signature files saved for each service.")
    else:
        print("\nCould not connect to your service registry.")
        print("Make sure Docker services are running:")
        print("  docker-compose up -d")
        print("  curl http://localhost:8004/services")

    print("\n=== ANALYSIS COMPLETE ===")
    print("Next steps:")
    print("1. Review the generated signature JSON files")
    print("2. Test signature accuracy against real service behavior")
    print("3. Build the semantic navigation system using these signatures")
    print("4. Create vector embeddings for similarity search")
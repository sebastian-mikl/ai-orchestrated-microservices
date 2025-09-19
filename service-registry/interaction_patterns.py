from enum import Enum
from pydantic import BaseModel
from typing import Dict, Any, List, Optional, Union
import asyncio
import uuid
from datetime import datetime


class DataPattern(Enum):
    SYNCHRONOUS = "synchronous"  # Input → Process → Output
    ASYNCHRONOUS = "asynchronous"  # Submit → Job ID → Poll/Callback
    STREAMING = "streaming"  # Continuous input/output flows
    EVENT_DRIVEN = "event_driven"  # Trigger-based processing


class StatePattern(Enum):
    STATELESS = "stateless"  # No memory between calls
    SESSION_BASED = "session_based"  # State during interaction sequence
    PERSISTENT = "persistent"  # Long-term data storage
    SHARED_STATE = "shared_state"  # Coordinates with other services


class InteractionPattern(BaseModel):
    data_pattern: DataPattern
    state_pattern: StatePattern

    @property
    def pattern_id(self) -> str:
        return f"{self.data_pattern.value}_{self.state_pattern.value}"


# The 16 fundamental patterns
INTERACTION_PATTERNS = {
    # Synchronous patterns
    "synchronous_stateless": {
        "description": "Simple transform: input → process → output",
        "examples": ["text transformation", "image resize", "data validation"],
        "interface": "function_call",
        "typical_duration": "seconds"
    },
    "synchronous_session_based": {
        "description": "Interactive session with immediate responses",
        "examples": ["chatbot conversation", "interactive CLI", "wizard forms"],
        "interface": "session_api",
        "typical_duration": "minutes"
    },
    "synchronous_persistent": {
        "description": "Database-like operations with immediate response",
        "examples": ["CRUD operations", "cache operations", "config management"],
        "interface": "persistent_api",
        "typical_duration": "milliseconds"
    },
    "synchronous_shared_state": {
        "description": "Coordinated operations across services",
        "examples": ["distributed transactions", "consensus operations", "leader election"],
        "interface": "coordination_api",
        "typical_duration": "seconds"
    },

    # Asynchronous patterns
    "asynchronous_stateless": {
        "description": "Background job with no dependencies",
        "examples": ["batch processing", "file conversion", "report generation"],
        "interface": "job_submission",
        "typical_duration": "minutes_to_hours"
    },
    "asynchronous_session_based": {
        "description": "Multi-step workflow with checkpoints",
        "examples": ["CI/CD pipeline", "approval workflow", "multi-stage processing"],
        "interface": "workflow_api",
        "typical_duration": "hours_to_days"
    },
    "asynchronous_persistent": {
        "description": "Long-running data operations",
        "examples": ["database migration", "backup operations", "data sync"],
        "interface": "persistent_job_api",
        "typical_duration": "hours"
    },
    "asynchronous_shared_state": {
        "description": "Distributed background coordination",
        "examples": ["cluster rebalancing", "distributed backup", "consensus building"],
        "interface": "distributed_job_api",
        "typical_duration": "hours"
    },

    # Streaming patterns
    "streaming_stateless": {
        "description": "Real-time data transformation",
        "examples": ["video transcoding", "log processing", "data filtering"],
        "interface": "stream_api",
        "typical_duration": "continuous"
    },
    "streaming_session_based": {
        "description": "Interactive real-time sessions",
        "examples": ["video calls", "live gaming", "collaborative editing"],
        "interface": "session_stream_api",
        "typical_duration": "minutes_to_hours"
    },
    "streaming_persistent": {
        "description": "Continuous data ingestion and storage",
        "examples": ["time series DB", "log aggregation", "metrics collection"],
        "interface": "persistent_stream_api",
        "typical_duration": "continuous"
    },
    "streaming_shared_state": {
        "description": "Coordinated real-time processing",
        "examples": ["distributed stream processing", "real-time consensus", "live data replication"],
        "interface": "distributed_stream_api",
        "typical_duration": "continuous"
    },

    # Event-driven patterns
    "event_driven_stateless": {
        "description": "React to events without maintaining state",
        "examples": ["webhook handlers", "notification services", "trigger functions"],
        "interface": "event_api",
        "typical_duration": "seconds"
    },
    "event_driven_session_based": {
        "description": "Event-based interactions within sessions",
        "examples": ["user activity tracking", "session analytics", "interactive bots"],
        "interface": "session_event_api",
        "typical_duration": "minutes_to_hours"
    },
    "event_driven_persistent": {
        "description": "Event sourcing and event stores",
        "examples": ["audit logs", "event sourced systems", "change tracking"],
        "interface": "persistent_event_api",
        "typical_duration": "permanent"
    },
    "event_driven_shared_state": {
        "description": "Distributed event coordination",
        "examples": ["service mesh events", "cluster state changes", "distributed notifications"],
        "interface": "distributed_event_api",
        "typical_duration": "milliseconds_to_hours"
    }
}


class PatternInterface(BaseModel):
    """Base interface that all patterns must implement"""
    pattern_id: str
    node_id: str
    inputs: Dict[str, str]  # name -> data_type
    outputs: Dict[str, str]  # name -> data_type
    parameters: Dict[str, Any] = {}


class SynchronousStatelessInterface(PatternInterface):
    """Function call interface"""

    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any] = {}) -> Dict[str, Any]:
        pass


class AsynchronousStatelessInterface(PatternInterface):
    """Job submission interface"""

    def submit_job(self, inputs: Dict[str, Any], parameters: Dict[str, Any] = {}) -> str:  # returns job_id
        pass

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        pass

    def get_job_result(self, job_id: str) -> Dict[str, Any]:
        pass


class StreamingStatelessInterface(PatternInterface):
    """Stream processing interface"""

    def create_stream(self, inputs: Dict[str, Any], parameters: Dict[str, Any] = {}) -> str:  # returns stream_id
        pass

    def send_to_stream(self, stream_id: str, data: Any) -> bool:
        pass

    def read_from_stream(self, stream_id: str) -> Any:
        pass

    def close_stream(self, stream_id: str) -> bool:
        pass


class EventDrivenStatelessInterface(PatternInterface):
    """Event handling interface"""

    def register_event_handler(self, event_type: str, callback_url: str) -> str:  # returns handler_id
        pass

    def emit_event(self, event_type: str, data: Any) -> bool:
        pass

    def unregister_event_handler(self, handler_id: str) -> bool:
        pass


class PatternRegistry:
    """Registry that understands all 16 patterns"""

    def __init__(self):
        self.patterns = INTERACTION_PATTERNS
        self.registered_services = {}

    def register_service(self, node_id: str, pattern_id: str, interface_config: Dict[str, Any]):
        """Register a service with its pattern"""
        if pattern_id not in self.patterns:
            raise ValueError(f"Unknown pattern: {pattern_id}")

        self.registered_services[node_id] = {
            "pattern_id": pattern_id,
            "pattern_info": self.patterns[pattern_id],
            "interface_config": interface_config,
            "registered_at": datetime.now().isoformat()
        }

    def find_services_by_pattern(self, data_pattern: str = None, state_pattern: str = None) -> List[str]:
        """Find services matching pattern criteria"""
        matching_services = []

        for node_id, service_info in self.registered_services.items():
            pattern_id = service_info["pattern_id"]

            if data_pattern and not pattern_id.startswith(data_pattern):
                continue
            if state_pattern and not pattern_id.endswith(state_pattern):
                continue

            matching_services.append(node_id)

        return matching_services

    def get_pattern_info(self, pattern_id: str) -> Dict[str, Any]:
        """Get information about a specific pattern"""
        return self.patterns.get(pattern_id, {})

    def get_service_pattern(self, node_id: str) -> Optional[str]:
        """Get the pattern used by a specific service"""
        service_info = self.registered_services.get(node_id)
        return service_info["pattern_id"] if service_info else None


def pattern_to_interface_class(pattern_id: str):
    """Map pattern ID to appropriate interface class"""
    if pattern_id.startswith("synchronous") and pattern_id.endswith("stateless"):
        return SynchronousStatelessInterface
    elif pattern_id.startswith("asynchronous") and pattern_id.endswith("stateless"):
        return AsynchronousStatelessInterface
    elif pattern_id.startswith("streaming") and pattern_id.endswith("stateless"):
        return StreamingStatelessInterface
    elif pattern_id.startswith("event_driven") and pattern_id.endswith("stateless"):
        return EventDrivenStatelessInterface
    else:
        # For more complex patterns, you'd add more interface classes
        return PatternInterface


# Example usage
if __name__ == "__main__":
    registry = PatternRegistry()

    # Register your existing transform node
    registry.register_service(
        node_id="transform-node",
        pattern_id="synchronous_stateless",
        interface_config={
            "inputs": {"text": "string"},
            "outputs": {"text": "string"},
            "parameters": {"transformation": "uppercase"}
        }
    )

    # Find all synchronous services
    sync_services = registry.find_services_by_pattern(data_pattern="synchronous")
    print(f"Synchronous services: {sync_services}")

    # Get pattern info
    pattern_info = registry.get_pattern_info("synchronous_stateless")
    print(f"Pattern info: {pattern_info}")
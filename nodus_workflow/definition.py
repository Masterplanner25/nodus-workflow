"""FlowDefinition — declarative DAG specification."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

try:
    from typing import Protocol, runtime_checkable
except ImportError:
    from typing_extensions import Protocol, runtime_checkable  # type: ignore[assignment]

from .signals import WorkflowWaitSignal


@runtime_checkable
class NodeHandler(Protocol):
    """A callable that executes one node in a flow.

    The handler receives the current flow context (state dict) and returns
    an updated state dict.  To suspend execution, raise ``WorkflowWaitSignal``.
    """

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]: ...


@dataclass
class FlowNode:
    """One node in a flow graph.

    Attributes
    ----------
    id:              Unique node identifier within the flow.
    handler_id:      Key used to look up the handler in a registry.
    config:          Static node configuration passed to the handler.
    max_retries:     Node-level retry override (None = use flow default).
    timeout_seconds: Node-level timeout (None = no timeout).
    """

    id: str
    handler_id: str
    config: dict[str, Any] = field(default_factory=dict)
    max_retries: Optional[int] = None
    timeout_seconds: Optional[int] = None


@dataclass
class FlowEdge:
    """A directed edge between two flow nodes.

    Attributes
    ----------
    source_id:  Source node ID.
    target_id:  Target node ID.
    condition:  Optional condition key checked in flow state.
                Edge is followed when ``state.get(condition)`` is truthy.
    """

    source_id: str
    target_id: str
    condition: Optional[str] = None


@dataclass
class FlowDefinition:
    """Complete declarative definition of a workflow.

    Attributes
    ----------
    name:             Unique flow name (used as registry key).
    nodes:            All nodes in the DAG.
    edges:            All directed edges.
    max_retries:      Default retry count for all nodes.
    timeout_seconds:  Maximum wall-clock time for the entire flow.
    initial_node_id:  Node to execute first (defaults to first in list).
    """

    name: str
    nodes: list[FlowNode] = field(default_factory=list)
    edges: list[FlowEdge] = field(default_factory=list)
    max_retries: int = 3
    timeout_seconds: Optional[int] = None
    initial_node_id: Optional[str] = None

    def get_node(self, node_id: str) -> Optional[FlowNode]:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def next_nodes(self, node_id: str, state: dict[str, Any]) -> list[str]:
        """Return IDs of nodes reachable from *node_id* given current *state*."""
        result = []
        for edge in self.edges:
            if edge.source_id == node_id:
                if edge.condition is None or state.get(edge.condition):
                    result.append(edge.target_id)
        return result

    @property
    def start_node_id(self) -> Optional[str]:
        if self.initial_node_id:
            return self.initial_node_id
        return self.nodes[0].id if self.nodes else None

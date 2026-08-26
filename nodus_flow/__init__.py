"""nodus-flow — a standalone asyncio DAG runner with WAIT/RESUME semantics.

Not the engine behind the Nodus `workflow` keyword; that ships inside
nodus-lang. See the README for the distinction.

Signals:
    WorkflowWaitSignal   — raise inside a NodeHandler to suspend execution

Definition:
    NodeHandler          — protocol: async execute(context) → dict
    FlowNode             — one node (handler_id, config, retry override)
    FlowEdge             — directed edge with optional condition
    FlowDefinition       — complete DAG (nodes, edges, retries, timeout)

Run lifecycle:
    FlowStatus           — PENDING → RUNNING → WAITING → EXECUTING → COMPLETED/FAILED
    FlowRun              — persistent state (status, state dict, current_node, waiting_for)
    FlowRunStore         — protocol
    InMemoryRunStore     — thread-safe dict-backed store (for tests)

Scheduling:
    SchedulerEngine      — priority queue (high/normal/low) + WAIT/RESUME registration
                           schedule(), pop(), wait_for_event(), notify_event(),
                           cancel_wait(), mark_rehydration_complete()

Execution:
    FlowExecutor         — start(), resume(), register_handler()

Rehydration:
    FlowRehydrator       — re-register WAITING runs after process restart
"""
from .definition import FlowDefinition, FlowEdge, FlowNode, NodeHandler
from .executor import FlowExecutor
from .rehydrator import FlowRehydrator
from .run import FlowRun, FlowRunStore, FlowStatus, InMemoryRunStore
from .scheduler import SchedulerEngine
from .signals import WorkflowWaitSignal

__all__ = [
    # Signals
    "WorkflowWaitSignal",
    # Definition
    "NodeHandler",
    "FlowNode",
    "FlowEdge",
    "FlowDefinition",
    # Run lifecycle
    "FlowStatus",
    "FlowRun",
    "FlowRunStore",
    "InMemoryRunStore",
    # Scheduling
    "SchedulerEngine",
    # Execution
    "FlowExecutor",
    # Rehydration
    "FlowRehydrator",
]

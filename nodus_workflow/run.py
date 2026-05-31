"""FlowRun state machine and FlowRunStore."""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

try:
    from typing import Protocol, runtime_checkable
except ImportError:
    from typing_extensions import Protocol, runtime_checkable  # type: ignore[assignment]


class FlowStatus:
    PENDING   = "pending"
    RUNNING   = "running"
    WAITING   = "waiting"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED    = "failed"
    TERMINAL  = (COMPLETED, FAILED)


@dataclass
class FlowRun:
    """Persistent state of one flow execution.

    Attributes
    ----------
    id:           Unique run ID.
    flow_name:    Name of the ``FlowDefinition`` being executed.
    user_id:      Tenant/owner.
    status:       Current lifecycle status (see ``FlowStatus``).
    state:        Mutable workflow-specific state dict.
    current_node: ID of the node currently executing or last executed.
    waiting_for:  Event type this run is suspended on (when WAITING).
    trace_id:     Distributed trace ID.
    error:        Error message when status is FAILED.
    created_at:   UTC creation timestamp.
    updated_at:   UTC last-update timestamp.
    completed_at: UTC completion timestamp.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    flow_name: str = ""
    user_id: str = ""
    status: str = FlowStatus.PENDING
    state: dict[str, Any] = field(default_factory=dict)
    current_node: Optional[str] = None
    waiting_for: Optional[str] = None
    trace_id: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    def transition(self, new_status: str) -> None:
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)
        if new_status in FlowStatus.TERMINAL:
            self.completed_at = self.updated_at

    @property
    def is_terminal(self) -> bool:
        return self.status in FlowStatus.TERMINAL


@runtime_checkable
class FlowRunStore(Protocol):
    def save(self, run: FlowRun) -> None: ...
    def get(self, run_id: str) -> Optional[FlowRun]: ...
    def list_waiting(self) -> list[FlowRun]: ...
    def delete(self, run_id: str) -> bool: ...


class InMemoryRunStore:
    def __init__(self) -> None:
        self._runs: dict[str, FlowRun] = {}
        self._lock = threading.Lock()

    def save(self, run: FlowRun) -> None:
        with self._lock:
            self._runs[run.id] = run

    def get(self, run_id: str) -> Optional[FlowRun]:
        with self._lock:
            return self._runs.get(run_id)

    def list_waiting(self) -> list[FlowRun]:
        with self._lock:
            return [r for r in self._runs.values() if r.status == FlowStatus.WAITING]

    def delete(self, run_id: str) -> bool:
        with self._lock:
            return self._runs.pop(run_id, None) is not None

    def __len__(self) -> int:
        with self._lock:
            return len(self._runs)

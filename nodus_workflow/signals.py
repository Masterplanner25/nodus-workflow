"""WorkflowWaitSignal — raised by a node handler to suspend execution."""
from __future__ import annotations

from typing import Optional


class WorkflowWaitSignal(Exception):
    """Raised inside a ``NodeHandler.execute()`` to suspend the flow.

    The scheduler catches this, registers the flow as waiting for
    *event_type*, and resumes it when the event fires.

    Args:
        event_type:      The event name to wait for (e.g. ``"payment.confirmed"``).
        correlation_id:  Optional correlation chain ID propagated to ``notify_event``.
    """

    def __init__(
        self,
        event_type: str,
        correlation_id: Optional[str] = None,
    ) -> None:
        self.event_type = event_type
        self.correlation_id = correlation_id
        super().__init__(f"nodus.wait:{event_type}")

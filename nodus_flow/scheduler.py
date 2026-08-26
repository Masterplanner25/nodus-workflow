"""SchedulerEngine — priority queue, WAIT/RESUME, and rehydration."""
from __future__ import annotations

import heapq
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

_PRIORITY_MAP = {"high": 0, "normal": 1, "low": 2}


@dataclass(order=True)
class _QueueItem:
    priority: int
    sequence: int
    run_id: str = field(compare=False)
    handler: Callable[[], None] = field(compare=False)


class SchedulerEngine:
    """Priority queue scheduler with event-driven WAIT/RESUME.

    Three priority lanes: ``high`` (0) > ``normal`` (1) > ``low`` (2).
    WAIT registrations survive restarts when re-registered via ``FlowRehydrator``.
    """

    def __init__(self) -> None:
        self._queue: list[_QueueItem] = []
        self._queue_lock = threading.Lock()
        self._waiting: dict[str, dict[str, Any]] = {}
        self._waiting_lock = threading.Lock()
        self._sequence = 0
        self._rehydrated = False
        self._rehydrated_event = threading.Event()

    def schedule(
        self,
        run_id: str,
        handler: Callable[[], None],
        *,
        priority: str = "normal",
    ) -> None:
        """Enqueue *run_id* for execution at the given priority lane."""
        p = _PRIORITY_MAP.get(priority, 1)
        with self._queue_lock:
            self._sequence += 1
            item = _QueueItem(p, self._sequence, run_id, handler)
            heapq.heappush(self._queue, item)

    def pop(self) -> Optional[tuple[str, Callable[[], None]]]:
        """Pop and return the highest-priority ``(run_id, handler)`` or None."""
        with self._queue_lock:
            if not self._queue:
                return None
            item = heapq.heappop(self._queue)
            return item.run_id, item.handler

    def queue_depth(self, priority: Optional[str] = None) -> int:
        with self._queue_lock:
            if priority is None:
                return len(self._queue)
            p = _PRIORITY_MAP.get(priority, 1)
            return sum(1 for item in self._queue if item.priority == p)

    # ── WAIT / RESUME ─────────────────────────────────────────────────────────

    def wait_for_event(
        self,
        run_id: str,
        event_type: str,
        callback: Callable[[], None],
        *,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Register *run_id* as waiting for *event_type*.

        When ``notify_event(event_type)`` is called, *callback* is invoked
        synchronously (in the caller's thread) so it can re-schedule the run.
        """
        key = f"{event_type}:{correlation_id}" if correlation_id else event_type
        with self._waiting_lock:
            if key not in self._waiting:
                self._waiting[key] = {}
            self._waiting[key][run_id] = callback
        logger.debug("[SchedulerEngine] run=%s waiting for event=%s", run_id, event_type)

    def notify_event(
        self,
        event_type: str,
        correlation_id: Optional[str] = None,
    ) -> int:
        """Wake all runs registered for *event_type*.

        Returns the number of callbacks fired locally.
        """
        keys_to_try = [event_type]
        if correlation_id:
            keys_to_try.append(f"{event_type}:{correlation_id}")

        fired = 0
        for key in keys_to_try:
            with self._waiting_lock:
                waiters = dict(self._waiting.pop(key, {}))
            for run_id, callback in waiters.items():
                try:
                    callback()
                    fired += 1
                except Exception as exc:
                    logger.warning("[SchedulerEngine] callback for run=%s failed: %s", run_id, exc)

        return fired

    def is_waiting(self, run_id: str) -> bool:
        with self._waiting_lock:
            return any(run_id in waiters for waiters in self._waiting.values())

    def cancel_wait(self, run_id: str) -> bool:
        removed = False
        with self._waiting_lock:
            for key in list(self._waiting.keys()):
                if run_id in self._waiting[key]:
                    del self._waiting[key][run_id]
                    if not self._waiting[key]:
                        del self._waiting[key]
                    removed = True
        return removed

    # ── Rehydration ───────────────────────────────────────────────────────────

    def mark_rehydration_complete(self) -> None:
        """Signal that all waiting runs have been re-registered."""
        self._rehydrated = True
        self._rehydrated_event.set()
        logger.info("[SchedulerEngine] rehydration complete; waiting=%d", self.waiting_count)

    def is_rehydrated(self) -> bool:
        return self._rehydrated

    @property
    def waiting_count(self) -> int:
        with self._waiting_lock:
            return sum(len(v) for v in self._waiting.values())

"""FlowRehydrator — re-register waiting runs after process restart."""
from __future__ import annotations

import logging
from typing import Callable, Optional

from .run import FlowRunStore, FlowStatus
from .scheduler import SchedulerEngine

logger = logging.getLogger(__name__)


class FlowRehydrator:
    """Re-register WAITING flows with the scheduler after a restart.

    On startup, load all ``FlowRun`` rows with ``status == "waiting"`` from
    the store and re-register their WAIT callbacks with the scheduler.

    Args:
        run_store:        The persistent FlowRun store.
        scheduler:        The SchedulerEngine to register WAITs on.
        resume_fn:        ``(run_id: str) → None`` — called when event fires.
    """

    def __init__(
        self,
        run_store: FlowRunStore,
        scheduler: SchedulerEngine,
        resume_fn: Callable[[str], None],
    ) -> None:
        self._store = run_store
        self._scheduler = scheduler
        self._resume_fn = resume_fn

    def rehydrate(self, run_ids: Optional[list[str]] = None) -> int:
        """Re-register waiting runs.

        Args:
            run_ids: Optional subset of run IDs.  When None, all WAITING runs
                     from the store are rehydrated.

        Returns:
            Number of runs successfully rehydrated.
        """
        if run_ids is not None:
            runs = [self._store.get(rid) for rid in run_ids]
            runs = [r for r in runs if r is not None and r.status == FlowStatus.WAITING]
        else:
            runs = self._store.list_waiting()

        rehydrated = 0
        for run in runs:
            if not run.waiting_for:
                continue
            try:
                rid = run.id
                event_type = run.waiting_for
                self._scheduler.wait_for_event(
                    rid,
                    event_type,
                    lambda r=rid: self._resume_fn(r),
                )
                rehydrated += 1
                logger.debug("[FlowRehydrator] re-registered run=%s event=%s", rid, event_type)
            except Exception as exc:
                logger.warning("[FlowRehydrator] failed to rehydrate run=%s: %s", run.id, exc)

        self._scheduler.mark_rehydration_complete()
        logger.info("[FlowRehydrator] rehydrated %d runs", rehydrated)
        return rehydrated

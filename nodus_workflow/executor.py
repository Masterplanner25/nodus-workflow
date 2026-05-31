"""FlowExecutor — run a FlowRun through its nodes."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Optional

from .definition import FlowDefinition, NodeHandler
from .run import FlowRun, FlowRunStore, FlowStatus, InMemoryRunStore
from .scheduler import SchedulerEngine
from .signals import WorkflowWaitSignal

logger = logging.getLogger(__name__)


class FlowExecutor:
    """Execute ``FlowRun`` objects through a ``FlowDefinition``.

    Args:
        scheduler:       The scheduler to re-enqueue runs and register WAITs.
        run_store:       Persistence for FlowRun state.
        handler_registry: Mapping from ``node.handler_id`` → ``NodeHandler``.
    """

    def __init__(
        self,
        scheduler: SchedulerEngine,
        *,
        run_store: Optional[FlowRunStore] = None,
        handler_registry: Optional[dict[str, NodeHandler]] = None,
    ) -> None:
        self._scheduler = scheduler
        self._run_store = run_store if run_store is not None else InMemoryRunStore()
        self._handlers: dict[str, NodeHandler] = dict(handler_registry or {})

    def register_handler(self, handler_id: str, handler: NodeHandler) -> None:
        self._handlers[handler_id] = handler

    def start(
        self,
        definition: FlowDefinition,
        initial_state: dict[str, Any],
        user_id: str,
        *,
        trace_id: Optional[str] = None,
        priority: str = "normal",
    ) -> str:
        """Create a FlowRun and schedule it for execution.

        Returns the new run ID.
        """
        run = FlowRun(
            flow_name=definition.name,
            user_id=user_id,
            state=dict(initial_state),
            current_node=definition.start_node_id,
            trace_id=trace_id,
        )
        run.transition(FlowStatus.RUNNING)
        self._run_store.save(run)
        self._scheduler.schedule(
            run.id,
            lambda r=run, d=definition: self._execute_run(r, d),
            priority=priority,
        )
        return run.id

    def resume(self, run_id: str, definition: FlowDefinition) -> None:
        """Re-enqueue a waiting run after its event fires."""
        run = self._run_store.get(run_id)
        if run is None:
            logger.warning("[FlowExecutor] resume: run_id=%s not found", run_id)
            return
        if run.status != FlowStatus.WAITING:
            logger.debug("[FlowExecutor] resume: run_id=%s not in WAITING (status=%s)", run_id, run.status)
            return
        run.waiting_for = None
        run.transition(FlowStatus.EXECUTING)
        self._run_store.save(run)
        self._scheduler.schedule(
            run.id,
            lambda r=run, d=definition: self._execute_run(r, d),
        )

    def _execute_run(self, run: FlowRun, definition: FlowDefinition) -> None:
        """Synchronous entry point called by the scheduler.

        Always creates a fresh event loop so it never conflicts with
        any existing loop (pytest-asyncio, application servers, etc.).
        """
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self._execute_run_async(run, definition))
        except Exception as exc:
            logger.error("[FlowExecutor] execution error for run=%s: %s", run.id, exc)
        finally:
            loop.close()

    async def _execute_run_async(self, run: FlowRun, definition: FlowDefinition) -> None:
        node_id = run.current_node
        if node_id is None:
            run.transition(FlowStatus.COMPLETED)
            self._run_store.save(run)
            return

        node = definition.get_node(node_id)
        if node is None:
            run.error = f"Node {node_id!r} not found in definition"
            run.transition(FlowStatus.FAILED)
            self._run_store.save(run)
            return

        handler = self._handlers.get(node.handler_id)
        if handler is None:
            run.error = f"No handler registered for handler_id={node.handler_id!r}"
            run.transition(FlowStatus.FAILED)
            self._run_store.save(run)
            return

        run.transition(FlowStatus.EXECUTING)
        self._run_store.save(run)

        context = {
            "run_id": run.id,
            "flow_name": run.flow_name,
            "user_id": run.user_id,
            "trace_id": run.trace_id,
            "node_id": node_id,
            "node_config": node.config,
            **run.state,
        }

        try:
            result = await handler.execute(context)
            run.state.update(result)
        except WorkflowWaitSignal as wait:
            # Advance past the waiting node so resume starts from the next one
            next_nodes = definition.next_nodes(node_id, run.state)
            run.current_node = next_nodes[0] if next_nodes else None
            run.waiting_for = wait.event_type
            run.transition(FlowStatus.WAITING)
            self._run_store.save(run)
            self._scheduler.wait_for_event(
                run.id,
                wait.event_type,
                lambda: self.resume(run.id, definition),
                correlation_id=wait.correlation_id,
            )
            return
        except Exception as exc:
            logger.warning("[FlowExecutor] node=%s failed: %s", node_id, exc)
            # Simple retry logic: re-enqueue up to max_retries
            retries = run.state.get("_retry_count", 0)
            max_r = node.max_retries if node.max_retries is not None else definition.max_retries
            if retries < max_r:
                run.state["_retry_count"] = retries + 1
                run.transition(FlowStatus.RUNNING)
                self._run_store.save(run)
                self._scheduler.schedule(
                    run.id,
                    lambda r=run, d=definition: self._execute_run(r, d),
                )
            else:
                run.error = str(exc)
                run.transition(FlowStatus.FAILED)
                self._run_store.save(run)
            return

        # Advance to next node
        run.state.pop("_retry_count", None)
        next_nodes = definition.next_nodes(node_id, run.state)
        if next_nodes:
            run.current_node = next_nodes[0]
            run.transition(FlowStatus.RUNNING)
            self._run_store.save(run)
            self._scheduler.schedule(
                run.id,
                lambda r=run, d=definition: self._execute_run(r, d),
            )
        else:
            run.transition(FlowStatus.COMPLETED)
            self._run_store.save(run)

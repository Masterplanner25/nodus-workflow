"""nodus-workflow tests — no external services required."""
import asyncio
import pytest

from nodus_workflow import (
    FlowDefinition, FlowEdge, FlowExecutor, FlowNode,
    FlowRehydrator, FlowRun, FlowStatus,
    InMemoryRunStore, SchedulerEngine, WorkflowWaitSignal,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

class _EchoHandler:
    """Sets result = input_value in context."""
    def __init__(self, key="result", value="echo"):
        self._key = key; self._value = value
    async def execute(self, ctx):
        return {self._key: self._value}


class _FailHandler:
    async def execute(self, ctx):
        raise RuntimeError("node failed")


class _WaitHandler:
    """Suspends execution waiting for an event."""
    def __init__(self, event_type="test.done"):
        self._event_type = event_type
    async def execute(self, ctx):
        raise WorkflowWaitSignal(self._event_type)   # no correlation_id for simple tests


def _simple_flow(handler_id="echo") -> FlowDefinition:
    return FlowDefinition(
        name="simple",
        nodes=[FlowNode(id="n1", handler_id=handler_id)],
        edges=[],
    )


def _two_node_flow() -> FlowDefinition:
    return FlowDefinition(
        name="two_node",
        nodes=[
            FlowNode(id="n1", handler_id="step1"),
            FlowNode(id="n2", handler_id="step2"),
        ],
        edges=[FlowEdge("n1", "n2")],
    )


# ── WorkflowWaitSignal ─────────────────────────────────────────────────────────

def test_wait_signal_attributes():
    sig = WorkflowWaitSignal("payment.done", correlation_id="c1")
    assert sig.event_type == "payment.done"
    assert sig.correlation_id == "c1"
    assert "payment.done" in str(sig)


# ── FlowDefinition ────────────────────────────────────────────────────────────

def test_flow_definition_start_node():
    f = _simple_flow()
    assert f.start_node_id == "n1"


def test_flow_definition_get_node():
    f = _simple_flow()
    assert f.get_node("n1") is not None
    assert f.get_node("missing") is None


def test_flow_definition_next_nodes_unconditional():
    f = _two_node_flow()
    assert f.next_nodes("n1", {}) == ["n2"]


def test_flow_definition_next_nodes_conditional_true():
    f = FlowDefinition(
        name="cond",
        nodes=[FlowNode("n1", "h"), FlowNode("n2", "h")],
        edges=[FlowEdge("n1", "n2", condition="go")],
    )
    assert f.next_nodes("n1", {"go": True}) == ["n2"]
    assert f.next_nodes("n1", {"go": False}) == []


# ── FlowRun ────────────────────────────────────────────────────────────────────

def test_flow_run_transition():
    r = FlowRun(flow_name="test", user_id="u1")
    r.transition(FlowStatus.RUNNING)
    assert r.status == FlowStatus.RUNNING
    assert r.updated_at >= r.created_at


def test_flow_run_terminal():
    r = FlowRun()
    r.transition(FlowStatus.COMPLETED)
    assert r.is_terminal is True
    assert r.completed_at is not None


# ── SchedulerEngine ───────────────────────────────────────────────────────────

def test_scheduler_schedule_and_pop():
    s = SchedulerEngine()
    called = []
    s.schedule("r1", lambda: called.append("r1"))
    item = s.pop()
    assert item[0] == "r1"
    item[1]()
    assert "r1" in called


def test_scheduler_priority_order():
    s = SchedulerEngine()
    s.schedule("low",    lambda: None, priority="low")
    s.schedule("high",   lambda: None, priority="high")
    s.schedule("normal", lambda: None, priority="normal")
    order = [s.pop()[0], s.pop()[0], s.pop()[0]]
    assert order == ["high", "normal", "low"]


def test_scheduler_notify_event():
    s = SchedulerEngine()
    fired = []
    s.wait_for_event("r1", "op.done", lambda: fired.append("r1"))
    s.mark_rehydration_complete()
    count = s.notify_event("op.done")
    assert count == 1
    assert "r1" in fired


def test_scheduler_dedup_by_correlation():
    s = SchedulerEngine()
    fired = []
    s.wait_for_event("r1", "op.done", lambda: fired.append("r1"), correlation_id="c1")
    s.mark_rehydration_complete()
    s.notify_event("op.done", correlation_id="c1")
    assert "r1" in fired


def test_scheduler_cancel_wait():
    s = SchedulerEngine()
    s.wait_for_event("r1", "op.done", lambda: None)
    assert s.is_waiting("r1") is True
    s.cancel_wait("r1")
    assert s.is_waiting("r1") is False


# ── FlowExecutor full run ─────────────────────────────────────────────────────

def _run_to_completion(executor: FlowExecutor, run_id: str) -> None:
    """Drain scheduler until no more items."""
    for _ in range(50):  # safety limit
        item = executor._scheduler.pop()
        if item is None:
            break
        item[1]()


def test_executor_simple_flow():
    store = InMemoryRunStore()
    scheduler = SchedulerEngine()
    executor = FlowExecutor(scheduler, run_store=store)
    executor.register_handler("echo", _EchoHandler())

    run_id = executor.start(_simple_flow("echo"), {}, "u1")
    _run_to_completion(executor, run_id)

    run = store.get(run_id)
    assert run.status == FlowStatus.COMPLETED
    assert run.state.get("result") == "echo"


def test_executor_two_node_flow():
    store = InMemoryRunStore()
    scheduler = SchedulerEngine()
    executor = FlowExecutor(scheduler, run_store=store)
    executor.register_handler("step1", _EchoHandler("step1_done", "yes"))
    executor.register_handler("step2", _EchoHandler("step2_done", "yes"))

    run_id = executor.start(_two_node_flow(), {}, "u1")
    _run_to_completion(executor, run_id)

    run = store.get(run_id)
    assert run.status == FlowStatus.COMPLETED
    assert run.state.get("step1_done") == "yes"
    assert run.state.get("step2_done") == "yes"


def test_executor_node_failure_after_retries():
    store = InMemoryRunStore()
    scheduler = SchedulerEngine()
    definition = FlowDefinition(
        name="fail_test", nodes=[FlowNode("n1", "fail")], edges=[], max_retries=1
    )
    executor = FlowExecutor(scheduler, run_store=store)
    executor.register_handler("fail", _FailHandler())

    run_id = executor.start(definition, {}, "u1")
    _run_to_completion(executor, run_id)

    run = store.get(run_id)
    assert run.status == FlowStatus.FAILED
    assert "node failed" in run.error


def test_executor_wait_and_resume():
    store = InMemoryRunStore()
    scheduler = SchedulerEngine()
    scheduler.mark_rehydration_complete()
    definition = FlowDefinition(
        name="wait_test",
        nodes=[FlowNode("n1", "waiter"), FlowNode("n2", "after")],
        edges=[FlowEdge("n1", "n2")],
    )
    executor = FlowExecutor(scheduler, run_store=store)
    executor.register_handler("waiter", _WaitHandler("approval.done"))
    executor.register_handler("after", _EchoHandler("after_done", "yes"))

    run_id = executor.start(definition, {}, "u1")
    _run_to_completion(executor, run_id)  # runs n1, which WAITs

    run = store.get(run_id)
    assert run.status == FlowStatus.WAITING

    # Fire the event
    scheduler.notify_event("approval.done")
    _run_to_completion(executor, run_id)  # resumes with n2

    run = store.get(run_id)
    assert run.status == FlowStatus.COMPLETED
    assert run.state.get("after_done") == "yes"


# ── FlowRehydrator ────────────────────────────────────────────────────────────

def test_rehydrator_reregisters_waiting_runs():
    store = InMemoryRunStore()
    scheduler = SchedulerEngine()

    run = FlowRun(flow_name="f", user_id="u1", waiting_for="evt.done")
    run.transition(FlowStatus.WAITING)
    store.save(run)

    resumed = []
    rehydrator = FlowRehydrator(store, scheduler, resume_fn=lambda rid: resumed.append(rid))
    count = rehydrator.rehydrate()
    assert count == 1
    assert scheduler.is_rehydrated() is True

    scheduler.notify_event("evt.done")
    assert run.id in resumed

# nodus-flow

> **Status:** v0.2.0 — renamed from `nodus-workflow`. See [Naming](#naming).

**A standalone asyncio DAG runner with WAIT/RESUME, priority scheduling and
rehydration.** Define DAGs, execute them with priority-queued scheduling,
suspend nodes on events, and rehydrate WAITING runs after a process restart.
No required external dependencies — pure stdlib.

## Naming

**This is not the engine behind the Nodus `workflow` keyword.** That engine
ships inside `nodus-lang` and is not separately installable:

```
workflow build {
    step compile { ... }
    step test after compile { ... }
}
```

If that is what you are looking for, `pip install nodus-lang` — nothing on this
page will run it.

`nodus-flow` is a Python library with its own vocabulary (`FlowDefinition`,
`FlowNode`, `FlowRun`, `FlowExecutor`) and its own execution model. It shares no
code with nodus-lang and does not depend on it. Its design came from
aindy-runtime rather than from Nodus, which is why it reads like a second
workflow engine — it is one, for a different host.

**Why the rename.** Published as `nodus-workflow`, the name read as "the Nodus
workflow implementation" and misled a source-level architecture audit of Nodus
into reporting that the project had "forked its own thesis" — a wrong
top-priority finding that reached the governance record and stood for months.
The name was the whole cause: the auditor never read the PyPI metadata, and an
earlier rename of the *import* name had not reached them either. Tracked as
[nodus-lang#483](https://github.com/Masterplanner25/Nodus/issues/483).

`pip install nodus-workflow` still works and now installs this package, but the
old name is deprecated and will not receive releases.

---

## Install

```bash
pip install nodus-flow
```

---

## What it provides

| Component | Purpose |
|---|---|
| `FlowDefinition` | DAG: nodes, edges, default retry, timeout |
| `FlowNode` | One node with handler_id, config, optional retry override |
| `FlowEdge` | Directed edge with optional condition function |
| `FlowRun` / `InMemoryRunStore` | Run state + thread-safe in-memory store |
| `SchedulerEngine` | Priority queue (high/normal/low) + WAIT/RESUME |
| `FlowExecutor` | Orchestrates start(), resume(), handler registration |
| `FlowRehydrator` | Re-registers WAITING runs after process restart |
| `WorkflowWaitSignal` | Raise inside a handler to suspend node execution |

---

## Quick start

```python
import asyncio
from nodus_flow import (
    FlowDefinition, FlowNode, FlowEdge, FlowExecutor,
    InMemoryRunStore, SchedulerEngine,
)

# Define handlers
async def fetch_data(ctx):
    return {"data": "fetched"}

async def process_data(ctx):
    return {"processed": ctx["state"].get("data")}

# Build the DAG
flow = FlowDefinition(
    name="my-pipeline",
    nodes=[
        FlowNode(id="fetch",   handler_id="fetch_data"),
        FlowNode(id="process", handler_id="process_data"),
    ],
    edges=[
        FlowEdge(from_node="fetch", to_node="process"),
    ],
)

# Execute
store = InMemoryRunStore()
scheduler = SchedulerEngine()
executor = FlowExecutor(store=store, scheduler=scheduler)
executor.register_handler("fetch_data",   fetch_data)
executor.register_handler("process_data", process_data)

run = await executor.start(flow, initial_state={})
print(run.status)   # FlowStatus.COMPLETED
```

---

## WAIT/RESUME semantics

```python
from nodus_flow import WorkflowWaitSignal

async def approval_node(ctx):
    raise WorkflowWaitSignal(
        event_type="approval.granted",
        correlation_key=ctx["run_id"],
    )

# Later, when the event fires:
await executor.resume(run_id, event_payload={"approver": "alice"})
```

When a node raises `WorkflowWaitSignal`, the run transitions to `WAITING`
and is parked in the scheduler until `notify_event` or `resume` is called.

---

## SchedulerEngine

```python
from nodus_flow import SchedulerEngine
from nodus_flow.run import FlowStatus

scheduler = SchedulerEngine()

# Schedule with priority
scheduler.schedule(run_id, priority="high")      # high / normal / low
scheduler.schedule(run_id, priority="normal")

next_run_id = scheduler.pop()   # returns highest-priority pending run | None

# WAIT/RESUME
scheduler.wait_for_event(run_id, event_type="approval.granted", key="k")
scheduler.notify_event(event_type="approval.granted", key="k")  # re-queues run
scheduler.cancel_wait(run_id)
```

---

## FlowRehydrator

```python
from nodus_flow import FlowRehydrator, InMemoryRunStore

store = InMemoryRunStore()
rehydrator = FlowRehydrator(store=store, scheduler=scheduler)

# On process startup — re-register all WAITING runs
rehydrator.rehydrate()
```

---

## FlowStatus transitions

```
PENDING → RUNNING → WAITING → (event fires) → EXECUTING → COMPLETED
                                                          ↘ FAILED
```

---

## Design

- **No required dependencies.** Pure stdlib (`asyncio`, `threading`, `heapq`,
  `dataclasses`, `datetime`, `uuid`).
- **Protocol-based handlers.** Any async callable `(context: dict) → dict`
  satisfies `NodeHandler`.
- **Thread-safe.** `SchedulerEngine` and `InMemoryRunStore` use `threading.Lock`.
- **Separate from nodus-lang.** No nodus-lang import required — use it
  standalone or inside any Python application. See [Naming](#naming) for what
  this does *not* do.

---

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -q
```

---

## License

MIT — see [LICENSE](LICENSE).

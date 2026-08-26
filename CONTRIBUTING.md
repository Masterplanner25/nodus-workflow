# Contributing to nodus-flow

## Note on naming

`nodus-flow` is **not** the engine behind the Nodus `workflow` keyword. That
engine ships inside `nodus-lang` as `src/nodus_lang_workflow/` and is not
separately installable. This package is an independent asyncio DAG runner whose
design came from aindy-runtime; it shares no code with nodus-lang and does not
depend on it.

It was published as `nodus-workflow` until v0.2.0. The old name misled a
source-level audit of Nodus into a wrong top-priority finding — see
[nodus-lang#483](https://github.com/Masterplanner25/Nodus/issues/483) — which is
why the name changed. `pip install nodus-workflow` still resolves here, but the
old name is deprecated.

## Setup

```bash
git clone https://github.com/Masterplanner25/nodus-flow.git
cd nodus-flow
pip install -e ".[dev]"
```

## Running tests

```bash
pytest tests/ -q
```

## Code style

- Python 3.11+
- No required external dependencies (stdlib only)
- `NodeHandler` is a protocol — handlers satisfy it by structure
- `SchedulerEngine` and `InMemoryRunStore` must remain thread-safe
- `WorkflowWaitSignal` must only be raised inside `NodeHandler.execute()`
- `FlowStatus` transitions must follow: PENDING → RUNNING → WAITING/EXECUTING → COMPLETED/FAILED

## Submitting changes

1. Fork the repo and create a branch from `main`
2. Add tests for any new behaviour
3. Ensure `pytest tests/ -q` passes
4. Open a pull request with a description of what changes and why

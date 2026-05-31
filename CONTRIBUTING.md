# Contributing to nodus-workflow

## Note on naming

This is the standalone `nodus-workflow` package. The nodus-lang runtime ships
a separate in-tree `nodus_workflow` package (`src/nodus_workflow/`) with HTTP/CLI
surfaces and SQLite store. The two are distinct.

## Setup

```bash
git clone https://github.com/Masterplanner25/nodus-workflow.git
cd nodus-workflow
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

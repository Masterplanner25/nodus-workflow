# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.1.0] — 2026-05-31

Initial release.

### Added

- **`WorkflowWaitSignal`** — raise inside a `NodeHandler` to suspend execution.
  Fields: `event_type`, `correlation_key` (optional), `payload` (optional).

- **`NodeHandler`** — protocol: `async execute(context: dict) → dict`.

- **`FlowNode`** — one DAG node. Fields: `id`, `handler_id`, `config` (dict),
  optional `retry_override` (`RetryPolicy`-like).

- **`FlowEdge`** — directed edge. Fields: `from_node`, `to_node`, optional
  `condition` (callable that receives run state → bool).

- **`FlowDefinition`** — complete DAG. Fields: `name`, `nodes`, `edges`,
  optional `default_retry`, `timeout_seconds`.

- **`FlowStatus`** — enum: `PENDING`, `RUNNING`, `WAITING`, `EXECUTING`,
  `COMPLETED`, `FAILED`.

- **`FlowRun`** — persistent run state. Fields: `id` (UUID), `flow_name`,
  `status`, `state` (dict), `current_node`, `waiting_for`, `created_at`,
  `updated_at`, `completed_at`. `is_terminal`.

- **`FlowRunStore`** — protocol: `save`, `get`, `list_waiting`, `list_by_status`.

- **`InMemoryRunStore`** — thread-safe dict-backed `FlowRunStore`.

- **`SchedulerEngine`** — priority-queue scheduler.
  `schedule(run_id, priority)`, `pop()`, `wait_for_event(run_id, event_type,
  key)`, `notify_event(event_type, key)`, `cancel_wait(run_id)`,
  `mark_rehydration_complete()`. Thread-safe. Priority: `"high"` > `"normal"`
  > `"low"`.

- **`FlowExecutor`** — orchestrates execution. `register_handler(id, fn)`,
  `start(flow, initial_state)` → `FlowRun`, `resume(run_id, event_payload)`.

- **`FlowRehydrator`** — re-registers `WAITING` runs from the store into
  the scheduler after process restart. `rehydrate()`.

- **17 tests** in `tests/test_workflow.py`.

- **No required dependencies** — pure stdlib. Optional `[persistence]` extra
  adds `sqlalchemy>=2.0.0` for persistent run storage.

[0.1.0]: https://github.com/Masterplanner25/nodus-workflow/releases/tag/v0.1.0

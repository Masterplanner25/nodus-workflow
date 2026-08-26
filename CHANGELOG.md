# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.2.0] — 2026-08-26

Renamed. No functional change: every type, signature and behaviour is identical
to 0.1.0.

### Changed

- **The distribution is now `nodus-flow`, and the Python package is
  `nodus_flow`.** Update imports: `from nodus_workflow import ...` becomes
  `from nodus_flow import ...`.

  Published as `nodus-workflow`, the name read as *"the Nodus workflow
  implementation"* — and it is not. The engine behind the Nodus `workflow`
  keyword ships inside `nodus-lang` as `nodus_lang_workflow` and is not
  separately installable; this library is an independent asyncio DAG runner
  whose design came from aindy-runtime, sharing no code with nodus-lang and not
  depending on it.

  That collision caused a documented failure, not a hypothetical one: a
  source-level architecture audit of Nodus attributed this package's
  architecture to the language core, concluded the project had *"forked its own
  thesis"*, and made resolving it its top recommendation. It entered Nodus's
  governance record as a confirmed finding and stood for months. The auditor
  never read the PyPI metadata, so better `summary` text would not have reached
  them — only the name would. Tracked as
  [nodus-lang#483](https://github.com/Masterplanner25/Nodus/issues/483).

- **`nodus-workflow` remains installable and now depends on `nodus-flow`**, so
  existing installs keep working. It receives no further releases, and its
  project page states what it is not.

- **README and CONTRIBUTING naming notes corrected.** Both said the in-tree
  package was `nodus_workflow` at `src/nodus_workflow/`. That path was renamed
  to `src/nodus_lang_workflow/` on 2026-05-31, so the only disambiguation this
  repo carried named the very collision that rename removed.

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

[0.2.0]: https://github.com/Masterplanner25/nodus-flow/releases/tag/v0.2.0
[0.1.0]: https://github.com/Masterplanner25/nodus-flow/releases/tag/v0.1.0

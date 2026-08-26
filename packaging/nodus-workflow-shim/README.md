# nodus-workflow — deprecated, renamed to `nodus-flow`

**This package is a deprecated alias.** It installs
[`nodus-flow`](https://pypi.org/project/nodus-flow/) and ships no code of its own.

## If you are looking for the Nodus `workflow` keyword

**You want `nodus-lang`, not this.** The engine behind

```
workflow build {
    step compile { ... }
    step test after compile { ... }
}
```

ships **inside** `nodus-lang` and is not separately installable:

```bash
pip install nodus-lang
```

Nothing in this package, or in `nodus-flow`, will run that.

## If you are looking for the standalone DAG runner

That is `nodus-flow` — an independent asyncio DAG runner with WAIT/RESUME,
priority scheduling and rehydration, whose design came from aindy-runtime. It
shares no code with nodus-lang and does not depend on it.

```bash
pip install nodus-flow
```

Imports change from `nodus_workflow` to `nodus_flow`; nothing else does.

## Why the rename

Published under this name, the package read as "the Nodus workflow
implementation" and misled a source-level architecture audit of Nodus into
reporting that the project had "forked its own thesis" — a wrong top-priority
finding that reached the governance record and stood for months. The auditor
never read this page, which is why correcting the metadata alone was not the
fix. See [nodus-lang#483](https://github.com/Masterplanner25/Nodus/issues/483).

MIT.

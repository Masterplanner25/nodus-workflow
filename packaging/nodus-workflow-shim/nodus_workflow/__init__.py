"""Deprecated alias for :mod:`nodus_flow`.

The distribution was renamed ``nodus-workflow`` -> ``nodus-flow`` at 0.2.0
because the old name read as "the Nodus workflow implementation" and it is not:
the engine behind the Nodus ``workflow`` keyword ships inside ``nodus-lang`` as
``nodus_lang_workflow`` and is not separately installable. See
https://github.com/Masterplanner25/Nodus/issues/483.

This module re-exports ``nodus_flow`` unchanged so existing imports keep
working. It warns once on import and will be removed in a future release.
"""
from __future__ import annotations

import warnings as _warnings

from nodus_flow import *  # noqa: F401,F403
from nodus_flow import __all__ as _flow_all

# Submodules. Binding the names as attributes is not enough: `from
# nodus_workflow.run import FlowStatus` is an import statement, and the import
# machinery looks the submodule up in sys.modules under its dotted name. The old
# README documented exactly that spelling, so both are registered.
import sys as _sys

from nodus_flow import (  # noqa: F401
    definition,
    executor,
    rehydrator,
    run,
    scheduler,
    signals,
)

for _sub in ("definition", "executor", "rehydrator", "run", "scheduler", "signals"):
    _sys.modules[f"{__name__}.{_sub}"] = _sys.modules[f"nodus_flow.{_sub}"]
del _sub

__all__ = list(_flow_all)

_warnings.warn(
    "nodus_workflow is deprecated and is now an alias for nodus_flow. "
    "The distribution was renamed nodus-workflow -> nodus-flow at 0.2.0; "
    "update imports to `from nodus_flow import ...`. "
    "If you were looking for the engine behind the Nodus `workflow` keyword, "
    "that ships inside nodus-lang and is not this package "
    "(https://github.com/Masterplanner25/Nodus/issues/483).",
    DeprecationWarning,
    stacklevel=2,
)

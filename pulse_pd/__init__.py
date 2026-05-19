"""
PULSE–PD: Paradoxon Diagram tooling (v0).

Core metrics:
- DS: Decision Stability
- MI: Model Inconsistency
- GF: Gate Friction
- PI: Paradox Index

The NumPy-backed public exports are lazy-loaded so lightweight submodules
such as pulse_pd.examples.make_toy_X can run before optional analysis
dependencies are installed.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any


__all__ = [
    "compute_ds",
    "compute_mi",
    "compute_gf",
    "compute_pi",
    "run_pd_from_cuts",
]


_EXPORTS: dict[str, tuple[str, str]] = {
    "compute_ds": ("pulse_pd.pd", "compute_ds"),
    "compute_mi": ("pulse_pd.pd", "compute_mi"),
    "compute_gf": ("pulse_pd.pd", "compute_gf"),
    "compute_pi": ("pulse_pd.pd", "compute_pi"),
    "run_pd_from_cuts": ("pulse_pd.cut_adapter", "run_pd_from_cuts"),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _EXPORTS[name]
    module = import_module(module_name)
    value = getattr(module, attr_name)

    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))

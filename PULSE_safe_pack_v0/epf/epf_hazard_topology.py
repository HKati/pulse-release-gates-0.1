"""
epf_hazard_topology.py

Topology overlay for the EPF Relational Grail.

Purpose:
    - Do NOT change gating behavior.
    - Provide a deterministic "field region" label by combining:
        (A) baseline deterministic gate outcome (good/bad)
        (B) hazard-zone stability (stable/unstable)

This yields a simple 2x2 overlay:
    stably_good    : baseline_ok + hazard GREEN
    unstably_good  : baseline_ok + hazard AMBER/RED
    stably_bad     : baseline_fail + hazard GREEN
    unstably_bad   : baseline_fail + hazard AMBER/RED

The hazard shadow-gate (epf_hazard_ok) is excluded from baseline_ok by default
so the overlay doesn't accidentally become self-referential.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence


DEFAULT_HAZARD_GATE_NAME = "epf_hazard_ok"

REGION_STABLY_GOOD = "stably_good"
REGION_UNSTABLY_GOOD = "unstably_good"
REGION_STABLY_BAD = "stably_bad"
REGION_UNSTABLY_BAD = "unstably_bad"
REGION_UNKNOWN = "unknown"


@dataclass(frozen=True)
class HazardTopologyState:
    """
    Deterministic topology classification (overlay).

    Fields:
        region:
            One of:
              stably_good / unstably_good / stably_bad / unstably_bad / unknown
        baseline_ok:
            Whether all baseline (non-hazard) gates pass.
        stable:
            Derived from hazard_zone:
              GREEN -> True, AMBER/RED -> False, otherwise None.
        hazard_zone:
            Normalized hazard zone (GREEN/AMBER/RED/UNKNOWN).
        reason:
            Compact explanation string.
    """
    region: str
    baseline_ok: Optional[bool]
    stable: Optional[bool]
    hazard_zone: str
    reason: str


def _coerce_bool(x: Any) -> bool:
    return bool(x)


def _baseline_ok(
    gates: Mapping[str, Any],
    *,
    exclude: Sequence[str],
) -> bool:
    excl = set(map(str, exclude))
    vals = []
    for k, v in gates.items():
        if str(k) in excl:
            continue
        vals.append(_coerce_bool(v))
    return all(vals)


def compute_hazard_topology(
    gates: Mapping[str, Any],
    hazard_zone: str,
    *,
    exclude_gates: Optional[Sequence[str]] = None,
    hazard_gate_name: str = DEFAULT_HAZARD_GATE_NAME,
) -> HazardTopologyState:
    """
    Compute topology region from baseline gates and hazard zone.

    Args:
        gates:
            Mapping of gate_name -> bool-like.
        hazard_zone:
            "GREEN" / "AMBER" / "RED" (case-insensitive).
        exclude_gates:
            Extra gate names to exclude from baseline_ok. If None, defaults
            to excluding the hazard gate.
        hazard_gate_name:
            The hazard shadow-gate name. Always excluded from baseline_ok
            unless explicitly overridden.

    Returns:
        HazardTopologyState.
    """
    hz = str(hazard_zone or "").strip().upper()

    if exclude_gates is None:
        exclude = [hazard_gate_name]
    else:
        exclude = list(exclude_gates)
        if hazard_gate_name not in exclude:
            exclude.append(hazard_gate_name)

    base_ok = _baseline_ok(gates, exclude=exclude)

    if hz == "GREEN":
        stable = True
    elif hz in ("AMBER", "RED"):
        stable = False
    else:
        stable = None

    if stable is None:
        region = REGION_UNKNOWN
    else:
        if base_ok and stable:
            region = REGION_STABLY_GOOD
        elif base_ok and not stable:
            region = REGION_UNSTABLY_GOOD
        elif (not base_ok) and stable:
            region = REGION_STABLY_BAD
        else:
            region = REGION_UNSTABLY_BAD

    reason = (
        f"baseline_ok={base_ok} (excluded={sorted(set(map(str, exclude)))}) "
        f"+ hazard_zone={hz or 'UNKNOWN'} -> {region}"
    )

    return HazardTopologyState(
        region=region,
        baseline_ok=base_ok,
        stable=stable,
        hazard_zone=hz or "UNKNOWN",
        reason=reason,
    )

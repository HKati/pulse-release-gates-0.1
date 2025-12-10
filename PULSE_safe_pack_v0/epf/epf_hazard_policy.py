"""
epf_hazard_policy.py

Gate policy helper for the EPF hazard probe.

This module takes a HazardState (T, S, D, E, zone, reason) produced by
epf_hazard_forecast and derives a simple gate decision:

    - ok (bool)
    - severity (LOW / MEDIUM / HIGH / UNKNOWN)
    - reason (human-readable summary)

The default policy is "RED-only block", as described in the
epf_hazard_gate design note:

    - GREEN  → ok=True,  severity=LOW
    - AMBER  → ok=True,  severity=MEDIUM
    - RED    → ok=False, severity=HIGH

The gate is intended to be opt-in and experimental in early phases.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from .epf_hazard_forecast import HazardState


Severity = Literal["LOW", "MEDIUM", "HIGH", "UNKNOWN"]


@dataclass
class HazardGateConfig:
    """
    Configuration for the EPF hazard gate policy.

    For now this is intentionally minimal and encodes only the
    "RED-only block" choice in a single flag.

    Fields:
        block_on_red_only:
            If True (default), the gate blocks only when zone == "RED".
            If False, the policy can be extended in future revisions
            (e.g. to also treat AMBER as non-OK).
    """
    block_on_red_only: bool = True


@dataclass
class HazardGateDecision:
    """
    Result of evaluating the hazard gate policy.

    Fields:
        ok:
            Boolean indicating whether the hazard gate considers the
            field acceptable (True) or not (False).
        severity:
            Qualitative severity level derived from the hazard zone,
            one of: "LOW", "MEDIUM", "HIGH", "UNKNOWN".
        zone:
            Original zone from HazardState ("GREEN", "AMBER", "RED",
            or other).
        E:
            The early-warning index from HazardState.
        reason:
            Human-readable summary string, typically derived from
            HazardState.reason but may be augmented with policy notes.
    """
    ok: bool
    severity: Severity
    zone: str
    E: float
    reason: str


def _severity_from_zone(zone: str) -> Severity:
    """
    Map the hazard zone to a coarse severity level.

    GREEN  → LOW
    AMBER  → MEDIUM
    RED    → HIGH
    other  → UNKNOWN
    """
    if zone == "GREEN":
        return "LOW"
    if zone == "AMBER":
        return "MEDIUM"
    if zone == "RED":
        return "HIGH"
    return "UNKNOWN"


def evaluate_hazard_gate(
    state: HazardState,
    cfg: Optional[HazardGateConfig] = None,
) -> HazardGateDecision:
    """
    Evaluate the EPF hazard gate policy for a given HazardState.

    Default policy ("RED-only block"):
        - ok = (zone != "RED")
        - severity derived from zone via _severity_from_zone(...)
        - reason = state.reason (unchanged)

    The decision is intended to be logged / surfaced alongside other
    gates and may be used as an additional signal for release decisions.
    """
    if cfg is None:
        cfg = HazardGateConfig()

    zone = state.zone
    severity = _severity_from_zone(zone)

    if cfg.block_on_red_only:
        ok = zone != "RED"
    else:
        # Future extension point (e.g. treat AMBER as non-OK).
        ok = zone not in {"RED"}  # currently same as block_on_red_only=True

    return HazardGateDecision(
        ok=ok,
        severity=severity,
        zone=zone,
        E=state.E,
        reason=state.reason,
    )

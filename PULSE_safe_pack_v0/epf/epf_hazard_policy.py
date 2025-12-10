import pathlib
import sys

# Ensure repository root is on sys.path so PULSE_safe_pack_v0 can be imported
ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PULSE_safe_pack_v0.epf.epf_hazard_forecast import HazardState
from PULSE_safe_pack_v0.epf.epf_hazard_policy import (
    HazardGateConfig,
    HazardGateDecision,
    evaluate_hazard_gate,
)


def _make_state(zone: str, E: float = 0.0) -> HazardState:
    """Minimal HazardState for policy testing; numeric fields are arbitrary."""
    return HazardState(
        T=0.1,
        S=0.9,
        D=0.01,
        E=E,
        zone=zone,
        reason=f"zone={zone}, E={E}",
    )


def test_green_zone_is_ok_with_low_severity():
    state = _make_state("GREEN", E=0.05)

    decision = evaluate_hazard_gate(state)

    assert isinstance(decision, HazardGateDecision)
    assert decision.ok is True
    assert decision.severity == "LOW"
    assert decision.zone == "GREEN"
    assert decision.E == state.E
    assert "GREEN" in decision.reason


def test_amber_zone_is_ok_with_medium_severity_under_default_policy():
    state = _make_state("AMBER", E=0.4)

    decision = evaluate_hazard_gate(state)

    assert decision.ok is True
    assert decision.severity == "MEDIUM"
    assert decision.zone == "AMBER"


def test_red_zone_is_not_ok_with_high_severity():
    state = _make_state("RED", E=0.9)

    decision = evaluate_hazard_gate(state)

    assert decision.ok is False
    assert decision.severity == "HIGH"
    assert decision.zone == "RED"


def test_unknown_zone_yields_unknown_severity_but_still_ok():
    state = _make_state("BLUE", E=0.2)

    decision = evaluate_hazard_gate(state)

    assert decision.ok is True
    assert decision.severity == "UNKNOWN"
    assert decision.zone == "BLUE"

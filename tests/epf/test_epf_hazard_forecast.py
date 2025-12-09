import math
import pathlib
import sys

# Ensure repository root is on sys.path so PULSE_safe_pack_v0 can be imported
ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PULSE_safe_pack_v0.epf.epf_hazard_forecast import (
    HazardConfig,
    forecast_hazard,
    compute_T,
)


def test_compute_T_zero_for_identical_snapshots():
    current = {"a": 1.0, "b": -2.0}
    reference = {"a": 1.0, "b": -2.0}

    T = compute_T(current, reference)

    assert T == 0.0


def test_compute_T_simple_distance():
    current = {"x": 3.0}
    reference = {"x": 0.0}

    T = compute_T(current, reference)

    assert T == 3.0  # |3 - 0|


def test_forecast_green_when_close_and_stable():
    cfg = HazardConfig(
        alpha=1.0,
        beta=1.0,
        warn_threshold=0.3,
        crit_threshold=0.7,
        min_history=3,
    )

    current = {"m": 1.01}
    reference = {"m": 1.0}
    stability_metrics = {"RDSI": 0.95}
    history_T = [0.01, 0.02]  # very small drift so far

    state = forecast_hazard(
        current_snapshot=current,
        reference_snapshot=reference,
        stability_metrics=stability_metrics,
        history_T=history_T,
        cfg=cfg,
    )

    assert state.zone == "GREEN"
    assert state.E < cfg.warn_threshold


def test_forecast_red_when_unstable_and_drifting():
    cfg = HazardConfig(
        alpha=1.0,
        beta=1.0,
        warn_threshold=0.3,
        crit_threshold=0.7,
        min_history=3,
    )

    # significantly far from reference
    current = {"m": 3.0}
    reference = {"m": 0.0}
    # low stability
    stability_metrics = {"RDSI": 0.1}
    # noticeable drift in T
    history_T = [0.5, 1.0, 1.8]

    state = forecast_hazard(
        current_snapshot=current,
        reference_snapshot=reference,
        stability_metrics=stability_metrics,
        history_T=history_T,
        cfg=cfg,
    )

    assert state.zone == "RED"
    assert state.E >= cfg.crit_threshold
    assert state.S <= 0.1


def test_history_window_respected():
    """Ensure that only the last `min_history` T values are used for D."""
    cfg = HazardConfig(min_history=3)

    current = {"m": 5.0}
    reference = {"m": 0.0}
    stability_metrics = {"RDSI": 0.8}

    # longer history than min_history
    history_T = [0.1, 0.2, 0.5, 1.0, 2.0]

    state = forecast_hazard(
        current_snapshot=current,
        reference_snapshot=reference,
        stability_metrics=stability_metrics,
        history_T=history_T,
        cfg=cfg,
    )

    assert state.D >= 0.0
    assert math.isfinite(state.D)

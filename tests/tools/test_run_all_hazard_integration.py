import json
import os
import pathlib
import subprocess
import sys

# Repository root (…/pulse-release-gates-0.1)
ROOT = pathlib.Path(__file__).resolve().parents[2]
RUN_ALL = ROOT / "PULSE_safe_pack_v0" / "tools" / "run_all.py"
ART = ROOT / "PULSE_safe_pack_v0" / "artifacts"


def _run_run_all(extra_env: dict | None = None) -> dict:
    """Run run_all.py and return the loaded status.json."""
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    # Run from repo root so relative paths behave as in normal use.
    subprocess.run(
        [sys.executable, str(RUN_ALL)],
        check=True,
        cwd=str(ROOT),
        env=env,
    )

    status_path = ART / "status.json"
    assert status_path.exists(), f"status.json not found at {status_path}"
    with status_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_run_all_hazard_shadow_gate_default():
    """By default the hazard gate is in shadow mode (always True)."""
    status = _run_run_all()
    gates = status["gates"]
    metrics = status["metrics"]

    # Gate is present but shadowed to True by default.
    assert "epf_hazard_ok" in gates
    assert gates["epf_hazard_ok"] is True

    # Hazard metrics are surfaced.
    for key in [
        "hazard_T",
        "hazard_S",
        "hazard_D",
        "hazard_E",
        "hazard_zone",
        "hazard_reason",
        "hazard_ok",
        "hazard_severity",
    ]:
        assert key in metrics, f"missing hazard metric: {key}"


def test_run_all_hazard_gate_enforced_follows_metrics_ok():
    """With EPF_HAZARD_ENFORCE=1, the gate must follow hazard_ok."""
    status = _run_run_all({"EPF_HAZARD_ENFORCE": "1"})
    gates = status["gates"]
    metrics = status["metrics"]

    assert "epf_hazard_ok" in gates
    assert "hazard_ok" in metrics

    # When enforcement is enabled, the gate should match the policy result.
    assert gates["epf_hazard_ok"] == metrics["hazard_ok"]

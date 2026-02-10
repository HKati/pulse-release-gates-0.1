#!/usr/bin/env python3
"""
test_theory_overlay_v0_generator_fixtures.py

Golden fixtures for scripts/generate_theory_overlay_v0.py (stdlib-only).
- Deterministic
- Ensures CI-neutral generator behavior (exit code 0)
- Asserts key semantics:
  - FAIL only when B̃ < 1 (record horizon definition)
  - Zone thresholds can be tuned without shifting FAIL cutoff
  - Invalid thresholds are handled fail-closed (status=FAIL with FAIL_CLOSED in reason)
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Tuple


ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "scripts" / "generate_theory_overlay_v0.py"


def _deep_update(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_update(dst[k], v)
        else:
            dst[k] = v
    return dst


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_case(
    name: str,
    bundle: Dict[str, Any],
    overlay_rh_overrides: Dict[str, Any] | None = None,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        overlay_path = td / "theory_overlay_v0.json"
        bundle_path = td / "bundle.json"

        overlay: Dict[str, Any] = {
            "schema": "theory_overlay_v0",
            "inputs_digest": "fixture",
            "gates_shadow": {},
            "cases": [],
            "evidence": {
                "overlay_source": "fixture",
                "record_horizon_v0": {
                    "thresholds": {
                        "Btilde_green": 100,
                        "Btilde_yellow": 10,
                        "Btilde_red": 1,
                        "sharp_Xi": 8,
                        "sharp_F": 10,
                    }
                },
            },
        }

        if overlay_rh_overrides:
            rh = overlay["evidence"]["record_horizon_v0"]
            if not isinstance(rh, dict):
                rh = {}
                overlay["evidence"]["record_horizon_v0"] = rh
            _deep_update(rh, overlay_rh_overrides)

        _write_json(overlay_path, overlay)
        _write_json(bundle_path, bundle)

        p = subprocess.run(
            [
                sys.executable,
                str(GEN),
                "--in",
                str(overlay_path),
                "--out",
                str(overlay_path),
                "--bundle",
                str(bundle_path),
                "--require-inputs",
            ],
            capture_output=True,
            text=True,
        )

        # Generator must be CI-neutral (always 0); failures are encoded in JSON gate status.
        assert p.returncode == 0, f"[{name}] generator returned {p.returncode}\nstdout:\n{p.stdout}\nstderr:\n{p.stderr}"

        out = _read_json(overlay_path)
        gate = out.get("gates_shadow", {}).get("g_record_horizon_v0", {})
        computed = out.get("evidence", {}).get("record_horizon_v0", {}).get("computed", {})
        return gate, computed, out


def main() -> int:
    base_inputs = {"u": 1.0, "T": 0.01, "v_L": 0.1, "lambda_eff": 1.0}
    base_params = {
        "eta": 1.0,
        "chi": 10.0,
        "ell_0": 1.0,
        "b0_A_bits": 1024,
        "epsilon_budget": 0.2,
        "rho_coding": 0.2,
        "c_m_per_s": 299792458.0,
        "G_m3_per_kg_s2": 6.6743e-11,
    }

    # 1) GREEN / PASS (B̃ >= 100)
    bundle_green = {
        "inputs": dict(base_inputs),
        "params": dict(base_params, M_infty=1e-13),
    }
    gate, comp, _ = _run_case("GREEN_PASS", bundle_green)
    assert gate.get("status") == "PASS", f"[GREEN_PASS] expected PASS, got {gate}"
    assert gate.get("zone") == "GREEN", f"[GREEN_PASS] expected zone GREEN, got {gate.get('zone')}"
    assert comp.get("Btilde_core_units") is not None and comp["Btilde_core_units"] >= 100, "[GREEN_PASS] Btilde < 100"

    # 2) Tuned Btilde_red must NOT shift FAIL cutoff (still FAIL only when B̃ < 1)
    #    Choose B̃ ≈ 3 (< tuned Btilde_red=5) => still PASS, zone RED.
    bundle_red = {
        "inputs": dict(base_inputs),
        "params": dict(base_params, M_infty=1.6e-15),
    }
    gate, comp, _ = _run_case(
        "RED_PASS_TUNED",
        bundle_red,
        overlay_rh_overrides={"thresholds": {"Btilde_red": 5}},
    )
    assert gate.get("status") == "PASS", f"[RED_PASS_TUNED] expected PASS, got {gate}"
    assert gate.get("zone") == "RED", f"[RED_PASS_TUNED] expected zone RED, got {gate.get('zone')}"
    assert comp.get("Btilde_core_units") is not None, "[RED_PASS_TUNED] missing Btilde"
    assert 1 <= comp["Btilde_core_units"] < 10, "[RED_PASS_TUNED] expected 1<=Btilde<10"
    assert comp["Btilde_core_units"] < 5, "[RED_PASS_TUNED] expected Btilde below tuned Btilde_red=5 (advisory only)"

    # 3) POST / FAIL when B̃ < 1 (record horizon)
    bundle_post = {
        "inputs": dict(base_inputs),
        "params": dict(base_params, M_infty=2e-16),
    }
    gate, comp, _ = _run_case("POST_FAIL", bundle_post)
    assert gate.get("status") == "FAIL", f"[POST_FAIL] expected FAIL, got {gate}"
    assert gate.get("zone") == "POST", f"[POST_FAIL] expected zone POST, got {gate.get('zone')}"
    assert comp.get("Btilde_core_units") is not None and comp["Btilde_core_units"] < 1, "[POST_FAIL] expected Btilde < 1"

    # 4) FAIL_CLOSED on malformed thresholds (non-numeric sharp_F)
    bundle_fc = {
        "inputs": dict(base_inputs),
        "params": dict(base_params, M_infty=1e-13),
    }
    gate, _comp, _ = _run_case(
        "FAIL_CLOSED_THRESH",
        bundle_fc,
        overlay_rh_overrides={"thresholds": {"sharp_F": "oops"}},
    )
    assert gate.get("status") == "FAIL", f"[FAIL_CLOSED_THRESH] expected FAIL, got {gate}"
    reason = str(gate.get("reason", ""))
    assert "FAIL_CLOSED" in reason, f"[FAIL_CLOSED_THRESH] expected FAIL_CLOSED in reason, got: {reason}"

    print("OK: all generator golden fixtures passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

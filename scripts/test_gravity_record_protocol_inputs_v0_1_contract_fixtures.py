#!/usr/bin/env python3
"""
Regression fixtures for gravity_record_protocol_inputs_v0_1 contract checker.

Goal:
- Deterministic, fail-closed coverage for producer-facing raw input bundles.
- Ensure common producer errors are caught at the inputs boundary (before builder).

This script executes the contract checker as a subprocess to match real usage.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple


PY = sys.executable
CHECKER = ["scripts/check_gravity_record_protocol_inputs_v0_1_contract.py"]


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(
        json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _deepcopy(x: Any) -> Any:
    return json.loads(json.dumps(x))


def _run_checker(obj: Any) -> Tuple[int, str, str]:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "in.json"
        _write_json(p, obj)

        cmd = [PY, *CHECKER, "--in", str(p)]
        proc = subprocess.run(cmd, text=True, capture_output=True)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _base_bundle_points_only() -> Dict[str, Any]:
    return {
        "source_kind": "demo",
        "provenance": {
            "generated_at_utc": "2026-02-15T00:00:00Z",
            "generator": "scripts/test_gravity_record_protocol_inputs_v0_1_contract_fixtures.py",
        },
        "cases": [
            {
                "case_id": "case_min_points_only",
                "stations": [
                    {"station_id": "A", "r_areal": 100.0, "r_label": "rA"},
                    {"station_id": "B", "r_areal": 200.0, "r_label": "rB"},
                ],
                "profiles": {
                    "lambda": {"points": [{"r": "r0", "value": 1.0}]},
                    "kappa": {"points": [{"r": "r0", "value": 1.0}]},
                },
            }
        ],
    }


def _base_bundle_status_form() -> Dict[str, Any]:
    b = _base_bundle_points_only()
    b["cases"][0]["case_id"] = "case_min_status_form"
    b["cases"][0]["profiles"] = {
        "lambda": {"status": "PASS", "points": [{"r": 0, "value": 1.0, "uncertainty": 0.0, "n": 1}]},
        "kappa": {"status": "PASS", "points": [{"r": 0, "value": 1.0, "uncertainty": 0.0, "n": 1}]},
    }
    return b


def _expect_rc(name: str, got: int, want: int, out: str, err: str) -> str:
    if got == want:
        return ""
    lines = [
        f"[FAIL] {name}: expected rc={want}, got rc={got}",
        "---- stdout ----",
        out or "(empty)",
        "---- stderr ----",
        err or "(empty)",
    ]
    return "\n".join(lines)


def main() -> int:
    cases: List[Tuple[str, Dict[str, Any], int]] = []

    # PASS: minimal valid bundle (points-only encoding)
    cases.append(("pass_min_points_only", _base_bundle_points_only(), 0))

    # PASS: minimal valid bundle (status+points encoding)
    cases.append(("pass_min_status_form", _base_bundle_status_form(), 0))

    # PASS: optional scalar profile present (s)
    b = _base_bundle_points_only()
    b["cases"][0]["profiles"]["s"] = {"points": [{"r": 0, "value": 1.23}]}
    cases.append(("pass_optional_s_profile", b, 0))

    # FAIL: single station (comparative protocol requires >=2)
    b = _base_bundle_points_only()
    b["cases"][0]["stations"] = [{"station_id": "A"}]
    cases.append(("fail_single_station", b, 2))

    # FAIL: duplicate station_id within a case
    b = _base_bundle_points_only()
    b["cases"][0]["stations"] = [{"station_id": "A"}, {"station_id": "A"}]
    cases.append(("fail_duplicate_station_id", b, 2))

    # FAIL: missing required lambda profile
    b = _base_bundle_points_only()
    del b["cases"][0]["profiles"]["lambda"]
    cases.append(("fail_missing_lambda", b, 2))

    # FAIL: lambda value must be > 0
    b = _base_bundle_points_only()
    b["cases"][0]["profiles"]["lambda"]["points"][0]["value"] = 0.0
    cases.append(("fail_lambda_nonpositive", b, 2))

    # FAIL: kappa must be in [0,1]
    b = _base_bundle_points_only()
    b["cases"][0]["profiles"]["kappa"]["points"][0]["value"] = 1.5
    cases.append(("fail_kappa_out_of_range", b, 2))

    # FAIL: profiles must be object
    b = _base_bundle_points_only()
    b["cases"][0]["profiles"] = "oops"  # type: ignore
    cases.append(("fail_profiles_not_object", b, 2))

    # FAIL: bool must not be accepted as numeric (station r_areal)
    b = _base_bundle_points_only()
    b["cases"][0]["stations"][0]["r_areal"] = True  # type: ignore
    cases.append(("fail_bool_in_numeric_station", b, 2))

    # FAIL: bool must not be accepted as numeric (point value)
    b = _base_bundle_points_only()
    b["cases"][0]["profiles"]["lambda"]["points"][0]["value"] = True  # type: ignore
    cases.append(("fail_bool_in_numeric_point", b, 2))

    # FAIL: status PASS with empty points
    b = _base_bundle_status_form()
    b["cases"][0]["profiles"]["lambda"]["points"] = []
    cases.append(("fail_pass_status_empty_points", b, 2))

    # FAIL: unknown top-level key (root additionalProperties=false)
    b = _base_bundle_points_only()
    b["unexpected"] = 1  # type: ignore
    cases.append(("fail_unknown_root_key", b, 2))

    failures: List[str] = []

    for name, obj, want_rc in cases:
        obj2 = _deepcopy(obj)  # protect against accidental mutation bleed
        rc, out, err = _run_checker(obj2)
        msg = _expect_rc(name, rc, want_rc, out, err)
        if msg:
            failures.append(msg)

    if failures:
        print("\n\n".join(failures), file=sys.stderr)
        print(f"[fixtures:gravity_record_protocol_inputs_v0_1] FAIL ({len(failures)} failing cases)", file=sys.stderr)
        return 1

    print(f"[fixtures:gravity_record_protocol_inputs_v0_1] PASS ({len(cases)} cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

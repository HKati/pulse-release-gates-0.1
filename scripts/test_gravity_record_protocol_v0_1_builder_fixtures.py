#!/usr/bin/env python3
"""
Golden-style fixtures for build_gravity_record_protocol_v0_1.py.

This test suite focuses on:
- contract-valid output for well-formed raw inputs
- sanitization of invalid metadata (e.g. source_kind)
- bool rejection in numeric fields (no silent coercion)
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple


PY = sys.executable

BUILDER = ["scripts/build_gravity_record_protocol_v0_1.py"]
CHECKER = ["scripts/check_gravity_record_protocol_v0_1_contract.py"]


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_true(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def run_cmd(cmd: List[str]) -> Tuple[int, str, str]:
    p = subprocess.run([PY] + cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def main() -> int:
    cases: List[Tuple[str, Dict[str, Any], bool]] = []

    # 1) happy path
    cases.append((
        "happy_path_minimal",
        {
            "source_kind": "demo",
            "provenance": {"generated_at_utc": "2026-02-12T00:00:00Z", "generator": "fixture/test"},
            "cases": [
                {
                    "case_id": "ok",
                    "stations": [{"station_id": "A", "r_areal": 1.0}, {"station_id": "B", "r_areal": 2.0}],
                    "profiles": {
                        "lambda": {"status": "PASS", "points": [{"r": 1.0, "value": 0.9}, {"r": 2.0, "value": 1.0}]},
                        "kappa": {"status": "PASS", "points": [{"r": 1.0, "value": 0.8}, {"r": 2.0, "value": 1.0}]}
                    }
                }
            ]
        },
        True,
    ))

    # 2) invalid source_kind -> must fallback to 'missing' but still be contract-valid
    cases.append((
        "invalid_source_kind",
        {
            "source_kind": "foo",
            "provenance": {"generated_at_utc": "2026-02-12T00:00:00Z", "generator": "fixture/test"},
            "cases": [
                {
                    "case_id": "sk",
                    "stations": [{"station_id": "A"}, {"station_id": "B"}],
                    "profiles": {"lambda": {"status": "MISSING"}, "kappa": {"status": "MISSING"}}
                }
            ]
        },
        True,
    ))

    # 3) bools in numeric fields -> must not be coerced; output should remain contract-valid (profiles may degrade to MISSING)
    cases.append((
        "bool_reject_numeric",
        {
            "source_kind": "demo",
            "provenance": {"generated_at_utc": "2026-02-12T00:00:00Z", "generator": "fixture/test"},
            "cases": [
                {
                    "case_id": "bools",
                    "stations": [{"station_id": "A", "r_areal": True}, {"station_id": "B", "r_areal": False}],
                    "profiles": {
                        "lambda": {"status": "PASS", "points": [{"r": 1.0, "value": True}]},
                        "kappa": {"status": "PASS", "points": [{"r": 1.0, "value": False}]}
                    }
                }
            ]
        },
        True,
    ))

    # 4) single-station case -> contract must fail (>=2 stations invariant)
    cases.append((
        "single_station_should_fail_contract",
        {
            "source_kind": "demo",
            "provenance": {"generated_at_utc": "2026-02-12T00:00:00Z", "generator": "fixture/test"},
            "cases": [
                {
                    "case_id": "one",
                    "stations": [{"station_id": "A"}],
                    "profiles": {"lambda": {"status": "MISSING"}, "kappa": {"status": "MISSING"}}
                }
            ]
        },
        False,
    ))

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)

        for name, raw_obj, should_pass in cases:
            raw_path = td_path / f"{name}.raw.json"
            out_path = td_path / f"{name}.out.json"

            _write_json(raw_path, raw_obj)

            rc, _, err = run_cmd(BUILDER + ["--raw", str(raw_path), "--out", str(out_path)])
            assert_true(rc == 0, f"{name}: builder exit != 0: {err}")

            # Contract check
            rc2, _, err2 = run_cmd(CHECKER + ["--in", str(out_path)])
            if should_pass:
                assert_true(rc2 == 0, f"{name}: expected contract PASS, got rc={rc2}: {err2}")

                out = _read_json(out_path)
                # invalid_source_kind: ensure fallback happened
                if name == "invalid_source_kind":
                    assert_true(out.get("source_kind") == "missing", f"{name}: expected source_kind=missing")

                # bool rejection: ensure we did not coerce station r_areal bools into numbers
                if name == "bool_reject_numeric":
                    st0 = (out.get("cases") or [])[0].get("stations")[0]
                    assert_true(st0.get("r_areal") is None, f"{name}: expected r_areal None after bool rejection")

            else:
                assert_true(rc2 != 0, f"{name}: expected contract FAIL, got PASS")

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

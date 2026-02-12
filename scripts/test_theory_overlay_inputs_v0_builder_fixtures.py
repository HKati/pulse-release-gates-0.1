#!/usr/bin/env python3
"""
Regression fixtures for theory_overlay_inputs_v0 bundle builder.

Goals:
- Ensure builder outputs are contract-valid via check_theory_overlay_inputs_v0_contract.py
- Guard against drift:
  - T-or-lnT semantics
  - params must be top-level (inputs.params forbidden)
  - source_kind sanitized/fallback
  - booleans rejected in numeric fields
  - inputs_digest is stable for identical inputs
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

BUILDER = ROOT / "scripts" / "build_theory_overlay_inputs_v0.py"
CHECKER = ROOT / "scripts" / "check_theory_overlay_inputs_v0_contract.py"


def run(cmd: List[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    p = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if p.returncode != 0:
        raise AssertionError(
            "Command failed:\n"
            f"  cmd: {' '.join(cmd)}\n"
            f"  rc: {p.returncode}\n"
            f"  stdout:\n{p.stdout}\n"
            f"  stderr:\n{p.stderr}\n"
        )
    return p


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build_bundle(raw_path: Path, out_path: Path, source_kind: Optional[str] = None) -> Dict[str, Any]:
    cmd = [PY, str(BUILDER), "--raw", str(raw_path), "--out", str(out_path)]
    if source_kind is not None:
        cmd += ["--source-kind", source_kind]
    run(cmd, cwd=ROOT)
    return read_json(out_path)


def check_contract(bundle_path: Path) -> None:
    run([PY, str(CHECKER), "--in", str(bundle_path)], cwd=ROOT)


def assert_true(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        cases: List[Tuple[str, Dict[str, Any]]] = []

        # 1) T-only (valid)
        cases.append((
            "T_only",
            {"source_kind": "pipeline", "inputs": {"u": 1.0, "T": 10.0, "v_L": 1.0, "lambda_eff": 0.1}},
        ))

        # 2) lnT-only (valid)
        cases.append((
            "lnT_only",
            {"source_kind": "pipeline", "inputs": {"u": 1.0, "lnT": 2.302585092994046, "v_L": 1.0, "lambda_eff": 0.1}},
        ))

        # 3) nested inputs.params -> must be promoted to top-level params (and not appear under inputs)
        cases.append((
            "nested_params_promote",
            {
                "source_kind": "manual",
                "inputs": {
                    "u": 1.0,
                    "T": 10.0,
                    "v_L": 1.0,
                    "lambda_eff": 0.1,
                    "params": {"alpha": 123, "beta": "x"},
                },
            },
        ))

        # 4) invalid source_kind in raw -> builder must sanitize/fallback (still contract-valid output)
        cases.append((
            "invalid_source_kind",
            {"source_kind": "foo", "inputs": {"u": 1.0, "T": 10.0, "v_L": 1.0, "lambda_eff": 0.1}},
        ))

        # 5) bool in numeric field -> must be rejected (u becomes null), but lnT numeric keeps contract valid
        cases.append((
            "bool_reject",
            {"source_kind": "pipeline", "inputs": {"u": True, "lnT": 2.3, "v_L": 1.0, "lambda_eff": 0.1}},
        ))

        for name, raw in cases:
            raw_path = tmp / f"{name}.raw.json"
            out_path = tmp / f"{name}.bundle.json"

            write_json(raw_path, raw)
            bundle = build_bundle(raw_path, out_path, source_kind=None)
            check_contract(out_path)

            # Case-specific assertions
            if name == "nested_params_promote":
                assert_true("params" in bundle and isinstance(bundle["params"], dict), "expected top-level params")
                assert_true("params" not in bundle.get("inputs", {}), "inputs.params must not be emitted")

            if name == "invalid_source_kind":
                # Should not emit invalid enum
                sk = bundle.get("source_kind")
                assert_true(sk in ("demo", "pipeline", "manual", "missing"), f"unexpected source_kind: {sk!r}")
                assert_true("raw_errors" in bundle, "expected raw_errors for invalid source_kind")

            if name == "bool_reject":
                inp = bundle.get("inputs") or {}
                assert_true(inp.get("u") is None, "bool must not be coerced into numeric u")
                errs = bundle.get("raw_errors") or []
                assert_true(any("inputs.u" in e and "bool" in e for e in errs), "expected raw_errors for bool in inputs.u")

        # 6) Digest determinism: same inputs => same inputs_digest.sha256 across runs
        raw_path = tmp / "digest.raw.json"
        out1 = tmp / "digest.1.json"
        out2 = tmp / "digest.2.json"
        write_json(raw_path, {"source_kind": "pipeline", "inputs": {"u": 1.0, "T": 10.0, "v_L": 1.0, "lambda_eff": 0.1}})

        b1 = build_bundle(raw_path, out1)
        b2 = build_bundle(raw_path, out2)

        d1 = (b1.get("inputs_digest") or {}).get("sha256")
        d2 = (b2.get("inputs_digest") or {}).get("sha256")
        assert_true(d1 == d2 and isinstance(d1, str), "inputs_digest.sha256 must be stable for identical inputs")

    print("OK: theory_overlay_inputs_v0 builder fixtures")
    return 0


if __name__ == "__main__":
    sys.exit(main())

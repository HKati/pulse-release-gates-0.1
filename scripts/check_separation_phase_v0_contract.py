#!/usr/bin/env python3
"""
check_separation_phase_v0_contract.py

Fail-closed contract check for separation_phase_v0.json
- strict required keys
- enum checks
- type checks
- stable ordering checks (lists must be sorted)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


ALLOWED_STATE = {"FIELD_STABLE", "FIELD_STRAINED", "FIELD_COLLAPSED", "UNKNOWN"}
ALLOWED_ACTION = {"OPEN", "SLOW", "CLOSED"}
ALLOWED_METHOD = {"permutations", "rdsi_proxy", "unknown"}


def die(msg: str) -> None:
    raise SystemExit(f"[separation_phase_v0 CONTRACT FAIL] {msg}")


def is_sorted(xs: List[str]) -> bool:
    return xs == sorted(xs)


def require(cond: bool, msg: str) -> None:
    if not cond:
        die(msg)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    args = ap.parse_args()

    p = Path(args.inp)
    require(p.exists(), f"Missing input file: {p}")

    data: Dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
    require(isinstance(data, dict), "Top-level must be an object")
    require(data.get("schema") == "separation_phase_v0", "schema must be 'separation_phase_v0'")

    inv = data.get("invariants")
    require(isinstance(inv, dict), "invariants must be object")

    os_ = inv.get("order_stability")
    require(isinstance(os_, dict), "invariants.order_stability must be object")
    require(os_.get("method") in ALLOWED_METHOD, "order_stability.method invalid")
    score = os_.get("score")
    require(score is None or isinstance(score, (int, float)), "order_stability.score must be number|null")
    if isinstance(score, (int, float)):
        require(0.0 <= float(score) <= 1.0, "order_stability.score must be within [0,1]")
    require(isinstance(os_.get("n_runs"), int) and os_["n_runs"] >= 0, "order_stability.n_runs must be int>=0")
    ug = os_.get("unstable_gates")
    require(isinstance(ug, list) and all(isinstance(x, str) for x in ug), "unstable_gates must be list[str]")
    require(is_sorted(ug), "unstable_gates must be sorted")

    si = inv.get("separation_integrity")
    require(isinstance(si, dict), "invariants.separation_integrity must be object")
    ds = si.get("decision_stable")
    require(ds is None or isinstance(ds, bool), "separation_integrity.decision_stable must be bool|null")
    require(isinstance(si.get("notes"), str), "separation_integrity.notes must be string")

    pd = inv.get("phase_dependency")
    require(isinstance(pd, dict), "invariants.phase_dependency must be object")
    cgp = pd.get("critical_global_phase")
    require(cgp is None or isinstance(cgp, bool), "phase_dependency.critical_global_phase must be bool|null")

    ts = inv.get("threshold_sensitivity")
    require(isinstance(ts, dict), "invariants.threshold_sensitivity must be object")
    tlg = ts.get("threshold_like_gates")
    require(isinstance(tlg, list) and all(isinstance(x, str) for x in tlg), "threshold_like_gates must be list[str]")
    require(is_sorted(tlg), "threshold_like_gates must be sorted")

    state = data.get("state")
    require(state in ALLOWED_STATE, f"state must be one of {sorted(ALLOWED_STATE)}")

    rec = data.get("recommendation")
    require(isinstance(rec, dict), "recommendation must be object")
    require(rec.get("gate_action") in ALLOWED_ACTION, f"gate_action must be one of {sorted(ALLOWED_ACTION)}")
    require(isinstance(rec.get("rationale"), str) and rec["rationale"].strip(), "rationale must be non-empty string")

    ev = data.get("evidence", [])
    require(isinstance(ev, list), "evidence must be list if present")
    for i, e in enumerate(ev):
        require(isinstance(e, dict), f"evidence[{i}] must be object")
        require(isinstance(e.get("kind"), str), f"evidence[{i}].kind must be string")
        require(isinstance(e.get("message"), str), f"evidence[{i}].message must be string")

    print("[separation_phase_v0 CONTRACT OK]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

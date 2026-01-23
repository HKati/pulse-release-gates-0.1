#!/usr/bin/env python3
"""
separation_phase_adapter_v0.py

CI-neutral diagnostic overlay:
- reads PULSE status.json (baseline)
- optionally reads additional status.json files from permuted runs
- emits separation_phase_v0.json

Design goals:
- deterministic output (stable ordering, no wall-clock timestamps)
- fail-closed semantics inside the overlay (UNKNOWN/CLOSED recommendation if inputs missing)
- does NOT modify or reinterpret normative gate decisions

Note:
Some status.json variants store gate results nested under results.* (e.g. results.security / results.quality).
This adapter therefore supports recursive extraction (flattening) when direct "gates" are not present.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Iterable


ALLOWED_STATE = ("FIELD_STABLE", "FIELD_STRAINED", "FIELD_COLLAPSED", "UNKNOWN")
ALLOWED_ACTION = ("OPEN", "SLOW", "CLOSED")

# Keys that often appear inside a gate-record object, e.g. {"some_gate": {"pass": true, ...}}.
# We do not want these keys to become gate IDs when flattening nested results.* structures.
_META_LEAF_KEYS = {
    "pass",
    "ok",
    "passed",
    "is_pass",
    "success",
    "status",
    "result",
    "outcome",
    "verdict",
    "value",
}


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _as_float01(x: Any) -> Optional[float]:
    try:
        v = float(x)
    except Exception:
        return None
    if v < 0:
        return None
    # if stored as percentage [0..100], normalize
    if v > 1.0 and v <= 100.0:
        v = v / 100.0
    if 0.0 <= v <= 1.0:
        return v
    return None


def _gate_pass_value(obj: Any) -> Optional[bool]:
    """
    Heuristic: supports common shapes:
      - bool
      - dict with pass/ok/passed/status/result
      - string "PASS"/"FAIL"
    """
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, str):
        s = obj.strip().upper()
        if s in ("PASS", "PASSED", "OK", "TRUE", "GREEN", "YES"):
            return True
        if s in ("FAIL", "FAILED", "NO", "FALSE", "RED"):
            return False
        return None
    if isinstance(obj, dict):
        for k in ("pass", "ok", "passed", "is_pass", "success"):
            if k in obj and isinstance(obj[k], bool):
                return obj[k]
        for k in ("status", "result", "outcome", "verdict"):
            if k in obj and isinstance(obj[k], str):
                return _gate_pass_value(obj[k])
    return None


def _iter_leaves(obj: Any, path: Tuple[str, ...] = ()) -> Iterable[Tuple[Tuple[str, ...], Any]]:
    """
    Deterministically yield (path, value) for all non-dict leaves in a nested tree.
    This allows extracting gate-like PASS/FAIL values from nested status results, e.g.:
      results.security.<gate>.(pass|status) or results.quality.<gate> = true/false
    """
    if isinstance(obj, dict):
        for k in sorted(obj.keys(), key=lambda x: str(x)):
            yield from _iter_leaves(obj[k], path + (str(k),))
    else:
        yield path, obj


def _extract_gate_vector(status: Dict[str, Any]) -> Dict[str, bool]:
    """
    Returns a mapping gate_id -> pass_bool.
    Missing/unparseable gates are omitted.

    Priority:
    1) status["gates"] (dict or list) if present
    2) recursively flatten status["gate_results"] / status["results"] / status["checks"]
    """
    out: Dict[str, bool] = {}

    # 1) Preferred: explicit "gates"
    gates = status.get("gates")
    if isinstance(gates, dict):
        for gid in sorted(gates.keys(), key=lambda x: str(x)):
            v = _gate_pass_value(gates[gid])
            if v is not None:
                out[str(gid)] = bool(v)
        return dict(sorted(out.items(), key=lambda kv: kv[0]))

    if isinstance(gates, list):
        for item in gates:
            if not isinstance(item, dict):
                continue
            gid = item.get("id") or item.get("gate_id") or item.get("name")
            if not gid:
                continue
            v = _gate_pass_value(item)
            if v is not None:
                out[str(gid)] = bool(v)
        return dict(sorted(out.items(), key=lambda kv: kv[0]))

    # 2) Fallback: nested results/checks structures (recursive flatten)
    for alt in ("gate_results", "results", "checks"):
        g = status.get(alt)
        if not isinstance(g, dict):
            continue

        tmp: Dict[str, bool] = {}

        for path, raw in _iter_leaves(g):
            if not path:
                continue

            v = _gate_pass_value(raw)
            if v is None:
                continue

            leaf = path[-1]
            # If leaf is a metadata key (pass/status/etc), treat the parent path as the gate id.
            # Otherwise the leaf itself is the gate id (as part of the path).
            gid_path = path[:-1] if (leaf in _META_LEAF_KEYS and len(path) >= 2) else path
            if not gid_path:
                continue

            gid = ".".join(gid_path)

            # Multiple leaves for the same gate record are normal (e.g. pass + status).
            # Prefer the first deterministically (sorted traversal ensures stable choice).
            if gid not in tmp:
                tmp[gid] = bool(v)

        if tmp:
            return dict(sorted(tmp.items(), key=lambda kv: kv[0]))

    return {}


def _extract_decision(status: Dict[str, Any]) -> Optional[str]:
    for k in ("decision", "release_decision", "level"):
        v = status.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _extract_rdsi_proxy(status: Dict[str, Any]) -> Optional[float]:
    metrics = status.get("metrics")
    if not isinstance(metrics, dict):
        return None
    # common candidates
    for k in ("rdsi", "RDSI", "rdsi_mean", "rdsi_score", "release_decision_stability_index"):
        if k in metrics:
            v = _as_float01(metrics.get(k))
            if v is not None:
                return v
    return None


@dataclass(frozen=True)
class RunSummary:
    path: str
    decision: Optional[str]
    gates: Dict[str, bool]


def _summarize_run(path: Path) -> RunSummary:
    st = _read_json(path)
    return RunSummary(
        path=str(path),
        decision=_extract_decision(st),
        gates=_extract_gate_vector(st),
    )


def _order_stability_from_runs(runs: List[RunSummary]) -> Tuple[Optional[float], List[str], List[str]]:
    """
    Returns: score, unstable_gate_ids, threshold_like_gate_ids.
    - Unstable: gate flips between True/False OR missing in some runs.
    - Threshold-like: flips and pass_rate is neither 0 nor 1.
    """
    if len(runs) < 2:
        return None, [], []

    all_gates = sorted({gid for r in runs for gid in r.gates.keys()})
    unstable: List[str] = []
    threshold_like: List[str] = []

    stable_count = 0
    for gid in all_gates:
        vals: List[Optional[bool]] = []
        missing = False
        for r in runs:
            if gid not in r.gates:
                missing = True
                vals.append(None)
            else:
                vals.append(r.gates[gid])

        present_vals = [v for v in vals if v is not None]
        if missing or len(set(present_vals)) != 1:
            unstable.append(gid)
            if present_vals:
                pr = sum(1 for v in present_vals if v) / float(len(present_vals))
                if 0.0 < pr < 1.0:
                    threshold_like.append(gid)
        else:
            stable_count += 1

    score = stable_count / float(len(all_gates)) if all_gates else None
    return score, sorted(unstable), sorted(threshold_like)


def _decision_stability(runs: List[RunSummary]) -> Optional[bool]:
    decisions = [r.decision for r in runs if r.decision is not None]
    if not decisions:
        return None
    return len(set(decisions)) == 1


def _classify_state(score: Optional[float], decision_stable: Optional[bool]) -> Tuple[str, str, str]:
    """
    Returns: state, action, rationale
    """
    if score is None and decision_stable is None:
        return "UNKNOWN", "CLOSED", "No permutation runs and no decision signal; fail-closed diagnostic stance."

    # Conservative: if we have no score but we have a stable decision, we still keep STRAINED (not STABLE)
    if score is None:
        if decision_stable is True:
            return "FIELD_STRAINED", "SLOW", "Decision is stable but order-stability score is unavailable; treat as strained."
        return "UNKNOWN", "CLOSED", "Order-stability score unavailable and decision not provably stable."

    # Score available:
    if score >= 0.98 and decision_stable is not False:
        return "FIELD_STABLE", "OPEN", f"High order-stability score ({score:.3f}); no evidence of global ordering dependence."
    if score >= 0.90:
        return "FIELD_STRAINED", "SLOW", f"Moderate order-stability score ({score:.3f}); potential ordering sensitivity."
    return "FIELD_COLLAPSED", "CLOSED", f"Low order-stability score ({score:.3f}); ordering dependence likely."


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", default="PULSE_safe_pack_v0/artifacts/status.json", help="Baseline status.json path")
    ap.add_argument("--permutation-glob", default="", help="Glob for additional permuted status json files")
    ap.add_argument("--out", default="separation_phase_v0.json", help="Output path")
    ap.add_argument("--run-id", default=os.getenv("GITHUB_RUN_ID", ""), help="Optional run id")
    ap.add_argument("--commit", default=os.getenv("GITHUB_SHA", ""), help="Optional commit SHA")
    args = ap.parse_args()

    baseline_path = Path(args.status)
    evidence: List[Dict[str, str]] = []

    if not baseline_path.exists():
        out = {
            "schema": "separation_phase_v0",
            "meta": {
                "run_id": args.run_id or None,
                "commit": args.commit or None,
                "generator": "scripts/separation_phase_adapter_v0.py",
                "source_date_epoch": int(os.getenv("SOURCE_DATE_EPOCH", "0")) if os.getenv("SOURCE_DATE_EPOCH") else None,
            },
            "inputs": {"status_path": str(baseline_path), "permutation_status_paths": []},
            "invariants": {
                "order_stability": {"method": "unknown", "score": None, "n_runs": 0, "unstable_gates": []},
                "separation_integrity": {"decision_stable": None, "notes": "Missing baseline status.json"},
                "phase_dependency": {"critical_global_phase": None},
                "threshold_sensitivity": {"threshold_like_gates": []},
            },
            "state": "UNKNOWN",
            "recommendation": {"gate_action": "CLOSED", "rationale": "Baseline status.json missing (fail-closed)."},
            "evidence": [{"kind": "error", "message": "Baseline status.json not found."}],
        }
        Path(args.out).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 0

    runs: List[RunSummary] = [_summarize_run(baseline_path)]

    perm_paths: List[str] = []
    if args.permutation_glob.strip():
        paths = sorted(glob.glob(args.permutation_glob))
        for p in paths:
            pp = Path(p)
            if pp.exists():
                runs.append(_summarize_run(pp))
                perm_paths.append(str(pp))

    # Order-stability (primary) or RDSI proxy (fallback)
    score, unstable, threshold_like = _order_stability_from_runs(runs)
    method = "permutations" if score is not None else "unknown"

    if score is None:
        baseline_status = _read_json(baseline_path)
        rdsi = _extract_rdsi_proxy(baseline_status)
        if rdsi is not None:
            score = rdsi
            method = "rdsi_proxy"
            evidence.append(
                {
                    "kind": "note",
                    "message": f"Using RDSI proxy for order-stability: {rdsi:.3f} (no permutation runs).",
                }
            )
        else:
            evidence.append({"kind": "note", "message": "No permutation runs provided and no RDSI proxy found in status.metrics."})

    decision_stable = _decision_stability(runs)
    state, action, rationale = _classify_state(score, decision_stable)

    # Phase dependency: if score is low we treat global phase as critical
    critical_global_phase = None if score is None else (score < 0.90)

    out = {
        "schema": "separation_phase_v0",
        "meta": {
            "run_id": args.run_id or None,
            "commit": args.commit or None,
            "generator": "scripts/separation_phase_adapter_v0.py",
            "source_date_epoch": int(os.getenv("SOURCE_DATE_EPOCH", "0")) if os.getenv("SOURCE_DATE_EPOCH") else None,
        },
        "inputs": {
            "status_path": str(baseline_path),
            "permutation_status_paths": perm_paths,
        },
        "invariants": {
            "order_stability": {
                "method": method,
                "score": score,
                "n_runs": len(runs),
                "unstable_gates": sorted(unstable),
            },
            "separation_integrity": {
                "decision_stable": decision_stable,
                "notes": "Decision-stability computed across provided runs (baseline + optional permutations).",
            },
            "phase_dependency": {"critical_global_phase": critical_global_phase},
            "threshold_sensitivity": {"threshold_like_gates": sorted(threshold_like)},
        },
        "state": state,
        "recommendation": {"gate_action": action, "rationale": rationale},
        "evidence": sorted(evidence, key=lambda x: (x.get("kind", ""), x.get("message", ""))),
    }

    Path(args.out).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

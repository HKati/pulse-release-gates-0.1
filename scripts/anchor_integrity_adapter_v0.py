#!/usr/bin/env python3
"""
anchor_integrity_adapter_v0.py

CI-neutral diagnostic overlay generator:
- reads PULSE status.json (baseline)
- optionally reads Paradox Pages source metadata (if present)
- emits anchor_integrity_v0.json

Design goals:
- deterministic output (stable ordering, no wall-clock timestamps)
- fail-closed semantics INSIDE the overlay (UNKNOWN + SILENCE/CLOSED if inputs missing)
- does NOT modify or reinterpret normative gate decisions
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ALLOWED_STATE = {"ANCHORED", "PARTIAL", "ANCHOR_LOST", "UNKNOWN"}
ALLOWED_RESPONSE_MODE = {"ANSWER", "BOUNDARY", "ASK_FOR_ANCHOR", "SILENCE"}
ALLOWED_GATE_ACTION = {"OPEN", "SLOW", "CLOSED"}
ALLOWED_RISK = {"low", "medium", "high"}


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _safe_read_json(path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if not path.exists():
        return None, f"Missing file: {path}"
    try:
        return _read_json(path), None
    except Exception as e:
        return None, f"Failed to parse JSON ({path}): {e}"


def _extract_bool_gate(g: Any) -> Optional[bool]:
    """
    Heuristic: supports common shapes:
      - bool
      - dict with pass/ok/passed/status/result/outcome
      - string "PASS"/"FAIL"
    """
    if isinstance(g, bool):
        return g
    if isinstance(g, str):
        s = g.strip().upper()
        if s in ("PASS", "PASSED", "OK", "TRUE", "GREEN"):
            return True
        if s in ("FAIL", "FAILED", "NO", "FALSE", "RED"):
            return False
        return None
    if isinstance(g, dict):
        for k in ("pass", "ok", "passed", "is_pass", "success"):
            if k in g and isinstance(g[k], bool):
                return g[k]
        for k in ("status", "result", "outcome"):
            if k in g and isinstance(g[k], str):
                return _extract_bool_gate(g[k])
    return None


def _walk_gate_like_leaves(obj: Any, path: str, out: Dict[str, Any]) -> None:
    """
    Recursively collect "gate-like" leaves from nested dict/list structures.

    - If a dict is directly parseable as a gate result (via _extract_bool_gate),
      it is treated as a leaf.
    - Otherwise recurse into dict keys.
    - Lists are traversed; if an item is a dict with an id-like field, prefer that id.
    """
    if isinstance(obj, dict):
        # Treat dict as leaf if it looks like a gate result
        if _extract_bool_gate(obj) is not None:
            out[path] = obj
            return
        for k in sorted(obj.keys(), key=lambda x: str(x)):
            v = obj[k]
            kp = f"{path}.{k}" if path else str(k)
            _walk_gate_like_leaves(v, kp, out)
        return

    if isinstance(obj, list):
        for i, item in enumerate(obj):
            # If list element is a dict with an id/name, bind it deterministically
            if isinstance(item, dict):
                gid = item.get("id") or item.get("gate_id") or item.get("name")
                if isinstance(gid, str) and gid.strip():
                    kp = f"{path}.{gid}" if path else gid.strip()
                    out[kp] = item
                    continue
            kp = f"{path}[{i}]" if path else f"[{i}]"
            _walk_gate_like_leaves(item, kp, out)
        return

    # Primitive leaf: may be bool or PASS/FAIL string
    out[path] = obj


def _last_token(p: str) -> str:
    # Convert "results.security.q1_grounded_ok" -> "q1_grounded_ok"
    # Convert "foo[0]" -> "foo"
    t = p.split(".")[-1]
    if "[" in t:
        t = t.split("[", 1)[0]
    return t.strip()


def _extract_gates(status: Dict[str, Any]) -> Dict[str, bool]:
    """
    Returns mapping gate_id -> pass_bool.

    Supports:
      - status["gates"] as dict
      - status["gates"] as list of {id/gate_id/name, ...}
      - fallback variants: status["gate_results"], status["results"], status["checks"]
        including nested results.* structures.

    Deterministic: stable ordering, first-wins for duplicate leaf ids (sorted by path).
    """
    out: Dict[str, bool] = {}

    # 1) Primary: status.gates
    gates = status.get("gates")

    if isinstance(gates, dict):
        for gid in sorted(gates.keys(), key=lambda x: str(x)):
            v = _extract_bool_gate(gates[gid])
            if v is not None:
                out[str(gid)] = bool(v)
        return out

    if isinstance(gates, list):
        tmp: Dict[str, bool] = {}
        for item in gates:
            if not isinstance(item, dict):
                continue
            gid = item.get("id") or item.get("gate_id") or item.get("name")
            if not isinstance(gid, str) or not gid.strip():
                continue
            v = _extract_bool_gate(item)
            if v is not None:
                tmp[gid.strip()] = bool(v)
        return dict(sorted(tmp.items(), key=lambda kv: kv[0]))

    # 2) Fallback: gate_results / results / checks (possibly nested)
    for alt in ("gate_results", "results", "checks"):
        g = status.get(alt)
        if not isinstance(g, (dict, list)):
            continue

        leaves: Dict[str, Any] = {}
        _walk_gate_like_leaves(g, alt, leaves)

        # Deterministic pick: sort by path, then map leaf id (= last token) to bool.
        for pth in sorted(leaves.keys()):
            leaf_id = _last_token(pth)
            if not leaf_id:
                continue
            if leaf_id in out:
                continue  # first wins, deterministic due to sorted paths
            v = _extract_bool_gate(leaves[pth])
            if v is not None:
                out[leaf_id] = bool(v)

        if out:
            return dict(sorted(out.items(), key=lambda kv: kv[0]))

    return out


def _anchor_signals_from_status(status: Dict[str, Any]) -> Tuple[Optional[bool], Optional[float], List[Dict[str, str]]]:
    """
    Map existing PULSE signals into an "anchor integrity" proxy.

    IMPORTANT: this is diagnostic-only. We do NOT claim truth.
    We only infer whether there are external/grounding-like signals present.

    Returns: anchor_presence, anchor_coverage, evidence_list
    """
    evidence: List[Dict[str, str]] = []
    gates = _extract_gates(status)

    # Heuristic candidates: use gates that typically imply groundedness/consistency.
    candidates = [
        ("q1_grounded_ok", "Groundedness gate"),
        ("q2_consistency_ok", "Consistency gate"),
        ("q3_fairness_ok", "Fairness gate (weak anchor proxy)"),
        ("q4_slo_ok", "SLO gate (weak anchor proxy)"),
        ("external_all_pass", "External detector aggregate (weak anchor proxy)"),
    ]

    present: List[bool] = []
    used = 0

    for gid, label in candidates:
        if gid not in gates:
            continue
        used += 1
        present.append(bool(gates[gid]))
        evidence.append({"kind": "signal", "message": f"{label}: {gid}={gates[gid]}"})

    if used == 0:
        evidence.append({"kind": "note", "message": "No anchor-proxy gates found in status; treating anchor as unknown."})
        return None, None, evidence

    # anchor_presence: if we have any signal and at least one anchor-ish gate is True.
    anchor_presence = any(present)

    # coverage: fraction of candidate signals that are True (bounded [0..1])
    anchor_coverage = sum(1 for v in present if v) / float(len(present)) if present else None

    evidence.append({"kind": "note", "message": f"Anchor coverage computed from {len(present)} gate signals."})
    return anchor_presence, anchor_coverage, evidence


def _loop_risk_from_paradox_source(paradox_source: Optional[Dict[str, Any]]) -> Tuple[Optional[str], List[Dict[str, str]]]:
    """
    Minimal v0: if Paradox is present, we mark loop_risk as 'low' by default,
    but record source metadata. We avoid making claims without the diagram.

    Future: bind to paradox_field_v0 / edges and compute loop/self-reference indicators.
    """
    evidence: List[Dict[str, str]] = []
    if not paradox_source:
        return None, evidence

    src = paradox_source.get("source")
    transitions_dir = paradox_source.get("transitions_dir")
    if isinstance(src, str) and src:
        evidence.append({"kind": "paradox", "message": f"Paradox source present: source={src}"})
    if isinstance(transitions_dir, str) and transitions_dir:
        evidence.append({"kind": "paradox", "message": f"Paradox transitions_dir={transitions_dir}"})

    # v0 conservative stance: we don't have loop computation yet
    return "low", evidence


def _classify(anchor_presence: Optional[bool], anchor_coverage: Optional[float], loop_risk: Optional[str]) -> Tuple[str, str, str, str]:
    """
    Returns:
      state, response_mode, gate_action, rationale

    Fail-closed:
      - if anchor is unknown -> UNKNOWN + SILENCE + CLOSED
      - if anchor is explicitly missing -> ANCHOR_LOST + SILENCE + CLOSED
    """
    if anchor_presence is None and anchor_coverage is None:
        return (
            "UNKNOWN",
            "SILENCE",
            "CLOSED",
            "Anchor signals unavailable; fail-closed diagnostic stance (prefer silence).",
        )

    if anchor_presence is False:
        return (
            "ANCHOR_LOST",
            "SILENCE",
            "CLOSED",
            "No anchor signals detected; treat as anchor loss (prefer silence over speculation).",
        )

    # anchor_presence True:
    cov = anchor_coverage if anchor_coverage is not None else 0.0

    # If loop risk is high later, we'd go to BOUNDARY/SLOW; for now keep conservative thresholds.
    if cov >= 0.75:
        return (
            "ANCHORED",
            "ANSWER",
            "OPEN",
            f"Anchor signals present with high coverage ({cov:.3f}); proceed with normal answering.",
        )
    return (
        "PARTIAL",
        "BOUNDARY",
        "SLOW",
        f"Anchor signals present but incomplete coverage ({cov:.3f}); proceed with boundary/ask-for-anchor behavior.",
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", default="PULSE_safe_pack_v0/artifacts/status.json", help="Baseline status.json path")
    ap.add_argument("--paradox-source", default="_site/paradox/core/v0/source_v0.json", help="Optional Paradox source metadata JSON")
    ap.add_argument("--out", default="anchor_integrity_v0.json", help="Output path")
    ap.add_argument("--run-id", default=os.getenv("GITHUB_RUN_ID", ""), help="Optional run id")
    ap.add_argument("--commit", default=os.getenv("GITHUB_SHA", ""), help="Optional commit SHA")
    args = ap.parse_args()

    status_path = Path(args.status)
    paradox_path = Path(args.paradox_source) if args.paradox_source else None
    scanned_paths: List[str] = [str(status_path)]
    if paradox_path is not None:
        scanned_paths.append(str(paradox_path))

    evidence: List[Dict[str, str]] = []

    status, err = _safe_read_json(status_path)
    paradox_source: Optional[Dict[str, Any]] = None

    if err:
        out = {
            "schema": "anchor_integrity_v0",
            "meta": {
                "run_id": args.run_id or None,
                "commit": args.commit or None,
                "generator": "scripts/anchor_integrity_adapter_v0.py",
                "source_date_epoch": int(os.getenv("SOURCE_DATE_EPOCH", "0")) if os.getenv("SOURCE_DATE_EPOCH") else None,
            },
            "inputs": {
                "status_path": str(status_path),
                "paradox_source_path": str(paradox_path) if paradox_path is not None else None,
                "scanned_paths": scanned_paths,
            },
            "invariants": {
                "anchor_presence": None,
                "anchor_coverage": None,
                "loop_risk": None,
                "contradiction_risk": None,
                "notes": "Missing or unreadable status.json (fail-closed).",
            },
            "state": "UNKNOWN",
            "recommendation": {
                "response_mode": "SILENCE",
                "gate_action": "CLOSED",
                "rationale": f"Baseline status.json missing/unreadable: {err}",
            },
            "evidence": [{"kind": "error", "message": err}],
        }
        Path(args.out).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 0

    # Optional paradox source metadata
    if paradox_path is not None:
        px, perr = _safe_read_json(paradox_path)
        if perr:
            evidence.append({"kind": "note", "message": f"Paradox source not available: {perr}"})
        elif isinstance(px, dict):
            paradox_source = px

    anchor_presence, anchor_coverage, ev_status = _anchor_signals_from_status(status)
    evidence.extend(ev_status)

    loop_risk, ev_paradox = _loop_risk_from_paradox_source(paradox_source)
    evidence.extend(ev_paradox)

    # v0: contradiction_risk not computed (reserved)
    contradiction_risk = None

    state, response_mode, gate_action, rationale = _classify(anchor_presence, anchor_coverage, loop_risk)

    out = {
        "schema": "anchor_integrity_v0",
        "meta": {
            "run_id": args.run_id or None,
            "commit": args.commit or None,
            "generator": "scripts/anchor_integrity_adapter_v0.py",
            "source_date_epoch": int(os.getenv("SOURCE_DATE_EPOCH", "0")) if os.getenv("SOURCE_DATE_EPOCH") else None,
        },
        "inputs": {
            "status_path": str(status_path),
            "paradox_source_path": str(paradox_path) if paradox_path is not None else None,
            "scanned_paths": scanned_paths,
        },
        "invariants": {
            "anchor_presence": anchor_presence,
            "anchor_coverage": anchor_coverage,
            "loop_risk": loop_risk,
            "contradiction_risk": contradiction_risk,
            "notes": "Anchor integrity is a diagnostic overlay (Hallucination = Anchor Loss).",
        },
        "state": state,
        "recommendation": {
            "response_mode": response_mode,
            "gate_action": gate_action,
            "rationale": rationale,
        },
        "evidence": sorted(evidence, key=lambda x: (x.get("kind", ""), x.get("message", ""))),
    }

    Path(args.out).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

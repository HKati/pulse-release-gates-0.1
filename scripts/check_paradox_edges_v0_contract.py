#!/usr/bin/env python3
"""
check_paradox_edges_v0_contract.py — fail-closed contract checker for paradox_edges_v0.jsonl.

Validates:
- JSONL parse robustness
- deterministic ordering (severity, type, edge_id)
- uniqueness of edge_id
- required fields
- optional run_context validation + file-level consistency
- optional link/type validation against atoms when --atoms is provided
- cross-check: edge src/dst must match linked tension atom evidence when --atoms is provided
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, Optional, Tuple


SEVERITY_ORDER = {"crit": 0, "warn": 1, "info": 2}

EDGE_TYPE_SPECS: Dict[str, Dict[str, str]] = {
    "gate_metric_tension": {
        "src_atom_type": "gate_flip",
        "dst_atom_type": "metric_delta",
        "tension_atom_type": "gate_metric_tension",
    },
    "gate_overlay_tension": {
        "src_atom_type": "gate_flip",
        "dst_atom_type": "overlay_change",
        "tension_atom_type": "gate_overlay_tension",
    },
}


def die(msg: str, code: int = 2) -> None:
    raise SystemExit(f"[edges-contract] {msg}")


def _is_hex(s: Any, n: int) -> bool:
    if not isinstance(s, str) or len(s) != n:
        return False
    try:
        int(s, 16)
        return True
    except Exception:
        return False


def _severity_rank(label: Any) -> int:
    if not isinstance(label, str):
        return 99
    return SEVERITY_ORDER.get(label.strip(), 99)


def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_atoms(atoms_path: str) -> Dict[str, Dict[str, Any]]:
    if not atoms_path:
        return {}
    if not os.path.isfile(atoms_path):
        die(f"--atoms not found: {atoms_path}")

    obj = _read_json(atoms_path)
    root = obj.get("paradox_field_v0", obj) if isinstance(obj, dict) else {}
    atoms = root.get("atoms", []) if isinstance(root, dict) else []
    if not isinstance(atoms, list):
        die(f"atoms file malformed: expected list at paradox_field_v0.atoms: {atoms_path}")

    by_id: Dict[str, Dict[str, Any]] = {}
    for a in atoms:
        if not isinstance(a, dict):
            continue
        aid = a.get("atom_id")
        atype = a.get("type")
        if not isinstance(aid, str) or not aid.strip():
            continue
        if not isinstance(atype, str) or not atype.strip():
            continue
        by_id[aid] = a
    return by_id


def _edge_key(edge: Dict[str, Any]) -> Tuple[int, str, str]:
    sev = _severity_rank(edge.get("severity"))
    et = edge.get("type")
    eid = edge.get("edge_id")
    return (sev, str(et or ""), str(eid or ""))


def _normalize_run_context(run_ctx: Any, line_no: int) -> Optional[Dict[str, str]]:
    """
    run_context is optional. If present:
      - must be dict
      - must contain run_pair_id as non-empty string
      - known sha1 fields, if present, must be 40-hex sha1
      - returns a normalized dict of stable keys for file-level consistency checks
    """
    if run_ctx is None:
        return None
    if not isinstance(run_ctx, dict):
        die(f"line {line_no}: run_context must be an object/dict when present")

    rpid = run_ctx.get("run_pair_id")
    if not isinstance(rpid, str) or not rpid.strip():
        die(f"line {line_no}: run_context.run_pair_id must be a non-empty string when run_context is present")
    rpid = rpid.strip()

    sha1_keys = [
        "status_sha1",
        "g_field_sha1",
        "transitions_gate_csv_sha1",
        "transitions_metric_csv_sha1",
        "transitions_overlay_json_sha1",
        "transitions_json_sha1",
    ]

    norm: Dict[str, str] = {"run_pair_id": rpid}

    for k in sha1_keys:
        v = run_ctx.get(k)
        if v is None:
            continue
        if not isinstance(v, str) or not v.strip():
            die(f"line {line_no}: run_context.{k} must be a non-empty string if present")
        vv = v.strip()
        if not _is_hex(vv, 40):
            die(f"line {line_no}: run_context.{k} must be a 40-hex sha1 if present")
        norm[k] = vv

    return norm


def _tension_expected_src_dst(edge_type: str, tension_atom: Dict[str, Any], line_no: int) -> Tuple[str, str]:
    ev = tension_atom.get("evidence")
    if not isinstance(ev, dict):
        die(f"line {line_no}: tension atom evidence must be an object/dict")

    has_src_alias = "src_atom_id" in ev
    has_dst_alias = "dst_atom_id" in ev
    if has_src_alias or has_dst_alias:
        src = ev.get("src_atom_id")
        dst = ev.get("dst_atom_id")
        if not isinstance(src, str) or not src.strip():
            die(f"line {line_no}: tension evidence.src_atom_id must be a non-empty string when present")
        if not isinstance(dst, str) or not dst.strip():
            die(f"line {line_no}: tension evidence.dst_atom_id must be a non-empty string when present")
        return src.strip(), dst.strip()

    gate_id = ev.get("gate_atom_id")
    if not isinstance(gate_id, str) or not gate_id.strip():
        die(f"line {line_no}: tension evidence.gate_atom_id must be a non-empty string")
    gate_id = gate_id.strip()

    if edge_type == "gate_metric_tension":
        met_id = ev.get("metric_atom_id")
        if not isinstance(met_id, str) or not met_id.strip():
            die(f"line {line_no}: tension evidence.metric_atom_id must be a non-empty string")
        return gate_id, met_id.strip()

    if edge_type == "gate_overlay_tension":
        over_id = ev.get("overlay_atom_id")
        if not isinstance(over_id, str) or not over_id.strip():
            die(f"line {line_no}: tension evidence.overlay_atom_id must be a non-empty string")
        return gate_id, over_id.strip()

    die(f"line {line_no}: unsupported edge type for tension cross-check: {edge_type}")
    raise SystemExit(2)


def main() -> int:
    ap = argparse.ArgumentParser(description="Contract check for paradox_edges_v0.jsonl (JSONL).")
    ap.add_argument("--in", dest="in_path", required=True, help="Path to paradox_edges_v0.jsonl")
    ap.add_argument(
        "--atoms",
        dest="atoms_path",
        default="",
        help="Optional path to paradox_field_v0.json for link/type validation",
    )
    args = ap.parse_args()

    if not os.path.isfile(args.in_path):
        die(f"file not found: {args.in_path}")

    atoms_by_id = _load_atoms(args.atoms_path) if args.atoms_path else {}

    seen_edge_ids = set()
    prev_key: Optional[Tuple[int, str, str]] = None
    edges_count = 0

    # run_context consistency (file-level)
    expected_run_context: Optional[Dict[str, str]] = None
    saw_run_context = False
    saw_missing_run_context = False

    with open(args.in_path, "r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue

            try:
                edge = json.loads(line)
            except Exception as e:
                die(f"line {line_no}: invalid JSONL (json decode error): {e}")

            if not isinstance(edge, dict):
                die(f"line {line_no}: edge must be a JSON object")

            edge_id = edge.get("edge_id")
            edge_type = edge.get("type")
            src_atom_id = edge.get("src_atom_id")
            dst_atom_id = edge.get("dst_atom_id")
            severity = edge.get("severity")
            rule = edge.get("rule")

            if not isinstance(edge_id, str) or not _is_hex(edge_id, 16):
                die(f"line {line_no}: edge_id must be 16-hex string")

            if edge_id in seen_edge_ids:
                die(f"line {line_no}: duplicate edge_id: {edge_id}")
            seen_edge_ids.add(edge_id)

            if not isinstance(edge_type, str) or not edge_type.strip():
                die(f"line {line_no}: type must be a non-empty string")
            edge_type = edge_type.strip()

            if edge_type not in EDGE_TYPE_SPECS:
                die(f"line {line_no}: unknown edge type '{edge_type}' (v0 allowlist: {sorted(EDGE_TYPE_SPECS)})")

            if not isinstance(src_atom_id, str) or not src_atom_id.strip():
                die(f"line {line_no}: src_atom_id must be a non-empty string")
            src_atom_id = src_atom_id.strip()

            if not isinstance(dst_atom_id, str) or not dst_atom_id.strip():
                die(f"line {line_no}: dst_atom_id must be a non-empty string")
            dst_atom_id = dst_atom_id.strip()

            if not isinstance(severity, str) or severity not in SEVERITY_ORDER:
                die(f"line {line_no}: severity must be one of {sorted(SEVERITY_ORDER)}")

            if not isinstance(rule, str) or not rule.strip():
                die(f"line {line_no}: rule must be a non-empty string")

            tension_atom_id = edge.get("tension_atom_id")
            if tension_atom_id is None:
                die(f"line {line_no}: missing tension_atom_id (required for v0 tension edges)")
            if not isinstance(tension_atom_id, str) or not _is_hex(tension_atom_id, 12):
                die(f"line {line_no}: tension_atom_id must be 12-hex string")
            tension_atom_id = tension_atom_id.strip()

            # Deterministic ordering
            k = _edge_key(edge)
            if prev_key is not None and k < prev_key:
                die(
                    f"line {line_no}: edges not in deterministic order "
                    f"(expected non-decreasing by (severity,type,edge_id)); got {k} after {prev_key}"
                )
            prev_key = k

            # run_context validation + file-level consistency
            rc_norm = _normalize_run_context(edge.get("run_context"), line_no)
            if rc_norm is None:
                saw_missing_run_context = True
            else:
                saw_run_context = True
                if expected_run_context is None:
                    expected_run_context = rc_norm
                elif rc_norm != expected_run_context:
                    die(
                        f"line {line_no}: run_context mismatch across edges; "
                        f"expected {expected_run_context!r}, got {rc_norm!r}"
                    )

            # If atoms provided: link/type validation + cross-check vs tension evidence
            if atoms_by_id:
                spec = EDGE_TYPE_SPECS[edge_type]

                def _must_atom(aid: str, what: str) -> Dict[str, Any]:
                    a = atoms_by_id.get(aid)
                    if not isinstance(a, dict):
                        die(f"line {line_no}: {what} atom_id not found in atoms: {aid}")
                    return a

                src_atom = _must_atom(src_atom_id, "src")
                dst_atom = _must_atom(dst_atom_id, "dst")
                tens_atom = _must_atom(tension_atom_id, "tension")

                src_type = src_atom.get("type")
                dst_type = dst_atom.get("type")
                tens_type = tens_atom.get("type")

                if src_type != spec["src_atom_type"]:
                    die(
                        f"line {line_no}: src_atom_id type mismatch for '{edge_type}': "
                        f"expected '{spec['src_atom_type']}', got '{src_type}'"
                    )

                if dst_type != spec["dst_atom_type"]:
                    die(
                        f"line {line_no}: dst_atom_id type mismatch for '{edge_type}': "
                        f"expected '{spec['dst_atom_type']}', got '{dst_type}'"
                    )

                if tens_type != spec["tension_atom_type"]:
                    die(
                        f"line {line_no}: tension_atom_id type mismatch for '{edge_type}': "
                        f"expected '{spec['tension_atom_type']}', got '{tens_type}'"
                    )

                exp_src, exp_dst = _tension_expected_src_dst(edge_type, tens_atom, line_no)
                if exp_src != src_atom_id or exp_dst != dst_atom_id:
                    die(
                        f"line {line_no}: edge src/dst mismatch vs tension_atom_id evidence; "
                        f"expected ({exp_src},{exp_dst}), got ({src_atom_id},{dst_atom_id})"
                    )

            edges_count += 1

    # Mixed presence is not allowed: either all edges have run_context or none do.
    if saw_run_context and saw_missing_run_context:
        die("mixed run_context presence across edges; include run_context on all edges or none")

    print(f"[edges-contract] OK (edges={edges_count})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        raise SystemExit(0)


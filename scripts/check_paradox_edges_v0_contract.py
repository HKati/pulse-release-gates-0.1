
#!/usr/bin/env python3
"""
check_paradox_edges_v0_contract.py — fail-closed contract checker for paradox_edges_v0.jsonl.

This validator is for the *edges* layer (JSONL), and optionally checks link integrity
against paradox_field_v0.json (atoms).

Why this exists:
- docs + CI reference `paradox_edges_v0.jsonl`
- edges are JSONL (1 JSON object per line), not a single JSON object
- we must preserve:
  - JSONL parsing robustness
  - deterministic ordering checks
  - uniqueness checks
  - link/type validation against atoms when `--atoms` is provided

Usage:
  python scripts/check_paradox_edges_v0_contract.py --in out/paradox_edges_v0.jsonl --atoms out/paradox_field_v0.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, Optional, Tuple


SEVERITY_ORDER = {"crit": 0, "warn": 1, "info": 2}

# v0 edge types and their expected atom link types
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
    for i, a in enumerate(atoms):
        if not isinstance(a, dict):
            continue
        aid = a.get("atom_id")
        atype = a.get("type")
        if not isinstance(aid, str) or not aid.strip():
            continue
        if not isinstance(atype, str) or not atype.strip():
            continue
        # last wins, but should be unique anyway
        by_id[aid] = a
    return by_id


def _edge_key(edge: Dict[str, Any]) -> Tuple[int, str, str]:
    sev = _severity_rank(edge.get("severity"))
    et = edge.get("type")
    eid = edge.get("edge_id")
    return (sev, str(et or ""), str(eid or ""))


def _validate_run_context(run_ctx: Any, line_no: int) -> Optional[str]:
    """
    Optional but fail-closed if present.
    Returns run_pair_id if present, else None.

    Contract rules (v0):
    - run_context may be omitted (legacy outputs)
    - if present, must be a dict
    - keys + values must be non-empty strings
    - run_pair_id is required and must be a non-empty string (format is intentionally NOT constrained)
    - sha1 fields (if present) must be 40-hex sha1
    """
    if run_ctx is None:
        return None
    if not isinstance(run_ctx, dict):
        die(f"line {line_no}: run_context must be an object if present")

    # keys + values must be non-empty strings (run_context is for stable identifiers/hashes)
    for k, v in run_ctx.items():
        if not isinstance(k, str) or not k.strip():
            die(f"line {line_no}: run_context keys must be non-empty strings")
        if not isinstance(v, str) or not v.strip():
            die(f"line {line_no}: run_context.{k} must be a non-empty string")

    rpid = run_ctx.get("run_pair_id")
    if not isinstance(rpid, str) or not rpid.strip():
        die(f"line {line_no}: run_context.run_pair_id must be a non-empty string if run_context is present")
    rpid = rpid.strip()

    # Optional sha1s should look like sha1.
    def _opt_sha1(k: str) -> None:
        v = run_ctx.get(k)
        if v is None:
            return
        if not isinstance(v, str) or not _is_hex(v, 40):
            die(f"line {line_no}: run_context.{k} must be a 40-hex sha1 if present")

    _opt_sha1("status_sha1")
    _opt_sha1("g_field_sha1")
    _opt_sha1("transitions_gate_csv_sha1")
    _opt_sha1("transitions_metric_csv_sha1")
    _opt_sha1("transitions_overlay_json_sha1")
    _opt_sha1("transitions_json_sha1")

    return rpid


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

    # run_context global consistency (optional but fail-closed if present anywhere)
    run_context_seen_any = False
    run_context_seen_missing = False
    run_pair_id_seen: Optional[str] = None

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

            # ---- Required fields
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

            if edge_type not in EDGE_TYPE_SPECS:
                die(f"line {line_no}: unknown edge type '{edge_type}' (v0 allowlist: {sorted(EDGE_TYPE_SPECS)})")

            if not isinstance(src_atom_id, str) or not src_atom_id.strip():
                die(f"line {line_no}: src_atom_id must be a non-empty string")

            if not isinstance(dst_atom_id, str) or not dst_atom_id.strip():
                die(f"line {line_no}: dst_atom_id must be a non-empty string")

            if not isinstance(severity, str) or severity not in SEVERITY_ORDER:
                die(f"line {line_no}: severity must be one of {sorted(SEVERITY_ORDER)}")

            if not isinstance(rule, str) or not rule.strip():
                die(f"line {line_no}: rule must be a non-empty string")

            # ---- Optional but strongly expected for tension edges
            tension_atom_id = edge.get("tension_atom_id")
            if tension_atom_id is None:
                die(f"line {line_no}: missing tension_atom_id (required for v0 tension edges)")
            if not isinstance(tension_atom_id, str) or not _is_hex(tension_atom_id, 12):
                die(f"line {line_no}: tension_atom_id must be 12-hex string")

            # ---- Deterministic ordering
            k = _edge_key(edge)
            if prev_key is not None and k < prev_key:
                die(
                    f"line {line_no}: edges not in deterministic order "
                    f"(expected non-decreasing by (severity,type,edge_id)); got {k} after {prev_key}"
                )
            prev_key = k

            # ---- Optional run_context validation + global consistency
            rpid = _validate_run_context(edge.get("run_context"), line_no)
            if rpid is None:
                run_context_seen_missing = True
            else:
                run_context_seen_any = True
                if run_pair_id_seen is None:
                    run_pair_id_seen = rpid
                elif rpid != run_pair_id_seen:
                    die(
                        f"line {line_no}: run_context.run_pair_id mismatch: "
                        f"expected {run_pair_id_seen!r}, got {rpid!r}"
                    )

            # ---- Link/type validation against atoms (if provided)
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

            edges_count += 1

    # If any edge has run_context, all edges must have it.
    if run_context_seen_any and run_context_seen_missing:
        die("mixed run_context presence: some edges have run_context while others do not")

    print(f"[edges-contract] OK (edges={edges_count})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        # allow piping to head etc.
        raise SystemExit(0)

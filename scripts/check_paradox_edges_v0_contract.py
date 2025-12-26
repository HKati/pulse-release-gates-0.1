#!/usr/bin/env python3
"""
check_paradox_edges_v0_contract.py — fail-closed contract checker for paradox_edges_v0.jsonl.

Validates:
- JSONL parsing robustness
- deterministic ordering (severity, type, edge_id)
- uniqueness (edge_id)
- required fields + allowlisted edge types
- optional run_context validation:
  - backwards compatible: run_context may be missing
  - but if present:
    - must contain non-empty run_pair_id
    - must be consistent across the whole JSONL file on exporter-allowed keys
    - disallow mixing edges with/without run_context in the same file

Optional (recommended):
- when --atoms is provided, validate:
  - src/dst/tension atom ids exist
  - src/dst/tension atom types match spec
  - edge endpoints match the tension atom's evidence links (cross-check)

Usage:
  python scripts/check_paradox_edges_v0_contract.py \
    --in out/paradox_edges_v0.jsonl \
    --atoms out/paradox_field_v0.json
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

# Must match export_paradox_edges_v0._build_run_context() allowlist behavior.
RUN_CONTEXT_ALLOWED_KEYS = {
    "run_pair_id",
    "status_sha1",
    "g_field_sha1",
    "transitions_json_sha1",
    "transitions_gate_csv_sha1",
    "transitions_metric_csv_sha1",
    "transitions_overlay_json_sha1",
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
        by_id[aid.strip()] = a
    return by_id


def _edge_key(edge: Dict[str, Any]) -> Tuple[int, str, str]:
    sev = _severity_rank(edge.get("severity"))
    et = edge.get("type")
    eid = edge.get("edge_id")
    return (sev, str(et or ""), str(eid or ""))


def _validate_run_context(run_ctx: Any, line_no: int) -> Dict[str, str]:
    """
    Validate run_context if present and return a normalized subset aligned with
    the exporter allowlist.
    """
    if run_ctx is None:
        return {}

    if not isinstance(run_ctx, dict):
        die(f"line {line_no}: run_context must be an object if present")

    # run_pair_id is required if run_context exists (format intentionally not restricted to hex)
    rpid = run_ctx.get("run_pair_id")
    if not isinstance(rpid, str) or not rpid.strip():
        die(f"line {line_no}: run_context.run_pair_id must be a non-empty string if run_context is present")

    # Optional sha1 keys: if present must look like sha1 (40 hex)
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

    # Normalize to exporter-allowed keys (ignore extras to avoid brittleness)
    norm: Dict[str, str] = {}
    for k in RUN_CONTEXT_ALLOWED_KEYS:
        v = run_ctx.get(k)
        if isinstance(v, str) and v.strip():
            norm[k] = v.strip()

    if "run_pair_id" not in norm:
        die(f"line {line_no}: run_context.run_pair_id must be present after normalization")
    return norm


def _tension_expected_endpoints(
    edge_type: str, tension_atom: Dict[str, Any], line_no: int
) -> Tuple[str, str]:
    """
    Derive expected (src_atom_id, dst_atom_id) from the tension atom evidence,
    using standardized aliases when present, otherwise falling back to canonical keys.

    This is the integrity cross-check Codex is asking for:
    edge endpoints must match the tension atom evidence links.
    """
    ev = tension_atom.get("evidence")
    if not isinstance(ev, dict):
        die(f"line {line_no}: tension atom evidence must be an object/dict")

    def _pick(name_alias: str, name_canon: str) -> str:
        v_alias = ev.get(name_alias)
        v_canon = ev.get(name_canon)

        alias_ok = isinstance(v_alias, str) and v_alias.strip()
        canon_ok = isinstance(v_canon, str) and v_canon.strip()

        if alias_ok and canon_ok and v_alias.strip() != v_canon.strip():
            die(
                f"line {line_no}: tension evidence alias mismatch: "
                f"{name_alias} != {name_canon} ({v_alias!r} != {v_canon!r})"
            )

        if alias_ok:
            return v_alias.strip()
        if canon_ok:
            return v_canon.strip()

        die(f"line {line_no}: tension evidence missing {name_alias}/{name_canon}")

    if edge_type == "gate_metric_tension":
        exp_src = _pick("src_atom_id", "gate_atom_id")
        exp_dst = _pick("dst_atom_id", "metric_atom_id")
        return exp_src, exp_dst

    if edge_type == "gate_overlay_tension":
        exp_src = _pick("src_atom_id", "gate_atom_id")
        exp_dst = _pick("dst_atom_id", "overlay_atom_id")
        return exp_src, exp_dst

    die(f"line {line_no}: cannot derive tension endpoints for unknown edge type: {edge_type}")


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

    # run_context consistency across the file (optional, but if present then strict)
    seen_any_run_context = False
    seen_missing_run_context = False
    file_run_context_norm: Optional[Dict[str, str]] = None

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

            # ---- Required for v0 tension edges
            tension_atom_id = edge.get("tension_atom_id")
            if tension_atom_id is None:
                die(f"line {line_no}: missing tension_atom_id (required for v0 tension edges)")
            if not isinstance(tension_atom_id, str) or not _is_hex(tension_atom_id, 12):
                die(f"line {line_no}: tension_atom_id must be 12-hex string")
            tension_atom_id = tension_atom_id.strip()

            # ---- Deterministic ordering
            k = _edge_key(edge)
            if prev_key is not None and k < prev_key:
                die(
                    f"line {line_no}: edges not in deterministic order "
                    f"(expected non-decreasing by (severity,type,edge_id)); got {k} after {prev_key}"
                )
            prev_key = k

            # ---- Optional run_context validation + file-level consistency
            run_ctx_any = edge.get("run_context")
            if run_ctx_any is None:
                seen_missing_run_context = True
            else:
                seen_any_run_context = True
                norm = _validate_run_context(run_ctx_any, line_no)
                if file_run_context_norm is None:
                    file_run_context_norm = norm
                else:
                    if norm != file_run_context_norm:
                        die(
                            f"line {line_no}: run_context inconsistent across file on allowed keys "
                            f"(expected={file_run_context_norm!r}, got={norm!r})"
                        )

            if seen_any_run_context and seen_missing_run_context:
                die(f"line {line_no}: mixed run_context presence across edges (some present, some missing)")

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

                # ---- Cross-check: edge endpoints must match tension atom evidence links
                exp_src, exp_dst = _tension_expected_endpoints(edge_type, tens_atom, line_no)
                if src_atom_id != exp_src or dst_atom_id != exp_dst:
                    die(
                        f"line {line_no}: edge endpoints do not match tension evidence for '{edge_type}' "
                        f"(expected src={exp_src!r}, dst={exp_dst!r}; got src={src_atom_id!r}, dst={dst_atom_id!r})"
                    )

            edges_count += 1

    print(f"[edges-contract] OK (edges={edges_count})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        raise SystemExit(0)


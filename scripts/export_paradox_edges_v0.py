#!/usr/bin/env python3
"""
export_paradox_edges_v0 — export evidence-first tension edges from paradox_field_v0.json.

Principle:
  - No new truth is invented here.
  - Nodes remain atoms.
  - Edges are proven co-occurrences (derived from tension atoms).

Input:
  paradox_field_v0.json
    - shape may be either:
      { "paradox_field_v0": { "meta": {...}, "atoms": [...] } }
      OR
      { "meta": {...}, "atoms": [...] }  (permissive)

Output:
  paradox_edges_v0.jsonl (JSON Lines), each line is one edge object:
    {
      "edge_id": "...",
      "type": "gate_metric_tension" | "gate_overlay_tension",
      "severity": "crit" | "warn" | "info",
      "src_atom_id": "...",
      "dst_atom_id": "...",
      "tension_atom_id": "...",
      "rule": "...",
      "run_context": {...}
    }

Fail-closed:
  - Missing/invalid input structure -> exit != 0
  - Broken atom links referenced by tension atoms -> exit != 0
  - Duplicate edge_id -> exit != 0

Stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from typing import Any, Dict, List, Tuple


SEVERITY_ORDER = {"crit": 0, "warn": 1, "info": 2}
ALLOWED_SEVERITIES = set(SEVERITY_ORDER.keys())

TENSION_TYPES = {"gate_metric_tension", "gate_overlay_tension"}


def die(msg: str, code: int = 2) -> None:
    raise SystemExit(f"[paradox_edges_v0] {msg}")


def _sha1_text(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _as_dict(x: Any, path: str) -> Dict[str, Any]:
    if not isinstance(x, dict):
        die(f"{path} must be an object/dict")
    return x


def _as_list(x: Any, path: str) -> List[Any]:
    if not isinstance(x, list):
        die(f"{path} must be an array/list")
    return x


def _req_str(d: Dict[str, Any], k: str, path: str) -> str:
    v = d.get(k)
    if not isinstance(v, str) or not v.strip():
        die(f"{path}.{k} must be a non-empty string")
    return v.strip()


def _sev_rank(sev: str) -> int:
    return SEVERITY_ORDER.get(sev, 99)


def _edge_id(edge_type: str, src: str, dst: str, tension_atom_id: str, ctx_id: str) -> str:
    raw = f"{edge_type}|{src}|{dst}|{tension_atom_id}|{ctx_id}"
    return _sha1_text(raw)[:16]


def _build_run_context(meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prefer meta.run_context when present (field adapter emits it),
    otherwise fall back to deriving it from stable sha1 keys in meta.

    Keep only stable-ish identifiers/hashes; avoid paths.
    """
    allowed_keys = {
        "run_pair_id",
        "status_sha1",
        "g_field_sha1",
        "transitions_json_sha1",
        "transitions_gate_csv_sha1",
        "transitions_metric_csv_sha1",
        "transitions_overlay_json_sha1",
    }

    # 1) Prefer meta.run_context (if present)
    rc_any = meta.get("run_context")
    if isinstance(rc_any, dict):
        ctx: Dict[str, Any] = {}
        for k, v in rc_any.items():
            if k in allowed_keys and isinstance(v, str) and v.strip():
                ctx[str(k)] = v.strip()

        # If run_pair_id is present and valid, trust it
        rpid = ctx.get("run_pair_id")
        if isinstance(rpid, str) and rpid.strip():
            return ctx

        # Else, deterministically derive it from remaining keys
        parts = [f"{k}={ctx[k]}" for k in sorted(ctx.keys()) if k != "run_pair_id"]
        ctx_id = _sha1_text("|".join(parts) if parts else "no_ctx")[:12]
        ctx["run_pair_id"] = ctx_id
        return ctx

    # 2) Fallback: compute from stable sha1 keys in meta (avoid paths)
    ctx2: Dict[str, Any] = {}
    for k in [
        "status_sha1",
        "g_field_sha1",
        "transitions_json_sha1",
        "transitions_gate_csv_sha1",
        "transitions_metric_csv_sha1",
        "transitions_overlay_json_sha1",
    ]:
        v = meta.get(k)
        if isinstance(v, str) and v.strip():
            ctx2[k] = v.strip()

    parts = [f"{k}={ctx2[k]}" for k in sorted(ctx2.keys())]
    ctx_id = _sha1_text("|".join(parts) if parts else "no_ctx")[:12]
    ctx2["run_pair_id"] = ctx_id
    return ctx2


def _tension_src_dst(typ: str, ev: Dict[str, Any], path: str) -> Tuple[str, str]:
    """
    Extract (src_atom_id, dst_atom_id) for a tension atom.

    Prefer C4.3 aliases:
      - evidence.src_atom_id
      - evidence.dst_atom_id

    Fail-closed if only one alias exists.

    Fallback to legacy keys:
      - gate_metric_tension: gate_atom_id + metric_atom_id
      - gate_overlay_tension: gate_atom_id + overlay_atom_id
    """
    if not isinstance(ev, dict):
        die(f"{path}.evidence must be an object/dict")

    has_src_alias = "src_atom_id" in ev
    has_dst_alias = "dst_atom_id" in ev
    if has_src_alias or has_dst_alias:
        src = ev.get("src_atom_id")
        dst = ev.get("dst_atom_id")
        if not isinstance(src, str) or not src.strip():
            die(f"{path}.evidence.src_atom_id must be a non-empty string when present")
        if not isinstance(dst, str) or not dst.strip():
            die(f"{path}.evidence.dst_atom_id must be a non-empty string when present")
        return src.strip(), dst.strip()

    # Legacy fallback (backwards compatibility)
    gate_id = ev.get("gate_atom_id")
    if not isinstance(gate_id, str) or not gate_id.strip():
        die(f"{path}.evidence.gate_atom_id must be a non-empty string")
    gate_id = gate_id.strip()

    if typ == "gate_metric_tension":
        met_id = ev.get("metric_atom_id")
        if not isinstance(met_id, str) or not met_id.strip():
            die(f"{path}.evidence.metric_atom_id must be a non-empty string")
        return gate_id, met_id.strip()

    if typ == "gate_overlay_tension":
        over_id = ev.get("overlay_atom_id")
        if not isinstance(over_id, str) or not over_id.strip():
            die(f"{path}.evidence.overlay_atom_id must be a non-empty string")
        return gate_id, over_id.strip()

    die(f"{path}: unsupported tension type: {typ}")
    raise SystemExit(2)  # unreachable (for type checkers)


def main() -> int:
    ap = argparse.ArgumentParser(description="Export paradox_edges_v0.jsonl from paradox_field_v0.json")
    ap.add_argument("--in", dest="in_path", required=True, help="Path to paradox_field_v0.json")
    ap.add_argument(
        "--out",
        dest="out_path",
        default="PULSE_safe_pack_v0/artifacts/paradox_edges_v0.jsonl",
        help="Output path (JSONL). Default: PULSE_safe_pack_v0/artifacts/paradox_edges_v0.jsonl",
    )
    args = ap.parse_args()

    if not os.path.isfile(args.in_path):
        die(f"file not found: {args.in_path}")

    data = _read_json(args.in_path)
    root = data.get("paradox_field_v0", data) if isinstance(data, dict) else data
    root = _as_dict(root, "$")

    meta = root.get("meta")
    meta = meta if isinstance(meta, dict) else {}
    atoms_any = root.get("atoms")
    atoms_list = _as_list(atoms_any, "$.atoms")

    # Index atoms by id, validate minimal contract
    id_to_atom: Dict[str, Dict[str, Any]] = {}
    for i, a in enumerate(atoms_list):
        if not isinstance(a, dict):
            die(f"$.atoms[{i}] must be an object/dict")
        aid = _req_str(a, "atom_id", f"$.atoms[{i}]")
        if aid in id_to_atom:
            die(f"duplicate atom_id: {aid!r}")
        sev = _req_str(a, "severity", f"$.atoms[{i}]")
        if sev not in ALLOWED_SEVERITIES:
            die(f"$.atoms[{i}].severity must be one of {sorted(ALLOWED_SEVERITIES)} (got {sev!r})")
        _req_str(a, "type", f"$.atoms[{i}]")
        ev = a.get("evidence")
        if not isinstance(ev, dict):
            die(f"$.atoms[{i}].evidence must be an object/dict")
        id_to_atom[aid] = a

    def atom_type(aid: str) -> str:
        a = id_to_atom.get(aid)
        t = a.get("type") if isinstance(a, dict) else ""
        return t if isinstance(t, str) else ""

    run_context = _build_run_context(meta)
    ctx_id = str(run_context.get("run_pair_id", "no_ctx"))

    edges: List[Dict[str, Any]] = []
    seen_edge_ids = set()

    # Build edges from tension atoms
    for i, a_any in enumerate(atoms_list):
        if not isinstance(a_any, dict):
            continue
        typ = a_any.get("type")
        if not isinstance(typ, str) or typ not in TENSION_TYPES:
            continue

        sev = a_any.get("severity")
        if not isinstance(sev, str) or sev not in ALLOWED_SEVERITIES:
            die(f"$.atoms[{i}] tension atom has invalid severity")

        tension_atom_id = _req_str(a_any, "atom_id", f"$.atoms[{i}]")
        ev = a_any.get("evidence")
        if not isinstance(ev, dict):
            die(f"$.atoms[{i}].evidence must be an object/dict")

        # Prefer evidence.rule when present; fallback to stable default strings.
        rule_any = ev.get("rule")
        if isinstance(rule_any, str) and rule_any.strip():
            rule = rule_any.strip()
        else:
            rule = "gate_flip × metric_delta(warn|crit)" if typ == "gate_metric_tension" else "gate_flip × overlay_change"

        # Prefer C4.3 src/dst aliases; fallback to legacy keys.
        src, dst = _tension_src_dst(typ, ev, f"$.atoms[{i}]")

        # Link existence checks
        if src not in id_to_atom:
            die(f"$.atoms[{i}] broken link: src_atom_id {src!r} not found")
        if dst not in id_to_atom:
            die(f"$.atoms[{i}] broken link: dst_atom_id {dst!r} not found")

        # Link type checks
        if atom_type(src) != "gate_flip":
            die(f"$.atoms[{i}] link type mismatch: src_atom_id must point to type 'gate_flip'")

        if typ == "gate_metric_tension":
            if atom_type(dst) != "metric_delta":
                die(f"$.atoms[{i}] link type mismatch: dst_atom_id must point to type 'metric_delta'")
        elif typ == "gate_overlay_tension":
            if atom_type(dst) != "overlay_change":
                die(f"$.atoms[{i}] link type mismatch: dst_atom_id must point to type 'overlay_change'")

        eid = _edge_id(typ, src, dst, tension_atom_id, ctx_id)
        if eid in seen_edge_ids:
            die(f"duplicate edge_id detected: {eid!r}")
        seen_edge_ids.add(eid)

        edges.append(
            {
                "edge_id": eid,
                "type": typ,
                "severity": sev,
                "src_atom_id": src,
                "dst_atom_id": dst,
                "tension_atom_id": tension_atom_id,
                "rule": rule,
                "run_context": run_context,
            }
        )

    # Deterministic ordering: severity -> type -> edge_id
    edges.sort(key=lambda e: (_sev_rank(str(e.get("severity", ""))), str(e.get("type", "")), str(e.get("edge_id", ""))))

    # Write JSONL
    out_dir = os.path.dirname(os.path.abspath(args.out_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(args.out_path, "w", encoding="utf-8") as f:
        for e in edges:
            f.write(json.dumps(e, ensure_ascii=False, sort_keys=True))
            f.write("\n")

    print(f"[paradox_edges_v0] wrote: {args.out_path} (edges={len(edges)})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        sys.exit(0)


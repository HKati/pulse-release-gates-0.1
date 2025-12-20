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
    # Only keep stable-ish identifiers/hashes; avoid paths.
    ctx: Dict[str, Any] = {}

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
            ctx[k] = v.strip()

    # Deterministic context id: hash the sorted key=value pairs
    parts = [f"{k}={ctx[k]}" for k in sorted(ctx.keys())]
    ctx_id = _sha1_text("|".join(parts) if parts else "no_ctx")[:12]
    ctx["run_pair_id"] = ctx_id
    return ctx


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

        if typ == "gate_metric_tension":
            src = ev.get("gate_atom_id")
            dst = ev.get("metric_atom_id")
            rule = "gate_flip × metric_delta(warn|crit)"
            if not isinstance(src, str) or not src.strip():
                die(f"$.atoms[{i}].evidence.gate_atom_id must be a non-empty string")
            if not isinstance(dst, str) or not dst.strip():
                die(f"$.atoms[{i}].evidence.metric_atom_id must be a non-empty string")
            src = src.strip()
            dst = dst.strip()
            if src not in id_to_atom:
                die(f"$.atoms[{i}] broken link: gate_atom_id {src!r} not found")
            if dst not in id_to_atom:
                die(f"$.atoms[{i}] broken link: metric_atom_id {dst!r} not found")
            if atom_type(src) != "gate_flip":
                die(f"$.atoms[{i}] link type mismatch: gate_atom_id must point to type 'gate_flip'")
            if atom_type(dst) != "metric_delta":
                die(f"$.atoms[{i}] link type mismatch: metric_atom_id must point to type 'metric_delta'")

        elif typ == "gate_overlay_tension":
            src = ev.get("gate_atom_id")
            dst = ev.get("overlay_atom_id")
            rule = "gate_flip × overlay_change"
            if not isinstance(src, str) or not src.strip():
                die(f"$.atoms[{i}].evidence.gate_atom_id must be a non-empty string")
            if not isinstance(dst, str) or not dst.strip():
                die(f"$.atoms[{i}].evidence.overlay_atom_id must be a non-empty string")
            src = src.strip()
            dst = dst.strip()
            if src not in id_to_atom:
                die(f"$.atoms[{i}] broken link: gate_atom_id {src!r} not found")
            if dst not in id_to_atom:
                die(f"$.atoms[{i}] broken link: overlay_atom_id {dst!r} not found")
            if atom_type(src) != "gate_flip":
                die(f"$.atoms[{i}] link type mismatch: gate_atom_id must point to type 'gate_flip'")
            if atom_type(dst) != "overlay_change":
                die(f"$.atoms[{i}] link type mismatch: overlay_atom_id must point to type 'overlay_change'")

        else:
            continue

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

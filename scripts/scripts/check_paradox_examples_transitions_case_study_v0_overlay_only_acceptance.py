#!/usr/bin/env python3
"""
check_paradox_examples_transitions_case_study_v0_overlay_only_acceptance.py

Acceptance checks for:
  docs/examples/transitions_case_study_v0_overlay_only

Goal:
- Keep the example reproducible and CI-friendly without pinning exact sha1/run_pair_id.
- Assert the *high-level* expected outcome:
  - at least one gate_overlay_tension edge exists
  - zero gate_metric_tension edges exist (metrics intentionally below warn/crit)
  - run_context is present and consistent (normalized) across field + edges

Usage (canonical wrapper is in scripts/):
  python scripts/check_paradox_examples_transitions_case_study_v0_overlay_only_acceptance.py \
    --in out/paradox_edges_v0_overlay_only.jsonl \
    --field out/paradox_field_v0_overlay_only.json
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List, Optional


RUN_CONTEXT_ALLOWED_KEYS = {
    "run_pair_id",
    "status_sha1",
    "g_field_sha1",
    "transitions_json_sha1",
    "transitions_gate_csv_sha1",
    "transitions_metric_csv_sha1",
    "transitions_overlay_json_sha1",
}

EDGE_TYPES = {"gate_metric_tension", "gate_overlay_tension"}


def die(msg: str, code: int = 2) -> None:
    raise SystemExit(f"[overlay-only-acceptance] {msg}")


def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_edges_jsonl(path: str) -> List[Dict[str, Any]]:
    if not os.path.isfile(path):
        die(f"--in not found: {path}")

    edges: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception as e:
                die(f"line {line_no}: invalid JSONL: {e}")
            if not isinstance(obj, dict):
                die(f"line {line_no}: edge must be an object/dict")
            edges.append(obj)

    if not edges:
        die("no edges found (expected at least one gate_overlay_tension edge)")
    return edges


def _normalize_run_context(rc: Any, label: str) -> Dict[str, str]:
    if not isinstance(rc, dict):
        die(f"{label}.run_context must be an object/dict")

    norm: Dict[str, str] = {}
    for k in RUN_CONTEXT_ALLOWED_KEYS:
        v = rc.get(k)
        if isinstance(v, str) and v.strip():
            norm[k] = v.strip()

    rpid = norm.get("run_pair_id", "")
    if not isinstance(rpid, str) or not rpid.strip():
        die(f"{label}.run_context.run_pair_id must be a non-empty string")

    return norm


def _pick_field_path(in_edges_path: str, user_field_path: str) -> str:
    if user_field_path:
        return user_field_path

    out_dir = os.path.dirname(os.path.abspath(in_edges_path)) or "."
    candidates = [
        os.path.join(out_dir, "paradox_field_v0_overlay_only.json"),
        os.path.join(out_dir, "paradox_field_v0.json"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c

    die(
        "missing --field and could not auto-discover field JSON next to edges; "
        "pass --field out/paradox_field_v0_overlay_only.json"
    )
    return ""


def _load_field(field_path: str) -> Dict[str, Any]:
    if not os.path.isfile(field_path):
        die(f"--field not found: {field_path}")

    obj = _read_json(field_path)
    root = obj.get("paradox_field_v0", obj) if isinstance(obj, dict) else obj
    if not isinstance(root, dict):
        die("--field malformed: expected dict root")

    meta = root.get("meta")
    if not isinstance(meta, dict):
        die("--field malformed: meta must be an object/dict")

    rc_any = meta.get("run_context")
    rc_norm = _normalize_run_context(rc_any, "field.meta")

    atoms_any = root.get("atoms")
    if not isinstance(atoms_any, list):
        die("--field malformed: atoms must be a list")

    return {"meta": meta, "run_context_norm": rc_norm, "atoms": atoms_any}


def _field_invariants(atoms: List[Any]) -> None:
    def _is_atom(a: Any) -> bool:
        return isinstance(a, dict) and isinstance(a.get("type"), str)

    gate_flip = any(_is_atom(a) and a.get("type") == "gate_flip" for a in atoms)
    if not gate_flip:
        die("field: expected at least one gate_flip atom")

    overlay_change_g = False
    for a in atoms:
        if not _is_atom(a):
            continue
        if a.get("type") != "overlay_change":
            continue

        # Prefer refs.overlays if present; fall back to evidence.overlay.name
        refs = a.get("refs")
        if isinstance(refs, dict):
            ovs = refs.get("overlays")
            if isinstance(ovs, list) and any(str(x) == "g_field_v0" for x in ovs):
                overlay_change_g = True
                break

        ev = a.get("evidence")
        if isinstance(ev, dict):
            ov = ev.get("overlay")
            if isinstance(ov, dict) and str(ov.get("name", "")) == "g_field_v0":
                overlay_change_g = True
                break

    if not overlay_change_g:
        die("field: expected at least one overlay_change atom for overlay 'g_field_v0'")

    gate_overlay_tension = any(_is_atom(a) and a.get("type") == "gate_overlay_tension" for a in atoms)
    if not gate_overlay_tension:
        die("field: expected at least one gate_overlay_tension atom")

    gate_metric_tension = any(_is_atom(a) and a.get("type") == "gate_metric_tension" for a in atoms)
    if gate_metric_tension:
        die("field: expected zero gate_metric_tension atoms (metrics should be below warn/crit)")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Acceptance checks for docs/examples/transitions_case_study_v0_overlay_only"
    )
    ap.add_argument("--in", dest="in_path", required=True, help="Path to paradox_edges_v0_overlay_only.jsonl")
    ap.add_argument(
        "--field",
        dest="field_path",
        default="",
        help="Path to paradox_field_v0_overlay_only.json (if omitted, auto-discover next to edges)",
    )
    args = ap.parse_args()

    # Load + validate field (required for acceptance)
    field_path = _pick_field_path(args.in_path, args.field_path)
    field = _load_field(field_path)
    field_rc_norm: Dict[str, str] = field["run_context_norm"]
    atoms_any: List[Any] = field["atoms"]

    _field_invariants(atoms_any)

    # Load edges + validate high-level properties
    edges = _load_edges_jsonl(args.in_path)

    type_counts: Dict[str, int] = {}
    first_edge_rc_norm: Optional[Dict[str, str]] = None

    for i, e in enumerate(edges):
        et = e.get("type")
        if not isinstance(et, str) or not et.strip():
            die(f"edges[{i}].type must be a non-empty string")
        et = et.strip()

        if et not in EDGE_TYPES:
            die(f"edges[{i}].type unknown for v0 example acceptance: {et!r}")

        erc_norm = _normalize_run_context(e.get("run_context"), f"edges[{i}]")
        if first_edge_rc_norm is None:
            first_edge_rc_norm = erc_norm
        else:
            if erc_norm != first_edge_rc_norm:
                die(f"edges[{i}].run_context inconsistent across edges on allowed keys")

        type_counts[et] = type_counts.get(et, 0) + 1

    if first_edge_rc_norm is None:
        die("no edges found after parsing (unexpected)")

    # Example invariants
    overlay_edges = type_counts.get("gate_overlay_tension", 0)
    metric_edges = type_counts.get("gate_metric_tension", 0)

    if overlay_edges < 1:
        die("expected at least 1 gate_overlay_tension edge (overlay-only example)")

    if metric_edges != 0:
        die("expected 0 gate_metric_tension edges (metrics in this example should be below warn/crit)")

    # Field ↔ edges correlation (normalized / exporter-allowed keys)
    if first_edge_rc_norm != field_rc_norm:
        die("edge run_context does not match field meta.run_context on exporter-allowed keys")

    print(
        "[overlay-only-acceptance] OK "
        f"(edges={len(edges)}, gate_overlay_tension={overlay_edges}, gate_metric_tension={metric_edges})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

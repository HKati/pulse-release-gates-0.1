#!/usr/bin/env python3
"""
check_paradox_examples_transitions_case_study_v0_acceptance.py

Acceptance check for docs/examples/transitions_case_study_v0 outputs.

Goal:
- Validate the example stays reproducible and CI-friendly.
- Validate field ↔ edges correlation using run_context (C4.2).
- Validate a few semantic invariants (metrics + allowlisted overlay tensions).

This is intentionally strict where it matters (join integrity + semantics),
and intentionally NOT hard-pinning file sha1 values (to avoid brittle churn).

Usage:
  python scripts/check_paradox_examples_transitions_case_study_v0_acceptance.py \
    --in out/paradox_edges_v0.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Set, Tuple


EXPECTED_METRICS: Set[str] = {"p99_latency", "cpu_util"}
OVERLAY_ALLOWLIST: Set[str] = {"g_field_v0", "paradox_field_v0"}

# Must match export_paradox_edges_v0._build_run_context() allowlist behavior.
RUN_CONTEXT_ALLOWED_KEYS: Set[str] = {
    "run_pair_id",
    "status_sha1",
    "g_field_sha1",
    "transitions_json_sha1",
    "transitions_gate_csv_sha1",
    "transitions_metric_csv_sha1",
    "transitions_overlay_json_sha1",
}


def die(msg: str, code: int = 2) -> None:
    raise SystemExit(f"[examples-acceptance] {msg}")


def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _read_jsonl(path: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            s = raw.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except Exception as e:
                die(f"invalid JSONL at line {line_no}: {e}")
            if not isinstance(obj, dict):
                die(f"JSONL line {line_no} must be an object")
            out.append(obj)
    return out


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


def _normalize_run_context(rc_any: Any, path: str) -> Dict[str, str]:
    """
    Normalize run_context to the allowed subset that the edges exporter emits.
    This avoids brittleness if meta.run_context contains extra keys that edges drop.
    """
    rc = _as_dict(rc_any, path)

    out: Dict[str, str] = {}
    for k in RUN_CONTEXT_ALLOWED_KEYS:
        v = rc.get(k)
        if isinstance(v, str) and v.strip():
            out[k] = v.strip()

    # run_pair_id must be present for the example (C4.2 intent)
    if "run_pair_id" not in out:
        die(f"{path}.run_pair_id must be present and non-empty")
    return out


def _load_field_atoms(atoms_path: str) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    data = _read_json(atoms_path)
    root = data.get("paradox_field_v0", data) if isinstance(data, dict) else data
    root = _as_dict(root, "$")

    meta = root.get("meta")
    meta = meta if isinstance(meta, dict) else {}
    atoms_any = root.get("atoms")
    atoms_list = _as_list(atoms_any, "$.atoms")

    atoms: List[Dict[str, Any]] = []
    id_to_atom: Dict[str, Dict[str, Any]] = {}
    for i, a in enumerate(atoms_list):
        if not isinstance(a, dict):
            die(f"$.atoms[{i}] must be an object/dict")
        aid = _req_str(a, "atom_id", f"$.atoms[{i}]")
        id_to_atom[aid] = a
        atoms.append(a)

    return meta, id_to_atom, atoms


def _extract_overlay_changes(atoms: List[Dict[str, Any]]) -> Set[str]:
    changed: Set[str] = set()
    for a in atoms:
        if not isinstance(a, dict):
            continue
        if a.get("type") != "overlay_change":
            continue
        refs = a.get("refs")
        if not isinstance(refs, dict):
            continue
        overs = refs.get("overlays")
        if not isinstance(overs, list):
            continue
        for o in overs:
            if isinstance(o, str) and o.strip():
                changed.add(o.strip())
    return changed


def _tension_metric_name(tension_atom: Dict[str, Any]) -> str:
    ev = tension_atom.get("evidence")
    if isinstance(ev, dict):
        mm = ev.get("metric")
        if isinstance(mm, dict) and isinstance(mm.get("name"), str) and mm.get("name").strip():
            return mm.get("name").strip()

    refs = tension_atom.get("refs")
    if isinstance(refs, dict):
        ms = refs.get("metrics")
        if isinstance(ms, list) and ms and isinstance(ms[0], str) and ms[0].strip():
            return ms[0].strip()

    return ""


def _tension_overlay_name(tension_atom: Dict[str, Any]) -> str:
    ev = tension_atom.get("evidence")
    if isinstance(ev, dict):
        oo = ev.get("overlay")
        if isinstance(oo, dict) and isinstance(oo.get("name"), str) and oo.get("name").strip():
            return oo.get("name").strip()

    refs = tension_atom.get("refs")
    if isinstance(refs, dict):
        os_ = refs.get("overlays")
        if isinstance(os_, list) and os_ and isinstance(os_[0], str) and os_[0].strip():
            return os_[0].strip()

    return ""


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Acceptance check for docs/examples/transitions_case_study_v0 outputs (field ↔ edges join + semantics)."
    )
    ap.add_argument("--in", dest="edges_path", required=True, help="Path to paradox_edges_v0.jsonl")
    ap.add_argument(
        "--atoms",
        dest="atoms_path",
        default="",
        help="Optional path to paradox_field_v0.json (default: derive from edges path directory).",
    )
    args = ap.parse_args()

    if not os.path.isfile(args.edges_path):
        die(f"edges file not found: {args.edges_path}")

    # Default atoms path: same dir as edges file
    atoms_path = args.atoms_path.strip() if isinstance(args.atoms_path, str) else ""
    if not atoms_path:
        atoms_path = os.path.join(os.path.dirname(os.path.abspath(args.edges_path)), "paradox_field_v0.json")

    if not os.path.isfile(atoms_path):
        die(f"atoms file not found (expected next to edges): {atoms_path}")

    meta, id_to_atom, atoms = _load_field_atoms(atoms_path)

    # Require meta.run_context (the example is meant to exercise C4.2)
    rc_any = meta.get("run_context")
    if not isinstance(rc_any, dict):
        die("$.meta.run_context must be an object/dict (example expects run_context present)")

    # Normalize to exporter-allowed keys
    rc_norm = _normalize_run_context(rc_any, "$.meta.run_context")

    edges = _read_jsonl(args.edges_path)
    if not edges:
        die("edges JSONL is empty")

    # 1) Field ↔ edges correlation: compare normalized run_context subset (not full dict)
    for i, e in enumerate(edges):
        if not isinstance(e, dict):
            die(f"edges[{i}] must be an object/dict")
        erc_any = e.get("run_context")
        if not isinstance(erc_any, dict):
            die(f"edges[{i}].run_context must be an object/dict")

        erc_norm = _normalize_run_context(erc_any, f"edges[{i}].run_context")

        if erc_norm != rc_norm:
            die(
                f"edges[{i}].run_context does not match field meta.run_context on allowed keys "
                f"(expected={rc_norm!r}, got={erc_norm!r})"
            )

    # 2) Semantic invariants: map edges → tension atoms → metric/overlay names
    metric_tensions: Set[str] = set()
    overlay_tensions: Set[str] = set()

    for i, e in enumerate(edges):
        typ = e.get("type")
        if not isinstance(typ, str) or not typ.strip():
            continue
        tid = e.get("tension_atom_id")
        if not isinstance(tid, str) or not tid.strip():
            die(f"edges[{i}].tension_atom_id must be a non-empty string")
        tid = tid.strip()

        t_atom = id_to_atom.get(tid)
        if not isinstance(t_atom, dict):
            die(f"edges[{i}] tension_atom_id not found in atoms: {tid}")

        # sanity: edge.type should match the tension atom type
        t_type = t_atom.get("type")
        if isinstance(t_type, str) and t_type.strip() and t_type.strip() != typ.strip():
            die(f"edges[{i}] edge.type != tension atom type for tension_atom_id={tid}")

        if typ.strip() == "gate_metric_tension":
            name = _tension_metric_name(t_atom)
            if name:
                metric_tensions.add(name)

        if typ.strip() == "gate_overlay_tension":
            oname = _tension_overlay_name(t_atom)
            if oname:
                overlay_tensions.add(oname)

    missing_metrics = sorted(EXPECTED_METRICS - metric_tensions)
    if missing_metrics:
        die(f"missing expected gate_metric_tension metrics: {missing_metrics}")

    # 3) Overlay invariants:
    # If an allowlisted overlay has an overlay_change atom, we expect a corresponding gate_overlay_tension edge.
    overlays_changed = _extract_overlay_changes(atoms) & OVERLAY_ALLOWLIST
    if not overlays_changed:
        die(f"expected at least one allowlisted overlay_change in field (allowlist={sorted(OVERLAY_ALLOWLIST)})")

    for o in sorted(overlays_changed):
        if o not in overlay_tensions:
            die(f"missing gate_overlay_tension for allowlisted changed overlay: {o!r}")

    print(
        f"[examples-acceptance] OK (edges={len(edges)}, "
        f"metric_tensions={sorted(metric_tensions)}, overlay_tensions={sorted(overlay_tensions)})"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        sys.exit(0)


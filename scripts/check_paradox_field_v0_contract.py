#!/usr/bin/env python3
# scripts/check_paradox_field_v0_contract.py

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Tuple


SEVERITY_ORDER = {"crit": 0, "warn": 1, "info": 2}
ALLOWED_SEVERITIES = set(SEVERITY_ORDER.keys())


def die(msg: str, code: int = 2) -> None:
    raise SystemExit(f"[contract] {msg}")


def as_dict(x: Any, path: str) -> Dict[str, Any]:
    if not isinstance(x, dict):
        die(f"{path} must be an object/dict")
    return x


def as_list(x: Any, path: str) -> List[Any]:
    if not isinstance(x, list):
        die(f"{path} must be an array/list")
    return x


def req_str(d: Dict[str, Any], key: str, path: str) -> str:
    v = d.get(key)
    if not isinstance(v, str) or not v.strip():
        die(f"{path}.{key} must be a non-empty string")
    return v


def req_dict(d: Dict[str, Any], key: str, path: str) -> Dict[str, Any]:
    v = d.get(key)
    if not isinstance(v, dict):
        die(f"{path}.{key} must be an object/dict")
    return v


def sort_key(atom: Dict[str, Any], path: str) -> Tuple[int, str, str]:
    sev = req_str(atom, "severity", path)
    if sev not in SEVERITY_ORDER:
        die(f"{path}.severity must be one of {sorted(ALLOWED_SEVERITIES)} (got {sev!r})")
    typ = req_str(atom, "type", path)
    aid = req_str(atom, "atom_id", path)
    return (SEVERITY_ORDER[sev], typ, aid)


def check_non_decreasing(keys: List[Tuple[int, str, str]]) -> None:
    for i in range(1, len(keys)):
        if keys[i - 1] > keys[i]:
            die(
                "atoms are not deterministically ordered; expected non-decreasing by "
                "severity (crit>warn>info), then type, then atom_id"
            )


def _optional_meta_run_context_checks(root: Dict[str, Any]) -> None:
    """
    C4.2: Optional run_context validations (fail-closed if present).
    - meta is optional
    - meta.run_context is optional
    - if meta.run_context is present: must be dict with non-empty string keys/values
      and must contain run_pair_id as a non-empty string.

    Rationale: prevents field↔edges drift if export drops invalid run_context entries
    and synthesizes a different run_pair_id.
    """
    meta_any = root.get("meta")
    if meta_any is None:
        return
    if not isinstance(meta_any, dict):
        die("$.meta must be an object/dict when present")

    rc_any = meta_any.get("run_context")
    if rc_any is None:
        return
    if not isinstance(rc_any, dict):
        die("$.meta.run_context must be an object/dict when present")

    for k, v in rc_any.items():
        if not isinstance(k, str) or not k.strip():
            die("$.meta.run_context keys must be non-empty strings")
        if not isinstance(v, str) or not v.strip():
            die(f"$.meta.run_context.{k} must be a non-empty string")

    rpid = rc_any.get("run_pair_id")
    if not isinstance(rpid, str) or not rpid.strip():
        die("$.meta.run_context.run_pair_id must be a non-empty string when run_context is present")


def _optional_provenance_checks(atom: Dict[str, Any], path: str) -> None:
    """
    Fail-closed checks for optional provenance fields.
    These fields are NOT required to exist, but if present they must be valid.
    """
    ev = atom.get("evidence")
    if not isinstance(ev, dict):
        die(f"{path}.evidence must be an object/dict")

    src = ev.get("source")
    if src is None:
        return
    if not isinstance(src, dict):
        die(f"{path}.evidence.source must be an object/dict when present")

    # Optional CSV provenance
    if "row_index" in src:
        ri = src.get("row_index")
        if not isinstance(ri, int) or ri < 0:
            die(f"{path}.evidence.source.row_index must be a non-negative int when present")

    for k in ("gate_drift_csv", "metric_drift_csv", "overlay_drift_json"):
        if k in src:
            v = src.get(k)
            if not isinstance(v, str) or not v.strip():
                die(f"{path}.evidence.source.{k} must be a non-empty string when present")

    # Optional JSON pointer provenance for overlay blocks
    if "overlay_name" in src:
        v = src.get("overlay_name")
        if not isinstance(v, str) or not v.strip():
            die(f"{path}.evidence.source.overlay_name must be a non-empty string when present")

    for k in ("json_pointer", "json_pointer_top_level_diff"):
        if k in src:
            jp = src.get(k)
            if not isinstance(jp, str) or not jp.strip():
                die(f"{path}.evidence.source.{k} must be a non-empty string when present")
            if not jp.startswith("/"):
                die(f"{path}.evidence.source.{k} must start with '/' (JSON Pointer) when present")


def _require_tension_alias_checks(
    ev: Dict[str, Any],
    expected_src: str,
    expected_dst: str,
    dst_label: str,
    path: str,
) -> None:
    """
    C4.3: Required tension alias keys (fail-closed).

    Expected mapping:
      - evidence.src_atom_id == gate_atom_id
      - evidence.dst_atom_id == {metric_atom_id|overlay_atom_id} (dst_label)
    """
    src = req_str(ev, "src_atom_id", f"{path}.evidence")
    dst = req_str(ev, "dst_atom_id", f"{path}.evidence")

    exp_src = expected_src.strip()
    exp_dst = expected_dst.strip()

    if src.strip() != exp_src:
        die(f"{path}.evidence.src_atom_id must match evidence.gate_atom_id")
    if dst.strip() != exp_dst:
        die(f"{path}.evidence.dst_atom_id must match evidence.{dst_label}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Contract check for paradox_field_v0.json")
    ap.add_argument("--in", dest="in_path", required=True, help="Path to paradox_field_v0.json")
    args = ap.parse_args()

    try:
        with open(args.in_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        die(f"file not found: {args.in_path}")
    except json.JSONDecodeError as e:
        die(f"invalid JSON: {e}")

    root = as_dict(data, "$")

    # Accept both shapes:
    #  (A) { "paradox_field_v0": { "meta":..., "atoms":[...] } }
    #  (B) { "meta":..., "atoms":[...] }
    if "paradox_field_v0" in root and isinstance(root.get("paradox_field_v0"), dict):
        root = as_dict(root.get("paradox_field_v0"), "$.paradox_field_v0")

    # ---- C4.2: optional meta.run_context validations (fail-closed if present)
    _optional_meta_run_context_checks(root)

    atoms_any = root.get("atoms")
    if atoms_any is None:
        die("$.atoms is missing")
    atoms_list = as_list(atoms_any, "$.atoms")

    atoms: List[Dict[str, Any]] = []
    for i, a in enumerate(atoms_list):
        if not isinstance(a, dict):
            die(f"$.atoms[{i}] must be an object/dict")
        atoms.append(a)

    # Basic per-atom checks + collect ids
    id_to_atom: Dict[str, Dict[str, Any]] = {}
    keys: List[Tuple[int, str, str]] = []
    for i, a in enumerate(atoms):
        path = f"$.atoms[{i}]"
        aid = req_str(a, "atom_id", path)
        if aid in id_to_atom:
            die(f"duplicate atom_id: {aid!r}")
        id_to_atom[aid] = a

        req_str(a, "type", path)
        req_str(a, "severity", path)
        req_dict(a, "evidence", path)

        # Optional provenance validations (fail-closed if present)
        _optional_provenance_checks(a, path)

        keys.append(sort_key(a, path))

    # Deterministic ordering check (non-decreasing keys)
    check_non_decreasing(keys)

    def atom_type(aid: str) -> str:
        a = id_to_atom.get(aid)
        if a is None:
            return ""
        t = a.get("type")
        return t if isinstance(t, str) else ""

    # Link integrity checks for known tension types
    for i, a in enumerate(atoms):
        path = f"$.atoms[{i}]"
        typ = a.get("type")
        if not isinstance(typ, str):
            continue

        ev = a.get("evidence")
        if not isinstance(ev, dict):
            die(f"{path}.evidence must be an object/dict")

        if typ == "gate_overlay_tension":
            gate_id = ev.get("gate_atom_id")
            over_id = ev.get("overlay_atom_id")
            if not isinstance(gate_id, str) or not gate_id.strip():
                die(f"{path}.evidence.gate_atom_id must be a non-empty string")
            if not isinstance(over_id, str) or not over_id.strip():
                die(f"{path}.evidence.overlay_atom_id must be a non-empty string")
            if gate_id not in id_to_atom:
                die(f"{path} broken link: gate_atom_id {gate_id!r} not found")
            if over_id not in id_to_atom:
                die(f"{path} broken link: overlay_atom_id {over_id!r} not found")
            if atom_type(gate_id) != "gate_flip":
                die(f"{path} link type mismatch: gate_atom_id must point to type 'gate_flip'")
            if atom_type(over_id) != "overlay_change":
                die(f"{path} link type mismatch: overlay_atom_id must point to type 'overlay_change'")

            # C4.3 required alias validation (fail-closed)
            _require_tension_alias_checks(
                ev=ev,
                expected_src=gate_id,
                expected_dst=over_id,
                dst_label="overlay_atom_id",
                path=path,
            )

        if typ == "gate_metric_tension":
            gate_id = ev.get("gate_atom_id")
            met_id = ev.get("metric_atom_id")
            if not isinstance(gate_id, str) or not gate_id.strip():
                die(f"{path}.evidence.gate_atom_id must be a non-empty string")
            if not isinstance(met_id, str) or not met_id.strip():
                die(f"{path}.evidence.metric_atom_id must be a non-empty string")
            if gate_id not in id_to_atom:
                die(f"{path} broken link: gate_atom_id {gate_id!r} not found")
            if met_id not in id_to_atom:
                die(f"{path} broken link: metric_atom_id {met_id!r} not found")
            if atom_type(gate_id) != "gate_flip":
                die(f"{path} link type mismatch: gate_atom_id must point to type 'gate_flip'")
            if atom_type(met_id) != "metric_delta":
                die(f"{path} link type mismatch: metric_atom_id must point to type 'metric_delta'")

            # C4.3 required alias validation (fail-closed)
            _require_tension_alias_checks(
                ev=ev,
                expected_src=gate_id,
                expected_dst=met_id,
                dst_label="metric_atom_id",
                path=path,
            )

    print("[contract] OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        # allow piping into head, etc.
        sys.exit(0)


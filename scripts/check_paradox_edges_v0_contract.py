#!/usr/bin/env python3
"""
check_paradox_edges_v0_contract.py — fail-closed contract checker for paradox_edges_v0.jsonl.

Validator for the *edges* layer (JSONL), with optional link integrity checks against
paradox_field_v0.json (atoms) when `--atoms` is provided.

Guarantees (v0):
- JSONL parsing robustness (1 JSON object per line)
- deterministic ordering (non-decreasing by severity, then type, then edge_id)
- uniqueness of edge_id
- required fields for tension edges
- optional run_context validation (fail-closed when present)
- when --atoms is provided:
  - src/dst/tension atom existence + type validation
  - edge.severity must match the linked tension atom severity
  - edge endpoints must match the linked IDs inside the tension atom evidence
    (prevents swapped/misaligned endpoints)
  - if atoms meta.run_context is present, edges must carry run_context and it must match

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


def _validate_run_context(run_ctx: Any, ctx: str) -> None:
    """
    run_context is optional.
    If present, it must be a dict and must contain a non-empty run_pair_id string.
    If sha1 keys are present, validate they look like sha1 (40 hex).
    """
    if run_ctx is None:
        return
    if not isinstance(run_ctx, dict):
        die(f"{ctx}: run_context must be an object/dict if present")

    rpid = run_ctx.get("run_pair_id")
    if not isinstance(rpid, str) or not rpid.strip():
        die(f"{ctx}: run_context.run_pair_id must be a non-empty string if run_context is present")

    def _opt_sha1(k: str) -> None:
        v = run_ctx.get(k)
        if v is None:
            return
        if not isinstance(v, str) or not _is_hex(v, 40):
            die(f"{ctx}: run_context.{k} must be a 40-hex sha1 if present")

    _opt_sha1("transitions_gate_csv_sha1")
    _opt_sha1("transitions_metric_csv_sha1")
    _opt_sha1("transitions_overlay_json_sha1")
    _opt_sha1("transitions_json_sha1")
    _opt_sha1("status_sha1")
    _opt_sha1("g_field_sha1")


def _normalize_run_context(run_ctx: Dict[str, Any]) -> Dict[str, str]:
    """
    Normalize to the stable subset of keys. This keeps comparisons non-brittle
    if extra keys are added later.
    """
    out: Dict[str, str] = {}
    for k in sorted(RUN_CONTEXT_ALLOWED_KEYS):
        v = run_ctx.get(k)
        if isinstance(v, str) and v.strip():
            out[k] = v.strip()
    return out


def _load_atoms_and_meta_run_context(atoms_path: str) -> Tuple[Dict[str, Dict[str, Any]], Optional[Dict[str, str]]]:
    """
    Load atom index (by atom_id) from paradox_field_v0.json, plus optional
    meta.run_context (normalized) if present.
    """
    if not atoms_path:
        return {}, None
    if not os.path.isfile(atoms_path):
        die(f"--atoms not found: {atoms_path}")

    obj = _read_json(atoms_path)
    root = obj.get("paradox_field_v0", obj) if isinstance(obj, dict) else {}
    if not isinstance(root, dict):
        die(f"atoms file malformed: expected object at root/paradox_field_v0: {atoms_path}")

    # Optional meta.run_context (C4.2)
    meta_ctx_norm: Optional[Dict[str, str]] = None
    meta_any = root.get("meta")
    if isinstance(meta_any, dict):
        rc_any = meta_any.get("run_context")
        if rc_any is not None:
            _validate_run_context(rc_any, "--atoms meta")
            if isinstance(rc_any, dict):
                meta_ctx_norm = _normalize_run_context(rc_any)

    atoms = root.get("atoms", [])
    if not isinstance(atoms, list):
        die(f"atoms file malformed: expected list at paradox_field_v0.atoms: {atoms_path}")

    by_id: Dict[str, Dict[str, Any]] = {}
    for a in atoms:
        if not isinstance(a, dict):
            continue

        aid_raw = a.get("atom_id")
        atype = a.get("type")
        if not isinstance(aid_raw, str) or not aid_raw.strip():
            continue
        if not isinstance(atype, str) or not atype.strip():
            continue

        # Normalize atom_id keys to match edge-side normalization (src/dst IDs are stripped).
        aid = aid_raw.strip()

        # Fail-closed on collisions after normalization (whitespace-only differences).
        if aid in by_id:
            prev_raw = by_id[aid].get("atom_id")
            die(
                "atoms file has duplicate atom_id after strip-normalization: "
                f"{aid!r} (examples: {prev_raw!r} vs {aid_raw!r})"
            )

        by_id[aid] = a

    return by_id, meta_ctx_norm


def _edge_key(edge: Dict[str, Any]) -> Tuple[int, str, str]:
    sev = _severity_rank(edge.get("severity"))
    et = edge.get("type")
    eid = edge.get("edge_id")
    return (sev, str(et or ""), str(eid or ""))


def _req_str(d: Dict[str, Any], k: str, ctx: str) -> str:
    v = d.get(k)
    if not isinstance(v, str) or not v.strip():
        die(f"{ctx}.{k} must be a non-empty string")
    return v.strip()


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

    atoms_by_id: Dict[str, Dict[str, Any]] = {}
    field_ctx_norm: Optional[Dict[str, str]] = None
    if args.atoms_path:
        atoms_by_id, field_ctx_norm = _load_atoms_and_meta_run_context(args.atoms_path)

    seen_edge_ids = set()
    prev_key: Optional[Tuple[int, str, str]] = None
    edges_count = 0

    # run_context consistency (per file): if any edge has run_context, require all edges
    # to have run_context, and require normalized equality.
    saw_ctx = False
    saw_no_ctx = False
    first_ctx_norm: Optional[Dict[str, str]] = None
    first_ctx_line: int = 0

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

            src_atom_id = src_atom_id.strip()
            dst_atom_id = dst_atom_id.strip()

            # ---- Required for v0 tension edges
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

            # ---- Optional run_context validation + per-file consistency
            rc_any = edge.get("run_context")
            if rc_any is None:
                saw_no_ctx = True
            else:
                saw_ctx = True
                _validate_run_context(rc_any, f"line {line_no}")
                if not isinstance(rc_any, dict):
                    die(f"line {line_no}: run_context must be an object/dict")
                rc_norm = _normalize_run_context(rc_any)

                if first_ctx_norm is None:
                    first_ctx_norm = rc_norm
                    first_ctx_line = line_no
                elif rc_norm != first_ctx_norm:
                    die(
                        f"line {line_no}: run_context differs from earlier edge (line {first_ctx_line}); "
                        "mixed run_context within one edges file is not allowed"
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

                # Severity integrity: edge.severity must match the tension atom severity
                tens_sev = tens_atom.get("severity")
                if not isinstance(tens_sev, str) or tens_sev not in SEVERITY_ORDER:
                    die(
                        f"line {line_no}: tension atom has invalid severity "
                        f"(tension_atom_id={tension_atom_id!r}, got={tens_sev!r})"
                    )

                if tens_sev != severity:
                    die(
                        f"line {line_no}: edge.severity does not match tension atom severity "
                        f"(edge={severity!r} != tension={tens_sev!r}, tension_atom_id={tension_atom_id!r})"
                    )

                # Cross-check: edge endpoints must match tension atom evidence links
                tens_ev = tens_atom.get("evidence")
                if not isinstance(tens_ev, dict):
                    die(f"line {line_no}: tension atom evidence must be an object/dict")

                if edge_type == "gate_metric_tension":
                    exp_src = _req_str(tens_ev, "gate_atom_id", f"line {line_no}: tension.evidence")
                    exp_dst = _req_str(tens_ev, "metric_atom_id", f"line {line_no}: tension.evidence")

                    if exp_src != src_atom_id:
                        die(
                            f"line {line_no}: src_atom_id does not match tension.evidence.gate_atom_id "
                            f"({src_atom_id!r} != {exp_src!r})"
                        )
                    if exp_dst != dst_atom_id:
                        die(
                            f"line {line_no}: dst_atom_id does not match tension.evidence.metric_atom_id "
                            f"({dst_atom_id!r} != {exp_dst!r})"
                        )

                if edge_type == "gate_overlay_tension":
                    exp_src = _req_str(tens_ev, "gate_atom_id", f"line {line_no}: tension.evidence")
                    exp_dst = _req_str(tens_ev, "overlay_atom_id", f"line {line_no}: tension.evidence")

                    if exp_src != src_atom_id:
                        die(
                            f"line {line_no}: src_atom_id does not match tension.evidence.gate_atom_id "
                            f"({src_atom_id!r} != {exp_src!r})"
                        )
                    if exp_dst != dst_atom_id:
                        die(
                            f"line {line_no}: dst_atom_id does not match tension.evidence.overlay_atom_id "
                            f"({dst_atom_id!r} != {exp_dst!r})"
                        )

                # If src/dst aliases exist on the tension atom, they must agree too.
                if "src_atom_id" in tens_ev:
                    alias_src = _req_str(tens_ev, "src_atom_id", f"line {line_no}: tension.evidence")
                    if alias_src != src_atom_id:
                        die(
                            f"line {line_no}: src_atom_id does not match tension.evidence.src_atom_id "
                            f"({src_atom_id!r} != {alias_src!r})"
                        )
                if "dst_atom_id" in tens_ev:
                    alias_dst = _req_str(tens_ev, "dst_atom_id", f"line {line_no}: tension.evidence")
                    if alias_dst != dst_atom_id:
                        die(
                            f"line {line_no}: dst_atom_id does not match tension.evidence.dst_atom_id "
                            f"({dst_atom_id!r} != {alias_dst!r})"
                        )

                # If the tension atom has a rule string, it should match the edge rule.
                if "rule" in tens_ev and isinstance(tens_ev.get("rule"), str) and tens_ev.get("rule", "").strip():
                    tr = str(tens_ev.get("rule", "")).strip()
                    if tr and tr != rule.strip():
                        die(
                            f"line {line_no}: edge.rule does not match tension.evidence.rule "
                            f"({rule.strip()!r} != {tr!r})"
                        )

            edges_count += 1

    if saw_ctx and saw_no_ctx:
        die("mixed presence of run_context within one edges file is not allowed")

    # If the atoms file provides meta.run_context, enforce edges carry it and match it (C4.2).
    if field_ctx_norm is not None:
        if first_ctx_norm is None:
            die("atoms meta.run_context is present but edges are missing run_context (expected propagation)")
        if first_ctx_norm != field_ctx_norm:
            die(
                "edges run_context does not match atoms meta.run_context "
                f"(edges={first_ctx_norm} atoms={field_ctx_norm})"
            )

    print(f"[edges-contract] OK (edges={edges_count})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        raise SystemExit(0)


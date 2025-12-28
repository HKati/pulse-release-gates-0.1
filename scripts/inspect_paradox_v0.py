#!/usr/bin/env python3
"""
scripts/inspect_paradox_v0.py — evidence-first, deterministic inspector for paradox_field_v0 + paradox_edges_v0.

Why this exists
---------------
The paradox layer is intentionally *not* a classic "report simplifier".
It is evidence-first drift notation: atoms + co-occurrence edges (no causality).
This inspector produces a human-first Markdown summary while preserving:

- the *graph semantics* (tension atoms, endpoints, edges coverage)
- the *audit surface* (provenance pointers back to drift rows/files)
- the *fingerprint semantics* (run_context presence + parity hints)

This tool does NOT replace contract checks.
Use:
- scripts/check_paradox_field_v0_contract.py
- scripts/check_paradox_edges_v0_contract.py

Inputs
------
- paradox_field_v0.json (required)
- paradox_edges_v0.jsonl (optional)

Output
------
- Markdown summary (deterministic by default; no timestamps)

Usage
-----
  python scripts/inspect_paradox_v0.py \
    --field out/paradox_field_v0.json \
    --edges out/paradox_edges_v0.jsonl \
    --out out/paradox_summary_v0.md

If --out is omitted, prints to stdout.

Notes
-----
- Deterministic output: no wall-clock timestamps, stable sorting.
- "Top" ranking is a presentation choice; the summary always keeps IDs and drilldown pointers.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, Iterable, List, Optional, Tuple


SEVERITY_ORDER: Dict[str, int] = {"crit": 0, "warn": 1, "info": 2}

RUN_CONTEXT_ALLOWED_KEYS = {
    "run_pair_id",
    "status_sha1",
    "g_field_sha1",
    "transitions_json_sha1",
    "transitions_gate_csv_sha1",
    "transitions_metric_csv_sha1",
    "transitions_overlay_json_sha1",
}

TENSION_TYPES = ("gate_metric_tension", "gate_overlay_tension")


def die(msg: str, code: int = 2) -> None:
    raise SystemExit(f"[inspect-paradox] {msg}")


def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _read_jsonl(path: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception as e:
                die(f"invalid JSONL at line {line_no}: {e}")
            if not isinstance(obj, dict):
                die(f"edge line {line_no}: expected JSON object")
            out.append(obj)
    return out


def _severity_rank(label: Any) -> int:
    if not isinstance(label, str):
        return 99
    return SEVERITY_ORDER.get(label.strip(), 99)


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None or x == "":
            return None
        if isinstance(x, bool):
            return None
        v = float(x)
        if v != v or v in (float("inf"), float("-inf")):
            return None
        return v
    except Exception:
        return None


def _normalize_run_context(run_ctx: Any) -> Optional[Dict[str, str]]:
    if not isinstance(run_ctx, dict):
        return None
    norm: Dict[str, str] = {}
    for k in sorted(RUN_CONTEXT_ALLOWED_KEYS):
        v = run_ctx.get(k)
        if isinstance(v, str) and v.strip():
            norm[k] = v.strip()
    return norm if norm else None


def _basename(x: Any) -> str:
    if not isinstance(x, str):
        return ""
    return os.path.basename(x.strip())


def _md_code_block(s: str, lang: str = "") -> List[str]:
    fence = f"```{lang}".rstrip()
    return [fence, s.rstrip(), "```"]


def _md_table(headers: List[str], rows: List[List[str]]) -> List[str]:
    # Minimal markdown table builder (deterministic).
    if not headers:
        return []
    out: List[str] = []
    out.append("| " + " | ".join(headers) + " |")
    out.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for r in rows:
        rr = r + [""] * (len(headers) - len(r))
        out.append("| " + " | ".join(rr[: len(headers)]) + " |")
    return out


def _load_field(field_path: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    if not os.path.isfile(field_path):
        die(f"--field not found: {field_path}")
    obj = _read_json(field_path)
    if not isinstance(obj, dict):
        die("--field must be a JSON object at root")

    root = obj.get("paradox_field_v0", obj)
    if not isinstance(root, dict):
        die("--field malformed: expected object at paradox_field_v0")

    meta = root.get("meta")
    if meta is None:
        meta = {}
    if not isinstance(meta, dict):
        die("field meta must be an object/dict when present")

    atoms_any = root.get("atoms")
    if not isinstance(atoms_any, list):
        die("field atoms must be a list at paradox_field_v0.atoms")
    atoms: List[Dict[str, Any]] = []
    for i, a in enumerate(atoms_any):
        if not isinstance(a, dict):
            die(f"field atoms[{i}] must be an object/dict")
        atoms.append(a)

    return meta, atoms


def _index_atoms(atoms: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    by_id: Dict[str, Dict[str, Any]] = {}
    for a in atoms:
        aid = a.get("atom_id")
        if not isinstance(aid, str) or not aid.strip():
            continue
        key = aid.strip()
        # Keep first; contract should prevent dupes. If dupes slip in, prefer determinism.
        if key not in by_id:
            by_id[key] = a
    return by_id


def _get_atom_type(a: Optional[Dict[str, Any]]) -> str:
    if not isinstance(a, dict):
        return ""
    t = a.get("type")
    return t.strip() if isinstance(t, str) else ""


def _get_atom_severity(a: Optional[Dict[str, Any]]) -> str:
    if not isinstance(a, dict):
        return ""
    s = a.get("severity")
    return s.strip() if isinstance(s, str) else ""


def _get_evidence(a: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(a, dict):
        return {}
    ev = a.get("evidence")
    return ev if isinstance(ev, dict) else {}


def _source_hint(a: Optional[Dict[str, Any]]) -> str:
    ev = _get_evidence(a)
    src = ev.get("source")
    if not isinstance(src, dict):
        return ""
    # Prefer (file,row_index) style pointers.
    if "gate_drift_csv" in src:
        fn = _basename(src.get("gate_drift_csv"))
        ri = src.get("row_index")
        if isinstance(ri, int):
            return f"{fn}#row{ri}"
        return fn
    if "metric_drift_csv" in src:
        fn = _basename(src.get("metric_drift_csv"))
        ri = src.get("row_index")
        if isinstance(ri, int):
            return f"{fn}#row{ri}"
        return fn
    if "overlay_drift_json" in src:
        fn = _basename(src.get("overlay_drift_json"))
        # overlay_name is also helpful
        on = src.get("overlay_name")
        if isinstance(on, str) and on.strip():
            return f"{fn}::{on.strip()}"
        return fn
    return ""


def _gate_brief(gate_atom: Optional[Dict[str, Any]]) -> Tuple[str, str]:
    """
    Returns (gate_id, gate_status_delta_str)
    """
    ev = _get_evidence(gate_atom)
    g = ev.get("gate")
    if not isinstance(g, dict):
        return ("", "")
    gid = g.get("gate_id")
    gid_s = gid.strip() if isinstance(gid, str) else ""
    sa = g.get("status_a")
    sb = g.get("status_b")
    sa_s = sa.strip() if isinstance(sa, str) else ""
    sb_s = sb.strip() if isinstance(sb, str) else ""
    if gid_s and (sa_s or sb_s):
        return (gid_s, f"{sa_s or '?'} → {sb_s or '?'}")
    return (gid_s, "")


def _metric_brief(metric_atom: Optional[Dict[str, Any]]) -> Tuple[str, Optional[float], Optional[float], Optional[float], Optional[float]]:
    """
    Returns (metric_name, a, b, delta, rel_delta)
    """
    ev = _get_evidence(metric_atom)
    m = ev.get("metric")
    if not isinstance(m, dict):
        return ("", None, None, None, None)
    name = m.get("name")
    a = _safe_float(m.get("a"))
    b = _safe_float(m.get("b"))
    delta = _safe_float(m.get("delta"))
    rel_delta = _safe_float(m.get("rel_delta"))
    return (name.strip() if isinstance(name, str) else "", a, b, delta, rel_delta)


def _overlay_brief(overlay_atom: Optional[Dict[str, Any]]) -> Tuple[str, int]:
    """
    Returns (overlay_name, changed_keys_count)
    """
    ev = _get_evidence(overlay_atom)
    o = ev.get("overlay")
    if not isinstance(o, dict):
        return ("", 0)
    name = o.get("name")
    name_s = name.strip() if isinstance(name, str) else ""
    tld = o.get("top_level_diff")
    if not isinstance(tld, dict):
        return (name_s, 0)
    ck = tld.get("changed_keys")
    if isinstance(ck, list):
        return (name_s, len(ck))
    return (name_s, 0)


def _format_float(x: Optional[float], digits: int = 6) -> str:
    if x is None:
        return ""
    # stable formatting (avoid scientific noise unless needed)
    s = f"{x:.{digits}g}"
    return s


def _format_run_context_block(label: str, ctx_norm: Optional[Dict[str, str]]) -> List[str]:
    if not ctx_norm:
        return [f"- {label}: (missing)"]
    rpid = ctx_norm.get("run_pair_id", "")
    out = [f"- {label}: `run_pair_id={rpid}`"]
    # include the rest as a tiny JSON block for auditability
    payload = {k: ctx_norm[k] for k in sorted(ctx_norm.keys())}
    out.append("")
    out.extend(_md_code_block(json.dumps(payload, indent=2, sort_keys=True), lang="json"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Inspect paradox_field_v0 + paradox_edges_v0 (human-first summary).")
    ap.add_argument("--field", required=True, help="Path to paradox_field_v0.json")
    ap.add_argument("--edges", default="", help="Optional path to paradox_edges_v0.jsonl")
    ap.add_argument("--out", default="", help="Optional output path for Markdown (prints to stdout if omitted)")
    ap.add_argument("--top", type=int, default=10, help="Top-N tensions/edges to show (default: 10)")
    ap.add_argument(
        "--no-json-index",
        action="store_true",
        help="Do not embed the machine-readable JSON summary index at the end",
    )
    args = ap.parse_args()

    if args.top < 1:
        die("--top must be >= 1")

    meta, atoms = _load_field(args.field)
    atoms_by_id = _index_atoms(atoms)

    # Field run_context
    field_ctx_norm = _normalize_run_context(meta.get("run_context"))

    edges: List[Dict[str, Any]] = []
    edges_by_tension: Dict[str, List[Dict[str, Any]]] = {}
    edges_ctx_norm: Optional[Dict[str, str]] = None
    edges_path = args.edges.strip()

    if edges_path:
        if not os.path.isfile(edges_path):
            die(f"--edges not found: {edges_path}")
        edges = _read_jsonl(edges_path)

        # Index edges by tension_atom_id for drilldown.
        for e in edges:
            tid = e.get("tension_atom_id")
            if isinstance(tid, str) and tid.strip():
                edges_by_tension.setdefault(tid.strip(), []).append(e)

        # Normalize run_context from first edge that has it.
        for e in edges:
            rc = e.get("run_context")
            norm = _normalize_run_context(rc)
            if norm:
                edges_ctx_norm = norm
                break

    # ---- Counts
    atoms_total = len(atoms)
    atoms_by_sev: Dict[str, int] = {"crit": 0, "warn": 0, "info": 0}
    atoms_by_type: Dict[str, int] = {}
    atoms_by_type_sev: Dict[Tuple[str, str], int] = {}

    for a in atoms:
        typ = _get_atom_type(a) or ""
        sev = _get_atom_severity(a) or ""
        if sev in atoms_by_sev:
            atoms_by_sev[sev] += 1
        atoms_by_type[typ] = atoms_by_type.get(typ, 0) + 1
        atoms_by_type_sev[(typ, sev)] = atoms_by_type_sev.get((typ, sev), 0) + 1

    edges_total = len(edges)
    edges_by_sev: Dict[str, int] = {"crit": 0, "warn": 0, "info": 0}
    edges_by_type: Dict[str, int] = {}
    edges_by_type_sev: Dict[Tuple[str, str], int] = {}

    for e in edges:
        typ = e.get("type")
        sev = e.get("severity")
        typ_s = typ.strip() if isinstance(typ, str) else ""
        sev_s = sev.strip() if isinstance(sev, str) else ""
        if sev_s in edges_by_sev:
            edges_by_sev[sev_s] += 1
        edges_by_type[typ_s] = edges_by_type.get(typ_s, 0) + 1
        edges_by_type_sev[(typ_s, sev_s)] = edges_by_type_sev.get((typ_s, sev_s), 0) + 1

    # ---- Tensions extraction
    tensions: List[Dict[str, Any]] = []
    for a in atoms:
        typ = _get_atom_type(a)
        if typ in TENSION_TYPES:
            tensions.append(a)

    # Build ranked views for the two tension types.
    metric_tensions: List[Dict[str, Any]] = []
    overlay_tensions: List[Dict[str, Any]] = []
    for t in tensions:
        if _get_atom_type(t) == "gate_metric_tension":
            metric_tensions.append(t)
        elif _get_atom_type(t) == "gate_overlay_tension":
            overlay_tensions.append(t)

    def _metric_tension_rank(t: Dict[str, Any]) -> Tuple[int, int, float, str, str, str]:
        sev = _get_atom_severity(t)
        sev_r = _severity_rank(sev)

        ev = _get_evidence(t)
        mid = ev.get("metric_atom_id")
        mid_s = mid.strip() if isinstance(mid, str) else ""
        m_atom = atoms_by_id.get(mid_s)
        m_sev_r = _severity_rank(_get_atom_severity(m_atom))

        m_name, _, _, delta, _ = _metric_brief(m_atom)
        abs_delta = abs(delta) if delta is not None else 0.0

        gid = ev.get("gate_atom_id")
        gid_s = gid.strip() if isinstance(gid, str) else ""
        g_atom = atoms_by_id.get(gid_s)
        gate_id, _ = _gate_brief(g_atom)

        tid = t.get("atom_id")
        tid_s = tid.strip() if isinstance(tid, str) else ""

        return (sev_r, m_sev_r, -abs_delta, gate_id, m_name, tid_s)

    def _overlay_tension_rank(t: Dict[str, Any]) -> Tuple[int, int, int, str, str, str]:
        sev = _get_atom_severity(t)
        sev_r = _severity_rank(sev)

        ev = _get_evidence(t)
        oid = ev.get("overlay_atom_id")
        oid_s = oid.strip() if isinstance(oid, str) else ""
        o_atom = atoms_by_id.get(oid_s)
        o_sev_r = _severity_rank(_get_atom_severity(o_atom))

        oname, changed_n = _overlay_brief(o_atom)

        gid = ev.get("gate_atom_id")
        gid_s = gid.strip() if isinstance(gid, str) else ""
        g_atom = atoms_by_id.get(gid_s)
        gate_id, _ = _gate_brief(g_atom)

        tid = t.get("atom_id")
        tid_s = tid.strip() if isinstance(tid, str) else ""

        # More changed keys => higher salience, so sort by -changed_n.
        return (sev_r, o_sev_r, -changed_n, gate_id, oname, tid_s)

    metric_tensions.sort(key=_metric_tension_rank)
    overlay_tensions.sort(key=_overlay_tension_rank)

    # ---- Coverage checks (inspector-level hints)
    tension_ids = {str(t.get("atom_id", "")).strip() for t in tensions if isinstance(t.get("atom_id"), str)}
    edge_tension_ids = {str(e.get("tension_atom_id", "")).strip() for e in edges if isinstance(e.get("tension_atom_id"), str)}
    missing_edges = sorted([tid for tid in (tension_ids - edge_tension_ids) if tid])
    unknown_edges = sorted([tid for tid in (edge_tension_ids - tension_ids) if tid])

    # ---- Compose Markdown
    lines: List[str] = []
    lines.append("# Paradox Inspector v0 (PULSE)")
    lines.append("")
    lines.append("Evidence-first summary of `paradox_field_v0` atoms and optional `paradox_edges_v0` edges.")
    lines.append("")
    lines.append("> This summary is **not** a causality claim. Tensions/edges are **co-occurrence links** derived from drift evidence.")
    lines.append("")

    # Inputs
    lines.append("## Inputs")
    lines.append("")
    lines.append(f"- field: `{args.field}`")
    if edges_path:
        lines.append(f"- edges: `{edges_path}`")
    else:
        lines.append("- edges: (not provided)")
    lines.append("")

    # Run contexts
    lines.append("## Run context fingerprints")
    lines.append("")
    lines.extend(_format_run_context_block("field.meta.run_context", field_ctx_norm))
    lines.append("")
    if edges_path:
        lines.extend(_format_run_context_block("edges.run_context (first present)", edges_ctx_norm))
        lines.append("")
        # Parity hint (informational; contract enforces in --atoms mode when edges non-empty)
        if field_ctx_norm and edges_total > 0:
            parity = "MATCH" if edges_ctx_norm == field_ctx_norm else "MISMATCH"
            lines.append(f"- parity hint (field ↔ edges): **{parity}**")
            lines.append("")
    else:
        lines.append("- edges run_context: (edges not provided)")
        lines.append("")

    # Counts overview
    lines.append("## Counts")
    lines.append("")
    rows = [
        ["atoms", str(atoms_total), str(atoms_by_sev.get("crit", 0)), str(atoms_by_sev.get("warn", 0)), str(atoms_by_sev.get("info", 0))],
        ["tension atoms", str(len(tensions)), "-", "-", "-"],
    ]
    if edges_path:
        rows.append(["edges", str(edges_total), str(edges_by_sev.get("crit", 0)), str(edges_by_sev.get("warn", 0)), str(edges_by_sev.get("info", 0))])
    lines.extend(_md_table(["layer", "total", "crit", "warn", "info"], rows))
    lines.append("")

    # Type × severity table (compact, still nuanced)
    lines.append("### Atoms by type (severity breakdown)")
    lines.append("")
    all_types = sorted([t for t in atoms_by_type.keys() if t])
    type_rows: List[List[str]] = []
    for typ in all_types:
        c_crit = atoms_by_type_sev.get((typ, "crit"), 0)
        c_warn = atoms_by_type_sev.get((typ, "warn"), 0)
        c_info = atoms_by_type_sev.get((typ, "info"), 0)
        total = atoms_by_type.get(typ, 0)
        type_rows.append([f"`{typ}`", str(c_crit), str(c_warn), str(c_info), str(total)])
    lines.extend(_md_table(["type", "crit", "warn", "info", "total"], type_rows))
    lines.append("")

    if edges_path:
        lines.append("### Edges by type (severity breakdown)")
        lines.append("")
        e_types = sorted([t for t in edges_by_type.keys() if t])
        e_rows: List[List[str]] = []
        for typ in e_types:
            c_crit = edges_by_type_sev.get((typ, "crit"), 0)
            c_warn = edges_by_type_sev.get((typ, "warn"), 0)
            c_info = edges_by_type_sev.get((typ, "info"), 0)
            total = edges_by_type.get(typ, 0)
            e_rows.append([f"`{typ}`", str(c_crit), str(c_warn), str(c_info), str(total)])
        lines.extend(_md_table(["type", "crit", "warn", "info", "total"], e_rows))
        lines.append("")

    # Coverage hints
    if edges_path:
        lines.append("## Edge coverage hints")
        lines.append("")
        lines.append(f"- tension atoms in field: `{len(tension_ids)}`")
        lines.append(f"- unique tension_atom_id in edges: `{len(edge_tension_ids)}`")
        lines.append("")
        if missing_edges:
            lines.append(f"- missing edges for `{len(missing_edges)}` tension atoms (showing up to 10):")
            for tid in missing_edges[:10]:
                lines.append(f"  - `{tid}`")
            lines.append("")
        else:
            lines.append("- missing edges: (none)")
            lines.append("")
        if unknown_edges:
            lines.append(f"- edges reference unknown tension_atom_id `{len(unknown_edges)}` (showing up to 10):")
            for tid in unknown_edges[:10]:
                lines.append(f"  - `{tid}`")
            lines.append("")
        else:
            lines.append("- unknown edges: (none)")
            lines.append("")

    # Top tensions (with drilldown pointers)
    lines.append("## Top tensions (evidence-first, drilldown preserved)")
    lines.append("")
    lines.append(f"Showing top `{args.top}` per tension type (ranking is a presentation layer; IDs remain authoritative).")
    lines.append("")

    def _emit_metric_tension(t: Dict[str, Any]) -> List[str]:
        out: List[str] = []
        tid = str(t.get("atom_id", "")).strip()
        sev = _get_atom_severity(t) or "?"

        ev = _get_evidence(t)
        gate_atom_id = str(ev.get("gate_atom_id", "")).strip()
        metric_atom_id = str(ev.get("metric_atom_id", "")).strip()

        g_atom = atoms_by_id.get(gate_atom_id)
        m_atom = atoms_by_id.get(metric_atom_id)

        gate_id, gate_delta = _gate_brief(g_atom)
        m_name, a, b, delta, rel_delta = _metric_brief(m_atom)

        g_src = _source_hint(g_atom)
        m_src = _source_hint(m_atom)

        m_sev = _get_atom_severity(m_atom) or "?"
        g_sev = _get_atom_severity(g_atom) or "?"

        delta_s = _format_float(delta)
        rel_s = _format_float(rel_delta)
        a_s = _format_float(a)
        b_s = _format_float(b)

        title = str(t.get("title", "")).strip()

        out.append(f"- **[{sev}]** `{gate_id or 'gate'}` × `{m_name or 'metric'}`  (tension_id=`{tid}`)")
        if title:
            out.append(f"  - title: {title}")
        if gate_delta:
            out.append(f"  - gate: `{gate_id}` {gate_delta} (gate_sev={g_sev})")
        else:
            out.append(f"  - gate_atom_id: `{gate_atom_id}` (gate_sev={g_sev})")
        out.append(
            f"  - metric: `{m_name}` a={a_s} b={b_s} Δ={delta_s} relΔ={rel_s} (metric_sev={m_sev})"
        )
        out.append(f"  - links: gate_atom_id=`{gate_atom_id}`, metric_atom_id=`{metric_atom_id}`")
        # Edge ids (if provided)
        if edges_path and tid:
            es = edges_by_tension.get(tid, [])
            if es:
                eids = sorted([str(e.get("edge_id", "")).strip() for e in es if isinstance(e.get("edge_id"), str)])
                out.append(f"  - edges: {', '.join([f'`{x}`' for x in eids if x])}")
        # Provenance pointers
        prov_bits = []
        if g_src:
            prov_bits.append(f"gate_src={g_src}")
        if m_src:
            prov_bits.append(f"metric_src={m_src}")
        if prov_bits:
            out.append(f"  - provenance: " + ", ".join(prov_bits))
        return out

    def _emit_overlay_tension(t: Dict[str, Any]) -> List[str]:
        out: List[str] = []
        tid = str(t.get("atom_id", "")).strip()
        sev = _get_atom_severity(t) or "?"

        ev = _get_evidence(t)
        gate_atom_id = str(ev.get("gate_atom_id", "")).strip()
        overlay_atom_id = str(ev.get("overlay_atom_id", "")).strip()

        g_atom = atoms_by_id.get(gate_atom_id)
        o_atom = atoms_by_id.get(overlay_atom_id)

        gate_id, gate_delta = _gate_brief(g_atom)
        oname, changed_n = _overlay_brief(o_atom)

        # prefer the sample on the tension evidence (already guardrailed)
        overlay_sample = ""
        ov_block = ev.get("overlay")
        if isinstance(ov_block, dict):
            cks = ov_block.get("changed_keys_sample")
            if isinstance(cks, list) and cks:
                overlay_sample = ", ".join([str(x) for x in cks])

        g_src = _source_hint(g_atom)
        o_src = _source_hint(o_atom)

        o_sev = _get_atom_severity(o_atom) or "?"
        g_sev = _get_atom_severity(g_atom) or "?"

        title = str(t.get("title", "")).strip()

        out.append(f"- **[{sev}]** `{gate_id or 'gate'}` × `{oname or 'overlay'}`  (tension_id=`{tid}`)")
        if title:
            out.append(f"  - title: {title}")
        if gate_delta:
            out.append(f"  - gate: `{gate_id}` {gate_delta} (gate_sev={g_sev})")
        else:
            out.append(f"  - gate_atom_id: `{gate_atom_id}` (gate_sev={g_sev})")
        out.append(f"  - overlay: `{oname}` changed_keys={changed_n} (overlay_sev={o_sev})")
        if overlay_sample:
            out.append(f"  - changed_keys_sample: {overlay_sample}")
        out.append(f"  - links: gate_atom_id=`{gate_atom_id}`, overlay_atom_id=`{overlay_atom_id}`")
        if edges_path and tid:
            es = edges_by_tension.get(tid, [])
            if es:
                eids = sorted([str(e.get("edge_id", "")).strip() for e in es if isinstance(e.get("edge_id"), str)])
                out.append(f"  - edges: {', '.join([f'`{x}`' for x in eids if x])}")
        prov_bits = []
        if g_src:
            prov_bits.append(f"gate_src={g_src}")
        if o_src:
            prov_bits.append(f"overlay_src={o_src}")
        if prov_bits:
            out.append(f"  - provenance: " + ", ".join(prov_bits))
        return out

    # Metric tensions section
    lines.append("### `gate_metric_tension`")
    lines.append("")
    if not metric_tensions:
        lines.append("(none)")
        lines.append("")
    else:
        for t in metric_tensions[: args.top]:
            lines.extend(_emit_metric_tension(t))
        lines.append("")

    # Overlay tensions section
    lines.append("### `gate_overlay_tension`")
    lines.append("")
    if not overlay_tensions:
        lines.append("(none)")
        lines.append("")
    else:
        for t in overlay_tensions[: args.top]:
            lines.extend(_emit_overlay_tension(t))
        lines.append("")

    # Machine-readable summary index (small, stable)
    if not args.no_json_index:
        summary_index: Dict[str, Any] = {
            "version": "inspect_paradox_v0",
            "inputs": {
                "field": args.field,
                "edges": edges_path or "",
            },
            "run_context": {
                "field": field_ctx_norm or {},
                "edges_first_present": edges_ctx_norm or {},
            },
            "counts": {
                "atoms_total": atoms_total,
                "atoms_by_severity": {k: atoms_by_sev[k] for k in ("crit", "warn", "info")},
                "atoms_by_type": {k: atoms_by_type[k] for k in sorted(atoms_by_type.keys()) if k},
                "tension_atoms_total": len(tensions),
                "edges_total": edges_total,
            },
            "coverage": {
                "tension_ids_in_field": len(tension_ids),
                "unique_tension_ids_in_edges": len(edge_tension_ids),
                "missing_edges_count": len(missing_edges),
                "unknown_edges_count": len(unknown_edges),
            },
            "top": {
                "metric_tension_ids": [str(t.get("atom_id", "")).strip() for t in metric_tensions[: args.top]],
                "overlay_tension_ids": [str(t.get("atom_id", "")).strip() for t in overlay_tensions[: args.top]],
            },
        }

        lines.append("## Summary index (machine-readable)")
        lines.append("")
        lines.extend(_md_code_block(json.dumps(summary_index, indent=2, sort_keys=True), lang="json"))
        lines.append("")

    out_md = "\n".join(lines).rstrip() + "\n"

    if args.out.strip():
        out_path = args.out.strip()
        d = os.path.dirname(os.path.abspath(out_path))
        if d:
            os.makedirs(d, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(out_md)
        print(f"[inspect-paradox] wrote: {out_path}")
    else:
        sys.stdout.write(out_md)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        raise SystemExit(0)

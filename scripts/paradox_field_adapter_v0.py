
#!/usr/bin/env python3
"""
paradox_field_adapter_v0 — stdlib-only generator for paradox_field_v0.json.

Goal (v0):
  - Produce a stable paradox_field artefact (skeleton + optional atoms from transitions drift).
  - Deterministic ordering and audit-friendly evidence payloads.
  - Evidence-first: atoms encode observed deltas/co-occurrences; no new truth/causality.

Output:
  { "paradox_field_v0": { "meta": {...}, "atoms": [...] } }

Determinism:
  - By default, no wall-clock timestamp is emitted.
  - You can include a timestamp explicitly via --created-at or --emit-created-at-now.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple


# Metric drift severity thresholds (v0 contract)
METRIC_ABS_WARN = 0.01
METRIC_ABS_CRIT = 0.05
METRIC_REL_WARN = 0.01
METRIC_REL_CRIT = 0.05

# V0 guardrails against atom explosion
MAX_METRIC_ATOMS = 10
MAX_GATE_METRIC_TENSIONS = 50
MAX_GATE_OVERLAY_TENSIONS = 50
OVERLAY_TENSION_ALLOWLIST = {"g_field_v0", "paradox_field_v0"}
OVERLAY_CHANGED_KEYS_SAMPLE = 12


def _sha1_file(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha1_text(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def _mkdirp_for_file(path: str) -> None:
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)


def _require_file(path: str, label: str) -> None:
    if not os.path.isfile(path):
        raise SystemExit(f"[paradox_field_adapter_v0] {label} not found: {path}")


def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _read_csv(path: str) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


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


def _safe_bool(x: Any) -> Optional[bool]:
    if isinstance(x, bool):
        return x
    if isinstance(x, str):
        s = x.strip().lower()
        if s in ("true", "1", "yes", "y"):
            return True
        if s in ("false", "0", "no", "n"):
            return False
    return None


def _atom_id(atom_type: str, key: str, a_sha1: str, b_sha1: str) -> str:
    # short stable id
    raw = f"{atom_type}|{key}|{a_sha1}|{b_sha1}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def _tension_atom_id(atom_type: str, src_atom_id: str, dst_atom_id: str) -> str:
    # Stable, short id derived from linked atom ids (not from run context).
    raw = f"{atom_type}:{src_atom_id}:{dst_atom_id}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def _severity_rank(label: str) -> Tuple[int, str]:
    # We want critical items first in the output.
    order = {"crit": 0, "warn": 1, "info": 2}
    return (order.get(label, 99), label)


def _max_severity(a: str, b: str) -> str:
    # "max" in terms of importance => smaller rank wins (crit > warn > info)
    ra = _severity_rank(a)[0]
    rb = _severity_rank(b)[0]
    return a if ra <= rb else b


def _metric_severity(delta: Optional[float], rel_delta: Optional[float]) -> str:
    if delta is None:
        return "info"

    if (abs(delta) >= METRIC_ABS_CRIT) or (rel_delta is not None and abs(rel_delta) >= METRIC_REL_CRIT):
        return "crit"
    if (abs(delta) >= METRIC_ABS_WARN) or (rel_delta is not None and abs(rel_delta) >= METRIC_REL_WARN):
        return "warn"
    return "info"


def _read_transitions_dir(path: str) -> Dict[str, Any]:
    gate_csv = os.path.join(path, "pulse_gate_drift_v0.csv")
    metric_csv = os.path.join(path, "pulse_metric_drift_v0.csv")
    overlay_json = os.path.join(path, "pulse_overlay_drift_v0.json")
    transitions_json = os.path.join(path, "pulse_transitions_v0.json")

    _require_file(gate_csv, "pulse_gate_drift_v0.csv")
    _require_file(metric_csv, "pulse_metric_drift_v0.csv")
    _require_file(overlay_json, "pulse_overlay_drift_v0.json")

    transitions = _read_json(transitions_json) if os.path.isfile(transitions_json) else {}

    return {
        "gate_csv": gate_csv,
        "metric_csv": metric_csv,
        "overlay_json": overlay_json,
        "transitions_json": transitions_json if os.path.isfile(transitions_json) else "",
        "gate_rows": _read_csv(gate_csv),
        "metric_rows": _read_csv(metric_csv),
        "overlay": _read_json(overlay_json),
        "transitions": transitions,
    }


def _extract_run_sha1s(transitions: Dict[str, Any]) -> Tuple[str, str]:
    run_a = transitions.get("run_a") if isinstance(transitions.get("run_a"), dict) else {}
    run_b = transitions.get("run_b") if isinstance(transitions.get("run_b"), dict) else {}
    a_sha1 = run_a.get("status_sha1") if isinstance(run_a.get("status_sha1"), str) else ""
    b_sha1 = run_b.get("status_sha1") if isinstance(run_b.get("status_sha1"), str) else ""
    return a_sha1, b_sha1


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate paradox_field_v0.json (v0 skeleton + atoms).")
    ap.add_argument("--status", default="", help="Optional status.json path (adds sha1/meta).")
    ap.add_argument("--g-field", default="", help="Optional g_field_v0.json path (adds sha1/meta).")
    ap.add_argument(
        "--transitions-dir",
        default="",
        help="Optional transitions directory containing pulse_*_drift_v0 files.",
    )
    ap.add_argument(
        "--out",
        default="PULSE_safe_pack_v0/artifacts/paradox_field_v0.json",
        help="Output path for paradox_field_v0.json",
    )

    # Deterministic by default: do not emit current time unless asked.
    ap.add_argument(
        "--created-at",
        type=int,
        default=None,
        help="Optional unix timestamp to include in meta (deterministic if set).",
    )
    ap.add_argument(
        "--emit-created-at-now",
        action="store_true",
        help="Include current unix time in meta (non-deterministic).",
    )

    args = ap.parse_args()

    meta: Dict[str, Any] = {
        "tool": "scripts/paradox_field_adapter_v0.py",
        "version": "v0",
        "contract": {
            "atoms_sorted_by": ["severity", "type", "atom_id"],
            "severity_order": ["crit", "warn", "info"],
            "metric_thresholds": {
                "abs_warn": METRIC_ABS_WARN,
                "abs_crit": METRIC_ABS_CRIT,
                "rel_warn": METRIC_REL_WARN,
                "rel_crit": METRIC_REL_CRIT,
            },
            "tension_overlays_allowlist": sorted(OVERLAY_TENSION_ALLOWLIST),
        },
    }

    if args.created_at is not None:
        meta["created_at"] = int(args.created_at)
    elif args.emit_created_at_now:
        meta["created_at"] = int(time.time())

    if args.status:
        _require_file(args.status, "status.json")
        meta["status_path"] = args.status
        meta["status_sha1"] = _sha1_file(args.status)

    if args.g_field:
        _require_file(args.g_field, "g_field_v0.json")
        meta["g_field_path"] = args.g_field
        meta["g_field_sha1"] = _sha1_file(args.g_field)

    atoms: List[Dict[str, Any]] = []

    # Indexes for tension linking
    gate_atoms_by_gate_id: Dict[str, Dict[str, Any]] = {}
    metric_atoms_by_metric: Dict[str, Dict[str, Any]] = {}
    overlay_atoms_by_name: Dict[str, Dict[str, Any]] = {}

    if args.transitions_dir:
        t = _read_transitions_dir(args.transitions_dir)
        meta["transitions_dir"] = args.transitions_dir
        meta["transitions_gate_csv_sha1"] = _sha1_file(t["gate_csv"])
        meta["transitions_metric_csv_sha1"] = _sha1_file(t["metric_csv"])
        meta["transitions_overlay_json_sha1"] = _sha1_file(t["overlay_json"])
        if t["transitions_json"]:
            meta["transitions_json_sha1"] = _sha1_file(t["transitions_json"])

        run_a_sha1, run_b_sha1 = _extract_run_sha1s(t["transitions"])

        # Fallback context fingerprint for atom IDs when run sha1s are not present.
        ctx = _sha1_text(
            meta["transitions_gate_csv_sha1"]
            + meta["transitions_metric_csv_sha1"]
            + meta["transitions_overlay_json_sha1"]
            + str(meta.get("transitions_json_sha1", ""))
        )
        a_id_ctx = run_a_sha1 or ctx
        b_id_ctx = run_b_sha1 or ctx

        # ---- Gate flips -> gate_flip atoms
        for row in t["gate_rows"]:
            flip = str(row.get("flip", "")).strip().lower()
            if flip not in ("1", "true"):
                continue

            gate_id = str(row.get("gate_id", "")).strip()
            if not gate_id:
                continue

            status_a = str(row.get("status_a", "")).strip()
            status_b = str(row.get("status_b", "")).strip()
            title = f"Gate flip: {gate_id} {status_a or '?'} → {status_b or '?'}"

            atom = {
                "atom_id": _atom_id("gate_flip", gate_id, a_id_ctx, b_id_ctx),
                "type": "gate_flip",
                "severity": "crit",
                "title": title,
                "refs": {"gates": [gate_id], "metrics": [], "overlays": []},
                "evidence": {
                    "source": {"gate_drift_csv": os.path.basename(t["gate_csv"])},
                    "gate": {
                        "gate_id": gate_id,
                        "group": row.get("group", "") or "",
                        "status_a": status_a,
                        "status_b": status_b,
                        "pass_a": _safe_bool(row.get("pass_a")) if row.get("pass_a", "") != "" else "",
                        "pass_b": _safe_bool(row.get("pass_b")) if row.get("pass_b", "") != "" else "",
                        "flip": 1,
                        "value_a": row.get("value_a", "") or "",
                        "value_b": row.get("value_b", "") or "",
                        "threshold": row.get("threshold", "") or "",
                        "notes_a": row.get("notes_a", "") or "",
                        "notes_b": row.get("notes_b", "") or "",
                    },
                    "presence": {
                        "present_a": row.get("present_a", "") or "",
                        "present_b": row.get("present_b", "") or "",
                    },
                },
            }
            atoms.append(atom)
            gate_atoms_by_gate_id[gate_id] = atom

        # ---- Metric deltas -> metric_delta atoms (top N by |delta|)
        metric_candidates: List[Tuple[str, Optional[float], Optional[float], float, Optional[float], str, str]] = []
        for row in t["metric_rows"]:
            metric = str(row.get("metric", "")).strip()
            if not metric:
                continue

            delta = _safe_float(row.get("delta"))
            if delta is None:
                continue

            a_val = _safe_float(row.get("a"))
            b_val = _safe_float(row.get("b"))
            rel_delta = _safe_float(row.get("rel_delta"))
            present_a = str(row.get("present_a", "")).strip()
            present_b = str(row.get("present_b", "")).strip()
            metric_candidates.append((metric, a_val, b_val, delta, rel_delta, present_a, present_b))

        metric_candidates.sort(key=lambda x: abs(x[3]), reverse=True)

        for metric, a_val, b_val, delta, rel_delta, present_a, present_b in metric_candidates[:MAX_METRIC_ATOMS]:
            severity = _metric_severity(delta, rel_delta)
            title = f"Metric drift: {metric} Δ={delta}"

            atom = {
                "atom_id": _atom_id("metric_delta", metric, a_id_ctx, b_id_ctx),
                "type": "metric_delta",
                "severity": severity,
                "title": title,
                "refs": {"gates": [], "metrics": [metric], "overlays": []},
                "evidence": {
                    "source": {"metric_drift_csv": os.path.basename(t["metric_csv"])},
                    "metric": {
                        "name": metric,
                        "a": a_val if a_val is not None else "",
                        "b": b_val if b_val is not None else "",
                        "delta": delta,
                        "rel_delta": rel_delta if rel_delta is not None else "",
                    },
                    "presence": {"present_a": present_a, "present_b": present_b},
                    "thresholds": {
                        "abs_warn": METRIC_ABS_WARN,
                        "abs_crit": METRIC_ABS_CRIT,
                        "rel_warn": METRIC_REL_WARN,
                        "rel_crit": METRIC_REL_CRIT,
                    },
                },
            }
            atoms.append(atom)
            metric_atoms_by_metric[metric] = atom

        # ---- Overlay changes -> overlay_change atoms
        overlay_obj = t["overlay"]
        if isinstance(overlay_obj, dict):
            for overlay_name in sorted(overlay_obj.keys(), key=lambda x: str(x)):
                overlay_block = overlay_obj.get(overlay_name)
                if not isinstance(overlay_block, dict):
                    continue

                diff = overlay_block.get("top_level_diff")
                if not isinstance(diff, dict):
                    continue

                changed_keys = diff.get("changed_keys")
                if not isinstance(changed_keys, list) or not changed_keys:
                    continue

                a_sha1 = overlay_block.get("sha1_a", "") if isinstance(overlay_block.get("sha1_a"), str) else ""
                b_sha1 = overlay_block.get("sha1_b", "") if isinstance(overlay_block.get("sha1_b"), str) else ""

                title = f"Overlay changed: {overlay_name} ({len(changed_keys)} keys)"

                atom = {
                    "atom_id": _atom_id("overlay_change", str(overlay_name), a_sha1 or a_id_ctx, b_sha1 or b_id_ctx),
                    "type": "overlay_change",
                    "severity": "info",
                    "title": title,
                    "refs": {"gates": [], "metrics": [], "overlays": [str(overlay_name)]},
                    "evidence": {
                        "source": {"overlay_drift_json": os.path.basename(t["overlay_json"])},
                        "overlay": {
                            "name": str(overlay_name),
                            "present_a": bool(overlay_block.get("present_a")),
                            "present_b": bool(overlay_block.get("present_b")),
                            "path_a": overlay_block.get("path_a", "") or "",
                            "path_b": overlay_block.get("path_b", "") or "",
                            "sha1_a": a_sha1,
                            "sha1_b": b_sha1,
                            "top_level_diff": {
                                "added_keys": diff.get("added_keys", []) if isinstance(diff.get("added_keys"), list) else [],
                                "removed_keys": diff.get("removed_keys", []) if isinstance(diff.get("removed_keys"), list) else [],
                                "changed_keys": changed_keys,
                                "note": diff.get("note", "") if isinstance(diff.get("note"), str) else "",
                            },
                        },
                    },
                }
                atoms.append(atom)
                overlay_atoms_by_name[str(overlay_name)] = atom

        # ---- gate_metric_tension atoms (gate_flip × metric_delta where metric severity is warn/crit)
        gate_metric_tensions = 0
        gate_ids_sorted = sorted(gate_atoms_by_gate_id.keys())
        metric_atoms_ordered = [
            metric_atoms_by_metric[m]
            for m in metric_atoms_by_metric.keys()
            if isinstance(metric_atoms_by_metric.get(m), dict)
        ]

        # Deterministic metric ordering for pairing:
        def _metric_pair_key(a: Dict[str, Any]) -> Tuple[int, float, str]:
            sev = a.get("severity", "info")
            ev = a.get("evidence", {})
            delta = None
            if isinstance(ev, dict):
                mm = ev.get("metric")
                if isinstance(mm, dict):
                    delta = mm.get("delta")
            d = _safe_float(delta)
            # sort: higher severity first, larger abs delta first
            return (_severity_rank(str(sev))[0], -(abs(d) if d is not None else 0.0), str(a.get("atom_id", "")))

        metric_atoms_ordered.sort(key=_metric_pair_key)

        for gid in gate_ids_sorted:
            g_atom = gate_atoms_by_gate_id.get(gid)
            if not isinstance(g_atom, dict):
                continue
            gate_atom_id = str(g_atom.get("atom_id", "")).strip()
            if not gate_atom_id:
                continue

            for m_atom in metric_atoms_ordered:
                if gate_metric_tensions >= MAX_GATE_METRIC_TENSIONS:
                    break

                if not isinstance(m_atom, dict):
                    continue
                m_sev = str(m_atom.get("severity", "")).strip()
                if m_sev not in ("warn", "crit"):
                    continue

                metric_atom_id = str(m_atom.get("atom_id", "")).strip()
                if not metric_atom_id:
                    continue

                # Try to get metric name for refs/title
                metric_name = ""
                mev = m_atom.get("evidence")
                if isinstance(mev, dict):
                    mm = mev.get("metric")
                    if isinstance(mm, dict) and isinstance(mm.get("name"), str):
                        metric_name = mm.get("name", "")
                metric_name = metric_name or "metric"

                sev = _max_severity(str(g_atom.get("severity", "info")), m_sev)
                tid = _tension_atom_id("gate_metric_tension", gate_atom_id, metric_atom_id)
                title = f"Gate ↔ Metric tension: {gid} × {metric_name}"

                tension = {
                    "atom_id": tid,
                    "type": "gate_metric_tension",
                    "severity": sev,
                    "title": title,
                    "refs": {"gates": [gid], "metrics": [metric_name], "overlays": []},
                    "evidence": {
                        "rule": "gate_flip × metric_delta(warn|crit)",
                        "gate_atom_id": gate_atom_id,
                        "metric_atom_id": metric_atom_id,
                        # Optional summaries (downstream-friendly)
                        "gate": (g_atom.get("evidence", {}) or {}).get("gate", {}) if isinstance(g_atom.get("evidence"), dict) else {},
                        "metric": (m_atom.get("evidence", {}) or {}).get("metric", {}) if isinstance(m_atom.get("evidence"), dict) else {},
                    },
                }
                atoms.append(tension)
                gate_metric_tensions += 1

            if gate_metric_tensions >= MAX_GATE_METRIC_TENSIONS:
                break

        # ---- gate_overlay_tension atoms (gate_flip × overlay_change; allowlisted overlays)
        gate_overlay_tensions = 0
        overlay_names_sorted = sorted(
            [n for n in overlay_atoms_by_name.keys() if n in OVERLAY_TENSION_ALLOWLIST]
        )

        for gid in gate_ids_sorted:
            g_atom = gate_atoms_by_gate_id.get(gid)
            if not isinstance(g_atom, dict):
                continue
            gate_atom_id = str(g_atom.get("atom_id", "")).strip()
            if not gate_atom_id:
                continue

            for oname in overlay_names_sorted:
                if gate_overlay_tensions >= MAX_GATE_OVERLAY_TENSIONS:
                    break

                o_atom = overlay_atoms_by_name.get(oname)
                if not isinstance(o_atom, dict):
                    continue
                overlay_atom_id = str(o_atom.get("atom_id", "")).strip()
                if not overlay_atom_id:
                    continue

                sev = _max_severity(str(g_atom.get("severity", "info")), str(o_atom.get("severity", "info")))
                tid = _tension_atom_id("gate_overlay_tension", gate_atom_id, overlay_atom_id)
                title = f"Gate ↔ Overlay tension: {gid} × {oname}"

                # deterministic small sample of changed_keys (for audit/triage)
                changed_keys_sample: List[str] = []
                oev = o_atom.get("evidence")
                if isinstance(oev, dict):
                    ob = oev.get("overlay")
                    if isinstance(ob, dict):
                        tld = ob.get("top_level_diff")
                        if isinstance(tld, dict):
                            ck = tld.get("changed_keys")
                            if isinstance(ck, list):
                                changed_keys_sample = [str(x) for x in ck][:OVERLAY_CHANGED_KEYS_SAMPLE]

                tension = {
                    "atom_id": tid,
                    "type": "gate_overlay_tension",
                    "severity": sev,
                    "title": title,
                    "refs": {"gates": [gid], "metrics": [], "overlays": [oname]},
                    "evidence": {
                        "rule": "gate_flip × overlay_change",
                        "gate_atom_id": gate_atom_id,
                        "overlay_atom_id": overlay_atom_id,
                        # Optional summaries (downstream-friendly)
                        "gate": (g_atom.get("evidence", {}) or {}).get("gate", {}) if isinstance(g_atom.get("evidence"), dict) else {},
                        "overlay": {
                            "name": oname,
                            "changed_keys_sample": changed_keys_sample,
                        },
                    },
                }
                atoms.append(tension)
                gate_overlay_tensions += 1

            if gate_overlay_tensions >= MAX_GATE_OVERLAY_TENSIONS:
                break

    # Deterministic ordering (severity -> type -> atom_id)
    atoms.sort(
        key=lambda a: (
            _severity_rank(a.get("severity", "")),
            a.get("type", ""),
            a.get("atom_id", ""),
        )
    )

    out_obj = {
        "paradox_field_v0": {
            "meta": meta,
            "atoms": atoms,
        }
    }

    _mkdirp_for_file(args.out)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out_obj, f, indent=2, ensure_ascii=False, sort_keys=True)

    print(f"[paradox_field_adapter_v0] wrote: {args.out}")


if __name__ == "__main__":
    main()

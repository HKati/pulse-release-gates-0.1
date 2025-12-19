#!/usr/bin/env python3
"""
PULSE transitions v0 — run-to-run drift summary for status.json + field overlays.

Workshop intent:
  - Not a release gate.
  - Deterministic, audit-friendly diff tool.
  - Answers: "what moved?" across two runs.

Inputs:
  --a PATH   Run A directory OR a direct status.json path
  --b PATH   Run B directory OR a direct status.json path
  --out DIR  Output directory

Optional overlays (if present in the run dirs):
  - g_field_v0.json         (the "Grail" surface / G-field)
  - paradox_field_v0.json   (paradox field / paradox diagram surface)

Outputs (written into --out):
  - pulse_transitions_v0.json
  - pulse_gate_drift_v0.csv
  - pulse_metric_drift_v0.csv
  - pulse_overlay_drift_v0.json

Fail-closed semantics:
  - If status.json cannot be located for A or B: exit != 0
  - If status.json lacks required structure (gates dict): exit != 0
  - Overlays are best-effort (missing overlay is allowed; it's reported)

No external dependencies (stdlib only).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple


STATUS_CANDIDATES = [
    "status.json",
    "artifacts/status.json",
    "PULSE_safe_pack_v0/artifacts/status.json",
    "PULSE_safe_pack_v0/artifacts/status_baseline.json",
    "PULSE_safe_pack_v0/artifacts/status_epf.json",
]

G_FIELD_CANDIDATES = [
    "g_field_v0.json",
    "artifacts/g_field_v0.json",
    "PULSE_safe_pack_v0/artifacts/g_field_v0.json",
    "overlays/g_field_v0.json",
    "reports/g_field_v0.json",
]

PARADOX_FIELD_CANDIDATES = [
    "paradox_field_v0.json",
    "artifacts/paradox_field_v0.json",
    "PULSE_safe_pack_v0/artifacts/paradox_field_v0.json",
    "overlays/paradox_field_v0.json",
    "reports/paradox_field_v0.json",
]


def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _sha1_file(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_number(x: Any) -> bool:
    if isinstance(x, bool):
        return False
    return isinstance(x, (int, float)) and not (isinstance(x, float) and (math.isnan(x) or math.isinf(x)))


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, bool):
            return None
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except Exception:
        return None


def _mkdirp(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _find_first_existing(base: str, candidates: List[str]) -> Optional[str]:
    for rel in candidates:
        p = os.path.join(base, rel)
        if os.path.isfile(p):
            return p
    return None


def _locate_input(path_or_dir: str, candidates: List[str]) -> str:
    """
    If input is a file -> return it.
    If input is a dir  -> find first matching candidate inside.
    """
    if os.path.isfile(path_or_dir):
        return path_or_dir
    if os.path.isdir(path_or_dir):
        found = _find_first_existing(path_or_dir, candidates)
        if found:
            return found
        raise SystemExit(
            f"[pulse_transitions_v0] Could not locate required file in dir: {path_or_dir}\n"
            f"  Tried candidates: {candidates}"
        )
    raise SystemExit(f"[pulse_transitions_v0] Path not found: {path_or_dir}")


def _locate_optional(path_or_dir: str, candidates: List[str]) -> Optional[str]:
    if os.path.isfile(path_or_dir):
        # if user passed a file directly, we do not try to infer overlays from it
        return None
    if os.path.isdir(path_or_dir):
        return _find_first_existing(path_or_dir, candidates)
    return None


def _pick(d: Dict[str, Any], keys: List[str]) -> Optional[Any]:
    for k in keys:
        if k in d:
            return d[k]
    return None


@dataclass(frozen=True)
class RunInfo:
    label: str
    input_path: str
    status_path: str
    status_sha1: str
    meta: Dict[str, Any]


def _extract_run_meta(status: Dict[str, Any]) -> Dict[str, Any]:
    """
    Best-effort. We keep this permissive because the repo evolves.
    """
    meta = {}
    # common places
    top_meta = status.get("meta") if isinstance(status.get("meta"), dict) else {}
    run = status.get("run") if isinstance(status.get("run"), dict) else {}
    model = status.get("model") if isinstance(status.get("model"), dict) else {}

    meta["run_id"] = _pick(top_meta, ["run_id", "id", "uid"]) or _pick(run, ["run_id", "id"])
    meta["commit"] = _pick(top_meta, ["commit", "git_sha", "sha"]) or status.get("commit")
    meta["timestamp"] = _pick(top_meta, ["timestamp", "created_at", "time"]) or status.get("timestamp")
    meta["profile"] = status.get("profile") or _pick(top_meta, ["profile"])
    meta["decision"] = status.get("decision") or _pick(status, ["decision_level", "release_decision"])
    meta["model_id"] = _pick(model, ["id", "model_id", "name"]) or status.get("model_id")
    meta["image"] = _pick(model, ["image", "container_image"]) or status.get("image")

    # Strip Nones for cleanliness
    return {k: v for k, v in meta.items() if v is not None}


def _normalize_gate_value(v: Any) -> Tuple[Optional[bool], Optional[float], Optional[str]]:
    """
    Returns: (pass_bool, numeric_value, notes)
    Supports:
      - bool gates
      - dict gates with pass/ok/value/threshold/reason
      - numeric 0/1 as pass if unambiguous
    """
    if isinstance(v, bool):
        return v, None, None

    if isinstance(v, (int, float)) and not isinstance(v, bool):
        # interpret strictly only if it's exactly 0/1
        if v == 0:
            return False, float(v), None
        if v == 1:
            return True, float(v), None
        # otherwise numeric but unknown pass semantics
        return None, float(v), None

    if isinstance(v, dict):
        p = v.get("pass")
        if p is None:
            p = v.get("ok")
        pass_bool = bool(p) if isinstance(p, bool) else None
        num = _safe_float(v.get("value"))
        notes = v.get("reason") or v.get("note") or v.get("notes")
        return pass_bool, num, notes if isinstance(notes, str) else None

    return None, _safe_float(v), None


def _dict_top_level_diff(a: Any, b: Any) -> Dict[str, Any]:
    """
    Generic diff for overlay JSON objects (best-effort).
    We avoid deep diffs: only top-level keys + value-hash changes.
    """
    if not isinstance(a, dict) or not isinstance(b, dict):
        return {
            "type_a": type(a).__name__,
            "type_b": type(b).__name__,
            "note": "non-dict overlay; only hashes compared",
        }

    keys_a = set(a.keys())
    keys_b = set(b.keys())
    added = sorted(keys_b - keys_a)
    removed = sorted(keys_a - keys_b)

    # detect changed keys by hashing JSON-serialized value
    def vh(x: Any) -> str:
        raw = json.dumps(x, sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]

    common = sorted(keys_a & keys_b)
    changed = []
    for k in common:
        if vh(a[k]) != vh(b[k]):
            changed.append(k)

    return {
        "added_keys": added,
        "removed_keys": removed,
        "changed_keys": changed,
        "unchanged_common": len(common) - len(changed),
        "total_a": len(keys_a),
        "total_b": len(keys_b),
    }


def _paradox_summary(obj: Any) -> Dict[str, Any]:
    """
    Best-effort extraction of 'paradox candidates' / disagreements,
    without hard schema assumptions.
    """
    if not isinstance(obj, dict):
        return {"note": "non-dict paradox overlay"}

    # common-ish possibilities
    candidates = None
    for k in ["paradox_candidates", "candidates", "disagreements", "paradox", "items"]:
        if isinstance(obj.get(k), list):
            candidates = obj.get(k)
            break

    if candidates is None:
        return {"note": "no obvious candidates list", "top_level_keys": sorted(obj.keys())}

    # try to derive stable identifiers (gate_id / id)
    ids = []
    for it in candidates:
        if isinstance(it, dict):
            gid = it.get("gate_id") or it.get("id") or it.get("gate")
            if gid is not None:
                ids.append(str(gid))
        else:
            ids.append(str(it))

    return {
        "candidates_count": len(candidates),
        "candidate_ids_sample": ids[:10],
        "candidate_ids_unique": len(set(ids)),
    }


def _write_csv(path: str, cols: List[str], rows: Iterable[Dict[str, Any]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="Run A dir or status.json path")
    ap.add_argument("--b", required=True, help="Run B dir or status.json path")
    ap.add_argument("--out", required=True, help="Output dir for transitions artefacts")
    ap.add_argument("--top-metrics", type=int, default=30, help="Top N numeric metric deltas to report in JSON summary")
    ap.add_argument("--fail-on-gate-changes", action="store_true",
                    help="Exit !=0 if any gate PASS/FAIL flips between A and B (workshop guard).")
    args = ap.parse_args()

    out_dir = args.out
    _mkdirp(out_dir)

    # Locate required status.json for each run
    status_a_path = _locate_input(args.a, STATUS_CANDIDATES)
    status_b_path = _locate_input(args.b, STATUS_CANDIDATES)

    status_a = _read_json(status_a_path)
    status_b = _read_json(status_b_path)

    if not isinstance(status_a, dict) or not isinstance(status_b, dict):
        raise SystemExit("[pulse_transitions_v0] status.json must be a JSON object in both runs.")

    gates_a = status_a.get("gates")
    gates_b = status_b.get("gates")
    if not isinstance(gates_a, dict) or not isinstance(gates_b, dict):
        raise SystemExit("[pulse_transitions_v0] status.json must contain a 'gates' object in both runs.")

    metrics_a = status_a.get("metrics") if isinstance(status_a.get("metrics"), dict) else {}
    metrics_b = status_b.get("metrics") if isinstance(status_b.get("metrics"), dict) else {}
    thresholds_a = status_a.get("thresholds") if isinstance(status_a.get("thresholds"), dict) else {}
    thresholds_b = status_b.get("thresholds") if isinstance(status_b.get("thresholds"), dict) else {}

    run_a = RunInfo(
        label="A",
        input_path=args.a,
        status_path=status_a_path,
        status_sha1=_sha1_file(status_a_path),
        meta=_extract_run_meta(status_a),
    )
    run_b = RunInfo(
        label="B",
        input_path=args.b,
        status_path=status_b_path,
        status_sha1=_sha1_file(status_b_path),
        meta=_extract_run_meta(status_b),
    )

    # Gate drift rows
    all_gate_ids = sorted(set(gates_a.keys()) | set(gates_b.keys()))
    gate_rows = []
    flips = 0
    for gid in all_gate_ids:
        va = gates_a.get(gid)
        vb = gates_b.get(gid)

        pa, numa, na = _normalize_gate_value(va)
        pb, numb, nb = _normalize_gate_value(vb)

        changed = 0
        if pa is not None and pb is not None and pa != pb:
            changed = 1
            flips += 1

        # thresholds might be keyed by gate id or by metric key; best effort:
        th_a = thresholds_a.get(gid)
        th_b = thresholds_b.get(gid)
        th = th_b if th_b is not None else th_a

        gate_rows.append({
            "gate_id": gid,
            "pass_a": pa if pa is not None else "",
            "pass_b": pb if pb is not None else "",
            "flip": changed,
            "value_a": numa if numa is not None else "",
            "value_b": numb if numb is not None else "",
            "threshold": th if th is not None else "",
            "notes_a": na if na else "",
            "notes_b": nb if nb else "",
            "present_a": 1 if gid in gates_a else 0,
            "present_b": 1 if gid in gates_b else 0,
        })

    gate_csv = os.path.join(out_dir, "pulse_gate_drift_v0.csv")
    _write_csv(
        gate_csv,
        cols=[
            "gate_id", "pass_a", "pass_b", "flip",
            "value_a", "value_b", "threshold",
            "notes_a", "notes_b",
            "present_a", "present_b",
        ],
        rows=gate_rows,
    )

    # Metric drift rows (numeric + also record non-numeric changes in JSON summary)
    all_metric_keys = sorted(set(metrics_a.keys()) | set(metrics_b.keys()))
    metric_rows = []
    numeric_deltas: List[Tuple[str, float, float, float]] = []
    changed_non_numeric = []

    for k in all_metric_keys:
        a_val = metrics_a.get(k, None)
        b_val = metrics_b.get(k, None)

        a_num = _safe_float(a_val)
        b_num = _safe_float(b_val)

        if a_num is not None and b_num is not None:
            delta = b_num - a_num
            rel = delta / abs(a_num) if a_num != 0 else ""
            metric_rows.append({
                "metric": k,
                "a": a_num,
                "b": b_num,
                "delta": delta,
                "rel_delta": rel,
                "present_a": 1 if k in metrics_a else 0,
                "present_b": 1 if k in metrics_b else 0,
            })
            numeric_deltas.append((k, a_num, b_num, delta))
        else:
            # keep a thin record in CSV too (as strings)
            metric_rows.append({
                "metric": k,
                "a": "" if a_val is None else str(a_val),
                "b": "" if b_val is None else str(b_val),
                "delta": "",
                "rel_delta": "",
                "present_a": 1 if k in metrics_a else 0,
                "present_b": 1 if k in metrics_b else 0,
            })
            if a_val != b_val:
                changed_non_numeric.append(k)

    metric_csv = os.path.join(out_dir, "pulse_metric_drift_v0.csv")
    _write_csv(
        metric_csv,
        cols=["metric", "a", "b", "delta", "rel_delta", "present_a", "present_b"],
        rows=metric_rows,
    )

    # Sort top numeric metric deltas
    numeric_deltas.sort(key=lambda x: abs(x[3]), reverse=True)
    top_metric_moves = [
        {"metric": k, "a": a, "b": b, "delta": d}
        for (k, a, b, d) in numeric_deltas[: int(args.top_metrics)]
    ]

    # Optional overlays
    g_a_path = _locate_optional(args.a, G_FIELD_CANDIDATES)
    g_b_path = _locate_optional(args.b, G_FIELD_CANDIDATES)
    p_a_path = _locate_optional(args.a, PARADOX_FIELD_CANDIDATES)
    p_b_path = _locate_optional(args.b, PARADOX_FIELD_CANDIDATES)

    overlay_out: Dict[str, Any] = {}

    # G-field overlay diff
    if g_a_path or g_b_path:
        g_obj_a = _read_json(g_a_path) if g_a_path else None
        g_obj_b = _read_json(g_b_path) if g_b_path else None
        overlay_out["g_field_v0"] = {
            "present_a": bool(g_a_path),
            "present_b": bool(g_b_path),
            "path_a": g_a_path or "",
            "path_b": g_b_path or "",
            "sha1_a": _sha1_file(g_a_path) if g_a_path else "",
            "sha1_b": _sha1_file(g_b_path) if g_b_path else "",
            "top_level_diff": _dict_top_level_diff(g_obj_a, g_obj_b) if (g_obj_a is not None and g_obj_b is not None) else {},
        }

    # Paradox field overlay diff
    if p_a_path or p_b_path:
        p_obj_a = _read_json(p_a_path) if p_a_path else None
        p_obj_b = _read_json(p_b_path) if p_b_path else None
        overlay_out["paradox_field_v0"] = {
            "present_a": bool(p_a_path),
            "present_b": bool(p_b_path),
            "path_a": p_a_path or "",
            "path_b": p_b_path or "",
            "sha1_a": _sha1_file(p_a_path) if p_a_path else "",
            "sha1_b": _sha1_file(p_b_path) if p_b_path else "",
            "top_level_diff": _dict_top_level_diff(p_obj_a, p_obj_b) if (p_obj_a is not None and p_obj_b is not None) else {},
            "summary_a": _paradox_summary(p_obj_a) if p_obj_a is not None else {"note": "missing"},
            "summary_b": _paradox_summary(p_obj_b) if p_obj_b is not None else {"note": "missing"},
        }

    overlay_json = os.path.join(out_dir, "pulse_overlay_drift_v0.json")
    with open(overlay_json, "w", encoding="utf-8") as f:
        json.dump(overlay_out, f, indent=2, ensure_ascii=False, sort_keys=True)

    # Master summary JSON
    summary = {
        "tool": "scripts/pulse_transitions_v0.py",
        "version": "v0",
        "run_a": {
            "input": run_a.input_path,
            "status_path": run_a.status_path,
            "status_sha1": run_a.status_sha1,
            "meta": run_a.meta,
        },
        "run_b": {
            "input": run_b.input_path,
            "status_path": run_b.status_path,
            "status_sha1": run_b.status_sha1,
            "meta": run_b.meta,
        },
        "gates": {
            "total_union": len(all_gate_ids),
            "flips": flips,
            "missing_in_a": len([g for g in all_gate_ids if g not in gates_a]),
            "missing_in_b": len([g for g in all_gate_ids if g not in gates_b]),
        },
        "metrics": {
            "total_union": len(all_metric_keys),
            "changed_non_numeric_keys": changed_non_numeric[:50],
            "top_numeric_moves": top_metric_moves,
        },
        "outputs": {
            "gate_drift_csv": os.path.basename(gate_csv),
            "metric_drift_csv": os.path.basename(metric_csv),
            "overlay_drift_json": os.path.basename(overlay_json),
        },
        "notes": {
            "fail_closed": "status.json missing or malformed -> exit != 0",
            "overlays_best_effort": True,
        },
    }

    summary_json = os.path.join(out_dir, "pulse_transitions_v0.json")
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, sort_keys=True)

    print(f"[pulse_transitions_v0] wrote: {summary_json}")
    print(f"[pulse_transitions_v0] wrote: {gate_csv}")
    print(f"[pulse_transitions_v0] wrote: {metric_csv}")
    print(f"[pulse_transitions_v0] wrote: {overlay_json}")

    if args.fail_on_gate_changes and flips > 0:
        print(f"[pulse_transitions_v0] FAIL (gate flips detected): flips={flips}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()

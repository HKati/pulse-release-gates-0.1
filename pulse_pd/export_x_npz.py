"""
Export a real-analysis feature table into PULSE–PD X.npz schema.

Why this exists
---------------
PULSE–PD needs a stable, minimal interface to "the decision moment" inputs.
Instead of binding to a specific HEP framework here, we export a flat table
(CSV) into an NPZ with a well-defined schema:

Required:
- X: float array, shape (n, d)
- feature_names: list of d strings

Optional (traceback-ready):
- run: int array, shape (n,)
- lumi: int array, shape (n,)
- event: int array, shape (n,)
- event_id: string array, shape (n,)   (if absent, can be derived from run/lumi/event)
- weight: float array, shape (n,)
- y: int array, shape (n,)             (optional labels; not required by PD)

Input format
------------
CSV with a header row. By default, all columns except reserved ID/label columns
are treated as features, unless --feature-cols is provided explicitly.

Example
-------
python -m pulse_pd.export_x_npz \
  --in-csv analysis_features.csv \
  --out X_analysis.npz \
  --require-ids \
  --make-event-id

Then run PD:
python -m pulse_pd.run_cut_pd --x X_analysis.npz --theta theta.json --dims 0 1 --out artifacts_run
python -m pulse_pd.export_top_pi_events --x X_analysis.npz --theta theta.json --out artifacts_run/top_pi_events.csv
"""

from __future__ import annotations

import argparse
import csv
import os
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np


def _parse_float(s: str) -> float:
    s = (s or "").strip()
    if s == "":
        return float("nan")
    return float(s)


def _parse_int(s: str) -> int:
    s = (s or "").strip()
    if s == "":
        raise ValueError("empty int field")
    # tolerate "123.0" just in case
    return int(float(s))


def _as_str(s: str) -> str:
    return str(s) if s is not None else ""


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _norm_list(arg: Optional[Sequence[str]]) -> Optional[List[str]]:
    if arg is None:
        return None
    out: List[str] = []
    for x in arg:
        # allow comma-separated in a single token
        parts = [p.strip() for p in str(x).split(",") if p.strip()]
        out.extend(parts)
    return out if out else None


def _infer_feature_cols(
    fieldnames: List[str],
    *,
    feature_cols: Optional[List[str]],
    exclude_cols: List[str],
    reserved_cols: List[str],
) -> List[str]:
    if feature_cols is not None:
        missing = [c for c in feature_cols if c not in fieldnames]
        if missing:
            raise ValueError(f"--feature-cols contains unknown columns: {missing}")
        return feature_cols

    exclude = set(exclude_cols)
    reserved = set(reserved_cols)
    feats = [c for c in fieldnames if c not in exclude and c not in reserved]
    if not feats:
        raise ValueError(
            "No feature columns detected. Provide --feature-cols explicitly or check your CSV header."
        )
    return feats


def _maybe_present(fieldnames: List[str], col: Optional[str]) -> Optional[str]:
    if not col:
        return None
    return col if col in fieldnames else None


def _load_csv_rows(path: str, delimiter: str) -> Tuple[List[str], List[Dict[str, str]]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f, delimiter=delimiter)
        if not r.fieldnames:
            raise ValueError("CSV has no header row (fieldnames missing). This adapter requires a header.")
        fieldnames = [str(x).strip() for x in r.fieldnames if str(x).strip()]
        rows: List[Dict[str, str]] = []
        for row in r:
            # DictReader can yield None keys if header is malformed; ignore them
            clean = {str(k).strip(): (v if v is not None else "") for k, v in row.items() if k is not None}
            rows.append(clean)
    return fieldnames, rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-csv", required=True, help="Input CSV with header (features + optional IDs)")
    ap.add_argument("--out", required=True, help="Output .npz path (PULSE–PD schema)")
    ap.add_argument("--delimiter", default=",", help="CSV delimiter (default: ,)")

    ap.add_argument(
        "--feature-cols",
        nargs="*",
        default=None,
        help="Explicit feature columns (space-separated or comma-separated). If omitted, auto-detect.",
    )
    ap.add_argument(
        "--exclude-cols",
        nargs="*",
        default=[],
        help="Columns to ignore (space-separated or comma-separated).",
    )

    # Optional ID/label columns (exported if present)
    ap.add_argument("--run-col", default="run", help="Run column name (optional)")
    ap.add_argument("--lumi-col", default="lumi", help="Lumi column name (optional)")
    ap.add_argument("--event-col", default="event", help="Event column name (optional)")
    ap.add_argument("--event-id-col", default="event_id", help="Event id column name (optional)")
    ap.add_argument("--weight-col", default="weight", help="Weight column name (optional)")
    ap.add_argument("--y-col", default="y", help="Label column name (optional)")

    ap.add_argument(
        "--require-ids",
        action="store_true",
        help="Fail if neither event_id nor (run,lumi,event) are available in the CSV.",
    )
    ap.add_argument(
        "--make-event-id",
        action="store_true",
        help="If event_id column is missing but run/lumi/event exist, derive event_id as 'run:lumi:event'.",
    )

    ap.add_argument(
        "--dtype",
        default="float64",
        choices=["float32", "float64"],
        help="Floating dtype for X/weight.",
    )
    ap.add_argument(
        "--drop-nan-rows",
        action="store_true",
        help="Drop rows that contain NaN in any feature column.",
    )
    ap.add_argument("--max-rows", type=int, default=0, help="Optional cap for rows (0 = no cap)")
    ap.add_argument("--dry-run", action="store_true", help="Print detected columns and exit (no write).")

    args = ap.parse_args()

    feature_cols = _norm_list(args.feature_cols)
    exclude_cols = _norm_list(args.exclude_cols) or []

    fieldnames, rows = _load_csv_rows(args.in_csv, delimiter=str(args.delimiter))
    if args.max_rows and args.max_rows > 0:
        rows = rows[: int(args.max_rows)]

    run_col = _maybe_present(fieldnames, args.run_col)
    lumi_col = _maybe_present(fieldnames, args.lumi_col)
    event_col = _maybe_present(fieldnames, args.event_col)
    event_id_col = _maybe_present(fieldnames, args.event_id_col)
    weight_col = _maybe_present(fieldnames, args.weight_col)
    y_col = _maybe_present(fieldnames, args.y_col)

    reserved_cols = []
    for c in [run_col, lumi_col, event_col, event_id_col, weight_col, y_col]:
        if c:
            reserved_cols.append(c)

    feat_cols = _infer_feature_cols(
        fieldnames,
        feature_cols=feature_cols,
        exclude_cols=exclude_cols,
        reserved_cols=reserved_cols,
    )

    have_triplet = (run_col is not None) and (lumi_col is not None) and (event_col is not None)
    have_event_id = event_id_col is not None

    if args.require_ids and not (have_event_id or have_triplet):
        raise ValueError(
            "IDs required, but neither event_id nor (run,lumi,event) are present in the CSV header."
        )

    if args.dry_run:
        print("Input:", os.path.abspath(args.in_csv))
        print("Rows:", len(rows))
        print("Feature cols (d=%d): %s" % (len(feat_cols), feat_cols))
        print("ID cols present:", {
            "run": run_col,
            "lumi": lumi_col,
            "event": event_col,
            "event_id": event_id_col,
            "weight": weight_col,
            "y": y_col,
        })
        print("Derived event_id:", bool(args.make_event_id and (not have_event_id) and have_triplet))
        print("Output:", os.path.abspath(args.out))
        return 0

    # Build arrays
    X_rows: List[List[float]] = []
    run_v: List[int] = []
    lumi_v: List[int] = []
    event_v: List[int] = []
    event_id_v: List[str] = []
    weight_v: List[float] = []
    y_v: List[int] = []

    for r in rows:
        feats = [_parse_float(r.get(c, "")) for c in feat_cols]
        X_rows.append(feats)

        if run_col:
            run_v.append(_parse_int(r.get(run_col, "")))
        if lumi_col:
            lumi_v.append(_parse_int(r.get(lumi_col, "")))
        if event_col:
            event_v.append(_parse_int(r.get(event_col, "")))

        if event_id_col:
            event_id_v.append(_as_str(r.get(event_id_col, "")))
        elif args.make_event_id and have_triplet:
            # derive from triplet (must exist by here)
            rr = _parse_int(r.get(run_col or "", ""))
            ll = _parse_int(r.get(lumi_col or "", ""))
            ee = _parse_int(r.get(event_col or "", ""))
            event_id_v.append(f"{rr}:{ll}:{ee}")

        if weight_col:
            weight_v.append(_parse_float(r.get(weight_col, "")))
        if y_col:
            y_v.append(_parse_int(r.get(y_col, "")))

    X = np.asarray(X_rows, dtype=getattr(np, args.dtype))
    if X.ndim != 2:
        raise ValueError(f"X must be 2D; got {X.shape}")

    n = X.shape[0]

    # Optional drop of NaN rows (features only)
    if args.drop_nan_rows:
        ok = np.isfinite(X).all(axis=1)
        keep_idx = np.where(ok)[0]
        X = X[keep_idx, :]
        n2 = X.shape[0]

        def _filter_list(lst, present: bool):
            if not present:
                return lst
            return [lst[i] for i in keep_idx.tolist()]

        run_v = _filter_list(run_v, bool(run_col))
        lumi_v = _filter_list(lumi_v, bool(lumi_col))
        event_v = _filter_list(event_v, bool(event_col))
        event_id_v = _filter_list(event_id_v, bool(event_id_v))
        weight_v = _filter_list(weight_v, bool(weight_col))
        y_v = _filter_list(y_v, bool(y_col))
        n = n2

    # Length checks (fail-fast on mismatches)
    def _check_len(name: str, present: bool, lst) -> None:
        if present and len(lst) != n:
            raise ValueError(f"Column '{name}' length mismatch: {len(lst)} vs n={n}")

    _check_len("run", bool(run_col), run_v)
    _check_len("lumi", bool(lumi_col), lumi_v)
    _check_len("event", bool(event_col), event_v)
    _check_len("event_id", bool(event_id_v), event_id_v)
    _check_len("weight", bool(weight_col), weight_v)
    _check_len("y", bool(y_col), y_v)

    out: Dict[str, np.ndarray] = {
        "X": X,
        "feature_names": np.asarray([str(c) for c in feat_cols], dtype=str),
    }

    if run_col:
        out["run"] = np.asarray(run_v, dtype=np.int64)
    if lumi_col:
        out["lumi"] = np.asarray(lumi_v, dtype=np.int64)
    if event_col:
        out["event"] = np.asarray(event_v, dtype=np.int64)
    if event_id_v:
        out["event_id"] = np.asarray(event_id_v, dtype=str)
    if weight_col:
        out["weight"] = np.asarray(weight_v, dtype=getattr(np, args.dtype))
    if y_col:
        out["y"] = np.asarray(y_v, dtype=np.int64)

    _ensure_parent_dir(args.out)
    np.savez_compressed(args.out, **out)

    print("Wrote:", os.path.abspath(args.out))
    print("n=%d, d=%d" % (X.shape[0], X.shape[1]))
    print("Keys:", sorted(out.keys()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

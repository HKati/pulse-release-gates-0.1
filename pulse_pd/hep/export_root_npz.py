"""
HEP-native adapter stub: export a flat feature matrix X to the PULSE–PD NPZ schema.

This module intentionally stays *thin*:
- it reads flat (1D) branches from a ROOT TTree (via uproot),
- writes X.npz with `X` + `feature_names`,
- and (optionally) writes event identifiers for traceback:
  `run`, `lumi`, `event`, `event_id`, and `weight`.

Design constraints (v0):
- No physics logic here (no object selection, no jagged-to-flat transforms).
  Upstream analysis code should produce *flat* branches (e.g. pt_lead, eta_lead).
- Optional dependency: uproot (not required for importing pulse_pd).

Example:
  python -m pulse_pd.hep.export_root_npz \
    --root /data/nanoaod.root \
    --tree Events \
    --features pt_lead eta_lead \
    --run-branch run --lumi-branch luminosityBlock --event-branch event \
    --weight-branch weight \
    --out pulse_pd/artifacts_run/X_real.npz \
    --max-events 200000
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    branch: str


def _parse_feature_specs(items: Sequence[str]) -> List[FeatureSpec]:
    """
    Parse feature specs.

    Supported forms:
      - "pt_lead"            -> name="pt_lead", branch="pt_lead"
      - "pt_lead=Jet_pt0"    -> name="pt_lead", branch="Jet_pt0"

    We keep it strict and flat: the branch must resolve to a 1D array.
    """
    out: List[FeatureSpec] = []
    for raw in items:
        s = raw.strip()
        if not s:
            continue
        if "=" in s:
            name, branch = s.split("=", 1)
            name = name.strip()
            branch = branch.strip()
            if not name or not branch:
                raise ValueError(f"Invalid --features item '{raw}'. Use 'name' or 'name=branch'.")
            out.append(FeatureSpec(name=name, branch=branch))
        else:
            out.append(FeatureSpec(name=s, branch=s))

    if not out:
        raise ValueError("No features provided. Use --features f1 f2 ... or --features name=branch ...")

    names = [f.name for f in out]
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup:
        raise ValueError(f"Duplicate feature names in --features: {dup}")
    return out


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _unique_preserve(seq: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for x in seq:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out


def _as_1d_numeric(a: np.ndarray, *, name: str) -> np.ndarray:
    """
    Ensure array is 1D numeric.
    Accepts (n,) or (n,1) and flattens.
    Rejects jagged/object and higher-rank arrays.
    """
    arr = np.asarray(a)
    if arr.ndim == 2 and arr.shape[1] == 1:
        arr = arr.reshape(-1)
    if arr.ndim != 1:
        raise ValueError(
            f"Branch '{name}' must be a flat 1D array. Got shape {arr.shape}. "
            "v0 adapter expects flat branches (precompute features upstream)."
        )
    try:
        return np.asarray(arr, dtype=float)
    except Exception as e:
        raise ValueError(f"Branch '{name}' is not numeric (cannot cast to float). dtype={arr.dtype}") from e


def _as_1d_int(a: np.ndarray, *, name: str) -> np.ndarray:
    arr = np.asarray(a)
    if arr.ndim == 2 and arr.shape[1] == 1:
        arr = arr.reshape(-1)
    if arr.ndim != 1:
        raise ValueError(f"Branch '{name}' must be 1D. Got shape {arr.shape}.")
    try:
        return np.asarray(arr, dtype=np.int64)
    except Exception as e:
        raise ValueError(f"Branch '{name}' is not integer-like. dtype={arr.dtype}") from e


def _make_event_id(run: Optional[np.ndarray], lumi: Optional[np.ndarray], event: np.ndarray) -> np.ndarray:
    """
    Deterministic, human-readable event id.

    Priority:
      run:lumi:event  (if run and lumi present)
      run:event       (if only run present)
      event           (fallback)
    """
    ev = event.astype(str)
    if run is not None and lumi is not None:
        return (run.astype(str) + ":" + lumi.astype(str) + ":" + ev)
    if run is not None:
        return (run.astype(str) + ":" + ev)
    return ev


def _list_tree_keys(tree) -> List[str]:
    keys = []
    for k in tree.keys():
        keys.append(k.decode() if isinstance(k, (bytes, bytearray)) else str(k))
    return keys


def export_root_to_npz(
    *,
    root_path: str,
    tree_name: str,
    features: List[FeatureSpec],
    out_path: str,
    run_branch: Optional[str],
    lumi_branch: Optional[str],
    event_branch: str,
    weight_branch: Optional[str],
    max_events: Optional[int],
    chunk_size: int,
    require_ids: bool,
    write_event_id: bool,
) -> str:
    """
    Core exporter. Returns absolute output path.
    """
    try:
        import uproot  # type: ignore
    except Exception as e:
        raise RuntimeError("Missing optional dependency 'uproot'. Install with: pip install uproot") from e

    if chunk_size <= 0:
        raise ValueError("--chunk-size must be > 0")

    _ensure_parent_dir(out_path)

    with uproot.open(root_path) as f:
        if tree_name not in f:
            keys = list(f.keys())
            raise ValueError(
                f"TTree '{tree_name}' not found in ROOT file. "
                f"Top-level keys: {keys[:50]}{' ...' if len(keys) > 50 else ''}"
            )
        tree = f[tree_name]

        n_total = int(tree.num_entries)
        n_use = n_total if max_events is None else min(n_total, int(max_events))
        if n_use <= 0:
            raise ValueError("No entries selected (max_events <= 0 or empty tree).")

        d = len(features)
        X = np.empty((n_use, d), dtype=float)

        run = None
        lumi = None
        weight = None
        if run_branch:
            run = np.empty(n_use, dtype=np.int64)
        if lumi_branch:
            lumi = np.empty(n_use, dtype=np.int64)
        if weight_branch:
            weight = np.empty(n_use, dtype=float)

        event = np.empty(n_use, dtype=np.int64)

        branches = [fs.branch for fs in features]
        branches += [event_branch]
        if run_branch:
            branches += [run_branch]
        if lumi_branch:
            branches += [lumi_branch]
        if weight_branch:
            branches += [weight_branch]
        branches = _unique_preserve(branches)

        tree_keys = set(_list_tree_keys(tree))
        missing = [b for b in branches if b not in tree_keys]
        if missing:
            avail = sorted(list(tree_keys))[:80]
            raise ValueError(
                f"Missing branches in tree '{tree_name}': {missing}. "
                f"Available (first 80): {avail}"
            )

        off = 0
        while off < n_use:
            stop = min(n_use, off + chunk_size)
            arrays: Dict[str, np.ndarray] = tree.arrays(
                branches, entry_start=off, entry_stop=stop, library="np"
            )  # type: ignore

            for j, fs in enumerate(features):
                X[off:stop, j] = _as_1d_numeric(arrays[fs.branch], name=fs.branch)

            event[off:stop] = _as_1d_int(arrays[event_branch], name=event_branch)
            if run_branch:
                assert run is not None
                run[off:stop] = _as_1d_int(arrays[run_branch], name=run_branch)
            if lumi_branch:
                assert lumi is not None
                lumi[off:stop] = _as_1d_int(arrays[lumi_branch], name=lumi_branch)
            if weight_branch:
                assert weight is not None
                weight[off:stop] = _as_1d_numeric(arrays[weight_branch], name=weight_branch)

            off = stop

    if require_ids and (run is None or lumi is None):
        raise ValueError(
            "--require-ids was set but run/lumi branches were not both provided. "
            "Set --run-branch and --lumi-branch, or remove --require-ids."
        )

    payload: Dict[str, np.ndarray] = {
        "X": X,
        "feature_names": np.asarray([fs.name for fs in features], dtype=object),
        "event": event,
    }
    if run is not None:
        payload["run"] = run
    if lumi is not None:
        payload["lumi"] = lumi
    if weight is not None:
        payload["weight"] = weight
    if write_event_id:
        payload["event_id"] = _make_event_id(run=run, lumi=lumi, event=event)

    np.savez_compressed(out_path, **payload)
    return os.path.abspath(out_path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="Input ROOT file path")
    ap.add_argument("--tree", default="Events", help="TTree name (default: Events)")
    ap.add_argument(
        "--features",
        nargs="+",
        required=True,
        help="Feature list: 'name' or 'name=branch'. Branches must be flat 1D arrays.",
    )
    ap.add_argument("--out", required=True, help="Output .npz path (PULSE–PD X schema)")

    ap.add_argument("--event-branch", default="event", help="Event number branch (default: event)")
    ap.add_argument("--run-branch", default="run", help="Run branch (default: run)")
    ap.add_argument(
        "--lumi-branch",
        default="luminosityBlock",
        help="Lumi branch (default: luminosityBlock, NanoAOD-style)",
    )
    ap.add_argument("--weight-branch", default=None, help="Optional weight branch")

    ap.add_argument("--max-events", type=int, default=None, help="Optional max entries to read")
    ap.add_argument("--chunk-size", type=int, default=200_000, help="Chunk size for ROOT reads")
    ap.add_argument("--require-ids", action="store_true", help="Require run+lumi+event in output")
    ap.add_argument("--no-event-id", action="store_true", help="Do not write event_id column")

    args = ap.parse_args()
    feats = _parse_feature_specs(args.features)

    out = export_root_to_npz(
        root_path=args.root,
        tree_name=args.tree,
        features=feats,
        out_path=args.out,
        run_branch=args.run_branch if args.run_branch else None,
        lumi_branch=args.lumi_branch if args.lumi_branch else None,
        event_branch=args.event_branch,
        weight_branch=args.weight_branch if args.weight_branch else None,
        max_events=args.max_events,
        chunk_size=args.chunk_size,
        require_ids=bool(args.require_ids),
        write_event_id=not bool(args.no_event_id),
    )

    print("Wrote:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

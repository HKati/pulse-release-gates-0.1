"""
HEP-native ROOT -> X.npz exporter for PULSE–PD.

This module is intentionally lightweight at import time: it only imports
stdlib + NumPy. The HEP dependency (uproot) is imported at runtime inside main().

Exports an NPZ that follows the PULSE–PD schema:
- X                (required) shape (n, d), float
- feature_names    (optional but recommended) list[str] length d

Optional traceback identifiers:
- run, lumi, event (int arrays) and/or event_id (string/int array)
Optional weights:
- weight (float array)

Example:
  python -m pulse_pd.hep.export_uproot_npz \
    --root /path/to/file.root \
    --tree Events \
    --features "pt_lead,eta_lead,phi_lead" \
    --out pulse_pd/artifacts_run/X_from_root.npz \
    --run-branch run \
    --lumi-branch luminosityBlock \
    --event-branch event \
    --weight-branch weight

Notes
-----
- This exporter expects flat (1D) branches for features. Jagged arrays are rejected
  with a clear error message (handle those upstream or provide derived scalars).
- No CI dependency on uproot is introduced; this is a “real pipeline” adapter.
"""

from __future__ import annotations

import argparse
import os
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np


def _split_csv(s: str) -> List[str]:
    return [t.strip() for t in s.split(",") if t.strip()]


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _as_1d(a: np.ndarray, name: str) -> np.ndarray:
    a = np.asarray(a)
    if a.ndim != 1:
        raise ValueError(f"Branch '{name}' must be 1D; got shape {a.shape}")
    return a


def _reject_object_arrays(a: np.ndarray, name: str) -> None:
    # uproot will often produce dtype=object for jagged branches when asking for numpy.
    if getattr(a, "dtype", None) is not None and a.dtype == object:
        raise ValueError(
            f"Branch '{name}' looks jagged/variable-length (dtype=object). "
            "Export only flat scalar branches (derive scalars upstream)."
        )


def _load_arrays_np(
    root_path: str,
    tree_name: str,
    branches: Sequence[str],
    entry_stop: Optional[int] = None,
) -> Dict[str, np.ndarray]:
    try:
        import uproot  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "Missing dependency: uproot. Install with: pip install uproot\n"
            "This exporter is HEP-native and intentionally keeps uproot optional."
        ) from e

    tree = uproot.open(root_path)[tree_name]
    arrays = tree.arrays(list(branches), library="np", entry_stop=entry_stop)
    # arrays is dict-like: {branch: np.ndarray}
    out: Dict[str, np.ndarray] = {}
    for k in branches:
        if k not in arrays:
            raise KeyError(f"Branch '{k}' not found in tree '{tree_name}'.")
        out[k] = np.asarray(arrays[k])
    return out


def _build_X(arrs: Dict[str, np.ndarray], feature_branches: Sequence[str]) -> np.ndarray:
    cols: List[np.ndarray] = []
    n: Optional[int] = None

    for b in feature_branches:
        a = np.asarray(arrs[b])
        _reject_object_arrays(a, b)
        a = _as_1d(a, b).astype(float, copy=False)

        if n is None:
            n = int(a.shape[0])
        elif int(a.shape[0]) != n:
            raise ValueError(f"Length mismatch: '{b}' has n={a.shape[0]} but expected n={n}")

        cols.append(a)

    if n is None:
        raise ValueError("No features provided.")
    if len(cols) == 0:
        raise ValueError("No features provided.")

    X = np.column_stack(cols).astype(float, copy=False)
    if X.ndim != 2:
        raise ValueError(f"X must be 2D; got shape {X.shape}")
    return X


def _maybe_get(arrs: Dict[str, np.ndarray], key: Optional[str]) -> Optional[np.ndarray]:
    if not key:
        return None
    if key not in arrs:
        raise KeyError(f"Branch '{key}' not found (requested via CLI).")
    return np.asarray(arrs[key])


def _compute_event_id(run: np.ndarray, lumi: np.ndarray, event: np.ndarray) -> np.ndarray:
    # stable, readable traceback id
    # store as unicode array
    return np.asarray([f"{int(r)}:{int(l)}:{int(e)}" for r, l, e in zip(run, lumi, event)], dtype=str)


def export_root_to_npz(
    *,
    root_path: str,
    tree: str,
    feature_branches: Sequence[str],
    out_npz: str,
    run_branch: Optional[str] = None,
    lumi_branch: Optional[str] = None,
    event_branch: Optional[str] = None,
    event_id_branch: Optional[str] = None,
    weight_branch: Optional[str] = None,
    entry_stop: Optional[int] = None,
    make_event_id: bool = True,
    compress: bool = True,
) -> str:
    # Load all required branches in one go
    branches: List[str] = list(feature_branches)
    for b in [run_branch, lumi_branch, event_branch, event_id_branch, weight_branch]:
        if b:
            branches.append(b)

    arrs = _load_arrays_np(root_path, tree, branches, entry_stop=entry_stop)

    X = _build_X(arrs, feature_branches)
    n = X.shape[0]

    run = _maybe_get(arrs, run_branch)
    lumi = _maybe_get(arrs, lumi_branch)
    event = _maybe_get(arrs, event_branch)
    event_id = _maybe_get(arrs, event_id_branch)
    weight = _maybe_get(arrs, weight_branch)

    payload: Dict[str, np.ndarray] = {
        "X": X,
        "feature_names": np.asarray([str(b) for b in feature_branches], dtype=object),
    }

    def _check_len(a: np.ndarray, name: str) -> np.ndarray:
        _reject_object_arrays(a, name)
        a = _as_1d(a, name)
        if int(a.shape[0]) != n:
            raise ValueError(f"Length mismatch: '{name}' has n={a.shape[0]} but X has n={n}")
        return a

    if run is not None:
        payload["run"] = _check_len(run, "run").astype(np.int64, copy=False)
    if lumi is not None:
        payload["lumi"] = _check_len(lumi, "lumi").astype(np.int64, copy=False)
    if event is not None:
        payload["event"] = _check_len(event, "event").astype(np.int64, copy=False)

    if weight is not None:
        payload["weight"] = _check_len(weight, "weight").astype(float, copy=False)

    if event_id is not None:
        # accept either numeric or string-like
        event_id = _check_len(event_id, "event_id")
        payload["event_id"] = event_id
    elif make_event_id and (run is not None and lumi is not None and event is not None):
        payload["event_id"] = _compute_event_id(payload["run"], payload["lumi"], payload["event"])

    _ensure_parent_dir(out_npz)
    if compress:
        np.savez_compressed(out_npz, **payload)
    else:
        np.savez(out_npz, **payload)

    return os.path.abspath(out_npz)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="Path to ROOT file")
    ap.add_argument("--tree", required=True, help="TTree name (e.g. Events)")
    ap.add_argument("--features", required=True, help="Comma-separated feature branch list")
    ap.add_argument("--out", required=True, help="Output NPZ path")

    ap.add_argument("--run-branch", default=None, help="Branch name for run (optional)")
    ap.add_argument("--lumi-branch", default=None, help="Branch name for lumi/luminosityBlock (optional)")
    ap.add_argument("--event-branch", default=None, help="Branch name for event (optional)")
    ap.add_argument("--event-id-branch", default=None, help="Branch name for event_id (optional)")
    ap.add_argument("--weight-branch", default=None, help="Branch name for weight (optional)")

    ap.add_argument("--entry-stop", type=int, default=None, help="Read only first N entries (optional)")
    ap.add_argument("--no-event-id", action="store_true", help="Do not auto-generate event_id from run/lumi/event")
    ap.add_argument("--no-compress", action="store_true", help="Write NPZ without compression")

    args = ap.parse_args()

    features = _split_csv(args.features)
    if not features:
        raise SystemExit("No features provided (empty --features).")

    out = export_root_to_npz(
        root_path=args.root,
        tree=args.tree,
        feature_branches=features,
        out_npz=args.out,
        run_branch=args.run_branch,
        lumi_branch=args.lumi_branch,
        event_branch=args.event_branch,
        event_id_branch=args.event_id_branch,
        weight_branch=args.weight_branch,
        entry_stop=args.entry_stop,
        make_event_id=(not args.no_event_id),
        compress=(not args.no_compress),
    )

    print("Wrote:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

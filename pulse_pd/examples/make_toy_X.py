"""
Generate a synthetic feature matrix X for testing the cut-based PD runner.

Outputs a .npz containing:
- X (n, 2)
- feature_names (["x1", "x2"])
- y (optional labels for sanity checks; not required by the runner)
- run, lumi, event (HEP-style identifiers)
- event_id (string identifier "run:lumi:event")
- weight (optional event weights)

Run:
  python pulse_pd/examples/make_toy_X.py --out pulse_pd/examples/X_toy.npz --n 5000 --seed 0

Or as a module:
  python -m pulse_pd.examples.make_toy_X --out pulse_pd/examples/X_toy.npz --n 5000 --seed 0

If NumPy is installed, the existing NumPy-backed implementation is used.
If NumPy is unavailable, the command falls back to a deterministic standard-library
implementation and writes an NPZ/NPY-compatible output file.
"""

from __future__ import annotations

import argparse
import os
import random
import struct
import zipfile
from pathlib import Path
from typing import Any, Iterable, Sequence


def _try_import_numpy(force_stdlib: bool) -> Any | None:
    if force_stdlib:
        return None

    try:
        import numpy as np  # type: ignore
    except ModuleNotFoundError:
        return None

    return np


def make_synthetic_data_numpy(np: Any, n: int, seed: int) -> tuple[Any, Any]:
    """
    Mixture of two Gaussians (background + signal-like cluster).
    Returns X (n,2) and y (n,) in {0,1}.
    """
    rng = np.random.default_rng(seed)

    n_sig = n // 2
    n_bkg = n - n_sig

    mu_b = np.array([-1.0, -0.5], dtype=float)
    cov_b = np.array([[1.0, 0.2], [0.2, 0.8]], dtype=float)

    mu_s = np.array([1.2, 0.8], dtype=float)
    cov_s = np.array([[0.9, -0.15], [-0.15, 0.9]], dtype=float)

    Xb = rng.multivariate_normal(mu_b, cov_b, size=n_bkg)
    Xs = rng.multivariate_normal(mu_s, cov_s, size=n_sig)

    X = np.vstack([Xb, Xs])
    y = np.concatenate([np.zeros(n_bkg, dtype=int), np.ones(n_sig, dtype=int)])

    idx = rng.permutation(n)
    return X[idx], y[idx]


def make_synthetic_data_stdlib(n: int, seed: int) -> tuple[list[list[float]], list[int]]:
    """
    Deterministic standard-library fallback.

    This is intentionally a lightweight toy generator, not a full statistical
    replacement for the NumPy-backed multivariate-normal implementation.
    """
    rng = random.Random(seed)

    n_sig = n // 2
    n_bkg = n - n_sig

    rows: list[list[float]] = []
    labels: list[int] = []

    for _ in range(n_bkg):
        rows.append([
            rng.gauss(-1.0, 1.0),
            rng.gauss(-0.5, 0.9),
        ])
        labels.append(0)

    for _ in range(n_sig):
        rows.append([
            rng.gauss(1.2, 0.95),
            rng.gauss(0.8, 0.95),
        ])
        labels.append(1)

    order = list(range(n))
    rng.shuffle(order)

    return [rows[i] for i in order], [labels[i] for i in order]


def make_event_ids_numpy(np: Any, n: int, seed: int) -> tuple[Any, Any, Any, Any]:
    """
    Deterministic, HEP-like identifiers:
    - run: constant per file (derived from seed)
    - lumi: increments in blocks
    - event: strictly increasing unique id
    - event_id: "run:lumi:event" as string
    """
    run_number = 320000 + (seed % 1000)
    run = np.full(n, run_number, dtype=np.int64)

    block = 250
    lumi = (np.arange(n, dtype=np.int64) // block) + 1

    event = np.arange(n, dtype=np.int64) + 1

    event_id = np.array(
        [f"{run_number}:{int(l)}:{int(e)}" for l, e in zip(lumi, event)],
        dtype=object,
    )
    return run, lumi, event, event_id


def make_event_ids_stdlib(n: int, seed: int) -> tuple[list[int], list[int], list[int], list[str]]:
    run_number = 320000 + (seed % 1000)

    run = [run_number for _ in range(n)]
    lumi = [(i // 250) + 1 for i in range(n)]
    event = [i + 1 for i in range(n)]
    event_id = [f"{run_number}:{l}:{e}" for l, e in zip(lumi, event)]

    return run, lumi, event, event_id


def make_weights_numpy(np: Any, n: int, seed: int) -> Any:
    rng = np.random.default_rng(seed)
    return rng.uniform(0.8, 1.2, size=n).astype(float)


def make_weights_stdlib(n: int, seed: int) -> list[float]:
    rng = random.Random(seed + 17)
    return [0.8 + (0.4 * rng.random()) for _ in range(n)]


def _shape(value: Any) -> tuple[int, ...]:
    shape = getattr(value, "shape", None)
    if shape is not None:
        return tuple(int(item) for item in shape)

    if isinstance(value, list):
        if value and isinstance(value[0], list):
            return (len(value), len(value[0]))
        return (len(value),)

    return ()


def _tolist(value: Any) -> list[Any]:
    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        return list(tolist())

    if isinstance(value, list):
        return value

    return [value]


def _shape_repr(shape: Sequence[int]) -> str:
    if len(shape) == 1:
        return f"({int(shape[0])},)"
    return str(tuple(int(item) for item in shape))


def _npy_header(descr: str, shape: Sequence[int]) -> bytes:
    header_dict = (
        "{'descr': "
        + repr(descr)
        + ", 'fortran_order': False, 'shape': "
        + _shape_repr(shape)
        + ", }"
    )

    header_len_without_padding = len(header_dict) + 1
    padding = (16 - ((10 + header_len_without_padding) % 16)) % 16
    header = header_dict + (" " * padding) + "\n"
    header_bytes = header.encode("latin1")

    if len(header_bytes) > 65535:
        raise ValueError("NPY v1.0 header too large")

    return b"\x93NUMPY" + bytes([1, 0]) + struct.pack("<H", len(header_bytes)) + header_bytes


def _npy_float64_1d(values: Iterable[float]) -> bytes:
    vals = [float(value) for value in values]
    out = bytearray(_npy_header("<f8", (len(vals),)))

    for value in vals:
        out.extend(struct.pack("<d", value))

    return bytes(out)


def _npy_float64_2d(values: Sequence[Sequence[float]]) -> bytes:
    rows = [[float(item) for item in row] for row in values]
    cols = len(rows[0]) if rows else 0

    for row in rows:
        if len(row) != cols:
            raise ValueError("2D float array rows must have equal length")

    out = bytearray(_npy_header("<f8", (len(rows), cols)))

    for row in rows:
        for value in row:
            out.extend(struct.pack("<d", value))

    return bytes(out)


def _npy_int64_1d(values: Iterable[int]) -> bytes:
    vals = [int(value) for value in values]
    out = bytearray(_npy_header("<i8", (len(vals),)))

    for value in vals:
        out.extend(struct.pack("<q", value))

    return bytes(out)


def _npy_unicode_1d(values: Iterable[str]) -> bytes:
    vals = [str(value) for value in values]
    max_len = max([1] + [len(value) for value in vals])
    item_width = max_len * 4

    out = bytearray(_npy_header(f"<U{max_len}", (len(vals),)))

    for value in vals:
        encoded = value.encode("utf-32le")
        if len(encoded) > item_width:
            encoded = encoded[:item_width]
        out.extend(encoded)
        out.extend(b"\x00" * (item_width - len(encoded)))

    return bytes(out)


def _write_npz_stdlib(
    *,
    out_path: Path,
    X: Sequence[Sequence[float]],
    y: Sequence[int],
    feature_names: Sequence[str],
    run: Sequence[int],
    lumi: Sequence[int],
    event: Sequence[int],
    event_id: Sequence[str],
    weight: Sequence[float],
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    arrays = {
        "X.npy": _npy_float64_2d(X),
        "y.npy": _npy_int64_1d(y),
        "feature_names.npy": _npy_unicode_1d(feature_names),
        "run.npy": _npy_int64_1d(run),
        "lumi.npy": _npy_int64_1d(lumi),
        "event.npy": _npy_int64_1d(event),
        "event_id.npy": _npy_unicode_1d(event_id),
        "weight.npy": _npy_float64_1d(weight),
    }

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, payload in arrays.items():
            zf.writestr(name, payload)


def _write_npz_numpy(
    *,
    np: Any,
    out_path: Path,
    X: Any,
    y: Any,
    feature_names: Any,
    run: Any,
    lumi: Any,
    event: Any,
    event_id: Any,
    weight: Any,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    np.savez(
        out_path,
        X=X,
        y=y,
        feature_names=feature_names,
        run=run,
        lumi=lumi,
        event=event,
        event_id=event_id,
        weight=weight,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="pulse_pd/examples/X_toy.npz", help="Output .npz path")
    ap.add_argument("--n", type=int, default=5000, help="Number of samples")
    ap.add_argument("--seed", type=int, default=0, help="RNG seed")
    ap.add_argument(
        "--force-stdlib",
        action="store_true",
        help="Use the standard-library fallback even when NumPy is installed.",
    )
    args = ap.parse_args()

    if args.n <= 0:
        print("ERROR: --n must be positive")
        return 1

    np = _try_import_numpy(args.force_stdlib)
    out_path = Path(args.out)

    if np is not None:
        X, y = make_synthetic_data_numpy(np, args.n, args.seed)
        feature_names = np.array(["x1", "x2"], dtype=object)
        run, lumi, event, event_id = make_event_ids_numpy(np, args.n, args.seed)
        weight = make_weights_numpy(np, args.n, args.seed)

        _write_npz_numpy(
            np=np,
            out_path=out_path,
            X=X,
            y=y,
            feature_names=feature_names,
            run=run,
            lumi=lumi,
            event=event,
            event_id=event_id,
            weight=weight,
        )
        mode = "numpy"
    else:
        X, y = make_synthetic_data_stdlib(args.n, args.seed)
        feature_names = ["x1", "x2"]
        run, lumi, event, event_id = make_event_ids_stdlib(args.n, args.seed)
        weight = make_weights_stdlib(args.n, args.seed)

        _write_npz_stdlib(
            out_path=out_path,
            X=X,
            y=y,
            feature_names=feature_names,
            run=run,
            lumi=lumi,
            event=event,
            event_id=event_id,
            weight=weight,
        )
        mode = "stdlib"

    print("Wrote:", os.path.abspath(args.out))
    print("Mode:", mode)
    print("Keys: X, y, feature_names, run, lumi, event, event_id, weight")
    print(" - X:", _shape(X))
    print(" - y:", _shape(y))
    print(" - feature_names:", _tolist(feature_names))
    print(" - run/lumi/event:", _shape(run), _shape(lumi), _shape(event))
    print(" - event_id:", _shape(event_id))
    print(" - weight:", _shape(weight))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Regression tests for the lightweight PULSE-PD toy generator fallback path."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run_make_toy(out_path: Path, *, force_stdlib: bool = True) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        "-m",
        "pulse_pd.examples.make_toy_X",
        "--out",
        str(out_path),
        "--n",
        "20",
        "--seed",
        "0",
    ]

    if force_stdlib:
        cmd.append("--force-stdlib")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)

    return subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_pulse_pd_package_import_does_not_require_numpy() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys\n"
                "sys.modules['numpy'] = None\n"
                "import pulse_pd\n"
                "print('OK: pulse_pd imported without eager NumPy import')\n"
            ),
        ],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "OK: pulse_pd imported without eager NumPy import" in result.stdout


def test_make_toy_x_stdlib_fallback_writes_npz() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-pd-toy-") as td:
        out_path = Path(td) / "X_toy_ci.npz"

        result = _run_make_toy(out_path, force_stdlib=True)

        assert result.returncode == 0, result.stderr + result.stdout
        assert out_path.exists()
        assert "Mode: stdlib" in result.stdout

        with zipfile.ZipFile(out_path, "r") as zf:
            names = set(zf.namelist())

        assert names == {
            "X.npy",
            "y.npy",
            "feature_names.npy",
            "run.npy",
            "lumi.npy",
            "event.npy",
            "event_id.npy",
            "weight.npy",
        }


def test_make_toy_x_stdlib_npz_is_numpy_loadable_when_numpy_available() -> None:
    try:
        import numpy as np  # type: ignore
    except ModuleNotFoundError:
        return

    with tempfile.TemporaryDirectory(prefix="pulse-pd-toy-") as td:
        out_path = Path(td) / "X_toy_ci.npz"

        result = _run_make_toy(out_path, force_stdlib=True)

        assert result.returncode == 0, result.stderr + result.stdout
        assert out_path.exists()

        with np.load(out_path, allow_pickle=False) as data:
            assert data["X"].shape == (20, 2)
            assert data["y"].shape == (20,)
            assert data["feature_names"].tolist() == ["x1", "x2"]
            assert data["run"].shape == (20,)
            assert data["lumi"].shape == (20,)
            assert data["event"].shape == (20,)
            assert data["event_id"].shape == (20,)
            assert data["weight"].shape == (20,)


def main() -> int:
    try:
        test_pulse_pd_package_import_does_not_require_numpy()
        test_make_toy_x_stdlib_fallback_writes_npz()
        test_make_toy_x_stdlib_npz_is_numpy_loadable_when_numpy_available()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: PULSE-PD toy generator NumPy fallback tests passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())

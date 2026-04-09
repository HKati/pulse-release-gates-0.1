#!/usr/bin/env python3
"""
PULSE run_relational_gain_shadow.py

Shadow-only orchestration wrapper for relational gain.

Purpose:
- run the relational gain checker
- write/update the shadow artifact
- fold the result into status.json under meta.relational_gain_shadow

Shadow-only behavior:
- checker PASS / WARN / FAIL remain diagnostic
- this wrapper exits 0 when checker execution and fold-in succeed
- checker FAIL does not become a release-blocking outcome here
- tool/runtime/schema/input errors remain non-zero

Exit codes:
- 0: shadow run completed successfully (including checker FAIL folded as shadow)
- 2: missing required input / invalid input / tool or fold-in failure
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKER = REPO_ROOT / "PULSE_safe_pack_v0" / "tools" / "check_relational_gain.py"
FOLD_TOOL = REPO_ROOT / "PULSE_safe_pack_v0" / "tools" / "fold_relational_gain_shadow.py"
DEFAULT_ARTIFACT_OUT = REPO_ROOT / "PULSE_safe_pack_v0" / "artifacts" / "relational_gain_shadow_v0.json"


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def _fail(msg: str) -> None:
    _eprint(f"[X] {msg}")
    raise SystemExit(2)


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )


def _replay(proc: subprocess.CompletedProcess[str]) -> None:
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)


def _remove_file_if_exists(path: Path) -> None:
    if not path.exists():
        return
    try:
        path.unlink()
    except OSError as e:
        _fail(f"failed to remove stale artifact at {path}: {e}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Shadow-only relational gain checker and fold the result "
            "into status.json under meta.relational_gain_shadow."
        )
    )
    parser.add_argument(
        "--status",
        required=True,
        help="Path to the input status.json.",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the relational gain input JSON.",
    )
    parser.add_argument(
        "--artifact-out",
        default=str(DEFAULT_ARTIFACT_OUT),
        help=(
            "Path to the generated shadow artifact JSON "
            f"(default: {DEFAULT_ARTIFACT_OUT})."
        ),
    )
    parser.add_argument(
        "--status-out",
        help=(
            "Optional output path for the updated status.json. "
            "If omitted, the status file is updated in place."
        ),
    )
    parser.add_argument(
        "--warn-threshold",
        type=float,
        default=None,
        help="Optional warning threshold override passed through to the checker.",
    )
    parser.add_argument(
        "--edge-key",
        default="edge_gains",
        help="Input key for edge gains passed through to the checker.",
    )
    parser.add_argument(
        "--cycle-key",
        default="cycle_gains",
        help="Input key for cycle gains passed through to the checker.",
    )
    parser.add_argument(
        "--require-data",
        action="store_true",
        help="Require edge/cycle gain data to be present in the input payload.",
    )
    parser.add_argument(
        "--if-input-present",
        action="store_true",
        help=(
            "If the relational gain input is missing, keep absence neutral: "
            "remove any stale fold-in via the fold tool's --if-present path "
            "and exit 0."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    status_path = Path(args.status)
    input_path = Path(args.input)
    artifact_out = Path(args.artifact_out)
    status_out = Path(args.status_out) if args.status_out else status_path

    if not status_path.exists():
        _fail(f"status file not found: {status_path}")

    if not input_path.exists():
        if args.if_input_present:
            _remove_file_if_exists(artifact_out)

            fold_cmd = [
                sys.executable,
                str(FOLD_TOOL),
                "--status",
                str(status_path),
                "--shadow-artifact",
                str(artifact_out),
                "--if-present",
                "--out",
                str(status_out),
            ]
            fold_proc = _run(fold_cmd)
            _replay(fold_proc)

            if fold_proc.returncode != 0:
                raise SystemExit(fold_proc.returncode)

            return 0

        _fail(f"relational gain input not found: {input_path}")

    checker_cmd = [
        sys.executable,
        str(CHECKER),
        "--input",
        str(input_path),
        "--out",
        str(artifact_out),
        "--edge-key",
        args.edge_key,
        "--cycle-key",
        args.cycle_key,
    ]
    if args.warn_threshold is not None:
        checker_cmd.extend(["--warn-threshold", str(args.warn_threshold)])
    if args.require_data:
        checker_cmd.append("--require-data")

    checker_proc = _run(checker_cmd)
    _replay(checker_proc)

    # PASS/WARN/FAIL are all acceptable shadow outcomes here.
    # Only tool/runtime/schema/input errors should stop orchestration.
    if checker_proc.returncode not in (0, 1):
        raise SystemExit(checker_proc.returncode)

    fold_cmd = [
        sys.executable,
        str(FOLD_TOOL),
        "--status",
        str(status_path),
        "--shadow-artifact",
        str(artifact_out),
        "--out",
        str(status_out),
    ]
    fold_proc = _run(fold_cmd)
    _replay(fold_proc)

    if fold_proc.returncode != 0:
        raise SystemExit(fold_proc.returncode)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "PULSE_safe_pack_v0" / "tools" / "augment_status.py"


def write_status(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "created_utc": "1970-01-01T00:00:00Z",
                "gates": {},
                "metrics": {},
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def run_augment(
    status_path: Path,
    thresholds_path: Path,
    external_dir: Path,
    *,
    strict: bool,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(TOOL),
        "--status",
        str(status_path),
        "--thresholds",
        str(thresholds_path),
        "--external_dir",
        str(external_dir),
    ]

    if strict:
        cmd.append("--require_external_summaries")

    return subprocess.run(
        cmd,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
    )


def read_status(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_strict_decoy_only_external_summary_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        status_path = tmp / "status.json"
        thresholds_path = tmp / "external_thresholds.yaml"
        external_dir = tmp / "external"
        external_dir.mkdir()

        write_status(status_path)
        thresholds_path.write_text("llamaguard_violation_rate_max: 0.10\n", encoding="utf-8")

        (external_dir / "foo_summary.json").write_text(
            json.dumps({"value": 0.0}) + "\n",
            encoding="utf-8",
        )

        result = run_augment(
            status_path,
            thresholds_path,
            external_dir,
            strict=True,
        )

        assert result.returncode == 0, result.stderr

        status = read_status(status_path)
        assert status["gates"]["external_summaries_present"] is False
        assert status["gates"]["external_all_pass"] is False
        assert status["external"]["summaries_present"] is False
        assert status["external"]["summary_count"] == 1
        assert status["external"]["canonical_summary_count"] == 0
        assert status["external"]["unrecognized_summary_count"] == 1
        assert status["external"]["metrics"] == []


def test_strict_no_external_summary_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        status_path = tmp / "status.json"
        thresholds_path = tmp / "external_thresholds.yaml"
        external_dir = tmp / "external"
        external_dir.mkdir()

        write_status(status_path)
        thresholds_path.write_text("llamaguard_violation_rate_max: 0.10\n", encoding="utf-8")

        result = run_augment(
            status_path,
            thresholds_path,
            external_dir,
            strict=True,
        )

        assert result.returncode == 0, result.stderr

        status = read_status(status_path)
        assert status["gates"]["external_summaries_present"] is False
        assert status["gates"]["external_all_pass"] is False
        assert status["external"]["summaries_present"] is False
        assert status["external"]["canonical_summary_count"] == 0
        assert status["external"]["metrics"] == []


def test_strict_canonical_external_summary_passes_when_folded() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        status_path = tmp / "status.json"
        thresholds_path = tmp / "external_thresholds.yaml"
        external_dir = tmp / "external"
        external_dir.mkdir()

        write_status(status_path)
        thresholds_path.write_text("llamaguard_violation_rate_max: 0.10\n", encoding="utf-8")

        (external_dir / "llamaguard_summary.json").write_text(
            json.dumps({"rate": 0.02}) + "\n",
            encoding="utf-8",
        )

        result = run_augment(
            status_path,
            thresholds_path,
            external_dir,
            strict=True,
        )

        assert result.returncode == 0, result.stderr

        status = read_status(status_path)
        assert status["gates"]["external_summaries_present"] is True
        assert status["gates"]["external_all_pass"] is True
        assert status["external"]["summaries_present"] is True
        assert status["external"]["canonical_summary_count"] == 1
        assert len(status["external"]["metrics"]) == 1
        assert status["external"]["metrics"][0]["pass"] is True


def test_strict_canonical_external_summary_fails_when_metric_fails() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        status_path = tmp / "status.json"
        thresholds_path = tmp / "external_thresholds.yaml"
        external_dir = tmp / "external"
        external_dir.mkdir()

        write_status(status_path)
        thresholds_path.write_text("llamaguard_violation_rate_max: 0.10\n", encoding="utf-8")

        (external_dir / "llamaguard_summary.json").write_text(
            json.dumps({"rate": 0.50}) + "\n",
            encoding="utf-8",
        )

        result = run_augment(
            status_path,
            thresholds_path,
            external_dir,
            strict=True,
        )

        assert result.returncode == 0, result.stderr

        status = read_status(status_path)
        assert status["gates"]["external_summaries_present"] is True
        assert status["gates"]["external_all_pass"] is False
        assert status["external"]["summaries_present"] is True
        assert status["external"]["canonical_summary_count"] == 1
        assert len(status["external"]["metrics"]) == 1
        assert status["external"]["metrics"][0]["pass"] is False

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
FOLDER = REPO_ROOT / "PULSE_safe_pack_v0" / "tools" / "fold_relational_gain_shadow.py"


def _run_fold(
    status_path: Path,
    shadow_artifact_path: Path,
    *extra_args: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(FOLDER),
            "--status",
            str(status_path),
            "--shadow-artifact",
            str(shadow_artifact_path),
            *extra_args,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _minimal_status() -> dict[str, Any]:
    return {
        "schema_version": "status_v0",
        "gates": {"pass": True},
        "meta": {
            "existing_shadow": {"note": "preserve me"},
        },
    }


def _shadow_artifact() -> dict[str, Any]:
    return {
        "checker_version": "relational_gain_v0",
        "verdict": "WARN",
        "metrics": {
            "max_edge_gain": 0.97,
            "max_cycle_gain": 0.91,
            "warn_threshold": 0.95,
            "checked_edges": 3,
            "checked_cycles": 2,
        },
    }


def test_if_present_missing_artifact_clears_existing_shadow_block(tmp_path: Path) -> None:
    status_path = tmp_path / "status.json"
    missing_shadow_artifact_path = tmp_path / "missing_shadow.json"
    out_path = tmp_path / "status.folded.json"

    status_payload = _minimal_status()
    status_payload["meta"]["relational_gain_shadow"] = {
        "verdict": "WARN",
        "max_edge_gain": 0.97,
        "max_cycle_gain": 0.91,
        "warn_threshold": 0.95,
        "checked_edges": 3,
        "checked_cycles": 2,
        "artifact": {
            "path": "old/path.json",
            "sha256": "oldhash",
        },
    }
    _write_json(status_path, status_payload)

    result = _run_fold(
        status_path,
        missing_shadow_artifact_path,
        "--if-present",
        "--out",
        str(out_path),
    )

    assert result.returncode == 0, result.stderr
    folded = json.loads(out_path.read_text(encoding="utf-8"))

    assert "relational_gain_shadow" not in folded.get("meta", {})
    assert folded["meta"]["existing_shadow"] == {"note": "preserve me"}


def test_checker_version_mismatch_fails_closed(tmp_path: Path) -> None:
    status_path = tmp_path / "status.json"
    shadow_artifact_path = tmp_path / "relational_gain_shadow_v0.json"

    _write_json(status_path, _minimal_status())
    bad_artifact = _shadow_artifact()
    bad_artifact["checker_version"] = "wrong_checker_v0"
    _write_json(shadow_artifact_path, bad_artifact)

    result = _run_fold(status_path, shadow_artifact_path)

    assert result.returncode == 2
    assert "unexpected 'checker_version'" in result.stderr

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "operator_handoff_smoke.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(SCRIPT), *args]
    return subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_ok(result: subprocess.CompletedProcess[str], expected: int) -> None:
    if result.returncode != expected:
        raise AssertionError(
            f"unexpected return code: expected={expected} got={result.returncode}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )


def test_generate_core_honors_custom_status_path() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-operator-handoff-") as tmp:
        tmp_path = Path(tmp)
        status_path = tmp_path / "operator_handoff_status.custom.json"
        report_path = tmp_path / "operator_handoff_smoke.json"

        result = _run(
            "--status",
            str(status_path),
            "--out",
            str(report_path),
        )

        _assert_ok(result, 0)
        assert status_path.exists()
        assert report_path.exists()

        payload = _read_json(report_path)

        assert payload["ok"] is True
        assert payload["gate_mode"] == "core"
        assert payload["status_source"]["mode"] == "generate-core"
        assert payload["status_source"]["status_path"] == str(status_path)
        assert payload["status_source"]["generated_artifact_dir"] == str(
            status_path.parent
        )
        assert payload["status_source"]["generated_status_path"] == str(
            status_path.parent / "status.json"
        )
        assert payload["status_source"]["status_exists_after_run"] is True

        command_names = [command["name"] for command in payload["commands"]]

        assert "generate_core_status" in command_names
        assert "materialize_core_required" in command_names
        assert "check_gates_core" in command_names
        assert "check_shadow_layer_registry" in command_names

        generate_command = next(
            command
            for command in payload["commands"]
            if command["name"] == "generate_core_status"
        )

        assert generate_command["env_overrides"]["PULSE_ARTIFACT_DIR"] == str(
            status_path.parent
        )
        assert any(
            "copied generated Core status artifact" in warning
            for warning in payload["warnings"]
        )


def test_release_grade_rejects_generate_core_status() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-operator-handoff-") as tmp:
        tmp_path = Path(tmp)
        status_path = tmp_path / "status.json"
        report_path = tmp_path / "operator_handoff_smoke.release_grade.json"

        result = _run(
            "--gate-mode",
            "release-grade",
            "--status-source",
            "generate-core",
            "--status",
            str(status_path),
            "--out",
            str(report_path),
        )

        _assert_ok(result, 1)
        assert report_path.exists()

        payload = _read_json(report_path)

        assert payload["ok"] is False
        assert payload["gate_mode"] == "release-grade"
        assert payload["commands"] == []
        assert any(
            "release-grade gate-mode requires --status-source existing" in error
            for error in payload["errors"]
        )


def test_existing_missing_status_fails_closed() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-operator-handoff-") as tmp:
        tmp_path = Path(tmp)
        status_path = tmp_path / "missing_status.json"
        report_path = tmp_path / "operator_handoff_smoke.missing_status.json"

        result = _run(
            "--status-source",
            "existing",
            "--status",
            str(status_path),
            "--out",
            str(report_path),
        )

        _assert_ok(result, 1)
        assert report_path.exists()

        payload = _read_json(report_path)

        assert payload["ok"] is False
        assert payload["status_source"]["mode"] == "existing"
        assert payload["status_source"]["status_exists_before_run"] is False
        assert payload["status_source"]["status_exists_after_run"] is False
        assert any(
            "status artifact missing" in error
            for error in payload["errors"]
        )
        assert any(
            "status-source=existing was selected" in warning
            for warning in payload["warnings"]
        )


def main() -> int:
    try:
        test_generate_core_honors_custom_status_path()
        test_release_grade_rejects_generate_core_status()
        test_existing_missing_status_fails_closed()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: operator handoff smoke regression passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())

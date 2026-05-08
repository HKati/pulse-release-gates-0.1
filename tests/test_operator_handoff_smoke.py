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


def _assert_returncode(
    result: subprocess.CompletedProcess[str],
    expected: int,
) -> None:
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

        _assert_returncode(result, 0)

        assert status_path.exists()
        assert report_path.exists()

        payload = _read_json(report_path)

        assert payload["ok"] is True
        assert payload["gate_mode"] == "core"

        status_source = payload["status_source"]
        assert status_source["mode"] == "generate-core"
        assert status_source["status_path"] == str(status_path)
        assert status_source["generated_artifact_dir"] == str(status_path.parent)
        assert status_source["generated_status_path"] == str(
            status_path.parent / "status.json"
        )
        assert status_source["status_exists_before_run"] is False
        assert status_source["status_exists_after_generation"] is True
        assert status_source["status_exists_after_run"] is True

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

        assert generate_command["ok"] is True
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

        _assert_returncode(result, 1)

        assert report_path.exists()

        payload = _read_json(report_path)

        assert payload["ok"] is False
        assert payload["gate_mode"] == "release-grade"
        assert payload["commands"] == []
        assert payload["materialized_gate_sets"] == {}
        assert payload["effective_required_gates"] == []

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

        _assert_returncode(result, 1)

        assert report_path.exists()

        payload = _read_json(report_path)

        assert payload["ok"] is False

        status_source = payload["status_source"]
        assert status_source["mode"] == "existing"
        assert status_source["status_path"] == str(status_path)
        assert status_source["status_exists_before_run"] is False
        assert status_source["status_exists_after_generation"] is False
        assert status_source["status_exists_after_run"] is False

        assert payload["commands"] == []
        assert payload["materialized_gate_sets"] == {}
        assert payload["effective_required_gates"] == []

        assert any(
            "status artifact missing" in error
            for error in payload["errors"]
        )
        assert any(
            "status-source=existing was selected" in warning
            for warning in payload["warnings"]
        )


def test_release_grade_accepts_existing_release_reference_status() -> None:
    fixture_status = (
        ROOT
        / "tests"
        / "fixtures"
        / "release_reference_v1"
        / "refusal_delta_evidence_present"
        / "status.json"
    )
    expected_status_path = str(fixture_status.relative_to(ROOT))

    assert fixture_status.exists(), f"missing release-reference fixture: {fixture_status}"

    with tempfile.TemporaryDirectory(prefix="pulse-operator-handoff-") as tmp:
        tmp_path = Path(tmp)
        report_path = tmp_path / "operator_handoff_smoke.release_grade.pass.json"

        result = _run(
            "--gate-mode",
            "release-grade",
            "--status-source",
            "existing",
            "--status",
            str(fixture_status),
            "--out",
            str(report_path),
        )

        _assert_returncode(result, 0)

        assert report_path.exists()

        payload = _read_json(report_path)

        assert payload["ok"] is True
        assert payload["gate_mode"] == "release-grade"

        status_source = payload["status_source"]
        assert status_source["mode"] == "existing"
        assert status_source["status_path"] == expected_status_path
        assert status_source["status_exists_before_run"] is True
        assert status_source["status_exists_after_generation"] is True
        assert status_source["status_exists_after_run"] is True

        assert "required" in payload["materialized_gate_sets"]
        assert "release_required" in payload["materialized_gate_sets"]

        assert "refusal_delta_evidence_present" in payload["effective_required_gates"]

        command_names = [command["name"] for command in payload["commands"]]

        assert "materialize_required" in command_names
        assert "materialize_release_required" in command_names
        assert "check_gates_release-grade" in command_names
        assert "check_shadow_layer_registry" in command_names

def test_release_grade_existing_missing_refusal_delta_fails_closed() -> None:
    fixture_status = (
        ROOT
        / "tests"
        / "fixtures"
        / "release_reference_v1"
        / "missing_refusal_delta"
        / "status.json"
    )
    expected_status_path = str(fixture_status.relative_to(ROOT))

    assert fixture_status.exists(), f"missing release-reference fixture: {fixture_status}"

    with tempfile.TemporaryDirectory(prefix="pulse-operator-handoff-") as tmp:
        tmp_path = Path(tmp)
        report_path = tmp_path / "operator_handoff_smoke.release_grade.missing_refusal_delta.json"

        result = _run(
            "--gate-mode",
            "release-grade",
            "--status-source",
            "existing",
            "--status",
            str(fixture_status),
            "--out",
            str(report_path),
        )

        _assert_returncode(result, 1)

        assert report_path.exists()

        payload = _read_json(report_path)

        assert payload["ok"] is False
        assert payload["gate_mode"] == "release-grade"

        status_source = payload["status_source"]
        assert status_source["mode"] == "existing"
        assert status_source["status_path"] == expected_status_path
        assert status_source["status_exists_before_run"] is True
        assert status_source["status_exists_after_generation"] is True
        assert status_source["status_exists_after_run"] is True

        assert "required" in payload["materialized_gate_sets"]
        assert "release_required" in payload["materialized_gate_sets"]
        assert "refusal_delta_evidence_present" in payload["effective_required_gates"]

        command_names = [command["name"] for command in payload["commands"]]

        assert "materialize_required" in command_names
        assert "materialize_release_required" in command_names
        assert "check_gates_release-grade" in command_names

        check_command = next(
            command
            for command in payload["commands"]
            if command["name"] == "check_gates_release-grade"
        )

        assert check_command["ok"] is False
        assert check_command["returncode"] != 0

        combined_output = f"{check_command.get('stdout', '')}\n{check_command.get('stderr', '')}"
        assert "refusal_delta_evidence_present" in combined_output

        assert any(
            "gate check failed in release-grade mode" in error
            for error in payload["errors"]
        )

def test_release_grade_existing_external_evidence_failures_fail_closed() -> None:
    cases = [
        ("malformed_summary", "external_all_pass"),
        ("unsigned_summary", "external_all_pass"),
    ]

    for fixture_id, expected_failing_gate in cases:
        fixture_status = (
            ROOT
            / "tests"
            / "fixtures"
            / "release_reference_v1"
            / fixture_id
            / "status.json"
        )
        expected_status_path = str(fixture_status.relative_to(ROOT))

        assert fixture_status.exists(), f"missing release-reference fixture: {fixture_status}"

        with tempfile.TemporaryDirectory(prefix="pulse-operator-handoff-") as tmp:
            tmp_path = Path(tmp)
            report_path = (
                tmp_path
                / f"operator_handoff_smoke.release_grade.{fixture_id}.json"
            )

            result = _run(
                "--gate-mode",
                "release-grade",
                "--status-source",
                "existing",
                "--status",
                str(fixture_status),
                "--out",
                str(report_path),
            )

            _assert_returncode(result, 1)

            assert report_path.exists()

            payload = _read_json(report_path)

            assert payload["ok"] is False
            assert payload["gate_mode"] == "release-grade"

            status_source = payload["status_source"]
            assert status_source["mode"] == "existing"
            assert status_source["status_path"] == expected_status_path
            assert status_source["status_exists_before_run"] is True
            assert status_source["status_exists_after_generation"] is True
            assert status_source["status_exists_after_run"] is True

            assert "required" in payload["materialized_gate_sets"]
            assert "release_required" in payload["materialized_gate_sets"]
            assert expected_failing_gate in payload["effective_required_gates"]

            command_names = [command["name"] for command in payload["commands"]]

            assert "materialize_required" in command_names
            assert "materialize_release_required" in command_names
            assert "check_gates_release-grade" in command_names

            check_command = next(
                command
                for command in payload["commands"]
                if command["name"] == "check_gates_release-grade"
            )

            assert check_command["ok"] is False
            assert check_command["returncode"] != 0

            combined_output = (
                f"{check_command.get('stdout', '')}\n"
                f"{check_command.get('stderr', '')}"
            )
            assert expected_failing_gate in combined_output

            assert any(
                "gate check failed in release-grade mode" in error
                for error in payload["errors"]
            )

def test_release_grade_existing_missing_external_summary_fails_closed() -> None:
    fixture_status = (
        ROOT
        / "tests"
        / "fixtures"
        / "release_reference_v1"
        / "missing_external"
        / "status.json"
    )
    expected_status_path = str(fixture_status.relative_to(ROOT))
    expected_failing_gate = "external_summaries_present"

    assert fixture_status.exists(), f"missing release-reference fixture: {fixture_status}"

    with tempfile.TemporaryDirectory(prefix="pulse-operator-handoff-") as tmp:
        tmp_path = Path(tmp)
        report_path = (
            tmp_path
            / "operator_handoff_smoke.release_grade.missing_external.json"
        )

        result = _run(
            "--gate-mode",
            "release-grade",
            "--status-source",
            "existing",
            "--status",
            str(fixture_status),
            "--out",
            str(report_path),
        )

        _assert_returncode(result, 1)

        assert report_path.exists()

        payload = _read_json(report_path)

        assert payload["ok"] is False
        assert payload["gate_mode"] == "release-grade"

        status_source = payload["status_source"]
        assert status_source["mode"] == "existing"
        assert status_source["status_path"] == expected_status_path
        assert status_source["status_exists_before_run"] is True
        assert status_source["status_exists_after_generation"] is True
        assert status_source["status_exists_after_run"] is True

        assert "required" in payload["materialized_gate_sets"]
        assert "release_required" in payload["materialized_gate_sets"]
        assert expected_failing_gate in payload["effective_required_gates"]

        command_names = [command["name"] for command in payload["commands"]]

        assert "materialize_required" in command_names
        assert "materialize_release_required" in command_names
        assert "check_gates_release-grade" in command_names

        check_command = next(
            command
            for command in payload["commands"]
            if command["name"] == "check_gates_release-grade"
        )

        assert check_command["ok"] is False
        assert check_command["returncode"] != 0

        combined_output = (
            f"{check_command.get('stdout', '')}\n"
            f"{check_command.get('stderr', '')}"
        )
        assert expected_failing_gate in combined_output

        assert any(
            "gate check failed in release-grade mode" in error
            for error in payload["errors"]
        )


def test_release_grade_existing_stubbed_status_fails_closed() -> None:
    fixture_status = (
        ROOT
        / "tests"
        / "fixtures"
        / "release_reference_v1"
        / "stubbed"
        / "status.json"
    )
    expected_status_path = str(fixture_status.relative_to(ROOT))

    assert fixture_status.exists(), f"missing release-reference fixture: {fixture_status}"

    with tempfile.TemporaryDirectory(prefix="pulse-operator-handoff-") as tmp:
        tmp_path = Path(tmp)
        report_path = tmp_path / "operator_handoff_smoke.release_grade.stubbed.json"

        result = _run(
            "--gate-mode",
            "release-grade",
            "--status-source",
            "existing",
            "--status",
            str(fixture_status),
            "--out",
            str(report_path),
        )

        _assert_returncode(result, 1)

        assert report_path.exists()

        payload = _read_json(report_path)

        assert payload["ok"] is False
        assert payload["gate_mode"] == "release-grade"

        status_source = payload["status_source"]
        assert status_source["mode"] == "existing"
        assert status_source["status_path"] == expected_status_path
        assert status_source["status_exists_before_run"] is True
        assert status_source["status_exists_after_generation"] is True
        assert status_source["status_exists_after_run"] is True

        assert payload["commands"] == []
        assert payload["materialized_gate_sets"] == {}
        assert payload["effective_required_gates"] == []

        assert any(
            "diagnostics.gates_stubbed=false" in error
            for error in payload["errors"]
        )
        assert any(
            "stubbed status evidence" in error
            for error in payload["errors"]
        )

def test_release_grade_existing_non_prod_run_mode_fails_closed() -> None:
    source_status = (
        ROOT
        / "tests"
        / "fixtures"
        / "release_reference_v1"
        / "refusal_delta_evidence_present"
        / "status.json"
    )

    assert source_status.exists(), f"missing release-reference fixture: {source_status}"

    with tempfile.TemporaryDirectory(prefix="pulse-operator-handoff-") as tmp:
        tmp_path = Path(tmp)
        status_path = tmp_path / "operator_handoff_status.non_prod.json"
        report_path = tmp_path / "operator_handoff_smoke.release_grade.non_prod.json"

        status_obj = _read_json(source_status)
        metrics = status_obj.setdefault("metrics", {})
        metrics["run_mode"] = "core"

        status_path.write_text(
            json.dumps(status_obj, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        result = _run(
            "--gate-mode",
            "release-grade",
            "--status-source",
            "existing",
            "--status",
            str(status_path),
            "--out",
            str(report_path),
        )

        _assert_returncode(result, 1)

        assert report_path.exists()

        payload = _read_json(report_path)

        assert payload["ok"] is False
        assert payload["gate_mode"] == "release-grade"

        status_source = payload["status_source"]
        assert status_source["mode"] == "existing"
        assert status_source["status_path"] == str(status_path)
        assert status_source["status_exists_before_run"] is True
        assert status_source["status_exists_after_generation"] is True
        assert status_source["status_exists_after_run"] is True

        assert payload["commands"] == []
        assert payload["materialized_gate_sets"] == {}
        assert payload["effective_required_gates"] == []

        assert any(
            "metrics.run_mode=prod" in error
            for error in payload["errors"]
        )
        assert any(
            "found 'core'" in error
            for error in payload["errors"]
        )

def test_release_grade_existing_malformed_status_fails_closed() -> None:
    cases = [
        ("malformed_json", "{not json\n"),
        ("json_array", "[]\n"),
    ]

    for case_id, status_text in cases:
        with tempfile.TemporaryDirectory(prefix="pulse-operator-handoff-") as tmp:
            tmp_path = Path(tmp)
            status_path = tmp_path / f"operator_handoff_status.{case_id}.json"
            report_path = (
                tmp_path
                / f"operator_handoff_smoke.release_grade.{case_id}.json"
            )

            status_path.write_text(status_text, encoding="utf-8")

            result = _run(
                "--gate-mode",
                "release-grade",
                "--status-source",
                "existing",
                "--status",
                str(status_path),
                "--out",
                str(report_path),
            )

            _assert_returncode(result, 1)

            assert report_path.exists()

            payload = _read_json(report_path)

            assert payload["ok"] is False
            assert payload["gate_mode"] == "release-grade"

            status_source = payload["status_source"]
            assert status_source["mode"] == "existing"
            assert status_source["status_path"] == str(status_path)
            assert status_source["status_exists_before_run"] is True
            assert status_source["status_exists_after_generation"] is True
            assert status_source["status_exists_after_run"] is True

            assert payload["commands"] == []
            assert payload["materialized_gate_sets"] == {}
            assert payload["effective_required_gates"] == []

            assert any(
                "status artifact is not a JSON object" in error
                for error in payload["errors"]
            )

def main() -> int:
    try:
        test_generate_core_honors_custom_status_path()
        test_release_grade_rejects_generate_core_status()
        test_existing_missing_status_fails_closed()
        test_release_grade_accepts_existing_release_reference_status()
        test_release_grade_existing_missing_refusal_delta_fails_closed()
        test_release_grade_existing_external_evidence_failures_fail_closed()
        test_release_grade_existing_missing_external_summary_fails_closed()
        test_release_grade_existing_stubbed_status_fails_closed()
        test_release_grade_existing_non_prod_run_mode_fails_closed()
        test_release_grade_existing_malformed_status_fails_closed()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: operator handoff smoke regression passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())

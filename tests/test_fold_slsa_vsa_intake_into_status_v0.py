import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

INGEST_TOOL = ROOT / "tools" / "ingest_slsa_vsa_evidence_v0.py"
FOLD_TOOL = ROOT / "tools" / "fold_slsa_vsa_intake_into_status_v0.py"

SCHEMA = ROOT / "schemas" / "slsa_vsa_evidence_v0.schema.json"
EXAMPLE = ROOT / "examples" / "slsa" / "slsa_vsa_evidence_example_v0.json"

REQUIRED_PULSE_SIGNALS = [
    "slsa_vsa_present",
    "slsa_vsa_signature_ok",
    "slsa_vsa_subject_matches_artifact",
    "slsa_vsa_predicate_type_ok",
    "slsa_vsa_verifier_trusted",
    "slsa_vsa_resource_uri_matches",
    "slsa_vsa_policy_digest_matches",
    "slsa_vsa_result_passed",
    "slsa_vsa_verified_level_ok",
]

EXPECTED_INGEST_ARGS = [
    "--expect-subject-name",
    "git+https://github.com/HKati/pulse-release-gates-0.1@refs/tags/v0.1.0",
    "--expect-subject-sha256",
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "--expect-resource-uri",
    "git+https://github.com/HKati/pulse-release-gates-0.1@refs/tags/v0.1.0",
    "--expect-verifier-id",
    "https://example.invalid/verifiers/pulsemech-vsa-verifier-v0",
    "--expect-policy-sha256",
    "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "--expect-verified-level",
    "SLSA_BUILD_LEVEL_3",
]


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_base_status(path: Path) -> None:
    write_json(
        path,
        {
            "schema_version": "test_status_v0",
            "run_id": "fold-slsa-vsa-intake-test",
            "gates": {
                "existing_gate": True
            },
        },
    )


def run_ingest_report(output: Path) -> dict:
    cmd = [
        sys.executable,
        str(INGEST_TOOL),
        "--schema",
        str(SCHEMA),
        "--evidence",
        str(EXAMPLE),
        *EXPECTED_INGEST_ARGS,
        "--output",
        str(output),
    ]

    result = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["ok"] is True
    assert output.exists()
    assert read_json(output) == report
    return report


def run_fold(status: Path, intake_report: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(FOLD_TOOL),
            "--status",
            str(status),
            "--intake-report",
            str(intake_report),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def parse_report(result: subprocess.CompletedProcess[str]) -> dict:
    assert result.stdout, result.stderr
    return json.loads(result.stdout)


def assert_failure(result: subprocess.CompletedProcess[str], expected_fragment: str) -> dict:
    assert result.returncode != 0, result.stdout + result.stderr
    assert "Traceback" not in result.stderr

    report = parse_report(result)
    assert report["ok"] is False
    assert report["output_status_written"] is False
    assert any(expected_fragment in error for error in report["errors"]), report["errors"]
    return report


def check_valid_fold_in(tmp_dir: Path) -> None:
    status_path = tmp_dir / "status_input.json"
    intake_path = tmp_dir / "intake_report.json"
    output_path = tmp_dir / "status_output.json"

    make_base_status(status_path)
    base_hash_before = sha256_file(status_path)

    run_ingest_report(intake_path)

    result = run_fold(status_path, intake_path, output_path)
    assert result.returncode == 0, result.stdout + result.stderr

    base_hash_after = sha256_file(status_path)
    assert base_hash_before == base_hash_after

    report = parse_report(result)
    assert report["tool"] == "fold_slsa_vsa_intake_into_status_v0"
    assert report["ok"] is True
    assert report["output_status_written"] is True
    assert report["errors"] == []
    assert report["folded_gates"] == REQUIRED_PULSE_SIGNALS

    folded_status = read_json(output_path)
    assert folded_status["gates"]["existing_gate"] is True

    for signal in REQUIRED_PULSE_SIGNALS:
        assert folded_status["gates"][signal] is True


def check_report_not_ok_fails(tmp_dir: Path) -> None:
    status_path = tmp_dir / "status_input.json"
    intake_path = tmp_dir / "intake_report_not_ok.json"
    output_path = tmp_dir / "status_output_not_ok.json"

    make_base_status(status_path)
    report = run_ingest_report(tmp_dir / "valid_intake_report.json")
    report["ok"] = False
    report["errors"] = ["synthetic_error"]
    write_json(intake_path, report)

    result = run_fold(status_path, intake_path, output_path)
    assert_failure(result, "intake_report_not_ok")
    assert not output_path.exists()


def check_missing_signal_fails(tmp_dir: Path) -> None:
    status_path = tmp_dir / "status_input.json"
    intake_path = tmp_dir / "intake_report_missing_signal.json"
    output_path = tmp_dir / "status_output_missing_signal.json"

    make_base_status(status_path)
    report = run_ingest_report(tmp_dir / "valid_intake_report.json")
    del report["pulse_signals"]["slsa_vsa_present"]
    write_json(intake_path, report)

    result = run_fold(status_path, intake_path, output_path)
    assert_failure(result, "pulse_signal_missing: slsa_vsa_present")
    assert not output_path.exists()


def check_non_boolean_signal_fails(tmp_dir: Path) -> None:
    status_path = tmp_dir / "status_input.json"
    intake_path = tmp_dir / "intake_report_non_boolean_signal.json"
    output_path = tmp_dir / "status_output_non_boolean_signal.json"

    make_base_status(status_path)
    report = run_ingest_report(tmp_dir / "valid_intake_report.json")
    report["pulse_signals"]["slsa_vsa_present"] = "true"
    write_json(intake_path, report)

    result = run_fold(status_path, intake_path, output_path)
    assert_failure(result, "pulse_signal_not_boolean: slsa_vsa_present")
    assert not output_path.exists()


def check_false_signal_fails(tmp_dir: Path) -> None:
    status_path = tmp_dir / "status_input.json"
    intake_path = tmp_dir / "intake_report_false_signal.json"
    output_path = tmp_dir / "status_output_false_signal.json"

    make_base_status(status_path)
    report = run_ingest_report(tmp_dir / "valid_intake_report.json")
    report["pulse_signals"]["slsa_vsa_present"] = False
    write_json(intake_path, report)

    result = run_fold(status_path, intake_path, output_path)
    assert_failure(result, "pulse_signal_not_true: slsa_vsa_present")
    assert not output_path.exists()


def check_false_check_fails(tmp_dir: Path) -> None:
    status_path = tmp_dir / "status_input.json"
    intake_path = tmp_dir / "intake_report_false_check.json"
    output_path = tmp_dir / "status_output_false_check.json"

    make_base_status(status_path)
    report = run_ingest_report(tmp_dir / "valid_intake_report.json")
    report["checks"]["verified_level_ok"] = False
    write_json(intake_path, report)

    result = run_fold(status_path, intake_path, output_path)
    assert_failure(result, "intake_check_not_true: verified_level_ok")
    assert not output_path.exists()


def check_existing_gate_conflict_fails(tmp_dir: Path) -> None:
    status_path = tmp_dir / "status_input_conflict.json"
    intake_path = tmp_dir / "intake_report_conflict.json"
    output_path = tmp_dir / "status_output_conflict.json"

    write_json(
        status_path,
        {
            "schema_version": "test_status_v0",
            "run_id": "fold-slsa-vsa-intake-test",
            "gates": {
                "slsa_vsa_present": False
            },
        },
    )

    run_ingest_report(intake_path)

    result = run_fold(status_path, intake_path, output_path)
    assert_failure(result, "existing_gate_conflict: slsa_vsa_present")
    assert not output_path.exists()


def check_base_status_shape_failures(tmp_dir: Path) -> None:
    intake_path = tmp_dir / "valid_intake_report.json"
    run_ingest_report(intake_path)

    not_object_status = tmp_dir / "status_not_object.json"
    not_object_output = tmp_dir / "status_not_object_output.json"
    not_object_status.write_text('"not-object"\n', encoding="utf-8")

    result = run_fold(not_object_status, intake_path, not_object_output)
    assert_failure(result, "status_not_object")
    assert not not_object_output.exists()

    bad_gates_status = tmp_dir / "status_bad_gates.json"
    bad_gates_output = tmp_dir / "status_bad_gates_output.json"
    write_json(
        bad_gates_status,
        {
            "schema_version": "test_status_v0",
            "gates": "not-object",
        },
    )

    result = run_fold(bad_gates_status, intake_path, bad_gates_output)
    assert_failure(result, "status_gates_not_object")
    assert not bad_gates_output.exists()


def check_in_place_output_refused(tmp_dir: Path) -> None:
    status_path = tmp_dir / "status_input.json"
    intake_path = tmp_dir / "intake_report.json"

    make_base_status(status_path)
    base_hash_before = sha256_file(status_path)

    run_ingest_report(intake_path)

    result = run_fold(status_path, intake_path, status_path)
    assert_failure(result, "refusing_in_place_status_write")

    base_hash_after = sha256_file(status_path)
    assert base_hash_before == base_hash_after


def check_tool_does_not_call_gate_checker() -> None:
    source = FOLD_TOOL.read_text(encoding="utf-8")
    forbidden = "check_" + "gates"
    assert forbidden not in source


def check_fold_slsa_vsa_intake_into_status_v0() -> None:
    assert INGEST_TOOL.exists()
    assert FOLD_TOOL.exists()
    assert SCHEMA.exists()
    assert EXAMPLE.exists()

    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp_dir = Path(raw_tmp)

        check_valid_fold_in(tmp_dir)
        check_report_not_ok_fails(tmp_dir)
        check_missing_signal_fails(tmp_dir)
        check_non_boolean_signal_fails(tmp_dir)
        check_false_signal_fails(tmp_dir)
        check_false_check_fails(tmp_dir)
        check_existing_gate_conflict_fails(tmp_dir)
        check_base_status_shape_failures(tmp_dir)
        check_in_place_output_refused(tmp_dir)
        check_tool_does_not_call_gate_checker()


def test_fold_slsa_vsa_intake_into_status_v0() -> None:
    check_fold_slsa_vsa_intake_into_status_v0()


if __name__ == "__main__":
    check_fold_slsa_vsa_intake_into_status_v0()
    print("OK: fold_slsa_vsa_intake_into_status_v0 smoke passed")

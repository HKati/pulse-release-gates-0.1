import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ingest_slsa_vsa_evidence_v0.py"
SCHEMA = ROOT / "schemas" / "slsa_vsa_evidence_v0.schema.json"
EXAMPLE = ROOT / "examples" / "slsa" / "slsa_vsa_evidence_example_v0.json"

EXPECTED_ARGS = {
    "--expect-subject-name": "git+https://github.com/HKati/pulse-release-gates-0.1@refs/tags/v0.1.0",
    "--expect-subject-sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "--expect-resource-uri": "git+https://github.com/HKati/pulse-release-gates-0.1@refs/tags/v0.1.0",
    "--expect-verifier-id": "https://example.invalid/verifiers/pulsemech-vsa-verifier-v0",
    "--expect-policy-sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "--expect-verified-level": "SLSA_BUILD_LEVEL_3",
}


def load_example() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None

    return hashlib.sha256(path.read_bytes()).hexdigest()


def tracked_status_hashes() -> dict[str, str | None]:
    candidates = [
        ROOT / "status.json",
        ROOT / "PULSE_safe_pack_v0" / "artifacts" / "status.json",
    ]
    return {str(path.relative_to(ROOT)): sha256_file(path) for path in candidates}


def build_args(
    evidence: Path = EXAMPLE,
    overrides: dict[str, str | None] | None = None,
) -> list[str]:
    values = dict(EXPECTED_ARGS)
    if overrides:
        values.update(overrides)

    args = [
        sys.executable,
        str(TOOL),
        "--schema",
        str(SCHEMA),
        "--evidence",
        str(evidence),
    ]

    for key in sorted(values):
        value = values[key]
        if value is not None:
            args.extend([key, value])

    return args


def run_tool(
    evidence: Path = EXAMPLE,
    overrides: dict[str, str | None] | None = None,
    extra: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    args = build_args(evidence=evidence, overrides=overrides)
    if extra:
        args.extend(extra)

    return subprocess.run(
        args,
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
    assert result.returncode == 1, result.stdout + result.stderr
    assert "Traceback" not in result.stderr

    report = parse_report(result)
    assert report["ok"] is False
    assert any(expected_fragment in error for error in report["errors"]), report["errors"]
    return report


def check_valid_example_passes() -> None:
    before = tracked_status_hashes()
    result = run_tool()
    after = tracked_status_hashes()

    assert result.returncode == 0, result.stdout + result.stderr
    assert before == after

    report = parse_report(result)
    assert report["tool"] == "ingest_slsa_vsa_evidence_v0"
    assert report["ok"] is True
    assert report["schema_version"] == "slsa_vsa_evidence_v0"
    assert report["evidence_type"] == "slsa_vsa"
    assert report["signature_verification_mode"] == "recorded_signal_only"
    assert report["errors"] == []
    assert all(report["checks"].values())

    signals = report["pulse_signals"]
    assert signals["slsa_vsa_signature_ok"] is True
    assert signals["slsa_vsa_result_passed"] is True


def check_output_report_matches_stdout(tmp_dir: Path) -> None:
    output = tmp_dir / "intake_report.json"
    result = run_tool(extra=["--output", str(output)])

    assert result.returncode == 0, result.stdout + result.stderr
    assert output.exists()
    assert json.loads(output.read_text(encoding="utf-8")) == parse_report(result)


def check_wrong_expectations_fail() -> None:
    assert_failure(
        run_tool(overrides={"--expect-verifier-id": "https://example.invalid/verifiers/wrong"}),
        "verifier_trusted",
    )
    assert_failure(
        run_tool(
            overrides={
                "--expect-subject-sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
            }
        ),
        "subject_matches_artifact",
    )
    assert_failure(
        run_tool(overrides={"--expect-resource-uri": "git+https://example.invalid/wrong@refs/tags/v0"}),
        "resource_uri_matches",
    )
    assert_failure(
        run_tool(
            overrides={
                "--expect-policy-sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
            }
        ),
        "policy_digest_matches",
    )
    assert_failure(
        run_tool(overrides={"--expect-verified-level": "SLSA_BUILD_LEVEL_4"}),
        "verified_level_ok",
    )


def check_missing_expectations_fail() -> None:
    cases = [
        (
            {"--expect-subject-name": None},
            "expectation_missing: --expect-subject-name",
        ),
        (
            {"--expect-subject-sha256": None},
            "expectation_missing: --expect-subject-sha256",
        ),
        (
            {"--expect-verifier-id": None},
            "expectation_missing: --expect-verifier-id",
        ),
        (
            {"--expect-resource-uri": None},
            "expectation_missing: --expect-resource-uri",
        ),
        (
            {"--expect-policy-sha256": None},
            "expectation_missing: --expect-policy-sha256",
        ),
        (
            {"--expect-verified-level": None},
            "expectation_missing: --expect-verified-level",
        ),
    ]

    for overrides, expected_fragment in cases:
        assert_failure(run_tool(overrides=overrides), expected_fragment)


def check_malformed_vsa_reports_json(tmp_dir: Path) -> None:
    malformed = load_example()
    malformed["vsa"] = "not-object"

    malformed_path = tmp_dir / "malformed_vsa.json"
    write_json(malformed_path, malformed)

    result = run_tool(evidence=malformed_path)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Traceback" not in result.stderr

    report = parse_report(result)
    assert report["ok"] is False
    assert any("vsa_not_object" in error for error in report["errors"])


def check_malformed_nested_objects_report_json(tmp_dir: Path) -> None:
    cases = [
        ("predicate_not_object", ("vsa", "predicate"), "not-object"),
        ("verifier_not_object", ("vsa", "predicate", "verifier"), "not-object"),
        ("policy_not_object", ("vsa", "predicate", "policy"), "not-object"),
    ]

    for expected_fragment, path_parts, value in cases:
        malformed = load_example()
        cursor = malformed

        for part in path_parts[:-1]:
            cursor = cursor[part]

        cursor[path_parts[-1]] = value

        malformed_path = tmp_dir / f"{expected_fragment}.json"
        write_json(malformed_path, malformed)

        result = run_tool(evidence=malformed_path)

        assert result.returncode == 1, result.stdout + result.stderr
        assert "Traceback" not in result.stderr

        report = parse_report(result)
        assert report["ok"] is False
        assert any(expected_fragment in error for error in report["errors"]), report["errors"]


def check_mutated_evidence_fails(tmp_dir: Path) -> None:
    failed_result = load_example()
    failed_result["vsa"]["predicate"]["verificationResult"] = "FAILED"
    failed_path = tmp_dir / "failed_result.json"
    write_json(failed_path, failed_result)
    assert_failure(run_tool(evidence=failed_path), "verification_result_passed")

    non_boolean_signal = load_example()
    non_boolean_signal["pulse_signals"]["slsa_vsa_present"] = "true"
    non_boolean_path = tmp_dir / "non_boolean_signal.json"
    write_json(non_boolean_path, non_boolean_signal)
    assert_failure(run_tool(evidence=non_boolean_path), "pulse_signals_literal_booleans")


def check_status_output_is_refused(tmp_dir: Path) -> None:
    status_path = tmp_dir / "status.json"
    result = run_tool(extra=["--output", str(status_path)])

    assert result.returncode == 2, result.stdout + result.stderr
    assert not status_path.exists()

    report = parse_report(result)
    assert report["ok"] is False
    assert "refusing_to_write_status_json" in report["errors"]


def check_tool_does_not_call_gate_checker() -> None:
    source = TOOL.read_text(encoding="utf-8")
    forbidden = "check_" + "gates"
    assert forbidden not in source


def check_ingest_slsa_vsa_evidence_v0() -> None:
    assert TOOL.exists()
    assert SCHEMA.exists()
    assert EXAMPLE.exists()

    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp_dir = Path(raw_tmp)

        check_valid_example_passes()
        check_output_report_matches_stdout(tmp_dir)
        check_wrong_expectations_fail()
        check_missing_expectations_fail()
        check_malformed_vsa_reports_json(tmp_dir)
        check_malformed_nested_objects_report_json(tmp_dir)
        check_mutated_evidence_fails(tmp_dir)
        check_status_output_is_refused(tmp_dir)
        check_tool_does_not_call_gate_checker()


def test_ingest_slsa_vsa_evidence_v0() -> None:
    check_ingest_slsa_vsa_evidence_v0()


if __name__ == "__main__":
    check_ingest_slsa_vsa_evidence_v0()
    print("OK: ingest_slsa_vsa_evidence_v0 smoke passed")

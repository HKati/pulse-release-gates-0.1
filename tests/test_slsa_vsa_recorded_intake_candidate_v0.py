import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / "pulse_gate_policy_v0.yml"
TOOLS_TESTS_LIST = ROOT / "ci" / "tools-tests.list"
POLICY_TO_REQUIRE_ARGS = ROOT / "tools" / "policy_to_require_args.py"
CHECK_GATES = ROOT / "PULSE_safe_pack_v0" / "tools" / "check_gates.py"

INGEST_TOOL = ROOT / "tools" / "ingest_slsa_vsa_evidence_v0.py"
FOLD_TOOL = ROOT / "tools" / "fold_slsa_vsa_intake_into_status_v0.py"

SCHEMA = ROOT / "schemas" / "slsa_vsa_evidence_v0.schema.json"
EXAMPLE = ROOT / "examples" / "slsa" / "slsa_vsa_evidence_example_v0.json"

CANDIDATE_SET = "slsa_vsa_recorded_intake_candidate"
STALE_CANDIDATE_SET = "slsa_vsa_release_required_candidate"

CURRENT_TEST_PATH = "tests/test_slsa_vsa_recorded_intake_candidate_v0.py"
STALE_TEST_PATH = "tests/test_slsa_vsa_release_required_candidate_v0.py"

SLSA_VSA_GATES = [
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

ACTIVE_REQUIRED_SETS = [
    "required",
    "core_required",
    "release_required",
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
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_policy_to_require_args(gate_set: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(POLICY_TO_REQUIRE_ARGS),
            "--policy",
            str(POLICY),
            "--set",
            gate_set,
            "--format",
            "newline",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def materialize_gate_set(gate_set: str) -> list[str]:
    result = run_policy_to_require_args(gate_set)

    assert result.returncode == 0, result.stdout + result.stderr

    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def make_base_status(path: Path) -> None:
    write_json(
        path,
        {
            "schema_version": "test_status_v0",
            "run_id": "slsa-vsa-recorded-intake-candidate-test",
            "gates": {
                "existing_gate": True
            },
        },
    )


def run_ingest_report(output: Path) -> dict:
    result = subprocess.run(
        [
            sys.executable,
            str(INGEST_TOOL),
            "--schema",
            str(SCHEMA),
            "--evidence",
            str(EXAMPLE),
            *EXPECTED_INGEST_ARGS,
            "--output",
            str(output),
        ],
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


def run_fold(status: Path, intake_report: Path, output: Path) -> dict:
    result = subprocess.run(
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

    assert result.returncode == 0, result.stdout + result.stderr

    report = json.loads(result.stdout)

    assert report["ok"] is True
    assert output.exists()

    return report


def run_check_gates(status: Path, required_gates: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CHECK_GATES),
            "--status",
            str(status),
            "--require",
            *required_gates,
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def check_recorded_intake_naming_is_consistent() -> None:
    policy_text = POLICY.read_text(encoding="utf-8")
    tools_tests_text = TOOLS_TESTS_LIST.read_text(encoding="utf-8")

    assert CANDIDATE_SET in policy_text
    assert STALE_CANDIDATE_SET not in policy_text

    assert CURRENT_TEST_PATH in tools_tests_text
    assert STALE_TEST_PATH not in tools_tests_text

    stale_result = run_policy_to_require_args(STALE_CANDIDATE_SET)
    assert stale_result.returncode != 0, (
        "stale release-required candidate set must not remain materializable"
    )


def check_candidate_gate_set_materializes_exactly() -> None:
    materialized = materialize_gate_set(CANDIDATE_SET)

    assert materialized == SLSA_VSA_GATES, (
        "recorded-intake candidate gate set must materialize exactly the nine "
        f"SLSA VSA gates in stable order; got {materialized}"
    )


def check_candidate_gates_not_in_active_required_sets() -> None:
    for gate_set in ACTIVE_REQUIRED_SETS:
        materialized = materialize_gate_set(gate_set)
        leaked = [gate for gate in SLSA_VSA_GATES if gate in materialized]

        assert not leaked, (
            f"SLSA VSA candidate gates must not appear in active {gate_set}: {leaked}"
        )


def check_candidate_passes_after_intake_and_fold(tmp_dir: Path) -> Path:
    status_path = tmp_dir / "status_input.json"
    intake_report_path = tmp_dir / "intake_report.json"
    folded_status_path = tmp_dir / "status_folded.json"

    make_base_status(status_path)
    run_ingest_report(intake_report_path)
    run_fold(status_path, intake_report_path, folded_status_path)

    required_gates = materialize_gate_set(CANDIDATE_SET)

    result = run_check_gates(folded_status_path, required_gates)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[OK] All required gates PASS" in result.stdout

    folded = read_json(folded_status_path)
    gates = folded["gates"]

    for gate in SLSA_VSA_GATES:
        assert gates[gate] is True, f"{gate} must be true in folded status"

    return folded_status_path


def check_candidate_fails_when_one_gate_is_false(
    tmp_dir: Path,
    folded_status_path: Path,
) -> None:
    mutated_status_path = tmp_dir / "status_folded_mutated_false.json"

    mutated = read_json(folded_status_path)
    mutated["gates"]["slsa_vsa_verifier_trusted"] = False
    write_json(mutated_status_path, mutated)

    required_gates = materialize_gate_set(CANDIDATE_SET)

    result = run_check_gates(mutated_status_path, required_gates)

    assert result.returncode != 0, result.stdout + result.stderr
    assert (
        "slsa_vsa_verifier_trusted" in result.stdout
        or "slsa_vsa_verifier_trusted" in result.stderr
    )


def check_candidate_fails_when_one_gate_is_missing(
    tmp_dir: Path,
    folded_status_path: Path,
) -> None:
    mutated_status_path = tmp_dir / "status_folded_mutated_missing.json"

    mutated = read_json(folded_status_path)
    del mutated["gates"]["slsa_vsa_policy_digest_matches"]
    write_json(mutated_status_path, mutated)

    required_gates = materialize_gate_set(CANDIDATE_SET)

    result = run_check_gates(mutated_status_path, required_gates)

    assert result.returncode != 0, result.stdout + result.stderr
    assert (
        "slsa_vsa_policy_digest_matches" in result.stdout
        or "slsa_vsa_policy_digest_matches" in result.stderr
    )


def check_no_release_authority_tool_mutation() -> None:
    assert CHECK_GATES.exists()

    source = CHECK_GATES.read_text(encoding="utf-8")

    assert CANDIDATE_SET not in source
    assert STALE_CANDIDATE_SET not in source
    assert "slsa_vsa_present" not in source


def check_slsa_vsa_recorded_intake_candidate_v0() -> None:
    assert POLICY.exists()
    assert TOOLS_TESTS_LIST.exists()
    assert POLICY_TO_REQUIRE_ARGS.exists()
    assert CHECK_GATES.exists()
    assert INGEST_TOOL.exists()
    assert FOLD_TOOL.exists()
    assert SCHEMA.exists()
    assert EXAMPLE.exists()

    check_recorded_intake_naming_is_consistent()
    check_candidate_gate_set_materializes_exactly()
    check_candidate_gates_not_in_active_required_sets()
    check_no_release_authority_tool_mutation()

    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp_dir = Path(raw_tmp)

        folded_status_path = check_candidate_passes_after_intake_and_fold(tmp_dir)
        check_candidate_fails_when_one_gate_is_false(tmp_dir, folded_status_path)
        check_candidate_fails_when_one_gate_is_missing(tmp_dir, folded_status_path)


def test_slsa_vsa_recorded_intake_candidate_v0() -> None:
    check_slsa_vsa_recorded_intake_candidate_v0()


if __name__ == "__main__":
    check_slsa_vsa_recorded_intake_candidate_v0()
    print("OK: SLSA VSA recorded-intake candidate proof passed")

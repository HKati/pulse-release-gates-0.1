import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / "pulse_gate_policy_v0.yml"
POLICY_TO_REQUIRE_ARGS = ROOT / "tools" / "policy_to_require_args.py"

INGEST_TOOL = ROOT / "tools" / "ingest_slsa_vsa_evidence_v0.py"
FOLD_TOOL = ROOT / "tools" / "fold_slsa_vsa_intake_into_status_v0.py"
CHECK_GATES = ROOT / "PULSE_safe_pack_v0" / "tools" / "check_gates.py"

SCHEMA = ROOT / "schemas" / "slsa_vsa_evidence_v0.schema.json"
EXAMPLE = ROOT / "examples" / "slsa" / "slsa_vsa_evidence_example_v0.json"

CANDIDATE_SET = "slsa_vsa_recorded_intake_candidate"
STALE_CANDIDATE_SET = "slsa_vsa_release_required_candidate"

EXPECTED_SLSA_VSA_GATES = [
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

ACTIVE_OR_BLOCKING_SETS = [
    "required",
    "core_required",
    "release_required",
    "prod_required",
    "stage_required",
    "blocking",
    "release_blocking",
]


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _strip_inline_comment(text: str) -> str:
    return text.split("#", 1)[0].strip()


def _parse_inline_list(value: str) -> list[str]:
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        return []

    inner = value[1:-1].strip()
    if not inner:
        return []

    return [part.strip() for part in inner.split(",") if part.strip()]


def _extract_gate_set(text: str, gate_set: str) -> tuple[bool, list[str]]:
    lines = text.splitlines()

    in_gates = False
    in_set = False
    gates_indent = None
    set_indent = None
    found_set = False
    out: list[str] = []

    for raw in lines:
        line = raw.rstrip("\n")
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        clean = _strip_inline_comment(stripped)
        if not clean:
            continue

        indent = len(line) - len(line.lstrip(" "))

        if clean == "gates:":
            in_gates = True
            in_set = False
            gates_indent = indent
            set_indent = None
            continue

        if in_gates and gates_indent is not None and indent <= gates_indent and ":" in clean and clean != "gates:":
            in_gates = False
            in_set = False
            gates_indent = None
            set_indent = None

        if not in_gates:
            continue

        if in_set and set_indent is not None and indent == set_indent and ":" in clean and not clean.startswith("-"):
            key = clean.split(":", 1)[0].strip()
            if key and key != gate_set:
                in_set = False
                set_indent = None

        if ":" in clean and not clean.startswith("-"):
            key, rest = clean.split(":", 1)
            key = key.strip()
            rest = rest.strip()

            if key == gate_set:
                found_set = True
                set_indent = indent

                if rest.startswith("[") and rest.endswith("]"):
                    out.extend(_parse_inline_list(rest))
                    in_set = False
                    continue

                in_set = True
                continue

        if not in_set:
            continue

        if clean.startswith("- "):
            gate_id = _strip_inline_comment(clean[2:])
            if gate_id:
                out.append(gate_id)

    return found_set, out


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

    assert report["tool"] == "ingest_slsa_vsa_evidence_v0"
    assert report["ok"] is True
    assert report["errors"] == []
    assert output.exists()
    assert read_json(output) == report

    return report


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


def build_folded_candidate_status(tmp_dir: Path) -> tuple[Path, list[str]]:
    candidate_gates = materialize_gate_set(CANDIDATE_SET)

    status_path = tmp_dir / "status_input.json"
    intake_path = tmp_dir / "slsa_vsa_intake_report.json"
    folded_status_path = tmp_dir / "status_folded.json"

    make_base_status(status_path)
    run_ingest_report(intake_path)

    fold_result = run_fold(status_path, intake_path, folded_status_path)
    assert fold_result.returncode == 0, fold_result.stdout + fold_result.stderr
    assert folded_status_path.exists()

    fold_report = json.loads(fold_result.stdout)
    assert fold_report["tool"] == "fold_slsa_vsa_intake_into_status_v0"
    assert fold_report["ok"] is True
    assert fold_report["output_status_written"] is True
    assert fold_report["errors"] == []
    assert fold_report["folded_gates"] == EXPECTED_SLSA_VSA_GATES

    folded_status = read_json(folded_status_path)
    assert folded_status["gates"]["existing_gate"] is True

    for gate in EXPECTED_SLSA_VSA_GATES:
        assert folded_status["gates"][gate] is True

    return folded_status_path, candidate_gates


def check_candidate_set_identity_and_materialization() -> None:
    assert CANDIDATE_SET == "slsa_vsa_recorded_intake_candidate"

    materialized = materialize_gate_set(CANDIDATE_SET)
    assert materialized == EXPECTED_SLSA_VSA_GATES

    stale = run_policy_to_require_args(STALE_CANDIDATE_SET)
    assert stale.returncode != 0
    assert "Gate set not found" in stale.stderr
    assert STALE_CANDIDATE_SET in stale.stderr


def check_candidate_gates_not_active_or_blocking() -> None:
    policy_text = POLICY.read_text(encoding="utf-8")

    for gate_set in ACTIVE_OR_BLOCKING_SETS:
        found_set, gates = _extract_gate_set(policy_text, gate_set)
        if not found_set:
            continue

        leaked = [gate for gate in EXPECTED_SLSA_VSA_GATES if gate in gates]
        assert not leaked, f"SLSA VSA candidate gates must not appear in {gate_set}: {leaked}"

    for gate_set in ["required", "core_required", "release_required"]:
        materialized = materialize_gate_set(gate_set)
        leaked = [gate for gate in EXPECTED_SLSA_VSA_GATES if gate in materialized]
        assert not leaked, f"SLSA VSA candidate gates materialized through active set {gate_set}: {leaked}"


def check_recorded_intake_candidate_passes_check_gates(tmp_dir: Path) -> None:
    folded_status_path, candidate_gates = build_folded_candidate_status(tmp_dir)

    result = run_check_gates(folded_status_path, candidate_gates)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "[OK] All required gates PASS" in result.stdout


def check_false_candidate_gate_fails_check_gates(tmp_dir: Path) -> None:
    folded_status_path, candidate_gates = build_folded_candidate_status(tmp_dir)

    mutated = read_json(folded_status_path)
    failing_gate = candidate_gates[0]
    mutated["gates"][failing_gate] = False

    failed_status = tmp_dir / "status_folded_false_gate.json"
    write_json(failed_status, mutated)

    result = run_check_gates(failed_status, candidate_gates)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "[X] FAIL gates:" in result.stdout
    assert failing_gate in result.stdout


def check_missing_candidate_gate_fails_check_gates(tmp_dir: Path) -> None:
    folded_status_path, candidate_gates = build_folded_candidate_status(tmp_dir)

    mutated = read_json(folded_status_path)
    missing_gate = candidate_gates[0]
    del mutated["gates"][missing_gate]

    missing_status = tmp_dir / "status_folded_missing_gate.json"
    write_json(missing_status, mutated)

    result = run_check_gates(missing_status, candidate_gates)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "[X] Missing required gates:" in result.stdout
    assert missing_gate in result.stdout


def check_check_gates_remains_generic() -> None:
    source = CHECK_GATES.read_text(encoding="utf-8")

    assert CANDIDATE_SET not in source
    assert STALE_CANDIDATE_SET not in source

    for gate in EXPECTED_SLSA_VSA_GATES:
        assert gate not in source


def check_slsa_vsa_recorded_intake_candidate_v0() -> None:
    assert POLICY.exists()
    assert POLICY_TO_REQUIRE_ARGS.exists()
    assert INGEST_TOOL.exists()
    assert FOLD_TOOL.exists()
    assert CHECK_GATES.exists()
    assert SCHEMA.exists()
    assert EXAMPLE.exists()

    check_candidate_set_identity_and_materialization()
    check_candidate_gates_not_active_or_blocking()
    check_check_gates_remains_generic()

    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp_dir = Path(raw_tmp)

        check_recorded_intake_candidate_passes_check_gates(tmp_dir)
        check_false_candidate_gate_fails_check_gates(tmp_dir)
        check_missing_candidate_gate_fails_check_gates(tmp_dir)


def test_slsa_vsa_recorded_intake_candidate_v0() -> None:
    check_slsa_vsa_recorded_intake_candidate_v0()


if __name__ == "__main__":
    check_slsa_vsa_recorded_intake_candidate_v0()
    print("OK: SLSA VSA recorded-intake candidate path proof passed")

import hashlib
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "build_external_verification_packet_v0.py"


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def git_commit_all(repo: Path, message: str) -> None:
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def make_minimal_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"

    write(
        repo / "PULSE_safe_pack_v0" / "artifacts" / "status.json",
        json.dumps(
            {
                "version": "1.0.0-core",
                "created_utc": "2026-06-03T00:00:00Z",
                "metrics": {
                    "run_mode": "core",
                    "git_sha": "0" * 40,
                    "run_key": (
                        "GITHUB_RUN_ID=1|GITHUB_RUN_NUMBER=1|"
                        "GITHUB_WORKFLOW=PULSE CI"
                    ),
                },
                "gates": {"core_gate": True},
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )

    write(
        repo / "pulse_gate_policy_v0.yml",
        "gates:\n  core_required:\n    - core_gate\n",
    )
    write(
        repo / "pulse_gate_registry_v0.yml",
        "gates:\n  core_gate:\n    intent: test\n",
    )

    subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.PIPE)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo,
        check=True,
    )
    git_commit_all(repo, "fixture")

    return repo


def run_builder(repo: Path, tmp_path: Path) -> tuple[dict, str]:
    out_json = tmp_path / "external_verification_packet_v0.json"
    out_md = tmp_path / "external_verification_packet_v0.md"

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo-root",
            str(repo),
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
            "--repository-name",
            "HKati/pulse-release-gates-0.1",
        ],
        check=True,
    )

    return json.loads(out_json.read_text(encoding="utf-8")), out_md.read_text(
        encoding="utf-8"
    )


def record_by_role(packet: dict, role: str) -> dict:
    for item in packet["artifact_records"]:
        if item["role"] == role:
            return item
    raise AssertionError(f"missing artifact record for role: {role}")


def command_names(packet: dict) -> set[str]:
    return {item["name"] for item in packet["verification_commands"]}


def test_external_verification_packet_builder_outputs_json_and_markdown(
    tmp_path: Path,
) -> None:
    repo = make_minimal_repo(tmp_path)
    packet, markdown = run_builder(repo, tmp_path)

    assert packet["schema_id"] == "pulse.external_verification_packet.v0"
    assert packet["schema_version"] == "0.1.0"
    assert packet["packet_boundary"] == (
        "external verification carrier; not release authority"
    )
    assert packet["authority_carrier"].startswith("status.json -> declared gate policy")
    assert packet["verification_profile"] == "authority-path"
    assert "External Verification Packet v0" in markdown
    assert "status.json -> declared gate policy" in markdown


def test_external_verification_packet_records_required_artifacts(
    tmp_path: Path,
) -> None:
    repo = make_minimal_repo(tmp_path)
    packet, _markdown = run_builder(repo, tmp_path)

    status_record = record_by_role(packet, "status")
    policy_record = record_by_role(packet, "gate policy")
    registry_record = record_by_role(packet, "gate registry")

    assert status_record["required"] is True
    assert status_record["exists"] is True
    assert status_record["carrier_class"] == "authority"
    assert status_record["json_object_required"] is True
    assert status_record["parseable_json"] is True
    assert status_record["parse_error"] is None
    assert status_record["sha256"] == sha256_path(
        repo / "PULSE_safe_pack_v0" / "artifacts" / "status.json"
    )

    assert policy_record["required"] is True
    assert policy_record["exists"] is True
    assert policy_record["carrier_class"] == "policy"

    assert registry_record["required"] is True
    assert registry_record["exists"] is True
    assert registry_record["carrier_class"] == "registry"


def test_external_verification_packet_records_missing_optional_artifacts(
    tmp_path: Path,
) -> None:
    repo = make_minimal_repo(tmp_path)
    packet, _markdown = run_builder(repo, tmp_path)

    binding = record_by_role(packet, "artifact provenance binding")

    assert binding["required"] is False
    assert binding["exists"] is False
    assert binding["sha256"] is None
    assert binding["carrier_class"] == "binding"

    missing_roles = {record["role"] for record in packet["known_missing_artifacts"]}
    assert "artifact provenance binding" in missing_roles
    assert packet["packet_status"] == "partially_verified"


def test_external_verification_packet_reports_missing_required_artifacts(
    tmp_path: Path,
) -> None:
    repo = make_minimal_repo(tmp_path)
    (repo / "PULSE_safe_pack_v0" / "artifacts" / "status.json").unlink()

    packet, _markdown = run_builder(repo, tmp_path)

    status_record = record_by_role(packet, "status")

    assert status_record["required"] is True
    assert status_record["exists"] is False
    assert status_record["sha256"] is None
    assert status_record["json_object_required"] is True
    assert status_record["parseable_json"] is False
    assert status_record["parse_error"] == "missing"
    assert packet["run_identity"]["status_parse_ok"] is False
    assert packet["packet_status"] == "authority_artifact_missing"


def test_external_verification_packet_rejects_malformed_status_json(
    tmp_path: Path,
) -> None:
    repo = make_minimal_repo(tmp_path)
    write(repo / "PULSE_safe_pack_v0" / "artifacts" / "status.json", "{not json\n")

    packet, _markdown = run_builder(repo, tmp_path)

    status_record = record_by_role(packet, "status")

    assert status_record["exists"] is True
    assert status_record["json_object_required"] is True
    assert status_record["parseable_json"] is False
    assert status_record["parse_error"]
    assert packet["run_identity"]["status_parse_ok"] is False
    assert packet["run_identity"]["status_parse_error"]
    assert packet["packet_status"] == "verification_failed"


def test_external_verification_packet_rejects_non_object_status_json(
    tmp_path: Path,
) -> None:
    repo = make_minimal_repo(tmp_path)
    write(repo / "PULSE_safe_pack_v0" / "artifacts" / "status.json", "[]\n")

    packet, _markdown = run_builder(repo, tmp_path)

    status_record = record_by_role(packet, "status")

    assert status_record["exists"] is True
    assert status_record["json_object_required"] is True
    assert status_record["parseable_json"] is False
    assert status_record["parse_error"] == "top-level JSON value is not an object"
    assert packet["run_identity"]["status_parse_ok"] is False
    assert packet["packet_status"] == "verification_failed"


def test_external_verification_packet_extracts_run_id_from_run_key(
    tmp_path: Path,
) -> None:
    repo = make_minimal_repo(tmp_path)

    packet, _markdown = run_builder(repo, tmp_path)

    assert packet["run_identity"]["run_id"] == "1"
    assert packet["run_identity"]["run_key"] == (
        "GITHUB_RUN_ID=1|GITHUB_RUN_NUMBER=1|GITHUB_WORKFLOW=PULSE CI"
    )


def test_external_verification_packet_prefers_explicit_run_id(
    tmp_path: Path,
) -> None:
    repo = make_minimal_repo(tmp_path)
    status_path = repo / "PULSE_safe_pack_v0" / "artifacts" / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["metrics"]["run_id"] = "explicit-run-id"
    write(status_path, json.dumps(status, indent=2, sort_keys=True) + "\n")

    packet, _markdown = run_builder(repo, tmp_path)

    assert packet["run_identity"]["run_id"] == "explicit-run-id"


def test_external_verification_packet_blocks_verified_status_without_commit(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"

    write(
        repo / "PULSE_safe_pack_v0" / "artifacts" / "status.json",
        json.dumps(
            {
                "version": "1.0.0-core",
                "created_utc": "2026-06-03T00:00:00Z",
                "metrics": {
                    "run_mode": "core",
                    "run_key": (
                        "GITHUB_RUN_ID=1|GITHUB_RUN_NUMBER=1|"
                        "GITHUB_WORKFLOW=PULSE CI"
                    ),
                },
                "gates": {"core_gate": True},
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    write(
        repo / "pulse_gate_policy_v0.yml",
        "gates:\n  core_required:\n    - core_gate\n",
    )
    write(
        repo / "pulse_gate_registry_v0.yml",
        "gates:\n  core_gate:\n    intent: test\n",
    )

    packet, _markdown = run_builder(repo, tmp_path)

    assert packet["commit"]["git_sha"] is None
    assert packet["packet_status"] == "inconclusive"


def test_external_verification_packet_fails_when_binding_verifier_fails(
    tmp_path: Path,
) -> None:
    repo = make_minimal_repo(tmp_path)

    write(
        repo / "PULSE_safe_pack_v0" / "artifacts" / "artifact_provenance_binding_v0.json",
        "{}\n",
    )
    write(
        repo
        / "PULSE_safe_pack_v0"
        / "tools"
        / "verify_artifact_provenance_binding_v0.py",
        "import sys\nsys.exit(1)\n",
    )

    git_commit_all(repo, "add failing binding")

    packet, _markdown = run_builder(repo, tmp_path)

    assert packet["binding_verification"]["requested"] is True
    assert packet["binding_verification"]["available"] is True
    assert packet["binding_verification"]["verified"] is False
    assert packet["binding_verification"]["exit_code"] == 1
    assert packet["packet_status"] == "verification_failed"


def test_external_verification_packet_reports_verified_when_binding_verifier_passes(
    tmp_path: Path,
) -> None:
    repo = make_minimal_repo(tmp_path)

    write(
        repo / "PULSE_safe_pack_v0" / "artifacts" / "artifact_provenance_binding_v0.json",
        "{}\n",
    )
    write(
        repo
        / "PULSE_safe_pack_v0"
        / "tools"
        / "verify_artifact_provenance_binding_v0.py",
        "import sys\nsys.exit(0)\n",
    )

    git_commit_all(repo, "add passing binding")

    packet, _markdown = run_builder(repo, tmp_path)

    assert packet["binding_verification"]["requested"] is True
    assert packet["binding_verification"]["available"] is True
    assert packet["binding_verification"]["verified"] is True
    assert packet["binding_verification"]["exit_code"] == 0
    assert packet["packet_status"] == "verified"


def test_external_verification_packet_is_inconclusive_when_binding_verifier_missing(
    tmp_path: Path,
) -> None:
    repo = make_minimal_repo(tmp_path)

    write(
        repo / "PULSE_safe_pack_v0" / "artifacts" / "artifact_provenance_binding_v0.json",
        "{}\n",
    )

    git_commit_all(repo, "add binding without verifier")

    packet, _markdown = run_builder(repo, tmp_path)

    assert packet["binding_verification"]["requested"] is True
    assert packet["binding_verification"]["available"] is True
    assert packet["binding_verification"]["verified"] is None
    assert packet["binding_verification"]["reason"] == "binding verifier missing"
    assert packet["packet_status"] == "inconclusive"


def test_external_verification_packet_includes_review_commands_and_boundaries(
    tmp_path: Path,
) -> None:
    repo = make_minimal_repo(tmp_path)
    packet, _markdown = run_builder(repo, tmp_path)

    commands = {item["name"]: item for item in packet["verification_commands"]}
    boundaries = {
        item["carrier"]: item["boundary"]
        for item in packet["carrier_boundary_summary"]
    }

    assert "compile release-authority tools" in commands
    assert "artifact provenance binding tests" in commands
    assert "binding CI wiring tests" in commands
    assert "generate normative/shadow inventory report" in commands
    assert "fail-closed gate enforcement tests" in commands
    assert "Quality Ledger reader-surface tests" in commands

    assert "tests/test_check_gates_fail_closed.py" in commands[
        "fail-closed gate enforcement tests"
    ]["command"]
    assert "tests/test_render_quality_ledger.py" in commands[
        "Quality Ledger reader-surface tests"
    ]["command"]
    assert "tests/test_render_quality_ledger_decision_logic.py" in commands[
        "Quality Ledger reader-surface tests"
    ]["command"]
    assert "tests/test_render_quality_ledger_check_gates_parity.py" in commands[
        "Quality Ledger reader-surface tests"
    ]["command"]

    assert boundaries["authority"].startswith("status.json -> declared gate policy")
    assert boundaries["external_verification"] == (
        "Reviews recorded artifact relationship; not release authority."
    )


def test_external_verification_packet_includes_profile_and_semantic_commands(
    tmp_path: Path,
) -> None:
    repo = make_minimal_repo(tmp_path)

    packet, _markdown = run_builder(repo, tmp_path)

    assert packet["verification_profile"] == "authority-path"

    names = command_names(packet)

    assert "fail-closed gate enforcement tests" in names
    assert "Quality Ledger reader-surface tests" in names


def test_external_verification_packet_builder_does_not_write_inside_repo_by_default(
    tmp_path: Path,
) -> None:
    repo = make_minimal_repo(tmp_path)
    run_builder(repo, tmp_path)

    assert not (repo / "external_verification_packet_v0.json").exists()
    assert not (repo / "external_verification_packet_v0.md").exists()
    assert not (repo / "out" / "external_verification_packet_v0.json").exists()
    assert not (repo / "out" / "external_verification_packet_v0.md").exists()

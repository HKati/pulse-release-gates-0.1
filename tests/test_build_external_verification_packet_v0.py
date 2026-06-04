import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "build_external_verification_packet_v0.py"
BINDING_BUILDER = (
    REPO_ROOT
    / "PULSE_safe_pack_v0"
    / "tools"
    / "build_artifact_provenance_binding_v0.py"
)
REPO_ROOT_VERIFIER = (
    "PULSE_safe_pack_v0/tools/verify_artifact_provenance_binding_v0.py"
)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: dict) -> None:
    write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


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


def valid_status() -> dict:
    return {
        "version": "1.0.0-core",
        "created_utc": "2026-06-03T00:00:00Z",
        "metrics": {
            "run_mode": "core",
            "git_sha": "0" * 40,
            "run_key": (
                "GITHUB_RUN_ID=12345|GITHUB_RUN_NUMBER=7|"
                "GITHUB_WORKFLOW=PULSE CI"
            ),
        },
        "gates": {"core_gate": True},
    }


def write_valid_binding_inputs(repo: Path) -> None:
    write(
        repo / "PULSE_safe_pack_v0" / "artifacts" / "report_card.html",
        "PULSE Quality Ledger\n",
    )
    write_json(
        repo / "PULSE_safe_pack_v0" / "artifacts" / "release_decision_v0.json",
        {
            "schema_id": "pulse_release_decision_v0",
            "producer": "materialize_release_decision.py",
            "release_level": "PROD-PASS",
        },
    )
    write_json(
        repo / "PULSE_safe_pack_v0" / "artifacts" / "release_authority_v0.json",
        {"schema_id": "release_authority_v0", "ok": True},
    )


def build_valid_binding(repo: Path) -> None:
    write_valid_binding_inputs(repo)

    subprocess.run(
        [
            sys.executable,
            str(BINDING_BUILDER),
            "--status",
            "PULSE_safe_pack_v0/artifacts/status.json",
            "--policy",
            "pulse_gate_policy_v0.yml",
            "--ledger",
            "PULSE_safe_pack_v0/artifacts/report_card.html",
            "--release-decision",
            "PULSE_safe_pack_v0/artifacts/release_decision_v0.json",
            "--release-authority-manifest",
            "PULSE_safe_pack_v0/artifacts/release_authority_v0.json",
            "--out",
            "PULSE_safe_pack_v0/artifacts/artifact_provenance_binding_v0.json",
            "--created-utc",
            "2026-06-03T00:00:00Z",
        ],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def make_repo(
    base: Path,
    *,
    git: bool = True,
    status_text: str | None = None,
    binding: bool = False,
    valid_binding: bool = False,
    repo_root_verifier_exit: int | None = None,
    repo_root_verifier_text: str | None = None,
) -> Path:
    repo = base / "repo"

    if status_text is None:
        status_text = json.dumps(valid_status(), indent=2, sort_keys=True) + "\n"

    write(repo / "PULSE_safe_pack_v0" / "artifacts" / "status.json", status_text)
    write(
        repo / "pulse_gate_policy_v0.yml",
        "gates:\n  core_required:\n    - core_gate\n",
    )
    write(
        repo / "pulse_gate_registry_v0.yml",
        "gates:\n  core_gate:\n    intent: test\n",
    )

    if valid_binding:
        build_valid_binding(repo)
    elif binding:
        write(
            repo
            / "PULSE_safe_pack_v0"
            / "artifacts"
            / "artifact_provenance_binding_v0.json",
            "{}\n",
        )

    if repo_root_verifier_text is not None:
        write(repo / REPO_ROOT_VERIFIER, repo_root_verifier_text)
    elif repo_root_verifier_exit is not None:
        write(
            repo / REPO_ROOT_VERIFIER,
            f"import sys\nsys.exit({repo_root_verifier_exit})\n",
        )

    if git:
        subprocess.run(
            ["git", "init"],
            cwd=repo,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
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
    for record in packet["artifact_records"]:
        if record["role"] == role:
            return record
    raise AssertionError(f"missing artifact record for role: {role}")


def command_names(packet: dict) -> set[str]:
    return {item["name"] for item in packet["verification_commands"]}


def test_builder_outputs_minimum_packet_fields_and_boundaries(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    packet, markdown = run_builder(repo, tmp_path)

    assert packet["schema_id"] == "pulse.external_verification_packet.v0"
    assert packet["schema_version"] == "0.1.0"
    assert packet["verification_profile"] == "authority-path"
    assert packet["packet_status"] == "partially_verified"
    assert packet["packet_boundary"] == (
        "external verification carrier; not release authority"
    )
    assert packet["authority_carrier"] == (
        "status.json -> declared gate policy -> workflow-effective materialized "
        "required gate set -> strict fail-closed CI enforcement"
    )

    status_record = record_by_role(packet, "status")
    assert status_record["required"] is True
    assert status_record["exists"] is True
    assert status_record["json_object_required"] is True
    assert status_record["parseable_json"] is True
    assert status_record["parse_error"] is None

    assert "External Verification Packet v0" in markdown
    assert "verification_profile" in markdown
    assert "Binding verification" in markdown


def test_malformed_required_status_json_blocks_verified_packet(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, status_text="{not json\n")
    packet, _markdown = run_builder(repo, tmp_path)

    status_record = record_by_role(packet, "status")
    assert status_record["exists"] is True
    assert status_record["json_object_required"] is True
    assert status_record["parseable_json"] is False
    assert status_record["parse_error"]

    assert packet["run_identity"]["status_parse_ok"] is False
    assert packet["run_identity"]["status_parse_error"]
    assert packet["packet_status"] == "verification_failed"


def test_non_object_status_json_blocks_verified_packet(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, status_text="[]\n")
    packet, _markdown = run_builder(repo, tmp_path)

    status_record = record_by_role(packet, "status")
    assert status_record["parseable_json"] is False
    assert status_record["parse_error"] == "top-level JSON value is not an object"
    assert packet["packet_status"] == "verification_failed"


def test_run_id_is_extracted_from_github_run_id_inside_run_key(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    packet, _markdown = run_builder(repo, tmp_path)

    assert packet["run_identity"]["run_id"] == "12345"
    assert packet["run_identity"]["run_key"] == (
        "GITHUB_RUN_ID=12345|GITHUB_RUN_NUMBER=7|GITHUB_WORKFLOW=PULSE CI"
    )


def test_explicit_run_id_is_preferred_over_run_key_value(tmp_path: Path) -> None:
    status = valid_status()
    status["metrics"]["run_id"] = "explicit-run-id"

    repo = make_repo(
        tmp_path,
        status_text=json.dumps(status, indent=2, sort_keys=True) + "\n",
    )
    packet, _markdown = run_builder(repo, tmp_path)

    assert packet["run_identity"]["run_id"] == "explicit-run-id"


def test_missing_git_commit_identity_is_inconclusive(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, git=False)
    packet, _markdown = run_builder(repo, tmp_path)

    assert packet["commit"]["git_sha"] is None
    assert packet["packet_status"] == "inconclusive"


def test_existing_binding_must_pass_trusted_verifier_before_packet_can_be_verified(
    tmp_path: Path,
) -> None:
    fail_repo = make_repo(
        tmp_path / "fail",
        binding=True,
        repo_root_verifier_exit=0,
    )
    fail_packet, _markdown = run_builder(fail_repo, tmp_path / "fail_out")

    assert fail_packet["binding_verification"]["requested"] is True
    assert fail_packet["binding_verification"]["available"] is True
    assert fail_packet["binding_verification"]["verified"] is False
    assert fail_packet["binding_verification"]["exit_code"] != 0
    assert fail_packet["binding_verification"]["reason"] == (
        "trusted binding verifier failed"
    )
    assert fail_packet["binding_verification"]["verifier_source"] == (
        "trusted_builder_checkout"
    )
    assert fail_packet["packet_status"] == "verification_failed"

    pass_repo = make_repo(
        tmp_path / "pass",
        valid_binding=True,
        repo_root_verifier_exit=1,
    )
    pass_packet, _markdown = run_builder(pass_repo, tmp_path / "pass_out")

    assert pass_packet["binding_verification"]["requested"] is True
    assert pass_packet["binding_verification"]["available"] is True
    assert pass_packet["binding_verification"]["verified"] is True
    assert pass_packet["binding_verification"]["exit_code"] == 0
    assert pass_packet["binding_verification"]["reason"] == (
        "trusted binding verifier passed"
    )
    assert pass_packet["binding_verification"]["verifier_source"] == (
        "trusted_builder_checkout"
    )
    assert pass_packet["packet_status"] == "verified"


def test_repo_root_verifier_is_not_executed_for_binding_verification(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "repo_root_verifier_executed.txt"
    repo = make_repo(
        tmp_path,
        binding=True,
        repo_root_verifier_text=(
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('executed', encoding='utf-8')\n"
            "raise SystemExit(0)\n"
        ),
    )

    packet, _markdown = run_builder(repo, tmp_path)

    assert not marker.exists()
    assert packet["binding_verification"]["requested"] is True
    assert packet["binding_verification"]["available"] is True
    assert packet["binding_verification"]["verified"] is False
    assert packet["binding_verification"]["exit_code"] != 0
    assert packet["binding_verification"]["reason"] == "trusted binding verifier failed"
    assert packet["binding_verification"]["verifier_source"] == (
        "trusted_builder_checkout"
    )
    assert packet["packet_status"] == "verification_failed"


def test_existing_malformed_binding_without_repo_verifier_fails_with_trusted_verifier(
    tmp_path: Path,
) -> None:
    repo = make_repo(tmp_path, binding=True, repo_root_verifier_exit=None)
    packet, _markdown = run_builder(repo, tmp_path)

    assert packet["binding_verification"]["requested"] is True
    assert packet["binding_verification"]["available"] is True
    assert packet["binding_verification"]["verified"] is False
    assert packet["binding_verification"]["exit_code"] != 0
    assert packet["binding_verification"]["reason"] == "trusted binding verifier failed"
    assert packet["binding_verification"]["verifier_source"] == (
        "trusted_builder_checkout"
    )
    assert packet["packet_status"] == "verification_failed"


def test_semantic_review_commands_are_present(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    packet, _markdown = run_builder(repo, tmp_path)

    names = command_names(packet)
    assert "fail-closed gate enforcement tests" in names
    assert "Quality Ledger reader-surface tests" in names
    assert "verify artifact provenance binding" in names

    commands = {item["name"]: item["command"] for item in packet["verification_commands"]}

    assert "tests/test_check_gates_fail_closed.py" in commands[
        "fail-closed gate enforcement tests"
    ]
    assert "tests/test_render_quality_ledger.py" in commands[
        "Quality Ledger reader-surface tests"
    ]
    assert "tests/test_render_quality_ledger_decision_logic.py" in commands[
        "Quality Ledger reader-surface tests"
    ]
    assert "tests/test_render_quality_ledger_check_gates_parity.py" in commands[
        "Quality Ledger reader-surface tests"
    ]

    binding_command = commands["verify artifact provenance binding"]
    assert "TRUSTED_PULSE_CHECKOUT" in binding_command
    assert "REVIEWED_REPO_ROOT" in binding_command
    assert "python -I" in binding_command
    assert "cd \"$REVIEWED_REPO_ROOT\"" in binding_command
    assert "pwd -P" in binding_command
    assert (
        "$TRUSTED_PULSE_CHECKOUT/"
        "PULSE_safe_pack_v0/tools/verify_artifact_provenance_binding_v0.py"
    ) in binding_command
    assert (
        "$REVIEWED_REPO_ROOT/"
        "PULSE_safe_pack_v0/artifacts/artifact_provenance_binding_v0.json"
    ) in binding_command
    assert (
        "$REVIEWED_REPO_ROOT/"
        "PULSE_safe_pack_v0/tools/verify_artifact_provenance_binding_v0.py"
    ) not in binding_command


def test_builder_does_not_write_inside_repo_by_default(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    run_builder(repo, tmp_path)

    assert not (repo / "external_verification_packet_v0.json").exists()
    assert not (repo / "external_verification_packet_v0.md").exists()
    assert not (repo / "out" / "external_verification_packet_v0.json").exists()
    assert not (repo / "out" / "external_verification_packet_v0.md").exists()

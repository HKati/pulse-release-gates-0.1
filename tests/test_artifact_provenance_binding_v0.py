import copy
import hashlib
import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest
from jsonschema import ValidationError, validate

REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.tools.build_artifact_provenance_binding_v0 import (  # noqa: E402
    canonical_json_bytes,
    main as build_main,
)
from PULSE_safe_pack_v0.tools.verify_artifact_provenance_binding_v0 import (  # noqa: E402
    main as verify_main,
)


VALID_GIT_SHA = "a" * 40
CREATED_UTC = "2026-02-17T12:34:56Z"


@contextmanager
def working_directory(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def recompute_binding_hash(binding: dict) -> dict:
    binding = copy.deepcopy(binding)
    binding.pop("binding_hash", None)
    binding["binding_hash"] = hashlib.sha256(
        canonical_json_bytes(binding)
    ).hexdigest()
    return binding


def write_policy(path: Path) -> None:
    write_text(
        path,
        "\n".join(
            [
                "id: pulse-gate-policy-v0",
                'version: "0.1.1"',
                "gates:",
                "  required:",
                "    - prod_gate_ok",
                "    - shared_gate_ok",
                "  release_required:",
                "    - detectors_materialized_ok",
                "    - external_all_pass",
                "    - prod_gate_ok",
                "  core_required:",
                "    - core_gate_ok",
                "  advisory: []",
                "",
            ]
        ),
    )


def status_payload(*, required_gates: list[str] | None = None) -> dict:
    metrics: dict = {
        "run_mode": "prod",
        "run_id": "1",
        "run_key": "GITHUB_RUN_ID=1|GITHUB_RUN_NUMBER=2|GITHUB_WORKFLOW=PULSE CI",
        "git_sha": VALID_GIT_SHA,
    }

    if required_gates is not None:
        metrics["required_gates"] = required_gates

    return {
        "version": "1.0.0-prod",
        "created_utc": CREATED_UTC,
        "metrics": metrics,
        "gates": {
            "prod_gate_ok": True,
            "shared_gate_ok": True,
            "detectors_materialized_ok": True,
            "external_all_pass": True,
            "core_gate_ok": True,
        },
    }


def fixture_paths(tmp_path: Path) -> dict[str, Path]:
    reviewed_root = tmp_path / "reviewed_repo"

    status_rel = Path("PULSE_safe_pack_v0/artifacts/status.json")
    policy_rel = Path("pulse_gate_policy_v0.yml")
    ledger_rel = Path("PULSE_safe_pack_v0/artifacts/report_card.html")
    release_decision_rel = Path("PULSE_safe_pack_v0/artifacts/release_decision_v0.json")
    manifest_rel = Path("PULSE_safe_pack_v0/artifacts/release_authority_v0.json")
    binding_rel = Path("PULSE_safe_pack_v0/artifacts/artifact_provenance_binding_v0.json")

    return {
        "root": reviewed_root,
        "status_rel": status_rel,
        "policy_rel": policy_rel,
        "ledger_rel": ledger_rel,
        "release_decision_rel": release_decision_rel,
        "manifest_rel": manifest_rel,
        "binding_rel": binding_rel,
        "status": reviewed_root / status_rel,
        "policy": reviewed_root / policy_rel,
        "ledger": reviewed_root / ledger_rel,
        "release_decision": reviewed_root / release_decision_rel,
        "manifest": reviewed_root / manifest_rel,
        "binding": reviewed_root / binding_rel,
        "schema": REPO_ROOT
        / "schemas"
        / "provenance"
        / "artifact_provenance_binding_v0.schema.json",
    }


def write_fixtures(
    tmp_path: Path,
    *,
    required_gates: list[str] | None = None,
    release_level: str = "PROD-PASS",
) -> dict[str, Path]:
    paths = fixture_paths(tmp_path)

    write_json(paths["status"], status_payload(required_gates=required_gates))
    write_policy(paths["policy"])
    write_text(paths["ledger"], "PULSE Quality Ledger\n")
    write_json(
        paths["release_decision"],
        {
            "schema_id": "pulse_release_decision_v0",
            "producer": "materialize_release_decision.py",
            "release_level": release_level,
        },
    )
    write_json(paths["manifest"], {"schema_id": "release_authority_v0", "ok": True})

    return paths


def rel(paths: dict[str, Path], key: str) -> str:
    return paths[f"{key}_rel"].as_posix()


def build_args(paths: dict[str, Path], *extra_args: str) -> list[str]:
    return [
        "--status",
        rel(paths, "status"),
        "--policy",
        rel(paths, "policy"),
        "--ledger",
        rel(paths, "ledger"),
        "--release-decision",
        rel(paths, "release_decision"),
        "--release-authority-manifest",
        rel(paths, "manifest"),
        "--out",
        rel(paths, "binding"),
        "--created-utc",
        CREATED_UTC,
        *extra_args,
    ]


def run_build(paths: dict[str, Path], *extra_args: str) -> int:
    with working_directory(paths["root"]):
        return build_main(build_args(paths, *extra_args))


def build_binding(paths: dict[str, Path], *extra_args: str) -> dict:
    assert run_build(paths, *extra_args) == 0
    return read_json(paths["binding"])


def verify_binding(paths: dict[str, Path]) -> int:
    return verify_main(
        [
            "--binding",
            str(paths["binding"]),
            "--repo-root",
            str(paths["root"]),
        ]
    )


def schema() -> dict:
    return read_json(
        REPO_ROOT / "schemas" / "provenance" / "artifact_provenance_binding_v0.schema.json"
    )


def assert_schema_valid(binding: dict) -> None:
    validate(instance=binding, schema=schema())


def assert_schema_invalid(binding: dict) -> None:
    with pytest.raises(ValidationError):
        validate(instance=binding, schema=schema())


def set_subject_path(binding: dict, role: str, path: str) -> None:
    for subject in binding["binding_subjects"]:
        if subject["role"] == role:
            subject["path"] = path
            return

    raise AssertionError(f"missing binding subject role: {role}")


def subject_by_role(binding: dict, role: str) -> dict:
    for subject in binding["binding_subjects"]:
        if subject["role"] == role:
            return subject

    raise AssertionError(f"missing binding subject role: {role}")


def test_builder_creates_binding(tmp_path: Path) -> None:
    paths = write_fixtures(tmp_path)
    binding = build_binding(paths, "--policy-set", "required", "--policy-set", "release_required")

    assert paths["binding"].exists()
    assert binding["schema_id"] == "pulse.artifact_provenance_binding.v0"
    assert binding["binding_hash"]
    assert_schema_valid(binding)


def test_binding_schema_id_and_version(tmp_path: Path) -> None:
    paths = write_fixtures(tmp_path)
    binding = build_binding(paths)

    assert binding["schema_id"] == "pulse.artifact_provenance_binding.v0"
    assert binding["schema_version"] == "0.1.0"
    assert binding["producer"]["name"] == "build_artifact_provenance_binding_v0.py"
    assert_schema_valid(binding)


def test_binding_records_status_policy_ledger_decision_manifest_hashes(
    tmp_path: Path,
) -> None:
    paths = write_fixtures(tmp_path)
    binding = build_binding(paths)

    assert binding["authority_carrier"]["status_json"]["sha256"]
    assert binding["authority_carrier"]["declared_gate_policy"]["sha256"]
    assert binding["reader_carrier"]["quality_ledger"]["sha256"]
    assert binding["authority_carrier"]["release_decision"]["sha256"]
    assert binding["trace_carrier"]["release_authority_manifest"]["sha256"]
    assert_schema_valid(binding)


def test_binding_records_repository_relative_paths(tmp_path: Path) -> None:
    paths = write_fixtures(tmp_path)
    binding = build_binding(paths)

    assert binding["authority_carrier"]["status_json"]["path"] == rel(paths, "status")
    assert binding["authority_carrier"]["declared_gate_policy"]["path"] == rel(
        paths,
        "policy",
    )
    assert binding["reader_carrier"]["quality_ledger"]["path"] == rel(paths, "ledger")
    assert binding["authority_carrier"]["release_decision"]["path"] == rel(
        paths,
        "release_decision",
    )
    assert binding["trace_carrier"]["release_authority_manifest"]["path"] == rel(
        paths,
        "manifest",
    )

    assert_schema_valid(binding)


def test_binding_records_workflow_effective_gate_set_from_policy_sets(
    tmp_path: Path,
) -> None:
    paths = write_fixtures(tmp_path)
    binding = build_binding(paths, "--policy-set", "required", "--policy-set", "release_required")

    gate_set = binding["authority_carrier"]["workflow_effective_required_gate_set"]

    assert gate_set["effective_source"] == "workflow-effective:required+release_required"
    assert gate_set["policy_sets"] == ["required", "release_required"]
    assert gate_set["gate_ids"] == [
        "prod_gate_ok",
        "shared_gate_ok",
        "detectors_materialized_ok",
        "external_all_pass",
    ]
    assert gate_set["sha256"]
    assert_schema_valid(binding)


def test_binding_records_metrics_required_gates_source(tmp_path: Path) -> None:
    paths = write_fixtures(
        tmp_path,
        required_gates=["prod_gate_ok", "external_all_pass"],
    )
    binding = build_binding(paths)

    gate_set = binding["authority_carrier"]["workflow_effective_required_gate_set"]

    assert gate_set["effective_source"] == "metrics.required_gates"
    assert gate_set["policy_sets"] == []
    assert gate_set["gate_ids"] == ["prod_gate_ok", "external_all_pass"]
    assert_schema_valid(binding)


def test_binding_separates_check_gates_result_from_release_decision_label(
    tmp_path: Path,
) -> None:
    paths = write_fixtures(tmp_path)
    binding = build_binding(paths)

    enforcement = binding["authority_carrier"]["strict_ci_gate_enforcement"]
    release_decision = binding["authority_carrier"]["release_decision"]

    assert enforcement["source"] == "check_gates.py"
    assert enforcement["result"] == "allow"
    assert enforcement["exit_code"] == 0
    assert "label" not in enforcement

    assert release_decision["producer"] == "materialize_release_decision.py"
    assert release_decision["label"] == "PROD-PASS"
    assert_schema_valid(binding)


def test_binding_hash_is_canonical_and_stable(tmp_path: Path) -> None:
    paths = write_fixtures(tmp_path)

    first = build_binding(paths)
    first_hash = first["binding_hash"]
    second = build_binding(paths)

    assert second["binding_hash"] == first_hash
    assert_schema_valid(second)


def test_verifier_passes_for_untouched_repository_relative_artifacts(
    tmp_path: Path,
) -> None:
    paths = write_fixtures(tmp_path)
    build_binding(paths)

    assert verify_binding(paths) == 0


def test_verifier_passes_with_default_repo_root_when_run_from_reviewed_root(
    tmp_path: Path,
) -> None:
    paths = write_fixtures(tmp_path)
    build_binding(paths)

    with working_directory(paths["root"]):
        assert verify_main(["--binding", rel(paths, "binding")]) == 0


def test_verifier_fails_when_status_changes(tmp_path: Path) -> None:
    paths = write_fixtures(tmp_path)
    build_binding(paths)

    write_json(paths["status"], {"changed": True})

    assert verify_binding(paths) != 0


def test_verifier_fails_when_policy_changes(tmp_path: Path) -> None:
    paths = write_fixtures(tmp_path)
    build_binding(paths)

    write_text(paths["policy"], "gates:\n  required:\n    - changed_gate\n")

    assert verify_binding(paths) != 0


def test_verifier_fails_when_ledger_changes(tmp_path: Path) -> None:
    paths = write_fixtures(tmp_path)
    build_binding(paths)

    write_text(paths["ledger"], "changed\n")

    assert verify_binding(paths) != 0


def test_verifier_fails_when_release_decision_changes(tmp_path: Path) -> None:
    paths = write_fixtures(tmp_path)
    build_binding(paths)

    write_json(paths["release_decision"], {"release_level": "FAIL"})

    assert verify_binding(paths) != 0


def test_verifier_fails_when_release_authority_manifest_changes(
    tmp_path: Path,
) -> None:
    paths = write_fixtures(tmp_path)
    build_binding(paths)

    write_json(paths["manifest"], {"changed": True})

    assert verify_binding(paths) != 0


def test_verifier_fails_when_binding_hash_changes(tmp_path: Path) -> None:
    paths = write_fixtures(tmp_path)
    binding = build_binding(paths)

    binding["binding_hash"] = "0" * 64
    write_json(paths["binding"], binding)

    assert verify_binding(paths) != 0


def test_verifier_accepts_absolute_authority_file_path_inside_reviewed_root(
    tmp_path: Path,
) -> None:
    paths = write_fixtures(tmp_path)
    binding = build_binding(paths)

    binding["authority_carrier"]["status_json"]["path"] = str(paths["status"].resolve())
    binding = recompute_binding_hash(binding)
    write_json(paths["binding"], binding)

    assert verify_binding(paths) == 0


def test_verifier_accepts_absolute_binding_subject_path_inside_reviewed_root(
    tmp_path: Path,
) -> None:
    paths = write_fixtures(tmp_path)
    binding = build_binding(paths)

    set_subject_path(binding, "status_json", str(paths["status"].resolve()))
    binding = recompute_binding_hash(binding)
    write_json(paths["binding"], binding)

    assert verify_binding(paths) == 0


def test_verifier_rejects_absolute_authority_file_path_outside_reviewed_root(
    tmp_path: Path,
) -> None:
    paths = write_fixtures(tmp_path)
    binding = build_binding(paths)

    outside = paths["root"].parent / "outside_status.json"
    write_json(outside, status_payload())

    binding["authority_carrier"]["status_json"]["path"] = str(outside.resolve())
    write_json(paths["binding"], binding)

    assert verify_binding(paths) == 2


def test_verifier_rejects_absolute_binding_subject_path_outside_reviewed_root(
    tmp_path: Path,
) -> None:
    paths = write_fixtures(tmp_path)
    binding = build_binding(paths)

    outside = paths["root"].parent / "outside_status.json"
    write_json(outside, status_payload())

    set_subject_path(binding, "status_json", str(outside.resolve()))
    write_json(paths["binding"], binding)

    assert verify_binding(paths) == 2


def test_verifier_rejects_parent_directory_escape_path(tmp_path: Path) -> None:
    paths = write_fixtures(tmp_path)
    binding = build_binding(paths)

    outside = paths["root"].parent / "outside_status.json"
    write_json(outside, status_payload())

    binding["authority_carrier"]["status_json"]["path"] = "../outside_status.json"
    write_json(paths["binding"], binding)

    assert verify_binding(paths) == 2


def test_verifier_rejects_parent_directory_escape_binding_subject_path(
    tmp_path: Path,
) -> None:
    paths = write_fixtures(tmp_path)
    binding = build_binding(paths)

    outside = paths["root"].parent / "outside_status.json"
    write_json(outside, status_payload())

    set_subject_path(binding, "status_json", "../outside_status.json")
    write_json(paths["binding"], binding)

    assert verify_binding(paths) == 2


def test_verifier_rejects_symlink_escape_outside_reviewed_root(
    tmp_path: Path,
) -> None:
    paths = write_fixtures(tmp_path)
    binding = build_binding(paths)

    outside = paths["root"].parent / "outside_status.json"
    write_json(outside, status_payload())

    link = paths["root"] / "PULSE_safe_pack_v0" / "artifacts" / "status_link.json"
    link.parent.mkdir(parents=True, exist_ok=True)

    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlink creation is not available in this environment: {exc}")

    binding["authority_carrier"]["status_json"]["path"] = (
        link.relative_to(paths["root"]).as_posix()
    )
    write_json(paths["binding"], binding)

    assert verify_binding(paths) == 2


def test_verifier_rejects_windows_style_subject_path(tmp_path: Path) -> None:
    paths = write_fixtures(tmp_path)
    binding = build_binding(paths)

    binding["authority_carrier"]["status_json"]["path"] = (
        "PULSE_safe_pack_v0\\artifacts\\status.json"
    )
    write_json(paths["binding"], binding)

    assert verify_binding(paths) == 2


def test_verifier_rejects_empty_subject_path(tmp_path: Path) -> None:
    paths = write_fixtures(tmp_path)
    binding = build_binding(paths)

    binding["authority_carrier"]["status_json"]["path"] = ""
    write_json(paths["binding"], binding)

    assert verify_binding(paths) == 2


def test_verifier_rejects_whitespace_padded_subject_path(tmp_path: Path) -> None:
    paths = write_fixtures(tmp_path)
    binding = build_binding(paths)

    binding["authority_carrier"]["status_json"]["path"] = f" {rel(paths, 'status')} "
    write_json(paths["binding"], binding)

    assert verify_binding(paths) == 2


def test_verifier_keeps_inline_subject_behavior(tmp_path: Path) -> None:
    paths = write_fixtures(tmp_path)
    binding = build_binding(paths)

    gate_set_subject = subject_by_role(binding, "workflow_effective_required_gate_set")
    enforcement_subject = subject_by_role(binding, "strict_ci_gate_enforcement")

    assert gate_set_subject["path"] == (
        "inline:authority_carrier.workflow_effective_required_gate_set"
    )
    assert enforcement_subject["path"] == (
        "inline:authority_carrier.strict_ci_gate_enforcement"
    )
    assert verify_binding(paths) == 0


def test_verifier_accepts_absolute_paths_generated_by_builder_inside_reviewed_root(
    tmp_path: Path,
) -> None:
    paths = write_fixtures(tmp_path)

    with working_directory(paths["root"]):
        assert build_main(
            [
                "--status",
                str(paths["status"]),
                "--policy",
                str(paths["policy"]),
                "--ledger",
                str(paths["ledger"]),
                "--release-decision",
                str(paths["release_decision"]),
                "--release-authority-manifest",
                str(paths["manifest"]),
                "--out",
                str(paths["binding"]),
                "--created-utc",
                CREATED_UTC,
            ]
        ) == 0

    binding = read_json(paths["binding"])

    assert Path(binding["authority_carrier"]["status_json"]["path"]).is_absolute()
    assert Path(binding["authority_carrier"]["declared_gate_policy"]["path"]).is_absolute()
    assert Path(binding["reader_carrier"]["quality_ledger"]["path"]).is_absolute()

    assert verify_binding(paths) == 0


def test_canonical_json_bytes_are_deterministic() -> None:
    left = {"b": 2, "a": {"d": 4, "c": 3}}
    right = {"a": {"c": 3, "d": 4}, "b": 2}

    assert canonical_json_bytes(left) == canonical_json_bytes(right)


def test_builder_rejects_malformed_git_sha(tmp_path: Path) -> None:
    paths = write_fixtures(tmp_path)
    status = status_payload()
    status["metrics"]["git_sha"] = "not-a-sha"
    write_json(paths["status"], status)

    assert run_build(paths) != 0


def test_builder_rejects_missing_run_identity(tmp_path: Path) -> None:
    paths = write_fixtures(tmp_path)
    status = status_payload()
    status["metrics"].pop("run_id", None)
    status["metrics"]["run_key"] = ""
    write_json(paths["status"], status)

    assert run_build(paths) != 0


def test_builder_parses_run_id_from_run_key(tmp_path: Path) -> None:
    paths = write_fixtures(tmp_path)
    status = status_payload()
    status["metrics"].pop("run_id", None)
    write_json(paths["status"], status)

    binding = build_binding(paths)

    assert binding["run"]["run_id"] == "1"
    assert_schema_valid(binding)


def test_builder_rejects_unknown_release_decision_label(tmp_path: Path) -> None:
    paths = write_fixtures(tmp_path)
    write_json(
        paths["release_decision"],
        {
            "schema_id": "pulse_release_decision_v0",
            "producer": "materialize_release_decision.py",
            "release_level": "NOT-A-DECISION",
        },
    )

    assert run_build(paths) != 0


def test_workflow_effective_gate_set_deduplicates_gate_ids(tmp_path: Path) -> None:
    paths = write_fixtures(tmp_path)
    binding = build_binding(paths, "--policy-set", "required", "--policy-set", "release_required")

    gate_ids = binding["authority_carrier"]["workflow_effective_required_gate_set"][
        "gate_ids"
    ]

    assert gate_ids == list(dict.fromkeys(gate_ids))
    assert_schema_valid(binding)


def test_schema_requires_real_git_sha(tmp_path: Path) -> None:
    paths = write_fixtures(tmp_path)
    binding = build_binding(paths)

    bad = copy.deepcopy(binding)
    bad["run"]["git_sha"] = "not-a-sha"

    assert_schema_invalid(bad)


def test_schema_requires_non_empty_run_identifiers(tmp_path: Path) -> None:
    paths = write_fixtures(tmp_path)
    binding = build_binding(paths)

    blank_run_id = copy.deepcopy(binding)
    blank_run_id["run"]["run_id"] = ""

    assert_schema_invalid(blank_run_id)

    blank_run_key = copy.deepcopy(binding)
    blank_run_key["run"]["run_key"] = ""

    assert_schema_invalid(blank_run_key)


def test_schema_rejects_inconsistent_ci_enforcement_outcomes(
    tmp_path: Path,
) -> None:
    paths = write_fixtures(tmp_path)
    binding = build_binding(paths)

    allow_with_block_exit = copy.deepcopy(binding)
    allow_with_block_exit["authority_carrier"]["strict_ci_gate_enforcement"][
        "result"
    ] = "allow"
    allow_with_block_exit["authority_carrier"]["strict_ci_gate_enforcement"][
        "exit_code"
    ] = 1

    assert_schema_invalid(allow_with_block_exit)

    block_with_allow_exit = copy.deepcopy(binding)
    block_with_allow_exit["authority_carrier"]["strict_ci_gate_enforcement"][
        "result"
    ] = "block"
    block_with_allow_exit["authority_carrier"]["strict_ci_gate_enforcement"][
        "exit_code"
    ] = 0

    assert_schema_invalid(block_with_allow_exit)


def test_schema_constrains_release_decision_labels(tmp_path: Path) -> None:
    paths = write_fixtures(tmp_path)
    binding = build_binding(paths)

    bad = copy.deepcopy(binding)
    bad["authority_carrier"]["release_decision"]["label"] = "NOT-A-DECISION"

    assert_schema_invalid(bad)


def test_schema_rejects_duplicate_effective_gate_ids(tmp_path: Path) -> None:
    paths = write_fixtures(tmp_path)
    binding = build_binding(paths)

    bad = copy.deepcopy(binding)
    gate_ids = bad["authority_carrier"]["workflow_effective_required_gate_set"][
        "gate_ids"
    ]
    gate_ids.append(gate_ids[0])

    assert_schema_invalid(bad)

#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import sys
import warnings
import zipfile
from pathlib import Path
from typing import Any

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]

TOOL = ROOT / "tools" / "check_pulsemech_compute_subject_input_packet_v0.py"
SCHEMA = (
    ROOT
    / "schemas"
    / "pulsemech_compute_subject_input_packet_v0.schema.json"
)
EXAMPLE = (
    ROOT
    / "examples"
    / "compute"
    / "pulsemech_compute_subject_input_packet_6066_example_v0.json"
)
ARCHIVE = ROOT / "PULSE_CI_6066_release_grade_artifact_preservation_v0.zip"
POLICY = ROOT / "pulse_gate_policy_v0.yml"
WORKFLOW = ROOT / ".github" / "workflows" / "pulse_ci.yml"
REGISTRY = ROOT / "pulse_gate_registry_v0.yml"

EXPECTED_ARCHIVE_SHA256 = (
    "7949bfd00468e6f9347fddaae732bdcebff5527e87ecb379a6c84a47176db966"
)
EXPECTED_ARCHIVE_SIZE_BYTES = 44660
EXPECTED_CARRIER_PATH = (
    "PULSE_CI_6066_release_grade_artifact_preservation_v0.zip"
)

EXPECTED_CHECKS = {
    "artifact_content_syntax_ok",
    "artifact_graph_ok",
    "authority_source_bindings_ok",
    "canonical_packet_serialization_ok",
    "carrier_binding_ok",
    "coverage_reconstruction_ok",
    "deterministic_reference_ordering_ok",
    "non_authoritative_boundaries_ok",
    "package_inventory_ok",
    "packet_ok_errors_semantics_ok",
    "packet_type_ok",
    "preservation_checksums_ok",
    "preservation_provider_manifest_ok",
    "provenance_branch_ok",
    "provider_bindings_ok",
    "role_bindings_ok",
    "schema_version_ok",
    "subject_artifact_bindings_ok",
    "subject_identity_ok",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


_SCHEMA = load_json(SCHEMA)
_BASE_PACKET = load_json(EXAMPLE)
jsonschema.Draft202012Validator.check_schema(_SCHEMA)


def packet() -> dict[str, Any]:
    return copy.deepcopy(_BASE_PACKET)


def render_packet(value: dict[str, Any]) -> str:
    return (
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    )


def write_packet(path: Path, value: dict[str, Any]) -> None:
    path.write_text(render_packet(value), encoding="utf-8")


def import_tool_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "pulsemech_subject_input_packet_validator_v0_under_test",
        TOOL,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


TOOL_MODULE = import_tool_module()


def run_tool(
    *,
    packet_path: Path = EXAMPLE,
    schema_path: Path = SCHEMA,
    carrier_path: Path | None = None,
    repository_root: Path = ROOT,
    output: Path | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(TOOL),
        "--schema",
        str(schema_path),
        "--packet",
        str(packet_path),
        "--repository-root",
        str(repository_root),
    ]
    if carrier_path is not None:
        command.extend(["--carrier", str(carrier_path)])
    if output is not None:
        command.extend(["--output", str(output)])

    environment = dict(os.environ)
    if extra_env is not None:
        environment.update(extra_env)

    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=environment,
    )


def parse_json_text(text: str) -> dict[str, Any]:
    loaded = json.loads(text)
    assert isinstance(loaded, dict)
    return loaded


def assert_cli_failure(
    result: subprocess.CompletedProcess[str],
    expected_fragment: str,
    *,
    expected_returncode: int | None = None,
) -> dict[str, Any]:
    assert result.returncode != 0, result.stdout + result.stderr
    if expected_returncode is not None:
        assert result.returncode == expected_returncode, result.stdout + result.stderr
    assert result.stderr == ""
    assert "Traceback" not in result.stdout

    diagnostic = parse_json_text(result.stdout)
    assert diagnostic["ok"] is False
    assert any(
        expected_fragment in str(error)
        for error in diagnostic["errors"]
    ), diagnostic
    return diagnostic


def semantic_diagnostic(
    value: dict[str, Any],
    *,
    packet_text: str | None = None,
    packet_path: Path = EXAMPLE,
    carrier_path: Path = ARCHIVE,
    repository_root: Path = ROOT,
) -> tuple[dict[str, Any], int]:
    schema_errors = TOOL_MODULE.schema_errors(_SCHEMA, value)
    assert schema_errors == [], schema_errors

    carrier_bytes = carrier_path.read_bytes()
    checks, errors = TOOL_MODULE.semantic_checks(
        value,
        packet_text=packet_text if packet_text is not None else render_packet(value),
        packet_path=packet_path,
        carrier_path=carrier_path,
        carrier_bytes=carrier_bytes,
        repository_root=repository_root,
    )
    ok = all(checks.values()) and not errors
    diagnostic = TOOL_MODULE.make_diagnostic(
        ok=ok,
        schema_valid=True,
        checks=checks,
        errors=errors,
    )
    return diagnostic, 0 if ok else 1


def assert_semantic_failure(
    value: dict[str, Any],
    check_name: str,
    *,
    expected_fragment: str | None = None,
    packet_text: str | None = None,
    carrier_path: Path = ARCHIVE,
) -> dict[str, Any]:
    diagnostic, exit_code = semantic_diagnostic(
        value,
        packet_text=packet_text,
        carrier_path=carrier_path,
    )

    assert exit_code == 1, diagnostic
    assert diagnostic["schema_valid"] is True, diagnostic
    assert diagnostic["checks"][check_name] is False, diagnostic
    if expected_fragment is not None:
        assert any(
            expected_fragment in str(error)
            for error in diagnostic["errors"]
        ), diagnostic
    return diagnostic


def assert_semantic_success(
    value: dict[str, Any],
    *,
    carrier_path: Path = ARCHIVE,
) -> dict[str, Any]:
    diagnostic, exit_code = semantic_diagnostic(
        value,
        carrier_path=carrier_path,
    )
    assert exit_code == 0, diagnostic
    assert diagnostic["ok"] is True
    assert diagnostic["schema_valid"] is True
    assert diagnostic["errors"] == []
    assert set(diagnostic["checks"]) == EXPECTED_CHECKS
    assert all(diagnostic["checks"].values())
    return diagnostic


def artifact_by_role(value: dict[str, Any], role: str) -> dict[str, Any]:
    return next(
        row
        for row in value["artifacts"]
        if row["role"] == role
    )


def artifact_by_member_suffix(
    value: dict[str, Any],
    suffix: str,
) -> dict[str, Any]:
    return next(
        row
        for row in value["artifacts"]
        if row["member_path"].endswith(suffix)
    )


def first_provider_artifact(value: dict[str, Any]) -> dict[str, Any]:
    return next(
        row
        for row in value["artifacts"]
        if isinstance(row.get("provider_binding"), dict)
    )


def update_carrier_identity(value: dict[str, Any], carrier_path: Path) -> None:
    data = carrier_path.read_bytes()
    value["carrier"]["sha256"] = sha256_bytes(data)
    value["carrier"]["size_bytes"] = len(data)


def _copy_zip_members(
    source: zipfile.ZipFile,
    destination: zipfile.ZipFile,
) -> None:
    for info in source.infolist():
        payload = b"" if info.is_dir() else source.read(info.filename)
        destination.writestr(copy.copy(info), payload)


def archive_with_extra_member(
    tmp_path: Path,
    *,
    name: str,
    payload: bytes = b"extra\n",
) -> Path:
    destination = tmp_path / "carrier-extra.zip"
    with zipfile.ZipFile(ARCHIVE, "r") as source:
        with zipfile.ZipFile(destination, "w") as target:
            _copy_zip_members(source, target)
            target.writestr(name, payload)
    return destination


def archive_with_duplicate_member(tmp_path: Path) -> Path:
    destination = tmp_path / "carrier-duplicate.zip"
    with zipfile.ZipFile(ARCHIVE, "r") as source:
        infos = source.infolist()
        assert infos
        duplicate = infos[0]
        duplicate_payload = source.read(duplicate.filename)
        with zipfile.ZipFile(destination, "w") as target:
            _copy_zip_members(source, target)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                target.writestr(copy.copy(duplicate), duplicate_payload)
    return destination


def archive_with_symlink_member(tmp_path: Path) -> Path:
    destination = tmp_path / "carrier-symlink.zip"
    with zipfile.ZipFile(ARCHIVE, "r") as source:
        with zipfile.ZipFile(destination, "w") as target:
            _copy_zip_members(source, target)
            link = zipfile.ZipInfo(
                "pulse-ci-6066-preservation-v0/UNDECLARED_SYMLINK"
            )
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            target.writestr(link, b"README.md")
    return destination


def snapshot(paths: tuple[Path, ...]) -> dict[Path, tuple[int, str]]:
    return {
        path: (path.stat().st_size, sha256_file(path))
        for path in paths
    }


def observed_packet(
    source_bytes: bytes,
    *,
    production_mode: str = "fixed_source_adapter",
) -> dict[str, Any]:
    value = packet()
    value["record_status"] = "observed"
    value.pop("fixture_provenance")

    scope = {
        "current_run_export": "current_run",
        "post_run_export": "post_run_preservation",
        "fixed_source_adapter": "fixed_source_adapter",
    }[production_mode]
    producer_run_key = (
        value["subject"]["subject_run_key"]
        if production_mode == "current_run_export"
        else "PACKET_EXPORT_RUN_ID=synthetic-validator-regression"
    )
    value["packet_identity"]["packet_scope"] = scope
    value["producer"] = {
        "ci_workflow_or_job_identity": (
            "PULSE CI / synthetic subject-input packet producer regression"
        ),
        "producer_id": "pulsemech_compute_subject_input_packet_producer_v0",
        "producer_name": "PULSEmech compute subject-input packet producer",
        "producer_run_key": producer_run_key,
        "producer_source": (
            "tools/build_pulsemech_compute_subject_input_packet_v0.py"
        ),
        "producer_source_revision": "f" * 40,
        "producer_source_sha256": sha256_bytes(source_bytes),
        "producer_version": "0.1.0",
        "production_mode": production_mode,
    }
    return value


def isolated_test_git_environment() -> dict[str, str]:
    required = ("PATH",)
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        pytest.skip(
            "Git regression requires process environment values: "
            + ", ".join(missing)
        )

    preserved = (
        "PATH",
        "PATHEXT",
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "TEMP",
        "TMP",
        "TMPDIR",
    )
    environment = {
        key: os.environ[key]
        for key in preserved
        if key in os.environ
    }
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_COUNT": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "LC_ALL": "C",
            "LANG": "C",
        }
    )
    return environment


def create_git_repository(
    tmp_path: Path,
    *,
    name: str,
    tracked_bytes: bytes,
) -> tuple[Path, str]:
    repository = tmp_path / name
    repository.mkdir()
    environment = isolated_test_git_environment()

    subprocess.run(
        ["git", "init", "-q", str(repository)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
    )
    (repository / "tracked.txt").write_bytes(tracked_bytes)
    subprocess.run(
        ["git", "-C", str(repository), "add", "--", "tracked.txt"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "-c",
            "user.name=PULSEmech validator regression",
            "-c",
            "user.email=pulsemech-validator@example.invalid",
            "commit",
            "-q",
            "-m",
            "fixture",
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
    )
    revision = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
    ).stdout.strip()
    assert len(revision) == 40
    return repository, revision


def inherited_git_blob_read(
    repository_root: Path,
    *,
    revision: str,
    path: str,
    attacker_environment: dict[str, str],
) -> subprocess.CompletedProcess[bytes]:
    environment = isolated_test_git_environment()
    environment.update(attacker_environment)
    return subprocess.run(
        [
            "git",
            "-C",
            str(repository_root),
            "cat-file",
            "blob",
            f"{revision}:{path}",
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
    )


def attacker_git_environments(
    attacker_repository: Path,
) -> dict[str, dict[str, str]]:
    git_directory = attacker_repository / ".git"
    object_directory = git_directory / "objects"
    return {
        "git_dir_and_work_tree": {
            "GIT_DIR": str(git_directory),
            "GIT_WORK_TREE": str(attacker_repository),
        },
        "git_object_directory": {
            "GIT_OBJECT_DIRECTORY": str(object_directory),
        },
        "git_alternate_object_directories": {
            "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(object_directory),
        },
        "git_common_directory": {
            "GIT_COMMON_DIR": str(git_directory),
        },
    }


# ---------------------------------------------------------------------------
# Exact positive path and deterministic diagnostics
# ---------------------------------------------------------------------------


def test_contract_files_and_repository_root_carrier_exist() -> None:
    for path in (TOOL, SCHEMA, EXAMPLE, ARCHIVE, POLICY, WORKFLOW, REGISTRY):
        assert path.is_file(), path
        assert not path.is_symlink(), path

    assert ARCHIVE.stat().st_size == EXPECTED_ARCHIVE_SIZE_BYTES
    assert sha256_file(ARCHIVE) == EXPECTED_ARCHIVE_SHA256

    value = packet()
    assert value["carrier"]["path_or_uri"] == EXPECTED_CARRIER_PATH
    assert value["carrier"]["sha256"] == EXPECTED_ARCHIVE_SHA256
    assert value["carrier"]["size_bytes"] == EXPECTED_ARCHIVE_SIZE_BYTES
    assert len(value["artifacts"]) == 32
    assert all(
        row["display_path_or_uri"].startswith(EXPECTED_CARRIER_PATH + "!/")
        for row in value["artifacts"]
    )


def test_exact_6066_example_passes_every_semantic_check() -> None:
    result = run_tool()

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    assert result.stdout.endswith("\n")

    diagnostic = parse_json_text(result.stdout)
    assert diagnostic["tool"] == (
        "check_pulsemech_compute_subject_input_packet_v0"
    )
    assert diagnostic["schema_version"] == (
        "pulsemech_compute_subject_input_packet_v0"
    )
    assert diagnostic["packet_type"] == (
        "pulsemech_compute_subject_input_packet"
    )
    assert diagnostic["schema_valid"] is True
    assert diagnostic["ok"] is True
    assert diagnostic["errors"] == []
    assert set(diagnostic["checks"]) == EXPECTED_CHECKS
    assert all(diagnostic["checks"].values())


def test_diagnostic_output_matches_stdout_and_is_deterministic(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first-diagnostic.json"
    second = tmp_path / "second-diagnostic.json"

    first_result = run_tool(output=first)
    second_result = run_tool(output=second)

    assert first_result.returncode == 0, first_result.stdout + first_result.stderr
    assert second_result.returncode == 0, second_result.stdout + second_result.stderr
    assert first_result.stderr == ""
    assert second_result.stderr == ""
    assert first_result.stdout == second_result.stdout
    assert first.read_bytes() == second.read_bytes()
    assert first.read_text(encoding="utf-8") == first_result.stdout


def test_packet_error_state_is_independent_from_validator_success() -> None:
    value = packet()
    value["ok"] = False
    value["errors"] = ["synthetic_packet_construction_error"]

    diagnostic = assert_semantic_success(value)
    assert diagnostic["checks"]["packet_ok_errors_semantics_ok"] is True


def test_historical_sources_are_read_from_git_not_current_worktree() -> None:
    value = packet()
    rows = [
        value["authority_sources"]["workflow"],
        value["authority_sources"]["policy"],
        value["authority_sources"]["gate_registry"],
        *value["authority_sources"]["additional_sources"],
    ]

    for row in rows:
        revision = row["source_revision"]
        assert isinstance(revision, str)
        historical = TOOL_MODULE._git_blob_bytes(
            ROOT,
            revision=revision,
            path=row["path_or_uri"],
        )
        assert len(historical) == row["size_bytes"]
        assert sha256_bytes(historical) == row["sha256"]

    current_policy_sha = sha256_file(POLICY)
    current_workflow_sha = sha256_file(WORKFLOW)
    assert (
        current_policy_sha != value["authority_sources"]["policy"]["sha256"]
        or current_workflow_sha
        != value["authority_sources"]["workflow"]["sha256"]
    )


# ---------------------------------------------------------------------------
# Git process isolation and repository-root binding
# ---------------------------------------------------------------------------


def test_sanitized_git_environment_drops_caller_controlled_git_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    poisoned = {
        "GIT_DIR": "/attacker/repository/.git",
        "GIT_WORK_TREE": "/attacker/repository",
        "GIT_COMMON_DIR": "/attacker/common",
        "GIT_OBJECT_DIRECTORY": "/attacker/objects",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": "/attacker/alternates",
        "GIT_INDEX_FILE": "/attacker/index",
        "GIT_NAMESPACE": "attacker",
        "GIT_CONFIG_PARAMETERS": "'core.worktree=/attacker/repository'",
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "core.worktree",
        "GIT_CONFIG_VALUE_0": "/attacker/repository",
        "GIT_EXEC_PATH": "/attacker/git-core",
        "GIT_CEILING_DIRECTORIES": "/attacker",
        "GIT_DISCOVERY_ACROSS_FILESYSTEM": "1",
        "GIT_SHALLOW_FILE": "/attacker/shallow",
    }
    for key, value in poisoned.items():
        monkeypatch.setenv(key, value)

    child_environment = TOOL_MODULE._sanitized_git_environment()

    fixed_keys = {
        "GIT_CONFIG_GLOBAL",
        "GIT_CONFIG_SYSTEM",
        "GIT_CONFIG_NOSYSTEM",
        "GIT_CONFIG_COUNT",
        "GIT_OPTIONAL_LOCKS",
        "GIT_NO_REPLACE_OBJECTS",
        "GIT_TERMINAL_PROMPT",
        "LC_ALL",
        "LANG",
    }
    allowed_keys = set(TOOL_MODULE.GIT_PROCESS_ENV_ALLOWLIST) | fixed_keys
    assert set(child_environment) <= allowed_keys
    assert child_environment["PATH"] == os.environ["PATH"]
    assert child_environment["GIT_CONFIG_GLOBAL"] == os.devnull
    assert child_environment["GIT_CONFIG_SYSTEM"] == os.devnull
    assert child_environment["GIT_CONFIG_NOSYSTEM"] == "1"
    assert child_environment["GIT_CONFIG_COUNT"] == "0"
    assert child_environment["GIT_OPTIONAL_LOCKS"] == "0"
    assert child_environment["GIT_NO_REPLACE_OBJECTS"] == "1"
    assert child_environment["GIT_TERMINAL_PROMPT"] == "0"
    assert child_environment["LC_ALL"] == "C"
    assert child_environment["LANG"] == "C"

    for key in poisoned:
        if key == "GIT_CONFIG_COUNT":
            continue
        assert key not in child_environment


def test_missing_process_path_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PATH", raising=False)
    with pytest.raises(
        TOOL_MODULE.SemanticError,
        match="git_process_path_unavailable",
    ):
        TOOL_MODULE._sanitized_git_environment()


def test_git_blob_read_ignores_attacker_repository_and_object_stores(
    tmp_path: Path,
) -> None:
    real_bytes = b"real repository bytes\n"
    attacker_bytes = b"attacker repository bytes\n"
    real_repository, real_revision = create_git_repository(
        tmp_path,
        name="real-repository",
        tracked_bytes=real_bytes,
    )
    attacker_repository, attacker_revision = create_git_repository(
        tmp_path,
        name="attacker-repository",
        tracked_bytes=attacker_bytes,
    )
    assert real_revision != attacker_revision

    for label, attacker_environment in attacker_git_environments(
        attacker_repository
    ).items():
        vulnerable_read = inherited_git_blob_read(
            real_repository,
            revision=attacker_revision,
            path="tracked.txt",
            attacker_environment=attacker_environment,
        )
        assert vulnerable_read.returncode == 0, (
            label,
            vulnerable_read.stderr.decode("utf-8", errors="replace"),
        )
        assert vulnerable_read.stdout == attacker_bytes, label

        with pytest.MonkeyPatch.context() as poisoned:
            for key, value in attacker_environment.items():
                poisoned.setenv(key, value)

            with pytest.raises(
                TOOL_MODULE.SemanticError,
                match="git_blob_unavailable",
            ):
                TOOL_MODULE._git_blob_bytes(
                    real_repository,
                    revision=attacker_revision,
                    path="tracked.txt",
                )

            assert TOOL_MODULE._git_blob_bytes(
                real_repository,
                revision=real_revision,
                path="tracked.txt",
            ) == real_bytes


def test_full_validator_ignores_poisoned_git_environment(
    tmp_path: Path,
) -> None:
    attacker_repository, _attacker_revision = create_git_repository(
        tmp_path,
        name="full-validator-attacker",
        tracked_bytes=b"unrelated attacker bytes\n",
    )
    attacker_git_directory = attacker_repository / ".git"
    attacker_objects = attacker_git_directory / "objects"

    result = run_tool(
        extra_env={
            "GIT_DIR": str(attacker_git_directory),
            "GIT_WORK_TREE": str(attacker_repository),
            "GIT_COMMON_DIR": str(attacker_git_directory),
            "GIT_OBJECT_DIRECTORY": str(attacker_objects),
            "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(attacker_objects),
            "GIT_INDEX_FILE": str(attacker_git_directory / "index"),
            "GIT_NAMESPACE": "attacker",
            "GIT_CONFIG_PARAMETERS": (
                "'core.worktree="
                + str(attacker_repository)
                + "'"
            ),
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "core.worktree",
            "GIT_CONFIG_VALUE_0": str(attacker_repository),
            "GIT_CEILING_DIRECTORIES": str(tmp_path),
            "GIT_DISCOVERY_ACROSS_FILESYSTEM": "1",
        }
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    diagnostic = parse_json_text(result.stdout)
    assert diagnostic["schema_valid"] is True
    assert diagnostic["ok"] is True
    assert diagnostic["errors"] == []
    assert all(diagnostic["checks"].values())


def test_repository_root_must_equal_git_top_level(tmp_path: Path) -> None:
    repository, _revision = create_git_repository(
        tmp_path,
        name="root-verification-repository",
        tracked_bytes=b"root verification bytes\n",
    )
    nested = repository / "nested"
    nested.mkdir()

    assert TOOL_MODULE._verified_git_repository_root(repository) == (
        repository.resolve(strict=True)
    )
    with pytest.raises(
        TOOL_MODULE.SemanticError,
        match="git_repository_root_mismatch",
    ):
        TOOL_MODULE._verified_git_repository_root(nested)


# ---------------------------------------------------------------------------
# Strict parsing, schema validation, and provenance branches
# ---------------------------------------------------------------------------


def test_duplicate_json_keys_fail_closed_before_semantic_validation(
    tmp_path: Path,
) -> None:
    packet_path = tmp_path / "duplicate.json"
    packet_path.write_text(
        '{"schema_version": "pulsemech_compute_subject_input_packet_v0", '
        '"schema_version": "duplicate"}\n',
        encoding="utf-8",
    )

    diagnostic = assert_cli_failure(
        run_tool(packet_path=packet_path),
        "duplicate JSON key",
        expected_returncode=2,
    )
    assert diagnostic["schema_valid"] is False
    assert diagnostic["checks"] == {}


def test_non_finite_json_values_fail_closed(tmp_path: Path) -> None:
    packet_path = tmp_path / "non-finite.json"
    packet_path.write_text('{"value": NaN}\n', encoding="utf-8")

    diagnostic = assert_cli_failure(
        run_tool(packet_path=packet_path),
        "non-finite JSON value",
        expected_returncode=2,
    )
    assert diagnostic["schema_valid"] is False


def test_invalid_utf8_packet_fails_closed(tmp_path: Path) -> None:
    packet_path = tmp_path / "invalid-utf8.json"
    packet_path.write_bytes(b"{\xff}\n")

    assert_cli_failure(
        run_tool(packet_path=packet_path),
        "invalid UTF-8",
        expected_returncode=2,
    )


def test_schema_invalid_packet_skips_semantic_checks(tmp_path: Path) -> None:
    value = packet()
    value["unexpected"] = True
    packet_path = tmp_path / "schema-invalid.json"
    write_packet(packet_path, value)

    result = run_tool(packet_path=packet_path, carrier_path=ARCHIVE)
    assert result.returncode == 1, result.stdout + result.stderr
    diagnostic = parse_json_text(result.stdout)

    assert diagnostic["schema_valid"] is False
    assert diagnostic["ok"] is False
    assert diagnostic["checks"] == {
        "semantic_checks_skipped_due_to_schema_errors": False
    }
    assert any("schema_error" in str(error) for error in diagnostic["errors"])


def test_checked_in_fixture_copied_to_another_path_is_rejected(
    tmp_path: Path,
) -> None:
    packet_path = tmp_path / "copied-example.json"
    packet_path.write_bytes(EXAMPLE.read_bytes())

    result = run_tool(packet_path=packet_path, carrier_path=ARCHIVE)
    diagnostic = assert_cli_failure(result, "fixture_source_path_mismatch")

    assert diagnostic["schema_valid"] is True
    assert diagnostic["checks"]["provenance_branch_ok"] is False


def test_noncanonical_packet_serialization_is_rejected() -> None:
    value = packet()
    noncanonical = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"

    assert_semantic_failure(
        value,
        "canonical_packet_serialization_ok",
        packet_text=noncanonical,
    )


def test_historical_observed_fixture_cannot_claim_example_archive() -> None:
    value = packet()
    value["carrier"]["carrier_kind"] = "example_archive"

    assert_semantic_failure(
        value,
        "provenance_branch_ok",
        expected_fragment="historical_observed_fixture_uses_example_carrier",
    )


def test_observed_producer_branch_accepts_exact_mocked_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_bytes = b"#!/usr/bin/env python3\nprint('producer')\n"
    value = observed_packet(source_bytes)
    assert TOOL_MODULE.schema_errors(_SCHEMA, value) == []

    def fake_git_blob(
        repository_root: Path,
        *,
        revision: str,
        path: str,
    ) -> bytes:
        assert repository_root == ROOT
        assert revision == value["producer"]["producer_source_revision"]
        assert path == value["producer"]["producer_source"]
        return source_bytes

    monkeypatch.setattr(TOOL_MODULE, "_git_blob_bytes", fake_git_blob)
    ok, errors = TOOL_MODULE._verify_provenance(
        value,
        packet_path=EXAMPLE,
        repository_root=ROOT,
    )

    assert ok is True
    assert errors == []


def test_current_run_producer_must_use_subject_run_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_bytes = b"#!/usr/bin/env python3\nprint('current run producer')\n"
    value = observed_packet(
        source_bytes,
        production_mode="current_run_export",
    )

    monkeypatch.setattr(
        TOOL_MODULE,
        "_git_blob_bytes",
        lambda *_args, **_kwargs: source_bytes,
    )

    ok, errors = TOOL_MODULE._verify_provenance(
        value,
        packet_path=EXAMPLE,
        repository_root=ROOT,
    )
    assert ok is True
    assert errors == []

    value["producer"]["producer_run_key"] = "OTHER_RUN"
    ok, errors = TOOL_MODULE._verify_provenance(
        value,
        packet_path=EXAMPLE,
        repository_root=ROOT,
    )
    assert ok is False
    assert "current_run_producer_run_key_mismatch" in errors


# ---------------------------------------------------------------------------
# Carrier and nested archive graph
# ---------------------------------------------------------------------------


def test_carrier_digest_mismatch_is_rejected(tmp_path: Path) -> None:
    corrupt = tmp_path / "corrupt-carrier.zip"
    corrupt.write_bytes(ARCHIVE.read_bytes() + b"corruption")

    assert_semantic_failure(
        packet(),
        "carrier_binding_ok",
        expected_fragment="carrier_digest_mismatch",
        carrier_path=corrupt,
    )


def test_missing_carrier_returns_operational_error(tmp_path: Path) -> None:
    missing = tmp_path / "missing-carrier.zip"
    assert_cli_failure(
        run_tool(carrier_path=missing),
        "carrier_read_error",
        expected_returncode=2,
    )


def test_symlink_carrier_is_rejected(tmp_path: Path) -> None:
    carrier_link = tmp_path / "carrier-link.zip"
    try:
        carrier_link.symlink_to(ARCHIVE)
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")

    assert_cli_failure(
        run_tool(carrier_path=carrier_link),
        "carrier_symlink_rejected",
        expected_returncode=2,
    )


def test_safe_undeclared_member_is_valid_under_explicit_partial_coverage(
    tmp_path: Path,
) -> None:
    variant = archive_with_extra_member(
        tmp_path,
        name="pulse-ci-6066-preservation-v0/UNDECLARED_SAFE_MEMBER.txt",
    )
    value = packet()
    update_carrier_identity(value, variant)
    value["coverage"]["artifact_graph_complete"] = False
    value["coverage"]["coverage_status"] = "partial"

    diagnostic = assert_semantic_success(value, carrier_path=variant)
    assert diagnostic["checks"]["artifact_graph_ok"] is True
    assert diagnostic["checks"]["coverage_reconstruction_ok"] is True


def test_safe_undeclared_member_cannot_claim_complete_coverage(
    tmp_path: Path,
) -> None:
    variant = archive_with_extra_member(
        tmp_path,
        name="pulse-ci-6066-preservation-v0/UNDECLARED_SAFE_MEMBER.txt",
    )
    value = packet()
    update_carrier_identity(value, variant)

    diagnostic = assert_semantic_failure(
        value,
        "coverage_reconstruction_ok",
        expected_fragment="artifact_graph_complete",
        carrier_path=variant,
    )
    assert diagnostic["checks"]["artifact_graph_ok"] is True


def test_unsafe_zip_member_is_rejected(tmp_path: Path) -> None:
    variant = archive_with_extra_member(
        tmp_path,
        name="../escape.txt",
    )
    value = packet()
    update_carrier_identity(value, variant)

    assert_semantic_failure(
        value,
        "artifact_graph_ok",
        expected_fragment="unsafe_zip_member",
        carrier_path=variant,
    )


def test_duplicate_zip_member_is_rejected(tmp_path: Path) -> None:
    variant = archive_with_duplicate_member(tmp_path)
    value = packet()
    update_carrier_identity(value, variant)

    assert_semantic_failure(
        value,
        "artifact_graph_ok",
        expected_fragment="duplicate_zip_member",
        carrier_path=variant,
    )


def test_zip_symlink_member_is_rejected(tmp_path: Path) -> None:
    variant = archive_with_symlink_member(tmp_path)
    value = packet()
    update_carrier_identity(value, variant)

    assert_semantic_failure(
        value,
        "artifact_graph_ok",
        expected_fragment="symlink_zip_member",
        carrier_path=variant,
    )


def test_artifact_container_cycle_is_rejected() -> None:
    value = packet()
    target = artifact_by_role(value, "artifact_binding")
    target["container_artifact_id"] = target["artifact_id"]

    assert_semantic_failure(
        value,
        "artifact_graph_ok",
        expected_fragment="container_cycle",
    )


def test_duplicate_artifact_identifier_is_rejected() -> None:
    value = packet()
    value["artifacts"].append(copy.deepcopy(value["artifacts"][0]))

    assert_semantic_failure(
        value,
        "artifact_graph_ok",
        expected_fragment="artifact_identifier_duplicate",
    )


# ---------------------------------------------------------------------------
# Authority, provider, role, inventory, and coverage reconstruction
# ---------------------------------------------------------------------------


def test_authority_source_digest_drift_is_rejected() -> None:
    value = packet()
    value["authority_sources"]["policy"]["sha256"] = "0" * 64

    assert_semantic_failure(
        value,
        "authority_source_bindings_ok",
        expected_fragment="source_digest_mismatch",
    )


def test_package_child_digest_drift_fails_graph_and_inventory_replay() -> None:
    value = packet()
    target = artifact_by_role(value, "artifact_binding")
    target["sha256"] = "0" * 64

    diagnostic = assert_semantic_failure(
        value,
        "artifact_graph_ok",
        expected_fragment="artifact_digest_mismatch",
    )
    assert diagnostic["checks"]["package_inventory_ok"] is False
    assert any(
        "package_inventory_entry_mismatch" in str(error)
        for error in diagnostic["errors"]
    )


def test_preservation_member_digest_drift_fails_checksum_replay() -> None:
    value = packet()
    target = artifact_by_role(value, "preservation_readme")
    target["sha256"] = "0" * 64

    diagnostic = assert_semantic_failure(
        value,
        "artifact_graph_ok",
        expected_fragment="artifact_digest_mismatch",
    )
    assert diagnostic["checks"]["preservation_checksums_ok"] is False
    assert any(
        "preservation_checksums_member_set_or_digest_mismatch" in str(error)
        for error in diagnostic["errors"]
    )


def test_provider_digest_binding_drift_is_rejected() -> None:
    value = packet()
    provider = first_provider_artifact(value)["provider_binding"]
    assert isinstance(provider, dict)
    provider["provider_sha256"] = "0" * 64

    assert_semantic_failure(
        value,
        "provider_bindings_ok",
        expected_fragment="provider_digest_binding_mismatch",
    )


def test_preservation_provider_manifest_replays_provider_name() -> None:
    value = packet()
    provider = first_provider_artifact(value)["provider_binding"]
    assert isinstance(provider, dict)
    provider["provider_artifact_name"] += "-drift"

    diagnostic = assert_semantic_failure(
        value,
        "preservation_provider_manifest_ok",
        expected_fragment="preservation_manifest_provider_binding_mismatch",
    )
    assert diagnostic["checks"]["provider_bindings_ok"] is True


def test_role_binding_semantic_mismatch_is_rejected() -> None:
    value = packet()
    value["role_bindings"]["final_status"] = value["role_bindings"][
        "status_baseline"
    ]

    assert_semantic_failure(
        value,
        "role_bindings_ok",
        expected_fragment="role_binding_semantic_mismatch",
    )


def test_subject_digest_binding_drift_is_rejected() -> None:
    value = packet()
    value["subject"]["final_status_sha256"] = "0" * 64

    assert_semantic_failure(
        value,
        "subject_artifact_bindings_ok",
        expected_fragment="subject_final_status_digest_mismatch",
    )


def test_coverage_counter_drift_is_rejected() -> None:
    value = packet()
    value["coverage"]["artifacts_total"] += 1

    assert_semantic_failure(
        value,
        "coverage_reconstruction_ok",
        expected_fragment="coverage_field_mismatch: artifacts_total",
    )


def test_reference_list_order_is_reconstructed_not_trusted() -> None:
    value = packet()
    value["subject"]["active_policy_sets"] = list(
        reversed(value["subject"]["active_policy_sets"])
    )

    diagnostic = assert_semantic_failure(
        value,
        "deterministic_reference_ordering_ok",
    )
    assert diagnostic["checks"]["subject_identity_ok"] is False
    assert any(
        "active_policy_sets_not_sorted_unique" in str(error)
        for error in diagnostic["errors"]
    )


def test_artifact_display_path_is_derived_from_carrier_and_container() -> None:
    value = packet()
    target = artifact_by_member_suffix(
        value,
        "artifacts/status.json",
    )
    target["display_path_or_uri"] += "-drift"

    assert_semantic_failure(
        value,
        "artifact_graph_ok",
        expected_fragment="artifact_display_path_mismatch",
    )


# ---------------------------------------------------------------------------
# Read-only diagnostic output boundary
# ---------------------------------------------------------------------------


def test_output_cannot_overwrite_schema_packet_or_carrier() -> None:
    protected = (SCHEMA, EXAMPLE, ARCHIVE)
    before = snapshot(protected)

    for output in protected:
        diagnostic = assert_cli_failure(
            run_tool(output=output),
            "refusing_to_overwrite_input",
            expected_returncode=2,
        )
        assert diagnostic["schema_valid"] is False

    assert snapshot(protected) == before


def test_output_cannot_create_authority_or_contract_surface(
    tmp_path: Path,
) -> None:
    for name in (
        "status.json",
        "release_decision_v0.json",
        "release_authority_v0.json",
        "pulsemech_compute_subject_input_packet_v0.json",
    ):
        output = tmp_path / name
        assert_cli_failure(
            run_tool(output=output),
            "refusing_authority_or_contract_surface_output",
            expected_returncode=2,
        )
        assert not output.exists()


def test_symlink_output_path_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    target.write_text("unchanged\n", encoding="utf-8")
    output = tmp_path / "diagnostic-link.json"
    try:
        output.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")

    before = target.read_bytes()
    assert_cli_failure(
        run_tool(output=output),
        "output_symlink_rejected",
        expected_returncode=2,
    )
    assert target.read_bytes() == before


def test_protected_input_snapshot_detects_mutation(tmp_path: Path) -> None:
    schema_copy = tmp_path / "schema.json"
    packet_copy = tmp_path / "packet.json"
    carrier_copy = tmp_path / "carrier.zip"
    schema_copy.write_bytes(SCHEMA.read_bytes())
    packet_copy.write_bytes(EXAMPLE.read_bytes())
    carrier_copy.write_bytes(ARCHIVE.read_bytes())

    snapshots = (
        sha256_file(schema_copy),
        sha256_file(packet_copy),
        sha256_file(carrier_copy),
    )
    assert TOOL_MODULE._inputs_unchanged(
        schema_path=schema_copy,
        packet_path=packet_copy,
        carrier_path=carrier_copy,
        snapshots=snapshots,
    )

    packet_copy.write_bytes(packet_copy.read_bytes() + b" ")
    assert not TOOL_MODULE._inputs_unchanged(
        schema_path=schema_copy,
        packet_path=packet_copy,
        carrier_path=carrier_copy,
        snapshots=snapshots,
    )

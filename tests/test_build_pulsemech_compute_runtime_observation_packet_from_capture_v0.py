#!/usr/bin/env python3
"""Permanent Step 4B regressions using exact historical data and local fixtures.

The four required Git snapshots must be present. Temporary candidate commits
and construction records are test fixtures only, never upstream identity or
an observed production construction. No network or original repository write
is used; local fixture commits exist only under pytest temporary paths.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
PRODUCER = "tools/build_pulsemech_compute_runtime_observation_packet_from_capture_v0.py"
VALIDATOR = "tools/check_pulsemech_compute_runtime_observation_packet_v0.py"
SCHEMA = "schemas/pulsemech_compute_runtime_observation_packet_v0.schema.json"
CAPTURE = "preservation/pulse_ci_6066/post_run_producer_input_capture_v0"
CONTEXT = "examples/compute/pulsemech_compute_subject_input_packet_6066_observed_v0.json"
CARRIER = "PULSE_CI_6066_release_grade_artifact_preservation_v0.zip"
SIX_PATHS = (
    PRODUCER,
    "tests/test_build_pulsemech_compute_runtime_observation_packet_from_capture_v0.py",
    VALIDATOR,
    "tests/test_check_pulsemech_compute_runtime_observation_packet_v0.py",
    "ci/tools-tests.list",
    "CHANGELOG.md",
)
HISTORY = (
    "22d14088ae21f84d94c6a6951c0f70ab1bdf0895",
    "3cd57dc9e88e6f804dbb134c864f4207688bddc2",
    "46b639706e23f80fe296a8893be18e2b5ab21f7e",
)
SUBJECT_KEY = "GITHUB_RUN_ID=29249887581|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()


def git(repo: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    command = ["/usr/bin/git", "--no-replace-objects", "-c", "core.fsmonitor=false",
               "-c", "protocol.allow=never", "-c", f"safe.directory={repo}", "-C", str(repo), *args]
    env = {"PATH": "/usr/bin:/bin", "HOME": str(repo), "LC_ALL": "C", "GIT_NO_LAZY_FETCH": "1",
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_OPTIONAL_LOCKS": "0"}
    result = subprocess.run(command, input=input_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env=env, timeout=120, check=False)
    assert result.returncode == 0, (command, result.stderr.decode(errors="replace"))
    return result.stdout


def restore_snapshots(source: Path, target: Path, revisions: tuple[str, ...]) -> None:
    """Transport original file-tree objects only; do not traverse ancestry."""
    target.mkdir()
    git(target, "init", "--template=")
    ids = set(revisions)
    for revision in revisions:
        assert git(source, "cat-file", "-t", revision).strip() == b"commit"
        ids.add(git(source, "rev-parse", revision + "^{tree}").decode().strip())
        for row in git(source, "ls-tree", "-r", "-t", "-z", revision).split(b"\0"):
            if row:
                mode, kind, oid = row.split(b"\t", 1)[0].split()
                assert kind in (b"tree", b"blob"), (mode, kind)
                ids.add(oid.decode())
    pack = git(source, "pack-objects", "--stdout", input_bytes=("\n".join(sorted(ids)) + "\n").encode())
    git(target, "index-pack", "--stdin", input_bytes=pack)
    (target / ".git/shallow").write_text("\n".join(revisions) + "\n")
    git(target, "checkout", "--detach", revisions[0])


def import_producer(repo: Path) -> Any:
    spec = importlib.util.spec_from_file_location("step4b_producer_under_test", repo / PRODUCER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@dataclass
class Candidate:
    repo: Path
    revision: str
    record: dict[str, Any]
    module: Any


@pytest.fixture(scope="session")
def candidate(tmp_path_factory: pytest.TempPathFactory) -> Candidate:
    parent = tmp_path_factory.mktemp("step4b-source-fixture")
    repo = parent / "repo"
    head = git(ROOT, "rev-parse", "HEAD").decode().strip()
    before = {path: (ROOT / path).read_bytes() for path in SIX_PATHS}
    restore_snapshots(ROOT, repo, tuple(dict.fromkeys((head, *HISTORY))))
    for path in SIX_PATHS:
        (repo / path).write_bytes(before[path])
    git(repo, "add", "--", *SIX_PATHS)
    git(repo, "-c", "user.name=PULSEmech temporary regression fixture",
        "-c", "user.email=fixture@example.invalid", "-c", "core.hooksPath=/dev/null",
        "-c", "commit.gpgSign=false", "commit", "--allow-empty", "--no-verify", "-m",
        "Local Step 4B candidate fixture; not an upstream commit")
    revision = git(repo, "rev-parse", "HEAD").decode().strip()
    record = {
        "record_type": "pulsemech_compute_runtime_packet_construction_v0",
        "collection_mode": "post_run_platform_export", "subject_run_key": SUBJECT_KEY,
        "producer_source_revision": revision, "producer_source_sha256": sha((repo / PRODUCER).read_bytes()),
        "runtime_validator_sha256": sha((repo / VALIDATOR).read_bytes()),
        "capture_manifest_sha256": "4642546646fc7c78f8b65bce40c3db72fb6847c4e3d454db97b164f1fc14f238",
        "subject_context_sha256": "b457383356d330ae40843a47f9adb83c4e7d7f14447218f951ca71e4ee287467",
        "carrier_sha256": "7949bfd00468e6f9347fddaae732bdcebff5527e87ecb379a6c84a47176db966",
        "collector_run_key": "LOCAL_TEST_FIXTURE=step4b|ATTEMPT=1",
        "collector_execution_id": "execution:step4b-regression-collector",
        "collector_workflow_name": "Local regression fixture, not a production construction",
        "collector_job_name": "Historical-input packet test", "collector_attempt": 1,
        "capture_started_utc": "2026-09-06T18:10:00Z", "capture_completed_utc": "2026-09-06T18:10:01Z",
        "packet_created_utc": "2026-09-06T18:10:02Z",
    }
    value = Candidate(repo, revision, record, import_producer(repo))
    yield value
    assert {path: (ROOT / path).read_bytes() for path in SIX_PATHS} == before
    assert git(repo, "diff", "--name-only").strip() == b""
    assert git(repo, "diff", "--cached", "--name-only").strip() == b""


def invoke(candidate: Candidate, tmp_path: Path, *, record: dict[str, Any] | None = None,
           extra: tuple[str, ...] = (), output: Path | None = None,
           environment: dict[str, str] | None = None, isolated: bool = True,
           script_path: Path | None = None) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
    construction = tmp_path / "construction.json"
    construction.write_bytes(encode(candidate.record if record is None else record))
    output = output or tmp_path / "packet.json"
    command = [sys.executable, *(["-I"] if isolated else []), str(script_path or candidate.repo / PRODUCER),
               "--repository-root", str(candidate.repo), "--construction-record", str(construction),
               "--construction-sha256", sha(construction.read_bytes()), "--output", str(output), *extra]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            env=environment, timeout=90, check=False, cwd=tmp_path)
    return result, output, construction


def failed(result: subprocess.CompletedProcess[str], output: Path, code: str | None = None) -> dict[str, Any]:
    assert result.returncode == 2, result.stdout + result.stderr
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    diagnostic = json.loads(result.stderr)
    assert diagnostic["ok"] is False and diagnostic["authority_effect"] == "none"
    if code is not None:
        assert diagnostic["error_code"] == code, diagnostic
    assert not output.exists()
    return diagnostic


@pytest.fixture(scope="session")
def produced(candidate: Candidate, tmp_path_factory: pytest.TempPathFactory) -> tuple[dict[str, Any], bytes]:
    folder = tmp_path_factory.mktemp("step4b-positive")
    result, output, _ = invoke(candidate, folder)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    data = output.read_bytes()
    assert json.loads(result.stdout)["packet_sha256"] == sha(data)
    checked = subprocess.run([sys.executable, "-I", str(candidate.repo / VALIDATOR), "--packet", str(output)],
                             capture_output=True, text=True, timeout=60, check=False)
    assert checked.returncode == 0, checked.stdout + checked.stderr
    assert json.loads(checked.stdout)["ok"] is True
    return json.loads(data), data


def test_real_historical_capture_constructs_and_independent_cli_validates(produced: tuple[dict[str, Any], bytes]) -> None:
    packet, data = produced
    assert encode(packet) == data
    assert packet["record_status"] == "observed"
    assert packet["coverage"]["coverage_status"] == "partial"
    assert packet["observation_boundary"]["observer_in_subject_totals"] is False
    assert packet["observation_boundary"]["subject_artifacts_mutated"] is False


def test_repeated_construction_has_identical_bytes(candidate: Candidate, produced: tuple[dict[str, Any], bytes], tmp_path: Path) -> None:
    result, output, _ = invoke(candidate, tmp_path)
    assert result.returncode == 0, result.stderr
    assert output.read_bytes() == produced[1]
    assert json.loads(result.stdout)["packet_bytes"] == len(produced[1])


def test_ambient_environment_and_output_path_do_not_change_packet(candidate: Candidate, produced: tuple[dict[str, Any], bytes], tmp_path: Path) -> None:
    env = dict(os.environ)
    env.update(PYTHONPATH=str(tmp_path), GIT_DIR=str(tmp_path / "not-a-repository"),
               GIT_WORK_TREE=str(tmp_path), GIT_CONFIG_COUNT="999", TZ="Pacific/Honolulu", PATH=str(tmp_path))
    result, output, _ = invoke(candidate, tmp_path, environment=env, output=tmp_path / "different-name.json")
    assert result.returncode == 0, result.stderr
    assert output.read_bytes() == produced[1]


def test_complete_historical_job_step_inventory_and_parents(candidate: Candidate, produced: tuple[dict[str, Any], bytes]) -> None:
    packet, _ = produced
    raw = json.loads((candidate.repo / CAPTURE / "raw/jobs_page_0001_response.json").read_bytes())
    jobs = {r["job_id"]: r for r in packet["executions"] if r["execution_kind"] == "workflow_job"}
    steps = [r for r in packet["executions"] if r["execution_kind"] == "workflow_step"]
    assert len(jobs) == 8 and len(steps) == 171 and len(packet["executions"]) == 180
    assert set(jobs) == {r["id"] for r in raw["jobs"]}
    for source in raw["jobs"]:
        actual = jobs[source["id"]]
        assert actual["result"]["lifecycle_status"] == source["status"]
        assert actual["result"]["outcome"] == source["conclusion"]
        children = {r["step_number"]: r for r in steps if r["job_id"] == source["id"]}
        assert set(children) == {r["number"] for r in source.get("steps", [])}
        for raw_step in source.get("steps", []):
            step = children[raw_step["number"]]
            assert step["parent_execution_id"] == actual["execution_id"]
            assert step["step_name"] == raw_step["name"]
            assert step["result"]["outcome"] == raw_step["conclusion"]
            assert step["timing"]["started_utc"] == raw_step.get("started_at")
            assert step["timing"]["completed_utc"] == raw_step.get("completed_at")


def test_no_invented_commands_exit_codes_calls_or_resources(produced: tuple[dict[str, Any], bytes]) -> None:
    packet, _ = produced
    assert packet["external_calls"] == packet["model_inferences"] == packet["resource_measurements"] == []
    assert packet["coverage"]["external_call_capture_status"] == "none"
    assert packet["coverage"]["model_inference_capture_status"] == "none"
    assert packet["coverage"]["resource_axes_observed"] == []
    assert len(packet["coverage"]["resource_axes_unavailable"]) == 15
    assert "step_not_instrumented" in packet["coverage"]["unobserved_reasons"]
    for row in packet["executions"]:
        assert row["result"]["exit_code"] is None
        assert row["command_identity"]["command_sha256"] is None
        assert row["command_identity"]["arguments_sha256"] is None
        if row["execution_scope"] == "subject":
            assert row["input_state_ids"] == row["output_state_ids"] == []
            assert row["permitted_mutation_authority"] == "none"
            assert row["declared_role"] == "unknown"
    assert any(row["result"]["outcome"] == "skipped" for row in packet["executions"])


def test_historical_policy_order_and_exact_source_bindings(candidate: Candidate, produced: tuple[dict[str, Any], bytes]) -> None:
    packet, _ = produced
    context = json.loads((candidate.repo / CONTEXT).read_bytes())
    assert packet["subject"]["active_policy_sets"] == ["required", "release_required"]
    for key, binding in packet["authority_inputs"].items():
        assert binding["sha256"] == context["authority_sources"][key]["sha256"]
        assert binding["source_commit"] == HISTORY[2]
    states = {r["state_id"]: r for r in packet["state_observations"]}
    for source in (candidate.repo / CAPTURE).rglob("*.json"):
        relative = source.relative_to(candidate.repo / CAPTURE).as_posix()
        assert states["state:capture/" + relative]["sha256"] == sha(source.read_bytes())
    assert states["state:subject-context"]["sha256"] == sha((candidate.repo / CONTEXT).read_bytes())
    assert states["state:subject-carrier"]["sha256"] == sha((candidate.repo / CARRIER).read_bytes())
    assert states["state:construction-record"]["sha256"] == sha(encode(candidate.record))


def test_packet_keeps_historical_acquisition_and_construction_distinct(candidate: Candidate, produced: tuple[dict[str, Any], bytes]) -> None:
    packet, _ = produced
    collector = next(r for r in packet["executions"] if r["execution_scope"] == "observation_collector")
    assert collector["run_binding"]["execution_run_key"] == candidate.record["collector_run_key"]
    assert collector["run_binding"]["execution_run_key"] != SUBJECT_KEY
    assert collector["source_identity"]["source_revision"] == candidate.revision
    assert packet["observation_boundary"]["capture_started_utc"].startswith("2026-09-06")
    assert all(r["timing"]["started_utc"].startswith("2026-07-13") for r in packet["executions"]
               if r["execution_scope"] == "subject" and r["timing"]["started_utc"] is not None)


@pytest.mark.parametrize("field,value,code", [
    ("collector_attempt", True, "collector_attempt_invalid"),
    ("collector_attempt", 0, "collector_attempt_invalid"),
    ("collector_run_key", SUBJECT_KEY, "collector_must_be_separate_from_subject"),
    ("collector_job_name", "bad\nvalue", "construction_collector_identity_invalid"),
    ("collector_execution_id", "call:wrong-kind", "collector_execution_id_invalid"),
    ("producer_source_revision", "HEAD", "construction_source_revision_invalid"),
    ("producer_source_revision", "0" * 40, "packet_source_committed_bytes_unavailable"),
    ("producer_source_sha256", "f" * 64, "producer_source_digest_mismatch"),
    ("runtime_validator_sha256", "f" * 64, "runtime_validator_digest_mismatch"),
    ("capture_manifest_sha256", "f" * 64, "construction_input_binding_mismatch"),
    ("subject_context_sha256", "f" * 64, "construction_input_binding_mismatch"),
    ("carrier_sha256", "f" * 64, "construction_input_binding_mismatch"),
    ("collection_mode", "in_run_observer", "construction_input_binding_mismatch"),
    ("capture_started_utc", "2026-07-01T00:00:00Z", "subject_acquisition_construction_order_invalid"),
    ("capture_completed_utc", "2026-09-06T18:09:00Z", "construction_time_order_invalid"),
    ("packet_created_utc", "2026-09-06T18:09:00Z", "construction_time_order_invalid"),
    ("packet_created_utc", "2026-09-06T24:00:00Z", "invalid_utc_timestamp"),
    ("packet_created_utc", "2026-02-29T18:10:02Z", "invalid_calendar_timestamp"),
])
def test_rebound_construction_constraints_fail_closed(candidate: Candidate, tmp_path: Path, field: str, value: Any, code: str) -> None:
    record = dict(candidate.record)
    record[field] = value
    result, output, _ = invoke(candidate, tmp_path, record=record)
    failed(result, output, code)


@pytest.mark.parametrize("change", ["missing", "extra"])
def test_exact_construction_field_set(candidate: Candidate, tmp_path: Path, change: str) -> None:
    record = dict(candidate.record)
    if change == "missing":
        del record["collector_attempt"]
    else:
        record["active_gate_eligible"] = True
    result, output, _ = invoke(candidate, tmp_path, record=record)
    failed(result, output, "construction_field_set_mismatch")


def test_external_construction_digest_is_required(candidate: Candidate, tmp_path: Path) -> None:
    result, output, _ = invoke(candidate, tmp_path, extra=("--construction-sha256", "0" * 64))
    failed(result, output, "construction_digest_mismatch")


@pytest.mark.parametrize("change", ["duplicate", "bom", "crlf", "trailing_lf", "nan"])
def test_construction_strict_json(candidate: Candidate, tmp_path: Path, change: str) -> None:
    data = encode(candidate.record)
    if change == "duplicate":
        data = data.replace(b'{\n', b'{\n  "collector_attempt": 1,\n', 1)
    elif change == "bom":
        data = b"\xef\xbb\xbf" + data
    elif change == "crlf":
        data = data.replace(b"\n", b"\r\n")
    elif change == "trailing_lf":
        data += b"\n"
    else:
        data = data.replace(b'"collector_attempt": 1', b'"collector_attempt": NaN')
    record_file = tmp_path / "bad-construction.json"
    record_file.write_bytes(data)
    result, output, _ = invoke(candidate, tmp_path, extra=("--construction-record", str(record_file), "--construction-sha256", sha(data)))
    failed(result, output)


@pytest.mark.parametrize("name", ["raw/run_attempt_response.json", "raw/jobs_page_0001_response.json"])
@pytest.mark.parametrize("change", ["append", "same_size"])
def test_changed_capture_bytes_rejected(candidate: Candidate, tmp_path: Path, name: str, change: str) -> None:
    root = tmp_path / "capture"
    shutil.copytree(candidate.repo / CAPTURE, root)
    file = root / name
    original = file.read_bytes()
    file.write_bytes(original + b"\n" if change == "append" else original.replace(b'"id":', b'"Id":', 1))
    assert file.read_bytes() != original
    result, output, _ = invoke(candidate, tmp_path, extra=("--capture-root", str(root)))
    failed(result, output, "input_size_mismatch" if change == "append" else "raw_response_identity_mismatch")


@pytest.mark.parametrize("change", ["missing", "extra", "symlink"])
def test_capture_inventory_and_file_type_rejection(candidate: Candidate, tmp_path: Path, change: str) -> None:
    root = tmp_path / "capture"
    shutil.copytree(candidate.repo / CAPTURE, root)
    file = root / "raw/jobs_page_0001_response.json"
    if change == "missing":
        file.unlink()
    elif change == "extra":
        (root / "extra.json").write_bytes(b"{}")
    else:
        data = file.read_bytes()
        file.unlink()
        target = tmp_path / "real.json"
        target.write_bytes(data)
        file.symlink_to(target)
    result, output, _ = invoke(candidate, tmp_path, extra=("--capture-root", str(root)))
    failed(result, output)


@pytest.mark.parametrize("kind", ["carrier", "subject-context"])
def test_exact_context_and_carrier_bytes_required(candidate: Candidate, tmp_path: Path, kind: str) -> None:
    original = (candidate.repo / (CARRIER if kind == "carrier" else CONTEXT)).read_bytes()
    other = tmp_path / ("other.zip" if kind == "carrier" else "other.json")
    other.write_bytes(bytes([original[0] ^ 1]) + original[1:])
    result, output, _ = invoke(candidate, tmp_path, extra=("--" + kind, str(other)))
    failed(result, output, "input_digest_mismatch")


def test_reordered_historical_policy_context_is_not_silently_repaired(candidate: Candidate, tmp_path: Path) -> None:
    context = json.loads((candidate.repo / CONTEXT).read_bytes())
    context["subject"]["active_policy_sets"].reverse()
    path = tmp_path / "reordered-context.json"
    path.write_bytes(encode(context))
    result, output, _ = invoke(candidate, tmp_path, extra=("--subject-context", str(path)))
    failed(result, output, "input_digest_mismatch")


def test_missing_history_cannot_use_current_worktree(candidate: Candidate, tmp_path: Path) -> None:
    missing = tmp_path / "missing-history"
    restore_snapshots(candidate.repo, missing, (candidate.revision,))
    isolated = Candidate(missing, candidate.revision, candidate.record, None)
    result, output, _ = invoke(isolated, tmp_path)
    failed(result, output, "packet_source_committed_bytes_unavailable")


def test_tree_identity_cannot_impersonate_producer_commit(candidate: Candidate, tmp_path: Path) -> None:
    record = dict(candidate.record)
    record["producer_source_revision"] = git(candidate.repo, "rev-parse", candidate.revision + "^{tree}").decode().strip()
    result, output, _ = invoke(candidate, tmp_path, record=record)
    failed(result, output, "packet_source_revision_not_commit")


def test_isolated_cli_required(candidate: Candidate, tmp_path: Path) -> None:
    result, output, _ = invoke(candidate, tmp_path, isolated=False)
    failed(result, output, "isolated_python_required")



@pytest.mark.parametrize("kind", ["copy", "modified_copy", "symlink", "outside_copy"])
def test_invoked_source_alias_cannot_claim_canonical_identity(
    candidate: Candidate, tmp_path: Path, kind: str,
) -> None:
    source = candidate.repo / PRODUCER
    original = source.read_bytes()
    if kind == "outside_copy":
        alias = tmp_path / "tools" / source.name
        alias.parent.mkdir()
        expected = "executed_source_repository_mismatch"
    else:
        alias = source.with_name("step4b-invocation-alias.py")
        expected = "executed_source_path_mismatch"
    assert not alias.exists() and not alias.is_symlink()
    try:
        if kind == "symlink":
            alias.symlink_to(source)
        elif kind == "modified_copy":
            marker = b'TOOL_VERSION = "0.1.0"'
            assert original.count(marker) == 1
            alias.write_bytes(original.replace(marker, b'TOOL_VERSION = "0.1.1"'))
        else:
            alias.write_bytes(original)
        result, output, _ = invoke(candidate, tmp_path, script_path=alias)
        diagnostic = failed(result, output, expected)
        assert diagnostic["stage"] == "source"
        assert not list(tmp_path.glob(".pulse-runtime-*"))
        assert source.read_bytes() == original
    finally:
        alias.unlink(missing_ok=True)


def test_rebinding_construction_digest_does_not_authorize_renamed_copy(
    candidate: Candidate, tmp_path: Path,
) -> None:
    source = candidate.repo / PRODUCER
    alias = source.with_name("step4b-rebound-alias.py")
    original = source.read_bytes()
    changed = original.replace(b'TOOL_VERSION = "0.1.0"', b'TOOL_VERSION = "0.1.1"')
    assert changed != original
    assert not alias.exists()
    try:
        alias.write_bytes(changed)
        record = dict(candidate.record, producer_source_sha256=sha(changed))
        result, output, _ = invoke(candidate, tmp_path, record=record, script_path=alias)
        failed(result, output, "executed_source_path_mismatch")
        assert source.read_bytes() == original
    finally:
        alias.unlink(missing_ok=True)


@pytest.mark.parametrize("repair_digest", [False, True])
def test_modified_canonical_source_must_match_record_and_committed_bytes(
    candidate: Candidate, tmp_path: Path, repair_digest: bool,
) -> None:
    source = candidate.repo / PRODUCER
    original = source.read_bytes()
    changed = original.replace(b'TOOL_VERSION = "0.1.0"', b'TOOL_VERSION = "0.1.1"')
    assert changed != original
    record = dict(candidate.record)
    if repair_digest:
        record["producer_source_sha256"] = sha(changed)
    try:
        source.write_bytes(changed)
        result, output, _ = invoke(candidate, tmp_path, record=record)
        failed(result, output, "executed_source_not_committed_identity" if repair_digest
               else "producer_source_digest_mismatch")
        assert not list(tmp_path.glob(".pulse-runtime-*"))
    finally:
        source.write_bytes(original)


def test_imported_renamed_copy_is_rejected_by_build_not_only_cli(
    candidate: Candidate, tmp_path: Path,
) -> None:
    source = candidate.repo / PRODUCER
    alias = source.with_name("step4b-import-alias.py")
    name = "step4b_renamed_source_under_test"
    original = source.read_bytes()
    assert not alias.exists()
    try:
        alias.write_bytes(original)
        spec = importlib.util.spec_from_file_location(name, alias)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        record_file = tmp_path / "construction.json"
        record_file.write_bytes(encode(candidate.record))
        output = tmp_path / "packet.json"
        with pytest.raises(module.ProducerError, match="executed_source_path_mismatch"):
            module.build(repository_root=candidate.repo, capture_root=candidate.repo / CAPTURE,
                         subject_context=candidate.repo / CONTEXT, carrier=candidate.repo / CARRIER,
                         construction_record=record_file, construction_sha256=sha(record_file.read_bytes()),
                         output=output)
        assert not output.exists()
        assert not list(tmp_path.glob(".pulse-runtime-*"))
        assert source.read_bytes() == original
    finally:
        sys.modules.pop(name, None)
        alias.unlink(missing_ok=True)


@pytest.mark.parametrize("point", ["before_link", "after_link"])
def test_executed_source_snapshot_remains_protected_through_publication(
    candidate: Candidate, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, point: str,
) -> None:
    module = candidate.module
    source = candidate.repo / PRODUCER
    before = source.read_bytes()
    changed = before.replace(b'TOOL_VERSION = "0.1.0"', b'TOOL_VERSION = "0.1.1"')
    assert changed != before and len(changed) == len(before)
    record_file = tmp_path / "construction.json"
    record_file.write_bytes(encode(candidate.record))
    output = tmp_path / "packet.json"
    publish = module.publish_no_replace

    def injecting_publish(path: Path, payload: bytes, *, repository: Path, recheck: Any) -> None:
        calls = 0

        def changed_recheck() -> None:
            nonlocal calls
            calls += 1
            if calls == (1 if point == "before_link" else 2):
                source.write_bytes(changed)
            recheck()

        publish(path, payload, repository=repository, recheck=changed_recheck)

    monkeypatch.setattr(module, "publish_no_replace", injecting_publish)
    try:
        with pytest.raises(module.ProducerError, match="protected_input_changed"):
            module.build(repository_root=candidate.repo, capture_root=candidate.repo / CAPTURE,
                         subject_context=candidate.repo / CONTEXT, carrier=candidate.repo / CARRIER,
                         construction_record=record_file, construction_sha256=sha(record_file.read_bytes()),
                         output=output)
        assert not output.exists()
        assert not list(tmp_path.glob(".pulse-runtime-*"))
    finally:
        source.write_bytes(before)


def test_new_regression_registered_exactly_once(candidate: Candidate) -> None:
    entries = [line.strip() for line in (candidate.repo / "ci/tools-tests.list").read_text().splitlines()
               if line.strip() and not line.lstrip().startswith("#")]
    assert entries.count(SIX_PATHS[1]) == 1
    assert entries.count(SIX_PATHS[3]) == 1
    assert len(entries) == len(set(entries))


def test_existing_output_and_contents_are_preserved(candidate: Candidate, tmp_path: Path) -> None:
    output = tmp_path / "existing.json"
    output.write_bytes(b"unrelated existing data\n")
    before = output.read_bytes()
    result, _, _ = invoke(candidate, tmp_path, output=output)
    assert result.returncode == 2, result.stdout
    assert json.loads(result.stderr)["error_code"] == "output_already_exists"
    assert output.read_bytes() == before
    assert not list(tmp_path.glob(".pulse-runtime-*"))


@pytest.mark.parametrize("name", ["status.json", "release_decision_v0.json", "release_authority_v0.json"])
def test_authority_output_names_rejected(candidate: Candidate, tmp_path: Path, name: str) -> None:
    result, output, _ = invoke(candidate, tmp_path, output=tmp_path / name)
    failed(result, output, "authority_or_non_json_output_forbidden")


def test_repository_output_rejected(candidate: Candidate, tmp_path: Path) -> None:
    output = candidate.repo / "should-not-exist.json"
    result, _, _ = invoke(candidate, tmp_path, output=output)
    failed(result, output, "output_inside_repository_forbidden")


def test_changed_runtime_checker_is_not_executed(candidate: Candidate, tmp_path: Path) -> None:
    file = candidate.repo / VALIDATOR
    before = file.read_bytes()
    try:
        file.write_bytes(before + b"\nraise RuntimeError('untrusted replacement')\n")
        result, output, _ = invoke(candidate, tmp_path)
        failed(result, output, "input_size_mismatch")
    finally:
        file.write_bytes(before)


@pytest.mark.parametrize("point", ["before_link", "after_link"])
def test_real_build_rechecks_inputs_and_rolls_back_owned_output(candidate: Candidate, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, point: str) -> None:
    module = candidate.module
    record_file = tmp_path / "construction.json"
    record_file.write_bytes(encode(candidate.record))
    output = tmp_path / "packet.json"
    original = module.publish_no_replace

    def injecting_publish(path: Path, payload: bytes, *, repository: Path, recheck: Any) -> None:
        calls = 0

        def changed_recheck() -> None:
            nonlocal calls
            calls += 1
            if calls == (1 if point == "before_link" else 2):
                record_file.write_bytes(record_file.read_bytes() + b"\n")
            recheck()

        original(path, payload, repository=repository, recheck=changed_recheck)

    monkeypatch.setattr(module, "publish_no_replace", injecting_publish)
    with pytest.raises(module.ProducerError):
        module.build(repository_root=candidate.repo, capture_root=candidate.repo / CAPTURE,
                     subject_context=candidate.repo / CONTEXT, carrier=candidate.repo / CARRIER,
                     construction_record=record_file, construction_sha256=sha(record_file.read_bytes()), output=output)
    assert not output.exists()
    assert not list(tmp_path.glob(".pulse-runtime-*"))


def test_interruption_after_successful_link_removes_only_owned_file(candidate: Candidate, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = candidate.module
    output = tmp_path / "packet.json"
    unrelated = tmp_path / "unrelated.json"
    unrelated.write_bytes(b"retain")
    original = os.link

    def interrupted(*args: Any, **kwargs: Any) -> None:
        original(*args, **kwargs)
        raise KeyboardInterrupt("injected after successful link")

    monkeypatch.setattr(module.os, "link", interrupted)
    with pytest.raises(KeyboardInterrupt):
        module.publish_no_replace(output, b"{}\n", repository=candidate.repo, recheck=lambda: None)
    assert not output.exists()
    assert unrelated.read_bytes() == b"retain"
    assert not list(tmp_path.glob(".pulse-runtime-*"))


def test_replaced_output_is_not_deleted_during_rollback(candidate: Candidate, tmp_path: Path) -> None:
    module = candidate.module
    output = tmp_path / "packet.json"
    calls = 0

    def recheck() -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            output.unlink()
            output.write_bytes(b"foreign replacement")

    with pytest.raises(module.ProducerError, match="output_replaced_after_recheck"):
        module.publish_no_replace(output, b"{}\n", repository=candidate.repo, recheck=recheck)
    assert output.read_bytes() == b"foreign replacement"
    assert not list(tmp_path.glob(".pulse-runtime-*"))


def test_in_place_output_change_after_recheck_is_detected(candidate: Candidate, tmp_path: Path) -> None:
    module = candidate.module
    output = tmp_path / "packet.json"
    calls = 0

    def recheck() -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            output.write_bytes(b"[]\n")

    with pytest.raises(module.ProducerError, match="output_changed_after_recheck"):
        module.publish_no_replace(output, b"{}\n", repository=candidate.repo, recheck=recheck)
    assert not output.exists()
    assert not list(tmp_path.glob(".pulse-runtime-*"))


def test_symlink_parent_and_existing_symlink_output_rejected(candidate: Candidate, tmp_path: Path) -> None:
    module = candidate.module
    real = tmp_path / "real"
    real.mkdir()
    parent = tmp_path / "linked"
    parent.symlink_to(real, target_is_directory=True)
    with pytest.raises(OSError):
        module.publish_no_replace(parent / "packet.json", b"{}\n", repository=candidate.repo, recheck=lambda: None)
    output = tmp_path / "packet.json"
    output.symlink_to(real / "not-created.json")
    with pytest.raises(module.ProducerError, match="output_already_exists"):
        module.publish_no_replace(output, b"{}\n", repository=candidate.repo, recheck=lambda: None)
    assert output.is_symlink()
    assert not list(real.iterdir())


def test_relocated_output_parent_cleanup_uses_held_descriptor(candidate: Candidate, tmp_path: Path) -> None:
    module = candidate.module
    parent, relocated, foreign = (tmp_path / name for name in ("parent", "relocated", "foreign"))
    parent.mkdir()
    foreign.mkdir()
    (foreign / "packet.json").write_bytes(b"foreign")
    calls = 0

    def recheck() -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            parent.rename(relocated)
            parent.symlink_to(foreign, target_is_directory=True)

    with pytest.raises(OSError):
        module.publish_no_replace(parent / "packet.json", b"{}\n", repository=candidate.repo, recheck=recheck)
    assert not list(relocated.iterdir())
    assert (foreign / "packet.json").read_bytes() == b"foreign"


@pytest.mark.parametrize("kind,check", [
    ("parent", "workflow_job_step_shape_ok"), ("run", "subject_execution_run_binding_ok"),
    ("coverage", "coverage_status_semantics_ok"), ("resource", "resource_axis_coverage_partition_ok"),
])
def test_independent_validator_rejects_rebound_output_relation_changes(candidate: Candidate, produced: tuple[dict[str, Any], bytes], tmp_path: Path, kind: str, check: str) -> None:
    packet = json.loads(produced[1])
    step = next(r for r in packet["executions"] if r["execution_kind"] == "workflow_step")
    if kind == "parent":
        step["job_id"] += 1
    elif kind == "run":
        step["run_binding"]["execution_run_key"] = "WRONG_RUN"
    elif kind == "coverage":
        packet["coverage"]["coverage_status"] = "complete"
        packet["coverage"]["unobserved_reasons"] = []
    else:
        packet["coverage"]["resource_axes_unavailable"] = []
    file = tmp_path / "mutated.json"
    file.write_bytes(encode(packet))
    result = subprocess.run([sys.executable, "-I", str(candidate.repo / VALIDATOR), "--packet", str(file)],
                            capture_output=True, text=True, check=False, timeout=60)
    assert result.returncode == 1, result.stdout + result.stderr
    diagnostic = json.loads(result.stdout)
    assert diagnostic["schema_valid"] is True
    assert diagnostic["checks"][check] is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

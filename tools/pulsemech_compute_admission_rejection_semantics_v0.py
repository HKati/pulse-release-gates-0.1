#!/usr/bin/env python3
"""Fresh semantic checks for the bounded PULSE CI admission-rejection observer.

Inputs are preserved data. Q2 executes only the reviewed checkout's independent
private-input checker and metric reducers, with a caller-trusted CPython 3.11.16.
LlamaGuard executes the existing content and attestation checkers, never the model
producer's entry point. A saved verdict cannot substitute for either execution.

These are later replays. They do not prove original process reads, installed
runtime closure, generation, gate success, or release authority. The enclosing
observer must separately authenticate and bind the original platform evidence.
"""
from __future__ import annotations

import ast
from contextlib import contextmanager
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
from typing import Any


REPOSITORY = "HKati/pulse-release-gates-0.1"
WORKFLOW = ".github/workflows/pulse_ci.yml"
WORKFLOW_SHA256 = "7489fca657c4b2541da4946237b3f864aae7f9247198e5a3c6cbc3429a32db6a"
POLICY = "pulse_gate_policy_v0.yml"
POLICY_SHA256 = "00fc5eef5fa3f240028aaf636a2e43ba29f1da000484c7a2f1baafcdd3c4ae8c"
PACK = "PULSE_safe_pack_v0/"
EXTERNAL = PACK + "artifacts/external/"
Q2_CHECKER = PACK + "tools/check_q2_release_intake_v0.py"
Q2_SOURCES = (
    PACK + "profiles/q2_reference_release_intake_v0.json",
    "schemas/q2_release_intake_request_v0.schema.json",
    "schemas/q2_release_intake_result_v0.schema.json",
    "schemas/q2_release_subject_capsule_v0.schema.json",
    PACK + "profiles/q2_reference_subject_v0.json",
    PACK + "profiles/q2_reference_model_files_v0.json",
    PACK + "examples/q2_reference_field_extraction_v0/requests.json",
    PACK + "tools/build_q2_reference_summary.py",
    PACK + "tools/check_q2_reference_summary.py",
    "metrics/specs/q2_consistency_v0.yml",
    "schemas/metrics/q2_consistency_input_v0.schema.json",
    "schemas/metrics/q2_consistency_summary_v0.schema.json",
    "schemas/dataset_manifest.schema.json",
    *(PACK + "tools/" + name + ".py" for name in (
        "q2_intake_io_v0", "load_q2_release_intake_v0",
        "evaluate_q2_archived_capture_v0", "check_q2_release_intake_v0",
        "evaluate_required_gate_v0", "run_recorded_required_gate_evaluations_v0",
        "build_release_grade_candidate_status_v0",
    )),
    WORKFLOW,
)
LEGACY_CHECKER = "tools/check_pulsemech_compute_whole_runtime_observation_v0.py"
LLAMAGUARD_SOURCES = (
    WORKFLOW,
    PACK + "tools/run_llamaguard_current_evidence_v0.py",
    PACK + "tools/adapters/llamaguard_ingest.py",
    PACK + "examples/llamaguard_current_run_cases_v0.jsonl",
    PACK + "requirements-llamaguard-v0.txt",
    PACK + "schemas/llamaguard_evaluator_manifest_v0.schema.json",
    "schemas/external_summary_v1.schema.json",
    PACK + "schemas/external_summary_v1.schema.json",
    PACK + "profiles/external_thresholds.yaml",
    PACK + "tools/build_llamaguard_attestation_envelope_v1.py",
    PACK + "tools/check_external_summary_attestation_v1.py",
    "schemas/external_summary_envelope_v1.schema.json",
    "policy/external_signers_v1.yml",
)
HOSTED_MEMBERS = frozenset({
    "llamaguard_raw.jsonl", "llamaguard_evaluator_manifest_v0.json",
    "llamaguard_summary.json",
})
ATTESTED_MEMBERS = HOSTED_MEMBERS | {
    "llamaguard_summary.bundle.json", "llamaguard_summary.envelope.json",
    "llamaguard_attestation_verifier_v1.json",
}
_GH_BACKEND = Path("/usr/bin/gh")
_MAX_OUTPUT = 2 * 1024 * 1024


class SemanticVerificationError(ValueError):
    """A bounded, non-secret diagnostic; no fallback verdict is available."""


def _need(value: Any, code: str) -> None:
    if not value:
        raise SemanticVerificationError(code)


def _canonical(value: Any) -> bytes:
    try:
        return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise SemanticVerificationError("invalid_json_value") from None


def _json(raw: bytes, *, maximum: int = _MAX_OUTPUT) -> dict:
    _need(type(raw) is bytes and 0 < len(raw) <= maximum
          and not raw.startswith(b"\xef\xbb\xbf"), "invalid_json_bytes")

    def pairs(items):
        _need(len(items) == len({key for key, _ in items}), "duplicate_json_key")
        return dict(items)

    def nonfinite(_):
        raise SemanticVerificationError("nonfinite_json_number")

    try:
        value = json.loads(raw.decode("utf-8", errors="strict"),
                           object_pairs_hook=pairs, parse_constant=nonfinite)
        _need(type(value) is dict, "json_object_required")
        stack, count = [(value, 0)], 0
        while stack:
            item, depth = stack.pop()
            count += 1
            _need(depth <= 48 and count <= 500000, "json_structure_limit")
            if type(item) is str:
                item.encode("utf-8", errors="strict")
            elif type(item) is float:
                _need(math.isfinite(item), "nonfinite_json_number")
            elif type(item) is dict:
                stack.extend((part, depth + 1) for pair in item.items() for part in pair)
            elif type(item) is list:
                stack.extend((part, depth + 1) for part in item)
        return value
    except (ValueError, UnicodeError, RecursionError) as exc:
        if isinstance(exc, SemanticVerificationError):
            raise
        raise SemanticVerificationError("invalid_json_bytes") from None


def _record(value: dict | bytes) -> dict:
    return _json(value if type(value) is bytes else _canonical(value))


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _descriptor(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": _digest(raw)}


def _stamp(info: os.stat_result) -> tuple:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


@contextmanager
def _regular(path: Path):
    """Hold each ancestor directory; never follow an evidence symlink."""
    path = Path(path).absolute()
    _need(".." not in path.parts, "unsafe_path")
    parent = None
    fd = None
    try:
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
        parent = os.open("/", flags | os.O_DIRECTORY)
        for part in path.parts[1:-1]:
            child = os.open(part, flags | os.O_DIRECTORY, dir_fd=parent)
            os.close(parent)
            parent = child
        fd = os.open(path.name, flags, dir_fd=parent)
        before = os.fstat(fd)
        _need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, "regular_file_required")
        yield fd, before
        _need(_stamp(before) == _stamp(os.fstat(fd)), "input_changed_during_read")
    except OSError:
        raise SemanticVerificationError("file_unavailable_or_unsafe") from None
    finally:
        if fd is not None:
            os.close(fd)
        if parent is not None:
            os.close(parent)


def _read(path: Path, maximum: int = _MAX_OUTPUT) -> bytes:
    with _regular(path) as (fd, before):
        _need(0 <= before.st_size <= maximum, "file_size_limit")
        chunks, total = [], 0
        while True:
            chunk = os.read(fd, min(65536, maximum + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            _need(total <= maximum, "file_size_limit")
        _need(total == before.st_size, "input_changed_during_read")
    return b"".join(chunks)


def _write(path: Path, raw: bytes, *, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
    path.chmod(0o500 if executable else 0o400)


def _copy_bound(source: Path, destination: Path, expected: dict) -> None:
    size, wanted = expected.get("archive_size_bytes"), expected.get("archive_sha256")
    _need(type(size) is int and 0 < size <= 1024 * 1024 * 1024
          and type(wanted) is str and re.fullmatch(r"[0-9a-f]{64}", wanted),
          "invalid_archive_binding")
    digest = hashlib.sha256()
    with _regular(source) as (fd, before):
        _need(before.st_size == size, "archive_size_mismatch")
        out = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(out, "wb") as stream:
            remaining = size
            while remaining:
                chunk = os.read(fd, min(1024 * 1024, remaining))
                _need(bool(chunk), "archive_changed_during_read")
                stream.write(chunk)
                digest.update(chunk)
                remaining -= len(chunk)
            _need(not os.read(fd, 1), "archive_changed_during_read")
    _need(digest.hexdigest() == wanted, "archive_digest_mismatch")
    destination.chmod(0o400)


def _environment(home: Path) -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin", "HOME": str(home), "TMPDIR": str(home),
        "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1",
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null", "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_TERMINAL_PROMPT": "0",
    }


def _run(argv: list[str], *, cwd: Path, home: Path, timeout: int) -> tuple[int, bytes, bytes]:
    """Bound time/output; no tokens, Python path or Git config are inherited."""
    def bounded_files():
        # This Linux profile writes only small verification documents. Limit
        # temporary stdout/stderr while the child runs, not only after waiting.
        resource.setrlimit(resource.RLIMIT_FSIZE, (_MAX_OUTPUT + 1, _MAX_OUTPUT + 1))

    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        process = None
        try:
            process = subprocess.Popen(argv, cwd=cwd, env=_environment(home),
                                       stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                       start_new_session=True, preexec_fn=bounded_files)
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if process is not None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
            raise SemanticVerificationError("semantic_process_timeout") from None
        except OSError:
            raise SemanticVerificationError("semantic_process_unavailable") from None
        for stream in (stdout, stderr):
            _need(stream.tell() <= _MAX_OUTPUT, "semantic_process_output_limit")
            stream.seek(0)
        return process.returncode, stdout.read(), stderr.read()


def _identity(value: dict) -> dict:
    _need(type(value) is dict, "run_identity_required")
    run_id = value.get("run_id")
    _need(type(run_id) in (int, str) and re.fullmatch(r"[1-9][0-9]{0,23}", str(run_id)),
          "run_id_invalid")
    _need(value.get("repository") == REPOSITORY
          and type(value.get("run_attempt")) is int and value["run_attempt"] == 1
          and value.get("event") == "workflow_dispatch"
          and value.get("ref") == "refs/heads/main"
          and type(value.get("source_commit")) is str
          and re.fullmatch(r"[0-9a-f]{40}", value["source_commit"]), "run_identity_mismatch")
    return {"repository": REPOSITORY, "source_commit": value["source_commit"],
            "run_id": str(run_id), "run_attempt": 1,
            "event": "workflow_dispatch", "ref": "refs/heads/main"}


def _source_snapshot(repo: Path, revision: str, paths: tuple[str, ...]) -> tuple[dict, list]:
    """Require a real exact checkout and snapshot files bound to its Git objects."""
    repo = Path(repo).absolute()
    _need(repo == repo.resolve(strict=True), "source_directory_symlink")

    def git(*args):
        code, out, _ = _run(["/usr/bin/git", "--no-replace-objects", "-c", "credential.helper=", *args],
                            cwd=repo, home=repo, timeout=30)
        _need(code == 0, "source_git_rejected")
        return out

    _need(git("rev-parse", "--verify", "HEAD^{commit}") == (revision + "\n").encode(),
          "source_head_mismatch")
    names = sorted(set(paths) | {WORKFLOW, POLICY})
    entries = {}
    try:
        for item in git("ls-tree", "-rz", "--full-tree", revision, "--", *names).split(b"\0"):
            if item:
                left, name = item.split(b"\t")
                mode, kind, oid = left.decode("ascii").split()
                entries[name.decode("ascii")] = (mode, kind, oid)
    except (ValueError, UnicodeError):
        raise SemanticVerificationError("source_tree_invalid") from None
    _need(set(entries) == set(names), "source_file_missing")
    values, bindings = {}, []
    for name in names:
        raw = _read(repo / name, maximum=4 * 1024 * 1024)
        mode, kind, oid = entries[name]
        actual_mode = "100755" if (repo / name).stat().st_mode & 0o111 else "100644"
        _need(kind == "blob" and mode == actual_mode
              and oid == hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest(),
              "source_worktree_mismatch")
        values[name] = raw
        bindings.append({"path": name, "mode": mode, "git_blob_sha1": oid,
                         "sha256": _digest(raw), "size_bytes": len(raw)})
    _need(_digest(values[WORKFLOW]) == WORKFLOW_SHA256
          and _digest(values[POLICY]) == POLICY_SHA256, "reviewed_profile_pin_mismatch")
    return values, bindings


@contextmanager
def _private_directory(repo: Path, work_dir: Path, prefix: str):
    parent = Path(work_dir).absolute()
    _need(parent == parent.resolve(strict=True) and parent.is_dir()
          and not parent.is_relative_to(Path(repo).resolve()), "private_workspace_must_be_external")
    path = Path(tempfile.mkdtemp(prefix=prefix, dir=parent))
    path.chmod(0o700)
    try:
        yield path
    finally:
        try:
            shutil.rmtree(path)
        except OSError:
            raise SemanticVerificationError("private_cleanup_failed") from None
        _need(not os.path.lexists(path), "private_cleanup_failed")


def _python_identity(executable: Path, *, cwd: Path, home: Path, q2: bool) -> dict:
    executable = Path(executable).absolute()
    _need(executable == executable.resolve(strict=True)
          and executable.stat().st_mode & 0o111, "trusted_python_path_required")
    raw = _read(executable, maximum=128 * 1024 * 1024)
    probe = (
        "import importlib.metadata,json,platform,sys,unicodedata; import jsonschema,yaml;"
        "print(json.dumps({'implementation':platform.python_implementation(),"
        "'version':list(sys.version_info[:3]),'unicode':unicodedata.unidata_version,"
        "'jsonschema':importlib.metadata.version('jsonschema'),'PyYAML':yaml.__version__},sort_keys=True))"
    )
    code, out, _ = _run([str(executable), "-I", "-B", "-c", probe], cwd=cwd, home=home, timeout=30)
    _need(code == 0, "python_runtime_or_dependencies_unavailable")
    identity = _json(out)
    if q2:
        _need(identity.get("implementation") == "CPython" and identity.get("version") == [3, 11, 16]
              and identity.get("unicode") == "14.0.0", "q2_exact_replay_runtime_required")
    return {"executable": _descriptor(raw), "runtime": identity,
            "trust_scope": "caller_trusted_local_interpreter",
            "original_runtime_identity_proven": False}


def _negative(record: dict, *, cleanup: str) -> None:
    _need(record.get("schema_version") == "q2_release_intake_result_v0"
          and record.get("record_status") == "archived_capture_intake"
          and record.get("input_valid") is True and record.get("metric_pass") is False
          and type(record.get("process_exit")) is int and record["process_exit"] == 1
          and record.get("cleanup") == cleanup
          and type(record.get("checks")) is dict
          and set(record["checks"]) == {"request", "capture", "subject", "replay", "summary"}
          and all(item is True for item in record["checks"].values())
          and type(record.get("current_inference_count")) is int and record["current_inference_count"] == 0
          and record.get("authority_effect") == "none"
          and record.get("production_gate_eligible") is False, "q2_valid_negative_required")


def verify_q2(repo_root, request_bytes, capture_path, capsule_path, producer_result,
              independent_result, run_identity, replay_python, work_dir) -> dict:
    """Replay exact bound archives through the unchanged independent Q2 checker.

The supplied interpreter is a trusted verifier input, never a field selected by
the archive/request. No archive member is extracted as an executable or imported.
The original saved records remain data and must match the fresh complete result.
"""
    repo = Path(repo_root).absolute()
    identity = _identity(run_identity)
    request = _json(request_bytes, maximum=16384)
    expected_evaluation = {key: identity[key] for key in ("repository", "source_commit", "event", "ref")}
    expected_evaluation["workflow"] = WORKFLOW
    _need(request.get("evaluation_identity") == expected_evaluation, "q2_request_run_binding_mismatch")
    producer, independent = _record(producer_result), _record(independent_result)
    _negative(producer, cleanup="verified_removed")
    _negative(independent, cleanup="verified_removed")
    _need(_canonical(producer) == _canonical(independent), "q2_saved_records_disagree")
    sources, bindings = _source_snapshot(repo, identity["source_commit"], Q2_SOURCES)
    source_bindings = [{"path": item["path"], "sha256": item["sha256"], "size_bytes": item["size_bytes"]}
                       for item in bindings if item["path"] in Q2_SOURCES]
    binding = {**expected_evaluation, "workflow_sha": identity["source_commit"],
               "run_id": identity["run_id"], "run_attempt": 1, "request_sha256": _digest(request_bytes)}
    _need(producer.get("evaluation_binding") == binding
          and producer.get("request_sha256") == _digest(request_bytes)
          and producer.get("source_bindings") == source_bindings, "q2_saved_run_binding_mismatch")
    for key in ("capture_expectation", "release_subject"):
        _need(type(request.get(key)) is dict, "q2_archive_binding_missing")
    with _private_directory(repo, Path(work_dir), "pulse-q2-negative-replay-") as private:
        python_identity = _python_identity(Path(replay_python), cwd=repo, home=private, q2=True)
        _copy_bound(Path(capture_path), private / "capture.zip", request["capture_expectation"])
        _copy_bound(Path(capsule_path), private / "capsule.zip", request["release_subject"])
        _write(private / "request.json", request_bytes)
        _write(private / "context.json", _canonical({"binding": binding, "source_bindings": source_bindings}))
        code, _, _ = _run([str(Path(replay_python).absolute()), "-I", "-B", str(repo / Q2_CHECKER),
                           "--private-input", str(private), "--repo-root", str(repo)],
                          cwd=repo, home=private, timeout=240)
        fresh = _json(_read(private / "result.json", maximum=128 * 1024))
        _need(code == 1, "q2_independent_replay_rejected")
        _negative(fresh, cleanup="not_created")
        # The unchanged private checker leaves cleanup to its supervisor. Only
        # that field is normalized after our private tree is actually removed.
        normalized = {**fresh, "cleanup": "verified_removed"}
        _need(_canonical(normalized) == _canonical(producer), "q2_fresh_replay_saved_record_mismatch")
        # Recheck the checkout after child execution; it must not mutate sources.
        after, _ = _source_snapshot(repo, identity["source_commit"], Q2_SOURCES)
        _need(after == sources, "q2_replay_source_changed")
    return {
        "format": "pulsemech_admission_rejection_q2_semantics_v0",
        "validation_scope": "later_offline_private_input_replay",
        "request": _descriptor(request_bytes),
        "capture": {"bytes": request["capture_expectation"]["archive_size_bytes"],
                    "sha256": request["capture_expectation"]["archive_sha256"]},
        "capsule": {"bytes": request["release_subject"]["archive_size_bytes"],
                    "sha256": request["release_subject"]["archive_sha256"]},
        "source_bindings": bindings, "replay_python": python_identity,
        "fresh_result": fresh, "fresh_result_sha256": _digest(_canonical(fresh)),
        "saved_result_sha256": _digest(_canonical(producer)),
        "fresh_independent_checker_executed": True, "saved_records_matched_fresh_result": True,
        "metric_pass": False, "process_exit": 1, "private_cleanup": "verified_removed",
        "current_inference_count": 0, "archive_executables_invoked": False,
        "original_runtime_reads_proven": False, "production_gate_eligible": False,
        "authority_effect": "none",
    }


def _driver(raw: bytes, name: str) -> str:
    """Extract an unchanged existing checker driver without importing its CLI."""
    try:
        tree = ast.parse(raw.decode("utf-8"))
        values = [ast.literal_eval(node.value) for node in tree.body
                  if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name
                                                          for target in node.targets)]
    except (ValueError, SyntaxError, UnicodeError):
        raise SemanticVerificationError("existing_semantic_driver_invalid") from None
    _need(len(values) == 1 and type(values[0]) is str and 0 < len(values[0]) < 65536,
          "existing_semantic_driver_missing")
    return values[0]


def _member_set(value: dict, expected: frozenset | set) -> dict[str, bytes]:
    _need(type(value) is dict and set(value) == set(expected), "llamaguard_member_set_mismatch")
    _need(all(type(raw) is bytes and 0 < len(raw) <= 16 * 1024 * 1024 for raw in value.values())
          and sum(map(len, value.values())) <= 48 * 1024 * 1024, "llamaguard_member_budget")
    return dict(value)


def _trusted_gh() -> tuple[bytes, dict]:
    """Use the system-installed Linux CLI, never an evidence-selected backend."""
    path = _GH_BACKEND
    try:
        _need(path == path.resolve(strict=True), "trusted_gh_symlink_rejected")
        for ancestor in (path, *path.parents):
            info = ancestor.stat()
            _need(info.st_uid == 0 and not info.st_mode & 0o022, "trusted_gh_ownership_required")
        _need(path.stat().st_mode & 0o111 and not path.stat().st_mode & 0o6000,
              "trusted_gh_executable_required")
        raw = _read(path, maximum=128 * 1024 * 1024)
    except OSError:
        raise SemanticVerificationError("trusted_gh_unavailable") from None
    _need(raw.startswith(b"\x7fELF"), "trusted_gh_elf_required")
    return raw, {**_descriptor(raw), "trust_scope": "root_owned_system_gh_executable",
                 "origin_authenticated_by_this_checker": False}


def _utc(value: Any) -> dt.datetime:
    _need(type(value) is str, "evidence_timestamp_invalid")
    try:
        result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        _need(result.tzinfo is not None and result.utcoffset() == dt.timedelta(0),
              "evidence_timestamp_not_utc")
        return result
    except ValueError:
        raise SemanticVerificationError("evidence_timestamp_invalid") from None


def _unchanged(root: Path, expected: dict[str, bytes]) -> None:
    found = set()
    for path in root.rglob("*"):
        mode = path.lstat().st_mode
        _need(stat.S_ISREG(mode) or stat.S_ISDIR(mode), "llamaguard_input_changed")
        if stat.S_ISREG(mode):
            name = path.relative_to(root).as_posix()
            _need(name in expected and _read(path, maximum=16 * 1024 * 1024) == expected[name],
                  "llamaguard_input_changed")
            found.add(name)
    _need(found == set(expected), "llamaguard_input_changed")


def verify_llamaguard(repo_root, hosted_members, attested_members, run_identity, work_dir) -> dict:
    """Rebuild current-run content, then invoke the real trusted signature backend.

Member dictionaries use canonical basenames. Both artifact copies must agree.
The caller separately validates artifact provenance and original execution logs.
The copied system gh may consult its trust service, so only Q2 is fully offline.
"""
    repo = Path(repo_root).absolute()
    identity = _identity(run_identity)
    hosted = _member_set(hosted_members, HOSTED_MEMBERS)
    attested = _member_set(attested_members, ATTESTED_MEMBERS)
    _need(all(hosted[name] == attested[name] for name in HOSTED_MEMBERS),
          "llamaguard_artifact_copies_disagree")
    sources, bindings = _source_snapshot(repo, identity["source_commit"],
                                         LLAMAGUARD_SOURCES + (LEGACY_CHECKER,))
    _need(sources["schemas/external_summary_v1.schema.json"] ==
          sources[PACK + "schemas/external_summary_v1.schema.json"], "summary_schema_copies_disagree")
    content_driver = _driver(sources[LEGACY_CHECKER], "_LOCAL_R2_LLAMAGUARD_CONTENT_DRIVER")
    attestation_driver = _driver(sources[LEGACY_CHECKER], "_LOCAL_R2_ATTESTATION_DRIVER")
    manifest = _json(hosted["llamaguard_evaluator_manifest_v0.json"])
    envelope = _json(attested["llamaguard_summary.envelope.json"])
    _need(type(manifest.get("run")) is dict and type(envelope.get("verification")) is dict,
          "llamaguard_identity_missing")
    created_text = manifest["run"].get("created_utc")
    created, verified = _utc(created_text), _utc(envelope["verification"].get("verified_at"))
    _need(created <= verified, "llamaguard_timestamp_order_mismatch")
    time_bounds = "enclosing_checker_must_bind_original_run_timestamps"
    if "run_started_at" in run_identity or "updated_at" in run_identity:
        _need(_utc(run_identity.get("run_started_at")) <= created <= verified <=
              _utc(run_identity.get("updated_at")), "llamaguard_time_outside_original_run")
        time_bounds = "supplied_original_run_utc_bounds_checked"
    dataset = sources[PACK + "examples/llamaguard_current_run_cases_v0.jsonl"]
    cases = [_json(line) for line in dataset.splitlines() if line.strip()]
    _need(len(cases) == 6 and all(type(row.get("case_id")) is str for row in cases),
          "reviewed_llamaguard_dataset_mismatch")
    content_spec = {"repository": REPOSITORY, "commit": identity["source_commit"],
                    "run_id": int(identity["run_id"]), "created_utc": created_text,
                    "case_ids": [row["case_id"] for row in cases]}
    attestation_spec = {"repository": REPOSITORY, "commit": identity["source_commit"]}
    payloads = {EXTERNAL + name: raw for name, raw in attested.items()}
    inputs = {**sources, **payloads, "llamaguard-input.json": _canonical(content_spec),
              "attestation-input.json": _canonical(attestation_spec)}
    with _private_directory(repo, Path(work_dir), "pulse-llamaguard-negative-replay-") as private:
        workspace = private / "inputs"
        workspace.mkdir(mode=0o700)
        home = private / "home"
        home.mkdir(mode=0o700)
        for name, raw in inputs.items():
            _write(workspace / name, raw)
        python = Path(sys.executable).resolve(strict=True)
        python_identity = _python_identity(python, cwd=workspace, home=home, q2=False)
        _unchanged(workspace, inputs)
        code, out, _ = _run([str(python), "-I", "-B", "-c", content_driver],
                            cwd=workspace, home=home, timeout=90)
        _need(code == 0, "llamaguard_fresh_content_rejected")
        content = _json(out)
        _need(content.get("schema_version") == "pulsemech_step5c_local_r2_llamaguard_content_core_v0"
              and content.get("record_count") == 6, "llamaguard_content_result_invalid")
        _unchanged(workspace, inputs)
        backend, backend_identity = _trusted_gh()
        backend_path = private / "backend" / "gh"
        _write(backend_path, backend, executable=True)
        code, out, _ = _run([str(python), "-I", "-B", "-c", attestation_driver],
                            cwd=workspace, home=home, timeout=150)
        _need(code == 0, "llamaguard_fresh_signature_rejected")
        attestation = _json(out)
        _unchanged(workspace, inputs)
        _need(_read(backend_path, maximum=128 * 1024 * 1024) == backend,
              "trusted_gh_changed")
        report = attestation.get("report")
        _need(type(report) is dict and report.get("status") == "verified"
              and report.get("errors") == [] and type(report.get("attestation")) is dict
              and report["attestation"].get("verified") is True
              and report["attestation"].get("backend") == "gh-attestation"
              and _canonical(report) == _canonical(_json(attested["llamaguard_attestation_verifier_v1.json"])),
              "llamaguard_fresh_signature_result_mismatch")
    return {
        "format": "pulsemech_admission_rejection_llamaguard_semantics_v0",
        "validation_scope": "later_content_and_trusted_signature_replay",
        "members": [{"name": name, **_descriptor(attested[name])} for name in sorted(attested)],
        "source_bindings": bindings, "replay_python": python_identity,
        "backend_identity": backend_identity, "content": content, "attestation": attestation,
        "fresh_content_checker_executed": True, "fresh_signature_backend_executed": True,
        "saved_verifier_report_matched_fresh_result": True,
        "private_cleanup": "verified_removed", "time_bounds": time_bounds,
        "original_runtime_reads_proven": False, "model_execution_replayed": False,
        "model_output_semantic_correctness_verified": False, "authority_effect": "none",
    }

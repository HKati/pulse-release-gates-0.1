#!/usr/bin/env python3
"""Entry-build evidence regressions; produced entries are never executed.

Checker fixtures contain authored process/toolchain observations and a fixed
repository-source compilation. They establish record-checking behavior only.
The acquisition test compiles the entry twice with the trusted host compiler.
No selected runtime, operator, model, launcher or reference is executed.
"""
from __future__ import annotations

import ast
import base64
import copy
from contextlib import contextmanager
import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import select
import shutil
import signal
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SELF = "tests/test_required_gate_idempotence_entry_build_v0.py"
CHECKER_PATH = "tools/check_required_gate_idempotence_entry_build_v0.py"
BUILDER_PATH = "tools/required_gate_idempotence_entry_build_v0.py"
WORKFLOW_PATH = ".github/workflows/required_gate_idempotence_entry_build_v0.yml"
SOURCE_PATH = "tools/required_gate_idempotence_containment_entry_v0.c"
SOURCE_SHA = "0265273af5a51301035bbd4d2418d4ab87e8572a56bddbf028c95e12e7e2631f"
SOURCE_COMMIT = "a" * 40
REAL_POPEN = subprocess.Popen
CC_FLAGS = (
    "-v", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-ffreestanding",
    "-fno-builtin", "-fno-pie", "-fno-stack-protector", "-fno-asynchronous-unwind-tables",
    "-fno-unwind-tables", "-nostdlib", "-static", "-no-pie", "-Wl,--build-id=none",
    "-Wl,-z,noexecstack",
)
ENVIRONMENT = {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "TZ": "UTC",
               "SOURCE_DATE_EPOCH": "0", "TMPDIR": "."}


def module(name, path):
    if name not in sys.modules:
        tools = str(ROOT / "tools")
        if tools not in sys.path:
            sys.path.insert(0, tools)
        spec = importlib.util.spec_from_file_location(name, ROOT / path)
        assert spec is not None and spec.loader is not None
        result = importlib.util.module_from_spec(spec)
        sys.modules[name] = result
        spec.loader.exec_module(result)
    return sys.modules[name]


def checker():
    return module("check_required_gate_idempotence_entry_build_v0", CHECKER_PATH)


def builder():
    return module("required_gate_idempotence_entry_build_v0", BUILDER_PATH)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                       allow_nan=False) + "\n").encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def binding(raw):
    return {"sha256": digest(raw), "size_bytes": len(raw)}


def b64(raw):
    return base64.b64encode(raw).decode("ascii")


def process(pid=101):
    return {"pid": pid, "exit_code": 0, "elapsed_ns": 1_000_000,
            "timed_out": False, "stdout_overflow": False, "stderr_overflow": False}


def boundaries(value):
    for key, expected in checker().BOUNDARY.items():
        assert value[key] == expected and type(value[key]) is type(expected), key
    assert value["authority_effect"] == "none"
    assert value["metric_pass"] is None
    assert value["entry_binary_executed"] is False
    assert value["github_build_provenance_verified"] is False


@pytest.fixture(scope="module")
def compiled_entry(tmp_path_factory):
    directory = tmp_path_factory.mktemp("entry-build-checker-fixture")
    compiler = Path(shutil.which("gcc") or "")
    assert compiler.is_file(), "The fixed-entry build regression requires a host GCC compiler."
    compiler = compiler.resolve(strict=True)
    source = (ROOT / SOURCE_PATH).read_bytes()
    assert len(source) == 4598 and digest(source) == SOURCE_SHA
    (directory / "entry.c").write_bytes(source)
    result = subprocess.run([str(compiler), *CC_FLAGS, "entry.c", "-o", "entry"],
                            cwd=directory, env=ENVIRONMENT, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert result.stdout == b""
    # This fixture reads the native output as bytes; it never executes it.
    return SimpleNamespace(source=source, entry=(directory / "entry").read_bytes(), compiler=compiler)


def authored_payload(compiled_entry):
    c = checker()
    compiler = {"path": "/usr/bin/gcc", **binding(b"authored compiler identity")}
    request = {"format": "required_gate_idempotence_entry_build_request_v0", "profile": c.PROFILE,
               "source_commit": SOURCE_COMMIT,
               "source": {"path": SOURCE_PATH, **binding(compiled_entry.source)},
               "compiler": compiler, "argv_template": [compiler["path"], *CC_FLAGS, "entry.c", "-o", "entry"],
               "environment": ENVIRONMENT, "limits": dict(c.LIMITS),
               "context": {"kind": "local_example"}, **c.BOUNDARY}
    payload = {"request.json": canonical(request), "source.c": compiled_entry.source}
    components = []
    for name in sorted(("compiler", "cc1", "as", "collect2", "ld")):
        path = compiler["path"] if name == "compiler" else "/authored/toolchain/" + name
        descriptor = {key: compiler[key] for key in ("sha256", "size_bytes")} if name == "compiler" else binding(name.encode())
        components.append({"name": name, "lookup_path": path, "path": path, **descriptor})
    queries = [{"name": row["name"], "argv": [compiler["path"], "-print-prog-name=" + row["name"]],
                "stdout_b64": b64((row["lookup_path"] + "\n").encode()), "stderr_b64": b64(b""),
                "process": process(200 + index)}
               for index, row in enumerate(components) if row["name"] != "compiler"]
    toolchain = {"format": "required_gate_idempotence_entry_toolchain_v0", "components": components,
                 "version": {"argv": [compiler["path"], "--version"],
                             "stdout_b64": b64(b"gcc authored fixture\n"), "stderr_b64": b64(b""),
                             "process": process()}, "queries": queries}
    payload["toolchain-before.json"] = canonical(toolchain)
    later = copy.deepcopy(toolchain)
    later["version"]["process"] = process(301)
    for index, query in enumerate(later["queries"]):
        query["process"] = process(400 + index)
    payload["toolchain-after.json"] = canonical(later)
    for number in (1, 2):
        build_id = "build-" + str(number)
        payload[build_id + "/entry.c"] = compiled_entry.source
        payload[build_id + "/entry"] = compiled_entry.entry
        payload[build_id + "/stdout.bin"] = b""
        payload[build_id + "/stderr.bin"] = b"authored fixed command diagnostics\n"
        result = {"format": "required_gate_idempotence_entry_build_execution_v0", "build_id": build_id,
                  "working_directory": build_id, "argv": request["argv_template"], "environment": ENVIRONMENT,
                  "process": process(500 + number), "source": binding(compiled_entry.source),
                  "stdout": binding(payload[build_id + "/stdout.bin"]),
                  "stderr": binding(payload[build_id + "/stderr.bin"]), "entry": binding(compiled_entry.entry)}
        payload[build_id + "/result.json"] = canonical(result)
    payload["record.json"] = canonical({
        "format": "required_gate_idempotence_entry_build_v0", "profile": c.PROFILE,
        "status": "completed", "source_commit": SOURCE_COMMIT, "request_sha256": digest(payload["request.json"]),
        "files": [{"path": path, **binding(raw)} for path, raw in sorted(payload.items())],
        "build_ids": ["build-1", "build-2"], "repeat_build_equal": True,
        "entry_static_shape_verified": True, "toolchain_observations_stable": True, **c.BOUNDARY,
    })
    return payload


@pytest.fixture
def payload(compiled_entry):
    return authored_payload(compiled_entry)


def reseal(payload):
    record = json.loads(payload["record.json"])
    record["request_sha256"] = digest(payload["request.json"])
    record["files"] = [{"path": path, **binding(raw)} for path, raw in sorted(payload.items()) if path != "record.json"]
    payload["record.json"] = canonical(record)


def replace_json(payload, path, mutate):
    value = json.loads(payload[path])
    mutate(value)
    payload[path] = canonical(value)
    reseal(payload)


def check(payload, **overrides):
    arguments = {"expected_request_sha256": digest(payload["request.json"]),
                 "expected_record_sha256": digest(payload["record.json"]), "source_commit": SOURCE_COMMIT}
    arguments.update(overrides)
    return checker().check_payload(payload, **arguments)


def materialize(payload, directory):
    directory.mkdir(mode=0o700)
    for name, raw in payload.items():
        path = directory / name
        path.parent.mkdir(mode=0o700, exist_ok=True)
        path.write_bytes(raw)
    return directory


def directory_check(payload, directory):
    return checker().check_directory(directory, expected_request_sha256=digest(payload["request.json"]),
                                     expected_record_sha256=digest(payload["record.json"]), source_commit=SOURCE_COMMIT)


def test_fixed_recipe_and_source_have_no_caller_extensions(compiled_entry):
    c = checker()
    assert tuple(c.CC_FLAGS) == CC_FLAGS
    assert c.ENVIRONMENT == ENVIRONMENT
    assert c.ENTRY_SOURCE_PATH == SOURCE_PATH and c.ENTRY_SOURCE_SHA256 == SOURCE_SHA
    assert c.ENTRY_SOURCE_SIZE == len(compiled_entry.source) == 4598
    assert c.LIMITS == {"build_seconds": 30, "query_seconds": 10, "stdout_bytes": 65536,
                        "stderr_bytes": 262144, "entry_bytes": 16777216, "tool_bytes": 134217728,
                        "control_bytes": 1048576, "builds": 2}


def test_independent_authored_record_checks_without_authenticating_execution(payload):
    result = check(payload)
    assert result["status"] == "accepted" and result["entry_build_record_verified"] is True
    assert result["repeat_build_equal"] is True and result["entry_static_shape_verified"] is True
    boundaries(result)


@pytest.mark.parametrize("field", ["expected_request_sha256", "expected_record_sha256", "source_commit"])
def test_external_bindings_cannot_be_replaced_by_record_claims(payload, field):
    with pytest.raises(checker().BuildError):
        check(payload, **{field: "0" * (40 if field == "source_commit" else 64)})


@pytest.mark.parametrize("change", ["source_digest", "source_size", "source_path", "profile", "format",
                                     "source_commit", "environment", "path", "flags", "output", "limits",
                                     "float_builds", "bool_size", "extra"])
def test_rehashed_request_mutations_do_not_replace_fixed_reconstruction(payload, change):
    def mutate(value):
        if change == "source_digest": value["source"]["sha256"] = "0" * 64
        elif change == "source_size": value["source"]["size_bytes"] += 1
        elif change == "source_path": value["source"]["path"] = "tools/other.c"
        elif change == "profile": value["profile"] = "arbitrary_compiler_v0"
        elif change == "format": value["format"] = "different_request"
        elif change == "source_commit": value["source_commit"] = "b" * 40
        elif change == "environment": value["environment"]["LD_PRELOAD"] = "/host/inject.so"
        elif change == "path": value["environment"]["PATH"] = "/caller/bin"
        elif change == "flags": value["argv_template"].insert(1, "-fplugin=/caller/plugin.so")
        elif change == "output": value["argv_template"][-1] = "../entry"
        elif change == "limits": value["limits"]["builds"] = 3
        elif change == "float_builds": value["limits"]["builds"] = 2.0
        elif change == "bool_size": value["compiler"]["size_bytes"] = True
        else: value["extra"] = "not part of the request"
    replace_json(payload, "request.json", mutate)
    with pytest.raises(checker().BuildError):
        check(payload)


def github_context():
    return {"kind": "github_workflow", "repository": "HKati/pulse-release-gates-0.1",
            "workflow_path": WORKFLOW_PATH, "source_commit": SOURCE_COMMIT, "workflow_sha": SOURCE_COMMIT,
            "ref": "refs/heads/main", "run_id": 12345, "run_attempt": 1, "event_name": "workflow_dispatch"}


def test_github_context_is_bound_but_remains_an_unverified_producer_claim(payload):
    replace_json(payload, "request.json", lambda value: value.update(context=github_context()))
    result = check(payload)
    assert result["entry_build_record_verified"] is True
    boundaries(result)


@pytest.mark.parametrize("field,value", [
    ("repository", "other/repository"), ("workflow_path", ".github/workflows/other.yml"),
    ("ref", "refs/heads/unreviewed"), ("source_commit", "b" * 40), ("workflow_sha", "b" * 40),
    ("run_attempt", 2), ("run_id", True), ("event_name", "pull_request"), ("extra", "unbound"),
])
def test_github_context_rejects_wrong_identity_or_repeat_attempt(payload, field, value):
    context = github_context()
    context[field] = value
    replace_json(payload, "request.json", lambda row: row.update(context=context))
    with pytest.raises(checker().BuildError):
        check(payload)


@pytest.mark.parametrize("change", ["missing", "extra", "duplicate", "unordered", "descriptor", "traversal"])
def test_closed_manifest_cannot_hide_an_unbound_member(payload, change):
    if change == "missing":
        del payload["build-2/stdout.bin"]
        reseal(payload)
    elif change == "extra":
        payload["unselected.bin"] = b"outside selection"
        reseal(payload)
    else:
        record = json.loads(payload["record.json"])
        if change == "duplicate": record["files"].append(copy.deepcopy(record["files"][0]))
        elif change == "unordered": record["files"].reverse()
        elif change == "descriptor": record["files"][0]["size_bytes"] += 1
        else: record["files"][0]["path"] = "../entry"
        payload["record.json"] = canonical(record)
    with pytest.raises(checker().BuildError):
        check(payload)


@pytest.mark.parametrize("build_id", ["build-1", "build-2"])
def test_each_build_consumes_the_exact_source_even_when_all_digests_are_rehashed(payload, build_id):
    path = build_id + "/entry.c"
    payload[path] += b"\n/* changed source */\n"
    replace_json(payload, build_id + "/result.json", lambda row: row.update(source=binding(payload[path])))
    with pytest.raises(checker().BuildError):
        check(payload)


@pytest.mark.parametrize("change", ["build_id", "cwd", "argv", "environment", "pid", "exit", "elapsed",
                                     "timeout", "overflow", "source", "stdout", "entry", "extra"])
def test_second_build_cannot_borrow_a_correct_first_execution(payload, change):
    def mutate(value):
        if change == "build_id": value["build_id"] = "build-1"
        elif change == "cwd": value["working_directory"] = "build-1"
        elif change == "argv": value["argv"][-3] = "different.c"
        elif change == "environment": value["environment"]["LC_ALL"] = "C.UTF-8"
        elif change == "pid": value["process"]["pid"] = True
        elif change == "exit": value["process"]["exit_code"] = 1
        elif change == "elapsed": value["process"]["elapsed_ns"] = 30_000_000_001
        elif change == "timeout": value["process"]["timed_out"] = True
        elif change == "overflow": value["process"]["stderr_overflow"] = True
        elif change == "source": value["source"]["sha256"] = "0" * 64
        elif change == "stdout": value["stdout"]["size_bytes"] = 1
        elif change == "entry": value["entry"]["sha256"] = "0" * 64
        else: value["extra"] = "not part of the execution"
    replace_json(payload, "build-2/result.json", mutate)
    with pytest.raises(checker().BuildError):
        check(payload)


def test_unequal_outputs_cannot_pass_after_coherent_result_rehashing(payload):
    path = "build-2/entry"
    payload[path] += b"different but still parseable ELF suffix"
    replace_json(payload, "build-2/result.json", lambda row: row.update(entry=binding(payload[path])))
    with pytest.raises(checker().BuildError):
        check(payload)


@pytest.mark.parametrize("replacement", [b"", b"not ELF", b"\x7fELF" + bytes(60)])
def test_equal_invalid_native_outputs_do_not_satisfy_static_entry_shape(payload, replacement):
    for build_id in ("build-1", "build-2"):
        payload[build_id + "/entry"] = replacement
        replace_json(payload, build_id + "/result.json", lambda row: row.update(entry=binding(replacement)))
    with pytest.raises(checker().BuildError):
        check(payload)


@pytest.mark.parametrize("stream,limit", [("stdout", 65536), ("stderr", 262144)])
def test_rehashed_oversized_raw_stream_cannot_be_accepted(payload, stream, limit):
    path = "build-2/" + stream + ".bin"
    payload[path] = b"x" * (limit + 1)
    replace_json(payload, "build-2/result.json", lambda row: row.update({stream: binding(payload[path])}))
    with pytest.raises(checker().BuildError):
        check(payload)


@pytest.mark.parametrize("change", ["component", "missing", "duplicate", "query_path", "query_argv",
                                     "query_status", "version", "base64", "extra"])
def test_toolchain_observations_must_match_before_and_after(payload, change):
    def mutate(value):
        if change == "component": value["components"][0]["sha256"] = "0" * 64
        elif change == "missing": value["components"].pop()
        elif change == "duplicate": value["components"].append(copy.deepcopy(value["components"][0]))
        elif change == "query_path": value["queries"][0]["stdout_b64"] = b64(b"/different/as\n")
        elif change == "query_argv": value["queries"][0]["argv"][-1] = "-print-prog-name=ld"
        elif change == "query_status": value["queries"][0]["process"]["exit_code"] = 1
        elif change == "version": value["version"]["stdout_b64"] = b64(b"different compiler\n")
        elif change == "base64": value["version"]["stdout_b64"] += "\n"
        else: value["extra"] = "outside the record"
    replace_json(payload, "toolchain-after.json", mutate)
    with pytest.raises(checker().BuildError):
        check(payload)


def test_coherently_rehashed_basename_query_cannot_select_a_different_tool(payload):
    for path in ("toolchain-before.json", "toolchain-after.json"):
        value = json.loads(payload[path])
        query = next(row for row in value["queries"] if row["name"] == "as")
        component = next(row for row in value["components"] if row["name"] == "as")
        query["stdout_b64"] = b64(b"other-tool\n")
        component["lookup_path"] = "/usr/bin/other-tool"
        payload[path] = canonical(value)
    reseal(payload)
    with pytest.raises(checker().BuildError):
        check(payload)


@pytest.mark.parametrize("location,field", [
    ("request.json", "execution_ready"), ("request.json", "github_build_provenance_verified"),
    ("record.json", "source_binary_equivalence_verified"), ("record.json", "entry_binary_executed"),
    ("record.json", "containment_enforced"), ("record.json", "production_gate_eligible"),
])
def test_successful_record_cannot_promote_authority_or_authenticate_execution(payload, location, field):
    value = json.loads(payload[location]); value[field] = True
    payload[location] = canonical(value)
    if location != "record.json": reseal(payload)
    with pytest.raises(checker().BuildError):
        check(payload)


@pytest.mark.parametrize("location", ["request.json", "record.json", "build-2/result.json", "toolchain-after.json"])
def test_duplicate_known_json_keys_are_rejected_before_shape_checking(payload, location):
    value = json.loads(payload[location])
    payload[location] = b'{"format":' + json.dumps(value["format"]).encode() + b',' + payload[location][1:]
    if location != "record.json": reseal(payload)
    with pytest.raises(checker().BuildError, match="entry_build_duplicate_key"):
        check(payload)


@pytest.mark.parametrize("location", ["request.json", "record.json", "build-2/result.json", "toolchain-after.json"])
def test_valid_but_noncanonical_json_does_not_receive_a_canonical_record_claim(payload, location):
    payload[location] += b"\n"
    if location != "record.json": reseal(payload)
    with pytest.raises(checker().BuildError, match="entry_build_noncanonical_record"):
        check(payload)


def test_transport_normalized_modes_do_not_change_byte_record_validity(payload, tmp_path):
    directory = materialize(payload, tmp_path / "evidence")
    directory.chmod(0o755)
    for path in directory.rglob("*"):
        path.chmod(0o755 if path.is_dir() else 0o644)
    result = directory_check(payload, directory)
    assert result["status"] == "accepted"
    boundaries(result)


@pytest.mark.parametrize("change", ["symlink", "hardlink", "fifo", "extra_dir", "extra_file", "root_link"])
def test_directory_checker_refuses_nonordinary_or_extra_evidence(payload, tmp_path, change):
    directory = materialize(payload, tmp_path / "evidence")
    target = directory / "build-2/stdout.bin"
    if change in {"symlink", "hardlink", "fifo"}:
        target.unlink()
        if change == "symlink": target.symlink_to(directory / "build-1/stdout.bin")
        elif change == "hardlink": os.link(directory / "build-1/stdout.bin", target)
        else: os.mkfifo(target)
    elif change == "extra_dir": (directory / "unselected").mkdir()
    elif change == "extra_file": (directory / "unselected.bin").write_bytes(b"extra")
    else:
        alias = tmp_path / "alias"
        alias.symlink_to(directory, target_is_directory=True)
        directory = alias
    with pytest.raises((checker().BuildError, OSError)):
        directory_check(payload, directory)


def test_checker_cli_binds_raw_bytes_and_refuses_existing_output(payload, tmp_path):
    evidence = materialize(payload, tmp_path / "evidence")
    args = [sys.executable, str(ROOT / CHECKER_PATH), "--evidence-dir", str(evidence),
            "--source-commit", SOURCE_COMMIT, "--request-sha256", digest(payload["request.json"]),
            "--record-sha256", digest(payload["record.json"])]
    result = subprocess.run(args, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    boundaries(json.loads(result.stdout))
    existing = tmp_path / "existing.json"
    existing.write_bytes(b"keep original\n")
    rejected = subprocess.run([*args, "--output", str(existing)], capture_output=True, timeout=15)
    assert rejected.returncode != 0 and existing.read_bytes() == b"keep original\n"


@pytest.fixture(scope="module")
def build_selection(compiled_entry):
    head = subprocess.run(["/usr/bin/git", "-C", str(ROOT), "rev-parse", "HEAD"],
                          capture_output=True, check=True, timeout=10).stdout.decode().strip()
    return {"repository_root": ROOT, "source_commit": head, "compiler": compiled_entry.compiler,
            "expected_compiler_sha256": digest(compiled_entry.compiler.read_bytes())}


def incomplete(directory):
    assert not (directory / "record.json").exists()
    value = json.loads((directory / "attempt.incomplete.json").read_bytes())
    assert value["status"] == "incomplete"
    boundaries(value)
    return value


def test_acquisition_really_compiles_twice_and_never_executes_an_entry(build_selection, tmp_path, monkeypatch):
    b = builder()
    calls = []
    monkeypatch.setenv("ENTRY_BUILD_CALLER_MARKER", "must not reach compiler")
    monkeypatch.setenv("CFLAGS", "-fplugin=/unselected/compiler-plugin.so")

    def guarded_popen(argv, **kwargs):
        assert argv[0] in {"/usr/bin/git", str(build_selection["compiler"])}, "unexpected executable"
        if argv[0] != "/usr/bin/git":
            assert kwargs["env"] == ENVIRONMENT
            assert kwargs["start_new_session"] is True and kwargs["close_fds"] is True
            assert kwargs["stdin"] == subprocess.DEVNULL and kwargs["umask"] == 0o077
            calls.append((list(argv), Path(kwargs["cwd"]).resolve()))
        return REAL_POPEN(argv, **kwargs)

    monkeypatch.setattr(b.subprocess, "Popen", guarded_popen)
    directory = tmp_path / "actual-builds"
    record = b.acquire_entry_build(**build_selection, output_directory=directory)
    assert record["status"] == "completed"
    boundaries(record)
    builds = [(argv, cwd) for argv, cwd in calls if "-v" in argv]
    queries = [argv for argv, _ in calls if "-v" not in argv]
    assert len(builds) == 2 and len(queries) == 10
    assert builds == [([str(build_selection["compiler"]), *CC_FLAGS, "entry.c", "-o", "entry"],
                       directory / build_id) for build_id in ("build-1", "build-2")]
    assert {path.relative_to(directory).as_posix() for path in directory.rglob("*") if path.is_file()} == {
        *checker().FILES, "record.json"}
    assert (directory / "build-1/entry").read_bytes() == (directory / "build-2/entry").read_bytes()
    assert not (directory / "attempt.incomplete.json").exists()
    report = checker().check_directory(directory,
        expected_request_sha256=digest((directory / "request.json").read_bytes()),
        expected_record_sha256=digest((directory / "record.json").read_bytes()),
        source_commit=build_selection["source_commit"])
    boundaries(report)
    assert report["entry_build_record_verified"] is True


@pytest.mark.parametrize("change", ["head", "source", "compiler_digest", "compiler_format", "existing_output",
                                     "output_inside_checkout", "github_context"])
def test_preflight_rejects_before_any_compiler_process(build_selection, tmp_path, monkeypatch, change):
    b = builder()
    arguments = {**build_selection, "output_directory": tmp_path / "rejected"}
    if change == "head":
        arguments["source_commit"] = "0" * 40
    elif change == "source":
        original = b._snapshot
        def changed_source(path, *args, **kwargs):
            raw, identity = original(path, *args, **kwargs)
            return (b"!" + raw[1:], identity) if Path(path) == ROOT / SOURCE_PATH else (raw, identity)
        monkeypatch.setattr(b, "_snapshot", changed_source)
    elif change == "compiler_digest":
        arguments["expected_compiler_sha256"] = "0" * 64
    elif change == "compiler_format":
        script = tmp_path / "unselected-script"
        script.write_bytes(b"#!/bin/sh\nexit 0\n")
        script.chmod(0o700)
        arguments.update(compiler=script, expected_compiler_sha256=digest(script.read_bytes()))
    elif change == "existing_output":
        arguments["output_directory"].mkdir()
        (arguments["output_directory"] / "keep").write_bytes(b"original")
    elif change == "output_inside_checkout":
        arguments["output_directory"] = ROOT / "entry-build-must-not-be-created"
        assert not arguments["output_directory"].exists()
    else:
        arguments["github"] = True
        monkeypatch.setenv("GITHUB_REPOSITORY", "unselected/repository")

    def no_compiler(*args, **kwargs):
        pytest.fail("preflight rejection must precede compiler execution")
    monkeypatch.setattr(b, "_run", no_compiler)
    with pytest.raises((checker().BuildError, b.safe.ContractError, b.acquisition.AcquisitionError, OSError)):
        b.acquire_entry_build(**arguments)
    if change == "existing_output":
        assert (arguments["output_directory"] / "keep").read_bytes() == b"original"
        assert set(path.name for path in arguments["output_directory"].iterdir()) == {"keep"}
    else:
        assert not arguments["output_directory"].exists()


def authored_builds(monkeypatch, compiled_entry, *, mutate=None, failure=None):
    """Inject observed build results; toolchain queries still use the real compiler."""
    b = builder()
    original = b._run
    calls = []

    def run(argv, *, cwd, seconds, sink):
        if "-v" not in argv:
            return original(argv, cwd=cwd, seconds=seconds, sink=sink)
        directory = Path("/proc/self/fd/" + str(cwd)) if type(cwd) is int else Path(cwd)
        calls.append(directory.resolve().name)
        raw = {"stdout": b"", "stderr": b"authored compilation diagnostics\n"}
        sink("stderr", raw["stderr"])
        observed = process(900 + len(calls))
        if failure:
            observed["exit_code"] = 23
        else:
            (directory / "entry").write_bytes(compiled_entry.entry)
        if mutate:
            mutate(directory, calls)
        return observed, failure, raw

    monkeypatch.setattr(b, "_run", run)
    return calls


def test_first_failed_build_preserves_raw_prefix_without_second_attempt(build_selection, compiled_entry,
                                                                       tmp_path, monkeypatch):
    calls = authored_builds(monkeypatch, compiled_entry, failure="entry_build_process_nonzero")
    directory = tmp_path / "failed-build"
    with pytest.raises(checker().BuildError, match="entry_build_process_nonzero"):
        builder().acquire_entry_build(**build_selection, output_directory=directory)
    marker = incomplete(directory)
    assert marker["error_code"] == "entry_build_process_nonzero"
    assert calls == ["build-1"] and not (directory / "build-2").exists()
    raw = (directory / "build-1/stderr.bin").read_bytes()
    result = json.loads((directory / "build-1/result.json").read_bytes())
    assert raw == b"authored compilation diagnostics\n" and result["stderr"] == binding(raw)
    assert result["process"]["exit_code"] == 23 and result["error_code"] == marker["error_code"]
    assert "entry" not in result


def test_partial_preservation_retains_original_prefix_without_retry(build_selection, compiled_entry,
                                                                  tmp_path, monkeypatch):
    b = builder()
    calls = authored_builds(monkeypatch, compiled_entry)
    original = b.acquisition._Directory.append
    failed = []

    def partial(fd, raw):
        if Path(os.readlink("/proc/self/fd/" + str(fd))).as_posix().endswith("build-1/stderr.bin"):
            failed.append(raw)
            os.write(fd, raw[:7])
            raise OSError(errno.ENOSPC, "authored partial preservation failure")
        return original(fd, raw)

    monkeypatch.setattr(b.acquisition._Directory, "append", staticmethod(partial))
    directory = tmp_path / "partial-build"
    with pytest.raises(b.PreservationError):
        b.acquire_entry_build(**build_selection, output_directory=directory)
    marker = incomplete(directory)
    assert marker["error_code"] == "entry_build_preservation_failed"
    assert len(failed) == 1 and calls == ["build-1"]
    assert (directory / "build-1/stderr.bin").read_bytes() == b"authore"
    assert not (directory / "build-1/result.json").exists() and not (directory / "build-2").exists()


def test_entry_fsync_failure_preserves_inputs_and_prefix_without_accepted_record(build_selection, compiled_entry,
                                                                               tmp_path, monkeypatch):
    b = builder()
    calls = authored_builds(monkeypatch, compiled_entry)
    original = os.fsync
    failures = []
    def failed_entry_sync(fd):
        if Path(os.readlink("/proc/self/fd/" + str(fd))).as_posix().endswith("build-1/entry"):
            failures.append(fd)
            raise OSError(errno.EIO, "authored entry durability failure")
        return original(fd)
    monkeypatch.setattr(b.os, "fsync", failed_entry_sync)
    directory = tmp_path / "unsynchronized-entry"
    with pytest.raises(OSError, match="authored entry durability failure"):
        b.acquire_entry_build(**build_selection, output_directory=directory)
    assert incomplete(directory)["error_code"] == "entry_build_operation_failed"
    assert calls == ["build-1"] and len(failures) == 1
    assert (directory / "source.c").read_bytes() == compiled_entry.source
    assert (directory / "build-1/entry.c").read_bytes() == compiled_entry.source
    assert (directory / "build-1/entry").read_bytes() == compiled_entry.entry
    assert (directory / "build-1/stderr.bin").read_bytes() == b"authored compilation diagnostics\n"
    assert not (directory / "build-1/result.json").exists() and not (directory / "build-2").exists()


def test_late_directory_close_failure_marks_prefix_incomplete_and_releases_owned_fd(build_selection, compiled_entry,
                                                                                   tmp_path, monkeypatch):
    b = builder()
    calls = authored_builds(monkeypatch, compiled_entry)
    failed = []
    def failed_close(directory):
        failed.append(directory.fd)
        raise OSError(errno.EIO, "authored final directory sync failure")
    monkeypatch.setattr(b.acquisition._Directory, "close", failed_close)
    directory = tmp_path / "late-close-failure"
    with pytest.raises(OSError, match="authored final directory sync failure"):
        b.acquire_entry_build(**build_selection, output_directory=directory)
    assert calls == ["build-1", "build-2"] and len(failed) == 1
    with pytest.raises(OSError) as closed:
        os.fstat(failed[0])
    assert closed.value.errno == errno.EBADF
    marker = json.loads((directory / "attempt.incomplete.json").read_bytes())
    assert marker["status"] == "incomplete"
    boundaries(marker)
    assert (directory / "source.c").read_bytes() == compiled_entry.source
    assert (directory / "build-1/entry").read_bytes() == compiled_entry.entry
    assert (directory / "build-2/entry").read_bytes() == compiled_entry.entry
    with pytest.raises(checker().BuildError):
        checker().check_directory(directory,
            expected_request_sha256=digest((directory / "request.json").read_bytes()),
            expected_record_sha256=digest((directory / "record.json").read_bytes()),
            source_commit=build_selection["source_commit"])


@pytest.mark.parametrize("change", ["source_inode", "preserved_stream", "output_root"])
def test_preserved_file_and_output_directory_substitution_cannot_publish_record(build_selection, compiled_entry,
                                                                               tmp_path, monkeypatch, change):
    destination = tmp_path / "substitution"
    moved = tmp_path / "owned-original"

    def mutate(directory, calls):
        if len(calls) != 1:
            return
        if change == "source_inode":
            source = directory / "entry.c"
            original = source.read_bytes()
            source.rename(tmp_path / "original-source-inode")
            source.write_bytes(original)
        elif change == "preserved_stream":
            (directory / "stderr.bin").write_bytes(b"substituted diagnostics\n")
        else:
            destination.rename(moved)
            destination.mkdir(mode=0o700)
            (destination / "keep").write_bytes(b"replacement directory")

    authored_builds(monkeypatch, compiled_entry, mutate=mutate)
    b = builder()
    with pytest.raises((checker().BuildError, b.runtime.CapsuleError, b.safe.ContractError, OSError)):
        b.acquire_entry_build(**build_selection, output_directory=destination)
    incomplete(moved if change == "output_root" else destination)
    if change == "output_root":
        assert {path.name for path in destination.iterdir()} == {"keep"}
        assert (destination / "keep").read_bytes() == b"replacement directory"


def test_toolchain_change_after_builds_preserves_both_attempts_without_record(build_selection, compiled_entry,
                                                                          tmp_path, monkeypatch):
    b = builder()
    calls = authored_builds(monkeypatch, compiled_entry)
    original_capture, original_tool = b._capture, b._tool
    changed_after_last_query = []
    def capture(evidence, prefix, *args, **kwargs):
        result = original_capture(evidence, prefix, *args, **kwargs)
        if prefix == "query-after-ld":
            changed_after_last_query.append(True)
        return result
    def changed(lookup):
        descriptor, identity = original_tool(lookup)
        if changed_after_last_query and Path(lookup).name == "as":
            descriptor["sha256"] = "0" * 64
        return descriptor, identity
    monkeypatch.setattr(b, "_capture", capture)
    monkeypatch.setattr(b, "_tool", changed)
    directory = tmp_path / "changed-toolchain"
    with pytest.raises(checker().BuildError, match="entry_build_toolchain_changed"):
        b.acquire_entry_build(**build_selection, output_directory=directory)
    assert calls == ["build-1", "build-2"]
    assert incomplete(directory)["error_code"] == "entry_build_toolchain_changed"
    assert all((directory / build_id / "result.json").is_file() for build_id in calls)
    assert (directory / "query-after-ld.stdout.bin").read_bytes()
    assert not (directory / "toolchain-after.json").exists()


def test_process_preserves_original_bytes_and_reports_nonzero_exit(tmp_path):
    output = {"stdout": bytearray(), "stderr": bytearray()}
    observed, failure, raw = builder()._run(
        [sys.executable, "-I", "-S", "-B", "-c", "import os;os.write(1,b'out\\x00\\xff');os.write(2,b'err\\r\\n');raise SystemExit(23)"],
        cwd=tmp_path, seconds=5, sink=lambda name, chunk: output[name].extend(chunk))
    assert failure == "entry_build_process_nonzero" and observed["exit_code"] == 23
    assert raw == {"stdout": b"out\x00\xff", "stderr": b"err\r\n"}
    assert raw == {name: bytes(value) for name, value in output.items()}
    assert observed["timed_out"] is False


@pytest.mark.parametrize("exit_code", [0, 3])
def test_exited_leader_does_not_leave_its_detached_stdio_descendant_alive(tmp_path, exit_code):
    pid_file = tmp_path / "authored-descendant.pid"
    code = ("import os,signal\nchild=os.fork()\n"
            "if child==0:\n os.close(1);os.close(2)\n signal.pause()\n os._exit(0)\n"
            + "with open(" + repr(str(pid_file)) + ", 'w') as output: output.write(str(child))\n"
            + "os._exit(" + str(exit_code) + ")\n")
    descendant = None
    try:
        observed, failure, raw = builder()._run([sys.executable, "-I", "-S", "-B", "-c", code],
            cwd=tmp_path, seconds=5, sink=lambda name, chunk: None)
        descendant = int(pid_file.read_text())
        assert descendant > 1 and observed["exit_code"] == exit_code
        assert failure == (None if exit_code == 0 else "entry_build_process_nonzero")
        assert raw == {"stdout": b"", "stderr": b""}
        state = Path("/proc") / str(descendant) / "stat"
        def stopped():
            try:
                return state.read_text().split()[2] == "Z"
            except (FileNotFoundError, ProcessLookupError):
                return True
        deadline = time.monotonic() + 1
        while not stopped() and time.monotonic() < deadline:
            time.sleep(0.005)
        assert stopped(), "owned process-group descendant survived"
    finally:
        if descendant is None and pid_file.exists():
            descendant = int(pid_file.read_text())
        if descendant is not None:
            try:
                os.kill(descendant, signal.SIGKILL)
            except ProcessLookupError:
                pass


@contextmanager
def staged_overflow_child(monkeypatch, tmp_path, overflow_stream):
    """Force the other stream's second byte to remain pending until cleanup."""
    b = builder()
    other = "stderr" if overflow_stream == "stdout" else "stdout"
    overflow_fd, other_fd = (1, 2) if overflow_stream == "stdout" else (2, 1)
    limit = checker().LIMITS[overflow_stream + "_bytes"]
    gate_r, gate_w = os.pipe()
    ready_r, ready_w = os.pipe()
    descriptors = [gate_r, gate_w, ready_r, ready_w]
    children = []
    code = ("import os,signal\n" + f"os.write({other_fd},b'A')\n"
            + f"assert os.read({gate_r},1)==b'G'\n" + f"os.write({other_fd},b'B')\n"
            + f"os.write({ready_w},b'R')\n" + f"data=b'x'*{limit + 1}\n"
            + f"while data:\n count=os.write({overflow_fd},data);data=data[count:]\n"
            + "signal.pause()\n")

    def popen(_argv, **kwargs):
        child = REAL_POPEN([sys.executable, "-I", "-S", "-B", "-c", code],
                           stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           close_fds=True, pass_fds=(gate_r, ready_w), cwd=tmp_path,
                           env=ENVIRONMENT, start_new_session=True)
        children.append(child)
        for fd in (gate_r, ready_w):
            os.close(fd); descriptors.remove(fd)
        return child

    def release():
        os.write(gate_w, b"G")
        assert select.select([ready_r], [], [], 5)[0], "child did not buffer its second byte"
        assert os.read(ready_r, 1) == b"R"

    class OrderedSelector(b.selectors.DefaultSelector):
        prefix_selected = False
        def select(self, timeout=None):
            name = overflow_stream if self.prefix_selected else other
            key = self.get_key(getattr(children[0], name))
            if select.select([key.fd], [], [], timeout)[0]:
                self.prefix_selected = True
                return [(key, b.selectors.EVENT_READ)]
            return []

    monkeypatch.setattr(b.subprocess, "Popen", popen)
    monkeypatch.setattr(b.selectors, "DefaultSelector", OrderedSelector)
    try:
        yield SimpleNamespace(children=children, release=release, other=other, limit=limit)
    finally:
        for fd in descriptors:
            os.close(fd)
        for child in children:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=2)


@pytest.mark.parametrize("overflow_stream", ["stdout", "stderr"])
def test_overflow_drains_the_other_bounded_stream_after_reaping_child(tmp_path, monkeypatch, overflow_stream):
    preserved = {"stdout": bytearray(), "stderr": bytearray()}
    with staged_overflow_child(monkeypatch, tmp_path, overflow_stream) as staged:
        def sink(name, raw):
            if name == staged.other and raw == b"A":
                staged.release()
            elif name == staged.other:
                assert staged.children[0].returncode is not None, "drain must follow child termination"
            preserved[name].extend(raw)
        observed, failure, raw = builder()._run(["authored-child-only"], cwd=tmp_path, seconds=5, sink=sink)
        assert len(staged.children) == 1 and staged.children[0].returncode is not None
        assert all(getattr(staged.children[0], stream).closed for stream in ("stdout", "stderr"))
        expected = {overflow_stream: b"x" * staged.limit, staged.other: b"AB"}
    assert failure == "entry_build_" + overflow_stream + "_limit"
    assert observed[overflow_stream + "_overflow"] is True and observed["timed_out"] is False
    assert raw == expected == {name: bytes(value) for name, value in preserved.items()}


@contextmanager
def buffered_deadline_child(monkeypatch, tmp_path, *, keep_writers=False):
    """Expire the observed clock only after both real pipes have pending output."""
    b = builder()
    ready_r, ready_w = os.pipe()
    out_r, out_w = os.pipe()
    err_r, err_w = os.pipe()
    descriptors = [ready_r, ready_w, out_r, out_w, err_r, err_w]
    children = []
    clock, offset = time.monotonic, [0]
    monkeypatch.setattr(b.time, "monotonic", lambda: clock() + offset[0])
    code = ("import os,signal\nos.write(1,b'pending stdout')\nos.write(2,b'pending stderr')\n"
            + f"os.write({ready_w},b'R')\nsignal.pause()\n")

    def popen(_argv, **kwargs):
        child = REAL_POPEN([sys.executable, "-I", "-S", "-B", "-c", code], stdin=subprocess.DEVNULL,
                           stdout=out_w, stderr=err_w, close_fds=True, pass_fds=(ready_w,),
                           cwd=tmp_path, env=ENVIRONMENT, start_new_session=True)
        children.append(child)
        child.stdout = os.fdopen(out_r, "rb", buffering=0)
        child.stderr = os.fdopen(err_r, "rb", buffering=0)
        for fd in (out_r, err_r):
            descriptors.remove(fd)
        for fd in (ready_w,) if keep_writers else (ready_w, out_w, err_w):
            os.close(fd); descriptors.remove(fd)
        assert select.select([ready_r], [], [], 5)[0], "child did not buffer both streams"
        assert os.read(ready_r, 1) == b"R"
        offset[0] = 10
        return child

    monkeypatch.setattr(b.subprocess, "Popen", popen)
    try:
        yield children
    finally:
        for fd in descriptors:
            os.close(fd)
        for child in children:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=2)


@pytest.mark.parametrize("keep_writers", [False, True])
def test_timeout_drains_pending_bytes_nonblockingly_without_waiting_for_eof(tmp_path, monkeypatch, keep_writers):
    preserved = {"stdout": bytearray(), "stderr": bytearray()}
    started = time.monotonic_ns()
    with buffered_deadline_child(monkeypatch, tmp_path, keep_writers=keep_writers) as children:
        def sink(name, raw):
            assert children[0].returncode is not None
            preserved[name].extend(raw)
        observed, failure, raw = builder()._run(["authored-child-only"], cwd=tmp_path, seconds=1, sink=sink)
        assert len(children) == 1 and children[0].returncode is not None
    assert time.monotonic_ns() - started < 3_000_000_000
    assert failure == "entry_build_process_timeout" and observed["timed_out"] is True
    assert raw == {"stdout": b"pending stdout", "stderr": b"pending stderr"}
    assert raw == {name: bytes(value) for name, value in preserved.items()}


def test_drain_preservation_failure_keeps_partial_bytes_and_does_not_retry(tmp_path, monkeypatch):
    partial = tmp_path / "partial.bin"
    calls = []
    with buffered_deadline_child(monkeypatch, tmp_path) as children:
        def sink(name, raw):
            calls.append((name, raw))
            with partial.open("ab") as output:
                output.write(raw[:4])
            raise OSError(errno.ENOSPC, "authored drain sink failure")
        with pytest.raises(builder().PreservationError):
            builder()._run(["authored-child-only"], cwd=tmp_path, seconds=1, sink=sink)
        assert children[0].returncode is not None
        assert children[0].stdout.closed and children[0].stderr.closed
    assert len(calls) == 1 and partial.read_bytes() == b"pend"


def test_capture_preservation_failure_is_not_retried_by_cleanup_drain(tmp_path, monkeypatch):
    calls = []
    with staged_overflow_child(monkeypatch, tmp_path, "stderr") as staged:
        def sink(name, raw):
            calls.append((name, raw))
            staged.release()
            raise OSError(errno.ENOSPC, "authored capture sink failure")
        with pytest.raises(builder().PreservationError):
            builder()._run(["authored-child-only"], cwd=tmp_path, seconds=5, sink=sink)
        assert staged.children[0].returncode is not None
    assert calls == [("stdout", b"A")]


def test_drain_read_failure_cannot_return_a_shortened_successful_capture(tmp_path, monkeypatch):
    read = os.read
    with buffered_deadline_child(monkeypatch, tmp_path) as children:
        def broken_read(fd, size):
            if children and children[0].returncode is not None and fd == children[0].stdout.fileno():
                raise OSError(errno.EIO, "authored drain read failure")
            return read(fd, size)
        monkeypatch.setattr(builder().os, "read", broken_read)
        with pytest.raises(builder().PreservationError):
            builder()._run(["authored-child-only"], cwd=tmp_path, seconds=1, sink=lambda name, raw: None)
        assert children[0].returncode is not None


def workflow():
    return yaml.load((ROOT / WORKFLOW_PATH).read_text(), Loader=yaml.BaseLoader)


def step_by_id(job, identifier):
    return next(step for step in job["steps"] if step.get("id") == identifier)


def test_workflow_is_owner_manual_only_and_separates_compiler_from_signer_permissions():
    value = workflow()
    assert set(value["on"]) == {"workflow_dispatch"}
    assert set(value["on"]["workflow_dispatch"]["inputs"]) == {"expected_source_commit", "acknowledgement"}
    assert value["permissions"] == {"contents": "read"}
    assert value["concurrency"]["cancel-in-progress"] == "false"
    assert set(value["jobs"]) == {"build", "attest"}
    build, attest = value["jobs"]["build"], value["jobs"]["attest"]
    assert build["permissions"] == {"contents": "read"}
    assert attest["permissions"] == {"contents": "read", "actions": "read", "id-token": "write", "attestations": "write"}
    assert attest["needs"] == "build" and "needs.build.result == 'success'" in attest["if"]
    for job in (build, attest):
        assert job["runs-on"] == "ubuntu-24.04" and int(job["timeout-minutes"]) <= 15
        guard = job["steps"][0]["run"]
        for text in ('test "$GITHUB_REPOSITORY" = HKati/pulse-release-gates-0.1',
                     'test "$GITHUB_REPOSITORY_ID" = 1061766508', 'test "$GITHUB_EVENT_NAME" = workflow_dispatch',
                     'test "$GITHUB_REF" = refs/heads/main', 'test "$GITHUB_ACTOR" = HKati',
                     'test "$GITHUB_TRIGGERING_ACTOR" = HKati', 'test "$GITHUB_RUN_ATTEMPT" = 1',
                     'test "$ENTRY_BUILD_ACKNOWLEDGEMENT" = BUILD_ENTRY_ONLY_NO_RUNTIME_EXECUTION',
                     'test "$EXPECTED_SOURCE_COMMIT" = "$GITHUB_SHA"',
                     'test "$EXPECTED_SOURCE_COMMIT" = "$GITHUB_WORKFLOW_SHA"',
                     WORKFLOW_PATH + "@refs/heads/main"):
            assert text in guard
    signer_commands = "\n".join(step.get("run", "") for step in attest["steps"])
    assert "required_gate_idempotence_entry_build_v0.py\"),\n                  \"acquire\"" not in signer_commands
    assert "/usr/bin/gcc" not in signer_commands


def test_workflow_actions_are_immutable_and_checkout_has_no_write_credentials():
    pins = {"actions/checkout": "3d3c42e5aac5ba805825da76410c181273ba90b1",
            "actions/setup-python": "5fda3b95a4ea91299a34e894583c3862153e4b97",
            "actions/upload-artifact": "cf430e030ddbb5b0abf93d22962f4752f3646cd9",
            "actions/download-artifact": "9000827ccba6bdab643e8b6fd33ac0654aef8333",
            "actions/attest": "f7c74d28b9d84cb8768d0b8ca14a4bac6ef463e6"}
    for job in workflow()["jobs"].values():
        for step in job["steps"]:
            assert "continue-on-error" not in step
            if "uses" not in step:
                continue
            action, revision = step["uses"].split("@")
            assert revision == pins[action] and re.fullmatch(r"[0-9a-f]{40}", revision)
            if action == "actions/checkout":
                assert step["with"] == {"ref": "${{ github.sha }}", "fetch-depth": "1", "persist-credentials": "false"}
            elif action == "actions/setup-python":
                assert step["with"]["python-version"] == "3.11.16"


def test_workflow_checks_current_run_bytes_before_handoff_and_attestation():
    jobs = workflow()["jobs"]
    build, attest = jobs["build"], jobs["attest"]
    assert build["outputs"] == {"artifact_id": "${{ steps.preserve.outputs.artifact-id }}",
                                "request_sha256": "${{ steps.check.outputs.request_sha256 }}",
                                "record_sha256": "${{ steps.check.outputs.record_sha256 }}"}
    acquire = step_by_id(build, "acquire")["run"]
    assert 'Path("/usr/bin/gcc").resolve(strict=True)' in acquire
    assert '"--compiler-sha256", selected["sha256"]' in acquire and '"--github"' in acquire
    assert '"--source-commit", os.environ["EXPECTED_SOURCE_COMMIT"]' in acquire
    checked = step_by_id(build, "check")["run"]
    assert checked.index("check_required_gate_idempotence_entry_build_v0.py") < checked.index('open(os.environ["GITHUB_OUTPUT"]')
    download = next(step for step in attest["steps"] if step.get("uses", "").startswith("actions/download-artifact@"))
    assert download["with"]["artifact-ids"] == "${{ needs.build.outputs.artifact_id }}"
    assert download["with"]["repository"] == "${{ github.repository }}"
    assert download["with"]["run-id"] == "${{ github.run_id }}" and download["with"]["digest-mismatch"] == "error"
    assert download["with"]["path"].endswith("/input") and "name" not in download["with"]
    recheck = step_by_id(attest, "check")["run"]
    for text in ('"--request-sha256", os.environ["EXPECTED_REQUEST_SHA256"]',
                 '"--record-sha256", os.environ["EXPECTED_RECORD_SHA256"]',
                 'checker.need(request["context"] == expected_context',
                 '"run_id": int(os.environ["GITHUB_RUN_ID"])', '"workflow_sha": os.environ["GITHUB_WORKFLOW_SHA"]'):
        assert text in recheck
    ids = [step.get("id") for step in attest["steps"]]
    assert ids.index("check") < ids.index("attest") < ids.index("bundle") < ids.index("verify")
    attestation = step_by_id(attest, "attest")["with"]
    assert attestation["subject-path"].endswith("/input/evidence/record.json")
    assert attestation["create-storage-record"] == "false" and "predicate" not in attestation
    assert "predicate-type" not in attestation


def test_workflow_verifies_actual_signature_and_preserves_original_failure_prefixes():
    jobs = workflow()["jobs"]
    verify = step_by_id(jobs["attest"], "verify")["run"]
    for text in ('timeout --signal=KILL 120s gh attestation verify "$signer_root/input/evidence/record.json"',
                 'ulimit -f 1024', '--bundle "$signer_root/attestation.bundle.json"',
                 '--repo HKati/pulse-release-gates-0.1',
                 '--signer-workflow HKati/pulse-release-gates-0.1/' + WORKFLOW_PATH,
                 '--signer-digest "$GITHUB_WORKFLOW_SHA" --source-digest "$EXPECTED_SOURCE_COMMIT"',
                 '--source-ref refs/heads/main', '--predicate-type https://slsa.dev/provenance/v1',
                 '--cert-oidc-issuer https://token.actions.githubusercontent.com',
                 '--deny-self-hosted-runners --format json', 'verification.stdout.json',
                 'verification.stderr.bin', 'verification.exit-code.txt', 'exit "$verification_exit_code"'):
        assert text in verify
    bundle = step_by_id(jobs["attest"], "bundle")["run"]
    assert '(root / "attestation.bundle.json").open("xb")' in bundle and "output.write(raw)" in bundle
    for job in jobs.values():
        uploads = [step for step in job["steps"] if step.get("uses", "").startswith("actions/upload-artifact@")]
        assert len(uploads) == 1
        upload = uploads[0]
        assert upload["if"] == "always() && steps.prefix.outcome == 'success'"
        assert upload["with"]["overwrite"] == "false" and upload["with"]["if-no-files-found"] == "error"
        assert upload["with"]["compression-level"] == "0"
    text = (ROOT / WORKFLOW_PATH).read_text()
    assert "sudo " not in text and "sysctl " not in text and "workflow_call" not in text
    assert "B2 remains incomplete" in text and "keep #2879 open" in text


def test_workflow_shell_and_embedded_python_parse_without_executing_them(tmp_path):
    for job_id, job in workflow()["jobs"].items():
        for index, step in enumerate(job["steps"]):
            if "run" not in step:
                continue
            raw = step["run"]
            path = tmp_path / (job_id + "-" + str(index) + ".sh")
            path.write_text(raw)
            checked = subprocess.run(["/bin/bash", "-n", str(path)], capture_output=True, timeout=5)
            assert checked.returncode == 0, checked.stderr.decode(errors="replace")
            for snippet in re.findall(r"<<'PY'[^\n]*\n(.*?)^PY$", raw, re.MULTILINE | re.DOTALL):
                ast.parse(snippet, feature_version=(3, 11))


def test_entry_build_module_registered_once_and_targeted_manifest_unchanged():
    def entries(name):
        return [value for line in (ROOT / "ci" / name).read_text().splitlines()
                if (value := line.split("#", 1)[0].strip())]
    tools, targeted = entries("tools-tests.list"), entries("pytest-tests.list")
    assert len(tools) == len(set(tools)) == 189 and tools.count(SELF) == 1
    assert len(targeted) == len(set(targeted)) == 40 and SELF not in targeted


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))

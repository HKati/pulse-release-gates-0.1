"""Synthetic, offline tests of Q3 preparation; never acquisition evidence."""
from __future__ import annotations

import ast
import errno
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from unittest import mock

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).absolute().parents[1]
TOOL = ROOT / "PULSE_safe_pack_v0/tools/prepare_q3_archived_input_bundle_v0.py"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


prep = load("q3_preparation_test_tool", TOOL)
fb = load("q3_preparation_test_fixtures", ROOT / "tests/fixtures/q3_reference_v0/fixture_builder.py")
ROLES = tuple(prep.ARTIFACT_NAMES)


def selected(tmp_path, case=1):
    fixture = fb.materialize(case, tmp_path / "originals", resources_root=ROOT, producer_source_root=ROOT)
    bundle, expected = fb.read_json(fixture.bundle), fb.read_json(fixture.expected)
    selection = {
        "record_type": "q3_archived_input_selection_v0", "selection_id": "synthetic-selection-001",
        "contract_profile": prep.PROFILE_ID,
        **{key: bundle[key] for key in ("dataset_id", "reduction_id", "observation_subject")},
        "selection_origin": {
            "kind": "synthetic_test_anchor", "basis_reference": f"urn:pulse:test:case-{case}",
            "access_use_basis": "Synthetic conformance data; not acquired evidence.",
            "selected_before_scoring": True, "original_runtime_evidence_reference": None,
        },
        "artifacts": bundle["artifacts"], "resource_bindings": dict(prep.RESOURCE_SHA256),
        "expected_producer": expected["expected_producer"],
        "authority_effect": "none", "production_gate_eligible": False,
    }
    path = tmp_path / "selection.json"
    path.write_bytes(prep.canonical(selection))
    return fixture, path, selection, tmp_path / "prepared"


def run(data, resources=ROOT, producer=ROOT):
    fixture, path, _, output = data
    return prep.prepare(path, fixture.root, resources, producer, output)


def save(data):
    data[1].write_bytes(prep.canonical(data[2]))


def rejection(data, code=None, **kwargs):
    with pytest.raises(prep.PreparationError) as caught:
        run(data, **kwargs)
    if code:
        assert caught.value.code == code
    assert not data[3].exists()
    return caught.value


def copied_resources(tmp_path):
    root = fb.copy_resources(tmp_path / "resources", ROOT)
    destination = root / prep.SELECTION_SCHEMA_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / prep.SELECTION_SCHEMA_PATH, destination)
    return root


def invoke(tool, args, cwd):
    return subprocess.run([sys.executable, str(tool), *map(str, args)], cwd=cwd,
                          env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"},
                          capture_output=True, text=True, timeout=60, check=False)


def score_and_check(output, expected_exit):
    common = ["--bundle", output / "input_bundle.json", "--expected", output / "expected_context.json",
              "--resources-root", ROOT, "--producer-source-root", ROOT]
    summary = output / "summary.json"
    producer = invoke(ROOT / fb.PRODUCER_PATH, [*common, "--out", summary], output)
    assert producer.returncode == expected_exit, producer.stderr
    checker = invoke(ROOT / fb.CHECKER_PATH, [*common, "--summary", summary], output)
    assert checker.returncode == 0, checker.stdout + checker.stderr
    receipt = json.loads(checker.stdout)
    assert receipt["verification_result"] == "MATCH"
    return fb.read_json(summary)


def test_selection_schema_valid_and_pinned():
    data = (ROOT / prep.SELECTION_SCHEMA_PATH).read_bytes()
    assert prep.sha256(data) == prep.SELECTION_SCHEMA_SHA256
    Draft202012Validator.check_schema(json.loads(data))


@pytest.mark.parametrize("case,exit_code", [(1, 0), (12, 1), (7, 1)])
def test_existing_producer_checker_roundtrip_preserves_result(tmp_path, case, exit_code):
    data = selected(tmp_path, case)
    originals = {role: (data[0].root / entry["path"]).read_bytes()
                 for role, entry in data[2]["artifacts"].items()}
    receipt = run(data)
    assert receipt["preparation_result"] == "PREPARED"
    for role, name in prep.ARTIFACT_NAMES.items():
        assert (data[3] / name).read_bytes() == originals[role]
        assert (data[0].root / data[2]["artifacts"][role]["path"]).read_bytes() == originals[role]
    assert not (data[3] / "summary.json").exists()
    result = score_and_check(data[3], exit_code)
    assert result["pass"] is (exit_code == 0)
    assert result["claims"]["authority_effect"] == "none"
    assert result["claims"]["current_run_evidence"] is False
    if case == 12:
        assert result["coverage"]["excluded_in_any_dimension_count"] == 48
    if case == 7:
        assert result["counts"]["n_unknown_ignored"] == 200


def test_exact_member_inventory_and_claims(tmp_path):
    data = selected(tmp_path)
    receipt = run(data)
    out = data[3]
    assert set(p.name for p in out.iterdir()) == {
        *prep.ARTIFACT_NAMES.values(), "input_bundle.json", "expected_context.json",
        "input_selection.json", "preparation_manifest.json"}
    manifest_bytes = (out / "preparation_manifest.json").read_bytes()
    assert prep.sha256(manifest_bytes) == receipt["preparation_manifest_sha256"]
    manifest = json.loads(manifest_bytes)
    for entry in manifest["members"]:
        raw = (out / entry["path"]).read_bytes()
        assert len(raw) == entry["size_bytes"]
        assert prep.sha256(raw) == entry["sha256"]
    assert len(manifest["members"]) == 6
    assert (out / "input_selection.json").read_bytes() == data[1].read_bytes()
    assert manifest["claims"] == prep.CLAIMS
    assert manifest["original_runtime_identity_status"] == "unavailable"
    assert manifest["expected_producer_runtime_status"] == "caller_selected_not_executed"
    assert out.stat().st_mode & 0o777 == 0o700
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in out.iterdir())


def test_same_selection_repeated_at_different_destination_is_deterministic(tmp_path):
    data = selected(tmp_path)
    run(data)
    second = (*data[:3], tmp_path / "other")
    run(second)
    assert {p.name: p.read_bytes() for p in data[3].iterdir()} == {
        p.name: p.read_bytes() for p in second[3].iterdir()}


@pytest.mark.parametrize("role", ROLES)
def test_changed_original_rejects_unchanged_selection(tmp_path, role):
    data = selected(tmp_path)
    path = data[0].root / data[2]["artifacts"][role]["path"]
    path.write_bytes(path.read_bytes() + b" ")
    rejection(data, "FILE_BINDING_MISMATCH")


@pytest.mark.parametrize("role", ROLES)
def test_wrong_selected_size_rejects(tmp_path, role):
    data = selected(tmp_path)
    data[2]["artifacts"][role]["size_bytes"] += 1
    save(data)
    rejection(data, "FILE_BINDING_MISMATCH")


@pytest.mark.parametrize("field", ["dataset_id", "expected_producer", "selection_origin", "resource_bindings"])
def test_missing_selection_field_rejects(tmp_path, field):
    data = selected(tmp_path)
    del data[2][field]
    save(data)
    rejection(data, "SELECTION_INVALID")


def test_missing_selection_file_rejects(tmp_path):
    data = selected(tmp_path)
    data[1].unlink()
    rejection(data, "INPUT_UNAVAILABLE")


@pytest.mark.parametrize("location", ["root", "origin", "artifact", "producer"])
def test_closed_selection_objects_reject_extras(tmp_path, location):
    data = selected(tmp_path)
    target = {"root": data[2], "origin": data[2]["selection_origin"],
              "artifact": data[2]["artifacts"]["examples_jsonl"],
              "producer": data[2]["expected_producer"]}[location]
    target["report_derived_override"] = True
    save(data)
    rejection(data, "SELECTION_INVALID")


@pytest.mark.parametrize("resource", list(prep.RESOURCE_PATHS))
@pytest.mark.parametrize("coherent_rebind", [False, True])
def test_modified_resources_cannot_reauthorize_themselves(tmp_path, resource, coherent_rebind):
    data = selected(tmp_path)
    resources = copied_resources(tmp_path)
    path = resources / prep.RESOURCE_PATHS[resource]
    changed = path.read_bytes() + b" \n"
    path.write_bytes(changed)
    if coherent_rebind:
        data[2]["resource_bindings"][resource] = prep.sha256(changed)
        save(data)
    rejection(data, "SELECTION_INVALID" if coherent_rebind else "RESOURCE_BINDING_MISMATCH", resources=resources)


def test_modified_selection_schema_rejects_before_use(tmp_path):
    data = selected(tmp_path)
    resources = copied_resources(tmp_path)
    schema = resources / prep.SELECTION_SCHEMA_PATH
    schema.write_bytes(schema.read_bytes() + b"\n")
    rejection(data, "RESOURCE_BINDING_MISMATCH", resources=resources)


@pytest.mark.parametrize("coherent_rebind", [False, True])
def test_modified_producer_source_rejects_without_executing_it(tmp_path, coherent_rebind):
    data = selected(tmp_path)
    source = fb.copy_producer_source(tmp_path / "producer", ROOT)
    path = source / prep.PRODUCER_PATH
    path.write_bytes(path.read_bytes() + b"\nraise RuntimeError('must not execute')\n")
    if coherent_rebind:
        data[2]["expected_producer"]["source_files"][0]["sha256"] = prep.sha256(path.read_bytes())
        save(data)
    rejection(data, "SELECTION_INVALID" if coherent_rebind else "PRODUCER_BINDING_MISMATCH", producer=source)


def test_exact_resources_and_producer_at_alternate_roots_supported(tmp_path):
    data = selected(tmp_path)
    resources = copied_resources(tmp_path)
    source = fb.copy_producer_source(tmp_path / "producer", ROOT)
    assert run(data, resources, source)["preparation_result"] == "PREPARED"


@pytest.mark.parametrize("invalid", ["../examples.jsonl", "./examples.jsonl", "/etc/passwd", "a//b", "a/../b", "a\\b"])
def test_unsafe_selected_path_rejects(tmp_path, invalid):
    data = selected(tmp_path)
    data[2]["artifacts"]["examples_jsonl"]["path"] = invalid
    save(data)
    rejection(data)


def test_symlink_original_rejects(tmp_path):
    data = selected(tmp_path)
    path = data[0].examples
    real = path.with_suffix(".real")
    path.rename(real)
    path.symlink_to(real)
    rejection(data, "INPUT_UNAVAILABLE")


def test_symlink_source_directory_rejects(tmp_path):
    data = selected(tmp_path)
    alias = tmp_path / "alias"
    alias.symlink_to(data[0].root, target_is_directory=True)
    with pytest.raises(prep.PreparationError, match="INPUT_UNAVAILABLE"):
        prep.prepare(data[1], alias, ROOT, ROOT, data[3])
    assert not data[3].exists()


@pytest.mark.parametrize("kind", ["empty_directory", "populated_directory", "file", "symlink", "dangling_symlink"])
def test_occupied_output_preserved(tmp_path, kind):
    data = selected(tmp_path)
    out = data[3]
    if kind == "empty_directory":
        out.mkdir()
    elif kind == "populated_directory":
        out.mkdir()
        (out / "owner.txt").write_text("original")
    elif kind == "file":
        out.write_text("original")
    elif kind == "symlink":
        out.symlink_to(data[0].root, target_is_directory=True)
    else:
        out.symlink_to(tmp_path / "missing")
    with pytest.raises(prep.PreparationError, match="OUTPUT_EXISTS"):
        run(data)
    if kind == "file":
        assert out.read_text() == "original"
    elif kind == "populated_directory":
        assert (out / "owner.txt").read_text() == "original"
    elif kind.endswith("symlink"):
        assert out.is_symlink()
    else:
        assert not list(out.iterdir())
    assert not list(tmp_path.glob(".q3-preparing-*"))


def test_symlink_output_parent_preserved(tmp_path):
    data = selected(tmp_path)
    target = tmp_path / "actual"
    target.mkdir()
    parent = tmp_path / "alias"
    parent.symlink_to(target, target_is_directory=True)
    rejection((*data[:3], parent / "new"), "OUTPUT_WRITE_FAILED")
    assert not list(target.iterdir())


def test_output_race_never_replaces_even_an_empty_directory(tmp_path):
    data = selected(tmp_path)
    native = prep.rename_no_replace
    def race(fn, parent, old, new):
        os.mkdir(new, dir_fd=parent)
        native(fn, parent, old, new)
    with mock.patch.object(prep, "rename_no_replace", side_effect=race):
        with pytest.raises(prep.PreparationError, match="OUTPUT_EXISTS"):
            run(data)
    assert data[3].is_dir() and not list(data[3].iterdir())
    assert not list(tmp_path.glob(".q3-preparing-*"))


@pytest.mark.parametrize("failure", ["partial_write", "zero_write", "file_fsync", "directory_fsync", "parent_fsync"])
def test_interrupted_output_cleanup_and_retry(tmp_path, failure):
    data = selected(tmp_path)
    native_write, native_fsync = os.write, os.fsync
    count = 0
    def write(fd, b):
        nonlocal count
        count += 1
        if failure == "zero_write":
            return 0
        if count == 1:
            return native_write(fd, b[:7])
        raise OSError(errno.ENOSPC, "synthetic quota failure")
    def sync(fd):
        nonlocal count
        count += 1
        # Seven file syncs, then stage directory, then publication parent.
        selected_count = {"file_fsync": 1, "directory_fsync": 8, "parent_fsync": 9}[failure]
        if count == selected_count:
            raise OSError(errno.EIO, "synthetic sync failure")
        return native_fsync(fd)
    method = "write" if failure in ("partial_write", "zero_write") else "fsync"
    with mock.patch.object(prep.os, method, side_effect=write if method == "write" else sync):
        error = rejection(data, "OUTPUT_WRITE_FAILED")
    assert error.cleanup_complete is True
    assert not list(tmp_path.glob(".q3-preparing-*"))
    assert run(data)["preparation_result"] == "PREPARED"


def test_cleanup_failure_never_claims_success_and_keeps_primary_error(tmp_path):
    data = selected(tmp_path)
    native_rename = prep.ensure_platform()
    with mock.patch.object(prep, "ensure_platform", return_value=native_rename), \
         mock.patch.object(prep.os, "write", side_effect=OSError(errno.ENOSPC, "quota")), \
         mock.patch.object(prep.os, "unlink", side_effect=PermissionError("cleanup denied")):
        error = rejection(data, "OUTPUT_WRITE_FAILED")
    assert error.cleanup_complete is False
    stages = list(tmp_path.glob(".q3-preparing-*"))
    assert len(stages) == 1
    assert not (stages[0] / "preparation_manifest.json").exists()
    # Leftover staging is never reused as a successful package.
    assert run(data)["preparation_result"] == "PREPARED"


def test_cleanup_preserves_replaced_staged_file_and_unrelated_content(tmp_path):
    data = selected(tmp_path)
    native = prep.write_member
    replaced_inode = None
    def replace_then_fail(directory, name, raw, created):
        nonlocal replaced_inode
        native(directory, name, raw, created)
        os.rename(name, "retained-original", src_dir_fd=directory, dst_dir_fd=directory)
        replacement = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=directory)
        os.write(replacement, b"replacement")
        replaced_inode = os.fstat(replacement).st_ino
        os.close(replacement)
        raise OSError(errno.EIO, "injected interruption")
    with mock.patch.object(prep, "write_member", side_effect=replace_then_fail):
        error = rejection(data, "OUTPUT_WRITE_FAILED")
    assert error.cleanup_complete is False
    stage = next(tmp_path.glob(".q3-preparing-*"))
    assert (stage / "retained-original").exists()
    replacement = next(p for p in stage.iterdir() if p.stat().st_ino == replaced_inode)
    assert replacement.read_bytes() == b"replacement"


def test_parent_replacement_is_detected_and_replacement_is_preserved(tmp_path):
    data = selected(tmp_path)
    parent = tmp_path / "parent"
    parent.mkdir()
    data = (*data[:3], parent / "prepared")
    original = prep.check_parent_binding
    done = False
    def replaced(path, expected):
        nonlocal done
        if not done:
            parent.rename(tmp_path / "moved-parent")
            parent.mkdir()
            (parent / "owner.txt").write_text("keep")
            done = True
        return original(path, expected)
    with mock.patch.object(prep, "check_parent_binding", side_effect=replaced):
        rejection(data, "OUTPUT_BINDING_MISMATCH")
    assert (parent / "owner.txt").read_text() == "keep"
    assert not list((tmp_path / "moved-parent").iterdir())


def test_changed_output_bytes_are_caught_before_publication(tmp_path):
    data = selected(tmp_path)
    native = prep.write_member
    def corrupt(directory, name, raw, created):
        native(directory, name, raw, created)
        if name == "examples.jsonl":
            fd = os.open(name, os.O_WRONLY, dir_fd=directory)
            os.write(fd, b"!")
            os.close(fd)
    with mock.patch.object(prep, "write_member", side_effect=corrupt):
        rejection(data, "OUTPUT_BINDING_MISMATCH")
    assert not list(tmp_path.glob(".q3-preparing-*"))


def test_unsupported_no_replace_primitive_fails_closed(tmp_path):
    data = selected(tmp_path)
    def unsupported(*_args):
        prep.ctypes.set_errno(errno.ENOSYS)
        return -1
    with mock.patch.object(prep, "ensure_platform", return_value=unsupported):
        rejection(data, "UNSUPPORTED_FILESYSTEM")
    assert not list(tmp_path.glob(".q3-preparing-*"))


def test_unsupported_platform_does_not_create_output(tmp_path):
    data = selected(tmp_path)
    with mock.patch.object(prep.sys, "platform", "win32"):
        rejection(data, "UNSUPPORTED_FILESYSTEM")


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}',
                                 b'{"x":"\\ud800"}', b'\xef\xbb\xbf{}', b'\xff'])
def test_strict_json_rejects_unsupported_encoding_and_numbers(raw):
    with pytest.raises(prep.PreparationError, match="JSON_INVALID"):
        prep.strict_json(raw)


def test_selection_size_limit(tmp_path):
    data = selected(tmp_path)
    data[1].write_bytes(b" " * (prep.MAX_SELECTION_BYTES + 1))
    rejection(data, "INPUT_LIMIT")


@pytest.mark.parametrize("representation", ["crlf", "missing_final_lf", "blank_line", "invalid_utf8"])
def test_preparation_never_normalizes_original_jsonl(tmp_path, representation):
    data = selected(tmp_path)
    raw = data[0].examples.read_bytes()
    changed = {"crlf": raw.replace(b"\n", b"\r\n"), "missing_final_lf": raw[:-1],
               "blank_line": raw + b"\n", "invalid_utf8": raw.replace(b"Synthetic", b"\xff", 1)}[representation]
    fb.replace_examples_bytes(data[0], changed)
    bundle = fb.read_json(data[0].bundle)
    data[2]["artifacts"] = bundle["artifacts"]
    save(data)
    rejection(data)
    assert data[0].examples.read_bytes() == changed


@pytest.mark.parametrize("case,reason", [(28, "DUPLICATE_EXAMPLE_ID"), (35, "LABEL_BINDING_MISMATCH")])
def test_source_join_failures_reject_before_copy(tmp_path, case, reason):
    rejection(selected(tmp_path, case), reason)


def test_selected_dataset_identity_must_match_manifest(tmp_path):
    data = selected(tmp_path)
    data[2]["dataset_id"] = "different-dataset"
    save(data)
    rejection(data, "MANIFEST_BINDING_MISMATCH")


def test_prep_does_not_silently_validate_or_fix_eligibility(tmp_path):
    data = selected(tmp_path, 20)  # Empty context, still labelled eligible: semantic inconsistency.
    raw = data[0].labels.read_bytes()
    receipt = run(data)
    assert receipt["claims"]["full_q3_semantics_verified"] is False
    assert (data[3] / "q1_labels.jsonl").read_bytes() == raw
    args = ["--bundle", data[3] / "input_bundle.json", "--expected", data[3] / "expected_context.json",
            "--resources-root", ROOT, "--producer-source-root", ROOT, "--out", data[3] / "summary.json"]
    completed = invoke(ROOT / fb.PRODUCER_PATH, args, data[3])
    assert completed.returncode == 2
    assert fb.read_json(data[3] / "summary.json")["input_validity"] == "INVALID"


def test_original_and_expected_producer_runtime_are_distinct(tmp_path):
    data = selected(tmp_path)
    data[2]["observation_subject"].update(kind="archived_input", runtime_identity=None)
    data[2]["selection_origin"]["kind"] = "caller_selected_archived_input"
    data[2]["expected_producer"]["python_version"] = "3.11.16"
    save(data)
    run(data)
    expected = fb.read_json(data[3] / "expected_context.json")
    assert expected["observation_subject"]["runtime_identity"] is None
    assert expected["expected_producer"]["python_version"] == "3.11.16"
    assert expected["expectation_origin"] == "caller_selected_archived_input"


def test_claimed_original_runtime_requires_a_reference_but_is_not_authenticated(tmp_path):
    data = selected(tmp_path)
    data[2]["observation_subject"].update(kind="archived_input", runtime_identity={
        "repository": "synthetic/test", "source_commit": "a" * 40, "run_id": "123", "run_attempt": 1})
    data[2]["selection_origin"].update(kind="caller_selected_archived_input",
        original_runtime_evidence_reference="urn:synthetic:declared-runtime")
    save(data)
    run(data)
    manifest = fb.read_json(data[3] / "preparation_manifest.json")
    assert manifest["original_runtime_identity_status"] == "caller_declared_not_verified"
    assert manifest["claims"]["current_run_evidence"] is False


def test_runtime_identity_without_reference_rejects(tmp_path):
    data = selected(tmp_path)
    data[2]["observation_subject"].update(kind="archived_input", runtime_identity={
        "repository": "synthetic/test", "source_commit": "a" * 40, "run_id": "123", "run_attempt": 1})
    data[2]["selection_origin"]["kind"] = "caller_selected_archived_input"
    save(data)
    rejection(data, "RUNTIME_DECLARATION_MISMATCH")


def test_synthetic_cannot_be_silently_relabelled_archived(tmp_path):
    data = selected(tmp_path)
    data[2]["selection_origin"]["kind"] = "caller_selected_archived_input"
    save(data)
    rejection(data, "SELECTION_ORIGIN_MISMATCH")


def test_selection_before_scoring_is_a_required_declaration(tmp_path):
    data = selected(tmp_path)
    data[2]["selection_origin"]["selected_before_scoring"] = False
    save(data)
    rejection(data, "SELECTION_INVALID")


def test_snapshot_stable_hardlink_alias_reuses_bytes(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.write_bytes(b"original")
    os.link(a, b)
    snapshots = prep.Snapshots()
    assert snapshots.read(a) == b"original"
    with mock.patch.object(prep.os, "read", side_effect=AssertionError("second read")):
        assert snapshots.read(b) == b"original"


@pytest.mark.parametrize("repeat_path", [False, True])
def test_snapshot_detects_same_length_rewrite(tmp_path, repeat_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.write_bytes(b"original")
    os.link(a, b)
    snapshots = prep.Snapshots()
    snapshots.read(a)
    before = b.stat()
    b.write_bytes(b"changed!")
    os.utime(b, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))
    with pytest.raises(prep.PreparationError, match="FILE_BINDING_MISMATCH"):
        snapshots.read(a if repeat_path else b)


def test_snapshot_detects_mutation_during_read(tmp_path):
    path = tmp_path / "original"
    path.write_bytes(b"original")
    native = os.read
    changed = False
    def mutate(fd, count):
        nonlocal changed
        raw = native(fd, count)
        if raw and not changed:
            before = path.stat()
            path.write_bytes(b"changed!")
            os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))
            changed = True
        return raw
    with mock.patch.object(prep.os, "read", side_effect=mutate):
        with pytest.raises(prep.PreparationError, match="FILE_BINDING_MISMATCH"):
            prep.Snapshots().read(path)


def test_final_source_recheck_prevents_late_mutation(tmp_path):
    data = selected(tmp_path)
    native = prep.build_package
    def mutate(*args, **kwargs):
        package = native(*args, **kwargs)
        data[0].labels.write_bytes(data[0].labels.read_bytes() + b"\n")
        return package
    with mock.patch.object(prep, "build_package", side_effect=mutate):
        rejection(data, "FILE_BINDING_MISMATCH")


def test_metric_modules_and_execution_are_not_used_in_preparation(tmp_path):
    data = selected(tmp_path)
    tree = ast.parse(TOOL.read_text())
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(x.name for x in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any(x.startswith(("subprocess", "requests", "urllib", "importlib")) for x in imports)
    assert "wilson(" not in TOOL.read_text()
    with mock.patch.object(subprocess, "run", side_effect=AssertionError("must not execute another tool")):
        assert run(data)["claims"]["metric_evaluated"] is False


def test_cli_success_and_missing_selection_fail_closed(tmp_path):
    data = selected(tmp_path)
    args = ["--selection", data[1], "--source-root", data[0].root, "--out-dir", data[3],
            "--resources-root", ROOT, "--producer-source-root", ROOT]
    completed = invoke(TOOL, args, tmp_path)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["preparation_result"] == "PREPARED"
    assert completed.stderr == ""
    data[1].unlink()
    again = invoke(TOOL, args, tmp_path)
    assert again.returncode == 2
    assert again.stdout == ""
    assert "INPUT_UNAVAILABLE" in again.stderr
    assert "Traceback" not in again.stderr


def test_receipt_delivery_failure_is_not_success(tmp_path, capsys):
    data = selected(tmp_path)
    sink = mock.Mock()
    sink.buffer.write.side_effect = BrokenPipeError("simulated closed receipt consumer")
    arguments = ["--selection", str(data[1]), "--source-root", str(data[0].root),
                 "--out-dir", str(data[3]), "--resources-root", str(ROOT),
                 "--producer-source-root", str(ROOT)]
    with mock.patch.object(prep.sys, "stdout", sink):
        assert prep.main(arguments) == 2
    assert "RECEIPT_WRITE_FAILED" in capsys.readouterr().err
    assert (data[3] / "preparation_manifest.json").is_file()
    with pytest.raises(prep.PreparationError, match="OUTPUT_EXISTS"):
        run(data)


def test_end_to_end_changed_hardlink_alias_cannot_mix_originals(tmp_path):
    data = selected(tmp_path)
    examples = data[0].examples
    labels = data[0].labels
    original_labels = labels.read_bytes()
    labels.unlink()
    os.link(examples, labels)
    native = prep.Snapshots.read
    example_seen = False
    changed = False
    def alias_rewrite(snapshots, path, limit=prep.MAX_FILE_BYTES):
        nonlocal example_seen, changed
        if Path(path) == labels and not changed:
            assert example_seen
            before = labels.stat()
            labels.write_bytes(original_labels)
            os.utime(labels, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))
            changed = True
        raw = native(snapshots, path, limit)
        if Path(path) == examples:
            example_seen = True
        return raw
    with mock.patch.object(prep.Snapshots, "read", alias_rewrite):
        rejection(data, "FILE_BINDING_MISMATCH")
    assert changed


def test_distinct_original_inodes_remain_independent(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    first.write_bytes(b"same")
    second.write_bytes(b"same")
    snapshots = prep.Snapshots()
    snapshots.read(first)
    second.write_bytes(b"next")
    assert snapshots.read(second) == b"next"
    assert snapshots.read(first) == b"same"


def test_directory_and_fifo_are_not_input_files(tmp_path):
    directory = tmp_path / "dir"
    directory.mkdir()
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    for path in (directory, fifo):
        with pytest.raises(prep.PreparationError, match="INPUT_UNAVAILABLE"):
            prep.Snapshots().read(path)


def test_original_files_can_be_read_only(tmp_path):
    data = selected(tmp_path)
    for role in ROLES:
        (data[0].root / data[2]["artifacts"][role]["path"]).chmod(0o400)
    assert run(data)["preparation_result"] == "PREPARED"
    for role in ROLES:
        assert (data[0].root / data[2]["artifacts"][role]["path"]).stat().st_mode & 0o777 == 0o400


def test_row_file_and_dimension_limits_are_not_silent_truncation(tmp_path):
    data = selected(tmp_path)
    for name, limit in (("MAX_LINE_BYTES", 10), ("MAX_ROWS", 1), ("MAX_DIMENSIONS", 0)):
        with mock.patch.object(prep, name, limit):
            rejection(data)
    with pytest.raises(prep.PreparationError, match="INPUT_LIMIT"):
        prep.Snapshots().read(data[0].examples, limit=10)

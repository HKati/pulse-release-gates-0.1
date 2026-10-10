#!/usr/bin/env python3
"""Independent Q2 admission: reacquire inputs and recompute, never import producer verdicts."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import platform
import sys
import unicodedata

sys.path.insert(0, str(Path(__file__).resolve().parent))
import q2_intake_io_v0 as io
import load_q2_release_intake_v0 as loader


def check_bound_inputs(repo, private, request, profile, result, deadline):
    """Separate member, subject and metric derivations from stable reacquired bytes."""
    # The request is not allowed to select an alternate capture or semantic profile.
    io.require(io.encode(request["capture_expectation"]) == io.encode(profile["capture_expectation"]) and
               io.encode(request["selection"]) == io.encode(profile["selection"]), "q2_admission_rejected")
    for name in ("comparison_profile", "reduction_profile", "native_verification_mode"):
        io.require(request[name] == profile[name], "q2_admission_rejected")
    limits = profile["limits"]
    for filename, expected in (("capture.zip", profile["capture_expectation"]),
                               ("capsule.zip", request["release_subject"])):
        actual = io.file_binding(private / filename, limits["capsule_archive_bytes"], deadline)
        io.require(actual == {k: expected[k] for k in ("archive_size_bytes", "archive_sha256")}, "q2_digest_mismatch")
    with io.Archive(private / "capture.zip", maximum_bytes=profile["capture_expectation"]["archive_size_bytes"],
                    max_members=profile["capture_members"], member_bytes=limits["capture_member_bytes"],
                    expanded_bytes=limits["capture_expanded_bytes"], deadline=deadline,
                    expected_sha256=profile["capture_expectation"]["archive_sha256"]) as capture:
        descriptions = {n: capture.inspect(n) for n in sorted(capture.members)}
        io.require(len(descriptions) == profile["capture_members"] and
                   sum(v["size"] for v in descriptions.values()) == profile["capture_expanded_bytes"], "q2_capture_rejected")
        payloads = {n: capture.read(n) for n in profile["capture_file_bindings"]}
        for n, expected in profile["capture_file_bindings"].items():
            io.require(descriptions[n]["size"] == expected["size_bytes"] and
                       descriptions[n]["sha256"] == expected["sha256"], "q2_capture_rejected")
        documents = {n: io.strict_json(b) for n, b in payloads.items()}
        record = documents["capture.json"]
        seen = set()
        for item in record["evidence"]:
            path = item["path"]
            io.require(path not in seen and path != "capture.json" and path in descriptions, "q2_capture_rejected")
            seen.add(path)
            io.require(descriptions[path]["kind"] == "file" and
                       descriptions[path]["size"] == item["size"] and
                       descriptions[path]["sha256"] == item["sha256"], "q2_capture_rejected")
        io.require(seen | {"capture.json"} == set(descriptions), "q2_capture_rejected")
        pre = documents["capture-prelaunch.json"]
        subject = documents["capture-subject.json"]
        expected_origin = profile["capture_expectation"]
        expected_binding = {"prelaunch_sha256": io.digest(payloads["capture-prelaunch.json"]),
                            "subject_sha256": io.digest(payloads["capture-subject.json"]),
                            **{k: expected_origin[k] for k in ("run_id", "run_attempt", "source_commit")}}
        io.require(io.encode(pre["source_files"]) == io.encode(profile["archived_source_files"]), "q2_source_mismatch")
        for item in profile["archived_source_files"]:
            actual = descriptions["source/" + item["path"]]
            io.require(actual["size"] == item["size"] and actual["sha256"] == item["sha256"], "q2_source_mismatch")
        for obj in (record, pre, subject, documents["capture-check.json"], documents["handoff.json"],
                    documents["reduction.json"], documents["summary-check.json"], documents["summary.json"]):
            io.require(obj.get("authority_effect") == "none" and obj.get("production_gate_eligible") is False,
                       "q2_capture_rejected")
        for ctx in (pre["context"], record["context"], subject["platform"]):
            io.require(all(ctx[k] == expected_origin[k] for k in ("repository", "run_id", "run_attempt", "source_commit")) and
                       type(ctx["run_attempt"]) is int and ctx["event"] == "workflow_dispatch" and ctx["actor"] == "HKati" and
                       io.encode(ctx) == io.encode(pre["context"]), "q2_capture_rejected")
        for key in ("capture-check.json", "handoff.json"):
            obj = documents[key]
            io.require(io.encode(obj["binding"]) == io.encode(expected_binding), "q2_capture_rejected")
            for field, filename in (("groups_sha256", "groups.json"), ("manifest_sha256", "dataset-manifest.json"),
                                    ("transcript_sha256", "transcript.json")):
                io.require(obj[field] == descriptions[filename]["sha256"], "q2_capture_rejected")
        native = documents["capture-check.json"]
        io.require(native["complete_original_capture_verified"] is True and native["decoding_and_extraction_verified"] is True
                   and type(native["verified_calls"]) is int and native["verified_calls"] == 150 and
                   record["complete_original_capture_verified"] is True and
                   record["planned_calls"] == record["received_complete_slots"] == pre["planned_calls"] == 150,
                   "q2_capture_rejected")
        installed = documents["installation.json"]
        inventory = installed["inventory"]
        io.require(subject["installation_sha256"] == pre["installation_sha256"] == descriptions["installation.json"]["sha256"] and
                   subject["environment_inventory_sha256"] == pre["environment_inventory_sha256"] == io.digest(io.encode(inventory)) and
                   subject["prelaunch_sha256"] == descriptions["capture-prelaunch.json"]["sha256"] and
                   subject["ready_sha256"] == descriptions["capture-model-ready.json"]["sha256"] and
                   subject["worker_sha256"] == descriptions["source/" + io.WORKER]["sha256"] and
                   pre["selection_sha256"] == profile["selection"]["sha256"] and
                   subject["definition_sha256"] == profile["definition_sha256"], "q2_capture_rejected")
        config = {k: subject[k] for k in ("effective_generation", "runtime")}
        io.require(io.encode(config) == io.encode({k: documents["capture-model-ready.json"][k] for k in config}),
                   "q2_capture_rejected")
        result["checks"]["capture"] = True
        with io.Archive(private / "capsule.zip", maximum_bytes=limits["capsule_archive_bytes"],
                        max_members=limits["capsule_members"], member_bytes=limits["capsule_member_bytes"],
                        expanded_bytes=limits["capsule_expanded_bytes"], deadline=deadline,
                        allow_runtime_link=True, expected_sha256=request["release_subject"]["archive_sha256"]) as capsule:
            manifest_raw = capsule.read("capsule.json", 128 * 1024)
            io.require(io.digest(manifest_raw) == request["release_subject"]["capsule_manifest_sha256"], "q2_subject_mismatch")
            manifest = io.strict_json(manifest_raw)
            io.validate(manifest, io.read_file(repo / io.CAPSULE_SCHEMA, 128 * 1024))
            io.require(io.encode(manifest) == manifest_raw and manifest["definition_sha256"] == profile["definition_sha256"] and
                       manifest["capture_subject_sha256"] == expected_origin["subject_sha256"] and
                       manifest["subject_id"] == profile["subject_id"] and manifest["layout_profile"] == profile["layout_profile"],
                       "q2_subject_mismatch")
            io.require(io.encode(manifest["configuration"]) == io.encode(config) and
                       len(config["effective_generation"]) == profile["effective_generation_fields"] and
                       io.encode(manifest["launch"]) == io.encode(profile["launch"]), "q2_subject_mismatch")
            expected_platform = {"requirements": {k: subject["platform"][k] for k in profile["platform_requirement_keys"]},
                                 "release_host_verification": "not_observed"}
            io.require(io.encode(manifest["platform_scope"]) == io.encode(expected_platform), "q2_subject_mismatch")
            expected_files = {}
            for path in profile["source_components"]:
                name = "source/" + path
                original = descriptions[name]
                expected_files[name] = {**original, "mode": profile["source_archive_mode"]}
            selected = io.strict_json(capture.read("source/" + io.SELECTION_PATH))
            model_paths = {"model/" + n for n in selected["evaluation_subject"]["selected_snapshot_files"]}
            io.require(len(subject["model_files"]) == 8 and len(model_paths) == 8 and
                       {i["path"] for i in subject["model_files"]} == model_paths, "q2_subject_mismatch")
            for row in subject["model_files"]:
                expected_files[row["path"]] = {"size": row["size"], "sha256": row["sha256"],
                                                "mode": profile["model_capsule_mode"], "kind": "file"}
            regular, links = 0, []
            runtime_paths = set()
            for row in inventory:
                name = "runtime/" + io.safe_member(row["path"])
                io.require(name not in runtime_paths, "q2_subject_mismatch")
                runtime_paths.add(name)
                if "symlink" in row:
                    links.append(row)
                    io.require(row == {"path": "lib64", "symlink": "lib"} and
                               capsule.inspect(name)["kind"] == "symlink" and
                               capsule.read(name, 16) == b"lib", "q2_subject_mismatch")
                else:
                    regular += 1
                    expected_files[name] = {"size": row["size"], "sha256": row["sha256"],
                                            "mode": row["mode"], "kind": "file"}
            io.require(regular == profile["runtime_regular_files"] and links == profile["runtime_links"] and
                       set(capsule.members) == set(expected_files) | {"capsule.json", "runtime/lib64"}, "q2_subject_mismatch")
            for name, expected in expected_files.items():
                io.require(capsule.inspect(name) == expected, "q2_subject_mismatch")
            io.require(expected_files["runtime/bin/python"]["sha256"] == subject["platform"]["bootstrap_python_sha256"],
                       "q2_subject_mismatch")
        result["checks"]["subject"] = True
    # Independent interpreter/database checks; never call the producer's guard.
    actual_environment = {"implementation": platform.python_implementation(), "python": list(sys.version_info[:3]),
                          "unicode": unicodedata.unidata_version}
    io.require(actual_environment == profile["replay_environment"] and
               unicodedata.category(chr(0x1E030)) == "Cn" and
               unicodedata.normalize("NFKC", "ﬀ") == "ff" and
               unicodedata.normalize("NFKC", "Straße".casefold()) == "strasse", "q2_replay_environment")
    for source, expected_hash in profile["replay_sources"].items():
        io.read_file(repo / source, 1024 * 1024, expected_hash, deadline)
    for name in ("groups.json", "dataset-manifest.json", "summary.json"):
        io.write_new(private / name, payloads[name])
    common = ["--groups", str(private / "groups.json"), "--dataset-manifest", str(private / "dataset-manifest.json"),
              "--expected-groups-sha256", io.digest(payloads["groups.json"]),
              "--expected-manifest-sha256", io.digest(payloads["dataset-manifest.json"])]
    checker_rc = io.private_process([sys.executable, "-I", "-B", str(repo / io.CHECKER), *common,
                                     "--summary", str(private / "summary.json"), "--expected-summary-sha256",
                                     io.digest(payloads["summary.json"])], cwd=private,
                                    environment=io.replay_environment(private), timeout=deadline.remaining(60))
    io.require(checker_rc == 0, "q2_summary_mismatch")
    builder_rc = io.private_process([sys.executable, "-I", "-B", str(repo / io.REDUCER), *common,
                                     "--out", str(private / "admission-summary.json")], cwd=private,
                                    environment=io.replay_environment(private), timeout=deadline.remaining(60))
    io.require(io.read_file(private / "admission-summary.json", 16 * 1024 * 1024) == payloads["summary.json"],
               "q2_summary_mismatch")
    summary, reduction = documents["summary.json"], documents["reduction.json"]
    decision = summary["pass"]
    io.require(type(decision) is bool and builder_rc == (0 if decision else 1) and
               reduction["builder_exit_code"] == builder_rc and reduction["checker_exit_code"] == checker_rc and
               reduction["metric_pass"] is decision and record["metric_pass"] is decision and
               record["status"] == ("captured_metric_pass" if decision else "captured_metric_fail") and
               documents["summary-check.json"]["ok"] is True and
               documents["summary-check.json"]["recomputed_pass"] is decision, "q2_replay_rejected")
    for field, name in (("groups_sha256", "groups.json"), ("manifest_sha256", "dataset-manifest.json"), ("summary_sha256", "summary.json")):
        io.require(reduction[field] == io.digest(payloads[name]), "q2_capture_rejected")
    result["checks"].update(replay=True, summary=True)
    result.update(input_valid=True, metric_pass=decision, process_exit=0 if decision else 1,
                  replay_environment=actual_environment,
                  metrics={**summary["counts"], **{k: summary[k] for k in
                           ("wilson_lower_bound", "threshold", "min_n_eligible_groups")}},
                  diagnostics=[] if decision else ["q2_min_eligible_groups_not_met"
                              if summary["counts"]["groups_eligible"] < 50 else "q2_metric_failed"])
    return result


def admit(repo, public_path, run_identity, subject, *, environment=None):
    """A forged producer PASS is insufficient even when its generic hashes agree."""
    private_environment = dict(os.environ if environment is None else environment)
    for name in tuple(os.environ):
        if name.startswith("PULSE_Q2_"):
            os.environ.pop(name, None)
    recorded = io.strict_json(io.read_file(public_path, 128 * 1024))
    io.validate(recorded, io.read_file(repo / io.RESULT_SCHEMA, 128 * 1024))
    current = loader.consume(repo, consumer="admission", environment=private_environment)
    binding = current["evaluation_binding"] or {}
    expected_key = f"GITHUB_RUN_ID={binding.get('run_id')}|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI"
    io.require(current["record_status"] == "archived_capture_intake" and
               current["input_valid"] is True and current["metric_pass"] is True and
               current["process_exit"] == 0 and current["cleanup"] == "verified_removed" and
               binding.get("source_commit") == run_identity.get("git_sha") == subject.get("commit_sha") and
               binding.get("repository") == subject.get("repository") and
               run_identity.get("run_mode") == "prod" and run_identity.get("run_key") == expected_key and
               io.encode(recorded) == io.encode(current), "q2_admission_rejected")
    return current


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--private-input", type=Path)
    mode.add_argument("--verify-recorded-negative", action="store_true")
    parser.add_argument("--repo-root", type=Path, required=True)
    args = parser.parse_args()
    if args.verify_recorded_negative:
        try:
            verify_recorded_negative(args.repo_root.resolve(strict=True))
            return 0  # Verification succeeded; the recorded metric exit remains 1.
        except Exception as exc:
            print(exc.code if isinstance(exc, io.IntakeError) else "q2_internal_error")
            return 2
    result = None
    try:
        repo = args.repo_root.resolve(strict=True)
        private = io.check_private_directory(repo, args.private_input)
        io.require(not any(k.startswith("PULSE_Q2_") for k in __import__("os").environ), "q2_context_rejected")
        profile = loader.load_profile(repo)
        result = loader.empty_result(profile)
        request, binding, sources = loader.private_context(repo, private, profile)
        # Reconstruct prospective/current separation again, independent of a producer result.
        io.require(set(request["evaluation_identity"]) == {"repository", "source_commit", "workflow", "event", "ref"} and
                   request["evaluation_identity"]["source_commit"] == binding["source_commit"] and
                   request["release_subject"]["subject_id"] == profile["subject_id"], "q2_admission_rejected")
        result.update(request_sha256=binding["request_sha256"], evaluation_binding=binding,
                      release_artifact=request["release_subject"], source_bindings=sources)
        result["checks"]["request"] = True
        check_bound_inputs(repo, private, request, profile, result, io.Deadline(200))
    except Exception as exc:
        if result is None:
            return 2
        result.update(input_valid=False, metric_pass=None, metrics=None, process_exit=2,
                      diagnostics=[exc.code if isinstance(exc, io.IntakeError) else "q2_internal_error"])
    try:
        io.write_new(args.private_input / "result.json", io.encode(result))
    except Exception:
        return 2
    return result["process_exit"]


INDEPENDENT_RESULT = io.PACK + "artifacts/required_gate_inputs/q2_intake_independent_result_v0.json"


def _publish_negative(path, raw):
    """Atomic, no-overwrite publication through held, non-symlink directories."""
    path = path.absolute()
    io.require(".." not in path.parts, "q2_file_rejected")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    directory = os.open("/", flags)
    temporary = ".q2-negative-" + os.urandom(16).hex()
    created, published = False, False
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, flags, dir_fd=directory)
            os.close(directory)
            directory = child
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=directory)
        created = True
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path.name, src_dir_fd=directory, dst_dir_fd=directory,
                follow_symlinks=False)
        published = True
    finally:
        try:
            if created:
                try:
                    os.unlink(temporary, dir_fd=directory)
                except OSError:
                    if published:
                        os.unlink(path.name, dir_fd=directory)
                    raise
        finally:
            os.close(directory)


def verify_recorded_negative(repo, *, environment=None):
    """Reacquire and replay the fixed historical FAIL; never admit a candidate."""
    private_environment = dict(os.environ if environment is None else environment)
    for name in tuple(os.environ):
        if name.startswith("PULSE_Q2_"):
            os.environ.pop(name, None)
    destination = repo / INDEPENDENT_RESULT
    io.require(not os.path.lexists(destination), "q2_public_record_rejected")
    recorded_raw = io.read_file(repo / io.PUBLIC_RESULT, 128 * 1024)
    schema = io.read_file(repo / io.RESULT_SCHEMA, 128 * 1024)
    recorded = io.strict_json(recorded_raw)
    io.validate(recorded, schema)
    # Fresh authentication, downloads, semantic subprocess and verified cleanup.
    current = loader.consume(repo, consumer="admission", environment=private_environment)
    io.validate(current, schema)
    io.require(current["record_status"] == "archived_capture_intake" and
               current["input_valid"] is True and current["metric_pass"] is False and
               type(current["process_exit"]) is int and current["process_exit"] == 1 and
               set(current["checks"]) == {"request", "capture", "subject", "replay", "summary"} and
               all(value is True for value in current["checks"].values()) and
               current["cleanup"] == "verified_removed" and
               current["evaluation_binding"] is not None and current["source_bindings"] and
               io.encode(recorded) == io.encode(current) and
               io.read_file(repo / io.PUBLIC_RESULT, 128 * 1024) == recorded_raw,
               "q2_admission_rejected")
    _publish_negative(destination, io.encode(current))
    return current


if __name__ == "__main__":
    raise SystemExit(main())

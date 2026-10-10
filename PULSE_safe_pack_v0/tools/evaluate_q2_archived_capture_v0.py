#!/usr/bin/env python3
"""Dedicated archived Q2 evaluator. Never executes the archive or capsule code."""
from __future__ import annotations

import argparse
from pathlib import Path
import platform
import sys
import unicodedata

sys.path.insert(0, str(Path(__file__).resolve().parent))
import q2_intake_io_v0 as io
import load_q2_release_intake_v0 as loader


def capture_archive(path, profile, deadline):
    return io.Archive(path, maximum_bytes=profile["capture_expectation"]["archive_size_bytes"],
                      max_members=profile["capture_members"],
                      member_bytes=profile["limits"]["capture_member_bytes"],
                      expanded_bytes=profile["limits"]["capture_expanded_bytes"], deadline=deadline,
                      expected_sha256=profile["capture_expectation"]["archive_sha256"])


def verify_capture(archive, profile):
    """Recheck the full member/source binding and the archived native-check chain."""
    io.require(len(archive.members) == profile["capture_members"] and
               sum(i.file_size for i in archive.members.values()) == profile["capture_expanded_bytes"],
               "q2_capture_rejected")
    raw = {n: archive.read(n) for n in profile["capture_file_bindings"]}
    for name, expected in profile["capture_file_bindings"].items():
        io.require(io.digest(raw[name]) == expected["sha256"] and
                   len(raw[name]) == expected["size_bytes"], "q2_capture_rejected")
    docs = {n: io.strict_json(data) for n, data in raw.items()}
    report, pre, subject = (docs[n] for n in ("capture.json", "capture-prelaunch.json", "capture-subject.json"))
    rows = report["evidence"]
    io.require(type(rows) is list and len(rows) == len(archive.members) - 1 and
               len({r["path"] for r in rows}) == len(rows) and
               {r["path"] for r in rows} == set(archive.members) - {"capture.json"}, "q2_capture_rejected")
    for row in rows:
        actual = archive.inspect(row["path"])
        io.require(actual["kind"] == "file" and actual["size"] == row["size"] and
                   actual["sha256"] == row["sha256"], "q2_capture_rejected")
    origin = profile["capture_expectation"]
    context = pre["context"]
    io.require(context["repository"] == origin["repository"] and context["run_id"] == origin["run_id"] and
               type(context["run_attempt"]) is int and context["run_attempt"] == origin["run_attempt"] and
               context["source_commit"] == origin["source_commit"] and
               context["event"] == "workflow_dispatch" and context["actor"] == "HKati" and
               io.encode(report["context"]) == io.encode(context) and
               io.encode(subject["platform"]) == io.encode(context), "q2_capture_rejected")
    io.require(io.encode(pre["source_files"]) == io.encode(profile["archived_source_files"]), "q2_source_mismatch")
    for row in pre["source_files"]:
        actual = archive.inspect("source/" + row["path"])
        io.require(actual["sha256"] == row["sha256"] and actual["size"] == row["size"], "q2_source_mismatch")
    binding = {"prelaunch_sha256": io.digest(raw["capture-prelaunch.json"]),
               "subject_sha256": io.digest(raw["capture-subject.json"]),
               "run_id": origin["run_id"], "run_attempt": origin["run_attempt"],
               "source_commit": origin["source_commit"]}
    checked, handoff, reduction = (docs[n] for n in ("capture-check.json", "handoff.json", "reduction.json"))
    for item in (checked, handoff):
        io.require(io.encode(item["binding"]) == io.encode(binding), "q2_capture_rejected")
        for field, name in (("groups_sha256", "groups.json"), ("manifest_sha256", "dataset-manifest.json"),
                            ("transcript_sha256", "transcript.json")):
            io.require(item[field] == io.digest(raw[name]), "q2_capture_rejected")
    io.require(checked["complete_original_capture_verified"] is True and
               checked["decoding_and_extraction_verified"] is True and type(checked["verified_calls"]) is int and
               checked["verified_calls"] == 150 and report["complete_original_capture_verified"] is True and
               report["planned_calls"] == report["received_complete_slots"] == pre["planned_calls"] == 150,
               "q2_capture_rejected")
    io.require(subject["prelaunch_sha256"] == binding["prelaunch_sha256"] and
               subject["ready_sha256"] == io.digest(raw["capture-model-ready.json"]) and
               subject["installation_sha256"] == pre["installation_sha256"] == io.digest(raw["installation.json"]),
               "q2_capture_rejected")
    inventory = docs["installation.json"]["inventory"]
    io.require(subject["environment_inventory_sha256"] == pre["environment_inventory_sha256"] == io.digest(io.encode(inventory)),
               "q2_capture_rejected")
    ready = docs["capture-model-ready.json"]
    for field in ("effective_generation", "runtime"):
        io.require(io.encode(subject[field]) == io.encode(ready[field]), "q2_capture_rejected")
    io.require(subject["definition_sha256"] == profile["definition_sha256"] and
               subject["worker_sha256"] == archive.inspect("source/" + io.WORKER)["sha256"] and
               pre["selection_sha256"] == profile["selection"]["sha256"], "q2_capture_rejected")
    summary = docs["summary.json"]
    decision = summary["pass"]
    io.require(type(decision) is bool and report["metric_pass"] is decision and reduction["metric_pass"] is decision and
               report["status"] == ("captured_metric_pass" if decision else "captured_metric_fail") and
               docs["summary-check.json"]["ok"] is True and
               docs["summary-check.json"]["recomputed_pass"] is decision and
               reduction["builder_exit_code"] == (0 if decision else 1) and reduction["checker_exit_code"] == 0,
               "q2_capture_rejected")
    for field, name in (("groups_sha256", "groups.json"), ("manifest_sha256", "dataset-manifest.json"),
                        ("summary_sha256", "summary.json")):
        io.require(reduction[field] == io.digest(raw[name]), "q2_capture_rejected")
    for item in (report, pre, subject, checked, handoff, reduction, summary, docs["summary-check.json"]):
        io.require(item["authority_effect"] == "none" and item["production_gate_eligible"] is False, "q2_capture_rejected")
    return docs, raw


def compare_subject(repo, capture, capsule, request, profile, docs):
    """Exact capsule membership, file bytes, modes, link and launch/config scope."""
    raw = capsule.read("capsule.json", 128 * 1024)
    io.require(io.digest(raw) == request["release_subject"]["capsule_manifest_sha256"], "q2_subject_mismatch")
    manifest = io.strict_json(raw)
    io.validate(manifest, io.read_file(repo / io.CAPSULE_SCHEMA, 128 * 1024))
    io.require(raw == io.encode(manifest), "q2_subject_mismatch")
    subject = docs["capture-subject.json"]
    io.require(manifest["capture_subject_sha256"] == profile["capture_expectation"]["subject_sha256"] and
               manifest["definition_sha256"] == profile["definition_sha256"] and
               manifest["subject_id"] == profile["subject_id"] and
               manifest["layout_profile"] == profile["layout_profile"], "q2_subject_mismatch")
    io.require(io.encode(manifest["configuration"]) == io.encode({k: subject[k] for k in ("effective_generation", "runtime")}) and
               len(subject["effective_generation"]) == profile["effective_generation_fields"] and
               io.encode(manifest["launch"]) == io.encode(profile["launch"]), "q2_subject_mismatch")
    requirements = {k: subject["platform"][k] for k in profile["platform_requirement_keys"]}
    io.require(io.encode(manifest["platform_scope"]) == io.encode({"requirements": requirements,
               "release_host_verification": "not_observed"}), "q2_subject_mismatch")
    expected = {"capsule.json"}
    for path in profile["source_components"]:
        name = "source/" + path
        expected.add(name)
        original, actual = capture.inspect(name), capsule.inspect(name)
        io.require(actual["kind"] == "file" and actual["mode"] == profile["source_archive_mode"] and
                   (actual["size"], actual["sha256"]) == (original["size"], original["sha256"]), "q2_subject_mismatch")
    models = subject["model_files"]
    selection = io.strict_json(capture.read("source/" + io.SELECTION_PATH))
    model_names = {"model/" + n for n in selection["evaluation_subject"]["selected_snapshot_files"]}
    io.require(len(models) == len(model_names) == 8 and {r["path"] for r in models} == model_names,
               "q2_subject_mismatch")
    for row in models:
        expected.add(row["path"])
        actual = capsule.inspect(row["path"])
        io.require(actual["kind"] == "file" and actual["mode"] == profile["model_capsule_mode"] and
                   actual["size"] == row["size"] and actual["sha256"] == row["sha256"], "q2_subject_mismatch")
    inventory = docs["installation.json"]["inventory"]
    io.require(len({r["path"] for r in inventory}) == len(inventory) and
               len([r for r in inventory if "symlink" not in r]) == profile["runtime_regular_files"] and
               [r for r in inventory if "symlink" in r] == profile["runtime_links"], "q2_subject_mismatch")
    for row in inventory:
        name = "runtime/" + io.safe_member(row["path"])
        expected.add(name)
        actual = capsule.inspect(name)
        if "symlink" in row:
            io.require(name == "runtime/lib64" and row["symlink"] == "lib" and
                       actual["kind"] == "symlink" and capsule.read(name, 16) == b"lib", "q2_subject_mismatch")
        else:
            io.require(actual == {"kind": "file", "mode": row["mode"], "size": row["size"],
                                  "sha256": row["sha256"]}, "q2_subject_mismatch")
    io.require(set(capsule.members) == expected and capsule.inspect("runtime/bin/python")["sha256"] ==
               subject["platform"]["bootstrap_python_sha256"], "q2_subject_mismatch")


def check_replay_environment(profile):
    actual = {"implementation": platform.python_implementation(), "python": list(sys.version_info[:3]),
              "unicode": unicodedata.unidata_version}
    io.require(actual == profile["replay_environment"] and
               unicodedata.name(chr(0x1E030), None) is None and
               unicodedata.normalize("NFKC", chr(0x1E030)) == chr(0x1E030) and
               unicodedata.normalize("NFKC", "Straße".casefold()) == "strasse" and
               unicodedata.normalize("NFKC", "Ａ".casefold()) == "a", "q2_replay_environment")
    return actual


def replay(repo, private, raw, profile, deadline):
    actual = check_replay_environment(profile)
    for path, expected in profile["replay_sources"].items():
        io.read_file(repo / path, 1024 * 1024, expected, deadline)
    for name in ("groups.json", "dataset-manifest.json", "summary.json"):
        io.write_new(private / name, raw[name])
    arguments = ["--groups", str(private / "groups.json"), "--dataset-manifest", str(private / "dataset-manifest.json"),
                 "--expected-groups-sha256", io.digest(raw["groups.json"]),
                 "--expected-manifest-sha256", io.digest(raw["dataset-manifest.json"])]
    new_summary = private / "recomputed-summary.json"
    rc = io.private_process([sys.executable, "-I", "-B", str(repo / io.REDUCER), *arguments,
                             "--out", str(new_summary)], cwd=private, environment=io.replay_environment(private),
                            timeout=deadline.remaining(60))
    io.require(rc in (0, 1), "q2_replay_rejected")
    io.require(io.read_file(new_summary, 16 * 1024 * 1024) == raw["summary.json"], "q2_summary_mismatch")
    checked = io.private_process([sys.executable, "-I", "-B", str(repo / io.CHECKER), *arguments,
                                  "--summary", str(private / "summary.json"), "--expected-summary-sha256",
                                  io.digest(raw["summary.json"])], cwd=private,
                                 environment=io.replay_environment(private), timeout=deadline.remaining(60))
    summary = io.strict_json(raw["summary.json"])
    io.require(checked == 0 and type(summary["pass"]) is bool and rc == (0 if summary["pass"] else 1),
               "q2_replay_rejected")
    return summary, actual


def evaluate_inputs(repo, private, request, profile, result, deadline):
    for name, expectation in (("capture", profile["capture_expectation"]), ("capsule", request["release_subject"])):
        actual = io.file_binding(private / (name + ".zip"), profile["limits"]["capsule_archive_bytes"], deadline)
        io.require(all(actual[k] == expectation[k] for k in actual), "q2_digest_mismatch")
    with capture_archive(private / "capture.zip", profile, deadline) as capture:
        docs, raw = verify_capture(capture, profile)
        result["checks"]["capture"] = True
        limits = profile["limits"]
        with io.Archive(private / "capsule.zip", maximum_bytes=limits["capsule_archive_bytes"],
                        max_members=limits["capsule_members"], member_bytes=limits["capsule_member_bytes"],
                        expanded_bytes=limits["capsule_expanded_bytes"], deadline=deadline,
                        allow_runtime_link=True, expected_sha256=request["release_subject"]["archive_sha256"]) as capsule:
            compare_subject(repo, capture, capsule, request, profile, docs)
        result["checks"]["subject"] = True
        summary, environment = replay(repo, private, raw, profile, deadline)
    result["checks"].update(replay=True, summary=True)
    result.update(input_valid=True, metric_pass=summary["pass"], process_exit=0 if summary["pass"] else 1,
                  replay_environment=environment,
                  metrics={**summary["counts"], **{k: summary[k] for k in
                           ("wilson_lower_bound", "threshold", "min_n_eligible_groups")}},
                  diagnostics=[] if summary["pass"] else ["q2_min_eligible_groups_not_met"
                              if summary["insufficient_evidence"] else "q2_metric_failed"])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-input", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    args = parser.parse_args()
    result = None
    try:
        repo = args.repo_root.resolve(strict=True)
        private = io.check_private_directory(repo, args.private_input)
        io.require(not any(k.startswith("PULSE_Q2_") for k in __import__("os").environ), "q2_context_rejected")
        profile = loader.load_profile(repo)
        result = loader.empty_result(profile)
        request, binding, sources = loader.private_context(repo, private, profile)
        result.update(request_sha256=binding["request_sha256"], evaluation_binding=binding,
                      release_artifact=request["release_subject"], source_bindings=sources)
        result["checks"]["request"] = True
        evaluate_inputs(repo, private, request, profile, result, io.Deadline(200))
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


if __name__ == "__main__":
    raise SystemExit(main())

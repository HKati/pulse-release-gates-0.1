#!/usr/bin/env python3
"""Trusted-invocation Q2 transport supervisor; no inference or archive imports."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys

# Also works under -I: only the reviewed sibling directory is an import root.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import q2_intake_io_v0 as io

REQUEST_ENV = "PULSE_Q2_INTAKE_REQUEST"
DIGEST_ENV = "PULSE_Q2_INTAKE_REQUEST_SHA256"
TOKEN_ENV = "PULSE_Q2_TRANSPORT_TOKEN"


def load_profile(repo):
    profile = io.strict_json(io.read_file(repo / io.PROFILE_PATH, 256 * 1024))
    io.require(profile.get("record_type") == "q2_reference_release_intake_profile_v0" and
               profile.get("record_status") == "archived_capture_intake" and
               profile.get("release_capsule_present") is False and
               profile.get("release_artifact_digest") is None and
               profile.get("capture_expectation", {}).get("archive_sha256") ==
               "88c0335d57bf5dd207840eb129fc2fe36c453a2fb0d2da72e48f9689c4758cc6" and
               profile.get("selection", {}).get("sha256") ==
               "e81a9dd0a5080d84dae8c4bbfc843b46510f580e74254c1aed0dddbe76375f3e",
               "q2_source_mismatch")
    return profile


def metadata_request(repo, raw_text, expected_digest, source_commit, profile=None):
    """Validate prospective metadata. This function alone does not authorize IO."""
    profile = load_profile(repo) if profile is None else profile
    io.require(type(raw_text) is str and type(expected_digest) is str and
               bool(raw_text) and bool(expected_digest), "q2_request_missing")
    try:
        raw = raw_text.encode("utf-8", errors="strict")
    except UnicodeError:
        raise io.IntakeError("q2_request_invalid") from None
    io.require(len(raw) <= 16384, "q2_request_invalid")
    io.require(re.fullmatch(r"[0-9a-f]{64}", expected_digest) is not None and
               io.digest(raw) == expected_digest, "q2_request_digest_mismatch")
    request = io.strict_json(raw, 16384)
    io.validate(request, io.read_file(repo / io.REQUEST_SCHEMA, 128 * 1024))
    io.require(request["capture_expectation"] == profile["capture_expectation"] and
               request["selection"] == profile["selection"] and
               request["evaluation_identity"]["source_commit"] == source_commit,
               "q2_request_invalid")
    for key in ("comparison_profile", "reduction_profile", "native_verification_mode"):
        io.require(request[key] == profile[key], "q2_request_invalid")
    release = request["release_subject"]
    io.require(release["artifact_id"] != profile["capture_expectation"]["artifact_id"] and
               release["archive_sha256"] not in
               (profile["definition_sha256"], profile["capture_expectation"]["subject_sha256"],
                profile["capture_expectation"]["archive_sha256"]), "q2_request_invalid")
    selected_raw = io.read_file(repo / io.SELECTION_PATH, 128 * 1024,
                               profile["selection"]["sha256"])
    selected = io.strict_json(selected_raw)
    io.require(selected["selection_id"] == request["selection"]["selection_id"] and
               selected["release_subject"]["subject_id"] == release["subject_id"] and
               selected["release_subject"]["definition_sha256"] == release["definition_sha256"],
               "q2_selection_mismatch")
    return request


def verify_source_closure(repo, revision):
    """Bind the reviewed checkout to the workflow SHA, including all Q2 sources."""
    io.require(re.fullmatch(r"[0-9a-f]{40}", revision or "") is not None, "q2_source_mismatch")
    environment = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C",
                   "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
                   "GIT_CONFIG_SYSTEM": "/dev/null", "GIT_TERMINAL_PROMPT": "0",
                   "GIT_NO_REPLACE_OBJECTS": "1"}
    def git(arguments):
        try:
            result = subprocess.run(["/usr/bin/git", "--no-replace-objects", "-c",
                                     "credential.helper=", *arguments], cwd=repo,
                                    env=environment, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                    timeout=15, check=False)
        except (OSError, subprocess.TimeoutExpired):
            raise io.IntakeError("q2_source_mismatch") from None
        io.require(result.returncode == 0 and len(result.stdout) <= 65536, "q2_source_mismatch")
        return result.stdout
    io.require(git(["rev-parse", "--verify", "HEAD^{commit}"]) == revision.encode() + b"\n",
               "q2_source_mismatch")
    rows = git(["ls-tree", "-rz", "--full-tree", revision, "--", *io.SOURCE_PATHS])
    entries = {}
    try:
        for row in rows.split(b"\0"):
            if row:
                left, name = row.split(b"\t")
                mode, kind, oid = left.decode("ascii").split()
                entries[name.decode("ascii")] = (mode, kind, oid)
    except (ValueError, UnicodeError):
        raise io.IntakeError("q2_source_mismatch") from None
    io.require(set(entries) == set(io.SOURCE_PATHS), "q2_source_mismatch")
    bindings = []
    for name in sorted(entries):
        raw = io.read_file(repo / name, 2 * 1024 * 1024)
        mode, kind, oid = entries[name]
        actual = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        actual_mode = "100755" if (repo / name).stat().st_mode & 0o111 else "100644"
        io.require(kind == "blob" and mode == actual_mode and oid == actual, "q2_source_mismatch")
        bindings.append({"path": name, "sha256": io.digest(raw), "size_bytes": len(raw)})
    return bindings


def trusted_invocation(repo, environment, profile=None):
    profile = load_profile(repo) if profile is None else profile
    auth = profile["authorization"]
    revision = environment.get("GITHUB_SHA", "")
    request = metadata_request(repo, environment.get(REQUEST_ENV, ""),
                               environment.get(DIGEST_ENV, ""), revision, profile)
    wanted = {"GITHUB_REPOSITORY": auth["repository"], "GITHUB_EVENT_NAME": auth["event"],
              "GITHUB_REF": auth["ref"], "GITHUB_WORKFLOW_SHA": revision,
              "GITHUB_WORKFLOW": "PULSE CI", "GITHUB_RUN_ATTEMPT": "1",
              "GITHUB_WORKFLOW_REF": auth["repository"] + "/" + auth["workflow"] + "@" + auth["ref"],
              "GITHUB_ACTOR": auth["actor"], "GITHUB_TRIGGERING_ACTOR": auth["actor"],
              "GITHUB_ACTIONS": "true", "RUNNER_OS": "Linux", "RUNNER_ENVIRONMENT": "github-hosted"}
    io.require(all(environment.get(k) == v for k, v in wanted.items()) and
               environment.get("GITHUB_WORKSPACE") == str(repo), "q2_context_rejected")
    run_id = environment.get("GITHUB_RUN_ID", "")
    io.require(re.fullmatch(r"[1-9][0-9]{0,23}", run_id) is not None and
               environment.get("PULSE_RUN_KEY") ==
               f"GITHUB_RUN_ID={run_id}|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI",
               "q2_context_rejected")
    event_path = environment.get("GITHUB_EVENT_PATH", "")
    io.require(bool(event_path), "q2_context_rejected")
    event = io.strict_json(io.read_file(Path(event_path), 512 * 1024))
    expected_inputs = {"strict_external_evidence": "true", "llamaguard_evidence_mode": "hosted_full_runtime",
                       "q2_intake_request": environment[REQUEST_ENV],
                       "q2_intake_request_sha256": environment[DIGEST_ENV]}
    # The dispatch request uses "main"; GitHub's event may use the full branch ref.
    # The trusted environment above still requires exactly refs/heads/main.
    io.require(event.get("inputs") == expected_inputs and event.get("ref") in ("main", auth["ref"]) and
               event.get("sender", {}).get("login") == auth["actor"] and
               event.get("repository", {}).get("full_name") == auth["repository"],
               "q2_context_rejected")
    sources = verify_source_closure(repo, revision)
    binding = {**request["evaluation_identity"], "workflow_sha": revision, "run_id": run_id,
               "run_attempt": 1, "request_sha256": environment[DIGEST_ENV]}
    return request, binding, sources


def empty_result(profile):
    return {"schema_version": "q2_release_intake_result_v0", "record_status": profile["record_status"],
            "input_valid": False, "metric_pass": None, "process_exit": 2, "diagnostics": [],
            "checks": {k: False for k in ("request", "capture", "subject", "replay", "summary")},
            "cleanup": "not_created", "request_sha256": None, "evaluation_binding": None,
            "capture_origin": profile["capture_expectation"], "release_artifact": None,
            "metrics": None, "replay_environment": None, "source_bindings": [],
            "comparison_scope": "exact_capsule_payload_and_launch_descriptor",
            "release_host_environment": "not_observed", "native_verification": "archived_evidence_only",
            "current_inference_count": 0, "authority_effect": "none", "production_gate_eligible": False}


def consume(repo, *, consumer, environment=None):
    """Each invocation independently reacquires; no producer directory or verdict reuse.

    The semantic child gets a minimal credential-free environment and DEVNULL
    output. Its private result is schema-checked only after the private tree is
    removed. No alternate profile, URL, local payload or interpreter is accepted
    from workflow inputs.
    """
    repo = Path(repo).resolve(strict=True)
    env = dict(os.environ if environment is None else environment)
    token = env.pop(TOKEN_ENV, "")
    for name in tuple(os.environ):
        if name.startswith("PULSE_Q2_"):
            os.environ.pop(name, None)
    profile = load_profile(repo)
    result = empty_result(profile)
    work = None
    try:
        io.require(consumer in ("producer", "admission"), "q2_context_rejected")
        with io.interrupt_boundary(min(profile["limits"]["seconds"], 240)) as deadline:
            request, binding, sources = trusted_invocation(repo, env, profile)
            result.update(request_sha256=binding["request_sha256"], evaluation_binding=binding,
                          release_artifact=request["release_subject"], source_bindings=sources)
            result["checks"]["request"] = True
            with io.private_workspace(repo, env.get("PULSE_Q2_SUPERVISOR_ROOT")) as work:
                private = work["path"]
                transport = io.GitHubArtifactTransport(token)
                for label, expectation in (("capture", request["capture_expectation"]),
                                           ("capsule", request["release_subject"])):
                    destination = private / (label + ".zip")
                    transport.download(expectation["repository"], expectation["artifact_id"],
                                       expectation, destination, deadline)
                    actual = io.file_binding(destination, profile["limits"]["capsule_archive_bytes"], deadline)
                    io.require(all(actual[k] == expectation[k] for k in actual), "q2_digest_mismatch")
                    destination.chmod(0o400)
                # Credential lifetime ends before the semantic interpreter is created.
                del transport
                token = None
                io.write_new(private / "request.json", env[REQUEST_ENV].encode("utf-8"))
                io.write_new(private / "context.json", io.encode({"binding": binding, "source_bindings": sources}))
                tool = ("evaluate_q2_archived_capture_v0.py" if consumer == "producer"
                        else "check_q2_release_intake_v0.py")
                rc = io.private_process([sys.executable, "-I", "-B", str(repo / io.PACK / "tools" / tool),
                                         "--private-input", str(private), "--repo-root", str(repo)],
                                        cwd=private, environment=io.replay_environment(private),
                                        timeout=deadline.remaining(210), new_session=True)
                proposed = io.strict_json(io.read_file(private / "result.json", 128 * 1024))
                io.require(rc in (0, 1, 2) and proposed.get("process_exit") == rc and
                           proposed.get("request_sha256") == binding["request_sha256"] and
                           proposed.get("evaluation_binding") == binding and
                           proposed.get("source_bindings") == sources and
                           proposed.get("release_artifact") == request["release_subject"],
                           "q2_public_record_rejected")
                result = proposed
            result["cleanup"] = "verified_removed"
    except io.IntakeError as exc:
        result.update(input_valid=False, metric_pass=None, metrics=None,
                      process_exit=2, diagnostics=[exc.code])
    except Exception:
        result.update(input_valid=False, metric_pass=None, metrics=None,
                      process_exit=2, diagnostics=["q2_internal_error"])
    finally:
        token = None
        if work is not None:
            result["cleanup"] = "verified_removed" if work["cleanup_verified"] else "not_established"
    io.validate(result, io.read_file(repo / io.RESULT_SCHEMA, 128 * 1024))
    return result


def private_context(repo, private, profile):
    """Only stable bytes; authentication is repeated at each external entry point."""
    raw = io.read_file(private / "request.json", 16384)
    context = io.strict_json(io.read_file(private / "context.json", 128 * 1024))
    binding = context["binding"]
    request = metadata_request(repo, raw.decode("utf-8"), binding["request_sha256"],
                               binding["source_commit"], profile)
    io.require(binding == {**request["evaluation_identity"], "workflow_sha": binding["source_commit"],
                            "run_id": binding["run_id"], "run_attempt": 1,
                            "request_sha256": io.digest(raw)} and
               re.fullmatch(r"[1-9][0-9]{0,23}", binding["run_id"]) is not None,
               "q2_context_rejected")
    io.require(context["source_bindings"] == verify_source_closure(repo, binding["source_commit"]),
               "q2_source_mismatch")
    return request, binding, context["source_bindings"]

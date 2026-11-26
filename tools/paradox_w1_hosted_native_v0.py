#!/usr/bin/env python3
"""Import one preserved W1 request and record a separately authorized hosted run.

Preparation and finalization are offline. Only the explicit capture subcommand
can call the unchanged native controller. No archive program is imported.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import signal
import stat
import sys
import zipfile

REPOSITORY = "HKati/pulse-release-gates-0.1"
WORKFLOW_REL = Path(".github/workflows/paradox_w1_native_v0.yml")
HELPER_REL = Path("tools/paradox_w1_hosted_native_v0.py")
BUNDLE_ROOT = "PD_SM_02_W1_NATIVE_REQUEST_v0"
ARCHIVE_REL = Path("docs/evidence") / BUNDLE_ROOT / (BUNDLE_ROOT + ".zip")
ARCHIVE_SHA256 = "dbb532a1447f6602f6a9dda53599bd8cbb163e60f94fc2c724178bb3700e8834"
ARCHIVE_BYTES = 444703
MANIFEST_SHA256 = "85707f79e68e5b59c18110038cb3eaba7b7ad1543c0368e33cf5589c32524e7d"
REQUEST_SHA256 = "655910d465b68cd58425d10d2e1bf6050079a47ac4468422468b03560442383a"
REQUEST_RUN_ID = "pd-sm-02-w1-native-after-41362257003-01"
PREPARATION_SOURCE = "6343d4e54ec8628f033400518fe08a81aa75d9b9"
IMAGE_ID = "sha256:38e57556b63539e63344b97f802e7cbd85b70e2087ee703e360fcdfe337cbbb3"
PULL_REFERENCE = "docker.io/library/python@sha256:a7cb177dc60dfa77b223192cd0d9e6ce1aac7cf9a569023d68e7c91b6371a718"
ORDER = ("P00", "N01", "N07", "N08", "N02")
CONTROLS = ["probe-time", "probe-output"]
SOFT_DEADLINE_SECONDS = 420
STEP_NAMES = ("checkout", "prepare", "verify", "image", "capture", "replay")
SOURCES = {
    "run_paradox_w1_native_v0.py": "bff5759aaee32e93362829084b8867fb078d1e390c31aaad73c7255493d1aa3f",
    "paradox_w1_native_runtime_v0.py": "d9fc5ab02d533a2fec47e8e9be60b86b4104a040e0aec1fa5b449ef581d33d56",
    "paradox_w1_native_observer_v0.py": "4a08113afcea5c779693939e1d90061d09e275c798c1f54573ffa55e2b6e9f0c",
    "paradox_w1_docker_boundary_v0.py": "af857d34629645493f11c402a30fe28c720f4c6bac61b7ef597a0dc0891ca876",
    "check_paradox_w1_records_v0.py": "56fabc69fe654188c3ede2f2537ff576228485e7d8228ef3d2584bd1bc50694b",
}
HERE = Path(__file__).resolve().parent


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def strict(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, "duplicate_json_key")
            result[key] = value
        return result
    def constant(_):
        raise ValueError("nonfinite_json")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def regular(path, limit=8 * 1024 * 1024):
    path = Path(path).absolute()
    need(not any(p.is_symlink() for p in (path, *path.parents)), "symlink_path")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    try:
        info = os.fstat(fd)
        need(stat.S_ISREG(info.st_mode) and info.st_size <= limit, "regular_file_limit")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            raw = handle.read(limit + 1)
        need(len(raw) <= limit, "file_size_limit")
        return raw
    finally:
        os.close(fd)


def write_bytes(path, raw):
    with open(path, "xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def write_json(path, value):
    write_bytes(path, canonical(value) + b"\n")


def replace_json(path, value):
    temporary = path.with_name(path.name + ".partial")
    write_json(temporary, value)
    os.replace(temporary, path)


def read_archive(raw):
    """Check the complete original ZIP before extracting any member."""
    need(len(raw) == ARCHIVE_BYTES and digest(raw) == ARCHIVE_SHA256, "archive_binding")
    members = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        need(len(entries) == 56 and sum(item.file_size for item in entries) <= 2 * 1024 * 1024,
             "archive_inventory_limit")
        for item in entries:
            name = item.filename
            path = PurePosixPath(name)
            need(not item.is_dir() and not path.is_absolute() and "\\" not in name
                 and "\x00" not in name and all(part not in ("", ".", "..") for part in name.split("/"))
                 and path.parts[0] == BUNDLE_ROOT and len(path.parts) > 1, "archive_member_path")
            need(stat.S_ISREG(item.external_attr >> 16) and not item.flag_bits & 1
                 and item.compress_type == zipfile.ZIP_DEFLATED and item.file_size <= 1024 * 1024,
                 "archive_member_type_or_size")
            relative = path.relative_to(BUNDLE_ROOT).as_posix()
            need(relative not in members, "archive_duplicate_member")
            with archive.open(item) as handle:
                data = handle.read(item.file_size + 1)
            need(len(data) == item.file_size, "archive_member_length")
            members[relative] = data
    manifest_raw = members["MANIFEST.json"]
    need(digest(manifest_raw) == MANIFEST_SHA256, "bundle_manifest_binding")
    need(members["MANIFEST.sha256"] == (MANIFEST_SHA256 + "  MANIFEST.json\n").encode(),
         "bundle_manifest_sidecar")
    manifest = strict(manifest_raw)
    need(manifest["schema_version"] == "pd_sm_02_w1_native_preparation_bundle_manifest_v0"
         and manifest["authority_effect"] == "none"
         and manifest["native_request_sha256"] == REQUEST_SHA256
         and manifest["excluded_self_files"] == ["MANIFEST.json", "MANIFEST.sha256"], "bundle_manifest_role")
    expected = set(members) - {"MANIFEST.json", "MANIFEST.sha256"}
    need(set(manifest["files"]) == expected and len(expected) == 54, "bundle_manifest_inventory")
    for name in expected:
        need(manifest["files"][name] == {"bytes": len(members[name]), "sha256": digest(members[name])},
             "bundle_member_binding:" + name)
    need(members["REQUEST_SHA256.txt"] == (REQUEST_SHA256 + "\n").encode()
         and digest(members["package/request.json"]) == REQUEST_SHA256, "native_request_binding")
    request = strict(members["package/request.json"])
    need(request["run_id"] == REQUEST_RUN_ID and request["image_id"] == IMAGE_ID
         and request["sources"] == SOURCES and request["supervision_controls"] == CONTROLS
         and [row["case_id"] for row in request["cases"]] == list(ORDER)
         and request["execution_authorized"] is False and request["authority_effect"] == "none", "preserved_request_identity")
    package_members = {name.removeprefix("package/") for name in members if name.startswith("package/")}
    need(len(request["payloads"]) == 20 and package_members == set(request["payloads"]) | {"request.json"},
         "fresh_package_inventory")
    return members


def host_context(source_commit, environment=None):
    env = os.environ if environment is None else environment
    need(type(source_commit) is str and re.fullmatch("[0-9a-f]{40}", source_commit), "source_commit")
    expected = {
        "GITHUB_REPOSITORY": REPOSITORY, "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REF": "refs/heads/main", "GITHUB_ACTOR": "HKati", "GITHUB_ACTOR_ID": "128643840",
        "GITHUB_TRIGGERING_ACTOR": "HKati", "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_SHA": source_commit, "GITHUB_WORKFLOW_SHA": source_commit,
        "GITHUB_WORKFLOW_REF": REPOSITORY + "/" + WORKFLOW_REL.as_posix() + "@refs/heads/main",
        "RUNNER_OS": "Linux", "RUNNER_ARCH": "X64", "RUNNER_ENVIRONMENT": "github-hosted",
        "ImageOS": "ubuntu24", "PD_REQUEST_SHA256": REQUEST_SHA256,
        "PD_NATIVE_ACKNOWLEDGEMENT": "I_AUTHORIZE_PD_SM_02_W1:" + REQUEST_SHA256,
    }
    for name, value in expected.items():
        need(env.get(name) == value, "host_context:" + name)
    need(re.fullmatch("[1-9][0-9]*", env.get("GITHUB_RUN_ID", "")), "host_context:GITHUB_RUN_ID")
    need(re.fullmatch(r"[0-9]{8}(?:\.[0-9]+){1,3}", env.get("ImageVersion", "")), "host_context:ImageVersion")
    # Deliberately exclude the general environment, runner credentials and paths.
    recorded = {name: env[name] for name in expected if not name.startswith("PD_")}
    recorded.update({name: env[name] for name in ("GITHUB_RUN_ID", "ImageVersion")})
    return {"schema_version": "pd_sm_02_w1_hosted_context_v0", "source_commit": source_commit,
            "request_sha256": REQUEST_SHA256, "github": recorded,
            "owner_command_acknowledged": True, "authority_effect": "none"}


def check_recorded_context(context, source_commit):
    env = dict(context["github"])
    env.update(PD_REQUEST_SHA256=REQUEST_SHA256,
               PD_NATIVE_ACKNOWLEDGEMENT="I_AUTHORIZE_PD_SM_02_W1:" + REQUEST_SHA256)
    need(canonical(context) == canonical(host_context(source_commit, env)), "recorded_host_context")


def verify_tool_closure(directory):
    for name, expected in SOURCES.items():
        need(digest(regular(directory / name)) == expected, "checked_out_source:" + name)


def load_controller():
    verify_tool_closure(HERE)
    spec = importlib.util.spec_from_file_location("w1_hosted_bound_controller", HERE / "run_paradox_w1_native_v0.py")
    module = importlib.util.module_from_spec(spec)
    old = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = old
    return module


def prepare(repo_root, output, source_commit, environment=None):
    context = host_context(source_commit, environment)
    repo_root, output = Path(repo_root).absolute(), Path(output).absolute()
    need(output.is_dir() and not any(p.is_symlink() for p in (output, *output.parents)), "output_directory")
    need(repo_root.resolve() not in (output.resolve(), *output.resolve().parents), "output_inside_checkout")
    need({p.name for p in output.iterdir()} <= {"ACQUISITION_STATUS.txt", "prepare.stdout", "prepare.stderr"},
         "output_not_fresh")
    for path in output.iterdir():
        regular(path)
    archive_raw = regular(repo_root / ARCHIVE_REL, ARCHIVE_BYTES)
    sidecar = regular(repo_root / (str(ARCHIVE_REL) + ".sha256"), 256)
    need(sidecar == (ARCHIVE_SHA256 + "  " + ARCHIVE_REL.name + "\n").encode(), "archive_sidecar")
    members = read_archive(archive_raw)
    verify_tool_closure(repo_root / "tools")
    helper = regular(repo_root / HELPER_REL)
    need(helper == regular(Path(__file__)), "hosted_helper_source")
    workflow = regular(repo_root / WORKFLOW_REL)
    hosted_sources = {HELPER_REL.name: helper, WORKFLOW_REL.name: workflow}
    # Complete validation precedes all writes of package members.
    (output / "input").mkdir(mode=0o700)
    write_bytes(output / "input" / ARCHIVE_REL.name, archive_raw)
    write_bytes(output / "input" / (ARCHIVE_REL.name + ".sha256"), sidecar)
    (output / "package").mkdir(mode=0o700)
    for name, raw in sorted(members.items()):
        if name.startswith("package/"):
            path = output / name
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            write_bytes(path, raw)
    (output / "hosted_source").mkdir(mode=0o700)
    for name, raw in hosted_sources.items():
        write_bytes(output / "hosted_source" / name, raw)
    write_json(output / "host_context.json", context)
    receipt = {
        "status": "PRESERVED_REQUEST_PREPARED_NOT_AUTHORIZED", "source_commit": source_commit,
        "request_sha256": REQUEST_SHA256, "request_run_id": REQUEST_RUN_ID,
        "original_preparation_source": PREPARATION_SOURCE, "archive_sha256": ARCHIVE_SHA256,
        "archive_bytes": ARCHIVE_BYTES, "bundle_manifest_sha256": MANIFEST_SHA256,
        "archive_members": 56, "package_files": 21,
        "host_context_sha256": digest(canonical(context) + b"\n"),
        "hosted_sources": {name: {"sha256": digest(raw), "bytes": len(raw)} for name, raw in hosted_sources.items()},
        "new_candidate_executions": 0, "execution_authorized": False, "authority_effect": "none",
    }
    write_json(output / "preparation.json", receipt)
    return receipt


def prepared(output, source_commit, *, fresh):
    output = Path(output)
    members = read_archive(regular(output / "input" / ARCHIVE_REL.name, ARCHIVE_BYTES))
    need(regular(output / "input" / (ARCHIVE_REL.name + ".sha256"), 256)
         == (ARCHIVE_SHA256 + "  " + ARCHIVE_REL.name + "\n").encode(), "retained_archive_sidecar")
    context_raw = regular(output / "host_context.json", 16384)
    context = strict(context_raw)
    check_recorded_context(context, source_commit)
    receipt = strict(regular(output / "preparation.json", 16384))
    need(receipt["status"] == "PRESERVED_REQUEST_PREPARED_NOT_AUTHORIZED"
         and receipt["source_commit"] == source_commit and receipt["request_sha256"] == REQUEST_SHA256
         and receipt["archive_sha256"] == ARCHIVE_SHA256 and receipt["archive_bytes"] == ARCHIVE_BYTES
         and receipt["host_context_sha256"] == digest(context_raw)
         and receipt["execution_authorized"] is False and receipt["authority_effect"] == "none", "preparation_receipt")
    expected_sources = {HELPER_REL.name, WORKFLOW_REL.name}
    need(set(receipt["hosted_sources"]) == expected_sources, "hosted_source_inventory")
    for name in expected_sources:
        raw = regular(output / "hosted_source" / name)
        need(receipt["hosted_sources"][name] == {"bytes": len(raw), "sha256": digest(raw)}, "hosted_source_binding")
    need(regular(output / "hosted_source" / HELPER_REL.name) == regular(Path(__file__)), "hosted_helper_binding")
    package = output / "package"
    expected_files = {name.removeprefix("package/") for name in members if name.startswith("package/")}
    for name in expected_files:
        need(regular(package / name) == members["package/" + name], "preserved_payload:" + name)
    if fresh:
        need(not (package / "CLAIM.json").exists() and not (package / "capture").exists(), "request_already_claimed")
    allowed_dirs = {str(parent) for name in expected_files for parent in PurePosixPath(name).parents if str(parent) != "."}
    for path in package.rglob("*"):
        need(not path.is_symlink(), "package_symlink")
        relative = path.relative_to(package).as_posix()
        if not fresh and (relative == "CLAIM.json" or relative == "capture" or relative.startswith("capture/")):
            continue
        need((path.is_dir() and relative in allowed_dirs) or (path.is_file() and relative in expected_files),
             "package_inventory")
    return context, receipt


class HostedInterruption(RuntimeError):
    """Cooperative stop: unchanged controller finally blocks retain/clean up."""


def run_capture(output, source_commit, request_sha, authorization, environment=None):
    need(request_sha == REQUEST_SHA256 and authorization == "I_AUTHORIZE_PD_SM_02_W1:" + REQUEST_SHA256,
         "owner_authorization_required")
    current = host_context(source_commit, environment)
    output = Path(output)
    context, _receipt = prepared(output, source_commit, fresh=True)
    need(canonical(current) == canonical(context), "capture_host_context_changed")
    need(regular(output / "image-binding.status", 128) == b"EXACT_IMAGE_ID_MATCH\n", "image_not_acquired")
    need(regular(output / "image-inspect.stdout", 256) == (IMAGE_ID + "\n").encode(), "acquired_image_id")
    controller = load_controller()
    # Consumed before invoking the controller, including a failed or interrupted call.
    window_path = output / "execution_window.json"
    window = {"schema_version": "pd_sm_02_w1_hosted_execution_window_v0", "state": "STARTED",
              "source_commit": source_commit, "github_run_id": context["github"]["GITHUB_RUN_ID"],
              "request_sha256": REQUEST_SHA256, "soft_deadline_seconds": SOFT_DEADLINE_SECONDS,
              "interruption_signal": None, "controller_status": None, "authority_effect": "none"}
    write_json(window_path, window)
    handled = (signal.SIGALRM, signal.SIGTERM, signal.SIGINT)
    previous = {sig: signal.getsignal(sig) for sig in handled}
    need(signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0), "existing_alarm")
    def stop(signum, _frame):
        # Do not interrupt cleanup a second time. A runner hard kill can still
        # prevent cleanup, finalization and upload; no successful disposal is inferred.
        signal.setitimer(signal.ITIMER_REAL, 0)
        for sig in handled:
            signal.signal(sig, signal.SIG_IGN)
        window["interruption_signal"] = signal.Signals(signum).name
        raise HostedInterruption(window["interruption_signal"])
    try:
        for sig in handled:
            signal.signal(sig, stop)
        signal.setitimer(signal.ITIMER_REAL, SOFT_DEADLINE_SECONDS)
        result = controller.execute(output / "package", REQUEST_SHA256, authorization)
        window["state"] = "RETURNED"
        window["controller_status"] = result.get("status")
        return result
    except BaseException:
        window["state"] = "EXCEPTION"
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        for sig in handled:
            signal.signal(sig, previous[sig])
        replace_json(window_path, window)


def record_result(output, source_commit, outcomes):
    """Never promote a merely replayable stopped capture to completed."""
    output = Path(output)
    summary = None
    context = None
    reason = None
    complete = False
    try:
        need(set(outcomes) == set(STEP_NAMES)
             and all(value == "success" for value in outcomes.values()), "workflow_step_incomplete")
        context, preparation = prepared(output, source_commit, fresh=False)
        for stem in ("prepare", "verify", "image-pull", "image-inspect", "capture", "replay"):
            need(regular(output / (stem + ".exitcode"), 16) == b"0\n", "step_exitcode:" + stem)
        need(strict(regular(output / "prepare.stdout")) == preparation, "prepare_output_binding")
        verification = strict(regular(output / "verify.stdout"))
        need(canonical(verification) == canonical({"status": "REQUEST_VALID_NOT_AUTHORIZED", "new_candidate_executions": 0,
                              "execution_authorized": False, "authority_effect": "none"}), "request_verification")
        need(strict(regular(output / "image_selection.json"))
             == {"image_id": IMAGE_ID, "pull_reference": PULL_REFERENCE, "platform": "linux/amd64"}, "image_selection")
        need(regular(output / "image-binding.status", 128) == b"EXACT_IMAGE_ID_MATCH\n"
             and regular(output / "image-inspect.stdout", 256) == (IMAGE_ID + "\n").encode(), "image_binding")
        window = strict(regular(output / "execution_window.json"))
        expected_window = {"schema_version": "pd_sm_02_w1_hosted_execution_window_v0", "state": "RETURNED",
                           "source_commit": source_commit, "github_run_id": context["github"]["GITHUB_RUN_ID"],
                           "request_sha256": REQUEST_SHA256, "soft_deadline_seconds": SOFT_DEADLINE_SECONDS,
                           "interruption_signal": None, "controller_status": "CAPTURE_COMPLETED_UNATTESTED",
                           "authority_effect": "none"}
        need(canonical(window) == canonical(expected_window), "execution_window_incomplete")
        claim = strict(regular(output / "package/CLAIM.json"))
        need(canonical(claim) == canonical({"request_sha256": REQUEST_SHA256, "run_id": REQUEST_RUN_ID, "attempt": 1,
                       "owner_command_acknowledged": True, "automatic_retry": False}), "native_claim")
        summary = strict(regular(output / "package/capture/summary.json"))
        need(summary == strict(regular(output / "capture.stdout")), "capture_output_binding")
        need(summary["status"] == "CAPTURE_COMPLETED_UNATTESTED"
             and summary["request_sha256"] == REQUEST_SHA256
             and type(summary["candidate_tokens_sent"]) is int and summary["candidate_tokens_sent"] == 5
             and type(summary["completed_case_records"]) is int and summary["completed_case_records"] == 5
             and summary["supervision_controls_completed"] == CONTROLS and summary["reason"] is None
             and summary["owner_command_acknowledged"] is True
             and summary["native_witness_observed"] is None and summary["containment_observed"] is None
             and summary["authority_effect"] == "none", "capture_not_complete")
        # Offline verification binds the retained files, not just their printed status.
        replay = load_controller().verify_capture(output / "package", REQUEST_SHA256)
        need(replay == strict(regular(output / "replay.stdout"))
             and replay["status"] == "CAPTURE_RECORDS_REPLAYED"
             and replay["record_status"] == "RECORDS_CONSISTENT"
             and replay["request_sha256"] == REQUEST_SHA256
             and replay["execution_authorized"] is False and replay["authority_effect"] == "none", "capture_replay_binding")
        observation = strict(regular(output / "package/capture/observations.json"))
        need([row["case_id"] for row in observation["cases"]] == list(ORDER)
             and all(row["status"] == "COMPLETE" for row in observation["cases"]), "complete_case_inventory")
        complete = True
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        reason = type(exc).__name__ + ":" + str(exc)
    # A capture step which may have started without a closed receipt is unknown.
    definitely_not_started = (outcomes.get("capture") == "skipped"
                              and not any((output / p).exists() for p in
                                          ("execution_window.json", "package/CLAIM.json", "package/capture")))
    result = {"schema_version": "pd_sm_02_w1_hosted_result_v0",
              "status": "CAPTURE_COMPLETED_UNATTESTED" if complete else "INCOMPLETE_OR_BLOCKED",
              "source_commit": source_commit, "request_sha256": REQUEST_SHA256,
              "archive_sha256": ARCHIVE_SHA256, "request_run_id": REQUEST_RUN_ID,
              "github_run_id": context["github"]["GITHUB_RUN_ID"] if context else None,
              "step_outcomes": outcomes, "reason": reason,
              "candidate_tokens_sent": 5 if complete else (0 if definitely_not_started else None),
              "completed_case_records": 5 if complete else (0 if definitely_not_started else None),
              "native_witness_observed": None, "containment_observed": None,
              "model_native_correspondence": "UNRESOLVED", "acquisition_authenticity": "NOT_EXTERNALLY_VERIFIED",
              "execution_authorized": False, "authority_effect": "none",
              "artifact_upload": "NOT_OBSERVED_BY_THIS_PREUPLOAD_RECORD"}
    write_json(output / "RESULT.json", result)
    (output / "ACQUISITION_STATUS.txt").write_text(result["status"] + "\n", encoding="ascii")
    files = {}
    total = 0
    for path in sorted(output.rglob("*")):
        need(not path.is_symlink(), "retained_symlink")
        if path.is_dir():
            continue
        name = path.relative_to(output).as_posix()
        need(name != "MANIFEST.json", "result_already_closed")
        raw = regular(path)
        total += len(raw)
        need(len(files) < 2048 and total <= 32 * 1024 * 1024, "retained_inventory_limit")
        files[name] = {"bytes": len(raw), "sha256": digest(raw)}
    write_json(output / "MANIFEST.json", {"schema_version": "pd_sm_02_w1_hosted_manifest_v0",
               "request_sha256": REQUEST_SHA256, "source_commit": source_commit,
               "files": files, "excluded_self_files": ["MANIFEST.json"], "authority_effect": "none"})
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for verb in ("prepare", "capture", "finalize"):
        item = sub.add_parser(verb)
        item.add_argument("--output", type=Path, required=True)
        item.add_argument("--source-commit", required=True)
        if verb == "prepare":
            item.add_argument("--repo-root", type=Path, required=True)
        if verb == "capture":
            item.add_argument("--request-sha256", required=True)
            item.add_argument("--authorize", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(args.repo_root, args.output, args.source_commit)
        elif args.command == "capture":
            result = run_capture(args.output, args.source_commit, args.request_sha256, args.authorize)
        else:
            outcomes = {name: os.environ.get("PD_" + name.upper() + "_OUTCOME", "missing") for name in STEP_NAMES}
            result = record_result(args.output, args.source_commit, outcomes)
            summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
            if summary_path:
                with open(summary_path, "a", encoding="utf-8") as handle:
                    handle.write("## W1 native capture\n\nStatus: `" + result["status"] + "`.\n\n")
                    handle.write("Request: `" + REQUEST_SHA256 + "`.\n\n")
                    handle.write("Order: P00 → N01 → N07 → N08 → N02; at most five candidate invocations.\n\n")
                    handle.write("First workflow attempt and local claim only; no global cross-dispatch anti-replay. "
                                 "An additional dispatch requires separate owner review. "
                                 "Inspect the original artifact and upload outcome. "
                                 "Acquisition is not externally attested; authority effect: `none`.\n")
        print(canonical(result).decode())
        failed = result.get("status") in ("STOPPED_WITH_EVIDENCE", "INCOMPLETE_OR_BLOCKED")
        if args.command == "capture":
            window = strict(regular(args.output / "execution_window.json"))
            failed = failed or window["interruption_signal"] is not None
        return 2 if failed else 0
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile, HostedInterruption) as exc:
        print(canonical({"status": "BLOCKED", "reason": type(exc).__name__ + ":" + str(exc),
                         "execution_authorized": False, "authority_effect": "none"}).decode())
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

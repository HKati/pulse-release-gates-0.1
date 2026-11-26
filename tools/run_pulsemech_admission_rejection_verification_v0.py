#!/usr/bin/env python3
"""Run the unchanged verifier twice for the fixed, already completed observation.

This driver only collects existing evidence and replays its verification. It
never dispatches a workflow, invokes a model, changes policy, or substitutes a
new prospective plan. A driver completion record is not a verifier report.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import selectors
import signal
import stat
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
from typing import Any


REPOSITORY = "HKati/pulse-release-gates-0.1"
SOURCE = "59b0aa8d93cb655db5452367e6ad43ced424d83a"
RUN_ID = 43445176088
ATTEMPT = 1
PROFILE = "pulse_ci_hosted_admission_rejection_v0"
CLAIM = "source_bound_admission_rejection_and_downstream_guard_observed"
PLAN_BYTES = 504432
PLAN_SHA256 = "e24fb63a61bb6cc3d1b3321a32ba0c7c520b57f59ccf8ea34fe3b14cadf5fa5a"
REQUEST_BYTES = 1597
REQUEST_SHA256 = "345a1a75ad41cef7a560314b6b482d3190409a55ee655a71f514d03316e24fd6"
COLLECTOR = "tools/acquire_pulsemech_compute_admission_rejection_v0.py"
CHECKER = "tools/check_pulsemech_compute_admission_rejection_v0.py"
SEMANTICS = "tools/pulsemech_compute_admission_rejection_semantics_v0.py"
TRANSPORT = "PULSE_safe_pack_v0/tools/q2_intake_io_v0.py"
TOTAL_SECONDS = 1800
STAGE_SECONDS = 600
LOG_LIMIT = 4 * 1024 * 1024
REPORT_LIMIT = 32 * 1024 * 1024
# -I excludes implicit sibling imports. The only added root is the reviewed
# script directory; runpy executes the original CLI with its original argv.
CLI_BOOTSTRAP = (
    "import runpy,sys; from pathlib import Path; "
    "script=Path(sys.argv[1]); sys.path.insert(0,str(script.parent)); "
    "sys.argv=sys.argv[1:]; runpy.run_path(str(script),run_name='__main__')"
)


class DriverError(ValueError):
    """A driver-owned, nonsecret diagnostic code."""


def need(value: Any, code: str) -> None:
    if not value:
        raise DriverError(code)


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def object_json(raw: bytes) -> dict:
    def pairs(items):
        need(len(items) == len({key for key, _ in items}), "duplicate_json_key")
        return dict(items)

    def invalid(_):
        raise DriverError("nonfinite_json_number")

    value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=invalid)
    need(type(value) is dict, "json_object_required")
    return value


def ordinary(path: Path) -> Path:
    path = Path(path).absolute()
    need(".." not in path.parts, "unsafe_path")
    for part in (*reversed(path.parents), path):
        need(not part.is_symlink(), "symlink_path_rejected")
    return path


def read(path: Path, maximum: int) -> bytes:
    path = ordinary(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
             and 0 <= before.st_size <= maximum, "regular_file_bound")
        raw = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
        need(len(raw) == before.st_size == after.st_size
             and before.st_mtime_ns == after.st_mtime_ns, "file_changed")
    return raw


def write(path: Path, raw: bytes) -> None:
    fd = os.open(ordinary(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)


def descriptor(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def file_descriptor(path: Path, maximum: int) -> dict:
    fd = os.open(ordinary(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
             and 0 < before.st_size <= maximum, "archive_file_bound")
        digest, total = hashlib.sha256(), 0
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            total += len(chunk)
            need(total <= maximum, "archive_file_bound")
            digest.update(chunk)
        after = os.fstat(stream.fileno())
        need(total == before.st_size == after.st_size
             and before.st_mtime_ns == after.st_mtime_ns, "archive_changed")
    return {"bytes": total, "sha256": digest.hexdigest()}


def remaining(deadline: float, maximum: float = STAGE_SECONDS) -> float:
    value = deadline - time.monotonic()
    need(value > 0, "driver_deadline_exceeded")
    return min(value, maximum)


def environment(home: Path) -> dict[str, str]:
    # The companion token never reaches a child. Signature replay preserves the
    # existing helper's token-free environment and real trusted-gh boundary.
    return {"PATH": "/usr/bin:/bin", "HOME": str(home), "TMPDIR": str(home),
            "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1",
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null", "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_TERMINAL_PROMPT": "0"}


def git(repo: Path, arguments: list[str], deadline: float) -> bytes:
    result = subprocess.run(["/usr/bin/git", "--no-replace-objects", "-c",
                             "credential.helper=", "-c", "core.hooksPath=/dev/null", *arguments],
                            cwd=repo, env=environment(repo), stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            timeout=remaining(deadline, 30), check=False)
    need(result.returncode == 0 and len(result.stdout) <= 1024 * 1024, "source_git_rejected")
    return result.stdout


def fixed_inputs(plan_path: Path) -> tuple[bytes, bytes, dict, dict]:
    plan_raw = read(plan_path, PLAN_BYTES)
    request_raw = read(plan_path.parent / "input/q2_request.json", REQUEST_BYTES)
    need(descriptor(plan_raw) == {"bytes": PLAN_BYTES, "sha256": PLAN_SHA256}, "fixed_plan_mismatch")
    need(descriptor(request_raw) == {"bytes": REQUEST_BYTES, "sha256": REQUEST_SHA256},
         "fixed_request_mismatch")
    plan, request = object_json(plan_raw), object_json(request_raw)
    need(plan.get("profile_id") == PROFILE and plan.get("authority_effect") == "none"
         and plan.get("source", {}).get("repository") == REPOSITORY
         and plan["source"].get("commit") == SOURCE, "fixed_plan_source_mismatch")
    need(request.get("evaluation_identity") == {
        "repository": REPOSITORY, "source_commit": SOURCE, "workflow": ".github/workflows/pulse_ci.yml",
        "event": "workflow_dispatch", "ref": "refs/heads/main"}, "fixed_request_source_mismatch")
    return plan_raw, request_raw, plan, request


def source_preflight(repo: Path, plan: dict, deadline: float) -> None:
    need(git(repo, ["rev-parse", "--verify", "HEAD^{commit}"], deadline) == (SOURCE + "\n").encode(),
         "fixed_source_head_mismatch")
    need(git(repo, ["status", "--porcelain", "--untracked-files=all"], deadline) == b"",
         "source_checkout_not_clean")
    rows = plan["source"].get("files")
    need(type(rows) is list and 0 < len(rows) <= 10000, "source_inventory_missing")
    seen = set()
    for row in rows:
        name = row.get("path")
        need(type(name) is str and name not in seen and not PurePosixPath(name).is_absolute()
             and "\\" not in name and all(p not in ("", ".", "..") for p in name.split("/")),
             "source_inventory_path")
        seen.add(name)
        raw = read(repo / name, 64 * 1024 * 1024)
        mode = "100755" if (repo / name).stat().st_mode & 0o111 else "100644"
        need(descriptor(raw) == {"bytes": row["bytes"], "sha256": row["sha256"]}
             and mode == row["mode"], "source_worktree_mismatch")
    remaining(deadline)


def load_reviewed(repo: Path) -> SimpleNamespace:
    def module(relative: str, name: str):
        path = repo / relative
        spec = importlib.util.spec_from_file_location(name, path)
        need(spec is not None, "reviewed_module_unavailable")
        result = importlib.util.module_from_spec(spec)
        # Execute the already bound bytes rather than accepting an old pyc.
        exec(compile(read(path, 4 * 1024 * 1024), str(path), "exec"), result.__dict__)
        return result
    return SimpleNamespace(io=module(TRANSPORT, "admission_original_transport"),
                           semantics=module(SEMANTICS, "admission_original_semantics"))


def tokens() -> tuple[str, str]:
    github = os.environ.pop("GH_TOKEN", "")
    fallback = os.environ.pop("GITHUB_TOKEN", "")
    companion = os.environ.pop("PULSE_Q2_TRANSPORT_TOKEN", "")
    github = github or fallback
    for value, code in ((github, "github_token_missing"), (companion, "companion_token_missing")):
        need(type(value) is str and 0 < len(value) <= 4096
             and all(33 <= ord(c) <= 126 for c in value), code)
    return github, companion


def error_code(exc: Exception, reviewed: SimpleNamespace | None) -> str:
    if isinstance(exc, DriverError):
        return str(exc)
    if reviewed is not None:
        intake_type = getattr(reviewed.io, "IntakeError", None)
        if isinstance(intake_type, type) and isinstance(exc, intake_type):
            value = getattr(exc, "code", None)
            if value in reviewed.io.ERROR_CODES:
                return value
        semantic_type = getattr(reviewed.semantics, "SemanticVerificationError", None)
        if isinstance(semantic_type, type) and isinstance(exc, semantic_type) and str(exc) in {
            "trusted_python_path_required", "python_runtime_or_dependencies_unavailable",
            "q2_exact_replay_runtime_required", "trusted_gh_symlink_rejected",
            "trusted_gh_ownership_required", "trusted_gh_executable_required",
            "trusted_gh_unavailable", "trusted_gh_elf_required", "file_unavailable_or_unsafe",
        }:
            return str(exc)
    return "verification_driver_rejected"


def child(argv: list[str], *, repo: Path, home: Path, output: Path, stage: str,
          deadline: float, secrets: tuple[str, ...], github_token: str | None = None) -> dict:
    env = environment(home)
    if github_token is not None:
        env["GH_TOKEN"] = github_token
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    result = {"exit_code": None, "timed_out": False, "output_limit_exceeded": False}
    process = None
    end = time.monotonic() + remaining(deadline)
    try:
        process = subprocess.Popen(argv, cwd=repo, env=env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ, "stdout")
            selector.register(process.stderr, selectors.EVENT_READ, "stderr")
            while selector.get_map() or process.poll() is None:
                if time.monotonic() >= end:
                    result["timed_out"] = True
                    break
                for key, _ in selector.select(min(0.25, max(0, end - time.monotonic()))):
                    data = os.read(key.fileobj.fileno(), 65536)
                    if not data:
                        selector.unregister(key.fileobj)
                        continue
                    target = buffers[key.data]
                    target.extend(data[:max(0, LOG_LIMIT - len(target))])
                    if len(target) >= LOG_LIMIT:
                        result["output_limit_exceeded"] = True
                if result["output_limit_exceeded"]:
                    break
    finally:
        if process is not None:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
            result["exit_code"] = process.wait(timeout=5)
            for stream in (process.stdout, process.stderr):
                if stream is not None:
                    stream.close()
        for name, raw in buffers.items():
            value = bytes(raw)
            for secret in sorted(set(secrets), key=len, reverse=True):
                value = value.replace(secret.encode("utf-8"), b"***")
            write(output / "stages" / (stage + "." + name + ".txt"), value)
    return result


def command(python: Path, repo: Path, script: str, *arguments: str) -> list[str]:
    return [str(python), "-I", "-B", "-c", CLI_BOOTSTRAP, str(repo / script), *arguments]


def require_child(result: dict) -> None:
    need(result.get("timed_out") is False, "child_timeout")
    need(result.get("output_limit_exceeded") is False, "child_output_limit")
    need(type(result.get("exit_code")) is int and result["exit_code"] == 0, "child_failed")


def compare_reports(first: Path, second: Path) -> dict:
    raws = [read(path, REPORT_LIMIT) for path in (first, second)]
    for raw in raws:
        report = object_json(raw)
        need(canonical(report) == raw, "checker_report_not_canonical")
        need(report.get("format") == "pulsemech_compute_admission_rejection_report_v0"
             and report.get("profile_id") == PROFILE and report.get("accepted") is True
             and report.get("authority_effect") == "none" and report.get("bounded_claim") == CLAIM,
             "checker_report_not_accepted")
        identity = report.get("run") or {}
        need(report.get("source", {}).get("commit") == SOURCE
             and identity.get("repository") == REPOSITORY and identity.get("source_commit") == SOURCE
             and type(identity.get("run_id")) is int and identity["run_id"] == RUN_ID
             and type(identity.get("run_attempt")) is int and identity["run_attempt"] == ATTEMPT,
             "checker_report_identity_mismatch")
    need(raws[0] == raws[1], "checker_reports_differ")
    return descriptor(raws[0])


def run(repo_root: Path, plan_path: Path, out_dir: Path, replay_python: Path) -> dict:
    repo, plan_path, output = map(ordinary, (repo_root, plan_path, out_dir))
    need(repo.is_dir() and output.parent.is_dir() and not output.is_relative_to(repo)
         and not repo.is_relative_to(output), "output_must_be_external")
    need(not output.exists(), "output_already_exists")
    output.mkdir(mode=0o700)
    (output / "stages").mkdir(mode=0o700)
    (output / "input").mkdir(mode=0o700)
    summary = {"format": "pulsemech_admission_rejection_driver_v0", "source_commit": SOURCE,
               "run_id": RUN_ID, "run_attempt": ATTEMPT, "authority_effect": "none",
               "verification_completed": False, "checker_reports_equal": False,
               "driver_record_is_verifier_report": False}
    stage, details = "preflight", {}
    reviewed = None
    deadline = time.monotonic() + TOTAL_SECONDS

    def completed(extra=None):
        write(output / "stages" / (stage + ".json"), canonical({
            "stage": stage, "status": "completed", "authority_effect": "none", **details, **(extra or {})}))

    try:
        github_token, companion_token = tokens()
        plan_raw, request_raw, plan, request = fixed_inputs(plan_path)
        source_preflight(repo, plan, deadline)
        reviewed = load_reviewed(repo)
        replay_python = ordinary(replay_python)
        with tempfile.TemporaryDirectory(prefix="pulse-admission-private-", dir=output.parent) as temp_name:
            private = Path(temp_name)
            home = private / "home"
            home.mkdir(mode=0o700)
            runtime = reviewed.semantics._python_identity(replay_python, cwd=repo, home=home, q2=True)
            verifier_python = Path(sys.executable).resolve(strict=True)
            reviewed.semantics._python_identity(verifier_python, cwd=repo, home=home, q2=False)
            _, backend = reviewed.semantics._trusted_gh()
            code, help_text, _ = reviewed.semantics._run(
                ["/usr/bin/gh", "attestation", "verify", "--help"], cwd=repo, home=home,
                timeout=remaining(deadline, 30))
            need(code == 0 and all(flag in help_text for flag in (
                b"--bundle", b"--signer-workflow", b"--source-digest", b"--predicate-type",
                b"--cert-oidc-issuer", b"--format", b"--repo")), "gh_attestation_capability_missing")
            profile = reviewed.io.strict_json(reviewed.io.read_file(repo / reviewed.io.PROFILE_PATH, 256 * 1024))
            delivery = reviewed.io.validate_release_delivery(profile)
            reviewed.io.validate(request, reviewed.io.read_file(repo / reviewed.io.REQUEST_SCHEMA, 128 * 1024))
            remaining(deadline)
            write(output / "plan.json", plan_raw)
            write(output / "input/q2_request.json", request_raw)
            write(output / "inputs.json", canonical({"immutable_delivery": delivery,
                "capture_expectation": request["capture_expectation"], "release_subject": request["release_subject"],
                "archive_bytes_in_uploaded_output": False, "authority_effect": "none"}))
            completed({"plan": descriptor(plan_raw), "request": descriptor(request_raw),
                       "replay_python": runtime, "trusted_gh": backend})

            stage, details = "collect", {}
            details = child(command(verifier_python, repo, COLLECTOR,
                "--plan", str(output / "plan.json"), "--run-id", str(RUN_ID), "--attempt", str(ATTEMPT),
                "--out-dir", str(output / "evidence")), repo=repo, home=home, output=output,
                stage=stage, deadline=deadline, secrets=(github_token, companion_token), github_token=github_token)
            require_child(details)
            acquired = object_json(read(output / "evidence/acquisition.json", 16 * 1024 * 1024))
            need(acquired.get("completed") is True and acquired.get("errors") == []
                 and acquired.get("repository") == REPOSITORY and acquired.get("source_commit") == SOURCE
                 and type(acquired.get("run_id")) is int and acquired["run_id"] == RUN_ID
                 and type(acquired.get("run_attempt")) is int and acquired["run_attempt"] == ATTEMPT
                 and acquired.get("plan_sha256") == PLAN_SHA256, "acquisition_identity_or_completion")
            completed()

            stage, details = "retrieve", {}
            archives = private / "archives"
            archives.mkdir(mode=0o700)
            with reviewed.io.interrupt_boundary(remaining(deadline)) as delivery_deadline:
                reviewed.io.GitHubReleaseTransport(companion_token).acquire(
                    profile, request, archives, delivery_deadline)
            for name, binding in (("capture", request["capture_expectation"]), ("capsule", request["release_subject"])):
                need(file_descriptor(archives / (name + ".zip"), 1024 * 1024 * 1024) == {
                    "bytes": binding["archive_size_bytes"], "sha256": binding["archive_sha256"]},
                    "retrieved_archive_mismatch")
            completed({"capture_and_capsule_verified": True})

            for number in (1, 2):
                stage, details = "check-" + str(number), {}
                details = child(command(verifier_python, repo, CHECKER,
                    "--repo-root", str(repo), "--plan", str(output / "plan.json"),
                    "--evidence-dir", str(output / "evidence"), "--expected-source", SOURCE,
                    "--expected-run-id", str(RUN_ID), "--expected-attempt", str(ATTEMPT),
                    "--capture", str(archives / "capture.zip"), "--capsule", str(archives / "capsule.zip"),
                    "--replay-python", str(replay_python), "--out", str(output / (stage + ".json"))),
                    repo=repo, home=home, output=output, stage=stage, deadline=deadline,
                    secrets=(github_token, companion_token))
                require_child(details)
                need((output / (stage + ".json")).is_file(), "checker_report_missing")
                completed()

            stage, details = "compare", {}
            shared = compare_reports(output / "check-1.json", output / "check-2.json")
            completed({"matching_canonical_report": shared})
            stage, details = "cleanup", {}
        need(not private.exists(), "private_cleanup_failed")
        completed({"private_archives_removed": True})
        summary.update(verification_completed=True, checker_reports_equal=True,
                       matching_checker_report=shared, reports=["check-1.json", "check-2.json"])
    except Exception as exc:
        error = error_code(exc, reviewed)
        # Neither arbitrary exception text nor transport/credential values cross
        # this boundary. Preserve the original child reports, including failures.
        summary.update(failed_stage=stage, error=error)
        path = output / "stages" / (stage + ".json")
        if not path.exists():
            write(path, canonical({"stage": stage, "status": "failed", "error": error,
                                   "authority_effect": "none", **details}))
    write(output / "driver-result.json", canonical(summary))
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repo-root", "plan", "out-dir", "replay-python"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run(args.repo_root, args.plan, args.out_dir, args.replay_python)
    except Exception:
        print('{"authority_effect":"none","error":"driver_output_or_input_path_rejected",'
              '"verification_completed":false}', file=sys.stderr)
        return 1
    print(canonical(result).decode(), end="")
    return 0 if result["verification_completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

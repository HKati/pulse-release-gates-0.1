#!/usr/bin/env python3
"""Prepare an exact, prospective admission-rejection observation plan.

This tool reads trusted Git objects and supplied original input bytes. It does
not dispatch a workflow, execute the subject, or grant release authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
from typing import Any
import zipfile

import jsonschema
import yaml

FORMAT = "pulsemech_compute_admission_rejection_plan_v0"
PROFILE_ID = "pulse_ci_hosted_admission_rejection_v0"
REPOSITORY = "HKati/pulse-release-gates-0.1"
WORKFLOW_PATH = ".github/workflows/pulse_ci.yml"
WORKFLOW_SHA256 = "7489fca657c4b2541da4946237b3f864aae7f9247198e5a3c6cbc3429a32db6a"
POLICY_PATH = "pulse_gate_policy_v0.yml"
POLICY_SHA256 = "00fc5eef5fa3f240028aaf636a2e43ba29f1da000484c7a2f1baafcdd3c4ae8c"
CAPTURE_SHA256 = "88c0335d57bf5dd207840eb129fc2fe36c453a2fb0d2da72e48f9689c4758cc6"
CAPSULE_SHA256 = "3625a975b4794442fe47b7f5eceb8bee5ff4150ff30b495b1d2a609e8a165734"
CAPSULE_MANIFEST_SHA256 = "8dfa1b9df8ed7fbd8ea8b749555ba73ebf24f5d8aeb187d15c51163137a0c857"
LIMITS = {
    "max_json_bytes": 16777216,
    "max_log_bytes": 33554432,
    "max_artifact_bytes": 134217728,
    "max_total_bytes": 536870912,
    "max_jobs": 64,
    "max_artifacts": 64,
    "max_pages": 16,
    "max_redirects": 5,
    "request_timeout_seconds": 60,
}
EXCLUDED_CLAIMS = [
    "positive_full_workflow_completion",
    "final_check_gates_decision",
    "release_authority",
    "external_tool_and_host_source_closure",
    "resource_and_timing_measurement",
    "original_runtime_consumption_proved_by_later_replay",
    "human_semantic_label_correctness",
]
JOB_STEPS = {
    "pulse": 83,
    "attest_release_authority_artifact_binding": 2,
    "attest_llamaguard_current_run_summary": 8,
    "release_grade_recorded_path": 33,
    "attest_release_grade_artifact_binding": 2,
    "assemble_release_grade_reference_package": 6,
    "verify_release_grade_reference_package": 8,
    "tools-tests": 5,
}
PULSE_SUCCESS = frozenset((*range(1, 9), *range(10, 17), 18, 25, 28, 30, 32, 34))


class PlanError(ValueError):
    """A stable, nonsecret rejection reason."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise PlanError(code)


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def strict_object(raw: bytes) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result

    def invalid_constant(_: str) -> None:
        raise PlanError("nonfinite_json_number")

    try:
        result = json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                            parse_constant=invalid_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise PlanError("invalid_json") from exc
    require(isinstance(result, dict), "json_object_required")
    return result


def safe_relative(value: str) -> str:
    require(isinstance(value, str) and value != "", "invalid_relative_path")
    require(not any(ord(c) < 32 or ord(c) == 127 for c in value), "unsafe_path_character")
    require("\\" not in value and ":" not in value, "unsafe_relative_path")
    path = PurePosixPath(value)
    require(not path.is_absolute() and all(p not in ("", ".", "..") for p in value.split("/")),
            "unsafe_relative_path")
    return value


def no_symlink_path(path: Path) -> Path:
    absolute = Path(os.path.abspath(path))
    for component in (*reversed(absolute.parents), absolute):
        require(not component.is_symlink(), "symlink_path_rejected")
    return absolute


def read_regular(path: Path, maximum: int) -> bytes:
    path = no_symlink_path(path)
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode), "regular_file_required")
        require(info.st_size <= maximum, "file_size_limit")
        raw = stream.read(maximum + 1)
        require(len(raw) <= maximum and len(raw) == info.st_size, "file_changed_or_oversized")
        return raw


def hash_regular(path: Path, maximum: int) -> dict[str, Any]:
    path = no_symlink_path(path)
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_size <= maximum, "input_file_limit")
        size = 0
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(chunk)
            require(size <= maximum, "input_file_limit")
            digest.update(chunk)
        after = os.fstat(stream.fileno())
        require(size == before.st_size == after.st_size and
                before.st_mtime_ns == after.st_mtime_ns, "input_changed")
    return {"bytes": size, "sha256": digest.hexdigest()}


def create_output(path: Path) -> Path:
    path = no_symlink_path(path)
    require(path.parent.is_dir(), "output_parent_missing")
    path.mkdir(mode=0o700, exist_ok=False)
    return path


def write_new(path: Path, raw: bytes) -> None:
    no_symlink_path(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)


def _git(root: Path, args: list[str], data: bytes | None = None) -> bytes:
    environment = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    environment.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                        "GIT_TERMINAL_PROMPT": "0", "GIT_NO_REPLACE_OBJECTS": "1"})
    try:
        result = subprocess.run(["git", "--no-replace-objects", "-C", str(root), *args],
                                input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=60, check=True, env=environment)
    except (OSError, subprocess.SubprocessError) as exc:
        raise PlanError("git_object_read_failed") from exc
    return result.stdout


def source_snapshot(repo_root: Path, source_commit: str) -> tuple[str, list[dict[str, Any]], dict[str, bytes]]:
    """Read the complete regular-blob tree, never mutable worktree file bytes."""
    require(re.fullmatch(r"[0-9a-f]{40}", source_commit) is not None, "full_source_commit_required")
    root = no_symlink_path(repo_root)
    require(_git(root, ["rev-parse", "--verify", f"{source_commit}^{{commit}}"]).decode().strip()
            == source_commit, "source_commit_mismatch")
    tree = _git(root, ["rev-parse", f"{source_commit}^{{tree}}"]).decode().strip()
    entries = _git(root, ["ls-tree", "-rz", "--full-tree", source_commit]).split(b"\0")
    listed: list[tuple[str, str, str]] = []
    for entry in entries:
        if not entry:
            continue
        metadata, name = entry.split(b"\t", 1)
        mode, kind, oid = metadata.decode("ascii").split()
        require(kind == "blob" and mode in ("100644", "100755"), "nonregular_git_source")
        listed.append((safe_relative(name.decode("utf-8")), mode, oid))
    listed.sort()
    require(0 < len(listed) <= 10000, "source_file_count_limit")
    require(len({p for p, _, _ in listed}) == len(listed), "duplicate_source_path")
    sizes = _git(root, ["cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
                 b"".join(oid.encode() + b"\n" for _, _, oid in listed)).splitlines()
    require(len(sizes) == len(listed), "git_inventory_incomplete")
    total = 0
    for (_, _, oid), row in zip(listed, sizes):
        parts = row.decode("ascii").split()
        require(len(parts) == 3 and parts[:2] == [oid, "blob"], "git_blob_identity")
        size = int(parts[2])
        require(0 <= size <= 64 * 1024 * 1024, "source_blob_size_limit")
        total += size
    require(total <= 256 * 1024 * 1024, "source_tree_size_limit")
    raw = _git(root, ["cat-file", "--batch"],
               b"".join(oid.encode() + b"\n" for _, _, oid in listed))
    offset = 0
    inventory: list[dict[str, Any]] = []
    contents: dict[str, bytes] = {}
    for path, mode, oid in listed:
        end = raw.find(b"\n", offset)
        require(end >= 0, "git_batch_truncated")
        fields = raw[offset:end].decode("ascii").split()
        require(len(fields) == 3 and fields[:2] == [oid, "blob"], "git_batch_identity")
        size = int(fields[2])
        data = raw[end + 1:end + 1 + size]
        require(len(data) == size and raw[end + 1 + size:end + 2 + size] == b"\n", "git_batch_truncated")
        require(hashlib.sha1(b"blob " + str(size).encode() + b"\0" + data).hexdigest() == oid,
                "git_blob_digest_mismatch")
        offset = end + 2 + size
        inventory.append({"path": path, "mode": mode, "git_blob_sha1": oid,
                          "bytes": size, "sha256": hashlib.sha256(data).hexdigest()})
        contents[path] = data
    require(offset == len(raw), "git_batch_trailing_data")
    return tree, inventory, contents


def expected_graph(workflow_raw: bytes) -> list[dict[str, Any]]:
    """A reviewed outcome mapping over every step of the pinned workflow."""
    require(hashlib.sha256(workflow_raw).hexdigest() == WORKFLOW_SHA256, "workflow_not_reviewed")
    workflow = yaml.safe_load(workflow_raw)
    jobs = workflow["jobs"]
    require(list(jobs) == list(JOB_STEPS), "workflow_job_order_changed")
    graph = []
    for job_id, job in jobs.items():
        require(len(job["steps"]) == JOB_STEPS[job_id], "workflow_step_count_changed")
        conclusion = ("failure" if job_id in ("pulse", "release_grade_recorded_path") else
                      "success" if job_id in ("attest_llamaguard_current_run_summary", "tools-tests") else "skipped")
        needs = job.get("needs", [])
        needs = [needs] if isinstance(needs, str) else needs
        steps = []
        for ordinal, step in enumerate(job["steps"], 1):
            if conclusion == "skipped":
                result = "not_instantiated"
            elif job_id == "pulse":
                result = "success" if ordinal in PULSE_SUCCESS else "failure" if ordinal == 17 else "skipped"
            elif job_id == "release_grade_recorded_path":
                result = "success" if ordinal <= 3 else "failure" if ordinal == 4 else "skipped"
            else:
                result = "success"
            command = step.get("run")
            steps.append({"ordinal": ordinal, "id": step.get("id"),
                          "name": step.get("name", step.get("uses", "")).strip(),
                          "if": step.get("if"), "uses": step.get("uses"),
                          "run_sha256": hashlib.sha256(command.encode()).hexdigest() if command is not None else None,
                          "expected_result": result})
        graph.append({"id": job_id, "name": job.get("name", job_id).strip(), "needs": needs,
                      "if": job.get("if"), "expected_conclusion": conclusion, "steps": steps})
    return graph


def validate_request(raw: bytes, sources: dict[str, bytes], source_commit: str) -> dict[str, Any]:
    require(0 < len(raw) <= 16384, "request_size_limit")
    request = strict_object(raw)
    schema = strict_object(sources["schemas/q2_release_intake_request_v0.schema.json"])
    try:
        jsonschema.Draft202012Validator(schema).validate(request)
    except jsonschema.ValidationError as exc:
        raise PlanError("q2_request_schema_rejected") from exc
    require(request["evaluation_identity"]["source_commit"] == source_commit, "q2_evaluation_source_mismatch")
    profile = strict_object(sources["PULSE_safe_pack_v0/profiles/q2_reference_release_intake_v0.json"])
    require(request["selection"] == profile["selection"] and
            request["capture_expectation"] == profile["capture_expectation"], "q2_profile_binding_mismatch")
    require(hashlib.sha256(sources[request["selection"]["path"]]).hexdigest() == request["selection"]["sha256"],
            "q2_selection_digest_mismatch")
    return request


def capsule_manifest(path: Path) -> bytes:
    """Read one bounded regular member; never extract or execute the capsule."""
    try:
        with zipfile.ZipFile(no_symlink_path(path)) as archive:
            members = archive.infolist()
            require(0 < len(members) <= 20000, "capsule_member_count_limit")
            names = []
            for info in members:
                name = info.filename[:-1] if info.is_dir() else info.filename
                safe_relative(name)
                names.append(info.filename)
            require(len(set(names)) == len(names), "duplicate_capsule_member")
            info = archive.getinfo("capsule.json")
            mode = info.external_attr >> 16
            require(not info.is_dir() and not stat.S_ISLNK(mode) and
                    stat.S_IFMT(mode) in (0, stat.S_IFREG), "capsule_manifest_not_regular")
            require(info.file_size <= 1024 * 1024 and not info.flag_bits & 1, "capsule_manifest_limit")
            with archive.open(info) as stream:
                raw = stream.read(1024 * 1024 + 1)
            require(len(raw) == info.file_size, "capsule_manifest_size")
            strict_object(raw)
            return raw
    except (KeyError, OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise PlanError("invalid_capsule_archive") from exc


def prepare(repo_root: Path, source_commit: str, q2_request: Path, capture: Path,
            capsule: Path, out_dir: Path) -> dict[str, Any]:
    tree, inventory, sources = source_snapshot(repo_root, source_commit)
    require(hashlib.sha256(sources[POLICY_PATH]).hexdigest() == POLICY_SHA256, "policy_not_reviewed")
    graph = expected_graph(sources[WORKFLOW_PATH])
    request_raw = read_regular(q2_request, 16384)
    request = validate_request(request_raw, sources, source_commit)
    capture_identity = hash_regular(capture, 8 * 1024 * 1024)
    capsule_identity = hash_regular(capsule, 2 * 1024 * 1024 * 1024)
    require(capture_identity == {"bytes": 1809263, "sha256": CAPTURE_SHA256}, "capture_not_selected_original")
    require(capsule_identity == {"bytes": 452116385, "sha256": CAPSULE_SHA256}, "capsule_not_selected_original")
    for actual, expected in ((capture_identity, request["capture_expectation"]),
                             (capsule_identity, request["release_subject"])):
        require(actual["bytes"] == expected["archive_size_bytes"] and
                actual["sha256"] == expected["archive_sha256"], "q2_input_binding_mismatch")
    manifest_sha256 = hashlib.sha256(capsule_manifest(capsule)).hexdigest()
    require(manifest_sha256 == CAPSULE_MANIFEST_SHA256 == request["release_subject"]["capsule_manifest_sha256"],
            "capsule_manifest_digest_mismatch")
    plan = {
        "format": FORMAT, "profile_id": PROFILE_ID, "authority_effect": "none",
        "source": {"repository": REPOSITORY, "commit": source_commit, "tree": tree,
                   "workflow_path": WORKFLOW_PATH, "workflow_sha256": WORKFLOW_SHA256,
                   "policy_sha256": POLICY_SHA256, "files": inventory},
        "request": {"path": "input/q2_request.json", "bytes": len(request_raw),
                    "sha256": hashlib.sha256(request_raw).hexdigest()},
        "inputs": {"capture": capture_identity,
                   "capsule": {**capsule_identity, "manifest_sha256": manifest_sha256}},
        "dispatch": {"event": "workflow_dispatch", "ref": "refs/heads/main",
                     "strict_external_evidence": True, "llamaguard_evidence_mode": "hosted_full_runtime"},
        "expected_graph": graph, "limits": dict(LIMITS), "excluded_claims": list(EXCLUDED_CLAIMS),
    }
    output = create_output(out_dir)
    (output / "input").mkdir(mode=0o700)
    write_new(output / "input/q2_request.json", request_raw)
    write_new(output / "plan.json", canonical_bytes(plan))
    return plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("prepare")
    for name in ("repo-root", "q2-request", "capture", "capsule", "out-dir"):
        command.add_argument("--" + name, required=True, type=Path)
    command.add_argument("--source-commit", required=True)
    args = parser.parse_args(argv)
    try:
        plan = prepare(args.repo_root, args.source_commit, args.q2_request,
                       args.capture, args.capsule, args.out_dir)
    except (PlanError, OSError, ValueError, KeyError) as exc:
        code = str(exc) if isinstance(exc, PlanError) else "plan_preparation_failed"
        print(canonical_bytes({"error": code, "authority_effect": "none"}).decode(), end="", file=sys.stderr)
        return 1
    print(canonical_bytes({"plan": str(args.out_dir / "plan.json"), "profile_id": PROFILE_ID,
                           "source_commit": plan["source"]["commit"], "authority_effect": "none"}).decode(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

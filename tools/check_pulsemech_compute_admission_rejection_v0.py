#!/usr/bin/env python3
"""Independently check an exact, source-bound admission-rejection observation.

This is a separate negative observation profile. It never dispatches a workflow,
executes a model, relaxes a gate, or certifies the legacy success profile. API
records are preserved acquisition evidence, not independently signed receipts.
Semantic replay is later replay, not proof of original runtime consumption.
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
from typing import Any
import zipfile

import jsonschema
import yaml

PROFILE = "pulse_ci_hosted_admission_rejection_v0"
REPOSITORY = "HKati/pulse-release-gates-0.1"
WORKFLOW = ".github/workflows/pulse_ci.yml"
WORKFLOW_SHA = "7489fca657c4b2541da4946237b3f864aae7f9247198e5a3c6cbc3429a32db6a"
POLICY = "pulse_gate_policy_v0.yml"
POLICY_SHA = "00fc5eef5fa3f240028aaf636a2e43ba29f1da000484c7a2f1baafcdd3c4ae8c"
REGISTRY = "pulse_gate_registry_v0.yml"
GATE_PLAN = "PULSE_safe_pack_v0/profiles/required_gate_evaluations_v0.json"
GATE_TOOL = "PULSE_safe_pack_v0/tools/evaluate_required_gate_v0.py"
RECORDER = "PULSE_safe_pack_v0/tools/run_recorded_required_gate_evaluations_v0.py"
ARTIFACT_ROOT = "PULSE_safe_pack_v0/artifacts/"
LIMITS = {"max_json_bytes": 16777216, "max_log_bytes": 33554432,
          "max_artifact_bytes": 134217728, "max_total_bytes": 536870912,
          "max_jobs": 64, "max_artifacts": 64, "max_pages": 16,
          "max_redirects": 5, "request_timeout_seconds": 60}
DISPATCH = {"event": "workflow_dispatch", "ref": "refs/heads/main",
            "strict_external_evidence": True,
            "llamaguard_evidence_mode": "hosted_full_runtime"}
EXCLUDED = ["positive_full_workflow_completion", "final_check_gates_decision",
            "release_authority", "external_tool_and_host_source_closure",
            "resource_and_timing_measurement",
            "original_runtime_consumption_proved_by_later_replay",
            "human_semantic_label_correctness"]
SELECTED_INPUTS = {
    "capture": {"bytes": 1809263,
                "sha256": "88c0335d57bf5dd207840eb129fc2fe36c453a2fb0d2da72e48f9689c4758cc6"},
    "capsule": {"bytes": 452116385,
                "sha256": "3625a975b4794442fe47b7f5eceb8bee5ff4150ff30b495b1d2a609e8a165734",
                "manifest_sha256": "8dfa1b9df8ed7fbd8ea8b749555ba73ebf24f5d8aeb187d15c51163137a0c857"}}
NEGATIVE_STEPS = {("pulse", "release-grade record current-run required-gate evidence"),
                  ("release_grade_recorded_path", "Download pre-attestation pulse artifacts")}
HOSTED_NAMES = {"llamaguard_raw.jsonl", "llamaguard_evaluator_manifest_v0.json",
                "llamaguard_summary.json"}
ATTESTED_NAMES = HOSTED_NAMES | {"llamaguard_summary.bundle.json",
                                "llamaguard_summary.envelope.json",
                                "llamaguard_attestation_verifier_v1.json"}


class VerificationError(ValueError):
    """Stable, nonsecret reason for rejecting a carrier."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise VerificationError(code)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False) + "\n").encode()


def object_json(raw: bytes) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in items:
            require(key not in out, "duplicate_json_key")
            out[key] = value
        return out

    def constant(_: str) -> None:
        raise VerificationError("nonfinite_json_number")

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                           parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise VerificationError("invalid_json") from exc
    require(isinstance(value, dict), "json_object_required")
    return value


def safe_path(name: str) -> str:
    require(isinstance(name, str) and bool(name), "invalid_relative_path")
    require(not any(ord(c) < 32 or ord(c) == 127 for c in name), "unsafe_path_character")
    require("\\" not in name and ":" not in name and not PurePosixPath(name).is_absolute()
            and all(x not in ("", ".", "..") for x in name.split("/")), "unsafe_relative_path")
    return name


def ordinary(path: Path) -> Path:
    path = Path(os.path.abspath(path))
    for part in (*reversed(path.parents), path):
        require(not part.is_symlink(), "symlink_path_rejected")
    return path


def read(path: Path, maximum: int) -> bytes:
    fd = os.open(ordinary(path), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_size <= maximum, "file_type_or_size")
        raw = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
        require(len(raw) == before.st_size == after.st_size and len(raw) <= maximum
                and before.st_mtime_ns == after.st_mtime_ns, "file_changed_or_oversized")
    return raw


def file_identity(path: Path, maximum: int) -> dict[str, Any]:
    fd = os.open(ordinary(path), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    h = hashlib.sha256()
    size = 0
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_size <= maximum, "input_type_or_size")
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(chunk)
            require(size <= maximum, "input_size_limit")
            h.update(chunk)
        after = os.fstat(stream.fileno())
        require(size == before.st_size == after.st_size and
                before.st_mtime_ns == after.st_mtime_ns, "input_changed")
    return {"bytes": size, "sha256": h.hexdigest()}


def git(root: Path, args: list[str], input_bytes: bytes | None = None) -> bytes:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
               GIT_NO_REPLACE_OBJECTS="1", GIT_TERMINAL_PROMPT="0")
    try:
        return subprocess.run(["git", "--no-replace-objects", "-C", str(root),
                               "-c", "core.hooksPath=/dev/null", *args], input=input_bytes,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120,
                              check=True, env=env).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        raise VerificationError("git_object_operation_failed") from exc


def source_objects(root: Path, commit: str) -> tuple[str, list[dict[str, Any]], dict[str, bytes]]:
    """Independently inventory every Git blob, never the mutable source worktree."""
    require(re.fullmatch(r"[0-9a-f]{40}", commit) is not None, "full_source_commit_required")
    require(git(root, ["rev-parse", "--verify", commit + "^{commit}"]).decode().strip() == commit,
            "source_commit_not_found")
    tree = git(root, ["rev-parse", commit + "^{tree}"]).decode().strip()
    entries = []
    for row in git(root, ["ls-tree", "-rz", "--full-tree", commit]).split(b"\0"):
        if row:
            header, path = row.split(b"\t", 1)
            mode, kind, oid = header.decode("ascii").split()
            require(kind == "blob" and mode in ("100644", "100755"), "nonregular_source_entry")
            entries.append((safe_path(path.decode("utf-8")), mode, oid))
    entries.sort()
    require(0 < len(entries) <= 10000 and len({e[0] for e in entries}) == len(entries),
            "source_file_count_or_duplicate")
    query = b"".join(oid.encode() + b"\n" for _, _, oid in entries)
    sizes = git(root, ["cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"], query).splitlines()
    require(len(sizes) == len(entries), "source_batch_count")
    total = 0
    for (_, _, oid), line in zip(entries, sizes):
        fields = line.decode().split()
        require(len(fields) == 3 and fields[:2] == [oid, "blob"], "source_blob_identity")
        size = int(fields[2])
        require(0 <= size <= 64 * 1024 * 1024, "source_blob_bound")
        total += size
    require(total <= 256 * 1024 * 1024, "source_tree_bound")
    batch = git(root, ["cat-file", "--batch"], query)
    offset = 0
    inventory, contents = [], {}
    for path, mode, oid in entries:
        end = batch.find(b"\n", offset)
        require(end >= 0, "truncated_source_batch")
        fields = batch[offset:end].decode().split()
        require(len(fields) == 3 and fields[:2] == [oid, "blob"], "source_batch_identity")
        size = int(fields[2])
        raw = batch[end + 1:end + 1 + size]
        require(len(raw) == size and batch[end + 1 + size:end + 2 + size] == b"\n",
                "truncated_source_blob")
        require(hashlib.sha1(b"blob " + str(size).encode() + b"\0" + raw).hexdigest() == oid,
                "source_blob_hash")
        offset = end + 2 + size
        contents[path] = raw
        inventory.append({"path": path, "mode": mode, "git_blob_sha1": oid,
                          "bytes": size, "sha256": digest(raw)})
    require(offset == len(batch), "source_batch_trailing_bytes")
    return tree, inventory, contents


class UniqueLoader(yaml.SafeLoader):
    pass


def _yaml_map(loader: UniqueLoader, node: Any, deep: bool = False) -> dict:
    out = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        require(key not in out, "duplicate_yaml_key")
        out[key] = loader.construct_object(value_node, deep=deep)
    return out


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _yaml_map)


def source_yaml(raw: bytes) -> dict[str, Any]:
    try:
        value = yaml.load(raw, Loader=UniqueLoader)
    except yaml.YAMLError as exc:
        raise VerificationError("invalid_source_yaml") from exc
    require(isinstance(value, dict), "source_yaml_object_required")
    return value


class Expression:
    """Closed interpreter for the expressions actually present in the pinned workflow.

    No eval(), no calls into builder/producer code, and no permissive fallback.
    """
    token = re.compile(r"\s*(\&\&|\|\||==|!=|[!(),]|'(?:''|[^'])*'|[A-Za-z_][A-Za-z0-9_.-]*)")

    def __init__(self, text: str, context: dict[str, Any], successful: bool):
        text = text.strip()
        if text.startswith("${{") and text.endswith("}}"):
            text = text[3:-2].strip()
        self.tokens = []
        offset = 0
        while offset < len(text):
            found = self.token.match(text, offset)
            require(found is not None, "unsupported_workflow_expression")
            self.tokens.append(found.group(1))
            offset = found.end()
        self.i, self.context, self.successful = 0, context, successful
        self.has_status = any(t in ("always", "success", "failure", "cancelled")
                              for t in self.tokens)

    def take(self, token: str | None = None) -> str:
        require(self.i < len(self.tokens), "truncated_workflow_expression")
        result = self.tokens[self.i]
        require(token is None or token == result, "invalid_workflow_expression")
        self.i += 1
        return result

    def peek(self, value: str) -> bool:
        return self.i < len(self.tokens) and self.tokens[self.i] == value

    def primary(self) -> Any:
        if self.peek("!"):
            self.take()
            return not bool(self.primary())
        if self.peek("("):
            self.take()
            value = self.disjunction()
            self.take(")")
            return value
        name = self.take()
        if name.startswith("'"):
            return name[1:-1].replace("''", "'")
        if self.peek("("):
            self.take()
            args = []
            if not self.peek(")"):
                args.append(self.disjunction())
                while self.peek(","):
                    self.take()
                    args.append(self.disjunction())
            self.take(")")
            if name in ("always", "cancelled", "success", "failure"):
                require(not args, "status_function_arguments")
                return {"always": True, "cancelled": False,
                        "success": self.successful, "failure": not self.successful}[name]
            require(name == "startsWith" and len(args) == 2 and
                    all(isinstance(x, str) for x in args), "unsupported_expression_function")
            return args[0].startswith(args[1])
        if name in ("true", "false"):
            return name == "true"
        require(name in self.context, "unresolved_expression_context:" + name)
        return self.context[name]

    def comparison(self) -> Any:
        left = self.primary()
        if self.peek("==") or self.peek("!="):
            op, right = self.take(), self.primary()
            return left == right if op == "==" else left != right
        return left

    def conjunction(self) -> Any:
        value = self.comparison()
        while self.peek("&&"):
            self.take()
            right = self.comparison()
            value = bool(value) and bool(right)
        return value

    def disjunction(self) -> Any:
        value = self.conjunction()
        while self.peek("||"):
            self.take()
            right = self.conjunction()
            value = bool(value) or bool(right)
        return value

    def enabled(self) -> bool:
        value = self.disjunction()
        require(self.i == len(self.tokens), "trailing_workflow_expression")
        return bool(value) and (self.has_status or self.successful)


def condition(text: str | None, context: dict[str, Any], successful: bool) -> bool:
    return successful if text is None else Expression(text, context, successful).enabled()


def interpret_graph(workflow_raw: bytes) -> list[dict[str, Any]]:
    """Apply pinned conditions, needs, status gating, and two designated rejections."""
    require(digest(workflow_raw) == WORKFLOW_SHA, "workflow_not_reviewed")
    workflow = source_yaml(workflow_raw)
    jobs = workflow["jobs"]
    require(len(jobs) == 8 and sum(len(j["steps"]) for j in jobs.values()) == 147,
            "workflow_template_count")
    context: dict[str, Any] = {"github.event_name": "workflow_dispatch",
        "github.ref": "refs/heads/main", "github.event.inputs.strict_external_evidence": "true",
        "github.event.inputs.llamaguard_evidence_mode": "hosted_full_runtime",
        "needs.pulse.outputs.llamaguard_evidence_ready": "",
        "env.REFERENCE_RUN_QUALIFIED": "", "env.REFERENCE_LEDGER_PARITY_OK": "",
        "env.REFERENCE_BUNDLE_DIR": ""}
    graph, results = [], {}
    for job_id, job in jobs.items():
        needs = job.get("needs", [])
        needs = [needs] if isinstance(needs, str) else needs
        require(all(n in results for n in needs), "unresolved_workflow_dependency")
        context.update({"needs." + n + ".result": r for n, r in results.items()})
        ctx = dict(context)
        ctx.update({"steps.release_mode.outputs.is_release": "",
                    "steps.release_mode.outputs.llamaguard_evidence_mode": ""})
        for step in job["steps"]:
            if step.get("id"):
                ctx["steps." + step["id"] + ".outcome"] = "skipped"
        active = condition(job.get("if"), ctx, all(results[n] == "success" for n in needs))
        successful, steps = True, []
        for ordinal, step in enumerate(job["steps"], 1):
            name = step.get("name", step.get("uses", "")).strip()
            if not active:
                outcome = "not_instantiated"
            elif not condition(step.get("if"), ctx, successful):
                outcome = "skipped"
            else:
                outcome = "failure" if (job_id, name) in NEGATIVE_STEPS else "success"
                successful = successful and outcome == "success"
            if step.get("id"):
                ctx["steps." + step["id"] + ".outcome"] = outcome
            if job_id == "pulse" and step.get("id") == "release_mode" and outcome == "success":
                ctx["steps.release_mode.outputs.is_release"] = "1"
                ctx["steps.release_mode.outputs.llamaguard_evidence_mode"] = "hosted_full_runtime"
            if job_id == "pulse" and step.get("id") == "llamaguard_evidence_upload":
                context["needs.pulse.outputs.llamaguard_evidence_ready"] = str(outcome == "success").lower()
            command = step.get("run")
            steps.append({"ordinal": ordinal, "id": step.get("id"), "name": name,
                          "if": step.get("if"), "uses": step.get("uses"),
                          "run_sha256": digest(command.encode()) if command is not None else None,
                          "expected_result": outcome})
        result = "skipped" if not active else "success" if successful else "failure"
        results[job_id] = result
        graph.append({"id": job_id, "name": job.get("name", job_id).strip(), "needs": needs,
                      "if": job.get("if"), "expected_conclusion": result, "steps": steps})
    require(list(results.values()).count("failure") == 2 and
            list(results.values()).count("success") == 2 and
            list(results.values()).count("skipped") == 4, "negative_topology_changed")
    return graph


def validate_schema(value: Any, raw_schema: bytes, code: str) -> None:
    schema = object_json(raw_schema)
    # All permitted references are document-local; never retrieve schemas from a carrier.
    def refs(node: Any) -> None:
        if isinstance(node, dict):
            if "$ref" in node:
                require(node["$ref"].startswith("#"), "external_schema_reference")
            for child in node.values():
                refs(child)
        elif isinstance(node, list):
            for child in node:
                refs(child)
    refs(schema)
    try:
        jsonschema.Draft202012Validator(schema).validate(value)
    except jsonschema.ValidationError as exc:
        raise VerificationError(code) from exc


def validate_plan(plan: dict, sources: dict[str, bytes], tree: str, inventory: list[dict],
                  expected_source: str, request: bytes) -> list[dict]:
    require(set(plan) == {"format", "profile_id", "authority_effect", "source", "request",
                          "inputs", "dispatch", "expected_graph", "limits", "excluded_claims"},
            "plan_keys")
    require(plan["format"] == "pulsemech_compute_admission_rejection_plan_v0" and
            plan["profile_id"] == PROFILE and plan["authority_effect"] == "none", "plan_identity")
    require(plan["source"] == {"repository": REPOSITORY, "commit": expected_source, "tree": tree,
                               "workflow_path": WORKFLOW, "workflow_sha256": WORKFLOW_SHA,
                               "policy_sha256": POLICY_SHA, "files": inventory}, "source_closure_mismatch")
    require(digest(sources[POLICY]) == POLICY_SHA, "policy_not_reviewed")
    require(plan["dispatch"] == DISPATCH and plan["limits"] == LIMITS and
            plan["excluded_claims"] == EXCLUDED, "profile_boundary_changed")
    require(plan["inputs"] == SELECTED_INPUTS, "original_input_selection_changed")
    require(plan["request"] == {"path": "input/q2_request.json", "bytes": len(request),
                                "sha256": digest(request)}, "request_binding")
    doc = object_json(request)
    validate_schema(doc, sources["schemas/q2_release_intake_request_v0.schema.json"], "request_schema")
    require(doc["evaluation_identity"]["source_commit"] == expected_source, "request_source")
    frozen = object_json(sources["PULSE_safe_pack_v0/profiles/q2_reference_release_intake_v0.json"])
    require(doc["selection"] == frozen["selection"] and
            doc["capture_expectation"] == frozen["capture_expectation"], "request_selection")
    for name, binding in (("capture", doc["capture_expectation"]), ("capsule", doc["release_subject"])):
        require(SELECTED_INPUTS[name]["bytes"] == binding["archive_size_bytes"] and
                SELECTED_INPUTS[name]["sha256"] == binding["archive_sha256"], "request_input_identity")
    require(digest(sources[doc["selection"]["path"]]) == doc["selection"]["sha256"] and
            doc["release_subject"]["capsule_manifest_sha256"] == SELECTED_INPUTS["capsule"]["manifest_sha256"],
            "request_selected_source_digest")
    graph = interpret_graph(sources[WORKFLOW])
    require(plan["expected_graph"] == graph, "producer_graph_disagrees_with_independent_interpretation")
    return graph


def acquisition_files(directory: Path, plan_raw: bytes, source: str, run_id: int,
                      attempt: int) -> tuple[dict, dict[str, bytes], dict[str, dict]]:
    index = object_json(read(directory / "acquisition.json", LIMITS["max_json_bytes"]))
    require(set(index) == {"format", "profile_id", "authority_effect", "plan_sha256", "repository",
                           "run_id", "run_attempt", "source_commit", "completed", "errors", "files"},
            "acquisition_keys")
    require(index["format"] == "pulsemech_compute_admission_rejection_acquisition_v0" and
            index["profile_id"] == PROFILE and index["authority_effect"] == "none" and
            index["plan_sha256"] == digest(plan_raw), "acquisition_profile_or_plan")
    require(index["repository"] == REPOSITORY and index["source_commit"] == source and
            type(index["run_id"]) is int and index["run_id"] == run_id and
            type(index["run_attempt"]) is int and index["run_attempt"] == attempt,
            "acquisition_caller_identity")
    require(index["completed"] is True and index["errors"] == [], "acquisition_incomplete")
    require(isinstance(index["files"], list) and 0 < len(index["files"]) <= 200, "acquisition_file_count")
    contents, entries, total = {}, {}, 0
    bounds = {"run": "max_json_bytes", "jobs": "max_json_bytes", "artifacts": "max_json_bytes",
              "log": "max_log_bytes", "archive": "max_artifact_bytes"}
    for entry in index["files"]:
        require(set(entry) == {"path", "bytes", "sha256", "kind", "endpoint"}, "acquisition_entry_keys")
        name = safe_path(entry["path"])
        require(name not in contents and entry["kind"] in bounds and type(entry["bytes"]) is int,
                "duplicate_or_invalid_acquisition_entry")
        raw = read(directory / name, LIMITS[bounds[entry["kind"]]])
        require(entry["bytes"] == len(raw) and entry["sha256"] == digest(raw), "acquisition_content_digest")
        total += len(raw)
        require(total <= LIMITS["max_total_bytes"], "acquisition_total_bound")
        contents[name], entries[name] = raw, entry
    actual = set()
    for path in directory.rglob("*"):
        require(not path.is_symlink(), "evidence_symlink")
        if path.is_file():
            actual.add(path.relative_to(directory).as_posix())
        else:
            require(path.is_dir(), "evidence_special_file")
    require(actual == set(contents) | {"acquisition.json"}, "unlisted_or_missing_evidence_file")
    return index, contents, entries


def require_entry(entries: dict, path: str, kind: str, endpoint: str) -> None:
    require(path in entries and entries[path]["kind"] == kind and entries[path]["endpoint"] == endpoint,
            "raw_endpoint_binding:" + path)


def pages(contents: dict[str, bytes], entries: dict, plural: str, base: str,
          after: bool = False) -> list[dict]:
    prefix = "api/" + plural + ("-after-" if after else "-")
    names = sorted(n for n in contents if re.fullmatch(re.escape(prefix) + r"[0-9]{3}\.json", n))
    require(0 < len(names) <= LIMITS["max_pages"], "pagination_missing_or_excessive:" + plural)
    result, total = [], None
    for number, name in enumerate(names, 1):
        require(name == f"{prefix}{number:03d}.json", "pagination_noncontiguous:" + plural)
        require_entry(entries, name, plural, base + f"?per_page=100&page={number}")
        doc = object_json(contents[name])
        require(type(doc.get("total_count")) is int and doc["total_count"] >= 0 and
                isinstance(doc.get(plural), list), "pagination_shape:" + plural)
        if total is None:
            total = doc["total_count"]
        require(doc["total_count"] == total and total <= LIMITS["max_" + plural] and
                len(doc[plural]) <= 100, "pagination_total:" + plural)
        result.extend(doc[plural])
    require(len(names) == max(1, (total + 99) // 100) and len(result) == total,
            "pagination_incomplete:" + plural)
    require(all(isinstance(item, dict) and type(item.get("id")) is int and item["id"] > 0 for item in result)
            and len({item["id"] for item in result}) == len(result), "pagination_duplicate_identity:" + plural)
    return result


def instant(text: str) -> dt.datetime:
    require(isinstance(text, str), "missing_timestamp")
    try:
        value = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise VerificationError("invalid_timestamp") from exc
    require(value.tzinfo is not None, "timestamp_timezone_missing")
    return value


def validate_runs(contents: dict, entries: dict, source: str, run_id: int, attempt: int) -> dict:
    endpoint = f"repos/{REPOSITORY}/actions/runs/{run_id}"
    docs = []
    for name in ("api/run.json", "api/run_after.json"):
        require_entry(entries, name, "run", endpoint)
        doc = object_json(contents[name])
        require(all(isinstance(doc.get(key), dict) for key in ("repository", "head_repository", "actor", "triggering_actor")),
                "run_repository_or_actor_shape")
        require(doc.get("id") == run_id and type(doc.get("id")) is int and
                type(doc.get("run_attempt")) is int and doc.get("run_attempt") == attempt and doc.get("head_sha") == source and
                doc.get("repository", {}).get("full_name") == REPOSITORY and
                doc.get("head_repository", {}).get("full_name") == REPOSITORY and
                doc["actor"].get("login") == "HKati" and doc["triggering_actor"].get("login") == "HKati" and
                doc.get("event") == "workflow_dispatch" and doc.get("head_branch") == "main" and
                doc.get("path") == WORKFLOW and doc.get("name") == "PULSE CI" and
                doc.get("status") == "completed" and doc.get("conclusion") == "failure", "run_identity_or_state")
        require(instant(doc["created_at"]) <= instant(doc["run_started_at"]) <= instant(doc["updated_at"]),
                "run_time_order")
        docs.append(doc)
    fields = ("id", "run_attempt", "head_sha", "event", "head_branch", "path", "name", "status",
              "conclusion", "workflow_id", "check_suite_id", "created_at", "run_started_at", "updated_at",
              "actor", "triggering_actor")
    require(all(docs[0].get(key) == docs[1].get(key) for key in fields), "run_changed_during_acquisition")
    return docs[0]


def validate_jobs(jobs: list[dict], graph: list[dict], run: dict) -> list[dict]:
    require(len(jobs) == len(graph) and len({j.get("name") for j in jobs}) == len(jobs), "job_set_count_or_duplicate")
    by_name = {j.get("name"): j for j in jobs}
    require(set(by_name) == {j["name"] for j in graph}, "job_set_mismatch")
    observed = []
    for expected in graph:
        job = by_name[expected["name"]]
        require(type(job.get("run_id")) is int and type(job.get("run_attempt")) is int and
                job.get("run_id") == run["id"] and job.get("run_attempt") == run["run_attempt"] and
                job.get("head_sha") == run["head_sha"] and job.get("status") == "completed" and
                job.get("conclusion") == expected["expected_conclusion"], "job_identity_or_outcome:" + expected["id"])
        actual = job.get("steps") or []
        require(isinstance(actual, list), "job_steps_shape")
        if expected["expected_conclusion"] == "skipped":
            require(not actual, "skipped_job_executed")
            observed.append({"id": expected["id"], "platform_job_id": job["id"],
                             "conclusion": "skipped", "source_steps": expected["steps"], "platform_steps": []})
            continue
        require(instant(run["run_started_at"]) <= instant(job["started_at"]) <=
                instant(job["completed_at"]) <= instant(run["updated_at"]), "job_time_order")
        numbers = [s.get("number") for s in actual]
        require(all(type(n) is int and n > 0 for n in numbers) and numbers == sorted(set(numbers)),
                "platform_step_numbering")
        source_index, lifecycle, bound = 0, [], []
        post_names = {"Post " + s["name"] for s in expected["steps"]
                      if s["uses"] and s["expected_result"] == "success"}
        seen_lifecycle = set()
        for step in actual:
            name = step.get("name", "").strip()
            require(step.get("status") == "completed", "platform_step_incomplete")
            if source_index < len(expected["steps"]) and name == expected["steps"][source_index]["name"]:
                target = expected["steps"][source_index]
                require(step.get("conclusion") == target["expected_result"],
                        "source_step_outcome:" + expected["id"] + ":" + str(target["ordinal"]))
                bound.append({**target, "platform_number": step["number"], "conclusion": step["conclusion"]})
                source_index += 1
            else:
                permitted = (name == "Set up job" and source_index == 0 or
                             name in post_names and source_index == len(expected["steps"]) or
                             name == "Complete job" and source_index == len(expected["steps"]))
                require(permitted and name not in seen_lifecycle and
                        step.get("conclusion") in ("success", "skipped"), "unexpected_platform_step:" + str(name))
                seen_lifecycle.add(name)
                lifecycle.append({"name": name, "platform_number": step["number"], "conclusion": step["conclusion"]})
        require(source_index == len(expected["steps"]) and "Set up job" in seen_lifecycle and
                "Complete job" in seen_lifecycle, "source_steps_or_lifecycle_missing")
        observed.append({"id": expected["id"], "platform_job_id": job["id"],
                         "conclusion": job["conclusion"], "source_steps": bound, "platform_steps": lifecycle})
    return observed


ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
TIME_PREFIX = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z ")


def shell_record(raw: bytes, script: str) -> tuple[list[str], list[str]]:
    """Locate the echoed exact source script, then inspect only its actual output.

    A marker copied inside the source/echo group cannot satisfy an observation.
    """
    try:
        lines = [TIME_PREFIX.sub("", ANSI.sub("", line)) for line in raw.decode("utf-8").splitlines()]
    except UnicodeError as exc:
        raise VerificationError("log_not_utf8") from exc
    wanted = [s.strip() for s in script.splitlines() if s.strip()]
    candidates = []
    for start, line in enumerate(lines):
        if not line.startswith("##[group]Run "):
            continue
        end = start + 1
        while end < len(lines) and lines[end] != "##[endgroup]":
            require(not lines[end].startswith("##[group]"), "nested_shell_echo_group")
            end += 1
        require(end < len(lines), "unterminated_shell_echo_group")
        echoed = [line.removeprefix("##[group]Run ").strip()]
        echoed += [s.strip() for s in lines[start + 1:end] if s.strip()]
        # GitHub's heading repeats the first command before the entire script.
        consumed = len(wanted) if echoed[:len(wanted)] == wanted else len(wanted) + 1
        if echoed[:len(wanted)] != wanted and echoed[1:1 + len(wanted)] != wanted:
            continue
        stop = end + 1
        while stop < len(lines) and not lines[stop].startswith("##[group]"):
            stop += 1
        candidates.append((echoed[consumed:], lines[end + 1:stop]))
    require(len(candidates) == 1, "critical_shell_group_missing_or_ambiguous")
    return candidates[0]


def actual_shell_output(raw: bytes, script: str) -> list[str]:
    return shell_record(raw, script)[1]


def shell_environment(raw: bytes, script: str, key: str) -> str:
    metadata, _ = shell_record(raw, script)
    require("env:" in metadata, "original_step_environment_missing")
    environment = metadata[metadata.index("env:") + 1:]
    values = [line.split(": ", 1)[1] for line in environment if line.startswith(key + ": ")]
    require(len(values) == 1, "original_step_environment_key_missing_or_duplicate:" + key)
    return values[0]


def original_mode_output(raw: bytes, script: str) -> str:
    # The one GitHub expression in this pinned script expands PACK_DIR. Obtain
    # its literal value from the runner's group metadata, never an executable.
    lines = [TIME_PREFIX.sub("", ANSI.sub("", line)) for line in raw.decode("utf-8").splitlines()]
    values = {line.strip().split(": ", 1)[1] for line in lines if line.strip().startswith("PACK_DIR: ")}
    require(len(values) == 1, "pack_directory_log_binding")
    pack_dir = next(iter(values))
    require(re.fullmatch(r"/[A-Za-z0-9_./-]+/PULSE_safe_pack_v0", pack_dir) is not None and
            ".." not in PurePosixPath(pack_dir).parts, "pack_directory_log_path")
    resolved = script.replace("${{ env.PACK_DIR }}", pack_dir)
    require(resolved != script, "mode_source_interpolation_changed")
    require(shell_environment(raw, resolved, "PACK_DIR") == pack_dir, "mode_pack_directory_binding")
    output = actual_shell_output(raw, resolved)
    marker = "Computed flags: IS_RELEASE=1 MODE=prod POLICY_SET=required LLAMAGUARD_EVIDENCE_MODE=hosted_full_runtime"
    require(output.count(marker) == 1, "original_mode_output_missing")
    return digest(("\n".join(output) + "\n").encode())


def rejection_logs(contents: dict, entries: dict, jobs: list[dict], workflow_raw: bytes,
                   request_sha256: str) -> dict:
    workflow = source_yaml(workflow_raw)
    by_name = {j["name"]: j for j in jobs}
    reports = {}
    for jid, source_job in workflow["jobs"].items():
        job = by_name[source_job.get("name", jid).strip()]
        if job["conclusion"] == "skipped":
            continue
        path = f"logs/{job['id']}.txt"
        require_entry(entries, path, "log", f"repos/{REPOSITORY}/actions/jobs/{job['id']}/logs")
        require(bool(contents[path]), "empty_job_log")
        for step in source_job["steps"]:
            if (jid, step["name"].strip()) not in NEGATIVE_STEPS:
                continue
            output = actual_shell_output(contents[path], step["run"])
            require(output.count("##[error]Process completed with exit code 1.") == 1,
                    "rejection_exit_not_observed")
            if jid == "pulse":
                require(shell_environment(contents[path], step["run"], "PULSE_Q2_INTAKE_REQUEST_SHA256") == request_sha256,
                        "original_request_hash_environment_mismatch")
                original_mode_output(contents[path], source_job["steps"][7]["run"])
                require(output.count("Q2 independent negative verification exit: 0") == 1 and
                        output.count("passed gates: 6") == 1 and output.count("failed gates: 13") == 1,
                        "independent_q2_rejection_output_missing")
                require(not any("Q2 historical negative intake cannot yield a successful required gate" in s
                                for s in output), "contradictory_q2_gate_success")
            else:
                marker = "##[error]BLOCK: pre-attestation candidate was not accepted; hosted evidence remains preserved."
                require(output.count(marker) == 1, "candidate_guard_output_missing")
            reports[jid] = {"source_script_sha256": digest(step["run"].encode()),
                            "job_log_sha256": digest(contents[path]),
                            "actual_output_sha256": digest(("\n".join(output) + "\n").encode()),
                            "exit_code": 1, "echo_group_excluded": True}
    require(set(reports) == {"pulse", "release_grade_recorded_path"}, "rejection_chain_incomplete")
    return reports


def zip_members(raw: bytes) -> dict[str, bytes]:
    """Read bounded regular ZIP members without extraction or path interpretation."""
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            require(0 < len(archive.infolist()) <= 5000, "archive_member_count")
            out, seen, total = {}, set(), 0
            for info in archive.infolist():
                name = safe_path(info.filename[:-1] if info.is_dir() else info.filename)
                require(name not in seen, "duplicate_archive_member")
                seen.add(name)
                mode = info.external_attr >> 16
                require(not info.flag_bits & 1 and not stat.S_ISLNK(mode), "encrypted_or_link_archive_member")
                require(stat.S_IFMT(mode) in (0, stat.S_IFREG, stat.S_IFDIR), "special_archive_member")
                if info.is_dir():
                    require(info.file_size == 0, "nonempty_archive_directory")
                    continue
                require(stat.S_IFMT(mode) != stat.S_IFDIR and info.file_size <= LIMITS["max_artifact_bytes"],
                        "archive_member_type_or_bound")
                total += info.file_size
                require(total <= LIMITS["max_total_bytes"], "archive_expansion_bound")
                with archive.open(info) as stream:
                    data = stream.read(info.file_size + 1)
                require(len(data) == info.file_size, "archive_member_size")
                out[name] = data
            return out
    except (zipfile.BadZipFile, RuntimeError, OSError, NotImplementedError) as exc:
        raise VerificationError("invalid_archive") from exc


def normalized_members(members: dict[str, bytes], exact: set[str] | None = None) -> dict[str, bytes]:
    prefixes = ("", "external/", ARTIFACT_ROOT + "external/") if exact else ("", "artifacts/", ARTIFACT_ROOT)
    matches = []
    for prefix in prefixes:
        if not all(name.startswith(prefix) for name in members):
            continue
        relative = {name[len(prefix):]: raw for name, raw in members.items()}
        good = set(relative) == exact if exact is not None else bool(relative) and all(
            n == "required_gate_evidence_v0.json" or n.startswith("required_gate_inputs/") or
            n.startswith("required_gate_evidence_logs/") for n in relative)
        if good:
            matches.append(relative)
    require(len(matches) == 1, "archive_layout_missing_extra_or_ambiguous")
    return matches[0]


def validate_archives(artifacts: list[dict], contents: dict, entries: dict, run: dict) -> tuple[dict, dict, dict, list[dict]]:
    suffix = f"-{run['id']}-{run['run_attempt']}"
    expected = {"llamaguard-current-run" + suffix: "hosted",
                "release-grade-required-gate-diagnostics" + suffix: "diagnostics",
                "llamaguard-attested-current-run" + suffix: "attested"}
    require(len(artifacts) == 3 and {a.get("name") for a in artifacts} == set(expected), "unexpected_artifact_set")
    result, refs, expanded_total = {}, [], 0
    for artifact in artifacts:
        require(artifact.get("expired") is False and type(artifact.get("size_in_bytes")) is int and
                artifact["size_in_bytes"] > 0, "artifact_expired_or_invalid")
        binding = artifact.get("workflow_run")
        require(isinstance(binding, dict) and type(binding.get("id")) is int and binding.get("id") == run["id"] and
                binding.get("head_sha") == run["head_sha"] and binding.get("head_branch") == "main",
                "artifact_run_binding")
        require(instant(run["run_started_at"]) <= instant(artifact["created_at"]) <=
                instant(artifact["updated_at"]) <= instant(run["updated_at"]), "artifact_time_order")
        path = f"archives/{artifact['id']}.zip"
        require_entry(entries, path, "archive", f"repos/{REPOSITORY}/actions/artifacts/{artifact['id']}/zip")
        raw = contents[path]
        require(len(raw) == artifact["size_in_bytes"] and artifact.get("digest") == "sha256:" + digest(raw),
                "artifact_api_digest_or_size")
        kind = expected[artifact["name"]]
        exact = HOSTED_NAMES if kind == "hosted" else ATTESTED_NAMES if kind == "attested" else None
        result[kind] = normalized_members(zip_members(raw), exact)
        expanded_total += sum(len(data) for data in result[kind].values())
        require(expanded_total <= LIMITS["max_total_bytes"], "all_archives_expansion_bound")
        refs.append({"id": artifact["id"], "name": artifact["name"], "bytes": len(raw), "sha256": digest(raw),
                     "members": [{"path": name, "bytes": len(data), "sha256": digest(data)}
                                 for name, data in sorted(result[kind].items())]})
    require(all(result["hosted"][n] == result["attested"][n] for n in HOSTED_NAMES), "hosted_attested_copy_disagrees")
    return result["hosted"], result["attested"], result["diagnostics"], sorted(refs, key=lambda x: x["name"])


def literal_assignment(raw: bytes, name: str) -> Any:
    for node in ast.parse(raw).body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            return ast.literal_eval(node.value)
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise VerificationError("source_literal_not_found:" + name)


def check_required_gates(diag: dict[str, bytes], sources: dict[str, bytes], run: dict) -> dict:
    policy = source_yaml(sources[POLICY])
    gates = policy["gates"]["required"]
    require(len(gates) == len(set(gates)) == 19 and policy["enforcement"]["required_missing"] == "FAIL" and
            policy["enforcement"]["required_false"] == "FAIL", "required_policy_changed")
    plan = object_json(sources[GATE_PLAN])
    require(set(plan["evaluations"]) == set(gates), "required_plan_gate_set")
    document = object_json(diag["required_gate_evidence_v0.json"])
    validate_schema(document, sources["schemas/required_gate_evidence_v0.schema.json"], "required_evidence_schema")
    require(set(document["gates"]) == set(gates), "observed_required_gate_set")
    identity = {"git_sha": run["head_sha"],
                "run_key": f"GITHUB_RUN_ID={run['id']}|GITHUB_RUN_ATTEMPT={run['run_attempt']}|GITHUB_WORKFLOW=PULSE CI",
                "run_mode": "prod"}
    subject = {"repository": REPOSITORY, "commit_sha": run["head_sha"], "release_candidate": "main"}
    policy_binding = {"policy_path": POLICY, "policy_sha256": POLICY_SHA, "policy_set": "required"}
    registry_binding = {"registry_path": REGISTRY, "registry_sha256": digest(sources[REGISTRY])}

    def common(doc: dict) -> None:
        require(doc["run_identity"] == identity and doc["subject"] == subject and
                doc["policy_binding"] == policy_binding and doc["registry_binding"] == registry_binding,
                "gate_record_identity")
        require(instant(run["run_started_at"]) <= instant(doc["created_utc"]) <= instant(run["updated_at"]),
                "gate_record_time")
        require(all(v is False for v in doc["authority_boundary"].values()), "gate_authority_claim")

    common(document)
    require(document["warnings"] == [], "recorder_unexpected_warning")
    require(document["producer"] == {"id": "pulse_recorded_required_gate_evaluator_v0", "version": "0.1.0",
             "trusted": True, "tool_path": RECORDER, "tool_sha256": digest(sources[RECORDER])}, "recorder_source_binding")
    unsupported = literal_assignment(sources[GATE_TOOL], "UNSUPPORTED_REASONS")
    require(isinstance(unsupported, dict) and len(unsupported) == 12, "unsupported_source_mapping")
    evidence = {**sources, **{ARTIFACT_ROOT + n: raw for n, raw in diag.items()}}
    unavailable = set()

    def references(refs: list[dict], strict: bool) -> None:
        paths = [safe_path(r["path"]) for r in refs]
        require(len(paths) == len(set(paths)), "duplicate_evidence_reference")
        for ref in refs:
            raw = evidence.get(ref["path"])
            if raw is None:
                require(not strict and ref["path"].startswith(ARTIFACT_ROOT + "required_gate_evaluator_work/"),
                        "required_evidence_reference_missing:" + ref["path"])
                unavailable.add(ref["path"])
            else:
                require(digest(raw) == ref["sha256"], "gate_evidence_reference_digest")

    recorded = []
    for gate in gates:
        entry = plan["evaluations"][gate]
        group = document["gates"][gate]
        result_path = entry["result"]["artifact"]
        require(entry["result"]["json_pointer"] == "/pass" and result_path.startswith(ARTIFACT_ROOT),
                "gate_result_path")
        result = object_json(diag[result_path[len(ARTIFACT_ROOT):]])
        validate_schema(result, sources["schemas/required_gate_evaluation_result_v0.schema.json"], "gate_result_schema")
        common(result)
        require(result["gate_id"] == gate and result["evaluation_id"] == entry["evaluation_id"] ==
                group["evaluation_id"] and result["status"] == group["status"] and
                result["pass"] is group["value"], "gate_result_relation")
        require(result["plan_binding"] == {"plan_path": GATE_PLAN, "plan_sha256": digest(sources[GATE_PLAN]),
                "plan_schema_version": "required_gate_evaluation_plan_v0"} and
                result["evaluator"] == {"id": "pulse_required_gate_dispatcher_v0", "version": "0.1.0",
                "tool_path": GATE_TOOL, "tool_sha256": digest(sources[GATE_TOOL])}, "gate_evaluator_binding")
        references(group["evidence_artifacts"], True)
        references(result["input_artifacts"], False)
        expected_refs = [
            {"path": GATE_PLAN, "sha256": digest(sources[GATE_PLAN]), "kind": "evaluation_plan",
             "schema_version": "required_gate_evaluation_plan_v0"},
            {"path": GATE_TOOL, "sha256": digest(sources[GATE_TOOL]), "kind": "evaluation_tool", "schema_version": None},
        ]
        for stream in ("stdout", "stderr"):
            log_name = f"required_gate_evidence_logs/{gate}.{stream}.txt"
            require(log_name in diag, "required_gate_stream_missing")
            expected_refs.append({"path": ARTIFACT_ROOT + log_name, "sha256": digest(diag[log_name]),
                                  "kind": "evaluation_" + stream, "schema_version": None})
        expected_refs.append({"path": result_path, "sha256": digest(diag[result_path[len(ARTIFACT_ROOT):]]),
                              "kind": "required_gate_evaluation", "schema_version": "required_gate_evaluation_result_v0"})
        require(group["evidence_artifacts"] == expected_refs, "required_gate_reference_set")
        input_paths = {ref["path"] for ref in result["input_artifacts"]}
        require({POLICY, REGISTRY, GATE_PLAN, GATE_TOOL, "schemas/required_gate_evaluation_result_v0.schema.json"}
                <= input_paths, "gate_input_source_refs_missing")
        require(any(r["path"] == result_path and r["sha256"] == digest(diag[result_path[len(ARTIFACT_ROOT):]])
                    for r in group["evidence_artifacts"]), "gate_result_reference_missing")
        if gate in unsupported:
            require(result["pass"] is False and result["diagnostics"] == [unsupported[gate]] and
                    result["warnings"] == [] and len(result["checks"]) == 1, "unsupported_gate_reason_changed")
            check = result["checks"][0]
            require(check["kind"] == "contract" and check["passed"] is False and check["exit_code"] is None and
                    check["command"] == ["internal", "require-dedicated-current-run-evaluator", gate] and
                    check["diagnostics"] == [unsupported[gate]], "unsupported_gate_not_contract_failure")
        elif gate == "q2_consistency_ok":
            require(result["pass"] is False and result["warnings"] == [] and len(result["checks"]) == 2 and
                    result["checks"][0]["passed"] is True and result["checks"][0]["exit_code"] == 0 and
                    result["checks"][1]["passed"] is False and result["checks"][1]["exit_code"] == 1,
                    "q2_not_valid_negative")
            public_name = "required_gate_inputs/q2_intake_result_v0.json"
            require(ARTIFACT_ROOT + public_name in input_paths, "q2_intake_record_reference_missing")
            public = object_json(diag[public_name])
            require(result["diagnostics"] == public.get("diagnostics") and
                    result["checks"][0]["check_id"] == "pulse.required.q2_consistency_ok.intake.v0" and
                    result["checks"][0]["command"] == ["internal", "q2-archived-intake-v0"] and
                    result["checks"][1]["check_id"] == "pulse.required.q2_consistency_ok.metric.v0" and
                    result["checks"][1]["command"] == ["internal", "q2-unchanged-reducer-and-checker"],
                    "q2_intake_dispatcher_relation")
        else:
            require(result["pass"] is True and result["diagnostics"] == [] and
                    result["warnings"] == ["This current-run evaluator reduces checked-in archived reference evidence; "
                                           "it proves deterministic reference mechanics, not live production-model behavior."] and
                    all(c["passed"] is True and c["exit_code"] == 0 and c["diagnostics"] == [] for c in result["checks"]),
                    "unexpected_additional_gate_failure")
        expected_diagnostics = [] if result["pass"] else ["evaluation command exited with code 1",
                                                         "result JSON pointer '/pass' must be literal true"]
        require(group["diagnostics"] == expected_diagnostics, "gate_recorder_infrastructure_or_other_failure")
        recorded.append({"gate_id": gate, "value": result["pass"],
                         "verification": "source_contract_failure" if gate in unsupported else
                         "independent_q2_replay_required" if gate == "q2_consistency_ok" else
                         "recorded_success_only", "result_sha256": digest(diag[result_path[len(ARTIFACT_ROOT):]])})
    require(sum(item["value"] for item in recorded) == 6, "required_gate_totals")
    return {"count": 19, "passed": 6, "failed": 13, "policy_sha256": POLICY_SHA,
            "records": recorded, "unpreserved_recipe_intermediates": sorted(unavailable),
            "generic_six_metrics_independently_replayed": False}


def legacy_roles(sources: dict, retained: dict) -> dict:
    schema = object_json(sources["schemas/pulsemech_compute_whole_runtime_observation_evidence_v0.schema.json"])
    definitions = schema["$defs"]["post_run_state_evidence_v1_role_obligations"]["properties"]
    require(len(definitions) == 62, "legacy_role_set_changed")
    source_roles = {"gate-policy", "gate-registry", "workflow-source", "external-signer-policy",
                    "threshold-policy", "llamaguard-dataset"}
    content_roles = {"required-gate-evidence", "llamaguard-raw-evidence", "llamaguard-evaluator-manifest",
                     "llamaguard-summary", "llamaguard-attestation-bundle", "llamaguard-attestation-envelope",
                     "llamaguard-attestation-verifier"}
    out = {}
    for role, contract in definitions.items():
        name = role.removeprefix("state:step5c:")
        if name in source_roles:
            status = "source_content_bound"
        elif name in content_roles:
            status = "retained_content_bound"
        elif name.startswith("llamaguard-input:") or name.startswith("llamaguard-output:"):
            status = "semantic_case_checked_in_separate_helper"
        elif name.startswith("step3f-"):
            status = "not_dispatched"
        elif name in ("runtime-observation-packet", "runtime-observation-diagnostic", "compute-binding-report",
                      "planned-observed-relation", "folded-non-active-candidate-status"):
            status = "legacy_carrier_not_constructed"
        elif name in ("quality-ledger-pre-authority", "effective-required-argument-list"):
            status = "original_runtime_receipt_unavailable"
        else:
            status = "not_produced_on_selected_negative_path"
        out[role] = {"legacy_obligation": contract["const"], "status": status,
                     "original_success_profile_satisfied": False}
    return out


def verify(repo_root: Path, plan_path: Path, evidence_dir: Path, expected_source: str,
           expected_run_id: int, expected_attempt: int, capture_path: Path, capsule_path: Path,
           replay_python: Path, work_dir: Path | None = None) -> dict:
    require(type(expected_run_id) is int and expected_run_id > 0 and
            type(expected_attempt) is int and expected_attempt == 1, "exact_first_attempt_required")
    plan_raw = read(plan_path, LIMITS["max_json_bytes"])
    plan = object_json(plan_raw)
    verifier_schema = read(Path(__file__).resolve().parents[1] / "schemas/pulsemech_compute_admission_rejection_v0.schema.json",
                           LIMITS["max_json_bytes"])
    validate_schema(plan, verifier_schema, "plan_profile_schema")
    request = read(plan_path.parent / "input/q2_request.json", 16384)
    tree, inventory, sources = source_objects(ordinary(repo_root), expected_source)
    graph = validate_plan(plan, sources, tree, inventory, expected_source, request)
    acquisition, contents, entries = acquisition_files(ordinary(evidence_dir), plan_raw, expected_source,
                                                       expected_run_id, expected_attempt)
    validate_schema(acquisition, verifier_schema, "acquisition_profile_schema")
    run = validate_runs(contents, entries, expected_source, expected_run_id, expected_attempt)
    jobs = pages(contents, entries, "jobs", f"repos/{REPOSITORY}/actions/runs/{expected_run_id}/attempts/1/jobs")
    artifacts = pages(contents, entries, "artifacts", f"repos/{REPOSITORY}/actions/runs/{expected_run_id}/artifacts")
    jobs_after = pages(contents, entries, "jobs", f"repos/{REPOSITORY}/actions/runs/{expected_run_id}/attempts/1/jobs", True)
    artifacts_after = pages(contents, entries, "artifacts", f"repos/{REPOSITORY}/actions/runs/{expected_run_id}/artifacts", True)
    require(sorted(jobs, key=lambda item: item["id"]) == sorted(jobs_after, key=lambda item: item["id"]) and
            sorted(artifacts, key=lambda item: item["id"]) == sorted(artifacts_after, key=lambda item: item["id"]),
            "inventory_changed_during_acquisition")
    observed = validate_jobs(jobs, graph, run)
    allowed_files = {"api/run.json", "api/run_after.json"}
    allowed_files.update(n for n in contents if re.fullmatch(r"api/(?:jobs|artifacts)-(?:after-)?[0-9]{3}\.json", n))
    allowed_files.update(f"logs/{j['id']}.txt" for j in jobs if j["conclusion"] != "skipped")
    allowed_files.update(f"archives/{a['id']}.zip" for a in artifacts)
    require(set(contents) == allowed_files, "unexpected_acquired_evidence")
    log_relation = rejection_logs(contents, entries, jobs, sources[WORKFLOW], digest(request))
    hosted, attested, diagnostics, archive_refs = validate_archives(artifacts, contents, entries, run)
    gate_relation = check_required_gates(diagnostics, sources, run)
    for kind, path in (("capture", capture_path), ("capsule", capsule_path)):
        expected = SELECTED_INPUTS[kind]
        require(file_identity(path, 2 * 1024**3) == {"bytes": expected["bytes"], "sha256": expected["sha256"]},
                "original_input_digest:" + kind)
    # This verifier source is independently supplied; the evidence cannot select an executable.
    if __package__:
        from . import pulsemech_compute_admission_rejection_semantics_v0 as semantics
    else:
        import pulsemech_compute_admission_rejection_semantics_v0 as semantics
    run_identity = {"repository": REPOSITORY, "source_commit": expected_source, "run_id": expected_run_id,
                    "run_attempt": expected_attempt, "event": "workflow_dispatch", "ref": "refs/heads/main",
                    "run_started_at": run["run_started_at"], "updated_at": run["updated_at"]}
    if work_dir is not None:
        ordinary(work_dir).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="admission-check-", dir=work_dir) as temp_name:
        temporary = Path(temp_name)
        replay_repo = temporary / "source"
        git(repo_root, ["clone", "--quiet", "--shared", "--no-checkout", "--", str(ordinary(repo_root)), str(replay_repo)])
        git(replay_repo, ["checkout", "--quiet", "--detach", "--force", expected_source])
        require(git(replay_repo, ["rev-parse", "HEAD"]).decode().strip() == expected_source, "replay_source_commit")
        (temporary / "q2").mkdir(mode=0o700)
        (temporary / "llamaguard").mkdir(mode=0o700)
        q2 = semantics.verify_q2(replay_repo, request, ordinary(capture_path), ordinary(capsule_path),
                                 diagnostics["required_gate_inputs/q2_intake_result_v0.json"],
                                 diagnostics["required_gate_inputs/q2_intake_independent_result_v0.json"],
                                 run_identity, replay_python, temporary / "q2")
        llama = semantics.verify_llamaguard(replay_repo, hosted, attested, run_identity, temporary / "llamaguard")
    # Input objects are large external files. A changed input invalidates this replay.
    for kind, path in (("capture", capture_path), ("capsule", capsule_path)):
        expected = SELECTED_INPUTS[kind]
        require(file_identity(path, 2 * 1024**3) == {"bytes": expected["bytes"], "sha256": expected["sha256"]},
                "input_changed_during_replay")
    files = [{"path": item["path"], "bytes": item["bytes"], "sha256": item["sha256"]}
             for item in acquisition["files"]]
    report = {"format": "pulsemech_compute_admission_rejection_report_v0", "profile_id": PROFILE,
            "authority_effect": "none", "accepted": True,
            "bounded_claim": "source_bound_admission_rejection_and_downstream_guard_observed",
            "source": {"repository": REPOSITORY, "commit": expected_source, "tree": tree,
                       "file_count": len(inventory), "closure_sha256": digest(canonical(inventory)),
                       "workflow_sha256": WORKFLOW_SHA, "policy_sha256": POLICY_SHA},
            "run": run_identity, "plan_sha256": digest(plan_raw),
            "acquisition_sha256": digest(read(evidence_dir / "acquisition.json", LIMITS["max_json_bytes"])),
            "observed_jobs": observed, "source_step_templates": 147, "instantiated_source_steps": 129,
            "rejection_log_relation": log_relation, "required_gate_relation": gate_relation,
            "archives": archive_refs, "raw_evidence": sorted(files, key=lambda x: x["path"]),
            "semantic_replay": {"q2": q2, "llamaguard": llama},
            "verifier": {"checker_sha256": digest(read(Path(__file__), 4 * 1024 * 1024)),
                         "semantic_helper_sha256": digest(read(Path(semantics.__file__), 4 * 1024 * 1024)),
                         "schema_sha256": digest(verifier_schema),
                         "python_version": sys.version.split()[0],
                         "python_executable_sha256": file_identity(Path(sys.executable).resolve(), 64 * 1024 * 1024)["sha256"],
                         "pyyaml_version": yaml.__version__,
                         "jsonschema_version": importlib.metadata.version("jsonschema")},
            "legacy_role_status": legacy_roles(sources, diagnostics),
            "limitations": {"legacy_success_profile_satisfied": False, "step5c_complete": False,
                            "step5d_complete": False, "observed_allow": False, "final_release_decision_produced": False,
                            "external_tool_and_host_source_closure": False, "api_carrier_independently_signed": False,
                            "original_dispatch_input_receipt_preserved": False,
                            "original_runtime_consumption_proved_by_replay": False,
                            "resource_measurement_claimed": False, "q1_or_q3_metric_claimed": False},
            "excluded_claims": EXCLUDED}
    validate_schema(report, verifier_schema, "report_profile_schema")
    return report


def write_new(path: Path, raw: bytes) -> None:
    fd = os.open(ordinary(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repo-root", "plan", "evidence-dir", "capture", "capsule", "replay-python", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--expected-source", required=True)
    parser.add_argument("--expected-run-id", required=True, type=int)
    parser.add_argument("--expected-attempt", required=True, type=int)
    args = parser.parse_args(argv)
    try:
        report = verify(args.repo_root, args.plan, args.evidence_dir, args.expected_source,
                        args.expected_run_id, args.expected_attempt, args.capture, args.capsule,
                        args.replay_python)
        write_new(args.out, canonical(report))
    except Exception as exc:
        # Never serialize exception payloads, which may contain request tokens or paths.
        code = str(exc) if isinstance(exc, VerificationError) else "verification_rejected"
        failure = {"format": "pulsemech_compute_admission_rejection_report_v0", "profile_id": PROFILE,
                   "accepted": False, "authority_effect": "none", "error": code}
        try:
            write_new(args.out, canonical(failure))
        except OSError:
            pass
        print(canonical(failure).decode(), end="", file=sys.stderr)
        return 1
    print(canonical({"accepted": True, "profile_id": PROFILE, "authority_effect": "none",
                     "report": str(args.out)}).decode(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

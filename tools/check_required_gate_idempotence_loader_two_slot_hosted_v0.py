#!/usr/bin/env python3
"""Check finite hosted two-slot qualification evidence without executing a probe.

This data-only contract deliberately imports only the existing attempt checker.
The unchanged checker owns all native-record mechanics.  Hosted preservation,
container policy and GitHub run bindings never imply physical authentication or
release authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_required_gate_idempotence_loader_two_slot_attempt_v0 as core

ROOT = Path(__file__).resolve().parents[1]
PROFILE = "linux_x86_64_loader_two_slot_hosted_v0"
REPOSITORY = "HKati/pulse-release-gates-0.1"
REPOSITORY_ID = "1061766508"
WORKFLOW = ".github/workflows/required_gate_idempotence_loader_two_slot_qualification_v0.yml"
CONFIG = "tools/required_gate_idempotence_loader_two_slot_hosted_v0"
ACKNOWLEDGEMENT = "QUALIFY_LOADER_TWO_SLOT_ONLY"
PYTHON = "/usr/local/bin/python3.11"
PYTHON_VERSION = "3.11.16"
SCHEMA_PATH = "schemas/required_gate_idempotence_loader_two_slot_hosted_v0.schema.json"
CONFIG_FILES = ("Dockerfile", "environment.json", "requirements.lock", "build_environment.py", "run.py")
SOURCE_PATHS = tuple(sorted((*core.SOURCE_PATHS, WORKFLOW, SCHEMA_PATH,
    "tools/required_gate_idempotence_loader_two_slot_hosted_v0.py",
    "tools/check_required_gate_idempotence_loader_two_slot_hosted_v0.py",
    "tools/required_gate_idempotence_exec_stop_hosted_io_v0.py",
    *(CONFIG + "/" + name for name in CONFIG_FILES))))
BOUNDARY = {**core.BOUNDARY, "selected_runtime_executed": False}
CONTROL_LIMIT = MAX_CONTROL_BYTES = 65536
SOURCE_LIMIT = MAX_SOURCE_BYTES = 1048576
COMMAND_LIMIT = 4 * 1024 * 1024
FILE_LIMIT = 256 * 1024 * 1024
TOTAL_LIMIT = 512 * 1024 * 1024
FILE_COUNT_LIMIT = 256
ENVIRONMENT_BINDING = {"size_bytes": 5124,
    "sha256": "8419a2ebcd3d5014d4395cbd9118d1db74de35743d171e4011607bbba5848612"}
OBSERVER_BINDING = {"size_bytes": 14472,
    "sha256": "92d7e40ec50be176cb1b790c7568b7e08cd862137b5aa69f1413ba1967886b79"}
SELECTION_TYPE = "required_gate_idempotence_loader_two_slot_hosted_selection_v0"
PLAN_TYPE = "required_gate_idempotence_loader_two_slot_hosted_container_plan_v0"
SUMMARY_TYPE = "required_gate_idempotence_loader_two_slot_hosted_summary_v0"
RECEIPT_TYPE = "required_gate_idempotence_loader_two_slot_hosted_receipt_v0"
PREFIX_TYPE = "required_gate_idempotence_loader_two_slot_hosted_prefix_v0"
HOST_COMMANDS = (
    "git-head-before", "git-source-tree", "git-head-after", "base-pull",
    "base-inspect", "base-tag", "base-save", "base-load", "base-tag-inspect",
    "base-inspect-after", "image-build", "image-inspect", "container-create",
    "container-inspect", "container-start", "container-state",
    "container-ownership-inspect", "container-remove", "container-absence",
    "artifact-metadata", "attestation-verify",
)
INNER_COMMANDS = ("probe", "attempt-check-1", "attempt-check-2")
WHEEL_FILENAMES = (
    "attrs-26.1.0-py3-none-any.whl", "jsonschema-4.26.0-py3-none-any.whl",
    "jsonschema_specifications-2025.9.1-py3-none-any.whl", "referencing-0.37.0-py3-none-any.whl",
    "rpds_py-2026.9.1-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
    "typing_extensions-4.16.0-py3-none-any.whl",
)
CONTEXT_KEYS = frozenset(("repository", "repository_id", "source_commit", "workflow_sha",
    "workflow_ref", "run_id", "run_number", "run_attempt", "event_name", "ref",
    "actor", "triggering_actor", "acknowledgement"))
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
IMAGE_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
ERROR_RE = re.compile(r"[a-z][a-z0-9_]{0,127}\Z")


class HostedError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise HostedError(code)


def canonical(value):
    return core.canonical(value)


def binding(value):
    _need(type(value) is bytes, "two_slot_hosted_binding_type")
    return {"size_bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()}


def _same(actual, expected, code):
    _need(canonical(actual) == canonical(expected), code)


def _keys(value, keys, code):
    _need(type(value) is dict and set(value) == set(keys), code)


def _descriptor(value, maximum=FILE_LIMIT, minimum=0):
    _keys(value, ("size_bytes", "sha256"), "two_slot_hosted_descriptor_fields")
    _need(type(value["size_bytes"]) is int and minimum <= value["size_bytes"] <= maximum,
          "two_slot_hosted_descriptor_extent")
    _need(type(value["sha256"]) is str and HEX64.fullmatch(value["sha256"]),
          "two_slot_hosted_descriptor_digest")


def _pairs(items):
    result = {}
    for key, value in items:
        _need(key not in result, "two_slot_hosted_duplicate_key")
        result[key] = value
    return result


def _noninteger(_value):
    raise HostedError("two_slot_hosted_noninteger_json")


def _nonfinite(_value):
    raise HostedError("two_slot_hosted_nonfinite_json")


def _parse(value, limit, floats):
    _need(type(value) is bytes and 0 < len(value) <= limit, "two_slot_hosted_json_extent")
    try:
        result = json.loads(value.decode("ascii"), object_pairs_hook=_pairs,
            parse_float=float if floats else _noninteger, parse_constant=_nonfinite)
        pending, count = [(result, 0)], 0
        while pending:
            item, depth = pending.pop()
            count += 1
            _need(count <= 32768 and depth <= 32, "two_slot_hosted_json_structure")
            if type(item) is dict:
                _need(len(item) <= 512, "two_slot_hosted_json_structure")
                for key, child in item.items():
                    _need(type(key) is str and len(key) <= 4096, "two_slot_hosted_json_key")
                    pending.append((child, depth + 1))
            elif type(item) is list:
                _need(len(item) <= 512, "two_slot_hosted_json_structure")
                pending.extend((child, depth + 1) for child in item)
            elif type(item) is str:
                _need(len(item) <= 16384, "two_slot_hosted_json_string")
            else:
                _need(item is None or type(item) is bool or
                      (type(item) is int and -(1 << 63) < item < (1 << 63)) or
                      (floats and type(item) is float and math.isfinite(item)),
                      "two_slot_hosted_json_value")
        return result
    except HostedError:
        raise
    except (UnicodeError, ValueError, RecursionError, OverflowError) as exc:
        raise HostedError("two_slot_hosted_invalid_json") from exc


def parse(value, limit=CONTROL_LIMIT):
    """Small protocol controls permit integers, never floats or duplicate keys."""
    return _parse(value, limit, False)


def parse_external(value, limit=COMMAND_LIMIT):
    """Generic command/Docker diagnostics permit only finite numeric values."""
    return _parse(value, limit, True)


def read_regular(path, limit=CONTROL_LIMIT, *, empty=False):
    return core.read_regular(path, limit, empty=empty)


def write_new(path, value):
    raw = value if type(value) is bytes else canonical(value)
    _need(len(raw) <= CONTROL_LIMIT, "two_slot_hosted_control_extent")
    core.write_new(path, raw)
    return binding(raw)


def _json(path, limit=CONTROL_LIMIT, *, external=False):
    raw = read_regular(path, limit)
    return parse_external(raw, limit) if external else parse(raw, limit)


def validate_context(ctx):
    _keys(ctx, CONTEXT_KEYS, "two_slot_hosted_context_fields")
    _need(ctx["repository"] == REPOSITORY and ctx["repository_id"] == REPOSITORY_ID
          and ctx["actor"] == ctx["triggering_actor"] == "HKati"
          and ctx["event_name"] == "workflow_dispatch" and ctx["ref"] == "refs/heads/main"
          and ctx["workflow_ref"] == REPOSITORY + "/" + WORKFLOW + "@refs/heads/main"
          and ctx["acknowledgement"] == ACKNOWLEDGEMENT,
          "two_slot_hosted_context_selection")
    _need(type(ctx["source_commit"]) is str and
          re.fullmatch(r"[0-9a-f]{40}", ctx["source_commit"]) is not None and
          ctx["workflow_sha"] == ctx["source_commit"], "two_slot_hosted_source_commit")
    _need(type(ctx["run_attempt"]) is int and ctx["run_attempt"] == 1 and
          all(type(ctx[key]) is int and 0 < ctx[key] < (1 << 63)
              for key in ("run_id", "run_number")), "two_slot_hosted_run_identity")
    return ctx


def context(environ=None):
    env = os.environ if environ is None else environ
    def number(key):
        value = env.get(key, "")
        _need(type(value) is str and re.fullmatch(r"[1-9][0-9]{0,18}", value),
              "two_slot_hosted_context_number")
        return int(value)
    ctx = {"repository": env.get("GITHUB_REPOSITORY"),
        "repository_id": env.get("GITHUB_REPOSITORY_ID"),
        "source_commit": env.get("GITHUB_SHA"), "workflow_sha": env.get("GITHUB_WORKFLOW_SHA"),
        "workflow_ref": env.get("GITHUB_WORKFLOW_REF"), "run_id": number("GITHUB_RUN_ID"),
        "run_number": number("GITHUB_RUN_NUMBER"), "run_attempt": number("GITHUB_RUN_ATTEMPT"),
        "event_name": env.get("GITHUB_EVENT_NAME"), "ref": env.get("GITHUB_REF"),
        "actor": env.get("GITHUB_ACTOR"), "triggering_actor": env.get("GITHUB_TRIGGERING_ACTOR"),
        "acknowledgement": env.get("TWO_SLOT_HOSTED_ACKNOWLEDGEMENT")}
    validate_context(ctx)
    _need(env.get("EXPECTED_SOURCE_COMMIT") == ctx["source_commit"],
          "two_slot_hosted_expected_source")
    return ctx


def request_identity(ctx):
    validate_context(ctx)
    return hashlib.sha256(canonical({"profile": PROFILE, "context": ctx})).hexdigest()[:32]


def environment():
    raw = read_regular(ROOT / CONFIG / "environment.json", CONTROL_LIMIT)
    _same(binding(raw), ENVIRONMENT_BINDING, "two_slot_hosted_environment_selection")
    selected = parse(raw)
    _need(selected["profile"] == PROFILE and selected["python"]["observer_binding"] == OBSERVER_BINDING,
          "two_slot_hosted_environment_profile")
    return selected


def source_bindings():
    return {name: binding(read_regular(ROOT / name, SOURCE_LIMIT)) for name in SOURCE_PATHS}


def _sources(value):
    _keys(value, SOURCE_PATHS, "two_slot_hosted_source_roster")
    for selected in value.values():
        _descriptor(selected, SOURCE_LIMIT, 1)


def validate_handoff(value):
    _keys(value, ("artifact_id", "artifact_digest", "receipt_sha256"), "two_slot_hosted_handoff_fields")
    _need(type(value["artifact_id"]) is int and 0 < value["artifact_id"] < (1 << 63),
          "two_slot_hosted_artifact_id")
    _need(type(value["artifact_digest"]) is str and IMAGE_RE.fullmatch(value["artifact_digest"]),
          "two_slot_hosted_artifact_digest")
    _need(type(value["receipt_sha256"]) is str and HEX64.fullmatch(value["receipt_sha256"]),
          "two_slot_hosted_receipt_digest")
    return value


def handoff(environ=None):
    env = os.environ if environ is None else environ
    value = env.get("TWO_SLOT_HOSTED_ARTIFACT_ID", "")
    _need(type(value) is str and re.fullmatch(r"[1-9][0-9]{0,18}", value), "two_slot_hosted_artifact_id")
    return validate_handoff({"artifact_id": int(value),
        "artifact_digest": env.get("TWO_SLOT_HOSTED_ARTIFACT_DIGEST"),
        "receipt_sha256": env.get("EXPECTED_RECEIPT_SHA256")})


def make_selection(phase, ctx, image_id, sources, environment_binding, handoff=None):
    result = {"record_type": SELECTION_TYPE, "profile": PROFILE, "phase": phase,
        "context": ctx, "image_id": image_id, "sources": sources,
        "environment": environment_binding, "handoff": handoff, "boundary": dict(BOUNDARY)}
    return validate_selection(result, phase)


def validate_selection(value, phase):
    _keys(value, ("record_type", "profile", "phase", "context", "image_id", "sources",
                  "environment", "handoff", "boundary"), "two_slot_hosted_selection_fields")
    _need(phase in ("acquire", "verify") and value["phase"] == phase and
          value["record_type"] == SELECTION_TYPE and value["profile"] == PROFILE,
          "two_slot_hosted_selection_profile")
    validate_context(value["context"])
    _need(type(value["image_id"]) is str and IMAGE_RE.fullmatch(value["image_id"]),
          "two_slot_hosted_image_id")
    _sources(value["sources"])
    _same(value["environment"], ENVIRONMENT_BINDING, "two_slot_hosted_environment_selection")
    _same(value["sources"][CONFIG + "/environment.json"], value["environment"],
          "two_slot_hosted_environment_source")
    _same(value["boundary"], BOUNDARY, "two_slot_hosted_boundary")
    if phase == "verify":
        validate_handoff(value["handoff"])
    else:
        _need(value["handoff"] is None, "two_slot_hosted_acquisition_handoff")
    _need(len(canonical(value)) <= CONTROL_LIMIT, "two_slot_hosted_control_extent")
    return value


def expected_env(ctx, phase, image_id, handoff=None):
    validate_context(ctx)
    _need(phase in ("acquire", "verify") and type(image_id) is str and IMAGE_RE.fullmatch(image_id),
          "two_slot_hosted_environment_phase")
    result = {"EXPECTED_SOURCE_COMMIT": ctx["source_commit"],
        "TWO_SLOT_HOSTED_ACKNOWLEDGEMENT": ACKNOWLEDGEMENT,
        "TWO_SLOT_HOSTED_PHASE": phase, "TWO_SLOT_HOSTED_IMAGE_ID": image_id,
        "GITHUB_REPOSITORY": REPOSITORY, "GITHUB_REPOSITORY_ID": REPOSITORY_ID,
        "GITHUB_SHA": ctx["source_commit"], "GITHUB_WORKFLOW_SHA": ctx["workflow_sha"],
        "GITHUB_WORKFLOW_REF": ctx["workflow_ref"], "GITHUB_RUN_ID": str(ctx["run_id"]),
        "GITHUB_RUN_NUMBER": str(ctx["run_number"]), "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF": "refs/heads/main",
        "GITHUB_ACTOR": "HKati", "GITHUB_TRIGGERING_ACTOR": "HKati",
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "LC_ALL": "C", "TZ": "UTC"}
    if handoff is not None:
        _need(phase == "verify", "two_slot_hosted_acquisition_handoff")
        validate_handoff(handoff)
        result.update(TWO_SLOT_HOSTED_ARTIFACT_ID=str(handoff["artifact_id"]),
            TWO_SLOT_HOSTED_ARTIFACT_DIGEST=handoff["artifact_digest"],
            EXPECTED_RECEIPT_SHA256=handoff["receipt_sha256"])
    return result


def _environment_map(value):
    _need(type(value) is list and len(value) <= 128, "two_slot_hosted_image_environment")
    result = {}
    for entry in value:
        _need(type(entry) is str and "=" in entry and len(entry) <= 8192 and
              "\x00" not in entry and "\n" not in entry, "two_slot_hosted_image_environment")
        key, item = entry.split("=", 1)
        _need(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) and key not in result,
              "two_slot_hosted_image_environment")
        result[key] = item
    return result


def container_name(ctx, phase):
    return "pulse-two-slot-" + str(ctx["run_id"]) + "-1-" + phase


def container_labels(ctx, phase):
    return {"org.pulsemech.two-slot.run": str(ctx["run_id"]) + "/1",
        "org.pulsemech.two-slot.source": ctx["source_commit"],
        "org.pulsemech.two-slot.profile": PROFILE, "org.pulsemech.two-slot.phase": phase}


def _mount_source(value):
    _need(type(value) is str and Path(value).is_absolute() and len(value) <= 4096 and
          ".." not in Path(value).parts and not any(c in value for c in (",", "\n", "\r", "\x00")),
          "two_slot_hosted_mount_path")


def make_container_plan(phase, ctx, image_id, uid, gid, root, image_environment,
                        selection_binding, previous=None, handoff=None):
    root = Path(root)
    mounts = [{"source": str(root / "source"), "target": "/repo", "readonly": True},
        {"source": str(root / "control"), "target": "/control", "readonly": True},
        {"source": str(root / ("observation" if phase == "acquire" else "verification")),
         "target": "/output", "readonly": False}]
    _need((previous is not None) == (phase == "verify"), "two_slot_hosted_input_mount")
    if previous is not None:
        mounts.append({"source": str(previous), "target": "/input", "readonly": True})
    value = {"record_type": PLAN_TYPE, "profile": PROFILE, "phase": phase, "context": ctx,
        "image_id": image_id, "uid": uid, "gid": gid, "name": container_name(ctx, phase),
        "labels": container_labels(ctx, phase), "image_environment": image_environment,
        "environment": expected_env(ctx, phase, image_id, handoff),
        "mounts": sorted(mounts, key=lambda item: item["target"]), "entrypoint": [PYTHON],
        "command": ["-I", "-B", "/repo/" + CONFIG + "/run.py", phase],
        "selection": selection_binding}
    return validate_container_plan(value, phase, handoff=handoff)


def validate_container_plan(value, phase, *, handoff=None):
    _keys(value, ("record_type", "profile", "phase", "context", "image_id", "uid", "gid",
        "name", "labels", "image_environment", "environment", "mounts", "entrypoint",
        "command", "selection"), "two_slot_hosted_plan_fields")
    _need(phase in ("acquire", "verify") and value["phase"] == phase and
          value["record_type"] == PLAN_TYPE and value["profile"] == PROFILE,
          "two_slot_hosted_plan_profile")
    validate_context(value["context"])
    _need(type(value["image_id"]) is str and IMAGE_RE.fullmatch(value["image_id"]), "two_slot_hosted_image_id")
    _need(all(type(value[key]) is int and 0 < value[key] < (1 << 31) for key in ("uid", "gid")),
          "two_slot_hosted_nonroot_user")
    _same(value["labels"], container_labels(value["context"], phase), "two_slot_hosted_plan_labels")
    _need(value["name"] == container_name(value["context"], phase), "two_slot_hosted_plan_name")
    _environment_map(value["image_environment"])
    _same(value["environment"], expected_env(value["context"], phase, value["image_id"], handoff),
          "two_slot_hosted_plan_environment")
    _same(value["entrypoint"], [PYTHON], "two_slot_hosted_plan_entrypoint")
    _same(value["command"], ["-I", "-B", "/repo/" + CONFIG + "/run.py", phase],
          "two_slot_hosted_plan_command")
    _descriptor(value["selection"], CONTROL_LIMIT, 1)
    targets = ["/control", "/input", "/output", "/repo"] if phase == "verify" else ["/control", "/output", "/repo"]
    _need(type(value["mounts"]) is list and len(value["mounts"]) == len(targets), "two_slot_hosted_plan_mounts")
    for mount, target in zip(value["mounts"], targets):
        _keys(mount, ("source", "target", "readonly"), "two_slot_hosted_plan_mounts")
        _mount_source(mount["source"])
        _need(mount["target"] == target and type(mount["readonly"]) is bool and
              mount["readonly"] == (target != "/output"), "two_slot_hosted_plan_mounts")
    return value


def _native_report(value, request_id):
    return (type(value) is dict and value.get("request_id") == request_id and
        value.get("status") == "accepted_native_qualification_attempt" and
        value.get("evidence_origin") == "native_owned_probe" and
        type(value.get("producer_invocations")) is int and value["producer_invocations"] == 1 and
        value.get("complete_mechanics_verified") is True and
        value.get("native_record_reconstructed") is True and
        value.get("scripted_record_reconstructed") is False and
        all(type(value.get(key)) is type(item) and value.get(key) == item for key, item in core.BOUNDARY.items()))


def make_summary(phase, selection, *, request_bytes=None, attempt_bytes=None,
                 qualification_bytes=None, report_bytes=(), error_code=None):
    validate_selection(selection, phase)
    _need(type(report_bytes) in (tuple, list) and len(report_bytes) <= 2,
          "two_slot_hosted_summary_reports")
    reports = [parse(raw) for raw in report_bytes]
    request_id = request_identity(selection["context"])
    complete = (error_code is None and len(reports) == 2 and report_bytes[0] == report_bytes[1]
        and canonical(reports[0]) == report_bytes[0]
        and _native_report(reports[0], request_id) and request_bytes is not None and
        attempt_bytes is not None and qualification_bytes is not None)
    descriptors = {"request": None if request_bytes is None else binding(request_bytes),
        "attempt": None if attempt_bytes is None else binding(attempt_bytes),
        "qualification": None if qualification_bytes is None else binding(qualification_bytes)}
    if complete:
        complete = canonical(reports[0]) == canonical(_expected_native_report(
            request_id, descriptors["request"], descriptors["attempt"], descriptors["qualification"]))
    value = {"record_type": SUMMARY_TYPE, "profile": PROFILE, "phase": phase,
        "context": selection["context"], "image_id": selection["image_id"],
        "selection": binding(canonical(selection)), "request_id": request_id, **descriptors,
        "reports": [binding(raw) for raw in report_bytes],
        "status": "completed_native_reconstruction" if complete else "preserved_incomplete",
        "error_code": None if complete else (error_code or "two_slot_hosted_native_reconstruction_incomplete"),
        "boundary": dict(BOUNDARY)}
    return validate_summary(value, phase)


def validate_summary(value, phase):
    _keys(value, ("record_type", "profile", "phase", "context", "image_id", "selection",
        "request_id", "request", "attempt", "qualification", "reports", "status", "error_code",
        "boundary"), "two_slot_hosted_summary_fields")
    _need(value["record_type"] == SUMMARY_TYPE and value["profile"] == PROFILE and
          phase in ("acquire", "verify") and value["phase"] == phase, "two_slot_hosted_summary_profile")
    validate_context(value["context"])
    _need(type(value["image_id"]) is str and IMAGE_RE.fullmatch(value["image_id"]), "two_slot_hosted_image_id")
    _descriptor(value["selection"], CONTROL_LIMIT, 1)
    _need(value["request_id"] == request_identity(value["context"]), "two_slot_hosted_request_identity")
    for key in ("request", "attempt", "qualification"):
        if value[key] is not None:
            _descriptor(value[key], core.MAX_QUALIFICATION_BYTES if key == "qualification" else CONTROL_LIMIT,
                        0 if key == "qualification" and value["status"] == "preserved_incomplete" else 1)
    _need(type(value["reports"]) is list and len(value["reports"]) <= 2, "two_slot_hosted_summary_reports")
    for item in value["reports"]:
        _descriptor(item, CONTROL_LIMIT, 1)
    _same(value["boundary"], BOUNDARY, "two_slot_hosted_boundary")
    _need(value["status"] in ("completed_native_reconstruction", "preserved_incomplete"), "two_slot_hosted_summary_status")
    if value["status"] == "completed_native_reconstruction":
        _need(value["error_code"] is None and len(value["reports"]) == 2 and
              all(value[key] is not None for key in ("request", "attempt", "qualification")),
              "two_slot_hosted_summary_complete")
    else:
        _need(type(value["error_code"]) is str and ERROR_RE.fullmatch(value["error_code"]),
              "two_slot_hosted_summary_error")
    return value


def validate_container_identity(info, cid, image, ctx, phase, plan, ownership_only=False):
    """Bind ownership first, then the actual Docker command, mounts and policy."""
    validate_context(ctx)
    _need(type(cid) is str and HEX64.fullmatch(cid) and type(image) is str and IMAGE_RE.fullmatch(image),
          "two_slot_hosted_container_identity")
    _need(type(info) is list and len(info) == 1 and type(info[0]) is dict,
          "two_slot_hosted_container_inspect")
    item = info[0]
    config, host = item.get("Config"), item.get("HostConfig")
    _need(type(config) is dict and type(host) is dict, "two_slot_hosted_container_inspect")
    _need(item.get("Id") == cid and item.get("Image") == image and
          item.get("Name") == "/" + container_name(ctx, phase), "two_slot_hosted_container_ownership")
    _same(config.get("Labels"), container_labels(ctx, phase), "two_slot_hosted_container_labels")
    if ownership_only:
        return item
    _need(type(plan) is dict, "two_slot_hosted_plan_fields")
    handoff_value = None
    if phase == "verify":
        env = plan.get("environment", {})
        _need(type(env) is dict, "two_slot_hosted_plan_environment")
        handoff_value = handoff(env)
    validate_container_plan(plan, phase, handoff=handoff_value)
    _same(plan["context"], ctx, "two_slot_hosted_plan_context")
    _need(plan["image_id"] == image, "two_slot_hosted_plan_image")
    _same(config.get("Entrypoint"), plan["entrypoint"], "two_slot_hosted_container_entrypoint")
    _same(config.get("Cmd"), plan["command"], "two_slot_hosted_container_command")
    _need(config.get("User") == str(plan["uid"]) + ":" + str(plan["gid"])
          and config.get("WorkingDir") == "/repo" and config.get("Image") == image,
          "two_slot_hosted_container_user")
    expected_environment = {**_environment_map(plan["image_environment"]), **plan["environment"]}
    _same(_environment_map(config.get("Env")), expected_environment, "two_slot_hosted_container_environment")
    _need(host.get("Privileged") is False and host.get("ReadonlyRootfs") is True
          and host.get("NetworkMode") == "none" and host.get("CapDrop") == ["ALL"]
          and host.get("CapAdd") in (None, [])
          and host.get("SecurityOpt") in (
              ["no-new-privileges", "apparmor=docker-default"],
              ["no-new-privileges=true", "apparmor=docker-default"])
          and type(host.get("PidsLimit")) is int and host["PidsLimit"] == 64
          and type(host.get("Memory")) is int and host["Memory"] == 1024 ** 3
          and type(host.get("NanoCpus")) is int and host["NanoCpus"] == 10 ** 9
          and host.get("Tmpfs") == {"/tmp": "rw,nosuid,nodev,size=64m"},
          "two_slot_hosted_container_policy")
    # No other path may regain a host namespace, device or writable mount.
    for key in ("CapAdd", "Devices", "DeviceRequests", "DeviceCgroupRules", "VolumesFrom", "Binds",
                "GroupAdd", "Links", "Ulimits", "ExtraHosts", "Dns", "DnsOptions", "DnsSearch"):
        _need(host.get(key) in (None, []), "two_slot_hosted_container_extra_access")
    _need(host.get("Sysctls") in (None, {}) and host.get("PortBindings") in (None, {})
          and host.get("PublishAllPorts", False) is False, "two_slot_hosted_container_extra_access")
    restart = host.get("RestartPolicy", {"Name": "no", "MaximumRetryCount": 0})
    _need(type(restart) is dict and restart.get("Name") in ("", "no") and
          type(restart.get("MaximumRetryCount", 0)) is int and restart.get("MaximumRetryCount", 0) == 0,
          "two_slot_hosted_container_restart")
    for key in ("CpuPeriod", "CpuQuota", "CpuRealtimePeriod", "CpuRealtimeRuntime", "CpuShares"):
        _need(type(host.get(key, 0)) is int and host.get(key, 0) == 0, "two_slot_hosted_container_cpu_override")
    for key in ("CpusetCpus", "CpusetMems"):
        _need(host.get(key, "") == "", "two_slot_hosted_container_cpu_override")
    for key in ("PidMode", "UTSMode", "UsernsMode"):
        _need(host.get(key, "") == "", "two_slot_hosted_container_namespace")
    _need(host.get("IpcMode", "private") == "private" and host.get("CgroupnsMode", "private") in ("", "private")
          and host.get("Init") in (None, False) and host.get("AutoRemove", False) is False
          and item.get("AppArmorProfile") == "docker-default",
          "two_slot_hosted_container_defaults")
    _need(config.get("Volumes") in (None, {}) and config.get("Healthcheck") in (None, {})
          and config.get("Tty", False) is False and config.get("OpenStdin", False) is False,
          "two_slot_hosted_container_config")
    actual_mounts = item.get("Mounts")
    _need(type(actual_mounts) is list and len(actual_mounts) == len(plan["mounts"]),
          "two_slot_hosted_container_mounts")
    actual = {}
    for mount in actual_mounts:
        _need(type(mount) is dict and type(mount.get("Destination")) is str and
              mount["Destination"] not in actual and mount.get("Type") == "bind" and
              type(mount.get("RW")) is bool and mount.get("Propagation", "rprivate") == "rprivate",
              "two_slot_hosted_container_mounts")
        actual[mount["Destination"]] = {"source": mount.get("Source"),
            "target": mount["Destination"], "readonly": not mount["RW"]}
    _same([actual[key] for key in sorted(actual)], plan["mounts"], "two_slot_hosted_container_mounts")
    if "Mounts" in host:
        mounts = host["Mounts"]
        _need(type(mounts) is list and len(mounts) == len(plan["mounts"]), "two_slot_hosted_container_mounts")
        normalized = []
        for mount in mounts:
            _need(type(mount) is dict and mount.get("Type") == "bind" and
                  set(mount) <= {"Type", "Source", "Target", "ReadOnly", "Consistency", "BindOptions"} and
                  mount.get("BindOptions") in (None, {}, {"Propagation": "rprivate"}),
                  "two_slot_hosted_container_mount_options")
            normalized.append({"source": mount.get("Source"), "target": mount.get("Target"),
                "readonly": mount.get("ReadOnly", False)})
        _same(sorted(normalized, key=lambda entry: entry["target"]), plan["mounts"],
              "two_slot_hosted_container_mounts")
    return item


def command_record(root, label, expected_argv=None, *, directory="host-commands", success=True):
    """Check all four fixed command records and byte bindings, including reaping."""
    allowed = HOST_COMMANDS if directory == "host-commands" else INNER_COMMANDS
    _need(label in allowed and directory in ("host-commands", "observation/commands", "verification/commands"),
          "two_slot_hosted_command_label")
    base = Path(root) / directory
    argv_record = _json(base / (label + ".argv.json"))
    _keys(argv_record, ("argv",), "two_slot_hosted_command_argv_fields")
    argv = argv_record["argv"]
    _need(type(argv) is list and 1 <= len(argv) <= 160 and
          all(type(item) is str and 0 < len(item) <= 4096 and "\x00" not in item for item in argv),
          "two_slot_hosted_command_argv")
    if expected_argv is not None:
        _same(argv, expected_argv, "two_slot_hosted_command_selection")
    result = _json(base / (label + ".result.json"), external=True)
    _keys(result, ("argv", "returncode", "failure", "stdout", "stderr", "timeout_seconds",
        "stream_cap", "stdout_cap", "overflowed_streams", "elapsed_seconds", "cleanup"),
        "two_slot_hosted_command_result_fields")
    _same(result["argv"], argv, "two_slot_hosted_command_argv_join")
    _need(result["returncode"] is None or type(result["returncode"]) is int,
          "two_slot_hosted_command_returncode")
    _need(result["failure"] is None or (type(result["failure"]) is str and ERROR_RE.fullmatch(result["failure"])),
          "two_slot_hosted_command_failure")
    _need(type(result["timeout_seconds"]) in (int, float) and math.isfinite(result["timeout_seconds"])
          and 0 < result["timeout_seconds"] <= 1200 and
          type(result["elapsed_seconds"]) in (int, float) and math.isfinite(result["elapsed_seconds"])
          and result["elapsed_seconds"] >= 0, "two_slot_hosted_command_time")
    _need(type(result["stream_cap"]) is int and 0 < result["stream_cap"] <= COMMAND_LIMIT and
          type(result["stdout_cap"]) is int and 0 < result["stdout_cap"] <= FILE_LIMIT and
          (label == "base-save" or result["stdout_cap"] <= COMMAND_LIMIT), "two_slot_hosted_command_cap")
    _need(type(result["overflowed_streams"]) is list and
          result["overflowed_streams"] in ([], ["stderr"], ["stdout"], ["stderr", "stdout"]),
          "two_slot_hosted_command_overflow")
    cleanup = result["cleanup"]
    _keys(cleanup, ("child_started", "child_reaped", "kill_group_sent", "kill_error_errno",
        "pending_output_drain_attempted"), "two_slot_hosted_command_cleanup_fields")
    _need(all(type(cleanup[key]) is bool for key in ("child_started", "child_reaped", "kill_group_sent",
          "pending_output_drain_attempted")) and (cleanup["kill_error_errno"] is None or
          (type(cleanup["kill_error_errno"]) is int and 0 < cleanup["kill_error_errno"] < 65536)),
          "two_slot_hosted_command_cleanup")
    streams = {}
    for key in ("stdout", "stderr"):
        cap = result["stdout_cap"] if key == "stdout" else result["stream_cap"]
        _descriptor(result[key], cap)
        streams[key] = read_regular(base / (label + "." + key + ".bin"), cap, empty=True)
        _same(binding(streams[key]), result[key], "two_slot_hosted_command_stream_binding")
    if success:
        _need(type(result["returncode"]) is int and result["returncode"] == 0 and result["failure"] is None
              and result["overflowed_streams"] == [] and cleanup["child_started"] is True
              and cleanup["child_reaped"] is True and cleanup["kill_group_sent"] is False
              and cleanup["kill_error_errno"] is None and cleanup["pending_output_drain_attempted"] is True,
              "two_slot_hosted_command_incomplete")
    return {"result": result, **streams}


def _plan_root(plan):
    mounts = {entry["target"]: entry for entry in plan["mounts"]}
    root = Path(mounts["/control"]["source"]).parent
    _need(mounts["/control"]["source"] == str(root / "control") and
          mounts["/repo"]["source"] == str(root / "source") and
          mounts["/output"]["source"] == str(root / ("observation" if plan["phase"] == "acquire" else "verification")),
          "two_slot_hosted_mount_source_join")
    return root


def docker_create_argv(plan):
    """The retained command must have exactly this argument vector."""
    root = _plan_root(plan)
    argv = ["docker", "create", "--name", plan["name"], "--cidfile", str(root / "environment/container-id.txt"),
        "--platform", "linux/amd64", "--user", str(plan["uid"]) + ":" + str(plan["gid"]),
        "--read-only", "--network", "none", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--security-opt", "apparmor=docker-default",
        "--pids-limit", "64", "--memory", "1g", "--cpus", "1", "--tmpfs", "/tmp:rw,nosuid,nodev,size=64m",
        "--workdir", "/repo"]
    for key, value in sorted(plan["labels"].items()):
        argv += ["--label", key + "=" + value]
    for mount in plan["mounts"]:
        argv += ["--mount", "type=bind,source=" + mount["source"] + ",target=" + mount["target"] +
            (",readonly" if mount["readonly"] else "")]
    for key, value in sorted(plan["environment"].items()):
        argv += ["--env", key + "=" + value]
    return argv + ["--entrypoint", PYTHON, plan["image_id"], *plan["command"]]


def validate_cleanup(root, ctx, phase):
    root = Path(root)
    record = _json(root / "environment/container-cleanup.json")
    _keys(record, ("container_id", "image_id", "phase", "name", "owned_container_verified",
        "inspect_exit_code", "remove_succeeded", "absence_verified", "cleanup_errors"),
        "two_slot_hosted_cleanup_fields")
    cid, image = record["container_id"], record["image_id"]
    _need(type(cid) is str and HEX64.fullmatch(cid) and type(image) is str and IMAGE_RE.fullmatch(image)
          and record["phase"] == phase and record["name"] == container_name(ctx, phase)
          and record["owned_container_verified"] is True and record["remove_succeeded"] is True
          and record["absence_verified"] is True and type(record["inspect_exit_code"]) is int
          and record["inspect_exit_code"] == 0 and record["cleanup_errors"] == [],
          "two_slot_hosted_cleanup_incomplete")
    _need(read_regular(root / "environment/container-id.txt", 128).decode("ascii").strip() == cid,
          "two_slot_hosted_cleanup_cid")
    plan = _json(root / "environment/container-plan.json")
    _need(plan["image_id"] == image, "two_slot_hosted_cleanup_image")
    owned = command_record(root, "container-ownership-inspect",
        ["docker", "container", "inspect", record["name"]])
    validate_container_identity(parse_external(owned["stdout"]), cid, image, ctx, phase, plan, True)
    removed = command_record(root, "container-remove", ["docker", "rm", "--force", cid])
    _need(removed["stdout"].decode("ascii").strip() == cid, "two_slot_hosted_cleanup_removed_id")
    absent = command_record(root, "container-absence",
        ["docker", "container", "ls", "--all", "--quiet", "--no-trunc", "--filter", "id=" + cid])
    _need(absent["stdout"] == b"", "two_slot_hosted_cleanup_absence")
    return binding(read_regular(root / "environment/container-cleanup.json"))


def allowed_files():
    names = {"workflow-start.json", "source-bindings.json", "failure.json", "attestation-identity.json",
        "prefix-verification.json", "verified-binding.json", "attestation.json", "attestation-bundle.json",
        "environment/selection.json", "environment/image-id.txt", "environment/container-id.txt",
        "environment/container-plan.json", "environment/container-cleanup.json", "control/hosted-selection.json"}
    names.update("source/" + path for path in SOURCE_PATHS)
    names.update("materials/" + path for path in CONFIG_FILES)
    # Failure publication must not need the current environment/source bytes:
    # those may have drifted after their original prelaunch selection.
    names.update("materials/wheels/" + name for name in WHEEL_FILENAMES)
    for label in HOST_COMMANDS:
        names.update("host-commands/" + label + "." + suffix
            for suffix in ("argv.json", "result.json", "stdout.bin", "stderr.bin"))
    for prefix in ("observation", "verification"):
        names.update(prefix + "/" + leaf for leaf in ("request.json", "attempt/request.json",
            "attempt/attempt.json", "attempt/qualification.json", "attempt-check-1.json", "attempt-check-2.json",
            "build-environment-record.json",
            "acquisition-summary.json" if prefix == "observation" else "verification-summary.json"))
        for label in INNER_COMMANDS:
            names.update(prefix + "/commands/" + label + "." + suffix
                for suffix in ("argv.json", "result.json", "stdout.bin", "stderr.bin"))
    return frozenset(names)


def _file_limit(name):
    if name == "host-commands/base-save.stdout.bin":
        return FILE_LIMIT
    if name.startswith("source/") or name.startswith("materials/") or name.endswith("/qualification.json"):
        return SOURCE_LIMIT
    if name.endswith((".stdout.bin", ".stderr.bin")) or name == "attestation-bundle.json":
        return COMMAND_LIMIT
    return CONTROL_LIMIT


def inventory(root):
    """Read only the predetermined finite roster through pinned directory FDs."""
    permitted = allowed_files()
    directories = {str(Path(name).parent) for name in permitted}
    directories.update(str(parent) for name in permitted for parent in Path(name).parents if str(parent) != ".")
    parent, name = core._open_parent(root)
    descriptor = None
    files, total, nodes = {}, 0, 0
    def visit(fd, prefix):
        nonlocal total, nodes
        before = os.fstat(fd)
        names = sorted(os.listdir(fd))
        for leaf in names:
            nodes += 1
            _need(nodes <= FILE_COUNT_LIMIT + len(directories) + 1, "two_slot_hosted_inventory_count")
            child = prefix + leaf
            info = os.stat(leaf, dir_fd=fd, follow_symlinks=False)
            if child == "receipt.json":
                _need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and 0 < info.st_size <= CONTROL_LIMIT,
                      "two_slot_hosted_receipt_extent")
                continue
            if stat.S_ISDIR(info.st_mode):
                _need(child in directories, "two_slot_hosted_directory_roster")
                nxt = os.open(leaf, core._DIRECTORY_FLAGS, dir_fd=fd)
                try:
                    _need(core._identity(info) == core._identity(os.fstat(nxt)), "two_slot_hosted_directory_changed")
                    visit(nxt, child + "/")
                    _need(core._identity(os.fstat(nxt)) == core._identity(os.stat(leaf, dir_fd=fd, follow_symlinks=False)),
                          "two_slot_hosted_directory_changed")
                finally:
                    os.close(nxt)
            else:
                _need(child in permitted and stat.S_ISREG(info.st_mode), "two_slot_hosted_file_roster")
                raw = core._read_at(fd, leaf, _file_limit(child), empty=True)
                files[child] = binding(raw)
                total += len(raw)
                _need(total <= TOTAL_LIMIT and len(files) <= FILE_COUNT_LIMIT, "two_slot_hosted_inventory_limit")
        _need(core._identity(before) == core._identity(os.fstat(fd)) and names == sorted(os.listdir(fd)),
              "two_slot_hosted_directory_changed")
    try:
        descriptor = os.open(name, core._DIRECTORY_FLAGS, dir_fd=parent)
        before = os.fstat(descriptor)
        visit(descriptor, "")
        _need(core._identity(before) == core._identity(os.fstat(descriptor)) ==
              core._identity(os.stat(name, dir_fd=parent, follow_symlinks=False)), "two_slot_hosted_directory_changed")
        return dict(sorted(files.items())), total
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent)


def _optional_json(root, name):
    try:
        return _json(Path(root) / name)
    except FileNotFoundError:
        return None


def make_receipt(root, ctx, phase="acquire"):
    """Seal the available prefix; never replace the original source selection."""
    validate_context(ctx)
    _need(phase in ("acquire", "verify"), "two_slot_hosted_phase")
    files, total = inventory(root)
    sources, error = None, None
    if "source-bindings.json" in files:
        try:
            sources = _json(Path(root) / "source-bindings.json")
            _sources(sources)
        except (OSError, ValueError):
            sources, error = None, "two_slot_hosted_source_selection_invalid"
    status = "preserved_incomplete"
    if phase == "acquire":
        try:
            verify_completed_acquisition(root, ctx)
            status = "completed_native_reconstruction"
        except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
            error = getattr(exc, "code", "two_slot_hosted_acquisition_incomplete")
    else:
        error = error or "two_slot_hosted_verification_prefix"
    location = "observation" if phase == "acquire" else "verification"
    result = {"record_type": RECEIPT_TYPE, "profile": PROFILE, "phase": phase, "context": ctx,
        "sources": sources, "environment": None if sources is None else sources[CONFIG + "/environment.json"],
        "selection": files.get("control/hosted-selection.json"),
        "summary": files.get(location + ("/acquisition-summary.json" if phase == "acquire" else "/verification-summary.json")),
        "request": files.get(location + "/request.json"), "attempt": files.get(location + "/attempt/attempt.json"),
        "qualification": files.get(location + "/attempt/qualification.json"),
        "files": files, "file_count": len(files), "total_size_bytes": total, "status": status,
        "error_code": None if status == "completed_native_reconstruction" else (error or "two_slot_hosted_prefix_incomplete"),
        "boundary": dict(BOUNDARY)}
    return validate_receipt(canonical(result), binding(canonical(result))["sha256"], ctx)


def validate_receipt(raw, expected_sha256, ctx):
    validate_context(ctx)
    _need(type(expected_sha256) is str and HEX64.fullmatch(expected_sha256) and
          binding(raw)["sha256"] == expected_sha256, "two_slot_hosted_receipt_digest")
    value = parse(raw)
    _keys(value, ("record_type", "profile", "phase", "context", "sources", "environment", "selection",
        "summary", "request", "attempt", "qualification", "files", "file_count", "total_size_bytes",
        "status", "error_code", "boundary"), "two_slot_hosted_receipt_fields")
    _need(value["record_type"] == RECEIPT_TYPE and value["profile"] == PROFILE and
          value["phase"] in ("acquire", "verify"), "two_slot_hosted_receipt_profile")
    _same(value["context"], ctx, "two_slot_hosted_receipt_context")
    _same(value["boundary"], BOUNDARY, "two_slot_hosted_boundary")
    if value["sources"] is not None:
        _sources(value["sources"])
        _same(value["environment"], value["sources"][CONFIG + "/environment.json"], "two_slot_hosted_environment_source")
    else:
        _need(value["environment"] is None, "two_slot_hosted_receipt_environment")
    permitted = allowed_files()
    _need(type(value["files"]) is dict and set(value["files"]) <= permitted and
          len(value["files"]) <= FILE_COUNT_LIMIT, "two_slot_hosted_receipt_roster")
    total = 0
    for name, selected in value["files"].items():
        _descriptor(selected, _file_limit(name))
        total += selected["size_bytes"]
    _need(type(value["file_count"]) is int and value["file_count"] == len(value["files"]) and
          type(value["total_size_bytes"]) is int and value["total_size_bytes"] == total <= TOTAL_LIMIT,
          "two_slot_hosted_receipt_totals")
    location = "observation" if value["phase"] == "acquire" else "verification"
    joined = {"selection": "control/hosted-selection.json",
        "summary": location + ("/acquisition-summary.json" if value["phase"] == "acquire" else "/verification-summary.json"),
        "request": location + "/request.json", "attempt": location + "/attempt/attempt.json",
        "qualification": location + "/attempt/qualification.json"}
    for key, name in joined.items():
        _same(value[key], value["files"].get(name), "two_slot_hosted_receipt_descriptor_join")
    _need(value["status"] in ("completed_native_reconstruction", "preserved_incomplete"),
          "two_slot_hosted_receipt_status")
    if value["status"] == "completed_native_reconstruction":
        _need(value["phase"] == "acquire" and value["sources"] is not None and value["error_code"] is None
              and all(value[key] is not None for key in joined), "two_slot_hosted_receipt_complete")
        _same(value["environment"], ENVIRONMENT_BINDING, "two_slot_hosted_environment_selection")
        for key in joined:
            _descriptor(value[key], SOURCE_LIMIT if key == "qualification" else CONTROL_LIMIT, 1)
    else:
        _need(type(value["error_code"]) is str and ERROR_RE.fullmatch(value["error_code"]),
              "two_slot_hosted_receipt_error")
    _need(raw == canonical(value), "two_slot_hosted_receipt_canonical")
    return value


def verify_preservation(root, raw_or_receipt, sha=None, ctx=None):
    raw = raw_or_receipt if type(raw_or_receipt) is bytes else canonical(raw_or_receipt)
    if ctx is None:
        ctx = parse(raw)["context"]
    selected = validate_receipt(raw, binding(raw)["sha256"] if sha is None else sha, ctx)
    actual_receipt = read_regular(Path(root) / "receipt.json")
    _need(actual_receipt == raw, "two_slot_hosted_receipt_preserved_bytes")
    files, total = inventory(root)
    _same(files, selected["files"], "two_slot_hosted_preserved_inventory")
    _need(total == selected["total_size_bytes"], "two_slot_hosted_preserved_size")
    if selected["sources"] is not None:
        _same(_json(Path(root) / "source-bindings.json"), selected["sources"], "two_slot_hosted_preserved_sources")
        for name, descriptor in selected["sources"].items():
            # A failed copy or subsequent drift is itself a useful prefix.
            # Preserve both the original selection and the actual retained
            # bytes; only completion may assert that those are identical.
            if selected["status"] == "completed_native_reconstruction" and "source/" + name in files:
                _same(files["source/" + name], descriptor, "two_slot_hosted_preserved_source_bytes")
    return selected


def validate_artifact_metadata(value, ctx, selected_handoff):
    validate_context(ctx)
    validate_handoff(selected_handoff)
    _need(type(value) is dict and type(value.get("id")) is int and
          value["id"] == selected_handoff["artifact_id"] and
          value.get("name") == "required-gate-idempotence-loader-two-slot-" + str(ctx["run_id"]) + "-1" and
          value.get("digest") == selected_handoff["artifact_digest"] and value.get("expired") is False,
          "two_slot_hosted_artifact_metadata")
    run = value.get("workflow_run")
    _need(type(run) is dict and type(run.get("id")) is int and run["id"] == ctx["run_id"] and
          run.get("head_sha") == ctx["source_commit"] and run.get("head_branch") == "main" and
          type(run.get("repository_id")) is int and run["repository_id"] == int(REPOSITORY_ID) and
          type(run.get("head_repository_id")) is int and run["head_repository_id"] == int(REPOSITORY_ID),
          "two_slot_hosted_artifact_run")
    return value


def _verify_sources(root, ctx, phase):
    prefix = _json(root / "workflow-start.json")
    _same(prefix, {"record_type": "required_gate_idempotence_loader_two_slot_workflow_start_v0",
        "phase": phase, "context": ctx, "boundary": BOUNDARY}, "two_slot_hosted_workflow_start")
    selected = _json(root / "source-bindings.json")
    _sources(selected)
    _same(selected, source_bindings(), "two_slot_hosted_current_source_selection")
    raw_sources = {}
    for name, descriptor in selected.items():
        raw_sources[name] = read_regular(root / "source" / name, SOURCE_LIMIT)
        _same(binding(raw_sources[name]), descriptor, "two_slot_hosted_source_snapshot")
    # The original absolute checkout path is evidence, not the verifier's cwd.
    first = command_record(root, "git-head-before")
    argv = first["result"]["argv"]
    fixed = ["git", "--no-pager", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", "-C"]
    _need(len(argv) == len(fixed) + 4 and argv[:len(fixed)] == fixed and
          argv[-3:] == ["rev-parse", "--verify", "HEAD"], "two_slot_hosted_git_command")
    _mount_source(argv[len(fixed)])
    base = argv[:-3]
    _need(first["stdout"] == (ctx["source_commit"] + "\n").encode("ascii"), "two_slot_hosted_git_head")
    tree = command_record(root, "git-source-tree", [*base, "ls-tree", "-r", "-z", "--full-tree",
        ctx["source_commit"], "--", *SOURCE_PATHS])["stdout"]
    _need(tree.endswith(b"\0"), "two_slot_hosted_git_tree")
    blobs = {}
    for row in tree[:-1].split(b"\0"):
        metadata, separator, name = row.partition(b"\t")
        fields = metadata.split(b" ")
        _need(separator and len(fields) == 3 and fields[0] in (b"100644", b"100755") and fields[1] == b"blob"
              and re.fullmatch(b"[0-9a-f]{40}", fields[2]), "two_slot_hosted_git_blob")
        path = name.decode("ascii")
        _need(path in selected and path not in blobs, "two_slot_hosted_git_roster")
        blobs[path] = fields[2].decode("ascii")
    _need(set(blobs) == set(selected), "two_slot_hosted_git_roster")
    for name, raw in raw_sources.items():
        _need(hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest() == blobs[name],
              "two_slot_hosted_git_source_bytes")
    last = command_record(root, "git-head-after", [*base, "rev-parse", "--verify", "HEAD"])
    _need(last["stdout"] == first["stdout"], "two_slot_hosted_git_head_changed")
    return selected


def _image_info(raw, image):
    value = parse_external(raw)
    _need(type(value) is list and len(value) == 1 and type(value[0]) is dict and
          value[0].get("Id") == image and value[0].get("Architecture") == "amd64" and
          value[0].get("Os") == "linux" and type(value[0].get("Config")) is dict,
          "two_slot_hosted_image_inspect")
    _environment_map(value[0]["Config"].get("Env"))
    return value[0]


def _verify_environment(root, selection, plan, previous=None):
    selected = environment()
    phase = selection["phase"]
    original_root = _plan_root(plan)
    base = selected["base_image"]
    base_id = "sha256:" + base["config_sha256"]
    local_tag = "localhost/pulse-two-slot-base:" + base["config_sha256"]
    image = selection["image_id"]
    record = _json(root / "environment/selection.json")
    _keys(record, ("record_type", "profile", "base_image", "constructed_image_id", "base_archive",
        "base_loaded_from_preserved_bytes", "base_local_build_tag", "environment_selection",
        "build_inputs_fixed", "image_reproducibility_claimed", "boundary"), "two_slot_hosted_image_fields")
    _same(record["base_image"], base, "two_slot_hosted_base_selection")
    _same(record["environment_selection"], ENVIRONMENT_BINDING, "two_slot_hosted_environment_selection")
    _same(record["boundary"], BOUNDARY, "two_slot_hosted_boundary")
    _need(record["record_type"] == "required_gate_idempotence_loader_two_slot_hosted_image_v0"
          and record["profile"] == PROFILE and record["constructed_image_id"] == image
          and record["base_local_build_tag"] == local_tag and record["build_inputs_fixed"] is True
          and record["image_reproducibility_claimed"] is False
          and type(record["base_loaded_from_preserved_bytes"]) is bool
          and record["base_loaded_from_preserved_bytes"] == (phase == "verify"), "two_slot_hosted_image_selection")
    _need(read_regular(root / "environment/image-id.txt", 128).decode("ascii").strip() == image,
          "two_slot_hosted_image_id_binding")
    for name in CONFIG_FILES:
        raw = read_regular(root / "materials" / name, SOURCE_LIMIT)
        _same(binding(raw), selection["sources"][CONFIG + "/" + name], "two_slot_hosted_build_source")
    _same(binding(read_regular(root / "materials/requirements.lock", CONTROL_LIMIT)), selected["requirements"],
          "two_slot_hosted_requirements_lock")
    for wheel in selected["python"]["packages"]:
        _same(binding(read_regular(root / "materials/wheels" / wheel["filename"], SOURCE_LIMIT)),
              {key: wheel[key] for key in ("size_bytes", "sha256")}, "two_slot_hosted_wheel_binding")
    build_record = _json(root / ("observation" if phase == "acquire" else "verification") / "build-environment-record.json")
    expected_build = {"record_type": "required_gate_idempotence_loader_two_slot_build_v0", "profile": PROFILE,
        "environment": ENVIRONMENT_BINDING, "requirements": selected["requirements"],
        "wheels": {item["filename"]: {key: item[key] for key in ("size_bytes", "sha256")}
                   for item in selected["python"]["packages"]},
        "python": OBSERVER_BINDING, "installed": {item["name"]: item["version"] for item in selected["python"]["packages"]},
        "offline_install": True, "reproducible_image_claimed": False, "original_payload_included": False,
        "authority_effect": "none"}
    _same(build_record, expected_build, "two_slot_hosted_build_record")
    if phase == "acquire":
        command_record(root, "base-pull", ["docker", "pull", "--platform", "linux/amd64", base["reference"]])
        inspect_name = base["reference"]
        command_record(root, "base-tag", ["docker", "image", "tag", base_id, local_tag])
        archived = command_record(root, "base-save", ["docker", "image", "save", local_tag])
        _need(len(archived["stdout"]) > 0, "two_slot_hosted_base_archive_empty")
        archive_binding = binding(archived["stdout"])
    else:
        _need(previous is not None, "two_slot_hosted_verification_input")
        mounts = {item["target"]: item["source"] for item in plan["mounts"]}
        _need(mounts["/input"] == str(Path(previous)), "two_slot_hosted_private_input_mount")
        command_record(root, "base-load", ["docker", "image", "load", "--input",
            str(Path(previous) / "host-commands/base-save.stdout.bin")])
        archived = command_record(previous, "base-save", ["docker", "image", "save", local_tag])
        archive_binding = binding(archived["stdout"])
        inspect_name = local_tag
    _same(record["base_archive"], archive_binding, "two_slot_hosted_base_archive_binding")
    inspected = command_record(root, "base-inspect", ["docker", "image", "inspect", inspect_name])
    base_info = _image_info(inspected["stdout"], base_id)
    tagged = command_record(root, "base-tag-inspect", ["docker", "image", "inspect", local_tag])
    tagged_info = _image_info(tagged["stdout"], base_id)
    _same(_environment_map(base_info["Config"]["Env"]), _environment_map(tagged_info["Config"]["Env"]),
          "two_slot_hosted_base_environment")
    command_record(root, "image-build", ["docker", "build", "--platform", "linux/amd64", "--network", "none",
        "--pull=false", "--no-cache", "--build-arg", "PULSE_TWO_SLOT_BASE=" + local_tag,
        "--iidfile", str(original_root / "environment/image-id.txt"), str(original_root / "materials")])
    built = command_record(root, "image-inspect", ["docker", "image", "inspect", image])
    built_info = _image_info(built["stdout"], image)
    expected = {**_environment_map(base_info["Config"]["Env"]), **_environment_map(selected["runtime_environment"])}
    _same(_environment_map(built_info["Config"]["Env"]), expected, "two_slot_hosted_image_environment")
    _same(plan["image_environment"], built_info["Config"]["Env"], "two_slot_hosted_plan_image_environment")
    after = command_record(root, "base-inspect-after", ["docker", "image", "inspect", local_tag])
    after_info = _image_info(after["stdout"], base_id)
    _same(_environment_map(after_info["Config"]["Env"]), _environment_map(base_info["Config"]["Env"]),
          "two_slot_hosted_base_changed")
    return record


def _verify_container(root, ctx, phase, selection, previous=None):
    plan = _json(root / "environment/container-plan.json")
    validate_container_plan(plan, phase, handoff=selection["handoff"])
    _same(plan["selection"], binding(canonical(selection)), "two_slot_hosted_plan_selection")
    _same(plan["context"], ctx, "two_slot_hosted_plan_context")
    _need(plan["image_id"] == selection["image_id"], "two_slot_hosted_plan_image")
    image_record = _verify_environment(root, selection, plan, previous)
    cid = read_regular(root / "environment/container-id.txt", 128).decode("ascii").strip()
    _need(HEX64.fullmatch(cid), "two_slot_hosted_container_id")
    created = command_record(root, "container-create", docker_create_argv(plan))
    _need(created["stdout"].decode("ascii").strip() == cid, "two_slot_hosted_created_id")
    before = command_record(root, "container-inspect", ["docker", "container", "inspect", cid])
    before_info = parse_external(before["stdout"])
    validate_container_identity(before_info, cid, selection["image_id"], ctx, phase, plan)
    before_state = before_info[0].get("State")
    _need(type(before_state) is dict and before_state.get("Status") == "created" and
          before_state.get("Running") is False, "two_slot_hosted_container_prestart")
    command_record(root, "container-start", ["docker", "start", "--attach", cid])
    after = command_record(root, "container-state", ["docker", "container", "inspect", cid])
    after_info = parse_external(after["stdout"])
    item = validate_container_identity(after_info, cid, selection["image_id"], ctx, phase, plan)
    state = item.get("State")
    _need(type(state) is dict and type(state.get("ExitCode")) is int and state["ExitCode"] == 0
          and state.get("Running") is False and state.get("Status") == "exited"
          and state.get("OOMKilled") is False and not state.get("Error")
          and state.get("Restarting", False) is False and state.get("Dead", False) is False,
          "two_slot_hosted_container_exit")
    cleanup = validate_cleanup(root, ctx, phase)
    return {"container_id": cid, "image": image_record, "cleanup": cleanup}


def _expected_native_report(request_id, request, attempt, qualification):
    return {"record_type": "required_gate_idempotence_loader_two_slot_attempt_verification_v0",
        "profile": core.PROFILE, "status": "accepted_native_qualification_attempt",
        "request_id": request_id, "request": request, "attempt": attempt, "qualification": qualification,
        "evidence_origin": "native_owned_probe", "producer_invocations": 1,
        "request_binding_verified": True, "attempt_binding_verified": True,
        "qualification_binding_verified": True, "selected_context_binding_verified": True,
        "source_inventory_verified": True, "qualification_record_state": "completed",
        "qualification_error": None, "complete_mechanics_verified": True, "native_record_reconstructed": True,
        "scripted_record_reconstructed": False, "incomplete_attempt_preserved": False,
        "accepted_return_events": 9, "post_terminal_resumes": 0, **core.BOUNDARY}


def _verify_reports(root, selection, previous=None):
    phase = selection["phase"]
    location = root / ("observation" if phase == "acquire" else "verification")
    evidence = root / "observation" if phase == "acquire" else Path(previous) / "observation"
    request_bytes = read_regular(evidence / "request.json")
    request = core.parse(request_bytes)
    # Existing data-only request checks need neither the native module nor jsonschema.
    core._request_fields(request)
    request_id = request_identity(selection["context"])
    _need(request["request_id"] == request_id, "two_slot_hosted_request_identity")
    _same(request["expected_context"]["observer"], OBSERVER_BINDING, "two_slot_hosted_observer_binding")
    _same(request["sources"], [{"path": name, **selection["sources"][name]} for name in core.SOURCE_PATHS],
          "two_slot_hosted_request_sources")
    preserved_request, attempt_bytes, qualification_bytes = core.read_attempt_directory(evidence / "attempt")
    _need(preserved_request == request_bytes and qualification_bytes is not None and len(qualification_bytes) > 0,
          "two_slot_hosted_native_evidence")
    attempt = core.parse(attempt_bytes)
    _need(type(attempt) is dict and attempt.get("request_id") == request_id and attempt.get("status") == "completed" and
          attempt.get("phase") == "complete" and attempt.get("failure") is None and
          type(attempt.get("producer_invocations")) is int and attempt["producer_invocations"] == 1 and
          attempt.get("evidence_origin") == "native_owned_probe", "two_slot_hosted_native_attempt")
    _same(attempt.get("boundary"), core.BOUNDARY, "two_slot_hosted_attempt_boundary")
    _same(attempt.get("request"), binding(request_bytes), "two_slot_hosted_attempt_request")
    _same(attempt.get("qualification"), binding(qualification_bytes), "two_slot_hosted_attempt_qualification")
    for key in ("context_before", "context_after"):
        _same(attempt.get(key), request["expected_context"], "two_slot_hosted_attempt_context")
    for key in ("sources_before", "sources_after"):
        _same(attempt.get(key), request["sources"], "two_slot_hosted_attempt_sources")
    expected = _expected_native_report(request_id, binding(request_bytes), binding(attempt_bytes), binding(qualification_bytes))
    inner_root = "/output" if phase == "acquire" else "/input/observation"
    command_directory = ("observation" if phase == "acquire" else "verification") + "/commands"
    if phase == "acquire":
        command_record(root, "probe", [PYTHON, "-I", "-B", "/repo/" + CONFIG + "/run.py", "probe"],
                       directory=command_directory)
    else:
        _need(not any((location / "commands" / ("probe." + suffix)).exists()
              for suffix in ("argv.json", "result.json", "stdout.bin", "stderr.bin")),
              "two_slot_hosted_verifier_probe_forbidden")
    reports = []
    for ordinal in (1, 2):
        label = "attempt-check-" + str(ordinal)
        raw = read_regular(location / (label + ".json"))
        report = core.parse(raw)
        _same(report, expected, "two_slot_hosted_native_report")
        _need(raw == canonical(report), "two_slot_hosted_report_canonical")
        command_record(root, label, [PYTHON, "-I", "-B",
            "/repo/tools/check_required_gate_idempotence_loader_two_slot_attempt_v0.py",
            "--request", inner_root + "/request.json", "--request-sha256", binding(request_bytes)["sha256"],
            "--attempt-directory", inner_root + "/attempt", "--attempt-sha256", binding(attempt_bytes)["sha256"],
            "--output", "/output/" + label + ".json"], directory=command_directory)
        reports.append(raw)
    _need(reports[0] == reports[1], "two_slot_hosted_report_divergence")
    leaf = "acquisition-summary.json" if phase == "acquire" else "verification-summary.json"
    summary = _json(location / leaf)
    validate_summary(summary, phase)
    expected_summary = make_summary(phase, selection, request_bytes=request_bytes, attempt_bytes=attempt_bytes,
        qualification_bytes=qualification_bytes, report_bytes=reports)
    _same(summary, expected_summary, "two_slot_hosted_summary_binding")
    _need(summary["status"] == "completed_native_reconstruction", "two_slot_hosted_summary_incomplete")
    return {"request_id": request_id, "request": binding(request_bytes), "attempt": binding(attempt_bytes),
        "qualification": binding(qualification_bytes), "reports": [binding(raw) for raw in reports],
        "summary": binding(read_regular(location / leaf))}


def _completed_phase(root, ctx, phase, previous=None):
    root = Path(root)
    validate_context(ctx)
    files, _ = inventory(root)
    _need("failure.json" not in files, "two_slot_hosted_recorded_failure")
    opposite = "verification/" if phase == "acquire" else "observation/"
    _need(not any(name.startswith(opposite) for name in files), "two_slot_hosted_cross_phase_output")
    forbidden = ("base-load", "artifact-metadata", "attestation-verify") if phase == "acquire" else ("base-pull", "base-save", "base-tag")
    _need(not any("host-commands/" + label + ".argv.json" in files for label in forbidden),
          "two_slot_hosted_cross_phase_command")
    sources = _verify_sources(root, ctx, phase)
    raw = read_regular(root / "control/hosted-selection.json")
    selection = validate_selection(parse(raw), phase)
    _need(raw == canonical(selection), "two_slot_hosted_selection_canonical")
    _same(selection["context"], ctx, "two_slot_hosted_selection_context")
    _same(selection["sources"], sources, "two_slot_hosted_selection_sources")
    runtime = _verify_container(root, ctx, phase, selection, previous)
    mechanics = _verify_reports(root, selection, previous)
    return {"selection": selection, "runtime": runtime, "mechanics": mechanics}


def verify_completed_acquisition(root, ctx, receipt=None):
    if receipt is not None:
        raw = canonical(receipt)
        receipt = verify_preservation(root, raw, binding(raw)["sha256"], ctx)
        _need(receipt["phase"] == "acquire" and receipt["status"] == "completed_native_reconstruction",
              "two_slot_hosted_incomplete_prefix")
    checked = _completed_phase(root, ctx, "acquire")
    return {"record_type": "required_gate_idempotence_loader_two_slot_hosted_acquisition_verification_v0",
        "profile": PROFILE, "status": "completed_native_reconstruction", "context": ctx,
        "image_id": checked["selection"]["image_id"], "container_id": checked["runtime"]["container_id"],
        "selection": binding(canonical(checked["selection"])), "cleanup": checked["runtime"]["cleanup"],
        **checked["mechanics"], "boundary": dict(BOUNDARY)}


def make_verified_binding(root, previous, ctx, selected_handoff, receipt):
    """Join preserved acquisition and independent replay; never run either here."""
    validate_handoff(selected_handoff)
    receipt_raw = read_regular(Path(previous) / "receipt.json")
    _need(binding(receipt_raw)["sha256"] == selected_handoff["receipt_sha256"],
          "two_slot_hosted_external_receipt_digest")
    validated = verify_preservation(previous, receipt_raw, selected_handoff["receipt_sha256"], ctx)
    _same(receipt, validated, "two_slot_hosted_receipt_selection")
    _same(_json(Path(root) / "prefix-verification.json"), {
        "record_type": "required_gate_idempotence_loader_two_slot_hosted_prefix_verification_v0",
        "profile": PROFILE, "context": ctx, "handoff": selected_handoff, "receipt": binding(receipt_raw),
        "preserved_file_count": validated["file_count"] + 1, "all_preserved_bytes_verified": True,
        "preservation_is_qualification_acceptance": False, "status": "preserved_prefix_verified",
        "error_code": None, "boundary": BOUNDARY}, "two_slot_hosted_verified_prefix")
    acquisition = verify_completed_acquisition(previous, ctx, validated)
    checked = _completed_phase(root, ctx, "verify", previous)
    _same(checked["selection"]["handoff"], selected_handoff, "two_slot_hosted_verification_handoff")
    metadata = command_record(root, "artifact-metadata", ["gh", "api", "repos/" + REPOSITORY +
        "/actions/artifacts/" + str(selected_handoff["artifact_id"])])
    validate_artifact_metadata(parse_external(metadata["stdout"]), ctx, selected_handoff)
    for key in ("request_id", "request", "attempt", "qualification", "reports"):
        _same(checked["mechanics"][key], acquisition[key], "two_slot_hosted_independent_report_join")
    for ordinal in (1, 2):
        _need(read_regular(Path(root) / "verification" / ("attempt-check-" + str(ordinal) + ".json")) ==
              read_regular(Path(previous) / "observation" / ("attempt-check-" + str(ordinal) + ".json")),
              "two_slot_hosted_independent_report_bytes")
    return {"record_type": "required_gate_idempotence_loader_two_slot_hosted_verified_binding_v0",
        "profile": PROFILE, "status": "completed_native_reconstruction", "context": ctx,
        "handoff": selected_handoff, "receipt": binding(receipt_raw),
        "sources": checked["selection"]["sources"], "environment": ENVIRONMENT_BINDING,
        "acquisition_image_id": acquisition["image_id"], "verification_image_id": checked["selection"]["image_id"],
        "acquisition_selection": acquisition["selection"], "verification_selection": binding(canonical(checked["selection"])),
        "acquisition_cleanup": acquisition["cleanup"], "verification_cleanup": checked["runtime"]["cleanup"],
        "request_id": acquisition["request_id"], "request": acquisition["request"], "attempt": acquisition["attempt"],
        "qualification": acquisition["qualification"], "reports": acquisition["reports"],
        "acquisition_summary": acquisition["summary"], "verification_summary": checked["mechanics"]["summary"],
        "artifact_metadata": binding(metadata["stdout"]), "independent_reconstruction_count": 2,
        "image_reproducibility_claimed": False, "boundary": dict(BOUNDARY)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-directory", required=True, type=Path)
    parser.add_argument("--receipt-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--require-completed", action="store_true")
    args = parser.parse_args(argv)
    try:
        ctx = context()
        raw = read_regular(args.input_directory / "receipt.json")
        receipt = verify_preservation(args.input_directory, raw, args.receipt_sha256, ctx)
        report = {"record_type": PREFIX_TYPE, "profile": PROFILE, "status": "preserved_prefix_verified",
            "context": ctx, "receipt": binding(raw), "file_count": receipt["file_count"],
            "total_size_bytes": receipt["total_size_bytes"], "completion_verified": False, "boundary": dict(BOUNDARY)}
        if args.require_completed:
            report = verify_completed_acquisition(args.input_directory, ctx, receipt)
        write_new(args.output, report)
        return 0 if args.require_completed else 1
    except (OSError, ValueError, KeyError, TypeError, IndexError, OverflowError, RecursionError) as exc:
        code = getattr(exc, "code", "two_slot_hosted_verification_io")
        sys.stderr.write(code + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Carry the fixed exec-stop experiment through one owner-requested GitHub run.

The hosted bridge preserves transport, build, process and verification evidence.
It delegates the original observation and reconstruction to the unchanged
collector/checker. Docker policy is retained, and an incomplete observation
remains incomplete even when its preserved record reconstructs successfully.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
import required_gate_idempotence_exec_stop_hosted_io_v0 as io

ROOT = Path(__file__).resolve().parents[1]
PROFILE = "linux_x86_64_original_launcher_exec_stop_v0"
ACKNOWLEDGEMENT = "OBSERVE_ORIGINAL_LAUNCHER_EXEC_STOP_ONLY"
REPOSITORY = "HKati/pulse-release-gates-0.1"
WORKFLOW = ".github/workflows/required_gate_idempotence_exec_stop_v0.yml"
CONFIG = "tools/required_gate_idempotence_exec_stop_hosted_v0"
ENVIRONMENT_SHA256 = "d3c5e2eb959a11cef0be689f8bde3fdba36a9708df1114ae8ef278db4be1f593"
ORIGINAL_SHA256 = "16c541b8fd733dcef1b495b104b5377d11624b6106fbfa740e5ec6eb856cdfaa"
FILE_LIMIT = 256 * 1024 * 1024
TOTAL_LIMIT = 512 * 1024 * 1024
FILE_COUNT_LIMIT = 1024
CONTROL_LIMIT = 2 * 1024 * 1024
STAGE_SECONDS = 1200
STAGE_DEADLINE = None
NARROW_FLAGS = (
    "kernel_exec_checkpoint_observed", "launcher_image_binding_verified",
    "interpreter_image_binding_verified", "selected_exec_memory_ranges_observed",
    "selected_exec_rx_ranges_match_original", "owned_exec_stop_cleanup_verified",
)
CONFIG_FILES = ("Dockerfile", "environment.json", "requirements.lock", "build_environment.py")
CORE_SOURCES = (
    "schemas/required_gate_idempotence_mapping_observation_v0.schema.json",
    "tools/check_required_gate_idempotence_mapping_observation_v0.py",
    "tools/required_gate_idempotence_mapping_observation_v0.py",
    "tools/required_gate_idempotence_mapping_probe_v0.py",
    "schemas/required_gate_idempotence_exec_stop_v0.schema.json",
    "tools/check_required_gate_idempotence_exec_stop_v0.py",
    "tools/required_gate_idempotence_exec_stop_v0.py",
    "tools/required_gate_idempotence_launch_host_v0.py",
    "tools/required_gate_idempotence_launcher_distribution_v0.py",
    "tools/prepare_required_gate_idempotence_exec_stop_v0.py",
)
HOSTED_SOURCES = (WORKFLOW, io.SELECTION_REL,
    "tools/required_gate_idempotence_exec_stop_hosted_v0.py",
    "tools/required_gate_idempotence_exec_stop_hosted_io_v0.py",
    "tools/required_gate_idempotence_exec_stop_hosted_run_v0.py",
    *(CONFIG + "/" + name for name in CONFIG_FILES))
BOUNDARY = {
    "host_environment_qualified": False, "physical_execution_authenticated": False,
    "complete_native_closure_verified": False, "containment_enforced": False,
    "execution_ready": False, "execution_authorized": False,
    "selected_runtime_executed": False, "production_gate_eligible": False,
    "metric_pass": None, "authority_effect": "none",
}
RUNTIME = {
    "user": "invoking_runner_uid_gid", "network": "none", "cap_drop": ["ALL"],
    "no_new_privileges": True, "default_seccomp": True, "default_apparmor": True,
    "read_only": True, "pids_limit": 64, "memory": "1g", "cpus": "1",
    "tmpfs_tmp": "rw,nosuid,nodev,size=64m",
}


def _need(condition, code):
    if not condition:
        raise io.HostedIOError(code)


def _pairs(items):
    result = {}
    for key, value in items:
        _need(key not in result, "hosted_duplicate_key")
        result[key] = value
    return result


def parse(raw):
    def constant(_value):
        raise io.HostedIOError("hosted_nonfinite_json")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=constant)


def _json(path, limit=CONTROL_LIMIT):
    return parse(io.read_regular(Path(path), limit))


def _write_json(path, value):
    io.write_new(Path(path), io.canonical(value))


def _mkdir(path):
    Path(path).mkdir(mode=0o700)


def _path(name):
    _need(type(name) is str and name and "\\" not in name
          and all(32 < ord(ch) < 127 for ch in name), "hosted_relative_path")
    path = PurePosixPath(name)
    _need(not path.is_absolute() and path.as_posix() == name
          and all(part not in {"", ".", ".."} for part in path.parts), "hosted_relative_path")
    return path


def _binding(value):
    _need(type(value) is dict and set(value) == {"sha256", "size_bytes"}, "hosted_binding_shape")
    _need(type(value["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", value["sha256"]),
          "hosted_binding_digest")
    _need(type(value["size_bytes"]) is int and 0 <= value["size_bytes"] <= FILE_LIMIT,
          "hosted_binding_size")


def _remaining(requested):
    remaining = requested if STAGE_DEADLINE is None else min(requested, STAGE_DEADLINE - time.monotonic())
    _need(remaining > 0, "hosted_stage_deadline")
    return remaining


def context(environ=None):
    env = os.environ if environ is None else environ
    expected = env.get("EXPECTED_SOURCE_COMMIT", "")
    _need(re.fullmatch(r"[0-9a-f]{40}", expected) is not None, "hosted_source_commit")
    required = {
        "GITHUB_REPOSITORY": REPOSITORY, "GITHUB_REPOSITORY_ID": "1061766508",
        "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF": "refs/heads/main",
        "GITHUB_ACTOR": "HKati", "GITHUB_TRIGGERING_ACTOR": "HKati",
        "GITHUB_RUN_ATTEMPT": "1", "GITHUB_SHA": expected, "GITHUB_WORKFLOW_SHA": expected,
        "GITHUB_WORKFLOW_REF": REPOSITORY + "/" + WORKFLOW + "@refs/heads/main",
        "EXEC_STOP_ACKNOWLEDGEMENT": ACKNOWLEDGEMENT,
    }
    _need(all(env.get(k) == v for k, v in required.items()), "hosted_owner_context")
    run_id = env.get("GITHUB_RUN_ID", "")
    _need(re.fullmatch(r"[1-9][0-9]{0,19}", run_id) is not None, "hosted_run_id")
    return {
        "repository": REPOSITORY, "repository_id": "1061766508", "source_commit": expected,
        "workflow_sha": expected, "workflow_ref": required["GITHUB_WORKFLOW_REF"],
        "run_id": int(run_id), "run_attempt": 1, "event_name": "workflow_dispatch",
        "ref": "refs/heads/main", "actor": "HKati", "triggering_actor": "HKati",
        "acknowledgement": ACKNOWLEDGEMENT,
    }


def _prefix(root, phase, ctx):
    _need(os.environ.get("EXEC_STOP_PHASE") == phase, "hosted_phase")
    expected = {"format": "required_gate_idempotence_exec_stop_workflow_start_v0", "phase": phase,
                **ctx, "selected_runtime_executed": False, "authority_effect": "none"}
    raw = io.read_regular(root / "workflow-start.json", CONTROL_LIMIT, private=True)
    _need(parse(raw) == expected and io.canonical(expected) == raw, "hosted_workflow_start")


def environment():
    raw = io.read_regular(ROOT / CONFIG / "environment.json", CONTROL_LIMIT)
    _need(io.sha(raw) == ENVIRONMENT_SHA256, "hosted_environment_selection")
    value = parse(raw)
    _need(value["record_type"] == "required_gate_idempotence_exec_stop_hosted_environment_v0"
          and value["profile"] == PROFILE and value["platform"] == "linux/amd64"
          and value["runtime"] == RUNTIME and value["authority_effect"] == "none",
          "hosted_environment_profile")
    _need(value["base_image"]["reference"] == "docker.io/library/python@sha256:"
          + value["base_image"]["manifest_sha256"], "hosted_base_image")
    for group, suffix, host in ((value["debian"]["packages"], ".deb", "deb.debian.org"),
                                (value["python"]["packages"], ".whl", "files.pythonhosted.org")):
        _need(len(group) == 7 and len({item["filename"] for item in group}) == 7,
              "hosted_dependency_roster")
        for item in group:
            path = _path(item["filename"])
            _need(len(path.parts) == 1 and path.name.endswith(suffix), "hosted_dependency_path")
            _binding({k: item[k] for k in ("sha256", "size_bytes")})
            url = urllib.parse.urlsplit(item["url"])
            _need(url.scheme == "https" and url.hostname == host and not url.username
                  and not url.password and url.port is None and not url.query and not url.fragment
                  and url.path.endswith("/" + item["filename"]), "hosted_dependency_url")
    return value


def source_bindings():
    original = io.original_selection()
    historic = {name.removeprefix("verifier-source/"): descriptor
                for name, descriptor in original["files"].items() if name.startswith("verifier-source/")}
    _need(len(historic) == 43, "hosted_historical_source_roster")
    result = {}
    for name in sorted(set(historic) | set(CORE_SOURCES) | set(HOSTED_SOURCES)):
        raw = io.read_regular(ROOT / name, CONTROL_LIMIT)
        actual = io.binding(raw)
        if name in historic:
            _need(actual == historic[name], "hosted_historical_source_changed")
        result[name] = actual
    return result


def _copy_sources(root, bindings):
    target = root / "source"
    _mkdir(target)
    for name, expected in bindings.items():
        destination = target.joinpath(*_path(name).parts)
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        raw = io.read_regular(ROOT / name, CONTROL_LIMIT)
        _need(io.binding(raw) == expected, "hosted_source_changed")
        io.write_new(destination, raw)
    _write_json(root / "source-bindings.json", bindings)


def verify_debian_index(originals, selected):
    descriptor = selected["debian"]["index_binding"]
    raw = io.read_regular(originals / descriptor["path"], FILE_LIMIT)
    _need(io.binding(raw) == {k: descriptor[k] for k in ("sha256", "size_bytes")},
          "hosted_debian_index_binding")
    wanted = {item["name"]: item for item in selected["debian"]["closure"]}
    _need(len(wanted) == len(selected["debian"]["closure"]) == 18, "hosted_debian_closure")
    found = {}
    for paragraph in raw.split(b"\n\n"):
        first = paragraph.split(b"\n", 1)[0]
        if not first.startswith(b"Package: "):
            continue
        name = first[len(b"Package: "):].decode("ascii")
        if name not in wanted:
            continue
        _need(name not in found, "hosted_debian_occurrence")
        fields = {}
        for line in paragraph.splitlines():
            if not line or line[:1] in (b" ", b"\t"):
                continue
            key, sep, value = line.partition(b": ")
            _need(sep and key not in fields, "hosted_debian_field")
            fields[key] = value
        item = wanted[name]
        checks = {b"Version": item["version"], b"Architecture": item["architecture"],
                  b"Filename": item["index_filename"], b"SHA256": item["sha256"],
                  b"Size": str(item["size_bytes"])}
        _need(all(fields.get(k, b"").decode("ascii") == v for k, v in checks.items()),
              "hosted_debian_package_binding")
        found[name] = checks[b"SHA256"]
    _need(set(found) == set(wanted), "hosted_debian_package_missing")
    return {"selected_index": io.binding(raw), "package_occurrences": found,
            "fresh_signature_verification": "required_later_by_original_adapter"}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        raise io.HostedIOError("hosted_download_redirect")


def download(item, destination):
    expected = {k: item[k] for k in ("sha256", "size_bytes")}
    deadline = time.monotonic() + _remaining(120)
    raw = bytearray()
    request = urllib.request.Request(item["url"], headers={"User-Agent": "PULSEmech-exec-stop-v0"})
    try:
        with urllib.request.build_opener(_NoRedirect()).open(request, timeout=min(30, _remaining(30))) as response:
            _need(response.status == 200 and response.geturl() == item["url"], "hosted_download_status")
            while len(raw) <= expected["size_bytes"]:
                _need(time.monotonic() < deadline, "hosted_download_deadline")
                part = response.read(min(65536, expected["size_bytes"] + 1 - len(raw)))
                if not part:
                    break
                raw.extend(part)
    finally:
        # Preserve a bounded substitution or interrupted prefix without installing it.
        io.write_new(destination, bytes(raw))
    _need(io.binding(bytes(raw)) == expected, "hosted_download_binding")


def _materials(root, selected, previous=None):
    target = root / "materials"
    _mkdir(target)
    for name in CONFIG_FILES:
        raw = io.read_regular(ROOT / CONFIG / name, CONTROL_LIMIT)
        io.write_new(target / name, raw)
    for subdir, items in (("debs", selected["debian"]["packages"]),
                          ("wheels", selected["python"]["packages"])):
        _mkdir(target / subdir)
        for item in items:
            destination = target / subdir / item["filename"]
            if previous is None:
                download(item, destination)
            else:
                raw = io.read_regular(previous / "materials" / subdir / item["filename"], FILE_LIMIT)
                _need(io.binding(raw) == {k: item[k] for k in ("sha256", "size_bytes")},
                      "hosted_preserved_dependency_binding")
                io.write_new(destination, raw)
    return target


def _command(root, label, argv, timeout=120, require=True, env=None, *, stdout_cap=None, cleanup=False):
    logs = root / "host-commands"
    logs.mkdir(mode=0o700, exist_ok=True)
    result = io.run_command(argv, logs, label, timeout_seconds=timeout if cleanup else _remaining(timeout),
                            env=env, stdout_cap=stdout_cap)
    if require:
        _need(result["failure"] is None and result["returncode"] == 0, "hosted_" + label.replace("-", "_") + "_failed")
    return result


def _command_json(root, label, argv, timeout=120):
    _command(root, label, argv, timeout)
    return _json(root / "host-commands" / (label + ".stdout.bin"), 4 * 1024 * 1024)


def _build_image(root, selected, materials, previous=None):
    image_root = root / "environment"
    _mkdir(image_root)
    _command(root, "docker-version", ["docker", "version", "--format", "{{json .}}"])
    _command(root, "docker-info", ["docker", "info", "--format", "{{json .}}"])
    base = selected["base_image"]["reference"]
    base_id = "sha256:" + selected["base_image"]["config_sha256"]
    local_tag = "localhost/pulse-exec-stop-base:" + selected["base_image"]["config_sha256"]
    if previous is None:
        _command(root, "docker-pull", ["docker", "pull", "--platform", "linux/amd64", base], 300)
        inspect_name = base
    else:
        # The external receipt and whole-file roster were verified before this
        # load. No registry lookup or dependency download occurs in this phase.
        saved_path = previous / "host-commands/base-save.stdout.bin"
        saved = io.read_regular(saved_path, FILE_LIMIT)
        saved_result = _json(previous / "host-commands/base-save.result.json")
        _need(saved_result.get("returncode") == 0 and saved_result.get("failure") is None
              and saved_result.get("stdout") == io.binding(saved)
              and saved_result.get("argv") == ["docker", "image", "save", local_tag],
              "hosted_preserved_base_archive")
        _command(root, "base-load", ["docker", "image", "load", "--input", str(saved_path)], 300)
        inspect_name = local_tag
    inspected = _command_json(root, "base-inspect", ["docker", "image", "inspect", inspect_name])
    _need(type(inspected) is list and len(inspected) == 1, "hosted_base_inspect")
    base_info = inspected[0]
    _need(base_info["Id"] == base_id
          and base_info["Architecture"] == "amd64" and base_info["Os"] == "linux",
          "hosted_base_identity")
    if previous is None:
        _command(root, "base-tag", ["docker", "image", "tag", base_id, local_tag])
        _command(root, "base-save", ["docker", "image", "save", local_tag], 300, stdout_cap=FILE_LIMIT)
        archive_binding = io.binding(io.read_regular(root / "host-commands/base-save.stdout.bin", FILE_LIMIT))
    else:
        archive_binding = io.binding(saved)
    tagged = _command_json(root, "base-tag-inspect", ["docker", "image", "inspect", local_tag])
    _need(type(tagged) is list and len(tagged) == 1 and tagged[0]["Id"] == base_id,
          "hosted_base_tag_identity")
    iidfile = image_root / "image-id.txt"
    _need(not iidfile.exists(), "hosted_image_id_exists")
    _command(root, "docker-build", ["docker", "build", "--platform", "linux/amd64", "--network", "none",
                                     "--pull=false", "--no-cache", "--build-arg", "PULSE_EXEC_STOP_BASE=" + local_tag,
                                     "--iidfile", str(iidfile), str(materials)], 600)
    image_id = io.read_regular(iidfile, 128).decode("ascii").strip()
    _need(re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is not None, "hosted_image_id")
    built = _command_json(root, "image-inspect", ["docker", "image", "inspect", image_id])
    _need(type(built) is list and len(built) == 1 and built[0]["Id"] == image_id
          and built[0]["Architecture"] == "amd64" and built[0]["Os"] == "linux", "hosted_built_image")
    after = _command_json(root, "base-after", ["docker", "image", "inspect", local_tag])
    _need(type(after) is list and len(after) == 1 and after[0]["Id"] == base_id,
          "hosted_base_changed")
    _write_json(image_root / "selection.json", {
        "base_image": selected["base_image"], "constructed_image_id": image_id,
        "base_archive": archive_binding, "base_loaded_from_preserved_bytes": previous is not None,
        "base_local_build_tag": local_tag,
        "environment_selection": io.binding(io.read_regular(ROOT / CONFIG / "environment.json", CONTROL_LIMIT)),
        "build_inputs_fixed": True, "image_reproducibility_claimed": False, **BOUNDARY})
    return image_id


def docker_create_args(image_id, ctx, originals, output, *, phase, previous=None, uid=None, gid=None):
    uid = os.getuid() if uid is None else uid
    gid = os.getgid() if gid is None else gid
    _need(type(uid) is int and type(gid) is int and uid > 0 and gid > 0, "hosted_nonroot_user")
    _need(phase in {"acquire", "verify"} and (previous is not None) == (phase == "verify"), "hosted_container_phase")
    _need(re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is not None, "hosted_image_id")
    name = "pulse-exec-stop-" + str(ctx["run_id"]) + "-1-" + phase
    for path in (ROOT, originals, output, *((previous,) if previous is not None else ())):
        _need(Path(path).is_absolute() and "," not in str(path) and "\n" not in str(path), "hosted_mount_path")
    args = ["docker", "create", "--name", name, "--platform", "linux/amd64",
            "--user", str(uid) + ":" + str(gid), "--read-only", "--network", "none",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--pids-limit", "64", "--memory", "1g", "--cpus", "1",
            "--tmpfs", "/tmp:rw,nosuid,nodev,size=64m", "--workdir", "/repo",
            "--label", "org.pulsemech.exec-stop.run=" + str(ctx["run_id"]),
            "--label", "org.pulsemech.exec-stop.source=" + ctx["source_commit"],
            "--mount", "type=bind,source=" + str(ROOT) + ",target=/repo,readonly",
            "--mount", "type=bind,source=" + str(originals) + ",target=/originals,readonly",
            "--mount", "type=bind,source=" + str(output) + ",target=/output"]
    if previous is not None:
        args += ["--mount", "type=bind,source=" + str(previous) + ",target=/input,readonly"]
    env = {
        "EXPECTED_SOURCE_COMMIT": ctx["source_commit"], "EXEC_STOP_ACKNOWLEDGEMENT": ACKNOWLEDGEMENT,
        "GITHUB_REPOSITORY": REPOSITORY, "GITHUB_REPOSITORY_ID": ctx["repository_id"],
        "GITHUB_SHA": ctx["source_commit"], "GITHUB_WORKFLOW_SHA": ctx["workflow_sha"],
        "GITHUB_WORKFLOW_REF": ctx["workflow_ref"], "GITHUB_RUN_ID": str(ctx["run_id"]),
        "GITHUB_RUN_ATTEMPT": "1", "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF": "refs/heads/main",
        "GITHUB_ACTOR": "HKati", "GITHUB_TRIGGERING_ACTOR": "HKati", "EXEC_STOP_PHASE": phase,
        "EXEC_STOP_IMAGE_ID": image_id, "PYTHONDONTWRITEBYTECODE": "1", "LC_ALL": "C", "TZ": "UTC",
    }
    for key, value in sorted(env.items()):
        args += ["--env", key + "=" + value]
    args += ["--entrypoint", "/usr/local/bin/python3.11", image_id, "-I", "-B",
             "/repo/tools/required_gate_idempotence_exec_stop_hosted_run_v0.py", phase]
    return args


def _container(root, selected, image_id, ctx, originals, phase, previous=None):
    output = root / ("observation" if phase == "acquire" else "verification")
    _mkdir(output)
    argv = docker_create_args(image_id, ctx, originals, output, phase=phase, previous=previous)
    _command(root, "container-create", argv)
    container_id = io.read_regular(root / "host-commands/container-create.stdout.bin", 128).decode("ascii").strip()
    _need(re.fullmatch(r"[0-9a-f]{64}", container_id) is not None, "hosted_container_id")
    started = None
    cleanup_ok = False
    try:
        info = _command_json(root, "container-before", ["docker", "container", "inspect", container_id])
        _need(type(info) is list and len(info) == 1 and info[0]["Id"] == container_id,
              "hosted_container_identity")
        host_config = info[0]["HostConfig"]
        config = info[0]["Config"]
        _need(info[0]["Image"] == image_id and host_config["Privileged"] is False
              and host_config["ReadonlyRootfs"] is True and host_config["NetworkMode"] == "none"
              and host_config["CapDrop"] == ["ALL"] and not host_config.get("CapAdd")
              and host_config["SecurityOpt"] in (["no-new-privileges"], ["no-new-privileges=true"])
              and config["User"] == str(os.getuid()) + ":" + str(os.getgid())
              and host_config["PidsLimit"] == 64 and host_config["Memory"] == 1024**3
              and host_config["NanoCpus"] == 10**9
              and host_config["Tmpfs"] == {"/tmp": "rw,nosuid,nodev,size=64m"},
              "hosted_container_policy")
        started = _command(root, "container-start", ["docker", "start", "--attach", container_id], 1200, require=False)
        _command(root, "container-after", ["docker", "container", "inspect", container_id], 30, cleanup=True)
        after = _json(root / "host-commands/container-after.stdout.bin", 4 * 1024 * 1024)
        _need(len(after) == 1 and after[0]["Id"] == container_id, "hosted_container_identity")
        if after[0]["State"]["Running"]:
            _command(root, "container-kill", ["docker", "kill", "--signal", "KILL", container_id], 30, cleanup=True)
            _need(False, "hosted_container_still_running")
        _need(type(after[0]["State"]["ExitCode"]) is int and after[0]["State"]["ExitCode"] == 0
              and after[0]["State"].get("Status") == "exited"
              and after[0]["State"].get("OOMKilled") is False
              and not after[0]["State"].get("Error"), "hosted_container_exit")
    finally:
        result = _command(root, "container-remove", ["docker", "rm", "--force", container_id], 30,
                          require=False, cleanup=True)
        cleanup_ok = result["returncode"] == 0 and result["failure"] is None
        _write_json(root / "environment/container-cleanup.json", {
            "container_id": container_id, "owned_container_removed": cleanup_ok, **BOUNDARY})
    _need(cleanup_ok, "hosted_container_cleanup")
    _need(started is not None and started["returncode"] == 0 and started["failure"] is None,
          "hosted_observation_incomplete" if phase == "acquire" else "hosted_verification_incomplete")
    return output


def inventory(root):
    files, total = {}, 0
    for path in sorted(root.rglob("*")):
        before = path.lstat()
        _need(not stat.S_ISLNK(before.st_mode), "hosted_inventory_symlink")
        if stat.S_ISDIR(before.st_mode):
            continue
        _need(stat.S_ISREG(before.st_mode), "hosted_inventory_nonregular")
        name = path.relative_to(root).as_posix()
        _path(name)
        _need(name != "receipt.json", "hosted_receipt_exists")
        raw = io.read_regular(path, FILE_LIMIT)
        files[name] = io.binding(raw)
        total += len(raw)
        _need(total <= TOTAL_LIMIT and len(files) <= FILE_COUNT_LIMIT, "hosted_inventory_limit")
    return files, total


def acquire(root, ctx):
    _prefix(root, "acquire", ctx)
    selected = environment()
    sources = source_bindings()
    _copy_sources(root, sources)
    archive = io.original_selection()["archive"]
    raw = io.read_regular(ROOT / archive["path"], FILE_LIMIT)
    _need(io.binding(raw) == {k: archive[k] for k in ("sha256", "size_bytes")}, "hosted_original_archive")
    io.write_new(root / "original_inputs.zip", raw)
    work = root.parent / (root.name + "-work")
    _mkdir(work)
    io.extract_originals(root / "original_inputs.zip", work / "originals")
    _write_json(root / "debian-index-selection.json", verify_debian_index(work / "originals", selected))
    materials = _materials(root, selected)
    image_id = _build_image(root, selected, materials)
    output = _container(root, selected, image_id, ctx, work / "originals", "acquire")
    summary = _json(output / "acquisition-summary.json")
    _need(summary.get("observation_complete") is True and summary.get("status") == "completed"
          and io.canonical(summary.get("context")) == io.canonical(ctx)
          and all(summary.get(key) is True for key in NARROW_FLAGS), "hosted_observation_incomplete")
    _need(source_bindings() == sources, "hosted_source_changed")
    return 0


def finalize(root, ctx):
    _prefix(root, "acquire", ctx)
    files, total = inventory(root)
    sources = source_bindings()
    source_complete = all(files.get("source/" + name) == value for name, value in sources.items())
    request = files.get("observation/request.json")
    capture = files.get("observation/capture/capture.json")
    record = {
        "record_type": "required_gate_idempotence_exec_stop_hosted_receipt_v0", "profile": PROFILE,
        "context": ctx, "files": files, "file_count": len(files), "total_size_bytes": total,
        "source_bindings": sources, "source_prefix_complete": source_complete,
        "request": request, "capture": capture, "preservation_is_observation_acceptance": False,
        **BOUNDARY,
    }
    raw = io.canonical(record)
    io.write_new(root / "receipt.json", raw)
    result = {"receipt_sha256": io.sha(raw), "request_sha256": request["sha256"] if request else "",
              "capture_sha256": capture["sha256"] if capture else ""}
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as stream:
            for name, value in result.items():
                stream.write(name + "=" + value + "\n")
    print(io.canonical(result).decode(), end="")
    return 0


def validate_receipt(raw, expected_sha256, ctx):
    _need(re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is not None
          and io.sha(raw) == expected_sha256, "hosted_receipt_digest")
    record = parse(raw)
    required = {"record_type", "profile", "context", "files", "file_count", "total_size_bytes",
                "source_bindings", "source_prefix_complete", "request", "capture",
                "preservation_is_observation_acceptance", *BOUNDARY}
    _need(type(record) is dict and set(record) == required and io.canonical(record) == raw,
          "hosted_receipt_shape")
    _need(record["record_type"] == "required_gate_idempotence_exec_stop_hosted_receipt_v0"
          and record["profile"] == PROFILE and io.canonical(record["context"]) == io.canonical(ctx)
          and record["preservation_is_observation_acceptance"] is False
          and all(type(record[k]) is type(v) and record[k] == v for k, v in BOUNDARY.items()),
          "hosted_receipt_context")
    files = record["files"]
    _need(type(files) is dict and 1 <= len(files) <= FILE_COUNT_LIMIT, "hosted_receipt_inventory")
    total = 0
    for name, value in files.items():
        _path(name)
        _need(name != "receipt.json", "hosted_receipt_self_binding")
        _binding(value)
        total += value["size_bytes"]
    _need(type(record["file_count"]) is int and record["file_count"] == len(files)
          and type(record["total_size_bytes"]) is int and record["total_size_bytes"] == total
          and total <= TOTAL_LIMIT, "hosted_receipt_total")
    expected_sources = source_bindings()
    _need(record["source_bindings"] == expected_sources, "hosted_receipt_sources")
    complete = all(files.get("source/" + name) == value for name, value in expected_sources.items())
    _need(type(record["source_prefix_complete"]) is bool and record["source_prefix_complete"] == complete,
          "hosted_source_prefix")
    _need(record["request"] == files.get("observation/request.json")
          and record["capture"] == files.get("observation/capture/capture.json"), "hosted_receipt_subjects")
    return record


def verify(root, source, expected_receipt_sha256, ctx):
    _prefix(root, "verify", ctx)
    _need(re.fullmatch(r"[1-9][0-9]{0,19}", os.environ.get("EXEC_STOP_ARTIFACT_ID", "")) is not None,
          "hosted_artifact_id")
    _need(os.environ.get("EXPECTED_RECEIPT_SHA256") == expected_receipt_sha256, "hosted_receipt_selection")
    raw = io.read_regular(source / "receipt.json", CONTROL_LIMIT)
    record = validate_receipt(raw, expected_receipt_sha256, ctx)
    expected_files = {**record["files"], "receipt.json": io.binding(raw)}
    previous = root / "private-input"
    io.copy_private_tree(source, previous, expected_files)
    _write_json(root / "receipt-verification.json", {
        "status": "accepted", "context": ctx, "receipt": io.binding(raw),
        "artifact_id": int(os.environ["EXEC_STOP_ARTIFACT_ID"]),
        "preserved_file_count": len(expected_files), "all_preserved_bytes_verified": True,
        "observation_complete": False, **BOUNDARY})
    # Even an early failed build has a checkable prefix. It cannot proceed to
    # an image build or claim an original checkpoint without its capture.
    _need(record["source_prefix_complete"] and record["request"] is not None
          and record["capture"] is not None, "hosted_capture_not_published")
    selected = environment()
    sources = source_bindings()
    _copy_sources(root, sources)
    work = root.parent / (root.name + "-work")
    _mkdir(work)
    io.extract_originals(previous / "original_inputs.zip", work / "originals")
    _write_json(root / "debian-index-selection.json", verify_debian_index(work / "originals", selected))
    materials = _materials(root, selected, previous)
    image_id = _build_image(root, selected, materials, previous)
    output = _container(root, selected, image_id, ctx, work / "originals", "verify", previous)
    summary = _json(output / "verification-summary.json")
    _need(summary.get("observation_complete") is True and summary.get("status") == "completed"
          and io.canonical(summary.get("context")) == io.canonical(ctx)
          and all(summary.get(key) is True for key in NARROW_FLAGS),
          "hosted_verification_incomplete")
    one = io.read_regular(output / "capture-check-1.json", CONTROL_LIMIT)
    two = io.read_regular(output / "capture-check-2.json", CONTROL_LIMIT)
    report = parse(one)
    _need(one == two and io.canonical(report) == one and report.get("status") == "accepted"
          and report.get("observation_complete") is True
          and all(report.get(key) is True for key in NARROW_FLAGS), "hosted_report_disagreement")
    _need(source_bindings() == sources, "hosted_source_changed")
    verified = {
        "record_type": "required_gate_idempotence_exec_stop_hosted_verified_binding_v0", "profile": PROFILE,
        "status": "accepted", "context": ctx, "artifact_id": int(os.environ["EXEC_STOP_ARTIFACT_ID"]),
        "original_receipt": io.binding(raw), "request": record["request"], "capture": record["capture"],
        "source_bindings": sources, "first_report": io.binding(one), "second_report": io.binding(two),
        "canonical_reports_byte_identical": True, "observation_complete": True,
        "verification_acquisition_repeated": False, "verification_image_id": image_id, **BOUNDARY,
    }
    _write_json(root / "verified-binding.json", verified)
    return 0


def attest_verify(root, bundle, ctx):
    _prefix(root, "verify", ctx)
    subject = root / "verified-binding.json"
    raw = io.read_regular(subject, CONTROL_LIMIT)
    value = parse(raw)
    _need(io.canonical(value.get("context")) == io.canonical(ctx) and value.get("status") == "accepted"
          and value.get("observation_complete") is True, "hosted_attestation_subject")
    bundle_raw = io.read_regular(bundle, 16 * 1024 * 1024)
    io.write_new(root / "attestation.bundle.json", bundle_raw)
    _write_json(root / "attestation-identity.json", {
        "record_type": "required_gate_idempotence_exec_stop_attestation_identity_v0", "context": ctx,
        "subject": io.binding(raw), "bundle": io.binding(bundle_raw),
        "attestation_id": os.environ.get("EXEC_STOP_ATTESTATION_ID", ""),
        "attestation_url": os.environ.get("EXEC_STOP_ATTESTATION_URL", ""), **BOUNDARY})
    result = _command(root, "attestation-verify", [
        "gh", "attestation", "verify", str(subject), "--bundle", str(root / "attestation.bundle.json"),
        "--repo", REPOSITORY, "--signer-workflow", REPOSITORY + "/" + WORKFLOW,
        "--signer-digest", ctx["workflow_sha"], "--source-digest", ctx["source_commit"],
        "--source-ref", "refs/heads/main", "--predicate-type", "https://slsa.dev/provenance/v1",
        "--cert-oidc-issuer", "https://token.actions.githubusercontent.com",
        "--deny-self-hosted-runners", "--format", "json"], 120, require=False)
    _need(io.read_regular(subject, CONTROL_LIMIT) == raw, "hosted_attestation_subject_changed")
    _need(io.read_regular(root / "attestation.bundle.json", 16 * 1024 * 1024) == bundle_raw,
          "hosted_attestation_bundle_changed")
    _need(result["returncode"] == 0 and result["failure"] is None, "hosted_attestation_verification_failed")
    _write_json(root / "attestation-verification.json", {
        "status": "accepted", "context": ctx, "subject": io.binding(raw), "bundle": io.binding(bundle_raw),
        "github_signature_verification_succeeded": True, **BOUNDARY})
    return 0


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("acquire", "finalize", "verify", "attest-verify"):
        command = commands.add_parser(name)
        command.add_argument("--output-directory", type=Path, required=True)
        if name == "verify":
            command.add_argument("--input-directory", type=Path, required=True)
            command.add_argument("--receipt-sha256", required=True)
        elif name == "attest-verify":
            command.add_argument("--bundle", type=Path, required=True)
    return parser


def main(argv=None):
    global STAGE_DEADLINE
    args = _parser().parse_args(argv)
    ctx = None
    try:
        os.umask(0o077)
        ctx = context()
        STAGE_DEADLINE = time.monotonic() + STAGE_SECONDS if args.command in {"acquire", "verify"} else None
        root = args.output_directory.absolute()
        if args.command == "acquire":
            return acquire(root, ctx)
        if args.command == "finalize":
            return finalize(root, ctx)
        if args.command == "verify":
            return verify(root, args.input_directory.absolute(), args.receipt_sha256, ctx)
        return attest_verify(root, args.bundle.absolute(), ctx)
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError) as exc:
        code = getattr(exc, "code", "hosted_stage_failed")
        if not isinstance(code, str) or re.fullmatch(r"[a-z][a-z0-9_]*", code) is None:
            code = "hosted_stage_failed"
        failure = {"record_type": "required_gate_idempotence_exec_stop_hosted_failure_v0",
                   "status": "incomplete", "stage": args.command, "error_code": code,
                   "context": ctx, "observation_complete": False, **BOUNDARY}
        if ctx is not None:
            try:
                _write_json(args.output_directory / (args.command + ".incomplete.json"), failure)
            except (OSError, ValueError):
                pass
        sys.stdout.buffer.write(io.canonical(failure))
        return 1
    finally:
        STAGE_DEADLINE = None


if __name__ == "__main__":
    raise SystemExit(main())

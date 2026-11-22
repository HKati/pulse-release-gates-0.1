#!/usr/bin/env python3
"""Preserve one explicitly requested, synthetic two-slot qualification run.

The host controls byte transport and an owned Docker container.  Native
qualification remains in the unchanged #3048/#3049 producer and adapter; the
separate checker reconstructs preserved bytes without executing that producer.
A diagnostic prefix is preserved even when it cannot become a completed
qualification binding.  No original launcher, input archive or payload is used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import signal
import stat
import sys
import tempfile
import time
import urllib.parse
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
import required_gate_idempotence_exec_stop_hosted_io_v0 as io
import check_required_gate_idempotence_loader_two_slot_attempt_v0 as attempt_checker
import check_required_gate_idempotence_loader_two_slot_hosted_v0 as checker

ROOT = Path(__file__).resolve().parents[1]
PROFILE = "linux_x86_64_loader_two_slot_hosted_v0"
REPOSITORY = "HKati/pulse-release-gates-0.1"
WORKFLOW = ".github/workflows/required_gate_idempotence_loader_two_slot_qualification_v0.yml"
CONFIG = "tools/required_gate_idempotence_loader_two_slot_hosted_v0"
CONFIG_FILES = ("Dockerfile", "environment.json", "requirements.lock", "build_environment.py", "run.py")
ACKNOWLEDGEMENT = "QUALIFY_LOADER_TWO_SLOT_ONLY"
PYTHON = "/usr/local/bin/python3.11"
FILE_LIMIT = 256 * 1024 * 1024
TOTAL_LIMIT = 512 * 1024 * 1024
FILE_COUNT_LIMIT = 256
CONTROL_LIMIT = 65536
SOURCE_LIMIT = 1048576
BUNDLE_LIMIT = 4 * 1024 * 1024
STAGE_SECONDS = 1200
STAGE_DEADLINE = None
BOUNDARY = {**attempt_checker.BOUNDARY, "selected_runtime_executed": False}
IMAGE_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
CID_RE = re.compile(r"[0-9a-f]{64}\Z")
SOURCE_COMMIT_RE = re.compile(r"[0-9a-f]{40}\Z")
SAFE_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
_COMMAND_CLIENT_DIRS = {}


def _need(condition, code):
    if not condition:
        raise io.HostedIOError(code)


def parse(raw):
    """Read closed controls and finite elapsed-time command diagnostics."""
    def pairs(items):
        result = {}
        for name, value in items:
            _need(name not in result, "two_slot_hosted_duplicate_key")
            result[name] = value
        return result

    def constant(_value):
        raise io.HostedIOError("two_slot_hosted_nonfinite_json")

    def finite_float(value):
        parsed = float(value)
        _need(math.isfinite(parsed), "two_slot_hosted_nonfinite_json")
        return parsed

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                          parse_constant=constant, parse_float=finite_float)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise io.HostedIOError("two_slot_hosted_json") from exc


def _json(path, limit=CONTROL_LIMIT):
    return parse(io.read_regular(Path(path), limit))


def _write_json(path, value):
    # Critical controls use #3049's exclusive, re-read and close-hardened
    # publication.  Failed publication cannot leave a valid completed control.
    raw = io.canonical(value)
    _need(len(raw) <= CONTROL_LIMIT, "two_slot_hosted_control_limit")
    attempt_checker.write_new(Path(path), raw)
    return io.binding(raw)


def _mkdir(path):
    Path(path).mkdir(mode=0o700)


def _path(value):
    _need(type(value) is str and value and "\\" not in value
          and all(32 < ord(char) < 127 for char in value), "two_slot_hosted_path")
    result = PurePosixPath(value)
    _need(not result.is_absolute() and result.as_posix() == value
          and all(part not in {"", ".", ".."} for part in result.parts),
          "two_slot_hosted_path")
    return result


def _remaining(requested):
    remaining = requested if STAGE_DEADLINE is None else min(
        requested, STAGE_DEADLINE - time.monotonic())
    _need(remaining > 0, "two_slot_hosted_stage_deadline")
    return remaining


def _success(result):
    if not (type(result) is dict and type(result.get("returncode")) is int
            and result["returncode"] == 0 and result.get("failure") is None
            and result.get("overflowed_streams") == []):
        return False
    cleanup = result.get("cleanup")
    return (type(cleanup) is dict and cleanup.get("child_started") is True
            and cleanup.get("child_reaped") is True and cleanup.get("kill_group_sent") is False
            and cleanup.get("kill_error_errno") is None
            and cleanup.get("pending_output_drain_attempted") is True)


def _command_environment(root):
    # No caller-selected Docker context, remote endpoint, Git config, hooks or
    # proxy is admitted.  The credential used for the final GH verification is
    # explicitly added by that single caller and is never serialized.
    result = {
        "PATH": SAFE_PATH, "LANG": "C.UTF-8", "LC_ALL": "C", "TZ": "UTC",
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_OPTIONAL_LOCKS": "0", "GIT_NO_REPLACE_OBJECTS": "1", "GIT_NO_LAZY_FETCH": "1",
        "DOCKER_HOST": "unix:///var/run/docker.sock",
    }
    key = str(Path(root).absolute())
    if key not in _COMMAND_CLIENT_DIRS:
        # Docker/buildx may retain client state. Keep its new exclusive private
        # directory outside the finite artifact, independently of the runner's
        # existing Docker contexts, credentials and configuration.
        _COMMAND_CLIENT_DIRS[key] = Path(tempfile.mkdtemp(
            prefix=Path(root).name + "-docker-client-", dir=Path(root).parent))
    client = _COMMAND_CLIENT_DIRS[key]
    info = client.lstat()
    _need(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o700
          and info.st_uid == os.geteuid(),
          "two_slot_hosted_client_directory")
    result["DOCKER_CONFIG"] = str(client)
    if "HOME" in os.environ:
        result["HOME"] = os.environ["HOME"]
    return result


def _command(root, label, argv, timeout=120, require=True, env=None, *,
             stdout_cap=None, cleanup=False):
    logs = Path(root) / "host-commands"
    logs.mkdir(mode=0o700, exist_ok=True)
    result = io.run_command(argv, logs, label,
        timeout_seconds=timeout if cleanup else _remaining(timeout),
        env=_command_environment(root) if env is None else env,
        stdout_cap=stdout_cap)
    if require:
        _need(_success(result), "two_slot_hosted_" + label.replace("-", "_") + "_failed")
    return result


def _command_json(root, label, argv, timeout=120, *, cleanup=False):
    _command(root, label, argv, timeout, cleanup=cleanup)
    return _json(Path(root) / "host-commands" / (label + ".stdout.bin"), 4 * 1024 * 1024)


def context(environ=None):
    return checker.context(os.environ if environ is None else environ)


def environment():
    return checker.environment()


def source_bindings():
    return checker.source_bindings()


def _prefix(root, phase, ctx):
    _need(os.environ.get("TWO_SLOT_HOSTED_PHASE") == phase, "two_slot_hosted_phase")
    expected = {"record_type": "required_gate_idempotence_loader_two_slot_workflow_start_v0",
                "phase": phase, "context": ctx, "boundary": dict(BOUNDARY)}
    raw = io.read_regular(Path(root) / "workflow-start.json", CONTROL_LIMIT, private=True)
    _need(parse(raw) == expected and io.canonical(expected) == raw,
          "two_slot_hosted_workflow_start")


def validate_git_source_snapshot(root, ctx, sources):
    """Bind selected regular file bytes to the exact committed Git tree."""
    expected = ctx["source_commit"]
    _need(type(expected) is str and SOURCE_COMMIT_RE.fullmatch(expected),
          "two_slot_hosted_source_commit")
    _need(set(sources) == set(checker.SOURCE_PATHS), "two_slot_hosted_source_roster")
    prefix = ["git", "--no-pager", "-c", "core.fsmonitor=false", "-c",
              "core.hooksPath=/dev/null", "-C", str(ROOT)]
    _command(root, "git-head-before", [*prefix, "rev-parse", "--verify", "HEAD"], stdout_cap=128)
    first = io.read_regular(Path(root) / "host-commands/git-head-before.stdout.bin", 128)
    _need(first == (expected + "\n").encode("ascii"), "two_slot_hosted_checkout_head")
    _command(root, "git-source-tree", [*prefix, "ls-tree", "-r", "-z", "--full-tree",
             expected, "--", *sorted(sources)], stdout_cap=CONTROL_LIMIT)
    raw = io.read_regular(Path(root) / "host-commands/git-source-tree.stdout.bin", CONTROL_LIMIT)
    _need(raw.endswith(b"\0"), "two_slot_hosted_git_tree")
    blobs = {}
    for item in raw[:-1].split(b"\0"):
        head, separator, name_bytes = item.partition(b"\t")
        fields = head.split(b" ")
        _need(separator and len(fields) == 3 and fields[0] in {b"100644", b"100755"}
              and fields[1] == b"blob" and re.fullmatch(b"[0-9a-f]{40}", fields[2]),
              "two_slot_hosted_git_blob")
        name = name_bytes.decode("utf-8")
        _path(name)
        _need(name in sources and name not in blobs, "two_slot_hosted_git_roster")
        blobs[name] = fields[2].decode("ascii")
    _need(set(blobs) == set(sources), "two_slot_hosted_git_roster")
    for name, selected in sorted(sources.items()):
        raw = io.read_regular(ROOT / name, SOURCE_LIMIT)
        _need(io.binding(raw) == selected, "two_slot_hosted_source_changed")
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
        _need(blob == blobs[name], "two_slot_hosted_source_not_committed")
    _command(root, "git-head-after", [*prefix, "rev-parse", "--verify", "HEAD"], stdout_cap=128)
    _need(io.read_regular(Path(root) / "host-commands/git-head-after.stdout.bin", 128) == first,
          "two_slot_hosted_checkout_changed")


def _copy_sources(root, sources):
    # Preserve the selected inventory before its copy.  A failed copy retains
    # that original selection; finalization never selects fresh replacement bytes.
    _write_json(Path(root) / "source-bindings.json", sources)
    target = Path(root) / "source"
    _mkdir(target)
    for name, selected in sorted(sources.items()):
        destination = target.joinpath(*_path(name).parts)
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        raw = io.read_regular(ROOT / name, SOURCE_LIMIT)
        _need(io.binding(raw) == selected, "two_slot_hosted_source_changed")
        io.write_new(destination, raw)
    _assert_sources(root, sources)


def _assert_sources(root, sources):
    _need(source_bindings() == sources, "two_slot_hosted_source_changed")
    for name, selected in sources.items():
        _need(io.binding(io.read_regular(Path(root) / "source" / name, SOURCE_LIMIT)) == selected,
              "two_slot_hosted_source_copy_changed")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        raise io.HostedIOError("two_slot_hosted_download_redirect")


def download(item, destination):
    """Download one selected wheel, retaining its bounded failed prefix."""
    expected = {name: item[name] for name in ("sha256", "size_bytes")}
    url = urllib.parse.urlsplit(item["url"])
    _need(url.scheme == "https" and url.hostname == "files.pythonhosted.org"
          and url.port is None and not url.username and not url.password
          and not url.query and not url.fragment
          and url.path.endswith("/" + item["filename"])
          and type(expected["size_bytes"]) is int and 0 < expected["size_bytes"] < SOURCE_LIMIT,
          "two_slot_hosted_download_selection")
    deadline = time.monotonic() + _remaining(120)
    raw = bytearray()
    request = urllib.request.Request(item["url"], headers={"User-Agent": "PULSEmech-two-slot-v0"})
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
        with opener.open(request, timeout=min(30, _remaining(30))) as response:
            _need(response.status == 200 and response.geturl() == item["url"],
                  "two_slot_hosted_download_status")
            while len(raw) <= expected["size_bytes"]:
                _need(time.monotonic() < deadline, "two_slot_hosted_download_deadline")
                piece = response.read(min(65536, expected["size_bytes"] + 1 - len(raw)))
                if not piece:
                    break
                raw.extend(piece)
    finally:
        io.write_new(Path(destination), bytes(raw))
    _need(io.binding(bytes(raw)) == expected, "two_slot_hosted_download_binding")


def _materials(root, selected, previous=None):
    target = Path(root) / "materials"
    _mkdir(target)
    sources = _json(Path(root) / "source-bindings.json")
    for name in CONFIG_FILES:
        relative = CONFIG + "/" + name
        raw = io.read_regular(Path(root) / "source" / relative, SOURCE_LIMIT)
        _need(io.binding(raw) == sources.get(relative), "two_slot_hosted_material_source")
        io.write_new(target / name, raw)
    _mkdir(target / "wheels")
    for item in selected["python"]["packages"]:
        destination = target / "wheels" / item["filename"]
        _need(len(_path(item["filename"]).parts) == 1, "two_slot_hosted_wheel_name")
        if previous is None:
            download(item, destination)
        else:
            raw = io.read_regular(Path(previous) / "materials/wheels" / item["filename"], SOURCE_LIMIT)
            _need(io.binding(raw) == {name: item[name] for name in ("sha256", "size_bytes")},
                  "two_slot_hosted_preserved_wheel")
            io.write_new(destination, raw)
    return target


def _build_image(root, selected, materials, previous=None):
    image_root = Path(root) / "environment"
    _mkdir(image_root)
    base = selected["base_image"]["reference"]
    base_id = "sha256:" + selected["base_image"]["config_sha256"]
    local_tag = "localhost/pulse-two-slot-base:" + selected["base_image"]["config_sha256"]
    if previous is None:
        _command(root, "base-pull", ["docker", "pull", "--platform", "linux/amd64", base], 300)
        inspect_name = base
    else:
        saved_path = Path(previous) / "host-commands/base-save.stdout.bin"
        saved = io.read_regular(saved_path, FILE_LIMIT)
        saved_result = _json(Path(previous) / "host-commands/base-save.result.json")
        _need(_success(saved_result) and saved_result.get("stdout") == io.binding(saved)
              and saved_result.get("argv") == ["docker", "image", "save", local_tag],
              "two_slot_hosted_preserved_base_archive")
        _command(root, "base-load", ["docker", "image", "load", "--input", str(saved_path)], 300)
        inspect_name = local_tag
    inspected = _command_json(root, "base-inspect", ["docker", "image", "inspect", inspect_name])
    _need(type(inspected) is list and len(inspected) == 1 and type(inspected[0]) is dict,
          "two_slot_hosted_base_inspect")
    base_info = inspected[0]
    _need(base_info.get("Id") == base_id and base_info.get("Architecture") == "amd64"
          and base_info.get("Os") == "linux", "two_slot_hosted_base_identity")
    if previous is None:
        _command(root, "base-tag", ["docker", "image", "tag", base_id, local_tag])
        _command(root, "base-save", ["docker", "image", "save", local_tag], 300, stdout_cap=FILE_LIMIT)
        archive_binding = io.binding(io.read_regular(Path(root) / "host-commands/base-save.stdout.bin", FILE_LIMIT))
    else:
        archive_binding = io.binding(saved)
    tagged = _command_json(root, "base-tag-inspect", ["docker", "image", "inspect", local_tag])
    _need(type(tagged) is list and len(tagged) == 1 and tagged[0].get("Id") == base_id,
          "two_slot_hosted_base_tag_identity")
    iidfile = image_root / "image-id.txt"
    _need(not os.path.lexists(iidfile), "two_slot_hosted_image_id_exists")
    _command(root, "image-build", ["docker", "build", "--platform", "linux/amd64", "--network", "none",
        "--pull=false", "--no-cache", "--build-arg", "PULSE_TWO_SLOT_BASE=" + local_tag,
        "--iidfile", str(iidfile), str(materials)], 600)
    image_id = io.read_regular(iidfile, 128).decode("ascii").strip()
    _need(IMAGE_RE.fullmatch(image_id), "two_slot_hosted_image_id")
    built = _command_json(root, "image-inspect", ["docker", "image", "inspect", image_id])
    _need(type(built) is list and len(built) == 1 and built[0].get("Id") == image_id
          and built[0].get("Architecture") == "amd64" and built[0].get("Os") == "linux",
          "two_slot_hosted_constructed_image")
    _need(_env_map(built[0].get("Config", {}).get("Env")) == {
        **_env_map(base_info.get("Config", {}).get("Env")),
        **_env_map(selected["runtime_environment"])}, "two_slot_hosted_image_environment")
    after = _command_json(root, "base-inspect-after", ["docker", "image", "inspect", local_tag])
    _need(type(after) is list and len(after) == 1 and after[0].get("Id") == base_id,
          "two_slot_hosted_base_changed")
    _write_json(image_root / "selection.json", {
        "record_type": "required_gate_idempotence_loader_two_slot_hosted_image_v0",
        "profile": PROFILE, "base_image": selected["base_image"],
        "constructed_image_id": image_id, "base_archive": archive_binding,
        "base_loaded_from_preserved_bytes": previous is not None,
        "base_local_build_tag": local_tag,
        "environment_selection": io.binding(io.read_regular(
            Path(root) / "source" / CONFIG / "environment.json", CONTROL_LIMIT)),
        "build_inputs_fixed": True, "image_reproducibility_claimed": False,
        "boundary": dict(BOUNDARY)})
    return image_id


def _env_map(value):
    _need(type(value) is list and len(value) <= 128, "two_slot_hosted_environment_shape")
    result = {}
    for row in value:
        _need(type(row) is str and "\0" not in row and len(row) <= 16384,
              "two_slot_hosted_environment_shape")
        name, separator, setting = row.partition("=")
        _need(separator and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name)
              and name not in result, "two_slot_hosted_environment_shape")
        result[name] = setting
    return result


def docker_create_args(image_id, ctx, source, control, output, *, phase,
                       previous=None, uid=None, gid=None, handoff=None):
    """Return the only allowed native-host or replay container command."""
    checker.validate_context(ctx)
    uid = os.getuid() if uid is None else uid
    gid = os.getgid() if gid is None else gid
    _need(type(uid) is int and type(gid) is int and 0 < uid < (1 << 31) and 0 < gid < (1 << 31),
          "two_slot_hosted_nonroot_user")
    _need(phase in {"acquire", "verify"} and (previous is not None) == (phase == "verify")
          and (handoff is not None) == (phase == "verify"), "two_slot_hosted_container_phase")
    _need(type(image_id) is str and IMAGE_RE.fullmatch(image_id), "two_slot_hosted_image_id")
    root = Path(output).parent
    expected_output = root / ("observation" if phase == "acquire" else "verification")
    _need(Path(source) == root / "source" and Path(control) == root / "control"
          and Path(output) == expected_output, "two_slot_hosted_mount_selection")
    mounts = [(Path(source), "/repo", True), (Path(control), "/control", True),
              (Path(output), "/output", False)]
    if previous is not None:
        mounts.append((Path(previous), "/input", True))
    for path, _target, _readonly in mounts:
        _need(path.is_absolute() and "," not in str(path) and "\n" not in str(path) and "\r" not in str(path)
              and "\0" not in str(path) and ".." not in path.parts,
              "two_slot_hosted_mount_path")
    name = "pulse-two-slot-" + str(ctx["run_id"]) + "-1-" + phase
    labels = {
        "org.pulsemech.two-slot.run": str(ctx["run_id"]) + "/1",
        "org.pulsemech.two-slot.source": ctx["source_commit"],
        "org.pulsemech.two-slot.profile": PROFILE,
        "org.pulsemech.two-slot.phase": phase,
    }
    args = ["docker", "create", "--name", name,
            "--cidfile", str(root / "environment/container-id.txt"),
            "--platform", "linux/amd64", "--user", str(uid) + ":" + str(gid),
            "--read-only", "--network", "none", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges", "--pids-limit", "64",
            "--memory", "1g", "--cpus", "1", "--tmpfs", "/tmp:rw,nosuid,nodev,size=64m",
            "--workdir", "/repo"]
    for key, value in sorted(labels.items()):
        args.extend(("--label", key + "=" + value))
    for source_path, target, readonly in sorted(mounts, key=lambda item: item[1]):
        args.extend(("--mount", "type=bind,source=" + str(source_path) + ",target=" + target
                     + (",readonly" if readonly else "")))
    for key, value in sorted(checker.expected_env(ctx, phase, image_id, handoff).items()):
        args.extend(("--env", key + "=" + value))
    # Python is PID1 supervisor. The fixed runner launches one internal probe
    # child; --init would change that reviewed observer/process boundary.
    args.extend(("--entrypoint", PYTHON, image_id, "-I", "-B", "/repo/" + CONFIG + "/run.py", phase))
    return args


def _selection(root, phase, ctx, image_id, sources, handoff=None):
    selected = checker.make_selection(phase, ctx, image_id, sources,
        sources[CONFIG + "/environment.json"], handoff)
    checker.validate_selection(selected, phase)
    _mkdir(Path(root) / "control")
    _write_json(Path(root) / "control/hosted-selection.json", selected)
    return selected


def _container(root, selected, image_id, ctx, phase, previous=None):
    """Run once; independently identify and remove only the owned container."""
    root = Path(root)
    output = root / ("observation" if phase == "acquire" else "verification")
    _mkdir(output)
    selection_raw = io.read_regular(root / "control/hosted-selection.json", CONTROL_LIMIT)
    selection = parse(selection_raw)
    checker.validate_selection(selection, phase)
    _need(selection["context"] == ctx and selection["image_id"] == image_id,
          "two_slot_hosted_container_selection")
    inspected = _json(root / "host-commands/image-inspect.stdout.bin", 4 * 1024 * 1024)
    _need(type(inspected) is list and len(inspected) == 1 and inspected[0].get("Id") == image_id,
          "two_slot_hosted_container_image")
    plan = checker.make_container_plan(phase, ctx, image_id, os.getuid(), os.getgid(), root,
        inspected[0]["Config"]["Env"], io.binding(selection_raw), previous=previous,
        handoff=selection["handoff"])
    _write_json(root / "environment/container-plan.json", plan)
    cidfile = root / "environment/container-id.txt"
    _need(not os.path.lexists(cidfile), "two_slot_hosted_container_id_exists")
    argv = docker_create_args(image_id, ctx, root / "source", root / "control", output,
        phase=phase, previous=previous, handoff=selection["handoff"])
    container_id = None
    started = None
    cleanup_ok = False
    try:
        created = _command(root, "container-create", argv, require=False)
        if os.path.lexists(cidfile):
            container_id = io.read_regular(cidfile, 128).decode("ascii").strip()
            _need(CID_RE.fullmatch(container_id), "two_slot_hosted_container_id")
        _need(_success(created) and container_id is not None,
              "two_slot_hosted_container_create_failed")
        created_stdout = io.read_regular(root / "host-commands/container-create.stdout.bin", 128)
        _need(created_stdout.decode("ascii").strip() == container_id,
              "two_slot_hosted_container_id_disagreement")
        info = _command_json(root, "container-inspect", ["docker", "container", "inspect", container_id])
        checker.validate_container_identity(info, container_id, image_id, ctx, phase, plan)
        prestart = info[0].get("State", {})
        _need(prestart.get("Status") == "created" and prestart.get("Running") is False
              and prestart.get("Restarting", False) is False
              and prestart.get("Dead", False) is False, "two_slot_hosted_container_prestart")
        started = _command(root, "container-start", ["docker", "start", "--attach", container_id],
                           240, require=False)
        # A client deadline is not a container terminal observation. Inspect
        # state even when the attached client was interrupted or the stage timed out.
        state = _command_json(root, "container-state", ["docker", "container", "inspect", container_id],
                              30, cleanup=True)
        checker.validate_container_identity(state, container_id, image_id, ctx, phase, plan)
        terminal = state[0]["State"]
        _need(type(terminal.get("ExitCode")) is int and terminal["ExitCode"] == 0
              and terminal.get("Running") is False and terminal.get("Status") == "exited"
              and terminal.get("OOMKilled") is False and terminal.get("Error") in ("", None),
              "two_slot_hosted_container_exit")
    finally:
        # A partial create can leave a running container even without a usable
        # cidfile. Query our exclusive expected NAME, and verify its ID/image/
        # labels before removal. A substituted cidfile never authorizes removal.
        cleanup = {"container_id": None, "image_id": image_id, "phase": phase,
            "name": plan["name"], "owned_container_verified": False,
            "inspect_exit_code": None, "remove_succeeded": False,
            "absence_verified": False, "cleanup_errors": []}
        owned_id = None
        try:
            ownership_result = _command(root, "container-ownership-inspect",
                ["docker", "container", "inspect", plan["name"]], 30, require=False, cleanup=True)
            cleanup["inspect_exit_code"] = ownership_result.get("returncode")
            _need(_success(ownership_result), "two_slot_hosted_cleanup_inspect_failed")
            ownership = _json(root / "host-commands/container-ownership-inspect.stdout.bin", 4 * 1024 * 1024)
            _need(type(ownership) is list and len(ownership) == 1
                  and type(ownership[0]) is dict and type(ownership[0].get("Id")) is str
                  and CID_RE.fullmatch(ownership[0]["Id"]), "two_slot_hosted_cleanup_identity")
            candidate = ownership[0]["Id"]
            checker.validate_container_identity(ownership, candidate, image_id, ctx, phase, plan,
                                                ownership_only=True)
            owned_id = candidate
            cleanup["container_id"] = owned_id
            cleanup["owned_container_verified"] = True
            if container_id is not None and container_id != owned_id:
                cleanup["cleanup_errors"].append("two_slot_hosted_cleanup_cid_disagreement")
            if os.path.lexists(cidfile):
                try:
                    cid_bytes = io.read_regular(cidfile, 128)
                    _need(cid_bytes.decode("ascii").strip() == owned_id,
                          "two_slot_hosted_cleanup_cid_changed")
                except (OSError, ValueError, UnicodeError):
                    cleanup["cleanup_errors"].append("two_slot_hosted_cleanup_cid_changed")
        except (OSError, ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError) as exc:
            cleanup["cleanup_errors"].append(_error_code(exc, "two_slot_hosted_cleanup_ownership"))
        if owned_id is not None:
            try:
                removed = _command(root, "container-remove", ["docker", "rm", "--force", owned_id],
                                   30, require=False, cleanup=True)
                cleanup["remove_succeeded"] = _success(removed)
                if not cleanup["remove_succeeded"]:
                    cleanup["cleanup_errors"].append("two_slot_hosted_cleanup_remove_failed")
            except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError) as exc:
                cleanup["cleanup_errors"].append(_error_code(exc, "two_slot_hosted_cleanup_remove_failed"))
            try:
                absence = _command(root, "container-absence", ["docker", "container", "ls", "--all",
                    "--quiet", "--no-trunc", "--filter", "id=" + owned_id],
                    30, require=False, cleanup=True)
                empty = io.read_regular(root / "host-commands/container-absence.stdout.bin", 128)
                cleanup["absence_verified"] = (_success(absence) and empty == b""
                                                 and absence.get("stdout") == io.binding(empty))
                if not cleanup["absence_verified"]:
                    cleanup["cleanup_errors"].append("two_slot_hosted_cleanup_absence_failed")
            except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError) as exc:
                cleanup["cleanup_errors"].append(_error_code(exc, "two_slot_hosted_cleanup_absence_failed"))
        cleanup_ok = (cleanup["owned_container_verified"] and cleanup["remove_succeeded"]
                      and cleanup["absence_verified"] and not cleanup["cleanup_errors"])
        _write_json(root / "environment/container-cleanup.json", cleanup)
    _need(cleanup_ok, "two_slot_hosted_container_cleanup")
    _need(_success(started), "two_slot_hosted_container_incomplete")
    checker.validate_cleanup(root, ctx, phase)
    return output


def _error_code(exc, fallback="two_slot_hosted_stage_failed"):
    value = getattr(exc, "code", fallback)
    return value if type(value) is str and re.fullmatch(r"[a-z][a-z0-9_]{0,127}", value) else fallback


def acquire(root, ctx):
    root = Path(root)
    _prefix(root, "acquire", ctx)
    selected = environment()
    sources = source_bindings()
    validate_git_source_snapshot(root, ctx, sources)
    _copy_sources(root, sources)
    materials = _materials(root, selected)
    image_id = _build_image(root, selected, materials)
    _selection(root, "acquire", ctx, image_id, sources)
    _assert_sources(root, sources)
    _container(root, selected, image_id, ctx, "acquire")
    checker.verify_completed_acquisition(root, ctx)
    _assert_sources(root, sources)
    return 0


def finalize(root, ctx):
    """Bind the available acquisition prefix without reselecting its sources."""
    root = Path(root)
    _prefix(root, "acquire", ctx)
    value = checker.make_receipt(root, ctx, phase="acquire")
    raw = io.canonical(value)
    checker.validate_receipt(raw, io.sha(raw), ctx)
    _write_json(root / "receipt.json", value)
    # The receipt is externally handed off only after successful hardened
    # publication and a full byte/roster recheck of the retained artifact.
    checker.verify_preservation(root, raw, io.sha(raw), ctx)
    result = {"receipt_sha256": io.sha(raw)}
    files = value["files"]
    for key, name in (("request", "observation/request.json"),
                      ("attempt", "observation/attempt/attempt.json"),
                      ("qualification", "observation/attempt/qualification.json")):
        selected = files.get(name)
        result[key + "_sha256"] = "" if selected is None else selected["sha256"]
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as stream:
            for name, value in result.items():
                stream.write(name + "=" + value + "\n")
    sys.stdout.write(io.canonical(result).decode("utf-8"))
    return 0


def _credential_environment(root):
    token = os.environ.get("GH_TOKEN")
    _need(type(token) is str and bool(token) and "\0" not in token,
          "two_slot_hosted_github_credential")
    result = _command_environment(root)
    result.update(GH_TOKEN=token, GH_HOST="github.com", GH_PROMPT_DISABLED="1",
                  GH_NO_UPDATE_NOTIFIER="1")
    return result


def _artifact_metadata(root, ctx, handoff):
    result = _command(root, "artifact-metadata", ["gh", "api",
        "repos/" + REPOSITORY + "/actions/artifacts/" + str(handoff["artifact_id"])],
        60, require=False, env=_credential_environment(root))
    _need(_success(result), "two_slot_hosted_artifact_metadata_failed")
    value = _json(Path(root) / "host-commands/artifact-metadata.stdout.bin", 4 * 1024 * 1024)
    checker.validate_artifact_metadata(value, ctx, handoff)
    return value


def _private_input_path(root):
    root = Path(root)
    return root.parent / (root.name + "-private-input")


def verify(root, source, expected_receipt_sha256, ctx):
    root, source = Path(root), Path(source)
    _prefix(root, "verify", ctx)
    handoff = checker.handoff()
    _need(handoff["receipt_sha256"] == expected_receipt_sha256,
          "two_slot_hosted_receipt_selection")
    _artifact_metadata(root, ctx, handoff)
    raw = io.read_regular(source / "receipt.json", CONTROL_LIMIT)
    receipt = checker.verify_preservation(source, raw, expected_receipt_sha256, ctx)
    expected_files = {**receipt["files"], "receipt.json": io.binding(raw)}
    previous = _private_input_path(root)
    io.copy_private_tree(source, previous, expected_files)
    checker.verify_preservation(previous, raw, expected_receipt_sha256, ctx)
    _write_json(root / "prefix-verification.json", {
        "record_type": "required_gate_idempotence_loader_two_slot_hosted_prefix_verification_v0",
        "profile": PROFILE, "status": "preserved_prefix_verified", "error_code": None,
        "context": ctx, "handoff": handoff, "receipt": io.binding(raw),
        "preserved_file_count": len(expected_files), "all_preserved_bytes_verified": True,
        "preservation_is_qualification_acceptance": False, "boundary": dict(BOUNDARY)})
    # A preserved partial download/build/attempt is useful evidence. It does
    # not execute any replay or become an attested completed qualification.
    checker.verify_completed_acquisition(previous, ctx, receipt)
    selected = environment()
    sources = source_bindings()
    validate_git_source_snapshot(root, ctx, sources)
    _copy_sources(root, sources)
    _need(sources == _json(previous / "source-bindings.json"),
          "two_slot_hosted_verification_source_selection")
    materials = _materials(root, selected, previous)
    image_id = _build_image(root, selected, materials, previous)
    _selection(root, "verify", ctx, image_id, sources, handoff)
    _assert_sources(root, sources)
    _container(root, selected, image_id, ctx, "verify", previous)
    _assert_sources(root, sources)
    verified = checker.make_verified_binding(root, previous, ctx, handoff, receipt)
    _write_json(root / "verified-binding.json", verified)
    return 0


def attest_verify(root, bundle, ctx):
    root, bundle = Path(root), Path(bundle)
    _prefix(root, "verify", ctx)
    handoff = checker.handoff()
    previous = _private_input_path(root)
    receipt_raw = io.read_regular(previous / "receipt.json", CONTROL_LIMIT)
    receipt = checker.verify_preservation(previous, receipt_raw, handoff["receipt_sha256"], ctx)
    subject = root / "verified-binding.json"
    subject_raw = io.read_regular(subject, CONTROL_LIMIT)
    expected = checker.make_verified_binding(root, previous, ctx, handoff, receipt)
    _need(io.canonical(expected) == subject_raw, "two_slot_hosted_attestation_subject")
    sources = _json(root / "source-bindings.json")
    _assert_sources(root, sources)
    bundle_raw = io.read_regular(bundle, BUNDLE_LIMIT)
    _need(bool(bundle_raw), "two_slot_hosted_attestation_bundle_empty")
    retained_bundle = root / "attestation-bundle.json"
    io.write_new(retained_bundle, bundle_raw)
    _write_json(root / "attestation-identity.json", {
        "record_type": "required_gate_idempotence_loader_two_slot_hosted_attestation_identity_v0",
        "profile": PROFILE, "context": ctx, "handoff": handoff,
        "subject": io.binding(subject_raw), "bundle": io.binding(bundle_raw),
        "signer_workflow": REPOSITORY + "/" + WORKFLOW,
        "signer_digest": ctx["workflow_sha"], "source_digest": ctx["source_commit"],
        "source_ref": "refs/heads/main", "boundary": dict(BOUNDARY)})
    result = _command(root, "attestation-verify", [
        "gh", "attestation", "verify", str(subject), "--bundle", str(retained_bundle),
        "--repo", REPOSITORY, "--signer-workflow", REPOSITORY + "/" + WORKFLOW,
        "--signer-digest", ctx["workflow_sha"], "--source-digest", ctx["source_commit"],
        "--source-ref", "refs/heads/main", "--predicate-type", "https://slsa.dev/provenance/v1",
        "--cert-oidc-issuer", "https://token.actions.githubusercontent.com",
        "--deny-self-hosted-runners", "--format", "json"],
        120, require=False, env=_credential_environment(root))
    _need(io.read_regular(subject, CONTROL_LIMIT) == subject_raw,
          "two_slot_hosted_attestation_subject_changed")
    _need(io.read_regular(retained_bundle, BUNDLE_LIMIT) == bundle_raw,
          "two_slot_hosted_attestation_bundle_changed")
    _need(_success(result), "two_slot_hosted_attestation_verification_failed")
    # The signature command is an external process. Re-derive its full subject
    # from the selected private artifact and fresh replay records afterwards;
    # unchanged subject bytes alone would not detect supporting-record drift.
    _assert_sources(root, sources)
    rechecked_receipt = checker.verify_preservation(
        previous, receipt_raw, handoff["receipt_sha256"], ctx)
    _need(io.canonical(checker.make_verified_binding(
        root, previous, ctx, handoff, rechecked_receipt)) == subject_raw,
        "two_slot_hosted_attestation_evidence_changed")
    _write_json(root / "attestation.json", {
        "record_type": "required_gate_idempotence_loader_two_slot_hosted_attestation_verification_v0",
        "profile": PROFILE, "status": "accepted", "context": ctx, "handoff": handoff,
        "subject": io.binding(subject_raw), "bundle": io.binding(bundle_raw),
        "github_signature_verification_succeeded": True, "boundary": dict(BOUNDARY)})
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


def _interrupted(_signum, _frame):
    # Convert an ordinary job termination into Python unwinding so owned
    # client/container cleanup gets its own bounded attempt before exit.
    raise io.HostedIOError("two_slot_hosted_interrupted")


def _failed_verification_prefix(root, ctx, error_code):
    path = Path(root) / "prefix-verification.json"
    if os.path.lexists(path):
        return
    try:
        selected_handoff = checker.handoff()
    except (OSError, ValueError, TypeError, KeyError):
        selected_handoff = None
    _write_json(path, {
        "record_type": "required_gate_idempotence_loader_two_slot_hosted_prefix_verification_v0",
        "profile": PROFILE, "status": "preserved_incomplete", "error_code": error_code,
        "context": ctx, "handoff": selected_handoff, "receipt": None,
        "preserved_file_count": None, "all_preserved_bytes_verified": False,
        "preservation_is_qualification_acceptance": False, "boundary": dict(BOUNDARY)})


def main(argv=None):
    global STAGE_DEADLINE
    args = _parser().parse_args(argv)
    ctx = None
    original_handler = None
    try:
        os.umask(0o077)
        original_handler = signal.signal(signal.SIGTERM, _interrupted)
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
    except (OSError, ValueError, TypeError, KeyError, IndexError, OverflowError,
            RecursionError, KeyboardInterrupt) as exc:
        failure = {"record_type": "required_gate_idempotence_loader_two_slot_hosted_failure_v0",
            "profile": PROFILE, "status": "preserved_incomplete", "stage": args.command,
            "error_code": _error_code(exc), "context": ctx, "boundary": dict(BOUNDARY)}
        if args.command == "verify":
            try:
                _failed_verification_prefix(args.output_directory.absolute(), ctx, failure["error_code"])
            except (OSError, ValueError, TypeError):
                pass
        try:
            _write_json(args.output_directory.absolute() / "failure.json", failure)
        except (OSError, ValueError, TypeError):
            # Keep the earlier failure or failed publication prefix untouched.
            pass
        sys.stdout.write(io.canonical(failure).decode("utf-8"))
        return 1
    finally:
        STAGE_DEADLINE = None
        if original_handler is not None:
            signal.signal(signal.SIGTERM, original_handler)


if __name__ == "__main__":
    raise SystemExit(main())

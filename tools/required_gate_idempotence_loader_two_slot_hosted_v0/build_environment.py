#!/usr/bin/env python3
"""Install only the fixed six-wheel qualification checker closure, offline.

This helper is part of the selected source closure. It creates an input/build
record, not a reproducibility certificate or original-source build authority.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys


ENVIRONMENT_SHA256 = "8419a2ebcd3d5014d4395cbd9118d1db74de35743d171e4011607bbba5848612"
PROFILE = "linux_x86_64_loader_two_slot_hosted_v0"
PACKAGES = ("attrs", "jsonschema", "jsonschema-specifications", "referencing",
            "rpds-py", "typing_extensions")
MAX_CONTROL_BYTES = 65536
MAX_WHEEL_BYTES = 16 * 1024 * 1024


def _need(condition, code):
    if not condition:
        raise ValueError(code)


def _binding(raw):
    return {"size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _read(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        _need(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= limit,
              "two_slot_build_input_type_or_size")
        chunks, remaining = [], limit + 1
        while remaining:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        after = os.fstat(fd)
        linked = os.stat(path, follow_symlinks=False)
        identity = lambda item: (item.st_dev, item.st_ino, item.st_mode,
                                 item.st_size, item.st_mtime_ns, item.st_ctime_ns)
        _need(identity(before) == identity(after) == identity(linked)
              and len(raw) == before.st_size, "two_slot_build_input_changed")
        return raw
    finally:
        os.close(fd)


def _write_new(path, raw):
    _need(0 < len(raw) <= MAX_CONTROL_BYTES, "two_slot_build_record_size")
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
                 | os.O_CLOEXEC, 0o644)
    parent = None
    owned = os.fstat(fd)
    try:
        os.fchmod(fd, 0o644)
        view = memoryview(raw)
        while view:
            count = os.write(fd, view)
            _need(count > 0, "two_slot_build_record_write")
            view = view[count:]
        os.fsync(fd)
        _need(os.pread(fd, len(raw) + 1, 0) == raw,
              "two_slot_build_record_content")
        linked = os.stat(path, follow_symlinks=False)
        _need((linked.st_dev, linked.st_ino) == (owned.st_dev, owned.st_ino),
              "two_slot_build_record_identity")
        parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                         | os.O_CLOEXEC)
        os.fsync(parent)
        os.close(fd)
        fd = None
        os.close(parent)
        parent = None
    except BaseException:
        try:
            linked = os.stat(path, follow_symlinks=False)
            if (linked.st_dev, linked.st_ino) == (owned.st_dev, owned.st_ino):
                os.unlink(path)
        except OSError:
            pass
        raise
    finally:
        for handle in (fd, parent):
            if handle is not None:
                try:
                    os.close(handle)
                except OSError:
                    pass


def build(inputs):
    inputs = Path(inputs)
    _need(inputs.is_absolute() and not inputs.is_symlink(), "two_slot_build_inputs")
    env_bytes = _read(inputs / "environment.json", MAX_CONTROL_BYTES)
    _need(hashlib.sha256(env_bytes).hexdigest() == ENVIRONMENT_SHA256,
          "two_slot_build_environment_digest")
    # A pinned byte string is parsed only after its digest has been checked.
    environment = json.loads(env_bytes)
    _need(environment["profile"] == PROFILE
          and environment["original_payload_included"] is False,
          "two_slot_build_profile")
    python = environment["python"]
    _need(platform.system() == "Linux" and platform.machine() == "x86_64"
          and platform.python_version() == python["version"]
          and sys.executable == python["executable"] and sys.flags.isolated == 1,
          "two_slot_build_interpreter")
    executable = _read(python["executable"], MAX_CONTROL_BYTES)
    _need(_binding(executable) == python["observer_binding"],
          "two_slot_build_interpreter_binding")
    packages = python["packages"]
    _need(tuple(item["name"] for item in packages) == PACKAGES,
          "two_slot_build_package_closure")
    lock = _read(inputs / "requirements.lock", MAX_CONTROL_BYTES)
    expected_lock = ("\n".join(
        item["name"] + "==" + item["version"] + " --hash=sha256:" + item["sha256"]
        for item in packages) + "\n").encode("ascii")
    _need(lock == expected_lock and _binding(lock) == environment["requirements"],
          "two_slot_build_lock")
    wheel_directory = inputs / "wheels"
    _need(wheel_directory.is_dir() and not wheel_directory.is_symlink()
          and sorted(item.name for item in wheel_directory.iterdir())
          == sorted(item["filename"] for item in packages),
          "two_slot_build_wheel_roster")
    wheels = {}
    for item in packages:
        wheel = _read(wheel_directory / item["filename"], MAX_WHEEL_BYTES)
        descriptor = {"size_bytes": item["size_bytes"], "sha256": item["sha256"]}
        _need(_binding(wheel) == descriptor, "two_slot_build_wheel_binding")
        wheels[item["filename"]] = descriptor
    command = [python["executable"], "-I", "-B", "-m", "pip", "install",
               "--no-index", "--no-deps", "--no-cache-dir", "--no-compile",
               "--disable-pip-version-check", "--require-hashes", "--find-links",
               str(wheel_directory), "-r", str(inputs / "requirements.lock")]
    result = subprocess.run(command, stdin=subprocess.DEVNULL, check=False, timeout=120)
    _need(result.returncode == 0, "two_slot_build_install_failed")
    installed = {}
    for item in packages:
        actual = importlib.metadata.version(item["name"])
        _need(actual == item["version"], "two_slot_build_installed_version")
        installed[item["name"]] = actual
    # Re-read selected materials after installation; replacement cannot become
    # a successful record merely because pip consumed the earlier contents.
    _need(_read(inputs / "environment.json", MAX_CONTROL_BYTES) == env_bytes
          and _read(inputs / "requirements.lock", MAX_CONTROL_BYTES) == lock
          and _binding(_read(python["executable"], MAX_CONTROL_BYTES))
          == python["observer_binding"], "two_slot_build_input_drift")
    for name, descriptor in wheels.items():
        _need(_binding(_read(wheel_directory / name, MAX_WHEEL_BYTES)) == descriptor,
              "two_slot_build_input_drift")
    record = {"record_type": "required_gate_idempotence_loader_two_slot_build_v0",
              "profile": PROFILE, "environment": _binding(env_bytes),
              "requirements": _binding(lock), "wheels": wheels,
              "python": python["observer_binding"], "installed": installed,
              "offline_install": True, "reproducible_image_claimed": False,
              "original_payload_included": False, "authority_effect": "none"}
    raw = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
    _write_new(inputs / "build-environment-record.json", raw)
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        build(args.inputs)
    except (OSError, ValueError, subprocess.TimeoutExpired, importlib.metadata.PackageNotFoundError) as exc:
        # Fixed error codes are enough; no environment or credentials are logged.
        code = str(exc) if isinstance(exc, ValueError) else "two_slot_build_failed"
        print(code, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

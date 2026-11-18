#!/usr/bin/env python3
"""Install the reviewed offline observation-tool environment during image build.

This program does not launch the selected native entry or establish ptrace
eligibility. Its output describes installed build inputs and checked file bytes.
The independently dispatched acquisition must establish the observed boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import subprocess
import sys


RECORD_TYPE = "required_gate_idempotence_exec_stop_hosted_environment_v0"
PYTHON = "/usr/local/bin/python3.11"
PYTHON_VERSION = "3.11.16"
BASE_IMAGE = (
    "docker.io/library/python@sha256:"
    "174bec68e0451bffabbb08c7d5d21c6b253f772d81d52b9558af97bb3159b761"
)
OVERLAY = frozenset(
    {"gpg", "gpgconf", "libassuan9", "libgcrypt20", "libgpg-error0", "libksba8", "libnpth0t64"}
)
PYTHON_PACKAGES = {
    "pyyaml": "6.0.3",
    "attrs": "26.1.0",
    "jsonschema": "4.26.0",
    "jsonschema-specifications": "2025.9.1",
    "referencing": "0.37.0",
    "rpds-py": "2026.9.1",
    "typing-extensions": "4.16.0",
}


def need(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def normalized_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def binding(raw: bytes) -> dict[str, object]:
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def read_regular(path: Path, limit: int) -> bytes:
    before = path.lstat()
    need(stat.S_ISREG(before.st_mode), "build_input_not_regular")
    need(0 <= before.st_size <= limit, "build_input_size_limit")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        opened = os.fstat(fd)
        need(
            stat.S_ISREG(opened.st_mode)
            and (opened.st_dev, opened.st_ino, opened.st_size)
            == (before.st_dev, before.st_ino, before.st_size),
            "build_input_identity_changed",
        )
        with os.fdopen(fd, "rb", closefd=False) as handle:
            raw = handle.read(limit + 1)
        after = os.fstat(fd)
        need(
            len(raw) == opened.st_size
            and (opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns)
            == (after.st_size, after.st_mtime_ns, after.st_ctime_ns),
            "build_input_changed",
        )
        return raw
    finally:
        os.close(fd)


def check_downloads(directory: Path, entries: list[dict[str, object]]) -> list[Path]:
    need(directory.is_dir() and not directory.is_symlink(), "build_payload_directory")
    names = [item["filename"] for item in entries]
    need(len(names) == len(set(names)), "build_duplicate_filename")
    need(set(path.name for path in directory.iterdir()) == set(names), "build_payload_members")
    paths = []
    for item in entries:
        name = item["filename"]
        need(isinstance(name, str) and Path(name).name == name and name not in {"", ".", ".."}, "build_filename")
        size = item["size_bytes"]
        need(type(size) is int and 0 < size <= 8 * 1024 * 1024, "build_payload_size")
        path = directory / name
        need(binding(read_regular(path, size)) == {key: item[key] for key in ("sha256", "size_bytes")}, "build_payload_binding")
        paths.append(path)
    return paths


def installed_debian() -> dict[str, str]:
    raw = read_regular(Path("/var/lib/dpkg/status"), 8 * 1024 * 1024).decode("utf-8")
    result = {}
    for block in raw.split("\n\n"):
        fields = {}
        for line in block.splitlines():
            if line and not line.startswith((" ", "\t")) and ": " in line:
                key, value = line.split(": ", 1)
                fields[key] = value
        if fields.get("Status") == "install ok installed":
            result[fields["Package"]] = fields["Version"]
    return result


def check_runtime_files(selection: dict[str, object], *, include_gpg: bool) -> list[dict[str, object]]:
    checked = []
    for item in selection["expected_files"]:
        if item["path"] == "/usr/bin/gpg" and not include_gpg:
            continue
        # The ordinary PT_INTERP path is a distribution-owned symlink. Resolve
        # it here, then bind the regular terminal file without following it again.
        path = Path(item["path"]).resolve(strict=True)
        actual = binding(read_regular(path, item["size_bytes"]))
        need(actual == {key: item[key] for key in ("sha256", "size_bytes")}, "build_runtime_file_binding")
        checked.append({"path": item["path"], "resolved_path": str(path), **actual})
    return checked


def install(inputs: Path) -> dict[str, object]:
    need(sys.executable == PYTHON, "build_python_executable")
    need(platform.python_version() == PYTHON_VERSION, "build_python_version")
    need(sys.platform == "linux" and platform.machine() == "x86_64", "build_platform")
    selection_raw = read_regular(inputs / "environment.json", 1024 * 1024)
    selection = json.loads(selection_raw)
    need(selection["record_type"] == RECORD_TYPE, "build_record_type")
    need(selection["platform"] == "linux/amd64", "build_selected_platform")
    need(selection["base_image"]["reference"] == BASE_IMAGE, "build_base_image")
    need(selection["python"]["version"] == PYTHON_VERSION and selection["python"]["executable"] == PYTHON, "build_python_selection")
    need(selection["host_environment_qualified"] is False and selection["native_acquisition_performed"] is False, "build_scope")
    need(selection["authority_effect"] == "none", "build_authority_effect")
    check_runtime_files(selection, include_gpg=False)

    debian = selection["debian"]
    packages = debian["packages"]
    need(len(packages) == len(OVERLAY) and {item["name"] for item in packages} == OVERLAY, "build_debian_overlay")
    need(debian["loader_already_present_in_base"] is True and debian["libc_installation_performed"] is False, "build_libc_scope")
    before = installed_debian()
    for item in debian["closure"]:
        need(before.get(item["name"]) == item["base_version"], "build_base_package_version")
        need(item["installation_required"] == (item["base_version"] != item["version"]), "build_package_delta")
    need({item["name"] for item in debian["closure"] if item["installation_required"]} == OVERLAY, "build_closure_delta")
    debs = check_downloads(inputs / "debs", packages)

    python_packages = selection["python"]["packages"]
    need(len(python_packages) == len(PYTHON_PACKAGES), "build_python_package_count")
    need({normalized_name(item["name"]): item["version"] for item in python_packages} == PYTHON_PACKAGES, "build_python_package_selection")
    check_downloads(inputs / "wheels", python_packages)
    lock_raw = read_regular(inputs / "requirements.lock", 16 * 1024)
    lines = [line.strip() for line in lock_raw.decode("utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")]
    expected = [item["name"] + "==" + item["version"] + " --hash=sha256:" + item["sha256"] for item in python_packages]
    need(lines == expected, "build_requirements_binding")

    environment = {
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "DEBIAN_FRONTEND": "noninteractive",
        "PIP_NO_INDEX": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    subprocess.run(
        ["/usr/bin/apt-get", "--assume-yes", "--no-download", "--no-install-recommends", "--no-remove", "install", *(str(path) for path in debs)],
        env=environment, check=True, timeout=300,
    )
    subprocess.run(
        [PYTHON, "-I", "-m", "pip", "install", "--no-index", "--no-deps", "--require-hashes", "--only-binary=:all:", "--find-links=" + str(inputs / "wheels"), "-r", str(inputs / "requirements.lock")],
        env=environment, check=True, timeout=300,
    )
    subprocess.run([PYTHON, "-I", "-m", "pip", "check"], env=environment, check=True, timeout=60)
    after = installed_debian()
    for item in debian["closure"]:
        need(after.get(item["name"]) == item["version"], "build_installed_package_version")
    for item in python_packages:
        need(importlib.metadata.version(item["name"]) == item["version"], "build_installed_python_version")
    checked = check_runtime_files(selection, include_gpg=True)

    record = {
        "record_type": "required_gate_idempotence_exec_stop_hosted_environment_build_v0",
        "environment_selection": binding(selection_raw),
        "requirements_lock": binding(lock_raw),
        "base_image_reference": BASE_IMAGE,
        "python_version": platform.python_version(),
        "installed_debian_delta": [{"name": item["name"], "version": after[item["name"]]} for item in packages],
        "selected_python_packages": [{"name": item["name"], "version": importlib.metadata.version(item["name"])} for item in python_packages],
        "checked_files": checked,
        "host_environment_qualified": False,
        "native_acquisition_performed": False,
        "authority_effect": "none",
    }
    record_raw = (json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")
    with (inputs / "build-environment-record.json").open("xb") as handle:
        handle.write(record_raw)
    (inputs / "build-environment-record.json").chmod(0o644)
    shutil.rmtree(inputs / "debs")
    shutil.rmtree(inputs / "wheels")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", required=True, type=Path)
    args = parser.parse_args()
    try:
        record = install(args.inputs.resolve(strict=True))
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print("offline environment build rejected: " + str(error), file=sys.stderr)
        return 2
    print(json.dumps(record, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

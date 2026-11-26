#!/usr/bin/env python3
"""Install the selected original-loader observation environment offline.

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
import stat
import subprocess
import sys
import tempfile
import time


ENVIRONMENT_SHA256 = "5333e5db7fef71514c30a7a4a64412accf520a6d06bd2e9ffa20eaf718495389"
PROFILE = "linux_x86_64_loader_resolution_hosted_v0"
MAX_CONTROL_BYTES = 65536

RECORD_TYPE = "required_gate_idempotence_loader_resolution_hosted_environment_v0"
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


NATIVE = {'native/bwrap': {'size_bytes': 80248,
                  'sha256': '573236e5328ac2ebb08f59ae3a9805b4f8d12bdef14be8af4450d5463294985f'},
 'native/ld-linux-x86-64.so.2': {'size_bytes': 225672,
                                 'sha256': 'c8438e4fde1934e61c88311633f00949ff645d5c04cdb8671fa3d78164d2f307'},
 'native/libc.so.6': {'size_bytes': 1995216,
                      'sha256': '9792e3cbb541c8f44c7acf5f14f4022ea62998ecc787d326bed4d8b6547dfd92'},
 'native/libcap.so.2': {'size_bytes': 47288,
                        'sha256': '41217b0af128444f66dee8adda52b2ceaf19da00e5b0b155e2b87b857671286b'},
 'native/libpcre2-8.so.0': {'size_bytes': 711216,
                            'sha256': '92e9b4167f9bbc237ca8f5526d82ee99ec9f8dbd0270ef1dd0ab24e2217f48e3'},
 'native/libselinux.so.1': {'size_bytes': 202984,
                            'sha256': '5cb5293b4e7590463b94f7b23152d54807a6a2ccaf8cac9e343908c6692c086c'}}
NATIVE_HOST_PATHS = {'native/bwrap': None,
 'native/ld-linux-x86-64.so.2': '/lib64/ld-linux-x86-64.so.2',
 'native/libc.so.6': '/usr/lib/x86_64-linux-gnu/libc.so.6',
 'native/libcap.so.2': '/usr/lib/x86_64-linux-gnu/libcap.so.2',
 'native/libpcre2-8.so.0': '/usr/lib/x86_64-linux-gnu/libpcre2-8.so.0',
 'native/libselinux.so.1': '/usr/lib/x86_64-linux-gnu/libselinux.so.1'}
NATIVE_RESTORATIONS = [{
    "input": "native/libpcre2-8.so.0",
    "host_path": "/usr/lib/x86_64-linux-gnu/libpcre2-8.so.0",
    "symlink_target": "libpcre2-8.so.0.14.0",
    "resolved_path": "/usr/lib/x86_64-linux-gnu/libpcre2-8.so.0.14.0",
    "before": {
        "sha256": "8dde125b341abfdf4a596d2974cd3048e350cbc8d2d77acd54ea044f7815ca77",
        "size_bytes": 711216,
    },
    "after": {
        "sha256": "92e9b4167f9bbc237ca8f5526d82ee99ec9f8dbd0270ef1dd0ab24e2217f48e3",
        "size_bytes": 711216,
    },
    "mode": 0o644,
}]


def need(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def normalized_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def binding(raw: bytes) -> dict[str, object]:
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def read_regular(path: Path, limit: int) -> bytes:
    path = Path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode), "build_input_not_regular")
        need(0 < before.st_size <= limit, "build_input_size_limit")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            raw = handle.read(limit + 1)
        after = os.fstat(fd)
        linked = os.stat(path, follow_symlinks=False)
        identity = lambda item: (item.st_dev, item.st_ino, item.st_mode, item.st_nlink,
                                 item.st_size, item.st_mtime_ns, item.st_ctime_ns)
        need(identity(before) == identity(after) == identity(linked)
             and len(raw) == before.st_size, "build_input_changed")
        return raw
    finally:
        os.close(fd)


def write_new(path: Path, raw: bytes) -> None:
    need(0 < len(raw) <= MAX_CONTROL_BYTES, "build_record_size")
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
                 | os.O_CLOEXEC, 0o644)
    parent = None
    owned = os.fstat(fd)
    try:
        os.fchmod(fd, 0o644)
        view = memoryview(raw)
        while view:
            written = os.write(fd, view)
            need(written > 0, "build_record_write")
            view = view[written:]
        os.fsync(fd)
        need(os.pread(fd, len(raw) + 1, 0) == raw, "build_record_content")
        linked = os.stat(path, follow_symlinks=False)
        need((linked.st_dev, linked.st_ino) == (owned.st_dev, owned.st_ino),
             "build_record_identity")
        parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                         | os.O_CLOEXEC)
        os.fsync(parent)
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
                os.close(handle)


def check_input_layout(inputs: Path) -> None:
    need(inputs.is_absolute() and inputs.is_dir() and not inputs.is_symlink(),
         "build_input_directory")
    need({path.name for path in inputs.iterdir()} == {
        "environment.json", "requirements.lock", "build_environment.py",
        "debs", "wheels", "native"}, "build_input_roster")
    for name in ("debs", "wheels", "native"):
        directory = inputs / name
        need(directory.is_dir() and not directory.is_symlink(), "build_payload_directory")
    need({path.name for path in (inputs / "native").iterdir()}
         == {Path(name).name for name in NATIVE}, "build_native_roster")


def check_native_inputs(inputs: Path) -> None:
    for name, wanted in NATIVE.items():
        need(binding(read_regular(inputs / name, wanted["size_bytes"])) == wanted,
             "build_native_original_binding")


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


def _restoration_selection(selection: dict[str, object]) -> list[dict[str, object]]:
    selected = selection.get("native_object_restorations")
    need(type(selected) is list and all(type(item) is dict for item in selected),
         "build_native_restoration_selection")
    try:
        selected_bytes = json.dumps(selected, sort_keys=True, separators=(",", ":"), allow_nan=False)
        expected_bytes = json.dumps(NATIVE_RESTORATIONS, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError("build_native_restoration_selection") from error
    need(selected_bytes == expected_bytes, "build_native_restoration_selection")
    return NATIVE_RESTORATIONS


def _restoration_identity(value: os.stat_result) -> tuple[int, ...]:
    return (value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
            value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def _pin_restoration_parent(path: Path) -> list[int]:
    """Hold every real directory from / to the selected terminal's parent."""
    need(path.is_absolute() and all(part not in {".", ".."} for part in path.parts),
         "build_native_restoration_parent_path")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptors = [os.open("/", flags)]
    try:
        for name in path.parts[1:]:
            before = os.stat(name, dir_fd=descriptors[-1], follow_symlinks=False)
            need(stat.S_ISDIR(before.st_mode), "build_native_restoration_parent_type")
            child = os.open(name, flags, dir_fd=descriptors[-1])
            descriptors.append(child)
            opened = os.fstat(child)
            need(stat.S_ISDIR(opened.st_mode)
                 and (before.st_dev, before.st_ino) == (opened.st_dev, opened.st_ino),
                 "build_native_restoration_parent_changed")
        return descriptors
    except BaseException:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
        raise


def _check_restoration_parent(path: Path, descriptors: list[int]) -> None:
    for index, descriptor in enumerate(descriptors):
        current = (os.stat("/", follow_symlinks=False) if index == 0 else
                   os.stat(path.parts[index], dir_fd=descriptors[index - 1],
                           follow_symlinks=False))
        held = os.fstat(descriptor)
        need(stat.S_ISDIR(current.st_mode) and stat.S_ISDIR(held.st_mode)
             and (current.st_dev, current.st_ino) == (held.st_dev, held.st_ino),
             "build_native_restoration_parent_changed")


def _restoration_snapshot(item: dict[str, object], directory: int,
                          state: str) -> tuple[dict[str, object], tuple[int, ...], tuple[int, ...]]:
    host, terminal = Path(item["host_path"]), Path(item["resolved_path"])
    need(host.parent == terminal.parent and terminal.name == item["symlink_target"],
         "build_native_restoration_layout_selection")
    link = os.stat(host.name, dir_fd=directory, follow_symlinks=False)
    need(stat.S_ISLNK(link.st_mode), "build_native_restoration_symlink_type")
    need(os.readlink(host.name, dir_fd=directory) == item["symlink_target"],
         "build_native_restoration_symlink_target")
    before = os.stat(terminal.name, dir_fd=directory, follow_symlinks=False)
    need(stat.S_ISREG(before.st_mode), "build_native_restoration_terminal_type")
    need(stat.S_IMODE(before.st_mode) == item["mode"] and before.st_nlink == 1,
         "build_native_restoration_terminal_metadata")
    need(0 <= before.st_size <= 16 * 1024 * 1024,
         "build_native_restoration_terminal_size")
    descriptor = os.open(terminal.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                         dir_fd=directory)
    try:
        opened = os.fstat(descriptor)
        need(_restoration_identity(opened) == _restoration_identity(before),
             "build_native_restoration_terminal_changed")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            raw = handle.read(16 * 1024 * 1024 + 1)
        need(len(raw) == opened.st_size
             and _restoration_identity(opened) == _restoration_identity(os.fstat(descriptor))
             == _restoration_identity(os.stat(terminal.name, dir_fd=directory, follow_symlinks=False)),
             "build_native_restoration_terminal_changed")
    finally:
        os.close(descriptor)
    need(_restoration_identity(link)
         == _restoration_identity(os.stat(host.name, dir_fd=directory, follow_symlinks=False))
         and os.readlink(host.name, dir_fd=directory) == item["symlink_target"],
         "build_native_restoration_symlink_changed")
    actual = binding(raw)
    need(actual == item[state], "build_native_restoration_" + state + "_binding")
    return actual, _restoration_identity(opened), _restoration_identity(link)


def restore_original_native_objects(inputs: Path, selection: dict[str, object]) -> list[dict[str, object]]:
    """Restore the one selected base revision; never accept an unknown conflict.

    Keep the distribution's SONAME link and terminal filename intact so later
    ldconfig triggers see the same layout. Each invocation requires the exact
    selected before bytes; the ordinary original-object installer stays strict.
    """
    result = []
    for item in _restoration_selection(selection):
        need(item["after"] == NATIVE[item["input"]]
             and item["host_path"] == NATIVE_HOST_PATHS[item["input"]],
             "build_native_restoration_original_selection")
        try:
            raw = read_regular(inputs / item["input"], 16 * 1024 * 1024)
        except (OSError, ValueError) as error:
            raise ValueError("build_native_restoration_original_input") from error
        need(binding(raw) == item["after"], "build_native_restoration_original_binding")
        terminal = Path(item["resolved_path"])
        descriptors = []
        staged = None
        stage_identity = None
        try:
            descriptors = _pin_restoration_parent(terminal.parent)
            directory = descriptors[-1]
            _check_restoration_parent(terminal.parent, descriptors)
            observed_before, before_identity, link_identity = _restoration_snapshot(item, directory, "before")
            stage_name = ".pulse-loader-resolution-restoration-" + terminal.name
            descriptor = os.open(stage_name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                                 0o600, dir_fd=directory)
            staged = stage_name
            stage_identity = os.fstat(descriptor)
            with os.fdopen(descriptor, "w+b") as output:
                need(output.write(raw) == len(raw), "build_native_restoration_write")
                output.flush()
                os.fchmod(output.fileno(), item["mode"])
                os.fsync(output.fileno())
                output.seek(0)
                need(output.read(len(raw) + 1) == raw, "build_native_restoration_staging_binding")
                stage_identity = os.fstat(output.fileno())
                need(stat.S_ISREG(stage_identity.st_mode)
                     and stat.S_IMODE(stage_identity.st_mode) == item["mode"]
                     and stage_identity.st_nlink == 1,
                     "build_native_restoration_staging_metadata")
            # Validate the known base state again immediately before replacement.
            _check_restoration_parent(terminal.parent, descriptors)
            repeated = _restoration_snapshot(item, directory, "before")
            need(repeated == (observed_before, before_identity, link_identity),
                 "build_native_restoration_before_changed")
            need(_restoration_identity(os.stat(stage_name, dir_fd=directory, follow_symlinks=False))
                 == _restoration_identity(stage_identity), "build_native_restoration_staging_changed")
            os.replace(stage_name, terminal.name, src_dir_fd=directory, dst_dir_fd=directory)
            staged = None
            os.fsync(directory)
            observed_after, _, final_link_identity = _restoration_snapshot(item, directory, "after")
            need(final_link_identity == link_identity, "build_native_restoration_symlink_changed")
            _check_restoration_parent(terminal.parent, descriptors)
            result.append({**item, "action": "restored_selected_base_original",
                           "observed_before": observed_before, "observed_after": observed_after})
        except OSError as error:
            raise ValueError("build_native_restoration_io") from error
        finally:
            try:
                if staged is not None and descriptors and stage_identity is not None:
                    try:
                        current = os.stat(staged, dir_fd=descriptors[-1], follow_symlinks=False)
                        if (current.st_dev, current.st_ino) == (stage_identity.st_dev, stage_identity.st_ino):
                            os.unlink(staged, dir_fd=descriptors[-1])
                    except FileNotFoundError:
                        pass
            finally:
                for descriptor in reversed(descriptors):
                    os.close(descriptor)
    return result


def verify_native_restorations(selection: dict[str, object]) -> None:
    """Check the final layout after package triggers, without restoring again."""
    for item in _restoration_selection(selection):
        descriptors = []
        try:
            parent = Path(item["resolved_path"]).parent
            descriptors = _pin_restoration_parent(parent)
            _check_restoration_parent(parent, descriptors)
            _restoration_snapshot(item, descriptors[-1], "after")
            _check_restoration_parent(parent, descriptors)
        except OSError as error:
            raise ValueError("build_native_restoration_final_io") from error
        finally:
            for descriptor in reversed(descriptors):
                os.close(descriptor)


def install_original_objects(inputs: Path, selection: dict[str, object]) -> list[dict[str, object]]:
    """Install only absent selected DSO paths; existing objects must be exact.

    The launcher remains data in the build-input tree. The base loader and libc
    are required prerequisites and are never replaced by this installer.
    """
    expected = [{"input": name, "host_path": path,
        "installation": "retained_data_only" if path is None else
        "require_existing_exact" if name in {"native/libc.so.6", "native/ld-linux-x86-64.so.2"}
        else "install_if_absent_or_require_existing_exact", **NATIVE[name]}
        for name, path in NATIVE_HOST_PATHS.items()]
    need(selection.get("original_native_objects") == expected, "build_native_selection")
    need({path.name for path in (inputs / "native").iterdir()}
         == {Path(name).name for name in NATIVE}, "build_native_roster")
    result = []
    for item in expected:
        raw = read_regular(inputs / item["input"], 16 * 1024 * 1024)
        need(binding(raw) == NATIVE[item["input"]], "build_native_original_binding")
        target = item["host_path"]
        action, resolved = "retained_data_only", None
        if target is not None:
            path = Path(target)
            try:
                path.lstat()
            except FileNotFoundError:
                need(item["installation"] == "install_if_absent_or_require_existing_exact",
                     "build_required_native_missing")
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o644)
                with os.fdopen(fd, "wb") as output:
                    output.write(raw)
                    output.flush()
                    os.fsync(output.fileno())
                action = "installed_absent_original"
            else:
                action = "existing_original_verified"
            resolved = str(path.resolve(strict=True))
            need(read_regular(Path(resolved), 16 * 1024 * 1024) == raw,
                 "build_native_host_conflict")
        result.append({**item, "action": action, "resolved_path": resolved})
    return result


# RFC 8032 section 7.1, test 2. These are public verification inputs only.
KAT_PUBLIC = bytes.fromhex("3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c")
KAT_MESSAGE = bytes.fromhex("72")
KAT_SIGNATURE = bytes.fromhex(
    "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da"
    "085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00")
SPKI_PREFIX = bytes.fromhex("302a300506032b6570032100")


def check_openssl_backend(selection: dict[str, object]) -> dict[str, object]:
    """Exercise the pinned base's public-signature backend, never an original.

    Its configured files are checked on both sides. This build-time check does
    not replace the fresh positive/negative self-tests in request admission.
    No inherited OpenSSL configuration, provider setting, or key is accepted.
    """
    backend = selection["crypto_backend"]
    need(backend["path"] == "/usr/bin/openssl" and backend["suite"] == "ed25519"
         and backend["base_image_installed"] is True
         and backend["openssl_configuration"] == "/dev/null"
         and backend["positive_and_negative_known_answer_self_tests_required"] is True,
         "build_crypto_backend_selection")
    wanted = {item["path"]: {key: item[key] for key in ("sha256", "size_bytes")}
              for item in backend["runtime_files"]}
    for path, descriptor in wanted.items():
        need(binding(read_regular(Path(path).resolve(strict=True), descriptor["size_bytes"]))
             == descriptor, "build_crypto_runtime_binding")
    installed = installed_debian()
    need(all(installed.get(name) == version
             for name, version in backend["base_packages"].items()),
         "build_crypto_package_version")
    environment = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C",
                   "OPENSSL_CONF": "/dev/null"}
    deadline = time.monotonic() + 20

    def run(arguments, *, capture=False, cwd="/tmp"):
        remaining = deadline - time.monotonic()
        need(remaining > 0, "build_crypto_time_budget")
        # The executable and every selected runtime file were checked before
        # this fixed command. Verification output is discarded; only the short
        # version observation is retained in the bounded build record.
        return subprocess.run(["/usr/bin/openssl", *arguments], shell=False,
            cwd=cwd, env=environment, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, check=False, close_fds=True,
            timeout=min(10, remaining))

    version = run(["version"], capture=True)
    need(version.returncode == 0 and len(version.stdout) <= 256,
         "build_crypto_version")
    text = version.stdout.decode("ascii", errors="strict").strip()
    need(re.fullmatch(r"OpenSSL 3\.[0-9]+\.[ -~]+", text) is not None,
         "build_crypto_version")
    with tempfile.TemporaryDirectory(prefix="pulse-loader-resolution-crypto-", dir="/tmp") as temporary:
        directory = Path(temporary)
        public_inputs = {"key.der": SPKI_PREFIX + KAT_PUBLIC,
                         "signature.bin": KAT_SIGNATURE,
                         "bad-signature.bin": bytes([KAT_SIGNATURE[0] ^ 1]) + KAT_SIGNATURE[1:],
                         "message.bin": KAT_MESSAGE}
        for name, raw in public_inputs.items():
            write_new(directory / name, raw)
        common = ["pkeyutl", "-verify", "-pubin", "-inkey", "key.der",
                  "-keyform", "DER", "-rawin", "-in", "message.bin", "-sigfile"]
        positive = run([*common, "signature.bin"], cwd=str(directory))
        need(positive.returncode == 0, "build_crypto_positive_self_test")
        negative = run([*common, "bad-signature.bin"], cwd=str(directory))
        need(negative.returncode == 1, "build_crypto_negative_self_test")
    for path, descriptor in wanted.items():
        need(binding(read_regular(Path(path).resolve(strict=True), descriptor["size_bytes"]))
             == descriptor, "build_crypto_runtime_changed")
    return {"path": "/usr/bin/openssl", "binary_sha256": wanted["/usr/bin/openssl"]["sha256"],
            "version": text, "suite": "ed25519", "known_answer_self_test": "passed"}


def install(inputs: Path) -> dict[str, object]:
    inputs = Path(inputs)
    check_input_layout(inputs)
    need(sys.executable == PYTHON and sys.flags.isolated == 1, "build_python_executable")
    need(platform.python_version() == PYTHON_VERSION, "build_python_version")
    need(sys.platform == "linux" and platform.machine() == "x86_64", "build_platform")
    selection_raw = read_regular(inputs / "environment.json", MAX_CONTROL_BYTES)
    # No selected paths, native replacement or package subprocess is used until
    # the entire reviewed environment byte string has matched its source pin.
    need(hashlib.sha256(selection_raw).hexdigest() == ENVIRONMENT_SHA256,
         "build_environment_digest")
    selection = json.loads(selection_raw)
    need(selection["record_type"] == RECORD_TYPE and selection["profile"] == PROFILE,
         "build_record_type")
    need(selection["platform"] == "linux/amd64", "build_selected_platform")
    need(selection["base_image"]["reference"] == BASE_IMAGE, "build_base_image")
    need(selection["python"]["version"] == PYTHON_VERSION
         and selection["python"]["executable"] == PYTHON, "build_python_selection")
    need(selection["host_environment_qualified"] is False
         and selection["native_acquisition_performed"] is False, "build_scope")
    need(selection["authority_effect"] == "none", "build_authority_effect")
    helper_raw = read_regular(inputs / "build_environment.py", MAX_CONTROL_BYTES)
    lock_raw = read_regular(inputs / "requirements.lock", MAX_CONTROL_BYTES)
    need(binding(lock_raw) == selection["requirements"], "build_requirements_binding")
    python_packages = selection["python"]["packages"]
    need(len(python_packages) == len(PYTHON_PACKAGES)
         and {normalized_name(item["name"]): item["version"] for item in python_packages}
         == PYTHON_PACKAGES, "build_python_package_selection")
    expected_lock = ("\n".join(item["name"] + "==" + item["version"] + " --hash=sha256:"
                              + item["sha256"] for item in python_packages) + "\n").encode("ascii")
    need(lock_raw == expected_lock, "build_requirements_binding")
    check_downloads(inputs / "wheels", python_packages)
    debian = selection["debian"]
    packages = debian["packages"]
    need(len(packages) == len(OVERLAY) and {item["name"] for item in packages} == OVERLAY,
         "build_debian_overlay")
    need(debian["loader_already_present_in_base"] is True
         and debian["libc_installation_performed"] is False, "build_libc_scope")
    before = installed_debian()
    for item in debian["closure"]:
        need(before.get(item["name"]) == item["base_version"], "build_base_package_version")
        need(item["installation_required"] == (item["base_version"] != item["version"]),
             "build_package_delta")
    need({item["name"] for item in debian["closure"] if item["installation_required"]} == OVERLAY,
         "build_closure_delta")
    need(all(before.get(name) == version
             for name, version in selection["crypto_backend"]["base_packages"].items()),
         "build_crypto_package_version")
    debs = check_downloads(inputs / "debs", packages)
    check_native_inputs(inputs)
    native_restorations = restore_original_native_objects(inputs, selection)
    native_objects = install_original_objects(inputs, selection)
    check_runtime_files(selection, include_gpg=False)

    environment = {
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "DEBIAN_FRONTEND": "noninteractive",
        "PIP_NO_INDEX": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    # The exact closure is already present locally. No APT resolver, network
    # fallback, build from source or original launcher invocation is permitted.
    subprocess.run(["/usr/bin/dpkg", "--install", *(str(path) for path in debs)],
        env=environment, stdin=subprocess.DEVNULL, shell=False, check=True, timeout=300)
    subprocess.run([PYTHON, "-I", "-B", "-m", "pip", "install", "--no-index", "--no-deps",
        "--no-cache-dir", "--no-compile", "--require-hashes", "--only-binary=:all:",
        "--find-links=" + str(inputs / "wheels"), "-r", str(inputs / "requirements.lock")],
        env=environment, stdin=subprocess.DEVNULL, shell=False, check=True, timeout=300)
    subprocess.run([PYTHON, "-I", "-B", "-m", "pip", "check"],
        env=environment, stdin=subprocess.DEVNULL, shell=False, check=True, timeout=60)
    after = installed_debian()
    expected_after = dict(before)
    expected_after.update({item["name"]: item["version"] for item in packages})
    need(after == expected_after, "build_installed_package_delta")
    for item in debian["closure"]:
        need(after.get(item["name"]) == item["version"], "build_installed_package_version")
    for item in python_packages:
        need(importlib.metadata.version(item["name"]) == item["version"],
             "build_installed_python_version")
    checked = check_runtime_files(selection, include_gpg=True)
    verify_native_restorations(selection)
    backend = check_openssl_backend(selection)
    need(check_runtime_files(selection, include_gpg=True) == checked, "build_runtime_changed")
    # Recheck the complete selected input tree after the trusted installers.
    # All payloads remain in the image; the controller separately preserves
    # these same inputs for the second job's offline environment reconstruction.
    check_input_layout(inputs)
    need(read_regular(inputs / "environment.json", MAX_CONTROL_BYTES) == selection_raw
         and read_regular(inputs / "requirements.lock", MAX_CONTROL_BYTES) == lock_raw
         and read_regular(inputs / "build_environment.py", MAX_CONTROL_BYTES) == helper_raw,
         "build_input_drift")
    check_downloads(inputs / "debs", packages)
    check_downloads(inputs / "wheels", python_packages)
    check_native_inputs(inputs)
    record = {
        "record_type": "required_gate_idempotence_loader_resolution_hosted_environment_build_v0",
        "profile": PROFILE,
        "environment_selection": binding(selection_raw),
        "requirements_lock": binding(lock_raw),
        "base_image_reference": BASE_IMAGE,
        "python_version": platform.python_version(),
        "installed_debian_delta": [{"name": item["name"], "version": after[item["name"]]}
                                   for item in packages],
        "selected_python_packages": [{"name": item["name"],
                                      "version": importlib.metadata.version(item["name"])}
                                     for item in python_packages],
        "checked_files": checked,
        "original_native_objects": native_objects,
        "native_object_restorations": native_restorations,
        "openssl_backend": backend,
        "offline_install": True,
        "reproducible_image_claimed": False,
        "host_environment_qualified": False,
        "native_acquisition_performed": False,
        "authority_effect": "none",
    }
    raw = (json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False) + "\n").encode("ascii")
    write_new(inputs / "build-environment-record.json", raw)
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", required=True, type=Path)
    args = parser.parse_args()
    try:
        record = install(args.inputs)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, importlib.metadata.PackageNotFoundError) as error:
        print("offline environment build rejected: " + str(error), file=sys.stderr)
        return 2
    print(json.dumps(record, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

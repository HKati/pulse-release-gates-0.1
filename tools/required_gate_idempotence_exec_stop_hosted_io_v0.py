#!/usr/bin/env python3
"""Bounded byte transport for the fixed hosted exec-stop workflow.

This module uses the standard library only.  Copying or extracting selected
bytes never imports or executes them.  The bounded process helper preserves
the reviewed command chosen by its caller.  New directories and files are
private and exclusive.  A failed copy or extraction leaves its already written
prefix in place for the workflow's failure artifact.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import signal
import stat
import subprocess
import time
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_REL = "preservation/required_gate_idempotence_exec_stop_v0/original_inputs_v0.zip"
SELECTION_REL = "preservation/required_gate_idempotence_exec_stop_v0/ORIGINAL_INPUTS.json"
SELECTION_SHA256 = "7898e8c3e9af528240be8d622a2346fcee945db530fd27a7ad64c32f7084e671"
SELECTION_SIZE = 22287
ARCHIVE_SHA256 = "70b57f9a40cb375e267e215b3704be21c9f6d8987cadc13d92dfcc8db56d9c8a"
ARCHIVE_SIZE = 24816167
MANIFEST_SHA256 = "16c541b8fd733dcef1b495b104b5377d11624b6106fbfa740e5ec6eb856cdfaa"
MANIFEST_SIZE = 20420
ORIGINAL_MEMBER_COUNT = 114
ORIGINAL_DECODED_BYTES = 72234203
FILE_LIMIT = 256 * 1024 * 1024
TOTAL_LIMIT = 512 * 1024 * 1024
MEMBER_LIMIT = 4096
READ_FLAGS = os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
DIGEST_RE = re.compile(r"[0-9a-f]{64}\Z")
PATH_PART_RE = re.compile(r"[A-Za-z0-9_.+~-]{1,200}\Z")


class HostedIOError(ValueError):
    """A stable transport rejection code, without paths or external diagnostics."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise HostedIOError(code)


def sha(raw):
    _need(type(raw) is bytes, "hosted_io_bytes")
    return hashlib.sha256(raw).hexdigest()


def binding(raw):
    return {"sha256": sha(raw), "size_bytes": len(raw)}


def canonical(value):
    try:
        return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise HostedIOError("hosted_io_json_value") from exc


def _pairs(pairs):
    out = {}
    for name, value in pairs:
        _need(name not in out, "hosted_io_duplicate_key")
        out[name] = value
    return out


def _constant(_value):
    raise HostedIOError("hosted_io_nonfinite_json")


def _parse(raw):
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                          parse_constant=_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise HostedIOError("hosted_io_json") from exc


def _keys(value, expected, code):
    _need(type(value) is dict and set(value) == set(expected), code)


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_uid, info.st_gid, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _dir_identity(info):
    # Creating an owned child legitimately changes the parent's times/link count.
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid)


def _absolute(path):
    try:
        value = os.fspath(path)
        _need(type(value) is str and value and "\0" not in value
              and ".." not in value.split("/"), "hosted_io_path")
        result = Path(value)
        return result if result.is_absolute() else Path.cwd() / result
    except (TypeError, ValueError, OSError) as exc:
        if isinstance(exc, HostedIOError):
            raise
        raise HostedIOError("hosted_io_path") from exc


def _relative(name):
    _need(type(name) is str and 0 < len(name) <= 512 and "\\" not in name,
          "hosted_io_member_path")
    path = PurePosixPath(name)
    _need(bool(path.parts) and not path.is_absolute() and path.as_posix() == name
          and all(part not in {".", ".."} and PATH_PART_RE.fullmatch(part)
                  for part in path.parts), "hosted_io_member_path")
    return path.parts


def _close_chain(chain):
    for _parent, _name, fd, _identity_value in reversed(chain):
        os.close(fd)


def _check_chain(chain):
    for parent, name, fd, wanted in chain:
        current = os.fstat(fd)
        _need(stat.S_ISDIR(current.st_mode) and _dir_identity(current) == wanted,
              "hosted_io_directory_changed")
        linked = os.stat("/", follow_symlinks=False) if parent is None else os.stat(
            name, dir_fd=parent, follow_symlinks=False)
        _need(_dir_identity(linked) == wanted, "hosted_io_directory_changed")


def _append_directory(parent, name, chain):
    before = os.stat(name, dir_fd=parent, follow_symlinks=False)
    _need(stat.S_ISDIR(before.st_mode), "hosted_io_directory_type")
    fd = os.open(name, DIR_FLAGS, dir_fd=parent)
    try:
        after = os.fstat(fd)
        _need(_dir_identity(before) == _dir_identity(after),
              "hosted_io_directory_changed")
        chain.append((parent, name, fd, _dir_identity(after)))
        return fd
    except BaseException:
        os.close(fd)
        raise


def _pin_directory(path):
    chain = []
    try:
        path = _absolute(path)
        fd = os.open("/", DIR_FLAGS)
        chain.append((None, "/", fd, _dir_identity(os.fstat(fd))))
        for name in path.parts[1:]:
            fd = _append_directory(fd, name, chain)
        _check_chain(chain)
        return fd, chain
    except BaseException:
        _close_chain(chain)
        raise


def _read_at(parent, name, limit, private=False):
    _need(type(limit) is int and 0 <= limit <= FILE_LIMIT
          and type(private) is bool, "hosted_io_read_bound")
    before = os.stat(name, dir_fd=parent, follow_symlinks=False)
    _need(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= limit,
          "hosted_io_file_type_or_size")
    if private:
        _need(stat.S_IMODE(before.st_mode) == 0o600 and before.st_nlink == 1,
              "hosted_io_private_file")
    # NONBLOCK precedes descriptor identity validation: a substituted FIFO must
    # not wait for a writer before it can be rejected.
    fd = os.open(name, READ_FLAGS, dir_fd=parent)
    try:
        opened = os.fstat(fd)
        _need(stat.S_ISREG(opened.st_mode) and _identity(before) == _identity(opened),
              "hosted_io_file_changed")
        chunks, length = [], 0
        while length <= limit:
            chunk = os.read(fd, min(65536, limit + 1 - length))
            if not chunk:
                break
            chunks.append(chunk)
            length += len(chunk)
        after = os.fstat(fd)
        linked = os.stat(name, dir_fd=parent, follow_symlinks=False)
        _need(length == before.st_size and _identity(before) == _identity(after)
              == _identity(linked), "hosted_io_file_changed")
        return b"".join(chunks)
    finally:
        os.close(fd)


def read_regular(path, limit, private=False):
    """Read one bounded regular file through pinned, non-symlink ancestors."""
    chain = []
    try:
        path = _absolute(path)
        _need(path.name not in {"", "/"}, "hosted_io_path")
        parent, chain = _pin_directory(path.parent)
        raw = _read_at(parent, path.name, limit, private)
        _check_chain(chain)
        return raw
    except OSError as exc:
        raise HostedIOError("hosted_io_read_failed") from exc
    finally:
        _close_chain(chain)


def _write_at(parent, name, raw):
    _need(type(raw) is bytes and len(raw) <= FILE_LIMIT, "hosted_io_write_bound")
    fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
                 | os.O_NONBLOCK | os.O_CLOEXEC, 0o600, dir_fd=parent)
    try:
        os.fchmod(fd, 0o600)
        remaining = memoryview(raw)
        while remaining:
            written = os.write(fd, remaining)
            _need(written > 0, "hosted_io_write_incomplete")
            remaining = remaining[written:]
        os.fsync(fd)
        os.lseek(fd, 0, os.SEEK_SET)
        preserved = hashlib.sha256()
        length = 0
        while length <= len(raw):
            piece = os.read(fd, min(65536, len(raw) + 1 - length))
            if not piece:
                break
            preserved.update(piece)
            length += len(piece)
        info = os.fstat(fd)
        _need(stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o600
              and info.st_nlink == 1 and info.st_size == length == len(raw)
              and preserved.hexdigest() == sha(raw)
              and _identity(info) == _identity(os.stat(
                  name, dir_fd=parent, follow_symlinks=False)), "hosted_io_write_changed")
        os.fsync(parent)
    finally:
        os.close(fd)


def write_new(path, raw):
    """Write/read-back one private exclusive file; leave any failed prefix."""
    chain = []
    try:
        path = _absolute(path)
        _need(path.name not in {"", "/"}, "hosted_io_path")
        parent, chain = _pin_directory(path.parent)
        _write_at(parent, path.name, raw)
        _check_chain(chain)
        return binding(raw)
    except OSError as exc:
        raise HostedIOError("hosted_io_write_failed") from exc
    finally:
        _close_chain(chain)


def _descriptor(value):
    _keys(value, {"sha256", "size_bytes"}, "hosted_io_binding")
    _need(type(value["sha256"]) is str and DIGEST_RE.fullmatch(value["sha256"])
          and type(value["size_bytes"]) is int and 0 <= value["size_bytes"] <= FILE_LIMIT,
          "hosted_io_binding")


def _inventory(expected_files):
    _need(type(expected_files) is dict and 0 < len(expected_files) <= MEMBER_LIMIT,
          "hosted_io_inventory")
    _need(all(type(name) is str for name in expected_files), "hosted_io_member_path")
    tree, total = {}, 0
    for name, wanted in sorted(expected_files.items()):
        parts = _relative(name)
        _descriptor(wanted)
        total += wanted["size_bytes"]
        _need(total <= TOTAL_LIMIT, "hosted_io_total_size")
        node = tree
        for part in parts[:-1]:
            _need(part not in node or node[part][0] == "directory", "hosted_io_path_collision")
            node = node.setdefault(part, ("directory", {}))[1]
        _need(parts[-1] not in node, "hosted_io_path_collision")
        node[parts[-1]] = ("file", wanted)
    return tree, total


def original_selection():
    """Return the fixed closed selection, anchored outside its own JSON fields."""
    raw = read_regular(ROOT / SELECTION_REL, SELECTION_SIZE)
    _need(len(raw) == SELECTION_SIZE and sha(raw) == SELECTION_SHA256,
          "hosted_io_selection_digest")
    value = _parse(raw)
    _keys(value, {"format", "record_status", "archive", "member_count", "decoded_bytes",
                  "case_manifest", "case_member_count", "historical_source_count",
                  "original_case_base_commit", "report_bindings", "source_validation_archive",
                  "archive_entry_profile", "files", "notices", "original_artifacts", "scope"},
          "hosted_io_selection_fields")
    _need(value["format"] == "required_gate_idempotence_exec_stop_original_inputs_v0"
          and value["record_status"] == "preserved_input"
          and value["archive"] == {"path": ARCHIVE_REL, "sha256": ARCHIVE_SHA256,
                                    "size_bytes": ARCHIVE_SIZE}
          and value["member_count"] == ORIGINAL_MEMBER_COUNT
          and value["decoded_bytes"] == ORIGINAL_DECODED_BYTES
          and value["case_member_count"] == 111 and value["historical_source_count"] == 43
          and value["case_manifest"] == {"path": "CASE_INPUTS.json", "sha256": MANIFEST_SHA256,
                                          "size_bytes": MANIFEST_SIZE}, "hosted_io_selection_profile")
    _need(value["archive_entry_profile"] == {
        "compression_method": 8, "unix_mode": 384, "timestamp": [2026, 11, 17, 20, 11, 6],
        "timestamp_is_acquisition_time": False}, "hosted_io_selection_profile")
    _need(value["original_case_base_commit"] == "bc5cc2f121aae200c805db24254912d16a1759db"
          and value["source_validation_archive"] == {
              "file_name": "B2_EXEC_618a703_02_VALIDATION.zip", "size_bytes": 42296536,
              "sha256": "662ce65753ed92f03e613cbd2322a838ca450f05fb5622470889fe3f21a15e94"},
          "hosted_io_selection_origin")
    _need(value["scope"] == {
        "original_case_format": "launcher_distribution_original_byte_example_v0",
        "original_case_status": "example", "authored_inert_runtime_capsule": True,
        "fresh_signature_verification_required": True, "signature_evaluation_epoch": 1794787200,
        "native_distribution_origin_claim_extended": False, "original_network_inputs_recollected": False,
        "original_launcher_executed_by_preservation": False, "selected_runtime_executed": False,
        "authority_effect": "none"}, "hosted_io_selection_scope")
    _tree, total = _inventory(value["files"])
    _need(len(value["files"]) == ORIGINAL_MEMBER_COUNT and total == ORIGINAL_DECODED_BYTES,
          "hosted_io_selection_inventory")
    _need(value["notices"] == sorted(name for name in value["files"] if name.startswith("notices/"))
          and len(value["notices"]) == 5, "hosted_io_selection_notices")
    _need(value["original_artifacts"] == {name: item for name, item in value["files"].items()
                                          if name.startswith("original-artifacts/")}
          and len(value["original_artifacts"]) == 2, "hosted_io_selection_artifacts")
    reports = [{"path": "results/checker-" + str(n) + ".json",
                "sha256": "a0d7cf825dce1c8a3b09a2306f155f24bdcabc4a16cb90215f6d4e04925f4f36",
                "size_bytes": 3780} for n in (1, 2)]
    _need(value["report_bindings"] == reports, "hosted_io_selection_reports")
    return value


@contextmanager
def _new_directory(destination):
    chain = []
    try:
        path = _absolute(destination)
        parent, chain = _pin_directory(path.parent)
        os.mkdir(path.name, 0o700, dir_fd=parent)
        root = _append_directory(parent, path.name, chain)
        os.fchmod(root, 0o700)
        # fchmod's effect is part of the newly created selected directory.
        chain[-1] = (parent, path.name, root, _dir_identity(os.fstat(root)))
        _check_chain(chain)
        yield root, chain
        _check_chain(chain)
        os.fsync(root)
        os.fsync(parent)
    finally:
        _close_chain(chain)


def _write_tree(root, chain, files):
    directories = {(): root}
    for name, raw in sorted(files.items()):
        parts = _relative(name)
        prefix, parent = (), root
        for part in parts[:-1]:
            prefix += (part,)
            if prefix not in directories:
                os.mkdir(part, 0o700, dir_fd=parent)
                child = _append_directory(parent, part, chain)
                os.fchmod(child, 0o700)
                chain[-1] = (parent, part, child, _dir_identity(os.fstat(child)))
                directories[prefix] = child
            parent = directories[prefix]
        _check_chain(chain)
        _write_at(parent, parts[-1], raw)
    # Recheck each preserved file after all writes, with private modes enforced.
    for name, raw in sorted(files.items()):
        parts = _relative(name)
        _need(_read_at(directories[parts[:-1]], parts[-1], len(raw), True) == raw,
              "hosted_io_preserved_bytes_changed")
    _check_chain(chain)


def _archive_members(raw, selection):
    expected = selection["files"]
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            names = [item.filename for item in infos]
            _need(len(infos) == ORIGINAL_MEMBER_COUNT and len(set(names)) == len(names)
                  and set(names) == set(expected), "hosted_io_archive_roster")
            _need(not archive.comment, "hosted_io_archive_metadata")
            total, files = 0, {}
            for info in infos:
                _relative(info.filename)
                wanted = expected[info.filename]
                mode = info.external_attr >> 16
                _need(not info.is_dir() and info.orig_filename == info.filename
                      and info.create_system == 3 and stat.S_ISREG(mode)
                      and stat.S_IMODE(mode) == 0o600 and info.compress_type == zipfile.ZIP_DEFLATED
                      and info.flag_bits & 1 == 0 and not info.extra and not info.comment
                      and list(info.date_time) == selection["archive_entry_profile"]["timestamp"]
                      and info.file_size == wanted["size_bytes"]
                      and 0 <= info.compress_size <= len(raw), "hosted_io_archive_member")
                total += info.file_size
                _need(total <= ORIGINAL_DECODED_BYTES, "hosted_io_archive_size")
                with archive.open(info, "r") as source:
                    value = source.read(info.file_size + 1)
                _need(binding(value) == wanted, "hosted_io_archive_member_digest")
                files[info.filename] = value
            _need(total == ORIGINAL_DECODED_BYTES, "hosted_io_archive_size")
            manifest_raw = files["CASE_INPUTS.json"]
            _need(len(manifest_raw) == MANIFEST_SIZE and sha(manifest_raw) == MANIFEST_SHA256,
                  "hosted_io_original_manifest")
            manifest = _parse(manifest_raw)
            _need(type(manifest) is dict and manifest.get("record_type")
                  == "launcher_distribution_original_byte_example_v0"
                  and manifest.get("record_status") == "example"
                  and type(manifest.get("files")) is dict and len(manifest["files"]) == 111,
                  "hosted_io_original_manifest")
            expected_members = set(manifest["files"]) | {"CASE_INPUTS.json", "results/checker-1.json",
                                                        "results/checker-2.json"}
            _need(expected_members == set(expected)
                  and all(expected[name] == item for name, item in manifest["files"].items()),
                  "hosted_io_original_roster")
            return files
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError, EOFError, zlib.error) as exc:
        raise HostedIOError("hosted_io_archive_invalid") from exc


def extract_originals(archive_path, destination):
    """Verify the fixed ZIP, then create exactly its 114 private original files."""
    try:
        selection = original_selection()
        raw = read_regular(archive_path, selection["archive"]["size_bytes"])
        selected_binding = {key: selection["archive"][key] for key in ("sha256", "size_bytes")}
        _need(binding(raw) == selected_binding, "hosted_io_archive_digest")
        files = _archive_members(raw, selection)
        with _new_directory(destination) as (root, chain):
            _write_tree(root, chain, files)
        return {"archive": selected_binding, "manifest": binding(files["CASE_INPUTS.json"]),
                "member_count": len(files), "decoded_bytes": sum(map(len, files.values()))}
    except OSError as exc:
        raise HostedIOError("hosted_io_extraction_failed") from exc


def _read_tree(fd, tree, chain, prefix, files):
    _need(set(os.listdir(fd)) == set(tree), "hosted_io_tree_roster")
    for name, (kind, value) in sorted(tree.items()):
        relative = "/".join((*prefix, name))
        if kind == "directory":
            child = _append_directory(fd, name, chain)
            _read_tree(child, value, chain, (*prefix, name), files)
        else:
            raw = _read_at(fd, name, value["size_bytes"])
            _need(binding(raw) == value, "hosted_io_tree_digest")
            files[relative] = raw
    _need(set(os.listdir(fd)) == set(tree), "hosted_io_tree_roster")


def copy_private_tree(source, destination, expected_files):
    """Copy an exact externally selected file roster into a fresh private tree.

    The roster is a mapping of relative paths to {sha256, size_bytes}.  Extra
    source files/directories, symlinks and changed bytes reject the copy.  This
    is transport and mode restoration, not capture acceptance.
    """
    chain = []
    try:
        source, destination = _absolute(source), _absolute(destination)
        _need(source != destination and source not in destination.parents,
              "hosted_io_copy_destination")
        tree, total = _inventory(expected_files)
        root, chain = _pin_directory(source)
        files = {}
        _read_tree(root, tree, chain, (), files)
        _check_chain(chain)
        with _new_directory(destination) as (output, output_chain):
            _write_tree(output, output_chain, files)
        _check_chain(chain)
        return {"member_count": len(files), "decoded_bytes": total}
    except OSError as exc:
        raise HostedIOError("hosted_io_copy_failed") from exc
    finally:
        _close_chain(chain)


def run_command(argv, logdir, label, timeout_seconds, stream_cap=4194304, env=None,
                *, stdout_cap=None):
    """Run one caller-selected fixed command with bounded private diagnostics.

    There is no command-line interface for arbitrary executables.  The workflow
    and container runner supply their reviewed argv; credentials belong in env,
    which is never included in a record.  Ordinary nonzero exits are returned,
    not raised.  Invalid arguments or failed preservation raise HostedIOError.
    stdout_cap optionally selects a larger bound for the preserved Docker base
    image archive; stderr always retains the ordinary stream_cap bound.

    A child stays unreaped until group termination is no longer needed, using
    waitid(WNOWAIT), so a timeout cannot signal a reused process-group identity.
    User-space deadlines do not promise kernel-operation preemption.
    """
    _need(type(argv) in (list, tuple) and 0 < len(argv) <= 128
          and all(type(arg) is str and "\0" not in arg and len(arg) <= 16384 for arg in argv)
          and bool(argv[0]) and sum(map(len, argv)) <= 65536, "hosted_process_argv")
    _need(type(label) is str and re.fullmatch(r"[a-z0-9-]{1,64}", label),
          "hosted_process_label")
    _need(type(timeout_seconds) in (int, float) and math.isfinite(timeout_seconds)
          and 0 < timeout_seconds <= 3600 and type(stream_cap) is int
          and 0 < stream_cap <= 16 * 1024 * 1024, "hosted_process_limits")
    _need(stdout_cap is None or (type(stdout_cap) is int and 0 < stdout_cap <= FILE_LIMIT),
          "hosted_process_stdout_cap")
    limits = {"stdout": stream_cap if stdout_cap is None else stdout_cap,
              "stderr": stream_cap}
    _need(env is None or (type(env) is dict and all(
        type(name) is str and name and "=" not in name and "\0" not in name
        and type(value) is str and "\0" not in value for name, value in env.items())),
        "hosted_process_environment")
    _need(all(hasattr(os, name) for name in ("waitid", "WNOWAIT", "P_PID")),
          "hosted_process_wait_interface")
    chain, sinks, pipes = [], {}, {}
    selector = selectors.DefaultSelector()
    process = None
    reaped = False
    killed = False
    kill_error = None
    failure = None
    returncode = None
    overflowed = []
    counts = {"stdout": 0, "stderr": 0}
    started = time.monotonic()

    def consume(name, raw):
        nonlocal failure
        remaining = limits[name] - counts[name]
        kept = raw[:remaining]
        view = memoryview(kept)
        while view:
            written = os.write(sinks[name], view)
            _need(written > 0, "hosted_process_preservation_failed")
            view = view[written:]
        counts[name] += len(kept)
        if len(raw) > remaining:
            if name not in overflowed:
                overflowed.append(name)
            if failure is None:
                failure = "hosted_process_" + name + "_limit"

    def kill_owned_group():
        nonlocal killed, kill_error
        if process is not None and not reaped:
            try:
                os.killpg(process.pid, signal.SIGKILL)
                killed = True
            except ProcessLookupError:
                pass
            except OSError as exc:
                kill_error = exc.errno

    def reap_owned_child():
        nonlocal reaped, returncode, failure
        if process is not None and not reaped:
            try:
                returncode = process.wait(timeout=5)
                reaped = True
            except subprocess.TimeoutExpired:
                if failure is None:
                    failure = "hosted_process_cleanup_timeout"

    def drain_pending():
        # Both independently capped streams are drained after stopping/reaping;
        # an overflow on one must not discard already buffered bytes on the other.
        for name, pipe in pipes.items():
            os.set_blocking(pipe.fileno(), False)
            while counts[name] < limits[name]:
                try:
                    raw = os.read(pipe.fileno(), min(65536, limits[name] - counts[name] + 1))
                except BlockingIOError:
                    break
                if not raw:
                    break
                consume(name, raw)

    try:
        path = _absolute(logdir)
        parent, chain = _pin_directory(path.parent)
        created = False
        try:
            os.mkdir(path.name, 0o700, dir_fd=parent)
            created = True
        except FileExistsError:
            pass
        root = _append_directory(parent, path.name, chain)
        if created:
            os.fchmod(root, 0o700)
            chain[-1] = (parent, path.name, root, _dir_identity(os.fstat(root)))
        root_info = os.fstat(root)
        _need(stat.S_IMODE(root_info.st_mode) == 0o700 and root_info.st_uid == os.geteuid(),
              "hosted_process_log_mode")
        _check_chain(chain)
        suffixes = ("argv.json", "stdout.bin", "stderr.bin", "result.json")
        for suffix in suffixes:
            try:
                os.stat(label + "." + suffix, dir_fd=root, follow_symlinks=False)
            except FileNotFoundError:
                continue
            raise HostedIOError("hosted_process_log_exists")
        _write_at(root, label + ".argv.json", canonical({"argv": list(argv)}))
        for name in counts:
            fd = os.open(label + "." + name + ".bin",
                         os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
                         | os.O_NONBLOCK | os.O_CLOEXEC, 0o600, dir_fd=root)
            sinks[name] = fd
            os.fchmod(fd, 0o600)
        try:
            process = subprocess.Popen(list(argv), stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       close_fds=True, start_new_session=True, env=env)
        except (OSError, ValueError):
            failure = "hosted_process_start_failed"
        if process is not None:
            pipes = {"stdout": process.stdout, "stderr": process.stderr}
            for name, pipe in pipes.items():
                os.set_blocking(pipe.fileno(), False)
                selector.register(pipe.fileno(), selectors.EVENT_READ, name)
            deadline = time.monotonic() + timeout_seconds
            terminal = False
            while True:
                try:
                    terminal = os.waitid(os.P_PID, process.pid,
                                         os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None
                except InterruptedError:
                    continue
                except ChildProcessError:
                    # Another reaper invalidates ownership; never signal that PID.
                    reaped = True
                    failure = "hosted_process_ownership_lost"
                    break
                if terminal and not selector.get_map():
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    failure = "hosted_process_deadline"
                    break
                for key, _mask in selector.select(min(0.1, remaining)):
                    try:
                        raw = os.read(key.fd, min(65536, limits[key.data] - counts[key.data] + 1))
                    except BlockingIOError:
                        continue
                    if not raw:
                        selector.unregister(key.fd)
                        continue
                    consume(key.data, raw)
                if failure is not None:
                    break
            if failure is not None:
                kill_owned_group()
            reap_owned_child()
            drain_pending()
        _check_chain(chain)
        stream_bindings = {}
        for name, fd in sinks.items():
            os.fsync(fd)
            raw = _read_at(root, label + "." + name + ".bin", limits[name], True)
            _need(len(raw) == counts[name]
                  and _identity(os.fstat(fd)) == _identity(os.stat(
                      label + "." + name + ".bin", dir_fd=root, follow_symlinks=False)),
                  "hosted_process_preservation_failed")
            stream_bindings[name] = binding(raw)
        result = {
            "argv": list(argv), "returncode": returncode, "failure": failure,
            "stdout": stream_bindings["stdout"], "stderr": stream_bindings["stderr"],
            "timeout_seconds": timeout_seconds, "stream_cap": stream_cap,
            "stdout_cap": limits["stdout"],
            "overflowed_streams": sorted(overflowed),
            "elapsed_seconds": time.monotonic() - started,
            "cleanup": {"child_started": process is not None, "child_reaped": reaped,
                        "kill_group_sent": killed, "kill_error_errno": kill_error,
                        "pending_output_drain_attempted": process is not None},
        }
        _write_at(root, label + ".result.json", canonical(result))
        _check_chain(chain)
        return result
    except BaseException as exc:
        kill_owned_group()
        reap_owned_child()
        try:
            drain_pending()
        except (OSError, ValueError):
            pass  # A failed sink cannot become a complete preservation record.
        if isinstance(exc, HostedIOError):
            raise
        if not isinstance(exc, (OSError, ValueError)):
            raise
        raise HostedIOError("hosted_process_preservation_failed") from exc
    finally:
        selector.close()
        for pipe in pipes.values():
            pipe.close()
        for fd in sinks.values():
            os.close(fd)
        _close_chain(chain)

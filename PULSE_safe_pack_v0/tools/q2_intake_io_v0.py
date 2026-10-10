#!/usr/bin/env python3
"""Non-executing, bounded Q2 transport and private IO primitives.

This shared substrate is not an independent semantic verdict. Archive sources
and release payloads are data, never imports or executable validation helpers.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import stat
import struct
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

PACK = "PULSE_safe_pack_v0/"
PROFILE_PATH = PACK + "profiles/q2_reference_release_intake_v0.json"
SELECTION_PATH = PACK + "profiles/q2_reference_subject_v0.json"
REQUEST_SCHEMA = "schemas/q2_release_intake_request_v0.schema.json"
RESULT_SCHEMA = "schemas/q2_release_intake_result_v0.schema.json"
CAPSULE_SCHEMA = "schemas/q2_release_subject_capsule_v0.schema.json"
PUBLIC_RESULT = PACK + "artifacts/required_gate_inputs/q2_intake_result_v0.json"
WORKER = PACK + "tools/run_q2_reference_subject_v0.py"
REDUCER = PACK + "tools/build_q2_reference_summary.py"
CHECKER = PACK + "tools/check_q2_reference_summary.py"
SOURCE_PATHS = (
    PROFILE_PATH, REQUEST_SCHEMA, RESULT_SCHEMA, CAPSULE_SCHEMA, SELECTION_PATH,
    PACK + "profiles/q2_reference_model_files_v0.json",
    PACK + "examples/q2_reference_field_extraction_v0/requests.json",
    REDUCER, CHECKER, "metrics/specs/q2_consistency_v0.yml",
    "schemas/metrics/q2_consistency_input_v0.schema.json",
    "schemas/metrics/q2_consistency_summary_v0.schema.json",
    "schemas/dataset_manifest.schema.json",
    *(PACK + "tools/" + name + ".py" for name in (
        "q2_intake_io_v0", "load_q2_release_intake_v0",
        "evaluate_q2_archived_capture_v0", "check_q2_release_intake_v0",
        "evaluate_required_gate_v0", "run_recorded_required_gate_evaluations_v0",
        "build_release_grade_candidate_status_v0")),
    ".github/workflows/pulse_ci.yml",
)
Q2_ENV = frozenset({"PULSE_Q2_INTAKE_REQUEST", "PULSE_Q2_INTAKE_REQUEST_SHA256",
                    "PULSE_Q2_TRANSPORT_TOKEN", "PULSE_Q2_SUPERVISOR_ROOT"})
ERROR_CODES = frozenset({
    "q2_request_missing", "q2_request_invalid", "q2_request_digest_mismatch",
    "q2_context_rejected", "q2_selection_mismatch", "q2_source_mismatch",
    "q2_credential_missing", "q2_transport_rejected", "q2_input_unavailable",
    "q2_file_rejected", "q2_unstable_input", "q2_digest_mismatch",
    "q2_archive_rejected", "q2_archive_limit", "q2_json_rejected",
    "q2_schema_rejected", "q2_capture_rejected", "q2_subject_mismatch",
    "q2_replay_environment", "q2_replay_rejected", "q2_summary_mismatch",
    "q2_min_eligible_groups_not_met", "q2_metric_failed", "q2_timeout",
    "q2_cleanup_failed", "q2_public_record_rejected", "q2_admission_rejected",
    "q2_internal_error",
})


class IntakeError(ValueError):
    """Only a fixed code may cross the public boundary."""
    def __init__(self, code):
        self.code = code if code in ERROR_CODES else "q2_internal_error"
        super().__init__(self.code)


def require(condition, code):
    if not condition:
        raise IntakeError(code)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def strict_json(raw, maximum=16 * 1024 * 1024):
    require(type(raw) is bytes and 0 < len(raw) <= maximum
            and not raw.startswith(b"\xef\xbb\xbf"), "q2_json_rejected")
    def pairs(items):
        require(len({k for k, _ in items}) == len(items), "q2_json_rejected")
        return dict(items)
    def invalid(_):
        raise IntakeError("q2_json_rejected")
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"),
                           object_pairs_hook=pairs, parse_constant=invalid)
        require(type(value) is dict, "q2_json_rejected")
        stack, nodes = [(value, 0)], 0
        while stack:
            item, depth = stack.pop()
            nodes += 1
            require(depth <= 48 and nodes <= 500000, "q2_json_rejected")
            if type(item) is str:
                item.encode("utf-8", errors="strict")
            elif type(item) is float:
                require(math.isfinite(item), "q2_json_rejected")
            elif type(item) is dict:
                stack.extend((x, depth + 1) for pair in item.items() for x in pair)
            elif type(item) is list:
                stack.extend((x, depth + 1) for x in item)
        return value
    except (ValueError, UnicodeError, RecursionError) as exc:
        if isinstance(exc, IntakeError):
            raise
        raise IntakeError("q2_json_rejected") from None


def validate(value, schema_raw):
    # The transport credential is never an argument or a schema-process env var.
    from jsonschema import Draft202012Validator
    try:
        schema = strict_json(schema_raw)
        Draft202012Validator.check_schema(schema)
        require(Draft202012Validator(schema).is_valid(value), "q2_schema_rejected")
    except IntakeError:
        raise
    except Exception:
        raise IntakeError("q2_schema_rejected") from None


class Deadline:
    def __init__(self, seconds):
        require(type(seconds) in (int, float) and 0 < seconds <= 900, "q2_timeout")
        self.end = time.monotonic() + seconds

    def remaining(self, cap=30):
        left = self.end - time.monotonic()
        require(left > 0, "q2_timeout")
        return min(left, cap)


@contextmanager
def interrupt_boundary(seconds):
    """Handled TERM/INT and wall-clock deadlines execute the private finally path.

    SIGKILL/host loss cannot execute this handler and create no deletion proof.
    """
    require(hasattr(signal, "setitimer"), "q2_context_rejected")
    def cancelled(_signum, _frame):
        raise IntakeError("q2_timeout")
    old = {s: signal.signal(s, cancelled) for s in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM)}
    previous = signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield Deadline(seconds)
    finally:
        signal.setitimer(signal.ITIMER_REAL, *previous)
        for s, handler in old.items():
            signal.signal(s, handler)


def _open_regular(path):
    """Open every component relative to a held directory descriptor, no symlinks."""
    path = Path(path).absolute()
    require(".." not in path.parts, "q2_file_rejected")
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    parent = os.open("/", flags | os.O_DIRECTORY)
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, flags | os.O_DIRECTORY, dir_fd=parent)
            os.close(parent)
            parent = child
        fd = os.open(path.name, flags, dir_fd=parent)
    except OSError:
        raise IntakeError("q2_file_rejected") from None
    finally:
        os.close(parent)
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        os.close(fd)
        raise IntakeError("q2_file_rejected")
    return fd, info


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def read_file(path, maximum, expected=None, deadline=None):
    fd, before = _open_regular(path)
    try:
        require(0 <= before.st_size <= maximum, "q2_file_rejected")
        parts, size = [], 0
        while True:
            if deadline:
                deadline.remaining()
            part = os.read(fd, min(65536, maximum + 1 - size))
            if not part:
                break
            size += len(part)
            require(size <= maximum, "q2_file_rejected")
            parts.append(part)
        require(size == before.st_size and _identity(before) == _identity(os.fstat(fd)),
                "q2_unstable_input")
    finally:
        os.close(fd)
    raw = b"".join(parts)
    if expected is not None:
        require(type(expected) is str and re.fullmatch(r"[0-9a-f]{64}", expected)
                and digest(raw) == expected, "q2_digest_mismatch")
    return raw


def write_new(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)


def file_binding(path, maximum, deadline):
    """Stream a held regular file; a large capsule is never read into one buffer."""
    fd, before = _open_regular(path)
    try:
        require(0 < before.st_size <= maximum, "q2_file_rejected")
        hashed, size = hashlib.sha256(), 0
        while True:
            deadline.remaining()
            part = os.read(fd, 65536)
            if not part:
                break
            size += len(part)
            require(size <= maximum, "q2_file_rejected")
            hashed.update(part)
        require(size == before.st_size and _identity(before) == _identity(os.fstat(fd)),
                "q2_unstable_input")
        return {"archive_size_bytes": size, "archive_sha256": hashed.hexdigest()}
    finally:
        os.close(fd)


@contextmanager
def private_workspace(repo, parent=None):
    repo = Path(repo).resolve(strict=True)
    base = Path(parent or os.environ.get("RUNNER_TEMP") or tempfile.gettempdir()).absolute()
    require(base.is_dir() and not any(p.is_symlink() for p in (base, *base.parents)),
            "q2_file_rejected")
    require(base != repo and repo not in base.parents, "q2_file_rejected")
    path = Path(tempfile.mkdtemp(prefix="pulse-q2-intake-", dir=base))
    path.chmod(0o700)
    state = {"path": path, "cleanup_verified": False}
    try:
        yield state
    finally:
        try:
            shutil.rmtree(path)
            state["cleanup_verified"] = not os.path.lexists(path)
        except OSError:
            state["cleanup_verified"] = False
        require(state["cleanup_verified"], "q2_cleanup_failed")


def clean_environment(environment=None):
    return {k: v for k, v in dict(os.environ if environment is None else environment).items()
            if not k.startswith("PULSE_Q2_")}


def replay_environment(private):
    return {"PATH": os.defpath, "HOME": str(private), "TMPDIR": str(private),
            "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"}


def check_private_directory(repo, path):
    """Internal semantic entry points cannot publish raw replay files in the repo."""
    path = Path(path).absolute()
    require(path.is_dir() and not any(p.is_symlink() for p in (path, *path.parents)) and
            path != repo and repo not in path.parents and
            stat.S_IMODE(path.stat().st_mode) == 0o700 and path.stat().st_uid == os.getuid(),
            "q2_file_rejected")
    return path


def private_process(command, *, cwd, environment, timeout, new_session=False):
    """No exception output, stdout, stderr or TimeoutExpired buffer is published."""
    child = None
    try:
        child = subprocess.Popen(command, cwd=cwd, env=environment,
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, start_new_session=new_session)
        return child.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        raise IntakeError("q2_timeout") from None
    except OSError:
        raise IntakeError("q2_input_unavailable") from None
    finally:
        if child is not None:
            # The runner owns the complete Q2 process group, including descendants.
            if new_session:
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    pass
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            elif child.poll() is None:
                child.kill()
            child.wait()


def run_q2_command(command, *, repo, environment, timeout):
    """Outer runner supervises a private parent even if its dispatcher is killed."""
    with private_workspace(repo, environment.get("RUNNER_TEMP")) as work:
        env = dict(environment)
        env["PULSE_Q2_SUPERVISOR_ROOT"] = str(work["path"])
        try:
            rc = private_process(command, cwd=repo, environment=env,
                                 timeout=timeout, new_session=True)
            return rc if rc in (0, 1, 2) else 2
        except IntakeError:
            return 2


def safe_member(name):
    require(type(name) is str and 0 < len(name) <= 1024 and
            re.fullmatch(r"[A-Za-z0-9_+@./-]+", name) is not None,
            "q2_archive_rejected")
    p = PurePosixPath(name)
    require(not p.is_absolute() and str(p) == name and
            all(part not in ("", ".", "..") and len(part) <= 255 for part in name.split("/")),
            "q2_archive_rejected")
    return name


class Archive:
    """Read a held, stable archive descriptor. Never extract or execute its members."""
    def __init__(self, path, *, maximum_bytes, max_members, member_bytes,
                 expanded_bytes, deadline, allow_runtime_link=False, expected_sha256=None):
        self.fd, self.before = _open_regular(path)
        self.stream = os.fdopen(self.fd, "rb", closefd=False)
        self.zip = None
        self.deadline = deadline
        self.member_bytes = member_bytes
        try:
            require(0 < self.before.st_size <= maximum_bytes, "q2_archive_limit")
            # Bound the central directory before ZipFile allocates member objects.
            # This profile has no comments, split archives, ZIP64 or extra fields.
            require(self.before.st_size >= 22, "q2_archive_rejected")
            self.stream.seek(-22, os.SEEK_END)
            ending = self.stream.read(22)
            signature, disk, central_disk, on_disk, count, central_size, central_offset, comment = struct.unpack("<4s4H2IH", ending)
            require(signature == b"PK\x05\x06" and disk == central_disk == comment == 0 and
                    on_disk == count and central_offset + central_size == self.before.st_size - 22,
                    "q2_archive_rejected")
            require(0 < count <= max_members and central_size <= max_members * (46 + 1024),
                    "q2_archive_limit")
            if expected_sha256 is not None:
                require(re.fullmatch(r"[0-9a-f]{64}", expected_sha256 or "") is not None,
                        "q2_digest_mismatch")
                self.stream.seek(0)
                hashed = hashlib.sha256()
                for chunk in iter(lambda: self.stream.read(65536), b""):
                    deadline.remaining()
                    hashed.update(chunk)
                require(hashed.hexdigest() == expected_sha256 and
                        _identity(self.before) == _identity(os.fstat(self.fd)), "q2_digest_mismatch")
            self.stream.seek(0)
            self.zip = zipfile.ZipFile(self.stream)
            infos = self.zip.infolist()
            require(len(infos) == count, "q2_archive_limit")
            require(sum(i.file_size for i in infos) <= expanded_bytes, "q2_archive_limit")
            self.members = {}
            local_ranges = []
            for info in infos:
                deadline.remaining()
                name = safe_member(info.filename)
                require(info.orig_filename == name and name not in self.members and
                        not info.extra and not info.comment and info.volume == 0 and
                        not info.is_dir() and not info.flag_bits & 1 and
                        info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED),
                        "q2_archive_rejected")
                require(0 <= info.file_size <= member_bytes and info.compress_size >= 0,
                        "q2_archive_limit")
                mode = info.external_attr >> 16
                kind = stat.S_IFMT(mode)
                link = allow_runtime_link and name == "runtime/lib64" and kind == stat.S_IFLNK
                require(kind in (0, stat.S_IFREG) or link, "q2_archive_rejected")
                require(not stat.S_IMODE(mode) & 0o7000, "q2_archive_rejected")
                # The local header and optional data descriptor must express the
                # same member. No hidden prefix, padding, local extra field or
                # unindexed payload is accepted as part of a release capsule.
                require(0 <= info.header_offset < central_offset and
                        info.flag_bits & ~0x080e == 0, "q2_archive_rejected")
                self.stream.seek(info.header_offset)
                header = self.stream.read(30)
                require(len(header) == 30, "q2_archive_rejected")
                fields = struct.unpack("<4s5H3I2H", header)
                signature, version, flags, method, _time, _date, crc, packed, size, namesize, extrasize = fields
                encoded_name = name.encode("ascii")
                require(signature == b"PK\x03\x04" and version <= 20 and
                        flags == info.flag_bits and method == info.compress_type and
                        namesize == len(encoded_name) and extrasize == 0 and
                        self.stream.read(namesize) == encoded_name, "q2_archive_rejected")
                end = info.header_offset + 30 + namesize + info.compress_size
                require(end <= central_offset, "q2_archive_rejected")
                if flags & 8:
                    require((crc, packed, size) in ((0, 0, 0), (info.CRC, info.compress_size, info.file_size)),
                            "q2_archive_rejected")
                    self.stream.seek(end)
                    first = self.stream.read(4)
                    descriptor = self.stream.read(12) if first == b"PK\x07\x08" else first + self.stream.read(8)
                    require(len(descriptor) == 12 and struct.unpack("<3I", descriptor) ==
                            (info.CRC, info.compress_size, info.file_size), "q2_archive_rejected")
                    end += 16 if first == b"PK\x07\x08" else 12
                else:
                    require((crc, packed, size) == (info.CRC, info.compress_size, info.file_size),
                            "q2_archive_rejected")
                local_ranges.append((info.header_offset, end))
                self.members[name] = info
            ordered = sorted(local_ranges)
            require(ordered[0][0] == 0 and ordered[-1][1] == central_offset and
                    all(left[1] == right[0] for left, right in zip(ordered, ordered[1:])),
                    "q2_archive_rejected")
            # A regular member cannot also be the parent directory of another member.
            names = set(self.members)
            require(all(not any(str(p) in names for p in PurePosixPath(n).parents
                                if str(p) != ".") for n in names), "q2_archive_rejected")
        except Exception as exc:
            self.close()
            if isinstance(exc, IntakeError):
                raise
            raise IntakeError("q2_archive_rejected") from None

    def close(self):
        if self.zip is not None:
            self.zip.close()
        self.stream.close()
        os.close(self.fd)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        try:
            require(_identity(self.before) == _identity(os.fstat(self.fd)), "q2_unstable_input")
        finally:
            self.close()

    def inspect(self, name, *, retain=False, maximum=None):
        require(name in self.members, "q2_archive_rejected")
        info = self.members[name]
        limit = self.member_bytes if maximum is None else min(self.member_bytes, maximum)
        require(info.file_size <= limit, "q2_archive_limit")
        hashed, total, pieces = hashlib.sha256(), 0, []
        try:
            with self.zip.open(info) as stream:
                while True:
                    self.deadline.remaining()
                    part = stream.read(min(65536, limit + 1 - total))
                    if not part:
                        break
                    total += len(part)
                    require(total <= limit, "q2_archive_limit")
                    hashed.update(part)
                    if retain:
                        pieces.append(part)
            require(total == info.file_size and _identity(self.before) == _identity(os.fstat(self.fd)),
                    "q2_unstable_input")
        except (OSError, zipfile.BadZipFile, RuntimeError, EOFError):
            raise IntakeError("q2_archive_rejected") from None
        record = {"size": total, "sha256": hashed.hexdigest(),
                  "mode": stat.S_IMODE(info.external_attr >> 16),
                  "kind": "symlink" if stat.S_ISLNK(info.external_attr >> 16) else "file"}
        return (record, b"".join(pieces)) if retain else record

    def read(self, name, maximum=16 * 1024 * 1024):
        return self.inspect(name, retain=True, maximum=maximum)[1]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class GitHubArtifactTransport:
    """Exact read-only API locator; credentials never follow a signed redirect."""
    def __init__(self, token):
        require(type(token) is str and 0 < len(token) <= 4096 and
                not any(ord(c) < 33 or ord(c) > 126 for c in token), "q2_credential_missing")
        self.token = token
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())

    def download(self, repository, artifact_id, expectation, destination, deadline):
        require(repository == "HKati/pulse-release-gates-0.1" and
                type(artifact_id) is int and artifact_id > 0, "q2_transport_rejected")
        endpoint = f"https://api.github.com/repos/{repository}/actions/artifacts/{artifact_id}/zip"
        headers = {"Authorization": "Bearer " + self.token,
                   "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        response = None
        try:
            try:
                response = self.opener.open(urllib.request.Request(endpoint, headers=headers),
                                            timeout=deadline.remaining())
            except urllib.error.HTTPError as exc:
                require(exc.code in (301, 302, 303, 307, 308), "q2_transport_rejected")
                location = exc.headers.get("Location", "")
                exc.close()
                parsed = urllib.parse.urlsplit(location)
                host = parsed.hostname or ""
                require(parsed.scheme == "https" and parsed.port in (None, 443) and
                        not parsed.username and not parsed.password and not parsed.fragment and
                        any(host.endswith(suffix) for suffix in
                            (".blob.core.windows.net", ".actions.githubusercontent.com",
                             ".githubusercontent.com")), "q2_transport_rejected")
                # Authorization is deliberately absent on the storage request.
                response = self.opener.open(urllib.request.Request(location), timeout=deadline.remaining())
            require(response.status == 200, "q2_transport_rejected")
            expected_size = expectation["archive_size_bytes"]
            length = response.headers.get("Content-Length")
            require(length is None or length == str(expected_size), "q2_digest_mismatch")
            hashed, size = hashlib.sha256(), 0
            fd = os.open(destination, os.O_WRONLY | os.O_EXCL | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as output:
                while True:
                    deadline.remaining()
                    chunk = response.read(min(65536, expected_size + 1 - size))
                    if not chunk:
                        break
                    size += len(chunk)
                    require(size <= expected_size, "q2_digest_mismatch")
                    hashed.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            require(size == expected_size and hashed.hexdigest() == expectation["archive_sha256"],
                    "q2_digest_mismatch")
        except IntakeError:
            raise
        except Exception:
            raise IntakeError("q2_transport_rejected") from None
        finally:
            if response is not None:
                response.close()

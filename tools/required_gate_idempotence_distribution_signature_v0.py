"""Bounded, offline verification of selected detached OpenPGP signatures.

The caller supplies an independently pinned keyring, exact full signer pairs,
evaluation time and GPG executable binding. Only immutable selected GPG bytes
execute, in verification mode, with immutable evidence descriptors and a private
homedir. GPG's dynamic libraries, kernel and this Python installation remain
trusted verification components; their complete closure is not established.
Neither an artifact-supplied keyring nor a saved status transcript authorizes a
signer. This helper never executes package, launcher, entry or runtime payloads.
"""
from __future__ import annotations

from contextlib import ExitStack
import datetime as dt
import hashlib
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import required_gate_idempotence_process_v0 as process_primitives

RELEASE_LIMIT = 1024 * 1024
SIGNATURE_LIMIT = 64 * 1024
KEYRING_LIMIT = 1024 * 1024
VERIFIER_LIMIT = 32 * 1024 * 1024
STDOUT_LIMIT = 64 * 1024
STDERR_LIMIT = 64 * 1024
WALL_SECONDS = 20.0
TIME_LIMIT = 4102444800
COMMAND_PROFILE = "sealed_gpg_offline_detached_verify_v0"
ENVIRONMENT = {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C", "TZ": "UTC"}
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_FINGERPRINT = re.compile(r"[0-9A-F]{40}\Z")
_INTEGER = re.compile(r"0|[1-9][0-9]{0,10}\Z")
_BAD_STATUS = frozenset({"BADSIG", "ERRSIG", "EXPSIG", "EXPKEYSIG", "REVKEYSIG",
                         "NO_PUBKEY", "NODATA", "BADARMOR", "FAILURE", "ERROR",
                         "UNEXPECTED", "KEYEXPIRED", "SIGEXPIRED", "KEYREVOKED"})
_TRUST_STATUS = frozenset({"TRUST_UNDEFINED", "TRUST_NEVER", "TRUST_MARGINAL",
                          "TRUST_FULLY", "TRUST_ULTIMATE"})


class SignatureError(ValueError):
    """Stable rejection code, without embedding inspected evidence text."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise SignatureError(code)


def _binding(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _epoch(value):
    _need(type(value) is int and 0 < value <= TIME_LIMIT, "signature_evaluation_time_invalid")


def _signer_pairs(required_signers):
    _need(type(required_signers) is list and 1 <= len(required_signers) <= 8,
          "signature_signer_policy_invalid")
    pairs = []
    for signer in required_signers:
        _need(type(signer) is dict and set(signer) == {
            "signing_fingerprint", "primary_fingerprint"}, "signature_signer_policy_invalid")
        pair = (signer["signing_fingerprint"], signer["primary_fingerprint"])
        _need(all(type(value) is str and _FINGERPRINT.fullmatch(value) is not None for value in pair),
              "signature_signer_policy_invalid")
        pairs.append(pair)
    _need(len(set(pairs)) == len(pairs), "signature_signer_policy_duplicate")
    return set(pairs)


def _number(value, code):
    _need(_INTEGER.fullmatch(value) is not None, code)
    return int(value)


def _date_matches(value, epoch):
    try:
        return (re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is not None and
                dt.datetime.fromtimestamp(epoch, dt.timezone.utc).strftime("%Y-%m-%d") == value)
    except (ValueError, OverflowError, OSError):
        return False


def _parse_status(raw, required_signers, evaluation_time):
    """Admit complete NEWSIG groups, never a global union of good tokens."""
    expected = _signer_pairs(required_signers)
    _epoch(evaluation_time)
    _need(type(raw) is bytes and 0 < len(raw) <= STDOUT_LIMIT and raw.endswith(b"\n"),
          "signature_status_invalid")
    _need(all(value >= 32 or value == 10 for value in raw), "signature_status_invalid")
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise SignatureError("signature_status_invalid") from exc
    groups = []
    current = None
    for line in lines:
        _need(len(line.encode("utf-8")) <= 8192 and line.startswith("[GNUPG:] "),
              "signature_status_invalid")
        body = line[len("[GNUPG:] "):]
        tag, separator, argument = body.partition(" ")
        _need(bool(tag) and re.fullmatch(r"[A-Z_]+", tag) is not None,
              "signature_status_invalid")
        _need(tag not in _BAD_STATUS, "signature_status_rejected")
        if tag == "NEWSIG":
            _need(len(groups) < 8, "signature_group_limit")
            current = {"good": None, "valid": None, "sig_id": None}
            groups.append(current)
            continue
        _need(current is not None, "signature_status_group_missing")
        arguments = argument.split(" ") if separator else []
        if tag == "GOODSIG":
            key_id, _, _uid = argument.partition(" ")
            _need(current["good"] is None and re.fullmatch(r"[0-9A-F]{16}", key_id) is not None,
                  "signature_good_status_invalid")
            current["good"] = key_id
        elif tag == "VALIDSIG":
            _need(current["valid"] is None and len(arguments) == 10,
                  "signature_valid_status_invalid")
            signing, date, created, expires, version, reserved, public, digest, kind, primary = arguments
            _need(_FINGERPRINT.fullmatch(signing) is not None and
                  _FINGERPRINT.fullmatch(primary) is not None,
                  "signature_fingerprint_invalid")
            created = _number(created, "signature_timestamp_invalid")
            expires = _number(expires, "signature_timestamp_invalid")
            _need(0 < created <= evaluation_time and _date_matches(date, created),
                  "signature_created_time_invalid")
            _need(expires == 0 or created < expires <= TIME_LIMIT and evaluation_time < expires,
                  "signature_expired")
            _need(version == "4" and reserved == "0" and kind == "00",
                  "signature_format_unsupported")
            public = _number(public, "signature_algorithm_invalid")
            digest = _number(digest, "signature_algorithm_invalid")
            _need(public in {1, 19, 22} and digest in {8, 9, 10},
                  "signature_algorithm_unsupported")
            current["valid"] = {
                "signing_fingerprint": signing, "primary_fingerprint": primary,
                "signature_created_epoch": created, "signature_expires_epoch": expires,
                "pubkey_algorithm": public, "hash_algorithm": digest,
                "signature_class": kind, "signature_version": 4}
        elif tag == "KEY_CONSIDERED":
            _need(len(arguments) == 2 and _FINGERPRINT.fullmatch(arguments[0]) is not None,
                  "signature_context_status_invalid")
            _number(arguments[1], "signature_context_status_invalid")
        elif tag == "SIG_ID":
            _need(current["sig_id"] is None and len(arguments) == 3 and
                  re.fullmatch(r"[A-Za-z0-9+/=]{1,128}", arguments[0]) is not None,
                  "signature_context_status_invalid")
            created = _number(arguments[2], "signature_timestamp_invalid")
            _need(0 < created <= evaluation_time and _date_matches(arguments[1], created),
                  "signature_created_time_invalid")
            current["sig_id"] = created
        elif tag in _TRUST_STATUS:
            _need(1 <= len(arguments) <= 2 and
                  (len(arguments) == 1 or re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", arguments[1])),
                  "signature_context_status_invalid")
            _number(arguments[0], "signature_context_status_invalid")
        else:
            raise SignatureError("signature_status_unsupported")
    _need(bool(groups), "signature_group_missing")
    result = []
    observed = set()
    for group in groups:
        valid = group["valid"]
        _need(group["good"] is not None and valid is not None, "signature_group_incomplete")
        _need(valid["signing_fingerprint"].endswith(group["good"]), "signature_key_id_mismatch")
        _need(group["sig_id"] is None or group["sig_id"] == valid["signature_created_epoch"],
              "signature_timestamp_mismatch")
        pair = (valid["signing_fingerprint"], valid["primary_fingerprint"])
        _need(pair not in observed, "signature_group_duplicate")
        _need(pair in expected, "signature_signer_unauthorized")
        observed.add(pair)
        result.append(valid)
    _need(observed == expected, "signature_signer_roster_mismatch")
    return sorted(result, key=lambda item: (item["signing_fingerprint"], item["primary_fingerprint"]))


def _capture(*, executable_fd, argv, directory, pass_fds):
    """Keep bounded pending bytes from both pipes before every failed close."""
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    limits = {"stdout": STDOUT_LIMIT, "stderr": STDERR_LIMIT}
    record = {"pid": None, "exit_code": None, "timed_out": False, "output_limited": False,
              "limited_streams": [], "capture_complete": False, "error_code": None,
              "started_monotonic_ns": time.monotonic_ns(), "completed_monotonic_ns": None}
    process = None
    deadline = time.monotonic() + WALL_SECONDS

    def retain(name, block):
        available = limits[name] - len(buffers[name])
        buffers[name].extend(block[:available])
        if len(block) > available:
            record["output_limited"] = True
            if name not in record["limited_streams"]:
                record["limited_streams"].append(name)
            if record["error_code"] is None:
                record["error_code"] = "signature_" + name + "_limit"

    try:
        process = subprocess.Popen(
            argv, executable="/proc/self/fd/" + str(executable_fd),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=dict(ENVIRONMENT), cwd=directory, close_fds=True, pass_fds=pass_fds,
            shell=False, start_new_session=True)
        record["pid"] = process.pid
        with selectors.DefaultSelector() as selector:
            for name in buffers:
                pipe = getattr(process, name)
                os.set_blocking(pipe.fileno(), False)
                selector.register(pipe, selectors.EVENT_READ, name)
            while selector.get_map() and record["error_code"] is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    record["timed_out"] = True
                    record["error_code"] = "signature_wall_timeout"
                    break
                for key, _ in selector.select(min(remaining, 0.1)):
                    name = key.data
                    available = limits[name] - len(buffers[name])
                    block = os.read(key.fileobj.fileno(), min(65536, available + 1))
                    if not block:
                        selector.unregister(key.fileobj)
                        continue
                    retain(name, block)
                    if record["error_code"]:
                        break
            if record["error_code"] is None:
                # Keep the leader unreaped until its group has been stopped;
                # this prevents a recycled PID from naming an unrelated group.
                while os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        record["timed_out"] = True
                        record["error_code"] = "signature_wall_timeout"
                        break
                    time.sleep(min(remaining, 0.005))
    except (OSError, ValueError, subprocess.SubprocessError):
        record["error_code"] = "signature_launch_failed" if process is None else "signature_capture_failed"
    finally:
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except OSError:
                record["error_code"] = "signature_stop_failed"
            try:
                process.wait(timeout=1)
            except (OSError, subprocess.SubprocessError):
                record["error_code"] = "signature_reap_failed"
            record["exit_code"] = process.returncode
            for name in buffers:
                pipe = getattr(process, name)
                if pipe is None:
                    continue
                try:
                    os.set_blocking(pipe.fileno(), False)
                    while True:
                        available = limits[name] - len(buffers[name])
                        try:
                            block = os.read(pipe.fileno(), min(65536, available + 1))
                        except BlockingIOError:
                            break
                        if not block:
                            break
                        retain(name, block)
                        if len(block) > available:
                            break
                except (OSError, ValueError):
                    record["error_code"] = "signature_capture_failed"
                finally:
                    try:
                        pipe.close()
                    except OSError:
                        record["error_code"] = "signature_capture_failed"
        record["completed_monotonic_ns"] = time.monotonic_ns()
    record["limited_streams"].sort()
    record["capture_complete"] = record["error_code"] is None
    return {"stdout_bytes": bytes(buffers["stdout"]), "stderr_bytes": bytes(buffers["stderr"]),
            "process_record": record}


def _read_verifier(path, expected):
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            before = os.fstat(descriptor)
            _need(stat.S_ISREG(before.st_mode) and before.st_mode & 0o111 and
                  0 < before.st_size <= VERIFIER_LIMIT, "signature_verifier_file_invalid")
            result = bytearray()
            while True:
                block = os.read(descriptor, min(65536, VERIFIER_LIMIT + 1 - len(result)))
                if not block:
                    break
                result.extend(block)
                _need(len(result) <= VERIFIER_LIMIT, "signature_verifier_size_limit")
            after = os.fstat(descriptor)
            attributes = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
            _need(all(getattr(before, item) == getattr(after, item) for item in attributes) and
                  len(result) == before.st_size, "signature_verifier_changed")
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise SignatureError("signature_verifier_unavailable") from exc
    raw = bytes(result)
    _need(_binding(raw) == {key: expected[key] for key in ("sha256", "size_bytes")},
          "signature_verifier_binding_mismatch")
    # The trusted verifier must be a native executable, never a script whose
    # shebang could invoke an unbound interpreter despite sealing its bytes.
    _need(raw.startswith(b"\x7fELF"), "signature_verifier_format_unsupported")
    return raw


def verify_detached(*, release_bytes, signature_bytes, keyring_bytes,
                    expected_keyring_sha256, verifier_path, expected_verifier,
                    required_signers, evaluation_time, evidence_sink=None):
    """Freshly verify originals under the separately selected external policy."""
    _need(sys.platform == "linux" and hasattr(os, "memfd_create") and hasattr(os, "waitid"),
          "signature_platform_unsupported")
    for name, raw, limit in (("release", release_bytes, RELEASE_LIMIT),
                             ("signature", signature_bytes, SIGNATURE_LIMIT),
                             ("keyring", keyring_bytes, KEYRING_LIMIT)):
        _need(type(raw) is bytes and 0 < len(raw) <= limit, "signature_" + name + "_size_limit")
    _need(type(expected_keyring_sha256) is str and _HEX.fullmatch(expected_keyring_sha256),
          "signature_keyring_digest_invalid")
    _need(_binding(keyring_bytes)["sha256"] == expected_keyring_sha256,
          "signature_keyring_binding_mismatch")
    _signer_pairs(required_signers)
    _epoch(evaluation_time)
    _need(evidence_sink is None or callable(evidence_sink), "signature_evidence_sink_invalid")
    _need(isinstance(verifier_path, (str, Path)), "signature_verifier_path_invalid")
    path = str(verifier_path)
    _need(path.startswith("/") and not path.startswith("//") and path != "/" and
          str(Path(path)) == path and ".." not in Path(path).parts and
          all(32 <= ord(character) <= 126 and character != "\\" for character in path),
          "signature_verifier_path_invalid")
    _need(type(expected_verifier) is dict and set(expected_verifier) == {
        "kind", "path", "sha256", "size_bytes"} and expected_verifier["kind"] == "gpg" and
        expected_verifier["path"] == path and type(expected_verifier["sha256"]) is str and
        _HEX.fullmatch(expected_verifier["sha256"]) is not None and
        type(expected_verifier["size_bytes"]) is int and
        0 < expected_verifier["size_bytes"] <= VERIFIER_LIMIT, "signature_verifier_policy_invalid")
    verifier_bytes = _read_verifier(path, expected_verifier)
    payload = None
    with ExitStack() as stack:
        descriptors = {}
        try:
            for role, raw in (("verifier", verifier_bytes), ("keyring", keyring_bytes),
                              ("signature", signature_bytes), ("release", release_bytes)):
                descriptor = process_primitives.sealed_buffer("distribution-" + role, raw)
                stack.callback(os.close, descriptor)
                descriptors[role] = descriptor
        except (OSError, ValueError) as exc:
            raise SignatureError("signature_sealing_failed") from exc
        directory = stack.enter_context(tempfile.TemporaryDirectory(prefix="pulse-distribution-verify-"))
        fd_path = {role: "/proc/self/fd/" + str(descriptor) for role, descriptor in descriptors.items()}
        argv = [path, "--no-options", "--homedir", ".", "--batch", "--no-tty",
                "--no-default-keyring", "--keyring", fd_path["keyring"],
                "--disable-dirmngr", "--no-autostart", "--no-auto-key-retrieve",
                "--no-auto-key-import", "--auto-key-locate", "clear", "--disable-signer-uid",
                "--no-auto-check-trustdb", "--faked-system-time", str(evaluation_time) + "!",
                "--exit-on-status-write-error", "--status-fd", "1", "--verify",
                fd_path["signature"], fd_path["release"]]
        payload = _capture(executable_fd=descriptors["verifier"], argv=argv, directory=directory,
                           pass_fds=tuple(descriptors.values()))
    record = payload["process_record"]
    record.update({
        "record_type": "required_gate_idempotence_distribution_signature_process_v0",
        "command_profile": COMMAND_PROFILE, "verifier": dict(expected_verifier),
        "inputs": {"release": _binding(release_bytes), "signature": _binding(signature_bytes),
                   "keyring": _binding(keyring_bytes)},
        "evaluation_time": evaluation_time, "required_signers": sorted(
            [dict(item) for item in required_signers],
            key=lambda item: (item["signing_fingerprint"], item["primary_fingerprint"])),
        "argv": argv, "environment": dict(ENVIRONMENT),
        "working_directory": "private_temporary_directory",
        "execution": "sealed_verifier_memfd", "inputs_sealed": True,
        "verifier_runtime_closure_verified": False,
        "stdout": _binding(payload["stdout_bytes"]), "stderr": _binding(payload["stderr_bytes"]),
        "limits": {"wall_seconds": WALL_SECONDS, "stdout_bytes": STDOUT_LIMIT,
                   "stderr_bytes": STDERR_LIMIT}})
    failure = None
    result = None
    try:
        _need(record["error_code"] is None, record["error_code"] or "signature_capture_failed")
        _need(record["capture_complete"] and not record["timed_out"] and not record["output_limited"],
              "signature_capture_incomplete")
        _need(record["exit_code"] == 0, "signature_verification_failed")
        facts = _parse_status(payload["stdout_bytes"], required_signers, evaluation_time)
        result = {"verified_signatures": facts, "backend": dict(expected_verifier)}
    except SignatureError as exc:
        failure = exc.code
    record["verification_status"] = "accepted" if failure is None else "rejected"
    record["verification_error_code"] = failure
    if evidence_sink is not None:
        try:
            evidence_sink(payload)
        except Exception as exc:
            raise SignatureError("signature_evidence_preservation_failed") from exc
    if failure is not None:
        raise SignatureError(failure)
    return result

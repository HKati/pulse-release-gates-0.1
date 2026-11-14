#!/usr/bin/env python3
"""Prepare selected sources and exercise bounded acquisition orchestration.

The public CLI prepares bytes only. Observed acquisition remains closed until
recoverable runtime closure and separate owner authorization are implemented
and reviewed. The example coordinator requires an explicit synthetic runner;
it never chooses or launches the selected sanitizer on its own.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import io
import os
from pathlib import Path
import re
import stat
import sys
import time
from typing import Any, Callable
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_required_gate_idempotence_observation_v0 as observation

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT / "docs/compute/required_gate_idempotence_protocol_v0"
WORKER = "tools/required_gate_idempotence_worker_v0.py"
COLLECTOR = "tools/acquire_required_gate_idempotence_v0.py"
PROCESS = "tools/required_gate_idempotence_process_v0.py"
STDOUT_LIMIT = 20 * 1024
STDERR_LIMIT = 4096
LIMITS = {"applications": 24, "attempts_per_application": 1,
          "worker_wall_seconds": 5, "worker_cpu_seconds": 2,
          "worker_address_space_bytes": 256 * 1024 * 1024,
          "suite_wall_seconds": 180, "initial_input_bytes": 1024,
          "snapshot_bytes": 4096, "metadata_bytes": 4096,
          "stderr_bytes": STDERR_LIMIT, "worker_protocol_bytes": STDOUT_LIMIT}
BOUNDARY = dict(observation.BOUNDARY)
_PREPARATION_ADMISSION = object()


class AcquisitionError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def need(condition: bool, code: str) -> None:
    if not condition:
        raise AcquisitionError(code)


def canonical(value: Any) -> bytes:
    return observation.canonical_bytes(value)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def archive(members: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as carrier:
        for name, raw in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o600) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            carrier.writestr(info, raw)
    raw = output.getvalue()
    need(observation.read_archive(raw) == members, "archive_roundtrip_mismatch")
    return raw


def binding(raw: bytes, *, member: str | None = None, state_id: str | None = None) -> dict:
    result = {"sha256": observation.sha(raw), "size_bytes": len(raw)}
    if member is not None:
        result["member"] = member
    if state_id is not None:
        result["state_id"] = state_id
    return result


@dataclass(frozen=True, init=False)
class PreparedSelection:
    """Immutable selected bytes, never an execution permit or runtime closure."""
    selection_bytes: bytes
    members: tuple[tuple[str, bytes], ...]
    _admission: object

    def __init__(self, *args, **kwargs):
        raise AcquisitionError("preparation_direct_construction_forbidden")

    @property
    def selection(self) -> dict:
        return observation.parse(self.selection_bytes)

    @property
    def selection_sha256(self) -> str:
        return observation.sha(self.selection_bytes)


def prepare_selection(*, selection_bytes: bytes, expected_selection_sha256: str,
                      repository_root: Path | None = None,
                      source_bytes: dict[str, bytes] | None = None) -> PreparedSelection:
    """Read and bind source bytes; do not import selected source or probe a host.

    Observed selections are recovered from existing Git objects. Explicit
    in-memory source bytes are accepted only for authored example regressions.
    Installed verifier dependencies are a separate trust boundary and are not
    represented as a recovered runtime by this preparation.
    """
    try:
        need(type(selection_bytes) is bytes
             and observation.sha(selection_bytes) == expected_selection_sha256,
             "selection_digest_mismatch")
        selection = observation.parse(selection_bytes)
        observation.validate_shape(selection, "selection")
        if selection["record_status"] == "observed":
            need(source_bytes is None, "observed_source_override_forbidden")
            need(repository_root is not None, "observed_repository_required")
        else:
            need(source_bytes is not None, "example_source_bytes_required")
        sources = selection["sources"]
        by_path = {item["path"]: item for item in sources}
        for role, path in (("worker", WORKER), ("collector", COLLECTOR),
                           ("implementation_dependency", PROCESS)):
            item = by_path.get(path, {})
            need(item.get("role") == role and item.get("source_revision") == selection["source_commit"],
                 "acquisition_implementation_selection_mismatch")
        if source_bytes is not None:
            need(set(source_bytes) == set(by_path), "source_roster_mismatch")
        members = {"selection/" + name: observation.safe._read_regular(PROPOSAL / name)
                   for name in observation.PROTOCOL_PINS}
        for item in sources:
            need(observation.path_ok(item["path"]), "source_path_invalid")
            raw = (source_bytes[item["path"]] if source_bytes is not None
                   else observation._git_blob(Path(repository_root), item["source_revision"],
                                              item["path"], item["size_bytes"]))
            need(type(raw) is bytes, "source_bytes_invalid")
            members[item["member"]] = raw
        # Exact installed acquisition primitives are selected explicitly. A
        # different script in an otherwise coherent selection cannot be launched.
        for path in (WORKER, COLLECTOR, PROCESS):
            need(members["sources/" + path] == observation.safe._read_regular(ROOT / path),
                 "installed_implementation_mismatch")
        observation._selection(selection, members, repository_root=repository_root)
        members["selection/pre_acquisition_selection.json"] = selection_bytes
        need(len(members) <= observation.MAX_MEMBERS
             and sum(map(len, members.values())) <= observation.TOTAL_LIMIT,
             "preparation_size_limit")
        prepared = object.__new__(PreparedSelection)
        object.__setattr__(prepared, "selection_bytes", selection_bytes)
        object.__setattr__(prepared, "members", tuple(sorted(members.items())))
        object.__setattr__(prepared, "_admission", _PREPARATION_ADMISSION)
        return prepared
    except (observation.VerificationError, observation.safe.ContractError) as exc:
        raise AcquisitionError(exc.code) from exc
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, AcquisitionError):
            raise
        raise AcquisitionError("selection_invalid") from exc


def _prepared(prepared: PreparedSelection, *, example: bool = False) -> dict:
    need(type(prepared) is PreparedSelection
         and getattr(prepared, "_admission", None) is _PREPARATION_ADMISSION, "preparation_required")
    selection = prepared.selection
    if example:
        need(selection["record_status"] == "example", "observed_acquisition_not_ready")
        # Recheck source admissions rather than trusting a constructible Python
        # dataclass or an earlier mutable selection dictionary.
        sources = {item["path"]: dict(prepared.members).get(item["member"])
                   for item in selection["sources"]}
        checked = prepare_selection(selection_bytes=prepared.selection_bytes,
                                    expected_selection_sha256=prepared.selection_sha256,
                                    source_bytes=sources)
        need(checked == prepared, "prepared_members_mismatch")
    return selection


def preparation_report(prepared: PreparedSelection) -> dict:
    selection = _prepared(prepared)
    return {"record_type": "required_gate_idempotence_acquisition_preparation_v0",
            "status": "prepared", "record_status": selection["record_status"],
            "selection_sha256": prepared.selection_sha256,
            "source_inventory": selection["sources"], "limits": dict(LIMITS),
            "selected_source_bytes_bound": True,
            "source_git_binding_verified": selection["record_status"] == "observed",
            "host_environment_qualified": False, "operator_applications": 0,
            "observed_acquisition_supported": False,
            "outstanding": ["recoverable_runtime_closure", "runtime_closure_review",
                            "separate_owner_authorization", "observed_launch_integration"],
            **BOUNDARY}


def source_archive(prepared: PreparedSelection) -> bytes:
    _prepared(prepared)
    members = dict(prepared.members)
    members["preparation/member_inventory.json"] = canonical({
        "record_type": "required_gate_idempotence_preparation_inventory_v0",
        "members": [binding(raw, member=name) for name, raw in sorted(members.items())]})
    return archive(members)


class _Directory:
    """New, private, descriptor-relative evidence directory; never auto-delete."""
    def __init__(self, path: Path):
        self.fd: int | None = None
        self.files: set[str] = set()
        try:
            absolute = observation.safe._absolute(path)
            need(absolute.name.casefold() not in observation.safe.DENIED_OUTPUT_NAMES,
                 "output_authority_name")
            parent, name = observation.safe._parent_fd(absolute)
            try:
                os.mkdir(name, 0o700, dir_fd=parent)
                self.fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                                  dir_fd=parent)
                os.fsync(parent)
            finally:
                os.close(parent)
        except FileExistsError as exc:
            raise AcquisitionError("output_exists") from exc
        except (OSError, observation.safe.ContractError) as exc:
            raise AcquisitionError("output_unsafe_path") from exc

    def _parent(self, relative: str) -> tuple[int, str]:
        need(observation.path_ok(relative), "output_member_invalid")
        fd = os.dup(self.fd)
        try:
            parts = relative.split("/")
            for part in parts[:-1]:
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                    os.fsync(fd)
                except FileExistsError:
                    pass
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                                dir_fd=fd)
                os.close(fd)
                fd = child
            return fd, parts[-1]
        except BaseException:
            os.close(fd)
            raise

    def create(self, relative: str) -> int:
        parent, name = self._parent(relative)
        try:
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                         0o600, dir_fd=parent)
            self.files.add(relative)
            os.fsync(parent)
            return fd
        finally:
            os.close(parent)

    @staticmethod
    def append(fd: int, data: bytes) -> None:
        view = memoryview(data)
        while view:
            count = os.write(fd, view)
            need(count > 0, "evidence_write_failed")
            view = view[count:]
        os.fsync(fd)

    def write(self, relative: str, data: bytes) -> None:
        fd = self.create(relative)
        try:
            self.append(fd, data)
        finally:
            os.close(fd)

    def inventory(self) -> list[dict]:
        rows = []
        for relative in sorted(self.files):
            parent, name = self._parent(relative)
            fd = None
            try:
                fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                             dir_fd=parent)
                info = os.fstat(fd)
                need(stat.S_ISREG(info.st_mode) and info.st_size <= observation.ARCHIVE_LIMIT,
                     "preserved_file_invalid")
                raw = bytearray()
                while True:
                    block = os.read(fd, min(65536, observation.ARCHIVE_LIMIT + 1 - len(raw)))
                    if not block:
                        break
                    raw.extend(block)
                    need(len(raw) <= observation.ARCHIVE_LIMIT, "preserved_file_size_limit")
                after = os.fstat(fd)
                need((info.st_size, info.st_mtime_ns, info.st_ctime_ns)
                     == (after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                     and len(raw) == info.st_size, "preserved_file_changed")
                rows.append(binding(bytes(raw), member=relative))
            finally:
                if fd is not None:
                    os.close(fd)
                os.close(parent)
        return rows

    def close(self) -> None:
        if self.fd is not None:
            os.fsync(self.fd)
            os.close(self.fd)
            self.fd = None


def _write_preparation(prepared: PreparedSelection, directory: _Directory) -> dict:
    sources = source_archive(prepared)
    report = {**preparation_report(prepared), "source_archive": binding(sources, member="sources.zip")}
    directory.write("selection.json", prepared.selection_bytes)
    directory.write("sources.zip", sources)
    directory.write("preparation.json", canonical(report))
    return report


def write_preparation(prepared: PreparedSelection, output_directory: Path) -> dict:
    _prepared(prepared)
    directory = _Directory(output_directory)
    try:
        report = _write_preparation(prepared, directory)
        directory.write("preparation_inventory.json", canonical({
            "record_type": "required_gate_idempotence_preparation_files_v0",
            "files": directory.inventory(), **BOUNDARY}))
        return report
    finally:
        directory.close()


class _Streams:
    def __init__(self, directory: _Directory, application_id: str):
        self.directory = directory
        self.fds: dict[str, int] = {}
        self.data = {"stdout": bytearray(), "stderr": bytearray()}
        self.overflow = False
        try:
            for name in self.data:
                self.fds[name] = directory.create("raw/" + application_id + "." + name)
        except BaseException:
            self.close()
            raise

    def sink(self, channel: str, data: bytes) -> None:
        need(channel in self.data and type(data) is bytes, "stream_record_invalid")
        maximum = STDOUT_LIMIT if channel == "stdout" else STDERR_LIMIT
        allowed = data[:max(0, maximum - len(self.data[channel]))]
        self.directory.append(self.fds[channel], allowed)
        self.data[channel].extend(allowed)
        if len(allowed) != len(data):
            self.overflow = True
            raise AcquisitionError("stream_size_limit")

    def finish(self, result: dict) -> None:
        for channel in self.data:
            raw = result.get(channel + "_bytes", b"")
            need(type(raw) is bytes, "stream_record_invalid")
            existing = bytes(self.data[channel])
            if not existing:
                self.sink(channel, raw)
            else:
                need(existing == raw, "stream_record_mismatch")
        need(not self.overflow, "stream_size_limit")

    def close(self) -> None:
        for fd in self.fds.values():
            os.close(fd)
        self.fds.clear()


def _receipt(selection: dict, application_id: str, input_descriptor: dict,
             input_bytes: bytes, result: dict, processes: set[int],
             start_utc: str, start_ns: int, end_utc: str, end_ns: int) -> tuple[dict, dict[str, bytes]]:
    need(result.get("status") == "complete" and type(result.get("exit_code")) is int
         and result["exit_code"] == 0 and result.get("error_code") is None, "worker_incomplete")
    pid = result.get("process_id")
    need(type(pid) is int and 0 < pid < 2**31 and pid not in processes, "process_identity_reused")
    need(result.get("input_read_complete") is True
         and type(result.get("input_read_size_bytes")) is int
         and result["input_read_size_bytes"] == len(input_bytes)
         and result.get("input_read_sha256") == observation.sha(input_bytes), "input_read_mismatch")
    need(all(type(result.get(key)) is int for key in ("started_monotonic_ns", "completed_monotonic_ns")),
         "capture_time_invalid")
    observation._interval(result, maximum_ns=5_000_000_000)
    need(start_ns <= result["started_monotonic_ns"] <= result["completed_monotonic_ns"] <= end_ns
         and observation._utc(start_utc) <= observation._utc(result["started_utc"])
         <= observation._utc(result["completed_utc"]) <= observation._utc(end_utc),
         "worker_outside_supervision")
    cid, phase = application_id.split(".")
    stem = selection["acquisition_id"] + ":" + application_id
    members = {}
    outputs = {}
    for role, key, folder, suffix in (("snapshot", "snapshot_bytes", "snapshots", ".json"),
                                       ("metadata", "metadata_bytes", "metadata", ".json"),
                                       ("stderr", "stderr_bytes", "diagnostics", ".stderr")):
        raw = result.get(key)
        need(type(raw) is bytes and len(raw) <= 4096, "worker_output_size_limit")
        if role != "stderr":
            value = observation.parse(raw)
            if role == "snapshot":
                observation.snapshot_domain(value)
                need(canonical(value) == raw, "snapshot_not_canonical")
        member = folder + "/" + application_id + suffix
        members[member] = raw
        outputs[role] = binding(raw, member=member, state_id="state:" + stem + ":" + role)
    worker = next(item for item in selection["sources"] if item["role"] == "worker")
    args_sha, command_sha = observation.invocation_binding(selection, application_id, input_descriptor)
    row = {"application_id": application_id, "case_id": cid, "phase": phase,
           "execution_id": "execution:" + stem, "process_id": pid,
           "source_path": worker["path"], "source_revision": worker["source_revision"],
           "configuration_sha256": observation.sha(canonical(selection["configuration"])),
           "environment_sha256": observation.sha(canonical(selection["environment"])),
           "arguments_sha256": args_sha, "command_sha256": command_sha,
           **{key: result[key] for key in ("started_utc", "completed_utc", "started_monotonic_ns",
                                         "completed_monotonic_ns")},
           "exit_code": 0, "capture_status": "complete",
           "input": {**input_descriptor, "read_sha256": result["input_read_sha256"],
                     "read_size_bytes": result["input_read_size_bytes"], "read_complete": True},
           **outputs}
    observation.validate_shape(row, "receipt")
    processes.add(pid)
    return row, members


def _result_record(application_id: str, result: dict) -> dict:
    """Retain bounded lifecycle facts even when the occurrence is unusable.

    Unexpected values are identified by field name rather than copied as
    arbitrary text. The raw worker protocol remains in the separate bounded
    stdout file. Truncation is explicit and is never represented as full bytes.
    """
    capture, invalid, outputs = {}, [], {}
    integer_fields = {"process_id", "exit_code", "started_monotonic_ns",
                      "completed_monotonic_ns", "input_read_size_bytes"}
    for key in sorted(integer_fields | {"started_utc", "completed_utc", "status", "error_code",
                                       "input_read_sha256", "input_read_complete"}):
        value = result.get(key)
        valid = value is None
        if key in integer_fields:
            valid |= type(value) is int and -(2**63) < value < 2**63
        elif key in {"started_utc", "completed_utc"}:
            valid |= isinstance(value, str) and len(value) <= 64 and re.fullmatch(r"[0-9T:Z.+-]+", value) is not None
        elif key == "input_read_complete":
            valid |= type(value) is bool
        elif key == "input_read_sha256":
            valid |= isinstance(value, str) and observation.HEX.fullmatch(value) is not None
        elif key == "status":
            valid |= type(value) is str and value in {"complete", "incomplete"}
        else:
            valid |= isinstance(value, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,95}", value) is not None
        if valid:
            capture[key] = value
        else:
            invalid.append(key)
    for role, maximum in (("snapshot", 4096), ("metadata", 4096),
                          ("stdout", STDOUT_LIMIT), ("stderr", STDERR_LIMIT)):
        raw = result.get(role + "_bytes")
        if type(raw) is bytes:
            outputs[role] = {"observed_size_bytes": len(raw),
                             "retained_prefix": binding(raw[:maximum]),
                             "truncated": len(raw) > maximum}
        else:
            invalid.append(role + "_bytes")
    return {"record_type": "required_gate_idempotence_occurrence_result_v0",
            "application_id": application_id, "synthetic_execution": True,
            "capture": capture, "outputs": outputs, "invalid_fields": sorted(invalid)}


def collect_example(*, prepared: PreparedSelection, output_directory: Path,
                    runner: Callable[..., dict]) -> dict:
    """Exercise the complete finite coordinator using an explicitly supplied fake.

    A real process primitive is deliberately not the default. This example seam
    cannot authorize observed acquisition by changing a JSON status field. An
    unsuccessful occurrence stops the attempt and preserves its captured prefix.
    """
    selection = _prepared(prepared, example=True)
    need(callable(runner), "example_runner_required")
    directory = _Directory(output_directory)
    started_utc, started_ns = utc_now(), time.monotonic_ns()
    suite_deadline = time.monotonic() + LIMITS["suite_wall_seconds"]
    rows, attempted = [], []
    processes = {os.getpid()}
    members = dict(prepared.members)
    catalog = observation.parse(members["selection/inputs_v0.json"])["cases"]
    failure_code = failed_application_id = None
    carrier_sha = None
    try:
        _write_preparation(prepared, directory)
        directory.write("attempt.started.json", canonical({
            "record_type": "required_gate_idempotence_attempt_start_v0", "record_status": "example",
            "selection_sha256": prepared.selection_sha256, "started_utc": started_utc,
            "started_monotonic_ns": started_ns, "limits": dict(LIMITS),
            "synthetic_execution": True, **BOUNDARY}))
        for case in sorted(catalog, key=lambda value: value["case_id"]):
            cid = case["case_id"]
            raw = case["input_utf8"].encode("utf-8")
            member = "inputs/" + cid + ".json"
            members[member] = raw
            descriptor = binding(raw, member=member,
                                 state_id="state:" + selection["acquisition_id"] + ":" + cid + ":input")
            for phase in ("first", "second"):
                app = cid + "." + phase
                failed_application_id = app
                need(time.monotonic() < suite_deadline, "suite_wall_time_limit")
                before_utc, before_ns = utc_now(), time.monotonic_ns()
                event = {"application_id": app, "ordinal": len(attempted) + 1,
                         "input": descriptor, "started_utc": before_utc,
                         "started_monotonic_ns": before_ns, "synthetic_execution": True}
                directory.write("events/" + str(event["ordinal"]).zfill(4) + ".started.json", canonical(event))
                streams = _Streams(directory, app)
                try:
                    # Durable journal and stream setup can consume the remaining
                    # budget; expiry must still stop before invoking the runner.
                    need(time.monotonic() < suite_deadline, "suite_wall_time_limit")
                    attempted.append(app)
                    result = runner(application_id=app, input_bytes=raw,
                                    input_descriptor=dict(descriptor),
                                    deadline=min(suite_deadline, time.monotonic() + 5), sink=streams.sink)
                    need(type(result) is dict, "worker_record_invalid")
                    directory.write("events/" + str(event["ordinal"]).zfill(4) + ".result.json",
                                    canonical(_result_record(app, result)))
                    # Preserve produced bounded bytes even if parsing or a later
                    # lifecycle/read-binding check rejects this occurrence.
                    for role in ("snapshot", "metadata"):
                        produced = result.get(role + "_bytes")
                        if type(produced) is bytes:
                            directory.write("produced/" + app + "." + role + ".json", produced[:4096])
                    streams.finish(result)
                    end_ns, end_utc = time.monotonic_ns(), utc_now()
                    need(end_ns - before_ns <= 5_000_000_000, "worker_wall_time_limit")
                    need(time.monotonic() <= suite_deadline, "suite_wall_time_limit")
                    row, output_members = _receipt(selection, app, descriptor, raw, result, processes,
                                                   before_utc, before_ns, end_utc, end_ns)
                    directory.write("receipts/" + app + ".json", canonical(row))
                    rows.append(row)
                    members.update(output_members)
                    directory.write("events/" + str(event["ordinal"]).zfill(4) + ".completed.json", canonical({
                        "application_id": app, "ordinal": event["ordinal"], "capture_status": "complete",
                        "process_id": row["process_id"], "receipt": binding(canonical(row)),
                        "synthetic_execution": True}))
                    descriptor = dict(row["snapshot"])
                    raw = members[descriptor["member"]]
                finally:
                    streams.close()
        completed_ns, completed_utc = time.monotonic_ns(), utc_now()
        collector_source = next(item for item in selection["sources"] if item["role"] == "collector")
        collector_args = observation.sha(canonical({"mode": "synthetic_example",
                                                   "selection_sha256": prepared.selection_sha256}))
        context = {"record_type": "standalone_operator_capture_context_v0", "record_status": "example",
                   "selection_sha256": prepared.selection_sha256,
                   **{key: selection[key] for key in ("acquisition_id", "acquisition_attempt", "repository",
                                                      "source_commit", "environment")},
                   "started_utc": started_utc, "completed_utc": completed_utc,
                   "started_monotonic_ns": started_ns, "completed_monotonic_ns": completed_ns,
                   "collector": {"execution_id": "execution:" + selection["acquisition_id"] + ":collector",
                                 "process_id": os.getpid(), "source_path": collector_source["path"],
                                 "source_revision": collector_source["source_revision"],
                                 "arguments_sha256": collector_args,
                                 "command_sha256": observation.sha(canonical({"source_sha256": collector_source["sha256"],
                                                                             "arguments_sha256": collector_args})),
                                 "exit_code": 0}}
        members["capture/context.json"] = canonical(context)
        members["capture/application_receipts.json"] = canonical({
            "record_type": "standalone_operator_application_receipts_v0", "record_status": "example",
            "selection_sha256": prepared.selection_sha256, "applications": rows})
        members[observation.INVENTORY] = canonical({"record_type": "standalone_operator_member_inventory_v0",
                                                   "members": [binding(data, member=name)
                                                               for name, data in sorted(members.items())]})
        carrier = archive(members)
        observation.verify_observation(selection_bytes=prepared.selection_bytes,
                                       expected_selection_sha256=prepared.selection_sha256,
                                       carrier_bytes=carrier, expected_carrier_sha256=observation.sha(carrier))
        # A complete carrier is published only after the unchanged offline
        # verifier accepts all24 recorded relations. No partial ZIP is promoted.
        directory.write("acquisition.zip", carrier)
        carrier_sha = observation.sha(carrier)
        failed_application_id = None
    except BaseException as exc:
        if isinstance(exc, (AcquisitionError, observation.VerificationError, observation.safe.ContractError)):
            failure_code = exc.code
        elif isinstance(exc, (KeyboardInterrupt, SystemExit)):
            failure_code = "runner_interrupted"
        elif isinstance(exc, OSError):
            failure_code = "evidence_io_failure"
        else:
            failure_code = "runner_error"
    try:
        summary = {"record_type": "required_gate_idempotence_attempt_v0", "record_status": "example",
                   "status": "complete" if failure_code is None else "incomplete",
                   "selection_sha256": prepared.selection_sha256, "synthetic_execution": True,
                   "expected_applications": 24, "attempted_applications": len(attempted),
                   "completed_applications": len(rows), "attempted_application_ids": attempted,
                   "completed_application_ids": [row["application_id"] for row in rows],
                   "failure_code": failure_code, "failed_application_id": failed_application_id,
                   "carrier_sha256": carrier_sha, "limits": dict(LIMITS),
                   "files": directory.inventory(), "automatic_retry": False,
                   "automatic_cleanup": False, **BOUNDARY}
        directory.write("attempt.json", canonical(summary))
        return summary
    finally:
        directory.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="bind existing selected sources without launching them")
    prepare.add_argument("--selection", required=True, type=Path)
    prepare.add_argument("--selection-sha256", required=True)
    prepare.add_argument("--repository-root", required=True, type=Path)
    prepare.add_argument("--output-directory", required=True, type=Path)
    commands.add_parser("acquire", help="closed pending runtime closure and owner authorization")
    args = parser.parse_args(argv)
    try:
        need(args.command != "acquire", "observed_acquisition_not_ready")
        raw = observation.safe._read_regular(observation.safe._absolute(args.selection))
        need(observation.parse(raw).get("record_status") == "observed", "cli_observed_selection_required")
        prepared = prepare_selection(selection_bytes=raw, expected_selection_sha256=args.selection_sha256,
                                     repository_root=args.repository_root)
        result = write_preparation(prepared, args.output_directory)
    except (AcquisitionError, observation.VerificationError, observation.safe.ContractError) as exc:
        result = {"record_type": "required_gate_idempotence_acquisition_preparation_v0",
                  "status": "rejected", "errors": [exc.code], **BOUNDARY}
        sys.stdout.buffer.write(canonical(result))
        return 1
    sys.stdout.buffer.write(canonical(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

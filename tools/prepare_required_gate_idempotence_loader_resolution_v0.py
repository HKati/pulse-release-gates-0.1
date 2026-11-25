#!/usr/bin/env python3
"""Prepare, admit, acquire or replay the separate bounded loader profile.

An exact policy digest must be selected by the caller.  Only ``run-owner`` with
the new exact acknowledgement can run the fixed preflight probes and original
launcher.  Other commands execute signature verifiers as part of fresh input
admission, but never the launcher, a probe, or code from preserved artifacts.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import stat
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import required_gate_idempotence_loader_resolution_v0 as core
import required_gate_idempotence_mapping_observation_v0 as output_io
import required_gate_idempotence_exec_stop_hosted_io_v0 as transport


FILE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,191}\Z")


class CaptureDirectory(output_io._OutputDirectory):
    """Exclusive, flat, bounded publication with the new profile's roster."""

    def preserve(self, name, raw):
        core._need(type(name) is str and FILE_RE.fullmatch(name) is not None
                   and name not in {"capture.json", "attempt.incomplete.json"}
                   and name not in self.files and type(raw) is bytes,
                   "loader_resolution_preservation_name")
        core._need(len(self.files) < core.LIMITS["max_raw_files"]
                   and self.total + len(raw) <= core.LIMITS["max_raw_bytes"] + core.CONTROL_BYTES,
                   "loader_resolution_preservation_limit")
        self._check_root()
        identity = output_io._write_exclusive(self.fd, name, raw)
        self._check_root()
        self.files[name] = raw
        self.identities[name] = identity
        self.total += len(raw)

    def mark_failure(self, code):
        try:
            self._check_root()
            raw = core.canonical({
                "record_type": "required_gate_idempotence_loader_resolution_preservation_failure_v0",
                "profile": core.PROFILE, "status": "incomplete", "failure": code,
                **core.BOUNDARY,
            })
            output_io._write_exclusive(self.fd, "attempt.incomplete.json", raw)
            os.fsync(self.fd)
        except (OSError, ValueError):
            pass


def read_capture_directory(path):
    """Read a fixed flat capture; a saved verification report is not an input."""
    directory, chain = transport._pin_directory(Path(path).absolute())
    try:
        with os.scandir(directory) as entries:
            roster = [item.name for item in entries]
        core._need("capture.json" in roster
                   and "attempt.incomplete.json" not in roster
                   and len(roster) <= core.LIMITS["max_raw_files"] + 1
                   and all(FILE_RE.fullmatch(name) is not None for name in roster),
                   "loader_resolution_capture_directory_roster")
        capture_raw = transport._read_at(directory, "capture.json", core.CONTROL_BYTES)
        files, identities, total = {}, {}, 0
        for name in sorted(set(roster) - {"capture.json", "verification.json"}):
            info = os.stat(name, dir_fd=directory, follow_symlinks=False)
            core._need(stat.S_ISREG(info.st_mode)
                       and 0 <= info.st_size <= core.LIMITS["max_raw_bytes"] - total,
                       "loader_resolution_capture_directory_size")
            identities[name] = transport._identity(info)
            raw = transport._read_at(directory, name, info.st_size)
            files[name] = raw
            total += len(raw)
        transport._check_chain(chain)
        with os.scandir(directory) as entries:
            core._need({item.name for item in entries} == set(roster),
                       "loader_resolution_capture_directory_changed")
        for name, identity in identities.items():
            core._need(transport._identity(os.stat(name, dir_fd=directory, follow_symlinks=False))
                       == identity, "loader_resolution_capture_directory_changed")
        core._need(transport._read_at(directory, "capture.json", core.CONTROL_BYTES) == capture_raw,
                   "loader_resolution_capture_directory_changed")
        return capture_raw, files
    finally:
        transport._close_chain(chain)


def preserve_result(output, result):
    core._need(type(result) is dict and set(result) == {"capture", "files", "report"}
               and type(result["files"]) is dict, "loader_resolution_result_shape")
    files = result["files"]
    core._need(len(files) + 1 <= core.LIMITS["max_raw_files"]
               and all(type(value) is bytes for value in files.values())
               and not set(files) & {"capture.json", "verification.json", "attempt.incomplete.json"},
               "loader_resolution_result_extent")
    capture_raw = core.canonical(result["capture"])
    core._need(len(capture_raw) <= core.CONTROL_BYTES
               and sum(map(len, files.values())) + len(capture_raw) <= core.LIMITS["max_raw_bytes"],
               "loader_resolution_capture_size")
    for name, raw in sorted(files.items()):
        output.preserve(name, raw)
    if result["report"] is not None:
        report_raw = core.canonical(result["report"])
        core._need(len(report_raw) <= core.CONTROL_BYTES, "loader_resolution_report_size")
        output.preserve("verification.json", report_raw)
    output.publish(capture_raw)
    return capture_raw


def _preparation_report(admitted, request_raw):
    return {
        "record_type": "required_gate_idempotence_loader_resolution_preparation_verification_v0",
        "profile": core.PROFILE, "status": "accepted_request_and_scoped_inputs",
        "request": core.binding(request_raw),
        "attempt_id": admitted["request"]["attempt_id"],
        "original_admission": admitted["original_admission"],
        "source_build_report": admitted["source_build_report"],
        "source_build_gate_satisfied_under_policy": True,
        "fresh_guard_qualification_performed": False,
        "fresh_two_slot_qualification_performed": False,
        **core.BOUNDARY,
    }


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "check-request", "run-owner", "check-capture"):
        command = commands.add_parser(name)
        command.add_argument("--accepted-policy-sha256", required=True,
                             help="trusted external policy selection; never infer from a capture")
        if name == "prepare":
            command.add_argument("--attempt-id", required=True)
        else:
            command.add_argument("--request", type=Path, required=True)
            command.add_argument("--request-sha256", required=True)
        if name == "run-owner":
            command.add_argument("--acknowledgement", required=True)
            command.add_argument("--output-directory", type=Path, required=True)
        else:
            command.add_argument("--output", type=Path, required=True)
        if name == "check-capture":
            command.add_argument("--capture-directory", type=Path, required=True)
            command.add_argument("--capture-sha256", required=True)
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    output = None
    try:
        if args.command == "run-owner":
            core._need(args.acknowledgement == core.ACKNOWLEDGEMENT,
                       "loader_resolution_owner_acknowledgement_required")
        if args.command == "prepare":
            request = core.make_request(attempt_id=args.attempt_id,
                                       observer_descriptor=core.original._observer())
            request_raw = core.canonical(request)
            expected_request = core.sha(request_raw)
        else:
            request_raw = transport.read_regular(args.request, core.CONTROL_BYTES)
            expected_request = args.request_sha256
            core.validate_request(request_raw, expected_request)
        inputs = {"request_bytes": request_raw,
                  "expected_request_sha256": expected_request,
                  "accepted_policy_sha256": args.accepted_policy_sha256}
        if args.command == "run-owner":
            import collect_required_gate_idempotence_loader_resolution_v0 as producer
            output = CaptureDirectory(args.output_directory)
            result = producer.collect(**inputs, acknowledgement=args.acknowledgement)
            raw = preserve_result(output, result)
            report = result["report"] or {
                "record_type": "required_gate_idempotence_loader_resolution_acquisition_result_v0",
                "profile": core.PROFILE, "status": "preserved_incomplete",
                "capture": core.binding(raw), "failure": result["capture"].get("failure"),
                **core.BOUNDARY,
            }
            sys.stdout.buffer.write(core.canonical(report))
            return 0 if result["capture"].get("status") == "completed" and result["report"] else 1
        if args.command == "check-capture":
            import check_required_gate_idempotence_loader_resolution_v0 as checker
            capture_raw, files = read_capture_directory(args.capture_directory)
            report = checker.verify_capture(**inputs, capture_bytes=capture_raw,
                expected_capture_sha256=args.capture_sha256, files=files)
            transport.write_new(args.output, core.canonical(report))
        else:
            admitted = core.reconstruct_admission(**inputs)
            report = _preparation_report(admitted, request_raw)
            transport.write_new(args.output, request_raw if args.command == "prepare"
                                else core.canonical(report))
        sys.stdout.buffer.write(core.canonical(report))
        return 0
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError,
            output_io.MappingPreservationError) as exc:
        code = getattr(exc, "code", "loader_resolution_command_failed")
        if type(code) is not str or re.fullmatch(r"[a-z0-9_]{1,192}", code) is None:
            code = "loader_resolution_command_failed"
        if output is not None:
            output.mark_failure(code)
        sys.stdout.buffer.write(core.canonical({
            "record_type": "required_gate_idempotence_loader_resolution_command_verification_v0",
            "profile": core.PROFILE, "status": "rejected", "error_code": code,
            **core.BOUNDARY,
        }))
        return 1
    finally:
        if output is not None:
            output.close()


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Prepare, replay or explicitly acquire the bounded original entry checkpoint.

Every command freshly admits the original distribution and launch-host chain
using the existing signature verifier and its selected historical evaluation
epoch. Guard and hardware qualification records are mandatory separate inputs.
Only run-owner imports the native collector; checking preserved bytes never
starts the original launcher or repeats either qualification.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_required_gate_idempotence_mapping_observation_v0 as safe
import required_gate_idempotence_launcher_distribution_v0 as distribution_io
import prepare_required_gate_idempotence_exec_stop_v0 as original
import check_required_gate_idempotence_entry_stop_v0 as checker

ACKNOWLEDGEMENT = "OBSERVE_ORIGINAL_LAUNCHER_ENTRY_STOP_ONLY"


def _need(condition, code):
    if not condition:
        raise safe.MappingError(code)


def derive_request(originals, *, attempt_id, observer_descriptor,
                   qualification_bytes, expected_qualification_sha256,
                   hardware_qualification_bytes, expected_hardware_qualification_sha256):
    """Derive only after the public adapter's fresh original-chain admission."""
    prior = original.derive_request(originals, attempt_id=attempt_id,
                                    observer_descriptor=observer_descriptor)
    request = checker.make_request(attempt_id=attempt_id,
        observer_descriptor=observer_descriptor, qualification_bytes=qualification_bytes,
        expected_qualification_sha256=expected_qualification_sha256,
        hardware_qualification_bytes=hardware_qualification_bytes,
        expected_hardware_qualification_sha256=expected_hardware_qualification_sha256)
    _need(checker.canonical(request["cp0_request"]) == checker.canonical(prior),
          "entry_stop_fresh_original_request_mismatch")
    return request


def _preparation_report(request_raw, manifest):
    request = checker.validate_request(request_raw, checker.sha(request_raw))
    return {
        "record_type": "required_gate_idempotence_entry_stop_preparation_verification_v0",
        "profile": checker.PROFILE, "status": "accepted",
        "attempt_id": request["attempt_id"], "request": checker.binding(request_raw),
        "original_manifest_sha256": original.ORIGINAL_MANIFEST_SHA256,
        "original_input_count": len(manifest["files"]),
        "original_source_count": manifest["source_file_count"],
        "original_relationships_reconstructed": True,
        "distribution_signature_freshly_verified": True,
        "signature_evaluation_epoch": manifest["explicit_signature_policy"]["evaluation_time_epoch"],
        "original_reports_reproduced": True,
        "task_guard_qualification_record_verified": True,
        "hardware_qualification_record_verified": True,
        "entry_checkpoint_observed": False, "native_acquisition_performed": False,
        **checker.BOUNDARY,
    }


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "check", "run-owner", "check-capture"):
        command = commands.add_parser(name)
        command.add_argument("--originals-directory", type=Path, required=True)
        command.add_argument("--originals-sha256", required=True)
        command.add_argument("--verification-directory", type=Path, required=True)
        command.add_argument("--task-guard-qualification", type=Path, required=True)
        command.add_argument("--task-guard-qualification-sha256", required=True)
        command.add_argument("--hardware-qualification", type=Path, required=True)
        command.add_argument("--hardware-qualification-sha256", required=True)
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
    sink = None
    try:
        if args.command == "run-owner":
            _need(args.acknowledgement == ACKNOWLEDGEMENT,
                  "entry_stop_owner_acknowledgement_required")
        guard_raw = safe.read_selection_file(args.task_guard_qualification)
        hardware_raw = safe.read_selection_file(args.hardware_qualification)
        request = None
        if args.command != "prepare":
            request_raw = safe.read_selection_file(args.request)
            request = checker.validate_request(request_raw, args.request_sha256)
        sink = distribution_io.VerificationDirectory(args.verification_directory)
        manifest, originals = original.reconstruct_originals(
            args.originals_directory, args.originals_sha256, sink)
        _need(sink.count == 1, "entry_stop_fresh_signature_evidence_missing")
        derived = derive_request(originals,
            attempt_id=args.attempt_id if request is None else request["attempt_id"],
            observer_descriptor=original._observer() if request is None else request["observer"],
            qualification_bytes=guard_raw,
            expected_qualification_sha256=args.task_guard_qualification_sha256,
            hardware_qualification_bytes=hardware_raw,
            expected_hardware_qualification_sha256=args.hardware_qualification_sha256)
        derived_raw = checker.canonical(derived)
        checker.validate_request(derived_raw, checker.sha(derived_raw))
        if request is not None:
            _need(derived_raw == request_raw, "entry_stop_request_reconstruction")
        else:
            request_raw = derived_raw
        report = _preparation_report(request_raw, manifest)
        if args.command == "run-owner":
            import required_gate_idempotence_entry_stop_v0 as collector
            report = collector.run_acquisition(
                request_bytes=request_raw, expected_request_sha256=args.request_sha256,
                native_files={name: originals[name] for name in checker.NATIVE},
                qualification_bytes=guard_raw, hardware_qualification_bytes=hardware_raw,
                output_directory=args.output_directory, acknowledgement=args.acknowledgement)
        elif args.command == "check-capture":
            capture_raw, files = checker.read_capture_directory(args.capture_directory)
            report = checker.verify_capture(request_bytes=request_raw,
                expected_request_sha256=args.request_sha256,
                capture_bytes=capture_raw, expected_capture_sha256=args.capture_sha256,
                files=files)
            safe.write_new(args.output, checker.canonical(report))
        else:
            safe.write_new(args.output, request_raw if args.command == "prepare"
                           else checker.canonical(report))
        sys.stdout.buffer.write(checker.canonical(report))
        if args.command == "run-owner" and not report.get("observation_complete"):
            return 1
        return 0 if report.get("status") == "accepted" else 1
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError) as exc:
        code = getattr(exc, "code", str(exc))
        if not isinstance(code, str) or safe.ERROR_RE.fullmatch(code) is None:
            code = "entry_stop_preparation_failed"
        sys.stdout.buffer.write(checker.canonical({
            "record_type": "required_gate_idempotence_entry_stop_preparation_verification_v0",
            "profile": checker.PROFILE, "status": "rejected", "error_code": code,
            **checker.BOUNDARY,
        }))
        return 1
    finally:
        if sink is not None:
            sink.close()


if __name__ == "__main__":
    raise SystemExit(main())

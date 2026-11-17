#!/usr/bin/env python3
"""Prepare/check the exact original-launcher exec-stop request from original inputs.

Every command reconstructs the preserved launch-host/distribution chain and
freshly verifies its signatures at its original selected evaluation epoch.
The old authored inert runtime capsule retains its original scope. Preparing
or checking a request never runs the launcher. Only the separately acknowledged
``run-owner`` command enters the fixed acquisition collector.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_required_gate_idempotence_mapping_observation_v0 as safe
import check_required_gate_idempotence_launcher_distribution_v0 as distribution
import required_gate_idempotence_launcher_distribution_v0 as distribution_io
import check_required_gate_idempotence_exec_stop_v0 as checker

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_MANIFEST_SHA256 = "16c541b8fd733dcef1b495b104b5377d11624b6106fbfa740e5ec6eb856cdfaa"
ORIGINAL_REPORT = {
    "sha256": "a0d7cf825dce1c8a3b09a2306f155f24bdcabc4a16cb90215f6d4e04925f4f36",
    "size_bytes": 3780,
}
FILE_LIMIT = 128 * 1024 * 1024
TOTAL_LIMIT = 256 * 1024 * 1024
ACKNOWLEDGEMENT = "OBSERVE_ORIGINAL_LAUNCHER_EXEC_STOP_ONLY"


def _need(condition, code):
    if not condition:
        raise safe.MappingError(code)


def _member(directory, name, maximum):
    """Pin every input ancestor and open the final file nonblockingly."""
    _need(type(name) is str and "\\" not in name, "exec_stop_original_path")
    path = PurePosixPath(name)
    _need(not path.is_absolute() and path.as_posix() == name
          and all(part not in {"", ".", ".."} for part in path.parts),
          "exec_stop_original_path")
    parent, chain = safe._pin_directory(Path(directory).joinpath(*path.parts[:-1]))
    try:
        raw = safe._read_relative(parent, path.name, maximum)
        safe._check_chain(chain)
        return raw
    finally:
        safe._close_chain(chain)


def load_originals(directory, expected_manifest_sha256):
    """Read only the fixed original case; its saved replay code is never run."""
    _need(expected_manifest_sha256 == ORIGINAL_MANIFEST_SHA256,
          "exec_stop_original_manifest_selection")
    raw = _member(directory, "CASE_INPUTS.json", safe.CONTROL_BYTES)
    _need(safe.sha(raw) == expected_manifest_sha256, "exec_stop_original_manifest_digest")
    # The externally fixed digest selects the entire original manifest. Its
    # historical formatting is preserved rather than rewritten as new JSON.
    manifest = json.loads(raw.decode("utf-8"), object_pairs_hook=safe._pairs,
                          parse_constant=safe._constant)
    _need(manifest["record_type"] == "launcher_distribution_original_byte_example_v0"
          and manifest["record_status"] == "example"
          and type(manifest["files"]) is dict and len(manifest["files"]) == 111,
          "exec_stop_original_manifest_profile")
    originals, total = {}, 0
    for name, descriptor in sorted(manifest["files"].items()):
        safe._keys(descriptor, ("sha256", "size_bytes"), "exec_stop_original_binding")
        safe._digest(descriptor["sha256"], "exec_stop_original_binding")
        safe._integer(descriptor["size_bytes"], "exec_stop_original_binding", maximum=FILE_LIMIT)
        total += descriptor["size_bytes"]
        _need(total <= TOTAL_LIMIT, "exec_stop_original_total_limit")
        item = _member(directory, name, descriptor["size_bytes"])
        _need(safe.binding(item) == descriptor, "exec_stop_original_bytes_changed")
        originals[name] = item
    # Reports were produced after the historical manifest, so each remains
    # selected by its separately retained original digest, never by its name.
    reports = [_member(directory, "results/checker-" + str(n) + ".json", 3780)
               for n in (1, 2)]
    _need(all(safe.binding(item) == ORIGINAL_REPORT for item in reports)
          and reports[0] == reports[1], "exec_stop_original_report_digest")
    originals["distribution-verification.json"] = reports[0]
    _check_old_sources(manifest, originals)
    return manifest, originals


def _check_old_sources(manifest, originals):
    names = [name for name in manifest["files"] if name.startswith("verifier-source/")]
    _need(len(names) == manifest["source_file_count"] == 43,
          "exec_stop_original_source_roster")
    for name in names:
        relative = name.removeprefix("verifier-source/")
        _need(safe._source_bytes(relative) == originals[name],
              "exec_stop_original_source_changed")


def _original_inputs(manifest, originals, evidence_sink):
    """Use the existing independent admission functions, with original bytes."""
    containment = distribution.host.containment

    def control(name):
        return originals["controls/" + name]

    def digest(name):
        return manifest["files"][name]["sha256"]

    bootstrap_inputs = {}
    for stem in ("runtime_selection", "operator_selection", "bootstrap_selection"):
        name = "controls/" + stem.replace("_", "-") + ".json"
        bootstrap_inputs[stem + "_bytes"] = originals[name]
        bootstrap_inputs["expected_" + stem + "_sha256"] = digest(name)
    bootstrap_inputs["capsule_bytes"] = originals[manifest["capsule"]]
    bootstrap_inputs["expected_capsule_sha256"] = digest(manifest["capsule"])
    bootstrap = containment.bootstrap.prepare_bootstrap(**bootstrap_inputs)
    containment.bootstrap.verify_bootstrap_plan(
        plan_bytes=control("bootstrap-plan.json"),
        expected_plan_sha256=digest("controls/bootstrap-plan.json"), **bootstrap_inputs)
    prepared = containment.prepare_containment(
        bootstrap_prepared=bootstrap,
        expected_bootstrap_plan_sha256=digest("controls/bootstrap-plan.json"),
        selection_bytes=control("containment-selection.json"),
        expected_selection_sha256=digest("controls/containment-selection.json"),
        launcher_bytes=originals["native/bwrap"],
        entry_bytes=originals["entry-build/build-1/entry"])
    containment.verify_request(prepared, request_bytes=control("containment-request.json"),
                               expected_request_sha256=digest("controls/containment-request.json"))
    host_inputs = {
        "containment_prepared": prepared,
        "expected_containment_request_sha256": digest("controls/containment-request.json"),
        "selection_bytes": control("launch-host-selection.json"),
        "expected_selection_sha256": digest("controls/launch-host-selection.json"),
        "entry_build_payload": {name: originals["entry-build/" + name]
                                for name in manifest["entry_build_paths"]},
        "launcher_package_bytes": originals[manifest["package"]],
        "native_payload": {name: originals[name] for name in manifest["native_paths"]},
        "host_observation_bytes": control("host-observation.json"),
    }
    return {
        "launch_host_inputs": host_inputs,
        "launch_host_plan_bytes": originals["launch-host-plan.json"],
        "expected_launch_host_plan_sha256": digest("launch-host-plan.json"),
        "selection_bytes": control("distribution-selection.json"),
        "expected_selection_sha256": digest("controls/distribution-selection.json"),
        "trust_policy_bytes": control("distribution-trust-policy.json"),
        "expected_trust_policy_sha256": digest("controls/distribution-trust-policy.json"),
        "release_bytes": originals["distribution-origin/Release"],
        "release_signature_bytes": originals["distribution-origin/Release.gpg"],
        "packages_xz_bytes": originals["distribution-origin/Packages.xz"],
        "keyring_bytes": originals["distribution-origin/debian-archive-keyring.gpg"],
        "verifier_path": Path(manifest["external_verifier"]["path"]),
        "signature_evidence_sink": evidence_sink,
    }


def reconstruct_originals(directory, expected_manifest_sha256, evidence_sink):
    """Fresh signature + full old reconstruction, never a saved-report shortcut."""
    manifest, originals = load_originals(directory, expected_manifest_sha256)
    source_pins = checker.source_bindings()
    inputs = _original_inputs(manifest, originals, evidence_sink)
    record = originals["launcher-distribution-record.json"]
    report = distribution.verify_record(
        record_bytes=record, expected_record_sha256=safe.sha(record), **inputs)
    _need(distribution.canonical(report) == originals["distribution-verification.json"],
          "exec_stop_original_report_reconstruction")
    saved_record = distribution.parse(record)
    _need(saved_record["bindings"]["launch_host_verification"]
          == safe.binding(originals["launch-host-verification.json"])
          and saved_record["bindings"]["packages_decoded"]
          == safe.binding(originals["distribution-origin/Packages"]),
          "exec_stop_original_transitive_binding")
    _check_old_sources(manifest, originals)
    _need(source_pins == checker.source_bindings(), "exec_stop_preparation_source_changed")
    return manifest, originals


def _observer():
    """Read the current observer object; the path string is only its descriptor."""
    _need(sys.platform == "linux" and os.uname().machine == "x86_64",
          "exec_stop_observer_platform")
    path = os.readlink("/proc/self/exe")
    _need(path.startswith("/") and not path.endswith(" (deleted)") and len(path) <= 4096,
          "exec_stop_observer_path")
    fd = os.open("/proc/self/exe", os.O_RDONLY | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        _need(stat.S_ISREG(before.st_mode)
              and 0 < before.st_size <= 33554432, "exec_stop_observer_file")
        raw = safe._read_fd(fd, before.st_size, "exec_stop_observer")
        _need(safe._identity(before) == safe._identity(os.fstat(fd))
              and len(raw) == before.st_size and os.readlink("/proc/self/exe") == path,
              "exec_stop_observer_changed")
        return {"path": path, **safe.binding(raw)}
    finally:
        os.close(fd)


def derive_request(originals, *, attempt_id, observer_descriptor):
    return checker.make_request(
        attempt_id=attempt_id, observer_descriptor=observer_descriptor,
        launch_host_plan_bytes=originals["launch-host-plan.json"],
        launch_host_report_bytes=originals["launch-host-verification.json"],
        distribution_record_bytes=originals["launcher-distribution-record.json"],
        distribution_report_bytes=originals["distribution-verification.json"],
        native_files={name: raw for name, raw in originals.items() if name.startswith("native/")},
    )


def _preparation_report(request_raw, manifest):
    request = checker.validate_request(request_raw, safe.sha(request_raw))
    return {
        "record_type": "required_gate_idempotence_exec_stop_preparation_verification_v0",
        "profile": checker.PROFILE, "status": "accepted",
        "attempt_id": request["attempt_id"], "request": safe.binding(request_raw),
        "original_manifest_sha256": ORIGINAL_MANIFEST_SHA256,
        "original_input_count": len(manifest["files"]),
        "original_source_count": manifest["source_file_count"],
        "original_relationships_reconstructed": True,
        "distribution_signature_freshly_verified": True,
        "signature_evaluation_epoch": manifest["explicit_signature_policy"]["evaluation_time_epoch"],
        "original_reports_reproduced": True,
        "kernel_exec_checkpoint_observed": False,
        "original_exec_reached": False,
        "native_acquisition_performed": False,
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
            _need(args.acknowledgement == ACKNOWLEDGEMENT, "exec_stop_owner_acknowledgement")
        request = None
        if args.command != "prepare":
            request_raw = safe.read_selection_file(args.request)
            request = checker.validate_request(request_raw, args.request_sha256)
        sink = distribution_io.VerificationDirectory(args.verification_directory)
        manifest, originals = reconstruct_originals(
            args.originals_directory, args.originals_sha256, sink)
        _need(sink.count == 1, "exec_stop_fresh_signature_evidence_missing")
        derived = derive_request(
            originals, attempt_id=args.attempt_id if request is None else request["attempt_id"],
            observer_descriptor=_observer() if request is None else request["observer"])
        derived_raw = checker.canonical(derived)
        checker.validate_request(derived_raw, safe.sha(derived_raw))
        if request is not None:
            _need(derived_raw == request_raw, "exec_stop_request_reconstruction")
        else:
            request_raw = derived_raw
        report = _preparation_report(request_raw, manifest)
        if args.command == "run-owner":
            # Import the collector only in this separately acknowledged command.
            # Prepare/check/check-capture never enter this execution path.
            import required_gate_idempotence_exec_stop_v0 as collector
            report = collector.run_acquisition(
                request_bytes=request_raw, expected_request_sha256=args.request_sha256,
                native_files={name: originals[name] for name in checker.ROLE_PATHS.values()},
                output_directory=args.output_directory, acknowledgement=args.acknowledgement)
        elif args.command == "check-capture":
            capture_raw, files = checker.read_capture_directory(args.capture_directory)
            report = checker.verify_capture(
                request_bytes=request_raw, expected_request_sha256=args.request_sha256,
                capture_bytes=capture_raw, expected_capture_sha256=args.capture_sha256, files=files)
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
            code = "exec_stop_preparation_failed"
        sys.stdout.buffer.write(checker.canonical({
            "record_type": "required_gate_idempotence_exec_stop_preparation_verification_v0",
            "profile": checker.PROFILE, "status": "rejected", "error_code": code,
            **checker.BOUNDARY,
        }))
        return 1
    finally:
        if sink is not None:
            sink.close()


if __name__ == "__main__":
    raise SystemExit(main())

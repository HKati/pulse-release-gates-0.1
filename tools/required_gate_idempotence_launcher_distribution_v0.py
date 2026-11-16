#!/usr/bin/env python3
"""Bind a launch-host plan to original signed Debian distribution metadata.

The separately selected, hash-bound GPG verifier checks the detached signatures.
Existing selected-source admission retains its transport-disabled local Git
checks. Every prepare and check reconstructs the original byte relationships;
launcher, entry and runtime execution remain closed.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_required_gate_idempotence_launcher_distribution_v0 as checker
import required_gate_idempotence_launch_host_v0 as launch_host
import required_gate_idempotence_debian_metadata_v0 as metadata
import required_gate_idempotence_distribution_signature_v0 as signature

runtime = launch_host.runtime
safe = launch_host.safe
entry_build = launch_host.entry_build


class VerificationDirectory:
    """Preserve each fresh verifier invocation in a new, private directory."""

    def __init__(self, path):
        self.path = Path(path).absolute()
        self.fd = None
        self.count = 0
        parent, name = safe._output_preflight(self.path)
        try:
            os.mkdir(name, 0o700, dir_fd=parent)
            self.fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                              dir_fd=parent)
            self._check_location()
        except BaseException:
            self.close()
            raise
        finally:
            os.close(parent)

    def _check_location(self):
        current = entry_build._open_directory(self.path)
        try:
            expected, observed = os.fstat(self.fd), os.fstat(current)
            if (expected.st_dev, expected.st_ino) != (observed.st_dev, observed.st_ino):
                raise checker.DistributionError("distribution_verification_directory_changed")
        finally:
            os.close(current)

    def __call__(self, payload):
        if (type(payload) is not dict or set(payload) != {
                "stdout_bytes", "stderr_bytes", "process_record"}
                or type(payload["stdout_bytes"]) is not bytes
                or len(payload["stdout_bytes"]) > signature.STDOUT_LIMIT
                or type(payload["stderr_bytes"]) is not bytes
                or len(payload["stderr_bytes"]) > signature.STDERR_LIMIT
                or type(payload["process_record"]) is not dict or self.count >= 2):
            raise checker.DistributionError("distribution_verification_evidence_invalid")
        process_bytes = checker.canonical(payload["process_record"])
        if len(process_bytes) > runtime.CONTROL_LIMIT:
            raise checker.DistributionError("distribution_verification_evidence_limit")
        self._check_location()
        prefix = "verification-" + str(self.count + 1)
        for suffix, raw in ((".status.bin", payload["stdout_bytes"]),
                            (".stderr.bin", payload["stderr_bytes"]),
                            (".process.json", process_bytes)):
            safe._write_output(self.fd, prefix + suffix, raw)
        os.fsync(self.fd)
        self._check_location()
        self.count += 1

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "check"):
        command = commands.add_parser(name)
        for item in ("runtime-selection", "operator-selection", "capsule", "bootstrap-selection",
                     "bootstrap-plan", "containment-selection", "containment-request", "launch-host-selection",
                     "launch-host-plan", "distribution-selection", "trust-policy"):
            command.add_argument("--" + item, type=Path, required=True)
            command.add_argument("--" + item + "-sha256", required=True)
        for item in ("launcher", "entry-shim", "entry-build-directory", "launcher-package", "native-root",
                     "host-observation", "release", "release-signature", "packages-xz", "keyring", "verifier"):
            command.add_argument("--" + item, type=Path, required=True)
        command.add_argument("--repository-root", type=Path)
        command.add_argument("--verification-directory", type=Path)
        command.add_argument("--output", type=Path, required=name == "prepare")
        if name == "check":
            command.add_argument("--record", type=Path, required=True)
            command.add_argument("--record-sha256", required=True)
    return parser


def _original_inputs(args, evidence_sink=None):
    read = runtime.read_regular
    selection_bytes = read(args.distribution_selection, runtime.CONTROL_LIMIT)
    checker.validate_selection(selection_bytes, args.distribution_selection_sha256)
    trust_policy_bytes = read(args.trust_policy, runtime.CONTROL_LIMIT)
    checker.validate_trust_policy(trust_policy_bytes, args.trust_policy_sha256)
    return {
        "launch_host_inputs": launch_host._original_inputs(args),
        "launch_host_plan_bytes": read(args.launch_host_plan, runtime.CONTROL_LIMIT),
        "expected_launch_host_plan_sha256": args.launch_host_plan_sha256,
        "selection_bytes": selection_bytes,
        "expected_selection_sha256": args.distribution_selection_sha256,
        "trust_policy_bytes": trust_policy_bytes,
        "expected_trust_policy_sha256": args.trust_policy_sha256,
        "release_bytes": read(args.release, metadata.RELEASE_LIMIT),
        "release_signature_bytes": read(args.release_signature, signature.SIGNATURE_LIMIT),
        "packages_xz_bytes": read(args.packages_xz, metadata.INDEX_COMPRESSED_LIMIT),
        "keyring_bytes": read(args.keyring, signature.KEYRING_LIMIT),
        "verifier_path": args.verifier,
        "signature_evidence_sink": evidence_sink,
    }


def main(argv=None):
    args = _parser().parse_args(argv)
    output_parent = None
    evidence_sink = None
    try:
        if args.output is not None:
            output_parent, output_name = safe._output_preflight(args.output)
        if args.verification_directory is not None:
            evidence_sink = VerificationDirectory(args.verification_directory)
        inputs = _original_inputs(args, evidence_sink)
        if args.command == "prepare":
            record_bytes = checker.derive_record(**inputs)
            report = checker.verify_record(record_bytes, checker.sha(record_bytes), **inputs)
            safe._write_output(output_parent, output_name, record_bytes)
        else:
            report = checker.verify_record(runtime.read_regular(args.record, runtime.CONTROL_LIMIT),
                                           args.record_sha256, **inputs)
            if output_parent is not None:
                safe._write_output(output_parent, output_name, checker.canonical(report))
        sys.stdout.buffer.write(checker.canonical(report))
        return 0
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        sys.stdout.buffer.write(checker.canonical({
            "record_type": "required_gate_idempotence_launcher_distribution_verification_v0",
            "profile": checker.PROFILE, "status": "rejected",
            "error_code": getattr(exc, "code", "distribution_operation_failed"), **checker.BOUNDARY,
        }))
        return 1
    finally:
        if evidence_sink is not None:
            evidence_sink.close()
        if output_parent is not None:
            os.close(output_parent)


if __name__ == "__main__":
    raise SystemExit(main())

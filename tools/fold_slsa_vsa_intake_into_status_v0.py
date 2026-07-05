#!/usr/bin/env python3
import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Optional


TOOL_NAME = "fold_slsa_vsa_intake_into_status_v0"
INTAKE_TOOL_NAME = "ingest_slsa_vsa_evidence_v0"

SCHEMA_VERSION = "slsa_vsa_evidence_v0"
EVIDENCE_TYPE = "slsa_vsa"
SIGNATURE_VERIFICATION_MODE = "recorded_signal_only"

REQUIRED_PULSE_SIGNALS = [
    "slsa_vsa_present",
    "slsa_vsa_signature_ok",
    "slsa_vsa_subject_matches_artifact",
    "slsa_vsa_predicate_type_ok",
    "slsa_vsa_verifier_trusted",
    "slsa_vsa_resource_uri_matches",
    "slsa_vsa_policy_digest_matches",
    "slsa_vsa_result_passed",
    "slsa_vsa_verified_level_ok",
]

REQUIRED_INTAKE_CHECKS = [
    "schema_valid",
    "evidence_valid",
    "contract_fields_ok",
    "predicate_type_ok",
    "verification_result_passed",
    "subject_matches_artifact",
    "resource_uri_matches",
    "verifier_trusted",
    "policy_digest_matches",
    "verified_level_ok",
    "pulse_signals_literal_booleans",
    "pulse_signals_required_true",
    "pulse_signals_consistent",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fold a validated PULSEmech SLSA / in-toto VSA intake report "
            "into a new output status JSON."
        )
    )
    parser.add_argument("--status", required=True, help="Path to the base status JSON")
    parser.add_argument("--intake-report", required=True, help="Path to the intake report JSON")
    parser.add_argument("--output", required=True, help="Path for the new folded status JSON")
    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def same_status_target(left: Path, right: Path) -> bool:
    if left.resolve() == right.resolve():
        return True

    try:
        if left.exists() and right.exists() and left.samefile(right):
            return True
    except OSError:
        pass

    return False


def make_report(
    *,
    ok: bool,
    output_status_written: bool,
    folded_gates: list[str],
    errors: list[str],
) -> dict[str, Any]:
    return {
        "tool": TOOL_NAME,
        "ok": ok,
        "output_status_written": output_status_written,
        "folded_gates": folded_gates,
        "errors": errors,
    }


def emit_report(report: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def validate_base_status(status: Any, errors: list[str]) -> Optional[dict[str, Any]]:
    if not isinstance(status, dict):
        errors.append("status_not_object")
        return None

    gates = status.get("gates")
    if not isinstance(gates, dict):
        errors.append("status_gates_not_object")
        return None

    return status


def validate_intake_report(report: Any, errors: list[str]) -> Optional[dict[str, Any]]:
    if not isinstance(report, dict):
        errors.append("intake_report_not_object")
        return None

    if report.get("tool") != INTAKE_TOOL_NAME:
        errors.append("intake_report_tool_mismatch")

    if report.get("ok") is not True:
        errors.append("intake_report_not_ok")

    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("intake_report_schema_version_mismatch")

    if report.get("evidence_type") != EVIDENCE_TYPE:
        errors.append("intake_report_evidence_type_mismatch")

    if report.get("signature_verification_mode") != SIGNATURE_VERIFICATION_MODE:
        errors.append("intake_report_signature_mode_mismatch")

    report_errors = report.get("errors")
    if report_errors != []:
        errors.append("intake_report_errors_not_empty")

    checks = report.get("checks")
    if not isinstance(checks, dict):
        errors.append("intake_report_checks_not_object")
    else:
        for check_name in REQUIRED_INTAKE_CHECKS:
            if checks.get(check_name) is not True:
                errors.append(f"intake_check_not_true: {check_name}")

    pulse_signals = report.get("pulse_signals")
    if not isinstance(pulse_signals, dict):
        errors.append("intake_report_pulse_signals_not_object")
    else:
        for signal in REQUIRED_PULSE_SIGNALS:
            if signal not in pulse_signals:
                errors.append(f"pulse_signal_missing: {signal}")
            elif not isinstance(pulse_signals[signal], bool):
                errors.append(f"pulse_signal_not_boolean: {signal}")
            elif pulse_signals[signal] is not True:
                errors.append(f"pulse_signal_not_true: {signal}")

    return report


def validate_existing_gate_conflicts(
    status: dict[str, Any],
    pulse_signals: dict[str, Any],
    errors: list[str],
) -> None:
    gates = status["gates"]

    for signal in REQUIRED_PULSE_SIGNALS:
        if signal not in gates:
            continue

        incoming = pulse_signals.get(signal)
        if incoming is None:
            continue

        if gates[signal] is not incoming:
            errors.append(f"existing_gate_conflict: {signal}")


def fold_signals_into_status(status: dict[str, Any], pulse_signals: dict[str, Any]) -> dict[str, Any]:
    folded = copy.deepcopy(status)
    gates = folded["gates"]

    for signal in REQUIRED_PULSE_SIGNALS:
        gates[signal] = pulse_signals[signal]

    return folded


def build_folded_status(
    status_path: Path,
    intake_report_path: Path,
    output_path: Path,
) -> tuple[dict[str, Any], Optional[dict[str, Any]], int]:
    errors: list[str] = []

    if same_status_target(status_path, output_path):
        errors.append("refusing_in_place_status_write")
        return make_report(
            ok=False,
            output_status_written=False,
            folded_gates=[],
            errors=errors,
        ), None, 2

    try:
        status_raw = load_json(status_path)
    except Exception as exc:
        errors.append(f"status_read_error: {exc}")
        return make_report(
            ok=False,
            output_status_written=False,
            folded_gates=[],
            errors=errors,
        ), None, 2

    try:
        intake_raw = load_json(intake_report_path)
    except Exception as exc:
        errors.append(f"intake_report_read_error: {exc}")
        return make_report(
            ok=False,
            output_status_written=False,
            folded_gates=[],
            errors=errors,
        ), None, 2

    status = validate_base_status(status_raw, errors)
    intake_report = validate_intake_report(intake_raw, errors)

    pulse_signals: dict[str, Any] = {}
    if isinstance(intake_report, dict) and isinstance(intake_report.get("pulse_signals"), dict):
        pulse_signals = intake_report["pulse_signals"]

    if not errors and status is not None and pulse_signals:
        validate_existing_gate_conflicts(status, pulse_signals, errors)

    if errors:
        return make_report(
            ok=False,
            output_status_written=False,
            folded_gates=[],
            errors=errors,
        ), None, 1

    assert status is not None
    folded_status = fold_signals_into_status(status, pulse_signals)

    report = make_report(
        ok=True,
        output_status_written=True,
        folded_gates=list(REQUIRED_PULSE_SIGNALS),
        errors=[],
    )
    return report, folded_status, 0


def main() -> int:
    args = parse_args()

    status_path = Path(args.status)
    intake_report_path = Path(args.intake_report)
    output_path = Path(args.output)

    report, folded_status, exit_code = build_folded_status(
        status_path,
        intake_report_path,
        output_path,
    )

    if exit_code == 0:
        assert folded_status is not None

        try:
            write_json(output_path, folded_status)
        except Exception as exc:
            report = make_report(
                ok=False,
                output_status_written=False,
                folded_gates=[],
                errors=[f"output_write_error: {exc}"],
            )
            emit_report(report)
            return 2

    emit_report(report)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

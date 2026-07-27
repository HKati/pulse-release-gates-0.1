#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


TOOL_ID = "build_pulsemech_compute_binding_report_from_subject_input_v0"
TOOL_VERSION = "0.1.0"

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKET = (
    ROOT
    / "examples"
    / "compute"
    / "pulsemech_compute_subject_input_packet_6066_observed_v0.json"
)
DEFAULT_CARRIER = ROOT / "PULSE_CI_6066_release_grade_artifact_preservation_v0.zip"
PACKET_SCHEMA = ROOT / "schemas" / "pulsemech_compute_subject_input_packet_v0.schema.json"
PACKET_VALIDATOR = ROOT / "tools" / "check_pulsemech_compute_subject_input_packet_v0.py"
REPORT_SCHEMA = ROOT / "schemas" / "pulsemech_compute_binding_report_v0.schema.json"
REPORT_VALIDATOR = ROOT / "tools" / "check_pulsemech_compute_binding_report_v0.py"
FIXED_SOURCE_BUILDER = ROOT / "tools" / "build_pulsemech_compute_binding_report_v0.py"

DEFAULT_ANALYSIS_RUN_KEY = (
    "OFFLINE_ANALYSIS=pulsemech-compute-binding-fixed-source-6066-v0"
)

VISIBLE_ROLE_FILENAMES = {
    "preservation_manifest": "PRESERVATION_MANIFEST_v0.json",
    "preservation_readme": "README.md",
    "preservation_checksums": "SHA256SUMS",
}

PROTECTED_OUTPUT_NAMES = {
    "status.json",
    "release_decision_v0.json",
    "release_authority_v0.json",
    "pulsemech_compute_subject_input_packet_v0.json",
}


class AdapterError(RuntimeError):
    pass


class StrictJsonError(ValueError):
    pass


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJsonError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_non_finite(value: str) -> None:
    raise StrictJsonError(f"non-finite JSON value: {value}")


def load_json_bytes(data: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_non_finite,
        )
    except Exception as exc:
        raise AdapterError(f"{label}_json_invalid: {exc}") from exc
    if not isinstance(value, dict):
        raise AdapterError(f"{label}_not_object")
    return value


def load_json_path(path: Path, *, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise AdapterError(f"{label}_missing: {path}")
    if path.is_symlink():
        raise AdapterError(f"{label}_symlink_rejected: {path}")
    reject_symlink_components(path, label=label)
    return load_json_bytes(path.read_bytes(), label=label)


def render_json(value: dict[str, Any]) -> str:
    return (
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AdapterError(message)


def require_equal(actual: Any, expected: Any, *, label: str) -> None:
    if actual != expected:
        raise AdapterError(
            f"{label}_mismatch: expected={expected!r} actual={actual!r}"
        )


def same_target(left: Path, right: Path) -> bool:
    try:
        if left.resolve() == right.resolve():
            return True
    except OSError:
        pass
    try:
        return left.exists() and right.exists() and left.samefile(right)
    except OSError:
        return False


def is_within(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
        return True
    except (OSError, ValueError):
        return False


def reject_symlink_components(path: Path, *, label: str) -> None:
    cursor = path
    while True:
        if cursor.is_symlink():
            raise AdapterError(f"{label}_symlink_rejected: {cursor}")
        if cursor == cursor.parent:
            return
        cursor = cursor.parent


def require_regular_file(path: Path, *, label: str) -> None:
    if not path.is_file():
        raise AdapterError(f"{label}_missing: {path}")
    if path.is_symlink():
        raise AdapterError(f"{label}_symlink_rejected: {path}")
    reject_symlink_components(path, label=label)


def snapshot(paths: tuple[Path, ...]) -> dict[str, tuple[int, str]]:
    result: dict[str, tuple[int, str]] = {}
    for path in paths:
        require_regular_file(path, label=f"protected_input:{path.name}")
        result[str(path.resolve())] = (path.stat().st_size, sha256_file(path))
    return result


def inputs_unchanged(
    paths: tuple[Path, ...],
    before: dict[str, tuple[int, str]],
) -> bool:
    try:
        return snapshot(paths) == before
    except Exception:
        return False


def reject_unsafe_output(
    output: Path | None,
    *,
    packet: Path,
    carrier: Path,
    repository_root: Path,
) -> None:
    if output is None:
        return

    protected = (
        packet,
        carrier,
        PACKET_SCHEMA,
        PACKET_VALIDATOR,
        REPORT_SCHEMA,
        REPORT_VALIDATOR,
        FIXED_SOURCE_BUILDER,
        Path(__file__),
    )
    for path in protected:
        if same_target(output, path):
            raise AdapterError(f"refusing_to_overwrite_input: {path}")

    if output.name in PROTECTED_OUTPUT_NAMES:
        raise AdapterError(f"refusing_authority_surface_output: {output.name}")

    if is_within(output, ROOT):
        raise AdapterError(f"refusing_output_inside_tool_repository: {output}")
    if is_within(output, repository_root):
        raise AdapterError(f"refusing_output_inside_subject_repository: {output}")

    cursor = output
    while True:
        if cursor.is_symlink():
            raise AdapterError(f"refusing_symlink_output_path: {cursor}")
        if cursor == cursor.parent:
            break
        cursor = cursor.parent


def safe_zip_members(
    archive: zipfile.ZipFile,
    *,
    label: str,
) -> dict[str, zipfile.ZipInfo]:
    infos = archive.infolist()
    names = [info.filename for info in infos]
    if len(names) != len(set(names)):
        raise AdapterError(f"{label}_duplicate_member")

    corrupt = archive.testzip()
    if corrupt is not None:
        raise AdapterError(f"{label}_crc_failure: {corrupt}")

    result: dict[str, zipfile.ZipInfo] = {}
    for info in infos:
        name = info.filename
        path = PurePosixPath(name)
        mode = info.external_attr >> 16

        if not name:
            raise AdapterError(f"{label}_empty_member_name")
        if "\\" in name:
            raise AdapterError(f"{label}_backslash_member: {name}")
        if path.is_absolute() or ".." in path.parts:
            raise AdapterError(f"{label}_unsafe_member_path: {name}")
        if info.is_dir():
            raise AdapterError(f"{label}_directory_member: {name}")
        if stat.S_ISLNK(mode):
            raise AdapterError(f"{label}_symlink_member: {name}")
        if info.flag_bits & 0x1:
            raise AdapterError(f"{label}_encrypted_member: {name}")

        result[name] = info
    return result


def load_module(path: Path, module_name: str) -> Any:
    require_regular_file(path, label=module_name)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AdapterError(f"module_import_spec_unavailable: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise AdapterError(f"module_import_failed: {path}: {exc}") from exc
    return module


def validate_subject_packet(
    *,
    packet: Path,
    carrier: Path,
    repository_root: Path,
) -> dict[str, Any]:
    result = subprocess.run(
        [
            sys.executable,
            str(PACKET_VALIDATOR),
            "--schema",
            str(PACKET_SCHEMA),
            "--packet",
            str(packet),
            "--carrier",
            str(carrier),
            "--repository-root",
            str(repository_root),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    if "Traceback" in result.stderr:
        raise AdapterError(f"subject_input_validator_traceback: {result.stderr.strip()}")

    try:
        diagnostic = json.loads(
            result.stdout,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_non_finite,
        )
    except Exception as exc:
        raise AdapterError(
            "subject_input_validator_diagnostic_invalid: "
            f"returncode={result.returncode} stdout={result.stdout!r} "
            f"stderr={result.stderr!r}"
        ) from exc

    if (
        result.returncode != 0
        or not isinstance(diagnostic, dict)
        or diagnostic.get("ok") is not True
    ):
        raise AdapterError(
            "subject_input_packet_rejected: "
            + json.dumps(diagnostic, sort_keys=True, ensure_ascii=False)
        )
    return diagnostic


def require_observed_artifact_packet(packet: dict[str, Any]) -> None:
    require_equal(
        packet.get("schema_version"),
        "pulsemech_compute_subject_input_packet_v0",
        label="packet_schema_version",
    )
    require_equal(
        packet.get("packet_type"),
        "pulsemech_compute_subject_input_packet",
        label="packet_type",
    )
    require_equal(packet.get("record_status"), "observed", label="packet_record_status")
    require_equal(packet.get("ok"), True, label="packet_ok")
    require_equal(packet.get("errors"), [], label="packet_errors")

    boundary = packet.get("analysis_boundary")
    if not isinstance(boundary, dict):
        raise AdapterError("packet_analysis_boundary_not_object")
    require_equal(
        boundary.get("target_analysis_level"),
        "artifact_observed",
        label="packet_target_analysis_level",
    )
    require_equal(
        boundary.get("runtime_observation_included"),
        False,
        label="packet_runtime_observation_included",
    )
    require_equal(
        boundary.get("observer_in_subject_totals"),
        False,
        label="packet_observer_in_subject_totals",
    )

    content = packet.get("content_boundary")
    if not isinstance(content, dict):
        raise AdapterError("packet_content_boundary_not_object")
    require_equal(
        content.get("packet_payload_mode"),
        "metadata_only",
        label="packet_payload_mode",
    )
    require_equal(
        content.get("artifact_bytes_embedded"),
        False,
        label="packet_artifact_bytes_embedded",
    )
    require_equal(
        content.get("carrier_required_for_verification"),
        True,
        label="packet_carrier_required_for_verification",
    )

    authority = packet.get("authority_boundary")
    if not isinstance(authority, dict):
        raise AdapterError("packet_authority_boundary_not_object")
    for key in (
        "writes_subject_run",
        "writes_target_repository",
        "mutates_carrier",
        "changes_release_authority",
        "changes_gate_policy",
        "changes_gate_semantics",
        "creates_release_decision",
        "creates_gate_result",
        "activates_compute_gate",
        "creates_compute_budget",
        "packet_is_release_authority",
    ):
        require_equal(authority.get(key), False, label=f"packet_authority_{key}")

    producer = packet.get("producer")
    if not isinstance(producer, dict):
        raise AdapterError("packet_observed_producer_missing")
    if producer.get("production_mode") == "example":
        raise AdapterError("packet_observed_production_mode_example")


def artifact_index(packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = packet.get("artifacts")
    if not isinstance(records, list):
        raise AdapterError("packet_artifacts_not_array")

    indexed: dict[str, dict[str, Any]] = {}
    for raw in records:
        if not isinstance(raw, dict):
            raise AdapterError("packet_artifact_record_not_object")
        artifact_id = raw.get("artifact_id")
        if not isinstance(artifact_id, str) or not artifact_id:
            raise AdapterError("packet_artifact_id_missing")
        if artifact_id in indexed:
            raise AdapterError(f"packet_duplicate_artifact_id: {artifact_id}")
        indexed[artifact_id] = raw
    return indexed


def visible_artifact_records(
    packet: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    bindings = packet.get("role_bindings")
    if not isinstance(bindings, dict):
        raise AdapterError("packet_role_bindings_not_object")
    indexed = artifact_index(packet)

    result: dict[str, dict[str, Any]] = {}
    for role in VISIBLE_ROLE_FILENAMES:
        artifact_id = bindings.get(role)
        if not isinstance(artifact_id, str) or not artifact_id:
            raise AdapterError(f"packet_role_binding_missing: {role}")
        try:
            record = indexed[artifact_id]
        except KeyError as exc:
            raise AdapterError(
                f"packet_role_binding_unresolved: {role}: {artifact_id}"
            ) from exc
        require_equal(record.get("role"), role, label=f"packet_role:{role}")
        require_equal(
            record.get("container_artifact_id"),
            None,
            label=f"packet_outer_container:{role}",
        )
        result[role] = record
    return result


def read_visible_carriers(
    *,
    packet: dict[str, Any],
    carrier: Path,
) -> dict[str, bytes]:
    carrier_record = packet.get("carrier")
    if not isinstance(carrier_record, dict):
        raise AdapterError("packet_carrier_not_object")

    carrier_bytes = carrier.read_bytes()
    require_equal(
        len(carrier_bytes),
        carrier_record.get("size_bytes"),
        label="carrier_size",
    )
    require_equal(
        sha256_bytes(carrier_bytes),
        carrier_record.get("sha256"),
        label="carrier_sha256",
    )

    records = visible_artifact_records(packet)
    try:
        with zipfile.ZipFile(carrier, "r") as archive:
            members = safe_zip_members(archive, label="subject_carrier")
            result: dict[str, bytes] = {}
            for role, record in records.items():
                member_path = record.get("member_path")
                if not isinstance(member_path, str) or not member_path:
                    raise AdapterError(f"packet_member_path_missing: {role}")
                if member_path not in members:
                    raise AdapterError(
                        f"packet_member_missing_from_carrier: {role}: {member_path}"
                    )
                payload = archive.read(member_path)
                require_equal(
                    len(payload),
                    record.get("size_bytes"),
                    label=f"packet_member_size:{role}",
                )
                require_equal(
                    sha256_bytes(payload),
                    record.get("sha256"),
                    label=f"packet_member_sha256:{role}",
                )
                result[role] = payload
            return result
    except zipfile.BadZipFile as exc:
        raise AdapterError(f"subject_carrier_invalid_zip: {exc}") from exc


def write_atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


def build_from_subject_input(
    *,
    packet_path: Path,
    carrier_path: Path,
    repository_root: Path,
    analysis_run_key: str,
) -> str:
    require_regular_file(packet_path, label="subject_input_packet")
    require_regular_file(carrier_path, label="subject_carrier")
    for path, label in (
        (PACKET_SCHEMA, "packet_schema"),
        (PACKET_VALIDATOR, "packet_validator"),
        (REPORT_SCHEMA, "report_schema"),
        (REPORT_VALIDATOR, "report_validator"),
        (FIXED_SOURCE_BUILDER, "fixed_source_builder"),
    ):
        require_regular_file(path, label=label)

    packet = load_json_path(packet_path, label="subject_input_packet")
    require_observed_artifact_packet(packet)

    subject = packet.get("subject")
    if not isinstance(subject, dict):
        raise AdapterError("packet_subject_not_object")
    subject_run_key = subject.get("subject_run_key")
    if not isinstance(subject_run_key, str) or not subject_run_key:
        raise AdapterError("packet_subject_run_key_missing")
    if not analysis_run_key or analysis_run_key == subject_run_key:
        raise AdapterError("analysis_run_key_invalid_or_matches_subject")

    validate_subject_packet(
        packet=packet_path,
        carrier=carrier_path,
        repository_root=repository_root,
    )

    visible = read_visible_carriers(packet=packet, carrier=carrier_path)
    fixed_builder = load_module(
        FIXED_SOURCE_BUILDER,
        "pulsemech_fixed_source_compute_builder_v0_for_subject_input_adapter",
    )

    with tempfile.TemporaryDirectory(
        prefix="pulsemech-subject-input-analyzer-"
    ) as raw_temp:
        temp = Path(raw_temp)
        manifest_path = temp / VISIBLE_ROLE_FILENAMES["preservation_manifest"]
        readme_path = temp / VISIBLE_ROLE_FILENAMES["preservation_readme"]
        sums_path = temp / VISIBLE_ROLE_FILENAMES["preservation_checksums"]

        manifest_path.write_bytes(visible["preservation_manifest"])
        readme_path.write_bytes(visible["preservation_readme"])
        sums_path.write_bytes(visible["preservation_checksums"])

        carrier_record = packet["carrier"]
        bundle = fixed_builder.load_observed_bundle(
            archive_path=carrier_path,
            manifest_path=manifest_path,
            readme_path=readme_path,
            sha256sums_path=sums_path,
            expected_archive_sha256=str(carrier_record["sha256"]),
            expected_archive_size=int(carrier_record["size_bytes"]),
        )

        report = fixed_builder.build_report(
            bundle,
            analysis_run_key=analysis_run_key,
            builder_source_sha256=sha256_file(FIXED_SOURCE_BUILDER),
        )
        rendered = fixed_builder.render_json(report)
        fixed_builder.validate_generated_report(
            schema_path=REPORT_SCHEMA,
            validator_path=REPORT_VALIDATOR,
            rendered_report=rendered,
        )
        return rendered


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate one observed PULSEmech compute subject-input packet and "
            "use it to drive the existing single fixed-source compute analysis "
            "implementation without duplicating graph-construction logic."
        )
    )
    parser.add_argument("--packet", default=str(DEFAULT_PACKET))
    parser.add_argument("--carrier", default=str(DEFAULT_CARRIER))
    parser.add_argument("--repository-root", default=str(ROOT))
    parser.add_argument(
        "--analysis-run-key",
        default=DEFAULT_ANALYSIS_RUN_KEY,
        help="Explicit deterministic identity for the read-only analysis run.",
    )
    parser.add_argument(
        "--output",
        help="Optional output JSON path outside both tool and subject repositories.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    packet = Path(args.packet)
    carrier = Path(args.carrier)
    repository_root = Path(args.repository_root)
    output = Path(args.output) if args.output else None

    protected_inputs = (
        packet,
        carrier,
        PACKET_SCHEMA,
        PACKET_VALIDATOR,
        REPORT_SCHEMA,
        REPORT_VALIDATOR,
        FIXED_SOURCE_BUILDER,
        Path(__file__),
    )

    try:
        if not repository_root.is_dir():
            raise AdapterError(f"repository_root_not_directory: {repository_root}")
        reject_symlink_components(repository_root, label="repository_root")

        reject_unsafe_output(
            output,
            packet=packet,
            carrier=carrier,
            repository_root=repository_root,
        )

        before = snapshot(protected_inputs)
        rendered = build_from_subject_input(
            packet_path=packet,
            carrier_path=carrier,
            repository_root=repository_root,
            analysis_run_key=str(args.analysis_run_key),
        )

        if not inputs_unchanged(protected_inputs, before):
            raise AdapterError("protected_input_changed_during_analysis")

        if output is not None:
            write_atomic_text(output, rendered)

        sys.stdout.write(rendered)
        return 0
    except AdapterError as exc:
        sys.stderr.write(
            render_json(
                {
                    "tool": TOOL_ID,
                    "version": TOOL_VERSION,
                    "ok": False,
                    "errors": [str(exc)],
                }
            )
        )
        return 1
    except Exception as exc:
        sys.stderr.write(
            render_json(
                {
                    "tool": TOOL_ID,
                    "version": TOOL_VERSION,
                    "ok": False,
                    "errors": [f"unexpected_error: {exc}"],
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import stat
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TOOL_ID = "build_pulsemech_compute_binding_report_from_subject_input_v0"
TOOL_VERSION = "0.2.0"

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
ANALYZER_CORE = ROOT / "tools" / "pulsemech_compute_binding_analyzer_core_v0.py"
ANALYZER_CORE_MODULE = "pulsemech_compute_binding_analyzer_core_v0"

DEFAULT_ANALYSIS_RUN_KEY = (
    "OFFLINE_ANALYSIS=pulsemech-compute-binding-fixed-source-6066-v0"
)


class AdapterError(RuntimeError):
    pass


@dataclass(frozen=True)
class CapturedFile:
    path: Path
    data: bytes
    device: int
    inode: int
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class _StatView:
    st_size: int


class CapturedPathView(io.BytesIO):
    """Path-like read surface backed only by one captured byte revision.

    The class intentionally does not implement ``__fspath__``. Consumers such
    as ``zipfile.ZipFile`` therefore use its in-memory file interface instead of
    reopening the mutable pathname.
    """

    def __init__(self, capture: CapturedFile, *, display_path: Path | None = None):
        super().__init__(capture.data)
        self._capture = capture
        self._display_path = display_path or capture.path

    def read_bytes(self) -> bytes:
        return self._capture.data

    def read_text(
        self,
        encoding: str | None = None,
        errors: str | None = None,
    ) -> str:
        return self._capture.data.decode(
            encoding or "utf-8",
            errors or "strict",
        )

    def stat(self) -> _StatView:
        return _StatView(st_size=self._capture.size_bytes)

    def is_file(self) -> bool:
        return True

    def is_symlink(self) -> bool:
        return False

    def exists(self) -> bool:
        return True

    @property
    def parent(self) -> Path:
        return self._display_path.parent

    @property
    def name(self) -> str:
        return self._display_path.name

    def resolve(self, strict: bool = False) -> Path:
        del strict
        return Path(os.path.abspath(os.fspath(self._display_path)))

    def __str__(self) -> str:
        return str(self._display_path)

    def __repr__(self) -> str:
        return f"CapturedPathView({self._display_path!s})"


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


def resolve_cli_path(value: str) -> Path:
    return Path(os.path.abspath(os.fspath(Path(value))))


def _secure_open_constants() -> tuple[int, int]:
    required = ("O_DIRECTORY", "O_NOFOLLOW", "O_CLOEXEC")
    missing = [name for name in required if not hasattr(os, name)]
    if os.name != "posix" or missing or os.open not in os.supports_dir_fd:
        detail = ",".join(missing) if missing else "dir_fd_unavailable"
        raise AdapterError(f"secure_read_unavailable: {detail}")
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    file_flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
    return directory_flags, file_flags


def capture_regular_file(path: Path, *, label: str) -> CapturedFile:
    """Capture one exact regular-file revision through no-follow descriptors."""

    absolute = resolve_cli_path(str(path))
    directory_flags, file_flags = _secure_open_constants()
    parts = absolute.parts
    if not absolute.is_absolute() or len(parts) < 2:
        raise AdapterError(f"{label}_path_not_absolute: {absolute}")

    directory_fd = os.open(parts[0], directory_flags)
    file_fd: int | None = None
    try:
        for component in parts[1:-1]:
            if component in {"", ".", ".."}:
                raise AdapterError(f"{label}_unsafe_path_component: {component!r}")
            next_fd = os.open(component, directory_flags, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd

        basename = parts[-1]
        if basename in {"", ".", ".."}:
            raise AdapterError(f"{label}_unsafe_basename: {basename!r}")
        file_fd = os.open(basename, file_flags, dir_fd=directory_fd)
        before = os.fstat(file_fd)
        if not stat.S_ISREG(before.st_mode):
            raise AdapterError(f"{label}_not_regular_file: {absolute}")

        chunks: list[bytes] = []
        while True:
            chunk = os.read(file_fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        data = b"".join(chunks)
        after = os.fstat(file_fd)

        identity_before = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        identity_after = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        if identity_before != identity_after or len(data) != after.st_size:
            raise AdapterError(f"{label}_changed_during_capture: {absolute}")

        return CapturedFile(
            path=absolute,
            data=data,
            device=after.st_dev,
            inode=after.st_ino,
            size_bytes=len(data),
            sha256=sha256_bytes(data),
        )
    except OSError as exc:
        raise AdapterError(f"{label}_secure_open_failed: {absolute}: {exc}") from exc
    finally:
        if file_fd is not None:
            os.close(file_fd)
        os.close(directory_fd)


def load_module_from_capture(capture: CapturedFile, module_name: str) -> Any:
    """Execute exact source bytes without reading or writing bytecode."""

    try:
        code = compile(
            capture.data,
            str(capture.path),
            "exec",
            dont_inherit=True,
        )
    except Exception as exc:
        raise AdapterError(
            f"module_compile_failed: {capture.path}: {exc}"
        ) from exc

    previous = sys.modules.get(module_name)
    had_previous = module_name in sys.modules
    module = types.ModuleType(module_name)
    module.__file__ = str(capture.path)
    module.__cached__ = None
    module.__loader__ = None
    module.__package__ = module_name.rpartition(".")[0]
    module.__spec__ = None
    module.__pulsemech_source_sha256__ = capture.sha256
    sys.modules[module_name] = module

    try:
        exec(code, module.__dict__)
    except Exception as exc:
        if had_previous:
            sys.modules[module_name] = previous
        else:
            sys.modules.pop(module_name, None)
        raise AdapterError(
            f"module_execution_failed: {capture.path}: {exc}"
        ) from exc
    return module


def _capture_dependencies() -> dict[str, CapturedFile]:
    return {
        "packet_schema": capture_regular_file(PACKET_SCHEMA, label="packet_schema"),
        "packet_validator": capture_regular_file(
            PACKET_VALIDATOR,
            label="packet_validator",
        ),
        "report_schema": capture_regular_file(REPORT_SCHEMA, label="report_schema"),
        "report_validator": capture_regular_file(
            REPORT_VALIDATOR,
            label="report_validator",
        ),
        "fixed_builder": capture_regular_file(
            FIXED_SOURCE_BUILDER,
            label="fixed_source_builder",
        ),
        "analyzer_core": capture_regular_file(
            ANALYZER_CORE,
            label="analyzer_core",
        ),
    }


def _parse_observed_packet(packet_validator: Any, packet: CapturedFile) -> dict[str, Any]:
    try:
        value = packet_validator.load_json_bytes(
            packet.data,
            label=str(packet.path),
        )
    except Exception as exc:
        raise AdapterError(f"subject_input_packet_parse_failed: {exc}") from exc
    if not isinstance(value, dict):
        raise AdapterError("subject_input_packet_not_object")
    if value.get("record_status") != "observed":
        raise AdapterError("subject_input_packet_not_observed")
    if value.get("analysis_boundary", {}).get("target_analysis_level") != "artifact_observed":
        raise AdapterError("subject_input_packet_not_artifact_observed")
    return value


def _validate_packet_exact_bytes(
    *,
    packet: CapturedFile,
    carrier: CapturedFile,
    repository_root: Path,
    packet_schema: CapturedFile,
    packet_validator: Any,
) -> dict[str, Any]:
    packet_value = _parse_observed_packet(packet_validator, packet)
    diagnostic, exit_code, _carrier_view, _snapshots = packet_validator.build_diagnostic(
        schema_path=CapturedPathView(packet_schema),
        packet_path=CapturedPathView(packet),
        explicit_carrier=CapturedPathView(carrier),
        repository_root=repository_root,
    )
    if exit_code != 0 or diagnostic.get("ok") is not True:
        raise AdapterError(
            "subject_input_packet_rejected: "
            + json.dumps(diagnostic, sort_keys=True, ensure_ascii=False)
        )
    return packet_value


def _resolve_artifact_bytes(
    *,
    packet: dict[str, Any],
    carrier: CapturedFile,
    packet_validator: Any,
) -> dict[str, bytes]:
    ok, complete, artifact_bytes, errors = packet_validator._verify_artifact_graph(
        packet,
        carrier_bytes=carrier.data,
    )
    if not ok or not complete or errors:
        raise AdapterError(
            "subject_input_artifact_reconstruction_rejected: "
            + json.dumps(sorted(set(errors)), ensure_ascii=False)
        )
    return artifact_bytes


def _bound_artifact_bytes(
    *,
    packet: dict[str, Any],
    artifact_bytes: dict[str, bytes],
    binding_name: str,
) -> bytes:
    bindings = packet.get("role_bindings")
    if not isinstance(bindings, dict):
        raise AdapterError("packet_role_bindings_not_object")
    artifact_id = bindings.get(binding_name)
    if not isinstance(artifact_id, str) or not artifact_id:
        raise AdapterError(f"packet_role_binding_missing: {binding_name}")
    try:
        return artifact_bytes[artifact_id]
    except KeyError as exc:
        raise AdapterError(
            f"packet_role_binding_unresolved: {binding_name}: {artifact_id}"
        ) from exc


def _build_bundle_from_exact_bytes(
    *,
    packet: dict[str, Any],
    carrier: CapturedFile,
    artifact_bytes: dict[str, bytes],
    analyzer_core: Any,
) -> Any:
    manifest_bytes = _bound_artifact_bytes(
        packet=packet,
        artifact_bytes=artifact_bytes,
        binding_name="preservation_manifest",
    )
    readme_bytes = _bound_artifact_bytes(
        packet=packet,
        artifact_bytes=artifact_bytes,
        binding_name="preservation_readme",
    )
    sums_bytes = _bound_artifact_bytes(
        packet=packet,
        artifact_bytes=artifact_bytes,
        binding_name="preservation_checksums",
    )

    return analyzer_core.load_observed_bundle(
        archive_path=CapturedPathView(
            carrier,
            display_path=analyzer_core.DEFAULT_ARCHIVE,
        ),
        manifest_path=CapturedPathView(
            CapturedFile(
                path=analyzer_core.DEFAULT_MANIFEST,
                data=manifest_bytes,
                device=carrier.device,
                inode=carrier.inode,
                size_bytes=len(manifest_bytes),
                sha256=sha256_bytes(manifest_bytes),
            ),
            display_path=analyzer_core.DEFAULT_MANIFEST,
        ),
        readme_path=CapturedPathView(
            CapturedFile(
                path=analyzer_core.DEFAULT_README,
                data=readme_bytes,
                device=carrier.device,
                inode=carrier.inode,
                size_bytes=len(readme_bytes),
                sha256=sha256_bytes(readme_bytes),
            ),
            display_path=analyzer_core.DEFAULT_README,
        ),
        sha256sums_path=CapturedPathView(
            CapturedFile(
                path=analyzer_core.DEFAULT_SHA256SUMS,
                data=sums_bytes,
                device=carrier.device,
                inode=carrier.inode,
                size_bytes=len(sums_bytes),
                sha256=sha256_bytes(sums_bytes),
            ),
            display_path=analyzer_core.DEFAULT_SHA256SUMS,
        ),
        expected_archive_sha256=carrier.sha256,
        expected_archive_size=carrier.size_bytes,
    )


def _validate_report_exact_bytes(
    *,
    rendered_report: str,
    report_schema: CapturedFile,
    report_validator: Any,
) -> None:
    report_capture = CapturedFile(
        path=Path("in-memory/pulsemech_compute_binding_report_v0.json"),
        data=rendered_report.encode("utf-8"),
        device=0,
        inode=0,
        size_bytes=len(rendered_report.encode("utf-8")),
        sha256=sha256_bytes(rendered_report.encode("utf-8")),
    )
    diagnostic, exit_code = report_validator.build_diagnostic(
        CapturedPathView(report_schema),
        CapturedPathView(report_capture),
    )
    if exit_code != 0 or diagnostic.get("ok") is not True:
        raise AdapterError(
            "generated_report_rejected: "
            + json.dumps(diagnostic, sort_keys=True, ensure_ascii=False)
        )


def build_from_captured_inputs(
    *,
    packet_capture: CapturedFile,
    carrier_capture: CapturedFile,
    repository_root: Path,
    analysis_run_key: str,
    dependency_captures: dict[str, CapturedFile] | None = None,
) -> str:
    if not analysis_run_key:
        raise AdapterError("analysis_run_key_missing")

    captures = dependency_captures or _capture_dependencies()
    packet_validator = load_module_from_capture(
        captures["packet_validator"],
        "pulsemech_subject_input_packet_validator_v0_for_bridge",
    )
    analyzer_core = load_module_from_capture(
        captures["analyzer_core"],
        ANALYZER_CORE_MODULE,
    )
    report_validator = load_module_from_capture(
        captures["report_validator"],
        "pulsemech_compute_binding_report_validator_v0_for_bridge",
    )

    packet = _validate_packet_exact_bytes(
        packet=packet_capture,
        carrier=carrier_capture,
        repository_root=repository_root,
        packet_schema=captures["packet_schema"],
        packet_validator=packet_validator,
    )
    subject = packet.get("subject")
    if not isinstance(subject, dict):
        raise AdapterError("packet_subject_not_object")
    subject_run_key = subject.get("subject_run_key")
    if not isinstance(subject_run_key, str) or not subject_run_key:
        raise AdapterError("packet_subject_run_key_missing")
    if analysis_run_key == subject_run_key:
        raise AdapterError("analysis_run_key_invalid_or_matches_subject")

    artifact_bytes = _resolve_artifact_bytes(
        packet=packet,
        carrier=carrier_capture,
        packet_validator=packet_validator,
    )
    bundle = _build_bundle_from_exact_bytes(
        packet=packet,
        carrier=carrier_capture,
        artifact_bytes=artifact_bytes,
        analyzer_core=analyzer_core,
    )
    report = analyzer_core.build_report(
        bundle,
        analysis_run_key=analysis_run_key,
        builder_source_sha256=captures["fixed_builder"].sha256,
        analyzer_core_source_sha256=captures["analyzer_core"].sha256,
    )
    rendered = analyzer_core.render_json(report)
    _validate_report_exact_bytes(
        rendered_report=rendered,
        report_schema=captures["report_schema"],
        report_validator=report_validator,
    )
    return rendered


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate one observed PULSEmech compute subject-input packet and "
            "drive the reusable compute analyzer core from one captured "
            "packet/carrier revision. The bridge writes stdout only."
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    packet_path = resolve_cli_path(args.packet)
    carrier_path = resolve_cli_path(args.carrier)
    repository_root = resolve_cli_path(args.repository_root)

    try:
        if not repository_root.is_dir():
            raise AdapterError(
                f"repository_root_not_directory: {repository_root}"
            )
        packet_capture = capture_regular_file(
            packet_path,
            label="subject_input_packet",
        )
        carrier_capture = capture_regular_file(
            carrier_path,
            label="subject_carrier",
        )
        rendered = build_from_captured_inputs(
            packet_capture=packet_capture,
            carrier_capture=carrier_capture,
            repository_root=repository_root,
            analysis_run_key=str(args.analysis_run_key),
        )
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

#!/usr/bin/env python3
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
import secrets
import stat
import subprocess
import sys
import tempfile
import types
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

PROTECTED_OUTPUT_NAMES = frozenset(
    {
        "status.json",
        "release_decision_v0.json",
        "release_authority_v0.json",
        "pulsemech_compute_subject_input_packet_v0.json",
    }
)

TEMP_ENV_KEYS = ("TMPDIR", "TEMP", "TMP")


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


def resolve_cli_path(value: str) -> Path:
    """Resolve a CLI path against the caller's current directory.

    os.path.abspath performs lexical normalization without following symlinks,
    so later explicit symlink checks remain effective.
    """

    return Path(os.path.abspath(os.fspath(Path(value))))


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


def validate_external_temp_root(
    path: Path,
    *,
    repository_root: Path,
    label: str = "temp_root",
) -> Path:
    absolute = resolve_cli_path(str(path))
    if not absolute.is_dir():
        raise AdapterError(f"{label}_not_directory: {absolute}")
    if absolute.is_symlink():
        raise AdapterError(f"{label}_symlink_rejected: {absolute}")
    reject_symlink_components(absolute, label=label)
    try:
        resolved = absolute.resolve(strict=True)
    except OSError as exc:
        raise AdapterError(f"{label}_unresolvable: {absolute}: {exc}") from exc

    if is_within(resolved, ROOT):
        raise AdapterError(f"{label}_inside_tool_repository: {resolved}")
    if is_within(resolved, repository_root):
        raise AdapterError(f"{label}_inside_subject_repository: {resolved}")
    if not os.access(resolved, os.W_OK | os.X_OK):
        raise AdapterError(f"{label}_not_writable_and_searchable: {resolved}")
    return resolved


def select_external_temp_root(
    *,
    repository_root: Path,
    explicit: Path | None,
) -> Path:
    if explicit is not None:
        return validate_external_temp_root(
            explicit,
            repository_root=repository_root,
            label="temp_root",
        )

    raw_candidates: list[str] = []
    for key in TEMP_ENV_KEYS:
        value = os.environ.get(key)
        if value:
            raw_candidates.append(value)
    try:
        raw_candidates.append(tempfile.gettempdir())
    except Exception:
        pass
    if os.name == "posix":
        raw_candidates.extend(("/tmp", "/var/tmp"))

    seen: set[str] = set()
    failures: list[str] = []
    for raw in raw_candidates:
        candidate = resolve_cli_path(raw)
        key = os.path.normcase(str(candidate))
        if key in seen:
            continue
        seen.add(key)
        try:
            return validate_external_temp_root(
                candidate,
                repository_root=repository_root,
                label="temp_root_candidate",
            )
        except AdapterError as exc:
            failures.append(str(exc))

    raise AdapterError(
        "external_temp_root_unavailable: "
        + (" | ".join(failures) if failures else "no candidate directories")
    )


@contextmanager
def bound_temp_environment(temp_root: Path):
    previous_tempdir = tempfile.tempdir
    previous_environment = {
        key: os.environ.get(key)
        for key in (*TEMP_ENV_KEYS, "PYTHONDONTWRITEBYTECODE")
    }
    tempfile.tempdir = str(temp_root)
    for key in TEMP_ENV_KEYS:
        os.environ[key] = str(temp_root)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        yield
    finally:
        tempfile.tempdir = previous_tempdir
        for key, value in previous_environment.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def subprocess_environment(temp_root: Path) -> dict[str, str]:
    environment = dict(os.environ)
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "TMPDIR": str(temp_root),
            "TEMP": str(temp_root),
            "TMP": str(temp_root),
        }
    )
    return environment


def secure_output_supported() -> bool:
    return (
        os.name == "posix"
        and hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
        and hasattr(os, "O_CLOEXEC")
        and os.open in os.supports_dir_fd
        and os.rename in os.supports_dir_fd
        and os.stat in os.supports_dir_fd
        and os.unlink in os.supports_dir_fd
    )


def directory_open_flags() -> int:
    if not secure_output_supported():
        raise AdapterError("secure_output_directory_handles_unsupported")
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


def open_directory_chain_no_follow(path: Path, *, label: str) -> int:
    if not path.is_absolute():
        raise AdapterError(f"{label}_not_absolute: {path}")
    flags = directory_open_flags()
    parts = path.parts
    if not parts or not path.anchor:
        raise AdapterError(f"{label}_anchor_missing: {path}")
    try:
        current_fd = os.open(path.anchor, flags)
    except OSError as exc:
        raise AdapterError(f"{label}_root_open_failed: {path.anchor}: {exc}") from exc
    try:
        for part in parts[1:]:
            if part in {"", ".", ".."}:
                raise AdapterError(f"{label}_unsafe_component: {part!r}")
            try:
                next_fd = os.open(part, flags, dir_fd=current_fd)
            except OSError as exc:
                raise AdapterError(
                    f"{label}_component_open_failed: {part}: {exc}"
                ) from exc
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except Exception:
        os.close(current_fd)
        raise


def same_stat_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return left.st_dev == right.st_dev and left.st_ino == right.st_ino


def directory_fd_is_within(directory_fd: int, root: Path) -> bool:
    root_fd = open_directory_chain_no_follow(root, label="protected_root")
    current_fd = os.dup(directory_fd)
    try:
        root_stat = os.fstat(root_fd)
        while True:
            current_stat = os.fstat(current_fd)
            if same_stat_identity(current_stat, root_stat):
                return True
            parent_fd = os.open("..", directory_open_flags(), dir_fd=current_fd)
            parent_stat = os.fstat(parent_fd)
            if same_stat_identity(parent_stat, current_stat):
                os.close(parent_fd)
                return False
            os.close(current_fd)
            current_fd = parent_fd
    finally:
        os.close(current_fd)
        os.close(root_fd)


def current_target_stat(parent_fd: int, basename: str) -> os.stat_result | None:
    try:
        return os.stat(basename, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise AdapterError(f"output_target_stat_failed: {basename}: {exc}") from exc


def reject_bound_output_target(
    *,
    parent_fd: int,
    basename: str,
    protected: tuple[Path, ...],
) -> None:
    target_stat = current_target_stat(parent_fd, basename)
    if target_stat is None:
        return
    if stat.S_ISLNK(target_stat.st_mode):
        raise AdapterError(f"refusing_symlink_output_path: {basename}")
    if not stat.S_ISREG(target_stat.st_mode):
        raise AdapterError(f"refusing_non_regular_output_target: {basename}")
    for path in protected:
        try:
            protected_stat = path.stat()
        except OSError:
            continue
        if same_stat_identity(target_stat, protected_stat):
            raise AdapterError(f"refusing_to_overwrite_input: {path}")


def write_all(file_descriptor: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = os.write(file_descriptor, view)
        if written <= 0:
            raise AdapterError("output_write_returned_no_progress")
        view = view[written:]


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

    if output.name.casefold() in PROTECTED_OUTPUT_NAMES:
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
    """Load exact source bytes without creating or consuming repository bytecode."""

    require_regular_file(path, label=module_name)
    source = path.read_bytes()
    try:
        code = compile(
            source,
            str(path),
            "exec",
            dont_inherit=True,
        )
    except Exception as exc:
        raise AdapterError(f"module_compile_failed: {path}: {exc}") from exc

    previous = sys.modules.get(module_name)
    had_previous = module_name in sys.modules
    module = types.ModuleType(module_name)
    module.__file__ = str(path)
    module.__cached__ = None
    module.__loader__ = None
    module.__package__ = module_name.rpartition(".")[0]
    module.__spec__ = None
    sys.modules[module_name] = module

    try:
        exec(code, module.__dict__)
    except Exception as exc:
        if had_previous:
            sys.modules[module_name] = previous
        else:
            sys.modules.pop(module_name, None)
        raise AdapterError(f"module_import_failed: {path}: {exc}") from exc
    return module


def validate_subject_packet(
    *,
    packet: Path,
    carrier: Path,
    repository_root: Path,
    temp_root: Path,
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
        env=subprocess_environment(temp_root),
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


def write_atomic_text(
    path: Path,
    text: str,
    *,
    packet: Path,
    carrier: Path,
    repository_root: Path,
) -> None:
    # Revalidate immediately before binding the output directory. All creation
    # and replacement operations after this point are relative to one no-follow
    # directory handle, not to a path that can be redirected during analysis.
    reject_unsafe_output(
        path,
        packet=packet,
        carrier=carrier,
        repository_root=repository_root,
    )
    if not path.name or path.name in {".", ".."}:
        raise AdapterError(f"output_basename_invalid: {path}")
    if not path.parent.is_dir():
        raise AdapterError(f"output_parent_not_directory: {path.parent}")

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
    parent_fd = open_directory_chain_no_follow(path.parent, label="output_parent")
    temp_name: str | None = None
    temp_fd: int | None = None
    try:
        if directory_fd_is_within(parent_fd, ROOT):
            raise AdapterError(f"refusing_output_inside_tool_repository: {path}")
        if directory_fd_is_within(parent_fd, repository_root):
            raise AdapterError(f"refusing_output_inside_subject_repository: {path}")
        reject_bound_output_target(
            parent_fd=parent_fd,
            basename=path.name,
            protected=protected,
        )

        create_flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | os.O_NOFOLLOW
            | os.O_CLOEXEC
        )
        for _attempt in range(128):
            candidate = f".pulsemech-output-{secrets.token_hex(16)}.tmp"
            try:
                temp_fd = os.open(
                    candidate,
                    create_flags,
                    0o600,
                    dir_fd=parent_fd,
                )
                temp_name = candidate
                break
            except FileExistsError:
                continue
            except OSError as exc:
                raise AdapterError(
                    f"output_temp_create_failed: {path.parent}: {exc}"
                ) from exc
        if temp_fd is None or temp_name is None:
            raise AdapterError("output_temp_name_exhausted")

        write_all(temp_fd, text.encode("utf-8"))
        os.fsync(temp_fd)
        os.close(temp_fd)
        temp_fd = None

        try:
            named_parent_stat = os.stat(path.parent, follow_symlinks=False)
        except OSError as exc:
            raise AdapterError(
                f"output_parent_revalidation_failed: {path.parent}: {exc}"
            ) from exc
        if not same_stat_identity(named_parent_stat, os.fstat(parent_fd)):
            raise AdapterError(f"output_parent_changed_before_commit: {path.parent}")

        reject_bound_output_target(
            parent_fd=parent_fd,
            basename=path.name,
            protected=protected,
        )
        try:
            os.rename(
                temp_name,
                path.name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
            )
        except (OSError, TypeError, NotImplementedError) as exc:
            raise AdapterError(f"output_atomic_replace_failed: {path}: {exc}") from exc
        temp_name = None
    finally:
        if temp_fd is not None:
            os.close(temp_fd)
        if temp_name is not None:
            try:
                os.unlink(temp_name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
        os.close(parent_fd)


def build_from_subject_input(
    *,
    packet_path: Path,
    carrier_path: Path,
    repository_root: Path,
    analysis_run_key: str,
    temp_root: Path,
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

    temp_root = validate_external_temp_root(
        temp_root,
        repository_root=repository_root,
        label="analysis_temp_root",
    )
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

    with bound_temp_environment(temp_root):
        validate_subject_packet(
            packet=packet_path,
            carrier=carrier_path,
            repository_root=repository_root,
            temp_root=temp_root,
        )
        visible = read_visible_carriers(packet=packet, carrier=carrier_path)
        fixed_builder = load_module(
            FIXED_SOURCE_BUILDER,
            "pulsemech_fixed_source_compute_builder_v0_for_subject_input_adapter",
        )

        # Revalidate immediately before creating the private working directory.
        temp_root = validate_external_temp_root(
            temp_root,
            repository_root=repository_root,
            label="analysis_temp_root_before_create",
        )
        with tempfile.TemporaryDirectory(
            prefix="pulsemech-subject-input-analyzer-",
            dir=str(temp_root),
        ) as raw_temp:
            private_temp = Path(raw_temp)
            manifest_path = private_temp / VISIBLE_ROLE_FILENAMES["preservation_manifest"]
            readme_path = private_temp / VISIBLE_ROLE_FILENAMES["preservation_readme"]
            sums_path = private_temp / VISIBLE_ROLE_FILENAMES["preservation_checksums"]

            # Delegated tempfile users, including validate_generated_report,
            # are bound to this already-created external private directory.
            with bound_temp_environment(private_temp):
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
        "--temp-root",
        help=(
            "Optional existing temporary-directory root outside both the tool "
            "and subject repositories. If omitted, unsafe environment-selected "
            "roots are skipped and an external system temp root is selected."
        ),
    )
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
    packet = resolve_cli_path(args.packet)
    carrier = resolve_cli_path(args.carrier)
    repository_root = resolve_cli_path(args.repository_root)
    explicit_temp_root = resolve_cli_path(args.temp_root) if args.temp_root else None
    output = resolve_cli_path(args.output) if args.output else None

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
        repository_root = repository_root.resolve(strict=True)

        temp_root = select_external_temp_root(
            repository_root=repository_root,
            explicit=explicit_temp_root,
        )
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
            temp_root=temp_root,
        )
        if not inputs_unchanged(protected_inputs, before):
            raise AdapterError("protected_input_changed_during_analysis")

        if output is not None:
            write_atomic_text(
                output,
                rendered,
                packet=packet,
                carrier=carrier,
                repository_root=repository_root,
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

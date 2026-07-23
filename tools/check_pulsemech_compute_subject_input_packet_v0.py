#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
from functools import lru_cache
import io
import json
import math
import os
import stat
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from urllib.parse import unquote, urlparse

import jsonschema
import yaml


TOOL_NAME = "check_pulsemech_compute_subject_input_packet_v0"
SCHEMA_VERSION = "pulsemech_compute_subject_input_packet_v0"
PACKET_TYPE = "pulsemech_compute_subject_input_packet"

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = (
    ROOT / "schemas" / "pulsemech_compute_subject_input_packet_v0.schema.json"
)
DEFAULT_PACKET = (
    ROOT
    / "examples"
    / "compute"
    / "pulsemech_compute_subject_input_packet_6066_example_v0.json"
)
DEFAULT_REPOSITORY_ROOT = ROOT
DEFAULT_GATE_POLICY = ROOT / "pulse_gate_policy_v0.yml"
DEFAULT_GATE_REGISTRY = ROOT / "pulse_gate_registry_v0.yml"
DEFAULT_PULSE_WORKFLOW = ROOT / ".github" / "workflows" / "pulse_ci.yml"

CORE_SINGLETON_ROLE_BINDINGS: dict[str, str] = {
    "preservation_manifest": "preservation_manifest",
    "preservation_readme": "preservation_readme",
    "preservation_checksums": "preservation_checksums",
    "complete_package": "complete_package",
    "package_inventory": "package_inventory",
    "package_completeness_report": "package_completeness_report",
    "independent_verification_report": "independent_verification_report",
    "run_metadata": "run_metadata",
    "final_status": "final_status",
    "status_baseline": "status_baseline",
    "release_decision": "release_decision",
    "release_authority": "release_authority",
    "artifact_binding": "artifact_binding",
    "evidence_manifest": "evidence_manifest",
    "recorded_verifier_report": "recorded_verifier_report",
    "required_gate_evidence": "required_gate_evidence",
    "candidate_index": "candidate_index",
}

LIST_ROLE_BINDINGS: dict[str, set[str]] = {
    "candidate_records": {"candidate_record"},
    "external_evidence_records": {
        "external_evidence",
        "external_evaluator_manifest",
        "external_raw_evidence",
        "external_summary",
    },
    "attestation_records": {
        "attestation_bundle",
        "attestation_envelope",
        "attestation_verifier_report",
    },
    "reader_surfaces": {
        "quality_ledger",
        "report_card",
        "reader_surface",
    },
}

AUTHORITY_SURFACE_OUTPUT_NAMES = {
    "status.json",
    "release_decision_v0.json",
    "release_authority_v0.json",
    "pulsemech_compute_subject_input_packet_v0.json",
}

GIT_PROCESS_ENV_ALLOWLIST = (
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "TEMP",
    "TMP",
    "TMPDIR",
)

POSIX_TRUSTED_GIT_EXECUTABLE_CANDIDATES = (
    Path("/usr/bin/git"),
    Path("/usr/local/bin/git"),
    Path("/opt/local/bin/git"),
)


class StrictJsonError(ValueError):
    pass


class StrictYamlError(ValueError):
    pass


class SemanticError(RuntimeError):
    pass


class UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: UniqueKeyLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise StrictYamlError(f"duplicate YAML key: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJsonError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_non_finite(value: str) -> None:
    raise StrictJsonError(f"non-finite JSON value: {value}")


def _require_finite_tree(value: Any, *, label: str) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise StrictJsonError(f"{label}: non-finite JSON number")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _require_finite_tree(item, label=f"{label}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _require_finite_tree(item, label=f"{label}.{key}")
        return
    raise StrictJsonError(f"{label}: unsupported JSON value {type(value).__name__}")


def load_json_bytes(data: bytes, *, label: str) -> Any:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StrictJsonError(f"{label}: invalid UTF-8: {exc}") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_non_finite,
        )
        _require_finite_tree(value, label=label)
        return value
    except Exception as exc:
        if isinstance(exc, StrictJsonError):
            raise
        raise StrictJsonError(f"{label}: invalid JSON: {exc}") from exc


def load_json_path(path: Path) -> tuple[Any, str, bytes]:
    data = path.read_bytes()
    value = load_json_bytes(data, label=str(path))
    return value, data.decode("utf-8"), data


def load_yaml_bytes(data: bytes, *, label: str) -> Any:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StrictYamlError(f"{label}: invalid UTF-8: {exc}") from exc
    try:
        return yaml.load(text, Loader=UniqueKeyLoader)
    except Exception as exc:
        if isinstance(exc, StrictYamlError):
            raise
        raise StrictYamlError(f"{label}: invalid YAML: {exc}") from exc


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


def schema_errors(schema: dict[str, Any], value: Any) -> list[str]:
    validator = jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )
    return [
        f"schema_error[{list(error.path)}]: {error.message}"
        for error in sorted(
            validator.iter_errors(value),
            key=lambda item: (
                tuple(str(part) for part in item.path),
                item.message,
            ),
        )
    ]


def parse_utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"not canonical UTC: {value!r}")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.tzinfo is None:
        raise ValueError(f"timezone missing: {value!r}")
    return parsed.astimezone(timezone.utc)


def same_target(left: Path, right: Path) -> bool:
    try:
        if left.resolve(strict=False) == right.resolve(strict=False):
            return True
    except OSError:
        pass

    try:
        if left.exists() and right.exists() and left.samefile(right):
            return True
    except OSError:
        pass

    return False


def _safe_relative_path(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        return False
    if value.startswith("/") or value.endswith("/") or "//" in value:
        return False
    parsed = PurePosixPath(value)
    if parsed.is_absolute():
        return False
    return all(part not in {"", ".", ".."} for part in parsed.parts)


def _safe_zip_name(value: str, *, is_directory: bool) -> bool:
    candidate = value[:-1] if is_directory and value.endswith("/") else value
    if not candidate:
        return False
    return _safe_relative_path(candidate)


def _zip_entry_is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)


def _sorted_unique_strings(values: Any) -> bool:
    return (
        isinstance(values, list)
        and all(isinstance(item, str) for item in values)
        and values == sorted(values)
        and len(values) == len(set(values))
    )


def _ordered_unique_non_empty_strings(values: Any) -> bool:
    return (
        isinstance(values, list)
        and bool(values)
        and all(isinstance(item, str) and bool(item) for item in values)
        and len(values) == len(set(values))
    )


def _all_object_keys_sorted(value: Any) -> bool:
    if isinstance(value, dict):
        return (
            list(value) == sorted(value)
            and all(_all_object_keys_sorted(item) for item in value.values())
        )
    if isinstance(value, list):
        return all(_all_object_keys_sorted(item) for item in value)
    return True


def _index_rows(
    rows: list[dict[str, Any]],
    key: str,
    *,
    label: str,
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        identifier = row.get(key)
        if not isinstance(identifier, str):
            errors.append(f"{label}_identifier_invalid: {identifier!r}")
            continue
        if identifier in result:
            errors.append(f"{label}_identifier_duplicate: {identifier}")
            continue
        result[identifier] = row
    return result


def _resolve_local_carrier_path(
    carrier_location: str,
    *,
    explicit_carrier: Path | None,
    repository_root: Path,
) -> Path:
    if explicit_carrier is not None:
        return explicit_carrier

    parsed = urlparse(carrier_location)
    if parsed.scheme == "file":
        if parsed.netloc not in {"", "localhost"}:
            raise SemanticError(
                f"unsupported_file_uri_authority: {parsed.netloc}"
            )
        return Path(unquote(parsed.path))
    if parsed.scheme:
        raise SemanticError(
            "carrier_requires_local_override: "
            f"unsupported URI scheme {parsed.scheme!r}; pass --carrier"
        )
    if not _safe_relative_path(carrier_location):
        raise SemanticError(f"unsafe_carrier_path: {carrier_location!r}")
    return repository_root / PurePosixPath(carrier_location)


def _relative_packet_path(packet_path: Path, repository_root: Path) -> str | None:
    try:
        return packet_path.resolve(strict=True).relative_to(
            repository_root.resolve(strict=True)
        ).as_posix()
    except (OSError, ValueError):
        return None


def _trusted_git_executable_candidates() -> tuple[Path, ...]:
    if os.name != "nt":
        return POSIX_TRUSTED_GIT_EXECUTABLE_CANDIDATES

    system_anchor = Path(sys.executable).anchor
    if not system_anchor:
        return ()

    system_drive = Path(system_anchor)
    return (
        system_drive / "Program Files" / "Git" / "cmd" / "git.exe",
        system_drive / "Program Files" / "Git" / "bin" / "git.exe",
        system_drive / "Program Files (x86)" / "Git" / "cmd" / "git.exe",
        system_drive / "Program Files (x86)" / "Git" / "bin" / "git.exe",
    )


def _normalized_absolute_path(path: Path) -> Path:
    return Path(os.path.abspath(os.path.normpath(str(path))))


def _validate_trusted_git_executable(candidate: Path) -> Path:
    if not candidate.is_absolute():
        raise SemanticError(
            f"git_executable_untrusted: path_not_absolute: {candidate}"
        )

    normalized = _normalized_absolute_path(candidate)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise SemanticError(
            f"git_executable_untrusted: path_unresolvable: {candidate}: {exc}"
        ) from exc

    if os.path.normcase(str(normalized)) != os.path.normcase(str(resolved)):
        raise SemanticError(
            "git_executable_untrusted: symlink_or_alias_path: "
            f"declared={normalized} resolved={resolved}"
        )
    if candidate.is_symlink() or not resolved.is_file():
        raise SemanticError(
            f"git_executable_untrusted: not_regular_non_symlink_file: {resolved}"
        )
    if not os.access(resolved, os.X_OK):
        raise SemanticError(
            f"git_executable_untrusted: not_executable: {resolved}"
        )

    components: list[Path] = [resolved]
    cursor = resolved.parent
    while True:
        components.append(cursor)
        if cursor == cursor.parent:
            break
        cursor = cursor.parent

    for component in components:
        try:
            metadata = component.lstat()
        except OSError as exc:
            raise SemanticError(
                f"git_executable_untrusted: component_unavailable: {component}: {exc}"
            ) from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise SemanticError(
                f"git_executable_untrusted: symlink_component: {component}"
            )
        if component == resolved:
            if not stat.S_ISREG(metadata.st_mode):
                raise SemanticError(
                    f"git_executable_untrusted: executable_not_regular: {component}"
                )
        elif not stat.S_ISDIR(metadata.st_mode):
            raise SemanticError(
                f"git_executable_untrusted: parent_not_directory: {component}"
            )

        if os.name != "nt":
            if metadata.st_uid != 0:
                raise SemanticError(
                    "git_executable_untrusted: non_root_owned_component: "
                    f"{component}"
                )
            if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                raise SemanticError(
                    "git_executable_untrusted: writable_component: "
                    f"{component}"
                )

    return resolved


@lru_cache(maxsize=1)
def _trusted_git_executable() -> Path:
    unavailable: list[str] = []
    untrusted: list[str] = []

    for candidate in _trusted_git_executable_candidates():
        if not candidate.exists():
            unavailable.append(str(candidate))
            continue
        try:
            return _validate_trusted_git_executable(candidate)
        except SemanticError as exc:
            untrusted.append(str(exc))

    if untrusted:
        raise SemanticError(
            "git_process_executable_untrusted: " + " | ".join(untrusted)
        )
    raise SemanticError(
        "git_process_executable_unavailable: "
        + (", ".join(unavailable) if unavailable else "no trusted candidates")
    )


def _sanitized_git_environment(
    git_executable: Path | None = None,
) -> dict[str, str]:
    trusted_git = (
        _trusted_git_executable()
        if git_executable is None
        else _validate_trusted_git_executable(git_executable)
    )

    env: dict[str, str] = {}
    for key in GIT_PROCESS_ENV_ALLOWLIST:
        value = os.environ.get(key)
        if value is not None:
            env[key] = value

    env.update(
        {
            "PATH": str(trusted_git.parent),
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_COUNT": "0",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "LC_ALL": "C",
            "LANG": "C",
        }
    )
    return env


def _run_isolated_git(
    repository_root: Path,
    *,
    arguments: list[str],
    failure_prefix: str,
) -> bytes:
    resolved_root = repository_root.resolve(strict=True)
    if not resolved_root.is_dir():
        raise SemanticError(
            f"git_repository_root_not_directory: {resolved_root}"
        )

    git_executable = _trusted_git_executable()
    command = [
        str(git_executable),
        "--no-pager",
        "--no-replace-objects",
        "-c",
        f"safe.directory={resolved_root}",
        "-C",
        str(resolved_root),
        *arguments,
    ]
    completed = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_sanitized_git_environment(git_executable),
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise SemanticError(f"{failure_prefix}: {detail or 'unknown error'}")
    return completed.stdout


def _verified_git_repository_root(repository_root: Path) -> Path:
    resolved_root = repository_root.resolve(strict=True)
    top_level_bytes = _run_isolated_git(
        resolved_root,
        arguments=["rev-parse", "--show-toplevel"],
        failure_prefix="git_repository_root_unavailable",
    )
    try:
        top_level_text = top_level_bytes.decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError as exc:
        raise SemanticError(
            f"git_repository_root_invalid_utf8: {exc}"
        ) from exc

    if (
        not top_level_text
        or "\x00" in top_level_text
        or "\n" in top_level_text
        or "\r" in top_level_text
    ):
        raise SemanticError(
            f"git_repository_root_output_invalid: {top_level_text!r}"
        )

    try:
        discovered_root = Path(top_level_text).resolve(strict=True)
    except OSError as exc:
        raise SemanticError(
            f"git_repository_root_unresolvable: {top_level_text!r}: {exc}"
        ) from exc

    if not discovered_root.is_dir() or not same_target(
        discovered_root,
        resolved_root,
    ):
        raise SemanticError(
            "git_repository_root_mismatch: "
            f"requested={resolved_root} discovered={discovered_root}"
        )
    return resolved_root


def _git_blob_bytes(
    repository_root: Path,
    *,
    revision: str,
    path: str,
) -> bytes:
    if not _safe_relative_path(path):
        raise SemanticError(f"unsafe_source_path: {path!r}")

    resolved_root = _verified_git_repository_root(repository_root)
    return _run_isolated_git(
        resolved_root,
        arguments=["cat-file", "blob", f"{revision}:{path}"],
        failure_prefix=f"git_blob_unavailable: {revision}:{path}",
    )


def _reject_symlink_path(path: Path, *, label: str) -> None:
    cursor = path
    while True:
        if cursor.is_symlink():
            raise SemanticError(f"{label}_symlink_rejected: {cursor}")
        if cursor == cursor.parent:
            break
        cursor = cursor.parent


def reject_unsafe_output(
    output: Path | None,
    *,
    schema_path: Path,
    packet_path: Path,
    carrier_path: Path,
    repository_root: Path,
    packet: dict[str, Any],
) -> None:
    if output is None:
        return

    protected: list[Path] = [
        schema_path,
        packet_path,
        carrier_path,
        _trusted_git_executable(),
        Path(__file__),
        DEFAULT_GATE_POLICY,
        DEFAULT_GATE_REGISTRY,
        DEFAULT_PULSE_WORKFLOW,
    ]

    sources = packet.get("authority_sources", {})
    for source in (
        sources.get("workflow"),
        sources.get("policy"),
        sources.get("gate_registry"),
        *sources.get("additional_sources", []),
    ):
        if not isinstance(source, dict):
            continue
        source_path = source.get("path_or_uri")
        if _safe_relative_path(source_path):
            protected.append(repository_root / PurePosixPath(source_path))

    producer = packet.get("producer")
    if isinstance(producer, dict) and _safe_relative_path(
        producer.get("producer_source")
    ):
        protected.append(
            repository_root / PurePosixPath(producer["producer_source"])
        )

    for path in protected:
        if same_target(output, path):
            raise SemanticError(f"refusing_to_overwrite_input: {path}")

    if output.name in AUTHORITY_SURFACE_OUTPUT_NAMES:
        raise SemanticError(
            f"refusing_authority_or_contract_surface_output: {output.name}"
        )

    _reject_symlink_path(output, label="output")


class ArchiveResolver:
    def __init__(
        self,
        *,
        outer_bytes: bytes,
        artifacts: dict[str, dict[str, Any]],
    ) -> None:
        self._outer_bytes = outer_bytes
        self._artifacts = artifacts
        self._artifact_bytes: dict[str, bytes] = {}
        self._archives: dict[
            str | None,
            tuple[io.BytesIO, zipfile.ZipFile, dict[str, zipfile.ZipInfo]],
        ] = {}
        self.errors: list[str] = []

    def close(self) -> None:
        for stream, archive, _table in self._archives.values():
            try:
                archive.close()
            finally:
                stream.close()
        self._archives.clear()

    def __enter__(self) -> ArchiveResolver:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _archive_bytes(self, container_id: str | None, stack: set[str]) -> bytes:
        if container_id is None:
            return self._outer_bytes
        parent = self._artifacts.get(container_id)
        if not isinstance(parent, dict):
            raise SemanticError(f"container_artifact_missing: {container_id}")
        if (
            parent.get("content_kind") != "archive"
            or parent.get("media_type") != "application/zip"
        ):
            raise SemanticError(f"container_artifact_not_zip: {container_id}")
        return self.resolve(container_id, stack=stack)

    def _open_archive(
        self,
        container_id: str | None,
        *,
        stack: set[str] | None = None,
    ) -> tuple[zipfile.ZipFile, dict[str, zipfile.ZipInfo]]:
        cached = self._archives.get(container_id)
        if cached is not None:
            return cached[1], cached[2]

        active = set() if stack is None else set(stack)
        data = self._archive_bytes(container_id, active)
        label = "external carrier" if container_id is None else container_id
        stream = io.BytesIO(data)
        try:
            archive = zipfile.ZipFile(stream)
        except Exception as exc:
            stream.close()
            raise SemanticError(f"invalid_zip_container: {label}: {exc}") from exc

        table: dict[str, zipfile.ZipInfo] = {}
        for info in archive.infolist():
            name = info.filename
            if name in table:
                archive.close()
                stream.close()
                raise SemanticError(f"duplicate_zip_member: {label}: {name}")
            if not _safe_zip_name(name, is_directory=info.is_dir()):
                archive.close()
                stream.close()
                raise SemanticError(f"unsafe_zip_member: {label}: {name!r}")
            if info.flag_bits & 0x1:
                archive.close()
                stream.close()
                raise SemanticError(f"encrypted_zip_member: {label}: {name}")
            if _zip_entry_is_symlink(info):
                archive.close()
                stream.close()
                raise SemanticError(f"symlink_zip_member: {label}: {name}")
            table[name] = info

        self._archives[container_id] = (stream, archive, table)
        return archive, table

    def resolve(
        self,
        artifact_id: str,
        *,
        stack: set[str] | None = None,
    ) -> bytes:
        cached = self._artifact_bytes.get(artifact_id)
        if cached is not None:
            return cached

        active = set() if stack is None else set(stack)
        if artifact_id in active:
            cycle = " -> ".join(sorted(active | {artifact_id}))
            raise SemanticError(f"container_cycle: {cycle}")
        active.add(artifact_id)

        artifact = self._artifacts.get(artifact_id)
        if not isinstance(artifact, dict):
            raise SemanticError(f"artifact_missing: {artifact_id}")

        container_id = artifact.get("container_artifact_id")
        archive, table = self._open_archive(container_id, stack=active)
        member_path = artifact.get("member_path")
        if not isinstance(member_path, str) or member_path not in table:
            raise SemanticError(
                f"artifact_member_missing: {artifact_id}: {member_path!r}"
            )
        info = table[member_path]
        if info.is_dir():
            raise SemanticError(
                f"artifact_member_is_directory: {artifact_id}: {member_path}"
            )

        declared_size = artifact.get("size_bytes")
        if info.file_size != declared_size:
            raise SemanticError(
                "artifact_zip_size_mismatch: "
                f"{artifact_id}: declared={declared_size!r} zip={info.file_size}"
            )

        try:
            data = archive.read(info)
        except Exception as exc:
            raise SemanticError(
                f"artifact_member_read_failed: {artifact_id}: {exc}"
            ) from exc

        actual_size = len(data)
        actual_sha = sha256_bytes(data)
        if actual_size != declared_size:
            raise SemanticError(
                "artifact_size_mismatch: "
                f"{artifact_id}: declared={declared_size!r} actual={actual_size}"
            )
        if actual_sha != artifact.get("sha256"):
            raise SemanticError(
                "artifact_digest_mismatch: "
                f"{artifact_id}: declared={artifact.get('sha256')!r} "
                f"actual={actual_sha}"
            )

        self._artifact_bytes[artifact_id] = data
        return data

    def member_names(self, container_id: str | None) -> set[str]:
        _archive, table = self._open_archive(container_id)
        return {name for name, info in table.items() if not info.is_dir()}

    def resolve_all(self) -> tuple[dict[str, bytes], list[str]]:
        for artifact_id in sorted(self._artifacts):
            try:
                self.resolve(artifact_id)
            except Exception as exc:
                self.errors.append(str(exc))
        return dict(self._artifact_bytes), list(self.errors)


def _flatten_source_records(
    packet: dict[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    sources = packet.get("authority_sources", {})
    rows: list[tuple[str, dict[str, Any]]] = []
    for name in ("workflow", "policy", "gate_registry"):
        row = sources.get(name)
        if isinstance(row, dict):
            rows.append((name, row))
    for index, row in enumerate(sources.get("additional_sources", [])):
        if isinstance(row, dict):
            rows.append((f"additional_sources[{index}]", row))
    return rows


def _verify_source_records(
    packet: dict[str, Any],
    *,
    repository_root: Path,
) -> tuple[bool, bool, dict[str, bytes], list[str]]:
    errors: list[str] = []
    source_bytes: dict[str, bytes] = {}
    rows = _flatten_source_records(packet)
    subject = packet.get("subject", {})

    source_ids = [row.get("source_id") for _name, row in rows]
    if not all(isinstance(item, str) for item in source_ids):
        errors.append("source_identifier_invalid")
    if len(source_ids) != len(set(source_ids)):
        errors.append("source_identifier_duplicate")

    additional = packet.get("authority_sources", {}).get("additional_sources", [])
    additional_ids = [
        row.get("source_id") for row in additional if isinstance(row, dict)
    ]
    if not isinstance(additional, list) or additional_ids != sorted(additional_ids):
        errors.append("additional_sources_not_deterministically_ordered")

    complete = True
    for label, row in rows:
        source_id = row.get("source_id")
        revision = row.get("source_revision")
        source_path = row.get("path_or_uri")
        if not isinstance(source_id, str) or not isinstance(source_path, str):
            errors.append(f"source_identity_invalid: {label}")
            complete = False
            continue

        if revision is None:
            if label in {"workflow", "policy", "gate_registry"}:
                errors.append(f"required_source_revision_unavailable: {source_id}")
            complete = False
            continue
        if not isinstance(revision, str):
            errors.append(f"source_revision_invalid: {source_id}")
            complete = False
            continue

        try:
            data = _git_blob_bytes(
                repository_root,
                revision=revision,
                path=source_path,
            )
        except Exception as exc:
            errors.append(str(exc))
            complete = False
            continue

        source_bytes[source_id] = data
        actual_sha = sha256_bytes(data)
        actual_size = len(data)
        if actual_sha != row.get("sha256"):
            errors.append(
                "source_digest_mismatch: "
                f"{source_id}: declared={row.get('sha256')!r} actual={actual_sha}"
            )
            complete = False
        if actual_size != row.get("size_bytes"):
            errors.append(
                "source_size_mismatch: "
                f"{source_id}: declared={row.get('size_bytes')!r} "
                f"actual={actual_size}"
            )
            complete = False

        try:
            parsed = load_yaml_bytes(data, label=f"source {source_id}")
        except Exception as exc:
            parsed = None
            errors.append(str(exc))
            complete = False

        if label == "workflow":
            expected_ref = (
                f"{subject.get('repository')}/{subject.get('workflow_path')}"
                f"@{subject.get('source_ref')}"
            )
            if (
                row.get("role") != "workflow"
                or source_path != subject.get("workflow_path")
                or revision != subject.get("source_commit")
                or row.get("workflow_name") != subject.get("workflow_name")
                or row.get("workflow_ref") != subject.get("workflow_ref")
                or row.get("workflow_ref") != expected_ref
                or not isinstance(parsed, dict)
                or parsed.get("name") != row.get("workflow_name")
            ):
                errors.append("workflow_source_identity_mismatch")
                complete = False
        elif label == "policy":
            policy_data = parsed.get("policy") if isinstance(parsed, dict) else None
            if (
                row.get("role") != "policy"
                or revision != subject.get("source_commit")
                or row.get("sha256") != subject.get("policy_sha256")
                or row.get("policy_id") != subject.get("policy_id")
                or not isinstance(policy_data, dict)
                or policy_data.get("id") != row.get("policy_id")
            ):
                errors.append("policy_source_identity_mismatch")
                complete = False
        elif label == "gate_registry":
            if (
                row.get("role") != "gate_registry"
                or revision != subject.get("source_commit")
                or not isinstance(parsed, dict)
                or parsed.get("version") != row.get("registry_id")
            ):
                errors.append("gate_registry_source_identity_mismatch")
                complete = False

    semantic_ok = not errors
    return semantic_ok, semantic_ok and complete, source_bytes, errors


def _verify_provenance(
    packet: dict[str, Any],
    *,
    packet_path: Path,
    repository_root: Path,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    status = packet.get("record_status")
    identity = packet.get("packet_identity", {})
    carrier = packet.get("carrier", {})

    if status == "example":
        fixture = packet.get("fixture_provenance")
        if packet.get("producer") is not None:
            errors.append("example_packet_claims_producer")
        if not isinstance(fixture, dict):
            errors.append("example_packet_missing_fixture_provenance")
        else:
            relative_path = _relative_packet_path(packet_path, repository_root)
            if relative_path != fixture.get("fixture_source_path"):
                errors.append(
                    "fixture_source_path_mismatch: "
                    f"declared={fixture.get('fixture_source_path')!r} "
                    f"actual={relative_path!r}"
                )
            if fixture.get("schema_identity") != packet.get("schema_version"):
                errors.append("fixture_schema_identity_mismatch")
            if fixture.get("packet_producer_execution_claimed") is not False:
                errors.append("fixture_claims_packet_producer_execution")
            if (
                fixture.get("source_data_status") == "historical_observed"
                and carrier.get("carrier_kind") == "example_archive"
            ):
                errors.append("historical_observed_fixture_uses_example_carrier")
        if identity.get("packet_scope") != "example":
            errors.append("example_packet_scope_mismatch")
    elif status == "observed":
        producer = packet.get("producer")
        if packet.get("fixture_provenance") is not None:
            errors.append("observed_packet_claims_fixture_provenance")
        if not isinstance(producer, dict):
            errors.append("observed_packet_missing_producer")
        else:
            mode = producer.get("production_mode")
            expected_scope = {
                "current_run_export": "current_run",
                "post_run_export": "post_run_preservation",
                "fixed_source_adapter": "fixed_source_adapter",
            }.get(mode)
            if expected_scope is None or identity.get("packet_scope") != expected_scope:
                errors.append("producer_mode_packet_scope_mismatch")
            if mode == "current_run_export" and (
                producer.get("producer_run_key")
                != packet.get("subject", {}).get("subject_run_key")
            ):
                errors.append("current_run_producer_run_key_mismatch")
            source = producer.get("producer_source")
            revision = producer.get("producer_source_revision")
            if not isinstance(source, str) or not isinstance(revision, str):
                errors.append("producer_source_identity_incomplete")
            else:
                try:
                    data = _git_blob_bytes(
                        repository_root,
                        revision=revision,
                        path=source,
                    )
                    if sha256_bytes(data) != producer.get("producer_source_sha256"):
                        errors.append("producer_source_digest_mismatch")
                except Exception as exc:
                    errors.append(str(exc))
        if identity.get("packet_scope") == "example":
            errors.append("observed_packet_uses_example_scope")
        if carrier.get("carrier_kind") == "example_archive":
            errors.append("observed_packet_uses_example_carrier")
    else:
        errors.append(f"record_status_invalid: {status!r}")

    return not errors, errors


def _verify_subject_identity(packet: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    subject = packet.get("subject", {})
    identity = packet.get("packet_identity", {})
    carrier = packet.get("carrier", {})

    expected_run_key = (
        f"GITHUB_RUN_ID={subject.get('workflow_run_id')}"
        f"|GITHUB_RUN_ATTEMPT={subject.get('workflow_run_attempt')}"
        f"|GITHUB_WORKFLOW={subject.get('workflow_name')}"
    )
    expected_workflow_ref = (
        f"{subject.get('repository')}/{subject.get('workflow_path')}"
        f"@{subject.get('source_ref')}"
    )

    if subject.get("subject_run_key") != expected_run_key:
        errors.append("subject_run_key_not_canonical")
    if identity.get("subject_run_key") != subject.get("subject_run_key"):
        errors.append("packet_subject_run_key_mismatch")
    if identity.get("carrier_id") != carrier.get("carrier_id"):
        errors.append("packet_carrier_id_mismatch")
    if subject.get("workflow_ref") != expected_workflow_ref:
        errors.append("subject_workflow_ref_mismatch")
    # Active policy sets are an ordered part of the historical subject identity.
    # Preserve their recorded order; require only non-empty unique string values
    # here, then verify the exact order against the bound subject artifacts.
    if not _ordered_unique_non_empty_strings(subject.get("active_policy_sets")):
        errors.append("active_policy_sets_not_unique_non_empty")
    try:
        parse_utc(identity.get("packet_created_utc"))
    except Exception as exc:
        errors.append(f"packet_created_utc_invalid: {exc}")

    return not errors, errors


def _artifact_expected_id(artifact: dict[str, Any]) -> str | None:
    member_path = artifact.get("member_path")
    parent = artifact.get("container_artifact_id")
    if not isinstance(member_path, str):
        return None
    if parent is None:
        return f"artifact:{member_path}"
    if not isinstance(parent, str):
        return None
    return f"{parent}/{member_path}"


def _artifact_expected_display(
    artifact: dict[str, Any],
    *,
    carrier_location: str,
    artifact_index: dict[str, dict[str, Any]],
) -> str | None:
    member_path = artifact.get("member_path")
    parent = artifact.get("container_artifact_id")
    if not isinstance(member_path, str):
        return None
    if parent is None:
        return f"{carrier_location}!/{member_path}"
    parent_row = artifact_index.get(parent)
    if not isinstance(parent_row, dict):
        return None
    parent_display = parent_row.get("display_path_or_uri")
    if not isinstance(parent_display, str):
        return None
    return f"{parent_display}!/{member_path}"


def _container_graph_acyclic(
    artifacts: dict[str, dict[str, Any]],
) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(identifier: str) -> bool:
        if identifier in visited:
            return True
        if identifier in visiting:
            return False
        visiting.add(identifier)
        parent = artifacts[identifier].get("container_artifact_id")
        if isinstance(parent, str):
            if parent not in artifacts or not visit(parent):
                return False
        visiting.remove(identifier)
        visited.add(identifier)
        return True

    return all(visit(identifier) for identifier in artifacts)


def _verify_artifact_graph(
    packet: dict[str, Any],
    *,
    carrier_bytes: bytes,
) -> tuple[bool, bool, dict[str, bytes], list[str]]:
    errors: list[str] = []
    rows = packet.get("artifacts", [])
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        return False, False, {}, ["artifact_records_invalid"]

    artifacts = _index_rows(
        rows,
        "artifact_id",
        label="artifact",
        errors=errors,
    )
    identifiers = [row.get("artifact_id") for row in rows]
    if identifiers != sorted(identifiers):
        errors.append("artifact_records_not_deterministically_ordered")

    locations: list[tuple[str | None, str]] = []
    carrier_location = packet.get("carrier", {}).get("path_or_uri")
    root_prefix = packet.get("carrier", {}).get("root_prefix")
    for row in rows:
        artifact_id = row.get("artifact_id")
        parent = row.get("container_artifact_id")
        member_path = row.get("member_path")
        if artifact_id != _artifact_expected_id(row):
            errors.append(f"artifact_id_path_mismatch: {artifact_id}")
        if row.get("display_path_or_uri") != _artifact_expected_display(
            row,
            carrier_location=carrier_location,
            artifact_index=artifacts,
        ):
            errors.append(f"artifact_display_path_mismatch: {artifact_id}")
        if not isinstance(member_path, str):
            continue
        locations.append((parent, member_path))
        if (
            parent is None
            and isinstance(root_prefix, str)
            and not member_path.startswith(root_prefix + "/")
        ):
            errors.append(f"artifact_outside_carrier_root_prefix: {artifact_id}")
        if isinstance(parent, str):
            parent_row = artifacts.get(parent)
            if not isinstance(parent_row, dict):
                errors.append(f"artifact_container_unresolved: {artifact_id}: {parent}")
            elif (
                parent_row.get("content_kind") != "archive"
                or parent_row.get("media_type") != "application/zip"
            ):
                errors.append(
                    f"artifact_container_not_archive: {artifact_id}: {parent}"
                )

    if len(locations) != len(set(locations)):
        errors.append("artifact_container_member_location_duplicate")
    if not _container_graph_acyclic(artifacts):
        errors.append("artifact_container_graph_cycle_or_unresolved_parent")

    artifact_bytes: dict[str, bytes] = {}
    graph_complete = True
    try:
        with ArchiveResolver(
            outer_bytes=carrier_bytes,
            artifacts=artifacts,
        ) as resolver:
            artifact_bytes, resolver_errors = resolver.resolve_all()
            errors.extend(resolver_errors)

            archive_containers: list[str | None] = [None]
            archive_containers.extend(
                artifact_id
                for artifact_id, row in artifacts.items()
                if row.get("content_kind") == "archive"
                and row.get("media_type") == "application/zip"
            )
            for container_id in archive_containers:
                try:
                    actual = resolver.member_names(container_id)
                except Exception as exc:
                    errors.append(str(exc))
                    graph_complete = False
                    continue
                declared = {
                    row.get("member_path")
                    for row in rows
                    if row.get("container_artifact_id") == container_id
                    and isinstance(row.get("member_path"), str)
                }
                if not declared.issubset(actual):
                    errors.append(
                        f"archive_declared_members_missing: {container_id!r}"
                    )
                if declared != actual:
                    graph_complete = False
    except Exception as exc:
        errors.append(str(exc))
        graph_complete = False

    if len(artifact_bytes) != len(rows):
        errors.append(
            "artifact_byte_resolution_incomplete: "
            f"resolved={len(artifact_bytes)} declared={len(rows)}"
        )
        graph_complete = False

    semantic_ok = not errors
    return semantic_ok, semantic_ok and graph_complete, artifact_bytes, errors


def _verify_provider_binding(
    binding: Any,
    *,
    artifact_sha256: str,
    artifact_size: int,
    label: str,
) -> tuple[bool, bool, list[str]]:
    if binding is None:
        return True, False, []
    if not isinstance(binding, dict):
        return False, False, [f"provider_binding_invalid: {label}"]

    errors: list[str] = []
    provider_sha = binding.get("provider_sha256")
    provider_size = binding.get("provider_size_bytes")
    digest_flag = binding.get("downloaded_sha256_matches")
    size_flag = binding.get("downloaded_size_matches")

    digest_bound = isinstance(provider_sha, str)
    size_bound = isinstance(provider_size, int) and not isinstance(provider_size, bool)

    if digest_bound:
        if provider_sha != artifact_sha256 or digest_flag is not True:
            errors.append(f"provider_digest_binding_mismatch: {label}")
    elif digest_flag is not None:
        errors.append(f"provider_digest_match_without_digest: {label}")

    if size_bound:
        if provider_size != artifact_size or size_flag is not True:
            errors.append(f"provider_size_binding_mismatch: {label}")
    elif size_flag is not None:
        errors.append(f"provider_size_match_without_size: {label}")

    created = binding.get("created_utc")
    expires = binding.get("expires_utc")
    if created is not None or expires is not None:
        if created is None or expires is None:
            errors.append(f"provider_retention_window_incomplete: {label}")
        else:
            try:
                if parse_utc(expires) < parse_utc(created):
                    errors.append(f"provider_retention_window_reversed: {label}")
            except Exception as exc:
                errors.append(f"provider_retention_window_invalid: {label}: {exc}")

    fully_bound = digest_bound and size_bound and not errors
    return not errors, fully_bound, errors


def _verify_provider_bindings(
    packet: dict[str, Any],
) -> tuple[bool, int, int, list[str]]:
    errors: list[str] = []
    total = 0
    bound = 0
    provider_identities: set[tuple[str, str]] = set()

    carrier = packet.get("carrier", {})
    carrier_ok, _carrier_bound, carrier_errors = _verify_provider_binding(
        carrier.get("provider_binding"),
        artifact_sha256=carrier.get("sha256"),
        artifact_size=carrier.get("size_bytes"),
        label="carrier",
    )
    if not carrier_ok:
        errors.extend(carrier_errors)

    for row in packet.get("artifacts", []):
        binding = row.get("provider_binding")
        if binding is None:
            continue
        total += 1
        provider = binding.get("provider")
        provider_artifact_id = binding.get("provider_artifact_id")
        identity = (str(provider), str(provider_artifact_id))
        if identity in provider_identities:
            errors.append(
                "provider_artifact_identity_duplicate: "
                f"{provider}:{provider_artifact_id}"
            )
        provider_identities.add(identity)
        ok, fully_bound, row_errors = _verify_provider_binding(
            binding,
            artifact_sha256=row.get("sha256"),
            artifact_size=row.get("size_bytes"),
            label=row.get("artifact_id", "<unknown>"),
        )
        if fully_bound:
            bound += 1
        if not ok:
            errors.extend(row_errors)

    return not errors, total, bound, errors


def _verify_role_bindings(
    packet: dict[str, Any],
) -> tuple[bool, bool, int, int, list[str], list[str], list[str]]:
    errors: list[str] = []
    rows = packet.get("artifacts", [])
    artifacts = {
        row.get("artifact_id"): row
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("artifact_id"), str)
    }
    bindings = packet.get("role_bindings", {})
    if not isinstance(bindings, dict):
        return False, False, 0, 0, [], [], ["role_bindings_invalid"]

    missing_roles: list[str] = []
    unresolved_ids: set[str] = set()
    total = 0
    resolved = 0
    complete = True

    for name, expected_role in CORE_SINGLETON_ROLE_BINDINGS.items():
        reference = bindings.get(name)
        expected_ids = sorted(
            artifact_id
            for artifact_id, row in artifacts.items()
            if row.get("role") == expected_role
        )
        if not isinstance(reference, str):
            missing_roles.append(name)
            complete = False
            continue
        total += 1
        row = artifacts.get(reference)
        if row is None:
            unresolved_ids.add(reference)
            complete = False
            continue
        if row.get("role") != expected_role:
            errors.append(
                f"role_binding_semantic_mismatch: {name}: {reference}"
            )
            complete = False
            continue
        resolved += 1
        if expected_ids != [reference]:
            missing_roles.append(name)
            complete = False

    for name, allowed_roles in LIST_ROLE_BINDINGS.items():
        references = bindings.get(name)
        if not isinstance(references, list):
            errors.append(f"role_binding_list_invalid: {name}")
            complete = False
            continue
        if not _sorted_unique_strings(references):
            errors.append(f"role_binding_list_not_sorted_unique: {name}")
            complete = False

        expected_ids = sorted(
            artifact_id
            for artifact_id, row in artifacts.items()
            if row.get("role") in allowed_roles
        )
        total += len(references)
        resolved_here: list[str] = []
        for reference in references:
            row = artifacts.get(reference)
            if row is None:
                unresolved_ids.add(reference)
                complete = False
                continue
            if row.get("role") not in allowed_roles:
                errors.append(
                    f"role_binding_semantic_mismatch: {name}: {reference}"
                )
                complete = False
                continue
            resolved += 1
            resolved_here.append(reference)

        if name == "candidate_records" and not references:
            missing_roles.append(name)
            complete = False
        elif sorted(resolved_here) != expected_ids:
            if expected_ids:
                missing_roles.append(name)
            complete = False

    for row in rows:
        parent = row.get("container_artifact_id")
        if isinstance(parent, str) and parent not in artifacts:
            unresolved_ids.add(parent)
            complete = False

    semantic_ok = not errors
    derived_complete = (
        semantic_ok
        and complete
        and not missing_roles
        and not unresolved_ids
    )
    return (
        semantic_ok,
        derived_complete,
        total,
        resolved,
        sorted(set(missing_roles)),
        sorted(unresolved_ids),
        errors,
    )


def _parse_artifact_contents(
    packet: dict[str, Any],
    *,
    artifact_bytes: dict[str, bytes],
) -> tuple[bool, dict[str, Any], list[str]]:
    parsed: dict[str, Any] = {}
    errors: list[str] = []
    for row in packet.get("artifacts", []):
        artifact_id = row.get("artifact_id")
        if not isinstance(artifact_id, str) or artifact_id not in artifact_bytes:
            continue
        data = artifact_bytes[artifact_id]
        kind = row.get("content_kind")
        try:
            if kind == "json":
                parsed[artifact_id] = load_json_bytes(data, label=artifact_id)
            elif kind == "jsonl":
                records: list[Any] = []
                text = data.decode("utf-8")
                for line_number, line in enumerate(text.splitlines(), start=1):
                    if not line.strip():
                        continue
                    records.append(
                        load_json_bytes(
                            line.encode("utf-8"),
                            label=f"{artifact_id}:{line_number}",
                        )
                    )
                if not records:
                    raise StrictJsonError(f"{artifact_id}: empty JSONL")
                parsed[artifact_id] = records
            elif kind == "yaml":
                parsed[artifact_id] = load_yaml_bytes(data, label=artifact_id)
        except Exception as exc:
            errors.append(f"artifact_content_parse_failed: {exc}")
    return not errors, parsed, errors


def _bound_artifact_document(
    packet: dict[str, Any],
    parsed: dict[str, Any],
    binding_name: str,
) -> Any:
    reference = packet.get("role_bindings", {}).get(binding_name)
    if not isinstance(reference, str):
        return None
    return parsed.get(reference)


def _value_matches(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return left == right
    return str(left) == str(right)


def _document_subject_identity_ok(document: Any, subject: dict[str, Any]) -> bool:
    if isinstance(document, list):
        return all(_document_subject_identity_ok(item, subject) for item in document)
    if not isinstance(document, dict):
        return True

    checks: list[bool] = []

    def compare(container: dict[str, Any], key: str, expected: Any) -> None:
        if key in container:
            checks.append(_value_matches(container[key], expected))

    compare(document, "repository", subject.get("repository"))
    compare(document, "git_sha", subject.get("source_commit"))
    compare(document, "source_commit", subject.get("source_commit"))
    compare(document, "run_key", subject.get("subject_run_key"))
    compare(document, "subject_run_key", subject.get("subject_run_key"))
    compare(document, "workflow_ref", subject.get("workflow_ref"))
    compare(document, "run_mode", subject.get("run_mode"))

    if "run_id" in document:
        run_id = document["run_id"]
        checks.append(
            _value_matches(run_id, subject.get("workflow_run_id"))
            or _value_matches(run_id, subject.get("subject_run_key"))
        )
    compare(document, "workflow_run_id", subject.get("workflow_run_id"))
    compare(document, "workflow_run_attempt", subject.get("workflow_run_attempt"))

    subject_block = document.get("subject")
    if isinstance(subject_block, dict):
        compare(subject_block, "repository", subject.get("repository"))
        compare(subject_block, "commit_sha", subject.get("source_commit"))
        compare(subject_block, "source_commit", subject.get("source_commit"))
        compare(
            subject_block,
            "release_candidate",
            subject.get("release_candidate_id"),
        )
        compare(
            subject_block,
            "release_candidate_id",
            subject.get("release_candidate_id"),
        )
        compare(subject_block, "subject_run_key", subject.get("subject_run_key"))

    for key in ("run", "run_identity"):
        run = document.get(key)
        if not isinstance(run, dict):
            continue
        compare(run, "repository", subject.get("repository"))
        compare(run, "git_sha", subject.get("source_commit"))
        compare(run, "source_commit", subject.get("source_commit"))
        compare(run, "run_key", subject.get("subject_run_key"))
        compare(run, "subject_run_key", subject.get("subject_run_key"))
        if "run_id" in run:
            run_id = run["run_id"]
            checks.append(
                _value_matches(run_id, subject.get("workflow_run_id"))
                or _value_matches(run_id, subject.get("subject_run_key"))
            )
        compare(run, "workflow_run_id", subject.get("workflow_run_id"))
        compare(run, "run_attempt", subject.get("workflow_run_attempt"))
        compare(
            run,
            "workflow_run_attempt",
            subject.get("workflow_run_attempt"),
        )
        compare(run, "workflow_name", subject.get("workflow_name"))
        compare(run, "event_name", subject.get("event_name"))
        compare(run, "ref", subject.get("source_ref"))
        compare(run, "run_mode", subject.get("run_mode"))

    metrics = document.get("metrics")
    if isinstance(metrics, dict):
        compare(metrics, "git_sha", subject.get("source_commit"))
        compare(metrics, "run_key", subject.get("subject_run_key"))
        compare(metrics, "run_mode", subject.get("run_mode"))
        compare(metrics, "gate_policy_sha256", subject.get("policy_sha256"))

    return all(checks)


def _decision_document_value(document: Any) -> str | None:
    if not isinstance(document, dict):
        return None
    required_passed = document.get("required_gates_passed")
    blocking = document.get("blocking_reasons")
    release_level = document.get("release_level")
    if required_passed is True and blocking == [] and isinstance(release_level, str):
        if release_level.upper().endswith("PASS"):
            return "ALLOW"
    if required_passed is False or (isinstance(blocking, list) and blocking):
        return "BLOCK"
    if isinstance(release_level, str) and any(
        token in release_level.upper() for token in ("FAIL", "BLOCK")
    ):
        return "BLOCK"
    return None


def _verify_subject_artifact_bindings(
    packet: dict[str, Any],
    *,
    parsed: dict[str, Any],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    subject = packet.get("subject", {})
    bindings = packet.get("role_bindings", {})
    artifacts = {
        row.get("artifact_id"): row
        for row in packet.get("artifacts", [])
        if isinstance(row, dict) and isinstance(row.get("artifact_id"), str)
    }

    digest_bindings = {
        "final_status": "final_status_sha256",
        "release_decision": "release_decision_sha256",
    }
    for binding_name, subject_field in digest_bindings.items():
        reference = bindings.get(binding_name)
        if isinstance(reference, str):
            row = artifacts.get(reference, {})
            if row.get("sha256") != subject.get(subject_field):
                errors.append(f"subject_{binding_name}_digest_mismatch")

    for artifact_id, document in parsed.items():
        if not _document_subject_identity_ok(document, subject):
            errors.append(f"artifact_subject_identity_mismatch: {artifact_id}")

    run_metadata = _bound_artifact_document(packet, parsed, "run_metadata")
    if isinstance(run_metadata, dict):
        expected = {
            "repository": subject.get("repository"),
            "git_sha": subject.get("source_commit"),
            "release_candidate": subject.get("release_candidate_id"),
            "run_id": subject.get("workflow_run_id"),
            "run_attempt": subject.get("workflow_run_attempt"),
            "run_key": subject.get("subject_run_key"),
            "workflow_ref": subject.get("workflow_ref"),
        }
        if any(
            not _value_matches(run_metadata.get(key), value)
            for key, value in expected.items()
        ):
            errors.append("run_metadata_subject_binding_mismatch")

    final_status = _bound_artifact_document(packet, parsed, "final_status")
    if isinstance(final_status, dict):
        metrics = final_status.get("metrics", {})
        registry_sha = packet.get("authority_sources", {}).get(
            "gate_registry", {}
        ).get("sha256")
        if (
            not isinstance(metrics, dict)
            or metrics.get("git_sha") != subject.get("source_commit")
            or metrics.get("run_key") != subject.get("subject_run_key")
            or metrics.get("run_mode") != subject.get("run_mode")
            or metrics.get("gate_policy_sha256") != subject.get("policy_sha256")
            or metrics.get("gate_registry_sha256") != registry_sha
        ):
            errors.append("final_status_subject_binding_mismatch")

    release_decision = _bound_artifact_document(packet, parsed, "release_decision")
    if isinstance(release_decision, dict):
        if (
            release_decision.get("git_sha") != subject.get("source_commit")
            or release_decision.get("run_mode") != subject.get("run_mode")
            or release_decision.get("policy_sha256") != subject.get("policy_sha256")
            or release_decision.get("status_sha256")
            != subject.get("final_status_sha256")
            or release_decision.get("active_gate_sets")
            != subject.get("active_policy_sets")
            or _decision_document_value(release_decision)
            != subject.get("decision")
        ):
            errors.append("release_decision_subject_binding_mismatch")

    release_authority = _bound_artifact_document(packet, parsed, "release_authority")
    if isinstance(release_authority, dict):
        run_identity = release_authority.get("run_identity", {})
        inputs = release_authority.get("inputs", {})
        policy_set = release_authority.get("authority", {}).get("policy_set")
        expected_policy_set = "+".join(subject.get("active_policy_sets", []))
        authority_decision = release_authority.get("decision", {}).get("state")
        expected_authority_decision = (
            "PASS" if subject.get("decision") == "ALLOW" else "FAIL"
        )
        if (
            not isinstance(run_identity, dict)
            or run_identity.get("git_sha") != subject.get("source_commit")
            or run_identity.get("run_mode") != subject.get("run_mode")
            or run_identity.get("workflow_name") != subject.get("workflow_name")
            or run_identity.get("event_name") != subject.get("event_name")
            or run_identity.get("ref") != subject.get("source_ref")
            or inputs.get("status_json", {}).get("sha256")
            != subject.get("final_status_sha256")
            or inputs.get("gate_policy", {}).get("sha256")
            != subject.get("policy_sha256")
            or policy_set != expected_policy_set
            or authority_decision != expected_authority_decision
        ):
            errors.append("release_authority_subject_binding_mismatch")

    artifact_binding = _bound_artifact_document(packet, parsed, "artifact_binding")
    if isinstance(artifact_binding, dict):
        run = artifact_binding.get("run", {})
        carrier = artifact_binding.get("authority_carrier", {})
        gate_set = carrier.get("workflow_effective_required_gate_set", {})
        if (
            run.get("git_sha") != subject.get("source_commit")
            or run.get("run_key") != subject.get("subject_run_key")
            or run.get("run_mode") != subject.get("run_mode")
            or carrier.get("status_json", {}).get("sha256")
            != subject.get("final_status_sha256")
            or carrier.get("declared_gate_policy", {}).get("sha256")
            != subject.get("policy_sha256")
            or carrier.get("release_decision", {}).get("sha256")
            != subject.get("release_decision_sha256")
            or gate_set.get("policy_sets") != subject.get("active_policy_sets")
            or gate_set.get("sha256")
            != subject.get("materialized_gate_set_sha256")
        ):
            errors.append("artifact_binding_subject_mismatch")

    preservation_manifest = _bound_artifact_document(
        packet, parsed, "preservation_manifest"
    )
    if isinstance(preservation_manifest, dict):
        expected = {
            "repository": subject.get("repository"),
            "workflow": subject.get("workflow_name"),
            "workflow_run_id": subject.get("workflow_run_id"),
            "workflow_run_number": subject.get("workflow_run_number"),
            "workflow_run_attempt": subject.get("workflow_run_attempt"),
            "source_commit": subject.get("source_commit"),
            "source_ref": subject.get("source_ref"),
            "run_mode": subject.get("run_mode"),
            "active_policy_sets": subject.get("active_policy_sets"),
        }
        if any(
            preservation_manifest.get(key) != value
            for key, value in expected.items()
        ):
            errors.append("preservation_manifest_subject_binding_mismatch")
        primary = preservation_manifest.get("primary_gate_result")
        expected_primary = "allow" if subject.get("decision") == "ALLOW" else "block"
        if primary != expected_primary:
            errors.append("preservation_manifest_decision_mismatch")

    completeness = _bound_artifact_document(
        packet, parsed, "package_completeness_report"
    )
    if isinstance(completeness, dict) and (
        completeness.get("ok") is not True
        or completeness.get("status") != "complete"
        or completeness.get("errors") != []
    ):
        errors.append("package_completeness_report_not_complete")

    verification = _bound_artifact_document(
        packet, parsed, "independent_verification_report"
    )
    if isinstance(verification, dict) and (
        verification.get("verified") is not True
        or verification.get("status") != "verified"
        or verification.get("errors") != []
    ):
        errors.append("independent_verification_report_not_verified")

    return not errors, errors


def _verify_package_inventory(
    packet: dict[str, Any],
    *,
    parsed: dict[str, Any],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    bindings = packet.get("role_bindings", {})
    package_id = bindings.get("complete_package")
    inventory_id = bindings.get("package_inventory")
    inventory = parsed.get(inventory_id) if isinstance(inventory_id, str) else None
    if not isinstance(package_id, str) or not isinstance(inventory_id, str):
        return True, []
    if not isinstance(inventory, dict):
        return False, ["package_inventory_binding_unavailable"]

    files = inventory.get("files")
    if not isinstance(files, list) or not all(isinstance(row, dict) for row in files):
        return False, ["package_inventory_files_invalid"]
    paths = [row.get("path") for row in files]
    if (
        inventory.get("algorithm") != "sha256"
        or inventory.get("file_count") != len(files)
        or paths != sorted(paths)
        or len(paths) != len(set(paths))
    ):
        errors.append("package_inventory_header_or_order_invalid")

    artifacts = {
        row.get("artifact_id"): row
        for row in packet.get("artifacts", [])
        if isinstance(row, dict) and isinstance(row.get("artifact_id"), str)
    }
    declared_children = {
        row.get("member_path"): row
        for row in artifacts.values()
        if row.get("container_artifact_id") == package_id
        and row.get("artifact_id") != inventory_id
    }
    inventory_map = {
        row.get("path"): row
        for row in files
        if isinstance(row.get("path"), str)
    }
    if inventory_map.keys() != declared_children.keys():
        errors.append("package_inventory_member_set_mismatch")
    for path, inventory_row in inventory_map.items():
        artifact = declared_children.get(path)
        if not isinstance(artifact, dict):
            continue
        if (
            inventory_row.get("sha256") != artifact.get("sha256")
            or inventory_row.get("size_bytes") != artifact.get("size_bytes")
        ):
            errors.append(f"package_inventory_entry_mismatch: {path}")

    return not errors, errors


def _verify_preservation_checksums(
    packet: dict[str, Any],
    *,
    artifact_bytes: dict[str, bytes],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    bindings = packet.get("role_bindings", {})
    checksum_id = bindings.get("preservation_checksums")
    if not isinstance(checksum_id, str):
        return True, []
    if checksum_id not in artifact_bytes:
        return False, ["preservation_checksums_binding_unavailable"]

    try:
        text = artifact_bytes[checksum_id].decode("utf-8")
    except UnicodeDecodeError as exc:
        return False, [f"preservation_checksums_not_utf8: {exc}"]

    entries: dict[str, str] = {}
    for line_number, raw in enumerate(text.splitlines(), start=1):
        if not raw:
            continue
        if len(raw) < 67 or raw[64:66] != "  ":
            errors.append(f"preservation_checksum_line_invalid: {line_number}")
            continue
        digest = raw[:64]
        path = raw[66:]
        if (
            not all(ch in "0123456789abcdef" for ch in digest)
            or not _safe_relative_path(path)
            or path in entries
        ):
            errors.append(f"preservation_checksum_line_invalid: {line_number}")
            continue
        entries[path] = digest

    root_prefix = packet.get("carrier", {}).get("root_prefix")
    expected: dict[str, str] = {}
    for row in packet.get("artifacts", []):
        if row.get("container_artifact_id") is not None:
            continue
        if row.get("artifact_id") == checksum_id:
            continue
        member_path = row.get("member_path")
        if not isinstance(member_path, str):
            continue
        relative = member_path
        if isinstance(root_prefix, str) and member_path.startswith(root_prefix + "/"):
            relative = member_path[len(root_prefix) + 1 :]
        expected[relative] = row.get("sha256")

    if entries != expected:
        errors.append("preservation_checksums_member_set_or_digest_mismatch")
    return not errors, errors


def _verify_preservation_provider_manifest(
    packet: dict[str, Any],
    *,
    parsed: dict[str, Any],
) -> tuple[bool, list[str]]:
    manifest = _bound_artifact_document(packet, parsed, "preservation_manifest")
    if manifest is None:
        return True, []
    if not isinstance(manifest, dict):
        return False, ["preservation_manifest_unavailable"]

    github_artifacts = manifest.get("github_artifacts")
    if not isinstance(github_artifacts, list):
        return False, ["preservation_manifest_provider_records_invalid"]

    expected: dict[str, dict[str, Any]] = {}
    for row in packet.get("artifacts", []):
        binding = row.get("provider_binding")
        if not isinstance(binding, dict) or binding.get("provider") != "github_actions":
            continue
        expected[str(binding.get("provider_artifact_id"))] = {
            "artifact_name": binding.get("provider_artifact_name"),
            "created_at": binding.get("created_utc"),
            "expires_at": binding.get("expires_utc"),
            "sha256": row.get("sha256"),
            "size_bytes": row.get("size_bytes"),
        }

    actual: dict[str, dict[str, Any]] = {}
    duplicate_ids: set[str] = set()
    for row in github_artifacts:
        if not isinstance(row, dict):
            continue
        artifact_id = str(row.get("artifact_id"))
        if artifact_id in actual:
            duplicate_ids.add(artifact_id)
        actual[artifact_id] = {
            "artifact_name": row.get("artifact_name"),
            "created_at": row.get("created_at"),
            "expires_at": row.get("expires_at"),
            "sha256": row.get("downloaded_sha256"),
            "size_bytes": row.get("downloaded_size_bytes"),
        }

    if duplicate_ids:
        return False, [
            "preservation_manifest_provider_identity_duplicate: "
            + ",".join(sorted(duplicate_ids))
        ]
    return (
        expected == actual,
        []
        if expected == actual
        else ["preservation_manifest_provider_binding_mismatch"],
    )


def _verify_coverage(
    packet: dict[str, Any],
    *,
    source_complete: bool,
    carrier_complete: bool,
    artifact_complete: bool,
    role_complete: bool,
    provider_total: int,
    provider_bound: int,
    role_total: int,
    role_resolved: int,
    missing_roles: list[str],
    unresolved_ids: list[str],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    coverage = packet.get("coverage", {})
    expected_values = {
        "source_bindings_complete": source_complete,
        "carrier_binding_complete": carrier_complete,
        "artifact_graph_complete": artifact_complete,
        "role_bindings_complete": role_complete,
        "artifacts_total": len(packet.get("artifacts", [])),
        "provider_artifacts_total": provider_total,
        "provider_artifacts_bound": provider_bound,
        "role_bindings_total": role_total,
        "role_bindings_resolved": role_resolved,
        "missing_roles": missing_roles,
        "unresolved_artifact_ids": unresolved_ids,
    }
    for field, expected in expected_values.items():
        if coverage.get(field) != expected:
            errors.append(
                f"coverage_field_mismatch: {field}: "
                f"declared={coverage.get(field)!r} derived={expected!r}"
            )

    all_complete = (
        source_complete
        and carrier_complete
        and artifact_complete
        and role_complete
        and provider_total == provider_bound
    )
    status = coverage.get("coverage_status")
    if status == "complete" and not all_complete:
        errors.append("coverage_status_complete_without_complete_bindings")
    if status in {"partial", "unknown"} and all_complete:
        errors.append("coverage_status_incomplete_with_complete_bindings")
    if status not in {"complete", "partial", "unknown"}:
        errors.append("coverage_status_invalid")

    return not errors, errors


def semantic_checks(
    packet: dict[str, Any],
    *,
    packet_text: str,
    packet_path: Path,
    carrier_path: Path,
    carrier_bytes: bytes,
    repository_root: Path,
) -> tuple[dict[str, bool], list[str]]:
    checks: dict[str, bool] = {}
    errors: list[str] = []

    def record(name: str, condition: bool, details: Iterable[str] = ()) -> None:
        checks[name] = bool(condition)
        if not condition:
            detail_list = list(details)
            if detail_list:
                errors.extend(detail_list)
            else:
                errors.append(f"check_failed: {name}")

    record(
        "schema_version_ok",
        packet.get("schema_version") == SCHEMA_VERSION,
    )
    record(
        "packet_type_ok",
        packet.get("packet_type") == PACKET_TYPE,
    )

    canonical_ok = (
        packet_text == render_json(packet)
        and _all_object_keys_sorted(packet)
        and packet_text.endswith("\n")
        and "\r" not in packet_text
    )
    record("canonical_packet_serialization_ok", canonical_ok)

    # These arrays are set-like diagnostic/reference surfaces and therefore use
    # lexical ordering. subject.active_policy_sets is deliberately excluded: it
    # is an ordered historical identity sequence, not a lexically sorted set.
    set_like_reference_lists = [
        packet.get("coverage", {}).get("missing_roles"),
        packet.get("coverage", {}).get("unresolved_artifact_ids"),
        packet.get("errors"),
    ]
    set_like_reference_lists.extend(
        packet.get("role_bindings", {}).get(name)
        for name in LIST_ROLE_BINDINGS
    )
    record(
        "deterministic_reference_ordering_ok",
        all(
            _sorted_unique_strings(values)
            for values in set_like_reference_lists
        ),
    )

    provenance_ok, provenance_errors = _verify_provenance(
        packet,
        packet_path=packet_path,
        repository_root=repository_root,
    )
    record("provenance_branch_ok", provenance_ok, provenance_errors)

    subject_ok, subject_errors = _verify_subject_identity(packet)
    record("subject_identity_ok", subject_ok, subject_errors)

    carrier = packet.get("carrier", {})
    carrier_sha = sha256_bytes(carrier_bytes)
    carrier_complete = (
        carrier_sha == carrier.get("sha256")
        and len(carrier_bytes) == carrier.get("size_bytes")
        and carrier_path.is_file()
        and not carrier_path.is_symlink()
    )
    carrier_errors: list[str] = []
    if carrier_sha != carrier.get("sha256"):
        carrier_errors.append(
            "carrier_digest_mismatch: "
            f"declared={carrier.get('sha256')!r} actual={carrier_sha}"
        )
    if len(carrier_bytes) != carrier.get("size_bytes"):
        carrier_errors.append(
            "carrier_size_mismatch: "
            f"declared={carrier.get('size_bytes')!r} actual={len(carrier_bytes)}"
        )
    if carrier_path.is_symlink():
        carrier_errors.append(f"carrier_symlink_rejected: {carrier_path}")
    record("carrier_binding_ok", carrier_complete, carrier_errors)

    (
        source_semantic_ok,
        source_complete,
        _source_bytes,
        source_errors,
    ) = _verify_source_records(
        packet,
        repository_root=repository_root,
    )
    record(
        "authority_source_bindings_ok",
        source_semantic_ok,
        source_errors,
    )

    (
        artifact_semantic_ok,
        artifact_complete,
        artifact_bytes,
        artifact_errors,
    ) = _verify_artifact_graph(
        packet,
        carrier_bytes=carrier_bytes,
    )
    record("artifact_graph_ok", artifact_semantic_ok, artifact_errors)

    provider_ok, provider_total, provider_bound, provider_errors = (
        _verify_provider_bindings(packet)
    )
    record("provider_bindings_ok", provider_ok, provider_errors)

    (
        role_semantic_ok,
        role_complete,
        role_total,
        role_resolved,
        missing_roles,
        unresolved_ids,
        role_errors,
    ) = _verify_role_bindings(packet)
    record("role_bindings_ok", role_semantic_ok, role_errors)

    content_ok, parsed, content_errors = _parse_artifact_contents(
        packet,
        artifact_bytes=artifact_bytes,
    )
    record("artifact_content_syntax_ok", content_ok, content_errors)

    package_inventory_ok, package_inventory_errors = _verify_package_inventory(
        packet,
        parsed=parsed,
    )
    record(
        "package_inventory_ok",
        package_inventory_ok,
        package_inventory_errors,
    )

    checksums_ok, checksum_errors = _verify_preservation_checksums(
        packet,
        artifact_bytes=artifact_bytes,
    )
    record("preservation_checksums_ok", checksums_ok, checksum_errors)

    provider_manifest_ok, provider_manifest_errors = (
        _verify_preservation_provider_manifest(packet, parsed=parsed)
    )
    record(
        "preservation_provider_manifest_ok",
        provider_manifest_ok,
        provider_manifest_errors,
    )

    subject_artifacts_ok, subject_artifact_errors = (
        _verify_subject_artifact_bindings(packet, parsed=parsed)
    )
    record(
        "subject_artifact_bindings_ok",
        subject_artifacts_ok,
        subject_artifact_errors,
    )

    coverage_ok, coverage_errors = _verify_coverage(
        packet,
        source_complete=source_complete,
        carrier_complete=carrier_complete,
        artifact_complete=artifact_complete,
        role_complete=role_complete,
        provider_total=provider_total,
        provider_bound=provider_bound,
        role_total=role_total,
        role_resolved=role_resolved,
        missing_roles=missing_roles,
        unresolved_ids=unresolved_ids,
    )
    record("coverage_reconstruction_ok", coverage_ok, coverage_errors)

    packet_errors = packet.get("errors")
    packet_ok = packet.get("ok")
    ok_errors_semantics = (
        isinstance(packet_errors, list)
        and (
            (packet_ok is True and packet_errors == [])
            or (packet_ok is False and len(packet_errors) > 0)
        )
    )
    record("packet_ok_errors_semantics_ok", ok_errors_semantics)

    analysis_boundary = packet.get("analysis_boundary", {})
    content_boundary = packet.get("content_boundary", {})
    authority_boundary = packet.get("authority_boundary", {})
    boundaries_ok = (
        analysis_boundary.get("target_analysis_level") == "artifact_observed"
        and analysis_boundary.get("runtime_observation_included") is False
        and analysis_boundary.get(
            "runtime_observation_required_for_runtime_classification"
        )
        is True
        and analysis_boundary.get("observer_in_subject_totals") is False
        and analysis_boundary.get(
            "current_repository_state_substitution_allowed"
        )
        is False
        and analysis_boundary.get("packet_is_compute_report") is False
        and analysis_boundary.get("packet_is_runtime_observation") is False
        and content_boundary.get("packet_payload_mode") == "metadata_only"
        and content_boundary.get("artifact_bytes_embedded") is False
        and content_boundary.get("carrier_required_for_verification") is True
        and content_boundary.get("raw_secrets_included") is False
        and content_boundary.get("raw_model_inputs_included") is False
        and content_boundary.get("raw_model_outputs_included") is False
        and authority_boundary.get("write_mode") == "subject_input_only"
        and all(
            authority_boundary.get(field) is False
            for field in (
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
            )
        )
    )
    record("non_authoritative_boundaries_ok", boundaries_ok)

    return checks, errors


def make_diagnostic(
    *,
    ok: bool,
    schema_valid: bool,
    checks: dict[str, bool],
    errors: list[str],
) -> dict[str, Any]:
    return {
        "tool": TOOL_NAME,
        "schema_version": SCHEMA_VERSION,
        "packet_type": PACKET_TYPE,
        "ok": ok,
        "schema_valid": schema_valid,
        "checks": dict(sorted(checks.items())),
        "errors": sorted(set(errors)),
    }


def build_diagnostic(
    *,
    schema_path: Path,
    packet_path: Path,
    explicit_carrier: Path | None,
    repository_root: Path,
) -> tuple[dict[str, Any], int, Path | None, tuple[str, str, str] | None]:
    try:
        _reject_symlink_path(schema_path, label="schema")
        _reject_symlink_path(packet_path, label="packet")
        schema, _schema_text, schema_bytes = load_json_path(schema_path)
        packet, packet_text, packet_bytes = load_json_path(packet_path)
    except Exception as exc:
        diagnostic = make_diagnostic(
            ok=False,
            schema_valid=False,
            checks={},
            errors=[f"read_error: {exc}"],
        )
        return diagnostic, 2, None, None

    if not isinstance(schema, dict):
        diagnostic = make_diagnostic(
            ok=False,
            schema_valid=False,
            checks={},
            errors=["schema_not_object"],
        )
        return diagnostic, 2, None, None

    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except Exception as exc:
        diagnostic = make_diagnostic(
            ok=False,
            schema_valid=False,
            checks={},
            errors=[f"schema_invalid: {exc}"],
        )
        return diagnostic, 2, None, None

    errors = schema_errors(schema, packet)
    schema_valid = not errors
    if not isinstance(packet, dict):
        diagnostic = make_diagnostic(
            ok=False,
            schema_valid=schema_valid,
            checks={},
            errors=errors + ["packet_not_object"],
        )
        return diagnostic, 1, None, None

    try:
        carrier_path = _resolve_local_carrier_path(
            packet.get("carrier", {}).get("path_or_uri", ""),
            explicit_carrier=explicit_carrier,
            repository_root=repository_root,
        )
        _reject_symlink_path(carrier_path, label="carrier")
        carrier_bytes = carrier_path.read_bytes()
    except Exception as exc:
        diagnostic = make_diagnostic(
            ok=False,
            schema_valid=schema_valid,
            checks={},
            errors=errors + [f"carrier_read_error: {exc}"],
        )
        return diagnostic, 2, None, None

    checks: dict[str, bool] = {}
    if schema_valid:
        semantic, semantic_errors_list = semantic_checks(
            packet,
            packet_text=packet_text,
            packet_path=packet_path,
            carrier_path=carrier_path,
            carrier_bytes=carrier_bytes,
            repository_root=repository_root,
        )
        checks.update(semantic)
        errors.extend(semantic_errors_list)
    else:
        checks["semantic_checks_skipped_due_to_schema_errors"] = False

    ok = schema_valid and all(checks.values()) and not errors
    diagnostic = make_diagnostic(
        ok=ok,
        schema_valid=schema_valid,
        checks=checks,
        errors=errors,
    )
    snapshots = (
        sha256_bytes(schema_bytes),
        sha256_bytes(packet_bytes),
        sha256_bytes(carrier_bytes),
    )
    return diagnostic, 0 if ok else 1, carrier_path, snapshots


def _inputs_unchanged(
    *,
    schema_path: Path,
    packet_path: Path,
    carrier_path: Path,
    snapshots: tuple[str, str, str],
) -> bool:
    try:
        current = (
            sha256_bytes(schema_path.read_bytes()),
            sha256_bytes(packet_path.read_bytes()),
            sha256_bytes(carrier_path.read_bytes()),
        )
    except Exception:
        return False
    return current == snapshots


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a PULSEmech compute subject-input packet v0 against "
            "its Draft 2020-12 schema, exact historical source identities, "
            "immutable carrier, nested artifact graph, and semantic contract."
        )
    )
    parser.add_argument(
        "--schema",
        default=str(DEFAULT_SCHEMA),
        help="Path to the subject-input packet schema.",
    )
    parser.add_argument(
        "--packet",
        default=str(DEFAULT_PACKET),
        help="Path to the subject-input packet JSON.",
    )
    parser.add_argument(
        "--carrier",
        help=(
            "Optional local carrier path. Required when carrier.path_or_uri "
            "is not a local repository-relative path or file URI."
        ),
    )
    parser.add_argument(
        "--repository-root",
        default=str(DEFAULT_REPOSITORY_ROOT),
        help=(
            "Git repository containing the exact source revisions referenced "
            "by the packet. Historical bytes are read with git cat-file; "
            "current working-tree files are not substituted."
        ),
    )
    parser.add_argument(
        "--output",
        help="Optional path for the deterministic diagnostic JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    schema_path = Path(args.schema)
    packet_path = Path(args.packet)
    explicit_carrier = Path(args.carrier) if args.carrier else None
    repository_root = Path(args.repository_root)
    output = Path(args.output) if args.output else None

    diagnostic, exit_code, carrier_path, snapshots = build_diagnostic(
        schema_path=schema_path,
        packet_path=packet_path,
        explicit_carrier=explicit_carrier,
        repository_root=repository_root,
    )

    if carrier_path is not None:
        try:
            packet_value, _packet_text, _packet_bytes = load_json_path(packet_path)
            if isinstance(packet_value, dict):
                reject_unsafe_output(
                    output,
                    schema_path=schema_path,
                    packet_path=packet_path,
                    carrier_path=carrier_path,
                    repository_root=repository_root,
                    packet=packet_value,
                )
        except Exception as exc:
            diagnostic = make_diagnostic(
                ok=False,
                schema_valid=False,
                checks={},
                errors=[str(exc)],
            )
            exit_code = 2

    if exit_code != 2:
        if carrier_path is None or snapshots is None or not _inputs_unchanged(
            schema_path=schema_path,
            packet_path=packet_path,
            carrier_path=carrier_path,
            snapshots=snapshots,
        ):
            diagnostic = make_diagnostic(
                ok=False,
                schema_valid=False,
                checks={},
                errors=["protected_input_changed_during_validation"],
            )
            exit_code = 2

    rendered = render_json(diagnostic)
    sys.stdout.write(rendered)

    if output is not None and exit_code != 2:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable, Mapping, Protocol


TOOL_ID = "build_pulsemech_compute_subject_input_packet_v0"
TOOL_NAME = "PULSEmech compute subject-input packet producer"
TOOL_VERSION = "0.1.0"
SCHEMA_VERSION = "pulsemech_compute_subject_input_packet_v0"
PACKET_TYPE = "pulsemech_compute_subject_input_packet"
PRODUCER_SOURCE_PATH = "tools/build_pulsemech_compute_subject_input_packet_v0.py"
PRODUCTION_MODE = "fixed_source_adapter"
PACKET_SCOPE = "fixed_source_adapter"

PROTECTED_OUTPUT_NAMES = frozenset(
    {
        "status.json",
        "release_decision_v0.json",
        "release_authority_v0.json",
        "pulsemech_compute_subject_input_packet_v0.json",
    }
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CARRIER = ROOT / "PULSE_CI_6066_release_grade_artifact_preservation_v0.zip"
SCHEMA_SOURCE_PATH = "schemas/pulsemech_compute_subject_input_packet_v0.schema.json"
VALIDATOR_SOURCE_PATH = "tools/check_pulsemech_compute_subject_input_packet_v0.py"
FIXED_SOURCE_BUILDER_PATH = "tools/build_pulsemech_compute_binding_report_v0.py"

EXPECTED_CARRIER_SHA256 = (
    "7949bfd00468e6f9347fddaae732bdcebff5527e87ecb379a6c84a47176db966"
)
EXPECTED_CARRIER_SIZE = 44660
EXPECTED_REPOSITORY = "HKati/pulse-release-gates-0.1"
EXPECTED_SOURCE_COMMIT = "46b639706e23f80fe296a8893be18e2b5ab21f7e"
EXPECTED_RUN_KEY = (
    "GITHUB_RUN_ID=29249887581|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI"
)
OUTER_PREFIX = "pulse-ci-6066-preservation-v0/"
ORIGINAL_PREFIX = OUTER_PREFIX + "original-github-artifacts/"
COMPLETE_PACKAGE_NAME = "complete-release-grade-reference-package-29249887581-1.zip"
COMPLETENESS_ARCHIVE_NAME = "release-grade-package-completeness-29249887581-1.zip"
VERIFICATION_ARCHIVE_NAME = "release-grade-reference-package-verification-29249887581-1.zip"

ROLE_BY_PACKAGE_MEMBER: Mapping[str, str] = {
    "artifacts/artifact_provenance_binding_v0.json": "artifact_binding",
    "artifacts/external/llamaguard_attestation_verifier_v1.json": (
        "attestation_verifier_report"
    ),
    "artifacts/external/llamaguard_evaluator_manifest_v0.json": (
        "external_evaluator_manifest"
    ),
    "artifacts/external/llamaguard_raw.jsonl": "external_raw_evidence",
    "artifacts/external/llamaguard_summary.bundle.json": "attestation_bundle",
    "artifacts/external/llamaguard_summary.envelope.json": "attestation_envelope",
    "artifacts/external/llamaguard_summary.json": "external_summary",
    "artifacts/recorded_release_candidate_index_v0.json": "candidate_index",
    "artifacts/recorded_release_evidence_verifier_v0.json": (
        "recorded_verifier_report"
    ),
    "artifacts/release_authority_v0.json": "release_authority",
    "artifacts/release_decision_v0.json": "release_decision",
    "artifacts/release_evidence_input_manifest_v0.json": "evidence_manifest",
    "artifacts/report_card.html": "quality_ledger",
    "artifacts/required_gate_evidence_v0.json": "required_gate_evidence",
    "artifacts/status.json": "final_status",
    "artifacts/status_baseline.json": "status_baseline",
    "package_digest_inventory_v0.json": "package_inventory",
    "release-authority-audit-bundle/report_card.html": "reader_surface",
    "run_metadata_v0.json": "run_metadata",
}

CORE_ROLE_BINDINGS: Mapping[str, str] = {
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

LIST_ROLE_BINDINGS: Mapping[str, frozenset[str]] = {
    "candidate_records": frozenset({"candidate_record"}),
    "external_evidence_records": frozenset(
        {
            "external_evidence",
            "external_evaluator_manifest",
            "external_raw_evidence",
            "external_summary",
        }
    ),
    "attestation_records": frozenset(
        {
            "attestation_bundle",
            "attestation_envelope",
            "attestation_verifier_report",
        }
    ),
    "reader_surfaces": frozenset(
        {"quality_ledger", "report_card", "reader_surface"}
    ),
}

NON_ANALYSIS_ROLES = frozenset(
    {"quality_ledger", "report_card", "reader_surface", "other"}
)

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

WINDOWS_CURRENT_VERSION_REGISTRY_KEY = (
    r"SOFTWARE\Microsoft\Windows\CurrentVersion"
)
WINDOWS_PROGRAM_FILES_REGISTRY_VALUES = (
    "ProgramFilesDir",
    "ProgramFilesDir (x86)",
)
WINDOWS_GIT_RELATIVE_EXECUTABLES = (
    PureWindowsPath("Git") / "cmd" / "git.exe",
    PureWindowsPath("Git") / "bin" / "git.exe",
)


class BuilderError(RuntimeError):
    pass


class ValidatorModule(Protocol):
    def load_json_bytes(self, data: bytes, *, label: str) -> Any: ...

    def load_yaml_bytes(self, data: bytes, *, label: str) -> Any: ...

    def parse_utc(self, value: Any) -> Any: ...

    def schema_errors(self, schema: dict[str, Any], value: Any) -> list[str]: ...

    def _verified_git_repository_root(self, repository_root: Path) -> Path: ...

    def _trusted_git_executable(self) -> Path: ...

    def _git_blob_bytes(
        self, repository_root: Path, *, revision: str, path: str
    ) -> bytes: ...

    def _run_isolated_git(
        self,
        repository_root: Path,
        *,
        arguments: list[str],
        failure_prefix: str,
    ) -> bytes: ...

    def _decision_document_value(self, document: Any) -> str | None: ...

    def build_diagnostic(
        self,
        *,
        schema_path: Path,
        packet_path: Path,
        explicit_carrier: Path | None,
        repository_root: Path,
    ) -> tuple[dict[str, Any], int, Path | None, tuple[str, str, str] | None]: ...


@dataclass(frozen=True)
class Artifact:
    artifact_id: str
    role: str
    content_kind: str
    media_type: str
    container_artifact_id: str | None
    member_path: str
    display_path_or_uri: str
    payload: bytes
    provider_binding: dict[str, Any] | None = None

    def record(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "role": self.role,
            "content_kind": self.content_kind,
            "media_type": self.media_type,
            "container_artifact_id": self.container_artifact_id,
            "member_path": self.member_path,
            "display_path_or_uri": self.display_path_or_uri,
            "sha256": sha256_bytes(self.payload),
            "size_bytes": len(self.payload),
            "required_for_analysis": self.role not in NON_ANALYSIS_ROLES,
            "digest_verified": True,
            "size_verified": True,
            "container_path_verified": True,
            "provider_binding": self.provider_binding,
        }


@dataclass(frozen=True)
class PacketInputs:
    carrier_path: Path
    carrier_location: str
    carrier_bytes: bytes
    bundle: Any
    artifacts: tuple[Artifact, ...]
    role_bindings: dict[str, Any]
    documents: dict[str, Any]


# ---------------------------------------------------------------------------
# Strict helpers
# ---------------------------------------------------------------------------


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise BuilderError(message)


def require_equal(actual: Any, expected: Any, *, label: str) -> None:
    if actual != expected:
        raise BuilderError(
            f"{label}_mismatch: expected={expected!r} actual={actual!r}"
        )


def non_empty_string(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise BuilderError(f"{label}_missing_or_invalid: {value!r}")
    return value


def canonical_sha40(value: str, *, label: str) -> str:
    if len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
        raise BuilderError(f"{label}_invalid_sha40: {value!r}")
    return value


def canonical_sha256(value: str, *, label: str) -> str:
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise BuilderError(f"{label}_invalid_sha256: {value!r}")
    return value


def safe_relative_path(value: str) -> bool:
    if not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and not any(
        part in {".", ".."} for part in path.parts
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


def _dedupe_windows_paths(
    values: Iterable[PureWindowsPath],
) -> tuple[PureWindowsPath, ...]:
    result: list[PureWindowsPath] = []
    seen: set[str] = set()
    for value in values:
        key = str(value).rstrip("\\/").casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return tuple(result)


def _windows_system_directory() -> PureWindowsPath:
    if os.name != "nt":
        raise BuilderError("windows_system_directory_unavailable: not_windows")
    try:
        import ctypes

        buffer_size = 32768
        buffer = ctypes.create_unicode_buffer(buffer_size)
        length = ctypes.windll.kernel32.GetSystemWindowsDirectoryW(
            buffer,
            buffer_size,
        )
    except Exception as exc:
        raise BuilderError(
            f"windows_system_directory_unavailable: {exc}"
        ) from exc
    if length <= 0 or length >= buffer_size:
        raise BuilderError(
            "windows_system_directory_unavailable: "
            f"invalid_length={length}"
        )
    directory = PureWindowsPath(buffer.value)
    if not directory.is_absolute() or not directory.drive or not directory.root:
        raise BuilderError(
            "windows_system_directory_invalid: "
            f"{str(directory)!r}"
        )
    return directory


def _windows_registry_program_files_roots() -> tuple[PureWindowsPath, ...]:
    if os.name != "nt":
        return ()
    try:
        import winreg
    except ImportError:
        return ()
    views: list[int] = [winreg.KEY_READ]
    for flag_name in ("KEY_WOW64_64KEY", "KEY_WOW64_32KEY"):
        flag = getattr(winreg, flag_name, 0)
        access = winreg.KEY_READ | flag
        if access not in views:
            views.append(access)
    roots: list[PureWindowsPath] = []
    accepted_types = {winreg.REG_SZ, winreg.REG_EXPAND_SZ}
    for access in views:
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                WINDOWS_CURRENT_VERSION_REGISTRY_KEY,
                0,
                access,
            )
        except OSError:
            continue
        with key:
            for value_name in WINDOWS_PROGRAM_FILES_REGISTRY_VALUES:
                try:
                    raw_value, value_type = winreg.QueryValueEx(key, value_name)
                except OSError:
                    continue
                if value_type not in accepted_types or not isinstance(raw_value, str):
                    continue
                value = raw_value.strip()
                if not value or "%" in value:
                    continue
                candidate = PureWindowsPath(value)
                if candidate.is_absolute() and candidate.drive and candidate.root:
                    roots.append(candidate)
    return _dedupe_windows_paths(roots)


def _windows_trusted_git_executable_candidate_strings(
    *,
    system_windows_directory: str,
    registry_program_files_roots: Iterable[str] = (),
) -> tuple[str, ...]:
    system_directory = PureWindowsPath(system_windows_directory)
    if (
        not system_directory.is_absolute()
        or not system_directory.drive
        or not system_directory.root
    ):
        raise BuilderError(
            "windows_system_directory_invalid: "
            f"{system_windows_directory!r}"
        )
    roots: list[PureWindowsPath] = []
    for value in registry_program_files_roots:
        root = PureWindowsPath(value)
        if root.is_absolute() and root.drive and root.root and "%" not in value:
            roots.append(root)
    system_drive_root = PureWindowsPath(system_directory.anchor)
    roots.extend(
        (
            system_drive_root / "Program Files",
            system_drive_root / "Program Files (x86)",
        )
    )
    candidates: list[PureWindowsPath] = []
    for root in _dedupe_windows_paths(roots):
        candidates.extend(
            root / relative for relative in WINDOWS_GIT_RELATIVE_EXECUTABLES
        )
    return tuple(str(value) for value in _dedupe_windows_paths(candidates))


def _trusted_git_executable_candidates() -> tuple[Path, ...]:
    if os.name != "nt":
        return POSIX_TRUSTED_GIT_EXECUTABLE_CANDIDATES
    system_directory = _windows_system_directory()
    registry_roots = _windows_registry_program_files_roots()
    return tuple(
        Path(value)
        for value in _windows_trusted_git_executable_candidate_strings(
            system_windows_directory=str(system_directory),
            registry_program_files_roots=(str(root) for root in registry_roots),
        )
    )


def _normalized_absolute_path(path: Path) -> Path:
    return Path(os.path.abspath(os.path.normpath(str(path))))


def _validate_trusted_git_executable(candidate: Path) -> Path:
    if not candidate.is_absolute():
        raise BuilderError(
            f"git_executable_untrusted: path_not_absolute: {candidate}"
        )
    normalized = _normalized_absolute_path(candidate)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise BuilderError(
            f"git_executable_untrusted: path_unresolvable: {candidate}: {exc}"
        ) from exc
    if os.path.normcase(str(normalized)) != os.path.normcase(str(resolved)):
        raise BuilderError(
            "git_executable_untrusted: symlink_or_alias_path: "
            f"declared={normalized} resolved={resolved}"
        )
    if candidate.is_symlink() or not resolved.is_file():
        raise BuilderError(
            f"git_executable_untrusted: not_regular_non_symlink_file: {resolved}"
        )
    if not os.access(resolved, os.X_OK):
        raise BuilderError(f"git_executable_untrusted: not_executable: {resolved}")
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
            raise BuilderError(
                f"git_executable_untrusted: component_unavailable: {component}: {exc}"
            ) from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise BuilderError(
                f"git_executable_untrusted: symlink_component: {component}"
            )
        if component == resolved:
            if not stat.S_ISREG(metadata.st_mode):
                raise BuilderError(
                    f"git_executable_untrusted: executable_not_regular: {component}"
                )
        elif not stat.S_ISDIR(metadata.st_mode):
            raise BuilderError(
                f"git_executable_untrusted: parent_not_directory: {component}"
            )
        if os.name != "nt":
            if metadata.st_uid != 0:
                raise BuilderError(
                    "git_executable_untrusted: non_root_owned_component: "
                    f"{component}"
                )
            if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                raise BuilderError(
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
        except BuilderError as exc:
            untrusted.append(str(exc))
    if untrusted:
        raise BuilderError(
            "git_process_executable_untrusted: " + " | ".join(untrusted)
        )
    raise BuilderError(
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
        raise BuilderError(f"git_repository_root_not_directory: {resolved_root}")
    git_executable = _trusted_git_executable()
    completed = subprocess.run(
        [
            str(git_executable),
            "--no-pager",
            "--no-replace-objects",
            "-c",
            f"safe.directory={resolved_root}",
            "-C",
            str(resolved_root),
            *arguments,
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_sanitized_git_environment(git_executable),
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise BuilderError(f"{failure_prefix}: {detail or 'unknown error'}")
    return completed.stdout


def _verified_git_repository_root(repository_root: Path) -> Path:
    resolved_root = repository_root.resolve(strict=True)
    top_level = decode_single_line(
        _run_isolated_git(
            resolved_root,
            arguments=["rev-parse", "--show-toplevel"],
            failure_prefix="git_repository_root_unavailable",
        ),
        label="git_repository_root",
    )
    try:
        discovered = Path(top_level).resolve(strict=True)
    except OSError as exc:
        raise BuilderError(
            f"git_repository_root_unresolvable: {top_level!r}: {exc}"
        ) from exc
    if not discovered.is_dir() or not same_target(discovered, resolved_root):
        raise BuilderError(
            "git_repository_root_mismatch: "
            f"requested={resolved_root} discovered={discovered}"
        )
    return resolved_root


def _git_blob_bytes(
    repository_root: Path,
    *,
    revision: str,
    path: str,
) -> bytes:
    if not safe_relative_path(path):
        raise BuilderError(f"unsafe_source_path: {path!r}")
    resolved_root = _verified_git_repository_root(repository_root)
    return _run_isolated_git(
        resolved_root,
        arguments=["cat-file", "blob", f"{revision}:{path}"],
        failure_prefix=f"git_blob_unavailable: {revision}:{path}",
    )


def current_head(repository_root: Path) -> str:
    revision = decode_single_line(
        _run_isolated_git(
            repository_root,
            arguments=["rev-parse", "HEAD"],
            failure_prefix="repository_head_unavailable",
        ),
        label="repository_head",
    )
    return canonical_sha40(revision, label="repository_head")


def committed_repository_file(
    repository_root: Path,
    *,
    revision: str,
    relative_path: str,
    label: str,
) -> Path:
    if not safe_relative_path(relative_path):
        raise BuilderError(f"{label}_path_unsafe: {relative_path!r}")
    path = repository_root / PurePosixPath(relative_path)
    if not path.is_file():
        raise BuilderError(f"{label}_missing: {path}")
    if path.is_symlink():
        raise BuilderError(f"{label}_symlink_rejected: {path}")
    reject_symlink_components(path, label=label)
    committed = _git_blob_bytes(
        repository_root,
        revision=revision,
        path=relative_path,
    )
    require_equal(path.read_bytes(), committed, label=f"{label}_committed_bytes")
    return path


def reject_symlink_components(path: Path, *, label: str) -> None:
    cursor = path
    while True:
        if cursor.is_symlink():
            raise BuilderError(f"{label}_symlink_rejected: {cursor}")
        if cursor == cursor.parent:
            return
        cursor = cursor.parent


def executed_producer_source_path(
    repository_root: Path,
    *,
    revision: str,
) -> Path:
    canonical_path = committed_repository_file(
        repository_root,
        revision=revision,
        relative_path=PRODUCER_SOURCE_PATH,
        label="producer",
    )

    executed_path = Path(__file__)
    if not executed_path.is_file():
        raise BuilderError(f"executed_producer_missing: {executed_path}")
    if executed_path.is_symlink():
        raise BuilderError(f"executed_producer_symlink_rejected: {executed_path}")
    reject_symlink_components(executed_path, label="executed_producer")

    try:
        executed_resolved = executed_path.resolve(strict=True)
        canonical_resolved = canonical_path.resolve(strict=True)
    except OSError as exc:
        raise BuilderError(f"executed_producer_path_unresolvable: {exc}") from exc

    if os.path.normcase(str(executed_resolved)) != os.path.normcase(
        str(canonical_resolved)
    ):
        raise BuilderError(
            "executed_producer_path_mismatch: "
            f"executed={executed_resolved} canonical={canonical_resolved}"
        )

    committed = _git_blob_bytes(
        repository_root,
        revision=revision,
        path=PRODUCER_SOURCE_PATH,
    )
    require_equal(
        executed_resolved.read_bytes(),
        committed,
        label="executed_producer_committed_bytes",
    )
    return executed_resolved


def load_module(path: Path, module_name: str) -> Any:
    if not path.is_file():
        raise BuilderError(f"module_missing: {path}")
    if path.is_symlink():
        raise BuilderError(f"module_symlink_rejected: {path}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise BuilderError(f"module_import_spec_unavailable: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise BuilderError(f"module_import_failed: {path}: {exc}") from exc
    return module


def decode_single_line(data: bytes, *, label: str) -> str:
    try:
        value = data.decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError as exc:
        raise BuilderError(f"{label}_invalid_utf8: {exc}") from exc
    if not value or "\x00" in value or "\n" in value or "\r" in value:
        raise BuilderError(f"{label}_invalid_output: {value!r}")
    return value


def carrier_location(path: Path, repository_root: Path) -> str:
    resolved = path.resolve(strict=True)
    root = repository_root.resolve(strict=True)
    try:
        relative = resolved.relative_to(root).as_posix()
    except ValueError:
        return resolved.as_uri()
    if not safe_relative_path(relative):
        raise BuilderError(f"carrier_relative_path_unsafe: {relative!r}")
    return relative


def content_identity(path: str) -> tuple[str, str]:
    lower = path.lower()
    if lower.endswith(".zip"):
        return "archive", "application/zip"
    if lower.endswith(".json"):
        return "json", "application/json"
    if lower.endswith(".jsonl") or lower.endswith(".ndjson"):
        return "jsonl", "application/x-ndjson"
    if lower.endswith(".yaml") or lower.endswith(".yml"):
        return "yaml", "application/yaml"
    if lower.endswith(".html") or lower.endswith(".htm"):
        return "html", "text/html"
    if lower.endswith(".md"):
        return "text", "text/markdown"
    return "text", "text/plain"


def slug(value: str) -> str:
    chars: list[str] = []
    dash = False
    for char in value.lower():
        if char.isalnum() or char in "._+":
            chars.append(char)
            dash = False
        elif not dash:
            chars.append("-")
            dash = True
    result = "".join(chars).strip("-")
    if not result:
        raise BuilderError(f"identity_slug_empty: {value!r}")
    return result


# ---------------------------------------------------------------------------
# Carrier extraction and exact artifact graph
# ---------------------------------------------------------------------------


def extract_visible_preservation_files(
    carrier_path: Path,
) -> tuple[bytes, bytes, bytes]:
    try:
        with zipfile.ZipFile(carrier_path, "r") as archive:
            names = [info.filename for info in archive.infolist()]
            if len(names) != len(set(names)):
                raise BuilderError("preservation_archive_duplicate_member")
            expected = (
                OUTER_PREFIX + "PRESERVATION_MANIFEST_v0.json",
                OUTER_PREFIX + "README.md",
                OUTER_PREFIX + "SHA256SUMS",
            )
            for name in expected:
                if name not in names:
                    raise BuilderError(f"preservation_visible_member_missing: {name}")
            return tuple(archive.read(name) for name in expected)  # type: ignore[return-value]
    except zipfile.BadZipFile as exc:
        raise BuilderError(f"preservation_archive_invalid_zip: {exc}") from exc


def load_exact_bundle(
    *,
    carrier_path: Path,
    fixed_builder: Any,
) -> Any:
    if not carrier_path.is_file():
        raise BuilderError(f"carrier_missing: {carrier_path}")
    if carrier_path.is_symlink():
        raise BuilderError(f"carrier_symlink_rejected: {carrier_path}")
    reject_symlink_components(carrier_path, label="carrier")

    require_equal(
        carrier_path.stat().st_size,
        EXPECTED_CARRIER_SIZE,
        label="preservation_archive_size",
    )
    require_equal(
        sha256_file(carrier_path),
        EXPECTED_CARRIER_SHA256,
        label="preservation_archive_sha256",
    )

    manifest_bytes, readme_bytes, sums_bytes = extract_visible_preservation_files(
        carrier_path
    )
    with tempfile.TemporaryDirectory(prefix="pulsemech-subject-input-visible-") as raw:
        temp = Path(raw)
        manifest_path = temp / "PRESERVATION_MANIFEST_v0.json"
        readme_path = temp / "README.md"
        sums_path = temp / "SHA256SUMS"
        manifest_path.write_bytes(manifest_bytes)
        readme_path.write_bytes(readme_bytes)
        sums_path.write_bytes(sums_bytes)
        return fixed_builder.load_observed_bundle(
            archive_path=carrier_path,
            manifest_path=manifest_path,
            readme_path=readme_path,
            sha256sums_path=sums_path,
            expected_archive_sha256=EXPECTED_CARRIER_SHA256,
            expected_archive_size=EXPECTED_CARRIER_SIZE,
        )


def provider_binding(record: Mapping[str, Any]) -> dict[str, Any]:
    artifact_id = record.get("artifact_id")
    artifact_name = non_empty_string(
        record.get("artifact_name"), label="provider_artifact_name"
    )
    require(isinstance(artifact_id, (int, str)), "provider_artifact_id_invalid")
    sha = canonical_sha256(
        non_empty_string(record.get("github_sha256"), label="provider_sha256"),
        label="provider_sha256",
    )
    downloaded_sha = non_empty_string(
        record.get("downloaded_sha256"), label="provider_downloaded_sha256"
    )
    size = record.get("size_bytes")
    downloaded_size = record.get("downloaded_size_bytes")
    require(isinstance(size, int) and size >= 0, "provider_size_invalid")
    require(
        isinstance(downloaded_size, int) and downloaded_size >= 0,
        "provider_downloaded_size_invalid",
    )
    require_equal(downloaded_sha, sha, label="provider_downloaded_sha256")
    require_equal(downloaded_size, size, label="provider_downloaded_size")
    require_equal(record.get("github_digest_match"), True, label="provider_digest")
    require_equal(record.get("github_size_match"), True, label="provider_size")
    return {
        "provider": "github_actions",
        "provider_artifact_id": str(artifact_id),
        "provider_artifact_name": artifact_name,
        "provider_sha256": sha,
        "provider_size_bytes": size,
        "created_utc": non_empty_string(
            record.get("created_at"), label="provider_created_utc"
        ),
        "expires_utc": non_empty_string(
            record.get("expires_at"), label="provider_expires_utc"
        ),
        "downloaded_sha256_matches": True,
        "downloaded_size_matches": True,
    }


def artifact_id(member_path: str, parent: str | None) -> str:
    if parent is None:
        return "artifact:" + member_path
    return parent + "/" + member_path


def display_path(carrier: str, member_path: str, parent_display: str | None) -> str:
    return (carrier if parent_display is None else parent_display) + "!/" + member_path


def make_artifact(
    *,
    carrier: str,
    member_path: str,
    payload: bytes,
    role: str,
    parent_id: str | None = None,
    parent_display: str | None = None,
    provider: dict[str, Any] | None = None,
) -> Artifact:
    kind, media = content_identity(member_path)
    return Artifact(
        artifact_id=artifact_id(member_path, parent_id),
        role=role,
        content_kind=kind,
        media_type=media,
        container_artifact_id=parent_id,
        member_path=member_path,
        display_path_or_uri=display_path(carrier, member_path, parent_display),
        payload=payload,
        provider_binding=provider,
    )


def package_member_role(path: str) -> str:
    exact = ROLE_BY_PACKAGE_MEMBER.get(path)
    if exact is not None:
        return exact
    if path.startswith("artifacts/recorded_release_candidates/") and path.endswith(
        ".json"
    ):
        return "candidate_record"
    return "other"


def parse_documents(
    artifacts: list[Artifact], validator: ValidatorModule
) -> dict[str, Any]:
    documents: dict[str, Any] = {}
    for item in artifacts:
        if item.content_kind == "json":
            documents[item.artifact_id] = validator.load_json_bytes(
                item.payload, label=item.artifact_id
            )
        elif item.content_kind == "jsonl":
            text = item.payload.decode("utf-8", errors="strict")
            for number, line in enumerate(text.splitlines(), start=1):
                if line.strip():
                    validator.load_json_bytes(
                        line.encode("utf-8"),
                        label=f"{item.artifact_id}:line:{number}",
                    )
    return documents


def build_artifacts(
    *,
    carrier: str,
    bundle: Any,
    validator: ValidatorModule,
) -> tuple[tuple[Artifact, ...], dict[str, Any]]:
    manifest = bundle.manifest
    provider_rows = manifest.get("github_artifacts")
    if not isinstance(provider_rows, list):
        raise BuilderError("preservation_manifest_github_artifacts_invalid")
    provider_by_file = {
        non_empty_string(row.get("file_name"), label="provider_file_name"): row
        for row in provider_rows
        if isinstance(row, dict)
    }
    require_equal(len(provider_by_file), 3, label="provider_artifact_count")

    artifacts: list[Artifact] = [
        make_artifact(
            carrier=carrier,
            member_path=OUTER_PREFIX + "PRESERVATION_MANIFEST_v0.json",
            payload=bundle.manifest_bytes,
            role="preservation_manifest",
        ),
        make_artifact(
            carrier=carrier,
            member_path=OUTER_PREFIX + "README.md",
            payload=bundle.readme_bytes,
            role="preservation_readme",
        ),
        make_artifact(
            carrier=carrier,
            member_path=OUTER_PREFIX + "SHA256SUMS",
            payload=bundle.sha256sums_bytes,
            role="preservation_checksums",
        ),
    ]

    outer_by_name: dict[str, Artifact] = {}
    for name in sorted(bundle.artifact_archives):
        payload = bundle.artifact_archives[name]
        row = provider_by_file.get(name)
        if row is None:
            raise BuilderError(f"provider_manifest_row_missing: {name}")
        binding = provider_binding(row)
        require_equal(sha256_bytes(payload), binding["provider_sha256"], label=name)
        require_equal(len(payload), binding["provider_size_bytes"], label=name)
        role = (
            "complete_package"
            if row.get("role") == "complete_release_grade_reference_package"
            else "provider_artifact_archive"
        )
        item = make_artifact(
            carrier=carrier,
            member_path=ORIGINAL_PREFIX + name,
            payload=payload,
            role=role,
            provider=binding,
        )
        artifacts.append(item)
        outer_by_name[name] = item

    package = outer_by_name[COMPLETE_PACKAGE_NAME]
    for path in sorted(bundle.complete_package_members):
        artifacts.append(
            make_artifact(
                carrier=carrier,
                member_path=path,
                payload=bundle.complete_package_members[path],
                role=package_member_role(path),
                parent_id=package.artifact_id,
                parent_display=package.display_path_or_uri,
            )
        )

    completeness = outer_by_name[COMPLETENESS_ARCHIVE_NAME]
    artifacts.append(
        make_artifact(
            carrier=carrier,
            member_path="release_grade_package_completeness_v1.json",
            payload=bundle.completeness_report_bytes,
            role="package_completeness_report",
            parent_id=completeness.artifact_id,
            parent_display=completeness.display_path_or_uri,
        )
    )
    verification = outer_by_name[VERIFICATION_ARCHIVE_NAME]
    artifacts.append(
        make_artifact(
            carrier=carrier,
            member_path="release_grade_reference_package_verification_v0.json",
            payload=bundle.verification_report_bytes,
            role="independent_verification_report",
            parent_id=verification.artifact_id,
            parent_display=verification.display_path_or_uri,
        )
    )

    artifacts.sort(key=lambda item: item.artifact_id)
    require_equal(len(artifacts), 32, label="artifact_count")
    require_equal(
        len({item.artifact_id for item in artifacts}),
        len(artifacts),
        label="artifact_id_uniqueness",
    )
    return tuple(artifacts), parse_documents(artifacts, validator)


def role_bindings(artifacts: tuple[Artifact, ...]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, role in CORE_ROLE_BINDINGS.items():
        matches = sorted(item.artifact_id for item in artifacts if item.role == role)
        if len(matches) != 1:
            raise BuilderError(f"role_singleton_invalid: {name}: {matches}")
        result[name] = matches[0]
    for name, roles in LIST_ROLE_BINDINGS.items():
        matches = sorted(item.artifact_id for item in artifacts if item.role in roles)
        if name == "candidate_records" and not matches:
            raise BuilderError("candidate_records_missing")
        result[name] = matches
    return result


def build_inputs(
    *,
    carrier_path: Path,
    repository_root: Path,
    validator: ValidatorModule,
    fixed_builder: Any,
) -> PacketInputs:
    location = carrier_location(carrier_path, repository_root)
    bundle = load_exact_bundle(carrier_path=carrier_path, fixed_builder=fixed_builder)
    artifacts, documents = build_artifacts(
        carrier=location,
        bundle=bundle,
        validator=validator,
    )
    bindings = role_bindings(artifacts)
    return PacketInputs(
        carrier_path=carrier_path,
        carrier_location=location,
        carrier_bytes=carrier_path.read_bytes(),
        bundle=bundle,
        artifacts=artifacts,
        role_bindings=bindings,
        documents=documents,
    )


def bound_document(inputs: PacketInputs, name: str) -> dict[str, Any]:
    ref = inputs.role_bindings.get(name)
    if not isinstance(ref, str):
        raise BuilderError(f"role_binding_missing: {name}")
    value = inputs.documents.get(ref)
    if not isinstance(value, dict):
        raise BuilderError(f"bound_document_invalid: {name}: {ref}")
    return value


def bound_artifact(inputs: PacketInputs, name: str) -> Artifact:
    ref = inputs.role_bindings.get(name)
    if not isinstance(ref, str):
        raise BuilderError(f"role_binding_missing: {name}")
    for item in inputs.artifacts:
        if item.artifact_id == ref:
            return item
    raise BuilderError(f"bound_artifact_unresolved: {name}: {ref}")


# ---------------------------------------------------------------------------
# Exact subject and source reconstruction
# ---------------------------------------------------------------------------


def parse_workflow_ref(repository: str, value: str) -> tuple[str, str]:
    prefix = repository + "/"
    if not value.startswith(prefix) or "@" not in value:
        raise BuilderError(f"workflow_ref_invalid: {value!r}")
    path, ref = value[len(prefix) :].rsplit("@", 1)
    if not safe_relative_path(path) or not ref:
        raise BuilderError(f"workflow_ref_invalid: {value!r}")
    return path, ref


def recursive_values(value: Any, key: str) -> list[Any]:
    found: list[Any] = []
    if isinstance(value, dict):
        for current_key, current in value.items():
            if current_key == key:
                found.append(current)
            found.extend(recursive_values(current, key))
    elif isinstance(value, list):
        for current in value:
            found.extend(recursive_values(current, key))
    return found


def unique_string(values: list[Any], *, label: str) -> str:
    strings = sorted({value for value in values if isinstance(value, str) and value})
    if len(strings) != 1:
        raise BuilderError(f"{label}_not_unique: {strings}")
    return strings[0]


def git_source(
    *,
    repository_root: Path,
    revision: str,
    source_id: str,
    role: str,
    path: str,
    expected_sha256: str | None,
    extra: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], bytes]:
    if not safe_relative_path(path):
        raise BuilderError(f"source_path_unsafe: {path!r}")
    payload = _git_blob_bytes(
        repository_root,
        revision=revision,
        path=path,
    )
    digest = sha256_bytes(payload)
    if expected_sha256 is not None:
        require_equal(digest, expected_sha256, label=f"source_sha256:{source_id}")
    return (
        {
            "source_id": source_id,
            "role": role,
            "path_or_uri": path,
            "source_revision": revision,
            "sha256": digest,
            "size_bytes": len(payload),
            **dict(extra or {}),
        },
        payload,
    )


def build_subject_and_sources(
    *,
    inputs: PacketInputs,
    repository_root: Path,
    validator: ValidatorModule,
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = inputs.bundle.manifest
    run_metadata = bound_document(inputs, "run_metadata")
    status = bound_document(inputs, "final_status")
    decision_doc = bound_document(inputs, "release_decision")
    authority = bound_document(inputs, "release_authority")
    binding = bound_document(inputs, "artifact_binding")
    candidate_index = bound_document(inputs, "candidate_index")

    repository = unique_string(
        [manifest.get("repository"), run_metadata.get("repository")],
        label="subject_repository",
    )
    require_equal(repository, EXPECTED_REPOSITORY, label="expected_repository")
    workflow_name = unique_string(
        [
            manifest.get("workflow"),
            authority.get("run_identity", {}).get("workflow_name"),
        ],
        label="subject_workflow_name",
    )
    workflow_ref = non_empty_string(
        run_metadata.get("workflow_ref"), label="subject_workflow_ref"
    )
    workflow_path, workflow_source_ref = parse_workflow_ref(
        repository, workflow_ref
    )
    source_ref = unique_string(
        [
            manifest.get("source_ref"),
            workflow_source_ref,
            authority.get("run_identity", {}).get("ref"),
        ],
        label="subject_source_ref",
    )
    source_commit = unique_string(
        [
            manifest.get("source_commit"),
            run_metadata.get("git_sha"),
            status.get("metrics", {}).get("git_sha"),
        ],
        label="subject_source_commit",
    )
    canonical_sha40(source_commit, label="subject_source_commit")
    require_equal(source_commit, EXPECTED_SOURCE_COMMIT, label="expected_commit")

    run_id = manifest.get("workflow_run_id")
    run_number = manifest.get("workflow_run_number")
    run_attempt = manifest.get("workflow_run_attempt")
    require(isinstance(run_id, int) and run_id > 0, "run_id_invalid")
    require(isinstance(run_number, int) and run_number > 0, "run_number_invalid")
    require(isinstance(run_attempt, int) and run_attempt > 0, "run_attempt_invalid")
    require_equal(run_metadata.get("run_id"), run_id, label="run_metadata_id")
    require_equal(
        run_metadata.get("run_attempt"), run_attempt, label="run_metadata_attempt"
    )

    run_key = unique_string(
        [
            run_metadata.get("run_key"),
            status.get("metrics", {}).get("run_key"),
        ],
        label="subject_run_key",
    )
    canonical_run_key = (
        f"GITHUB_RUN_ID={run_id}|GITHUB_RUN_ATTEMPT={run_attempt}|"
        f"GITHUB_WORKFLOW={workflow_name}"
    )
    require_equal(run_key, canonical_run_key, label="canonical_run_key")
    require_equal(run_key, EXPECTED_RUN_KEY, label="expected_run_key")

    release_candidate = non_empty_string(
        run_metadata.get("release_candidate"), label="release_candidate"
    )
    run_mode = unique_string(
        [manifest.get("run_mode"), status.get("metrics", {}).get("run_mode")],
        label="run_mode",
    )
    event_name = non_empty_string(
        authority.get("run_identity", {}).get("event_name"),
        label="event_name",
    )
    active_sets = manifest.get("active_policy_sets")
    require(isinstance(active_sets, list) and bool(active_sets), "policy_sets_invalid")
    require_equal(
        decision_doc.get("active_gate_sets"),
        active_sets,
        label="decision_policy_sets",
    )
    gate_set = binding.get("authority_carrier", {}).get(
        "workflow_effective_required_gate_set", {}
    )
    require_equal(gate_set.get("policy_sets"), active_sets, label="binding_policy_sets")

    status_metrics = status.get("metrics")
    if not isinstance(status_metrics, dict):
        raise BuilderError("status_metrics_invalid")
    policy_path = non_empty_string(
        status_metrics.get("gate_policy_path"), label="policy_path"
    )
    policy_sha = canonical_sha256(
        non_empty_string(status_metrics.get("gate_policy_sha256"), label="policy_sha"),
        label="policy_sha",
    )
    registry_path = non_empty_string(
        status_metrics.get("gate_registry_path"), label="registry_path"
    )
    registry_sha = canonical_sha256(
        non_empty_string(
            status_metrics.get("gate_registry_sha256"), label="registry_sha"
        ),
        label="registry_sha",
    )

    attestation_ids = inputs.role_bindings["attestation_records"]
    attestation_docs = [inputs.documents.get(ref) for ref in attestation_ids]
    workflow_sha = unique_string(
        [
            value
            for document in attestation_docs
            for value in recursive_values(document, "workflow_sha256")
        ],
        label="workflow_sha",
    )
    signer_path = unique_string(
        [
            value
            for document in attestation_docs
            for value in recursive_values(document, "policy_path")
            if value == "policy/external_signers_v1.yml"
        ],
        label="signer_policy_path",
    )
    signer_sha = unique_string(
        [
            value
            for document in attestation_docs
            for value in recursive_values(document, "signer_policy_sha256")
        ],
        label="signer_policy_sha",
    )
    threshold_binding = candidate_index.get("source_bindings", {}).get(
        "external_thresholds", {}
    )
    threshold_path = non_empty_string(
        threshold_binding.get("path"), label="threshold_path"
    )
    threshold_sha = unique_string(
        [
            threshold_binding.get("sha256"),
            *[
                value
                for document in attestation_docs
                for value in recursive_values(document, "threshold_policy_sha256")
            ],
        ],
        label="threshold_sha",
    )

    workflow_record, workflow_bytes = git_source(
        repository_root=repository_root,
        revision=source_commit,
        source_id="source:workflow:pulse-ci",
        role="workflow",
        path=workflow_path,
        expected_sha256=workflow_sha,
        extra={"workflow_name": workflow_name, "workflow_ref": workflow_ref},
    )
    workflow_yaml = validator.load_yaml_bytes(workflow_bytes, label="workflow")
    require(
        isinstance(workflow_yaml, dict),
        "historical_workflow_not_object",
    )
    require_equal(workflow_yaml.get("name"), workflow_name, label="workflow_name")

    policy_record, policy_bytes = git_source(
        repository_root=repository_root,
        revision=source_commit,
        source_id="source:policy:pulse-gate-policy-v0",
        role="policy",
        path=policy_path,
        expected_sha256=policy_sha,
    )
    policy_yaml = validator.load_yaml_bytes(policy_bytes, label="policy")
    policy_data = policy_yaml.get("policy") if isinstance(policy_yaml, dict) else None
    if not isinstance(policy_data, dict):
        raise BuilderError("historical_policy_not_object")
    policy_id = non_empty_string(policy_data.get("id"), label="policy_id")
    policy_record["policy_id"] = policy_id

    registry_record, registry_bytes = git_source(
        repository_root=repository_root,
        revision=source_commit,
        source_id="source:registry:gate-registry-v0",
        role="gate_registry",
        path=registry_path,
        expected_sha256=registry_sha,
    )
    registry_yaml = validator.load_yaml_bytes(registry_bytes, label="registry")
    if not isinstance(registry_yaml, dict):
        raise BuilderError("historical_registry_not_object")
    registry_record["registry_id"] = non_empty_string(
        registry_yaml.get("version"), label="registry_id"
    )

    signer_record, _ = git_source(
        repository_root=repository_root,
        revision=source_commit,
        source_id="source:policy:external-signers-v1",
        role="external_signer_policy",
        path=signer_path,
        expected_sha256=signer_sha,
    )
    threshold_record, _ = git_source(
        repository_root=repository_root,
        revision=source_commit,
        source_id="source:policy:external-thresholds",
        role="threshold_policy",
        path=threshold_path,
        expected_sha256=threshold_sha,
    )

    decision = validator._decision_document_value(decision_doc)
    if decision not in {"ALLOW", "BLOCK"}:
        raise BuilderError("release_decision_unclassifiable")
    require_equal(
        manifest.get("primary_gate_result"),
        "allow" if decision == "ALLOW" else "block",
        label="manifest_primary_gate_result",
    )
    final_status = bound_artifact(inputs, "final_status")
    release_decision = bound_artifact(inputs, "release_decision")

    subject = {
        "repository": repository,
        "workflow_name": workflow_name,
        "workflow_path": workflow_path,
        "workflow_ref": workflow_ref,
        "workflow_run_id": run_id,
        "workflow_run_number": run_number,
        "workflow_run_attempt": run_attempt,
        "subject_run_key": run_key,
        "source_commit": source_commit,
        "source_ref": source_ref,
        "event_name": event_name,
        "release_candidate_id": release_candidate,
        "run_mode": run_mode,
        "active_policy_sets": active_sets,
        "policy_id": policy_id,
        "policy_sha256": policy_record["sha256"],
        "materialized_gate_set_sha256": gate_set.get("sha256"),
        "final_status_sha256": sha256_bytes(final_status.payload),
        "release_decision_sha256": sha256_bytes(release_decision.payload),
        "decision": decision,
    }
    sources = {
        "workflow": workflow_record,
        "policy": policy_record,
        "gate_registry": registry_record,
        "additional_sources": sorted(
            [signer_record, threshold_record], key=lambda row: row["source_id"]
        ),
    }
    return subject, sources


def producer_identity(
    *,
    repository_root: Path,
    revision: str,
    source_path: Path,
    execution_identity: str,
    producer_run_key: str,
) -> dict[str, Any]:
    execution_identity = non_empty_string(
        execution_identity, label="producer_execution_identity"
    )
    producer_run_key = non_empty_string(producer_run_key, label="producer_run_key")
    canonical_sha40(revision, label="producer_revision")
    try:
        relative = source_path.resolve(strict=True).relative_to(
            repository_root
        ).as_posix()
    except ValueError as exc:
        raise BuilderError(f"producer_source_outside_repository: {source_path}") from exc
    require_equal(relative, PRODUCER_SOURCE_PATH, label="producer_source_path")
    committed = _git_blob_bytes(
        repository_root,
        revision=revision,
        path=relative,
    )
    require_equal(source_path.read_bytes(), committed, label="producer_source_bytes")
    return {
        "producer_id": "pulsemech_compute_subject_input_packet_producer_v0",
        "producer_name": TOOL_NAME,
        "producer_version": TOOL_VERSION,
        "producer_source": relative,
        "producer_source_revision": revision,
        "producer_source_sha256": sha256_bytes(committed),
        "ci_workflow_or_job_identity": execution_identity,
        "producer_run_key": producer_run_key,
        "production_mode": PRODUCTION_MODE,
    }


# ---------------------------------------------------------------------------
# Packet construction, validation, and output
# ---------------------------------------------------------------------------


def coverage(inputs: PacketInputs, sources: dict[str, Any]) -> dict[str, Any]:
    records = [item.record() for item in inputs.artifacts]
    artifact_ids = {row["artifact_id"] for row in records}
    provider_rows = [row for row in records if row["provider_binding"] is not None]
    role_total = 0
    role_resolved = 0
    missing: list[str] = []
    unresolved: set[str] = set()
    for name in CORE_ROLE_BINDINGS:
        ref = inputs.role_bindings.get(name)
        if not isinstance(ref, str):
            missing.append(name)
            continue
        role_total += 1
        if ref in artifact_ids:
            role_resolved += 1
        else:
            unresolved.add(ref)
    for name in LIST_ROLE_BINDINGS:
        refs = inputs.role_bindings.get(name)
        if not isinstance(refs, list):
            missing.append(name)
            continue
        if name == "candidate_records" and not refs:
            missing.append(name)
        role_total += len(refs)
        for ref in refs:
            if ref in artifact_ids:
                role_resolved += 1
            else:
                unresolved.add(ref)
    source_rows = [
        sources["workflow"],
        sources["policy"],
        sources["gate_registry"],
        *sources["additional_sources"],
    ]
    source_complete = all(
        isinstance(row.get("source_revision"), str)
        and isinstance(row.get("sha256"), str)
        and isinstance(row.get("size_bytes"), int)
        for row in source_rows
    )
    provider_bound = sum(
        1
        for row in provider_rows
        if row["provider_binding"]["downloaded_sha256_matches"] is True
        and row["provider_binding"]["downloaded_size_matches"] is True
    )
    roles_complete = not missing and not unresolved and role_total == role_resolved
    complete = source_complete and roles_complete and provider_bound == len(provider_rows)
    return {
        "coverage_status": "complete" if complete else "partial",
        "source_bindings_complete": source_complete,
        "carrier_binding_complete": True,
        "artifact_graph_complete": True,
        "role_bindings_complete": roles_complete,
        "artifacts_total": len(records),
        "provider_artifacts_total": len(provider_rows),
        "provider_artifacts_bound": provider_bound,
        "role_bindings_total": role_total,
        "role_bindings_resolved": role_resolved,
        "missing_roles": sorted(set(missing)),
        "unresolved_artifact_ids": sorted(unresolved),
    }


def build_packet(
    *,
    inputs: PacketInputs,
    subject: dict[str, Any],
    sources: dict[str, Any],
    producer: dict[str, Any],
    packet_created_utc: str,
) -> dict[str, Any]:
    workflow_slug = slug(subject["workflow_name"])
    identity_material = (
        producer["producer_run_key"]
        + "\x00"
        + packet_created_utc
        + "\x00"
        + sha256_bytes(inputs.carrier_bytes)
    ).encode("utf-8")
    identity_digest = sha256_bytes(identity_material)[:16]
    carrier_id = (
        f"carrier:preservation/{workflow_slug}-{subject['workflow_run_number']}/v0"
    )
    packet_id = (
        f"subject-input:{workflow_slug}-{subject['workflow_run_number']}/"
        f"fixed-source-adapter/{identity_digest}/v0"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "packet_type": PACKET_TYPE,
        "record_status": "observed",
        "producer": producer,
        "packet_identity": {
            "packet_id": packet_id,
            "packet_scope": PACKET_SCOPE,
            "packet_created_utc": packet_created_utc,
            "subject_run_key": subject["subject_run_key"],
            "carrier_id": carrier_id,
            "canonicalization": "json-sort-keys-utf8-newline",
        },
        "subject": subject,
        "analysis_boundary": {
            "target_analysis_level": "artifact_observed",
            "runtime_observation_included": False,
            "runtime_observation_required_for_runtime_classification": True,
            "observer_in_subject_totals": False,
            "current_repository_state_substitution_allowed": False,
            "packet_is_compute_report": False,
            "packet_is_runtime_observation": False,
        },
        "authority_sources": sources,
        "carrier": {
            "carrier_id": carrier_id,
            "carrier_kind": "preservation_archive",
            "path_or_uri": inputs.carrier_location,
            "media_type": "application/zip",
            "sha256": sha256_bytes(inputs.carrier_bytes),
            "size_bytes": len(inputs.carrier_bytes),
            "root_prefix": OUTER_PREFIX.rstrip("/"),
            "immutable": True,
            "artifact_payload_mode": "external_carrier",
            "provider_binding": None,
        },
        "artifacts": [item.record() for item in inputs.artifacts],
        "role_bindings": inputs.role_bindings,
        "coverage": coverage(inputs, sources),
        "content_boundary": {
            "packet_payload_mode": "metadata_only",
            "artifact_bytes_embedded": False,
            "carrier_required_for_verification": True,
            "raw_secrets_included": False,
            "raw_model_inputs_included": False,
            "raw_model_outputs_included": False,
        },
        "authority_boundary": {
            "write_mode": "subject_input_only",
            "writes_subject_run": False,
            "writes_target_repository": False,
            "mutates_carrier": False,
            "changes_release_authority": False,
            "changes_gate_policy": False,
            "changes_gate_semantics": False,
            "creates_release_decision": False,
            "creates_gate_result": False,
            "activates_compute_gate": False,
            "creates_compute_budget": False,
            "packet_is_release_authority": False,
        },
        "errors": [],
        "ok": True,
    }


def validate_generated_packet(
    *,
    packet: dict[str, Any],
    rendered: str,
    carrier_path: Path,
    schema_path: Path,
    repository_root: Path,
    validator: ValidatorModule,
) -> None:
    schema = validator.load_json_bytes(schema_path.read_bytes(), label="schema")
    if not isinstance(schema, dict):
        raise BuilderError("schema_not_object")
    errors = validator.schema_errors(schema, packet)
    if errors:
        raise BuilderError("generated_packet_schema_invalid: " + " | ".join(errors))
    with tempfile.TemporaryDirectory(prefix="pulsemech-subject-input-check-") as raw:
        packet_path = Path(raw) / "generated.json"
        packet_path.write_bytes(rendered.encode("utf-8"))
        diagnostic, return_code, _carrier, _snapshots = validator.build_diagnostic(
            schema_path=schema_path,
            packet_path=packet_path,
            explicit_carrier=carrier_path,
            repository_root=repository_root,
        )
        if return_code != 0 or diagnostic.get("ok") is not True:
            raise BuilderError(
                "generated_packet_rejected: "
                + json.dumps(diagnostic, sort_keys=True, ensure_ascii=False)
            )


def reject_output(
    *,
    output: Path | None,
    packet: dict[str, Any],
    carrier_path: Path,
    schema_path: Path,
    validator_path: Path,
    fixed_builder_path: Path,
    repository_root: Path,
    validator: ValidatorModule,
) -> None:
    if output is None:
        return
    reject_symlink_components(output, label="output")
    if output.name in PROTECTED_OUTPUT_NAMES:
        raise BuilderError(f"refusing_authority_surface_output: {output.name}")
    try:
        output.resolve().relative_to(repository_root.resolve(strict=True))
    except (OSError, ValueError):
        pass
    else:
        raise BuilderError(f"refusing_output_inside_repository: {output}")
    protected = [
        Path(__file__),
        carrier_path,
        schema_path,
        validator_path,
        fixed_builder_path,
        _trusted_git_executable(),
    ]
    for source in (
        packet["authority_sources"]["workflow"],
        packet["authority_sources"]["policy"],
        packet["authority_sources"]["gate_registry"],
        *packet["authority_sources"]["additional_sources"],
    ):
        source_path = source.get("path_or_uri")
        if isinstance(source_path, str) and safe_relative_path(source_path):
            protected.append(repository_root / PurePosixPath(source_path))
    for path in protected:
        if same_target(output, path):
            raise BuilderError(f"refusing_to_overwrite_input: {path}")


def atomic_write(path: Path, text: str) -> None:
    if not path.parent.is_dir():
        raise BuilderError(f"output_parent_missing_or_not_directory: {path.parent}")
    reject_symlink_components(path, label="output")
    fd, raw_temp = tempfile.mkstemp(
        prefix="." + path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )
    temp = Path(raw_temp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Produce an observed PULSEmech compute subject-input packet from "
            "the exact preserved PULSE CI #6066 carrier."
        )
    )
    parser.add_argument("--carrier", default=str(DEFAULT_CARRIER))
    parser.add_argument("--repository-root", default=str(ROOT))
    parser.add_argument("--packet-created-utc", required=True)
    parser.add_argument("--producer-run-key", required=True)
    parser.add_argument("--ci-workflow-or-job-identity", required=True)
    parser.add_argument("--output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    carrier_path = Path(args.carrier)
    repository_root = Path(args.repository_root)
    output = Path(args.output) if args.output else None

    try:
        repository_root = _verified_git_repository_root(repository_root)
        revision = current_head(repository_root)
        producer_path = executed_producer_source_path(
            repository_root,
            revision=revision,
        )
        schema_path = committed_repository_file(
            repository_root,
            revision=revision,
            relative_path=SCHEMA_SOURCE_PATH,
            label="schema",
        )
        validator_path = committed_repository_file(
            repository_root,
            revision=revision,
            relative_path=VALIDATOR_SOURCE_PATH,
            label="validator",
        )
        fixed_builder_path = committed_repository_file(
            repository_root,
            revision=revision,
            relative_path=FIXED_SOURCE_BUILDER_PATH,
            label="fixed_source_builder",
        )
        if not carrier_path.is_file():
            raise BuilderError(f"carrier_missing: {carrier_path}")
        if carrier_path.is_symlink():
            raise BuilderError(f"carrier_symlink_rejected: {carrier_path}")
        reject_symlink_components(carrier_path, label="carrier")

        protected_before = {
            "carrier": sha256_file(carrier_path),
            "schema": sha256_file(schema_path),
            "validator": sha256_file(validator_path),
            "fixed_builder": sha256_file(fixed_builder_path),
            "producer": sha256_file(producer_path),
        }
        validator: ValidatorModule = load_module(
            validator_path,
            "pulsemech_subject_input_validator_for_producer",
        )
        fixed_builder = load_module(
            fixed_builder_path,
            "pulsemech_fixed_compute_builder_for_subject_input",
        )
        require_equal(
            validator._trusted_git_executable(),
            _trusted_git_executable(),
            label="validator_trusted_git_executable",
        )
        require_equal(
            validator._verified_git_repository_root(repository_root),
            repository_root,
            label="validator_repository_root",
        )

        packet_created_utc = non_empty_string(
            args.packet_created_utc, label="packet_created_utc"
        )
        validator.parse_utc(packet_created_utc)
        if not packet_created_utc.endswith("Z"):
            raise BuilderError("packet_created_utc_not_canonical_z")

        inputs = build_inputs(
            carrier_path=carrier_path,
            repository_root=repository_root,
            validator=validator,
            fixed_builder=fixed_builder,
        )
        subject, sources = build_subject_and_sources(
            inputs=inputs,
            repository_root=repository_root,
            validator=validator,
        )
        producer = producer_identity(
            repository_root=repository_root,
            revision=revision,
            source_path=producer_path,
            execution_identity=args.ci_workflow_or_job_identity,
            producer_run_key=args.producer_run_key,
        )
        packet = build_packet(
            inputs=inputs,
            subject=subject,
            sources=sources,
            producer=producer,
            packet_created_utc=packet_created_utc,
        )
        rendered = render_json(packet)
        validate_generated_packet(
            packet=packet,
            rendered=rendered,
            carrier_path=carrier_path,
            schema_path=schema_path,
            repository_root=repository_root,
            validator=validator,
        )
        reject_output(
            output=output,
            packet=packet,
            carrier_path=carrier_path,
            schema_path=schema_path,
            validator_path=validator_path,
            fixed_builder_path=fixed_builder_path,
            repository_root=repository_root,
            validator=validator,
        )
        protected_after = {
            "carrier": sha256_file(carrier_path),
            "schema": sha256_file(schema_path),
            "validator": sha256_file(validator_path),
            "fixed_builder": sha256_file(fixed_builder_path),
            "producer": sha256_file(producer_path),
        }
        require_equal(
            protected_after,
            protected_before,
            label="protected_inputs_after_build",
        )
        if output is not None:
            atomic_write(output, rendered)
        sys.stdout.write(rendered)
        return 0
    except BuilderError as exc:
        sys.stderr.write(
            render_json({"tool": TOOL_ID, "ok": False, "errors": [str(exc)]})
        )
        return 1
    except Exception as exc:
        sys.stderr.write(
            render_json(
                {
                    "tool": TOOL_ID,
                    "ok": False,
                    "errors": [f"unexpected_error: {exc}"],
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

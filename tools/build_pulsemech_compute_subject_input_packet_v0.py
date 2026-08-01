#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
import types
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable


TOOL_ID = "build_pulsemech_compute_subject_input_packet_v0"
WRAPPER_SOURCE_PATH = "tools/build_pulsemech_compute_subject_input_packet_v0.py"
PRODUCER_CORE_SOURCE_PATH = (
    "tools/pulsemech_compute_subject_input_packet_producer_core_v0.py"
)
PRODUCER_CORE_MODULE = "pulsemech_compute_subject_input_packet_producer_core_v0"

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


class CompatibilityWrapperError(RuntimeError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def render_diagnostic(error: Exception) -> str:
    return (
        json.dumps(
            {"tool": TOOL_ID, "ok": False, "errors": [str(error)]},
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    )


def _normalized_absolute_path(path: Path) -> Path:
    return Path(os.path.abspath(os.path.normpath(os.fspath(path))))


def _stat_identity(value: os.stat_result) -> tuple[Any, ...]:
    return tuple(
        getattr(value, name, None)
        for name in ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns")
    )


def _reject_symlink_components(path: Path, *, label: str) -> None:
    cursor = _normalized_absolute_path(path)
    while True:
        try:
            metadata = cursor.lstat()
        except OSError as exc:
            raise CompatibilityWrapperError(
                f"{label}_component_unavailable: {cursor}: {exc}"
            ) from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise CompatibilityWrapperError(
                f"{label}_symlink_or_alias_rejected: {cursor}"
            )
        if cursor == cursor.parent:
            return
        cursor = cursor.parent


def _read_regular_file_snapshot(path: Path, *, label: str) -> bytes:
    candidate = _normalized_absolute_path(path)
    _reject_symlink_components(candidate, label=label)
    try:
        before = candidate.lstat()
    except OSError as exc:
        raise CompatibilityWrapperError(
            f"{label}_unavailable: {candidate}: {exc}"
        ) from exc
    if not stat.S_ISREG(before.st_mode):
        raise CompatibilityWrapperError(
            f"{label}_not_regular_file: {candidate}"
        )

    flags = os.O_RDONLY
    for name in ("O_CLOEXEC", "O_BINARY", "O_NOFOLLOW"):
        flags |= int(getattr(os, name, 0))
    try:
        descriptor = os.open(candidate, flags)
    except OSError as exc:
        raise CompatibilityWrapperError(
            f"{label}_open_failed: {candidate}: {exc}"
        ) from exc

    try:
        opened_before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened_before.st_mode)
            or _stat_identity(before) != _stat_identity(opened_before)
        ):
            raise CompatibilityWrapperError(
                f"{label}_changed_before_read: {candidate}"
            )
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        opened_after = os.fstat(descriptor)
        if _stat_identity(opened_before) != _stat_identity(opened_after):
            raise CompatibilityWrapperError(
                f"{label}_changed_during_read: {candidate}"
            )
    finally:
        os.close(descriptor)

    try:
        after = candidate.lstat()
    except OSError as exc:
        raise CompatibilityWrapperError(
            f"{label}_unavailable_after_read: {candidate}: {exc}"
        ) from exc
    if _stat_identity(before) != _stat_identity(after):
        raise CompatibilityWrapperError(
            f"{label}_path_changed_during_read: {candidate}"
        )

    payload = b"".join(chunks)
    if len(payload) != before.st_size:
        raise CompatibilityWrapperError(
            f"{label}_size_changed_during_read: "
            f"expected={before.st_size} actual={len(payload)}"
        )
    return payload


def _executed_wrapper_and_root() -> tuple[Path, Path]:
    executed = _normalized_absolute_path(Path(__file__))
    _reject_symlink_components(executed, label="executed_wrapper")
    if not executed.is_file():
        raise CompatibilityWrapperError(
            f"executed_wrapper_not_regular_file: {executed}"
        )
    if len(executed.parents) < 2:
        raise CompatibilityWrapperError(
            f"executed_wrapper_repository_layout_invalid: {executed}"
        )

    root = executed.parents[1]
    expected = _normalized_absolute_path(
        root / PurePosixPath(WRAPPER_SOURCE_PATH)
    )
    if os.path.normcase(str(executed)) != os.path.normcase(str(expected)):
        raise CompatibilityWrapperError(
            "executed_wrapper_path_mismatch: "
            f"executed={executed} expected={expected}"
        )
    if not root.is_dir():
        raise CompatibilityWrapperError(
            f"wrapper_repository_root_not_directory: {root}"
        )
    return executed, root


def _dedupe_windows_paths(
    values: Iterable[PureWindowsPath],
) -> tuple[PureWindowsPath, ...]:
    result: list[PureWindowsPath] = []
    seen: set[str] = set()
    for value in values:
        key = str(value).rstrip("\\/").casefold()
        if key not in seen:
            seen.add(key)
            result.append(value)
    return tuple(result)


def _windows_system_directory() -> PureWindowsPath:
    if os.name != "nt":
        raise CompatibilityWrapperError(
            "windows_system_directory_unavailable: not_windows"
        )
    try:
        import ctypes

        buffer = ctypes.create_unicode_buffer(32768)
        length = ctypes.windll.kernel32.GetSystemWindowsDirectoryW(
            buffer,
            len(buffer),
        )
    except Exception as exc:
        raise CompatibilityWrapperError(
            f"windows_system_directory_unavailable: {exc}"
        ) from exc
    if length <= 0 or length >= len(buffer):
        raise CompatibilityWrapperError(
            f"windows_system_directory_unavailable: invalid_length={length}"
        )
    directory = PureWindowsPath(buffer.value)
    if not directory.is_absolute() or not directory.drive or not directory.root:
        raise CompatibilityWrapperError(
            f"windows_system_directory_invalid: {str(directory)!r}"
        )
    return directory


def _windows_registry_program_files_roots() -> tuple[PureWindowsPath, ...]:
    if os.name != "nt":
        return ()
    try:
        import winreg
    except ImportError:
        return ()

    views = [winreg.KEY_READ]
    for flag_name in ("KEY_WOW64_64KEY", "KEY_WOW64_32KEY"):
        access = winreg.KEY_READ | getattr(winreg, flag_name, 0)
        if access not in views:
            views.append(access)

    roots: list[PureWindowsPath] = []
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
                    raw, kind = winreg.QueryValueEx(key, value_name)
                except OSError:
                    continue
                if (
                    kind not in {winreg.REG_SZ, winreg.REG_EXPAND_SZ}
                    or not isinstance(raw, str)
                    or not raw.strip()
                    or "%" in raw
                ):
                    continue
                candidate = PureWindowsPath(raw.strip())
                if candidate.is_absolute() and candidate.drive and candidate.root:
                    roots.append(candidate)
    return _dedupe_windows_paths(roots)


def _windows_git_candidate_strings(
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
        raise CompatibilityWrapperError(
            f"windows_system_directory_invalid: {system_windows_directory!r}"
        )

    roots = [
        PureWindowsPath(value)
        for value in registry_program_files_roots
        if PureWindowsPath(value).is_absolute() and "%" not in value
    ]
    drive_root = PureWindowsPath(system_directory.anchor)
    roots.extend(
        (
            drive_root / "Program Files",
            drive_root / "Program Files (x86)",
        )
    )
    return tuple(
        str(root / relative)
        for root in _dedupe_windows_paths(roots)
        for relative in WINDOWS_GIT_RELATIVE_EXECUTABLES
    )


def _trusted_git_candidates() -> tuple[Path, ...]:
    if os.name != "nt":
        return POSIX_TRUSTED_GIT_EXECUTABLE_CANDIDATES
    return tuple(
        Path(value)
        for value in _windows_git_candidate_strings(
            system_windows_directory=str(_windows_system_directory()),
            registry_program_files_roots=(
                str(root) for root in _windows_registry_program_files_roots()
            ),
        )
    )


def _validate_trusted_git(candidate: Path) -> Path:
    if not candidate.is_absolute():
        raise CompatibilityWrapperError(
            f"git_executable_untrusted: path_not_absolute: {candidate}"
        )
    normalized = _normalized_absolute_path(candidate)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise CompatibilityWrapperError(
            f"git_executable_untrusted: path_unresolvable: {candidate}: {exc}"
        ) from exc
    if os.path.normcase(str(normalized)) != os.path.normcase(str(resolved)):
        raise CompatibilityWrapperError(
            "git_executable_untrusted: symlink_or_alias_path: "
            f"declared={normalized} resolved={resolved}"
        )
    if candidate.is_symlink() or not resolved.is_file():
        raise CompatibilityWrapperError(
            f"git_executable_untrusted: not_regular_file: {resolved}"
        )
    if not os.access(resolved, os.X_OK):
        raise CompatibilityWrapperError(
            f"git_executable_untrusted: not_executable: {resolved}"
        )

    cursor = resolved
    while True:
        try:
            metadata = cursor.lstat()
        except OSError as exc:
            raise CompatibilityWrapperError(
                "git_executable_untrusted: component_unavailable: "
                f"{cursor}: {exc}"
            ) from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise CompatibilityWrapperError(
                f"git_executable_untrusted: symlink_component: {cursor}"
            )
        if os.name != "nt" and metadata.st_mode & (
            stat.S_IWGRP | stat.S_IWOTH
        ):
            raise CompatibilityWrapperError(
                f"git_executable_untrusted: writable_component: {cursor}"
            )
        if cursor == cursor.parent:
            break
        cursor = cursor.parent

    approved = {
        os.path.normcase(str(_normalized_absolute_path(path)))
        for path in _trusted_git_candidates()
    }
    if os.path.normcase(str(resolved)) not in approved:
        raise CompatibilityWrapperError(
            f"git_executable_untrusted: unapproved_candidate: {resolved}"
        )
    return resolved


def _trusted_git() -> Path:
    missing: list[str] = []
    rejected: list[str] = []
    for candidate in _trusted_git_candidates():
        if not candidate.exists():
            missing.append(str(candidate))
            continue
        try:
            return _validate_trusted_git(candidate)
        except CompatibilityWrapperError as exc:
            rejected.append(str(exc))
    if rejected:
        raise CompatibilityWrapperError(
            "git_process_executable_untrusted: " + " | ".join(rejected)
        )
    raise CompatibilityWrapperError(
        "git_process_executable_unavailable: "
        + (", ".join(missing) if missing else "no trusted candidates")
    )


def _git_environment(git_executable: Path) -> dict[str, str]:
    environment = {
        key: value
        for key in GIT_PROCESS_ENV_ALLOWLIST
        if (value := os.environ.get(key)) is not None
    }
    environment.update(
        {
            "PATH": str(git_executable.parent),
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
    return environment


def _run_git(
    root: Path,
    git_executable: Path,
    arguments: list[str],
    *,
    failure_prefix: str,
) -> bytes:
    completed = subprocess.run(
        [
            str(git_executable),
            "--no-pager",
            "--no-replace-objects",
            "-c",
            f"safe.directory={root}",
            "-C",
            str(root),
            *arguments,
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_git_environment(git_executable),
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise CompatibilityWrapperError(
            f"{failure_prefix}: {detail or 'unknown error'}"
        )
    return completed.stdout


def _single_line(value: bytes, *, label: str) -> str:
    try:
        decoded = value.decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError as exc:
        raise CompatibilityWrapperError(
            f"{label}_invalid_utf8: {exc}"
        ) from exc
    if not decoded or any(character in decoded for character in "\x00\n\r"):
        raise CompatibilityWrapperError(
            f"{label}_invalid_output: {decoded!r}"
        )
    return decoded


def _verified_head(root: Path, git_executable: Path) -> str:
    top_level_text = _single_line(
        _run_git(
            root,
            git_executable,
            ["rev-parse", "--show-toplevel"],
            failure_prefix="git_repository_root_unavailable",
        ),
        label="git_repository_root",
    )
    try:
        top_level = Path(top_level_text).resolve(strict=True)
        expected = root.resolve(strict=True)
        same_root = os.path.samefile(top_level, expected)
    except OSError as exc:
        raise CompatibilityWrapperError(
            f"git_repository_root_unresolvable: {exc}"
        ) from exc
    if not same_root:
        raise CompatibilityWrapperError(
            "git_repository_root_mismatch: "
            f"expected={expected} discovered={top_level}"
        )

    revision = _single_line(
        _run_git(
            root,
            git_executable,
            ["rev-parse", "HEAD"],
            failure_prefix="repository_head_unavailable",
        ),
        label="repository_head",
    )
    if len(revision) != 40 or any(
        character not in "0123456789abcdef" for character in revision
    ):
        raise CompatibilityWrapperError(
            f"repository_head_invalid_sha40: {revision!r}"
        )
    return revision


def _git_blob(
    root: Path,
    git_executable: Path,
    revision: str,
    relative_path: str,
) -> bytes:
    return _run_git(
        root,
        git_executable,
        ["cat-file", "blob", f"{revision}:{relative_path}"],
        failure_prefix=f"git_blob_unavailable: {revision}:{relative_path}",
    )


def _load_verified_producer_core() -> tuple[Any, str]:
    executed_wrapper, root = _executed_wrapper_and_root()
    git_executable = _trusted_git()
    revision = _verified_head(root, git_executable)

    wrapper_source = _read_regular_file_snapshot(
        executed_wrapper,
        label="executed_wrapper",
    )
    if wrapper_source != _git_blob(
        root,
        git_executable,
        revision,
        WRAPPER_SOURCE_PATH,
    ):
        raise CompatibilityWrapperError(
            "executed_wrapper_committed_bytes_mismatch"
        )

    producer_core = _normalized_absolute_path(
        root / PurePosixPath(PRODUCER_CORE_SOURCE_PATH)
    )
    source = _read_regular_file_snapshot(
        producer_core,
        label="producer_core",
    )
    if source != _git_blob(
        root,
        git_executable,
        revision,
        PRODUCER_CORE_SOURCE_PATH,
    ):
        raise CompatibilityWrapperError(
            "producer_core_committed_bytes_mismatch"
        )

    source_sha256 = sha256_bytes(source)
    try:
        code = compile(
            source,
            str(producer_core),
            "exec",
            dont_inherit=True,
        )
    except Exception as exc:
        raise CompatibilityWrapperError(
            f"producer_core_compile_failed: {producer_core}: {exc}"
        ) from exc

    previous = sys.modules.get(PRODUCER_CORE_MODULE)
    had_previous = PRODUCER_CORE_MODULE in sys.modules
    module = types.ModuleType(PRODUCER_CORE_MODULE)
    module.__file__ = str(producer_core)
    module.__cached__ = None
    module.__loader__ = None
    module.__package__ = ""
    module.__spec__ = None
    module.__pulsemech_source_sha256__ = source_sha256
    module.__pulsemech_verified_revision__ = revision
    sys.modules[PRODUCER_CORE_MODULE] = module

    try:
        exec(code, module.__dict__)
    except Exception as exc:
        if had_previous:
            sys.modules[PRODUCER_CORE_MODULE] = previous
        else:
            sys.modules.pop(PRODUCER_CORE_MODULE, None)
        raise CompatibilityWrapperError(
            f"producer_core_execution_failed: {producer_core}: {exc}"
        ) from exc

    globals()["_EXECUTED_WRAPPER_PATH"] = executed_wrapper
    globals()["_BOOTSTRAP_REPOSITORY_ROOT"] = root
    globals()["PRODUCER_CORE"] = producer_core
    return module, source_sha256


try:
    _PRODUCER_CORE, PRODUCER_CORE_SOURCE_SHA256 = _load_verified_producer_core()
except Exception as exc:
    error = (
        exc
        if isinstance(exc, CompatibilityWrapperError)
        else CompatibilityWrapperError(f"unexpected_wrapper_error: {exc}")
    )
    if __name__ == "__main__":
        sys.stderr.write(render_diagnostic(error))
        raise SystemExit(1)
    if error is exc:
        raise
    raise error from exc

# Preserve the established import surface. Packet production remains
# implemented only in the producer-core module.
for _name, _value in vars(_PRODUCER_CORE).items():
    if _name.startswith("__") or _name in {
        "main",
        "executed_producer_source_path",
    }:
        continue
    globals()[_name] = _value


def executed_producer_source_path(
    repository_root: Path,
    *,
    revision: str,
) -> Path:
    return _PRODUCER_CORE.executed_producer_source_path(
        repository_root,
        revision=revision,
        executed_source_path=_EXECUTED_WRAPPER_PATH,
    )


def main() -> int:
    return int(
        _PRODUCER_CORE.main(
            producer_source_path=_EXECUTED_WRAPPER_PATH,
            producer_core_source_sha256=PRODUCER_CORE_SOURCE_SHA256,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())

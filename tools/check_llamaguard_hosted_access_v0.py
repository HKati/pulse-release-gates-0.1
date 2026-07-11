#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


TOOL_NAME = "check_llamaguard_hosted_access_v0"
TOOL_VERSION = "0.1.0"
SCHEMA_VERSION = "llamaguard_hosted_access_preflight_v0"

PRODUCER_REL = (
    "PULSE_safe_pack_v0/tools/"
    "run_llamaguard_current_evidence_v0.py"
)
RUNTIME_REQUIREMENTS_REL = "PULSE_safe_pack_v0/requirements-llamaguard-v0.txt"
PROBE_FILES: tuple[str, ...] = (
    "config.json",
    "tokenizer_config.json",
)
MAX_PROBE_BYTES = 2 * 1024 * 1024

HEX40_RE = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
POSITIVE_INT_RE = re.compile(r"^[1-9][0-9]*$")
HUB_REQUIREMENT_RE = re.compile(
    r"^huggingface-hub==(?P<version>[A-Za-z0-9_.+!-]+)$",
    re.IGNORECASE,
)

AUTHORITY_BOUNDARY = {
    "access_preflight_only": True,
    "runs_model_inference": False,
    "downloads_model_weights": False,
    "produces_release_evidence": False,
    "writes_status": False,
    "materializes_gates": False,
    "calls_gate_checker": False,
    "creates_attestation": False,
    "authorizes_release": False,
    "blocks_release": False,
}


class PreflightError(ValueError):
    def __init__(self, code: str, *, field: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.field = field


class StrictJsonError(PreflightError):
    pass


@dataclass(frozen=True)
class HuggingFaceBindings:
    api_factory: Callable[..., Any]
    download_file: Callable[..., str]
    gated_repo_error: type[BaseException]
    repository_not_found_error: type[BaseException]
    revision_not_found_error: type[BaseException]
    entry_not_found_error: type[BaseException]
    hub_http_error: type[BaseException]


def _load_huggingface_bindings() -> HuggingFaceBindings:
    from huggingface_hub import HfApi, hf_hub_download
    from huggingface_hub.utils import (
        EntryNotFoundError,
        GatedRepoError,
        HfHubHTTPError,
        RepositoryNotFoundError,
        RevisionNotFoundError,
    )

    return HuggingFaceBindings(
        api_factory=HfApi,
        download_file=hf_hub_download,
        gated_repo_error=GatedRepoError,
        repository_not_found_error=RepositoryNotFoundError,
        revision_not_found_error=RevisionNotFoundError,
        entry_not_found_error=EntryNotFoundError,
        hub_http_error=HfHubHTTPError,
    )


def _installed_hub_version() -> str:
    try:
        return importlib.metadata.version("huggingface-hub")
    except importlib.metadata.PackageNotFoundError as exc:
        raise PreflightError("huggingface_hub_not_installed") from exc


def _json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJsonError("probe_duplicate_json_key", field=key)
        result[key] = value
    return result


def _read_strict_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8", errors="strict"),
            object_pairs_hook=_json_object,
            parse_constant=lambda value: (_ for _ in ()).throw(
                StrictJsonError("probe_non_finite_json", field=value)
            ),
        )
    except PreflightError:
        raise
    except Exception as exc:
        raise PreflightError("probe_invalid_json") from exc

    if not isinstance(payload, dict):
        raise PreflightError("probe_json_not_object")
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_repo_root(path: Path) -> Path:
    resolved = Path(os.path.abspath(os.path.normpath(str(path))))
    if resolved.is_symlink() or not resolved.is_dir():
        raise PreflightError("repo_root_not_regular_directory")
    return resolved


def _reject_symlink_components(
    repo_root: Path,
    path: Path,
    relative: str,
) -> None:
    try:
        relative_path = path.relative_to(repo_root)
    except ValueError as exc:
        raise PreflightError("repository_path_escape", field=relative) from exc

    current = repo_root
    for part in relative_path.parts:
        current = current / part
        if current.is_symlink():
            raise PreflightError(
                "repository_path_symlink_component",
                field=relative,
            )


def _safe_repo_path(repo_root: Path, relative: str) -> Path:
    path = Path(os.path.abspath(os.path.normpath(str(repo_root / relative))))
    try:
        path.relative_to(repo_root)
    except ValueError as exc:
        raise PreflightError("repository_path_escape", field=relative) from exc

    _reject_symlink_components(repo_root, path, relative)

    if not path.is_file():
        raise PreflightError("repository_file_missing_or_symlinked", field=relative)
    return path


def _git_head(repo_root: Path) -> str:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "rev-parse",
                "HEAD",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except Exception as exc:
        raise PreflightError("git_head_unavailable") from exc

    head = result.stdout.strip().lower()
    if not HEX40_RE.fullmatch(head):
        raise PreflightError("git_head_not_concrete_sha")
    return head


def _extract_string_constants(path: Path, names: set[str]) -> dict[str, str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="strict"))
    except Exception as exc:
        raise PreflightError("producer_source_parse_failed") from exc

    values: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id not in names:
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            values[target.id] = node.value.value

    missing = sorted(names - values.keys())
    if missing:
        raise PreflightError("producer_identity_constant_missing", field=",".join(missing))
    return values


def _canonical_runtime_identity(repo_root: Path) -> dict[str, str]:
    producer = _safe_repo_path(repo_root, PRODUCER_REL)
    requirements = _safe_repo_path(repo_root, RUNTIME_REQUIREMENTS_REL)

    constants = _extract_string_constants(producer, {"MODEL_ID", "MODEL_REVISION"})
    model_id = constants["MODEL_ID"].strip()
    model_revision = constants["MODEL_REVISION"].strip().lower()

    if not model_id or "/" not in model_id:
        raise PreflightError("invalid_model_id")
    if not HEX40_RE.fullmatch(model_revision):
        raise PreflightError("invalid_model_revision")

    matched_versions: list[str] = []
    for raw in requirements.read_text(encoding="utf-8", errors="strict").splitlines():
        line = raw.split("#", 1)[0].strip()
        match = HUB_REQUIREMENT_RE.fullmatch(line)
        if match:
            matched_versions.append(match.group("version"))

    if len(matched_versions) != 1:
        raise PreflightError("huggingface_hub_pin_not_unique")

    return {
        "model_id": model_id,
        "model_revision": model_revision,
        "huggingface_hub_version": matched_versions[0],
        "producer_path": PRODUCER_REL,
        "producer_sha256": _sha256(producer),
        "runtime_requirements_path": RUNTIME_REQUIREMENTS_REL,
        "runtime_requirements_sha256": _sha256(requirements),
    }


def _validate_repository(value: str) -> str:
    repository = value.strip()
    if not REPOSITORY_RE.fullmatch(repository):
        raise PreflightError("invalid_repository")
    return repository


def _validate_sha(value: str) -> str:
    sha = value.strip().lower()
    if not HEX40_RE.fullmatch(sha):
        raise PreflightError("invalid_git_sha")
    return sha


def _validate_positive_int(value: str, field: str) -> str:
    text = value.strip()
    if not POSITIVE_INT_RE.fullmatch(text):
        raise PreflightError("invalid_positive_integer", field=field)
    return text


def _validate_non_empty(value: str, field: str) -> str:
    text = value.strip()
    if not text:
        raise PreflightError("missing_required_text", field=field)
    return text


def _normalize_output(repo_root: Path, output: Path) -> Path:
    resolved = Path(os.path.abspath(os.path.normpath(str(output))))
    if resolved.name == "status.json":
        raise PreflightError("refusing_to_write_status_json")
    if resolved.is_symlink():
        raise PreflightError("refusing_to_write_symlink_output")
    if resolved.exists() and not resolved.is_file():
        raise PreflightError("refusing_to_write_non_file_output")

    for parent in (resolved.parent, *resolved.parent.parents):
        if parent.exists() and parent.is_symlink():
            raise PreflightError("refusing_to_write_through_symlink_parent")

    try:
        resolved.relative_to(repo_root)
    except ValueError:
        return resolved
    raise PreflightError("refusing_to_write_inside_repository")


def _utc_now() -> str:
    return (
        dt.datetime.now(tz=dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _base_report(
    *,
    repository: str,
    git_sha: str,
    workflow_ref: str,
    run_id: str,
    run_attempt: str,
    runtime: dict[str, str] | None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": {
            "name": TOOL_NAME,
            "version": TOOL_VERSION,
        },
        "created_utc": _utc_now(),
        "ok": False,
        "status": "blocked",
        "source": {
            "repository": repository,
            "git_sha": git_sha,
            "workflow_ref": workflow_ref,
            "run_id": run_id,
            "run_attempt": run_attempt,
        },
        "runtime": runtime,
        "checks": [],
        "probe_files": [],
        "failure": None,
        "authority_boundary": dict(AUTHORITY_BOUNDARY),
    }


def _add_check(
    report: dict[str, Any],
    check_id: str,
    passed: bool,
    details: str,
) -> None:
    report["checks"].append(
        {
            "check_id": check_id,
            "passed": bool(passed),
            "details": details,
        }
    )


def _fail(
    report: dict[str, Any],
    kind: str,
    *,
    field: str | None = None,
    http_status: int | None = None,
    exception_type: str | None = None,
) -> tuple[dict[str, Any], int]:
    failure: dict[str, Any] = {"kind": kind}
    if field:
        failure["field"] = field
    if http_status is not None:
        failure["http_status"] = http_status
    if exception_type:
        failure["exception_type"] = exception_type
    report["failure"] = failure
    report["ok"] = False
    report["status"] = "blocked"
    return report, 1


def _http_status(exc: BaseException) -> int | None:
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    return status if isinstance(status, int) else None


def check_access(
    *,
    repo_root: Path,
    token_env: str,
    repository: str,
    git_sha: str,
    workflow_ref: str,
    run_id: str,
    run_attempt: str,
) -> tuple[dict[str, Any], int]:
    repo_root = _normalize_repo_root(repo_root)
    repository = _validate_repository(repository)
    git_sha = _validate_sha(git_sha)
    workflow_ref = _validate_non_empty(workflow_ref, "workflow_ref")
    run_id = _validate_positive_int(run_id, "run_id")
    run_attempt = _validate_positive_int(run_attempt, "run_attempt")
    token_env = _validate_non_empty(token_env, "token_env")

    runtime: dict[str, str] | None = None
    report = _base_report(
        repository=repository,
        git_sha=git_sha,
        workflow_ref=workflow_ref,
        run_id=run_id,
        run_attempt=run_attempt,
        runtime=runtime,
    )

    try:
        checked_out_git_sha = _git_head(repo_root)
        report["source"]["checked_out_git_sha"] = checked_out_git_sha
        git_sha_matches = checked_out_git_sha == git_sha
        _add_check(
            report,
            "source.git_sha_matches_checkout",
            git_sha_matches,
            "reported git SHA matches the checked-out repository HEAD",
        )
        if not git_sha_matches:
            return _fail(
                report,
                "git_sha_checkout_mismatch",
                field="git_sha",
            )
    except PreflightError as exc:
        _add_check(
            report,
            "source.git_sha_matches_checkout",
            False,
            "checked-out repository HEAD could not be verified",
        )
        return _fail(report, exc.code, field=exc.field)

    try:
        runtime = _canonical_runtime_identity(repo_root)
        report["runtime"] = runtime
        _add_check(
            report,
            "runtime.canonical_identity_loaded",
            True,
            "model identity, revision, and Hub client pin were read from canonical repository files",
        )
    except PreflightError as exc:
        _add_check(
            report,
            "runtime.canonical_identity_loaded",
            False,
            "canonical hosted runtime identity could not be loaded",
        )
        return _fail(report, exc.code, field=exc.field)

    token = os.environ.get(token_env, "").strip()
    token_present = bool(token)
    _add_check(
        report,
        "token.present",
        token_present,
        f"environment variable {token_env} is non-empty",
    )
    if not token_present:
        return _fail(report, "missing_token", field=token_env)

    expected_hub_version = runtime["huggingface_hub_version"]
    try:
        installed_hub_version = _installed_hub_version()
    except PreflightError as exc:
        _add_check(
            report,
            "runtime.huggingface_hub_version",
            False,
            "pinned Hugging Face Hub client is not installed",
        )
        return _fail(report, exc.code)

    version_matches = installed_hub_version == expected_hub_version
    _add_check(
        report,
        "runtime.huggingface_hub_version",
        version_matches,
        "installed Hugging Face Hub client matches the canonical runtime pin",
    )
    report["runtime"]["installed_huggingface_hub_version"] = installed_hub_version
    if not version_matches:
        return _fail(report, "huggingface_hub_version_mismatch")

    try:
        bindings = _load_huggingface_bindings()
        api = bindings.api_factory(token=token)
        info = api.model_info(
            repo_id=runtime["model_id"],
            revision=runtime["model_revision"],
            token=token,
        )

        resolved_revision = getattr(info, "sha", None)
        resolved_matches = (
            isinstance(resolved_revision, str)
            and resolved_revision.lower() == runtime["model_revision"]
        )
        _add_check(
            report,
            "model.revision_resolved",
            resolved_matches,
            "Hub model metadata resolved to the exact pinned commit revision",
        )
        report["runtime"]["resolved_model_revision"] = (
            resolved_revision.lower()
            if isinstance(resolved_revision, str)
            else None
        )
        gated = getattr(info, "gated", None)
        report["runtime"]["gated"] = gated if isinstance(gated, (bool, str)) else None

        if not resolved_matches:
            return _fail(report, "model_revision_mismatch")

        with tempfile.TemporaryDirectory(
            prefix="pulse-llamaguard-access-preflight-"
        ) as temp_dir_text:
            temp_dir = Path(temp_dir_text).resolve()
            probes: list[dict[str, Any]] = []

            for filename in PROBE_FILES:
                downloaded = Path(
                    bindings.download_file(
                        repo_id=runtime["model_id"],
                        filename=filename,
                        revision=runtime["model_revision"],
                        token=token,
                        cache_dir=str(temp_dir),
                    )
                )
                resolved_file = downloaded.resolve(strict=True)
                try:
                    resolved_file.relative_to(temp_dir)
                except ValueError as exc:
                    raise PreflightError(
                        "probe_download_escaped_temporary_cache",
                        field=filename,
                    ) from exc

                if not resolved_file.is_file():
                    raise PreflightError("probe_file_missing", field=filename)

                size = resolved_file.stat().st_size
                if size <= 0:
                    raise PreflightError("probe_file_empty", field=filename)
                if size > MAX_PROBE_BYTES:
                    raise PreflightError("probe_file_too_large", field=filename)

                _read_strict_json_object(resolved_file)
                probes.append(
                    {
                        "path": filename,
                        "size_bytes": size,
                        "sha256": _sha256(resolved_file),
                        "json_object": True,
                    }
                )

            report["probe_files"] = probes

        _add_check(
            report,
            "model.metadata_files_accessible",
            len(report["probe_files"]) == len(PROBE_FILES),
            "small pinned-revision metadata files were downloaded and parsed without model weights or inference",
        )

    except PreflightError as exc:
        return _fail(report, exc.code, field=exc.field)
    except Exception as exc:  # noqa: BLE001
        bindings_value = locals().get("bindings")
        if isinstance(bindings_value, HuggingFaceBindings):
            if isinstance(exc, bindings_value.gated_repo_error):
                return _fail(
                    report,
                    "gated_model_access_denied",
                    http_status=_http_status(exc),
                )
            if isinstance(exc, bindings_value.revision_not_found_error):
                return _fail(
                    report,
                    "model_revision_not_found",
                    http_status=_http_status(exc),
                )
            if isinstance(exc, bindings_value.entry_not_found_error):
                return _fail(
                    report,
                    "probe_file_not_found",
                    http_status=_http_status(exc),
                )
            if isinstance(exc, bindings_value.repository_not_found_error):
                return _fail(
                    report,
                    "model_repository_not_found_or_inaccessible",
                    http_status=_http_status(exc),
                )
            if isinstance(exc, bindings_value.hub_http_error):
                return _fail(
                    report,
                    "huggingface_hub_http_error",
                    http_status=_http_status(exc),
                )

        return _fail(
            report,
            "unexpected_preflight_error",
            exception_type=type(exc).__name__,
        )

    report["ok"] = True
    report["status"] = "accessible"
    report["failure"] = None
    return report, 0


def _render(report: dict[str, Any]) -> str:
    return json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise PreflightError("refusing_to_write_symlink_output")
    path.write_text(_render(report), encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that the configured Hugging Face token can read the exact "
            "pinned LlamaGuard model revision without downloading model weights."
        )
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--token-env", default="HF_TOKEN")
    parser.add_argument("--repository", required=True)
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--workflow-ref", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    try:
        repo_root = _normalize_repo_root(Path(args.repo_root))
        output = _normalize_output(repo_root, Path(args.output))
    except PreflightError as exc:
        diagnostic = {
            "schema_version": SCHEMA_VERSION,
            "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
            "ok": False,
            "status": "output_refused",
            "failure": {
                "kind": exc.code,
                **({"field": exc.field} if exc.field else {}),
            },
            "authority_boundary": dict(AUTHORITY_BOUNDARY),
        }
        sys.stdout.write(_render(diagnostic))
        return 2

    try:
        report, exit_code = check_access(
            repo_root=repo_root,
            token_env=args.token_env,
            repository=args.repository,
            git_sha=args.git_sha,
            workflow_ref=args.workflow_ref,
            run_id=args.run_id,
            run_attempt=args.run_attempt,
        )
    except PreflightError as exc:
        report = _base_report(
            repository=str(args.repository),
            git_sha=str(args.git_sha),
            workflow_ref=str(args.workflow_ref),
            run_id=str(args.run_id),
            run_attempt=str(args.run_attempt),
            runtime=None,
        )
        report, exit_code = _fail(report, exc.code, field=exc.field)
    except Exception as exc:  # noqa: BLE001
        report = _base_report(
            repository=str(args.repository),
            git_sha=str(args.git_sha),
            workflow_ref=str(args.workflow_ref),
            run_id=str(args.run_id),
            run_attempt=str(args.run_attempt),
            runtime=None,
        )
        report, exit_code = _fail(
            report,
            "unexpected_preflight_error",
            exception_type=type(exc).__name__,
        )

    _write_report(output, report)
    sys.stdout.write(_render(report))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

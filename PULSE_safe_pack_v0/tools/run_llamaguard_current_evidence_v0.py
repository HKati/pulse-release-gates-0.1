#!/usr/bin/env python3
"""Produce current-run Llama Guard 3 1B raw evidence.

Input:

    PULSE_safe_pack_v0/examples/
    llamaguard_current_run_cases_v0.jsonl

Outputs:

    PULSE_safe_pack_v0/artifacts/external/
    llamaguard_raw.jsonl

    PULSE_safe_pack_v0/artifacts/external/
    llamaguard_evaluator_manifest_v0.json

The raw JSONL is consumed by:

    PULSE_safe_pack_v0/tools/adapters/
    llamaguard_ingest.py

This producer does not create an attestation, materialize gates,
modify status.json, replace check_gates.py, or create release authority.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.metadata
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


TOOL_SCHEMA = "llamaguard_current_run_evaluator_v0"
TOOL_VERSION = "0.1.0"

TOOL_REL = (
    "PULSE_safe_pack_v0/tools/"
    "run_llamaguard_current_evidence_v0.py"
)
MODEL_ID = "meta-llama/Llama-Guard-3-1B"
MODEL_REVISION = "acf7aafa60f0410f8f42b1fa35e077d705892029"
WORKFLOW_REL = ".github/workflows/pulse_ci.yml"
WORKFLOW_NAME = "PULSE CI"

DATASET_REL = (
    "PULSE_safe_pack_v0/examples/"
    "llamaguard_current_run_cases_v0.jsonl"
)
RAW_REL = (
    "PULSE_safe_pack_v0/artifacts/external/"
    "llamaguard_raw.jsonl"
)
MANIFEST_REL = (
    "PULSE_safe_pack_v0/artifacts/external/"
    "llamaguard_evaluator_manifest_v0.json"
)
MANIFEST_SCHEMA_REL = (
    "PULSE_safe_pack_v0/schemas/"
    "llamaguard_evaluator_manifest_v0.schema.json"
)

STALE_OUTPUT_RELS = (
    RAW_REL,
    MANIFEST_REL,
    (
        "PULSE_safe_pack_v0/artifacts/external/"
        "llamaguard_summary.json"
    ),
    (
        "PULSE_safe_pack_v0/artifacts/external/"
        "llamaguard_summary.jsonl"
    ),
    (
        "PULSE_safe_pack_v0/artifacts/external/"
        "llamaguard_summary.envelope.json"
    ),
    (
        "PULSE_safe_pack_v0/artifacts/external/"
        "llamaguard_summary.bundle.json"
    ),
    (
        "PULSE_safe_pack_v0/artifacts/external/"
        "llamaguard_summary.attestation.json"
    ),
    (
        "PULSE_safe_pack_v0/artifacts/external/"
        "llamaguard_attestation_verifier_v1.json"
    ),
)

HEX40_RE = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)
REPOSITORY_RE = re.compile(
    r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"
)
CASE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
RUN_KEY_RE = re.compile(
    r"^GITHUB_RUN_ID=(?P<run_id>[1-9][0-9]*)\|"
    r"GITHUB_RUN_ATTEMPT=(?P<run_attempt>[1-9][0-9]*)\|"
    r"GITHUB_WORKFLOW=(?P<workflow>[^|\r\n]+)$"
)
CATEGORY_RE = re.compile(
    r"\bS(?:[1-9]|1[0-3])\b",
    re.IGNORECASE,
)

AUTHORITY_BOUNDARY = {
    "creates_release_authority": False,
    "materializes_status": False,
    "materializes_release_required": False,
    "creates_attestation": False,
    "replaces_check_gates": False,
}


class RunnerError(ValueError):
    """Fail-closed current-run producer error."""


class UniqueJsonError(RunnerError):
    """Strict JSON parse error."""


def _json_object(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key, value in pairs:
        if key in result:
            raise UniqueJsonError(
                f"duplicate JSON key {key!r}"
            )

        result[key] = value

    return result


def _reject_nonfinite(value: str) -> None:
    raise UniqueJsonError(
        f"non-finite JSON constant {value!r}"
    )


def _require_finite_json_tree(
    value: Any,
    label: str,
) -> None:
    if (
        value is None
        or isinstance(
            value,
            (
                str,
                bool,
                int,
            ),
        )
    ):
        return

    if isinstance(value, float):
        if not math.isfinite(value):
            raise RunnerError(
                f"{label} contains a non-finite number"
            )

        return

    if isinstance(value, list):
        for index, item in enumerate(value):
            _require_finite_json_tree(
                item,
                f"{label}[{index}]",
            )

        return

    if isinstance(value, dict):
        for key, item in value.items():
            _require_finite_json_tree(
                item,
                f"{label}.{key}",
            )

        return

    raise RunnerError(
        f"{label} contains an unsupported JSON value"
    )


def _require_text(
    value: Any,
    label: str,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RunnerError(
            f"{label} must be a non-empty string"
        )

    return value.strip()


def _require_preserved_text(
    value: Any,
    label: str,
) -> str:
    """Validate non-empty text without changing its exact content."""

    if not isinstance(value, str) or not value.strip():
        raise RunnerError(
            f"{label} must be a non-empty string"
        )

    return value


def _resolve_lexically(
    repo_root: Path,
    supplied: Path,
) -> Path:
    candidate = (
        supplied
        if supplied.is_absolute()
        else repo_root / supplied
    )

    return Path(os.path.abspath(candidate))


def _require_canonical_path(
    repo_root: Path,
    supplied: Path,
    expected_relative: str,
    label: str,
) -> Path:
    actual = _resolve_lexically(
        repo_root,
        supplied,
    )
    expected = _resolve_lexically(
        repo_root,
        Path(expected_relative),
    )

    if actual != expected:
        raise RunnerError(
            f"{label} must use canonical path {expected}"
        )

    try:
        actual.relative_to(repo_root)

    except ValueError as exc:
        raise RunnerError(
            f"{label} escapes repository root"
        ) from exc

    return actual


def _reject_symlink_components(
    repo_root: Path,
    path: Path,
    label: str,
) -> None:
    try:
        relative = path.relative_to(repo_root)

    except ValueError as exc:
        raise RunnerError(
            f"{label} escapes repository root"
        ) from exc

    current = repo_root

    for part in relative.parts:
        current = current / part

        if current.is_symlink():
            raise RunnerError(
                f"{label} must not traverse a symlink: "
                f"{current}"
            )


def _require_regular_file(
    path: Path,
    label: str,
) -> None:
    if path.is_symlink() or not path.is_file():
        raise RunnerError(
            f"{label} must be a regular non-symlink file: "
            f"{path}"
        )


def _repo_relative(
    repo_root: Path,
    path: Path,
) -> str:
    try:
        return path.relative_to(repo_root).as_posix()

    except ValueError as exc:
        raise RunnerError(
            f"path escapes repository root: {path}"
        ) from exc


def _sha256_file(path: Path) -> str:
    _require_regular_file(
        path,
        f"SHA-256 input {path}",
    )

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(65536),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _load_json_object(
    path: Path,
    label: str,
) -> dict[str, Any]:
    _require_regular_file(path, label)

    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_json_object,
            parse_constant=_reject_nonfinite,
        )

    except RunnerError:
        raise

    except Exception as exc:
        raise RunnerError(
            f"{label} is not valid JSON: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise RunnerError(
            f"{label} must be a JSON object"
        )

    _require_finite_json_tree(payload, label)
    return payload


def _normalize_utc(value: Any) -> str:
    text = _require_text(
        value,
        "created_utc",
    )
    parse_value = (
        text[:-1] + "+00:00"
        if text.endswith("Z")
        else text
    )

    try:
        timestamp = dt.datetime.fromisoformat(
            parse_value
        )

    except ValueError as exc:
        raise RunnerError(
            "created_utc must be an ISO-8601 date-time"
        ) from exc

    if timestamp.tzinfo is None:
        raise RunnerError(
            "created_utc must include a timezone"
        )

    normalized = timestamp.astimezone(
        dt.timezone.utc
    ).replace(microsecond=0)

    return (
        normalized.isoformat(
            timespec="seconds"
        )
        .replace("+00:00", "Z")
    )


def _validate_repository(value: Any) -> str:
    repository = _require_text(
        value,
        "repository",
    )

    if not REPOSITORY_RE.fullmatch(repository):
        raise RunnerError(
            "repository must use '<owner>/<repo>' form"
        )

    return repository


def _validate_git_sha(value: Any) -> str:
    git_sha = _require_text(
        value,
        "git_sha",
    ).lower()

    if not HEX40_RE.fullmatch(git_sha):
        raise RunnerError(
            "git_sha must be a concrete 40-hex SHA"
        )

    return git_sha


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
        raise RunnerError(
            f"could not read checked-out git HEAD: {exc}"
        ) from exc

    head = result.stdout.strip().lower()

    if not HEX40_RE.fullmatch(head):
        raise RunnerError(
            "checked-out git HEAD is not a concrete 40-hex SHA"
        )

    return head


def _parse_run_key(
    value: Any,
) -> dict[str, Any]:
    run_key = _require_text(
        value,
        "run_key",
    )
    match = RUN_KEY_RE.fullmatch(run_key)

    if match is None:
        raise RunnerError(
            "run_key must use the canonical GitHub run identity form"
        )

    workflow_name = match.group("workflow")

    if workflow_name != WORKFLOW_NAME:
        raise RunnerError(
            f"run_key workflow must be {WORKFLOW_NAME!r}"
        )

    return {
        "run_key": run_key,
        "run_id": int(match.group("run_id")),
        "run_attempt": int(
            match.group("run_attempt")
        ),
        "workflow_name": workflow_name,
    }


def _validate_workflow_ref(
    value: Any,
    repository: str,
) -> str:
    workflow_ref = _require_text(
        value,
        "workflow_ref",
    )
    expected_prefix = (
        f"{repository}/{WORKFLOW_REL}@"
    )

    if not workflow_ref.startswith(expected_prefix):
        raise RunnerError(
            "workflow_ref must identify the exact "
            f"{WORKFLOW_REL} workflow"
        )

    source_ref = workflow_ref[
        len(expected_prefix):
    ]

    if (
        not source_ref
        or "\n" in source_ref
        or "\r" in source_ref
    ):
        raise RunnerError(
            "workflow_ref must include a concrete source ref"
        )

    return workflow_ref


def _validate_model_revision(value: Any) -> str:
    revision = _require_text(
        value,
        "model_revision",
    ).lower()

    if not HEX40_RE.fullmatch(revision):
        raise RunnerError(
            "model_revision must be a concrete 40-hex SHA"
        )

    if revision != MODEL_REVISION:
        raise RunnerError(
            "model_revision must match the checked-in "
            f"LlamaGuard revision {MODEL_REVISION}"
        )

    return revision


def _load_cases(
    path: Path,
) -> list[dict[str, str]]:
    _require_regular_file(
        path,
        "LlamaGuard current-run case set",
    )
    result: list[dict[str, str]] = []
    seen_case_ids: set[str] = set()

    try:
        handle = path.open(
            "r",
            encoding="utf-8",
            errors="strict",
        )

    except OSError as exc:
        raise RunnerError(
            f"could not open LlamaGuard case set: {exc}"
        ) from exc

    with handle:
        for line_number, raw_line in enumerate(
            handle,
            start=1,
        ):
            text = raw_line.strip()

            if not text:
                continue

            try:
                item = json.loads(
                    text,
                    object_pairs_hook=_json_object,
                    parse_constant=_reject_nonfinite,
                )

            except RunnerError as exc:
                raise RunnerError(
                    f"case-set line {line_number}: {exc}"
                ) from exc

            except Exception as exc:
                raise RunnerError(
                    f"case-set line {line_number} is not "
                    f"valid JSON: {exc}"
                ) from exc

            if not isinstance(item, dict):
                raise RunnerError(
                    f"case-set line {line_number} must be "
                    "an object"
                )

            _require_finite_json_tree(
                item,
                f"case-set line {line_number}",
            )

            unknown_keys = sorted(
                set(item)
                - {
                    "case_id",
                    "input",
                    "output",
                }
            )

            if unknown_keys:
                raise RunnerError(
                    f"case-set line {line_number} has "
                    f"unsupported keys: {unknown_keys}"
                )

            case_id = _require_text(
                item.get("case_id"),
                f"line {line_number}.case_id",
            )
            prompt = _require_preserved_text(
                item.get("input"),
                f"line {line_number}.input",
            )
            response = _require_preserved_text(
                item.get("output"),
                f"line {line_number}.output",
            )

            if not CASE_ID_RE.fullmatch(case_id):
                raise RunnerError(
                    f"case_id {case_id!r} uses an invalid format"
                )

            if case_id in seen_case_ids:
                raise RunnerError(
                    f"duplicate case_id {case_id!r}"
                )

            if len(prompt) > 4000:
                raise RunnerError(
                    f"case {case_id!r} input exceeds "
                    "4000 characters"
                )

            if len(response) > 4000:
                raise RunnerError(
                    f"case {case_id!r} output exceeds "
                    "4000 characters"
                )

            seen_case_ids.add(case_id)
            result.append(
                {
                    "case_id": case_id,
                    "input": prompt,
                    "output": response,
                }
            )

    if not result:
        raise RunnerError(
            "case set must contain at least one case"
        )

    if len(result) > 32:
        raise RunnerError(
            "case set must contain at most 32 cases"
        )

    return result


def _parse_model_output(
    value: Any,
) -> tuple[str, list[str], str]:
    raw_output = _require_text(
        value,
        "LlamaGuard output",
    )
    lines = [
        line.strip()
        for line in raw_output.splitlines()
        if line.strip()
    ]
    first = lines[0].lower()

    if first == "safe":
        if len(lines) != 1:
            raise RunnerError(
                "safe LlamaGuard output must not contain "
                "additional non-empty lines"
            )

        if CATEGORY_RE.search(raw_output):
            raise RunnerError(
                "safe LlamaGuard output must not contain "
                "S1-S13 categories"
            )

        return "safe", [], raw_output

    if first != "unsafe":
        raise RunnerError(
            "LlamaGuard output must begin with exactly "
            "'safe' or 'unsafe'"
        )

    if len(lines) < 2:
        raise RunnerError(
            "unsafe LlamaGuard output must include "
            "at least one S1-S13 category"
        )

    category_text = " ".join(lines[1:])
    categories = sorted(
        {
            match.upper()
            for match in CATEGORY_RE.findall(
                category_text
            )
        },
        key=lambda item: int(item[1:]),
    )

    if not categories:
        raise RunnerError(
            "unsafe LlamaGuard output must include "
            "at least one S1-S13 category"
        )

    remainder = CATEGORY_RE.sub(
        "",
        category_text,
    )
    remainder = re.sub(
        r"[\s,;]+",
        "",
        remainder,
    )

    if remainder:
        raise RunnerError(
            "unsafe LlamaGuard output contains "
            "unsupported category text"
        )

    return "unsafe", categories, raw_output


def _package_version(package: str) -> str:
    try:
        version = importlib.metadata.version(package)

    except importlib.metadata.PackageNotFoundError as exc:
        raise RunnerError(
            f"required runtime package is missing: {package}"
        ) from exc

    return _require_text(
        version,
        f"{package} version",
    )


def _runtime() -> tuple[Any, Any, Any, Any]:
    try:
        import torch
        from huggingface_hub import HfApi
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
        )

    except Exception as exc:
        raise RunnerError(
            "LlamaGuard runtime dependencies are "
            f"unavailable: {exc}"
        ) from exc

    return (
        torch,
        HfApi,
        AutoModelForCausalLM,
        AutoTokenizer,
    )


def _verify_remote_revision(
    api_type: Any,
    token: str,
    revision: str,
) -> str:
    try:
        info = api_type(token=token).model_info(
            repo_id=MODEL_ID,
            revision=revision,
            files_metadata=False,
        )

    except Exception as exc:
        raise RunnerError(
            "could not verify the gated exact model "
            f"revision: {exc}"
        ) from exc

    resolved = getattr(info, "sha", None)

    if (
        not isinstance(resolved, str)
        or not HEX40_RE.fullmatch(resolved)
    ):
        raise RunnerError(
            "resolved model revision must be a "
            "concrete 40-hex SHA"
        )

    resolved = resolved.lower()

    if resolved != revision:
        raise RunnerError(
            "resolved model revision does not match "
            "the checked-in exact revision"
        )

    return resolved


def _load_model(
    torch: Any,
    model_type: Any,
    tokenizer_type: Any,
    token: str,
    revision: str,
) -> tuple[Any, Any]:
    try:
        tokenizer = tokenizer_type.from_pretrained(
            MODEL_ID,
            revision=revision,
            token=token,
            trust_remote_code=False,
        )
        model = model_type.from_pretrained(
            MODEL_ID,
            revision=revision,
            token=token,
            trust_remote_code=False,
            use_safetensors=True,
            torch_dtype=torch.float32,
        )
        model.to("cpu")
        model.eval()

    except Exception as exc:
        raise RunnerError(
            f"could not load exact model revision: {exc}"
        ) from exc

    return model, tokenizer


def _classify_case(
    torch: Any,
    model: Any,
    tokenizer: Any,
    case: dict[str, str],
    max_new_tokens: int,
) -> tuple[str, list[str], str, int, int]:
    conversation = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": case["input"],
                }
            ],
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": case["output"],
                }
            ],
        },
    ]

    try:
        input_ids = tokenizer.apply_chat_template(
            conversation,
            return_tensors="pt",
        )

    except Exception as exc:
        raise RunnerError(
            f"case {case['case_id']!r} chat-template "
            f"failed: {exc}"
        ) from exc

    if (
        not hasattr(input_ids, "shape")
        or len(input_ids.shape) != 2
        or int(input_ids.shape[0]) != 1
        or int(input_ids.shape[1]) < 1
    ):
        raise RunnerError(
            f"case {case['case_id']!r} produced "
            "invalid input IDs"
        )

    input_ids = input_ids.to("cpu")
    prompt_tokens = int(input_ids.shape[1])

    try:
        with torch.inference_mode():
            generated = model.generate(
                input_ids,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                num_beams=1,
                pad_token_id=0,
            )

    except Exception as exc:
        raise RunnerError(
            f"case {case['case_id']!r} inference "
            f"failed: {exc}"
        ) from exc

    if (
        not hasattr(generated, "shape")
        or len(generated.shape) != 2
        or int(generated.shape[0]) != 1
        or int(generated.shape[1]) <= prompt_tokens
    ):
        raise RunnerError(
            f"case {case['case_id']!r} produced "
            "no classification tokens"
        )

    generated_tokens = generated[
        0,
        prompt_tokens:,
    ]

    try:
        decoded = tokenizer.decode(
            generated_tokens,
            skip_special_tokens=True,
        )

    except Exception as exc:
        raise RunnerError(
            f"case {case['case_id']!r} decode "
            f"failed: {exc}"
        ) from exc

    label, categories, raw_output = (
        _parse_model_output(decoded)
    )

    return (
        label,
        categories,
        raw_output,
        prompt_tokens,
        int(generated_tokens.shape[0]),
    )


def _write_text_atomic(
    path: Path,
    text: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )
    temp_path = Path(temp_name)

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(
            temp_path,
            path,
        )

    except Exception:
        if temp_path.exists():
            temp_path.unlink()

        raise


def _write_json_atomic(
    path: Path,
    payload: dict[str, Any],
) -> None:
    _write_text_atomic(
        path,
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n",
    )


def _remove_paths(paths: list[Path]) -> None:
    for path in paths:
        if not path.exists() and not path.is_symlink():
            continue

        if path.is_dir() and not path.is_symlink():
            raise RunnerError(
                f"stale output path is a directory: {path}"
            )

        path.unlink()


def _clear_stale_outputs(
    repo_root: Path,
) -> list[Path]:
    stale_paths = [
        _require_canonical_path(
            repo_root,
            Path(relative),
            relative,
            "stale LlamaGuard output",
        )
        for relative in STALE_OUTPUT_RELS
    ]

    for path in stale_paths:
        _reject_symlink_components(
            repo_root,
            path,
            "stale LlamaGuard output",
        )

    _remove_paths(stale_paths)

    external_dir = (
        repo_root
        / "PULSE_safe_pack_v0/artifacts/external"
    )

    if external_dir.exists():
        if external_dir.is_symlink():
            raise RunnerError(
                "external evidence directory must not "
                "be a symlink"
            )

        for temp_path in external_dir.glob(
            ".llamaguard*.tmp"
        ):
            if (
                temp_path.is_dir()
                and not temp_path.is_symlink()
            ):
                raise RunnerError(
                    "temporary LlamaGuard output is a "
                    f"directory: {temp_path}"
                )

            temp_path.unlink()

    return stale_paths


def _validate_manifest_schema(
    manifest: dict[str, Any],
    schema_path: Path,
) -> None:
    schema = _load_json_object(
        schema_path,
        "LlamaGuard evaluator-manifest schema",
    )

    try:
        Draft202012Validator.check_schema(schema)

    except Exception as exc:
        raise RunnerError(
            "LlamaGuard evaluator-manifest schema is "
            f"invalid: {exc}"
        ) from exc

    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    )
    errors = sorted(
        validator.iter_errors(manifest),
        key=lambda item: list(
            item.absolute_path
        ),
    )

    if not errors:
        return

    formatted: list[str] = []

    for error in errors:
        location = ".".join(
            str(part)
            for part in error.absolute_path
        )
        formatted.append(
            (
                f"{location}: "
                if location
                else ""
            )
            + error.message
        )

    raise RunnerError(
        "generated LlamaGuard evaluator manifest "
        "failed schema validation:\n - "
        + "\n - ".join(formatted)
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Produce current-run Llama Guard 3 1B "
            "raw evidence and evaluator manifest."
        )
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root.",
    )
    parser.add_argument(
        "--dataset",
        default=DATASET_REL,
        help="Canonical current-run case-set path.",
    )
    parser.add_argument(
        "--raw-out",
        default=RAW_REL,
        help="Canonical raw-evidence output path.",
    )
    parser.add_argument(
        "--manifest-out",
        default=MANIFEST_REL,
        help="Canonical evaluator-manifest output path.",
    )
    parser.add_argument(
        "--manifest-schema",
        default=MANIFEST_SCHEMA_REL,
        help="Canonical evaluator-manifest schema path.",
    )
    parser.add_argument(
        "--model-revision",
        default=MODEL_REVISION,
        help="Checked-in exact LlamaGuard model revision.",
    )
    parser.add_argument(
        "--token-env",
        default="HF_TOKEN",
        help="Environment variable containing the gated-model token.",
    )
    parser.add_argument(
        "--repository",
        default=os.getenv("GITHUB_REPOSITORY"),
        help="Current repository in owner/name form.",
    )
    parser.add_argument(
        "--git-sha",
        default=os.getenv("GITHUB_SHA"),
        help="Current checked-out 40-hex commit SHA.",
    )
    parser.add_argument(
        "--run-key",
        default=os.getenv("PULSE_RUN_KEY"),
        help="Canonical current-run PULSE run key.",
    )
    parser.add_argument(
        "--workflow-ref",
        default=os.getenv("GITHUB_WORKFLOW_REF"),
        help="Exact current GitHub workflow ref.",
    )
    parser.add_argument(
        "--release-candidate",
        default=os.getenv("PULSE_RELEASE_CANDIDATE"),
        help="Current release-candidate identity.",
    )
    parser.add_argument(
        "--created-utc",
        default=os.getenv("PULSE_CREATED_UTC"),
        help="Current-run UTC creation time.",
    )
    parser.add_argument(
        "--torch-threads",
        type=int,
        default=2,
        help="CPU thread count used for inference.",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=20,
        help="Maximum generated classification tokens.",
    )

    return parser


def main(
    argv: list[str] | None = None,
) -> int:
    args = _parser().parse_args(argv)
    repo_root: Path | None = None
    stale_paths: list[Path] = []
    raw_path: Path | None = None
    manifest_path: Path | None = None

    try:
        repo_root = Path(
            args.repo_root
        ).resolve()

        if not repo_root.is_dir():
            raise RunnerError(
                f"repository root is not a directory: "
                f"{repo_root}"
            )

        raw_path = _require_canonical_path(
            repo_root,
            Path(args.raw_out),
            RAW_REL,
            "raw output",
        )
        manifest_path = _require_canonical_path(
            repo_root,
            Path(args.manifest_out),
            MANIFEST_REL,
            "manifest output",
        )

        _reject_symlink_components(
            repo_root,
            raw_path,
            "raw output",
        )
        _reject_symlink_components(
            repo_root,
            manifest_path,
            "manifest output",
        )

        # Remove every stale LlamaGuard output before any
        # current-run admission or gated-model access attempt.
        stale_paths = _clear_stale_outputs(repo_root)

        tool_path = _require_canonical_path(
            repo_root,
            Path(TOOL_REL),
            TOOL_REL,
            "producer tool",
        )
        dataset_path = _require_canonical_path(
            repo_root,
            Path(args.dataset),
            DATASET_REL,
            "case set",
        )
        schema_path = _require_canonical_path(
            repo_root,
            Path(args.manifest_schema),
            MANIFEST_SCHEMA_REL,
            "evaluator-manifest schema",
        )

        for path, label in (
            (tool_path, "producer tool"),
            (dataset_path, "case set"),
            (schema_path, "evaluator-manifest schema"),
        ):
            _reject_symlink_components(
                repo_root,
                path,
                label,
            )
            _require_regular_file(path, label)

        actual_tool_path = Path(__file__).resolve()

        if actual_tool_path != tool_path.resolve():
            raise RunnerError(
                "producer must execute from the canonical "
                f"path {tool_path}"
            )

        repository = _validate_repository(
            args.repository
        )
        git_sha = _validate_git_sha(
            args.git_sha
        )
        checked_out_head = _git_head(repo_root)

        if checked_out_head != git_sha:
            raise RunnerError(
                "git_sha does not match checked-out "
                f"HEAD: {git_sha} != {checked_out_head}"
            )

        run_identity = _parse_run_key(
            args.run_key
        )
        workflow_ref = _validate_workflow_ref(
            args.workflow_ref,
            repository,
        )
        release_candidate = _require_text(
            args.release_candidate,
            "release_candidate",
        )
        created_utc = _normalize_utc(
            args.created_utc
        )
        model_revision = _validate_model_revision(
            args.model_revision
        )
        token_env = _require_text(
            args.token_env,
            "token_env",
        )

        if len(release_candidate) > 256:
            raise RunnerError(
                "release_candidate must be at most "
                "256 characters"
            )

        if not 1 <= args.torch_threads <= 16:
            raise RunnerError(
                "torch_threads must be between 1 and 16"
            )

        if not 1 <= args.max_new_tokens <= 64:
            raise RunnerError(
                "max_new_tokens must be between 1 and 64"
            )

        token = os.getenv(token_env)

        if not isinstance(token, str) or not token.strip():
            raise RunnerError(
                f"{token_env} is required for the gated "
                "official model"
            )

        cases = _load_cases(dataset_path)
        dataset_sha256 = _sha256_file(dataset_path)
        tool_sha256 = _sha256_file(tool_path)
        schema_sha256 = _sha256_file(schema_path)

        torch, api_type, model_type, tokenizer_type = (
            _runtime()
        )
        torch.set_num_threads(args.torch_threads)
        torch.manual_seed(0)

        resolved_revision = _verify_remote_revision(
            api_type,
            token.strip(),
            model_revision,
        )
        model, tokenizer = _load_model(
            torch,
            model_type,
            tokenizer_type,
            token.strip(),
            resolved_revision,
        )

        records: list[dict[str, Any]] = []

        for case_index, case in enumerate(cases):
            (
                label,
                categories,
                raw_model_output,
                prompt_tokens,
                generated_tokens,
            ) = _classify_case(
                torch,
                model,
                tokenizer,
                case,
                args.max_new_tokens,
            )

            records.append(
                {
                    "case_id": case["case_id"],
                    "input": case["input"],
                    "output": case["output"],
                    "llamaguard": {
                        "label": label,
                        "categories": categories,
                        "raw_output": raw_model_output,
                    },
                    "model": {
                        "id": MODEL_ID,
                        "revision": resolved_revision,
                        "dtype": "float32",
                    },
                    "run": {
                        "repository": repository,
                        "git_sha": git_sha,
                        "run_key": run_identity["run_key"],
                        "run_id": run_identity["run_id"],
                        "run_attempt": run_identity[
                            "run_attempt"
                        ],
                        "workflow_name": run_identity[
                            "workflow_name"
                        ],
                        "workflow_ref": workflow_ref,
                        "release_candidate": (
                            release_candidate
                        ),
                        "created_utc": created_utc,
                        "case_index": case_index,
                    },
                    "inference": {
                        "device": "cpu",
                        "manual_seed": 0,
                        "do_sample": False,
                        "num_beams": 1,
                        "pad_token_id": 0,
                        "max_new_tokens": (
                            args.max_new_tokens
                        ),
                        "prompt_tokens": prompt_tokens,
                        "generated_tokens": (
                            generated_tokens
                        ),
                        "torch_threads": (
                            args.torch_threads
                        ),
                    },
                }
            )

        raw_text = "".join(
            json.dumps(
                record,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            )
            + "\n"
            for record in records
        )
        _write_text_atomic(raw_path, raw_text)
        raw_sha256 = _sha256_file(raw_path)

        runtime_versions = {
            "python": sys.version.split()[0],
            "torch": _package_version("torch"),
            "transformers": _package_version(
                "transformers"
            ),
            "huggingface_hub": _package_version(
                "huggingface-hub"
            ),
            "tokenizers": _package_version(
                "tokenizers"
            ),
            "safetensors": _package_version(
                "safetensors"
            ),
        }

        safe_count = sum(
            record["llamaguard"]["label"] == "safe"
            for record in records
        )
        unsafe_count = sum(
            record["llamaguard"]["label"] == "unsafe"
            for record in records
        )

        manifest = {
            "schema_version": TOOL_SCHEMA,
            "producer": {
                "path": _repo_relative(
                    repo_root,
                    tool_path,
                ),
                "tool": (
                    "run_llamaguard_current_"
                    "evidence_v0.py"
                ),
                "version": TOOL_VERSION,
                "sha256": tool_sha256,
            },
            "run": {
                "repository": repository,
                "git_sha": git_sha,
                "run_key": run_identity["run_key"],
                "run_id": run_identity["run_id"],
                "run_attempt": run_identity[
                    "run_attempt"
                ],
                "workflow_name": run_identity[
                    "workflow_name"
                ],
                "workflow_ref": workflow_ref,
                "workflow_path": WORKFLOW_REL,
                "release_candidate": release_candidate,
                "created_utc": created_utc,
            },
            "model": {
                "id": MODEL_ID,
                "revision": resolved_revision,
                "dtype": "float32",
            },
            "runtime": {
                "versions": runtime_versions,
                "device": "cpu",
                "torch_threads": args.torch_threads,
                "generation": {
                    "manual_seed": 0,
                    "do_sample": False,
                    "num_beams": 1,
                    "pad_token_id": 0,
                    "max_new_tokens": (
                        args.max_new_tokens
                    ),
                },
            },
            "dataset": {
                "path": _repo_relative(
                    repo_root,
                    dataset_path,
                ),
                "sha256": dataset_sha256,
                "case_count": len(cases),
            },
            "output": {
                "raw_evidence_path": _repo_relative(
                    repo_root,
                    raw_path,
                ),
                "raw_evidence_sha256": raw_sha256,
                "record_count": len(records),
                "safe_count": safe_count,
                "unsafe_count": unsafe_count,
            },
            "schema_binding": {
                "path": _repo_relative(
                    repo_root,
                    schema_path,
                ),
                "sha256": schema_sha256,
            },
            "authority_boundary": dict(
                AUTHORITY_BOUNDARY
            ),
        }

        _validate_manifest_schema(
            manifest,
            schema_path,
        )
        _write_json_atomic(
            manifest_path,
            manifest,
        )

    except RunnerError as exc:
        if stale_paths:
            try:
                _remove_paths(stale_paths)

            except Exception:
                pass

        print(
            f"ERROR: {exc}",
            file=sys.stderr,
        )
        return 1

    except Exception as exc:  # noqa: BLE001
        if stale_paths:
            try:
                _remove_paths(stale_paths)

            except Exception:
                pass

        print(
            "ERROR: unexpected producer failure: "
            f"{exc}",
            file=sys.stderr,
        )
        return 1

    print(
        "OK: current-run LlamaGuard raw evidence "
        f"written to {raw_path}"
    )
    print(
        "OK: LlamaGuard evaluator manifest written "
        f"to {manifest_path}"
    )
    print(
        "LlamaGuard classifications: "
        f"safe={manifest['output']['safe_count']} "
        f"unsafe={manifest['output']['unsafe_count']} "
        f"total={manifest['output']['record_count']}"
    )
    print(
        "Exact model revision: "
        f"{manifest['model']['revision']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

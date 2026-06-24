#!/usr/bin/env python3
"""Build a current-run canonical LlamaGuard external summary.

Input:

    PULSE_safe_pack_v0/artifacts/external/llamaguard_raw.jsonl

Each non-empty JSONL record must contain:

    {
      "input": "...",
      "output": "...",
      "llamaguard": {
        "label": "safe" | "unsafe",
        "categories": ["..."]
      }
    }

Output:

    PULSE_safe_pack_v0/artifacts/external/llamaguard_summary.json

The produced artifact conforms to external_summary_v1 and remains
non-authoritative. It does not create an attestation, materialize gates,
modify status.json, or replace check_gates.py.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker


TOOL_NAME = "llamaguard"
ADAPTER_NAME = "llamaguard_ingest"
ADAPTER_VERSION = "1.0.0"

SUMMARY_SCHEMA_VERSION = "external_summary_v1"
SUMMARY_SCHEMA_REL = (
    "PULSE_safe_pack_v0/schemas/"
    "external_summary_v1.schema.json"
)
THRESHOLDS_REL = (
    "PULSE_safe_pack_v0/profiles/external_thresholds.yaml"
)
THRESHOLD_KEY = "llamaguard_violation_rate_max"

EXTERNAL_DIR_REL = "PULSE_safe_pack_v0/artifacts/external"
RAW_REL = f"{EXTERNAL_DIR_REL}/llamaguard_raw.jsonl"
SUMMARY_REL = f"{EXTERNAL_DIR_REL}/llamaguard_summary.json"

AUTHORITY_BOUNDARY = (
    "This external summary does not define release authority. "
    "It is recorded evidence that may be folded into status.json "
    "only after schema, identity, signer, and policy validation."
)

GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)
SIGNER_IDENTITY_RE = re.compile(
    r"^repo:"
    r"(?P<repository>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)"
    r":workflow:"
    r"(?P<workflow>[A-Za-z0-9_.\-/]+\.ya?ml)$"
)
WILDCARD_TOKENS = ("*", "?", "[", "]")

STALE_OUTPUTS = (
    "llamaguard_summary.json",
    "llamaguard_summary.jsonl",
    "llamaguard_summary.envelope.json",
    "llamaguard_summary.bundle.json",
    "llamaguard_summary.attestation.json",
    "llamaguard_attestation_verifier_v1.json",
)


class ProducerError(ValueError):
    """Fail-closed producer error."""


class UniqueYamlLoader(yaml.SafeLoader):
    """YAML loader that rejects duplicate mapping keys."""


def _yaml_mapping(
    loader: UniqueYamlLoader,
    node: Any,
    deep: bool = False,
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key_node, value_node in node.value:
        key = loader.construct_object(
            key_node,
            deep=deep,
        )

        if key in result:
            raise ProducerError(
                f"duplicate YAML key {key!r}"
            )

        result[key] = loader.construct_object(
            value_node,
            deep=deep,
        )

    return result


UniqueYamlLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _yaml_mapping,
)


def _json_object(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key, value in pairs:
        if key in result:
            raise ProducerError(
                f"duplicate JSON key {key!r}"
            )

        result[key] = value

    return result


def _reject_nonfinite(value: str) -> None:
    raise ProducerError(
        f"non-finite JSON constant {value!r}"
    )


def _require_finite_json_tree(
    value: Any,
    label: str,
) -> None:
    """Reject every non-finite number in a parsed JSON tree."""

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
            raise ProducerError(
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

    raise ProducerError(
        f"{label} contains an unsupported JSON value"
    )


def _require_text(
    value: Any,
    label: str,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProducerError(
            f"{label} must be a non-empty string"
        )

    return value.strip()


def _resolve(
    repo_root: Path,
    supplied: Path,
) -> Path:
    """Return a lexical absolute path without following symlinks."""

    candidate = (
        supplied
        if supplied.is_absolute()
        else repo_root / supplied
    )

    return Path(os.path.abspath(candidate))


def _require_inside(
    path: Path,
    parent: Path,
    label: str,
) -> None:
    try:
        path.resolve().relative_to(
            parent.resolve()
        )

    except ValueError as exc:
        raise ProducerError(
            f"{label} must remain inside {parent}"
        ) from exc


def _require_regular_file(
    path: Path,
    label: str,
) -> None:
    if path.is_symlink() or not path.is_file():
        raise ProducerError(
            f"{label} must be a regular non-symlink file: "
            f"{path}"
        )


def _require_canonical_path(
    actual: Path,
    expected: Path,
    label: str,
) -> None:
    if (
        Path(os.path.abspath(actual))
        != Path(os.path.abspath(expected))
    ):
        raise ProducerError(
            f"{label} must use canonical path "
            f"{expected}"
        )


def _repo_relative(
    repo_root: Path,
    path: Path,
) -> str:
    try:
        return (
            path.resolve()
            .relative_to(repo_root.resolve())
            .as_posix()
        )

    except ValueError as exc:
        raise ProducerError(
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


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_json(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")

    return _sha256_bytes(encoded)


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

    except ProducerError:
        raise

    except Exception as exc:
        raise ProducerError(
            f"{label} is not valid JSON: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise ProducerError(
            f"{label} must be a JSON object"
        )

    _require_finite_json_tree(
        payload,
        label,
    )

    return payload


def _load_yaml_mapping(
    path: Path,
    label: str,
) -> dict[str, Any]:
    _require_regular_file(path, label)

    try:
        payload = yaml.load(
            path.read_text(encoding="utf-8"),
            Loader=UniqueYamlLoader,
        )

    except ProducerError:
        raise

    except Exception as exc:
        raise ProducerError(
            f"{label} is not valid YAML: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise ProducerError(
            f"{label} must be a YAML mapping"
        )

    return payload


def _normalize_generated_at(value: Any) -> str:
    text = _require_text(
        value,
        "generated_at",
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
        raise ProducerError(
            "generated_at must be an ISO-8601 "
            "date-time"
        ) from exc

    if timestamp.tzinfo is None:
        raise ProducerError(
            "generated_at must include a timezone"
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

    parts = repository.split("/")

    if (
        len(parts) != 2
        or not all(parts)
        or any(
            not re.fullmatch(
                r"[A-Za-z0-9_.-]+",
                part,
            )
            for part in parts
        )
    ):
        raise ProducerError(
            "repository must use '<owner>/<repo>' form"
        )

    return repository


def _validate_git_sha(value: Any) -> str:
    git_sha = _require_text(
        value,
        "git_sha",
    ).lower()

    if not GIT_SHA_RE.fullmatch(git_sha):
        raise ProducerError(
            "git_sha must be a concrete 40-hex SHA"
        )

    return git_sha


def _validate_signer_identity(
    value: Any,
    repository: str,
) -> str:
    identity = _require_text(
        value,
        "signer_identity",
    )

    if any(
        token in identity
        for token in WILDCARD_TOKENS
    ):
        raise ProducerError(
            "signer_identity must be exact and "
            "must not contain wildcards"
        )

    match = SIGNER_IDENTITY_RE.fullmatch(
        identity
    )

    if match is None:
        raise ProducerError(
            "signer_identity must use "
            "'repo:<owner>/<repo>:workflow:"
            "<exact-workflow-path>.yml' form"
        )

    if match.group("repository") != repository:
        raise ProducerError(
            "signer_identity repository must match "
            "the declared repository"
        )

    workflow = match.group("workflow")

    if not workflow.startswith(
        ".github/workflows/"
    ):
        raise ProducerError(
            "signer_identity workflow must use an "
            "exact .github/workflows/*.yml path"
        )

    workflow_path = Path(workflow)

    if (
        workflow_path.is_absolute()
        or ".." in workflow_path.parts
    ):
        raise ProducerError(
            "signer workflow path is unsafe"
        )

    return identity


def _load_threshold(
    thresholds_path: Path,
) -> float:
    payload = _load_yaml_mapping(
        thresholds_path,
        "external threshold policy",
    )

    value = payload.get(THRESHOLD_KEY)

    if isinstance(value, bool):
        raise ProducerError(
            f"{THRESHOLD_KEY} must be numeric"
        )

    try:
        threshold = float(value)

    except (TypeError, ValueError) as exc:
        raise ProducerError(
            f"{THRESHOLD_KEY} must be numeric"
        ) from exc

    if not math.isfinite(threshold):
        raise ProducerError(
            f"{THRESHOLD_KEY} must be finite"
        )

    if threshold < 0.0 or threshold > 1.0:
        raise ProducerError(
            f"{THRESHOLD_KEY} must be between 0 and 1"
        )

    return threshold


def _read_llamaguard_jsonl(
    path: Path,
) -> tuple[int, int, dict[str, int]]:
    _require_regular_file(
        path,
        "LlamaGuard raw evidence",
    )

    total = 0
    unsafe = 0
    category_counts: dict[str, int] = {}

    try:
        handle = path.open(
            "r",
            encoding="utf-8",
            errors="strict",
        )

    except OSError as exc:
        raise ProducerError(
            f"could not open LlamaGuard raw evidence: "
            f"{exc}"
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
                record = json.loads(
                    text,
                    object_pairs_hook=_json_object,
                    parse_constant=_reject_nonfinite,
                )

            except ProducerError as exc:
                raise ProducerError(
                    f"LlamaGuard raw evidence line "
                    f"{line_number}: {exc}"
                ) from exc

            except Exception as exc:
                raise ProducerError(
                    f"LlamaGuard raw evidence line "
                    f"{line_number} is not valid JSON: "
                    f"{exc}"
                ) from exc

            if not isinstance(record, dict):
                raise ProducerError(
                    f"LlamaGuard raw evidence line "
                    f"{line_number} must be an object"
                )

            _require_finite_json_tree(
                record,
                (
                    "LlamaGuard raw evidence line "
                    f"{line_number}"
                ),
            )

            if not isinstance(
                record.get("input"),
                str,
            ):
                raise ProducerError(
                    f"LlamaGuard raw evidence line "
                    f"{line_number}.input must be a string"
                )

            if not isinstance(
                record.get("output"),
                str,
            ):
                raise ProducerError(
                    f"LlamaGuard raw evidence line "
                    f"{line_number}.output must be a string"
                )

            classification = record.get(
                "llamaguard"
            )

            if not isinstance(
                classification,
                dict,
            ):
                raise ProducerError(
                    f"LlamaGuard raw evidence line "
                    f"{line_number}.llamaguard "
                    "must be an object"
                )

            label_raw = classification.get(
                "label"
            )

            if not isinstance(label_raw, str):
                raise ProducerError(
                    f"LlamaGuard raw evidence line "
                    f"{line_number}.llamaguard.label "
                    "must be a string"
                )

            label = label_raw.strip().lower()

            if label not in {"safe", "unsafe"}:
                raise ProducerError(
                    f"LlamaGuard raw evidence line "
                    f"{line_number}.llamaguard.label "
                    "must be 'safe' or 'unsafe'"
                )

            categories_raw = classification.get(
                "categories",
                [],
            )

            if not isinstance(
                categories_raw,
                list,
            ):
                raise ProducerError(
                    f"LlamaGuard raw evidence line "
                    f"{line_number}.llamaguard."
                    "categories must be an array"
                )

            categories: set[str] = set()

            for category_raw in categories_raw:
                if (
                    not isinstance(
                        category_raw,
                        str,
                    )
                    or not category_raw.strip()
                ):
                    raise ProducerError(
                        f"LlamaGuard raw evidence line "
                        f"{line_number}.llamaguard."
                        "categories entries must be "
                        "non-empty strings"
                    )

                categories.add(
                    category_raw.strip()
                )

            total += 1

            if label == "unsafe":
                unsafe += 1

                for category in categories:
                    category_counts[category] = (
                        category_counts.get(
                            category,
                            0,
                        )
                        + 1
                    )

    if total == 0:
        raise ProducerError(
            "LlamaGuard raw evidence must contain "
            "at least one classification"
        )

    return total, unsafe, category_counts


def _clear_stale_outputs(
    external_dir: Path,
) -> None:
    external_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for filename in STALE_OUTPUTS:
        path = external_dir / filename

        if not path.exists() and not path.is_symlink():
            continue

        if path.is_dir() and not path.is_symlink():
            raise ProducerError(
                f"stale output path is a directory: "
                f"{path}"
            )

        path.unlink()

    for temp_path in external_dir.glob(
        ".llamaguard_summary.*.tmp"
    ):
        if temp_path.is_dir() and not temp_path.is_symlink():
            raise ProducerError(
                f"temporary output path is a directory: "
                f"{temp_path}"
            )

        temp_path.unlink()


def _validate_summary_schema(
    summary: dict[str, Any],
    schema_path: Path,
) -> None:
    schema = _load_json_object(
        schema_path,
        "external summary schema",
    )

    try:
        Draft202012Validator.check_schema(
            schema
        )

    except Exception as exc:
        raise ProducerError(
            f"external summary schema is invalid: "
            f"{exc}"
        ) from exc

    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    )

    errors = sorted(
        validator.iter_errors(summary),
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

    raise ProducerError(
        "generated external summary failed schema "
        "validation:\n - "
        + "\n - ".join(formatted)
    )


def _write_json_atomic(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temp_name = tempfile.mkstemp(
        prefix=".llamaguard_summary.",
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
            json.dump(
                payload,
                handle,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
                allow_nan=False,
            )

            handle.write("\n")
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


def _build_summary(
    *,
    repo_root: Path,
    raw_path: Path,
    dataset_path: Path,
    evaluator_manifest_path: Path | None,
    schema_path: Path,
    thresholds_path: Path,
    run_id: str,
    generated_at: str,
    release_candidate: str,
    git_sha: str,
    repository: str,
    signer_identity: str,
    tool_version: str,
    adapter_version: str,
) -> dict[str, Any]:
    total, unsafe, category_counts = (
        _read_llamaguard_jsonl(
            raw_path
        )
    )

    threshold = _load_threshold(
        thresholds_path
    )

    violation_rate = unsafe / total
    passed = violation_rate <= threshold

    raw_sha = _sha256_file(raw_path)
    dataset_sha = _sha256_file(dataset_path)
    adapter_path = Path(__file__).resolve()
    adapter_sha = _sha256_file(adapter_path)

    evaluator_manifest_sha: str | None = None
    evaluator_source: str

    if evaluator_manifest_path is not None:
        evaluator_manifest_sha = _sha256_file(
            evaluator_manifest_path
        )
        evaluator_source = _repo_relative(
            repo_root,
            evaluator_manifest_path,
        )

    else:
        evaluator_source = _repo_relative(
            repo_root,
            adapter_path,
        )

    evaluator_digest = _sha256_json(
        {
            "tool": TOOL_NAME,
            "tool_version": tool_version,
            "adapter": ADAPTER_NAME,
            "adapter_version": adapter_version,
            "adapter_sha256": adapter_sha,
            "evaluator_manifest_sha256": (
                evaluator_manifest_sha
            ),
        }
    )

    subject_digest = _sha256_bytes(
        git_sha.encode("utf-8")
    )

    run_token = _sha256_bytes(
        run_id.encode("utf-8")
    )[:12]

    summary_id = (
        "pulse_external_llamaguard_"
        f"{git_sha[:12]}_"
        f"{run_token}_"
        f"{raw_sha[:12]}"
    )

    raw_relative = _repo_relative(
        repo_root,
        raw_path,
    )

    dataset_relative = _repo_relative(
        repo_root,
        dataset_path,
    )

    reason = (
        "LlamaGuard violation rate "
        f"{violation_rate:.12g} "
        f"{'<=' if passed else '>'} "
        f"canonical threshold {threshold:.12g}."
    )

    summary: dict[str, Any] = {
        "schema_version": (
            SUMMARY_SCHEMA_VERSION
        ),
        "summary_id": summary_id,
        "tool": {
            "name": TOOL_NAME,
            "version": tool_version,
            "adapter": ADAPTER_NAME,
            "adapter_version": adapter_version,
        },
        "run": {
            "run_id": run_id,
            "generated_at": generated_at,
            "dataset_digest": dataset_sha,
            "evaluator_digest": evaluator_digest,
            "model_id": release_candidate,
        },
        "subject": {
            "kind": "release_candidate",
            "id": release_candidate,
            "digest_algorithm": "sha256",
            "digest": subject_digest,
        },
        "metrics": [
            {
                "key": (
                    "llamaguard_violation_rate"
                ),
                "value": violation_rate,
                "unit": "rate",
                "threshold": threshold,
                "comparator": "lte",
                "passed": passed,
                "severity": "critical",
                "notes": (
                    f"{unsafe} unsafe classification(s) "
                    f"across {total} current-run "
                    "LlamaGuard record(s)."
                ),
            }
        ],
        "threshold_ref": {
            "key": THRESHOLD_KEY,
            "version": "v0",
            "uri": THRESHOLDS_REL,
        },
        "evidence": {
            "raw_artifact_uri": raw_relative,
            "raw_artifact_digest": raw_sha,
        },
        "signing": {
            "mode": "github-attestation",
            "identity": signer_identity,
        },
        "result": {
            "passed": passed,
            "reason": reason,
            "release_contribution": "required",
        },
        "authority_boundary": (
            AUTHORITY_BOUNDARY
        ),
        "extensions": {
            "repository": repository,
            "source_commit": git_sha,
            "dataset_path": dataset_relative,
            "evaluator_source": evaluator_source,
            "adapter_sha256": adapter_sha,
            "classification_counts": {
                "total": total,
                "safe": total - unsafe,
                "unsafe": unsafe,
                "by_category": dict(
                    sorted(
                        category_counts.items()
                    )
                ),
            },
            "producer_boundary": {
                "creates_release_authority": False,
                "materializes_status": False,
                "materializes_release_required": False,
                "creates_attestation": False,
                "replaces_check_gates": False,
            },
        },
    }

    _validate_summary_schema(
        summary,
        schema_path,
    )

    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build a canonical current-run "
            "LlamaGuard external_summary_v1 "
            "artifact."
        )
    )

    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root.",
    )
    parser.add_argument(
        "--in",
        dest="raw_input",
        default=RAW_REL,
        help=(
            "Canonical current-run LlamaGuard "
            "JSONL evidence."
        ),
    )
    parser.add_argument(
        "--dataset",
        default=None,
        help=(
            "Dataset or prompt-set file. "
            "Defaults to the raw evidence file."
        ),
    )
    parser.add_argument(
        "--evaluator-manifest",
        default=None,
        help=(
            "Optional evaluator configuration or "
            "manifest file included in evaluator "
            "digest derivation."
        ),
    )
    parser.add_argument(
        "--out",
        default=SUMMARY_REL,
        help="Canonical output summary path.",
    )
    parser.add_argument(
        "--schema",
        default=SUMMARY_SCHEMA_REL,
        help="Bundled canonical external summary schema.",
    )
    parser.add_argument(
        "--thresholds",
        default=THRESHOLDS_REL,
        help="Canonical external threshold policy.",
    )
    parser.add_argument(
        "--run-id",
        default=os.getenv("PULSE_RUN_KEY"),
        help="Current PULSE run key.",
    )
    parser.add_argument(
        "--generated-at",
        default=os.getenv("PULSE_CREATED_UTC"),
        help="Current-run UTC date-time.",
    )
    parser.add_argument(
        "--release-candidate",
        default=os.getenv(
            "PULSE_RELEASE_CANDIDATE"
        ),
        help="Current release-candidate identity.",
    )
    parser.add_argument(
        "--git-sha",
        default=os.getenv("GITHUB_SHA"),
        help="Current concrete 40-hex commit SHA.",
    )
    parser.add_argument(
        "--repository",
        default=os.getenv("GITHUB_REPOSITORY"),
        help="Current repository in owner/name form.",
    )
    parser.add_argument(
        "--signer-identity",
        default=os.getenv(
            "PULSE_EXTERNAL_SIGNER_IDENTITY"
        ),
        help=(
            "Exact GitHub workflow signer identity."
        ),
    )
    parser.add_argument(
        "--tool-version",
        default=os.getenv(
            "LLAMAGUARD_VERSION"
        ),
        help="Concrete LlamaGuard version.",
    )
    parser.add_argument(
        "--adapter-version",
        default=ADAPTER_VERSION,
        help="Adapter version.",
    )

    return parser


def main(
    argv: list[str] | None = None,
) -> int:
    args = _parser().parse_args(argv)

    try:
        repo_root = Path(
            args.repo_root
        ).resolve()

        if not repo_root.is_dir():
            raise ProducerError(
                f"repository root is not a directory: "
                f"{repo_root}"
            )

        external_dir = (
            repo_root / EXTERNAL_DIR_REL
        ).resolve()

        output_path = _resolve(
            repo_root,
            Path(args.out),
        )

        canonical_output = (
            repo_root / SUMMARY_REL
        ).resolve()

        _require_canonical_path(
            output_path,
            canonical_output,
            "output summary",
        )

        _require_inside(
            output_path,
            repo_root,
            "output summary",
        )

        # Clear stale generated evidence before any
        # current-run summary admission attempt.
        _clear_stale_outputs(
            external_dir
        )

        raw_path = _resolve(
            repo_root,
            Path(args.raw_input),
        )

        canonical_raw = (
            repo_root / RAW_REL
        ).resolve()

        _require_canonical_path(
            raw_path,
            canonical_raw,
            "LlamaGuard raw evidence",
        )

        _require_inside(
            raw_path,
            external_dir,
            "LlamaGuard raw evidence",
        )

        _require_regular_file(
            raw_path,
            "LlamaGuard raw evidence",
        )

        dataset_path = (
            raw_path
            if args.dataset is None
            else _resolve(
                repo_root,
                Path(args.dataset),
            )
        )

        _require_inside(
            dataset_path,
            repo_root,
            "dataset",
        )

        _require_regular_file(
            dataset_path,
            "dataset",
        )

        evaluator_manifest_path: Path | None = None

        if args.evaluator_manifest is not None:
            evaluator_manifest_path = _resolve(
                repo_root,
                Path(args.evaluator_manifest),
            )

            _require_inside(
                evaluator_manifest_path,
                repo_root,
                "evaluator manifest",
            )

            _require_regular_file(
                evaluator_manifest_path,
                "evaluator manifest",
            )

        schema_path = _resolve(
            repo_root,
            Path(args.schema),
        )

        _require_canonical_path(
            schema_path,
            (
                repo_root
                / SUMMARY_SCHEMA_REL
            ).resolve(),
            "external summary schema",
        )

        thresholds_path = _resolve(
            repo_root,
            Path(args.thresholds),
        )

        _require_canonical_path(
            thresholds_path,
            (
                repo_root
                / THRESHOLDS_REL
            ).resolve(),
            "external threshold policy",
        )

        run_id = _require_text(
            args.run_id,
            "run_id",
        )

        generated_at = (
            _normalize_generated_at(
                args.generated_at
            )
        )

        release_candidate = _require_text(
            args.release_candidate,
            "release_candidate",
        )

        git_sha = _validate_git_sha(
            args.git_sha
        )

        repository = _validate_repository(
            args.repository
        )

        signer_identity = (
            _validate_signer_identity(
                args.signer_identity,
                repository,
            )
        )

        tool_version = _require_text(
            args.tool_version,
            "tool_version",
        )

        adapter_version = _require_text(
            args.adapter_version,
            "adapter_version",
        )

        summary = _build_summary(
            repo_root=repo_root,
            raw_path=raw_path,
            dataset_path=dataset_path,
            evaluator_manifest_path=(
                evaluator_manifest_path
            ),
            schema_path=schema_path,
            thresholds_path=thresholds_path,
            run_id=run_id,
            generated_at=generated_at,
            release_candidate=(
                release_candidate
            ),
            git_sha=git_sha,
            repository=repository,
            signer_identity=signer_identity,
            tool_version=tool_version,
            adapter_version=adapter_version,
        )

        _write_json_atomic(
            output_path,
            summary,
        )

    except ProducerError as exc:
        print(
            f"ERROR: {exc}",
            file=sys.stderr,
        )
        return 1

    except Exception as exc:  # noqa: BLE001
        print(
            f"ERROR: unexpected producer failure: "
            f"{exc}",
            file=sys.stderr,
        )
        return 1

    metric = summary["metrics"][0]
    passed = summary["result"]["passed"]

    print(
        "OK: canonical LlamaGuard external summary "
        f"written to {output_path}"
    )
    print(
        "LlamaGuard current-run result: "
        f"value={metric['value']} "
        f"threshold={metric['threshold']} "
        f"passed={passed}"
    )

    if passed is not True:
        print(
            "ERROR: LlamaGuard current-run evidence "
            "exceeds the canonical threshold",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Verify PULSE Artifact Provenance Binding v0."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path, PureWindowsPath
from typing import Any, Dict, List


SCHEMA_ID = "pulse.artifact_provenance_binding.v0"


class BindingMismatch(RuntimeError):
    """Raised when an artifact relation does not match the binding."""


class BindingMalformed(RuntimeError):
    """Raised when a binding or artifact cannot be read as required."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_canonical_json(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise BindingMalformed(f"missing bound artifact: {path}")

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise BindingMalformed(f"missing binding: {path}")

    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise BindingMalformed(f"expected top-level JSON object in {path}")

    return obj


def without_digest_field(value: Dict[str, Any], field_name: str) -> Dict[str, Any]:
    out = dict(value)
    out.pop(field_name, None)
    return out


def get_path(obj: Dict[str, Any], dotted: str) -> Any:
    current: Any = obj

    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            raise BindingMalformed(f"missing binding field: {dotted}")
        current = current[part]

    return current


def ensure_inside_reviewed_root(
    candidate: Path,
    *,
    reviewed_root: Path,
    label: str,
) -> Path:
    resolved = candidate.resolve()

    try:
        resolved.relative_to(reviewed_root)
    except ValueError as exc:
        raise BindingMalformed(
            f"{label} resolves outside reviewed repository root: {candidate}"
        ) from exc

    return resolved


def resolve_binding_path(binding_arg: Path, *, reviewed_root: Path) -> Path:
    candidate = binding_arg if binding_arg.is_absolute() else reviewed_root / binding_arg

    return ensure_inside_reviewed_root(
        candidate,
        reviewed_root=reviewed_root,
        label="binding path",
    )


def reject_non_portable_subject_path(path_text: str, *, label: str) -> None:
    if not path_text.strip():
        raise BindingMalformed(f"{label} is empty")

    if path_text != path_text.strip():
        raise BindingMalformed(f"{label} contains leading or trailing whitespace")

    if "\\" in path_text:
        raise BindingMalformed(
            f"{label} must be a POSIX-style repository-relative path"
        )

    windows_path = PureWindowsPath(path_text)
    if windows_path.drive or windows_path.is_absolute():
        raise BindingMalformed(f"{label} must be repository-relative")

    if Path(path_text).is_absolute():
        raise BindingMalformed(f"{label} must be repository-relative")


def resolve_bound_path(
    path_text: str,
    *,
    reviewed_root: Path,
    label: str,
) -> Path:
    reject_non_portable_subject_path(path_text, label=label)

    path = Path(path_text)

    if path_text.startswith("inline:"):
        raise BindingMalformed(f"{label} is inline but a file path is required")

    return ensure_inside_reviewed_root(
        reviewed_root / path,
        reviewed_root=reviewed_root,
        label=label,
    )


def recompute_inline_hash(binding: Dict[str, Any], inline_path: str) -> str:
    if inline_path == "inline:authority_carrier.workflow_effective_required_gate_set":
        obj = get_path(binding, "authority_carrier.workflow_effective_required_gate_set")
        if not isinstance(obj, dict):
            raise BindingMalformed("workflow_effective_required_gate_set is not an object")

        return sha256_canonical_json(without_digest_field(obj, "sha256"))

    if inline_path == "inline:authority_carrier.strict_ci_gate_enforcement":
        obj = get_path(binding, "authority_carrier.strict_ci_gate_enforcement")
        if not isinstance(obj, dict):
            raise BindingMalformed("strict_ci_gate_enforcement is not an object")

        return sha256_canonical_json(without_digest_field(obj, "sha256"))

    raise BindingMalformed(f"unsupported inline binding subject: {inline_path}")


def assert_equal(label: str, expected: str, actual: str) -> None:
    if expected != actual:
        raise BindingMismatch(f"{label} mismatch: expected {expected}, got {actual}")


def verify_file_field(
    binding: Dict[str, Any],
    *,
    reviewed_root: Path,
    path_field: str,
    sha_field: str,
) -> None:
    path_text = get_path(binding, path_field)
    expected = get_path(binding, sha_field)

    if not isinstance(path_text, str) or not isinstance(expected, str):
        raise BindingMalformed(f"invalid path/hash fields: {path_field}, {sha_field}")

    actual = sha256_file(
        resolve_bound_path(
            path_text,
            reviewed_root=reviewed_root,
            label=path_field,
        )
    )

    assert_equal(path_field, expected, actual)


def verify_binding_hash(binding: Dict[str, Any]) -> None:
    expected = binding.get("binding_hash")
    if not isinstance(expected, str) or not expected:
        raise BindingMalformed("missing binding_hash")

    actual = sha256_canonical_json(without_digest_field(binding, "binding_hash"))
    assert_equal("binding_hash", expected, actual)


def verify_inline_hashes(binding: Dict[str, Any]) -> None:
    gate_set = get_path(binding, "authority_carrier.workflow_effective_required_gate_set")
    if not isinstance(gate_set, dict):
        raise BindingMalformed("workflow_effective_required_gate_set is not an object")

    assert_equal(
        "workflow_effective_required_gate_set.sha256",
        str(gate_set.get("sha256")),
        sha256_canonical_json(without_digest_field(gate_set, "sha256")),
    )

    enforcement = get_path(binding, "authority_carrier.strict_ci_gate_enforcement")
    if not isinstance(enforcement, dict):
        raise BindingMalformed("strict_ci_gate_enforcement is not an object")

    assert_equal(
        "strict_ci_gate_enforcement.sha256",
        str(enforcement.get("sha256")),
        sha256_canonical_json(without_digest_field(enforcement, "sha256")),
    )


def verify_binding_subjects(
    binding: Dict[str, Any],
    *,
    reviewed_root: Path,
) -> None:
    subjects = binding.get("binding_subjects")

    if not isinstance(subjects, list) or not subjects:
        raise BindingMalformed("binding_subjects must be a non-empty list")

    for idx, subject in enumerate(subjects):
        if not isinstance(subject, dict):
            raise BindingMalformed(f"binding_subjects[{idx}] is not an object")

        role = subject.get("role")
        path_text = subject.get("path")
        expected = subject.get("sha256")

        if not isinstance(role, str) or not isinstance(path_text, str):
            raise BindingMalformed(f"binding_subjects[{idx}] has invalid fields")

        if not isinstance(expected, str):
            raise BindingMalformed(f"binding_subjects[{idx}] has invalid fields")

        if path_text.startswith("inline:"):
            actual = recompute_inline_hash(binding, path_text)
        else:
            actual = sha256_file(
                resolve_bound_path(
                    path_text,
                    reviewed_root=reviewed_root,
                    label=f"binding_subjects[{idx}].path",
                )
            )

        assert_equal(f"binding_subjects[{idx}] {role}", expected, actual)


def verify_binding(binding_path: Path, *, repo_root: Path | None = None) -> None:
    reviewed_root = (repo_root or Path.cwd()).resolve()

    if not reviewed_root.is_dir():
        raise BindingMalformed(f"reviewed repository root is not a directory: {reviewed_root}")

    resolved_binding_path = resolve_binding_path(
        binding_path,
        reviewed_root=reviewed_root,
    )

    binding = read_json(resolved_binding_path)

    if binding.get("schema_id") != SCHEMA_ID:
        raise BindingMalformed("unsupported schema_id")

    verify_file_field(
        binding,
        reviewed_root=reviewed_root,
        path_field="authority_carrier.status_json.path",
        sha_field="authority_carrier.status_json.sha256",
    )
    verify_file_field(
        binding,
        reviewed_root=reviewed_root,
        path_field="authority_carrier.declared_gate_policy.path",
        sha_field="authority_carrier.declared_gate_policy.sha256",
    )
    verify_file_field(
        binding,
        reviewed_root=reviewed_root,
        path_field="authority_carrier.release_decision.path",
        sha_field="authority_carrier.release_decision.sha256",
    )
    verify_file_field(
        binding,
        reviewed_root=reviewed_root,
        path_field="reader_carrier.quality_ledger.path",
        sha_field="reader_carrier.quality_ledger.sha256",
    )
    verify_file_field(
        binding,
        reviewed_root=reviewed_root,
        path_field="trace_carrier.release_authority_manifest.path",
        sha_field="trace_carrier.release_authority_manifest.sha256",
    )

    verify_inline_hashes(binding)
    verify_binding_subjects(binding, reviewed_root=reviewed_root)
    verify_binding_hash(binding)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binding", required=True)
    parser.add_argument(
        "--repo-root",
        default=".",
        help=(
            "Reviewed repository root used to resolve binding subject paths. "
            "Defaults to the current working directory."
        ),
    )
    args = parser.parse_args(argv)

    try:
        verify_binding(
            Path(args.binding),
            repo_root=Path(args.repo_root),
        )
    except BindingMismatch as exc:
        print(f"MISMATCH: {exc}", file=sys.stderr)
        return 1
    except (BindingMalformed, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

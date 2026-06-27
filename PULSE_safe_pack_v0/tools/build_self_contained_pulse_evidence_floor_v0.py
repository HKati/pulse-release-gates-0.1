#!/usr/bin/env python3
"""Build the self-contained PULSE evidence floor v0 artifact.

The self-contained floor records what PULSE can prove from its own artifact-bound
mechanics without requiring a hosted external model runtime.

It is not a release decision engine. It does not write status.json, materialize
release_required gates, call check_gates.py, create attestation, or create
release authority.

Expected use: run after a status artifact and required-gate evidence exist.
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


SCHEMA_VERSION = "self_contained_pulse_evidence_floor_v0"
TOOL_VERSION = "0.1.0"

DEFAULT_OUT = (
    "PULSE_safe_pack_v0/artifacts/"
    "self_contained_pulse_evidence_floor_v0.json"
)
DEFAULT_STATUS = "PULSE_safe_pack_v0/artifacts/status.json"
DEFAULT_REQUIRED_EVIDENCE = (
    "PULSE_safe_pack_v0/artifacts/required_gate_evidence_v0.json"
)
DEFAULT_POLICY = "pulse_gate_policy_v0.yml"
DEFAULT_REGISTRY = "pulse_gate_registry_v0.yml"

GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)

AUTHORITY_BOUNDARY = {
    "creates_release_authority": False,
    "authorizes_release": False,
    "materializes_status": False,
    "materializes_release_required": False,
    "replaces_check_gates": False,
    "requires_external_model_runtime": False,
}


class FloorError(ValueError):
    """Fail-closed self-contained floor error."""


class UniqueYamlLoader(yaml.SafeLoader):
    pass


def _yaml_mapping(
    loader: UniqueYamlLoader,
    node: Any,
    deep: bool = False,
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)

        if key in result:
            raise FloorError(f"duplicate YAML key {key!r}")

        result[key] = loader.construct_object(value_node, deep=deep)

    return result


UniqueYamlLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _yaml_mapping,
)


def _json_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key, value in pairs:
        if key in result:
            raise FloorError(f"duplicate JSON key {key!r}")

        result[key] = value

    return result


def _bad_constant(value: str) -> None:
    raise FloorError(f"non-finite JSON constant {value!r}")


def _finite_tree(value: Any, label: str) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return

    if isinstance(value, float):
        if not math.isfinite(value):
            raise FloorError(f"{label} contains a non-finite number")
        return

    if isinstance(value, list):
        for index, item in enumerate(value):
            _finite_tree(item, f"{label}[{index}]")
        return

    if isinstance(value, dict):
        for key, item in value.items():
            _finite_tree(item, f"{label}.{key}")
        return

    raise FloorError(f"{label} contains unsupported JSON value")


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FloorError(f"{label} must be a non-empty string")
    return value.strip()


def _utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _normalize_utc(value: Any, label: str) -> str:
    text = _text(value, label)
    parsed = text[:-1] + "+00:00" if text.endswith("Z") else text

    try:
        stamp = dt.datetime.fromisoformat(parsed)
    except ValueError as exc:
        raise FloorError(f"{label} must be ISO-8601") from exc

    if stamp.tzinfo is None:
        raise FloorError(f"{label} must include timezone")

    return (
        stamp.astimezone(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _resolve(repo: Path, supplied: Path | str) -> Path:
    path = Path(supplied)
    candidate = path if path.is_absolute() else repo / path
    return Path(os.path.abspath(os.path.normpath(str(candidate))))


def _inside_repo(repo: Path, path: Path, label: str) -> None:
    try:
        path.resolve().relative_to(repo.resolve())
    except ValueError as exc:
        raise FloorError(f"{label} escapes repository root: {path}") from exc


def _reject_symlink_components(repo: Path, path: Path, label: str) -> None:
    _inside_repo(repo, path, label)
    relative = path.resolve().relative_to(repo.resolve())
    current = repo.resolve()

    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise FloorError(f"{label} traverses a symlink: {current}")


def _regular(repo: Path, path: Path, label: str) -> None:
    _reject_symlink_components(repo, path, label)

    if path.is_symlink() or not path.is_file():
        raise FloorError(f"{label} must be a regular non-symlink file: {path}")


def _relative(repo: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError as exc:
        raise FloorError(f"path escapes repository root: {path}") from exc


def _sha256(repo: Path, path: Path, label: str) -> str:
    _regular(repo, path, label)
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)

    return digest.hexdigest()


def _load_json(repo: Path, path: Path, label: str) -> dict[str, Any]:
    _regular(repo, path, label)

    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_json_pairs,
            parse_constant=_bad_constant,
        )
    except FloorError:
        raise
    except Exception as exc:
        raise FloorError(f"{label} is not valid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise FloorError(f"{label} must be a JSON object")

    _finite_tree(payload, label)
    return payload


def _load_yaml(repo: Path, path: Path, label: str) -> dict[str, Any]:
    _regular(repo, path, label)

    try:
        payload = yaml.load(
            path.read_text(encoding="utf-8"),
            Loader=UniqueYamlLoader,
        )
    except FloorError:
        raise
    except Exception as exc:
        raise FloorError(f"{label} is not valid YAML: {exc}") from exc

    if not isinstance(payload, dict):
        raise FloorError(f"{label} must be a YAML mapping")

    return payload


def _required_gates(policy: dict[str, Any]) -> list[str]:
    gates = policy.get("gates")
    if not isinstance(gates, dict):
        raise FloorError("policy.gates must be a mapping")

    required = gates.get("required")
    if not isinstance(required, list) or not required:
        raise FloorError("policy.gates.required must be a non-empty list")

    result: list[str] = []
    seen: set[str] = set()

    for item in required:
        if not isinstance(item, str) or not item.strip():
            raise FloorError("policy.gates.required entries must be strings")
        gate = item.strip()
        if gate in seen:
            raise FloorError(f"duplicate required gate {gate!r}")
        seen.add(gate)
        result.append(gate)

    return result


def _registry_ids(registry: dict[str, Any]) -> set[str]:
    candidates: Any = registry.get("gates")
    if candidates is None:
        candidates = registry.get("registry")

    ids: set[str] = set()

    if isinstance(candidates, dict):
        ids.update(str(key) for key in candidates if isinstance(key, str))
        for value in candidates.values():
            if isinstance(value, dict):
                gate_id = value.get("id") or value.get("gate_id")
                if isinstance(gate_id, str):
                    ids.add(gate_id)
    elif isinstance(candidates, list):
        for item in candidates:
            if isinstance(item, str):
                ids.add(item)
            elif isinstance(item, dict):
                gate_id = item.get("id") or item.get("gate_id")
                if isinstance(gate_id, str):
                    ids.add(gate_id)

    if not ids:
        raise FloorError("gate registry does not expose any gate IDs")

    return ids


def _status_gates(status: dict[str, Any]) -> dict[str, Any]:
    gates = status.get("gates")
    if not isinstance(gates, dict):
        raise FloorError("status.gates must be a mapping")
    return gates


def _status_metrics(status: dict[str, Any]) -> dict[str, Any]:
    metrics = status.get("metrics")
    if not isinstance(metrics, dict):
        raise FloorError("status.metrics must be a mapping")
    return metrics


def _verify_status_identity(
    status: dict[str, Any],
    *,
    git_sha: str,
    run_key: str,
) -> None:
    metrics = _status_metrics(status)

    status_sha = metrics.get("git_sha")
    if isinstance(status_sha, str) and status_sha.lower() != git_sha:
        raise FloorError("status.metrics.git_sha does not match current commit")

    status_run_key = metrics.get("run_key")
    if isinstance(status_run_key, str) and status_run_key != run_key:
        raise FloorError("status.metrics.run_key does not match current run_key")

    run_mode = str(metrics.get("run_mode", "")).lower()
    if run_mode and run_mode != "prod":
        raise FloorError("self-contained floor requires prod run_mode when present")


def _check_required_gate_status(
    status: dict[str, Any],
    required: list[str],
) -> list[str]:
    gates = _status_gates(status)
    missing: list[str] = []

    for gate in required:
        if gates.get(gate) is not True:
            missing.append(gate)

    return missing


def _check_required_evidence(
    evidence: dict[str, Any],
    required: list[str],
    *,
    git_sha: str,
    run_key: str,
) -> None:
    if evidence.get("schema_version") != "required_gate_evidence_v0":
        raise FloorError("required-gate evidence schema_version mismatch")

    run = evidence.get("run_identity")
    if not isinstance(run, dict):
        raise FloorError("required-gate evidence run_identity must be an object")

    if run.get("git_sha") != git_sha:
        raise FloorError("required-gate evidence git_sha mismatch")
    if run.get("run_key") != run_key:
        raise FloorError("required-gate evidence run_key mismatch")

    gates = evidence.get("gates")
    if not isinstance(gates, dict):
        raise FloorError("required-gate evidence gates must be a mapping")

    missing = sorted(set(required) - set(gates))
    if missing:
        raise FloorError(f"required-gate evidence is missing gates: {missing}")

    failed = [
        gate
        for gate in required
        if not (
            isinstance(gates.get(gate), dict)
            and gates[gate].get("status") == "passed"
            and gates[gate].get("pass") is True
        )
    ]
    if failed:
        raise FloorError(f"required-gate evidence has non-passing gates: {failed}")


def _artifact(
    repo: Path,
    role: str,
    path: Path,
    required: bool = True,
) -> dict[str, Any]:
    return {
        "role": role,
        "path": _relative(repo, path),
        "sha256": _sha256(repo, path, role),
        "required": required,
        "available": True,
    }


def _check(
    check_id: str,
    details: str,
    *paths: str,
) -> dict[str, Any]:
    if not paths:
        raise FloorError(f"{check_id} must cite at least one evidence path")

    return {
        "check_id": check_id,
        "passed": True,
        "details": details,
        "evidence_paths": list(paths),
    }


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )
    temp = Path(temp_name)

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    payload,
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=False,
                    allow_nan=False,
                )
                + "\n"
            )
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(temp, path)
    except Exception:
        if temp.exists():
            temp.unlink()
        raise


def build_floor(
    *,
    repo: Path,
    status_path: Path,
    policy_path: Path,
    registry_path: Path,
    required_evidence_path: Path,
    repository: str,
    git_sha: str,
    run_key: str,
    workflow_ref: str,
    created_utc: str,
    external_model_status: str,
) -> dict[str, Any]:
    status = _load_json(repo, status_path, "status artifact")
    policy = _load_yaml(repo, policy_path, "gate policy")
    registry = _load_yaml(repo, registry_path, "gate registry")
    required_evidence = _load_json(
        repo,
        required_evidence_path,
        "required-gate evidence",
    )

    required = _required_gates(policy)
    registry_ids = _registry_ids(registry)

    unknown = sorted(set(required) - registry_ids)
    if unknown:
        raise FloorError(f"required gates missing from registry: {unknown}")

    _verify_status_identity(status, git_sha=git_sha, run_key=run_key)

    non_passing = _check_required_gate_status(status, required)
    if non_passing:
        raise FloorError(
            "status.gates required entries must be literal true: "
            f"{non_passing}"
        )

    _check_required_evidence(
        required_evidence,
        required,
        git_sha=git_sha,
        run_key=run_key,
    )

    status_rel = _relative(repo, status_path)
    policy_rel = _relative(repo, policy_path)
    registry_rel = _relative(repo, registry_path)
    required_evidence_rel = _relative(repo, required_evidence_path)

    artifacts = [
        _artifact(repo, "status", status_path),
        _artifact(repo, "gate_policy", policy_path),
        _artifact(repo, "gate_registry", registry_path),
        _artifact(repo, "required_gate_evidence", required_evidence_path),
    ]

    checks = [
        _check(
            "status_artifact_present_and_bound",
            "status.json is present as a regular artifact and identity checks passed.",
            status_rel,
        ),
        _check(
            "policy_and_registry_digest_bound",
            "gate policy and registry are present, digest-backed, and required gates are registry-backed.",
            policy_rel,
            registry_rel,
        ),
        _check(
            "required_gate_status_literal_true",
            "every policy gates.required entry is present in status.gates as literal true.",
            status_rel,
            policy_rel,
        ),
        _check(
            "required_gate_evidence_literal_pass",
            "required_gate_evidence_v0 covers every required gate with status=passed and pass=true.",
            required_evidence_rel,
        ),
        _check(
            "external_model_not_required_for_tier0",
            "Tier 0 proves the self-contained PULSE mechanism without claiming hosted external model evidence.",
            status_rel,
            policy_rel,
            registry_rel,
            required_evidence_rel,
        ),
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "created_utc": created_utc,
        "repository": repository,
        "git_sha": git_sha,
        "run_key": run_key,
        "workflow_ref": workflow_ref,
        "floor": {
            "tier": 0,
            "mode": "self_contained_pulse_evidence_floor",
            "description": (
                "Artifact-bound PULSE evidence floor built from self-contained "
                "schema, digest, run identity, policy, registry, status, and "
                "required-gate evidence checks."
            ),
        },
        "artifacts": artifacts,
        "self_contained_checks": checks,
        "external_model_evidence": {
            "status": external_model_status,
            "release_contribution": "none",
            "reason": (
                "The self-contained floor does not require a hosted external "
                "model runtime. External model evidence remains a separate "
                "conditional evidence lane."
            ),
        },
        "compute_admission": {
            "verdict": "ROUTE",
            "route": "self_contained_floor",
            "diagnostic_state": "OK",
            "reason": (
                "The available evidence is sufficient for Tier 0 self-contained "
                "PULSE mechanism proof; high-cost external runtime is not "
                "authorized by this artifact."
            ),
        },
        "authority_boundary": dict(AUTHORITY_BOUNDARY),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--status", default=DEFAULT_STATUS)
    parser.add_argument("--policy", default=DEFAULT_POLICY)
    parser.add_argument("--registry", default=DEFAULT_REGISTRY)
    parser.add_argument("--required-gate-evidence", default=DEFAULT_REQUIRED_EVIDENCE)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY"))
    parser.add_argument("--git-sha", default=os.getenv("GITHUB_SHA"))
    parser.add_argument("--run-key", default=os.getenv("PULSE_RUN_KEY"))
    parser.add_argument("--workflow-ref", default=os.getenv("GITHUB_WORKFLOW_REF"))
    parser.add_argument(
        "--created-utc",
        default=os.getenv("PULSE_CREATED_UTC") or _utc_now(),
    )
    parser.add_argument(
        "--external-model-status",
        default="not_required_for_tier0",
        choices=(
            "not_required_for_tier0",
            "optional_not_run",
            "unavailable_provider_blocked",
            "supplied_evidence_available",
            "hosted_full_runtime_available",
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    try:
        repo = _resolve(Path("."), args.repo_root)
        if repo.is_symlink() or not repo.is_dir():
            raise FloorError(f"repo-root must be a directory: {repo}")

        repository = _text(args.repository, "repository")
        if repository.count("/") != 1:
            raise FloorError("repository must use owner/name form")

        git_sha = _text(args.git_sha, "git_sha").lower()
        if not GIT_SHA_RE.fullmatch(git_sha):
            raise FloorError("git_sha must be a concrete 40-hex SHA")

        run_key = _text(args.run_key, "run_key")
        workflow_ref = _text(args.workflow_ref, "workflow_ref")
        created_utc = _normalize_utc(args.created_utc, "created_utc")

        status = _resolve(repo, args.status)
        policy = _resolve(repo, args.policy)
        registry = _resolve(repo, args.registry)
        required_evidence = _resolve(repo, args.required_gate_evidence)
        out = _resolve(repo, args.out)

        for path, label in (
            (status, "status path"),
            (policy, "policy path"),
            (registry, "registry path"),
            (required_evidence, "required-gate evidence path"),
            (out.parent, "output parent"),
        ):
            _reject_symlink_components(repo, path, label)

        floor = build_floor(
            repo=repo,
            status_path=status,
            policy_path=policy,
            registry_path=registry,
            required_evidence_path=required_evidence,
            repository=repository,
            git_sha=git_sha,
            run_key=run_key,
            workflow_ref=workflow_ref,
            created_utc=created_utc,
            external_model_status=args.external_model_status,
        )
        _write_json_atomic(out, floor)

    except FloorError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: unexpected self-contained floor failure: {exc}", file=sys.stderr)
        return 1

    print(f"OK: wrote self-contained PULSE evidence floor: {out}")
    print("Tier: 0")
    print("Authority boundary: self-contained floor != release authorization")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

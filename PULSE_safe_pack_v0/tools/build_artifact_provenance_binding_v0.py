#!/usr/bin/env python3
"""Build PULSE Artifact Provenance Binding v0."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

import yaml

SCHEMA_ID = "pulse.artifact_provenance_binding.v0"
SCHEMA_VERSION = "0.1.0"
PRODUCER_NAME = "build_artifact_provenance_binding_v0.py"
PRODUCER_VERSION = "0.1.0"

GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
VALID_RUN_MODES = {"demo", "core", "prod"}
VALID_RELEASE_DECISION_LABELS = {"FAIL", "STAGE-PASS", "PROD-PASS"}

class BindingBuildError(RuntimeError):
    """Raised when the binding cannot be built from the supplied artifacts."""


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


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise BindingBuildError(f"missing required artifact: {path}")
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_canonical_json(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise BindingBuildError(f"missing required JSON artifact: {path}")
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise BindingBuildError(f"expected top-level JSON object in {path}")
    return obj


def read_yaml(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise BindingBuildError(f"missing required YAML artifact: {path}")
    obj = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise BindingBuildError(f"expected top-level YAML object in {path}")
    return obj


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_str_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            out.append(text)
    return out


def parse_run_id_from_run_key(run_key: str) -> str:
    for part in run_key.split("|"):
        key, sep, value = part.partition("=")
        if sep and key == "GITHUB_RUN_ID" and value.strip():
            return value.strip()
    return ""


def extract_run_identity(status: Dict[str, Any]) -> Dict[str, str]:
    metrics = as_dict(status.get("metrics"))

    run_key = str(metrics.get("run_key") or status.get("run_key") or "").strip()
    run_id = str(metrics.get("run_id") or status.get("run_id") or "").strip()
    if not run_id and run_key:
        run_id = parse_run_id_from_run_key(run_key)

    git_sha = str(metrics.get("git_sha") or status.get("git_sha") or "").strip()
    run_mode = str(metrics.get("run_mode") or status.get("run_mode") or "").strip().lower()

    if not run_id:
        raise BindingBuildError("run_id is required")
    if not run_key:
        raise BindingBuildError("run_key is required")
    if not GIT_SHA_RE.fullmatch(git_sha):
        raise BindingBuildError("git_sha must be a 40-character lowercase hex commit SHA")
    if run_mode not in VALID_RUN_MODES:
        raise BindingBuildError("run_mode must be one of: demo, core, prod")

    return {
        "run_id": run_id,
        "run_key": run_key,
        "git_sha": git_sha,
        "run_mode": run_mode,
    }


def path_record(path: Path) -> str:
    return path.as_posix() if not path.is_absolute() else str(path)


def get_policy_gate_sets(policy: Dict[str, Any]) -> Dict[str, Any]:
    top_level = as_dict(policy.get("gates"))
    if top_level:
        return top_level
    nested = as_dict(as_dict(policy.get("policy")).get("gates"))
    if nested:
        return nested
    return {}


def dedupe_preserve_order(items: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def required_gate_set_from_policy_sets(
    gate_sets: Dict[str, Any], policy_sets: List[str]
) -> List[str]:
    gate_ids: List[str] = []
    for set_name in policy_sets:
        selected = as_str_list(gate_sets.get(set_name))
        if not selected:
            raise BindingBuildError(f"policy gate set is missing or empty: {set_name}")
        gate_ids.extend(selected)
    return dedupe_preserve_order(gate_ids)


def resolve_workflow_effective_gate_set(
    status: Dict[str, Any], policy: Dict[str, Any], cli_policy_sets: List[str]
) -> Dict[str, Any]:
    metrics = as_dict(status.get("metrics"))
    gate_sets = get_policy_gate_sets(policy)

    if cli_policy_sets:
        policy_sets = list(cli_policy_sets)
        gate_ids = required_gate_set_from_policy_sets(gate_sets, policy_sets)
        effective_source = "workflow-effective:" + "+".join(policy_sets)
    else:
        explicit = as_str_list(metrics.get("required_gates"))
        if explicit:
            policy_sets = []
            gate_ids = dedupe_preserve_order(explicit)
            effective_source = "metrics.required_gates"
        else:
            required_gate_set = metrics.get("required_gate_set")
            if isinstance(required_gate_set, str) and required_gate_set.strip():
                set_name = required_gate_set.strip()
                effective_source = f"metrics.required_gate_set:{set_name}"
            else:
                run_mode = str(metrics.get("run_mode", "")).strip().lower()
                set_name = "core_required" if run_mode in {"demo", "core"} else "required"
                effective_source = f"workflow-effective:{set_name}"
            policy_sets = [set_name]
            gate_ids = required_gate_set_from_policy_sets(gate_sets, policy_sets)

    if not gate_ids:
        raise BindingBuildError("workflow-effective required gate set is empty")

    gate_set = {
        "effective_source": effective_source,
        "policy_sets": policy_sets,
        "gate_ids": gate_ids,
    }
    gate_set["sha256"] = sha256_canonical_json(gate_set)
    return gate_set


def build_strict_ci_gate_enforcement(
    status: Dict[str, Any], gate_ids: List[str]
) -> Dict[str, Any]:
    gates = as_dict(status.get("gates"))
    allow = all(gates.get(gate_id) is True for gate_id in gate_ids)
    obj = {
        "source": "check_gates.py",
        "result": "allow" if allow else "block",
        "exit_code": 0 if allow else 1,
    }
    obj["sha256"] = sha256_canonical_json(obj)
    return obj


def extract_release_decision_label(release_decision: Dict[str, Any]) -> str:
    candidate_paths = [
        ("label",),
        ("release_level",),
        ("verdict",),
        ("decision",),
        ("release_decision", "label"),
        ("decision", "label"),
        ("release", "label"),
    ]
    for path in candidate_paths:
        current: Any = release_decision
        for part in path:
            if not isinstance(current, dict) or part not in current:
                current = None
                break
            current = current[part]
     if isinstance(current, str) and current.strip():
            label = current.strip()
            if label not in VALID_RELEASE_DECISION_LABELS:
                raise BindingBuildError(f"unsupported release decision label: {label}")
            return label
    raise BindingBuildError("release decision label cannot be read")


def build_binding(
    *,
    status_path: Path,
    policy_path: Path,
    ledger_path: Path,
    release_decision_path: Path,
    release_authority_manifest_path: Path,
    out_path: Path,
    policy_sets: List[str],
    created_utc: str | None = None,
) -> Dict[str, Any]:
    status = read_json(status_path)
    policy = read_yaml(policy_path)
    release_decision_json = read_json(release_decision_path)

    status_sha = sha256_file(status_path)
    policy_sha = sha256_file(policy_path)
    ledger_sha = sha256_file(ledger_path)
    release_decision_sha = sha256_file(release_decision_path)
    release_authority_manifest_sha = sha256_file(release_authority_manifest_path)

    required_gate_set = resolve_workflow_effective_gate_set(status, policy, policy_sets)
    strict_enforcement = build_strict_ci_gate_enforcement(
        status, as_str_list(required_gate_set.get("gate_ids"))
    )
    release_label = extract_release_decision_label(release_decision_json)

    run = extract_run_identity(status)
    
    binding = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "producer": {"name": PRODUCER_NAME, "version": PRODUCER_VERSION},
        "created_utc": created_utc or utc_now(),
        "run": run,
        "authority_carrier": {
            "status_json": {"path": path_record(status_path), "sha256": status_sha},
            "declared_gate_policy": {
                "path": path_record(policy_path),
                "sha256": policy_sha,
            },
            "workflow_effective_required_gate_set": required_gate_set,
            "strict_ci_gate_enforcement": strict_enforcement,
            "release_decision": {
                "path": path_record(release_decision_path),
                "producer": "materialize_release_decision.py",
                "label": release_label,
                "sha256": release_decision_sha,
            },
        },
        "reader_carrier": {
            "quality_ledger": {"path": path_record(ledger_path), "sha256": ledger_sha}
        },
        "trace_carrier": {
            "release_authority_manifest": {
                "path": path_record(release_authority_manifest_path),
                "sha256": release_authority_manifest_sha,
            }
        },
        "binding_subjects": [
            {"role": "status_json", "path": path_record(status_path), "sha256": status_sha},
            {
                "role": "declared_gate_policy",
                "path": path_record(policy_path),
                "sha256": policy_sha,
            },
            {
                "role": "workflow_effective_required_gate_set",
                "path": "inline:authority_carrier.workflow_effective_required_gate_set",
                "sha256": required_gate_set["sha256"],
            },
            {
                "role": "strict_ci_gate_enforcement",
                "path": "inline:authority_carrier.strict_ci_gate_enforcement",
                "sha256": strict_enforcement["sha256"],
            },
            {
                "role": "release_decision",
                "path": path_record(release_decision_path),
                "sha256": release_decision_sha,
            },
            {
                "role": "quality_ledger",
                "path": path_record(ledger_path),
                "sha256": ledger_sha,
            },
            {
                "role": "release_authority_manifest",
                "path": path_record(release_authority_manifest_path),
                "sha256": release_authority_manifest_sha,
            },
        ],
    }
    binding["binding_hash"] = sha256_canonical_json(binding)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(binding, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return binding


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--release-decision", required=True)
    parser.add_argument("--release-authority-manifest", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--policy-set", action="append", default=[])
    parser.add_argument("--created-utc", default=None)
    args = parser.parse_args(argv)

    try:
        build_binding(
            status_path=Path(args.status),
            policy_path=Path(args.policy),
            ledger_path=Path(args.ledger),
            release_decision_path=Path(args.release_decision),
            release_authority_manifest_path=Path(args.release_authority_manifest),
            out_path=Path(args.out),
            policy_sets=list(args.policy_set or []),
            created_utc=args.created_utc,
        )
    except BindingBuildError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

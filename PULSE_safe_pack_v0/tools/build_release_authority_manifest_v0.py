#!/usr/bin/env python3
"""Build a PULSE release_authority_v0.json audit manifest.

The manifest records the release-authority chain for one run:

- run identity
- input artifact hashes
- workflow-effective required gate set
- deterministic required-gate evaluation
- release decision record
- non-normative diagnostic context

This tool does not replace check_gates.py.
It does not change gate policy, status.json semantics, CI behavior, or
shadow-layer authority.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


CORE_DEFAULT_GATES = [
    "pass_controls_refusal",
    "pass_controls_sanit",
    "sanitization_effective",
    "q1_grounded_ok",
    "q4_slo_ok",
]


def _repo_root_from_tool() -> Path:
    # PULSE_safe_pack_v0/tools/<this file> -> repo root
    return Path(__file__).resolve().parents[2]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _load_json(path: Path) -> Any:
    try:
        return json.loads(_read_text(path))
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"failed to read JSON from {path}: {exc}") from exc


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _utc_now() -> str:
    return (
        _dt.datetime.now(tz=_dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _git_sha(root: Path) -> str:
    env_sha = os.environ.get("GITHUB_SHA")
    if env_sha and re.fullmatch(r"[0-9a-fA-F]{40}", env_sha):
        return env_sha.lower()

    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if re.fullmatch(r"[0-9a-fA-F]{40}", out):
            return out.lower()
    except Exception:  # noqa: BLE001
        pass

    return "0" * 40


def _parse_policy_minimal(path: Path) -> dict[str, Any]:
    """Parse the subset of pulse_gate_policy_v0.yml needed by this builder.

    Prefer PyYAML when available, but keep a small fallback parser so this tool
    remains usable in minimal environments.
    """
    text = _read_text(path)

    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text) or {}
        if isinstance(data, dict):
            return data
    except Exception:  # noqa: BLE001
        pass

    data: dict[str, Any] = {"policy": {}, "gates": {}}
    current_section: str | None = None
    current_gate_set: str | None = None

    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        if re.match(r"^[A-Za-z0-9_]+:\s*$", line):
            current_section = stripped[:-1]
            current_gate_set = None
            data.setdefault(current_section, {})
            continue

        if current_section == "policy":
            m = re.match(r"^\s{2}([A-Za-z0-9_]+):\s*(.+?)\s*$", line)
            if m:
                key, value = m.group(1), m.group(2).strip().strip('"').strip("'")
                data["policy"][key] = value
            continue

        if current_section == "gates":
            m_set = re.match(r"^\s{2}([A-Za-z0-9_]+):\s*$", line)
            if m_set:
                current_gate_set = m_set.group(1)
                data["gates"][current_gate_set] = []
                continue

            m_item = re.match(r"^\s{4}-\s*(\S+)\s*$", line)
            if m_item and current_gate_set:
                data["gates"][current_gate_set].append(m_item.group(1))

    return data


def _parse_registry_minimal(path: Path) -> dict[str, Any]:
    text = _read_text(path)
    version = "gate_registry_v0"

    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text) or {}
        if isinstance(data, dict):
            return data
    except Exception:  # noqa: BLE001
        pass

    for raw in text.splitlines():
        m = re.match(r"^version:\s*(.+?)\s*$", raw)
        if m:
            version = m.group(1).strip().strip('"').strip("'")
            break

    return {"version": version}


def _materialize_required_gates(
    policy: dict[str, Any],
    policy_set: str,
    explicit_required_gates: list[str],
) -> tuple[list[str], bool, str]:
    if explicit_required_gates:
        return list(dict.fromkeys(explicit_required_gates)), (
            "release_required" in explicit_required_gates
        ), "custom"

    gates = policy.get("gates") or {}
    if not isinstance(gates, dict):
        gates = {}

    def list_for(name: str) -> list[str]:
        value = gates.get(name) or []
        if not isinstance(value, list):
            return []
        return [str(v) for v in value]

    if policy_set == "required+release_required":
        required = list_for("required") + list_for("release_required")
        return list(dict.fromkeys(required)), True, policy_set

    if policy_set in {"core_required", "required", "release_required"}:
        required = list_for(policy_set)
        return list(dict.fromkeys(required)), policy_set == "release_required", policy_set

    if policy_set == "custom":
        return [], False, "custom"

    raise ValueError(f"unsupported policy set: {policy_set}")


def _advisory_gates(policy: dict[str, Any]) -> list[str]:
    gates = policy.get("gates") or {}
    if not isinstance(gates, dict):
        return []
    advisory = gates.get("advisory") or []
    if not isinstance(advisory, list):
        return []
    return [str(v) for v in advisory]


def _evaluate_required(status: dict[str, Any], required_gates: list[str]) -> tuple[dict[str, bool], list[str], list[str]]:
    gates = status.get("gates") or {}
    if not isinstance(gates, dict):
        gates = {}

    results: dict[str, bool] = {}
    failed: list[str] = []
    missing: list[str] = []

    for gate in required_gates:
        if gate not in gates:
            missing.append(gate)
            continue

        value = gates[gate]
        if value is True:
            results[gate] = True
        else:
            # Required PASS is strict literal true. Any present non-true value is
            # represented as false in the audit manifest.
            results[gate] = False
            failed.append(gate)

    return results, failed, missing


def _diagnostics(status: dict[str, Any], advisory: list[str]) -> dict[str, Any]:
    meta = status.get("meta") or {}
    status_meta_foldins: list[str] = []
    shadow_surfaces: list[dict[str, Any]] = []

    if isinstance(meta, dict):
        for key in sorted(meta):
            status_meta_foldins.append(f"meta.{key}")

        if "relational_gain_shadow" in meta:
            shadow_surfaces.append(
                {
                    "name": "relational_gain_shadow",
                    "role": "shadow",
                    "normative": False,
                }
            )

    gates = status.get("gates") or {}
    if not isinstance(gates, dict):
        gates = {}

    advisory_present = [gate for gate in advisory if gate in gates]

    return {
        "shadow_surfaces_present": shadow_surfaces,
        "shadow_surfaces_non_normative": True,
        "status_meta_foldins": status_meta_foldins,
        "advisory_gates_present": advisory_present,
        "publication_surfaces_present": [],
    }


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    root = _repo_root_from_tool()

    status_path = Path(args.status)
    policy_path = Path(args.policy)
    registry_path = Path(args.registry)
    evaluator_path = Path(args.evaluator)

    status = _load_json(status_path)
    if not isinstance(status, dict):
        raise ValueError("status.json must be a JSON object")

    policy = _parse_policy_minimal(policy_path)
    registry = _parse_registry_minimal(registry_path)

    required_gates, release_required_materialized, policy_set = _materialize_required_gates(
        policy,
        args.policy_set,
        args.required_gate,
    )

    if not required_gates:
        required_gates = CORE_DEFAULT_GATES if policy_set == "custom" else []
    if not required_gates:
        raise ValueError("effective required gate set is empty")

    results, failed, missing = _evaluate_required(status, required_gates)
    state = "FAIL" if failed or missing else "PASS"

    metrics = status.get("metrics") or {}
    if not isinstance(metrics, dict):
        metrics = {}

    policy_meta = policy.get("policy") or {}
    if not isinstance(policy_meta, dict):
        policy_meta = {}

    registry_version = registry.get("version", "gate_registry_v0")
    if not isinstance(registry_version, str):
        registry_version = str(registry_version)

    manifest = {
        "schema_version": "release_authority_v0",
        "created_utc": args.created_utc or _utc_now(),
        "run_identity": {
            "run_mode": str(args.run_mode or metrics.get("run_mode") or "core"),
            "workflow_name": args.workflow_name or os.environ.get("GITHUB_WORKFLOW") or "PULSE CI",
            "event_name": args.event_name or os.environ.get("GITHUB_EVENT_NAME") or "local",
            "ref": args.ref or os.environ.get("GITHUB_REF") or "local",
            "git_sha": args.git_sha or _git_sha(root),
        },
        "inputs": {
            "status_json": {
                "path": str(status_path),
                "sha256": _sha256(status_path),
            },
            "gate_policy": {
                "path": str(policy_path),
                "policy_id": str(policy_meta.get("id") or "pulse-gate-policy-v0"),
                "version": str(policy_meta.get("version") or ""),
                "sha256": _sha256(policy_path),
            },
            "gate_registry": {
                "path": str(registry_path),
                "version": registry_version,
                "sha256": _sha256(registry_path),
            },
            "evaluator": {
                "path": str(evaluator_path),
                "sha256": _sha256(evaluator_path),
            },
        },
        "authority": {
            "policy_set": policy_set,
            "effective_required_gates": required_gates,
            "release_required_materialized": release_required_materialized,
            "advisory_gates": _advisory_gates(policy),
        },
        "evaluation": {
            "evaluator": str(evaluator_path),
            "evaluator_sha256": _sha256(evaluator_path),
            "required_gate_results": results,
            "failed_required_gates": failed,
            "missing_required_gates": missing,
        },
        "decision": {
            "state": state,
            "fail_closed": True,
        },
        "diagnostics": _diagnostics(status, _advisory_gates(policy)),
    }

    return manifest


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    root = _repo_root_from_tool()

    parser = argparse.ArgumentParser(
        description="Build a release_authority_v0.json audit manifest."
    )
    parser.add_argument(
        "--status",
        default=str(root / "PULSE_safe_pack_v0" / "artifacts" / "status.json"),
    )
    parser.add_argument(
        "--policy",
        default=str(root / "pulse_gate_policy_v0.yml"),
    )
    parser.add_argument(
        "--registry",
        default=str(root / "pulse_gate_registry_v0.yml"),
    )
    parser.add_argument(
        "--evaluator",
        default=str(root / "PULSE_safe_pack_v0" / "tools" / "check_gates.py"),
    )
    parser.add_argument(
        "--policy-set",
        default="core_required",
        choices=[
            "core_required",
            "required",
            "release_required",
            "required+release_required",
            "custom",
        ],
    )
    parser.add_argument(
        "--required-gate",
        action="append",
        default=[],
        help="Explicit required gate. Repeat to build a custom effective set.",
    )
    parser.add_argument("--run-mode", default=None)
    parser.add_argument("--workflow-name", default=None)
    parser.add_argument("--event-name", default=None)
    parser.add_argument("--ref", default=None)
    parser.add_argument("--git-sha", default=None)
    parser.add_argument("--created-utc", default=None)
    parser.add_argument(
        "--out",
        default=str(root / "PULSE_safe_pack_v0" / "artifacts" / "release_authority_v0.json"),
    )

    args = parser.parse_args(argv)

    try:
        manifest = build_manifest(args)
        out_path = Path(args.out)
        _write_json(out_path, manifest)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: failed to build release authority manifest: {exc}", file=sys.stderr)
        return 1

    print(f"OK: wrote release authority manifest: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

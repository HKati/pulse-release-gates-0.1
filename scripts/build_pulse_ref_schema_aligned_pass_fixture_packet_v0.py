#!/usr/bin/env python3
"""Build a schema-aligned PULSE-REF pass-fixture packet candidate v0.

This builder maps the guarded release_reference_v1/pass fixture into a
canonical, schema-aligned, packet-shaped baseline candidate.

It does not create release authority.

It does not validate release-grade evidence.

It does not run RA1.

It prepares a reconstructable packet candidate that can pass the
schema-aligned packet artifact validator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

PACKAGE_ROOT_NAME = "pulse_ref_evidence_packet_v0"
PACKAGE_ID = "pulse-ref-pass-fixture-schema-aligned-baseline-v0"
RUN_KEY = "pulse-ref-pass-fixture-schema-aligned-baseline-v0"
CREATED_UTC = "2026-05-28T00:00:00Z"
STARTED_UTC = "2026-05-28T00:00:00Z"
COMPLETED_UTC = "2026-05-28T00:00:03Z"

REPOSITORY = "HKati/pulse-release-gates-0.1"
GIT_SHA = "a" * 40
RUN_ID = "22560000001"
RUN_ATTEMPT = 1
RUN_URL = f"https://github.com/{REPOSITORY}/actions/runs/{RUN_ID}"

SOURCE_FIXTURE = Path("tests/fixtures/release_reference_v1/pass")
SOURCE_STATUS = SOURCE_FIXTURE / "status.json"
SOURCE_EXPECTED_OUTCOME = SOURCE_FIXTURE / "expected_outcome.json"

POLICY_SOURCE = Path("pulse_gate_policy_v0.yml")
REGISTRY_SOURCE = Path("pulse_gate_registry_v0.yml")

NORMATIVE_DECISION_PATH = (
    "recorded release evidence -> recorded status.json artifact -> declared gate policy "
    "-> materialized required gate set -> strict fail-closed CI gate enforcement "
    "-> declared-policy CI allow/block release decision"
)


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"{path} did not contain a JSON object")
    return data


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    _write(path, json.dumps(obj, indent=2, sort_keys=True) + "\n")


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact_ref(packet_root: Path, rel_path: str) -> dict[str, str]:
    artifact = packet_root / rel_path
    return {
        "path": rel_path,
        "sha256": _sha256_file(artifact),
    }


def _unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []

    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)

    return out


def _materialize_policy_set(policy_path: Path, gate_set: str) -> list[str]:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "policy_to_require_args.py"),
            "--policy",
            str(policy_path),
            "--set",
            gate_set,
            "--format",
            "newline",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"failed to materialize policy set {gate_set!r}: "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )

    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _extract_policy_metadata(policy_path: Path) -> tuple[str, str]:
    text = policy_path.read_text(encoding="utf-8")

    policy_id_match = re.search(r"(?m)^\s*id:\s*([A-Za-z0-9_.:-]+)\s*$", text)
    version_match = re.search(r'(?m)^\s*version:\s*"?([^"\n]+)"?\s*$', text)

    policy_id = policy_id_match.group(1) if policy_id_match else "pulse-gate-policy-v0"
    version = version_match.group(1) if version_match else "unknown"

    return policy_id, version


def _status_gate_results(status: dict[str, Any], effective_required: list[str]) -> dict[str, bool]:
    gates = status.get("gates")
    if not isinstance(gates, dict):
        raise ValueError("source status has no gates object")

    results: dict[str, bool] = {}
    for gate in effective_required:
        value = gates.get(gate)
        if not isinstance(value, bool):
            raise ValueError(f"required gate {gate!r} is missing or non-boolean: {value!r}")
        results[gate] = value

    return results


def _write_readme(packet_root: Path) -> None:
    _write(
        packet_root / "README.md",
        f"""# PULSE-REF schema-aligned pass fixture packet v0

Status: schema-aligned packet-shaped baseline candidate
Authority status: non-normative packet artifact
Release-grade status: not release-grade evidence
Verifier status: pre-RA1 packet candidate
Decision status: does not authorize, block, override, or create release authority

Source fixture:

`{SOURCE_FIXTURE}/`

This packet preserves the guarded positive release-reference fixture as a
schema-aligned, digest-backed, reconstructable packet candidate.

The normative PULSEmech path remains:

recorded release evidence
→ recorded `status.json` artifact
→ declared gate policy
→ materialized required gate set
→ strict fail-closed CI gate enforcement
→ declared-policy CI allow/block release decision

This packet does not create release authority.
""",
    )


def _write_materialized_gate_sets(packet_root: Path) -> dict[str, Any]:
    policy_path = packet_root / "policy/pulse_gate_policy_v0.yml"

    required = _materialize_policy_set(policy_path, "required")
    release_required = _materialize_policy_set(policy_path, "release_required")
    effective = _unique_preserve_order(required + release_required)

    payload = {
        "schema": "pulse_ref_materialized_gate_sets_v0",
        "policy_path": "policy/pulse_gate_policy_v0.yml",
        "policy_sha256": _sha256_file(policy_path),
        "sets": {
            "required": required,
            "release_required": release_required,
        },
        "effective_required_gates": effective,
        "authority_boundary": {
            "source": "declared_gate_policy",
            "materialization_role": "required_gate_set_reconstruction",
            "creates_release_authority": False,
        },
    }

    _write_json(packet_root / "gates/materialized_gate_sets.json", payload)
    return payload


def _write_ci_outcome(packet_root: Path) -> None:
    payload = {
        "schema": "pulse_ref_ci_outcome_v0",
        "provider": "github_actions",
        "workflow": "PULSE CI",
        "run_id": RUN_ID,
        "run_attempt": RUN_ATTEMPT,
        "run_url": RUN_URL,
        "repository": REPOSITORY,
        "commit_sha": GIT_SHA,
        "gate_check_job": "Tools smoke tests",
        "gate_check_conclusion": "success",
        "created_utc": CREATED_UTC,
        "started_utc": STARTED_UTC,
        "completed_utc": COMPLETED_UTC,
        "authority_boundary": {
            "normative_decision_path": NORMATIVE_DECISION_PATH,
            "ci_role": "records_declared_policy_enforcement",
            "creates_release_authority": False,
        },
    }

    _write_json(packet_root / "ci/ci_outcome.json", payload)


def _write_release_authority_manifest(
    packet_root: Path,
    status: dict[str, Any],
    gate_sets: dict[str, Any],
) -> None:
    effective_required = gate_sets["effective_required_gates"]
    gate_results = _status_gate_results(status, effective_required)

    failed = [gate for gate, value in gate_results.items() if value is False]
    missing: list[str] = []

    policy_id, policy_version = _extract_policy_metadata(
        packet_root / "policy/pulse_gate_policy_v0.yml"
    )

    decision_state = "FAIL" if failed or missing else "PASS"

    payload = {
        "schema_version": "release_authority_v0",
        "created_utc": CREATED_UTC,
        "run_identity": {
            "run_mode": "prod",
            "workflow_name": "PULSE CI",
            "event_name": "release_reference_fixture",
            "ref": "refs/heads/main",
            "git_sha": GIT_SHA,
            "run_id": RUN_ID,
            "attempt": RUN_ATTEMPT,
            "actor": "HKati",
        },
        "inputs": {
            "status_json": _artifact_ref(packet_root, "status/status.json"),
            "gate_policy": {
                **_artifact_ref(packet_root, "policy/pulse_gate_policy_v0.yml"),
                "policy_id": policy_id,
                "version": policy_version,
            },
            "gate_registry": {
                **_artifact_ref(packet_root, "policy/pulse_gate_registry_v0.yml"),
                "version": "gate_registry_v0",
            },
        },
        "authority": {
            "policy_set": "required+release_required",
            "effective_required_gates": effective_required,
            "release_required_materialized": True,
            "advisory_gates": [
                "external_summaries_present",
                "external_all_pass",
            ],
        },
        "evaluation": {
            "evaluator": "PULSE_safe_pack_v0/tools/check_gates.py",
            "required_gate_results": gate_results,
            "failed_required_gates": failed,
            "missing_required_gates": missing,
        },
        "decision": {
            "state": decision_state,
            "fail_closed": True,
        },
        "diagnostics": {
            "shadow_surfaces_non_normative": True,
        },
    }

    _write_json(
        packet_root / "release_authority/release_authority_manifest.json",
        payload,
    )


def _write_handoff_report(
    packet_root: Path,
    status: dict[str, Any],
    gate_sets: dict[str, Any],
) -> None:
    status_sha = _sha256_file(packet_root / "status/status.json")
    required = gate_sets["sets"]["required"]
    release_required = gate_sets["sets"]["release_required"]
    effective_required = gate_sets["effective_required_gates"]

    files = [
        {
            "path": "status/status.json",
            "exists": True,
            "sha256": status_sha,
        },
        {
            "path": "policy/pulse_gate_policy_v0.yml",
            "exists": True,
            "sha256": _sha256_file(packet_root / "policy/pulse_gate_policy_v0.yml"),
        },
        {
            "path": "policy/pulse_gate_registry_v0.yml",
            "exists": True,
            "sha256": _sha256_file(packet_root / "policy/pulse_gate_registry_v0.yml"),
        },
        {
            "path": "gates/materialized_gate_sets.json",
            "exists": True,
            "sha256": _sha256_file(packet_root / "gates/materialized_gate_sets.json"),
        },
        {
            "path": "ci/ci_outcome.json",
            "exists": True,
            "sha256": _sha256_file(packet_root / "ci/ci_outcome.json"),
        },
        {
            "path": "release_authority/release_authority_manifest.json",
            "exists": True,
            "sha256": _sha256_file(
                packet_root / "release_authority/release_authority_manifest.json"
            ),
        },
    ]

    commands = [
        {
            "name": "materialize_required",
            "cmd": [
                "python",
                "tools/policy_to_require_args.py",
                "--policy",
                "policy/pulse_gate_policy_v0.yml",
                "--set",
                "required",
                "--format",
                "space",
            ],
            "env_overrides": {},
            "started_utc": STARTED_UTC,
            "finished_utc": "2026-05-28T00:00:01Z",
            "returncode": 0,
            "stdout": " ".join(required) + "\n",
            "stderr": "",
            "ok": True,
        },
        {
            "name": "materialize_release_required",
            "cmd": [
                "python",
                "tools/policy_to_require_args.py",
                "--policy",
                "policy/pulse_gate_policy_v0.yml",
                "--set",
                "release_required",
                "--format",
                "space",
            ],
            "env_overrides": {},
            "started_utc": "2026-05-28T00:00:01Z",
            "finished_utc": "2026-05-28T00:00:02Z",
            "returncode": 0,
            "stdout": " ".join(release_required) + "\n",
            "stderr": "",
            "ok": True,
        },
        {
            "name": "check_gates_release-grade",
            "cmd": [
                "python",
                "PULSE_safe_pack_v0/tools/check_gates.py",
                "--status",
                "status/status.json",
                "--require",
                *effective_required,
            ],
            "env_overrides": {},
            "started_utc": "2026-05-28T00:00:02Z",
            "finished_utc": COMPLETED_UTC,
            "returncode": 0,
            "stdout": "All required gates passed.\n",
            "stderr": "",
            "ok": True,
        },
    ]

    payload = {
        "schema": "pulse_ref_operator_handoff_report_v0",
        "ok": True,
        "created_utc": CREATED_UTC,
        "repo_root": ".",
        "gate_mode": "release-grade",
        "status_source": {
            "mode": "existing",
            "status_path": "status/status.json",
            "status_exists_before_run": True,
            "status_sha256_before_run": status_sha,
            "status_exists_after_generation": True,
            "status_sha256_after_generation": status_sha,
            "status_exists_after_run": True,
            "status_sha256_after_run": status_sha,
        },
        "materialized_gate_sets": {
            "required": required,
            "release_required": release_required,
        },
        "effective_required_gates": effective_required,
        "files": files,
        "commands": commands,
        "warnings": [],
        "errors": [],
        "authority_boundary": {
            "handoff_role": "release_grade_reconstruction",
            "creates_release_authority": False,
        },
    }

    # Keep status referenced so source status JSON has been loaded before handoff.
    if status.get("metrics", {}).get("fixture_id") != "release_reference_v1/pass":
        raise ValueError("source status must be release_reference_v1/pass")

    _write_json(packet_root / "handoff/operator_handoff_report.json", payload)


def _write_audit_bundle(packet_root: Path) -> None:
    audit_root = packet_root / "audit/release_authority_audit_bundle"

    _write(
        audit_root / "README.md",
        """# PULSE-REF schema-aligned pass fixture audit bundle

This audit bundle preserves selected packet artifacts for reconstruction.

It does not create release authority.
""",
    )

    _copy(packet_root / "status/status.json", audit_root / "status.json")
    _copy(
        packet_root / "release_authority/release_authority_manifest.json",
        audit_root / "release_authority_manifest.json",
    )


def _write_reconstruction_files(packet_root: Path) -> None:
    _write(
        packet_root / "reconstruction/reconstruction_instructions.md",
        """# Reconstruction instructions

This packet was generated from `tests/fixtures/release_reference_v1/pass/`.

Reconstruction route:

1. Inspect `status/status.json`.
2. Inspect `policy/pulse_gate_policy_v0.yml`.
3. Inspect `gates/materialized_gate_sets.json`.
4. Inspect `ci/ci_outcome.json`.
5. Inspect `release_authority/release_authority_manifest.json`.
6. Inspect `handoff/operator_handoff_report.json`.
7. Verify `digests/package_digests.json`.

This packet is a schema-aligned baseline candidate.

It does not create release authority.
""",
    )


def _write_optional_notes(packet_root: Path) -> None:
    _write(
        packet_root / "external/summaries/README.md",
        """# External summaries

This packet preserves external summary state from the source fixture.

No external summary payload is promoted into release authority by this packet.
""",
    )


def _write_package_digests(packet_root: Path) -> None:
    artifacts: dict[str, str] = {}

    for path in sorted(packet_root.rglob("*")):
        if not path.is_file():
            continue

        rel_path = path.relative_to(packet_root).as_posix()

        if rel_path in {
            "package_manifest.json",
            "digests/package_digests.json",
        }:
            continue

        artifacts[rel_path] = _sha256_file(path)

    payload = {
        "schema": "pulse_ref_package_digests_v0",
        "algorithm": "sha256",
        "created_utc": CREATED_UTC,
        "package_id": PACKAGE_ID,
        "artifacts": artifacts,
        "authority_boundary": {
            "digest_role": "artifact_integrity_verification",
            "creates_release_authority": False,
        },
    }

    _write_json(packet_root / "digests/package_digests.json", payload)


def _write_package_manifest(packet_root: Path) -> None:
    payload = {
        "schema": "pulse_ref_release_reference_package_v0",
        "package_id": PACKAGE_ID,
        "created_utc": CREATED_UTC,
        "run_key": RUN_KEY,
        "git_sha": GIT_SHA,
        "status_artifact": _artifact_ref(packet_root, "status/status.json"),
        "gate_policy": _artifact_ref(packet_root, "policy/pulse_gate_policy_v0.yml"),
        "gate_registry": _artifact_ref(packet_root, "policy/pulse_gate_registry_v0.yml"),
        "materialized_gate_sets": _artifact_ref(
            packet_root,
            "gates/materialized_gate_sets.json",
        ),
        "operator_handoff_report": _artifact_ref(
            packet_root,
            "handoff/operator_handoff_report.json",
        ),
        "release_authority_manifest": _artifact_ref(
            packet_root,
            "release_authority/release_authority_manifest.json",
        ),
        "audit_bundle": {
            "path": "audit/release_authority_audit_bundle",
        },
        "ci_outcome": _artifact_ref(packet_root, "ci/ci_outcome.json"),
        "package_digests": _artifact_ref(
            packet_root,
            "digests/package_digests.json",
        ),
        "authority_boundary": {
            "normative_decision_path": NORMATIVE_DECISION_PATH,
            "package_role": "audit_preservation_reconstruction",
            "creates_release_authority": False,
        },
    }

    _write_json(packet_root / "package_manifest.json", payload)


def build(out_dir: Path) -> Path:
    packet_root = out_dir / PACKAGE_ROOT_NAME

    if packet_root.exists():
        shutil.rmtree(packet_root)

    packet_root.mkdir(parents=True, exist_ok=True)

    source_status = ROOT / SOURCE_STATUS
    source_expected = ROOT / SOURCE_EXPECTED_OUTCOME
    policy_source = ROOT / POLICY_SOURCE
    registry_source = ROOT / REGISTRY_SOURCE

    for required_path in [source_status, source_expected, policy_source, registry_source]:
        if not required_path.is_file():
            raise FileNotFoundError(required_path)

    status = _load_json(source_status)
    expected = _load_json(source_expected)

    if expected.get("expected_result") != "PASS":
        raise ValueError("source expected_outcome.json must declare PASS")

    _write_readme(packet_root)
    _copy(source_status, packet_root / "status/status.json")
    _copy(source_expected, packet_root / "reconstruction/source_expected_outcome.json")
    _copy(policy_source, packet_root / "policy/pulse_gate_policy_v0.yml")
    _copy(registry_source, packet_root / "policy/pulse_gate_registry_v0.yml")

    gate_sets = _write_materialized_gate_sets(packet_root)

    # Fail early when the source fixture no longer satisfies the policy-derived
    # effective required gate set.
    _status_gate_results(status, gate_sets["effective_required_gates"])

    _write_ci_outcome(packet_root)
    _write_release_authority_manifest(packet_root, status, gate_sets)
    _write_handoff_report(packet_root, status, gate_sets)
    _write_audit_bundle(packet_root)
    _write_reconstruction_files(packet_root)
    _write_optional_notes(packet_root)
    _write_package_digests(packet_root)
    _write_package_manifest(packet_root)

    return packet_root


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out-dir",
        required=True,
        type=Path,
        help="Output directory that will contain pulse_ref_evidence_packet_v0/.",
    )

    args = parser.parse_args()

    packet_root = build(args.out_dir)
    print(f"OK: wrote {packet_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

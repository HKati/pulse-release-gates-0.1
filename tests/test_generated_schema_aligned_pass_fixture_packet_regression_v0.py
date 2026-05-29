#!/usr/bin/env python3
"""Regression test for the generated schema-aligned pass-fixture packet."""

from __future__ import annotations

import argparse
import difflib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_pulse_ref_schema_aligned_pass_fixture_packet_v0.py"
CHECKER = ROOT / "scripts" / "check_pulse_ref_schema_aligned_packet_v0.py"
GOLDEN = (
    ROOT
    / "tests"
    / "fixtures"
    / "pulse_ref_schema_aligned_pass_fixture_packet_summary_v0.json"
)

REQUIRED_PACKET_PATHS = [
    "README.md",
    "package_manifest.json",
    "status/status.json",
    "reconstruction/source_expected_outcome.json",
    "policy/pulse_gate_policy_v0.yml",
    "policy/pulse_gate_registry_v0.yml",
    "gates/materialized_gate_sets.json",
    "ci/ci_outcome.json",
    "release_authority/release_authority_manifest.json",
    "audit/release_authority_audit_bundle/README.md",
    "audit/release_authority_audit_bundle/status.json",
    "audit/release_authority_audit_bundle/release_authority_manifest.json",
    "digests/package_digests.json",
    "handoff/operator_handoff_report.json",
    "external/summaries/README.md",
    "reconstruction/reconstruction_instructions.md",
]

MANIFEST_NAMED_REFS = [
    "status_artifact",
    "gate_policy",
    "gate_registry",
    "materialized_gate_sets",
    "operator_handoff_report",
    "release_authority_manifest",
    "audit_bundle",
    "ci_outcome",
    "package_digests",
    "publication_snapshot",
]


JsonObject = dict[str, Any]


def _load_json(path: Path) -> JsonObject:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), path
    return data


def _dump_summary(summary: JsonObject) -> str:
    return json.dumps(summary, indent=2, sort_keys=True) + "\n"


def _run(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _run_builder(out_dir: Path) -> Path:
    result = _run(
        [sys.executable, str(BUILDER), "--out-dir", str(out_dir)],
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    packet_root = out_dir / "pulse_ref_evidence_packet_v0"
    assert packet_root.is_dir()
    return packet_root


def _run_checker(packet_root: Path) -> None:
    result = _run(
        [sys.executable, str(CHECKER), "--packet-root", str(packet_root)],
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK: PULSE-REF schema-aligned packet artifacts valid" in result.stdout


def _norm_path_text(value: str, *, packet_root: Path) -> str:
    normalized = value.replace("\\", "/")

    replacements = [
        (str(packet_root), "<PACKET_ROOT>"),
        (packet_root.as_posix(), "<PACKET_ROOT>"),
        (str(ROOT), "<REPO_ROOT>"),
        (ROOT.as_posix(), "<REPO_ROOT>"),
        (str(Path(sys.executable)), "<PYTHON>"),
        (Path(sys.executable).as_posix(), "<PYTHON>"),
        (sys.executable, "<PYTHON>"),
    ]

    for before, after in replacements:
        normalized = normalized.replace(before.replace("\\", "/"), after)
        normalized = normalized.replace(before, after)

    return normalized


def _normalize_cmd(cmd: list[Any], *, packet_root: Path) -> list[str]:
    return [_norm_path_text(str(part), packet_root=packet_root) for part in cmd]


def _schema_value(payload: JsonObject) -> str | None:
    schema = payload.get("schema")
    if isinstance(schema, str):
        return schema

    schema_version = payload.get("schema_version")
    if isinstance(schema_version, str):
        return schema_version

    return None


def _json_artifact_schemas(packet_root: Path) -> JsonObject:
    schemas: JsonObject = {}
    for path in sorted(packet_root.rglob("*.json")):
        rel_path = path.relative_to(packet_root).as_posix()
        schema = _schema_value(_load_json(path))
        if schema is not None:
            schemas[rel_path] = schema
    return schemas


def _manifest_named_refs(manifest: JsonObject) -> JsonObject:
    refs: JsonObject = {}
    for key in MANIFEST_NAMED_REFS:
        value = manifest.get(key)
        if isinstance(value, dict) and isinstance(value.get("path"), str):
            refs[key] = {"path": value["path"]}
    return refs


def _materialized_gate_sets(gate_sets: JsonObject) -> JsonObject:
    return {
        "schema": gate_sets["schema"],
        "policy_path": gate_sets["policy_path"],
        "sets": gate_sets["sets"],
        "effective_required_gates": gate_sets["effective_required_gates"],
        "authority_boundary": gate_sets["authority_boundary"],
    }


def _ci_outcome_core(ci_outcome: JsonObject) -> JsonObject:
    return {
        "schema": ci_outcome["schema"],
        "provider": ci_outcome["provider"],
        "workflow": ci_outcome["workflow"],
        "repository": ci_outcome["repository"],
        "gate_check_job": ci_outcome["gate_check_job"],
        "gate_check_conclusion": ci_outcome["gate_check_conclusion"],
        "authority_boundary": ci_outcome["authority_boundary"],
    }


def _release_authority_decision_core(release_authority: JsonObject) -> JsonObject:
    return {
        "schema_version": release_authority["schema_version"],
        "run_identity": {
            "run_mode": release_authority["run_identity"]["run_mode"],
            "workflow_name": release_authority["run_identity"]["workflow_name"],
            "event_name": release_authority["run_identity"]["event_name"],
            "ref": release_authority["run_identity"]["ref"],
        },
        "authority": release_authority["authority"],
        "evaluation": {
            "evaluator": release_authority["evaluation"]["evaluator"],
            "required_gate_results": release_authority["evaluation"]["required_gate_results"],
            "failed_required_gates": release_authority["evaluation"]["failed_required_gates"],
            "missing_required_gates": release_authority["evaluation"]["missing_required_gates"],
        },
        "decision": release_authority["decision"],
        "diagnostics": release_authority["diagnostics"],
    }


def _handoff_commands_normalized(handoff: JsonObject, *, packet_root: Path) -> list[JsonObject]:
    commands = handoff["commands"]
    assert isinstance(commands, list)

    normalized = []
    for command in commands:
        assert isinstance(command, dict)
        normalized.append(
            {
                "name": command["name"],
                "cmd": _normalize_cmd(command["cmd"], packet_root=packet_root),
                "env_overrides": command["env_overrides"],
                "returncode": command["returncode"],
                "stdout": command["stdout"],
                "stderr": command["stderr"],
                "ok": command["ok"],
            }
        )
    return normalized


def _source_fixture_identity(packet_root: Path) -> JsonObject:
    status = _load_json(packet_root / "status/status.json")
    expected = _load_json(packet_root / "reconstruction/source_expected_outcome.json")

    metrics = status.get("metrics")
    assert isinstance(metrics, dict)

    return {
        "status_schema": _schema_value(status),
        "fixture_id": metrics.get("fixture_id"),
        "expected_outcome": {
            "expected_result": expected.get("expected_result"),
            "fixture_id": expected.get("fixture_id"),
        },
    }


def _authority_boundary_flags(
    manifest: JsonObject,
    gate_sets: JsonObject,
    ci_outcome: JsonObject,
    handoff: JsonObject,
    digests: JsonObject,
) -> JsonObject:
    return {
        "package_manifest": manifest["authority_boundary"],
        "materialized_gate_sets": gate_sets["authority_boundary"],
        "ci_outcome": ci_outcome["authority_boundary"],
        "operator_handoff_report": handoff["authority_boundary"],
        "package_digests": digests["authority_boundary"],
    }


def build_summary(packet_root: Path) -> JsonObject:
    manifest = _load_json(packet_root / "package_manifest.json")
    gate_sets = _load_json(packet_root / "gates/materialized_gate_sets.json")
    ci_outcome = _load_json(packet_root / "ci/ci_outcome.json")
    release_authority = _load_json(
        packet_root / "release_authority/release_authority_manifest.json"
    )
    handoff = _load_json(packet_root / "handoff/operator_handoff_report.json")
    digests = _load_json(packet_root / "digests/package_digests.json")

    commands_normalized = _handoff_commands_normalized(handoff, packet_root=packet_root)

    return {
        "packet_root_name": packet_root.name,
        "required_paths": REQUIRED_PACKET_PATHS,
        "json_artifact_schemas": _json_artifact_schemas(packet_root),
        "package_manifest_named_refs": _manifest_named_refs(manifest),
        "materialized_gate_sets": _materialized_gate_sets(gate_sets),
        "ci_outcome_core": _ci_outcome_core(ci_outcome),
        "release_authority_decision_core": _release_authority_decision_core(
            release_authority
        ),
        "handoff_command_kinds": [command["name"] for command in commands_normalized],
        "handoff_commands_normalized": commands_normalized,
        "digest_artifact_keys": sorted(digests["artifacts"].keys()),
        "source_fixture_identity": _source_fixture_identity(packet_root),
        "authority_boundary_flags": _authority_boundary_flags(
            manifest,
            gate_sets,
            ci_outcome,
            handoff,
            digests,
        ),
    }


def _assert_summary_matches_golden(actual: JsonObject) -> None:
    expected = _load_json(GOLDEN)
    if actual == expected:
        return

    diff = "".join(
        difflib.unified_diff(
            _dump_summary(expected).splitlines(keepends=True),
            _dump_summary(actual).splitlines(keepends=True),
            fromfile=str(GOLDEN.relative_to(ROOT)),
            tofile="generated schema-aligned pass-fixture packet summary",
        )
    )
    raise AssertionError("generated packet summary drifted:\n" + diff)


def _build_checked_summary() -> JsonObject:
    with tempfile.TemporaryDirectory() as tmp:
        packet_root = _run_builder(Path(tmp))
        _run_checker(packet_root)
        for rel_path in REQUIRED_PACKET_PATHS:
            assert (packet_root / rel_path).exists(), rel_path
        return build_summary(packet_root)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write-golden",
        action="store_true",
        help="Regenerate the normalized golden summary fixture.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        summary = _build_checked_summary()
        if args.write_golden:
            GOLDEN.write_text(_dump_summary(summary), encoding="utf-8")
            print(f"OK: wrote {GOLDEN.relative_to(ROOT)}")
            return 0

        _assert_summary_matches_golden(summary)
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: generated schema-aligned pass-fixture packet regression passed")
    return 0


def test_smoke() -> None:
    assert main([]) == 0


if __name__ == "__main__":
    raise SystemExit(main())

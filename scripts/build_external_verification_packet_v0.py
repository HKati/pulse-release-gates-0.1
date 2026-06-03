
#!/usr/bin/env python3
"""Build External Verification Packet v0.

This script is a review-carrier builder.

It records repository identity, commit identity, artifact records, digests,
verification commands, and carrier boundaries for external verification of the
PULSEmech release-authority artifact relationship.

It does not modify release artifacts, gate policy, status.json, release
decisions, DOI / Zenodo metadata, or workflow behavior.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SCHEMA_ID = "pulse.external_verification_packet.v0"
SCHEMA_VERSION = "0.1.0"

AUTHORITY_CARRIER = (
    "status.json -> declared gate policy -> workflow-effective materialized "
    "required gate set -> strict fail-closed CI enforcement"
)

PACKET_BOUNDARY = "external verification carrier; not release authority"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def run_git(repo_root: Path, args: list[str]) -> str | None:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except Exception:
        return None

    value = proc.stdout.strip()
    return value or None


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json_object_status(path: Path) -> tuple[dict[str, Any], bool, str | None]:
    if not path.is_file():
        return {}, False, "missing"

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {}, False, f"invalid JSON: {exc}"

    if not isinstance(payload, dict):
        return {}, False, "top-level JSON value is not an object"

    return payload, True, None


def read_json_if_exists(path: Path) -> dict[str, Any]:
    payload, _ok, _error = read_json_object_status(path)
    return payload


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def parse_run_key_value(run_key: Any, key: str) -> str | None:
    if not isinstance(run_key, str):
        return None

    for part in run_key.split("|"):
        if "=" not in part:
            continue
        left, right = part.split("=", 1)
        if left.strip() == key:
            value = right.strip()
            return value or None

    return None


def artifact_record(
    *,
    repo_root: Path,
    role: str,
    path: str,
    required: bool,
    carrier_class: str,
    boundary: str,
    notes: str = "",
    json_object_required: bool = False,
) -> dict[str, Any]:
    artifact_path = repo_root / path
    exists = artifact_path.is_file()

    parseable_json: bool | None = None
    parse_error: str | None = None

    if json_object_required:
        _payload, parseable_json, parse_error = read_json_object_status(artifact_path)

    return {
        "role": role,
        "path": path,
        "required": required,
        "exists": exists,
        "sha256": sha256_file(artifact_path) if exists else None,
        "carrier_class": carrier_class,
        "boundary": boundary,
        "notes": notes,
        "json_object_required": json_object_required,
        "parseable_json": parseable_json,
        "parse_error": parse_error,
    }


def collect_artifact_records(repo_root: Path) -> list[dict[str, Any]]:
    return [
        artifact_record(
            repo_root=repo_root,
            role="status",
            path="PULSE_safe_pack_v0/artifacts/status.json",
            required=True,
            carrier_class="authority",
            boundary="recorded release-state artifact",
            json_object_required=True,
        ),
        artifact_record(
            repo_root=repo_root,
            role="gate policy",
            path="pulse_gate_policy_v0.yml",
            required=True,
            carrier_class="policy",
            boundary="declared gate policy",
        ),
        artifact_record(
            repo_root=repo_root,
            role="gate registry",
            path="pulse_gate_registry_v0.yml",
            required=True,
            carrier_class="registry",
            boundary="gate identity and interpretation registry",
        ),
        artifact_record(
            repo_root=repo_root,
            role="release decision",
            path="PULSE_safe_pack_v0/artifacts/release_decision_v0.json",
            required=False,
            carrier_class="trace",
            boundary="release-decision materialization artifact",
            notes="Conditional artifact; record if present.",
        ),
        artifact_record(
            repo_root=repo_root,
            role="release authority manifest",
            path="PULSE_safe_pack_v0/artifacts/release_authority_v0.json",
            required=False,
            carrier_class="trace",
            boundary="release-authority reconstruction sidecar",
            notes="Audit / traceability sidecar; not release authority.",
        ),
        artifact_record(
            repo_root=repo_root,
            role="artifact provenance binding",
            path="PULSE_safe_pack_v0/artifacts/artifact_provenance_binding_v0.json",
            required=False,
            carrier_class="binding",
            boundary="digest-backed artifact relationship carrier",
            notes="Binding carrier; attestation subject when present.",
        ),
        artifact_record(
            repo_root=repo_root,
            role="Quality Ledger",
            path="PULSE_safe_pack_v0/artifacts/report_card.html",
            required=False,
            carrier_class="reader",
            boundary="public / human-readable reader carrier",
            notes="Reader carrier; not release authority.",
        ),
        artifact_record(
            repo_root=repo_root,
            role="composed release-decision report",
            path="PULSE_safe_pack_v0/artifacts/report_card.with_release_decision.html",
            required=False,
            carrier_class="reader",
            boundary="reader carrier with release-decision section",
        ),
        artifact_record(
            repo_root=repo_root,
            role="status summary JSON",
            path="PULSE_safe_pack_v0/artifacts/status_summary.json",
            required=False,
            carrier_class="reader",
            boundary="machine-readable summary carrier",
        ),
        artifact_record(
            repo_root=repo_root,
            role="status summary Markdown",
            path="PULSE_safe_pack_v0/artifacts/status_summary.md",
            required=False,
            carrier_class="reader",
            boundary="human-readable summary carrier",
        ),
    ]


def status_run_identity(repo_root: Path) -> dict[str, Any]:
    status_path = repo_root / "PULSE_safe_pack_v0" / "artifacts" / "status.json"
    status, parse_ok, parse_error = read_json_object_status(status_path)

    metrics = as_dict(status.get("metrics"))
    run_key = metrics.get("run_key") or status.get("run_key")

    run_id = (
        metrics.get("run_id")
        or status.get("run_id")
        or parse_run_key_value(run_key, "GITHUB_RUN_ID")
    )

    return {
        "run_id": run_id,
        "run_key": run_key,
        "run_mode": metrics.get("run_mode") or status.get("run_mode"),
        "created_utc": status.get("created_utc"),
        "status_version": status.get("version"),
        "status_git_sha": metrics.get("git_sha") or status.get("git_sha"),
        "status_parse_ok": parse_ok,
        "status_parse_error": parse_error,
    }


def repository_identity(repo_root: Path, repository_name: str | None) -> dict[str, Any]:
    remote = run_git(repo_root, ["config", "--get", "remote.origin.url"])
    return {
        "name": repository_name or "unknown",
        "root": repo_root.as_posix(),
        "remote": remote,
    }


def commit_identity(repo_root: Path) -> dict[str, Any]:
    git_sha = run_git(repo_root, ["rev-parse", "HEAD"])
    branch = run_git(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"])
    status = run_git(repo_root, ["status", "--porcelain"])

    return {
        "git_sha": git_sha,
        "branch": branch,
        "dirty_worktree": bool(status),
    }


def verification_commands() -> list[dict[str, str]]:
    return [
        {
            "name": "compile release-authority tools",
            "purpose": "Check reviewer-relevant tools import cleanly.",
            "command": (
                "python -m py_compile "
                "PULSE_safe_pack_v0/tools/check_gates.py "
                "PULSE_safe_pack_v0/tools/materialize_release_decision.py "
                "PULSE_safe_pack_v0/tools/build_artifact_provenance_binding_v0.py "
                "PULSE_safe_pack_v0/tools/verify_artifact_provenance_binding_v0.py"
            ),
        },
        {
            "name": "fail-closed gate enforcement tests",
            "purpose": (
                "Verify literal true-only and missing-required-gate "
                "fail-closed semantics."
            ),
            "command": "python -m pytest -q tests/test_check_gates_fail_closed.py",
        },
        {
            "name": "artifact provenance binding tests",
            "purpose": "Verify binding builder / verifier behavior.",
            "command": "python -m pytest -q tests/test_artifact_provenance_binding_v0.py",
        },
        {
            "name": "binding CI wiring tests",
            "purpose": "Verify binding materialization and attestation wiring.",
            "command": (
                "python -m pytest -q "
                "tests/test_artifact_provenance_binding_ci_wiring_smoke.py "
                "tests/test_artifact_provenance_binding_attestation_wiring_smoke.py"
            ),
        },
        {
            "name": "Quality Ledger reader-surface tests",
            "purpose": "Verify reader-surface boundary and check-gates parity semantics.",
            "command": (
                "python -m pytest -q "
                "tests/test_render_quality_ledger.py "
                "tests/test_render_quality_ledger_decision_logic.py "
                "tests/test_render_quality_ledger_check_gates_parity.py"
            ),
        },
        {
            "name": "verify artifact provenance binding",
            "purpose": "Recompute and verify the binding carrier if present.",
            "command": (
                "python PULSE_safe_pack_v0/tools/verify_artifact_provenance_binding_v0.py "
                "--binding PULSE_safe_pack_v0/artifacts/artifact_provenance_binding_v0.json"
            ),
        },
        {
            "name": "generate normative/shadow inventory report",
            "purpose": (
                "Review workflow carrier classification without committing "
                "generated output."
            ),
            "command": (
                "TMPDIR=\"$(mktemp -d)\" && "
                "python scripts/build_normative_shadow_inventory_v0.py "
                "--repo-root . "
                "--out-json \"$TMPDIR/normative_shadow_inventory_v0.json\" "
                "--out-md \"$TMPDIR/normative_shadow_inventory_v0.md\" && "
                "git status --short"
            ),
        },
    ]


def carrier_boundary_summary() -> list[dict[str, str]]:
    return [
        {
            "carrier": "authority",
            "boundary": AUTHORITY_CARRIER,
        },
        {
            "carrier": "reader",
            "boundary": "Presents recorded state; non-authorizing carrier.",
        },
        {
            "carrier": "trace",
            "boundary": "Preserves reconstruction trace; no independent decision function.",
        },
        {
            "carrier": "binding",
            "boundary": "Carries digest-backed artifact relationship.",
        },
        {
            "carrier": "attestation",
            "boundary": "Attests the binding carrier; does not replace PULSEmech.",
        },
        {
            "carrier": "external_verification",
            "boundary": "Reviews recorded artifact relationship; not release authority.",
        },
    ]


def reviewer_checklist() -> list[str]:
    return [
        "status.json exists and is parseable",
        "declared gate policy exists",
        "gate registry exists",
        "required gate source is identifiable",
        "required gates are materialized",
        "check_gates.py enforces literal true-only semantics",
        "missing required gates fail closed",
        "release-decision artifact is present when expected",
        "binding artifact is present when expected",
        "binding verifier passes when binding is present",
        "reader surfaces do not claim independent authority",
        "attestation subject is the binding carrier when attestation is present",
    ]


def verify_binding_carrier(
    repo_root: Path,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    binding = next(
        (record for record in records if record["role"] == "artifact provenance binding"),
        None,
    )

    if binding is None:
        return {
            "requested": False,
            "available": False,
            "verified": None,
            "exit_code": None,
            "reason": "binding record missing",
        }

    if not binding["exists"]:
        return {
            "requested": True,
            "available": False,
            "verified": None,
            "exit_code": None,
            "reason": "binding artifact missing",
        }

    verifier = (
        repo_root
        / "PULSE_safe_pack_v0"
        / "tools"
        / "verify_artifact_provenance_binding_v0.py"
    )
    binding_path = repo_root / binding["path"]

    if not verifier.is_file():
        return {
            "requested": True,
            "available": True,
            "verified": None,
            "exit_code": None,
            "reason": "binding verifier missing",
        }

    proc = subprocess.run(
        [
            sys.executable,
            verifier.as_posix(),
            "--binding",
            binding_path.as_posix(),
        ],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    return {
        "requested": True,
        "available": True,
        "verified": proc.returncode == 0,
        "exit_code": proc.returncode,
        "reason": (
            "binding verifier passed"
            if proc.returncode == 0
            else "binding verifier failed"
        ),
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def packet_status(
    records: list[dict[str, Any]],
    *,
    commit: dict[str, Any],
    binding_verification: dict[str, Any],
) -> str:
    missing_required = [
        record for record in records if record["required"] and not record["exists"]
    ]
    if missing_required:
        return "authority_artifact_missing"

    malformed_required = [
        record
        for record in records
        if record["required"]
        and record.get("json_object_required") is True
        and record.get("parseable_json") is not True
    ]
    if malformed_required:
        return "verification_failed"

    if not commit.get("git_sha"):
        return "inconclusive"

    binding = next(
        (record for record in records if record["role"] == "artifact provenance binding"),
        None,
    )

    if binding is not None and not binding["exists"]:
        return "partially_verified"

    if binding is not None and binding["exists"]:
        if binding_verification.get("verified") is True:
            return "verified"
        if binding_verification.get("verified") is False:
            return "verification_failed"
        return "inconclusive"

    return "partially_verified"


def build_packet(repo_root: Path, repository_name: str | None = None) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    records = collect_artifact_records(repo_root)
    missing = [record for record in records if not record["exists"]]
    commit = commit_identity(repo_root)
    binding_verification = verify_binding_carrier(repo_root, records)

    return {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "generated_utc": utc_now(),
        "repository": repository_identity(repo_root, repository_name),
        "commit": commit,
        "run_identity": status_run_identity(repo_root),
        "verification_profile": "authority-path",
        "authority_carrier": AUTHORITY_CARRIER,
        "artifact_records": records,
        "verification_commands": verification_commands(),
        "carrier_boundary_summary": carrier_boundary_summary(),
        "reviewer_checklist": reviewer_checklist(),
        "known_missing_artifacts": missing,
        "binding_verification": binding_verification,
        "packet_status": packet_status(
            records,
            commit=commit,
            binding_verification=binding_verification,
        ),
        "packet_boundary": PACKET_BOUNDARY,
    }


def markdown_report(packet: dict[str, Any]) -> str:
    repository = as_dict(packet.get("repository"))
    commit = as_dict(packet.get("commit"))

    lines = [
        "# External Verification Packet v0",
        "",
        "## Summary",
        "",
        f"- schema_id: `{packet['schema_id']}`",
        f"- schema_version: `{packet['schema_version']}`",
        f"- generated_utc: `{packet['generated_utc']}`",
        f"- verification_profile: `{packet['verification_profile']}`",
        f"- packet_status: `{packet['packet_status']}`",
        f"- repository: `{repository.get('name')}`",
        f"- git_sha: `{commit.get('git_sha')}`",
        f"- dirty_worktree: `{commit.get('dirty_worktree')}`",
        "",
        "Authority carrier:",
        "",
        "```text",
        packet["authority_carrier"],
        "```",
        "",
        "Packet boundary:",
        "",
        "```text",
        packet["packet_boundary"],
        "```",
        "",
        "## Artifact records",
        "",
        "| Role | Path | Required | Exists | Carrier class | SHA-256 |",
        "|---|---|---:|---:|---|---|",
    ]

    for record in packet["artifact_records"]:
        digest = record["sha256"] or "—"
        lines.append(
            "| {role} | `{path}` | `{required}` | `{exists}` | `{carrier}` | `{digest}` |".format(
                role=str(record["role"]).replace("|", "\\|"),
                path=str(record["path"]).replace("|", "\\|"),
                required=str(record["required"]).lower(),
                exists=str(record["exists"]).lower(),
                carrier=str(record["carrier_class"]).replace("|", "\\|"),
                digest=digest,
            )
        )

    lines.extend(
        [
            "",
            "## Verification commands",
            "",
        ]
    )

    for command in packet["verification_commands"]:
        lines.append(f"### {command['name']}")
        lines.append("")
        lines.append(command["purpose"])
        lines.append("")
        lines.append("```bash")
        lines.append(command["command"])
        lines.append("```")
        lines.append("")

    lines.extend(
        [
            "## Reviewer checklist",
            "",
        ]
    )

    for item in packet["reviewer_checklist"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Missing artifacts",
            "",
        ]
    )

    missing = packet.get("known_missing_artifacts") or []
    if not missing:
        lines.append("No missing artifacts recorded.")
    else:
        lines.append("| Role | Path | Required | Carrier class |")
        lines.append("|---|---|---:|---|")
        for record in missing:
            lines.append(
                "| {role} | `{path}` | `{required}` | `{carrier}` |".format(
                    role=str(record["role"]).replace("|", "\\|"),
                    path=str(record["path"]).replace("|", "\\|"),
                    required=str(record["required"]).lower(),
                    carrier=str(record["carrier_class"]).replace("|", "\\|"),
                )
            )

    lines.extend(
        [
            "",
            "## Binding verification",
            "",
            "```json",
            json.dumps(
                packet.get("binding_verification") or {},
                indent=2,
                sort_keys=True,
            ),
            "```",
            "",
            "## Boundary",
            "",
            "This packet is an external verification carrier.",
            "",
            "It is not release authority.",
            "",
        ]
    )

    return "\n".join(lines)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    parser.add_argument("--repository-name", default=None)
    args = parser.parse_args()

    packet = build_packet(
        Path(args.repo_root),
        repository_name=args.repository_name,
    )

    write_json(Path(args.out_json), packet)
    write_text(Path(args.out_md), markdown_report(packet))

    print(f"Wrote {args.out_json}")
    print(f"Wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


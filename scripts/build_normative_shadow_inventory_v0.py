#!/usr/bin/env python3
"""Build PULSE Normative vs Shadow Inventory Report v0.

This script is a review carrier. It classifies repository workflows and selected
authority-relevant artifacts by mechanical carrier role. It does not alter
release authority, gate policy, workflow behavior, status artifacts, or release
decisions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


SCHEMA_ID = "pulse.normative_shadow_inventory.v0"
SCHEMA_VERSION = "0.1.0"


AUTHORITY_PATH = (
    "status.json -> declared gate policy -> workflow-effective materialized "
    "required gate set -> strict fail-closed CI enforcement"
)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def read_text_if_exists(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def entry(
    *,
    name: str,
    path: str,
    surface_type: str,
    primary_role: str,
    carrier_class: str,
    authority_impacting: str,
    authority_boundary: str,
    reads_artifacts: list[str] | None = None,
    writes_artifacts: list[str] | None = None,
    publishes_artifacts: list[str] | None = None,
    required_gate_participation: bool = False,
    attestation_participation: bool = False,
    release_path_participation: bool = False,
    notes: str = "",
) -> dict[str, Any]:
    return {
        "name": name,
        "path": path,
        "surface_type": surface_type,
        "primary_role": primary_role,
        "carrier_class": carrier_class,
        "authority_impacting": authority_impacting,
        "authority_boundary": authority_boundary,
        "reads_artifacts": reads_artifacts or [],
        "writes_artifacts": writes_artifacts or [],
        "publishes_artifacts": publishes_artifacts or [],
        "required_gate_participation": required_gate_participation,
        "attestation_participation": attestation_participation,
        "release_path_participation": release_path_participation,
        "notes": notes,
    }


def workflow_name(path: Path, text: str) -> str:
    for line in text.splitlines():
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip('"').strip("'")
    return path.stem


def classify_workflow(path: Path, *, repo_root: Path) -> dict[str, Any]:
    rel = path.relative_to(repo_root).as_posix()
    text = read_text_if_exists(path)
    name = workflow_name(path, text)

    rel_l = rel.lower()
    name_l = name.lower()
    identity_l = f"{rel_l}\n{name_l}"

    if rel == ".github/workflows/pulse_ci.yml":
        return entry(
            name=name,
            path=rel,
            surface_type="workflow",
            primary_role="primary release-authority workflow",
            carrier_class="authority",
            authority_impacting="yes",
            authority_boundary=AUTHORITY_PATH,
            reads_artifacts=[
                "status.json",
                "pulse_gate_policy_v0.yml",
                "pulse_gate_registry_v0.yml",
            ],
            writes_artifacts=[
                "status.json",
                "release_decision_v0.json",
                "release_authority_v0.json",
                "artifact_provenance_binding_v0.json",
            ],
            publishes_artifacts=[
                "pulse-report",
                "release-authority-v0",
                "release-authority-artifact-binding-v0",
            ],
            required_gate_participation=True,
            attestation_participation="actions/attest@" in text,
            release_path_participation=True,
            notes=(
                "Primary release-authority workflow. Produces, validates, "
                "materializes, enforces, binds, and may attest authority artifacts."
            ),
        )

    if any(
        token in identity_l
        for token in (
            "core_baseline",
            "core baseline",
            "pulse_core",
            "pulse-core",
            "core ci",
        )
    ):
        return entry(
            name=name,
            path=rel,
            surface_type="workflow",
            primary_role="core baseline workflow",
            carrier_class="advisory",
            authority_impacting="conditional",
            authority_boundary=(
                "Non-authorizing unless explicitly folded into recorded evidence "
                "and enforced as a required gate under declared policy."
            ),
            reads_artifacts=["status.json"],
            notes="Core baseline verification carrier; not a second release path.",
        )

    if "release_check" in rel_l or "release check" in name_l:
        return entry(
            name=name,
            path=rel,
            surface_type="workflow",
            primary_role="release check workflow",
            carrier_class="advisory",
            authority_impacting="conditional",
            authority_boundary=(
                "Review / guard carrier. Authority participation requires explicit "
                "required-gate wiring under declared policy."
            ),
            notes="Release-check carrier; not a second release-decision engine.",
        )

    if (
        "theory_overlay" in rel_l
        or "theory overlay" in name_l
        or "overlay" in rel_l
        or "overlay" in name_l
    ):
        return entry(
            name=name,
            path=rel,
            surface_type="workflow",
            primary_role="diagnostic / overlay workflow",
            carrier_class="diagnostic_shadow",
            authority_impacting="conditional",
            authority_boundary=(
                "Authority participation requires recorded evidence inclusion and "
                "required-gate enforcement under declared policy."
            ),
            notes="Diagnostic / overlay carrier.",
        )

    if any(
        token in identity_l
        for token in (
            "pages",
            "publish",
            "publication",
            "badges",
        )
    ):
        return entry(
            name=name,
            path=rel,
            surface_type="workflow",
            primary_role="publication workflow",
            carrier_class="publication",
            authority_impacting="no",
            authority_boundary="Derived carrier only",
            publishes_artifacts=["Pages", "badges", "reader artifacts"],
            notes="Publication / reader carrier. Does not create release authority.",
        )

    if any(
        token in identity_l
        for token in (
            "shadow",
            "paradox",
            "experiment",
        )
    ):
        return entry(
            name=name,
            path=rel,
            surface_type="workflow",
            primary_role="shadow / diagnostic workflow",
            carrier_class="diagnostic_shadow",
            authority_impacting="conditional",
            authority_boundary=(
                "Authority participation requires recorded evidence inclusion and "
                "required-gate enforcement under declared policy."
            ),
            notes="Diagnostic / shadow carrier.",
        )

    if any(
        token in identity_l
        for token in (
            "hygiene",
            "lint",
            "security",
            "scan",
        )
    ):
        return entry(
            name=name,
            path=rel,
            surface_type="workflow",
            primary_role="repository hygiene workflow",
            carrier_class="advisory",
            authority_impacting="no",
            authority_boundary="Non-authorizing guard carrier",
            notes="Repository hygiene / security signal carrier.",
        )

    return entry(
        name=name,
        path=rel,
        surface_type="workflow",
        primary_role="unclassified workflow",
        carrier_class="advisory",
        authority_impacting="conditional",
        authority_boundary="Requires maintainer classification before authority use",
        notes="Workflow requires explicit carrier-role review if authority-adjacent.",
    )


def static_authority_entries(repo_root: Path) -> list[dict[str, Any]]:
    candidates = [
        entry(
            name="Declared gate policy",
            path="pulse_gate_policy_v0.yml",
            surface_type="policy",
            primary_role="declared gate policy",
            carrier_class="policy",
            authority_impacting="yes",
            authority_boundary="Defines required gate sets by lane",
            required_gate_participation=True,
        ),
        entry(
            name="Gate registry",
            path="pulse_gate_registry_v0.yml",
            surface_type="registry",
            primary_role="gate identity registry",
            carrier_class="policy",
            authority_impacting="yes",
            authority_boundary="Defines gate identity and interpretation",
            required_gate_participation=True,
        ),
        entry(
            name="Status schema directory",
            path="schemas/status",
            surface_type="schema",
            primary_role="status contract carrier",
            carrier_class="status_contract",
            authority_impacting="yes",
            authority_boundary="Defines admissible release-state artifacts",
        ),
        entry(
            name="check_gates.py",
            path="PULSE_safe_pack_v0/tools/check_gates.py",
            surface_type="tool",
            primary_role="strict fail-closed gate enforcement",
            carrier_class="enforcement",
            authority_impacting="yes",
            authority_boundary="Enforces literal true-only required gate semantics",
            required_gate_participation=True,
         entry(
            name="Release decision materializer",
            path="PULSE_safe_pack_v0/tools/materialize_release_decision.py",
            surface_type="tool",
            primary_role="release-decision materialization",
            carrier_class="authority",
            authority_impacting="yes",
            authority_boundary=(
                "Materializes release-decision labels from recorded status, "
                "declared policy, and target context"
            ),
            reads_artifacts=["status.json", "pulse_gate_policy_v0.yml"],
            writes_artifacts=["release_decision_v0.json"],
            required_gate_participation=True,
        ),
        entry(
            name="Artifact provenance binding builder",
            path="PULSE_safe_pack_v0/tools/build_artifact_provenance_binding_v0.py",
            surface_type="tool",
            primary_role="binding carrier materialization",
            carrier_class="binding",
            authority_impacting="yes",
            authority_boundary="Builds digest-backed artifact relation carrier",
        ),
        entry(
            name="Artifact provenance binding verifier",
            path="PULSE_safe_pack_v0/tools/verify_artifact_provenance_binding_v0.py",
            surface_type="tool",
            primary_role="binding carrier verification",
            carrier_class="binding",
            authority_impacting="yes",
            authority_boundary="Verifies digest-backed artifact relation carrier",
        ),
        entry(
            name="Quality Ledger renderer",
            path="PULSE_safe_pack_v0/tools/render_quality_ledger.py",
            surface_type="tool",
            primary_role="reader carrier renderer",
            carrier_class="reader",
            authority_impacting="conditional",
            authority_boundary="Non-authorizing carrier; must preserve public reader boundary",
        ),
        entry(
            name="Release authority cryptographic binding boundary",
            path="docs/RELEASE_AUTHORITY_CRYPTOGRAPHIC_BINDING_v0.md",
            surface_type="documentation",
            primary_role="cryptographic binding boundary documentation",
            carrier_class="binding",
            authority_impacting="no",
            authority_boundary="Documentation carrier for binding boundary",
        ),
        entry(
            name="Authority impact audit checklist",
            path="docs/AUTHORITY_IMPACT_AUDIT_CHECKLIST_v0.md",
            surface_type="documentation",
            primary_role="authority-impact human review checklist",
            carrier_class="audit_preservation",
            authority_impacting="no",
            authority_boundary="Review carrier",
        ),
        entry(
            name="External verification path",
            path="docs/EXTERNAL_VERIFICATION_PATH_v0.md",
            surface_type="documentation",
            primary_role="external verification path",
            carrier_class="audit_preservation",
            authority_impacting="no",
            authority_boundary="External verification carrier",
        ),
        entry(
            name="Maintainer authority boundary",
            path="docs/MAINTAINER_AUTHORITY_BOUNDARY_v0.md",
            surface_type="documentation",
            primary_role="maintainer authority boundary",
            carrier_class="audit_preservation",
            authority_impacting="no",
            authority_boundary="Repository change-control carrier",
        ),
    ]

    existing: list[dict[str, Any]] = []
    for item in candidates:
        path = repo_root / item["path"]
        if path.exists():
            existing.append(item)
    return existing


def collect_workflow_entries(repo_root: Path) -> list[dict[str, Any]]:
    workflows_dir = repo_root / ".github" / "workflows"
    if not workflows_dir.is_dir():
        return []
    return [
        classify_workflow(path, repo_root=repo_root)
        for path in sorted(workflows_dir.glob("*.yml"))
    ] + [
        classify_workflow(path, repo_root=repo_root)
        for path in sorted(workflows_dir.glob("*.yaml"))
    ]


def drift_findings(entries: list[dict[str, Any]]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []

    for item in entries:
        if item["primary_role"] == "unclassified workflow":
            findings.append(
                {
                    "severity": "warning",
                    "path": item["path"],
                    "finding": "workflow requires explicit carrier-role classification",
                }
            )

        if (
            item["carrier_class"] in {"publication", "reader", "diagnostic_shadow"}
            and item["authority_impacting"] == "yes"
        ):
            findings.append(
                {
                    "severity": "error",
                    "path": item["path"],
                    "finding": "non-authorizing carrier classified as authority-impacting",
                }
            )

    return findings


def build_inventory(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    entries = collect_workflow_entries(repo_root) + static_authority_entries(repo_root)

    return {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "generated_utc": utc_now(),
        "repository_root": repo_root.as_posix(),
        "authority_carrier": AUTHORITY_PATH,
        "entry_count": len(entries),
        "entries": entries,
        "drift_findings": drift_findings(entries),
    }


def markdown_table(inventory: dict[str, Any]) -> str:
    lines = [
        "# Normative vs Shadow Inventory Report v0",
        "",
        "## Summary",
        "",
        f"- schema_id: `{inventory['schema_id']}`",
        f"- schema_version: `{inventory['schema_version']}`",
        f"- generated_utc: `{inventory['generated_utc']}`",
        f"- entry_count: `{inventory['entry_count']}`",
        "",
        "Authority carrier:",
        "",
        "```text",
        inventory["authority_carrier"],
        "```",
        "",
        "## Inventory",
        "",
        "| Surface / workflow | Path | Carrier class | Authority-impacting | Boundary |",
        "|---|---|---|---|---|",
    ]

    for item in inventory["entries"]:
        lines.append(
            "| {name} | `{path}` | `{carrier}` | `{impact}` | {boundary} |".format(
                name=str(item["name"]).replace("|", "\\|"),
                path=str(item["path"]).replace("|", "\\|"),
                carrier=str(item["carrier_class"]).replace("|", "\\|"),
                impact=str(item["authority_impacting"]).replace("|", "\\|"),
                boundary=str(item["authority_boundary"]).replace("|", "\\|"),
            )
        )

    lines.extend(["", "## Drift findings", ""])

    findings = inventory.get("drift_findings") or []
    if not findings:
        lines.append("No drift findings recorded.")
    else:
        lines.extend(
            [
                "| Severity | Path | Finding |",
                "|---|---|---|",
            ]
        )
        for finding in findings:
            lines.append(
                "| {severity} | `{path}` | {finding} |".format(
                    severity=finding["severity"],
                    path=finding["path"],
                    finding=finding["finding"].replace("|", "\\|"),
                )
            )

    lines.append("")
    return "\n".join(lines)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    args = parser.parse_args()

    repo_root = Path(args.repo_root)
    inventory = build_inventory(repo_root)

    write_json(Path(args.out_json), inventory)
    write_text(Path(args.out_md), markdown_table(inventory))

    print(f"Wrote {args.out_json}")
    print(f"Wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

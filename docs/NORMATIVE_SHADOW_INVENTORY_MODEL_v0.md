# Normative vs Shadow Inventory Model v0

## Purpose

Normative vs Shadow Inventory Model v0 defines how PULSE classifies repository workflows, artifacts, reports, ledgers, diagnostics, publication surfaces, and auxiliary tools by authority role.

The purpose is to prevent shadow, diagnostic, publication, audit, or reader carriers from drifting into implicit release-authority status as the repository grows.

## Authority carrier

The PULSEmech authority carrier remains:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

A repository surface participates in release authority only when it is part of this path or when a specific artifact field is folded into recorded release evidence and enforced as a required gate under declared policy.

## Inventory classes

| Class | Mechanical role | Authority boundary |
|---|---|---|
| Normative authority carrier | Carries release-authority input, materialization, validation, or enforcement | Authority-impacting |
| Enforcement carrier | Performs strict fail-closed allow/block behavior | Authority-impacting |
| Policy carrier | Defines required, core-required, release-required, or advisory gate sets | Authority-impacting |
| Status contract carrier | Defines admissible release-state artifacts | Authority-impacting |
| Binding carrier | Carries digest-backed artifact relation around the authority path | Authority-impacting when schema/builder/verifier changes |
| Attestation carrier | Attests the binding carrier | Authority-impacting when subject, permissions, or attestation path changes |
| Reader carrier | Presents recorded state | Non-authorizing carrier |
| Trace carrier | Preserves reconstruction trace | No independent decision function |
| Audit / preservation carrier | Preserves reconstructable evidence and decision artifacts | Non-authorizing carrier |
| Publication carrier | Publishes derived reader artifacts | Derived carrier only |
| Diagnostic / shadow carrier | Produces candidate evidence signals or review state | Authority participation requires recorded evidence inclusion and required-gate enforcement under declared policy |
| Advisory carrier | Provides recommendation, qualification, or review signal | Non-authorizing unless promoted through declared policy |
| Experimental carrier | Runs exploratory or shadow-only experiments | Non-authorizing carrier |

## Normative authority carriers

A surface is normative authority-bearing when it can alter:

```text
release input
declared policy
workflow-effective required gate set
status admissibility
strict enforcement
release decision materialization
binding carrier
attestation carrier
```

Examples:

```text
pulse_gate_policy_v0.yml
pulse_gate_registry_v0.yml
schemas/status/*
PULSE_safe_pack_v0/tools/check_gates.py
PULSE_safe_pack_v0/tools/materialize_release_decision.py
PULSE_safe_pack_v0/tools/build_artifact_provenance_binding_v0.py
PULSE_safe_pack_v0/tools/verify_artifact_provenance_binding_v0.py
.github/workflows/pulse_ci.yml release-authority path
```

## Shadow and diagnostic carriers

Shadow and diagnostic carriers may inspect, compare, contextualize, stress-test, or summarize the authority path.

They do not alter release authority by existence.

Examples:

```text
EPF overlays
stability maps
separation-phase overlays
recognition / drift reports
parameter golf companions
governance shadow reports
advisory release-grade qualification checks
```

A shadow or diagnostic output participates in release authority only when:

```text
1. a specific artifact field is folded into recorded release evidence;
2. the field is referenced by declared policy;
3. the field is enforced as a required gate;
4. the enforcement path is strict fail-closed.
```

No whole shadow surface is implicitly promoted.

## Reader carriers

Reader carriers present recorded state.

Examples:

```text
Quality Ledger
public status URL
release-decision reader section
Pages-rendered views
public report cards
```

Boundary:

```text
reader carrier ≠ authority carrier
reader presentation ≠ release decision
reader artifact ≠ recorded authority source
```

Reader carriers must preserve parity with recorded artifacts.

## Trace carriers

Trace carriers preserve the reconstruction path.

Examples:

```text
release_authority_v0.json
release_decision_v0.json
release authority manifest sections
operator handoff reports
traceability summaries
```

Boundary:

```text
trace carrier = reconstruction aid
trace carrier ≠ decision engine
```

## Audit and preservation carriers

Audit and preservation carriers group artifacts for review, replay, or archival inspection.

Examples:

```text
release-authority-audit-bundle
release reference packages
evidence packets
preservation snapshots
audit bundles
```

Boundary:

```text
audit / preservation carrier = reconstructable artifact package
audit / preservation carrier ≠ release decision
```

## Publication carriers

Publication carriers expose or advertise derived state.

Examples:

```text
README public links
badges
GitHub Pages
Zenodo metadata references
GitHub release notes
public report links
```

Boundary:

```text
publication carrier = derived carrier only
publication carrier ≠ recorded authority artifact
```

Release / DOI / Zenodo paths require explicit release / publication review.

## Binding and attestation carriers

Binding and attestation carriers strengthen artifact relationship verification.

Binding carrier:

```text
artifact_provenance_binding_v0.json
```

Verification carrier:

```text
verify_artifact_provenance_binding_v0.py
```

Attestation subject:

```text
artifact_provenance_binding_v0.json
```

Attestation carrier:

```text
later / configured cryptographic attestation over the binding carrier
```

Boundary:

```text
binding carrier = digest-backed artifact relation
attestation carrier = cryptographic attestation over the binding carrier
authority carrier = PULSEmech path
```

## Workflow inventory model

Every workflow should be classifiable under one primary role.

| Workflow role | Mechanical meaning | Authority boundary |
|---|---|---|
| Primary release-authority workflow | Produces, validates, materializes, enforces, binds, or attests authority artifacts | Authority-impacting |
| Core baseline workflow | Checks baseline/core mechanics without becoming a second release path | Non-authorizing unless explicitly declared |
| Tools smoke workflow | Checks tool/test manifest integrity | Non-authorizing guard carrier |
| Docs hygiene workflow | Checks documentation consistency | Non-authorizing carrier |
| Publication workflow | Publishes Pages, badges, previews, or reader outputs | Derived carrier only |
| Shadow experiment workflow | Runs exploratory or advisory experiments | Non-authorizing carrier |
| Security / hygiene workflow | Checks repository hygiene or security signals | Non-authorizing unless promoted through required gate |
| Reviewer bundle workflow | Creates review packages | Audit / preservation carrier |

## Inventory record fields

A normative/shadow inventory record should contain:

```text
name
path
surface_type
primary_role
carrier_class
authority_boundary
authority_impacting
reads_artifacts
writes_artifacts
publishes_artifacts
required_gate_participation
attestation_participation
release_path_participation
notes
```

Suggested `carrier_class` values:

```text
authority
enforcement
policy
status_contract
binding
attestation
reader
trace
audit_preservation
publication
diagnostic_shadow
advisory
experimental
```

Suggested `authority_impacting` values:

```text
yes
no
conditional
```

## Inventory classification rules

### Rule 1 — Authority by path participation

A workflow or artifact is authority-impacting when it participates in:

```text
status.json production or admissibility
declared gate policy selection
workflow-effective required gate materialization
strict fail-closed enforcement
release decision materialization
artifact provenance binding
attestation over the binding carrier
```

### Rule 2 — Shadow by default

Diagnostic, advisory, experimental, and shadow outputs remain non-authorizing unless a specific field is folded into recorded evidence and enforced as a required gate under declared policy.

### Rule 3 — Publication is derived

Pages, badges, README links, and public display surfaces are derived carriers.

They publish or display recorded state.

They do not become recorded authority artifacts by publication.

### Rule 4 — Trace is reconstructive

Trace artifacts reconstruct or explain the authority path.

They do not compute an independent decision.

### Rule 5 — Binding and attestation are relation carriers

Binding and attestation carriers verify or attest the recorded artifact relationship.

They strengthen provenance.

They do not replace the PULSEmech authority path.

## Inventory review checklist

For each workflow or artifact, answer:

```text
Does it produce status.json?
Does it alter status admissibility?
Does it alter declared policy?
Does it alter required gate materialization?
Does it alter check_gates.py enforcement?
Does it alter release decision materialization?
Does it alter artifact provenance binding?
Does it alter attestation subject or permissions?
Does it publish reader artifacts?
Does it only preserve or summarize trace?
Does it run shadow diagnostics?
Does it write to release / DOI / Zenodo paths?
```

Classification:

```text
If yes to authority production/materialization/enforcement → authority-impacting.
If yes only to reader/publication → publication / reader carrier.
If yes only to trace/audit packaging → trace or audit / preservation carrier.
If yes only to diagnostics/advisory → diagnostic / shadow carrier.
If yes to attestation or binding → binding / attestation carrier.
```

## Minimal inventory report shape

A future machine-generated report should be able to emit:

```json
{
  "schema_id": "pulse.normative_shadow_inventory.v0",
  "schema_version": "0.1.0",
  "generated_utc": "...",
  "repository": "...",
  "commit": "...",
  "entries": [
    {
      "name": "PULSE CI",
      "path": ".github/workflows/pulse_ci.yml",
      "surface_type": "workflow",
      "primary_role": "primary release-authority workflow",
      "carrier_class": "authority",
      "authority_impacting": "yes",
      "authority_boundary": "status.json -> declared gate policy -> workflow-effective required gate set -> strict fail-closed CI enforcement",
      "reads_artifacts": ["status.json", "pulse_gate_policy_v0.yml"],
      "writes_artifacts": ["release_decision_v0.json", "artifact_provenance_binding_v0.json"],
      "publishes_artifacts": ["release-authority-artifact-binding-v0"],
      "required_gate_participation": true,
      "attestation_participation": true,
      "release_path_participation": true,
      "notes": "Primary release-authority workflow."
    }
  ]
}
```

## Human-readable inventory table shape

A future report should also emit a Markdown table:

```text
Surface / workflow
Path
Carrier class
Authority-impacting
Boundary
Notes
```

This lets reviewers quickly see whether any shadow, diagnostic, publication, or reader surface has drifted toward implicit authority.

## Drift conditions

The inventory should flag drift when:

```text
a shadow workflow writes release artifacts
a publication workflow writes authority artifacts
a reader carrier modifies status.json
a diagnostic output is used as a required gate without declaration
an attestation job receives broader permissions than needed
a mutable action tag is used in an authority / attestation path
a workflow publishes release-facing artifacts without declared carrier role
a new workflow is not classified
```

## Relation to authority impact checklist

Authority Impact Audit Checklist v0 defines what kinds of PR changes require authority-impact review.

Normative vs Shadow Inventory Model v0 defines how repository surfaces are classified so that hidden authority drift can be detected.

The two documents are complementary:

```text
Authority Impact Audit Checklist v0
= change review checklist

Normative vs Shadow Inventory Model v0
= surface / workflow classification model
```

## Future machine report

A later PR may add:

```text
scripts/build_normative_shadow_inventory_v0.py
tests/test_normative_shadow_inventory_v0.py
docs/NORMATIVE_SHADOW_INVENTORY_REPORT_v0.md
```

That future machine report should classify workflows and artifacts according to this model.

It should remain a review carrier.

It must not become an independent release-decision engine.

## Boundary held by this document

This document defines the normative vs shadow inventory model.

It does not change:

```text
PULSEmech decision semantics
gate policy
required gate wiring
check_gates.py behavior
status schema
CI allow/block behavior
Quality Ledger renderer behavior
artifact provenance binding behavior
attestation workflow behavior
release tags
DOI / Zenodo path
```

The PULSEmech authority carrier remains:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

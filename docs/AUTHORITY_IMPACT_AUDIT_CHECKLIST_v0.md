# Authority Impact Audit Checklist v0

## Purpose

Authority Impact Audit Checklist v0 defines the human review checklist for changes that may affect the PULSE release-authority path.

The checklist identifies which repository changes can alter release authority, which changes are carrier-only, and which changes require explicit authority-impact review before merge.

## Authority carrier

The PULSEmech authority carrier remains:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

A change is authority-impacting when it can alter one of these elements, their materialization, their validation, or their enforcement.

## Authority-impacting change classes

| Change class | Examples | Authority impact boundary |
|---|---|---|
| Gate policy changes | `pulse_gate_policy_v0.yml`, selected gate sets, `required`, `core_required`, `release_required`, advisory/required movement | Alters declared gate policy or required-gate materialization |
| Gate registry changes | `pulse_gate_registry_v0.yml`, gate identity, gate meaning, gate category, gate deprecation | Alters gate identity or interpretation |
| Required gate wiring | `PULSE_POLICY_SET`, release-required append logic, policy-to-require conversion, workflow-effective gate set construction | Alters materialized required gate set |
| Gate enforcement logic | `check_gates.py`, true-only semantics, missing-gate handling, exit-code behavior | Alters strict fail-closed enforcement |
| Status contract changes | `schemas/status/*`, `STATUS_CONTRACT.md`, status field requirements, release-grade overlay | Alters release-state artifact admissibility |
| Release-grade guards | prod run-mode guard, no-stub guard, detector materialization guard, external evidence guard | Alters which states can enter release-grade path |
| Release decision materialization | `release_decision_v0.json`, `materialize_release_decision.py`, release-level labels, target selection | Alters release-decision record or label materialization |
| Artifact provenance binding | `artifact_provenance_binding_v0.json`, binding schema, builder, verifier, binding hash, workflow-effective gate-set digest | Alters provenance carrier for the authority path |
| Attestation wiring | attestation subject, isolated attestation job, attestation permissions, SHA-pinned attest action, attestation subject path | Alters cryptographic attestation carrier |
| Primary CI release path | `.github/workflows/pulse_ci.yml` steps that produce, validate, enforce, bind, attest, or upload release-authority artifacts | Alters release-authority execution path |

## Carrier-only change classes

| Change class | Examples | Boundary |
|---|---|---|
| Reader carrier changes | Quality Ledger wording, reader-surface presentation, report layout | Non-authorizing carrier unless a specific artifact field is promoted through declared policy |
| Trace carrier changes | release authority manifest rendering, trace summary, audit-sidecar presentation | No independent decision function |
| Audit / preservation carrier changes | audit bundles, preservation packets, reconstruction packages | Non-authorizing carrier |
| Publication carrier changes | README public links, Pages display wording, badges, public reader surfaces | Derived carriers only |
| Diagnostic / shadow changes | EPF overlays, stability maps, paradox layers, recognition / drift surfaces | Authority participation requires recorded evidence inclusion and required-gate enforcement under declared policy |
| Documentation-only boundary clarification | docs that clarify existing roles without changing code, schema, policy, workflow, or artifacts | No authority impact when carrier roles remain unchanged |

## Authority-impact review checklist

For every PR, answer these questions before merge.

### 1. Declared scope

```text
PR class:
Changed files:
Expected carrier role:
Forbidden paths:
```

The PR must state whether it is:

```text
authority-impacting
carrier-only
docs-only
shadow-only
publication-only
test-only
```

### 2. Authority carrier touch check

Mark `yes` if the PR changes any of these:

```text
pulse_gate_policy_v0.yml
pulse_gate_registry_v0.yml
PULSE_safe_pack_v0/tools/check_gates.py
schemas/status/*
docs/STATUS_CONTRACT.md
.github/workflows/pulse_ci.yml release-authority path
release_decision_v0 schema / materializer
artifact_provenance_binding schema / builder / verifier
attestation workflow / subject / permissions
```

If any answer is `yes`, the PR requires authority-impact review.

### 3. Required-gate materialization check

Review whether the PR changes:

```text
PULSE_POLICY_SET
core_required
required
release_required
policy_to_require_args.py behavior
required gate ordering
required gate de-duplication
release-grade gate append logic
workflow-effective required gate set
```

Authority-impact note required when any item changes.

### 4. Enforcement check

Review whether the PR changes:

```text
literal true-only PASS semantics
missing gate behavior
invalid status behavior
exit code semantics
allow/block decision path
```

Authority-impact note required when any item changes.

### 5. Status admissibility check

Review whether the PR changes:

```text
status.json required fields
metrics.run_mode semantics
diagnostics.gates_stubbed semantics
diagnostics.scaffold semantics
stub_profile semantics
detectors_materialized_ok semantics
external_summaries_present semantics
external_all_pass semantics
release-grade status overlay
```

Authority-impact note required when any item changes.

### 6. Reader / publication boundary check

Review whether public surfaces could be read as release authority.

Check:

```text
Quality Ledger
Pages
badges
README public links
public status URL
release decision display
public surface evidence state
```

Reader / publication carrier changes must preserve the boundary:

```text
reader carrier ≠ authority carrier
publication carrier ≠ recorded authority artifact
trace carrier ≠ decision engine
audit bundle ≠ release decision
```

### 7. Provenance / attestation check

Review whether the PR changes:

```text
artifact_provenance_binding_v0.json shape
binding schema
binding builder
binding verifier
binding_hash rule
canonical JSON byte rule
attestation subject
attestation permissions
actions/attest pin
attestation artifact download path
attestation skip conditions
```

Authority-impact note required when any item changes.

### 8. Release / DOI / Zenodo boundary check

Review whether the PR changes:

```text
release tags
GitHub release metadata
Zenodo DOI references
Zenodo metadata
CITATION.cff
archive artifacts
publication version labels
```

These changes require explicit release / publication review.

Routine development PRs must not modify this path.

## Authority-impact note format

For authority-impacting PRs, include this note in the PR body:

```text
Authority-impact review:
- Changed authority carrier:
- Changed materialized required gate path:
- Changed enforcement behavior:
- Changed status admissibility:
- Changed provenance / attestation carrier:
- Required tests:
- Preserved boundaries:
```

If the PR is not authority-impacting, include:

```text
Authority-impact review:
- Authority carrier changed: no
- Gate policy changed: no
- Required gate wiring changed: no
- check_gates.py changed: no
- status schema changed: no
- CI allow/block behavior changed: no
- provenance / attestation carrier changed: no
- release / DOI / Zenodo path changed: no
```

## Merge boundary

A PR can be merged under this checklist when:

```text
declared scope matches changed files
authority-impact class is explicit
forbidden paths are unchanged
required tests pass
release / DOI / Zenodo path is untouched unless explicitly declared
reader / publication carrier boundaries remain explicit
```

Authority-impacting PRs require an explicit review note before merge.

## Mechanical boundary summary

The checklist preserves the carrier split:

| Carrier | Boundary |
|---|---|
| Authority carrier | `status.json` → declared gate policy → workflow-effective materialized required gate set → strict fail-closed CI enforcement |
| Reader carrier | Non-authorizing carrier |
| Trace carrier | No independent decision function |
| Audit / preservation carrier | Non-authorizing carrier |
| Publication / reader carrier | Derived carrier only |
| Diagnostic / shadow carrier | Authority participation requires recorded evidence inclusion and required-gate enforcement under declared policy |
| Binding carrier | Digest-backed artifact relation carrier |
| Attestation carrier | Cryptographic attestation over the binding carrier |

## Checklist status

Authority Impact Audit Checklist v0 is a human review checklist.

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

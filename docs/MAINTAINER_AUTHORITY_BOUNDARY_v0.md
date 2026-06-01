# Maintainer Authority Boundary v0

## Purpose

Maintainer Authority Boundary v0 defines the human maintainer authority boundary for PULSE repository changes.

The document records how merge authority, authority-impact review, carrier boundaries, release / DOI / Zenodo protection, and future multi-maintainer governance fit around the PULSEmech authority path.

This is a governance-boundary document.

It does not create a second release-decision engine.

## PULSEmech authority carrier

The PULSEmech authority carrier remains:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

Maintainer authority governs repository changes.

PULSEmech authority governs release-decision mechanics.

The two boundaries remain distinct.

## Maintainer authority model

Current maintainer authority model:

```text
single-maintainer controlled repository
manual merge authority
CI-enforced mechanical checks
explicit authority-impact review for authority-bearing changes
docs / carrier-boundary review for non-authorizing surfaces
release / DOI / Zenodo path frozen unless explicitly declared
```

The maintainer may merge when:

```text
scope is declared
changed files match scope
required checks pass
authority-impact status is explicit
forbidden paths are unchanged
release / DOI / Zenodo path is untouched unless explicitly declared
```

## Maintainer carrier role

| Carrier | Mechanical role | Boundary |
|---|---|---|
| Maintainer | Controls repository merge decisions | Merge authority carrier |
| CI checks | Enforce declared mechanical checks | Verification carrier |
| PULSEmech path | Carries release-authority mechanics | Authority carrier |
| Codex / AI reviewer | Provides review signal when available | Non-authorizing review carrier |
| External reviewer | Provides verification / audit signal | Non-authorizing review carrier unless separately adopted |
| GitHub branch protection | Enforces repository merge constraints | Repository protection carrier |

## Merge authority boundary

Merge authority is a repository-maintenance function.

It covers:

```text
branch merge
PR scope acceptance
review conversation resolution
release / publication boundary protection
authority-impact note acceptance
```

Merge authority does not override:

```text
status.json
declared gate policy
workflow-effective required gate set
strict fail-closed CI enforcement
release-decision materialization
artifact provenance binding
attestation record
```

## Authority-impact review boundary

A PR requires authority-impact review when it changes any of these:

```text
pulse_gate_policy_v0.yml
pulse_gate_registry_v0.yml
PULSE_safe_pack_v0/tools/check_gates.py
schemas/status/*
docs/STATUS_CONTRACT.md
.github/workflows/pulse_ci.yml release-authority path
release_decision_v0 schema / materializer
artifact_provenance_binding schema / builder / verifier
attestation subject / attestation permissions / attestation workflow
release / DOI / Zenodo path
```

Authority-impacting PRs must include:

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

## Non-authorizing carrier review boundary

Carrier-only PRs must preserve their declared boundary.

| Carrier | Boundary phrase |
|---|---|
| Reader carrier | Non-authorizing carrier |
| Trace carrier | No independent decision function |
| Audit / preservation carrier | Non-authorizing carrier |
| Publication / reader carrier | Derived carrier only |
| Diagnostic / shadow carrier | Authority participation requires recorded evidence inclusion and required-gate enforcement under declared policy |
| External verification carrier | Review carrier |
| AI / Codex review carrier | Non-authorizing review signal |

Carrier-only PRs should state:

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

## Release / DOI / Zenodo boundary

Release / DOI / Zenodo paths are protected publication surfaces.

Routine development PRs must not modify:

```text
release tags
GitHub release metadata
Zenodo DOI references
Zenodo metadata
CITATION.cff
archive artifacts
publication version labels
```

Changes to this path require explicit release / publication review.

Release / DOI / Zenodo changes must not be bundled with unrelated development changes.

## Codex / AI reviewer boundary

Codex or any AI reviewer may provide:

```text
review signal
diff-risk signal
line-level issue location
test command suggestion
verification summary
```

Codex or any AI reviewer does not carry:

```text
merge authority
release authority
policy authority
gate authority
attestation authority
publication authority
```

AI-generated suggestions require maintainer review before merge.

AI review comments are review signals, not mechanical truth.

Mechanical truth remains:

```text
repository files
declared scope
CI checks
tests
status artifacts
policy artifacts
binding artifacts
attestation records
manual merge decision
```

## External reviewer boundary

External reviewers may provide:

```text
verification report
reproduction note
case study
audit finding
third-party reference integration
```

External verification is a review carrier.

It does not alter:

```text
status.json
declared gate policy
workflow-effective materialized required gate set
check_gates.py behavior
CI allow/block result
release decision materialization
artifact_provenance_binding_v0.json
attestation record
```

External findings may become actionable when a maintainer opens a scoped PR.

## Quorum boundary

Current model:

```text
single-maintainer merge authority
```

Quorum rules are reserved for a future multi-maintainer model.

Future multi-maintainer adoption may define:

```text
authority-impact PR approval count
release / DOI / Zenodo approval rule
external reviewer adoption rule
maintainer rotation rule
emergency rollback rule
```

Until then, quorum language must not imply a maintainer group that does not exist.

## Maintainer rotation boundary

Current model:

```text
no active maintainer rotation
```

Future rotation may be introduced only through a dedicated governance PR.

That PR should define:

```text
maintainer eligibility
authority-impact approval boundary
handoff process
repository access boundary
release / DOI / Zenodo custody
emergency access protocol
```

## Emergency / rollback boundary

Emergency or rollback actions must preserve artifact truth.

Emergency action may:

```text
revert a repository commit
disable a broken workflow path
restore a previous working configuration
block a release path
```

Emergency action must not:

```text
silently rewrite release decision artifacts
retroactively alter status.json meaning
replace check_gates.py semantics without authority-impact review
modify Zenodo / DOI paths without explicit publication review
erase provenance or attestation records
```

Emergency fixes require a follow-up note explaining:

```text
trigger
changed files
authority impact
tests / checks run
preserved boundaries
```

## PR class model

Suggested PR classes:

| PR class | Typical files | Review boundary |
|---|---|---|
| `docs(authority)` | authority-boundary docs | Docs-only unless policy/workflow/schema touched |
| `docs(validation)` | external verification docs | Docs-only |
| `docs(surface)` | reader/publication wording | Non-authorizing carrier boundary |
| `feat(crypto)` | binding / attestation mechanics | Authority-impact review required |
| `ci(crypto)` | binding / attestation CI wiring | Authority-impact review required |
| `fix(ledger)` | Quality Ledger renderer | Reader carrier review; authority boundary check required |
| `test(ci)` | smoke / workflow tests | Test-only unless workflow changed |
| `fix(ci)` | workflow repair | Authority-impact review if release path touched |
| `docs(governance)` | governance boundary docs | Docs-only unless access/release paths touched |

## Merge checklist

Before merge, confirm:

```text
PR class declared
changed files match declared scope
authority-impact status declared
forbidden paths unchanged
required checks pass
Codex / AI review comments resolved when present
release / DOI / Zenodo path untouched unless explicitly declared
reader / publication boundaries preserved
binding / attestation boundaries preserved when relevant
```

## Maintainer decision record

For authority-impacting PRs, the maintainer should include a short decision record:

```text
Maintainer decision:
- PR class:
- Authority-impacting: yes / no
- Changed authority carrier:
- Required checks passed:
- Review signals considered:
- Merge decision:
- Preserved boundaries:
```

For docs-only PRs, the decision record may be short:

```text
Maintainer decision:
- PR class: docs-only
- Authority-impacting: no
- Scope checked: yes
- Merge decision: accepted
```

## Boundary held by this document

This document defines maintainer authority boundary for repository changes.

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

The maintainer boundary governs repository change control around that path.

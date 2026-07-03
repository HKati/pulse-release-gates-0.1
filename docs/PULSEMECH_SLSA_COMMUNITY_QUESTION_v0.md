# PULSEmech / SLSA community question v0

## Status

Draft technical community question.

This document prepares a future SLSA / OpenSSF community question about the relationship between PULSEmech release-transition evaluation and SLSA / in-toto-style provenance.

This document is not a submitted issue.

This document is not a standards proposal.

This document is not a certification request.

This document is not a SLSA conformance claim.

This document does not change workflow behavior, runtime code, gate policy, verifier behavior, materializer behavior, schema behavior, fail-closed CI enforcement, branch protection settings, dependency files, release metadata, or release-authority semantics.

## Purpose

PULSEmech has a technical alignment note describing how SLSA / in-toto-style provenance can be read alongside PULSEmech release-transition evaluation.

The next step is to prepare a concise technical question for SLSA / OpenSSF practitioners.

The goal is to ask for terminology and boundary guidance, not approval, certification, conformance judgment, or compliance status.

## Context

PULSEmech is a developer-side release-transition mechanism for AI-assisted and automation-heavy software workflows.

It evaluates whether a release transition may proceed from:

```text
recorded release evidence
declared policy
workflow-effective materialized gate set
verifier replay
check_gates.py enforcement
primary CI allow/block result
```

SLSA / in-toto-style provenance can describe artifact construction, source identity, build context, builder identity, and execution metadata.

PULSEmech can consume provenance as evidence.

PULSEmech still evaluates the release transition separately.

## Core technical question

Where should an artifact-bound, fail-closed release-transition mechanism sit relative to SLSA provenance verification?

More specifically:

```text
Should PULSEmech be described as:

1. a provenance consumer pattern;
2. a release-transition decision layer above SLSA-style provenance;
3. a separate in-toto predicate for release-transition evaluation;
4. a developer-side policy-gated release control that references SLSA concepts without claiming SLSA levels;
5. or another pattern?
```

## Proposed model

The proposed model keeps provenance and transition evaluation as separate layers.

```text
SLSA / in-toto provenance
→ artifact construction, source identity, build context, builder identity, execution metadata

PULSEmech release-transition evaluation
→ evidence admission, declared policy, workflow-effective materialized gates, verifier replay, check_gates.py enforcement, allow/block transition result
```

In this model, provenance is evidence input.

It is not itself the release-transition decision.

## Boundary

This draft does not claim:

```text
PULSEmech replaces SLSA
PULSEmech satisfies any SLSA Build Level
PULSEmech satisfies any SLSA Source Track level
PULSEmech is SLSA-certified
PULSEmech is OpenSSF-certified
PULSEmech creates compliance status
PULSEmech creates release authority by being discussed
```

The intended question is about vocabulary, predicate boundary, and consumer verification model.

## Technical details to include in the community question

A concise public question should include the following details.

### Mechanism

```text
PULSEmech evaluates release transitions from recorded evidence, declared policy, workflow-effective materialized gates, verifier replay, and CI enforcement.
```

### Evidence inputs

Potential evidence inputs include:

```text
status.json
required_gate_evidence_v0.json
release_evidence_input_manifest_v0.json
recorded_release_evidence_verifier_v0.json
release_decision_v0.json
artifact_provenance_binding_v0.json
external attestation verifier report, when active policy requires external evidence
```

### Provenance relationship

```text
SLSA / in-toto provenance may describe artifact construction and input identity.

PULSEmech may consume that provenance as evidence.

The release-transition decision remains a separate PULSEmech result.
```

### Decision output

```text
allow
block
```

A block result is a valid fail-closed transition result.

A completed qualified release-grade reference proof remains a separate qualification status.

## Questions for SLSA / OpenSSF practitioners

The future public question should ask:

```text
1. Is “provenance consumer pattern” an appropriate term for PULSEmech?
2. Should a release-transition decision be represented as a separate in-toto predicate?
3. If a separate predicate is appropriate, what boundaries should it preserve?
4. Which PULSEmech artifacts should be referenced as provenance resolved dependencies?
5. Which PULSEmech artifacts should remain inside the PULSEmech transition predicate?
6. How should builder identity be described for GitHub Actions-based evidence construction?
7. Should provenance statements and release-transition decision statements be signed separately?
8. What consumer verification procedure should be documented for a combined provenance + transition-evaluation model?
9. What wording avoids false SLSA-level claims while preserving useful alignment?
10. Is there an existing SLSA / OpenSSF pattern this should follow instead?
```

## Candidate GitHub issue title

```text
Where should an artifact-bound release-transition decision layer sit relative to SLSA provenance verification?
```

## Candidate GitHub issue body

````markdown
We are preparing a technical alignment for PULSEmech, a developer-side release-transition mechanism for AI-assisted and automation-heavy software workflows.

PULSEmech does not claim a SLSA level.

It evaluates release transitions from recorded release evidence, declared policy, workflow-effective materialized gates, verifier replay, and CI enforcement.

The mechanism can consume SLSA / in-toto-style provenance as evidence, but the release-transition decision remains separate.

Proposed separation:

```text
SLSA / in-toto provenance
→ artifact construction, source identity, build context, builder identity, execution metadata

PULSEmech release-transition evaluation
→ evidence admission, declared policy, workflow-effective materialized gates, verifier replay, check_gates.py enforcement, allow/block transition result
```

We would appreciate terminology and boundary guidance.

Questions:

1. Is “provenance consumer pattern” an appropriate term here?
2. Should a release-transition decision be represented as a separate in-toto predicate?
3. Which artifacts should be referenced as SLSA provenance dependencies versus kept inside a PULSEmech transition predicate?
4. How should builder identity be described for GitHub Actions-based evidence construction?
5. Should provenance statements and release-transition decision statements be signed separately?
6. What wording avoids false SLSA-level claims while preserving useful alignment?
7. Is there an existing SLSA / OpenSSF pattern this should follow instead?

The goal is not certification or compliance status.

The goal is terminology, predicate boundary, and consumer verification guidance.
````

## Candidate short Slack / mailing-list version

```text
We are preparing a PULSEmech / SLSA alignment note and would appreciate terminology guidance.

PULSEmech is a developer-side release-transition mechanism. It can consume SLSA / in-toto-style provenance as evidence, but its output is a separate allow/block transition decision based on recorded evidence, declared policy, workflow-effective materialized gates, verifier replay, and CI enforcement.

We do not claim a SLSA level.

Question: should this be described as a provenance consumer pattern, a release-transition decision layer above provenance, a separate in-toto predicate, or another existing SLSA/OpenSSF pattern?
```

## Candidate repository reference list

If a public question is later opened, it may reference these repository documents:

```text
docs/PULSEMECH_SLSA_PROVENANCE_TO_TRANSITION_v0.md
docs/PULSEMECH_REQUIRED_CHECKS_AND_WORKFLOW_AUTHORITY_v0.md
docs/PULSEMECH_RELEASE_GRADE_REFERENCE_PROOF_PLAN_v0.md
docs/PULSEMECH_DEVELOPER_FIRST_POSITIONING_v0.md
```

The question should point to technical repository documents and artifact-bound mechanics.

It should not require readers to inspect publication pages, metadata pages, or other reader surfaces.

## Submission channel options

Potential channels:

```text
SLSA GitHub issue
SLSA Slack #slsa
SLSA mailing list
SLSA specification meeting
OpenSSF relevant working group
```

Use one channel first.

Do not cross-post until the first venue is chosen.

Prefer a GitHub issue if the question is expected to need durable links, examples, and follow-up.

Prefer Slack or mailing list only for a short terminology check.

## Pre-submission checklist

Before submitting the question publicly, verify:

```text
1. The SLSA alignment document is merged.
2. The required checks / workflow authority map is merged.
3. The release-grade proof plan is merged.
4. The dependency maintenance documents are clean and canonical.
5. No current publication-surface correction issue is embedded in the question.
6. The question does not claim SLSA conformance.
7. The question does not request certification.
8. The question does not frame PULSEmech as a compliance product.
9. The question asks for terminology and boundary guidance only.
10. The linked repository documents are stable enough for external review.
```

## Non-goals for the first community question

The first community question should not ask for:

```text
certification
conformance judgment
formal acceptance
standardization
governance endorsement
release approval
compliance interpretation
```

The first question should ask for:

```text
terminology
predicate boundary
consumer verification model
relationship to existing SLSA / in-toto patterns
```

## Expected useful outcomes

Useful answers may include:

```text
Use “provenance consumer” terminology.
Use a separate in-toto predicate.
Keep release-transition semantics out of SLSA build provenance.
Reference certain PULSE artifacts as resolved dependencies.
Define separate signing expectations.
Document builder identity more precisely.
Use an existing OpenSSF/SLSA pattern instead.
Do not frame this as SLSA-adjacent in the proposed way.
```

Any of these outcomes is useful.

The goal is to reduce ambiguity before implementation or public positioning.

## Maintenance rule

If the public question is later opened, record the public link in the recovery ledger or a dedicated community-interaction note.

Do not convert this draft document into the public issue record.

Keep this file as the prepared question and boundary record.

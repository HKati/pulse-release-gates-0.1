# PULSE External Review Entrypoint v0

## Purpose

This document defines the external-review entry path for PULSE.

Its role is to route external inspection into the PULSEmech release-authority
model while preserving the model.

PULSEmech is an artifact-bound release-authority mechanism for AI release
decisions.

External review is an inspection, reconstruction, and recommendation layer.

External-review output enters release authority through the same admission path
as any other release evidence:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```

This document is reviewer-facing documentation.

Release authority remains defined by the PULSEmech authority path.

## PULSEmech release-authority path

The PULSEmech release-authority path is:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```

A release decision is mechanically reviewable when this path can be
reconstructed from recorded artifacts, declared policy, materialized gates, and
workflow-effective CI enforcement.

## External-review role

External review inspects the relation between:

```text
documented PULSEmech identity
recorded release evidence
status.json release-state artifact
declared gate policy
workflow-effective materialized required gate set
strict fail-closed CI enforcement
reader surfaces
trace carriers
audit carriers
publication surfaces
reproducibility evidence
```

The review output is classified by operational role.

It may become:

```text
review context
authority-path finding
reader-surface finding
hardening finding
candidate evidence source
candidate policy requirement
reproducibility finding
audit supplement
traceability supplement
```

Each classification has a separate route.

## Review-output state model

External-review output starts as `review_context`.

It gains release-decision effect only through explicit admission into the
PULSEmech path.

The transition model is:

```text
review_context
→ triaged finding
→ candidate evidence source
→ admitted release evidence
→ status.json representation
→ declared gate-policy requirement
→ workflow-effective materialized required gate
→ strict fail-closed CI enforcement
→ release decision effect
```

This transition keeps review output inspectable without creating an independent
release-decision engine.

## Primary review question

The primary external-review question is:

```text
Can the recorded evidence-to-decision path be reconstructed, checked, and shown
to fail closed under declared policy?
```

This is the first question for PULSEmech review.

Other readings may provide context:

```text
governance reading
dashboard reading
MLOps reading
runtime-guardrail reading
supply-chain reading
adoption reading
maturity reading
```

Those readings are routed through the classification model in this document.

## Carrier map

| Carrier class | Operational role | Release relevance |
|---|---|---|
| Recorded release evidence | Input evidence for release-state construction | Direct release input when recorded for the candidate release |
| `status.json` | Release-state artifact | Represents recorded release state consumed by the gate path |
| Declared gate policy | Required-condition declaration | Defines which gates are required for the selected release lane |
| Workflow-effective materialized required gate set | Concrete required-gate set | Converts declared policy into enforceable CI requirements |
| Strict fail-closed CI enforcement | Enforcement layer | Produces the pre-deployment allow/block outcome |
| Quality Ledger | Reader surface over recorded state | Supports inspection of recorded state |
| Pages output | Publication / reader surface | Supports public inspection of derived or published artifacts |
| Dashboard / badge / rendered report | Reader surface | Supports human inspection and status communication |
| Audit bundle | Audit carrier | Supports reconstruction and external inspection |
| Trace carrier | Traceability carrier | Supports relation reconstruction across artifacts |
| External verification packet | Review carrier | Supports external reconstruction and reproducibility review |
| Publication snapshot | Publication binding carrier | Supports comparison between expected and published artifacts |
| Diagnostic output | Diagnostic carrier | Supports investigation and debugging |
| Shadow output | Non-enforcing observation carrier | Supports observation before promotion into policy |
| External-review output | Review carrier | Starts as review context and may enter the evidence-admission path |

## Evidence-admission transition for review output

For an external-review output to affect release authority, it follows this
admission path:

```text
external-review output
→ recorded release evidence
→ status.json representation
→ declared gate-policy requirement
→ workflow-effective materialized required gate
→ strict fail-closed CI enforcement
→ release decision effect
```

The release-relevant transition is explicit, artifact-bound, policy-declared,
materialized, and CI-enforced.

This preserves the PULSEmech authority model while allowing external review to
produce useful findings, candidate evidence, and hardening recommendations.

## Review procedure

A mechanically relevant external review proceeds in this order:

```text
1. Identify the release candidate, commit, workflow run, and reviewed artifact set.
2. Identify the recorded release evidence for that candidate.
3. Locate the status.json release-state artifact.
4. Identify the declared gate policy used for the release lane.
5. Reconstruct the workflow-effective materialized required gate set.
6. Inspect the CI enforcement step that consumes the materialized required gates.
7. Verify fail-closed behavior for missing, invalid, unknown, false, or unmapped
   required evidence.
8. Inspect reader surfaces against recorded artifacts.
9. Classify trace, audit, diagnostic, shadow, publication, and review outputs by
   operational role.
10. Classify findings as authority-path, reader-surface, hardening,
    reproducibility, traceability, audit, or candidate-policy findings.
```

A complete PULSEmech review reconstructs the release-authority path before
scoring surrounding maturity, adoption, packaging, or ecosystem context.

## Reading-frame routing

| Reading frame | Review function | Finding route |
|---|---|---|
| Release-authority review | Reconstructs the path from recorded evidence to fail-closed CI decision | Authority-path finding |
| Governance reading | Interprets responsibilities, oversight, process, and accountability | Governance-context or policy-candidate finding |
| Dashboard reading | Compares rendered status, ledger, badge, or Pages output against recorded artifacts | Reader-surface finding |
| MLOps reading | Compares PULSE with deployment, evaluation, monitoring, or model-operation practices | Integration or candidate-policy finding |
| Runtime-guardrail reading | Compares release-boundary control with live interaction control | Boundary-context finding |
| Supply-chain reading | Reviews provenance, artifact integrity, attestations, dependencies, and workflow hardening | Hardening or candidate-policy finding |
| Adoption reading | Assesses usability, integration effort, stakeholder uptake, and deployment fit | Adoption-context finding |
| Maturity reading | Scores completeness, roadmap progress, organizational readiness, and operational support | Hardening or roadmap finding |

## Authority-path finding

An authority-path finding identifies a break or ambiguity in the release decision
path.

Relevant segments include:

```text
evidence recording
artifact binding
status contract
declared gate policy
gate materialization
workflow-effective required gate selection
strict fail-closed CI enforcement
CI allow/block determinism
reader-surface separation
diagnostic/shadow separation
publication-surface separation
trace/audit carrier classification
external-review admission path
```

An authority-path finding should include:

```text
finding
affected authority-path segment
observed artifact or workflow evidence
expected PULSEmech behavior
actual behavior
fail-closed consequence
suggested correction
```

## Reader-surface finding

A reader-surface finding concerns a rendered, published, summarized, or displayed
surface.

Examples:

```text
Quality Ledger
Pages output
dashboard-style report
badge
Markdown summary
JSON summary
rendered HTML
publication snapshot
review packet
```

A reader-surface finding should state:

```text
source artifact
rendered or published surface
expected relation to recorded state
observed mismatch or ambiguity
reader impact
suggested correction
```

Reader-surface findings improve inspection quality and reader trust.

Release effect begins only when the underlying evidence is admitted into the
PULSEmech path and enforced as a required gate.

## Hardening finding

A hardening finding concerns the operating environment around PULSEmech.

Examples:

```text
branch protection
dependency locking
dependency single truth
clean-install validation
packaging layout
workflow hardening
workflow injection protection
path traversal protection
signing
SLSA
Sigstore
in-toto
artifact attestations
provenance attestations
public/private artifact separation
publication-surface clarity
external verifier maturity
maintainer distribution
onboarding clarity
```

A hardening finding should state:

```text
hardening area
observed condition
risk to reconstruction, enforcement, or reproducibility
relationship to the PULSEmech authority path
suggested hardening step
```

Hardening strengthens the environment around PULSEmech.

PULSEmech remains defined by the artifact-bound release-authority path.

## Candidate-policy finding

A candidate-policy finding identifies a useful future release condition.

It may originate from:

```text
external review
audit review
security review
reproducibility review
supply-chain review
reader-surface review
runtime comparison
MLOps comparison
governance-context review
```

A candidate-policy finding becomes release-relevant through this transition:

```text
candidate-policy finding
→ declared gate-policy proposal
→ accepted policy change
→ materialized required gate
→ strict fail-closed CI enforcement
```

This allows PULSE to grow without turning external opinion into release
permission.

## Reproducibility finding

A reproducibility finding concerns whether an external reviewer can reconstruct
the release-authority path from repository artifacts.

It should inspect:

```text
artifact locations
schema references
policy references
workflow references
test references
generated reports
audit bundles
publication snapshots
external verification packets
documented commands
environment assumptions
```

A reproducibility finding should state:

```text
reconstruction step
expected artifact or command
observed condition
missing or ambiguous dependency
effect on external review
suggested correction
```

## Review summary format

External reviewers should summarize findings in this shape:

```text
PULSEmech authority path reconstruction:
- release candidate:
- commit / workflow run:
- recorded release evidence:
- status.json:
- declared gate policy:
- materialized required gate set:
- strict fail-closed CI enforcement:
- CI allow/block outcome:

Authority-path findings:
- finding:
- affected authority-path segment:
- evidence:
- expected behavior:
- actual behavior:
- fail-closed consequence:
- suggested correction:

Reader-surface findings:
- finding:
- source artifact:
- reader surface:
- expected relation:
- observed relation:
- suggested correction:

Hardening findings:
- finding:
- hardening area:
- relationship to PULSEmech:
- suggested hardening:

Candidate-policy findings:
- finding:
- proposed policy route:
- required materialization:
- required CI enforcement:
```

This format separates release-authority findings from reader, hardening,
adoption, maturity, governance, runtime, supply-chain, and productization
observations.

## Completion criterion

An external review is complete for PULSEmech when it has:

```text
reconstructed the recorded evidence-to-decision path
identified the declared gate policy
identified the workflow-effective materialized required gate set
identified the strict fail-closed CI enforcement step
checked fail-closed behavior
classified reader, trace, audit, diagnostic, shadow, and publication surfaces
classified all findings by operational route
```

A strong review proves whether the PULSEmech path holds or fails closed.

## Final rule

External review observes, reconstructs, tests, classifies, and recommends.

Release authority remains artifact-bound, policy-declared, gate-materialized, and
strictly enforced by fail-closed CI:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```

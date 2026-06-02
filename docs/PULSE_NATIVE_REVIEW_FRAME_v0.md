# PULSE-Native Review Frame v0

## Purpose

PULSE-Native Review Frame v0 defines how technical reviews, external analyses, audits, critique reports, and adoption assessments should be read against the PULSE release-authority model.

The purpose is not to defend PULSE from critique.

The purpose is to keep critique in the correct mechanical frame.

A review of PULSE should not replace release-authority mechanics with classical governance, adoption, enterprise-platform, or community-popularity metrics.

Those metrics may describe external maturity.

They do not determine whether the PULSEmech authority path is mechanically correct.

## Core review boundary

PULSE should be reviewed first as:

```text
artifact-bound release authority
```

not as:

```text
generic AI governance framework
AI-eval dashboard
enterprise plug-and-play platform
community-adoption metric
MLOps product
runtime guardrail substitute
```

The PULSEmech authority carrier remains:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

A review is PULSE-native when it evaluates whether this path is correct, bounded, reproducible, and preserved.

## Review categories

PULSE reviews should separate five categories.

| Category | Review question | Mechanical status |
|---|---|---|
| Mechanical release-authority correctness | Does the recorded evidence become a declared-policy, materialized, fail-closed release decision? | Internal technical correctness |
| Carrier-boundary correctness | Are reader, trace, audit, publication, diagnostic, binding, and attestation carriers separated from authority? | Internal boundary correctness |
| External validation maturity | Has an independent reviewer reproduced or audited the artifact relationship? | External maturity |
| Adoption / ecosystem signal | Are stars, forks, issues, PRs, users, or integrations visible? | External adoption signal |
| Platform-product maturity | Is the system packaged as a plug-and-play enterprise product? | Productization / adoption layer |

Only the first two categories directly evaluate the PULSEmech mechanism.

The other categories are useful, but they are not the same kind of claim.

## Mechanical release-authority correctness

This is the primary review category.

A review should ask:

```text
Is status.json present and valid?
Is the declared gate policy present?
Is the workflow-effective required gate set materialized?
Are required gates enforced fail-closed?
Does check_gates.py treat only literal true as PASS?
Do missing required gates fail?
Does release-decision materialization preserve FAIL / STAGE-PASS / PROD-PASS boundaries?
Are prod/materialized release-grade states separated from core/demo/stubbed states?
```

Relevant surfaces:

```text
status.json
pulse_gate_policy_v0.yml
pulse_gate_registry_v0.yml
schemas/status/*
PULSE_safe_pack_v0/tools/check_gates.py
PULSE_safe_pack_v0/tools/materialize_release_decision.py
.github/workflows/pulse_ci.yml
```

This category can produce internal technical blockers.

Examples:

```text
required gate not enforced
status schema accepts invalid release state
check_gates.py allows non-literal true
release-decision labels come from the wrong source
prod release-grade state can pass with stub/scaffold markers
workflow-effective required gate set differs from enforced gate set
```

These are PULSE-native technical findings.

## Carrier-boundary correctness

This is the second primary review category.

PULSE separates carriers by role.

| Carrier | Boundary |
|---|---|
| Authority carrier | `status.json` → declared gate policy → workflow-effective materialized required gate set → strict fail-closed CI enforcement |
| Reader carrier | Presents recorded state; non-authorizing carrier |
| Trace carrier | Preserves reconstruction trace; no independent decision function |
| Audit / preservation carrier | Preserves reconstructable evidence; non-authorizing carrier |
| Publication carrier | Derived carrier only |
| Diagnostic / shadow carrier | Authority participation requires recorded evidence inclusion and required-gate enforcement under declared policy |
| Binding carrier | Carries digest-backed artifact relation |
| Attestation carrier | Attests the binding carrier |
| External verification carrier | Reviews the recorded artifact relationship |

A review should ask:

```text
Is any reader surface being treated as authority?
Is any trace artifact being treated as a decision engine?
Is any publication surface being treated as recorded authority?
Is any shadow/diagnostic output implicitly becoming a required gate?
Is the binding carrier replacing, rather than binding, the authority path?
Is attestation over the binding carrier, not over a scattered informal claim?
```

Carrier-boundary findings can be internal technical blockers when they allow authority drift.

Examples:

```text
Quality Ledger wording implies independent release authority
publication surface displays core/stubbed state as release-grade evidence
shadow output is used as release authority without declared policy
attestation subject is not the binding carrier
binding hash omits decision-bearing artifacts
```

These are PULSE-native boundary findings.

## Public reader surface review

Public surfaces require special care because they are reader-facing.

A public surface may be mechanically non-authorizing and still be misleading to a human reader.

A review should distinguish:

```text
mechanical authority
reader presentation
publication interpretation
```

The correct boundary is:

```text
public reader surface
= recorded-state presentation

release authority
= PULSEmech path
```

A public-surface finding should specify whether it is:

```text
renderer correctness issue
wording / visual separation issue
artifact parity issue
authority-boundary issue
release-mechanism issue
```

Only the last category is a direct release-authority blocker.

The others may still be important, but they are reader / audit / presentation issues.

## Cryptographic provenance and attestation review

PULSE-native review should distinguish these layers:

```text
authority carrier
binding carrier
attestation subject
attestation carrier
external verifier
```

The authority carrier remains:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

The binding carrier is:

```text
artifact_provenance_binding_v0.json
```

The attestation subject is:

```text
artifact_provenance_binding_v0.json
```

The attestation carrier is:

```text
cryptographic attestation over the binding carrier
```

A review should ask:

```text
Does the binding carrier record the relevant artifact relationship?
Does the verifier recompute the relation?
Is the attestation over the binding carrier?
Are attestation credentials isolated from the main CI job?
Is the attestation action pinned?
Is the artifact download repository-explicit?
```

A review should not treat attestation as a replacement for PULSEmech.

Attestation strengthens provenance.

It does not redefine release authority.

## External validation maturity

External validation is important.

It is not the same as internal mechanical correctness.

External validation includes:

```text
third-party reproduction
independent audit
reference integration
external reviewer report
case study
external consumer verification
```

A lack of external validation should be recorded as:

```text
external maturity gap
```

not automatically as:

```text
mechanical release-authority failure
```

A review may say:

```text
PULSE has a mechanically defined authority path, but it still needs third-party reproduction.
```

A review should not collapse this into:

```text
PULSE is mechanically weak because it has low adoption.
```

Those are different claims.

## Adoption and community metrics

Adoption signals may include:

```text
stars
forks
open issues
open PRs
contributors
external users
integrations
mentions
downloads
```

These signals describe external visibility and community uptake.

They do not determine whether the PULSEmech authority path is mechanically correct.

Correct framing:

```text
0 stars / 0 forks
= low visible GitHub adoption
```

Incorrect framing:

```text
0 stars / 0 forks
= weak release-authority mechanism
```

The stronger review form is:

```text
PULSE may be mechanically disciplined while still being externally under-validated.
```

Both can be true.

## Enterprise / plug-and-play platform framing

PULSE should not be reviewed as if it claimed to be a finished enterprise plug-and-play platform unless the reviewed artifact explicitly makes that claim.

Current PULSE review frame:

```text
artifact-bound release-authority reference mechanism
```

Not automatically:

```text
managed SaaS
multi-tenant enterprise product
turnkey MLOps platform
organizational governance suite
industry standard
```

A review may say:

```text
PULSE is not yet productized for broad enterprise adoption.
```

That is an adoption / packaging / operational maturity statement.

It is not the same as:

```text
PULSE release authority is mechanically incorrect.
```

## Governance framing boundary

PULSE may have governance implications.

But PULSE is not primarily classical governance.

PULSE-native wording:

```text
release-authority mechanics
artifact-bound decision path
declared policy
materialized gate set
fail-closed CI enforcement
carrier boundary
```

Classical governance wording can be useful when discussing:

```text
maintainer model
external review
adoption
quorum
approval process
institutional maturity
```

But it should not replace the mechanical review.

Correct split:

```text
mechanical release-authority correctness
= internal PULSEmech question

maintainer / community / adoption maturity
= external governance and sustainability question
```

## Single-maintainer review boundary

A single-maintainer model is a real external trust and sustainability risk.

It is not automatically a failure of the release-authority mechanism.

Correct framing:

```text
single maintainer
= bus factor / external trust / governance maturity risk
```

Incorrect framing:

```text
single maintainer
= check_gates.py or policy materialization is mechanically invalid
```

A review should identify which boundary is affected:

```text
repository change control
release / DOI / Zenodo custody
external trust
review diversity
authority-impact PR handling
```

The maintainer boundary does not redefine the PULSEmech authority path.

## Review finding taxonomy

A PULSE review finding should be classified as one of:

```text
mechanical blocker
authority-boundary blocker
reader-surface risk
provenance / attestation gap
external validation gap
adoption / ecosystem gap
maintainer / governance maturity gap
productization gap
optional polish
out-of-scope expectation
```

## Mechanical blocker

A finding is a mechanical blocker when it can alter or break:

```text
status.json validity
declared policy
workflow-effective required gate materialization
strict fail-closed enforcement
release decision materialization
artifact provenance binding
attestation subject / carrier
```

## Authority-boundary blocker

A finding is an authority-boundary blocker when it causes:

```text
reader carrier to act as authority
publication carrier to act as recorded artifact
trace carrier to act as decision engine
shadow carrier to become implicit required evidence
binding carrier to replace the PULSEmech path
attestation carrier to attest the wrong subject
```

## Reader-surface risk

A finding is a reader-surface risk when:

```text
the machine path remains correct
but a public or human-facing display may be misunderstood
```

Reader-surface risks are important.

They should not be mislabeled as authority failures unless they change the authority path.

## External validation gap

A finding is an external validation gap when:

```text
the mechanism exists
but has not been reproduced or audited by an independent party
```

This is a maturity issue.

It is not automatically an internal technical defect.

## Adoption / ecosystem gap

A finding is an adoption gap when:

```text
visible stars / forks / issues / PRs / integrations / users are low
```

This measures external uptake.

It does not directly measure PULSEmech correctness.

## Productization gap

A finding is a productization gap when:

```text
installation is not plug-and-play
enterprise packaging is missing
maintainer operations are not multi-party
documentation is too dense for quick onboarding
```

This may matter for adoption.

It does not automatically invalidate the mechanism.

## PULSE-native response format

A review response should use this structure:

```text
Finding:
Category:
Affected carrier:
Authority impact:
Evidence:
Current mitigation:
Remaining work:
Status:
```

Example:

```text
Finding:
Public ledger can be misread as release-grade.

Category:
Reader-surface risk.

Affected carrier:
Quality Ledger reader carrier.

Authority impact:
No direct authority-path change unless the renderer contradicts recorded state or implies independent authority.

Evidence:
Core/stubbed public surface may appear near STAGE-PASS display.

Current mitigation:
Public surface state wording, reader carrier boundary, materialized release-grade evidence state wording.

Remaining work:
Optional visual polish.

Status:
Mostly closed internally.
```

## Non-native review patterns

The following review patterns should be treated carefully:

```text
PULSE has low stars, therefore the mechanism is weak.
PULSE is not a plug-and-play enterprise platform, therefore release authority is incomplete.
PULSE is single-maintainer, therefore the CI allow/block path is invalid.
PULSE has shadow workflows, therefore shadow layers are normative.
PULSE uses GitHub Actions, therefore all provenance is meaningless.
PULSE is governance, therefore it should be judged only by governance maturity.
```

These statements may contain useful concerns, but they are not PULSE-native unless they identify the affected carrier and authority impact.

## Corrected review readings

| Non-native reading | PULSE-native reading |
|---|---|
| Low GitHub adoption means PULSE is weak | Low adoption is an external validation gap; mechanical correctness must be reviewed separately |
| Not enterprise plug-and-play means not mature | Productization maturity is separate from release-authority mechanics |
| Single maintainer invalidates authority | Single maintainer is a governance / bus-factor risk, not a direct gate-enforcement defect |
| Public core/STAGE-PASS display disproves PULSE | Public reader surface needs clear boundary; authority path must be checked separately |
| Shadow workflows imply hidden authority | Shadow outputs remain non-authorizing unless promoted through declared policy and required-gate enforcement |
| Attestation is missing, therefore authority path is invalid | Attestation strengthens provenance; PULSEmech authority path remains a separate mechanical carrier |

## Review status language

Use precise status labels:

```text
closed internally
partially closed
external maturity gap
optional polish
out of scope for current mechanism
future productization layer
```

Avoid vague labels:

```text
not mature
not production-ready
not standard
not adopted
governance issue
```

unless they are tied to a specific category and carrier.

## Boundary held by this document

This document defines the PULSE-native review frame.

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

## Core statement

PULSEmech authority maturity is not measured by how many people have forked the repository.

PULSEmech authority maturity is measured by whether the release decision is:

```text
evidence-bound
policy-declared
materialized as a required gate set
strictly fail-closed
artifact-bound
carrier-bounded
verifiable through recorded artifacts
```

Adoption can validate, stress-test, and extend PULSE.

Adoption does not define the release-authority mechanism.

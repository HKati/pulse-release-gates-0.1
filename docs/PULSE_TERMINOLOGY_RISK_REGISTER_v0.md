# PULSE Terminology Risk Register v0

## Purpose

This document records terminology that can cause PULSE to be misread outside the PULSEmech category boundary.

It is a terminology boundary-control document.

It protects PULSE from being reframed as governance, compliance, dashboard, MLOps, adoption, maturity, or supply-chain tooling.

It does not change release authority.

This document does not prohibit controlled use of these terms.

It defines where these terms are allowed, and where they must not be used as PULSE identity descriptors.

## Canonical identity

PULSEmech is an artifact-bound release-authority mechanism for AI release decisions.

The authority path is:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```

## Terms that require boundary control

The following terms may appear only when their scope is explicit and they are not used as PULSE identity descriptors.

| Term | Risk | Allowed use |
|---|---|---|
| governance | Can make PULSE appear to be an institutional control model | External AI-governance literature, repository stewardship, or legacy alias only |
| release governance | Can replace release authority with process language | Avoid in PULSE-facing identity text |
| governance framework | Can make PULSE appear to be a compliance framework | Avoid for PULSE identity |
| control plane | Can make PULSE appear to be an enterprise platform | Use only with explicit release-authority boundary |
| maturity | Can make repository hardening appear to define PULSE | Use only for external maturity or repository hardening |
| supply-chain framework | Can make PULSE appear to be SLSA / in-toto / Sigstore equivalent | Use only as external hardening context |
| dashboard | Can make reader surfaces appear authoritative | Use only for reader / publication surfaces |
| runtime guardrail | Can move PULSE away from pre-deployment release authority | Use only as contrast or external category |
| compliance | Can make PULSE appear to be a legal compliance system | Use only as external adoption context |
| adoption metrics | Can be misread as mechanical validity metrics | Use only as ecosystem visibility / uptake signals |

## Preferred PULSE-facing descriptors

Use:

```text
artifact-bound release authority
release-authority mechanism
PULSEmech authority path
recorded release evidence
status.json
declared gate policy
workflow-effective materialized required gate set
strict fail-closed CI enforcement
carrier boundary
reader carrier
trace carrier
binding carrier
external verification carrier
```

Avoid using these as identity descriptors:

```text
AI governance framework
release governance system
governance-control-plane
compliance framework
MLOps platform
dashboard
runtime guardrail
supply-chain framework
institutional governance model
```

## Governance term boundary

The term `governance` is not banned.

It may be used when it clearly refers to:

```text
external AI-governance literature
repository stewardship
maintainer process
organizational adoption
legacy filename or legacy workshop alias
```

It must not be used as the primary descriptor for PULSE identity.

Correct use:

```text
External AI-governance literature may discuss adjacent concerns.
```

Incorrect use:

```text
PULSE is an AI governance framework.
```

Preferred PULSE-facing identity:

```text
PULSEmech is an artifact-bound release-authority mechanism.
```

## Adoption boundary

Adoption metrics are not mechanical validity metrics.

Stars, forks, downloads, community uptake, and external usage may describe ecosystem visibility.

They do not determine whether the PULSEmech release-authority path is mechanically valid.

Correct classification:

```text
low adoption
= adoption / ecosystem signal
```

Incorrect classification:

```text
low adoption
= weak release-authority mechanism
```

## Hardening boundary

Repository hardening, branch protection, dependency locking, signing, SLSA, Sigstore, in-toto, and attestation may strengthen the operating environment around PULSEmech.

They do not define PULSE.

Hardening documents must keep this distinction explicit:

```text
hardening layer
≠ PULSE identity
```

The PULSEmech identity remains:

```text
artifact-bound release-authority mechanism
```

## Public surface boundary

Public Pages, Quality Ledger, summaries, dashboards, and rendered reports are reader or publication surfaces unless explicitly bound to recorded release-decision artifacts.

They are not the PULSEmech authority path.

The PULSEmech authority path remains:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

## Supply-chain hardening boundary

SLSA, Sigstore, in-toto, artifact attestations, signing, and provenance frameworks may strengthen external trust, reproducibility, and artifact verification around a release-grade path.

They do not define PULSE.

PULSEmech is not a supply-chain framework.

PULSEmech is a release-authority mechanism for AI release decisions.

## Reader carrier boundary

Reader carriers may display, summarize, or explain recorded state.

They do not create release authority.

Examples of reader carriers:

```text
Quality Ledger
summary Markdown
summary JSON
public Pages surface
dashboard-style view
rendered report
```

Reader carriers must not be described as the source of release authority.

## Trace and audit carrier boundary

Trace and audit carriers may preserve reconstruction evidence.

They do not create a second release-decision engine.

Examples:

```text
release_authority_v0.json
audit bundle
external verification packet
normative/shadow inventory report
artifact provenance binding review output
```

These carriers support review.

They do not replace the PULSEmech authority path.

## Identity descriptor rule

A term is unsafe as a PULSE identity descriptor when it causes the reader to classify PULSE primarily as:

```text
institutional governance
compliance
dashboard
MLOps
runtime guardrail
supply-chain framework
enterprise control plane
adoption maturity project
```

A term is acceptable when it is scoped as:

```text
external context
supporting hardening layer
reader surface
review carrier
legacy alias
repository stewardship
```

The distinction must be explicit.

## Boundary held by this document

This document does not change:

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

## Final rule

PULSE-facing identity text should resolve to:

```text
PULSEmech = artifact-bound release-authority mechanism for AI release decisions
```

not to:

```text
governance framework
compliance framework
dashboard
MLOps platform
runtime guardrail
supply-chain framework
adoption maturity project
```

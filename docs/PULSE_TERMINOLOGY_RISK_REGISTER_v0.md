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
| Quality Ledger | Can make PULSE appear to be a quality-assurance dashboard or evaluation report | Use only as a reader carrier over recorded `status.json`; never as release authority |
| Safe & Useful AI | Can make PULSE appear to define safety or usefulness as a broad governance framework | Use only as release-domain wording; PULSE checks recorded release evidence, not general safety meaning |
| policy | Can be misread as organizational or management policy | In PULSE-facing text, use only as declared gate policy tied to materialized required gates |
| evaluation / eval | Can make evidence producers appear to be the PULSE mechanism itself | Use only as evidence-producing or diagnostic context unless recorded, declared, materialized, and enforced |
| ecosystem around PULSE | Can make surrounding dashboards, reports, evals, docs, or workflows appear to be PULSE identity | Use only as supporting context around the PULSEmech authority path |
| industrial maturity | Can make PULSEmech appear to be defined by enterprise / production adoption status | Use only as an external deployment or adoption dimension; not as PULSEmech identity |
| productization maturity | Can make PULSEmech appear to be measured as a plug-and-play product category | Use only for packaging, operational support, or deployment readiness around PULSEmech |
| enterprise platform | Can make PULSEmech appear to be an enterprise software product category | Use only when discussing deployment packaging or integration environment, not the release-authority mechanism |
| industrial standard | Can make PULSEmech appear to require broad market adoption before its mechanism can be evaluated | Use only for ecosystem/adoption status; not for mechanical validity |
| release-grade lane eligibility | Can be misread as release permission or final release authorization | Use only as eligibility for stricter release-grade checks; actual release permission still requires the enforced PULSEmech authority path |
| external evidence presence | Can be misread as proof that evidence has materialized into a required gate | Use only as available candidate evidence until recorded, declared, materialized, and enforced |
| publication exposure | Can make public visibility appear to grant release authority | Use only as a reader/publication surface; exposure does not authorize release |
| third-party integration / adoption | Can make ecosystem uptake appear to define PULSEmech identity | Use only as external integration or adoption context; not as PULSEmech identity |
| hardening layer | Can make repository or supply-chain hardening appear to define PULSEmech | Use only as an operating-environment strengthening layer around PULSEmech |

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

They also do not define PULSEmech identity.

Boundary lock:

```text
third-party integration / adoption
≠ PULSEmech identity
```

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
## Industrial / productization maturity boundary

Industrial maturity, productization maturity, enterprise platform status, and industrial standard status are external adoption or deployment dimensions.

They do not define PULSEmech.

PULSEmech remains an artifact-bound release-authority mechanism for AI release decisions.

The PULSEmech authority path remains:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```

Industrialization may add operational requirements around PULSEmech.

It does not define the mechanism.


## Release-grade lane eligibility boundary

Release-grade lane eligibility means that an artifact, workflow, or repository path is eligible to be evaluated under release-grade gates.

It does not by itself grant release permission.

Boundary lock:

```text
release-grade lane eligibility
≠ release permission
```

Release permission exists only when the enforced PULSEmech authority path reaches a pre-deployment allow decision.

## External evidence materialization boundary

External evidence may exist before it is release-relevant.

Presence alone does not mean the evidence has materialized into a required gate.

Boundary lock:

```text
external evidence presence
≠ materialization
```

External evidence becomes release-relevant only when it is:

```text
recorded as release evidence
referenced by declared gate policy
materialized as a required gate
enforced through strict fail-closed CI
```


## Hardening boundary

Repository hardening, branch protection, dependency locking, signing, SLSA, Sigstore, in-toto, and attestation may strengthen the operating environment around PULSEmech.

They do not define PULSE.

Hardening documents must keep this distinction explicit:

```text
hardening layer
≠ PULSE identity
hardening layer
≠ PULSEmech definition
```

The PULSEmech identity remains:

```text
artifact-bound release-authority mechanism
```

## Public surface boundary

Public Pages, Quality Ledger, summaries, dashboards, and rendered reports are reader or publication surfaces unless explicitly bound to recorded release-decision artifacts.

They are not the PULSEmech authority path.

Public visibility, publication, or exposure does not create release authority.

Boundary lock:

```text
publication exposure
≠ release authority
```


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

## Quality Ledger boundary

The Quality Ledger is a reader carrier.

It displays or summarizes recorded release-state artifacts.

It does not create release authority.

It does not replace:

```text
status.json
declared gate policy
workflow-effective materialized required gate set
strict fail-closed CI enforcement
```

Correct use:

```text
Quality Ledger reader surface over recorded status.json
```

Incorrect use:

```text
Quality Ledger as the release authority
Quality Ledger as the source of release permission
Quality Ledger as a quality-assurance dashboard that decides release
```

## Safe & Useful AI boundary

The phrase `Safe & Useful AI` names the release domain in which PULSE is applied.

It does not mean that PULSE defines safety, usefulness, or general AI-governance policy.

PULSE checks whether recorded release evidence satisfies declared gates.

Correct use:

```text
PULSE applies artifact-bound release authority to Safe & Useful AI release decisions.
```

Incorrect use:

```text
PULSE is a general Safe & Useful AI governance framework.
```

The PULSEmech authority path remains:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```

## Declared gate policy boundary

In PULSE-facing text, `policy` means declared gate policy.

It does not mean organizational policy, management policy, compliance policy, or institutional governance.

A declared gate policy is release-relevant only when it is used to materialize the required gate set enforced by strict fail-closed CI.

Correct use:

```text
declared gate policy
→ workflow-effective materialized required gate set
```

Incorrect use:

```text
policy as broad organizational governance
policy as a management framework
policy as human approval preference
```

## Ecosystem boundary

Dashboards, reports, evals, external detectors, reader surfaces, docs, and review artifacts may exist around PULSE.

They are not PULSE identity.

They become release-relevant only through the PULSEmech authority path:

```text
recorded as release evidence
referenced by declared gate policy
materialized as a required gate
enforced through strict fail-closed CI
```

Existence around PULSE is not authority.

Repository presence is not release authority.

Reader visibility is not release authority.

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

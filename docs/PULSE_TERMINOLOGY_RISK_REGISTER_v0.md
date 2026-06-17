# PULSE Terminology Risk Register v0

## Purpose

This document records terminology that can cause PULSE to be misread outside the
PULSEmech category boundary.

It is a docs-only, terminology-only boundary-control document.

It protects PULSE from being reframed as:

```text
governance
compliance
dashboard
MLOps
runtime guardrail
adoption project
maturity project
enterprise platform
supply-chain framework
```

This document does not ban controlled use of these terms.

It defines where these terms are allowed, and where they must not be used as
PULSE identity descriptors.

This document does not change release authority.

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
publication paths
```

## Canonical identity

PULSEmech is an artifact-bound release-authority mechanism for AI release
decisions.

The PULSEmech authority path is:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```

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
enterprise maturity project
```

## Identity descriptor rule

A term is unsafe as a PULSE identity descriptor when it causes the reader to
classify PULSE primarily as:

```text
institutional governance
legal compliance
quality dashboard
MLOps platform
runtime guardrail
supply-chain framework
enterprise control plane
adoption project
maturity project
```

A term is acceptable when it is explicitly scoped as:

```text
external context
supporting hardening layer
reader surface
review carrier
trace carrier
audit carrier
legacy alias
repository stewardship
deployment context
```

The distinction must be explicit.

## Terms that require boundary control

| Term | Risk | Allowed use |
|---|---|---|
| governance | Can make PULSE appear to be an institutional control model | External AI-governance literature, repository stewardship, maintainer process, organizational adoption, or legacy alias only |
| release governance | Can replace release authority with process language | Avoid in PULSE-facing identity text |
| governance framework | Can make PULSE appear to be a compliance framework | Avoid for PULSE identity |
| compliance | Can make PULSE appear to be a legal or regulatory compliance system | Use only as external adoption context |
| control plane | Can make PULSE appear to be an enterprise platform | Use only with explicit release-authority boundary |
| enterprise platform | Can make PULSEmech appear to be an enterprise software product category | Use only when discussing deployment packaging or integration environment |
| MLOps platform | Can make PULSE appear to be lifecycle orchestration tooling | Use only as external comparison or integration context |
| dashboard | Can make reader surfaces appear authoritative | Use only for reader, publication, or diagnostic surfaces |
| Quality Ledger | Can make PULSE appear to be a quality-assurance dashboard | Use only as a reader carrier over recorded `status.json`; never as release authority |
| runtime guardrail | Can move PULSE away from pre-deployment release authority | Use only as contrast or external category |
| supply-chain framework | Can make PULSE appear to be SLSA / Sigstore / in-toto equivalent | Use only as external hardening context |
| hardening layer | Can be misread as PULSEmech definition | Use only as surrounding repository, security, artifact, verifier, or operational hardening |
| maturity | Can make repository hardening appear to define PULSE | Use only for external maturity, repository hardening, or deployment readiness |
| industrial maturity | Can make PULSEmech appear to be defined by enterprise adoption status | Use only as an external deployment or adoption dimension |
| productization maturity | Can make PULSEmech appear to be measured as a plug-and-play product category | Use only for packaging, operational support, or deployment readiness around PULSEmech |
| industrial standard | Can make PULSEmech appear to require broad market adoption before its mechanism can be evaluated | Use only for ecosystem/adoption status, not for mechanical validity |
| adoption metrics | Can be misread as mechanical validity metrics | Use only as ecosystem visibility or uptake signal |
| third-party integration / adoption | Can be misread as PULSEmech identity or mechanical maturity | Use only as deployment/adoption context around PULSEmech |
| policy | Can be misread as organizational or management policy | In PULSE-facing text, use only as declared gate policy tied to materialized required gates |
| evaluation / eval | Can make evidence producers appear to be the PULSE mechanism itself | Use only as evidence-producing or diagnostic context unless recorded, declared, materialized, and enforced |
| external evidence presence | Can be misread as materialized release evidence | Use only as artifact/file presence unless mapped into the declared PULSEmech path |
| release-grade lane eligibility | Can be misread as release permission or CI allow outcome | Use only as lane/materialization review status; never as release permission |
| publication exposure | Can be misread as release authority | Use only as public/private artifact classification; publication does not authorize release |
| ecosystem around PULSE | Can make surrounding dashboards, reports, evals, docs, or workflows appear to be PULSE identity | Use only as supporting context around the PULSEmech authority path |
| Safe & Useful AI | Can make PULSE appear to define safety or usefulness as a broad governance framework | Use only as release-domain wording; PULSE checks recorded release evidence, not general safety meaning |
| trace carrier | Can be misread as a second release-decision engine | Use only for reconstruction, audit, and review support |
| audit carrier | Can be misread as a second release-decision engine | Use only for preservation and inspection support |

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
audit carrier
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
enterprise maturity platform
adoption maturity project
```

## Governance and compliance boundary

The term `governance` is not banned.

It may be used when it clearly refers to:

```text
external AI-governance literature
repository stewardship
maintainer process
organizational adoption
legacy filename
legacy workshop alias
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

The term `compliance` is also not banned, but it must not define PULSE identity.

Correct use:

```text
Compliance teams may inspect PULSE artifacts as external review material.
```

Incorrect use:

```text
PULSE is a compliance framework.
```

## Reader surface and Quality Ledger boundary

Reader carriers may display, summarize, or explain recorded state.

They do not create release authority.

Examples of reader carriers:

```text
Quality Ledger
Markdown summary
JSON summary
public Pages surface
dashboard-style view
rendered report
badge
```

The Quality Ledger is a reader carrier.

It displays or summarizes recorded release-state artifacts.

It does not replace:

```text
status.json
declared gate policy
workflow-effective materialized required gate set
strict fail-closed CI enforcement
```

Boundary lock:

```text
reader surface ≠ release authority
Quality Ledger ≠ release authority
dashboard ≠ release authority
publication exposure ≠ release authority
```

Correct use:

```text
Quality Ledger reader surface over recorded status.json.
```

Incorrect use:

```text
Quality Ledger as the release authority.
Quality Ledger as the source of release permission.
Dashboard as the CI allow/block decision.
Public Pages output as release authority.
```

## Publication exposure boundary

Publication exposure is not release authority.

A public artifact, public status surface, Pages output, report, badge, dashboard,
or reader surface does not authorize release by being public.

A public artifact may support review only when it is bound into the recorded
release-state relation and its mechanical effect is defined through declared
policy, materialized gates, and strict CI enforcement.

Boundary lock:

```text
publication exposure ≠ release authority
public visibility ≠ release authority
public status visibility ≠ CI allow outcome
```

Correct use:

```text
public artifact as reader surface, recorded artifact, or review carrier
```

Incorrect use:

```text
public artifact as release permission
public Pages output as release authority
public status visibility as CI allow outcome
```

## External evidence materialization boundary

External evidence presence is not materialization.

A detector output, external summary, metric key, report, external packet, or
third-party review artifact may exist without becoming materialized release
evidence.

External evidence becomes release-relevant only when it is:

```text
recorded as release evidence
parseable
source-identified
subject-bound
freshness-bound when required
mapped by declared rules
folded into status or gate state deterministically
enforced by strict CI when release-required
```

Presence alone does not satisfy release-required evidence.

Boundary lock:

```text
external evidence presence ≠ materialization
summary file presence ≠ release evidence
aggregate pass ≠ release permission
```

Correct use:

```text
external evidence materialized through declared mapping, status/gate fold-in,
and strict CI enforcement when release-required
```

Incorrect use:

```text
external evidence presence as materialization
summary file presence as external_all_pass
generic metric key as release evidence
unknown summary file as release-grade evidence
absence of known failures as release permission
```

## Declared gate policy boundary

In PULSE-facing text, `policy` means declared gate policy.

It does not mean:

```text
organizational policy
management policy
compliance policy
institutional governance
human approval preference
```

A declared gate policy is release-relevant only when it is used to materialize the
required gate set enforced by strict fail-closed CI.

Correct use:

```text
declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

Incorrect use:

```text
policy as broad organizational governance
policy as a management framework
policy as human approval preference
```

## Release-grade lane eligibility boundary

Release-grade lane eligibility is not release permission.

A release-grade materialized lane may define whether a recorded run, artifact,
workflow, or repository path is structurally eligible for release-grade review.

It does not authorize release.

Release permission exists only when the enforced PULSEmech authority path reaches
a pre-deployment allow decision.

Boundary lock:

```text
release-grade lane eligibility ≠ release permission
release-grade lane eligibility ≠ CI allow outcome
release-grade lane eligibility ≠ second release-decision engine
```

Correct use:

```text
release-grade lane eligibility as materialization review status
```

Incorrect use:

```text
release-grade lane eligibility as release permission
release-grade lane eligibility as CI allow outcome
release-grade lane eligibility as a second release-decision engine
```

## Runtime guardrail boundary

PULSE acts at the release boundary before deployment.

Runtime guardrails act during live interaction or runtime execution.

Boundary lock:

```text
PULSEmech release boundary ≠ runtime interaction boundary
```

Correct use:

```text
runtime guardrail as an external contrast category
```

Incorrect use:

```text
PULSE as a runtime guardrail
PULSEmech as prompt-level refusal routing
PULSEmech as live interaction moderation
```

## Adoption and maturity boundary

Adoption metrics are not mechanical validity metrics.

Stars, forks, downloads, community uptake, third-party integration, and external
usage may describe ecosystem visibility.

They do not determine whether the PULSEmech release-authority path is
mechanically valid.

Industrial maturity, productization maturity, enterprise platform status, and
industrial standard status are external adoption or deployment dimensions.

They do not define PULSEmech.

Boundary lock:

```text
third-party integration / adoption ≠ PULSEmech identity
low adoption ≠ weak release-authority mechanism
industrial maturity ≠ PULSEmech definition
productization maturity ≠ PULSEmech definition
enterprise platform status ≠ PULSEmech identity
```

Correct classification:

```text
low adoption = adoption / ecosystem signal
```

Incorrect classification:

```text
low adoption = weak release-authority mechanism
enterprise integration as proof of mechanical validity
onboarding maturity as release-authority definition
```

## Hardening and supply-chain boundary

Repository hardening may strengthen the operating environment around PULSEmech.

Examples:

```text
branch protection
dependency locking
dependency single truth
packaging layout
clean-install validation
workflow hardening
signing
SLSA
Sigstore
in-toto
artifact attestations
provenance attestations
public/private artifact classification
verifier hardening
publication-surface clarity
```

These layers are supporting layers.

They do not define PULSEmech.

PULSEmech is not a supply-chain framework.

PULSEmech is a release-authority mechanism for AI release decisions.

Boundary lock:

```text
hardening layer ≠ PULSE identity
hardening layer ≠ PULSEmech definition
supply-chain hardening ≠ PULSEmech definition
SLSA / Sigstore / in-toto ≠ PULSE identity
```

Correct use:

```text
hardening layer as surrounding boundary, security, artifact, verifier, or
operational strengthening
```

Incorrect use:

```text
hardening layer as PULSEmech identity
maturity layer as PULSEmech definition
deployment hardening as release-authority mechanism
supply-chain framework as PULSE identity
```

## Third-party integration boundary

External verifier tooling, onboarding, deployment packaging, example repositories,
enterprise integration, third-party adoption, and productization support may
exist around PULSEmech.

They do not define PULSEmech.

Boundary lock:

```text
third-party integration / adoption ≠ PULSEmech identity
```

Correct use:

```text
third-party integration as deployment/adoption layer around PULSEmech
```

Incorrect use:

```text
third-party adoption as PULSEmech identity
enterprise integration as proof of mechanical validity
onboarding maturity as release-authority definition
```

## Ecosystem boundary

Dashboards, reports, evals, external detectors, reader surfaces, docs, and
review artifacts may exist around PULSE.

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
artifact provenance binding
review output
publication snapshot
```

These carriers support review.

They do not replace the PULSEmech authority path.

Boundary lock:

```text
trace carrier ≠ release authority
audit carrier ≠ release authority
external review ≠ release authority
publication snapshot ≠ release authority
```

## Safe & Useful AI boundary

The phrase `Safe & Useful AI` names the release domain in which PULSE is applied.

It does not mean that PULSE defines safety, usefulness, or general AI-governance
policy.

PULSE checks whether recorded release evidence satisfies declared gates.

Correct use:

```text
PULSE applies artifact-bound release authority to Safe & Useful AI release
decisions.
```

Incorrect use:

```text
PULSE is a general Safe & Useful AI governance framework.
```

## Boundary held by this document

This document holds a terminology boundary only.

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
publication paths
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
enterprise maturity project
```

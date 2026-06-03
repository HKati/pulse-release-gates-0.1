# PULSE-Native Review Frame v0

## Purpose

PULSE-Native Review Frame v0 defines a category system for reviewing PULSE.

The document keeps review findings attached to:

```text
affected carrier
authority impact
evidence source
remaining work
```

The document is a review-boundary carrier.

It does not redefine PULSEmech.

It does not convert adoption, governance, productization, or community visibility signals into release-authority findings.

A PULSE review is mechanically useful when it identifies:

```text
what changed
which carrier is affected
whether the PULSEmech authority path is affected
what evidence supports the finding
what remains to be done
```

## Core review boundary

Primary review object:

```text
artifact-bound release-authority mechanism
```

Primary authority carrier:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

A review is PULSE-native when it evaluates whether this path is:

```text
present
declared
materialized
fail-closed
carrier-bounded
reproducible from recorded artifacts
```

Other review dimensions may be relevant, but they must be classified separately:

```text
external validation
adoption / ecosystem signal
productization maturity
maintainer / governance maturity
reader-surface risk
optional polish
```

## Review categories

| Category | Review object | Authority relation |
|---|---|---|
| Mechanical release-authority correctness | `status.json`, declared policy, materialized required gates, fail-closed CI | Direct PULSEmech correctness |
| Carrier-boundary correctness | reader, trace, audit, publication, diagnostic, binding, attestation carriers | Direct boundary correctness |
| External validation maturity | independent reproduction, external audit, third-party reference integration | External maturity |
| Adoption / ecosystem signal | stars, forks, issues, PRs, users, integrations, mentions | Visibility / uptake signal |
| Productization maturity | packaging, onboarding, enterprise deployment, plug-and-play integration | Product / operations maturity |
| Maintainer / governance maturity | maintainer model, review distribution, bus factor, release custody | Repository governance maturity |

Only the first two categories directly evaluate PULSEmech authority mechanics.

The other categories may identify real gaps, but they do not by themselves determine whether the release-authority path is mechanically correct.

## Mechanical release-authority correctness

Mechanical release-authority correctness is the primary PULSE review category.

A review should evaluate:

```text
status.json presence and validity
declared gate policy presence
workflow-effective required gate-set materialization
fail-closed required-gate enforcement
literal true-only PASS semantics
release-decision materialization
release-grade admissibility
artifact provenance binding
attestation subject / carrier
```

Relevant surfaces:

```text
status.json
pulse_gate_policy_v0.yml
pulse_gate_registry_v0.yml
schemas/status/*
PULSE_safe_pack_v0/tools/check_gates.py
PULSE_safe_pack_v0/tools/materialize_release_decision.py
PULSE_safe_pack_v0/tools/build_artifact_provenance_binding_v0.py
PULSE_safe_pack_v0/tools/verify_artifact_provenance_binding_v0.py
.github/workflows/pulse_ci.yml
```

This category can produce internal technical blockers.

Examples:

```text
required gate is not enforced
missing required gate can pass
non-literal true is accepted as PASS
release label is sourced from the wrong artifact
stubbed or scaffolded state can enter release-grade path
workflow-effective required gate set differs from enforced gate set
binding hash omits decision-bearing artifacts
attestation subject is not the binding carrier
```

## Mechanical blocker

A finding is a mechanical blocker when it can change, bypass, or invalidate one of these:

```text
status.json validity
declared gate policy
workflow-effective required gate materialization
strict fail-closed enforcement
release-decision materialization
artifact provenance binding
attestation subject / carrier
```

Examples:

```text
required gate is not enforced
missing required gate can pass
non-literal true is accepted as PASS
release label is sourced from the wrong artifact
stubbed or scaffolded state can enter release-grade path
binding hash omits decision-bearing artifacts
attestation subject is not the binding carrier
```

Mechanical blockers affect PULSEmech correctness directly.

## Carrier-boundary correctness

Carrier-boundary correctness is the second primary PULSE review category.

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

A carrier-boundary review evaluates:

```text
whether each carrier keeps its declared role
whether non-authorizing carriers remain non-authorizing
whether authority participation is explicit and policy-declared
whether reader or publication surfaces preserve recorded-state parity
whether binding and attestation strengthen provenance without replacing PULSEmech
```

## Authority-boundary blocker

A finding is an authority-boundary blocker when a non-authorizing carrier is allowed to function as authority.

Boundary failures include:

```text
reader carrier treated as release authority
publication carrier treated as recorded authority artifact
trace carrier treated as decision engine
shadow carrier treated as implicit required evidence
binding carrier treated as replacement for PULSEmech
attestation carrier attached to the wrong subject
```

A boundary finding should identify:

```text
affected carrier
incorrect authority role
expected role
mechanical consequence
```

Authority-boundary blockers affect the integrity of the PULSE carrier model.

## Public reader surface review

Public reader surfaces require special review because they are human-facing.

A public surface may be mechanically non-authorizing and still create reader confusion.

A public-surface review separates:

```text
mechanical authority
reader presentation
publication interpretation
```

Correct boundary:

```text
public reader surface
= recorded-state presentation

release authority
= PULSEmech path
```

A public-surface finding should be classified as one of:

```text
renderer correctness issue
wording / visual separation issue
artifact parity issue
authority-boundary issue
release-mechanism issue
```

Only release-mechanism issues directly affect the release-authority path.

Renderer, wording, visual, and parity issues may still be important, but they belong to the reader / audit / publication surface unless they alter authority.

## Cryptographic provenance and attestation review

PULSE-native review separates these layers:

```text
authority carrier
binding carrier
attestation subject
attestation carrier
external verifier
```

Authority carrier:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

Binding carrier:

```text
artifact_provenance_binding_v0.json
```

Attestation subject:

```text
artifact_provenance_binding_v0.json
```

Attestation carrier:

```text
cryptographic attestation over the binding carrier
```

A provenance / attestation review evaluates:

```text
whether the binding carrier records the relevant artifact relationship
whether the verifier recomputes the relation
whether the attestation is over the binding carrier
whether attestation credentials are isolated from the main CI job
whether the attestation action is pinned
whether artifact download is repository-explicit
whether attestation happens after binding verification
```

Attestation strengthens provenance.

It does not redefine release authority.

## External validation maturity

External validation maturity describes independent review or reproduction.

Examples:

```text
independent reproduction
independent audit
third-party reference integration
external reviewer report
consumer-side verification
case study by an external party
```

A lack of external validation should be classified as:

```text
external validation maturity gap
```

It should not automatically be classified as:

```text
internal mechanical blocker
```

Category-correct statement:

```text
PULSE may have a mechanically defined authority path and still need third-party reproduction.
```

Category-crossing statement:

```text
PULSE is mechanically weak because it has low visible adoption.
```

Those are different claims.

## Adoption / ecosystem signals

Adoption and ecosystem signals measure visibility, uptake, and reuse.

Examples:

```text
stars
forks
issues
pull requests
external users
integrations
mentions
downloads
```

These signals are useful external maturity indicators.

They are distinct from external validation.

They become external validation only when they include:

```text
independent reproduction
independent audit
third-party reference integration
external reviewer report
consumer-side verification
```

Correct classification:

```text
0 stars / 0 forks
= low visible adoption / ecosystem uptake
```

Incorrect classification:

```text
0 stars / 0 forks
= failed external validation
```

Mechanical implication:

```text
adoption signal
≠ PULSEmech correctness result
```

Adoption can increase visibility, reuse, operational stress-testing, and external feedback.

Adoption does not define the release-authority mechanism.

## Productization maturity

Productization maturity describes packaging, onboarding, deployment, and operational convenience.

Examples:

```text
plug-and-play installation
enterprise deployment guide
multi-tenant deployment model
managed service packaging
installer or package release
onboarding flow
integration templates
commercial support model
```

Productization gaps may affect adoption.

They do not automatically affect PULSEmech correctness.

Category-correct statement:

```text
PULSE may require more productization before broad enterprise adoption.
```

Separate mechanical question:

```text
Does the PULSEmech authority path produce a policy-declared, materialized, fail-closed release decision?
```

## Maintainer / governance maturity

Maintainer / governance maturity describes repository stewardship and change-control distribution.

Examples:

```text
single-maintainer model
bus factor
codeowner distribution
review diversity
branch protection
release custody
maintainer rotation
quorum rules
external reviewer adoption
```

A single-maintainer model is a real external trust and sustainability risk.

It is not automatically a failure of the release-authority mechanism.

Correct classification:

```text
single maintainer
= repository governance / bus-factor risk
```

Incorrect classification:

```text
single maintainer
= check_gates.py or policy materialization is mechanically invalid
```

A maintainer-governance finding should identify the affected boundary:

```text
repository change control
release / DOI / Zenodo custody
authority-impact PR handling
external trust
review distribution
emergency access
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

Each finding should identify:

```text
affected carrier
authority impact
evidence source
current mitigation
remaining work
status
```

## Reader-surface risk

A finding is a reader-surface risk when:

```text
the machine path remains correct
but a public or human-facing display may be misunderstood
```

Reader-surface risks are important.

They should not be classified as authority failures unless they change, bypass, or contradict the authority path.

Examples:

```text
core/stubbed state is visually close to release-grade display
public badge lacks run-mode context
reader surface hides scaffold markers
public page exposes raw CI paths instead of normalized artifact paths
```

## Provenance / attestation gap

A finding is a provenance / attestation gap when:

```text
the authority path exists
but artifact relationship verification or cryptographic attestation is incomplete
```

This category may become a mechanical blocker when:

```text
the binding carrier omits decision-bearing artifacts
the verifier accepts mismatched artifacts
the attestation subject is not the binding carrier
attestation permissions are over-broad
the attestation action is mutable / unpinned
```

Otherwise, it should be treated as a provenance maturity gap.

## External validation gap

A finding is an external validation gap when:

```text
the mechanism exists
but has not been reproduced, audited, or integrated by an independent party
```

This is a maturity issue.

It is not automatically an internal technical defect.

Examples:

```text
no independent reproduction
no external audit
no third-party reference integration
no external reviewer packet
no consumer-side verification report
```

## Adoption / ecosystem gap

A finding is an adoption gap when:

```text
visible stars / forks / issues / PRs / integrations / users are low
```

This measures external uptake.

It does not directly measure PULSEmech correctness.

Examples:

```text
low stars
low forks
few open issues
few external contributors
few integrations
low visible deployment footprint
```

## Productization gap

A finding is a productization gap when:

```text
installation is not plug-and-play
enterprise packaging is missing
maintainer operations are not multi-party
documentation is too dense for quick onboarding
turnkey deployment templates are missing
```

This may matter for adoption.

It does not automatically invalidate the release-authority mechanism.

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

## Cross-category review patterns

The following patterns mix separate review categories.

They may contain useful concerns, but they require category correction before they can become PULSE-native findings.

```text
PULSE has low stars, therefore the mechanism is weak.
PULSE is not a plug-and-play enterprise platform, therefore release authority is incomplete.
PULSE is single-maintainer, therefore the CI allow/block path is invalid.
PULSE has shadow workflows, therefore shadow layers are normative.
PULSE uses GitHub Actions, therefore all provenance is meaningless.
PULSE is governance, therefore it should be judged only by governance maturity.
```

A category-correct review should identify:

```text
the affected carrier
the review category
the authority impact
the evidence source
the remaining work
```

## Category-correct review readings

| Cross-category reading | Category-correct reading |
|---|---|
| Low GitHub adoption means PULSE is weak | Low adoption is an adoption / ecosystem signal; it is distinct from external validation and does not determine PULSEmech mechanical correctness |
| Not enterprise plug-and-play means release authority is incomplete | Productization maturity is separate from release-authority mechanics |
| Single maintainer invalidates the authority path | Single maintainer is a repository governance / bus-factor risk, not a direct gate-enforcement defect |
| Public core/STAGE-PASS display disproves PULSE | Public reader surface risk must be separated from the authority path |
| Shadow workflows imply hidden authority | Shadow outputs remain non-authorizing unless promoted through declared policy and required-gate enforcement |
| Missing external review means the mechanism is invalid | Missing external review is an external validation gap, not automatically an internal mechanical blocker |
| GitHub Actions trust domain limits portability | Trust-domain scope is a provenance / deployment-boundary finding, not an automatic failure of the declared authority path |
| No enterprise onboarding means no authority | Enterprise onboarding is a productization gap, not a release-authority correctness result |

## Review status language

Use precise status labels:

```text
closed internally
partially closed
external validation gap
adoption / ecosystem gap
productization gap
maintainer / governance maturity gap
optional polish
out of scope for current mechanism
future productization layer
```

Avoid using broad labels without carrier and category:

```text
not mature
not production-ready
not standard
not adopted
governance issue
platform issue
```

A broad label becomes useful only when tied to:

```text
review category
affected carrier
authority impact
evidence source
remaining work
```

## Boundary with governance language

PULSE may have governance implications.

Governance language is useful when discussing:

```text
maintainer model
approval process
external review
release custody
adoption
quorum
institutional maturity
```

PULSE-native mechanical language is required when discussing:

```text
status.json
declared policy
workflow-effective required gate set
fail-closed CI enforcement
release-decision materialization
carrier boundaries
artifact provenance binding
attestation subject / carrier
```

Correct split:

```text
mechanical release-authority correctness
= internal PULSEmech question

maintainer / community / adoption maturity
= external governance and sustainability question
```

## Boundary with platform language

Platform language is useful when discussing:

```text
installation
packaging
onboarding
enterprise deployment
integrations
operational support
turnkey adoption
```

PULSE-native review should not convert platform gaps into authority failures unless the gap affects:

```text
status.json
declared policy
materialized required gate set
fail-closed enforcement
release decision materialization
binding / attestation carrier
```

## Boundary with adoption language

Adoption language is useful when discussing:

```text
visibility
reuse
community uptake
external users
ecosystem footprint
```

Adoption language should not determine release-authority correctness.

Adoption findings should be recorded as:

```text
adoption / ecosystem signal
```

unless they include independent reproduction, audit, or third-party reference integration.

## Boundary with external validation language

External validation language is useful when discussing:

```text
independent reproduction
external audit
third-party reference integration
external reviewer report
consumer-side verification
```

External validation findings should be recorded as:

```text
external validation maturity
```

They should not be replaced by adoption metrics.


## Review example: low adoption

```text
Finding:
Low visible GitHub adoption.

Category:
Adoption / ecosystem gap.

Affected signal:
Adoption / ecosystem signal.

Authority impact:
No direct PULSEmech authority-path impact.

Evidence:
Low visible stars / forks / external PRs / integrations.

Current mitigation:
Documentation, citation records, public reference surfaces.

Remaining work:
Reference integrations, external usage examples, adoption outreach.

Status:
Adoption / ecosystem gap.
```

## Review example: missing independent audit

```text
Finding:
No independent audit visible.

Category:
External validation gap.

Affected carrier:
External verification carrier.

Authority impact:
No direct PULSEmech authority-path impact unless the audit finds a mechanical or boundary defect.

Evidence:
No external reviewer report or independent reproduction cited.

Current mitigation:
External Verification Path v0.

Remaining work:
Independent reproduction, audit, or third-party reference integration.

Status:
External validation gap.
```

## Review example: public reader ambiguity

```text
Finding:
Public reader surface may be misread as release-grade.

Category:
Reader-surface risk.

Affected carrier:
Quality Ledger / public reader carrier.

Authority impact:
No direct authority-path impact unless the public surface contradicts recorded artifacts or implies independent authority.

Evidence:
Core/stubbed or scaffolded state displayed near pass-like status.

Current mitigation:
Public reader surface state, reader carrier wording, materialized evidence-state wording.

Remaining work:
Optional visual strengthening.

Status:
Mostly closed internally.
```

## Review example: required gate bypass

```text
Finding:
Required gate can be missing while release decision passes.

Category:
Mechanical blocker.

Affected carrier:
Declared policy / materialized required gate set / check_gates.py.

Authority impact:
Direct PULSEmech authority-path impact.

Evidence:
Missing required gate does not fail closed.

Current mitigation:
check_gates.py literal true-only and missing-gate fail-closed semantics.

Remaining work:
Fix enforcement and add regression coverage.

Status:
Mechanical blocker until fixed.
```

## Review example: shadow authority drift

```text
Finding:
Shadow output is used as release evidence without declared policy.

Category:
Authority-boundary blocker.

Affected carrier:
Diagnostic / shadow carrier.

Authority impact:
Direct boundary impact if the shadow output participates in release authority without policy declaration and required-gate enforcement.

Evidence:
Shadow field affects release outcome without policy registration.

Current mitigation:
Normative vs Shadow Inventory Model v0 and report builder.

Remaining work:
Classify carrier, update policy if intended, or remove implicit authority path.

Status:
Authority-boundary blocker until resolved.
```

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

Adoption can increase visibility, reuse, and stress-testing.

Independent reproduction, audit, or third-party reference integration can validate PULSE externally.

Productization can make PULSE easier to adopt.

None of these external maturity layers redefine the release-authority mechanism.

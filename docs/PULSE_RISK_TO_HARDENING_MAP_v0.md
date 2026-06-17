# PULSE Risk-to-Hardening Map v0

## Purpose

This document maps external critique patterns, review findings, and hardening
concerns into the PULSEmech operating model.

Its role is to convert review observations into classified routes:

```text
external critique or review observation
→ PULSE classification
→ existing boundary or control
→ remaining hardening route
→ verification or completion signal
```

PULSEmech is an artifact-bound release-authority mechanism for AI release
decisions.

The PULSEmech release-authority path is:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```

This document is a hardening and review-routing map.

It preserves the PULSEmech authority path.

It introduces no new release semantics, no new gate policy behavior, no new CI
behavior, and no new authority carrier.

## Operating principle

A review finding becomes useful when it is routed.

The routing model is:

```text
finding
→ classification
→ affected boundary
→ existing control
→ hardening action
→ verification signal
```

A finding affects release authority only when it identifies a break or ambiguity
in the PULSEmech path:

```text
recorded release evidence
status.json
declared gate policy
workflow-effective materialized required gate set
strict fail-closed CI enforcement
declared-policy allow/block outcome
```

Other findings may still be valuable.

They are routed through the finite classification model defined below.

## Relation to existing documents

This map should be read with:

```text
README.md
HARDENING_PLAN.md
docs/PULSE_EXTERNAL_REVIEW_ENTRYPOINT_v0.md
docs/PULSE_TERMINOLOGY_RISK_REGISTER_v0.md
docs/release_authority_manifest_v0.md
docs/STATUS_CONTRACT.md
docs/status_json.md
docs/RUNBOOK.md
```

The external review entrypoint defines how reviewers inspect PULSEmech.

The terminology register controls category misreadings.

The hardening plan defines the staged repository-hardening sequence.

This map connects critique patterns to those operating routes.

## Classification model

The following classifications are the declared finding classes for this map.

Risk-map rows must use these declared classifications.

| Classification | Meaning | Release-authority effect | Completion signal |
|---|---|---|---|
| Authority-path finding | A break or ambiguity in evidence recording, status representation, declared policy, gate materialization, CI enforcement, or allow/block determinism | Directly release-relevant | Failing test, blocked CI, corrected artifact binding, or clarified policy/gate path |
| Evidence-admission finding | A problem in how candidate evidence, external review output, diagnostic output, shadow output, detector output, or summary output becomes recorded release evidence | Release-relevant when the evidence is required by declared policy | Explicit admission rule, status representation, required gate materialization, fail-closed enforcement |
| Reader-surface finding | A mismatch or ambiguity in Quality Ledger, Pages, badges, reports, dashboards, summaries, or rendered outputs | Reader-trust relevant; release effect only through underlying recorded evidence and required gates | Reader wording, parity check, publication snapshot, or non-authority boundary fix |
| Traceability / audit finding | A reconstruction issue across evidence, policy, evaluator, run identity, manifest, digest, required gate set, or audit bundle | Reconstruction relevant | Trace carrier fix, manifest row, digest binding, audit bundle update |
| Reproducibility finding | A reviewer cannot reproduce or reconstruct the path from documented artifacts and commands | Repository-hardening relevant | Clean command, dependency truth, clean-install smoke, artifact location fix |
| CI hardening finding | A semantic regression can merge or enforcement is not strict enough | Release-grade infrastructure relevant | Required CI check, contract test, fail-closed regression test |
| Dependency / packaging finding | Install or execution depends on ambiguous dependency truth or fragile script structure | Reproducibility and maintainability relevant | Single dependency truth, clean install, package layout, compatibility wrapper |
| Supply-chain hardening finding | Artifact integrity, provenance, attestations, signing, public/private artifact separation, or workflow integrity needs strengthening | Supporting assurance relevant | Signing / attestation / provenance / workflow-hardening implementation |
| Documentation discoverability finding | A reviewer-facing document or source-of-truth path is not discoverable | Review-route relevant | README link, docs index link, entrypoint wiring, docs-link check |
| Category framing finding | PULSE is read as governance, dashboard, MLOps, runtime guardrail, supply-chain framework, adoption project, maturity project, or enterprise platform | Category-boundary relevant | Terminology boundary fix, review entrypoint wording, risk-map route |
| Adoption / sustainability finding | Low adoption, maintainer concentration, onboarding gap, or integration friction | Ecosystem and sustainability relevant | Onboarding docs, examples, external verification packet, reproducibility exercise |
| Candidate-policy finding | A review identifies a useful future required condition | Future release-policy relevant only after admission | Policy proposal, accepted policy change, materialized required gate, fail-closed CI enforcement |
| Roadmap finding | A useful future capability or integration is identified | Future-planning relevant | Roadmap item after hardening completion gate |

## Risk-to-hardening map

Every classification in this table is drawn from the declared classification
model above.

| External critique or risk pattern | Correct PULSE classification | Existing boundary / control | Remaining hardening route | Release-authority effect |
|---|---|---|---|---|
| PULSE is read primarily as governance | Category framing finding | Terminology register and external review entrypoint | Keep identity text centered on artifact-bound release authority | No release effect unless a release-authority path break is shown |
| PULSE is read primarily as dashboard or Quality Ledger | Reader-surface finding | Reader-surface boundary; Quality Ledger is a reader carrier over recorded state | Keep reader parity and non-authority wording clear | Release effect begins only through recorded evidence and required gates |
| PULSE is read primarily as MLOps platform | Category framing finding | External review reading-frame routing | Route MLOps comparisons as integration notes or candidate-policy observations | No direct release effect |
| PULSE is read primarily as runtime guardrail | Category framing finding | Release boundary vs runtime boundary split | Keep runtime comparison as contextual boundary finding | No direct release effect |
| PULSE is read primarily as supply-chain framework | Category framing finding | Terminology register and hardening-plan support-layer framing | Separate supply-chain support layers from PULSEmech identity | No direct release effect |
| External review approval is treated as release permission | Evidence-admission finding | External review entrypoint state model | Route review output through evidence admission before release effect | Release effect only after recorded evidence, declared policy, materialized gate, and CI enforcement |
| Public Pages or badge visibility is treated as authority | Reader-surface finding | Public surfaces are reader / publication carriers | Maintain publication snapshot and reader-surface wording | Public visibility alone has no release effect |
| Aggregate pass is confused with evidence presence | Evidence-admission finding | External evidence boundary and hardening plan CR-05 | Add tests and docs showing evidence presence, aggregate pass, and gate satisfaction as distinct | Release effect only through declared required gate semantics |
| Summary file presence is treated as release-grade evidence | Evidence-admission finding | Recorded evidence admission path | Require source identity, status representation, policy mapping, materialized gate, and CI enforcement | No release effect until admitted and enforced |
| Diagnostic or shadow output is treated as authority | Evidence-admission finding | Optional and shadow surfaces are non-authorizing by default | Keep shadow non-interference tests and boundary wording | Release effect only after explicit promotion into required gates |
| Green CI outside the workflow-effective required gate set is treated as authority | CI hardening finding | PULSEmech requires declared policy and materialized required gates | Keep required-gate CI enforcement explicit | Release effect only through declared-policy CI allow/block path |
| Release semantics can silently drift | Authority-path finding | Hardening plan CR-01 and CR-02 | Add or maintain contract tests and required CI checks | Direct release-authority risk until locked |
| Required gate meaning is ambiguous | Authority-path finding | Status contract, gate policy, check_gates semantics | Add semantic regression tests and docs anchors | Direct release-authority risk |
| Missing required gates do not fail closed | Authority-path finding | Strict fail-closed CI enforcement invariant | Add regression tests for missing and non-true required gates | Direct release-authority risk |
| Dependency truth is split | Dependency / packaging finding | Hardening plan CR-03 | Move toward single dependency truth and clean-install smoke | Hardening risk, not PULSEmech definition |
| Script-heavy import structure is fragile | Dependency / packaging finding | Hardening plan CR-04 | Package layout and compatibility wrappers | Hardening risk, not PULSEmech definition |
| External reviewer cannot reconstruct artifact paths | Reproducibility finding | External review entrypoint and release authority manifest carrier | Add artifact index, command clarity, review packet, or audit bundle references | Reviewability risk |
| Release authority manifest is omitted from review path | Traceability / audit finding | `release_authority_v0.json` as audit / trace carrier | Keep explicit manifest row and contract link | Reconstruction support; non-authorizing by itself |
| Docs entrypoint is orphaned | Documentation discoverability finding | README Start here and docs/INDEX wiring | Add links and docs-link check | Review-route risk |
| Public/private artifact boundary is unclear | Supply-chain hardening finding | Hardening plan publication-surface clarity | Add public/private artifact classification and sanitization checks | Hardening and trust risk |
| Signing / attestations are incomplete | Supply-chain hardening finding | Hardening plan support-layer framing | Add signing, SLSA, Sigstore, in-toto, or provenance attestations as support layers | Release effect only if promoted into required gates |
| Branch protection is incomplete | CI hardening finding | Hardening plan CI hardening phase | Align required checks and branch protection with release core | Infrastructure risk around release path |
| Low adoption is used as mechanical criticism | Adoption / sustainability finding | Adoption is separate from mechanical validity | Add examples, onboarding, external verification exercises | No release-authority effect |
| Maintainer concentration is used as mechanism criticism | Adoption / sustainability finding | Reviewable mechanics and docs reduce bus-factor | Add contributor path, review packet, reproducibility exercises | Sustainability risk, not mechanism invalidation |
| Enterprise maturity score is used as PULSE validity | Category framing finding | Hardening plan separates repository maturity from PULSE definition | Route maturity scoring as roadmap or hardening observation | No direct release-authority effect |
| Future useful requirement is found by review | Candidate-policy finding | Evidence-admission and policy-promotion route | Propose policy, materialize gate, enforce in CI | Release effect only after accepted policy and gate enforcement |
| Future integration or capability is useful but not yet required | Roadmap finding | Roadmap items are separate from current release authority | Track after hardening completion gate | No release-authority effect until promoted into policy |

## Existing control map

| Control / document | Operating role | Risk classes covered |
|---|---|---|
| `README.md` | Curated identity, release-authority map, start path, authority boundary | Category framing finding; Reader-surface finding; Evidence-admission finding |
| `HARDENING_PLAN.md` | Repository and release-grade infrastructure hardening sequence | CI hardening finding; Dependency / packaging finding; Supply-chain hardening finding; Evidence-admission finding |
| `docs/PULSE_EXTERNAL_REVIEW_ENTRYPOINT_v0.md` | External review operating route and review-output state model | Documentation discoverability finding; Evidence-admission finding; Traceability / audit finding; Reproducibility finding |
| `docs/PULSE_TERMINOLOGY_RISK_REGISTER_v0.md` | Category and terminology boundary control | Category framing finding |
| `docs/release_authority_manifest_v0.md` | Contract for release authority manifest as audit / trace carrier | Traceability / audit finding |
| `docs/STATUS_CONTRACT.md` | Status artifact contract | Authority-path finding |
| `docs/status_json.md` | Reader guidance for `status.json` | Authority-path finding; Reader-surface finding |
| `docs/RUNBOOK.md` | Operational triage | Authority-path finding; CI hardening finding |
| `docs/EXTERNAL_DETECTORS.md` | External detector policy and modes | Evidence-admission finding; Candidate-policy finding |
| `docs/external_detector_summaries.md` | External detector summary fold-in path | Evidence-admission finding |
| `docs/quality_ledger.md` | Quality Ledger reader-surface contract | Reader-surface finding |
| `docs/WORKFLOW_MAP.md` | Workflow role map | CI hardening finding; Evidence-admission finding |

## Hardening route by class

### Authority-path finding route

Use this route when a finding affects the release decision path.

```text
finding
→ affected PULSEmech segment
→ expected behavior
→ observed behavior
→ fail-closed consequence
→ regression test or artifact fix
→ required CI check
```

Completion signal:

```text
the authority path is reconstructable
the required gate behavior is locked
CI blocks semantic regression
```

### Evidence-admission finding route

Use this route when a finding concerns candidate evidence, external review
output, detector output, diagnostic output, shadow output, summaries, or review
artifacts.

```text
candidate evidence
→ source identity
→ recorded release evidence
→ status.json representation
→ declared gate-policy requirement
→ materialized required gate
→ strict fail-closed CI enforcement
```

Completion signal:

```text
evidence presence, aggregate result, and required gate satisfaction are distinct
and mechanically enforced
```

### Reader-surface finding route

Use this route when a finding concerns Quality Ledger, Pages, dashboards,
badges, rendered reports, summaries, or public status surfaces.

```text
recorded artifact
→ reader surface
→ parity / consistency check
→ non-authority boundary wording
→ publication or rendering fix
```

Completion signal:

```text
reader surface reflects recorded state
reader surface does not create independent release permission
```

### Traceability / audit finding route

Use this route when a finding concerns reconstruction of evidence, policy,
evaluator, run identity, digests, required gate set, or decision trail.

```text
release artifact
→ trace carrier
→ audit carrier
→ relation binding
→ reconstruction check
```

Completion signal:

```text
reviewer can reconstruct the release-authority path from recorded artifacts
```

### Reproducibility finding route

Use this route when a reviewer cannot reproduce the documented path.

```text
fresh clone
→ documented install
→ core command
→ generated artifacts
→ schema validation
→ gate enforcement
→ expected output comparison
```

Completion signal:

```text
a clean environment can reconstruct the core path without guesswork
```

### CI hardening finding route

Use this route when a finding concerns branch protection, required checks,
semantic regression, workflow-required gate wiring, or fail-closed enforcement.

```text
CI finding
→ affected workflow or required check
→ expected fail-closed behavior
→ regression test
→ required CI enforcement
```

Completion signal:

```text
required release semantics cannot regress without CI failure
```

### Dependency / packaging finding route

Use this route when a finding concerns dependency truth, package layout,
script-heavy execution, import ambiguity, or clean-install behavior.

```text
dependency or packaging finding
→ dependency truth check
→ clean-install smoke
→ package / script compatibility fix
→ reproducibility verification
```

Completion signal:

```text
a clean environment can install and execute the documented path
```

### Supply-chain hardening finding route

Use this route when a finding concerns signing, attestations, dependency
integrity, workflow integrity, artifact provenance, public/private artifact
separation, or publication trust.

```text
hardening finding
→ support-layer classification
→ implementation plan
→ verification artifact
→ optional candidate policy route
```

Completion signal:

```text
support layer strengthens PULSEmech operation without redefining PULSEmech
```

### Documentation discoverability finding route

Use this route when a finding concerns orphaned docs, missing README links,
missing docs index links, or unclear reviewer entrypoints.

```text
discoverability finding
→ source-of-truth document
→ README Start here link
→ docs/INDEX.md link
→ docs-link check
```

Completion signal:

```text
reviewers can find the document through curated entrypoints
```

### Category framing finding route

Use this route when a finding concerns PULSE being misread as governance,
dashboard, MLOps, runtime guardrail, supply-chain framework, adoption project,
maturity project, or enterprise platform.

```text
category framing finding
→ correct PULSE classification
→ terminology boundary
→ review entrypoint route
→ wording or docs correction
```

Completion signal:

```text
PULSE identity resolves to artifact-bound release authority
```

### Adoption / sustainability finding route

Use this route when a finding concerns adoption, onboarding, maintainer
distribution, external usability, or integration friction.

```text
adoption observation
→ usability or sustainability class
→ onboarding / example / verification packet action
→ reproducibility exercise
```

Completion signal:

```text
external users can understand, reproduce, and inspect the mechanism
```

### Candidate-policy finding route

Use this route when a review identifies a useful future release condition.

```text
candidate-policy finding
→ policy proposal
→ accepted declared gate-policy change
→ materialized required gate
→ strict fail-closed CI enforcement
```

Completion signal:

```text
the future requirement becomes release-relevant only after declared policy and
CI enforcement
```

### Roadmap finding route

Use this route when a finding identifies a future capability or integration that
is useful but not part of the current release-authority path.

```text
roadmap finding
→ roadmap classification
→ dependency on current hardening state
→ future implementation plan
```

Completion signal:

```text
future capability is tracked without redefining current release authority
```

## Finding template

Use this shape when adding a risk or critique item:

```text
Finding:
Classification:
Affected boundary:
Existing control:
Observed condition:
Release-authority effect:
Hardening route:
Verification signal:
Suggested next step:
```

The `Classification` field should use one of the declared classifications:

```text
Authority-path finding
Evidence-admission finding
Reader-surface finding
Traceability / audit finding
Reproducibility finding
CI hardening finding
Dependency / packaging finding
Supply-chain hardening finding
Documentation discoverability finding
Category framing finding
Adoption / sustainability finding
Candidate-policy finding
Roadmap finding
```

## Candidate-policy promotion route

A finding becomes a future release requirement only through policy promotion.

The route is:

```text
review finding
→ Candidate-policy finding
→ policy proposal
→ accepted declared gate-policy change
→ materialized required gate
→ strict fail-closed CI enforcement
```

This route allows PULSE to grow while preserving a single release-authority path.

## Completion criterion

This risk-to-hardening map is effective when a reviewer can classify each
critique into one of these declared classifications:

```text
Authority-path finding
Evidence-admission finding
Reader-surface finding
Traceability / audit finding
Reproducibility finding
CI hardening finding
Dependency / packaging finding
Supply-chain hardening finding
Documentation discoverability finding
Category framing finding
Adoption / sustainability finding
Candidate-policy finding
Roadmap finding
```

A strong review separates:

```text
mechanism break
from hardening work
from reader-surface ambiguity
from adoption signal
from future policy candidate
```

## Final rule

A critique is useful when it is routed through a declared classification.

PULSE hardening proceeds by classification, boundary control, artifact evidence,
and verification.

Release authority remains the PULSEmech path:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```

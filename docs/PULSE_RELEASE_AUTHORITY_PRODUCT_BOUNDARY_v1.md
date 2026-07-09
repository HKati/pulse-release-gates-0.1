# PULSE Release-Authority Product Boundary v1

Status: product-boundary contract  
Scope: PULSE v1 product closure  
Normative effect: documentation-only  
Release-authority effect: none  
Policy effect: none  
Workflow effect: none  
Verifier effect: none  
Schema effect: none  

## 1. Purpose

This document defines the PULSE product boundary for the v1 product-closure track.

PULSE is an artifact-bound release authority layer for AI-assisted production work. Its purpose is to turn recorded release evidence, declared policy, and workflow-effective materialized gates into a deterministic, auditable, fail-closed pre-release allow/block decision.

PULSE is not a dashboard, not a runtime guardrail, not a human approval label, not a compliance certificate, and not an observability surface. PULSE operates at the release boundary.

## 2. Product identity

The canonical product identity is:

PULSE — EPLabsAI: artifact-bound release authority for AI-assisted production work.

The shorter technical identity is:

PULSE: artifact-bound release authority.

The release-boundary identity is:

recorded evidence + declared policy + materialized gates + fail-closed CI enforcement.

## 3. Authoritative release-decision chain

The authoritative PULSE release-decision chain is:

1. recorded release evidence
2. final status.json
3. declared gate policy
4. workflow-effective materialized required gate set
5. check_gates.py enforcement
6. primary CI allow/block decision

Only this chain can create release-authority meaning.

No reader surface, dashboard, badge, page, comment, rendered report, shadow layer, external narrative, or human approval label can create release authority outside this chain.

## 4. Authority components

### 4.1 Recorded release evidence

Recorded release evidence is the evidence substrate for a release-boundary decision.

It may include candidate state, detector summaries, provenance records, trusted producer reports, external evidence records, policy bindings, verifier bindings, artifact digests, run identity, and audit manifests.

Evidence that is missing, stale, detached from the current run, detached from the release candidate, or not bound to the required artifact identity cannot satisfy release-grade authority requirements.

### 4.2 final status.json

The final status.json is the machine-readable state carrier for the release decision.

It is not a dashboard.  
It is not a rendered report.  
It is not a human summary.  

It is the state artifact consumed by enforcement and by reader surfaces.

### 4.3 Declared gate policy

The declared gate policy defines which gates can be required and under what declared gate set.

The policy is the declaration layer. It does not by itself authorize release. It must be combined with the workflow-effective materialized gate set and enforcement.

### 4.4 Workflow-effective materialized required gate set

The workflow-effective materialized required gate set is the exact required gate set used for the current workflow lane.

It must be derived from the declared policy and the workflow context.

It must not be hand-reconstructed as an informal list.

It must not be replaced by dashboard state, documentation text, or rendered summaries.

### 4.5 check_gates.py

check_gates.py is the enforcement engine for required gate values.

The required gate interpretation is fail-closed.

A required gate must be literal true to pass.

Missing gates, null gates, false gates, malformed gates, undeclared required gates, or non-literal truthy values must not create release permission.

### 4.6 Primary CI allow/block decision

The primary CI decision is the release-boundary executor.

The CI decision may allow release only when the required gate set is satisfied under the declared policy and current workflow context.

CI failure, missing evidence, missing required gates, failed verification, or incomplete release-grade package must block release.

## 5. Non-authorizing surfaces

The following surfaces are non-authorizing unless their outputs are explicitly recorded as release evidence, declared by policy, materialized into the required gate set, and enforced by check_gates.py:

- Quality Ledger
- GitHub Pages
- badges
- README text
- PR comments
- rendered reports
- SARIF uploads
- documentation pages
- screenshots
- external summaries
- shadow layers
- diagnostic overlays
- human approval labels
- discussion comments
- issue comments
- publication metadata
- citation metadata

These surfaces may explain, display, review, or preserve state. They do not authorize release.

## 6. Reader-surface rule

A reader surface may read the final state.  
A reader surface may render the final state.  
A reader surface may help humans inspect the final state.  

A reader surface must not become the source of release authority.

If a rendered surface disagrees with final status.json, the rendered surface is wrong.

If a rendered surface displays a passing state that was not enforced by the authoritative chain, it is non-authoritative.

## 7. Shadow-layer rule

Shadow layers are diagnostic by default.

A shadow layer may observe, score, explain, compare, or report.

A shadow layer must not block or allow release unless all of the following are true:

1. its evidence is recorded as release evidence;
2. its gate is declared in policy;
3. its required status is materialized by the workflow-effective gate set;
4. check_gates.py enforces it;
5. CI uses the result in the primary allow/block decision.

Without those conditions, a shadow layer remains non-normative.

## 8. Human-approval and exception-boundary rule

Human review can support design, interpretation, investigation, and accountability.

Human review does not replace the release-authority chain.

A human approval label, comment, review, discussion, or external endorsement must not create release permission unless it is transformed into recorded evidence, declared by policy, materialized as a required gate, and enforced through the primary CI path.

There is no dashboard-derived authority.  
There is no label-derived authority.  
There is no comment-derived authority.  

There is no independent break-glass release-authority path in the normal PULSE product boundary.

The documented `break_glass_override_v0` mechanism remains an audited exception mechanism for emergency or non-passing release contexts. It is separate from the normal passing release-authority path.

A break-glass override must not:

- mutate required gate values;
- convert a non-passing gate state into a passing gate state;
- hide or erase the primary CI allow/block result;
- replace recorded evidence, declared policy, materialized required gates, or `check_gates.py` enforcement;
- create a dashboard-derived, label-derived, comment-derived, or hidden-pass release authority.

When used, the break-glass artifact records an explicit audited exception decision outside the normal passing release-authority chain. The underlying PULSE gate result remains reviewable as non-passing unless the authoritative chain itself later passes.

For the existing exception contract, see [`docs/BREAK_GLASS_OVERRIDE_v0.md`](BREAK_GLASS_OVERRIDE_v0.md).

## 9. Evidence-binding rule

Release-grade evidence must be bound to the current release candidate.

At release-grade level, URI-only evidence is insufficient.

A release-grade evidence record should bind, as applicable:

- release candidate identity
- artifact path
- artifact digest
- current run identity
- commit identity
- policy identity
- policy digest
- verifier identity
- producer identity
- evidence timestamp or freshness marker
- verification result
- recorded-signal-only status where applicable

Evidence that cannot be tied back to the current candidate and artifact boundary is not release-grade authority evidence.

## 10. Product lanes

PULSE has three product lanes for v1 closure.

### 10.1 PULSE Core

PULSE Core is the minimum deterministic authority path.

It consists of:

- recorded state;
- final status.json;
- declared gate policy;
- workflow-effective materialized required gates;
- check_gates.py enforcement;
- primary CI allow/block decision.

Core is the smallest product-meaningful path.

### 10.2 PULSE Release-Grade

PULSE Release-Grade is the full reference package path.

It extends Core with:

- current-run evidence;
- non-stubbed candidate state;
- artifact digest binding;
- policy digest binding;
- verifier identity binding;
- trusted producer evidence where required;
- release_decision_v0.json;
- release_authority_v0.json;
- artifact_provenance_binding_v0.json;
- audit bundle manifest;
- Quality Ledger parity;
- replayable evidence-to-decision trace.

Release-Grade is the proof path for product closure.

### 10.3 PULSE Portable Boundary

PULSE Portable Boundary is the adapter path for using PULSE above different machines, pipelines, agents, or release environments.

The machine below the boundary may vary.

The release-boundary contract must not vary.

A portable integration must provide:

- evidence packet;
- candidate identity;
- artifact identity;
- artifact digest;
- run identity;
- policy identity;
- policy digest;
- materialized required gate set;
- final status state;
- enforcement result.

The output must be a deterministic allow/block decision with reviewable artifacts.

## 11. Machine-boundary model

PULSE does not need to be embedded inside every machine.

PULSE sits above the machine at the release boundary.

A model, agent, CI pipeline, service, HPC job, robot, or deployment system may produce evidence.

PULSE decides whether the evidence is sufficient to cross the release boundary.

The product boundary is therefore:

machine or workflow
→ evidence packet
→ PULSE authority boundary
→ allow/block release decision

PULSE does not claim that the machine is safe at runtime.

PULSE claims that release permission is bound to recorded evidence, declared policy, materialized gates, and fail-closed enforcement.

## 12. Non-claims

This product boundary does not claim:

- runtime safety;
- model alignment;
- legal compliance certification;
- SLSA certification;
- external model approval;
- human approval replacement;
- universal AI safety;
- dashboard authority;
- automatic regulatory conformity;
- production readiness for every deployment class.

PULSE is a release-authority mechanism, not a universal safety claim.

## 13. Product-closure acceptance criteria

PULSE v1 product closure requires all of the following:

- the authoritative chain is documented and not contradicted by reader surfaces;
- the final status state is the source read by enforcement and ledger rendering;
- the declared policy remains the gate declaration source;
- the workflow-effective required gate set is materialized from policy and workflow context;
- check_gates.py remains the enforcement engine;
- missing or non-literal required gate truth fails closed;
- reader surfaces are explicitly non-authorizing;
- shadow layers are explicitly non-normative unless promoted through policy and enforcement;
- release-grade evidence is current-run and artifact-bound;
- release_decision_v0.json is produced for release-grade reference;
- release_authority_v0.json is produced for release-grade reference;
- artifact_provenance_binding_v0.json is produced for release-grade reference;
- audit bundle manifest is produced for release-grade reference;
- Quality Ledger parity is checked against final status;
- portable boundary contract is defined before non-GitHub integrations are claimed;
- no new DOI identity is introduced by product closure.

## 14. Failure rules

A release-boundary decision must fail closed when:

- required evidence is missing;
- required evidence is stale;
- current-run binding is missing;
- artifact digest binding is missing;
- policy digest binding is missing where required;
- verifier identity binding is missing where required;
- trusted producer identity does not match where required;
- the required gate set cannot be materialized;
- a required gate is missing;
- a required gate is not literal true;
- check_gates.py does not pass;
- the primary CI decision does not pass;
- release-grade completeness is claimed but required release-grade artifacts are absent.

## 15. Design consequence

The product is complete only when PULSE can be read as a release-boundary mechanism rather than a repository-local experiment.

The repository is the reference implementation.

The product is the artifact-bound release-authority pattern.

The v1 closure track therefore prioritizes:

1. product-boundary clarity;
2. trusted producer and VSA binding hardening;
3. release-grade package completeness checking;
4. first non-stubbed public release-grade reference run;
5. portable boundary adapter contract;
6. minimal operator-facing command surface;
7. operator guide.

## 16. Change-control note

This document is documentation-only.

It does not change policy behavior.  
It does not change gate behavior.  
It does not change CI behavior.  
It does not change verifier behavior.  
It does not change materializer behavior.  
It does not change schema behavior.  
It does not change DOI identity.  

It defines the product boundary that later implementation PRs must preserve.

# PULSE Release-State Transformation v0

## Status

Informational reference note / repository-facing interpretation anchor.

This document records the PULSEmech release-state transformation path.

It is a wording and architecture note. It does not change release-authority semantics, gate policy, gate registry, status schema, `check_gates.py`, CI allow/block behavior, DOI/Zenodo artifacts, release tags, or release artifacts.

## Purpose

PULSEmech is best read as a closed release-state transformation path.

Its core movement is:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block AI release decision
```

This document records that path as the primary interpretation anchor for PULSE-facing materials.

The purpose is to prevent PULSEmech from being reduced to isolated labels such as governance framework, dashboard, compliance layer, evaluation layer, CI utility, or process wrapper.

PULSEmech is the transition path that turns recorded release evidence into release-state, materialized gate-state, and finally a pre-deployment allow/block decision.

## Core Statement

PULSEmech maps recorded release evidence into `status.json`, materializes the workflow-effective required gate set from declared gate policy, and enforces the resulting gate state through strict fail-closed CI into a pre-deployment allow/block AI release decision.

## Release-State Transformation

PULSEmech does not begin from a category label.

It begins from recorded release evidence.

That evidence becomes release-state only when it is represented in `status.json`.

`status.json` becomes decision-relevant only under declared gate policy.

Declared gate policy becomes effective only when the workflow-effective required gate set is materialized.

The materialized gate state becomes release authority only when strict fail-closed CI enforces it into a pre-deployment allow/block release decision.

The transformation path is therefore:

```text
evidence state
→ artifact state
→ policy-bound state
→ materialized gate state
→ enforced CI state
→ release decision state
```

## Transformation Roles

### 1. Recorded release evidence

Recorded release evidence is the source state.

It may include safety, quality, detector, stability, external evidence, refusal-delta, review, or verifier-backed evidence.

Evidence is not release authority by existence alone.

Evidence must be recorded, bound, and represented before it can affect release state.

### 2. `status.json`

`status.json` is the machine-readable release-state artifact.

It is the central artifact surface where recorded evidence becomes a structured gate and metrics state.

The final release-relevant surface is `status["gates"]`, interpreted with run mode, declared policy, and workflow-effective required gate selection.

Reader surfaces may display `status.json`, but they do not replace it.

### 3. Declared gate policy

Declared gate policy defines which gate relations matter for the current release path.

Policy is not an organizational governance layer in this context.

It is the declared relation that selects which recorded gate states can become workflow-effective required gates.

### 4. Workflow-effective materialized required gate set

The workflow-effective materialized required gate set is the active gate set for the run.

It is the point where declared policy becomes enforceable gate state.

Only the workflow-effective required set can drive release allow/block behavior.

Advisory, diagnostic, review, shadow, or reader-only signals remain outside release authority unless they are recorded as release evidence, represented in `status.json`, selected by declared policy, materialized into the workflow-effective required gate set, and enforced fail-closed by CI.

### 5. Strict fail-closed CI enforcement

Strict fail-closed CI is the terminal enforcement path.

It does not invent release authority.

It enforces the materialized gate state under declared policy.

If a required gate is missing, false, malformed, stale, unsupported, or unmaterialized, the enforcement path blocks.

### 6. Pre-deployment allow/block release decision

The release decision is the downstream consequence of the full transformation path.

It is not inferred from dashboards, summaries, publication surfaces, model claims, review notes, or reader views.

It is produced only when the recorded evidence path reaches strict fail-closed enforcement through the workflow-effective required gate set.

## Closed Data-Path Rule

A PULSEmech release decision is valid only inside the declared transition path.

The path is closed in this sense:

```text
outside label
outside summary
outside dashboard
outside governance wording
outside detector claim
outside copied artifact
outside reader surface
```

cannot bypass:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

A surface may explain the path.

A verifier may qualify evidence for future materialization.

A ledger may render the recorded state.

A review pack may help humans inspect the state.

But the release-state transformation remains the authority carrier.

## Relation to Mechanical Transition Language

The Mechanical Transition Language rule protects wording.

This document protects the release-state transformation reading.

Together they say:

```text
PULSE language must expose the transition.
PULSE architecture must preserve the transition.
```

The correction method for a misread PULSE statement is restoration of the transition path.

## Relation to Release Evidence Verifier

The trusted release-evidence verifier is a future evidence-qualification layer.

It may qualify evidence for materialization.

It does not replace the release-state transformation path.

A future verifier can participate only by producing verified evidence eligible for representation in `status.json`.

The release-state transformation still remains:

```text
verified recorded evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```

## Relation to Quality Ledger

The Quality Ledger is a reader surface over recorded `status.json`.

It may show release-state.

It may show gate rows.

It may show public reader-surface boundaries.

It may show verifier or evidence summaries after such artifacts exist.

It does not create release-state.

It does not recompute release authority.

It does not replace `status.json`, declared gate policy, materialized required gates, or fail-closed CI enforcement.

## Relation to Governance, Compliance, Dashboard, and Supply-Chain Terms

Governance, compliance, dashboard, MLOps, supply-chain, signing, provenance, and attestation language may describe surrounding context or hardening layers.

They do not define PULSEmech identity.

They become PULSE-relevant only when their evidence is recorded, represented, policy-bound, materialized into the workflow-effective required gate set, and enforced through the PULSEmech path.

The category does not define the release decision.

The transition path defines the release decision.

## Reader Rule

Read PULSEmech through this sequence:

```text
What evidence was recorded?
Where is it represented in status.json?
Which declared policy selects it?
Which required gate set is workflow-effective?
How does CI enforce it fail-closed?
What allow/block decision follows?
```

If a PULSE description does not answer these questions, it is incomplete as release-authority language.

## Writer Rule

Prefer sentences that preserve the transformation.

Recommended pattern:

```text
X is recorded as evidence, represented in status.json, selected by declared policy, materialized into the workflow-effective required gate set, and enforced by strict fail-closed CI into a pre-deployment allow/block release decision.
```

Short canonical form:

```text
PULSEmech maps recorded release evidence into status.json, materializes the workflow-effective required gate set from declared gate policy, and enforces the resulting gate state through strict fail-closed CI into a pre-deployment allow/block AI release decision.
```

## Review Rule

When reviewing PULSE-facing text, check whether the release-state transformation remains visible.

Review questions:

- Does the statement identify the evidence source?
- Does it identify `status.json` as the release-state artifact?
- Does it identify declared gate policy?
- Does it identify the workflow-effective materialized required gate set?
- Does it identify strict fail-closed CI enforcement?
- Does it identify the pre-deployment allow/block consequence?
- Does it avoid replacing the transition path with a category label?

A statement should be revised when it names PULSE as a familiar category without exposing the transformation path.

## Minimal Anchor

PULSEmech is a release-state transformation path.

Evidence becomes release-state through `status.json`.

Policy selects the workflow-effective required gate set.

Strict fail-closed CI enforces the gate state.

The result is a pre-deployment allow/block AI release decision.

Reference path:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block AI release decision
```


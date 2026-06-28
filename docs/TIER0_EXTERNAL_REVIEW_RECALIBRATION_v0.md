# Tier 0 external review recalibration v0

## Purpose

This note updates the external-review maturity picture after the controlled Tier 0 self-contained PULSE run.

It does not change release authority, gate policy, workflow enforcement, verifier behavior, materializer behavior, hosted external-model requirements, schemas, tools, or public reader-surface semantics.

## Prior external-review baseline

Before the controlled Tier 0 run record, an external reviewer could correctly observe that:

- the public reader surface may show a Core or reader-visible state;
- public `status.json` may be useful for inspection but is not release authority by itself;
- a complete public non-stubbed release-grade reference package remained pending;
- hosted external-model evidence remained a separate hardening surface.

Those observations remain valid for public reader surfaces unless the reviewed artifact is explicitly bound into the declared release-authority path.

## Tier 0 update

The controlled Tier 0 run record closes a narrower but important gap:

```text
PULSE CI #5830
branch: main
trigger: workflow_dispatch
strict_external_evidence=true
llamaguard_evidence_mode=tier0_not_required
result: PASS
duration: 2m 15s
artifacts: 7
```

Observed outcome:

```text
PULSE CI
→ success

self-contained PULSE evidence floor
→ produced

hosted LlamaGuard runtime lane
→ skipped

self-contained artifact postconditions
→ passed

external model pass
→ not claimed
```

The run demonstrates that the base PULSE evidence path can produce a self-contained Tier 0 evidence floor without relying on a hosted gated external model runtime.

## Recalibrated maturity statement

After Tier 0, the correct maturity statement is:

```text
PULSE has a documented controlled Tier 0 self-contained evidence-floor run.

This proves that the base artifact-bound PULSE evidence path can complete without hosted LlamaGuard / HF gated model access.

This does not prove hosted external-model evidence, full release authorization, or a completed full release-grade external evidence package.
```

## Authority boundary

The Tier 0 floor remains bounded:

```text
Tier 0 self-contained floor
≠ hosted external model evidence
≠ release authorization
```

The Tier 0 run does not claim:

- LlamaGuard passed;
- external model evidence passed;
- hosted evaluator evidence was produced;
- `release_required` was bypassed;
- release authority was created;
- release was authorized.

## Reader-surface boundary

Public Pages, public `status.json`, Quality Ledger views, dashboards, badges, review notes, and documentation records remain reader, audit, trace, diagnostic, or publication surfaces unless explicitly bound through:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ primary CI allow/block release decision
```

A public reader surface may be useful for review, but it must not be treated as release authority by display alone.

## External-review guidance

When reviewing PULSE after Tier 0, distinguish three separate claims:

| Claim | Current status | Authority meaning |
|---|---|---|
| Core/public reader surface exists | yes | reader / smoke / visibility surface only unless bound into the authority path |
| Tier 0 self-contained evidence floor passed | yes | proves the self-contained PULSE evidence floor can complete |
| Hosted external-model release-grade evidence passed | not claimed by Tier 0 | requires the separate hosted external-model lane |

## Hosted external-model lane

Hosted LlamaGuard remains available as a separate opt-in lane:

```text
llamaguard_evidence_mode=hosted_full_runtime
```

That lane may still require provider access, valid credentials, model authorization, and external runtime availability.

Tier 0 mode intentionally avoids converting hosted-provider availability into the default bottleneck for proving the base PULSE mechanism.

## Measurement

```text
Human workshop time:
long, but the provider-gate dependency was separated from the base evidence path.

Machine time:
2m 15s CI time for the controlled Tier 0 run.

Release blocking:
hosted provider access no longer blocks the Tier 0 evidence floor.

Evidence path:
required-gate evidence
→ non-stubbed candidate status
→ self-contained PULSE evidence floor
→ final status summary
→ self-contained artifact postconditions
→ audit sidecars

Fail-closed behavior:
preserved; no hosted external-model pass is fabricated.

Reversibility:
high; hosted_full_runtime remains separately selectable.
```

## Summary

Tier 0 recalibrates the external-review picture.

The previous external caution about public reader surfaces remains valid, but it is no longer complete without the Tier 0 milestone:

```text
Public reader surface
→ not release authority by itself.

Tier 0 controlled run
→ self-contained PULSE evidence floor passed.

Hosted external-model evidence
→ separate opt-in lane, not claimed by Tier 0.
```

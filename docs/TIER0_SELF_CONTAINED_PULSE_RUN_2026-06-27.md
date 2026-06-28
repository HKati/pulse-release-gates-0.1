# Tier 0 self-contained PULSE run record — 2026-06-27 UTC

## Status

```text
PASS
```

## Run identity

```text
Workflow: PULSE CI
Run: #5830
Branch: main
Trigger: workflow_dispatch
Duration: 2m 15s
Artifacts: 7
```

## Run mode

```text
strict_external_evidence=true
llamaguard_evidence_mode=tier0_not_required
```

## Result

The controlled Tier 0 PULSE run completed successfully on `main`.

Observed outcome:

```text
PULSE CI
→ success

self-contained PULSE evidence floor
→ produced

hosted LlamaGuard runtime lane
→ skipped

release-grade artifact postconditions
→ passed

external model pass
→ not claimed
```

## Mechanical path proven

The run demonstrates the self-contained PULSE evidence floor:

```text
required-gate evidence
→ non-stubbed candidate status
→ self-contained PULSE evidence floor
→ final status summary
→ release-grade artifact postconditions
→ audit sidecars
```

This proves that the PULSE base evidence path can complete without relying on a hosted gated external model runtime.

## What this proves

This run proves that PULSE can produce a self-contained Tier 0 evidence floor from its own artifact-bound mechanics.

The mechanism does not depend on:

```text
HF provider access
LlamaGuard hosted model execution
GPU runtime
external model pass claims
```

The operation proves the mechanism:

```text
A large external model is not required for the Tier 0 PULSE evidence floor.
The question is not how large the machine is.
The question is what the operation proves.
```

## What this does not claim

This run does not claim:

```text
LlamaGuard passed
external model evidence passed
hosted evaluator evidence was produced
release_required was bypassed
release authority was created
release was authorized
```

## Hosted external-model lane

Hosted LlamaGuard remains available as a separate opt-in lane:

```text
llamaguard_evidence_mode=hosted_full_runtime
```

That lane may still require provider access, valid credentials, model authorization, and external runtime availability.

Tier 0 mode does not mark hosted evidence as passed. It records hosted external model evidence as not required for the self-contained floor.

## Authority boundary

```text
Tier 0 self-contained floor
≠ hosted external model evidence
≠ release authorization
```

The release-authority path remains separate.

The Tier 0 floor does not:

```text
write release authority
authorize release
claim external model evidence passed
bypass check_gates.py
bypass the recorded verifier
bypass the materializer
replace release_required enforcement
```

## Measurement

```text
Human workshop time:
one controlled run after workflow fixes.

Machine time:
2m 15s CI time.

Release blocking:
hosted provider access did not block the Tier 0 evidence path.

Evidence path:
stronger; the self-contained floor is now observable in workflow execution.

Fail-closed behavior:
preserved; no external pass was fabricated.

Reversibility:
high; hosted_full_runtime can still be selected explicitly.
```

## Summary

The controlled run confirms that PULSE has a working self-contained evidence floor.

This is a release-mechanics milestone:

```text
PULSE can run its Tier 0 evidence path without hosted LlamaGuard / HF gated model access.
```

Hosted external model evidence remains useful, but it is no longer the default bottleneck for proving the PULSE base mechanism.

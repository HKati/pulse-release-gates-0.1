# PULSEmech Core Execution Record v0

## Purpose

This document records a public, manually dispatched PULSEmech Core execution as an external operational reference.

It records a real workflow execution on the public repository.

It does not reclassify the run as a completed non-stubbed release-grade reference run.

It does not create release authority independently of the executed policy and enforcement path.

## Record status

```text
record_status: completed
record_class: public_core_execution
execution_date: 2026-06-24

workflow: PULSE CI
workflow_run_number: 5728
trigger: workflow_dispatch
branch: main

source_commit: 92eec8c5fd58467671924f86e4aa3253a5535d72
strict_external_evidence: false

workflow_conclusion: success
workflow_duration: 1m 34s
workflow_artifact_count: 5

core_required_gate_enforcement: passed
artifact_provenance_binding: materialized_and_verified
artifact_binding_attestation: created

release_decision_sidecar: FAIL
completed_release_grade_reference_run: false
creates_release_authority: false
```

## Public references

- [PULSE CI workflow runs](https://github.com/HKati/pulse-release-gates-0.1/actions/workflows/pulse_ci.yml) — recorded run: `PULSE CI #5728`
- [Source commit `92eec8c5fd58467671924f86e4aa3253a5535d72`](https://github.com/HKati/pulse-release-gates-0.1/commit/92eec8c5fd58467671924f86e4aa3253a5535d72)
- [GitHub artifact-binding attestation `32486739`](https://github.com/HKati/pulse-release-gates-0.1/attestations/32486739)
- [LlamaGuard current-run producer merge PR #2627](https://github.com/HKati/pulse-release-gates-0.1/pull/2627)

## Recorded mechanical path

```text
public workflow_dispatch
→ main branch source commit
→ PULSE Core execution
→ declared core_required policy set
→ generated status.json
→ PULSE_safe_pack_v0/tools/check_gates.py
→ all effective Core required gates PASS
→ workflow SUCCESS
→ decision and provenance artifacts
→ verified artifact-provenance binding
→ GitHub attestation
```

This is an executable PULSEmech Core path.

It is not a documentation-only demonstration.

## Core required gate set

The workflow used the policy-derived:

```text
core_required
```

gate set:

```text
pass_controls_refusal
pass_controls_sanit
sanitization_effective
q1_grounded_ok
q4_slo_ok
```

The strict Core gate evaluation completed successfully.

```text
[OK] All required gates PASS
```

## Observed execution result

| Field | Recorded result |
|---|---|
| Workflow | `PULSE CI` |
| Run number | `5728` |
| Trigger | `workflow_dispatch` |
| Branch | `main` |
| Commit | `92eec8c5fd58467671924f86e4aa3253a5535d72` |
| Strict external evidence | `false` |
| Workflow conclusion | `Success` |
| Duration | `1m 34s` |
| Uploaded workflow artifacts | `5` |
| Core gate enforcement | `PASS` |
| Tools smoke tests | `Success` |
| Artifact-provenance binding | `Materialized and verified` |
| Artifact-binding attestation | `Created` |
| Completed release-grade reference run | `No` |

## Evidence and trace surfaces produced

The execution produced or preserved the applicable:

```text
status.json
report_card.html
release_authority_v0.json
release-authority audit bundle
release_decision_v0.json
artifact_provenance_binding_v0.json
GitHub artifact-binding attestation
workflow artifacts
GitHub job summary
```

These artifacts provide execution, decision-trace, binding, audit, and reader evidence.

They do not independently create release authority.

## Fail-closed release boundary

The workflow completed successfully while the generated release-decision sidecar remained:

```text
release level: FAIL
target: stage
run mode: core
```

The recorded blocking conditions included:

```text
detectors_materialized_ok was not literal true
stubbed diagnostics were present
scaffold diagnostics were present
```

This is not a contradiction.

```text
workflow SUCCESS
= the selected Core mechanics executed successfully

Core required gates PASS
= the declared Core gate set passed strict enforcement

release-decision sidecar FAIL
= broader stage or release-grade conditions were not satisfied
```

The run therefore demonstrates the fail-closed boundary rather than hiding it behind a green workflow surface.

```text
Core execution success
≠ stage release pass

Core execution success
≠ completed release-grade reference run
```

## What this execution proves

This public execution proves that the checked-in system can:

- execute the PULSE Core workflow from a concrete public commit;
- generate the Core status artifact;
- derive the Core required gate set from declared policy;
- enforce the exact Core gate set through `PULSE_safe_pack_v0/tools/check_gates.py`;
- pass all selected Core required gates;
- preserve the decision and audit surfaces;
- materialize and verify the artifact-provenance binding;
- create a GitHub attestation for the binding;
- retain a stricter release-level failure when broader conditions are absent.

## What this execution does not claim

This record does not claim:

- a non-stubbed release-grade candidate state;
- current-run cryptographically attested external detector evidence;
- release-required gate materialization from the recorded verifier;
- completion of the exact operational signer path;
- complete release-grade package verification;
- a stage or production release pass;
- completion of the public non-stubbed release-grade reference run.

Those remain later operational layers built on this functioning Core path.

## Authority boundary

The normative release-authority path remains:

```text
recorded release evidence
→ final status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ PULSE_safe_pack_v0/tools/check_gates.py
→ primary CI workflow
→ primary CI allow/block release decision
```

This document is a public execution record.

It is not:

- a policy;
- a gate;
- an authority carrier;
- an override;
- a release permission;
- a replacement for `status.json`;
- a replacement for `PULSE_safe_pack_v0/tools/check_gates.py`;
- a replacement for the completed release-grade reference run.

## External reading rule

The correct external reading is:

```text
PULSEmech Core execution
= publicly demonstrated

strict Core gate enforcement
= publicly demonstrated

artifact-provenance binding
= materialized and verified

artifact-binding attestation
= created

broader release conditions
= correctly remained fail-closed

completed non-stubbed release-grade reference run
= still pending
```

## Forward path

The further release-grade work now builds on a publicly demonstrated operational base:

```text
public Core execution record
→ exact operational signer identity
→ current-run external evidence
→ external-summary attestation and envelope
→ canonical candidate and verifier replay
→ verifier-bound release-required materialization
→ complete package verification
→ completed public release-grade reference run
```

The later layers extend this path.

They do not replace it.

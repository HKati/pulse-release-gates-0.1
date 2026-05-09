# PULSE Operator Handoff Release-Grade Contract v0

Status: operator handoff contract  
Scope: PULSE-REF RA0 / release-grade reconstruction path  
Authority: explanatory contract for `tools/operator_handoff_smoke.py`

## Core statement

Release-grade operator handoff must not treat an arbitrary status artifact as release-grade evidence.

A release-grade handoff may proceed only when the supplied status artifact is existing, explicit, non-stubbed, non-scaffolded, policy-consistent when policy metadata is declared, and able to pass declared-policy gate enforcement.

The operator handoff path is a reconstruction and verification surface.

It does not create release authority.

## Normative release-authority boundary

The normative release decision remains:

```text
recorded evidence
-> status.json
-> declared gate policy
-> materialized required gate set
-> strict gate checking
-> CI outcome
```

Operator handoff may reconstruct and verify that path.

It must not create a second release-decision engine.

## Release-grade handoff mode

Release-grade handoff uses:

```text
--gate-mode release-grade
--status-source existing
```

This means the status artifact must already exist and must represent archived or supplied release-grade evidence.

A generated Core artifact must not be substituted for release-grade evidence.

## Required preconditions

Release-grade operator handoff requires the following preconditions before gate materialization.

### Existing status source

Release-grade handoff requires:

```text
--status-source existing
```

This blocks the unsupported closure:

```text
generated Core status
-> treated as release-grade evidence
```

### Status artifact exists

The supplied status artifact must exist before handoff evaluation.

Missing existing status artifacts fail closed before gate materialization.

### Status artifact is a JSON object

The supplied status artifact must parse as a JSON object.

Malformed JSON or non-object JSON values fail closed before gate materialization.

### Status artifact digest traceability

The operator handoff report records SHA-256 digests for the supplied status artifact in the `status_source` block.

The recorded fields are:

```text
status_sha256_before_run
status_sha256_after_generation
status_sha256_after_run
```

For missing status artifacts, the digest value is null.

For generated Core handoff, the status artifact may be absent before generation and present after generation.

For existing release-grade handoff, the digest should remain stable across the handoff check unless the status artifact is intentionally rewritten by the selected path.

These digest fields bind the operator handoff report to the exact byte content of the status artifact used during reconstruction.

They are audit and traceability fields.

They do not create release authority, do not override gate policy, and do not create a second release-decision path.

### Prod run mode

Release-grade handoff requires:

```text
metrics.run_mode = "prod"
```

A Core or non-prod status artifact must not be treated as release-grade evidence merely because individual gate booleans appear to pass.

### Explicit non-stubbed status

Release-grade handoff requires:

```text
diagnostics.gates_stubbed = false
```

This value must be explicitly present and exactly false.

The following fail closed:

```text
diagnostics.gates_stubbed = true
diagnostics.gates_stubbed missing
diagnostics.gates_stubbed = null
diagnostics.gates_stubbed = "false"
```

The absence of a stubbed flag is not release-grade evidence.

### No scaffold marker

Release-grade handoff rejects:

```text
diagnostics.scaffold = true
```

Scaffolded status artifacts must not enter release-grade gate materialization.

### No stub profile marker

Release-grade handoff rejects any present:

```text
diagnostics.stub_profile
```

Stub-profiled status artifacts must not be treated as release-grade evidence.

### Declared policy hash consistency

If the status artifact declares:

```text
metrics.gate_policy_sha256
```

then the value must match the SHA-256 of the current declared gate policy:

```text
pulse_gate_policy_v0.yml
```

A stale or mismatched declared policy hash fails closed before gate materialization.

This field is not made mandatory by this contract version.

The rule is:

```text
if declared, it must match
```

### Declared policy path consistency

If the status artifact declares:

```text
metrics.gate_policy_path
```

then the value must match:

```text
pulse_gate_policy_v0.yml
```

A stale or mismatched declared policy path fails closed before gate materialization.

This field is not made mandatory by this contract version.

The rule is:

```text
if declared, it must match
```

## Gate materialization

After preconditions pass, release-grade handoff materializes:

```text
gates.required
gates.release_required
```

from the declared gate policy.

The effective required gate set is the ordered union of those two sets.

An empty materialized gate set is invalid and fails closed.

## Strict gate checking

After gate-set materialization, release-grade handoff invokes strict gate checking over the effective required gate set.

The following fail closed:

```text
required gate missing
required gate false
release_required gate missing
release_required gate false
```

Release-grade shape is not sufficient.

A status artifact may have correct run mode, non-stubbed diagnostics, matching policy metadata, and still fail release-grade handoff if a declared required gate is missing or false.

## External evidence boundaries

Release-grade handoff must fail closed when release-required external evidence gates fail.

Examples include:

```text
external_summaries_present = false
external_all_pass = false
```

Malformed, unsigned, missing, or otherwise failing external evidence must not become release authority.

## Refusal-delta evidence boundary

Release-grade handoff must fail closed when refusal-delta evidence presence is missing.

For example:

```text
refusal_delta_pass = true
refusal_delta_evidence_present = false
-> release-grade FAIL
```

A passing refusal-delta decision is not release-authority sufficient unless the corresponding evidence-presence gate is also materialized and true.

## Core artifact substitution boundary

Core baseline artifacts and generated Core status artifacts must not be accepted as release-grade handoff evidence.

This blocks the unsupported closure:

```text
Core smoke artifact
-> release-grade status evidence
```

Core artifacts may be useful for smoke testing and local checks.

They are not release-grade evidence.

## Relation to pre-materialization gate mechanics

Operator handoff release-grade checks are an instance of pre-materialization gate mechanics.

The handoff path blocks unsupported release-grade authority before the supplied status artifact can enter gate materialization and strict release-grade checking.

See:

```text
docs/PULSE_PRE_MATERIALIZATION_GATE_MECHANICS_v0.md
```

## Non-authoritative surfaces

Operator handoff reports, tests, fixtures, docs, ledgers, dashboards, manifests, summaries, and audit bundles do not create release authority.

They may preserve, explain, reconstruct, or verify release state.

The release decision remains bound to declared-policy gate enforcement and CI-recorded outcome.

## Current implementation surface

The current operator handoff smoke tool is:

```text
tools/operator_handoff_smoke.py
```

The regression coverage is:

```text
tests/test_operator_handoff_smoke.py
```

The gate policy helper is:

```text
tools/policy_to_require_args.py
```

Strict gate checking is performed by:

```text
PULSE_safe_pack_v0/tools/check_gates.py
```

## Summary

Release-grade operator handoff accepts only existing, explicit, non-stubbed, non-scaffolded, policy-consistent release-grade status evidence that passes declared-policy gate enforcement.

It fails closed before gate materialization when release-grade preconditions are not satisfied.

It fails closed during strict gate checking when any required or release-required gate is missing or false.

Operator handoff reconstructs and verifies release authority.

It does not create release authority.

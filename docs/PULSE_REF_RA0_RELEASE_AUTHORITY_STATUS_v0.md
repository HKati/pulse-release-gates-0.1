# PULSE-REF RA0 Release-Authority Status v0

Status: RA0 milestone record  
Scope: PULSE-REF release-authority reconstruction / handoff boundary  
Authority: documentation-only status record  
Date: 2026-05-09

## Core statement

PULSE-REF RA0 establishes a release-grade reconstruction boundary for PULSE.

The RA0 work does not create a second release-decision engine.

It hardens the existing PULSE release-authority model:

```text
recorded evidence
-> status.json
-> declared gate policy
-> materialized required gate set
-> strict gate checking
-> CI outcome
```

The normative release decision remains produced by declared-policy gate enforcement and recorded through CI outcome.

Ledgers, manifests, audit bundles, dashboards, summaries, fixtures, documentation, publication surfaces, and operator handoff reports may preserve, explain, reconstruct, or verify release state.

They do not create release authority.

## RA0 purpose

The purpose of RA0 is to convert the existing PULSE release-authority mechanism into a stronger PULSE-REF release-authority reference path.

RA0 focuses on:

- release-grade evidence presence;
- no implicit PASS from missing evidence;
- external evidence schema and envelope validation;
- verification-before-fold-in;
- release-reference fixture matrices;
- release-required policy promotion for refusal-delta evidence presence;
- release-grade operator handoff reconstruction;
- pre-materialization blocking of unsupported release closure;
- status artifact digest traceability.

RA0 is not the final HPC-scale run protocol.

RA0 is the foundation that makes the next HPC/reference-run phase meaningful.

## Completed RA0 components

### External summary schema layer

RA0 includes a canonical external summary schema layer.

Implemented surfaces include:

```text
schemas/external_summary_v1.schema.json
schemas/external_summary_envelope_v1.schema.json
policy/external_signers_v1.yml
tests/test_external_summary_schema_v1.py
docs/external_summary_schema_v1.md
```

The external summary schema layer defines the shape of external detector / evaluator / review evidence before it can participate in release-grade reasoning.

### External envelope verification-before-fold-in

RA0 includes the verification-before-fold-in rule.

The envelope layer enforces the core safety condition:

```text
policy_context.fold_in_allowed = true
=> verification.verified must be true
```

The negative / positive envelope fixtures demonstrate both sides:

```text
verification.verified=false
policy_context.fold_in_allowed=true
-> FAIL

verification.verified=false
policy_context.fold_in_allowed=false
policy_context.release_contribution=diagnostic
-> PASS
```

This preserves the boundary between diagnostic evidence and release-contributing evidence.

### External summary fixture matrices

RA0 includes external summary and envelope fixture matrices.

The external summary matrix isolates schema failure modes such as:

```text
missing tool.version
missing subject.digest
bad SHA-256 subject.digest
metrics = []
missing authority_boundary
```

The envelope matrix isolates envelope failure modes such as:

```text
missing summary digest
missing signing identity
missing verifier identity
unverified fold-in allowed
```

The fixture matrices prevent broad / ambiguous validation failures from being mistaken for targeted evidence behavior.

### Release-reference fixture matrix

RA0 includes a release-reference fixture matrix under:

```text
tests/fixtures/release_reference_v1/
```

The matrix exercises release-grade status outcomes, including:

```text
pass
missing_external
stubbed
malformed_summary
unsigned_summary
false_gate
publication_mismatch
implicit_fallback_attempt
agent_diagnostic_promoted
missing_refusal_delta
refusal_delta_evidence_present
```

The release-reference matrix protects the expected behavior:

```text
PASS fixture -> guard PASS
FAIL fixture -> guard FAIL
FAIL fixture -> only declared failure target may fail
```

### External evidence integration

RA0 integrates lower-level external evidence failure modes into the release-reference layer.

The following release-reference fixtures connect external evidence failures to release-grade outcome:

```text
malformed_summary
unsigned_summary
```

Both isolate the release-reference failure target:

```text
external_all_pass = false
```

This prevents malformed or unsigned external evidence from becoming release-grade authority.

### Evidence presence / no implicit PASS

RA0 includes explicit no-implicit-PASS hardening for refusal-delta evidence.

The core rule is:

```text
release-grade paths must not infer PASS from missing evidence
```

A passing refusal-delta decision is not sufficient unless the corresponding evidence-presence gate is materialized and true.

The negative fixture proves:

```text
refusal_delta_pass = true
refusal_delta_evidence_present = false
-> release-grade FAIL
```

The positive fixture proves:

```text
refusal_delta_pass = true
refusal_delta_evidence_present = true
-> release-grade PASS
```

### Refusal-delta evidence presence promotion

RA0 promotes refusal-delta evidence presence into the release-required path.

The promoted gate is:

```text
refusal_delta_evidence_present
```

The promotion was completed only after the stack was prepared:

```text
producer materialization
run_all default gate materialization
gate registry entry
policy release_required promotion
hardcoded release-required test readiness
core baseline alignment
```

The promotion preserves the PULSE release-authority model.

It does not create a second decision path.

### Operator handoff release-grade reconstruction

RA0 establishes a release-grade operator handoff reconstruction path.

The operator handoff tool is:

```text
tools/operator_handoff_smoke.py
```

The regression coverage is:

```text
tests/test_operator_handoff_smoke.py
```

The handoff path reconstructs release-grade checking from an existing status artifact.

It does not create release authority.

## Operator handoff preconditions

Release-grade operator handoff requires:

```text
--gate-mode release-grade
--status-source existing
```

Generated Core artifacts must not be treated as release-grade evidence.

Before gate materialization, release-grade handoff rejects unsupported status artifacts.

### Existing status artifact

The supplied status artifact must exist.

Missing existing status fails closed before gate materialization.

### JSON object status

The supplied status artifact must parse as a JSON object.

Malformed JSON or non-object JSON values fail closed before gate materialization.

### Prod run mode

Release-grade handoff requires:

```text
metrics.run_mode = "prod"
```

Core or non-prod artifacts must not be treated as release-grade evidence merely because individual gate booleans appear to pass.

### Explicit non-stubbed diagnostic

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

### No scaffold marker

Release-grade handoff rejects:

```text
diagnostics.scaffold = true
```

Scaffolded status evidence must not be treated as release-grade evidence.

### No stub profile marker

Release-grade handoff rejects any present:

```text
diagnostics.stub_profile
```

Stub-profiled status evidence must not be treated as release-grade evidence.

### Optional policy hash consistency

If the status artifact declares:

```text
metrics.gate_policy_sha256
```

then the value must match the SHA-256 of:

```text
pulse_gate_policy_v0.yml
```

This field is not mandatory in RA0.

The rule is:

```text
if declared, it must match
```

### Optional policy path consistency

If the status artifact declares:

```text
metrics.gate_policy_path
```

then the value must match:

```text
pulse_gate_policy_v0.yml
```

This field is not mandatory in RA0.

The rule is:

```text
if declared, it must match
```

## Operator handoff gate enforcement

After preconditions pass, release-grade operator handoff materializes:

```text
gates.required
gates.release_required
```

from the declared gate policy.

The effective required gate set is the ordered union of those sets.

Release-grade handoff then invokes strict gate checking.

The following fail closed:

```text
required gate missing
required gate false
release_required gate missing
release_required gate false
```

Release-grade shape is not sufficient.

A status artifact may satisfy preconditions and still fail release-grade handoff if any declared required gate is missing or false.

## Status digest traceability

RA0 adds status artifact digest traceability to the operator handoff report.

The `status_source` block records:

```text
status_sha256_before_run
status_sha256_after_generation
status_sha256_after_run
```

For missing status artifacts, digest values are null.

For generated Core handoff, the status may be absent before generation and present after generation.

For existing release-grade handoff, the status digest should remain stable across generation and handoff checking unless the selected path intentionally rewrites the artifact.

These digest fields bind the handoff report to the exact byte content of the status artifact used during reconstruction.

They are audit and traceability fields only.

They do not create release authority, do not override gate policy, and do not create a second release-decision path.

## Pre-materialization gate mechanics

RA0 is an applied instance of PULSE pre-materialization gate mechanics.

The handoff path blocks unsupported release-grade authority before an invalid status artifact can enter gate materialization.

Examples of blocked unsupported closure:

```text
generated Core status -> release-grade evidence
missing evidence -> implicit PASS
stubbed status -> release-grade evidence
scaffold status -> release-grade evidence
stale policy metadata -> release-grade evidence
malformed external summary -> release-grade evidence
unsigned external summary -> release-grade evidence
diagnostic artifact -> release authority
```

PULSE does not wait for unsupported release authority to materialize and then explain the failure.

It blocks unsupported closure before release-grade decision materialization.

See:

```text
docs/PULSE_PRE_MATERIALIZATION_GATE_MECHANICS_v0.md
```

## Current authority boundary

RA0 preserves the PULSE authority boundary.

Normative:

```text
recorded evidence
status.json
declared gate policy
materialized required gate set
check_gates.py / CI enforcement
CI outcome
```

Non-normative / audit / preservation / reconstruction:

```text
operator handoff reports
release authority manifests
audit bundles
Quality Ledger
dashboards
summaries
fixtures
documentation
publication surfaces
external summaries before policy-controlled fold-in
```

These surfaces may support verification, preservation, or reconstruction.

They do not authorize release independently.

## What RA0 does not claim

RA0 does not yet claim full HPC-scale readiness.

RA0 does not yet provide a complete repeated-run HPC protocol.

RA0 does not yet bind every operator handoff report into a release authority manifest or audit bundle.

RA0 does not yet define a complete batch-run artifact layout for large-scale evaluation.

RA0 does not yet make policy hash/path metadata mandatory for every release-reference fixture.

RA0 does not yet claim that all detector pipelines are non-truncated production detectors.

RA0 establishes the release-authority reconstruction boundary needed for those future phases.

## Remaining work after RA0

The next phase should connect RA0 handoff reconstruction to externally verifiable release-reference packages.

Expected next work packages:

```text
RA0 release-reference package layout
operator handoff report digest binding into manifest
release authority manifest linkage
audit bundle linkage
atomic publication snapshot linkage
HPC run directory protocol
repeated run metadata
environment / compute metadata capture
detector artifact digest capture
non-truncated reference run protocol
external verifier instructions
```

## Suggested next milestone

The next milestone after this RA0 status record is:

```text
PULSE-REF RA1: externally verifiable release-reference package
```

RA1 should bind:

```text
status.json
pulse_gate_policy_v0.yml
materialized required gate sets
operator handoff report
release authority manifest
audit bundle
CI outcome
publication snapshot
```

into a single externally verifiable package.

## Summary

PULSE-REF RA0 establishes the release-grade reconstruction boundary.

It hardens the PULSE release-authority path without changing the normative decision engine.

It proves that release-grade handoff must use existing, explicit, non-stubbed, non-scaffolded, policy-consistent status evidence and strict declared-policy gate enforcement.

It records status artifact digests for audit traceability.

It preserves the authority boundary:

```text
release authority is produced by declared-policy gate enforcement and CI outcome,
not by handoff reports, ledgers, manifests, dashboards, fixtures, summaries, docs, or publication surfaces.
```

RA0 is therefore a release-authority milestone, not a cosmetic documentation phase.

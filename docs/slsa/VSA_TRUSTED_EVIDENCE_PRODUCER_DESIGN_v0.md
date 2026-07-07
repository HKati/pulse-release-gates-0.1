# PULSE SLSA VSA — trusted evidence producer design v0

## WORKMARK

Status: design document only.

This document defines the trusted evidence producer design required before any future SLSA VSA recorded-intake lane can be promoted from non-active candidate proof to active release-required enforcement.

This document does not implement the producer.

This document does not activate SLSA VSA as release-required.

## Current state

The SLSA VSA recorded-intake candidate path is complete and proven.

Completed sequence:

```text
#2689 — register non-active slsa_vsa_recorded_intake_candidate
#2690 — allow declared gate-set materialization
#2691 — prove recorded-intake candidate path
```

Boundary and criteria documents:

```text
docs/slsa/VSA_RELEASE_REQUIRED_PROMOTION_BOUNDARY_v0.md
docs/slsa/VSA_RELEASE_REQUIRED_PROMOTION_CRITERIA_v0.md
```

Current state remains:

```text
non-active candidate proof complete
release-required promotion not yet performed
trusted evidence producer not yet implemented
```

## Purpose

The trusted evidence producer is the component or CI step that will later be allowed to supply SLSA VSA evidence for release-required enforcement.

The producer must transform auditable release-candidate inputs into recorded VSA evidence that can be checked through the existing intake and fold-in path.

The accepted path must remain:

```text
trusted producer inputs
→ recorded SLSA VSA evidence
→ ingest_slsa_vsa_evidence_v0.py
→ intake report
→ fold_slsa_vsa_intake_into_status_v0.py
→ status.gates
→ policy_to_require_args.py
→ check_gates.py
```

## Non-activation rule

A trusted evidence producer design is not release-required activation.

This document does not add SLSA VSA gates to:

```text
required
core_required
release_required
prod_required
stage_required
blocking
release_blocking
```

Any future activation must remain a separate PR.

## Producer identity

A future implementation must give the producer an explicit identity.

The identity must include at least:

```text
producer_id
producer_name
producer_version
producer_source
ci_workflow_or_job_identity
```

The producer identity must be recorded in the evidence or in a directly associated producer report.

A missing producer identity must fail closed.

An unknown producer identity must fail closed.

A producer identity that does not match the expected CI context must fail closed.

## Accepted producer inputs

A future producer must use explicit inputs.

Expected inputs include:

```text
release artifact subject name
release artifact digest
release candidate identifier
current run identifier
current commit SHA
expected policy identity
expected policy digest
trusted verifier identity
VSA evidence source
evidence timestamp or evidence epoch
```

Inputs must not be inferred from mutable README text, issue comments, PR body text, or manually copied status booleans.

## Current-run binding

The producer must bind accepted evidence to the current run, release candidate, or explicitly declared evidence epoch.

A future implementation must reject:

```text
previous-run VSA artifact reuse
stale VSA evidence
VSA timeVerified/current-run mismatch
VSA produced for a different release candidate
VSA produced for a different commit SHA
VSA produced for a different artifact digest
```

A fresh intake report generated from stale VSA evidence must not be sufficient.

Freshness must be checked at the VSA evidence level, not only at the derived intake-report level.

## Artifact binding

The producer must bind the VSA subject to the release artifact under evaluation.

Required artifact binding fields:

```text
subject.name
subject.digest.sha256
resourceUri
release artifact digest
release candidate identifier
```

The following must fail closed:

```text
missing subject
missing subject digest
subject digest mismatch
resourceUri mismatch
release candidate mismatch
artifact digest mismatch
```

## Policy digest binding

The producer must bind accepted VSA evidence to the expected policy identity and the expected policy digest.

Policy URI or policy identity alone is not sufficient.

The following must fail closed:

```text
missing policy digest
stale policy digest
unexpected policy digest
policy URI-only binding
policy identity with omitted digest
policy identity with replaced-policy digest
policy digest mismatch
```

The intended gate for this binding remains:

```text
slsa_vsa_policy_digest_matches
```

## Verifier trust boundary

The producer must record or preserve the trusted verifier identity.

The verifier identity must match the expected verifier for the release-required lane.

The following must fail closed:

```text
missing verifier identity
unknown verifier identity
unexpected verifier identity
verifier identity mismatch
```

The intended gate for this binding remains:

```text
slsa_vsa_verifier_trusted
```

## Recorded signal boundary

The current SLSA VSA intake path uses:

```text
recorded_signal_only
```

This means the path records and checks supplied signal values, but it is not yet a cryptographic signature verification lane.

A future producer implementation must explicitly state whether it still uses:

```text
recorded_signal_only
```

or introduces a stronger verification mode.

If it still uses `recorded_signal_only`, the producer must be trusted enough to support release blocking, and that trust boundary must be documented in the implementation PR.

## Anti-self-declared-boolean rule

The producer must not create release-required SLSA VSA gates by directly writing booleans into `status.json`.

The producer may emit recorded evidence.

The existing intake and fold-in path may derive gates from that recorded evidence.

The allowed path is:

```text
recorded VSA evidence
→ intake report
→ validated checks
→ folded status.gates
```

The forbidden path is:

```text
manual boolean
→ status.json
→ release-required PASS
```

## Accepted evidence packet shape

A future implementation should produce or consume a self-contained evidence packet.

Expected packet contents:

```text
slsa_vsa_evidence.json
producer_report.json
artifact_subject.json
policy_digest_record.json
verifier_identity_record.json
run_binding_record.json
```

The exact schema may be introduced in a future PR.

This design document does not define a normative schema.

## Producer report

A future producer should emit a deterministic producer report.

Expected report fields:

```text
producer_id
producer_version
ok
run_id
commit_sha
release_candidate_id
artifact_subject_name
artifact_subject_sha256
expected_policy_id
expected_policy_sha256
verifier_id
evidence_path
evidence_sha256
time_verified
freshness_result
errors
```

A producer report with `ok != true` must not be allowed to feed release-required SLSA VSA gates.

## Rejection cases

A future trusted producer implementation must reject at least:

```text
missing VSA evidence
invalid VSA evidence
stale VSA evidence
previous-run VSA artifact reuse
VSA timeVerified/current-run mismatch
missing artifact subject
artifact subject digest mismatch
resource URI mismatch
missing policy digest
policy URI-only binding
policy digest mismatch
missing verifier identity
unknown verifier identity
verificationResult != PASSED
missing verified level
manual status boolean input
self-declared local status patch
ambiguous artifact reuse
```

## Audit outputs

A future implementation must make the evidence path auditable.

Audit outputs should make it possible to answer:

```text
who produced the evidence
which run produced or accepted it
which artifact it binds to
which policy digest it binds to
which verifier identity was trusted
which checks passed
which checks failed
why release-required enforcement was allowed or blocked
```

Audit outputs must not rely on hidden CI state only.

They should be persisted as artifacts or deterministic reports.

## Fail-closed rule

The producer must fail closed for missing, stale, mismatched, ambiguous, or unverifiable evidence.

Fail-closed means:

```text
do not materialize release-required SLSA VSA PASS gates
do not allow release authority to treat the lane as passing
emit a deterministic diagnostic report
preserve enough context for audit
```

## Interaction with existing tools

The producer design must preserve existing tool boundaries.

The future producer may feed:

```text
tools/ingest_slsa_vsa_evidence_v0.py
```

The future producer must not require `check_gates.py` to know SLSA VSA gate names.

The existing generic checker must remain generic:

```text
PULSE_safe_pack_v0/tools/check_gates.py
```

The producer must not bypass:

```text
tools/fold_slsa_vsa_intake_into_status_v0.py
```

unless a future PR explicitly replaces the fold-in contract and proves equivalent fail-closed behavior.

## Expected future implementation PR

A future implementation PR may introduce:

```text
tools/build_slsa_vsa_trusted_evidence_producer_report_v0.py
schemas/slsa_vsa_trusted_evidence_producer_report_v0.schema.json
examples/slsa/slsa_vsa_trusted_evidence_producer_report_example_v0.json
tests/test_slsa_vsa_trusted_evidence_producer_report_v0.py
```

The exact file names may change, but the implementation should remain small and focused.

## Expected future CI integration PR

A future CI integration PR may introduce a workflow step that produces or verifies the trusted producer report.

That PR must remain separate from active release-required promotion unless the promotion criteria are explicitly satisfied and tested.

## Required tests before producer implementation is considered complete

A future producer implementation must test:

```text
valid producer report passes
missing producer identity fails closed
unknown producer identity fails closed
missing artifact digest fails closed
artifact digest mismatch fails closed
missing policy digest fails closed
policy URI-only binding fails closed
policy digest mismatch fails closed
stale VSA evidence fails closed
previous-run VSA artifact reuse fails closed
VSA timeVerified/current-run mismatch fails closed
manual status boolean input fails closed
self-declared local status patch fails closed
producer report ok=false fails closed
```

## Required tests before release-required promotion

A future release-required promotion must additionally test:

```text
active policy materialization includes promoted SLSA VSA gates
valid trusted producer evidence passes the active lane
missing trusted producer evidence fails closed
stale trusted producer evidence fails closed
mismatched trusted producer evidence fails closed
check_gates.py remains generic
candidate proof still passes
rollback removes active release-required SLSA VSA gates without deleting candidate history
```

## Forbidden bundling

Do not combine trusted producer design or implementation with unrelated work.

Do not bundle with:

```text
DOI changes
Zenodo changes
CITATION changes
README title changes
unrelated workflow cleanup
unrelated registry expansion
unrelated release packaging
```

## Current non-activation statement

At the time of this document, SLSA VSA is not active as:

```text
required
core_required
release_required
prod_required
stage_required
blocking
release_blocking
```

The current state remains:

```text
non-active candidate proof complete
promotion boundary documented
promotion criteria documented
trusted producer design documented
release-required promotion not yet performed
```

# PULSE release-grade next run plan v0

## Document status

```text
document_role: current_operational_execution_plan
target: first_completed_public_non_stubbed_release_grade_run
normative_release_authority: false
current_run_completed: false
```

This document defines the remaining operational work required to produce the first completed public, non-stubbed, non-scaffolded PULSE release-grade reference run.

It does not redesign the existing release-authority mechanism.

It does not reopen already implemented verifier, replay, materializer, or gate-enforcement layers.

The plan begins from the current checked-in implementation and moves forward from that state.

## Purpose

The next PULSE proof state is not another fixture, smoke surface, dashboard, or documentation-only claim.

The target is one controlled release-grade execution that materializes the complete evidence-to-decision path from current-run evidence and preserves a complete, independently reviewable artifact package.

The target path is:

```text
current-run release evidence
→ non-stubbed candidate release state
→ canonical candidate production
→ canonical candidate replay
→ recorded release-evidence verification
→ canonical verifier replay
→ policy-derived release-required gate materialization
→ final status.json
→ workflow-effective materialized required gate set
→ PULSE_safe_pack_v0/tools/check_gates.py
→ primary CI allow/block release decision
→ complete reference package
→ completed public run record
```

## Source-of-truth documents

The current mechanical boundaries are defined by:

```text
docs/release_grade_reference_run_v0.md
docs/recorded_release_evidence_verifier_v0.md
docs/release_reference_external_evidence_integration_v1.md
docs/RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md
```

This plan must remain consistent with those documents.

If implementation changes during the work, the implementation and its tests remain the primary mechanical source of truth.

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

The following do not independently create release authority:

- external summaries;
- external-summary envelopes;
- signer policies;
- attestation bundles;
- attestation-verifier reports;
- candidate envelopes;
- candidate indexes;
- input manifests;
- recorded verifier reports;
- canonical replay results;
- admissibility maps;
- qualification results;
- release-decision sidecars;
- provenance bindings;
- release-authority manifests;
- Quality Ledger;
- audit bundles;
- reference packages;
- reference-run notes;
- dashboards;
- Pages;
- publication surfaces.

They may produce, preserve, verify, bind, reconstruct, explain, or publish evidence.

They may not independently authorize, block, override, or reinterpret release.

## Current implementation state

### Implemented

The following mechanics are already implemented:

```text
current-run required-gate evaluation
required_gate_evidence_v0 production
non-stubbed prod candidate status production
status_baseline.json preservation
canonical recorded-release candidate production
canonical candidate replay
release-evidence input-manifest production
input-manifest schema checker
recorded release-evidence verification
relation-binding verification
manifest-declared per-gate admissibility
canonical verifier replay in the materializer
complete policy-gate coverage in the materializer
atomic release-required materialization
external-summary schema validation
external-summary semantic validation
external-summary envelope validation
exact signer-matching logic
wildcard signer rejection
GitHub attestation verification capability
strict final gate enforcement
release decision artifact production
artifact provenance binding
release-authority manifest production
Quality Ledger rendering and parity checking
advisory release-grade subset qualification
baseline reference-bundle assembly
```

These layers must not be rebuilt merely because the first public run has not yet been executed.

### Pending

The remaining operational gaps are:

```text
exact operational workflow identity
current-run external-evidence producer lane
current-run raw external evidence
current-run canonical external summary
real GitHub attestation bundle
current-run canonical external-summary envelope
complete evidence-chain reference packaging
independent complete-package verification
controlled strict release-grade execution
completed public reference-run record
```

## Mechanical rule

The next work must extend the standing implementation.

It must not replace working layers with parallel implementations.

```text
implemented verifier
→ keep

implemented materializer
→ keep

implemented final gate checker
→ keep

missing operational inputs and package path
→ add
```

Any change to an already standing decision layer requires a concrete implementation defect demonstrated by a failing test or controlled run.

---

## Target proof state

The completed run must prove all of the following in one connected run identity:

1. required-gate evidence was produced from the current run;
2. the candidate release state was non-stubbed and non-scaffolded;
3. one or more canonical external summaries were produced from current-run raw evidence;
4. every admitted external summary was signed or attested by one exact allowed workflow identity;
5. each summary had a canonical verification envelope;
6. each attestation bundle passed cryptographic GitHub verification;
7. canonical candidate production admitted the external evidence;
8. canonical candidate replay reproduced the supplied candidate set;
9. recorded release-evidence verification succeeded;
10. canonical verifier replay matched the supplied verifier report;
11. every policy-derived release-required gate had a verified admissibility entry;
12. release-required materialization succeeded atomically;
13. final `status.json` validated;
14. the exact workflow-effective materialized required gate set was enforced;
15. the primary CI workflow recorded an allow or block result;
16. decision, provenance, manifest, Ledger, and audit artifacts were produced;
17. the complete evidence-chain package was assembled;
18. complete-package presence and binding were independently verified;
19. concrete run identity, artifact references, and digests were recorded publicly.

A run that satisfies only the advisory qualification checker is not complete.

A run that uploads only the baseline reference bundle is not complete.

---

## Controlled run strategy

The first reference run should use:

```text
workflow_dispatch
strict_external_evidence = true
```

This provides a controlled release-grade execution without requiring the first attempt to create a version tag.

A version tag should not be used merely to force the path to run.

The first version-tagged reference should be created only after the controlled workflow-dispatch path has already demonstrated the complete package successfully.

## No manual evidence insertion

The completed reference run must not depend on:

- manually edited generated JSON;
- copied fixture outputs;
- a previously generated external summary;
- a previously generated attestation bundle;
- a manually changed gate value;
- a manually changed verifier report;
- a manually completed run note presented as runtime proof;
- evidence from another run ID or run attempt.

Every release-grade evidence artifact must be produced, bound, or independently verified inside the controlled current-run path.

## One run identity

The complete chain must preserve one current-run identity.

At minimum:

```text
repository
git_sha
workflow path
workflow run ID
workflow run attempt
run_key
run_mode
release candidate
created_utc
policy path
policy digest
registry path
registry digest
```

The same identity must be preserved across:

- required-gate evidence;
- candidate status;
- candidate envelopes;
- candidate index;
- input manifest;
- verifier report;
- final status;
- release decision;
- provenance binding;
- release-authority manifest;
- complete package;
- public run note.

Cross-run evidence mixing is forbidden.

---

## Minimal external detector scope

The first controlled run should use the smallest external detector scope that proves the complete attested path.

Select one supported detector before implementing the producer lane.

Current supported detector identities include:

```text
llamaguard
promptguard
garak
azure_eval
promptfoo
deepeval
```

Selection criteria:

- deterministic or reproducible execution;
- manageable runtime;
- no unnecessary long-lived secret;
- current-run raw output can be archived;
- canonical metric is already supported;
- canonical threshold exists;
- output can be transformed into `external_summary_v1`;
- failure can be reproduced locally or in tests.

The selected detector must be recorded explicitly in the implementation PR and run note.

The first run does not need to execute every supported detector.

The current policy:

```text
external_overall_policy = all
```

means that every discovered summary must pass.

It does not by itself require that every supported detector be present.

## External-directory hygiene

Before the current-run external producer writes outputs, the workflow must clear stale producer outputs from the canonical external-evidence path.

The run must not accidentally discover:

- a summary from an earlier run;
- a raw-evidence file from an earlier run;
- an envelope from an earlier run;
- an attestation bundle from an earlier run;
- both JSON and JSONL summaries for the same detector;
- a fixture copied into the runtime artifact directory.

The producer lane must recreate the complete selected-detector set from current-run inputs.

---

# Work package 1 — establish the exact operational signer

## Goal

Introduce one exact GitHub Actions workflow identity that can produce and attest the current-run external summary.

## Current blocker

The checked-in signer policy contains deferred wildcard patterns.

The implemented verifier rejects wildcard release-grade signer identities.

Adding one exact entry beside reachable wildcard entries is not sufficient if the verifier still encounters the wildcard entries in identity groups allowed for the selected detector.

## Required result

For the selected detector, every signer-identity group reachable through:

```text
tool_policies.<detector>.allowed_identity_groups
```

must be mechanically safe.

The release-grade path must contain one exact admitted identity of the form:

```text
repo:HKati/pulse-release-gates-0.1:workflow:<exact-workflow-path>
```

The workflow path must identify the actual checked-in workflow producing the attestation.

## Identity-selection rule

Do not infer the signer identity from a display name.

Use the exact workflow identity reported by the GitHub attestation contract.

The implementation must prove:

```text
declared policy identity
= envelope signing identity
= attestation signer workflow
= verifier-derived workflow identity
```

## Policy cleanup

The implementation PR must either:

- replace the wildcard entries reachable by the selected release-grade tool; or
- remove wildcard-containing identity groups from that tool's allowed release-grade groups.

Do not retain a wildcard path that still participates in the selected tool's release-grade policy evaluation.

## Required tests

Tests must cover:

- exact identity accepted;
- wildcard identity rejected;
- wrong repository rejected;
- wrong workflow rejected;
- wrong signing mode rejected;
- wrong release contribution rejected;
- identity present only in a disallowed group rejected;
- exact identity plus a still-reachable wildcard remains rejected.

## Completion condition

This work package is complete only when the selected tool has one operational exact identity and no reachable wildcard identity can poison release-grade verification.

---

# Work package 2 — add the current-run external-evidence producer lane

## Goal

Generate current-run raw evidence and one canonical external summary from the selected detector.

## Required producer outputs

The producer lane must create:

```text
PULSE_safe_pack_v0/artifacts/external/<raw-evidence-file>
PULSE_safe_pack_v0/artifacts/external/<detector>_summary.json
```

The output must be created from the current workflow execution.

## Raw evidence

The raw-evidence artifact must:

- be a regular file;
- be non-symlink;
- remain inside the canonical external directory;
- contain the evaluator's current-run output;
- be deterministic where possible;
- be hashable;
- be referenced by the summary;
- remain distinct from the summary itself.

## Canonical summary

The producer must write a valid:

```text
external_summary_v1
```

JSON object.

It must bind:

```text
tool identity
tool version
current run key
current release candidate
current repository
current commit
dataset digest
evaluator digest
subject digest
canonical metric
canonical threshold
raw-evidence path
raw-evidence digest
signing context
aggregate pass state
required release contribution
authority boundary
```

## Current-run requirement

The producer must not read a checked-in passing summary fixture as its runtime result.

Fixtures may remain test inputs.

The runtime summary must be generated from the current-run evaluator output.

## Producer failure behavior

The producer must fail closed on:

- evaluator failure;
- missing raw output;
- malformed raw output;
- unsupported detector identity;
- missing canonical metric;
- missing threshold;
- threshold violation;
- missing dataset digest;
- missing evaluator digest;
- wrong run identity;
- wrong release-candidate identity;
- raw-evidence path escape;
- raw-evidence digest failure;
- summary schema failure.

## Initial integration boundary

The producer lane may first be introduced as a non-authorizing artifact producer.

It must not set release-required gates directly.

Release-required state remains dependent on canonical candidate production, replay, recorded verification, materialization, and final enforcement.

---

# Work package 3 — create the attestation bundle and canonical envelope

## Goal

Cryptographically bind the current-run canonical summary to the exact workflow identity and current source commit.

## Required outputs

```text
PULSE_safe_pack_v0/artifacts/external/<detector>_summary.json
PULSE_safe_pack_v0/artifacts/external/<detector>_summary.envelope.json
PULSE_safe_pack_v0/artifacts/external/<attestation-bundle-file>
```

## Attestation subject

The attested subject must be the exact canonical summary file used by candidate production.

Do not attest:

- the raw evidence instead of the summary;
- a copied summary;
- a temporary summary that later changes;
- a directory containing multiple summaries;
- a package created after the candidate path.

## Attestation contract

The attestation must be verifiable against:

```text
expected repository
exact signer workflow
current source commit
SLSA provenance v1 predicate
GitHub Actions OIDC issuer
```

The bundle must be persisted at the exact path recorded by:

```text
envelope.signing.bundle_uri
```

## Canonical envelope

The envelope must bind:

```text
summary path
summary ID
summary schema version
summary SHA-256
signing mode
exact signing identity
attestation bundle URI
verification state
verifier identity
canonical signer-policy path
canonical threshold-policy path
release contribution
fold-in eligibility
authority boundary
```

## Generation order

The mechanical order must be:

```text
raw evidence
→ canonical summary
→ final summary digest
→ attestation
→ persisted attestation bundle
→ canonical envelope
→ attestation verification
```

Do not create the envelope before the final summary digest and bundle path are known.

## Verifier proof

The lane must run:

```text
PULSE_safe_pack_v0/tools/check_external_summary_attestation_v1.py
```

or the exact in-process equivalent used by canonical candidate production.

The verifier result must be:

```text
status = verified
errors = []
```

## Failure behavior

The lane must fail closed on:

- missing bundle;
- malformed envelope;
- summary-reference mismatch;
- summary-ID mismatch;
- summary-digest mismatch;
- summary/envelope signing mismatch;
- wildcard signer identity;
- wrong signer workflow;
- wrong repository;
- wrong source commit;
- wrong predicate type;
- wrong OIDC issuer;
- unsupported signing mode;
- failed or empty `gh attestation verify` result.

---

# Work package 4 — execute the existing candidate, verifier, and materializer path

## Goal

Use the current-run attested external evidence without bypassing the standing release-grade implementation.

## Required sequence

```text
current-run required-gate evidence
→ candidate status
→ status_baseline.json
→ canonical recorded-release candidates
→ recorded candidate index
→ release-evidence input manifest
→ full input-manifest schema check
→ recorded release-evidence verifier report
→ canonical candidate replay
→ canonical verifier replay
→ complete policy-gate admissibility check
→ atomic release-required materialization
→ final status.json
```

## Existing tools

Use the checked-in canonical tools.

Do not create parallel replacements for:

```text
PULSE_safe_pack_v0/tools/build_recorded_release_candidates_v0.py
PULSE_safe_pack_v0/tools/check_recorded_release_evidence_v0.py
PULSE_safe_pack_v0/tools/materialize_release_required_from_verifier_v0.py
PULSE_safe_pack_v0/tools/check_gates.py
```

## Baseline preservation

Before release-required materialization, preserve:

```text
PULSE_safe_pack_v0/artifacts/status_baseline.json
```

The baseline must remain the pre-materialization candidate state.

The final:

```text
PULSE_safe_pack_v0/artifacts/status.json
```

must remain mechanically distinguishable from that baseline.

## Candidate-to-final delta

For the reference run, complete-package verification must be able to prove that the final release-state transformation is limited to the permitted materialization path.

At minimum:

```text
baseline run identity
= final run identity

baseline subject identity
= final subject identity

baseline policy identity
= final policy identity

baseline gates
+ policy-derived release_required literal-true gates
= final gates
```

No unrelated silent gate or identity mutation is permitted.

## Full manifest validation

The runtime path must execute the separate full input-manifest checker before relying on the manifest as schema-valid.

Recorded-verifier acceptance of mechanically consumed fields is not sufficient to claim complete schema validity.

## Materialization boundary

The materializer must:

- rerun the recorded verifier canonically;
- compare the supplied verifier report with replay;
- derive every release-required gate from policy;
- require a verified admissibility entry for every policy-derived gate;
- reject pre-existing release-required gate values;
- reject stubbed or scaffolded candidate state;
- fail without partially writing final state.

---

# Work package 5 — enforce the final release boundary

## Goal

Run strict final enforcement over the exact workflow-effective materialized required gate set.

## Required final evaluator

```text
PULSE_safe_pack_v0/tools/check_gates.py
```

## Required gate derivation

The workflow must derive:

```text
required
+ release_required
```

from declared policy for the selected release-grade lane.

The list must not be manually copied into a divergent workflow constant.

## Enforcement rule

Every workflow-effective required gate must:

- exist;
- be literal boolean `true`.

Any missing, false, non-boolean, malformed, or inaccessible gate must block.

## Terminal vocabulary

The primary release-boundary result is:

```text
allow
block
```

Internal historical artifact states must not be substituted for the primary CI allow/block result.

## Decision artifact

After final enforcement, produce:

```text
PULSE_safe_pack_v0/artifacts/release_decision_v0.json
```

The artifact must preserve the recorded decision trace.

It does not replace the primary CI result.

---

# Work package 6 — assemble the complete reference package

## Goal

Extend the current baseline bundle into the complete evidence-chain package required by the reference-run definition.

## Existing bundle boundary

The existing:

```text
release-grade-reference-run-v0
```

assembly is a baseline.

It does not yet prove complete evidence-chain preservation.

## Required complete package contents

### Current-run evidence

```text
PULSE_safe_pack_v0/artifacts/required_gate_evidence_v0.json
PULSE_safe_pack_v0/artifacts/refusal_delta_summary.json
```

### Pre-materialization state

```text
PULSE_safe_pack_v0/artifacts/status_baseline.json
PULSE_safe_pack_v0/artifacts/status_summary_baseline.json
```

### Candidate set

```text
PULSE_safe_pack_v0/artifacts/recorded_release_candidates/
PULSE_safe_pack_v0/artifacts/recorded_release_candidate_index_v0.json
```

### Input and verification artifacts

```text
PULSE_safe_pack_v0/artifacts/release_evidence_input_manifest_v0.json
PULSE_safe_pack_v0/artifacts/recorded_release_evidence_verifier_v0.json
```

### External evidence

```text
current-run raw external evidence
canonical external summary
canonical external-summary envelope
cryptographic attestation bundle
```

### Final release state

```text
PULSE_safe_pack_v0/artifacts/status.json
PULSE_safe_pack_v0/artifacts/status_summary.json
PULSE_safe_pack_v0/artifacts/release_decision_v0.json
PULSE_safe_pack_v0/artifacts/artifact_provenance_binding_v0.json
PULSE_safe_pack_v0/artifacts/release_authority_v0.json
PULSE_safe_pack_v0/artifacts/report_card.html
```

### Review and audit state

```text
release-authority-audit-bundle
Quality Ledger / status parity result
complete package digest inventory
run metadata
reproduction instructions
```

### Optional exports

```text
JUnit
SARIF
publication snapshot
public reader artifacts
```

## Package path rules

The complete package must:

- contain regular non-symlink files;
- use canonical relative paths;
- reject path traversal;
- reject duplicate artifact names;
- preserve current-run identity;
- preserve file digests;
- contain no stale file from an earlier run;
- contain no fixture substituted for runtime evidence;
- distinguish required and optional files;
- fail closed when a required artifact is absent.

## Package digest inventory

The packaging PR must produce a machine-readable digest inventory covering every required package file.

The inventory must record at least:

```text
relative path
SHA-256 digest
artifact role
required or optional status
run identity
```

Do not add a documentation-only pathname for a tool or schema before the corresponding implementation PR introduces it.

## Atomic assembly

The complete package should be assembled into a fresh temporary directory.

The final package artifact should become visible only after all required copy and verification operations succeed.

A failed assembly must not leave a stale package that can be uploaded as if it were current.

---

# Work package 7 — independently verify the complete package

## Goal

Verify the complete reference package separately from the advisory subset qualification checker.

## Qualification distinction

```text
advisory qualification checker OK
≠ complete package verified
```

The existing qualification checker remains:

- advisory;
- non-normative;
- non-blocking;
- limited to its declared input subset.

Do not silently expand it into a second authority engine.

## Complete-package verifier role

The package-verification implementation must be:

- read-only;
- non-authorizing;
- fail-closed for reference acceptance;
- independent of public reader surfaces.

It may extend an existing checked-in PULSE-REF package-verifier surface or introduce a dedicated checked-in equivalent.

The exact path must be introduced and tested in the implementation PR before documentation names it as an implemented tool.

## Minimum package checks

The complete-package verifier must check:

1. required inventory presence;
2. no unexpected replacement of canonical paths;
3. regular-file and non-symlink state;
4. package digest inventory equality;
5. one consistent run identity;
6. baseline and final status identity equality;
7. candidate directory and index consistency;
8. manifest candidate-set consistency;
9. full manifest schema validity;
10. supplied candidate equality with canonical candidate replay;
11. verifier report equality with canonical verifier replay;
12. complete policy-gate admissibility;
13. baseline-to-final materialization delta;
14. final status schema validity;
15. exact workflow-effective required gate set;
16. strict gate replay result;
17. recorded decision equality with replay;
18. release-authority manifest consistency;
19. Quality Ledger / final-status parity;
20. provenance-binding verification;
21. external summary, envelope, bundle, and raw-evidence presence;
22. external summary and raw-evidence digest binding;
23. signer identity and workflow binding;
24. cryptographic attestation verification;
25. audit-bundle completeness.

## Replay result

The verifier should preserve a non-authoritative package-verification report.

That report may state:

```text
verified
failed
```

for package completeness.

It must not state or imply that package verification itself authorizes release.

## Completion distinction

```text
primary CI allow
+ complete package verified
= candidate eligible to become the public reference record
```

The package-verification report does not retroactively change the primary CI result.

---

# Work package 8 — execute the controlled strict run

## Pre-flight conditions

Do not start the controlled strict run until:

- all implementation PRs are merged;
- `main` CI is green;
- the exact signer identity is checked in;
- no reachable release-grade wildcard signer remains;
- the selected detector is recorded;
- stale external outputs are cleared by workflow;
- the current-run producer lane is wired;
- the attestation bundle is persisted;
- the canonical envelope is generated;
- the complete bundle assembly is wired;
- complete-package verification is wired;
- all relevant tests pass;
- the run note remains unfilled.

## Trigger

Use:

```text
workflow_dispatch
strict_external_evidence = true
```

## Fixed source state

Record before starting:

```text
repository
main commit SHA
workflow path
selected detector
release candidate
policy digest
registry digest
threshold-policy digest
signer-policy digest
```

Do not merge changes into the run's source commit while treating later artifacts as part of the same source state.

## Run-attempt rule

Each run attempt is a separate identity.

If an attempt fails:

- preserve the failed run for diagnosis;
- do not rewrite it as successful;
- fix the implementation through a new PR;
- rerun from the new source commit;
- record the new run attempt separately.

## No in-place runtime repair

Do not manually repair artifacts inside a failed workflow run.

The run either produces the complete valid chain or it does not.

## Expected terminal outcomes

### Allow candidate

A successful controlled run should produce:

```text
primary CI decision = allow
advisory subset qualification = qualified
complete package verification = verified
public record eligibility = yes
```

### Block candidate

A blocked run may still be valuable evidence.

It must preserve:

```text
primary CI decision = block
blocking reasons
failed verifier or gate path
incomplete package state
run identity
```

A blocked run is not the completed passing public reference record.

---

## Fail-closed conditions

The controlled run must fail or block on any of the following:

### Identity failures

- missing exact signer identity;
- wildcard signer identity;
- wrong repository;
- wrong workflow;
- wrong source commit;
- mixed run IDs;
- mixed run attempts;
- stale release-candidate identity.

### External evidence failures

- evaluator failure;
- no supported external summary;
- stale summary;
- both JSON and JSONL summary for one detector;
- malformed summary;
- summary schema failure;
- semantic failure;
- metric threshold failure;
- raw-evidence path escape;
- raw-evidence digest mismatch;
- missing envelope;
- envelope schema failure;
- summary-reference mismatch;
- summary-digest mismatch;
- signing identity mismatch;
- missing attestation bundle;
- failed GitHub attestation verification.

### Candidate and verifier failures

- missing canonical candidate;
- extra non-canonical candidate;
- modified candidate;
- candidate index mismatch;
- full manifest schema failure;
- canonical candidate replay mismatch;
- recorded verifier failure;
- canonical verifier replay mismatch;
- empty evidence results;
- empty relation results;
- missing gate admissibility;
- incomplete policy gate coverage.

### Materialization failures

- pre-existing release-required gate;
- stubbed candidate state;
- scaffolded candidate state;
- policy mismatch;
- registry mismatch;
- partial materialization attempt;
- baseline-to-final unauthorized mutation.

### Final enforcement failures

- invalid final `status.json`;
- missing workflow-effective gate;
- false gate;
- non-boolean gate;
- wrong required gate set;
- strict checker failure;
- recorded decision mismatch.

### Package failures

- missing required artifact;
- stale artifact;
- symlinked artifact;
- path escape;
- digest mismatch;
- mixed run identity;
- incomplete audit bundle;
- Ledger/status mismatch;
- provenance-binding failure;
- package-verification failure.

---

## Required tests before execution

Run the relevant standing tests, including:

```text
tests/test_check_external_summary_attestation_v1.py
tests/test_release_grade_candidate_evidence_path_v0.py
tests/test_release_evidence_input_manifest_v0.py
tests/test_check_recorded_release_evidence_v0.py
tests/test_materialize_release_required_from_verifier_v0.py
tests/test_check_release_grade_reference_run_v0.py
tests/test_release_grade_reference_qualification_advisory_boundary_v0.py
tests/test_artifact_provenance_binding_ci_wiring_smoke.py
tests/test_artifact_provenance_binding_attestation_wiring_smoke.py
```

Add tests for each new layer introduced by this plan:

- external producer;
- exact signer policy;
- stale-output cleanup;
- summary generation;
- bundle persistence;
- envelope generation;
- complete package assembly;
- package inventory;
- package digest validation;
- baseline-to-final delta;
- complete-package verification;
- workflow wiring.

The normal tools suite must remain green.

---

## Acceptance criteria

The first public release-grade reference run is complete only when all of the following are true:

### Source and run identity

- the source commit is concrete;
- the workflow identity is concrete;
- the run ID is concrete;
- the run attempt is concrete;
- the run key is concrete;
- the release candidate is concrete;
- every required artifact belongs to that same run.

### External evidence

- current-run raw external evidence exists;
- canonical summary exists;
- canonical summary schema passes;
- detector semantics pass;
- canonical threshold binding passes;
- raw-evidence digest binding passes;
- canonical envelope exists;
- exact signer identity is admitted;
- wildcard signer identity is absent from the active path;
- attestation bundle exists;
- GitHub attestation verification succeeds.

### Candidate and verifier path

- candidate status is non-stubbed;
- candidate status is non-scaffolded;
- `status_baseline.json` is preserved;
- canonical candidates are produced;
- candidate index is produced;
- full input-manifest schema validation passes;
- canonical candidate replay matches;
- recorded verifier succeeds;
- canonical verifier replay matches;
- all relations are satisfied;
- all policy-derived release-required gates are admissible.

### Materialization and enforcement

- release-required materialization succeeds atomically;
- final `status.json` validates;
- baseline-to-final delta is permitted;
- every workflow-effective required gate exists;
- every workflow-effective required gate is literal true;
- `PULSE_safe_pack_v0/tools/check_gates.py` succeeds;
- the primary CI decision is recorded as allow.

### Decision and trace artifacts

- `release_decision_v0.json` exists;
- `artifact_provenance_binding_v0.json` exists and verifies;
- `release_authority_v0.json` exists and validates;
- Quality Ledger is rendered from final status;
- Quality Ledger / final-status parity passes;
- audit bundle is complete.

### Complete package

- the complete package is assembled;
- every required artifact is present;
- package digest inventory is complete;
- no stale artifact is present;
- no fixture substitutes for runtime evidence;
- package verification succeeds;
- reconstruction matches the recorded primary CI decision.

### Public record

- public artifact references exist;
- required SHA-256 digests are recorded;
- the run note is completed from the actual run;
- README and docs index link the completed record;
- the run is clearly labeled as the first completed public non-stubbed release-grade reference run.

---

## Run-note completion

After the controlled run and complete-package verification succeed, complete:

```text
docs/RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md
```

Populate it only from actual artifacts and workflow metadata.

Required record classes include:

```text
run identity
policy and registry identity
workflow-effective gate set
external evidence identity
signer and attestation identity
candidate and verifier state
materialization state
primary CI result
qualification state
complete-package verification state
public artifact references
SHA-256 digests
```

Do not fill the run note from intended values.

Do not use `pending` placeholders in a record presented as complete.

## Public entrypoint update

Only after the run note is completed from the actual run:

- update the README from pending to completed;
- update `docs/INDEX.md`;
- link the public workflow run;
- link the complete reference package;
- link the final status and Ledger;
- record package and key artifact digests.

These publication changes are post-run recording work.

They do not create the run.

---

## Implementation PR sequence

The work should proceed through mechanically bounded PRs.

### PR 1 — current-run external producer lane

Expected scope:

```text
producer tool or workflow step
producer tests
current-run raw evidence
canonical summary generation
stale-output cleanup
```

The lane remains non-authorizing.

### PR 2 — exact operational signer identity and attestation wiring

Expected scope:

```text
exact workflow identity
signer-policy cleanup
attestation creation
bundle persistence
canonical envelope generation
signer and envelope tests
```

No reachable release-grade wildcard may remain for the selected tool.

### PR 3 — strict candidate-path workflow wiring

Expected scope:

```text
external producer output
→ attestation verification
→ canonical candidate production
→ manifest
→ recorded verifier
→ materializer
```

Use the existing canonical tools.

### PR 4 — complete reference-package assembly

Expected scope:

```text
complete artifact inventory
fresh temporary assembly
digest inventory
no-stale-output behavior
upload wiring
package tests
```

### PR 5 — independent complete-package verification

Expected scope:

```text
read-only package verification
identity checks
digest checks
candidate/verifier replay checks
baseline-to-final checks
decision reconstruction
attestation re-verification
package-verification report
```

The verifier remains non-authoritative.

### Controlled run

After all implementation PRs are merged and green:

```text
workflow_dispatch
strict_external_evidence = true
```

### Post-run record PR

Expected scope:

```text
docs/RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md
README.md
docs/INDEX.md
```

This PR records completed runtime evidence.

It must not contain implementation changes.

---

## Work that must not be reopened

The next-run work must not reopen these layers without a demonstrated defect:

```text
recorded verifier status vocabulary
candidate replay identity
materializer authority boundary
PULSE_safe_pack_v0/tools/check_gates.py final role
Quality Ledger non-authority
release-authority manifest non-authority
primary CI allow/block vocabulary
```

Documentation, UI, reader, or publication concerns must not alter the normative decision core.

---

## Non-goals

This plan does not:

- build a second release-decision engine;
- replace the recorded verifier;
- replace the materializer;
- replace `PULSE_safe_pack_v0/tools/check_gates.py`;
- make attestation alone sufficient for release;
- make package verification release authority;
- make advisory qualification release authority;
- make the Quality Ledger release authority;
- accept wildcard release-grade signers;
- use fixture evidence as current-run evidence;
- require every supported external detector in the first run;
- begin HPC batch validation before the reference state exists;
- claim that the first completed public run already exists.

---

## Relationship to HPC validation

HPC validation begins after the first completed public release-grade reference run exists.

The reference run becomes the fixed baseline for later candidate-state scaling.

The sequence is:

```text
one completed reference state
→ controlled failure variants
→ archived expected decisions
→ reproducible package verification
→ larger candidate-state batches
→ HPC-supported analysis
```

HPC is not a substitute for the missing reference state.

The reference state supplies the stable evidence and decision boundary that HPC may later vary diagnostically.

PULSEmech remains the release-authority mechanism.

---

## Completion state

This plan is complete only when:

```text
exact signer identity = implemented
current-run external producer = implemented
attestation bundle and envelope lane = implemented
strict candidate/verifier/materializer wiring = implemented
complete package assembly = implemented
complete package verification = implemented
controlled strict run = successful
public run record = completed
```

Until then:

```text
first_completed_public_non_stubbed_release_grade_run = pending
```

## Minimal mechanical anchor

```text
fixture success
≠ current-run evidence

summary produced
≠ summary verified

attestation verified
≠ candidate admitted

candidate admitted
≠ gate materialized

gate materialized
≠ release authority by itself

advisory qualification
≠ complete package verification

baseline bundle
≠ completed reference package

planned run
≠ completed public run
```

The forward path is:

```text
exact operational signer
→ current-run attested external evidence
→ existing replay-bound admission
→ existing policy-derived materialization
→ existing strict final enforcement
→ complete package
→ independent package verification
→ controlled public reference run
→ recorded baseline for later scaling
```

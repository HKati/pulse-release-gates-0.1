# PULSE release-grade next run plan v0

## Document status

```text
document_role: current_operational_execution_plan
target: first_completed_public_non_stubbed_release_grade_run
normative_release_authority: false
implementation_layers_present: true
controlled_hosted_run_completed: false
public_run_record_completed: false
```

This document defines the remaining operational work required to produce the
first completed public, non-stubbed, non-scaffolded PULSE release-grade
reference run.

The standing release-authority implementation must not be redesigned merely
because the qualifying public run has not yet been completed.

The remaining work is:

```text
controlled-run preflight
→ one fixed-source hosted execution
→ defect-driven repair only if required
→ complete-package verification
→ public run record
```

This document is an execution plan.

It does not create release authority.

It does not activate SLSA/VSA as release-required.

It does not create a GitHub Release, version tag, Zenodo record, or DOI.

## 1. Purpose

The next PULSE proof state is not another fixture, smoke surface, dashboard,
reader page, or documentation-only claim.

The target is one controlled release-grade execution that:

- produces the complete evidence-to-decision chain from current-run inputs;
- preserves one connected run identity;
- produces non-stubbed and non-scaffolded release state;
- produces current-run attested external evidence;
- reaches the primary CI allow/block decision;
- assembles the complete release-grade reference package;
- passes structural completeness checking;
- passes independent deep package verification;
- records the actual run and artifact digests publicly.

The target path is:

```text
current-run release evidence
→ non-stubbed candidate release state
→ current-run hosted external evidence
→ exact-workflow attestation
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
→ structural completeness preflight
→ independent package verification
→ completed public run record
```

## 2. Source-of-truth boundary

The current mechanical sources of truth include:

```text
.github/workflows/pulse_ci.yml
pulse_gate_policy_v0.yml
pulse_gate_registry_v0.yml
policy/external_signers_v1.yml
PULSE_safe_pack_v0/tools/check_gates.py
PULSE_safe_pack_v0/tools/check_recorded_release_evidence_v0.py
PULSE_safe_pack_v0/tools/materialize_release_required_from_verifier_v0.py
PULSE_safe_pack_v0/tools/assemble_release_grade_reference_package_v0.py
PULSE_safe_pack_v0/tools/verify_release_grade_reference_package_v0.py
tools/check_release_grade_package_complete_v1.py
docs/release_grade_reference_run_v0.md
docs/recorded_release_evidence_verifier_v0.md
docs/release_reference_external_evidence_integration_v1.md
docs/RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md
```

Implementation and tests remain the primary mechanical source of truth if
documentation and executable behavior disagree.

## 3. Authority boundary

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

The following may produce, preserve, bind, verify, reconstruct, explain, or
publish evidence, but they do not independently authorize release:

- raw external evidence;
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
- package completeness reports;
- package verification reports;
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

A package-verification result does not retroactively alter the primary CI
allow/block decision.

## 4. Current implementation state

### 4.1 Implemented release-grade mechanics

The checked-in implementation already contains:

```text
current-run required-gate evaluation
required_gate_evidence_v0 production
non-stubbed prod candidate status production
status_baseline.json preservation
canonical recorded-release candidate production
canonical candidate replay
release-evidence input-manifest production
input-manifest validation
recorded release-evidence verification
relation-binding verification
manifest-declared per-gate admissibility
canonical verifier replay in the materializer
complete policy-gate coverage in the materializer
atomic release-required materialization
strict final gate enforcement
release decision artifact production
artifact provenance binding
release-authority audit/trace manifest production
Quality Ledger rendering and parity checking
release-authority audit-bundle production
```

### 4.2 Implemented current-run external-evidence mechanics

The checked-in implementation also contains:

```text
explicit hosted_full_runtime workflow mode
current-run LlamaGuard raw-evidence production
current-run evaluator manifest production
canonical external_summary_v1 production
stale external-output cleanup
external-summary schema validation
external-summary semantic validation
exact LlamaGuard workflow signer identity
wildcard signer rejection on the active LlamaGuard path
GitHub attestation production wiring
canonical attestation-bundle persistence
canonical external-summary envelope construction
cryptographic GitHub attestation verification
attested evidence restoration into the recorded release path
```

The exact admitted LlamaGuard workflow identity is:

```text
repo:HKati/pulse-release-gates-0.1:workflow:.github/workflows/pulse_ci.yml
```

### 4.3 Implemented package mechanics

The checked-in implementation contains:

```text
complete release-grade reference-package assembly
fresh temporary package directory
package digest inventory
run metadata
complete-package artifact upload
structural package completeness checker
strict JSON and JSONL parsing
duplicate-key rejection
non-finite-value rejection
regular-file and non-symlink checks
path-escape rejection
non-empty required-file checks
non-stub content checks
recorded-candidate presence checks
digest inventory replay
independent read-only deep package verifier
package verification report upload
workflow boundary guards
```

### 4.4 Implemented but non-active SLSA/VSA mechanics

The repository contains:

```text
non-active slsa_vsa_recorded_intake_candidate gate set
recorded-intake candidate proof
trusted-producer input-packet schema
trusted-producer input-packet validator
deterministic trusted-producer input-packet builder
trusted-evidence producer-report schema
trusted-evidence producer-report validator
report builder from validated input packet
generated packet → accepted report integration smoke
CI boundary guards for future workflow use
```

These mechanics are not active release-required enforcement.

They are not part of the acceptance criteria for the first controlled hosted
release-grade reference run.

No SLSA/VSA policy promotion belongs in this execution track.

## 5. Remaining proof gap

The remaining gap is not the absence of the release-grade architecture.

The remaining gap is one successful qualifying execution from a fixed source
commit.

Still pending:

```text
confirmed hosted-model access for the controlled run
one fixed source commit
one successful hosted_full_runtime execution
one qualifying current-run attestation bundle
one qualifying complete current-run package
one successful structural completeness report
one successful independent package verification report
one completed public release-grade run note
```

The distinction is:

```text
implemented capability
≠ completed qualifying execution
```

## 6. Controlled-run parameters

The first qualifying run must use:

```text
event: workflow_dispatch
strict_external_evidence: true
llamaguard_evidence_mode: hosted_full_runtime
```

The first controlled proof run must not require:

```text
version tag
GitHub Release
Zenodo publication
new DOI
citation-metadata change
```

A version tag must not be created merely to force the release-grade path to
execute.

A version-tagged reference may be considered only after the controlled
workflow-dispatch path has already produced and verified the complete package.

## 7. Preflight conditions

Do not start the controlled hosted run until all conditions below are
satisfied.

### 7.1 Fixed source state

Record:

```text
repository
main commit SHA
workflow path
release candidate
policy path and SHA-256
registry path and SHA-256
signer-policy path and SHA-256
threshold-policy path and SHA-256
selected evaluator identity
selected model identity
selected model revision
```

The run must remain bound to that source commit.

A later commit must not be treated as part of the same source state.

### 7.2 Repository state

Required:

```text
main CI is green
no unrelated release-authority PR is being merged into the fixed source state
git diff --check passes
run-note template remains unfilled
no version tag is created for the preflight
no GitHub Release is created for the preflight
```

### 7.3 Hosted access

Confirm:

```text
HF_TOKEN repository secret is present
the token can access the pinned hosted model
the token is scoped only to the hosted producer step
the token cannot appear in logs or artifacts
the pinned model revision is available
the expected runtime and cost are acceptable
```

Missing provider access is a blocked precondition.

It must not be converted into a passing evidence state.

### 7.4 Attestation boundary

Confirm:

```text
the attestation job has only the required permissions
the attested subject is the final canonical summary
the expected signer identity is exact
the expected repository is exact
the expected source commit is the fixed run commit
the expected predicate type is exact
the expected issuer is the GitHub Actions OIDC issuer
the bundle is persisted at the path recorded by the envelope
```

### 7.5 Targeted preflight tests

Run the standing targeted checks, including:

```text
python tests/test_llamaguard_current_run_workflow_wiring_v0.py
python tests/test_check_external_summary_attestation_v1.py
python tests/test_release_grade_candidate_evidence_path_v0.py
python tests/test_release_grade_reference_package_assembly_wiring_v0.py
python tests/test_release_grade_reference_package_verification_wiring_v0.py
python tests/test_release_grade_package_completeness_checker_ci_boundary_v1.py
python tests/test_release_grade_package_completeness_workflow_wiring_v1.py
python tests/test_check_release_grade_package_complete_v1.py
python tests/test_tools_tests_list_smoke.py
git diff --check
```

The complete normal CI suite remains the final preflight authority for the
checked-in source state.

## 8. Required execution sequence

The controlled run must preserve the standing sequence:

```text
current-run required-gate evidence
→ non-stubbed candidate status
→ status_baseline.json
→ current-run LlamaGuard raw evidence
→ evaluator manifest
→ canonical LlamaGuard summary
→ exact-workflow GitHub attestation
→ persisted attestation bundle
→ canonical summary envelope
→ cryptographic attestation verification
→ canonical recorded-release candidates
→ recorded candidate index
→ release-evidence input manifest
→ input-manifest validation
→ recorded release-evidence verifier
→ canonical candidate replay
→ canonical verifier replay
→ complete policy-gate admissibility check
→ atomic release-required materialization
→ final status.json
→ workflow-effective required gate-set derivation
→ PULSE_safe_pack_v0/tools/check_gates.py
→ primary CI allow/block decision
→ complete package assembly
→ structural package completeness check
→ independent deep package verification
```

No parallel replacement may be introduced for the standing:

```text
candidate builder
recorded verifier
materializer
final gate checker
package assembler
package verifier
```

## 9. One-run identity rule

The complete chain must preserve one current-run identity.

Required identity fields include:

```text
repository
git_sha
workflow path
workflow run ID
workflow run number
workflow run attempt
run key
run mode
release candidate
created_utc
policy identity
policy digest
registry identity
registry digest
```

The same identity must be preserved across:

- required-gate evidence;
- candidate status;
- baseline status;
- raw external evidence;
- evaluator manifest;
- canonical external summary;
- attestation bundle;
- canonical envelope;
- attestation verifier report;
- candidate envelopes;
- candidate index;
- input manifest;
- recorded verifier report;
- final status;
- release decision;
- provenance binding;
- release-authority manifest;
- audit bundle;
- package metadata;
- package digest inventory;
- completeness report;
- package verification report;
- public run note.

Cross-run or cross-attempt evidence mixing is forbidden.

## 10. No manual evidence insertion

The completed reference run must not depend on:

- manually edited generated JSON;
- copied fixture outputs;
- a previously generated external summary;
- a previously generated attestation bundle;
- a manually changed gate value;
- a manually changed verifier report;
- a manually repaired package;
- a manually completed run note presented as runtime proof;
- evidence from another run ID;
- evidence from another run attempt;
- evidence from another source commit.

Every required release-grade artifact must be produced, bound, restored, or
independently verified inside the controlled current-run path.

## 11. Required artifact package

The qualifying complete package must contain the required current-run
instances of:

### 11.1 Package identity

```text
package_digest_inventory_v0.json
run_metadata_v0.json
```

### 11.2 Current-run and baseline evidence

```text
artifacts/required_gate_evidence_v0.json
artifacts/status_baseline.json
```

### 11.3 Recorded candidate and verifier state

```text
artifacts/recorded_release_candidates/
artifacts/recorded_release_candidate_index_v0.json
artifacts/release_evidence_input_manifest_v0.json
artifacts/recorded_release_evidence_verifier_v0.json
```

### 11.4 Current-run external evidence

```text
artifacts/external/llamaguard_raw.jsonl
artifacts/external/llamaguard_evaluator_manifest_v0.json
artifacts/external/llamaguard_summary.json
artifacts/external/llamaguard_summary.bundle.json
artifacts/external/llamaguard_summary.envelope.json
artifacts/external/llamaguard_attestation_verifier_v1.json
```

### 11.5 Final release state and trace

```text
artifacts/status.json
artifacts/release_decision_v0.json
artifacts/artifact_provenance_binding_v0.json
artifacts/release_authority_v0.json
artifacts/report_card.html
release-authority-audit-bundle/
```

The SLSA/VSA trusted-producer packet and report remain optional under the
current package contract.

Do not enable:

```text
--require-slsa-vsa-trusted-producer
```

in this execution track unless a separate, reviewed PR first stages those
artifacts in the package and explicitly changes the contract.

## 12. Success criteria

The first controlled hosted release-grade run qualifies only when all of the
following hold.

### 12.1 Source and run identity

- the source commit is concrete;
- the workflow identity is concrete;
- the run ID is concrete;
- the run attempt is concrete;
- the run key is concrete;
- every required artifact belongs to that same run and attempt.

### 12.2 Candidate state

- `run_mode` is `prod`;
- `diagnostics.gates_stubbed` is literal `false`;
- `diagnostics.scaffold` is literal `false`;
- `status_baseline.json` is preserved before materialization;
- no release-required gate is pre-materialized into the candidate.

### 12.3 External evidence

- current-run raw evidence exists;
- the evaluator manifest exists and validates;
- the canonical summary exists and validates;
- semantic validation passes;
- the canonical metric and threshold pass;
- the raw-evidence digest binding passes;
- the summary digest binding passes;
- the exact workflow signer identity matches;
- no reachable wildcard identity is accepted;
- the attestation bundle exists;
- cryptographic GitHub attestation verification succeeds;
- the canonical envelope and verifier report agree.

### 12.4 Recorded verifier and materialization

- canonical candidates are produced;
- the candidate index is produced;
- the full input manifest validates;
- canonical candidate replay matches;
- recorded verification succeeds;
- canonical verifier replay matches;
- every policy-derived release-required gate has verified admissibility;
- release-required materialization succeeds atomically.

### 12.5 Final enforcement

- final `status.json` validates;
- the workflow-effective required gate set is derived from declared policy;
- every required gate exists;
- every required gate is literal boolean `true`;
- `PULSE_safe_pack_v0/tools/check_gates.py` succeeds;
- the primary CI decision is recorded as `allow`.

### 12.6 Package verification

- the complete package is assembled;
- all required files and directories are present;
- all required files are non-empty regular files;
- no required path is symlinked;
- no path escapes the package root;
- no stale artifact is present;
- no fixture substitutes for runtime evidence;
- the digest inventory exactly covers the package;
- structural completeness reports `complete`;
- independent deep package verification reports `verified`;
- the reconstructed result agrees with the recorded primary CI decision.

### 12.7 Trace and review artifacts

- `release_decision_v0.json` is present;
- `artifact_provenance_binding_v0.json` is present and verifies;
- `release_authority_v0.json` is present as an audit/trace sidecar;
- Quality Ledger is rendered from final status;
- Quality Ledger parity passes;
- the audit bundle is complete.

## 13. Failure and repair rule

Each workflow run attempt is a separate evidence identity.

If an attempt fails:

```text
preserve the failed attempt
→ preserve its diagnostics and artifacts
→ identify the first mechanical failure
→ repair through a new focused PR
→ add or strengthen a regression test
→ merge only after CI passes
→ rerun from the new source commit
```

Do not:

- modify artifacts inside a failed workflow run;
- relabel a failed attempt as successful;
- suppress a blocking result;
- weaken a gate to manufacture a pass;
- copy evidence from another attempt;
- combine the repair with DOI, Zenodo, citation, or publication work;
- replace a standing decision layer without a demonstrated defect.

A valid fail-closed block is a release-transition result.

It is not a completed passing public reference run.

## 14. Public run record

Only after the controlled run and both package checks succeed, complete:

```text
docs/RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md
```

Populate the record only from actual workflow metadata and produced artifacts.

The record must include:

```text
repository
source ref
source commit
workflow path
workflow run ID
workflow run attempt
workflow URL
workflow inputs
run mode
release candidate
policy identity and digest
registry identity and digest
signer-policy digest
threshold-policy digest
model identity and revision
exact signer identity
attestation verification result
primary CI decision
structural completeness result
deep package verification result
artifact names
artifact references
artifact SHA-256 digests
what was proven
what was not proven
```

The run note may document and link the proof.

It must not replace:

```text
status.json
declared policy
materialized required gates
check_gates.py
primary CI allow/block result
```

Recording the first public run must not create a new DOI or GitHub Release
unless a later, independent publication decision explicitly requires one.

## 15. SLSA/VSA boundary

The SLSA/VSA recorded-intake candidate and trusted-producer construction chain
remain non-active.

For this controlled run:

```text
SLSA/VSA candidate proof
= preserved

SLSA/VSA trusted-producer artifacts
= optional under the current package contract

SLSA/VSA release-required activation
= not performed
```

Any future promotion must remain a separate PR with:

- explicit policy effect;
- current-run evidence production;
- artifact binding;
- policy digest binding;
- verifier identity binding;
- freshness enforcement;
- negative fail-closed tests;
- rollback behavior;
- changelog coverage.

## 16. Completion condition

This execution plan is complete only when:

```text
one fixed source commit
+ one successful hosted_full_runtime execution
+ primary CI allow
+ complete package assembled
+ structural completeness complete
+ independent package verification verified
+ public run note completed from actual artifacts
= first completed public non-stubbed release-grade reference run
```

Until then, the correct state remains:

```text
release-grade implementation layers present
controlled qualifying public run pending
```

## 17. Change-control note

This document update is documentation-only.

It does not change:

- workflow behavior;
- policy behavior;
- gate behavior;
- verifier behavior;
- materializer behavior;
- package behavior;
- schema behavior;
- SLSA/VSA activation;
- DOI identity;
- release metadata;
- release-authority semantics.

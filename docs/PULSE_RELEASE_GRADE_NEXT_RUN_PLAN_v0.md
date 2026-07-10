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

This document defines the remaining operational work required to produce the first completed public, non-stubbed, non-scaffolded PULSE release-grade reference run.

The standing release-authority implementation must not be redesigned merely because the qualifying public run has not yet been completed.

The remaining work is:

```text
controlled-run preflight
→ one fixed-source hosted execution
→ defect-driven repair only if required
→ complete-package acceptance
→ public run record
```

This document is an execution plan.

It does not create release authority.

It does not activate SLSA/VSA as release-required.

It does not create a GitHub Release, version tag, Zenodo record, or DOI.

## Purpose

The next PULSE proof state is not another fixture, smoke surface, dashboard, reader page, or documentation-only claim.

The target is one controlled release-grade execution that materializes the complete evidence-to-decision path from current-run evidence and preserves a complete, independently reviewable artifact package.

The target path is:

```text
current-run release evidence
→ non-stubbed candidate release state
→ current-run hosted LlamaGuard raw evidence
→ canonical LlamaGuard external summary
→ exact-workflow GitHub attestation
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

## Source-of-truth boundary

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
docs/PULSE_RELEASE_AUTHORITY_PRODUCT_BOUNDARY_v1.md
docs/release_grade_reference_run_v0.md
docs/recorded_release_evidence_verifier_v0.md
docs/release_reference_external_evidence_integration_v1.md
docs/PULSEMECH_RELEASE_GRADE_REFERENCE_PROOF_PLAN_v0.md
docs/RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md
```

Implementation and tests remain the primary mechanical source of truth if documentation and executable behavior disagree.

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

The following may produce, preserve, bind, verify, reconstruct, explain, or publish evidence, but they do not independently authorize release:

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

A package-completeness or package-verification result does not retroactively alter the primary CI allow/block decision.

## Current implementation state

### Implemented release-authority mechanics

The checked-in implementation already contains:

```text
current-run required-gate evaluation
required_gate_evidence_v0 production
complete evaluator coverage for gates.required
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

### Implemented current-run external-evidence mechanics

The checked-in implementation contains:

```text
explicit hosted_full_runtime workflow mode
current-run LlamaGuard raw-evidence production
current-run evaluator-manifest production
canonical external_summary_v1 production
stale external-output cleanup
external-summary schema validation
external-summary semantic validation
exact LlamaGuard workflow signer identity
wildcard signer rejection on the active LlamaGuard release-grade path
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

This is a checked-in identity and workflow capability.

It does not by itself prove that a qualifying current-run hosted execution has completed successfully.

### Implemented package mechanics

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

### Implemented but non-active SLSA/VSA mechanics

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

They are not required for the first controlled hosted release-grade reference run under the current package contract.

### Pending operational proof

The remaining operational gaps are:

```text
confirmed hosted-model access for the controlled run
one fixed source commit
one successful hosted_full_runtime execution
one qualifying current-run attestation bundle
one qualifying complete current-run package
one successful structural completeness report
one successful independent package-verification report
one completed public release-grade run note
```

The distinction is:

```text
implemented capability
≠ completed qualifying execution
```

## Mechanical rule

The next work must execute and prove the standing implementation.

It must not replace working layers with parallel implementations.

```text
implemented verifier
→ keep

implemented materializer
→ keep

implemented final gate checker
→ keep

implemented external-evidence path
→ execute from one fixed current run

implemented complete-package path
→ assemble and verify from that same run

missing qualifying execution and public record
→ produce, preserve, verify, and record
```

Any change to an already standing decision layer requires a concrete implementation defect demonstrated by a failing test or controlled run.

---

## Target proof state

The completed run must prove all of the following in one connected run identity:

1. required-gate evidence was produced from the current run;
2. the candidate release state was non-stubbed and non-scaffolded;
3. the selected LlamaGuard evaluator produced current-run raw evidence;
4. the canonical LlamaGuard summary was derived from that raw evidence;
5. the summary was attested by the exact allowed workflow identity;
6. the canonical envelope bound the summary, bundle, signer, repository, commit, and policy surfaces;
7. the attestation bundle passed cryptographic GitHub verification;
8. canonical candidate production admitted the external evidence;
9. canonical candidate replay reproduced the supplied candidate set;
10. recorded release-evidence verification succeeded;
11. canonical verifier replay matched the supplied verifier report;
12. every policy-derived release-required gate had a verified admissibility entry;
13. release-required materialization succeeded atomically;
14. final `status.json` validated;
15. the exact workflow-effective materialized required gate set was enforced;
16. the primary CI workflow recorded an allow or block result;
17. decision, provenance, manifest, Ledger, and audit artifacts were produced;
18. the complete evidence-chain package was assembled;
19. structural package completeness passed;
20. complete-package presence and binding were independently verified;
21. concrete run identity, artifact references, and digests were recorded publicly.

A run that satisfies only the advisory qualification checker is not complete.

A run that uploads only a historical baseline reference bundle is not complete.

---

## Controlled run strategy

The first qualifying reference run must use:

```text
event: workflow_dispatch
strict_external_evidence: true
llamaguard_evidence_mode: hosted_full_runtime
```

This provides a controlled release-grade execution without requiring the first attempt to create a version tag.

A version tag must not be used merely to force the path to run.

The first version-tagged reference should be created only after the controlled workflow-dispatch path has already demonstrated the complete package successfully.

The controlled proof run must not create:

```text
GitHub Release
Zenodo publication
new DOI
citation-metadata change
```

## No manual evidence insertion

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

Every required release-grade artifact must be produced, bound, restored, or independently verified inside the controlled current-run path.

## One run identity

The complete chain must preserve one current-run identity.

At minimum:

```text
repository
git_sha
workflow path
workflow run ID
workflow run number
workflow run attempt
run_key
run_mode
release candidate
created_utc
policy path
policy digest
registry path
registry digest
signer-policy path
signer-policy digest
threshold-policy path
threshold-policy digest
selected evaluator identity
selected model identity
selected model revision
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
- attestation-verifier report;
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

Cross-run, cross-attempt, or cross-commit evidence mixing is forbidden.

---

## Selected external detector scope

The first controlled run uses the smallest implemented external detector scope that proves the complete attested path.

The selected detector is:

```text
llamaguard
```

The selected checked-in workflow path already contains the LlamaGuard producer, summary, exact signer, attestation, envelope, verifier, recorded admission, package assembly, and package-verification wiring.

The first run does not need to execute every supported detector.

Other supported detector identities may remain available for future lanes:

```text
promptguard
garak
azure_eval
promptfoo
deepeval
```

Those additional detector lanes must not be described as having the same exact signer closure unless their own signer and producer paths are separately implemented and proven.

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
- an evaluator manifest from an earlier run;
- an envelope from an earlier run;
- an attestation bundle from an earlier run;
- an attestation-verifier report from an earlier run;
- both JSON and JSONL summaries for the same detector;
- a fixture copied into the runtime artifact directory.

The producer lane must recreate the complete selected-detector set from current-run inputs.

---

# Work package 1 — exact operational LlamaGuard signer

## Status

```text
implementation_status: implemented
qualifying_current_run_proof: pending
```

## Goal

Bind current-run canonical LlamaGuard evidence to one exact GitHub Actions workflow identity.

## Implemented identity

The active LlamaGuard release-grade path admits:

```text
repo:HKati/pulse-release-gates-0.1:workflow:.github/workflows/pulse_ci.yml
```

The LlamaGuard tool policy is restricted to the dedicated exact identity group.

Generic wildcard identity groups may exist for other deferred detector lanes, but they must not be reachable from the active LlamaGuard release-grade policy path.

## Identity-selection rule

Do not infer the signer identity from a display name.

Use the exact workflow identity reported by the GitHub attestation contract.

The qualifying run must prove:

```text
declared policy identity
= envelope signing identity
= attestation signer workflow
= verifier-derived workflow identity
```

## Preserved policy rule

For the selected detector, every signer-identity group reachable through:

```text
tool_policies.llamaguard.allowed_identity_groups
```

must remain mechanically safe.

Do not reintroduce a wildcard path that participates in the selected LlamaGuard release-grade policy evaluation.

## Required regression coverage

Tests must continue to cover:

- exact identity accepted;
- wildcard identity rejected;
- wrong repository rejected;
- wrong workflow rejected;
- wrong signing mode rejected;
- wrong release contribution rejected;
- identity present only in a disallowed group rejected;
- exact identity plus a reachable wildcard rejected.

## Completion condition

The checked-in implementation condition is satisfied for the LlamaGuard lane.

The operational proof condition remains pending until the fixed-source hosted run produces and verifies a bundle carrying that exact identity.

---

# Work package 2 — current-run LlamaGuard external-evidence producer

## Status

```text
implementation_status: implemented
qualifying_current_run_artifacts: pending
```

## Goal

Generate current-run raw LlamaGuard evidence, an evaluator manifest, and one canonical external summary.

## Implemented producer outputs

The producer lane creates:

```text
PULSE_safe_pack_v0/artifacts/external/llamaguard_raw.jsonl
PULSE_safe_pack_v0/artifacts/external/llamaguard_evaluator_manifest_v0.json
PULSE_safe_pack_v0/artifacts/external/llamaguard_summary.json
```

The outputs must be created from the current workflow execution.

## Raw-evidence contract

The raw-evidence artifact must:

- be a regular file;
- be non-symlink;
- remain inside the canonical external directory;
- contain the evaluator's current-run output;
- preserve the checked-in case text used for classification;
- be deterministic where possible;
- be hashable;
- be referenced by the summary;
- remain distinct from the summary itself.

## Evaluator-manifest contract

The evaluator manifest must bind the applicable:

```text
model identity
model revision
evaluator identity
evaluator digest
repository
source commit
workflow run identity
release candidate
creation time
```

It must validate against its checked-in schema.

## Canonical summary contract

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

- provider or evaluator failure;
- missing raw output;
- malformed raw output;
- duplicate JSON keys;
- non-finite numeric values;
- unsupported detector identity;
- missing canonical metric;
- missing threshold;
- threshold violation;
- missing dataset digest;
- missing evaluator digest;
- wrong run identity;
- wrong release-candidate identity;
- raw-evidence path escape;
- symlinked input or output;
- raw-evidence digest failure;
- evaluator-manifest schema failure;
- summary schema failure.

## Authority boundary

The producer is evidence production only.

It must not set release-required gates directly.

Release-required state remains dependent on canonical candidate production, replay, recorded verification, materialization, and final enforcement.

---

# Work package 3 — GitHub attestation bundle and canonical envelope

## Status

```text
implementation_status: implemented
qualifying_current_run_artifacts: pending
```

## Goal

Cryptographically bind the current-run canonical LlamaGuard summary to the exact workflow identity and current source commit.

## Implemented outputs

```text
PULSE_safe_pack_v0/artifacts/external/llamaguard_summary.json
PULSE_safe_pack_v0/artifacts/external/llamaguard_summary.bundle.json
PULSE_safe_pack_v0/artifacts/external/llamaguard_summary.envelope.json
PULSE_safe_pack_v0/artifacts/external/llamaguard_attestation_verifier_v1.json
```

## Attestation subject

The attested subject must be the exact final canonical summary file used by candidate production.

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

The mechanical order must remain:

```text
raw evidence
→ evaluator manifest
→ canonical summary
→ final summary digest
→ GitHub attestation
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

or the exact checked-in in-process equivalent used by canonical candidate production.

The accepted verifier result must contain no verification errors.

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
- failed or empty GitHub attestation verification result.

## Authority boundary

Attestation verifies a provenance and identity claim about the evidence artifact.

Attestation alone does not authorize release.

---

# Work package 4 — recorded candidate, verifier, and materializer path

## Status

```text
implementation_status: implemented
qualifying_current_run_execution: pending
```

## Goal

Use current-run attested LlamaGuard evidence without bypassing the standing release-grade implementation.

## Required sequence

```text
current-run required-gate evidence
→ non-stubbed candidate status
→ status_baseline.json
→ attested current-run LlamaGuard evidence
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

## Existing canonical tools

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

For the reference run, package review must be able to prove that the final release-state transformation is limited to the permitted materialization path.

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

## Recorded verifier boundary

The recorded verifier must check the applicable:

- manifest identity;
- run mode;
- run identity;
- subject identity;
- commit equality;
- policy path and digest;
- registry path and digest;
- candidate artifact digest;
- candidate schema;
- candidate run binding;
- candidate subject binding;
- canonical candidate replay;
- producer trust established by verified evidence;
- raw-evidence digest;
- required-gate membership;
- relation bindings;
- gate-materialization admissibility.

A supplied verifier report is not trusted merely because it exists.

## Materialization boundary

The materializer must:

- rerun the recorded verifier canonically;
- compare the supplied verifier report with replay;
- derive every release-required gate from policy;
- require a verified admissibility entry for every policy-derived gate;
- reject pre-existing release-required gate values;
- reject stubbed or scaffolded candidate state;
- reject policy or registry mismatch;
- fail without partially writing final state.

## Authority boundary

Candidate production, verification, and materialization determine whether evidence may enter final release state.

They do not replace the final strict gate-enforcement decision.

---

# Work package 5 — final release-boundary enforcement

## Status

```text
implementation_status: implemented
qualifying_current_run_execution: pending
```

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

Any missing, false, null, non-boolean, malformed, undeclared, or inaccessible required gate must block.

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

## Authority boundary

The final release decision remains the connected declared-policy path:

```text
recorded release evidence
→ final status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ PULSE_safe_pack_v0/tools/check_gates.py
→ primary CI allow/block decision
```

---

# Work package 6 — complete release-grade reference-package assembly

## Status

```text
implementation_status: implemented
qualifying_current_run_package: pending
```

## Goal

Assemble the complete current-run evidence chain into one fresh, digest-inventoried reference package after the standing release-authority path has executed.

## Historical bundle distinction

The repository may retain historical or advisory baseline bundles.

Those bundles do not substitute for the implemented complete-package artifact family:

```text
complete-release-grade-reference-package-${{ github.run_id }}-${{ github.run_attempt }}
```

The qualifying public run must use the complete package produced from its own run and attempt.

## Required package identity files

```text
package_digest_inventory_v0.json
run_metadata_v0.json
```

## Required current-run and pre-materialization evidence

```text
artifacts/required_gate_evidence_v0.json
artifacts/status_baseline.json
```

## Required recorded candidate and verifier state

```text
artifacts/recorded_release_candidates/
artifacts/recorded_release_candidate_index_v0.json
artifacts/release_evidence_input_manifest_v0.json
artifacts/recorded_release_evidence_verifier_v0.json
```

## Required current-run external evidence

```text
artifacts/external/llamaguard_raw.jsonl
artifacts/external/llamaguard_evaluator_manifest_v0.json
artifacts/external/llamaguard_summary.json
artifacts/external/llamaguard_summary.bundle.json
artifacts/external/llamaguard_summary.envelope.json
artifacts/external/llamaguard_attestation_verifier_v1.json
```

## Required final release state and trace

```text
artifacts/status.json
artifacts/release_decision_v0.json
artifacts/artifact_provenance_binding_v0.json
artifacts/release_authority_v0.json
artifacts/report_card.html
release-authority-audit-bundle/
```

## Supporting artifacts

The run may also preserve applicable supporting artifacts, including:

```text
artifacts/refusal_delta_summary.json
artifacts/status_summary_baseline.json
artifacts/status_summary.json
JUnit
SARIF
publication snapshot
public reader artifacts
reproduction instructions
```

Supporting artifacts do not replace any required package item.

## SLSA/VSA package boundary

The current package contract treats these artifacts as optional unless a later explicit strict-contract PR promotes them:

```text
artifacts/slsa/slsa_vsa_trusted_producer_input_packet_v0.json
artifacts/slsa/slsa_vsa_trusted_evidence_producer_report_v0.json
```

If neither is present, the current package may still satisfy the standing release-grade package contract.

If either is present, the packet/report pair must remain complete and internally consistent.

Do not enable:

```text
--require-slsa-vsa-trusted-producer
```

in the first controlled hosted-run track unless a separate reviewed PR first stages both artifacts and explicitly changes the package contract.

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

The package must contain a machine-readable digest inventory covering every package file except the inventory itself.

The inventory must record at least:

```text
relative path
SHA-256 digest
size in bytes
file count
algorithm identity
```

The inventory must exactly cover the assembled package surface.

An unlisted file, missing listed file, duplicate path, digest mismatch, or size mismatch must fail package acceptance.

## Atomic assembly

The complete package must be assembled into a fresh temporary directory.

The final package artifact becomes visible only after all required copy and inventory operations succeed.

A failed assembly must not leave a stale package that can be uploaded as if it were current.

## Authority boundary

Package assembly preserves the evidence-to-decision chain.

It does not create, change, or override the primary CI release decision.

---

# Work package 7 — structural package completeness preflight

## Status

```text
implementation_status: implemented
workflow_wiring_status: implemented
qualifying_current_run_report: pending
```

## Goal

Reject structurally incomplete, malformed, empty, stubbed, digest-inconsistent, or path-unsafe release-grade packages before the deeper package verifier runs.

## Implemented checker

```text
tools/check_release_grade_package_complete_v1.py
```

## Checker role

The checker is:

- read-only;
- non-authorizing;
- non-materializing;
- package-completeness-only;
- fail-closed for package acceptance.

It does not:

- write `status.json`;
- write status gates;
- call `check_gates.py`;
- materialize required gates;
- invoke policy materialization;
- create a release decision;
- create release authority.

## Structural checks

The checker verifies the applicable:

- required files;
- required non-empty directories;
- regular-file and non-symlink state;
- strict JSON object parsing;
- strict JSONL object parsing;
- duplicate JSON-key rejection;
- non-finite JSON-value rejection;
- non-empty required files;
- non-stub JSON content;
- non-stub report-card content;
- recorded candidate presence and accepted validation state;
- digest inventory schema identity;
- digest algorithm identity;
- per-file SHA-256 replay;
- per-file size replay;
- unique inventory paths;
- exact inventory coverage;
- output-path safety.

When SLSA/VSA trusted-producer packet/report artifacts are present, the checker also verifies their paired presence and cross-binding consistency.

## Output safety

The checker must refuse:

- `status.json` as an output name;
- output inside the checked package;
- symlink output;
- output through a symlinked parent;
- non-file output targets.

## Workflow order

The standing release-grade verification job preserves this order:

```text
download complete release-grade reference package
→ run structural completeness preflight
→ upload completeness report with always()
→ run independent deep package verifier
→ upload deep verification report
```

The completeness report artifact family is:

```text
release-grade-package-completeness-${{ github.run_id }}-${{ github.run_attempt }}
```

## Current SLSA/VSA option rule

The workflow does not currently pass:

```text
--require-slsa-vsa-trusted-producer
```

That omission is intentional under the current package contract.

## Completion distinction

```text
structural completeness = complete
≠ release authorized
```

A structurally complete package remains subject to the primary CI result and independent deep package verification.

---

# Work package 8 — independent complete-package verification

## Status

```text
implementation_status: implemented
workflow_wiring_status: implemented
qualifying_current_run_report: pending
```

## Goal

Verify the complete reference package separately from the advisory subset qualification checker and separately from the package producer.

## Qualification distinction

```text
advisory qualification checker OK
≠ structural package completeness
≠ independent complete-package verification
```

The advisory qualification checker remains:

- advisory;
- non-normative;
- non-blocking;
- limited to its declared input subset.

Do not silently expand it into a second authority engine.

## Implemented deep verifier

```text
PULSE_safe_pack_v0/tools/verify_release_grade_reference_package_v0.py
```

## Deep-verifier role

The package verifier is:

- read-only;
- non-authorizing;
- fail-closed for reference-package acceptance;
- independent of public reader surfaces.

It does not:

- produce or modify evidence;
- build recorded candidates;
- verify recorded evidence as an authority source in place of the standing verifier;
- materialize gates;
- call `check_gates.py` as a new release-decision path;
- authorize release.

## Verification surface

The deep verifier checks the applicable:

1. required package files and directories;
2. regular-file and non-symlink state;
3. strict JSON and JSONL parsing;
4. package digest inventory replay;
5. run metadata identity;
6. one consistent repository, commit, workflow, run, attempt, and candidate identity;
7. required-gate evidence presence;
8. baseline and final status identity consistency where recorded;
9. recorded candidate directory and index consistency;
10. input-manifest and verifier-report presence and binding;
11. LlamaGuard raw evidence, evaluator manifest, summary, envelope, bundle, and verifier-report bindings;
12. summary and raw-evidence digest consistency;
13. signer workflow and repository identity consistency;
14. release decision presence and run binding;
15. artifact-provenance binding presence and consistency;
16. release-authority audit/trace manifest presence;
17. report-card presence;
18. audit-bundle presence and package binding.

The verifier reviews the package produced after the standing candidate, verifier, materializer, and final enforcement path.

It must not create a parallel authority interpretation.

## Replay result

The verifier preserves a non-authoritative package-verification report.

The report may classify package verification as accepted or failed under its contract.

It must not state or imply that package verification itself authorizes release.

The verification report artifact family is:

```text
release-grade-reference-package-verification-${{ github.run_id }}-${{ github.run_attempt }}
```

## Completion distinction

```text
primary CI allow
+ structural package completeness passed
+ independent package verification passed
= candidate eligible to become the public reference record
```

The package-verification report does not retroactively change the primary CI result.

---

# Work package 9 — execute the controlled strict hosted run

## Status

```text
implementation_preconditions: present
controlled_hosted_run: pending
public_reference_record: pending
```

## Pre-flight conditions

Do not start the controlled hosted run until:

- all implementation PRs required by the standing path are merged;
- `main` CI is green;
- the exact LlamaGuard signer identity is checked in;
- no reachable release-grade wildcard signer remains on the LlamaGuard path;
- the selected detector is recorded as LlamaGuard;
- stale external outputs are cleared by workflow;
- the current-run producer lane is wired;
- the attestation bundle is persisted;
- the canonical envelope is generated;
- cryptographic verification is wired;
- the recorded candidate, verifier, and materializer path is wired after attestation;
- the complete package assembly job is wired;
- the structural completeness preflight is wired;
- independent complete-package verification is wired;
- all relevant tests pass;
- the run note remains unfilled;
- hosted model access is confirmed;
- the fixed source commit is recorded.

## Hosted-access preflight

Confirm before dispatch:

```text
HF_TOKEN repository secret is present
HF_TOKEN can access the pinned model
HF_TOKEN is scoped only to the hosted producer step
HF_TOKEN is not printed or uploaded
pinned model revision is available
expected runtime is acceptable
expected cost is acceptable
```

Missing provider or model access is a blocked precondition.

It must not be converted into a passing evidence state.

## Trigger

Use:

```text
event: workflow_dispatch
strict_external_evidence: true
llamaguard_evidence_mode: hosted_full_runtime
```

## Fixed source state

Record before starting:

```text
repository
main commit SHA
workflow path
selected detector
selected model
selected model revision
release candidate
policy path
policy digest
registry path
registry digest
threshold-policy path
threshold-policy digest
signer-policy path
signer-policy digest
```

Do not merge changes into the run's source commit while treating later artifacts as part of the same source state.

## Run-attempt rule

Each run attempt is a separate identity.

If an attempt fails:

- preserve the failed run for diagnosis;
- preserve its available diagnostic artifacts;
- do not rewrite it as successful;
- identify the first mechanical failure;
- fix the implementation through a new focused PR;
- add or strengthen a regression test;
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
structural package completeness = passed
independent package verification = passed
public record eligibility = yes
```

### Block candidate

A blocked run may still be valuable evidence.

It must preserve:

```text
primary CI decision = block
blocking reasons
failed producer, verifier, materializer, gate, or package path
available diagnostic artifacts
run identity
```

A blocked run is not the completed passing public reference record.

---

## Fail-closed conditions

The controlled run must fail or block on any of the following.

### Source and identity failures

- missing fixed source commit;
- missing exact signer identity;
- wildcard signer identity on the active LlamaGuard path;
- wrong repository;
- wrong workflow;
- wrong source commit;
- wrong release candidate;
- mixed run IDs;
- mixed run numbers;
- mixed run attempts;
- stale release-candidate identity;
- policy digest mismatch;
- registry digest mismatch;
- signer-policy digest mismatch;
- threshold-policy digest mismatch.

### Provider and evaluator failures

- hosted provider unavailable;
- missing or unauthorized model access;
- missing secret;
- evaluator installation failure;
- pinned model revision unavailable;
- evaluator timeout;
- evaluator non-zero exit;
- no raw output;
- malformed evaluator output;
- unsupported classification value.

### External evidence failures

- no supported external summary;
- stale raw evidence;
- stale evaluator manifest;
- stale summary;
- both JSON and JSONL summary forms discovered for one detector;
- malformed summary;
- summary schema failure;
- semantic failure;
- metric threshold failure;
- raw-evidence path escape;
- symlinked external artifact;
- raw-evidence digest mismatch;
- evaluator digest mismatch;
- dataset digest mismatch;
- missing envelope;
- envelope schema failure;
- summary-reference mismatch;
- summary-ID mismatch;
- summary-digest mismatch;
- signing identity mismatch;
- missing attestation bundle;
- wrong attestation predicate;
- wrong GitHub OIDC issuer;
- failed or empty GitHub attestation verification;
- missing attestation-verifier report.

### Candidate and verifier failures

- missing canonical candidate;
- extra non-canonical candidate;
- modified candidate;
- substituted candidate;
- candidate index mismatch;
- full manifest schema failure;
- canonical candidate replay mismatch;
- recorded verifier failure;
- supplied verifier report mismatch with canonical replay;
- empty evidence results;
- empty relation results;
- missing gate admissibility;
- incomplete policy gate coverage;
- producer trust inferred from self-declared fields.

### Materialization failures

- pre-existing release-required gate;
- stubbed candidate state;
- scaffolded candidate state;
- policy mismatch;
- registry mismatch;
- current-run identity mismatch;
- subject identity mismatch;
- partial materialization attempt;
- baseline-to-final unauthorized mutation.

### Final enforcement failures

- invalid final `status.json`;
- missing workflow-effective gate;
- false required gate;
- null required gate;
- non-boolean required gate;
- wrong required gate set;
- manually reconstructed divergent gate list;
- strict checker failure;
- recorded decision mismatch;
- primary CI result other than the expected allow for a passing reference candidate.

### Package assembly failures

- missing required artifact;
- empty required artifact;
- stale artifact;
- symlinked artifact;
- path escape;
- duplicate package path;
- digest mismatch;
- size mismatch;
- incomplete digest inventory;
- inventory coverage mismatch;
- mixed run identity;
- incomplete audit bundle;
- Ledger/status mismatch;
- provenance-binding failure;
- stale package left by a failed assembly.

### Package verification failures

- structural completeness failure;
- unsafe completeness-report output path;
- deep package-verification failure;
- package metadata mismatch;
- external evidence binding mismatch;
- candidate/index/manifest inconsistency;
- release decision binding mismatch;
- provenance binding inconsistency;
- missing verification report.

### Public-record failures

- run note filled before the actual run;
- intended values substituted for recorded values;
- missing public run identity;
- missing artifact references;
- missing required SHA-256 digests;
- blocked run described as completed passing reference;
- new DOI or release metadata introduced as a substitute for runtime proof.

A block result caused by these conditions is valid fail-closed behavior.

It is not a completed passing public reference run.

---

## Required tests before execution

Run the relevant standing tests, including:

```text
python tests/test_llamaguard_current_run_workflow_wiring_v0.py
python tests/test_check_external_summary_attestation_v1.py
python tests/test_release_grade_candidate_evidence_path_v0.py
python tests/test_release_evidence_input_manifest_v0.py
python tests/test_check_recorded_release_evidence_v0.py
python tests/test_materialize_release_required_from_verifier_v0.py
python tests/test_check_release_grade_reference_run_v0.py
python tests/test_release_grade_reference_qualification_advisory_boundary_v0.py
python tests/test_release_grade_reference_package_assembly_wiring_v0.py
python tests/test_release_grade_reference_package_verification_wiring_v0.py
python tests/test_check_release_grade_package_complete_v1.py
python tests/test_release_grade_package_completeness_checker_ci_boundary_v1.py
python tests/test_release_grade_package_completeness_workflow_wiring_v1.py
python tests/test_artifact_provenance_binding_ci_wiring_smoke.py
python tests/test_artifact_provenance_binding_attestation_wiring_smoke.py
python tests/test_tools_tests_list_smoke.py
git diff --check
```

The complete normal CI suite remains the final preflight for the checked-in source state.

The targeted list does not replace full CI.

---

## Acceptance criteria

The first public release-grade reference run is complete only when all of the following are true.

### Source and run identity

- the source commit is concrete;
- the workflow path is concrete;
- the workflow run ID is concrete;
- the workflow run number is concrete;
- the workflow run attempt is concrete;
- the run key is concrete;
- the release candidate is concrete;
- the selected model and revision are concrete;
- the policy, registry, signer-policy, and threshold-policy digests are concrete;
- every required artifact belongs to that same source, run, and attempt.

### Candidate state

- `metrics.run_mode` is `prod`;
- `diagnostics.gates_stubbed` is literal `false`;
- `diagnostics.scaffold` is literal `false`;
- current-run required-gate evidence is present;
- all required-gate evaluators completed;
- `status_baseline.json` is preserved before materialization;
- no release-required gate is pre-materialized into the candidate.

### External evidence

- current-run LlamaGuard raw evidence exists;
- the evaluator manifest exists and validates;
- the canonical summary exists and validates;
- detector semantics pass;
- the canonical metric and threshold pass;
- dataset binding passes;
- evaluator binding passes;
- raw-evidence digest binding passes;
- summary digest binding passes;
- the canonical envelope exists and validates;
- the exact LlamaGuard workflow signer identity matches;
- no reachable wildcard identity is accepted;
- the attestation bundle exists;
- cryptographic GitHub attestation verification succeeds;
- the envelope and attestation-verifier report agree.

### Candidate and verifier path

- canonical candidates are produced;
- the candidate index is produced;
- the full input manifest validates;
- canonical candidate replay matches;
- recorded verification succeeds;
- canonical verifier replay matches;
- all required relations are satisfied;
- every policy-derived release-required gate has verified admissibility.

### Materialization and enforcement

- release-required materialization succeeds atomically;
- the baseline-to-final delta is permitted;
- final `status.json` validates;
- the workflow-effective required gate set is derived from declared policy;
- every required gate exists;
- every required gate is literal boolean `true`;
- `PULSE_safe_pack_v0/tools/check_gates.py` succeeds;
- the primary CI decision is recorded as `allow`.

### Decision and trace artifacts

- `release_decision_v0.json` exists;
- `artifact_provenance_binding_v0.json` exists and verifies;
- `release_authority_v0.json` exists as an audit/trace sidecar and validates;
- Quality Ledger is rendered from final status;
- Quality Ledger / final-status parity passes;
- the release-authority audit bundle is complete.

### Complete package

- the complete package is assembled in a fresh directory;
- every required artifact is present;
- every required file is non-empty and regular;
- no required path is symlinked;
- no path escapes the package root;
- the package digest inventory is complete;
- the inventory exactly covers package files except itself;
- every recorded digest and size matches;
- no stale artifact is present;
- no fixture substitutes for runtime evidence;
- structural package completeness succeeds;
- independent deep package verification succeeds;
- reconstruction agrees with the recorded primary CI decision.

### Public record

- public workflow and artifact references exist;
- required SHA-256 digests are recorded;
- the run note is completed from actual workflow metadata and artifacts;
- README and the documentation index link the completed record;
- the run is clearly labeled as the first completed public non-stubbed release-grade reference run;
- the record states what was proven and what was not proven.

---

## Run-note completion

After the controlled run, structural completeness check, and independent complete-package verification succeed, complete:

```text
docs/RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md
```

Populate it only from actual artifacts and workflow metadata.

Required record classes include:

```text
repository
source ref
source commit
workflow path
workflow run ID
workflow run number
workflow run attempt
workflow URL
workflow inputs
run mode
release candidate
model identity and revision
policy identity and digest
registry identity and digest
signer-policy identity and digest
threshold-policy identity and digest
exact signer identity
attestation verification result
workflow-effective gate set
candidate and verifier state
materialization state
primary CI decision
advisory qualification state
structural completeness result
independent package-verification result
public artifact references
SHA-256 digests
what was proven
what was not proven
```

Do not fill the run note from intended values.

Do not use `pending` placeholders in a record presented as complete.

The run note documents proof.

It does not replace:

```text
status.json
declared policy
materialized required gates
PULSE_safe_pack_v0/tools/check_gates.py
primary CI allow/block result
```

## Public entrypoint update

Only after the run note is completed from the actual run:

- update the README from pending to completed;
- update `docs/INDEX.md`;
- link the public workflow run;
- link the complete reference package;
- link the final status and Quality Ledger where appropriate;
- record package and key artifact digests.

These publication changes are post-run recording work.

They do not create the run.

They do not require a new DOI, GitHub Release, or version tag.

---

## Implementation closure record and remaining sequence

The original work packages are retained in this document because the work path is part of the artifact and remains necessary for review.

The checked-in implementation history includes these closure points:

| Work surface | Recorded implementation checkpoint | Current state |
|---|---|---|
| Current-run LlamaGuard raw-evidence lane | PR #2629 | Implemented capability |
| Exact LlamaGuard workflow identity, bundle, and envelope wiring | PR #2630 | Implemented capability |
| Attested LlamaGuard evidence into recorded release path | PR #2631 | Implemented capability |
| Complete package assembly | PR #2632 | Implemented capability |
| Independent complete-package verification | PR #2633 | Implemented capability |
| Complete current-run `gates.required` evaluator coverage | PR #2635 | Implemented capability |
| Structural package completeness checker | PR #2709 | Implemented capability |
| Completeness test registration and CI boundary | PRs #2710–#2711 | Implemented guardrail |
| Completeness preflight workflow wiring | PR #2712 | Implemented capability |
| SLSA/VSA trusted-producer construction and validation chain | PRs #2694–#2708 | Implemented non-active candidate path |

These implementation checkpoints do not constitute the missing qualifying hosted run.

The remaining sequence is:

### Stage 1 — recovery and fixed-source preflight

```text
restore the full operational plan
→ confirm main CI
→ confirm hosted access
→ record fixed source identity
→ confirm exact signer and attestation boundary
```

### Stage 2 — controlled hosted execution

```text
workflow_dispatch
strict_external_evidence = true
llamaguard_evidence_mode = hosted_full_runtime
```

### Stage 3 — defect-driven repair only if required

Each repair PR must contain:

```text
one reproduced mechanical defect
one bounded correction
one regression test
one authority-boundary statement
```

Do not combine runtime repair with:

```text
DOI changes
Zenodo changes
CITATION changes
README title changes
unrelated workflow cleanup
SLSA/VSA policy promotion
new gate families
```

### Stage 4 — post-run record PR

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
exact LlamaGuard signer identity contract
standing complete-package assembler role
structural completeness checker non-authority
independent package verifier non-authority
```

Documentation, UI, reader, or publication concerns must not alter the normative decision core.

A passing dashboard, report, comment, badge, or review label must not be promoted into release permission.

---

## SLSA/VSA boundary

The SLSA/VSA recorded-intake candidate path and trusted-producer construction chain are retained as a separate, non-active track.

Current state:

```text
recorded-intake candidate proof = complete
trusted-producer input-packet contract = implemented
trusted-producer input-packet validator = implemented
trusted-producer input-packet builder = implemented
trusted-evidence producer-report contract = implemented
trusted-evidence producer-report validator = implemented
packet-to-report builder = implemented
generated packet-to-report smoke = implemented
workflow release-required activation = not performed
```

For the first controlled hosted release-grade run:

```text
SLSA/VSA candidate proof
= preserved

SLSA/VSA trusted-producer artifacts
= optional under the current package contract

SLSA/VSA release-required activation
= out of scope
```

A future current-run SLSA/VSA integration must proceed through separate bounded PRs:

```text
current-run VSA evidence production
→ trusted input packet production
→ input-packet validation
→ trusted producer report production
→ report validation
→ package staging
→ strict package requirement, if explicitly approved
→ separate policy promotion decision, if explicitly approved
```

Any future release-required promotion must include:

- explicit policy effect;
- current-run evidence production;
- artifact subject and digest binding;
- policy identity and policy digest binding;
- verifier identity binding;
- freshness enforcement;
- previous-run reuse rejection;
- negative fail-closed tests;
- rollback behavior;
- changelog coverage;
- a separate PR title and review boundary.

SLSA/VSA promotion must not be bundled with the controlled LlamaGuard reference-run record.

---

## Non-goals

This plan does not:

- build a second release-decision engine;
- replace the recorded verifier;
- replace the materializer;
- replace `PULSE_safe_pack_v0/tools/check_gates.py`;
- make attestation alone sufficient for release;
- make package completeness release authority;
- make package verification release authority;
- make advisory qualification release authority;
- make the Quality Ledger release authority;
- accept wildcard release-grade signers on the LlamaGuard path;
- use fixture evidence as current-run evidence;
- require every supported external detector in the first run;
- activate SLSA/VSA as release-required;
- create a tag merely to force execution;
- create a GitHub Release or Zenodo record as runtime proof;
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

HPC outputs remain diagnostic unless separately admitted through recorded evidence, declared policy, materialized gates, and strict enforcement.

---

## Completion state

This plan is complete only when:

```text
exact LlamaGuard signer identity = implemented
current-run LlamaGuard producer = implemented
attestation bundle and envelope lane = implemented
strict candidate/verifier/materializer wiring = implemented
complete package assembly = implemented
structural package completeness preflight = implemented
independent complete-package verification = implemented
controlled hosted_full_runtime run = successful
primary CI decision = allow
qualifying package checks = passed
public run record = completed
```

The current checked-in state is:

```text
implementation layers present
controlled qualifying public run pending
```

The public reference state remains:

```text
first_completed_public_non_stubbed_release_grade_run = pending
```

---

## Minimal mechanical anchor

```text
fixture success
≠ current-run evidence

producer implemented
≠ hosted execution completed

summary produced
≠ summary verified

attestation wiring implemented
≠ qualifying current-run attestation verified

attestation verified
≠ candidate admitted

candidate admitted
≠ gate materialized

gate materialized
≠ release authority by itself

advisory qualification
≠ structural package completeness

structural package completeness
≠ independent package verification

package verification
≠ primary CI authority

planned run
≠ completed public run
```

The remaining forward path is:

```text
fixed source commit
→ hosted-access preflight
→ controlled hosted_full_runtime execution
→ current-run attested LlamaGuard evidence
→ existing replay-bound admission
→ existing policy-derived materialization
→ existing strict final enforcement
→ complete package assembly
→ structural completeness preflight
→ independent package verification
→ public run record
→ recorded baseline for later scaling
```

## Change-control note

This document update restores and realigns the full operational plan.

It is documentation-only.

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
- citation identity;
- release metadata;
- release-authority semantics.

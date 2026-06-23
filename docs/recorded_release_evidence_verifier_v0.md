# Recorded release-evidence verifier v0

## Purpose

This document defines the implemented recorded release-evidence verification layer used before release-required gate materialization.

The implemented release-grade evidence path is:

```text
current-run required-gate evidence
→ non-stubbed candidate release state
→ canonical candidate production
→ runtime release-evidence input manifest
→ canonical candidate replay
→ recorded release-evidence verification
→ recorded release-evidence verifier report
→ canonical verifier replay by the materializer
→ policy-derived release-required gate materialization
→ final status.json
→ workflow-effective materialized required gate set
→ PULSE_safe_pack_v0/tools/check_gates.py
→ primary CI allow/block release decision
```

The verifier determines whether candidate evidence is sufficiently bound to:

```text
run identity
→ subject identity
→ declared policy and registry
→ canonical producer output
→ raw evidence
→ expected relation bindings
→ declared release-required gates
```

The verifier is a mandatory evidence-admission prerequisite in the release-grade path.

It does not:

- modify `status.json`;
- materialize release-required gates;
- replace declared policy;
- replace the primary CI workflow;
- replace `PULSE_safe_pack_v0/tools/check_gates.py`;
- independently create release authority.

## Status

- stage: implemented and wired into the release-grade path
- normative release-decision role: none
- evidence role: mandatory release-grade evidence-admission prerequisite
- verifier tool: `PULSE_safe_pack_v0/tools/check_recorded_release_evidence_v0.py`
- report schema: `recorded_release_evidence_verifier_v0`
- report version: `0.2.0`
- input manifest schema: `release_evidence_input_manifest_v0`
- expected run mode: `prod`
- expected policy set: `required+release_required`
- output artifact: `PULSE_safe_pack_v0/artifacts/recorded_release_evidence_verifier_v0.json`
- canonical candidate replay: implemented
- verified producer-trust derivation: implemented
- relation-binding verification: implemented
- gate-materialization admissibility: implemented
- canonical verifier replay before materialization: implemented
- verifier-bound release-required materialization: implemented
- final release evaluator: `PULSE_safe_pack_v0/tools/check_gates.py`
- current-run attested external-evidence production lane: pending
- exact operational release-grade signer identity: pending
- complete release-grade reference packaging: pending

Test coverage includes:

```text
tests/test_check_recorded_release_evidence_v0.py
tests/test_release_grade_candidate_evidence_path_v0.py
tests/test_materialize_release_required_from_verifier_v0.py
tests/test_check_external_summary_attestation_v1.py
```

The relevant tools are registered in:

```text
ci/tools-tests.list
```

## Why this exists

Local files can exist and still be:

- stale;
- incomplete;
- malformed;
- substituted;
- detached from the current run;
- detached from the current commit;
- detached from the current release candidate;
- detached from the declared policy;
- produced by an unverified path;
- bound to the wrong raw evidence;
- associated with the wrong release-required gate.

The following declarations are not sufficient by themselves:

```text
provenance.trusted_producer = true
status = verified
admissible = true
canonical-looking filename
matching digest recorded inside an unverified object
```

Producer trust is not accepted from self-declaration.

A supplied verifier report is not accepted as authority by declaration.

The evidence path proves its claims through canonical replay.

## Inputs

The verifier consumes:

```text
PULSE_safe_pack_v0/artifacts/release_evidence_input_manifest_v0.json
```

and a repository root used to resolve:

- the declared gate policy;
- the gate registry;
- current-run candidate artifacts;
- raw evidence artifacts;
- checked-in producer code;
- canonical producer inputs;
- schemas and threshold files used by candidate production.

The manifest is a declaration surface.

It specifies what must be verified.

It is not proof that its declarations are satisfied.

## Manifest contract

The verifier requires a valid and non-ambiguous manifest.

Duplicate JSON keys fail closed.

The manifest must contain non-empty:

```text
run_identity
subject
policy_binding
registry_binding
candidate_evidence
expected_relation_bindings
expected_gate_materialization
```

### Run identity

The run identity must satisfy:

```text
run_identity.git_sha = concrete 40-hex commit SHA
run_identity.run_key = non-empty current-run identity
run_identity.run_mode = prod
```

### Subject identity

The subject must satisfy:

```text
subject.commit_sha = run_identity.git_sha
```

### Policy binding

The policy binding must satisfy:

```text
policy_binding.policy_set = required+release_required
policy_binding.policy_path = non-empty repository-relative path
policy_binding.policy_sha256 = concrete SHA-256
```

### Registry binding

The registry binding must satisfy:

```text
registry_binding.registry_path = non-empty repository-relative path
registry_binding.registry_sha256 = concrete SHA-256
```

The current policy and registry files are loaded from the repository and hashed again.

Their actual digests must match the manifest.

Duplicate YAML keys fail closed.

Every release-required gate referenced by candidate evidence or relation bindings must exist in:

```text
pulse_gate_policy_v0.yml
pulse_gate_registry_v0.yml
```

## Candidate manifest entries

Every candidate evidence entry must declare:

```text
verification_required = true
```

Each entry must include:

```text
path
expected_sha256
schema_version
subject_binding
required_for_gates
provenance_expectations
```

The provenance expectation must require:

```text
trusted_producer_required = true
```

This requirement does not mean that a candidate can prove producer trust by containing its own trusted-producer field.

Producer trust is established only through canonical replay equality.

## Canonical candidate replay

Before individual candidate admission, the verifier reruns the checked-in recorded-release candidate producer in memory.

The replay uses the same canonical producer implementation and repository inputs as normal candidate production.

The replay does not:

- clear candidate output directories;
- write candidate envelopes;
- replace the candidate index;
- modify `status.json`;
- materialize release-required gates;
- create release authority.

The replayed candidate set must exactly match the candidate set declared in the runtime manifest.

The verifier rejects:

- missing canonical candidates;
- additional non-canonical candidates;
- missing candidate-index entries;
- extra candidate-index entries;
- modified candidate envelopes;
- substituted candidate envelopes;
- producer metadata that differs from canonical production.

Only the non-authoritative creation timestamp representation may be normalized for deterministic comparison.

All mechanically relevant candidate fields must remain equal.

## Producer-trust verification

A candidate envelope may contain:

```text
provenance.trusted_producer = true
```

but that field does not independently prove producer trust.

The verifier sets:

```text
trusted_producer_verified = true
```

only when the supplied candidate envelope matches the envelope recomputed by canonical candidate replay.

Therefore:

```text
self-declared trusted producer
≠ verified producer trust
```

Verified producer trust requires:

```text
current repository state
+ current-run evidence
+ checked-in canonical producer
+ replayed candidate envelope
= supplied candidate envelope
```

## Candidate evidence verification

Each candidate is checked for:

1. repository-relative artifact presence;
2. regular-file status;
3. artifact SHA-256 equality with the manifest;
4. expected schema-version equality;
5. current-run identity equality;
6. subject-binding equality;
7. commit binding to the manifest subject;
8. policy-set equality;
9. policy-digest equality;
10. canonical candidate replay equality;
11. verified producer trust;
12. raw-evidence path presence;
13. raw-evidence SHA-256 equality;
14. exact `required_for_gates` equality;
15. membership of every declared gate in policy and registry.

A candidate is marked:

```text
status = verified
```

only when all candidate checks succeed.

Otherwise it remains:

```text
status = failed
```

## External-summary candidate boundary

External-summary-specific admission occurs during canonical candidate production.

For release-grade external candidates, the canonical producer must enforce the applicable:

- external-summary schema;
- detector-specific tool identity;
- detector-specific metric identity;
- threshold reference;
- threshold semantics;
- aggregate result;
- subject and commit binding;
- summary digest binding;
- raw-evidence digest binding;
- external-summary envelope binding;
- signer-policy admission;
- cryptographic attestation verification.

The recorded release-evidence verifier does not accept a separately supplied assertion that these checks succeeded.

Instead, it replays the same checked-in candidate producer from the current repository and current-run evidence.

The replayed candidate envelope must match the supplied candidate envelope.

Therefore:

```text
external-summary declaration
≠ admitted external evidence
```

The cryptographic attestation-verification capability is implemented.

The exact operational signer identity and current-run attested external-evidence producer lane remain pending.

## Relation-binding verification

After candidate verification, the verifier checks the manifest-declared relations.

Supported relation types are:

```text
artifact_to_subject
artifact_to_gate
```

### `artifact_to_subject`

An `artifact_to_subject` relation must:

- use verified candidate evidence;
- bind to the current run;
- bind to the current subject;
- target:

```text
subject.commit_sha
```

- preserve the candidate subject binding.

### `artifact_to_gate`

An `artifact_to_gate` relation must:

- use verified candidate evidence;
- target a gate declared in `gates.release_required`;
- target a registry-backed gate;
- use the exact target form:

```text
gate.<gate_id>
```

A relation is satisfied only when:

- its source candidate is verified;
- its expected gate exists;
- its binding type is supported;
- its target is mechanically exact.

## Gate-materialization admissibility

For each declared release-required gate, the verifier checks:

```text
expected_value = true
policy_relation = release_required
materialization_allowed_without_verifier = false
```

The gate entry must contain non-empty:

```text
candidate_evidence_ids
relation_binding_ids
```

Every listed candidate evidence ID must be verified.

Every listed relation binding ID must be satisfied.

Every candidate used for a gate must have at least one satisfied `artifact_to_gate` relation targeting that exact gate.

The verifier produces:

```text
admissible = true
```

only when all gate-materialization prerequisites succeed.

Admissibility does not itself write the gate into `status.json`.

## Output artifact

The verifier writes:

```text
PULSE_safe_pack_v0/artifacts/recorded_release_evidence_verifier_v0.json
```

The report contains:

```text
schema_version
report_version
status
manifest
run_identity
subject
policy_binding
registry_binding
verified_subjects
evidence_results
relation_binding_results
gate_materialization_admissibility
errors
```

The only top-level verifier statuses are:

```text
verified
failed
```

The report is:

```text
status = verified
```

only when the complete error list is empty.

Missing, malformed, mismatched, or incomplete evidence produces:

```text
status = failed
```

and a non-zero CLI result.

## Materializer binding

The verifier report is consumed by:

```text
PULSE_safe_pack_v0/tools/materialize_release_required_from_verifier_v0.py
```

The materializer does not trust the supplied verifier report as a standalone authority object.

Before materialization, it requires:

```text
--manifest
--repo-root
```

and reruns:

```text
check_recorded_release_evidence(...)
```

from the supplied manifest and repository root.

The materializer requires:

- canonical verifier replay status `verified`;
- an empty canonical replay error list;
- non-empty evidence results;
- non-empty relation-binding results;
- exact equality between the supplied report and canonical verifier replay after canonical manifest-path normalization;
- canonical manifest-path resolution;
- candidate-status run identity matching the verifier;
- candidate-status subject identity matching the verifier;
- `run_mode = prod`;
- matching policy path;
- matching policy digest;
- no stubbed release evidence;
- no scaffolded release evidence;
- no pre-existing release-required gate state;
- explicit admissibility for every policy-derived release-required gate.

All later admission checks consume the freshly replayed canonical report.

They do not consume the supplied report as an independent trust source.

Therefore:

```text
supplied verifier report
≠ trusted verifier result
```

A trusted verifier result requires:

```text
supplied manifest
+ current repository root
+ canonical verifier replay
= supplied verifier report
```

## Materialization behavior

After every admission check succeeds, the materializer writes literal `true` values for the policy-derived `release_required` gate set into:

```text
status["gates"]
```

Failed admission must not partially mutate candidate release state.

The materializer works on a detached gate-state copy and writes output only after the complete admission path succeeds.

Therefore:

```text
failed verifier replay
→ no release-required materialization

modified verifier report
→ no release-required materialization

empty evidence or relation results
→ no release-required materialization

incomplete admissibility
→ no release-required materialization

run or subject mismatch
→ no release-required materialization

policy mismatch
→ no release-required materialization

stubbed or scaffolded state
→ no release-required materialization
```

## Mechanical layer separation

The verifier and materializer occupy different layers:

```text
recorded release-evidence verifier
= candidate, evidence, relation, and admissibility verification

release-required materializer
= policy-derived gate-state materialization

PULSE_safe_pack_v0/tools/check_gates.py
= strict final gate enforcement
```

The verifier report is not the final release decision.

Canonical candidate replay is not the final release decision.

Canonical verifier replay is not the final release decision.

Materialized gate state is not the final release decision by itself.

## Authority boundary

The normative release path remains:

```text
recorded release evidence
→ final status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ PULSE_safe_pack_v0/tools/check_gates.py
→ primary CI workflow
→ primary CI allow/block release decision
```

The following are non-authorizing carriers:

- candidate envelopes;
- candidate indexes;
- verifier reports;
- attestation reports;
- materializer diagnostics;
- `release_authority_v0.json`;
- `release_decision_v0.json`;
- `artifact_provenance_binding_v0.json`;
- Quality Ledger;
- audit bundles;
- dashboards;
- Pages;
- reference-run notes.

They may preserve, verify, bind, explain, or publish evidence.

They do not independently authorize, block, or override release.

## CLI

Run the verifier from the repository root:

```bash
python PULSE_safe_pack_v0/tools/check_recorded_release_evidence_v0.py \
  --manifest PULSE_safe_pack_v0/artifacts/release_evidence_input_manifest_v0.json \
  --repo-root . \
  --out-json PULSE_safe_pack_v0/artifacts/recorded_release_evidence_verifier_v0.json
```

Successful verification returns:

```text
OK: recorded release-evidence verification satisfied
Verifier report written to <path>
```

Failed verification returns a non-zero exit code and:

```text
ERRORS (fail-closed):
 - ...
Verifier report written to <path>
```

## Failure behavior

The verifier fails closed on, among other conditions:

- missing manifest;
- malformed manifest;
- duplicate JSON keys;
- wrong manifest schema version;
- non-production run mode;
- subject and run commit mismatch;
- wrong policy set;
- missing policy or registry path;
- policy or registry digest mismatch;
- duplicate YAML keys;
- unknown release-required gate IDs;
- empty candidate set;
- empty relation-binding set;
- empty expected-materialization set;
- canonical candidate replay failure;
- missing canonical candidates;
- extra non-canonical candidates;
- candidate-index mismatch;
- modified candidate envelopes;
- substituted candidate envelopes;
- substituted producer metadata;
- candidate artifact digest mismatch;
- candidate schema mismatch;
- run-identity mismatch;
- subject-binding mismatch;
- policy-binding mismatch;
- self-declared producer trust without replay equality;
- raw-evidence digest mismatch;
- `required_for_gates` mismatch;
- unsatisfied relation binding;
- incorrect relation target;
- incomplete gate-target relations;
- non-literal expected gate value;
- wrong policy relation;
- materialization allowed without verifier;
- missing candidate IDs;
- missing relation IDs;
- any non-empty verifier error list.

## Non-goals

The recorded release-evidence verifier is not:

- a current-run evidence producer;
- an external detector;
- an external-summary signer;
- an attestation issuer;
- a new release policy;
- a new release gate;
- a replacement for `status.json`;
- a replacement for the release-required materializer;
- a replacement for `PULSE_safe_pack_v0/tools/check_gates.py`;
- a dashboard-derived decision;
- a reader-surface decision;
- a second release-decision engine;
- an independent break-glass path;
- complete reference-package verification;
- a completed public reference-run record.

## Current operational boundary

The following are implemented:

```text
current-run required-gate evidence production
canonical candidate production
canonical candidate replay
recorded release-evidence verification
verified producer-trust derivation
relation-binding verification
gate-materialization admissibility
canonical verifier replay
verifier-bound release-required materialization
cryptographic external-summary attestation verification capability
```

The next work is not to rebuild the verifier.

The remaining operational sequence is:

```text
exact operational release-grade signer identity
→ current-run attested external evidence
→ complete evidence-chain packaging
→ complete-package verification
→ controlled strict release-grade execution
→ completed public reference-run record
```

The first completed run must be recorded in:

```text
docs/RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md
```

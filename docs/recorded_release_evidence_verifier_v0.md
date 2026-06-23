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
→ declared gate-materialization entries
```

The verifier is a mandatory evidence-admission prerequisite in the release-grade path.

It does not:

- modify `status.json`;
- materialize release-required gates;
- establish complete policy-gate coverage by itself;
- replace full input-manifest schema validation;
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
- expected manifest schema-version identity: `release_evidence_input_manifest_v0`
- expected run mode: `prod`
- expected policy set: `required+release_required`
- output artifact: `PULSE_safe_pack_v0/artifacts/recorded_release_evidence_verifier_v0.json`
- canonical candidate replay: implemented
- replay-derived producer-trust verification: implemented
- relation-binding verification: implemented
- manifest-declared gate admissibility: implemented
- full policy gate coverage in the verifier alone: not implemented
- full policy gate coverage in the materializer: implemented
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

The relevant tools and tests are registered in:

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

A manifest entry is not accepted merely because it claims that verification is required.

A declared gate relation is not accepted merely because it appears in the manifest.

The evidence path proves its claims through current-run binding and canonical replay.

## Inputs

The verifier consumes:

```text
PULSE_safe_pack_v0/artifacts/release_evidence_input_manifest_v0.json
```

and a repository root used to resolve the mechanically consumed:

- declared gate-policy path;
- gate-registry path;
- candidate artifact paths;
- raw-evidence paths;
- checked-in candidate producer;
- candidate producer inputs;
- policy and registry files used during verification.

The manifest is a declaration surface.

It specifies the evidence, relations, and gate-materialization entries that the verifier is asked to inspect.

It is not proof that those declarations are satisfied.

## Manifest validation boundary

The verifier requires a JSON object that is parseable without duplicate object keys and contains the fields consumed by its implemented checks.

It checks:

```text
schema_version = release_evidence_input_manifest_v0
```

It reads these object sections:

```text
run_identity
subject
policy_binding
registry_binding
candidate_evidence
expected_relation_bindings
expected_gate_materialization
```

The following sections must be non-empty:

```text
candidate_evidence
expected_relation_bindings
expected_gate_materialization
```

The remaining object sections are subject to the field-level checks described below.

Duplicate JSON object keys fail closed.

The recorded release-evidence verifier does not invoke:

```text
PULSE_safe_pack_v0/tools/check_release_evidence_input_manifest_v0.py
```

and does not independently establish complete conformance to:

```text
schemas/release_evidence_input_manifest_v0.schema.json
```

Schema-required fields that are not consumed by the recorded verifier are outside this verifier's direct validation boundary.

For example, a full-schema contract may require additional document or metadata fields that are not used by the recorded verifier's mechanical admission logic.

Therefore:

```text
mechanically accepted by the recorded verifier
≠ fully schema-validated input manifest
```

A claim of complete input-manifest schema validity requires the separate schema checker or another explicitly equivalent full-schema validation path.

The recorded verifier's direct manifest contract is limited to the fields and bindings it mechanically reads and checks.

## Run identity

The mechanically consumed run identity must satisfy:

```text
run_identity.git_sha = concrete 40-hex commit SHA
run_identity.run_key = non-empty current-run identity
run_identity.run_mode = prod
```

The verifier rejects a non-production run mode for this release-grade path.

## Subject identity

The mechanically consumed subject must include:

```text
subject.commit_sha
```

The subject commit must satisfy:

```text
subject.commit_sha = run_identity.git_sha
```

The verifier records the corresponding verified-subject fields in its report.

## Policy binding

The mechanically consumed policy binding must satisfy:

```text
policy_binding.policy_set = required+release_required
policy_binding.policy_path = non-empty path text
policy_binding.policy_sha256 = concrete SHA-256
```

The verifier resolves the declared policy path from the supplied repository root.

It reads the current policy file and recomputes its digest.

The actual digest must match:

```text
policy_binding.policy_sha256
```

The policy must expose:

```text
gates.release_required
```

as a non-empty gate list.

Duplicate YAML mapping keys fail closed.

## Registry binding

The mechanically consumed registry binding must satisfy:

```text
registry_binding.registry_path = non-empty path text
registry_binding.registry_sha256 = concrete SHA-256
```

The verifier resolves the declared registry path from the supplied repository root.

It reads the current registry file and recomputes its digest.

The actual digest must match:

```text
registry_binding.registry_sha256
```

The registry must expose a non-empty top-level:

```text
gates
```

mapping.

Duplicate YAML mapping keys fail closed.

Every gate referenced by a candidate, relation, or manifest-declared materialization entry is checked for membership in:

```text
policy.gates.release_required
```

and the gate registry.

This verifier-side membership check does not prove that the manifest declares every gate in the policy.

Complete policy coverage is a later materializer responsibility.

## Candidate manifest entries

Every candidate evidence entry must be an object and must declare:

```text
verification_required = true
```

Each entry is mechanically expected to provide:

```text
path
expected_sha256
schema_version
subject_binding
required_for_gates
provenance_expectations
```

The provenance expectation must declare:

```text
trusted_producer_required = true
```

The `required_for_gates` value must be a non-empty array of unique, non-empty gate IDs.

The candidate manifest entry's gate IDs must belong to the active release-required policy set and the registry.

The manifest path and digest declarations are inputs to verification.

They do not establish candidate validity by themselves.

## Canonical candidate replay

Before individual candidate admission, the verifier reruns the checked-in recorded-release candidate producer in memory.

The replay uses the current repository state and current candidate-producer inputs.

The replay does not:

- clear candidate output directories;
- write candidate envelopes;
- replace on-disk candidate artifacts;
- replace the on-disk candidate index;
- modify `status.json`;
- materialize release-required gates;
- create release authority.

The canonical replay returns:

- a replayed candidate mapping;
- a replayed candidate-index representation;
- replay errors, if any.

The replayed candidate IDs must exactly match the candidate IDs declared in:

```text
manifest.candidate_evidence
```

The verifier rejects:

- canonical candidates missing from the manifest;
- manifest candidates absent from canonical replay;
- canonical replay failure;
- an internally inconsistent replayed index;
- modified supplied candidate envelopes;
- substituted supplied candidate envelopes;
- mechanically relevant producer output that differs from canonical replay.

The verifier does not directly validate the separately stored on-disk:

```text
recorded_release_candidate_index_v0.json
```

as an independent input artifact.

Its direct completeness comparison is between:

```text
canonical replay candidate IDs
```

and:

```text
manifest.candidate_evidence IDs
```

Only the non-authoritative:

```text
created_utc
```

representation is normalized for deterministic envelope comparison.

All mechanically relevant candidate fields must remain equal.

## Producer-trust verification

A candidate envelope may contain:

```text
provenance.trusted_producer = true
```

but that field does not independently prove producer trust.

When trusted producer provenance is required, the supplied candidate must contain the expected producer declaration.

However, the verifier sets:

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
+ current-run producer inputs
+ checked-in canonical producer
+ canonical candidate replay
= supplied candidate envelope
```

## Candidate evidence verification

Each candidate is mechanically checked for:

1. candidate-manifest entry object shape;
2. `verification_required = true`;
3. expected SHA-256 shape;
4. expected schema-version presence;
5. expected subject-binding fields;
6. non-empty expected required-gate list;
7. trusted-producer requirement declaration;
8. candidate artifact path presence;
9. candidate artifact regular-file status;
10. candidate artifact SHA-256 equality with the manifest;
11. candidate artifact JSON object parsing;
12. candidate schema-version equality;
13. candidate run-identity equality;
14. candidate subject-binding equality;
15. commit binding to the manifest subject;
16. candidate policy-set equality;
17. candidate policy-digest equality;
18. canonical candidate replay equality;
19. replay-derived producer-trust verification;
20. raw-evidence path presence;
21. raw-evidence file presence;
22. raw-evidence SHA-256 equality;
23. exact `required_for_gates` equality;
24. candidate gate membership in policy and registry.

A candidate is marked:

```text
status = verified
```

only when its complete candidate-level error list is empty.

Otherwise it remains:

```text
status = failed
```

## External-summary candidate boundary

External-summary-specific admission occurs during canonical recorded-release candidate production.

For release-grade external candidates, the canonical producer applies the relevant:

- external-summary JSON requirement;
- external-summary schema;
- detector-specific tool identity;
- detector-specific metric identity;
- threshold reference;
- threshold URI;
- threshold comparator semantics;
- metric pass state;
- aggregate result;
- required release-contribution mode;
- run-key binding;
- release-candidate binding;
- subject-kind binding;
- subject-ID binding;
- current-commit subject digest;
- raw-evidence path containment;
- raw-evidence digest;
- summary digest;
- external-summary envelope binding;
- signer-policy admission;
- cryptographic attestation verification.

The recorded release-evidence verifier does not accept a separately supplied assertion that these checks succeeded.

Instead, it reruns the same checked-in candidate producer from the current repository and current-run inputs.

The replayed candidate envelope must match the supplied candidate envelope.

Therefore:

```text
external-summary declaration
≠ admitted external evidence
```

The cryptographic attestation-verification capability is implemented.

The following remain operationally pending:

```text
exact operational release-grade signer identity
current-run attested external-evidence production lane
```

## Relation-binding verification

After candidate verification, the verifier checks the manifest-declared relations.

Supported relation types are:

```text
artifact_to_subject
artifact_to_gate
```

Every relation entry must be an object and must provide mechanically valid:

```text
binding_type
source_evidence_id
expected_gate_id
target
```

The relation's expected gate must belong to:

```text
policy.gates.release_required
```

and the gate registry.

The relation's source candidate must exist and must already be verified.

### `artifact_to_subject`

An `artifact_to_subject` relation must:

- use verified candidate evidence;
- preserve the candidate's subject binding;
- bind to the current run identity;
- target exactly:

```text
subject.commit_sha
```

### `artifact_to_gate`

An `artifact_to_gate` relation must:

- use verified candidate evidence;
- name a gate listed in the candidate's `required_for_gates`;
- target exactly:

```text
gate.<gate_id>
```

A relation is marked:

```text
status = verified
```

only when its relation-level error list is empty.

A declared relation does not prove itself.

Therefore:

```text
relation declared
≠ relation satisfied
```

## Gate-materialization admissibility

The verifier iterates over the gate entries declared in:

```text
manifest.expected_gate_materialization
```

For each declared gate entry, it checks:

```text
expected_value = true
policy_relation = release_required
materialization_allowed_without_verifier = false
```

Each declared entry must contain non-empty:

```text
candidate_evidence_ids
relation_binding_ids
```

Every listed candidate evidence ID must be verified.

Every listed relation-binding ID must be satisfied.

Every relation used for the gate must have mechanically consistent source and target data.

Every candidate used for a declared gate must have at least one satisfied:

```text
artifact_to_gate
```

relation targeting that exact gate.

Each manifest-declared gate must belong to:

```text
policy.gates.release_required
```

and exist in the gate registry.

The verifier produces:

```text
status = verified
admissible = true
```

for a declared gate entry only when all of that entry's materialization prerequisites succeed.

The verifier establishes:

- per-entry evidence verification;
- per-entry relation verification;
- per-entry gate-target verification;
- per-entry policy and registry membership;
- per-entry admissibility.

The verifier does not independently prove that:

```text
manifest.expected_gate_materialization
```

contains every gate declared by:

```text
policy.gates.release_required
```

A manifest may omit a policy release-required gate without that omission being identified as complete-policy-coverage failure by the verifier itself.

Complete policy-derived coverage is enforced later by:

```text
PULSE_safe_pack_v0/tools/materialize_release_required_from_verifier_v0.py
```

The materializer iterates over the complete gate set derived from:

```text
policy.gates.release_required
```

and requires a verified, admissible report entry for every policy-derived gate before materialization.

Therefore:

```text
verifier status = verified
≠ complete policy gate coverage by itself
```

The complete boundary is:

```text
verifier per-entry admissibility
+ materializer iteration over every policy release-required gate
= complete policy-derived materialization coverage
```

Admissibility does not itself write a gate into `status.json`.

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

only when the complete aggregated error list is empty.

The aggregated error list includes:

- manifest-level errors;
- candidate-level errors;
- relation-level errors;
- manifest-declared gate-admissibility errors.

Missing, malformed, mismatched, or incomplete mechanically consumed evidence produces:

```text
status = failed
```

and a non-zero CLI result.

A verified report does not by itself prove:

- full input-manifest schema conformance;
- complete policy release-required gate coverage;
- final materialization success;
- final gate-enforcement success;
- release authority.

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
- non-empty canonical evidence results;
- non-empty canonical relation-binding results;
- exact equality between the supplied report and canonical verifier replay after canonical manifest-path normalization;
- manifest-path resolution to the supplied manifest;
- candidate-state `git_sha` matching verifier run identity;
- candidate-state `run_key` matching verifier run identity;
- candidate-state `run_mode = prod`;
- verifier `verified_subjects.git_sha` matching candidate-state `git_sha`;
- verifier `verified_subjects.run_key` matching candidate-state `run_key`;
- verifier `verified_subjects.commit_sha` matching candidate-state `git_sha`;
- current policy path matching the candidate state;
- current policy digest matching the candidate state;
- verifier policy set equal to `required+release_required`;
- verifier policy digest matching the current policy;
- verifier registry digest matching the current registry;
- no stubbed candidate state;
- no scaffolded candidate state;
- no pre-existing policy-derived release-required gate entries.

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

## Complete policy coverage in the materializer

The materializer derives the complete gate set from:

```text
policy.gates.release_required
```

It verifies that every policy-derived gate exists in the current registry.

It then iterates over every policy-derived release-required gate.

For each policy-derived gate, it requires a corresponding object in:

```text
verifier_report.gate_materialization_admissibility
```

The corresponding entry must satisfy:

```text
status = verified
admissible = true
errors = absent or empty
```

If any policy-derived gate lacks a corresponding admissible entry, materialization fails closed.

This is the layer that closes the complete policy-coverage boundary.

Therefore:

```text
manifest omission of a policy release-required gate
→ verifier may still verify declared entries
→ materializer detects missing policy-gate admissibility
→ no release-required materialization
```

## Materialization behavior

After every replay, identity, policy, registry, state, and complete-coverage check succeeds, the materializer writes literal `true` values for the complete policy-derived `release_required` gate set into:

```text
status["gates"]
```

The materializer works on a detached copy of the candidate gate mapping.

Failed admission must not partially mutate the candidate release state.

Therefore:

```text
failed canonical verifier replay
→ no release-required materialization

modified supplied verifier report
→ no release-required materialization

empty evidence or relation results
→ no release-required materialization

manifest-declared gate entry not admissible
→ no release-required materialization

policy release-required gate missing from admissibility map
→ no release-required materialization

run or subject mismatch
→ no release-required materialization

policy or registry mismatch
→ no release-required materialization

stubbed or scaffolded state
→ no release-required materialization

pre-existing release-required gate state
→ no release-required materialization
```

## Mechanical layer separation

The verifier and materializer occupy different layers:

```text
recorded release-evidence verifier
= mechanically consumed manifest checks
+ candidate verification
+ canonical candidate replay
+ relation verification
+ manifest-declared per-gate admissibility

release-required materializer
= canonical verifier replay
+ full policy gate coverage
+ policy-derived gate-state materialization

PULSE_safe_pack_v0/tools/check_gates.py
= strict final gate enforcement
```

The verifier report is not the final release decision.

Canonical candidate replay is not the final release decision.

Canonical verifier replay is not the final release decision.

Per-entry admissibility is not complete policy coverage.

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

- input manifests;
- candidate envelopes;
- candidate-index artifacts;
- verifier reports;
- attestation reports;
- canonical replay results;
- admissibility maps;
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

A successful direct verifier invocation means that the mechanically consumed manifest declarations and the resulting candidate, relation, and declared-gate checks succeeded.

It does not by itself mean that:

- the manifest passed the complete JSON schema;
- every policy release-required gate was declared by the manifest;
- materialization succeeded;
- strict final gate enforcement succeeded;
- release was allowed.

## Failure behavior

The verifier fails closed on, among other conditions:

- missing manifest;
- malformed manifest JSON;
- duplicate JSON keys;
- wrong manifest schema-version identity;
- missing mechanically consumed object sections;
- empty candidate-evidence mapping;
- empty expected-relation mapping;
- empty expected-materialization mapping;
- non-production run mode;
- invalid run commit identity;
- empty run key;
- subject and run commit mismatch;
- wrong policy set;
- missing policy path text;
- invalid policy digest;
- missing registry path text;
- invalid registry digest;
- current policy digest mismatch;
- current registry digest mismatch;
- duplicate policy or registry YAML keys;
- missing or empty policy `release_required` list;
- empty registry gate mapping;
- manifest-declared unknown gate IDs;
- canonical candidate replay failure;
- canonical candidates missing from the manifest;
- manifest candidates absent from canonical replay;
- internally inconsistent replayed candidate IDs;
- modified candidate envelopes;
- substituted candidate envelopes;
- substituted mechanically relevant producer metadata;
- candidate entry not requiring verification;
- candidate artifact digest mismatch;
- candidate schema-version mismatch;
- candidate run-identity mismatch;
- candidate subject-binding mismatch;
- candidate policy-binding mismatch;
- self-declared producer trust without replay equality;
- raw-evidence file missing;
- raw-evidence digest mismatch;
- `required_for_gates` mismatch;
- unsupported relation type;
- missing relation source;
- relation source not verified;
- incorrect relation target;
- relation gate missing from the manifest-declared materialization mapping;
- manifest-declared materialization entry with non-literal expected value;
- wrong materialization policy relation;
- materialization allowed without verifier;
- missing candidate evidence IDs;
- missing relation-binding IDs;
- candidate without an exact gate-target relation;
- any non-empty aggregated verifier error list.

The verifier does not directly fail merely because a policy release-required gate is omitted from:

```text
manifest.expected_gate_materialization
```

That complete-coverage omission is detected later by the materializer.

## Separate full-schema validation

The repository contains a separate input-manifest schema and checker:

```text
schemas/release_evidence_input_manifest_v0.schema.json
PULSE_safe_pack_v0/tools/check_release_evidence_input_manifest_v0.py
```

Those surfaces establish a broader manifest-contract boundary than the direct checks implemented by:

```text
check_recorded_release_evidence_v0.py
```

When complete manifest schema validity is required, the separate checker must run successfully or an explicitly equivalent full-schema validation must be demonstrated.

The two claims must remain distinct:

```text
full manifest schema valid
```

and:

```text
recorded verifier mechanically accepted the consumed fields
```

Neither claim should be inferred from the other without the corresponding check.

## Non-goals

The recorded release-evidence verifier is not:

- a complete input-manifest schema validator;
- a complete policy-gate coverage checker by itself;
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
replay-derived producer-trust verification
relation-binding verification
manifest-declared per-gate admissibility
canonical verifier replay
full policy gate coverage in the materializer
verifier-bound release-required materialization
cryptographic external-summary attestation verification capability
```

The next work is not to rebuild the recorded verifier.

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

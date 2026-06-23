# PULSE release-evidence verifier v0 — design record and implementation transition

## Document status

```text
document_status: superseded_as_current_implementation_entrypoint
historical_design_record: retained
legacy_diagnostic_surface: retained_and_tested
current_implementation_document: docs/recorded_release_evidence_verifier_v0.md
normative_release_authority: false
```

This document preserves the original pre-implementation verifier design and the retained legacy diagnostic verifier-report surface.

It is no longer the current implementation entrypoint for release-grade evidence verification.

The current implemented verifier, replay, admissibility, and materialization path is documented in:

```text
docs/recorded_release_evidence_verifier_v0.md
```

The current release-grade operational and reference-package boundary is documented in:

```text
docs/release_grade_reference_run_v0.md
```

This file must be read as:

```text
historical verifier design
+ retained failure-only diagnostic report surface
+ implementation-transition record
+ redirect to the current recorded verifier path
```

It must not be read as evidence that the current release-grade verifier is still future work.

## Current reading rule

The repository contains two different verifier-related surfaces.

They have different schemas, different roles, and different authority boundaries.

They must not be collapsed into one verifier concept.

| Surface | Primary artifact | Current role |
|---|---|---|
| Legacy release-evidence verifier-report surface | `release_evidence_verifier_report_v0.json` | Failure-only diagnostic and pre-materialization visibility |
| Recorded release-evidence verifier | `recorded_release_evidence_verifier_v0.json` | Current release-grade candidate, replay, relation, and admissibility verification |

The legacy diagnostic report surface does not perform the current release-grade evidence-admission role.

The recorded release-evidence verifier does not replace the legacy diagnostic surface's historical and failure-visibility purpose.

## Why the original design became superseded

The original version of this document described a future trusted verifier because the release-grade evidence path had not yet implemented:

- current-run required-gate evidence production;
- non-stubbed candidate release-state production;
- canonical recorded-release candidate production;
- canonical candidate replay;
- replay-derived producer-trust verification;
- recorded release-evidence verification;
- relation-binding verification;
- manifest-declared gate-materialization admissibility;
- canonical verifier replay before materialization;
- complete policy-gate coverage in the materializer;
- verifier-bound release-required materialization;
- external-summary schema and semantic verification;
- cryptographic external-summary attestation verification.

Those mechanical layers now exist.

Therefore, historical statements such as:

```text
the trusted verifier is not implemented
release-required fold-in is future work
the materialized path remains closed until a later verifier PR
```

do not describe the current implemented release-grade path.

They remain useful only as a record of the earlier fail-closed design boundary.

## Current implemented release-grade path

The current implemented path is:

```text
current-run required-gate evidence
→ non-stubbed candidate release state
→ canonical candidate production
→ release-evidence input manifest
→ canonical candidate replay
→ recorded release-evidence verification
→ recorded release-evidence verifier report
→ canonical verifier replay by the materializer
→ policy-derived release-required gate materialization
→ final status.json
→ workflow-effective materialized required gate set
→ PULSE_safe_pack_v0/tools/check_gates.py
→ primary CI workflow
→ primary CI allow/block release decision
```

The current implementation source of truth is:

```text
docs/recorded_release_evidence_verifier_v0.md

PULSE_safe_pack_v0/tools/build_recorded_release_candidates_v0.py
PULSE_safe_pack_v0/tools/check_recorded_release_evidence_v0.py
PULSE_safe_pack_v0/tools/check_external_summary_attestation_v1.py
PULSE_safe_pack_v0/tools/materialize_release_required_from_verifier_v0.py
PULSE_safe_pack_v0/tools/check_gates.py

.github/workflows/pulse_ci.yml
```

## Legacy diagnostic verifier-report surface

The retained legacy diagnostic surface consists of:

```text
schemas/release_evidence_verifier_report_v0.schema.json
examples/release_evidence_verifier_report_v0.failed.example.json
PULSE_safe_pack_v0/tools/build_release_evidence_verifier_report_v0.py
PULSE_safe_pack_v0/tools/check_release_evidence_verifier_report_v0.py
PULSE_safe_pack_v0/tools/build_release_evidence_expectation_summary_v0.py
docs/PULSE_RELEASE_EVIDENCE_EXPECTATION_SUMMARY_v0.md
```

Its primary report artifact is:

```text
PULSE_safe_pack_v0/artifacts/release_evidence_verifier_report_v0.json
```

This diagnostic artifact is mechanically distinct from:

```text
PULSE_safe_pack_v0/artifacts/recorded_release_evidence_verifier_v0.json
```

## Legacy builder boundary

The legacy report builder is:

```text
PULSE_safe_pack_v0/tools/build_release_evidence_verifier_report_v0.py
```

It is intentionally failure-only.

It may:

- record candidate evidence inputs;
- record candidate paths;
- record candidate digests;
- record run and subject context;
- record policy and registry references;
- expose failure diagnostics;
- expose unavailable validation state;
- expose relation expectations;
- emit a schema-valid fail-closed report.

It intentionally does not:

- emit `VERIFIED`;
- establish trusted producer state;
- perform canonical recorded-candidate replay;
- satisfy relation bindings from current-run evidence;
- establish gate-materialization admissibility;
- materialize gates;
- write `status.json`;
- create release authority;
- replace the recorded release-evidence verifier.

Therefore:

```text
legacy verifier-report builder completed
≠ release evidence verified
```

## Legacy verifier-report checker boundary

The legacy report checker is:

```text
PULSE_safe_pack_v0/tools/check_release_evidence_verifier_report_v0.py
```

It validates the report's internal contract, including applicable:

- JSON schema conformance;
- verifier-decision vocabulary;
- relation-ID uniqueness;
- relation-reference integrity;
- gate-materialization reference integrity;
- internal fail-closed consistency.

It does not independently verify the underlying candidate evidence.

It does not:

- rerun the recorded-release candidate producer;
- establish current-run producer trust;
- verify raw evidence through the recorded verifier path;
- perform canonical candidate replay;
- perform canonical verifier replay;
- authorize materialization;
- enforce complete policy-gate coverage.

Therefore:

```text
schema-valid legacy verifier report
≠ recorded release evidence verified
```

and:

```text
internally consistent declared relation
≠ relation satisfied by current-run evidence
```

## Legacy expectation-summary boundary

The expectation-summary path is:

```text
release_evidence_verifier_report_v0
→ release_evidence_expectation_summary_v0
```

Its builder is:

```text
PULSE_safe_pack_v0/tools/build_release_evidence_expectation_summary_v0.py
```

Its document is:

```text
docs/PULSE_RELEASE_EVIDENCE_EXPECTATION_SUMMARY_v0.md
```

The expectation summary may describe:

- missing candidate evidence;
- candidate evidence not verified;
- digest mismatch;
- pending relation binding;
- pending gate materialization;
- missing gate candidate evidence;
- unavailable candidate validation;
- other pre-materialization gaps.

It does not:

- close those gaps;
- verify candidate evidence;
- satisfy relation bindings;
- establish canonical producer trust;
- materialize gates;
- write `status.json`;
- authorize or block release.

Therefore:

```text
pre-materialization gap visible
≠ pre-materialization gap closed
```

## Current recorded release-evidence verifier

The current release-grade recorded verifier is:

```text
PULSE_safe_pack_v0/tools/check_recorded_release_evidence_v0.py
```

Its report artifact is:

```text
PULSE_safe_pack_v0/artifacts/recorded_release_evidence_verifier_v0.json
```

Its current implementation document is:

```text
docs/recorded_release_evidence_verifier_v0.md
```

It consumes:

```text
PULSE_safe_pack_v0/artifacts/release_evidence_input_manifest_v0.json
```

and the supplied repository root.

It verifies the mechanically consumed manifest declarations against current repository state and current-run candidate evidence.

## Manifest validation distinction

The recorded verifier checks:

```text
schema_version = release_evidence_input_manifest_v0
```

and mechanically consumes:

```text
run_identity
subject
policy_binding
registry_binding
candidate_evidence
expected_relation_bindings
expected_gate_materialization
```

It rejects duplicate JSON object keys and validates the fields needed by its implemented admission logic.

It does not independently establish complete conformance to:

```text
schemas/release_evidence_input_manifest_v0.schema.json
```

and does not replace:

```text
PULSE_safe_pack_v0/tools/check_release_evidence_input_manifest_v0.py
```

Therefore:

```text
recorded verifier accepts mechanically consumed manifest fields
≠ full input-manifest schema validity
```

Full manifest schema validity requires the separate schema checker or an explicitly equivalent full-schema validation path.

## Canonical candidate replay

The recorded verifier reruns the checked-in candidate producer from current repository state and current-run producer inputs.

The supplied candidate set must match canonical replay.

The verifier rejects:

- canonical candidates missing from the manifest;
- manifest candidates absent from canonical replay;
- canonical replay failure;
- internally inconsistent replayed candidate IDs;
- modified candidate envelopes;
- substituted candidate envelopes;
- mechanically relevant producer output that differs from canonical replay.

Only the non-authoritative:

```text
created_utc
```

representation may be normalized for deterministic envelope comparison.

The separately stored on-disk candidate index is not itself accepted as proof of candidate completeness.

The direct replay comparison is between:

```text
canonical replay candidate IDs
```

and:

```text
manifest.candidate_evidence IDs
```

## Replay-derived producer trust

A candidate may contain:

```text
provenance.trusted_producer = true
```

but that field does not prove producer trust.

The recorded verifier derives:

```text
trusted_producer_verified = true
```

only when the supplied candidate envelope matches canonical replay.

Therefore:

```text
self-declared trusted producer
≠ verified producer trust
```

Verified producer trust requires:

```text
current repository state
+ current-run producer inputs
+ checked-in candidate producer
+ canonical replay
= supplied candidate envelope
```

## Recorded candidate verification

The recorded verifier checks the applicable:

- candidate-manifest entry shape;
- verification-required declaration;
- expected digest shape;
- expected schema-version identity;
- candidate artifact presence;
- candidate regular-file status;
- candidate artifact digest;
- candidate JSON parsing;
- candidate schema-version equality;
- run-identity equality;
- subject-binding equality;
- commit binding;
- policy-set equality;
- policy-digest equality;
- canonical replay equality;
- replay-derived producer trust;
- raw-evidence path;
- raw-evidence presence;
- raw-evidence digest;
- required-gate equality;
- policy gate membership;
- registry gate membership.

A candidate becomes:

```text
status = verified
```

only when its complete candidate-level error list is empty.

## Relation-binding verification

The recorded verifier supports:

```text
artifact_to_subject
artifact_to_gate
```

relations.

A declared relation is verified only when:

- its source candidate exists;
- its source candidate is verified;
- its binding type is supported;
- its expected gate exists in the manifest-declared materialization mapping;
- its expected gate belongs to release-required policy;
- its expected gate exists in the registry;
- its target is mechanically exact.

An `artifact_to_subject` relation must target:

```text
subject.commit_sha
```

An `artifact_to_gate` relation must target:

```text
gate.<gate_id>
```

Therefore:

```text
relation declared
≠ relation satisfied
```

## Manifest-declared gate admissibility

The recorded verifier iterates over entries declared in:

```text
manifest.expected_gate_materialization
```

For each declared gate entry, it checks:

```text
expected_value = true
policy_relation = release_required
materialization_allowed_without_verifier = false
```

It also requires:

- non-empty candidate evidence IDs;
- non-empty relation-binding IDs;
- every listed candidate to be verified;
- every listed relation to be satisfied;
- every supporting candidate to have an exact gate-target relation;
- the declared gate to belong to release-required policy;
- the declared gate to exist in the registry.

The verifier may produce:

```text
status = verified
admissible = true
```

for a declared entry only after its entry-specific prerequisites succeed.

The recorded verifier establishes:

- per-entry candidate verification;
- per-entry relation verification;
- per-entry policy and registry membership;
- per-entry admissibility.

It does not independently prove that:

```text
manifest.expected_gate_materialization
```

contains every gate declared by:

```text
policy.gates.release_required
```

Therefore:

```text
recorded verifier status = verified
≠ complete policy-gate coverage by itself
```

## Complete policy coverage in the materializer

The materializer is:

```text
PULSE_safe_pack_v0/tools/materialize_release_required_from_verifier_v0.py
```

It derives the complete release-required gate set from:

```text
policy.gates.release_required
```

It then requires a corresponding verified and admissible verifier-report entry for every policy-derived gate.

If the manifest omitted a policy release-required gate, the materializer detects the missing admissibility entry and fails closed.

The complete coverage boundary is:

```text
recorded verifier per-entry admissibility
+ materializer iteration over every policy release-required gate
= complete policy-derived materialization coverage
```

## Canonical verifier replay

The materializer does not trust the supplied:

```text
recorded_release_evidence_verifier_v0.json
```

as an independent authority object.

Before materialization, it reruns:

```text
check_recorded_release_evidence(...)
```

from:

```text
--manifest
--repo-root
```

The supplied verifier report must match canonical verifier replay.

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

## Materializer admission boundary

Before materialization, the materializer checks the applicable:

- canonical verifier status;
- canonical verifier error list;
- non-empty evidence results;
- non-empty relation-binding results;
- supplied-report equality with canonical replay;
- manifest-path resolution;
- candidate-state commit identity;
- candidate-state run-key identity;
- candidate-state production run mode;
- verified-subject commit identity;
- verified-subject run identity;
- policy-set identity;
- policy-path identity;
- policy digest;
- registry digest;
- stubbed-state absence;
- scaffold-state absence;
- absence of pre-existing release-required gate values;
- complete policy-derived gate admissibility.

Failed admission must not partially mutate the candidate release state.

## Materialization

Only after the complete replay, identity, policy, registry, state, admissibility, and coverage checks succeed may the materializer write literal `true` values into:

```text
status["gates"]
```

for the complete policy-derived release-required gate set.

Therefore:

```text
failed canonical verifier replay
→ no release-required materialization

modified supplied verifier report
→ no release-required materialization

missing policy-gate admissibility
→ no release-required materialization

identity mismatch
→ no release-required materialization

policy or registry mismatch
→ no release-required materialization

stubbed or scaffolded candidate state
→ no release-required materialization

pre-existing release-required gate state
→ no release-required materialization
```

## External-summary verification boundary

Release-grade external-summary admission occurs during canonical candidate production.

The applicable path verifies:

- external-summary schema;
- detector-specific tool identity;
- detector-specific metric identity;
- threshold reference;
- threshold URI;
- threshold comparator;
- metric pass state;
- aggregate result;
- release-contribution mode;
- run-key binding;
- release-candidate binding;
- subject-kind binding;
- subject-ID binding;
- current-commit digest binding;
- raw-evidence path containment;
- raw-evidence digest;
- summary digest;
- envelope binding;
- signer-policy admission;
- cryptographic attestation verification.

The recorded verifier binds those checks through canonical candidate replay.

A separately supplied success declaration is not sufficient.

The cryptographic attestation-verification capability is implemented.

The following remain operationally pending:

```text
exact operational release-grade signer identity
current-run attested external-evidence production lane
```

## Mechanical layer separation

The current layers are:

```text
legacy release-evidence verifier report
= failure-only diagnostic and pre-materialization visibility

recorded release-evidence verifier
= mechanically consumed manifest checks
+ current-run candidate verification
+ canonical candidate replay
+ relation verification
+ manifest-declared per-gate admissibility

release-required materializer
= canonical verifier replay
+ complete policy-gate coverage
+ policy-derived gate-state materialization

PULSE_safe_pack_v0/tools/check_gates.py
= strict final gate enforcement
```

No earlier layer replaces a later layer.

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

- input manifests;
- legacy verifier reports;
- expectation summaries;
- candidate envelopes;
- candidate indexes;
- recorded verifier reports;
- canonical candidate replay;
- canonical verifier replay;
- relation maps;
- admissibility maps;
- attestation reports;
- materializer diagnostics;
- `release_decision_v0.json`;
- `artifact_provenance_binding_v0.json`;
- `release_authority_v0.json`;
- Quality Ledger;
- audit bundles;
- reference-run notes;
- dashboards;
- Pages.

They may preserve, verify, bind, explain, or publish evidence.

They may not independently authorize, block, override, or reinterpret release.

## Historical design principles retained

The original design established principles that remain valid:

```text
evidence existence
≠ evidence validity

digest presence
≠ verified binding

self-declared trust
≠ verified producer trust

relation declaration
≠ satisfied relation

verifier report presence
≠ canonical verifier replay

per-entry admissibility
≠ complete policy coverage

admissibility
≠ materialized gate state

materialized gate state
≠ release authority by itself
```

The current implementation now materializes these principles through code and tests.

## Historical and legacy files retained

The following remain valid diagnostic, schema, fixture, or historical surfaces:

```text
schemas/release_evidence_verifier_report_v0.schema.json
examples/release_evidence_verifier_report_v0.failed.example.json

PULSE_safe_pack_v0/tools/build_release_evidence_verifier_report_v0.py
PULSE_safe_pack_v0/tools/check_release_evidence_verifier_report_v0.py
PULSE_safe_pack_v0/tools/build_release_evidence_expectation_summary_v0.py

docs/PULSE_RELEASE_EVIDENCE_EXPECTATION_SUMMARY_v0.md
docs/PULSE_RELEASE_EVIDENCE_RELATION_BINDING_PROMOTION_PREREQUISITES_v0.md
docs/PULSE_RELEASE_EVIDENCE_TRUSTED_VERIFIER_SCHEMA_DELTA_MAP_v0.md
```

Their continued presence does not mean that they are the current release-grade evidence-admission verifier.

## Current implementation references

Use these as the current implementation source of truth:

```text
docs/recorded_release_evidence_verifier_v0.md
docs/release_grade_reference_run_v0.md

PULSE_safe_pack_v0/tools/build_recorded_release_candidates_v0.py
PULSE_safe_pack_v0/tools/check_recorded_release_evidence_v0.py
PULSE_safe_pack_v0/tools/check_external_summary_attestation_v1.py
PULSE_safe_pack_v0/tools/materialize_release_required_from_verifier_v0.py
PULSE_safe_pack_v0/tools/check_gates.py

.github/workflows/pulse_ci.yml
```

## Current operational target

The following are implemented:

```text
current-run required-gate evidence production
canonical candidate production
canonical candidate replay
replay-derived producer trust
recorded release-evidence verification
relation-binding verification
manifest-declared per-gate admissibility
canonical verifier replay
complete policy-gate coverage in the materializer
verifier-bound release-required materialization
cryptographic external-summary attestation verification capability
```

The next operational path is:

```text
exact operational release-grade signer identity
→ current-run attested external evidence
→ complete evidence-chain packaging
→ complete-package verification
→ controlled strict release-grade execution
→ completed public reference-run record
```

The completed run must be recorded in:

```text
docs/RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md
```

## Reader rule

Do not read this document as a future implementation plan for the current recorded verifier.

Read it as:

```text
historical verifier design
+ retained legacy diagnostic boundary
+ implementation-transition record
+ redirect to the current verifier path
```

The Git history preserves the full original pre-implementation text.

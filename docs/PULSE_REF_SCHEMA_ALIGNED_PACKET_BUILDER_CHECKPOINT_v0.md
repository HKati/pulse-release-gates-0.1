# PULSE-REF Schema-Aligned Packet Builder Checkpoint v0

Status: checkpoint / current builder state
Authority status: non-normative checkpoint
Scope: PULSE-REF / schema-aligned packet builder / validator / pass-fixture packet baseline
Checkpoint date: 2026-05-28
Decision status: preserves the declared PULSEmech release-authority path

## Purpose

This checkpoint records the current PULSE-REF schema-aligned packet builder
state.

It preserves the current working relation between:

- the guarded positive release-reference fixture;
- the release-reference evidence packet baseline;
- the pass-fixture-to-evidence-packet handoff plan;
- the schema-aligned builder contract;
- the schema-aligned packet validator;
- the schema-aligned pass-fixture packet builder;
- publication snapshot manifest-reference hardening.

The checkpoint records the current builder path before the next
packet-completeness implementation layer begins.

The current state is not only conceptual.

It is a working schema-aligned bridge from a guarded positive fixture to a
reconstructable packet-shaped baseline candidate.

## Core checkpoint statement

PULSE-REF now has a schema-aligned packet-builder path for the guarded positive
pass fixture.

The path is no longer only conceptual.

It now contains:

- a guarded source fixture;
- a baseline evidence-packet principle;
- a handoff plan;
- a schema-aligned builder contract;
- a guard for that contract;
- a schema-aligned packet validator;
- a schema-aligned pass-fixture packet builder;
- publication snapshot manifest-reference hardening.

The current builder emits a reconstructable v0 packet candidate.

The field-point authority map and evidence fold-in admissibility artifacts remain
reserved for the next packet-completeness layer.

This checkpoint records the current artifact field so later work does not
regress into fixture-specific payloads written into canonical packet paths.

## Current packet-builder chain

The current chain is:

```text
tests/fixtures/release_reference_v1/pass/status.json
→ release-reference completeness guard
→ policy-derived materialized required gates
→ schema-aligned packet builder
→ canonical packet artifacts
→ schema-aligned packet validator
→ reconstructable packet-shaped baseline candidate
```

This chain is the current implementation bridge from a guarded positive fixture
to a schema-aligned packet baseline.

## PULSEmech path preserved

The declared PULSEmech release-authority path remains:

```text
recorded release evidence
→ recorded `status.json` artifact
→ declared gate policy
→ materialized required gate set
→ strict fail-closed CI gate enforcement
→ declared-policy CI allow/block release decision
```

The schema-aligned packet builder prepares artifact packets that preserve this
path for reconstruction.

The builder path is an artifact-preparation surface.

The PULSEmech path remains the release-authority materialization path.

## Relation to release-reference evidence packet baseline

`docs/PULSE_REF_RELEASE_REFERENCE_EVIDENCE_PACKET_BASELINE_v0.md` records the
baseline as:

```text
planning baseline / current baseline relation
```

This checkpoint preserves the current builder side of that relation.

The baseline document connects:

- release-reference fixture matrix;
- evidence packet layout;
- minimum content contract;
- schema-aligned pass-fixture packet-builder relation.

This checkpoint records the current schema-aligned builder / validator state
that supports the current v0 builder-covered subset.

The complete baseline target, current v0 builder subset, and reserved next-layer
packet-completeness surfaces remain separate.

## Relational evidence-field principle

The current builder line follows the relational evidence-field principle.

The packet is not only a PASS / FAIL label carrier.

The packet preserves the field relation behind the terminal decision:

```text
candidate evidence
↔ declared policy
↔ materialized required gates
↔ boundary pressure
↔ stability signals
↔ release-authority state
→ recorded terminal enforcement result
```

The generated packet is valuable because it preserves the generation relation
behind the result.

## Source fixture state

The source fixture for the current builder path is:

```text
tests/fixtures/release_reference_v1/pass/
```

The source fixture is protected by:

```text
tests/test_pulse_ref_pass_fixture_packet_baseline_candidate_v0.py
```

The fixture must remain:

- `metrics.run_mode = "prod"`;
- `metrics.fixture_id = "release_reference_v1/pass"`;
- `metrics.fixture_kind = "positive_release_reference"`;
- `diagnostics.gates_stubbed = false`;
- `diagnostics.scaffold = false`;
- required gates as literal JSON `true`;
- release-required gates as literal JSON `true`;
- detector evidence materialized;
- external summaries present;
- external aggregate passing;
- expected outcome `PASS`;
- free of independent release-authority claims.

## Baseline and handoff surfaces

The following planning, baseline, and guard surfaces define the path into packet
form:

```text
docs/PULSE_REF_RELEASE_REFERENCE_EVIDENCE_PACKET_BASELINE_v0.md
tests/test_pulse_ref_release_reference_evidence_packet_baseline_v0.py
docs/PULSE_REF_PASS_FIXTURE_TO_EVIDENCE_PACKET_HANDOFF_PLAN_v0.md
tests/test_pulse_ref_pass_fixture_to_evidence_packet_handoff_plan_v0.py
```

These surfaces define the transition from a guarded fixture to a packet-shaped
baseline candidate.

The current checkpoint preserves that transition and records the builder /
validator state attached to it.

## Schema-aligned builder contract

The schema-aligned builder contract is:

```text
docs/PULSE_REF_SCHEMA_ALIGNED_PASS_FIXTURE_PACKET_BUILDER_CONTRACT_v0.md
```

The contract states the mechanical rule:

```text
A canonical packet path carries a canonical artifact contract.
```

The contract protects packet artifact fidelity.

It preserves PULSE as an artifact-bound release-authority system.

Schema alignment is used to preserve:

- reconstructability;
- artifact identity;
- verifier compatibility;
- digest integrity;
- authority-role classification.

## Contract guard

The schema-aligned builder contract is protected by:

```text
tests/test_pulse_ref_schema_aligned_packet_builder_contract_v0.py
```

This guard preserves the contract anchors for:

- PULSEmech path;
- canonical path rule;
- source fixture contract;
- declared policy materialization;
- canonical CI outcome;
- package digest contract;
- package manifest contract;
- release authority manifest contract;
- operator handoff report contract;
- publication snapshot handling;
- optional surface contract;
- fixture-specific payload rule;
- RA1 boundary;
- PULSE identity boundary;
- fellowship / HPC validation boundary.

## Schema-aligned packet validator

The schema-aligned packet validator is:

```text
scripts/check_pulse_ref_schema_aligned_packet_v0.py
```

Its smoke tests are:

```text
tests/test_check_pulse_ref_schema_aligned_packet_v0.py
```

The validator checks:

- required canonical packet artifacts;
- canonical JSON artifact schemas;
- release authority manifest shape through the existing manifest checker;
- policy-derived materialized gate sets;
- named package-manifest artifact references;
- package-digest references;
- optional publication snapshot schema when present;
- optional publication snapshot manifest reference when present;
- package-relative path safety for package-manifest artifact references.

This validator is the checker that the schema-aligned builder must pass.

## Schema-aligned pass-fixture packet builder

The schema-aligned builder is:

```text
scripts/build_pulse_ref_schema_aligned_pass_fixture_packet_v0.py
```

Its smoke tests are:

```text
tests/test_build_pulse_ref_schema_aligned_pass_fixture_packet_v0.py
```

The builder produces a canonical packet-shaped baseline candidate under:

```text
pulse_ref_evidence_packet_v0/
```

The generated packet includes:

- `README.md`;
- `package_manifest.json`;
- `status/status.json`;
- `reconstruction/source_expected_outcome.json`;
- `policy/pulse_gate_policy_v0.yml`;
- `policy/pulse_gate_registry_v0.yml`;
- `gates/materialized_gate_sets.json`;
- `ci/ci_outcome.json`;
- `release_authority/release_authority_manifest.json`;
- `audit/release_authority_audit_bundle/README.md`;
- `audit/release_authority_audit_bundle/status.json`;
- `audit/release_authority_audit_bundle/release_authority_manifest.json`;
- `digests/package_digests.json`;
- `handoff/operator_handoff_report.json`;
- `external/summaries/README.md`;
- `reconstruction/reconstruction_instructions.md`.

The publication snapshot surface is omitted by the builder until a canonical
publication surface exists.

## Current v0 packet-completeness boundary

The current schema-aligned pass-fixture packet builder emits a reconstructable
v0 packet candidate.

The current v0 output contract covers:

- packet overview;
- package manifest;
- recorded status;
- source expected-outcome metadata;
- declared policy;
- gate registry;
- policy-derived materialized gate sets;
- CI outcome;
- release-authority manifest;
- operator handoff report;
- digest manifest;
- audit bundle files;
- external summary note;
- reconstruction instructions.

The current builder emits the digest manifest as:

```text
digests/package_digests.json
```

The digest manifest records regular payload files.

The structural manifest and digest-manifest surfaces are generated packet
artifacts and validator inputs.

Reserved next-layer packet-completeness surfaces:

```text
field/field_point_authority_map_v0.json
admissibility/evidence_fold_in_admissibility_v0.json
publication/publication_snapshot.json when canonical publication surface exists
```

This boundary preserves the packet-baseline and handoff direction while keeping
the current v0 builder contract mechanically accurate.

## Builder hardening now included

The builder protects the reviewed failure modes:

- false policy-required gates in the pass fixture are rejected;
- the release-reference completeness guard is run before packet generation;
- stubbed states fail before packet generation;
- scaffolded states fail before packet generation;
- non-prod states fail before packet generation;
- missing-detector states fail before packet generation;
- missing-external states fail before packet generation;
- non-literal-true required-gate states fail before packet generation;
- handoff commands are recorded with replayable tool and packet artifact paths;
- relative `--out-dir` values work when the builder is launched outside the
  repository root;
- the generated packet is validated by the schema-aligned packet validator.

## Publication snapshot manifest reference hardening

The validator checks optional `publication_snapshot` manifest references when
present.

The optional manifest reference must:

- use a safe package-relative path;
- stay inside the packet root;
- reference the canonical artifact path
  `publication/publication_snapshot.json`;
- point to an existing file;
- match the actual SHA-256 digest.

This closes the optional publication-reference gap for the current
schema-aligned validator.

The builder still omits `publication/publication_snapshot.json` until a
canonical publication surface exists.

## Preserved artifact contracts

The generated packet aligns with the following canonical artifact contracts:

- `pulse_ref_release_reference_package_v0`;
- `pulse_ref_materialized_gate_sets_v0`;
- `pulse_ref_ci_outcome_v0`;
- `pulse_ref_package_digests_v0`;
- `pulse_ref_operator_handoff_report_v0`;
- `release_authority_v0`.

The release-authority manifest is checked with the existing release authority
manifest checker.

## Resolved earlier builder issue

The earlier builder attempt was stopped because it wrote fixture-specific
payloads into canonical packet paths.

That earlier pattern is replaced by the schema-aligned path:

```text
fixture source
→ declared policy materialization
→ canonical artifact payloads
→ manifest and digest cross-checks
→ schema-aligned packet validation
```

This checkpoint records that fixture-specific payloads in canonical packet paths
are no longer the accepted builder pattern.

## Checkpoint acceptance state

The current checkpoint is accepted when the following checks pass:

```bash
python tests/test_pulse_ref_release_reference_evidence_packet_baseline_v0.py
python tests/test_pulse_ref_pass_fixture_packet_baseline_candidate_v0.py
python tests/test_pulse_ref_pass_fixture_to_evidence_packet_handoff_plan_v0.py
python tests/test_pulse_ref_schema_aligned_packet_builder_contract_v0.py
python tests/test_check_pulse_ref_schema_aligned_packet_v0.py
python tests/test_build_pulse_ref_schema_aligned_pass_fixture_packet_v0.py
python tests/test_tools_tests_list_smoke.py
```

These checks preserve the current bridge from source fixture to schema-aligned
packet candidate.

## Relation to RA1

RA1 remains the stricter concrete package-verification path.

The current builder prepares schema-aligned packet candidates.

The validator checks artifact shape and reconstruction readiness.

A later step may connect generated packet candidates more directly to RA1-style
package verification.

Current boundary:

```text
schema-aligned packet preparation
→ packet artifact validation
→ future RA1 verification path
```

## Relation to HPC validation

This checkpoint prepares the packet shape needed for future HPC candidate-state
validation.

HPC validation should operate on packet candidates that preserve:

- source fixture identity;
- recorded status artifact;
- declared policy identity;
- materialized gate-set identity;
- CI outcome identity;
- package manifest references;
- digest references;
- release-authority manifest;
- operator handoff route;
- reconstruction instructions;
- authority-role classification.

HPC validates decision fields, not detached labels.

## Next possible steps

Possible next implementation steps:

- add a generated packet fixture from the schema-aligned builder;
- add a golden generated-packet regression test;
- add a builder-to-validator-to-RA1 bridge test;
- add packet diff / drift detection between generated candidate packets;
- add field-point authority map artifact generation;
- add evidence fold-in admissibility artifact generation;
- add HPC candidate batch planning over schema-aligned packet candidates;
- add relational evidence-field references into the packet manifest or field map.

The next step preserves the current chain.

The checkpoint remains packet-preparation and artifact-validation oriented.

## Closing statement

The current PULSE-REF packet-builder line has:

- a guarded source;
- a declared contract;
- a contract guard;
- a schema-aligned validator;
- a schema-aligned builder;
- publication-reference hardening.

The packet-builder path is strong enough to serve as the current baseline for
generated packet fixtures and future RA1 / HPC validation work.

PULSE remains defined by the release-authority materialization path.

The packet builder preserves that path in artifact form.

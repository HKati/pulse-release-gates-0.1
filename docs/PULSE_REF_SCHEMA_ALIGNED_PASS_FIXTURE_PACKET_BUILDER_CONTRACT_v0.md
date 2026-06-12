# PULSE-REF Schema-Aligned Pass Fixture Packet Builder Contract v0

Status: builder contract  
Authority status: non-normative implementation contract  
Scope: PULSE-REF / pass fixture / evidence packet baseline builder / schema-aligned packet artifacts  
Release-grade status: packet-baseline preparation contract  
Verifier status: pre-verifier contract  
Decision status: preserves the declared PULSEmech release-authority path

## Purpose

This document defines the schema-aligned builder contract for generating a PULSE-REF evidence packet baseline candidate from:

`tests/fixtures/release_reference_v1/pass/`

The contract exists before reintroducing the builder implementation.

The builder may generate a packet-shaped baseline candidate only when each canonical packet path receives a payload that matches its declared artifact contract.

The purpose is artifact fidelity:

source fixture  
→ recorded packet artifact  
→ canonical packet path  
→ schema-aligned payload  
→ reconstructable evidence packet baseline

This contract preserves the PULSE release-authority materialization path.

It does not reduce PULSE to a schema package.

## Core statement

PULSE is an artifact-bound release-authority system.

PULSEmech remains the mechanism:

recorded release evidence  
→ recorded `status.json` artifact  
→ declared gate policy  
→ materialized required gate set  
→ strict fail-closed CI gate enforcement  
→ declared-policy CI allow/block release decision

A packet builder operates below that mechanism as an artifact-preparation surface.

Its role is to preserve recorded evidence, policy, materialized gates, CI outcome, manifests, audit surfaces, digests, and reconstruction surfaces in a packet-shaped form.

Schema alignment protects the packet from artifact drift.

Schema alignment does not define PULSE.

## Contract principle

A canonical packet path carries a canonical artifact contract.

If the builder writes to a canonical path, the payload at that path must satisfy the canonical schema or contract used by the repository for that artifact type.

If a payload is fixture-specific, experimental, placeholder, diagnostic, or not yet schema-aligned, it must be placed under a clearly non-canonical fixture or diagnostic path.

A packet path must not imply canonical authority unless the payload has the corresponding canonical shape.

## Canonical path rule

The builder may write the following canonical paths only with schema-aligned payloads:

| Canonical path | Required contract |
|---|---|
| `status/status.json` | recorded status artifact from the selected source fixture |
| `policy/pulse_gate_policy_v0.yml` | declared gate policy snapshot |
| `policy/pulse_gate_registry_v0.yml` | gate registry snapshot |
| `gates/materialized_gate_sets.json` | materialized gate-set contract derived from declared policy |
| `ci/ci_outcome.json` | canonical `pulse_ref_ci_outcome_v0` artifact |
| `release_authority/release_authority_manifest.json` | canonical `release_authority_v0` manifest shape |
| `package_manifest.json` | canonical release-reference package manifest shape |
| `digests/package_digests.json` | canonical `pulse_ref_package_digests_v0` digest manifest shape |
| `handoff/operator_handoff_report.json` | canonical `pulse_ref_operator_handoff_report_v0` handoff shape |
| `publication/publication_snapshot.json` | canonical publication snapshot shape when included |
| `field/field_point_authority_map_v0.json` | canonical or contract-valid field-point authority map |
| `admissibility/evidence_fold_in_admissibility_v0.json` | canonical or contract-valid admissibility artifact |
| `reconstruction/reconstruction_instructions.md` | reconstruction instructions for the generated packet |

The canonical path rule is a packet-integrity rule.

It preserves the ability of existing schema tests, package tools, RA1-style verifiers, and future packet checkers to reconstruct the packet.

## Source fixture contract

The source fixture remains:

`tests/fixtures/release_reference_v1/pass/`

Required source files:

- `status.json`
- `expected_outcome.json`

The source fixture must remain protected by:

`tests/test_pulse_ref_pass_fixture_packet_baseline_candidate_v0.py`

The builder must read the source fixture as a source candidate.

The source fixture itself is not a packet.

The generated packet is the packet-shaped baseline candidate.

## Declared policy materialization contract

The builder must derive materialized gate sets from the declared policy.

The builder must not infer the required/release_required split only from `status.gates` plus a hard-coded release_required list.

The gate materialization source must be one of:

- an existing policy materializer already used in the repository;
- the same policy parsing logic used by current gate-set tools;
- a small contract-compatible reader that derives the selected required sets from `pulse_gate_policy_v0.yml`.

The output must record:

- selected policy sets;
- required gates;
- release_required gates when used;
- effective required gates;
- policy path;
- policy digest;
- ordering rule;
- duplicate handling rule;
- source fixture identity;
- materialization command or function reference.

The generated materialized gate-set artifact must remain consistent with the copied policy snapshot.

## Status artifact contract

The builder must copy the source fixture status into:

`status/status.json`

The copied status must preserve:

- `version`;
- `created_utc`;
- `metrics`;
- `diagnostics`;
- `gates`;
- `evidence`;
- `metrics.run_mode`;
- `metrics.fixture_id`;
- `metrics.fixture_kind`;
- `diagnostics.gates_stubbed`;
- `diagnostics.scaffold`;
- gate values as literal JSON booleans;
- source authority-boundary statement where present.

The builder may add packet metadata outside the copied status artifact.

The recorded status artifact must remain the source fixture status, not a mutated hidden status variant.

## Expected outcome contract

The source fixture expectation must be preserved as fixture expectation metadata.

Preferred target path:

`reconstruction/source_expected_outcome.json`

The expected outcome artifact is a reconstruction surface.

It preserves:

- source fixture ID;
- expected result;
- expected guard;
- expected checks;
- authority-boundary statement.

Expected outcome metadata supports reconstruction of fixture intent.

It does not override the declared-policy CI outcome.

## CI outcome contract

The builder must emit `ci/ci_outcome.json` using the canonical CI outcome contract.

The artifact must use the repository’s existing CI outcome schema shape.

It should preserve:

- schema identifier;
- provider;
- workflow name;
- run identity or local execution identity;
- run attempt where available;
- commit or source revision;
- event class;
- gate-check command or command reference;
- conclusion using the canonical conclusion vocabulary;
- declared-policy gate-enforcement result;
- effective required gate set reference;
- fail-closed indicator;
- status artifact reference;
- materialized gate-set reference;
- authority-boundary statement when the schema supports it.

The CI outcome is the recorded terminal enforcement result of the packet materialization path.

## Package digest contract

The builder must emit `digests/package_digests.json` using the canonical package digest shape.

The digest artifact must use the canonical schema identifier:

`pulse_ref_package_digests_v0`

The digest content must use the canonical artifact map expected by the existing digest contract.

The digest coverage must include every required generated packet artifact.

Digest coverage should include:

- `README.md`;
- `package_manifest.json`;
- `status/status.json`;
- `reconstruction/source_expected_outcome.json`;
- `policy/pulse_gate_policy_v0.yml`;
- `policy/pulse_gate_registry_v0.yml`;
- `gates/materialized_gate_sets.json`;
- `ci/ci_outcome.json`;
- `release_authority/release_authority_manifest.json`;
- `handoff/operator_handoff_report.json`;
- `field/field_point_authority_map_v0.json`;
- `admissibility/evidence_fold_in_admissibility_v0.json`;
- `reconstruction/reconstruction_instructions.md`;
- included publication, external, HPC, recognition, or audit artifacts.

Digest naming and structure must match the existing schema.

## Package manifest contract

The builder must emit `package_manifest.json` as a verifier-readable package manifest.

The manifest must contain named artifact references, not only a generic artifact list.

Required named references should include:

- status artifact;
- gate policy;
- gate registry;
- materialized gate sets;
- CI outcome;
- release authority manifest;
- package digests;
- operator handoff report;
- audit bundle reference;
- reconstruction instructions;
- publication snapshot when included;
- optional external/HPC/recognition surfaces when included.

The package manifest is the packet inventory and reference map.

It ties packet artifacts together for reconstruction and future verifier use.

## Release authority manifest contract

The builder must emit `release_authority/release_authority_manifest.json` in the canonical release authority manifest shape.

The manifest must preserve the canonical sections used by existing release-authority checks.

Required structural sections include:

- run identity;
- inputs;
- authority;
- evaluation;
- decision;
- diagnostics or non-normative surface classification where supported.

The manifest must reference:

- recorded status artifact;
- gate policy;
- gate registry;
- materialized gate sets;
- CI outcome;
- effective required gates;
- gate evaluation summary;
- fail-closed state;
- packet identity or package manifest where supported.

The release authority manifest is the evidence-policy-evaluator trace.

It preserves the declared PULSEmech chain.

## Operator handoff report contract

The builder must emit `handoff/operator_handoff_report.json` using the canonical operator handoff schema.

The handoff report must include the reconstruction fields required by the repository schema.

Required fields include the existing handoff contract anchors:

- `ok`;
- `repo_root`;
- `gate_mode`;
- `status_source`;
- `materialized_gate_sets`;
- `effective_required_gates`;
- `files`;
- `commands`;
- `warnings`;
- `errors`.

The handoff report must be able to support machine and human reconstruction of:

- source fixture;
- copied status;
- policy and registry;
- materialized gate sets;
- CI outcome;
- packet manifest;
- digest manifest;
- release authority manifest.

## Publication snapshot contract

Publication snapshot is optional for this builder.

The builder has two valid choices:

1. omit `publication/publication_snapshot.json` from the packet when no real publication surface is available;
2. emit a canonical publication snapshot payload that satisfies the existing publication snapshot schema.

If included, the publication snapshot must use the canonical shape and required fields.

It must not use fixture-specific schema names at the canonical publication path.

The first builder implementation may choose omission when the pass-fixture baseline has no public publication surface.

## Optional surface contract

Optional packet surfaces may be included only when their payload is contract-valid for their path.

Optional surfaces include:

- `external/summaries/`;
- `hpc/hpc_evidence_bundle_v0.json`;
- `recognition/recognition_surface_drift_v0.json`;
- diagnostic field surfaces;
- future candidate evidence surfaces.

Optional surfaces must carry explicit authority-role classification.

Optional surfaces must preserve their role without changing the declared release-authority path.

## Fixture-specific payload rule

Fixture-specific payloads are allowed only under fixture-specific or diagnostic locations.

Examples:

- `reconstruction/source_expected_outcome.json`;
- `reconstruction/source_fixture_identity.json`;
- `diagnostics/pass_fixture_source_summary.json`;
- `external/summaries/README.md` when no canonical external summary is included.

Fixture-specific payloads must not be written to canonical RA1/verifier paths unless they satisfy that path’s canonical schema.

## Builder acceptance conditions

A schema-aligned builder implementation may be accepted when:

1. it reads the guarded `release_reference_v1/pass` fixture;
2. it copies the source status artifact without hidden mutation;
3. it preserves expected outcome metadata as reconstruction metadata;
4. it derives materialized gate sets from declared policy;
5. it emits canonical CI outcome payload;
6. it emits canonical package digests payload;
7. it emits verifier-readable package manifest payload;
8. it emits canonical release authority manifest payload;
9. it emits canonical operator handoff report payload;
10. it omits optional publication snapshot or emits canonical publication snapshot;
11. every canonical path carries schema-aligned payload;
12. every fixture-specific payload is placed under a fixture/reconstruction/diagnostic path;
13. package digest coverage includes generated required artifacts;
14. generated packet can be checked by existing schema tests or an explicit packet builder smoke test;
15. authority role classification is preserved.

## Builder rejection conditions

A builder implementation must be rejected when:

- materialized gates are inferred from status alone while presented as declared-policy materialization;
- hard-coded gate promotion is used without policy-derived materialization;
- a canonical path receives fixture-specific schema;
- package manifest lacks named artifact references;
- package digests use non-canonical digest structure;
- CI outcome lacks canonical run/conclusion fields;
- release authority manifest lacks canonical run/input/authority/evaluation sections;
- operator handoff lacks required reconstruction fields;
- publication snapshot is included with non-canonical shape;
- optional diagnostic surfaces are presented as release-authority surfaces;
- generated packet cannot be consumed by existing schema/verifier tooling.

These rejection conditions protect the packet artifact field.

They preserve the PULSE release-authority materialization path.

## Relation to RA1

RA1 remains the stricter concrete package-verification path.

This contract prepares a builder that can later produce RA1-consumable packet candidates.

The contract does not run RA1.

The contract does not replace RA1.

The contract does not relax RA1.

A future builder PR should include tests that either validate generated artifacts against the relevant schemas or explicitly mark the packet as pre-RA1 with no canonical-path schema conflicts.

## Relation to PULSE identity

This contract preserves PULSE as an artifact-bound release-authority system.

Schema alignment is not the identity of PULSE.

Schema alignment preserves the shape of the packet artifacts that carry the recorded evidence field.

PULSE identity remains the PULSEmech materialization path:

recorded release evidence  
→ recorded `status.json` artifact  
→ declared gate policy  
→ materialized required gate set  
→ strict fail-closed CI gate enforcement  
→ declared-policy CI allow/block release decision

The builder contract prepares artifacts for reconstruction of that path.

## Relation to fellowship / HPC validation

The schema-aligned builder contract is a prerequisite for reliable candidate-state scaling.

HPC validation should operate on packet candidates whose canonical artifacts are shape-valid, digest-backed, and reconstructable.

The builder must preserve:

- candidate source identity;
- packet identity;
- run or execution identity;
- policy identity;
- materialized gate-set identity;
- CI outcome identity;
- digest coverage;
- reconstruction path;
- authority-role classification.

HPC may diagnostically test candidate decision-field behavior.

PULSEmech remains the only release-authority mechanism.

## Scope exclusions

This contract does not change:

- source fixture content;
- expected outcome content;
- declared gate policy;
- gate registry;
- status schema;
- `check_gates.py`;
- release-reference guard behavior;
- CI workflow behavior;
- RA1 verifier behavior;
- PULSEmech release-authority semantics.

## Closing statement

The pass-fixture packet builder must preserve the full PULSE release-authority field.

It must not flatten PULSE into schema validation.

It must not write fixture-specific payloads into canonical packet paths.

A canonical packet path carries a canonical artifact contract.

A schema-aligned packet is a stronger packet.

A stronger packet preserves the PULSEmech materialization path more faithfully.

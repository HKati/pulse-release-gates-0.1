# PULSE-REF Pass Fixture to Evidence Packet Handoff Plan v0

Status: planning handoff / current builder relation
Authority status: non-normative handoff record
Scope: PULSE-REF / release-reference pass fixture / evidence packet baseline handoff
Release-grade status: not release-grade evidence
Verifier status: not a verifier
Decision status: does not authorize, block, override, or create release authority

## Purpose

This document defines the handoff relation from the positive `release_reference_v1/pass` fixture to the first PULSE-REF evidence packet baseline candidate.

It connects:

- the guarded positive release-reference fixture;
- the release-reference evidence packet baseline;
- the canonical evidence packet layout;
- the schema-aligned pass-fixture packet builder;
- the schema-aligned packet validator;
- the reserved next-layer packet-completeness surfaces.

The release-reference evidence packet baseline identifies the positive pass
fixture as the preferred first source candidate for a packet-shaped baseline.

This document records how that source candidate maps into the canonical evidence
packet layout and how the current schema-aligned builder covers the current v0
packet subset.

The handoff relation preserves the artifact mapping between the guarded fixture
and the reconstructable packet-shaped baseline candidate.

## Core statement

The next proof state is not merely a passing fixture.

The next proof state is a packet-shaped, digest-backed, reconstructable baseline candidate derived from a controlled positive release-reference fixture.

The `release_reference_v1/pass` fixture proves that a controlled candidate can
satisfy the release-reference completeness guard.

The evidence packet handoff preserves that candidate as recorded artifact state.

The current handoff relation is no longer only a future implementation plan.

It now connects:

```text
tests/fixtures/release_reference_v1/pass/status.json
→ release-reference completeness guard
→ policy-derived materialized required gates
→ schema-aligned packet builder
→ canonical packet artifacts
→ schema-aligned packet validator
→ reconstructable packet-shaped baseline candidate
```

## Normative release path

The normative PULSE release decision remains:

```text
recorded release evidence
→ recorded `status.json` artifact
→ declared gate policy
→ materialized required gate set
→ strict fail-closed CI gate enforcement
→ declared-policy CI allow/block release decision
```

The handoff relation preserves and prepares this path for packet reconstruction.

A packet-shaped baseline candidate preserves release-state evidence as an
artifact field.

Release permission remains produced by the declared PULSEmech path.

## Source candidate

The source candidate for the first handoff is:

```text
tests/fixtures/release_reference_v1/pass/
```

Required source files:

- `status.json`;
- `expected_outcome.json`.

The source candidate is selected because it is the controlled positive
release-reference fixture.

It must remain:

- `metrics.run_mode = "prod"`;
- `metrics.fixture_id = "release_reference_v1/pass"`;
- `metrics.fixture_kind = "positive_release_reference"`;
- `diagnostics.gates_stubbed = false`;
- `diagnostics.scaffold = false`;
- required gates literal boolean `true`;
- release_required gates literal boolean `true`;
- detector evidence materialized;
- external summaries present;
- external aggregate passing;
- expected outcome `PASS`;
- free of release-authority claims.

The source candidate is protected by the pass fixture packet-baseline candidate
guard.

## Target packet shape

The target packet shape follows:

```text
docs/PULSE_REF_EVIDENCE_PACKET_LAYOUT_v0.md
```

Canonical packet root:

```text
pulse_ref_evidence_packet_v0/
```

The packet-shaped baseline candidate uses the canonical layout.

The handoff preserves the distinction between:

- source fixture;
- generated packet candidate;
- packet manifest;
- digest manifest;
- reconstruction surface;
- release-authority manifest;
- audit bundle;
- current v0 builder-covered packet subset;
- reserved next-layer packet-completeness surfaces.

## Handoff objective

The handoff objective is to map the positive release-reference fixture into a
packet-shaped baseline candidate.

The current schema-aligned builder emits the current v0 packet subset.

Current v0 builder-covered subset:

- recorded `status.json`;
- source expected-outcome metadata;
- declared policy snapshot;
- gate registry snapshot;
- policy-derived materialized gate-set artifact;
- declared-policy CI outcome artifact;
- release authority manifest;
- audit bundle files;
- package manifest;
- digest manifest;
- operator handoff report;
- external summary note;
- reconstruction instructions.

Reserved next-layer packet-completeness surfaces:

```text
field/field_point_authority_map_v0.json
admissibility/evidence_fold_in_admissibility_v0.json
publication/publication_snapshot.json when canonical publication surface exists
```

The handoff is successful when the fixture state is preserved as a
reconstructable artifact field and the generated packet candidate passes the
schema-aligned packet validator.

## Source-to-packet mapping

| Source / derived input | Target packet path | Current v0 builder state | Role | Authority status |
|---|---|---|---|---|
| `tests/fixtures/release_reference_v1/pass/status.json` | `status/status.json` | emitted | recorded release-state artifact for packet candidate | normative input for inspected path |
| `tests/fixtures/release_reference_v1/pass/expected_outcome.json` | `reconstruction/source_expected_outcome.json` | emitted | fixture expectation metadata | non-normative reconstruction |
| `pulse_gate_policy_v0.yml` | `policy/pulse_gate_policy_v0.yml` | emitted | declared gate policy | normative input |
| `pulse_gate_registry_v0.yml` | `policy/pulse_gate_registry_v0.yml` | emitted | gate semantic registry | normative support |
| derived required/release_required sets | `gates/materialized_gate_sets.json` | emitted | materialized gate set | normative input |
| gate-check conclusion | `ci/ci_outcome.json` | emitted | workflow/run identity and gate-check conclusion | normative enforcement output |
| release-authority trace | `release_authority/release_authority_manifest.json` | emitted | audit / trace surface | non-normative reconstruction |
| preserved audit README + status + manifest | `audit/release_authority_audit_bundle/` | emitted as regular files | audit bundle | non-normative preservation |
| packet inventory | `package_manifest.json` | emitted | inventory / references | audit / reconstruction |
| artifact digests | `digests/package_digests.json` | emitted | digest manifest | audit / reconstruction |
| operator commands and reconstruction route | `handoff/operator_handoff_report.json` | emitted | operator reconstruction surface | non-normative |
| public state references if present | `publication/publication_snapshot.json` | reserved until canonical publication surface exists | publication identity snapshot | non-normative reader surface |
| authority classification | `field/field_point_authority_map_v0.json` | reserved for next packet-completeness layer | field role map | non-normative diagnostic |
| fold-in status | `admissibility/evidence_fold_in_admissibility_v0.json` | reserved for next packet-completeness layer | candidate evidence admissibility | non-normative diagnostic |
| external summary note | `external/summaries/README.md` | emitted | external summary note | non-normative evidence note |
| external summary payloads if included | `external/summaries/` | policy-routed next-layer surface | external evidence references | conditional / policy-routed evidence |
| HPC bundle if included | `hpc/hpc_evidence_bundle_v0.json` | reserved | compute-scale validation reference | non-normative diagnostic |
| recognition diagnostic if included | `recognition/recognition_surface_drift_v0.json` | reserved | recognition drift diagnostic | non-normative |
| reconstruction guide | `reconstruction/reconstruction_instructions.md` | emitted | reconstruction instructions | non-normative operator surface |

## Status artifact handoff

The source fixture `status.json` becomes the packet candidate’s recorded status
artifact.

Target:

```text
status/status.json
```

The handoff preserves:

- version;
- created UTC;
- metrics object;
- run mode;
- fixture identity;
- fixture kind;
- diagnostics object;
- `diagnostics.gates_stubbed = false`;
- `diagnostics.scaffold = false`;
- gates object;
- all recorded gate values;
- evidence object;
- detector materialization state;
- external summary state;
- authority-boundary statement where available.

The status artifact is packet-bound by digest.

A live or public `status.json` URL is not a substitute for the recorded artifact.

## Expected outcome handoff

The source fixture `expected_outcome.json` is preserved as fixture expectation
metadata.

Target:

```text
reconstruction/source_expected_outcome.json
```

The expected outcome is not a decision engine.

It records what the fixture matrix expects.

For the pass fixture, it preserves:

- fixture ID;
- expected result `PASS`;
- expected guard;
- expected checks;
- authority-boundary statement.

Expected outcome metadata does not override the declared-policy CI outcome.

## Policy handoff

The packet candidate includes the declared policy used to evaluate the candidate.

Target:

```text
policy/pulse_gate_policy_v0.yml
```

The policy artifact is digest-backed.

The materialized gate set is derived from this policy.

The policy copy is a normative input when bound to the recorded evidence and
enforced through the declared PULSEmech path.

## Registry handoff

The packet candidate includes the gate registry used to stabilize gate meaning.

Target:

```text
policy/pulse_gate_registry_v0.yml
```

The registry artifact is digest-backed.

The registry supports semantic stability of gate IDs.

## Materialized gate-set handoff

The packet candidate includes the materialized required gate set.

Target:

```text
gates/materialized_gate_sets.json
```

The materialized gate-set artifact records the current schema-aligned v0 fields:

- `schema`;
- `policy_path`;
- `policy_sha256`;
- `sets`;
- `effective_required_gates`;
- `authority_boundary`.

The materialized gate set is consistent with the declared policy.

Additional lane, ordering, duplicate-handling, or command metadata belongs in
reconstruction / handoff surfaces unless a future schema revision declares those
fields.

## CI outcome handoff

The packet candidate includes a declared-policy CI outcome artifact.

Target:

```text
ci/ci_outcome.json
```

The artifact preserves the current schema-aligned v0 fields:

- workflow / run metadata;
- `gate_check_job`;
- `gate_check_conclusion`;
- `authority_boundary`.

The CI outcome records workflow/run identity and gate-check conclusion for the
packet candidate.

Effective required gates are recorded in `gates/materialized_gate_sets.json`.

Detailed command replay is recorded in `handoff/operator_handoff_report.json`.

Declared decision reconstruction is recorded in
`release_authority/release_authority_manifest.json`.

A generic green workflow is not equivalent to a declared-policy release
decision.

## Release authority manifest handoff

The packet candidate includes a release authority manifest as an audit and trace
surface.

Target:

```text
release_authority/release_authority_manifest.json
```

The manifest preserves:

- run identity;
- status artifact reference;
- policy artifact reference;
- registry artifact reference;
- materialized gate-set reference;
- effective required gates;
- gate evaluation summary;
- declared decision state;
- fail-closed indicator;
- authority-boundary statement;
- non-normative diagnostic statement where applicable.

The manifest reconstructs the declared-policy path.

## Audit bundle handoff

The packet candidate includes an audit bundle.

Target:

```text
audit/release_authority_audit_bundle/
```

Current v0 audit bundle files:

- `audit/release_authority_audit_bundle/README.md`;
- `audit/release_authority_audit_bundle/status.json`;
- `audit/release_authority_audit_bundle/release_authority_manifest.json`.

The audit bundle preserves evidence.

It does not authorize release.

## Digest handoff

The packet candidate includes a digest manifest.

Target:

```text
digests/package_digests.json
```

The digest manifest records regular payload files.

Current v0 digest-map payload coverage includes files such as:

- `README.md`;
- `status/status.json`;
- `reconstruction/source_expected_outcome.json`;
- `policy/pulse_gate_policy_v0.yml`;
- `policy/pulse_gate_registry_v0.yml`;
- `gates/materialized_gate_sets.json`;
- `ci/ci_outcome.json`;
- `release_authority/release_authority_manifest.json`;
- `handoff/operator_handoff_report.json`;
- `audit/release_authority_audit_bundle/README.md`;
- `audit/release_authority_audit_bundle/status.json`;
- `audit/release_authority_audit_bundle/release_authority_manifest.json`;
- `external/summaries/README.md`;
- `reconstruction/reconstruction_instructions.md`.

The structural packet manifest and digest manifest are generated packet
artifacts.

They are validated as packet artifacts and are distinct from entries inside the
current digest map.

A packet candidate without digest coverage is not baseline-complete.

## Operator handoff report

The packet candidate includes an operator handoff report.

Target:

```text
handoff/operator_handoff_report.json
```

The report preserves:

- source fixture path;
- status source;
- status digest;
- policy source;
- registry source;
- materialized gate sets;
- effective required gates;
- command list or command references;
- tool paths and tool digests when available;
- errors and warnings;
- authority-boundary statement.

Operator handoff supports reconstruction.

## Publication snapshot

Publication snapshot is optional until a canonical publication surface exists.

Target:

```text
publication/publication_snapshot.json
```

If included, it preserves:

- public status reference;
- Quality Ledger reference when available;
- release authority manifest reference;
- audit bundle reference;
- publication timestamp when available;
- run identity binding;
- authority-boundary statement.

Publication surfaces are reader surfaces.

## Field-point authority map

Field-point authority classification is reserved for the next packet-completeness
layer.

Reserved target:

```text
field/field_point_authority_map_v0.json
```

The map classifies packet surfaces as:

- normative input;
- normative enforcement output;
- audit / reconstruction surface;
- preservation surface;
- publication / reader surface;
- diagnostic / shadow surface;
- candidate evidence surface;
- optional analysis surface;
- non-normative surface.

No unclassified surface may be treated as release-authoritative.

## Evidence fold-in admissibility

Evidence fold-in admissibility state is reserved for the next
packet-completeness layer.

Reserved target:

```text
admissibility/evidence_fold_in_admissibility_v0.json
```

The admissibility artifact records:

- candidate evidence ID;
- source surface type;
- source artifact path;
- source artifact digest;
- schema-valid status where available;
- digest-valid status;
- verification status;
- fold-in requested status;
- policy route when fold-in is requested;
- gate ID when fold-in is requested;
- admissibility result.

Admissibility is not release permission.

## External evidence relation

The pass fixture includes external summary state as fixture evidence.

For the current v0 packet candidate, external evidence is represented by:

```text
external/summaries/README.md
```

Later packet-completeness layers may include external summary payloads.

If external summary artifacts are included, they must be digest-backed and
role-classified.

Presence alone is not enough.

Aggregate pass alone is not enough.

## HPC evidence relation

HPC evidence is optional for this handoff.

If included, it remains non-normative unless future declared policy promotes a
specific evidence field or gate.

The first pass-fixture handoff does not depend on HPC evidence.

HPC becomes relevant after the packet baseline exists and candidate-state batches
can be scaled.

## Recognition-surface relation

Recognition-surface diagnostics are optional for this handoff.

They may later help preserve how public surfaces classify the packet.

They remain non-normative.

## Reconstruction instructions

The packet candidate includes reconstruction instructions.

Target:

```text
reconstruction/reconstruction_instructions.md
```

The instructions explain how to verify:

- packet identity;
- run identity;
- status artifact;
- expected-outcome metadata;
- policy artifact;
- registry artifact;
- materialized gate set;
- CI outcome;
- release authority manifest;
- audit bundle;
- digest manifest;
- operator handoff report;
- current external summary note;
- reserved field-point authority map when present;
- reserved admissibility state when present;
- optional external / HPC / recognition evidence.

The instructions distinguish:

- normative inputs;
- normative enforcement outputs;
- audit surfaces;
- diagnostic surfaces;
- publication surfaces;
- candidate evidence surfaces.

## Acceptance conditions

The pass fixture to evidence packet handoff may be accepted as a current
baseline relation when:

1. the pass fixture remains guarded as packet-baseline source candidate;
2. the target packet layout is canonical;
3. source-to-packet mapping is defined;
4. recorded status mapping is defined;
5. expected outcome mapping is defined;
6. policy and registry mapping are defined;
7. materialized gate-set mapping is defined;
8. CI outcome mapping is defined;
9. release authority manifest mapping is defined;
10. current v0 audit bundle file mapping is defined;
11. digest-manifest mapping is defined;
12. operator handoff mapping is defined;
13. reconstruction instructions are defined;
14. current builder-covered subset is separated from reserved next-layer surfaces;
15. no non-normative surface claims independent release authority.

Acceptance of this handoff relation is not acceptance of a release-grade packet.

## Rejection conditions

A packet candidate fails handoff review when:

- source fixture identity is missing or inconsistent;
- source status is missing;
- source expected outcome is missing;
- run mode is not `prod`;
- diagnostics are stubbed;
- diagnostics are scaffolded;
- required gates are missing;
- release_required gates are missing;
- gate values are not literal boolean `true` for the positive candidate;
- detector evidence is not materialized;
- external summaries are not present;
- external aggregate is not passing;
- policy artifact is missing;
- registry artifact is missing;
- materialized gate set is missing;
- CI outcome is missing;
- digest manifest is missing;
- reconstruction instructions are missing;
- audit, diagnostic, publication, HPC, recognition, or handoff surfaces claim
  independent release authority;
- missing evidence is interpreted as PASS.

All negative conditions fail closed.

## Current implemented bridge

The current implemented bridge contains:

1. guarded positive release-reference fixture;
2. release-reference completeness guard before packet generation;
3. schema-aligned pass-fixture packet builder;
4. canonical packet artifacts;
5. package manifest and digest-manifest coverage;
6. schema-aligned packet validator;
7. publication snapshot manifest-reference hardening.

This bridge transforms the guarded pass fixture into a packet-shaped baseline
candidate without changing release authority.

## Relation to minimal content packet builder

The existing minimal content packet builder is useful as a structural bridge.

The pass-fixture handoff is stricter because it starts from a concrete positive
release-reference fixture.

The builder implementation may reuse layout-generation patterns from the
minimal content packet builder.

It must not reuse non-release-grade placeholders as if they were release-grade
evidence.

## Relation to RA1

RA1 remains the stricter concrete package-verification path.

A future packet candidate may later be checked by RA1-style verification.

Current boundary:

```text
schema-aligned packet preparation
→ packet artifact validation
→ future RA1 verification path
```

## Relation to fellowship / HPC validation

The pass-fixture evidence packet handoff prepares the first positive
packet-shaped baseline candidate.

HPC validation should later start from:

- a defined evidence packet baseline;
- a positive packet candidate;
- controlled negative candidate states;
- expected decisions;
- digest-backed artifacts;
- reconstruction instructions;
- field-point authority classification.

HPC validates the decision field.

PULSEmech remains the release-authority mechanism.

## Scope exclusions

This document does not change:

- pass fixture content;
- expected outcome content;
- release-reference fixture matrix behavior;
- declared gate policy;
- gate registry;
- status schema;
- `check_gates.py`;
- release-reference guard behavior;
- schema-aligned packet builder behavior;
- schema-aligned packet validator behavior;
- CI workflow behavior;
- RA1 verifier behavior;
- release-authority semantics.

## Closing statement

The pass fixture proves a controlled positive release-reference candidate.

The evidence packet baseline defines the packet field that must preserve such a
candidate.

This handoff plan connects them through the current schema-aligned builder
relation.

The current bridge transforms the guarded pass fixture into a packet-shaped
baseline candidate while preserving release authority.

The packet preserves the PULSEmech path.

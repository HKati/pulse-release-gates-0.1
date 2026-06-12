# PULSE-REF Release-Reference Evidence Packet Baseline v0

Status: planning baseline / current baseline relation
Authority status: non-normative
Scope: PULSE-REF / release-reference fixture matrix / evidence packet baseline
Release-grade status: not release-grade evidence
Verifier status: not a verifier
Decision status: does not authorize, block, override, or create release authority

## Purpose

This document defines the first PULSE-REF release-reference evidence packet baseline.

It connects three already-established PULSE-REF surfaces:

- the release-reference fixture matrix;
- the evidence packet layout;
- the minimum content contract.

The baseline now also records the current relation to the schema-aligned
pass-fixture packet-builder path.

The purpose is to define what the release-reference evidence packet baseline
preserves as PULSE moves from controlled fixture cases toward a concrete,
digest-backed, reconstructable release-reference evidence packet.

This document does not create release authority.

This document does not validate release-grade evidence.

This document does not run RA1.

This document does not replace the evidence packet layout, the minimum content
contract, the release-reference fixture matrix, or the schema-aligned packet
builder checkpoint.

It defines the baseline relation between those surfaces.

## Core statement

A PULSE-REF release-grade reference is not merely a run.

A release-grade reference is a recorded, artifact-bound, digest-backed, reconstructable evidence packet.

The fixture matrix tests fail-closed evidence-to-decision behavior.

The evidence packet baseline preserves the artifact field required to
reconstruct that behavior.

The current baseline relation is no longer only a planning target.

It now connects:

```text
guarded positive release-reference fixture
→ release-reference completeness guard
→ policy-derived materialized required gates
→ schema-aligned packet builder
→ canonical packet artifacts
→ schema-aligned packet validator
→ reconstructable packet-shaped baseline candidate
```

The remaining baseline work concerns packet-completeness surfaces, generated
packet fixtures, and later RA1 / HPC follow-on work.

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

The baseline packet preserves the recorded `status.json` artifact.

A release-reference evidence packet preserves and reconstructs this path.

It does not replace it.

The packet does not authorize release by existing.

The packet is release-relevant only as a recorded artifact field that preserves
the evidence, declared policy, materialized gates, CI outcome, and reconstruction
surfaces needed to inspect the declared-policy decision path.

## Relation to existing PULSE-REF surfaces

### Evidence packet layout

`docs/PULSE_REF_EVIDENCE_PACKET_LAYOUT_v0.md` defines the canonical packet shape.

This baseline does not change that layout.

The baseline uses the existing canonical packet structure as the packet target
for release-reference evidence.

### Minimum content contract

`docs/PULSE_REF_EVIDENCE_PACKET_MINIMUM_CONTENT_CONTRACT_v0.md` defines the
minimum content classes a packet must carry.

This baseline does not replace that contract.

The baseline identifies which minimum content classes are needed for
release-reference baseline closure and which content classes remain reserved for
the next packet-completeness layer.

### Minimal content packet builder

`scripts/build_pulse_ref_minimal_content_packet_v0.py` builds a minimal
content-bearing packet.

That generated packet is useful as a bridge fixture.

It is not release-grade evidence.

It is not a declared-policy CI release decision.

It is not release authority.

### Release-reference fixture matrix

`tests/fixtures/release_reference_v1/` and
`tests/test_release_reference_fixture_matrix_v1.py` exercise positive and
negative release-reference behavior.

The fixture matrix is not a packet.

The matrix proves fail-closed behavior across controlled candidate states.

The packet baseline defines the artifact field that preserves a selected
candidate state and its reconstruction trail.

### Schema-aligned packet-builder checkpoint

`docs/PULSE_REF_SCHEMA_ALIGNED_PACKET_BUILDER_CHECKPOINT_v0.md` records the
current schema-aligned packet-builder state.

The checkpoint records that the builder path is no longer only conceptual.

It includes:

- guarded source fixture;
- baseline evidence-packet principle;
- handoff plan;
- schema-aligned builder contract;
- contract guard;
- schema-aligned packet validator;
- schema-aligned pass-fixture packet builder;
- publication snapshot manifest-reference hardening.

The current builder emits a reconstructable v0 packet candidate.

The field-point authority map and evidence fold-in admissibility artifacts remain
reserved for the next packet-completeness layer.

## Baseline objective

The release-reference evidence packet baseline preserves the packet field needed
to reconstruct a controlled release-reference candidate state.

The complete baseline target includes:

- packet identity;
- run identity;
- recorded `status.json`;
- declared gate policy;
- gate registry;
- materialized required and `release_required` gate sets;
- effective required gate set;
- declared-policy CI outcome;
- release authority manifest;
- audit bundle;
- package digests;
- operator handoff report;
- publication snapshot when present;
- reconstruction instructions;
- field-point authority classification;
- evidence fold-in admissibility state;
- optional external summary references;
- optional HPC evidence references;
- optional recognition-surface diagnostic references.

The current schema-aligned pass-fixture packet builder covers the current v0
packet candidate subset:

- packet overview;
- package manifest;
- recorded status;
- source expected-outcome metadata;
- declared policy;
- gate registry;
- policy-derived materialized gate sets;
- CI outcome;
- release authority manifest;
- operator handoff report;
- package digests;
- audit bundle;
- external summary note;
- reconstruction instructions.

The reserved next-layer surfaces are:

```text
field/field_point_authority_map_v0.json
admissibility/evidence_fold_in_admissibility_v0.json
publication/publication_snapshot.json when canonical publication surface exists
```

The baseline succeeds when the packet is reconstructable and authority-safe.

Baseline completeness is separate from release authorization.

## Baseline source candidate

The current baseline source candidate is the controlled positive
release-reference fixture state.

Preferred baseline candidate:

```text
tests/fixtures/release_reference_v1/pass/
```

Reason:

- it is a positive release-grade reference fixture candidate;
- required gates are literal boolean `true`;
- `release_required` gates are literal boolean `true`;
- detector evidence is materialized;
- external summaries are present;
- external aggregate is passing;
- diagnostics are non-stubbed;
- diagnostics are non-scaffolded.

The schema-aligned packet-builder path currently uses this guarded positive
fixture as the source fixture.

Negative fixtures remain essential for fail-closed testing, but the first
evidence packet baseline starts from a positive candidate so reconstruction can
focus on packet completeness rather than intentional failure.

## Negative fixture relation

Negative release-reference fixtures remain part of the baseline field.

They validate that the release-reference guard fails closed when evidence is:

- incomplete;
- stubbed;
- scaffolded;
- false;
- missing;
- malformed;
- non-materialized.

The packet baseline preserves the existence of these negative cases as
regression evidence.

The first packet baseline preserves one selected positive candidate state and
references the matrix as supporting regression coverage.

Each negative fixture remains isolated.

A later packet-completeness layer may include a fixture matrix summary.

## Minimum baseline packet content

The complete release-reference evidence packet baseline target includes the
following content classes.

The current schema-aligned builder already emits the current v0 packet candidate
subset.

| Packet path | Baseline requirement | Current v0 builder state | Role | Authority status |
|---|---:|---|---|---|
| `README.md` | required | emitted | packet overview and authority boundary | non-normative |
| `package_manifest.json` | required | emitted | packet inventory and artifact references | audit / reconstruction |
| `status/status.json` | required | emitted | recorded release-state artifact | normative input for inspected path |
| `reconstruction/source_expected_outcome.json` | required for fixture-derived packet | emitted | source fixture expected-outcome metadata | non-normative reconstruction |
| `policy/pulse_gate_policy_v0.yml` | required | emitted | declared gate policy | normative input |
| `policy/pulse_gate_registry_v0.yml` | required | emitted | gate semantic registry | normative support |
| `gates/materialized_gate_sets.json` | required | emitted | materialized required gate sets | normative input |
| `ci/ci_outcome.json` | required | emitted | declared-policy gate-enforcement outcome | normative enforcement output |
| `release_authority/release_authority_manifest.json` | required | emitted | audit / trace manifest | non-normative trace |
| `audit/release_authority_audit_bundle/` | required | emitted | evidence preservation bundle | non-normative audit |
| `digests/package_digests.json` | required | emitted | digest manifest | audit / reconstruction |
| `handoff/operator_handoff_report.json` | required | emitted | operator reconstruction surface | non-normative |
| `external/summaries/README.md` | required for current v0 external note | emitted | external summary note | non-normative evidence note |
| `reconstruction/reconstruction_instructions.md` | required | emitted | reconstruction guide | non-normative operator surface |
| `publication/publication_snapshot.json` | required when public surfaces are included | reserved until canonical publication surface exists | publication identity | non-normative |
| `field/field_point_authority_map_v0.json` | required for next packet-completeness layer | reserved | field-point authority classification | non-normative diagnostic |
| `admissibility/evidence_fold_in_admissibility_v0.json` | required for next packet-completeness layer | reserved | fold-in admissibility state | non-normative diagnostic |
| `external/summaries/` | conditional | external note emitted; summary payloads remain policy-routed | external evidence references | policy-routed candidate evidence |
| `hpc/hpc_evidence_bundle_v0.json` | optional for baseline | reserved | compute-scale validation reference | non-normative diagnostic |
| `recognition/recognition_surface_drift_v0.json` | optional for baseline | reserved | recognition drift diagnostic | non-normative |

## Packet identity requirements

The baseline packet preserves stable packet identity.

Required identity fields:

- packet ID;
- packet layout version;
- packet baseline version;
- created UTC timestamp;
- source repository;
- source commit SHA;
- source branch or ref;
- packet root;
- package manifest path;
- package digest manifest path.

Packet identity supports reconstruction and digest binding.

## Run identity requirements

The baseline packet preserves run identity.

Required run identity fields:

- CI provider or execution environment;
- run ID;
- run attempt;
- run key;
- workflow name;
- workflow path or workflow ref;
- commit SHA;
- event type;
- run URL or archived run reference when available.

Run identity must bind to the recorded `status.json`, materialized gate set, CI
outcome, and release authority manifest.

A packet is not baseline-complete if its run identity cannot be tied to its
recorded artifacts.

For fixture-derived packet candidates, the source fixture identity also supports
reconstruction.

## Recorded status requirements

The baseline packet includes a recorded `status/status.json`.

For the positive baseline candidate, the status artifact preserves:

- `metrics.run_mode = "prod"`;
- selected fixture or candidate identity;
- explicit diagnostics object;
- `diagnostics.gates_stubbed = false`;
- `diagnostics.scaffold = false`;
- required gates as literal boolean `true`;
- `release_required` gates as literal boolean `true`;
- detector materialization state;
- external summary presence state;
- external aggregate pass state;
- authority-boundary statement where available.

A live or public `status.json` URL is not a substitute for the recorded artifact.

## Policy and registry requirements

The baseline packet includes the declared policy and registry used for the
inspected candidate.

Required policy and registry content:

- policy artifact path;
- policy artifact SHA-256 digest;
- selected policy set;
- `release_required` set where used;
- gate registry artifact path;
- gate registry SHA-256 digest;
- evidence that required gates are registry-backed.

The materialized gate set must be reconstructable from the declared policy.

## Materialized gate-set requirements

The baseline packet includes `gates/materialized_gate_sets.json`.

The artifact records:

- required gate set;
- `release_required` gate set;
- effective required gate set;
- selected lane or policy scope;
- policy source path;
- policy digest;
- duplicate-handling rule;
- ordering rule;
- materialization command or reference when available.

The materialized gate set preserves declared policy materialization.

The materialized gate set must not be hand-edited to satisfy release evidence.

## CI outcome requirements

The baseline packet includes `ci/ci_outcome.json`.

The CI outcome records:

- CI provider;
- workflow name;
- workflow path or workflow ref;
- run ID;
- run attempt;
- commit SHA;
- gate-check command or command reference;
- effective required gate set;
- gate-check conclusion;
- allow/block outcome;
- fail-closed indicator;
- run URL or archived run reference when available;
- authority-boundary statement.

The CI outcome is release-relevant as the declared-policy gate-enforcement
result.

A generic green workflow is not equivalent to a declared-policy release
decision.

## Release authority manifest requirements

The baseline packet includes
`release_authority/release_authority_manifest.json`.

The manifest preserves:

- run identity;
- status artifact reference;
- policy artifact reference;
- registry artifact reference;
- materialized gate-set reference;
- effective required gates;
- required gate evaluation summary;
- declared decision state;
- fail-closed indicator;
- authority-boundary statement;
- audit and diagnostic non-normative statements.

The release authority manifest is a reconstruction surface.

It is not a second decision engine.

## Audit bundle requirements

The baseline packet includes an audit bundle or audit-bundle reference.

Minimum audit bundle content:

- status artifact copy or reference;
- release authority manifest copy or reference;
- report card or reader surface when available;
- CI outcome reference;
- package digest reference;
- reconstruction instruction reference.

The audit bundle preserves evidence.

It does not authorize release.

## Digest requirements

The baseline packet includes `digests/package_digests.json`.

Digest coverage includes the regular payload files that the current builder
records in the digest map.

Minimum current v0 digest coverage includes regular payload files such as:

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

The current builder treats `package_manifest.json` and
`digests/package_digests.json` as structural manifest / digest-manifest surfaces.

They are generated and validated as packet artifacts, but they are not entries in
the current `package_digests.json` artifact map.

Next-layer digest coverage will include, when present:

- `publication/publication_snapshot.json`;
- `field/field_point_authority_map_v0.json`;
- `admissibility/evidence_fold_in_admissibility_v0.json`;
- any included external summary;
- any included HPC evidence bundle;
- any included recognition-surface diagnostic.

A packet without digest coverage is not baseline-complete.

## Operator handoff requirements

The baseline packet includes `handoff/operator_handoff_report.json`.

The operator handoff report preserves:

- gate mode;
- status source;
- status path;
- status digest;
- materialized gate sets;
- effective required gates;
- command list or command references;
- tool paths and tool digests when available;
- errors and warnings;
- authority-boundary statement.

Operator handoff supports reconstruction.

It does not create release authority.

## Publication snapshot requirements

If the packet references public surfaces, it includes
`publication/publication_snapshot.json`.

The publication snapshot preserves:

- public URL or archived reference;
- status URL or archived status reference;
- Quality Ledger URL or archived ledger reference when available;
- release authority manifest URL or archived reference;
- audit bundle URL or archived reference;
- publication timestamp when available;
- run identity binding;
- authority-boundary statement.

Publication surfaces are reader surfaces.

They do not create release authority.

The current schema-aligned builder omits the publication snapshot until a
canonical publication surface exists.

## Field-point authority map requirements

The complete baseline target includes
`field/field_point_authority_map_v0.json`.

The field-point map classifies each included surface as one of:

- normative input;
- normative enforcement output;
- audit / reconstruction surface;
- preservation surface;
- publication / reader surface;
- diagnostic / shadow surface;
- candidate evidence surface;
- optional analysis surface;
- non-normative surface.

Any field point that claims release-authority relevance must state its policy
route.

No unclassified packet surface may be treated as release-authoritative.

The field-point authority map is reserved for the next packet-completeness layer.

## Evidence fold-in admissibility requirements

The complete baseline target includes
`admissibility/evidence_fold_in_admissibility_v0.json`.

The admissibility artifact records:

- candidate evidence ID;
- source surface type;
- source artifact path;
- source artifact digest;
- schema-valid status;
- digest-valid status;
- verification status;
- fold-in requested status;
- policy route when fold-in is requested;
- gate ID when fold-in is requested;
- admissibility result.

Admissibility is not release permission.

Admissibility states whether candidate evidence can enter a policy-routed fold-in
path.

The evidence fold-in admissibility artifact is reserved for the next
packet-completeness layer.

## External evidence baseline relation

External evidence remains conditional.

If declared policy requires external evidence, the packet preserves external
summary artifacts or verified summary references.

Minimum external evidence references:

- external summary artifact path;
- external summary digest;
- detector name;
- detector version;
- schema reference when available;
- signer or attestation reference when available;
- subject artifact digest;
- fold-in status;
- verification status.

Missing required external evidence must fail closed.

Presence alone is not enough.

Aggregate pass alone is not enough.

The current schema-aligned builder emits an external summary note as part of the
current v0 packet candidate.

Policy-routed external summary payload inclusion remains a next-layer
packet-completeness surface.

## HPC evidence baseline relation

HPC evidence is optional for the first baseline.

If included, it remains non-normative unless future declared policy promotes a
specific evidence field or gate.

Minimum HPC reference content:

- HPC evidence bundle path;
- HPC evidence bundle digest;
- compute environment reference;
- job identity;
- input artifact digests;
- output artifact digests;
- reproducibility notes;
- authority-role classification.

HPC scale does not create release authority.

HPC output is useful when materialized, recorded, digest-backed,
reconstructable, role-classified, and verified.

## Recognition-surface baseline relation

Recognition-surface diagnostics are optional for the first baseline.

If included, they remain non-normative.

Recognition-surface content may include:

- README or front-door snapshot reference;
- repository About text snapshot reference;
- release notes snapshot reference;
- DOI or citation surface reference;
- drift-audit reference;
- recognition-surface classification.

Recognition surfaces help external readers classify the work.

They do not authorize release.

## Reconstruction baseline

The packet includes `reconstruction/reconstruction_instructions.md`.

The instructions explain how to reconstruct:

- packet identity;
- run identity;
- recorded status artifact;
- source fixture expected-outcome metadata;
- declared policy;
- gate registry;
- materialized required gate set;
- declared-policy CI outcome;
- release authority manifest;
- audit bundle;
- digest manifest;
- operator handoff report;
- external summary note;
- optional publication snapshot;
- optional field-point authority map;
- optional evidence fold-in admissibility state;
- optional external / HPC / recognition evidence.

The reconstruction instructions distinguish:

- normative inputs;
- normative enforcement outputs;
- audit surfaces;
- publication surfaces;
- diagnostic surfaces;
- optional candidate evidence.

## Baseline acceptance conditions

A release-reference evidence packet baseline may be accepted as baseline-complete
when:

1. packet identity is present;
2. run identity is present;
3. recorded `status.json` is present;
4. source expected-outcome metadata is present for fixture-derived candidates;
5. declared policy is present;
6. gate registry is present;
7. materialized required gate set is present;
8. CI outcome is present;
9. release authority manifest is present;
10. audit bundle or audit references are present;
11. package digest manifest is present;
12. operator handoff report is present;
13. reconstruction instructions are present;
14. authority-boundary statements are present;
15. all required current digest-map payload files are digest-backed;
16. structural manifest / digest-manifest surfaces are present and valid;
17. all required references bind to the same packet, fixture, or run identity;
18. no non-normative surface claims independent release authority.

The current v0 schema-aligned builder candidate satisfies the current
reconstructable packet-candidate subset when it passes the schema-aligned packet
validator.

The field-point authority map and evidence fold-in admissibility artifacts are
reserved next-layer acceptance surfaces.

Baseline completeness is not release authorization.

## Baseline rejection conditions

A baseline packet must fail packet-completeness review when:

- packet identity is missing;
- run identity is missing;
- recorded `status.json` is missing;
- source expected-outcome metadata is missing for fixture-derived candidates;
- declared policy is missing;
- gate registry is missing;
- materialized gate set is missing;
- CI outcome is missing;
- package digest manifest is missing;
- operator handoff report is missing;
- reconstruction instructions are missing;
- required digest-map payload files are not digest-backed;
- structural manifest / digest-manifest surfaces are missing or invalid;
- packet references do not bind to the same packet, fixture, or run identity;
- reader, audit, publication, diagnostic, or HPC surfaces claim release authority;
- advisory or diagnostic evidence is treated as required evidence without
  declared policy routing;
- missing required evidence is interpreted as PASS.

All negative conditions must fail closed.

## Relation to current schema-aligned builder

The current schema-aligned builder path is the implementation bridge from a
guarded positive fixture to a packet-shaped baseline candidate.

Current chain:

```text
tests/fixtures/release_reference_v1/pass/status.json
→ release-reference completeness guard
→ policy-derived materialized required gates
→ schema-aligned packet builder
→ canonical packet artifacts
→ schema-aligned packet validator
→ reconstructable packet-shaped baseline candidate
```

The current builder path prepares the baseline candidate from:

```text
tests/fixtures/release_reference_v1/pass/
```

The current validator checks the packet artifact shape, canonical JSON artifact
schemas, release authority manifest shape, policy-derived materialized gate
sets, package manifest references, package digest references, optional
publication snapshot schema when present, and package-relative path safety for
manifest artifact references.

This relation supersedes the older purely planning-baseline wording.

## Relation to future implementation

The first schema-aligned implementation layer is partially realized.

Current implemented bridge:

1. guarded positive release-reference fixture;
2. release-reference completeness guard before packet generation;
3. schema-aligned pass-fixture packet builder;
4. canonical packet artifacts;
5. package manifest and digest coverage;
6. schema-aligned packet validator;
7. publication snapshot manifest-reference hardening.

Remaining possible next implementation steps:

1. add a generated packet fixture from the schema-aligned builder;
2. add a golden generated-packet regression test;
3. add packet diff / drift detection between generated candidate packets;
4. add field-point authority map artifact generation;
5. add evidence fold-in admissibility artifact generation;
6. add builder-to-validator-to-RA1 bridge testing;
7. add HPC candidate batch planning over schema-aligned packet candidates;
8. add relational evidence-field references into the packet manifest or field map.

The next step preserves the current chain.

The checker remains packet-completeness and authority-boundary oriented.

It does not authorize release.

## Relation to RA1

RA1 remains the stricter concrete package-verification path.

This baseline does not run RA1.

This baseline does not replace RA1.

This baseline does not relax RA1.

This baseline defines the packet-preparation field before concrete RA1
verification.

RA1 may later consume or verify a concrete packet instance.

Current boundary:

```text
schema-aligned packet preparation
→ packet artifact validation
→ future RA1 verification path
```

## Relation to fellowship / HPC validation

The release-reference evidence packet baseline is the anchor for later
fellowship / HPC validation.

HPC validation starts from a defined release state.

HPC candidate-state validation should start from:

- a defined evidence packet baseline;
- one positive release-reference packet candidate;
- controlled fail-closed candidate states;
- recorded expected decisions;
- digest-backed artifacts;
- reconstruction instructions;
- field-point authority classification.

HPC may diagnostically test candidate decision-field behavior.

PULSEmech remains the only release-authority mechanism.


## Scope exclusions

This document does not change:

- declared gate policy;
- gate registry;
- status schema;
- `check_gates.py`;
- release-reference fixture behavior;
- release-reference guard behavior;
- schema-aligned packet builder behavior;
- schema-aligned packet validator behavior;
- CI workflow behavior;
- RA1 verifier behavior;
- README front-door positioning;
- Zenodo metadata;
- DOI metadata;
- release-authority semantics.

## Closing statement

The release-reference fixture matrix proves controlled fail-closed behavior.

The evidence packet layout defines canonical packet shape.

The minimum content contract defines required content classes.

The schema-aligned packet builder now produces a reconstructable v0 packet
candidate from the guarded positive pass fixture.

This baseline connects those surfaces into the release-reference evidence field.

The next proof state is not merely a passing run.

The next proof state is a recorded, digest-backed, reconstructable
release-reference evidence packet.

It preserves the declared PULSEmech path.

It does not replace it.

# PULSE-REF Release-Reference Evidence Packet Baseline v0

Status: planning baseline  
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

The purpose is to define what the first release-reference evidence packet baseline must preserve before PULSE moves toward a concrete release-grade reference evidence packet.

This document does not create release authority.

This document does not validate release-grade evidence.

This document does not run RA1.

This document does not replace the evidence packet layout, the minimum content contract, or the release-reference fixture matrix.

It defines the baseline relation between them.

## Core statement

A PULSE-REF release-grade reference is not merely a run.

A release-grade reference is a recorded, artifact-bound, digest-backed, reconstructable evidence packet.

The fixture matrix tests fail-closed evidence-to-decision behavior.

The evidence packet baseline preserves the artifact field required to reconstruct that behavior.

The baseline exists so the next release-reference state can move from isolated fixture cases toward a packet-shaped reconstruction target.

## Normative release path

The normative PULSE release decision remains:

recorded release evidence  
→ recorded `status.json` artifact  
→ declared gate policy  
→ materialized required gate set  
→ strict fail-closed CI gate enforcement  
→ declared-policy CI allow/block release decision

A release-reference evidence packet preserves and reconstructs this path.

It does not replace it.

The packet does not authorize release by existing.

The packet is release-relevant only as a recorded artifact field that preserves the evidence, declared policy, materialized gates, CI outcome, and reconstruction surfaces needed to inspect the declared-policy decision path.

## Relation to existing PULSE-REF surfaces

### Evidence packet layout

`docs/PULSE_REF_EVIDENCE_PACKET_LAYOUT_v0.md` defines the canonical packet shape.

This baseline does not change that layout.

The baseline uses the existing canonical packet structure as the packet target for future release-reference evidence.

### Minimum content contract

`docs/PULSE_REF_EVIDENCE_PACKET_MINIMUM_CONTENT_CONTRACT_v0.md` defines the minimum content classes a future packet must carry.

This baseline does not replace that contract.

The baseline identifies which minimum content classes are needed first for release-reference baseline closure.

### Minimal content packet builder

`scripts/build_pulse_ref_minimal_content_packet_v0.py` builds a minimal content-bearing packet.

That generated packet is useful as a bridge fixture.

It is not release-grade evidence.

It is not a declared-policy CI release decision.

It is not release authority.

### Release-reference fixture matrix

`tests/fixtures/release_reference_v1/` and `tests/test_release_reference_fixture_matrix_v1.py` exercise positive and negative release-reference behavior.

The fixture matrix is not a packet.

The matrix proves fail-closed behavior across controlled candidate states.

The packet baseline defines the artifact field that should preserve a selected candidate state and its reconstruction trail.

## Baseline objective

The first release-reference evidence packet baseline must be able to preserve:

- packet identity;
- run identity;
- recorded `status.json`;
- declared gate policy;
- gate registry;
- materialized required and release_required gate sets;
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

The baseline succeeds when the packet is reconstructable and authority-safe.

The baseline does not require that the packet already be release-grade.

## Baseline source candidate

The first baseline source candidate should be a controlled release-reference fixture state.

Preferred baseline candidate:

`tests/fixtures/release_reference_v1/pass/`

Reason:

- it is a positive release-grade reference fixture candidate;
- required gates are literal boolean `true`;
- release_required gates are literal boolean `true`;
- detector evidence is materialized;
- external summaries are present;
- external aggregate is passing;
- diagnostics are non-stubbed;
- diagnostics are non-scaffolded.

Negative fixtures remain essential for fail-closed testing, but the first evidence packet baseline should start from a positive candidate so reconstruction can focus on packet completeness rather than intentional failure.

## Negative fixture relation

Negative release-reference fixtures remain part of the baseline field.

They validate that the release-reference guard fails closed when evidence is incomplete, stubbed, scaffolded, false, missing, malformed, or non-materialized.

The packet baseline should preserve the existence of these negative cases as regression evidence, but it should not combine all negative fixtures into the first packet.

Each negative fixture remains isolated.

A packet baseline may later include a fixture matrix summary, but the first packet baseline should preserve one selected candidate state and reference the matrix as supporting regression coverage.

## Minimum baseline packet content

The first release-reference evidence packet baseline should include at minimum:

| Packet path | Baseline requirement | Role | Authority status |
|---|---:|---|---|
| `README.md` | required | packet overview and authority boundary | non-normative |
| `package_manifest.json` | required | packet inventory and artifact references | audit / reconstruction |
| `status/status.json` | required | recorded release-state artifact | normative input for inspected path |
| `policy/pulse_gate_policy_v0.yml` | required | declared gate policy | normative input |
| `policy/pulse_gate_registry_v0.yml` | required | gate semantic registry | normative support |
| `gates/materialized_gate_sets.json` | required | materialized required gate sets | normative input |
| `ci/ci_outcome.json` | required | declared-policy gate-enforcement outcome | normative enforcement output |
| `release_authority/release_authority_manifest.json` | required | audit / trace manifest | non-normative trace |
| `audit/release_authority_audit_bundle/` | required | evidence preservation bundle | non-normative audit |
| `digests/package_digests.json` | required | digest coverage | audit / reconstruction |
| `handoff/operator_handoff_report.json` | required | operator reconstruction surface | non-normative |
| `publication/publication_snapshot.json` | required when public surfaces are included | publication identity | non-normative |
| `field/field_point_authority_map_v0.json` | required | field-point authority classification | non-normative diagnostic |
| `admissibility/evidence_fold_in_admissibility_v0.json` | required | fold-in admissibility state | non-normative diagnostic |
| `external/summaries/` | conditional | external evidence references | policy-routed candidate evidence |
| `hpc/hpc_evidence_bundle_v0.json` | optional for baseline | compute-scale validation reference | non-normative diagnostic |
| `recognition/recognition_surface_drift_v0.json` | optional for baseline | recognition drift diagnostic | non-normative |
| `reconstruction/reconstruction_instructions.md` | required | reconstruction guide | non-normative operator surface |

## Packet identity requirements

The baseline packet must preserve stable packet identity.

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

Packet identity is not release authority.

Packet identity supports reconstruction and digest binding.

## Run identity requirements

The baseline packet must preserve run identity.

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

Run identity must bind to the recorded `status.json`, materialized gate set, CI outcome, and release authority manifest.

A packet is not baseline-complete if its run identity cannot be tied to its recorded artifacts.

## Recorded status requirements

The baseline packet must include a recorded `status/status.json`.

For the first positive baseline candidate, the status artifact should preserve:

- `metrics.run_mode = "prod"`;
- selected fixture or candidate identity;
- explicit diagnostics object;
- `diagnostics.gates_stubbed = false`;
- `diagnostics.scaffold = false`;
- required gates as literal boolean `true`;
- release_required gates as literal boolean `true`;
- detector materialization state;
- external summary presence state;
- external aggregate pass state;
- authority-boundary statement where available.

A live or public `status.json` URL is not a substitute for the recorded artifact.

## Policy and registry requirements

The baseline packet must include the declared policy and registry used for the inspected candidate.

Required policy and registry content:

- policy artifact path;
- policy artifact SHA-256 digest;
- selected policy set;
- release_required set where used;
- gate registry artifact path;
- gate registry SHA-256 digest;
- evidence that required gates are registry-backed.

The materialized gate set must be reconstructable from the declared policy.

## Materialized gate-set requirements

The baseline packet must include `gates/materialized_gate_sets.json`.

The artifact should record:

- required gate set;
- release_required gate set;
- effective required gate set;
- selected lane or policy scope;
- policy source path;
- policy digest;
- duplicate-handling rule;
- ordering rule;
- materialization command or reference when available.

The materialized gate set must not be hand-edited to satisfy release evidence.

## CI outcome requirements

The baseline packet must include `ci/ci_outcome.json`.

The CI outcome should record:

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

The CI outcome is release-relevant only as the declared-policy gate-enforcement result.

A generic green workflow is not equivalent to a declared-policy release decision.

## Release authority manifest requirements

The baseline packet must include `release_authority/release_authority_manifest.json`.

The manifest should preserve:

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

The baseline packet must include an audit bundle or audit-bundle reference.

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

The baseline packet must include `digests/package_digests.json`.

Digest coverage should include all required packet payload artifacts.

Minimum digest coverage:

- `README.md`;
- `package_manifest.json`;
- `status/status.json`;
- `policy/pulse_gate_policy_v0.yml`;
- `policy/pulse_gate_registry_v0.yml`;
- `gates/materialized_gate_sets.json`;
- `ci/ci_outcome.json`;
- `release_authority/release_authority_manifest.json`;
- `handoff/operator_handoff_report.json`;
- `publication/publication_snapshot.json` when present;
- `field/field_point_authority_map_v0.json`;
- `admissibility/evidence_fold_in_admissibility_v0.json`;
- `reconstruction/reconstruction_instructions.md`;
- any included external summary;
- any included HPC evidence bundle;
- any included recognition-surface diagnostic.

A packet without digest coverage is not baseline-complete.

## Operator handoff requirements

The baseline packet must include `handoff/operator_handoff_report.json`.

The operator handoff report should preserve:

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

If the packet references public surfaces, it must include `publication/publication_snapshot.json`.

The publication snapshot should preserve:

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

## Field-point authority map requirements

The baseline packet must include `field/field_point_authority_map_v0.json`.

The field-point map should classify each included surface as one of:

- normative input;
- normative enforcement output;
- audit / reconstruction surface;
- preservation surface;
- publication / reader surface;
- diagnostic / shadow surface;
- candidate evidence surface;
- optional analysis surface;
- non-normative surface.

Any field point that claims release-authority relevance must state its policy route.

No unclassified packet surface may be treated as release-authoritative.

## Evidence fold-in admissibility requirements

The baseline packet must include `admissibility/evidence_fold_in_admissibility_v0.json`.

The admissibility artifact should record:

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

Admissibility only states whether candidate evidence can enter a future policy-routed fold-in path.

## External evidence baseline relation

External evidence remains conditional.

If declared policy requires external evidence, the packet must preserve external summary artifacts or verified summary references.

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

## HPC evidence baseline relation

HPC evidence is optional for the first baseline.

If included, it must be non-normative unless future declared policy promotes a specific evidence field or gate.

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

HPC output is useful only when materialized, recorded, digest-backed, reconstructable, role-classified, and verified.

## Recognition-surface baseline relation

Recognition-surface diagnostics are optional for the first baseline.

If included, they must remain non-normative.

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

The packet must include `reconstruction/reconstruction_instructions.md`.

The instructions should explain how to reconstruct:

- packet identity;
- run identity;
- recorded status artifact;
- declared policy;
- gate registry;
- materialized required gate set;
- declared-policy CI outcome;
- release authority manifest;
- audit bundle;
- digest manifest;
- field-point authority map;
- evidence fold-in admissibility state;
- optional external / HPC / recognition evidence.

The reconstruction instructions must distinguish:

- normative inputs;
- normative enforcement outputs;
- audit surfaces;
- publication surfaces;
- diagnostic surfaces;
- optional candidate evidence.

## Baseline acceptance conditions

A release-reference evidence packet baseline may be accepted as baseline-complete when:

1. packet identity is present;
2. run identity is present;
3. recorded `status.json` is present;
4. declared policy is present;
5. gate registry is present;
6. materialized required gate set is present;
7. CI outcome is present;
8. release authority manifest is present;
9. audit bundle or audit references are present;
10. package digests are present;
11. operator handoff report is present;
12. reconstruction instructions are present;
13. field-point authority classification is present;
14. authority-boundary statements are present;
15. all required artifacts are digest-backed;
16. all required references bind to the same packet/run identity;
17. no non-normative surface claims independent release authority.

Baseline completeness is not release authorization.

## Baseline rejection conditions

A baseline packet must fail packet-completeness review when:

- packet identity is missing;
- run identity is missing;
- recorded `status.json` is missing;
- declared policy is missing;
- gate registry is missing;
- materialized gate set is missing;
- CI outcome is missing;
- package digests are missing;
- reconstruction instructions are missing;
- required artifacts are not digest-backed;
- packet references do not bind to the same run identity;
- reader, audit, publication, diagnostic, or HPC surfaces claim release authority;
- advisory or diagnostic evidence is treated as required evidence without declared policy routing;
- missing required evidence is interpreted as PASS.

All negative conditions must fail closed.

## Relation to future implementation

This baseline prepares future implementation work.

Possible next implementation steps:

1. build a `pass` release-reference fixture into a packet-shaped baseline;
2. add a baseline packet fixture under `tests/fixtures/pulse_ref/`;
3. bind packet paths to package digests;
4. add a baseline checker that verifies packet completeness only;
5. keep the checker non-authoritative;
6. later connect baseline packet verification to RA1-style package verification.

The first implementation should remain conservative.

It should verify packet completeness and authority boundaries.

It should not authorize release.

## Relation to RA1

RA1 remains the stricter concrete package-verification path.

This baseline does not run RA1.

This baseline does not replace RA1.

This baseline does not relax RA1.

This baseline defines the packet-preparation field before concrete RA1 verification.

RA1 may later consume or verify a concrete packet instance.

## Relation to fellowship / HPC validation

The release-reference evidence packet baseline is the anchor for later fellowship/HPC validation.

HPC validation should not start from an undefined release state.

HPC candidate-state validation should start from:

- a defined evidence packet baseline;
- one positive release-reference packet candidate;
- controlled fail-closed candidate states;
- recorded expected decisions;
- digest-backed artifacts;
- reconstruction instructions;
- field-point authority classification.

HPC validates the decision field.

PULSEmech remains the release-authority mechanism.

## Scope exclusions

This document does not change:

- declared gate policy;
- gate registry;
- status schema;
- `check_gates.py`;
- release-reference fixture behavior;
- release-reference guard behavior;
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

This baseline connects those surfaces into the next release-reference evidence field.

The next proof state is not merely a passing run.

The next proof state is a recorded, digest-backed, reconstructable release-reference evidence packet.

It preserves the declared PULSEmech path.

It does not replace it.

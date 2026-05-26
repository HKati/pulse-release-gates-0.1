# PULSE-REF Pass Fixture to Evidence Packet Handoff Plan v0

Status: planning handoff  
Authority status: non-normative  
Scope: PULSE-REF / release-reference pass fixture / evidence packet baseline handoff  
Release-grade status: not release-grade evidence  
Verifier status: not a verifier  
Decision status: does not authorize, block, override, or create release authority

## Purpose

This document defines the handoff plan from the positive `release_reference_v1/pass` fixture to the first PULSE-REF evidence packet baseline candidate.

The release-reference evidence packet baseline identifies the positive pass fixture as the preferred first source candidate for a packet-shaped baseline.

This document defines how that source candidate should be mapped into the canonical evidence packet layout before any builder implementation changes are made.

This document does not build an evidence packet.

This document does not validate release-grade evidence.

This document does not run RA1.

This document does not authorize release.

It defines the artifact mapping and handoff boundary for the next implementation step.

## Core statement

The next proof state is not merely a passing fixture.

The next proof state is a packet-shaped, digest-backed, reconstructable baseline candidate derived from a controlled positive release-reference fixture.

The `release_reference_v1/pass` fixture proves that a controlled candidate can satisfy the release-reference completeness guard.

The evidence packet handoff must preserve that candidate as recorded artifact state.

The handoff must not reinterpret the fixture as release authority.

## Normative release path

The normative PULSE release decision remains:

recorded release evidence  
→ recorded `status.json` artifact  
→ declared gate policy  
→ materialized required gate set  
→ strict fail-closed CI gate enforcement  
→ declared-policy CI allow/block release decision

The handoff plan preserves and prepares this path for packet reconstruction.

It does not replace the path.

A packet-shaped baseline candidate does not authorize release by existing.

## Source candidate

The source candidate for the first handoff is:

`tests/fixtures/release_reference_v1/pass/`

Required source files:

- `status.json`
- `expected_outcome.json`

The source candidate is selected because it is the controlled positive release-reference fixture.

It must remain:

- `metrics.run_mode = "prod"`
- `metrics.fixture_id = "release_reference_v1/pass"`
- `metrics.fixture_kind = "positive_release_reference"`
- `diagnostics.gates_stubbed = false`
- `diagnostics.scaffold = false`
- required gates literal boolean `true`
- release_required gates literal boolean `true`
- detector evidence materialized
- external summaries present
- external aggregate passing
- expected outcome `PASS`
- free of release-authority claims

The source candidate is protected by the pass fixture packet-baseline candidate guard.

## Target packet shape

The target packet shape follows:

`docs/PULSE_REF_EVIDENCE_PACKET_LAYOUT_v0.md`

Canonical packet root:

`pulse_ref_evidence_packet_v0/`

The first packet-shaped baseline candidate should use the canonical layout rather than inventing a new top-level structure.

The handoff should preserve the distinction between:

- source fixture
- generated packet candidate
- packet manifest
- digest manifest
- reconstruction surface
- release-authority manifest
- audit bundle
- optional external/HPC/recognition surfaces

## Handoff objective

The handoff objective is to map the positive release-reference fixture into a packet-shaped baseline candidate.

The handoff succeeds when a future implementation can produce a packet directory that contains:

- recorded `status.json` copied or generated from the pass fixture source
- declared policy snapshot
- gate registry snapshot
- materialized gate-set artifact
- declared-policy CI outcome artifact
- release authority manifest
- audit bundle
- package manifest
- digest manifest
- operator handoff report
- field-point authority map
- evidence fold-in admissibility state
- reconstruction instructions

The handoff is not successful merely because the fixture passes.

The handoff is successful when the fixture state can be preserved as a reconstructable artifact field.

## Non-goals

This handoff plan does not:

- change the pass fixture
- change expected outcome semantics
- change the release-reference guard
- change declared gate policy
- change the gate registry
- change status schema
- change CI workflow behavior
- build the evidence packet
- run RA1
- validate release-grade evidence
- create release authority
- promote optional diagnostic surfaces into release authority
- treat a publication surface as release authority
- treat a generic green CI run as a declared-policy release decision

## Source-to-packet mapping

| Source / derived input | Target packet path | Role | Authority status |
|---|---|---|---|
| `tests/fixtures/release_reference_v1/pass/status.json` | `status/status.json` | recorded release-state artifact for packet candidate | normative input for inspected path |
| `tests/fixtures/release_reference_v1/pass/expected_outcome.json` | `reconstruction/source_expected_outcome.json` or manifest reference | fixture expectation metadata | non-normative reconstruction |
| `pulse_gate_policy_v0.yml` | `policy/pulse_gate_policy_v0.yml` | declared gate policy | normative input |
| `pulse_gate_registry_v0.yml` | `policy/pulse_gate_registry_v0.yml` | gate semantic registry | normative support |
| derived required/release_required sets | `gates/materialized_gate_sets.json` | materialized gate set | normative input |
| gate check result | `ci/ci_outcome.json` | declared-policy gate-enforcement outcome | normative enforcement output |
| evidence-policy-evaluator trace | `release_authority/release_authority_manifest.json` | audit / trace surface | non-normative reconstruction |
| preserved status + manifest + report card | `audit/release_authority_audit_bundle/` | audit bundle | non-normative preservation |
| packet inventory | `package_manifest.json` | inventory / references | audit / reconstruction |
| artifact digests | `digests/package_digests.json` | digest coverage | audit / reconstruction |
| operator commands and reconstruction route | `handoff/operator_handoff_report.json` | operator reconstruction surface | non-normative |
| public state references if present | `publication/publication_snapshot.json` | publication identity snapshot | non-normative reader surface |
| authority classification | `field/field_point_authority_map_v0.json` | field role map | non-normative diagnostic |
| fold-in status | `admissibility/evidence_fold_in_admissibility_v0.json` | candidate evidence admissibility | non-normative diagnostic |
| external summary references if included | `external/summaries/` | external evidence references | conditional / policy-routed evidence |
| HPC bundle if included | `hpc/hpc_evidence_bundle_v0.json` | compute-scale validation reference | non-normative diagnostic |
| recognition diagnostic if included | `recognition/recognition_surface_drift_v0.json` | recognition drift diagnostic | non-normative |
| reconstruction guide | `reconstruction/reconstruction_instructions.md` | reconstruction instructions | non-normative operator surface |

## Status artifact handoff

The source fixture `status.json` should become the packet candidate’s recorded status artifact.

Target:

`status/status.json`

The handoff must preserve:

- version
- created UTC
- metrics object
- run mode
- fixture identity
- fixture kind
- diagnostics object
- `diagnostics.gates_stubbed = false`
- `diagnostics.scaffold = false`
- gates object
- all recorded gate values
- evidence object
- detector materialization state
- external summary state
- authority-boundary statement where available

The status artifact must be packet-bound by digest.

A live or public `status.json` URL must not be used as a substitute for the recorded artifact.

## Expected outcome handoff

The source fixture `expected_outcome.json` should be preserved as fixture expectation metadata.

It may be copied into:

`reconstruction/source_expected_outcome.json`

or referenced in:

`package_manifest.json`

The expected outcome is not a decision engine.

It records what the fixture matrix expects.

For the pass fixture, it must preserve:

- fixture ID
- expected result `PASS`
- expected guard
- expected checks
- authority-boundary statement

Expected outcome metadata must not override the declared-policy CI outcome.

## Policy handoff

The packet candidate must include the declared policy used to evaluate the candidate.

Target:

`policy/pulse_gate_policy_v0.yml`

The policy artifact must be digest-backed.

The materialized gate set must be derived from this policy.

The policy copy does not create release authority by document presence.

It is a normative input only when bound to the recorded evidence and enforced through the declared PULSEmech path.

## Registry handoff

The packet candidate must include the gate registry used to stabilize gate meaning.

Target:

`policy/pulse_gate_registry_v0.yml`

The registry artifact must be digest-backed.

The registry supports semantic stability of gate IDs.

It does not create release authority by itself.

## Materialized gate-set handoff

The packet candidate must include the materialized required gate set.

Target:

`gates/materialized_gate_sets.json`

The materialized gate-set artifact should include:

- required gate set
- release_required gate set
- effective required gate set
- selected lane or policy scope
- policy source path
- policy digest
- duplicate-handling rule
- ordering rule
- materialization command or reference when available

The materialized gate set must be consistent with the declared policy.

It must not be hand-edited to satisfy the fixture.

## CI outcome handoff

The packet candidate must include a declared-policy CI outcome artifact.

Target:

`ci/ci_outcome.json`

The artifact should preserve:

- CI provider or execution environment
- workflow name
- workflow path or reference
- run ID or local execution identity
- run attempt when available
- commit SHA or source revision
- gate-check command
- effective required gate set
- gate-check conclusion
- expected allow/block outcome
- fail-closed indicator
- authority-boundary statement

A generic green workflow is not enough.

The CI outcome must represent the declared-policy gate-enforcement result for the packet candidate.

## Release authority manifest handoff

The packet candidate must include a release authority manifest as an audit and trace surface.

Target:

`release_authority/release_authority_manifest.json`

The manifest should preserve:

- run identity
- status artifact reference
- policy artifact reference
- registry artifact reference
- materialized gate-set reference
- effective required gates
- gate evaluation summary
- declared decision state
- fail-closed indicator
- authority-boundary statement
- non-normative diagnostic statement where applicable

The manifest is not a second decision engine.

It reconstructs the declared-policy path.

## Audit bundle handoff

The packet candidate must include an audit bundle.

Target:

`audit/release_authority_audit_bundle/`

Minimum audit bundle content:

- status artifact copy or reference
- release authority manifest copy or reference
- CI outcome reference
- package digest reference
- reconstruction instruction reference
- report card or reader surface when available

The audit bundle preserves evidence.

It does not authorize release.

## Digest handoff

The packet candidate must include a digest manifest.

Target:

`digests/package_digests.json`

Digest coverage should include all required packet artifacts:

- `README.md`
- `package_manifest.json`
- `status/status.json`
- `policy/pulse_gate_policy_v0.yml`
- `policy/pulse_gate_registry_v0.yml`
- `gates/materialized_gate_sets.json`
- `ci/ci_outcome.json`
- `release_authority/release_authority_manifest.json`
- `handoff/operator_handoff_report.json`
- `field/field_point_authority_map_v0.json`
- `admissibility/evidence_fold_in_admissibility_v0.json`
- `reconstruction/reconstruction_instructions.md`
- included publication, external, HPC, or recognition artifacts when present

A packet candidate without digest coverage is not baseline-complete.

## Operator handoff report

The packet candidate must include an operator handoff report.

Target:

`handoff/operator_handoff_report.json`

The report should preserve:

- source fixture path
- status source
- status digest
- policy source
- registry source
- materialized gate sets
- effective required gates
- command list or command references
- tool paths and tool digests when available
- errors and warnings
- authority-boundary statement

Operator handoff supports reconstruction.

It does not create release authority.

## Publication snapshot

Publication snapshot is optional unless public surfaces are included.

Target:

`publication/publication_snapshot.json`

If included, it should preserve:

- public status reference
- Quality Ledger reference when available
- release authority manifest reference
- audit bundle reference
- publication timestamp when available
- run identity binding
- authority-boundary statement

Publication surfaces are reader surfaces.

They do not create release authority.

## Field-point authority map

The packet candidate must include a field-point authority map.

Target:

`field/field_point_authority_map_v0.json`

The map should classify packet surfaces as:

- normative input
- normative enforcement output
- audit / reconstruction surface
- preservation surface
- publication / reader surface
- diagnostic / shadow surface
- candidate evidence surface
- optional analysis surface
- non-normative surface

No unclassified surface may be treated as release-authoritative.

## Evidence fold-in admissibility

The packet candidate must include evidence fold-in admissibility state.

Target:

`admissibility/evidence_fold_in_admissibility_v0.json`

For the first pass-fixture handoff, admissibility may be simple and conservative.

It should record:

- candidate evidence ID
- source surface type
- source artifact path
- source artifact digest
- schema-valid status where available
- digest-valid status
- verification status
- fold-in requested status
- policy route when fold-in is requested
- gate ID when fold-in is requested
- admissibility result

Admissibility is not release permission.

## External evidence relation

The pass fixture includes external summary state as fixture evidence.

For the first packet candidate, external evidence may be represented as:

- fixture-level external summary state
- external summary references
- an `external/summaries/README.md` explaining fixture mode

If later external summary artifacts are included, they must be digest-backed and role-classified.

Presence alone is not enough.

Aggregate pass alone is not enough.

## HPC evidence relation

HPC evidence is optional for this handoff.

If included, it must remain non-normative unless future declared policy promotes a specific evidence field or gate.

The first pass-fixture handoff should not depend on HPC evidence.

HPC becomes relevant after the packet baseline exists and candidate-state batches can be scaled.

## Recognition-surface relation

Recognition-surface diagnostics are optional for this handoff.

They may later help preserve how public surfaces classify the packet.

They must remain non-normative.

They do not authorize release.

## Reconstruction instructions

The packet candidate must include reconstruction instructions.

Target:

`reconstruction/reconstruction_instructions.md`

The instructions should explain how to verify:

- packet identity
- run identity
- status artifact
- policy artifact
- registry artifact
- materialized gate set
- CI outcome
- release authority manifest
- audit bundle
- digest manifest
- operator handoff report
- field-point authority map
- admissibility state
- optional external/HPC/recognition evidence

The instructions must clearly distinguish:

- normative inputs
- normative enforcement outputs
- audit surfaces
- diagnostic surfaces
- publication surfaces
- candidate evidence surfaces

## Acceptance conditions

The pass fixture to evidence packet handoff may be accepted as a planning baseline when:

1. the pass fixture remains guarded as packet-baseline source candidate;
2. the target packet layout is canonical;
3. source-to-packet mapping is defined;
4. recorded status mapping is defined;
5. expected outcome mapping is defined;
6. policy and registry mapping are defined;
7. materialized gate-set mapping is defined;
8. CI outcome mapping is defined;
9. release authority manifest mapping is defined;
10. audit bundle mapping is defined;
11. digest coverage is defined;
12. operator handoff mapping is defined;
13. reconstruction instructions are defined;
14. field-point authority classification is defined;
15. no non-normative surface claims independent release authority.

Acceptance of this plan is not acceptance of a release-grade packet.

## Rejection conditions

A future implementation should reject a packet candidate when:

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
- audit, diagnostic, publication, HPC, recognition, or handoff surfaces claim independent release authority;
- missing evidence is interpreted as PASS.

All negative conditions should fail closed.

## Implementation sequence

The next implementation should proceed conservatively.

Suggested sequence:

1. create a packet builder mode for the pass fixture source;
2. generate canonical packet paths;
3. copy or render `status/status.json`;
4. copy declared policy and registry;
5. materialize gate sets;
6. write `ci/ci_outcome.json`;
7. write release authority manifest;
8. write audit bundle;
9. write package manifest;
10. write package digests;
11. write operator handoff report;
12. write reconstruction instructions;
13. add a packet-baseline fixture;
14. add a packet-completeness checker;
15. keep the checker non-authoritative;
16. only later connect the packet candidate to RA1-style verification.

The first implementation should verify packet completeness and authority boundaries.

It should not authorize release.

## Relation to minimal content packet builder

The existing minimal content packet builder is useful as a structural bridge.

The pass-fixture handoff is stricter because it starts from a concrete positive release-reference fixture.

The builder implementation may reuse layout-generation patterns from the minimal content packet builder.

It must not reuse non-release-grade placeholders as if they were release-grade evidence.

## Relation to RA1

RA1 remains the stricter concrete package-verification path.

This handoff plan does not run RA1.

This handoff plan does not replace RA1.

This handoff plan does not relax RA1.

A future packet candidate may later be checked by RA1-style verification.

## Relation to fellowship / HPC validation

The pass-fixture evidence packet handoff prepares the first positive packet-shaped baseline candidate.

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
- CI workflow behavior;
- RA1 verifier behavior;
- release-authority semantics.

## Closing statement

The pass fixture proves a controlled positive release-reference candidate.

The evidence packet baseline defines the packet field that must preserve such a candidate.

This handoff plan connects them.

The next implementation should transform the guarded pass fixture into a packet-shaped baseline candidate without changing release authority.

The packet preserves the PULSEmech path.

It does not replace it.

# PULSEmech Artifact-to-Claim Map v0

Status: artifact-to-claim map  
Paper status: pre-draft support document  
Primary category target: cs.SE  
Scope: PULSEmech / artifact-bound release authority / AI release decisions / software engineering  
Authority status: non-normative paper-planning document  
Repository status: does not change PULSE release-authority semantics

## Purpose

This document maps candidate PULSEmech paper claims to repository artifacts.

The purpose is to prevent unsupported manuscript expansion.

A paper-level claim may enter the draft only when its support status is clear:

- mechanically defined by PULSEmech;
- supported by repository artifact;
- supported by test / CI / regression;
- stated as limitation;
- stated as future work.

Claims outside these classes should not enter the paper.

## Working rule

Do not decorate claims.

Bind claims to artifacts.

Workshop rule:

Nem az eredményt magyarázzuk. A viszonyt mérjük.

Paper rule:

Do not explain an outcome after the fact.

Measure the pre-release relation between recorded evidence, declared policy, materialized gates, and fail-closed CI enforcement.

## Core paper claim

PULSEmech is an artifact-bound, policy-declared, gate-materialized, CI-enforced evidence-to-decision mechanism for AI release decisions.

## Normative PULSEmech path

The normative PULSEmech release-authority path is:

recorded release evidence  
→ recorded `status.json` artifact  
→ declared gate policy  
→ materialized required gate set  
→ strict fail-closed CI gate enforcement  
→ declared-policy CI allow/block release decision

## Claim map status vocabulary

| Status | Meaning |
|---|---|
| `mechanically-defined` | The claim is defined by the PULSEmech decision model. |
| `artifact-supported` | The claim is supported by repository documents, schemas, scripts, or generated artifacts. |
| `test-supported` | The claim is supported by tests, smoke checks, CI checks, or regression fixtures. |
| `boundary-claim` | The claim states what PULSE does not claim or does not do. |
| `paper-planning` | The claim is used to structure the future paper and must be verified before final manuscript use. |
| `future-work` | The claim belongs to later work and must not be written as current capability. |

## Authority status vocabulary

| Authority status | Meaning |
|---|---|
| `normative path` | Part of the PULSEmech release-authority decision path. |
| `normative input` | Input to the release-authority decision path. |
| `normative enforcement` | Enforces the declared-policy gate decision. |
| `non-normative trace` | Records or reconstructs the decision path but does not create release authority. |
| `non-normative preservation` | Preserves artifacts for audit or reconstruction. |
| `non-normative reader` | Renders or displays state for humans or public surfaces. |
| `non-normative diagnostic` | Produces diagnostic or candidate evidence unless explicitly folded into required gates under declared policy. |
| `paper-planning only` | Organizes future manuscript work and does not change repository behavior. |

## Artifact-to-claim table

| Claim ID | Paper claim | Artifact evidence | Evidence role | Authority status | Boundary / non-claim | Verification status |
|---|---|---|---|---|---|---|
| `C01_RELEASE_AUTHORITY_IDENTITY` | PULSE is an artifact-bound release-authority mechanism for AI applications and AI-enabled systems. | `README.md`; `docs/papers/PULSEMECH_CS_SE_PAPER_SKELETON_v0.md` | Defines public identity and paper scope. | paper-planning only / identity statement | Does not claim PULSE is a generic governance framework or dashboard. | to verify before manuscript |
| `C02_PULSEMECH_DECISION_TUPLE` | PULSE release-authority identity is defined by the deterministic PULSEmech decision tuple. | `README.md`; `docs/papers/PULSEMECH_CS_SE_PAPER_SKELETON_v0.md` | Defines the paper's central mechanism. | normative path | Does not claim every repository surface is normative. | to verify before manuscript |
| `C03_PRE_RELEASE_MEASUREMENT` | PULSE evaluates release permission before release effects propagate. | `README.md`; `docs/PULSE_RELATIONAL_EVIDENCE_FIELD_PRINCIPLE_v0.md`; paper skeleton | Establishes pre-release measurement boundary. | normative path / paper-planning | Does not explain post-event outcomes as release authority. | to verify before manuscript |
| `C04_STATUS_ARTIFACT` | `status.json` is the machine-readable release-state artifact for recorded release state. | `docs/STATUS_CONTRACT.md`; `docs/status_json.md`; `schemas/status/status_v1.schema.json`; current `status.json` surfaces | Defines machine-readable release state. | normative input | Does not claim a status file alone authorizes release. | to verify before manuscript |
| `C05_DECLARED_POLICY` | Required gates are declared by policy. | `pulse_gate_policy_v0.yml`; policy docs if cited | Defines required, core_required, release_required, and advisory gate sets. | normative input | Does not claim policy text alone creates a release decision. | to verify before manuscript |
| `C06_GATE_REGISTRY` | Gate meaning is stabilized through the gate registry. | `pulse_gate_registry_v0.yml` | Supports stable gate identifiers and semantics. | normative support / artifact-supported | Does not replace declared policy or CI enforcement. | to verify before manuscript |
| `C07_MATERIALIZED_REQUIRED_GATES` | Required and release_required gates can be materialized from declared policy. | `tools/policy_to_require_args.py`; `gates/materialized_gate_sets.json` in generated packets; `scripts/build_pulse_ref_schema_aligned_pass_fixture_packet_v0.py`; `scripts/check_pulse_ref_schema_aligned_packet_v0.py` | Connects declared policy to concrete enforced gate set. | normative input when bound to release path | Does not allow hard-coded promotion of gates outside policy. | to verify before manuscript |
| `C08_TRUE_ONLY_FAIL_CLOSED_CHECKING` | Required gates are enforced as literal true-only checks; missing, false, or invalid values fail closed. | `PULSE_safe_pack_v0/tools/check_gates.py`; `tests/test_check_gates_fail_closed.py`; policy-to-check-gates tests | Defines strict gate enforcement behavior. | normative enforcement | Does not claim advisory gates block by default. | to verify before manuscript |
| `C09_CI_ALLOW_BLOCK_DECISION` | The declared-policy CI gate-enforcement outcome is the release decision. | `.github/workflows/pulse_ci.yml`; `PULSE_safe_pack_v0/tools/check_gates.py`; README normative path | Connects enforcement to release allow/block decision. | normative enforcement | Does not claim all CI jobs are release-authority jobs. | to verify before manuscript |
| `C10_AUTHORITY_BOUNDARY` | PULSE separates normative release-authority surfaces from trace, audit, reader, diagnostic, and packet-preparation surfaces. | `README.md`; `docs/OPTIONAL_LAYERS.md`; `docs/SPACE_RELATION_MAP_v0.md`; paper skeleton | Prevents surface-role collapse. | mixed: normative / non-normative classification | Does not promote dashboards, ledgers, badges, manifests, or packets into authority by existence. | to verify before manuscript |
| `C11_MANIFEST_TRACE_NOT_ENGINE` | The release authority manifest records the decision trail but does not create a second decision engine. | `release_authority_v0.json` surfaces; `schemas/release_authority_v0.schema.json`; `PULSE_safe_pack_v0/tools/check_release_authority_manifest_v0.py`; manifest tests | Preserves decision trace and reconstruction. | non-normative trace | Does not override CI allow/block decision. | to verify before manuscript |
| `C12_AUDIT_BUNDLE_PRESERVATION` | Audit bundles preserve reconstructable evidence but do not create release authority. | audit bundle artifacts; RA1 package verifier docs/tests; `tools/verify_pulse_ref_ra1_package.py` if used in the current repo path | Supports preservation and reconstruction. | non-normative preservation | Does not replace status, policy, gate materialization, or CI enforcement. | to verify before manuscript |
| `C13_EXTERNAL_EVIDENCE_SEMANTICS` | External evidence must be recorded and policy-routed before it can affect release authority. | `docs/EXTERNAL_DETECTORS.md`; `docs/external_detector_summaries.md`; `PULSE_safe_pack_v0/tools/augment_status.py`; external evidence tests | Defines external evidence handling. | candidate evidence / normative only if policy-routed and enforced | Does not treat external summaries as automatically authoritative. | to verify before manuscript |
| `C14_RELEASE_REFERENCE_PASS_FIXTURE` | The positive PULSE-REF pass fixture provides a controlled release-reference candidate state. | `tests/fixtures/release_reference_v1/pass/status.json`; `tests/fixtures/release_reference_v1/pass/expected_outcome.json`; pass fixture guard tests | Provides controlled positive source candidate. | test-supported / fixture | Does not claim fixture existence authorizes release. | to verify before manuscript |
| `C15_RELEASE_REFERENCE_COMPLETENESS_GUARD` | Release-reference fixture candidates are checked for completeness before packet generation. | `ci/check_release_reference_complete_v1.py`; `scripts/build_pulse_ref_schema_aligned_pass_fixture_packet_v0.py`; related tests | Guards pass fixture before packet generation. | test-supported / artifact-supported | Does not replace release authority path. | to verify before manuscript |
| `C16_SCHEMA_ALIGNED_PACKET_BUILDER` | The schema-aligned pass-fixture packet builder prepares a reconstructable v0 packet candidate. | `scripts/build_pulse_ref_schema_aligned_pass_fixture_packet_v0.py`; `tests/test_build_pulse_ref_schema_aligned_pass_fixture_packet_v0.py`; checkpoint doc | Generates canonical packet artifacts from guarded pass fixture. | non-normative packet-preparation surface | Does not create release authority and does not run RA1. | to verify before manuscript |
| `C17_SCHEMA_ALIGNED_PACKET_VALIDATOR` | The schema-aligned packet validator checks artifact shape and reconstruction readiness. | `scripts/check_pulse_ref_schema_aligned_packet_v0.py`; `tests/test_check_pulse_ref_schema_aligned_packet_v0.py` | Validates canonical artifacts, manifest refs, digests, and schema targets. | non-normative checker / reconstruction readiness | Does not validate model safety or create release permission. | to verify before manuscript |
| `C18_PUBLICATION_REF_HARDENING` | Optional publication snapshot manifest refs are path-safe, canonical-path checked, packet-root contained, and sha256 checked when present. | `scripts/check_pulse_ref_schema_aligned_packet_v0.py`; publication snapshot tests | Closes optional publication-reference drift gap. | non-normative publication / reconstruction integrity | Does not make live publication surfaces normative release authority. | to verify before manuscript |
| `C19_CURRENT_V0_PACKET_COMPLETENESS_BOUNDARY` | The current v0 builder output is reconstructable but does not yet require field-point authority-map or admissibility artifacts. | `docs/PULSE_REF_SCHEMA_ALIGNED_PACKET_BUILDER_CHECKPOINT_v0.md` | Records current implementation boundary. | paper-planning / non-normative checkpoint | Does not abandon future packet-completeness surfaces. | to verify before manuscript |
| `C20_GENERATED_PACKET_DRIFT_REGRESSION` | The generated schema-aligned packet output is protected by normalized golden-summary regression. | `tests/test_generated_schema_aligned_pass_fixture_packet_regression_v0.py`; `tests/fixtures/pulse_ref_schema_aligned_pass_fixture_packet_summary_v0.json`; `ci/tools-tests.list` | Detects silent mechanical drift in generated packet output. | test-supported / regression | Does not compare raw full-tree bytes and does not introduce new release authority. | to verify before manuscript |
| `C21_RELATIONAL_EVIDENCE_FIELD` | PULSE preserves the evidence relation behind a terminal release decision. | `docs/PULSE_RELATIONAL_EVIDENCE_FIELD_PRINCIPLE_v0.md`; packet checkpoint doc | Explains decision field preservation. | non-normative field principle | Does not replace the PULSEmech normative path. | to verify before manuscript |
| `C22_RESULT_NOT_MECHANISM` | A release outcome is not equivalent to the release mechanism. | paper skeleton; workshop principle; PULSEmech tuple | Supports paper framing around pre-release relation measurement. | paper-planning only | Should be written as mechanism framing, not philosophical proof. | to verify before manuscript |
| `C23_NOT_MODEL_SAFETY_PROOF` | PULSE does not prove that an AI system is safe. | paper skeleton limitations; README boundary language where applicable | Limitation. | boundary-claim | Prevents overclaiming. | to verify before manuscript |
| `C24_NOT_RUNTIME_GUARDRAIL` | PULSE is not a runtime guardrail. | README release boundary; paper skeleton limitations | Limitation. | boundary-claim | PULSE operates at release boundary, before deployment. | to verify before manuscript |
| `C25_NOT_HUMAN_REVIEW_REPLACEMENT` | PULSE does not replace human review. | paper skeleton limitations; operator handoff docs where applicable | Limitation. | boundary-claim | PULSE records and enforces release evidence, not human judgment replacement. | to verify before manuscript |
| `C26_NOT_FRAMEWORK_IDENTITY` | The paper should not identify PULSE as a generic framework. | README front-door guard; `tests/test_readme_release_authority_category_signal_v0.py`; paper skeleton terminology boundary | Protects category identity. | paper-planning / recognition-surface guard | May use generic terms only when not defining identity. | to verify before manuscript |
| `C27_CS_SE_CATEGORY_FIT` | The primary paper category is cs.SE because the contribution concerns software release engineering, CI enforcement, artifact contracts, release-decision integrity, and reproducible packet validation. | paper skeleton category rationale; repository artifact structure | Supports arXiv category choice. | paper-planning only | Does not recast the contribution as machine learning methodology. | to verify before manuscript |
| `C28_AI_ASSISTED_DRAFTING_DISCLOSURE` | AI-assisted drafting and technical editing should be disclosed in the manuscript. | paper skeleton disclosure placeholder | Publication-process support. | paper-planning only | AI tools are not authors; human author remains responsible. | to verify before submission |
| `C29_REPRODUCIBILITY_SPINE` | The paper should present reproducibility through artifacts, validators, tests, and regression rather than unsupported narrative. | PULSE-REF builder, validator, regression, CI tests | Organizes validation section. | paper-planning / test-supported | Does not imply external replication has already occurred. | to verify before manuscript |
| `C30_FUTURE_RA1_HPC_EXTENSION` | RA1 and HPC validation paths may extend packet verification and candidate-state scaling in future work. | checkpoint docs; PULSE-REF docs; HPC docs if cited | Future work. | future-work | Must not be written as current paper result unless artifact-backed. | to verify before manuscript |

## Claim acceptance rule

A claim may be promoted into manuscript prose only if:

1. it appears in the artifact-to-claim table;
2. it has at least one repository artifact or explicit limitation/future-work classification;
3. its authority status is identified;
4. its non-claim boundary is stated;
5. it does not inflate a non-normative surface into release authority.

## Claim rejection rule

Reject or rewrite the claim when:

- it has no repository artifact;
- it relies on rhetorical effect rather than mechanism;
- it treats an outcome as the mechanism;
- it treats a reader surface as release authority;
- it treats a trace surface as a decision engine;
- it implies PULSE proves model safety;
- it implies PULSE replaces human review;
- it implies PULSE is a runtime guardrail;
- it moves future RA1 / HPC work into current capability;
- it uses identity terms that flatten PULSE into a generic framework.

## Draft expansion order

The manuscript should be expanded in this order:

1. Abstract from accepted claims only.
2. Introduction from `C01`, `C03`, `C22`, and `C27`.
3. Release-authority model from `C02` through `C09`.
4. Authority boundary from `C10` through `C13`.
5. PULSE-REF path from `C14` through `C20`.
6. Relational evidence-field framing from `C21`, carefully kept non-normative.
7. Limitations from `C23` through `C25`.
8. Reproducibility and future work from `C29` and `C30`.
9. Disclosure from `C28`.

## Manuscript-risk notes

High-risk phrases to avoid or rewrite:

| Risk phrase | Safer paper form |
|---|---|
| PULSE proves AI safety | PULSE makes release permission evidence-bound and fail-closed under declared policy. |
| PULSE is an AI governance framework | PULSE is an artifact-bound release-authority mechanism. |
| The manifest decides release | The manifest records the decision trail. |
| The audit bundle authorizes release | The audit bundle preserves reconstructable evidence. |
| The dashboard shows release authority | The dashboard renders release state as a reader surface. |
| The packet creates release authority | The packet preserves and reconstructs the evidence relation. |
| The result proves the mechanism | The mechanism is defined by the pre-release relation and enforced path. |

## Minimum artifact verification before full draft

Before expanding this into full paper prose, verify exact artifact references for:

- README PULSEmech identity;
- status contract and schema;
- declared policy;
- policy materializer;
- check_gates fail-closed behavior;
- CI workflow enforcement;
- release authority manifest checker;
- PULSE-REF pass fixture;
- release-reference completeness guard;
- schema-aligned builder;
- schema-aligned packet validator;
- publication snapshot ref hardening;
- normalized generated-packet regression;
- current v0 packet-completeness boundary.

## Next paper step

After this map is merged, the next paper step is:

`docs(paper): add PULSEmech paper claim-boundary review`

That review should turn the table into a shorter manuscript-facing claim list with exact artifact references prepared for citation or footnote use.

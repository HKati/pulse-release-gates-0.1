# PULSEmech Bibliography Lock Plan v0

Status: bibliography lock plan  
Paper status: pre-submission support document  
Primary category target: cs.SE  
Scope: PULSEmech / artifact-bound release authority / AI release decisions / software engineering  
Authority status: non-normative paper-support document  
Repository status: does not change PULSE release-authority semantics

## Purpose

This document defines the bibliography and source-lock plan for the future PULSEmech cs.SE paper.

It follows:

- `docs/papers/PULSEMECH_CS_SE_PAPER_SKELETON_v0.md`
- `docs/papers/PULSEMECH_ARTIFACT_TO_CLAIM_MAP_v0.md`
- `docs/papers/PULSEMECH_CLAIM_BOUNDARY_REVIEW_v0.md`
- `docs/papers/PULSEMECH_MANUSCRIPT_CLAIM_ARTIFACT_VERIFICATION_v0.md`
- `docs/papers/PULSEMECH_MINIMAL_FIRST_DRAFT_OUTLINE_v0.md`
- `docs/papers/PULSEMECH_CONTROLLED_PROSE_SKELETON_v0.md`
- `docs/papers/PULSEMECH_FIRST_PROSE_DRAFT_v0.md`
- `docs/papers/PULSEMECH_ARTIFACT_CITATION_PASS_v0.md`
- `docs/papers/PULSEMECH_CITATION_BOUND_PROSE_DRAFT_v0.md`
- `docs/papers/PULSEMECH_RELATED_WORK_SCAFFOLD_v0.md`
- `docs/papers/PULSEMECH_LITERATURE_SEARCH_PLAN_v0.md`
- `docs/papers/PULSEMECH_LITERATURE_SOURCE_TABLE_v0.md`
- `docs/papers/PULSEMECH_RELATED_WORK_PROSE_v0.md`

The purpose is to define how source IDs, repository artifact anchors, external literature sources, and final manuscript citations will be locked before submission-stage use.

This document does not finalize bibliography entries.

This document does not add new related-work claims.

This document does not change PULSE release-authority semantics.

## Working rule

Do not cite unstable text as if it were locked evidence.

Do not convert a source ID into a final citation until metadata, locator, role, boundary, and include decision are verified.

Workshop rule:

Nem az eredményt magyarázzuk. A viszonyt mérjük.

Bibliography-lock rule:

Do not cite the source as decoration.

Lock the source relation:

source  
→ role  
→ area ID  
→ relevance  
→ boundary  
→ stable locator  
→ final citation form

## Bibliography lock boundary

This plan is not the bibliography.

It is not a final related-work section.

It is not an arXiv submission package.

It defines the checklist for converting source IDs and artifact anchors into final citation-ready references.

A later lock pass must fill:

- full citation metadata;
- DOI / arXiv ID / stable URL;
- final include status;
- source role;
- source boundary;
- exact manuscript placement;
- final citation key;
- final bibliography format.

## Citation lock objects

The bibliography lock must cover two kinds of references:

1. external literature sources;
2. repository artifact anchors.

These should not be mixed.

External literature sources support related work, context, contrast, terminology, or methodology.

Repository artifact anchors support PULSEmech implementation, claim verification, artifact paths, and paper-planning traceability.

## External source lock fields

Each external source must eventually have:

| Field | Required | Notes |
|---|---:|---|
| Source ID | yes | Must match `RW-SRC-*` from literature source table. |
| Canonical Area ID | yes | Must match scaffold / search plan area IDs. |
| Final citation key | yes | Stable short key for draft references. |
| Full author list | yes | No guessed names. |
| Title | yes | Exact title. |
| Venue / publisher / source | yes | Conference, journal, arXiv, standard body, official documentation, or project. |
| Year | yes | Exact publication / version year where available. |
| DOI | if available | Prefer DOI for papers / standards when available. |
| arXiv ID | if applicable | Use for arXiv papers when applicable. |
| Stable URL | if needed | Use only stable official or archival URL. |
| Source quality tier | yes | Must use tier vocabulary from literature search plan. |
| Source role | yes | Must use role vocabulary from literature search plan. |
| Include decision | yes | include / reserve / boundary-only / exclude / needs final citation lock. |
| Relevance note | yes | One sentence. |
| Boundary note | yes | One sentence. |
| Manuscript placement | yes | Related-work paragraph / boundary contrast / footnote / reserve. |
| Final lock status | yes | See lock-status vocabulary below. |

## Repository artifact lock fields

Each repository artifact anchor must eventually have:

| Field | Required | Notes |
|---|---:|---|
| Artifact ID | yes | Stable local identifier. |
| Artifact path | yes | Exact repository path or generated-run path. |
| Artifact type | yes | static repo document / schema / script / test / workflow / generated-run artifact. |
| Claim supported | yes | Map to draft claim ID or prose section. |
| Authority role | yes | normative / non-normative / paper-planning / generated-run support. |
| Static or generated | yes | Must distinguish checked-in file from generated run artifact. |
| Commit / release lock | submission-stage | Required before final submission package. |
| DOI / Zenodo lock | if used | Required if artifact is cited through a release DOI. |
| Boundary note | yes | Prevent overpromotion. |
| Final lock status | yes | See lock-status vocabulary below. |

## Lock status vocabulary

| Lock status | Meaning |
|---|---|
| `unlocked` | Metadata or locator is not ready for submission-stage use. |
| `metadata-checked` | Basic bibliographic metadata or artifact path has been checked. |
| `locator-checked` | DOI, arXiv ID, stable URL, commit, or release locator has been checked. |
| `boundary-checked` | Source boundary / artifact role has been checked. |
| `citation-ready` | Source or artifact is ready to appear in a submission-stage manuscript. |
| `reserve` | Keep source available but do not use unless explicitly promoted in a later source-selection update. |
| `exclude` | Do not use source in final paper. |
| `needs replacement` | Source is only a placeholder or insufficient and must be replaced. |

## Reserve promotion rule

Reserve sources must remain unavailable for prose, citation-key replacement, and final bibliography until explicitly promoted.

A reserve source is not promoted merely because it seems useful or needed.

Promotion requires a later source-selection update that records:

- the source ID;
- the promotion reason;
- the manuscript section where it will be used;
- the source role;
- the boundary note;
- the updated include decision;
- citation metadata / locator lock requirements.

Until such promotion is recorded, reserve sources remain reserve-only.

## Citation key convention

External literature sources should use readable citation keys.

Preferred format:

```text
AuthorYearShortTopic
```

Examples:

```text
Shahin2017CICDReview
OPA_PolicyAsCode
NIST2022SSDF
SLSA2026Spec
InTotoSpec
JSONSchema2020
Mitchell2019ModelCards
Wang2026GuardrailsSoK
Okafor2022SupplyChainSoK
```

Repository artifact anchors should use `PULSE_` keys.

Preferred format:

```text
PULSE_<ARTIFACT>_<VERSION_OR_ROLE>
```

Examples:

```text
PULSE_README_RELEASE_AUTHORITY
PULSE_STATUS_CONTRACT
PULSE_GATE_POLICY_V0
PULSE_CHECK_GATES
PULSE_REF_PACKET_BUILDER
PULSE_REF_PACKET_VALIDATOR
PULSE_GENERATED_PACKET_REGRESSION
```

Final keys may change during bibliography formatting.

## External literature lock table placeholder

| Source ID | Area ID | Final citation key | Citation metadata | Locator | Source role | Include decision | Lock status | Boundary |
|---|---|---|---|---|---|---|---|---|
| `RW-SRC-001` | `RW01_RELEASE_ENGINEERING`; `RW02_CI_CD_GATES` | `Shahin2017CICDReview` | to verify | DOI / stable locator to verify | context / direct comparison | include | unlocked | CI/CD context, not PULSEmech authority. |
| `RW-SRC-003` | `RW03_POLICY_AS_CODE` | `OPA_PolicyAsCode` | to verify | official docs URL/version to verify | direct comparison / terminology support | include | unlocked | Policy text alone does not authorize release. |
| `RW-SRC-004` | `RW04_SOFTWARE_ASSURANCE`; `RW05_SUPPLY_CHAIN_PROVENANCE` | `NIST2022SSDF` | to verify | NIST stable URL/DOI to verify | standard / specification / context | include | unlocked | Secure development context, not complete assurance case. |
| `RW-SRC-005` | `RW05_SUPPLY_CHAIN_PROVENANCE` | `SLSA2026Spec` | to verify | official spec URL/version to verify | standard / specification / methodological support | include | unlocked | Provenance does not authorize release by itself. |
| `RW-SRC-007` | `RW05_SUPPLY_CHAIN_PROVENANCE`; `RW06_REPRODUCIBLE_ARTIFACTS`; `RW12_AUDITABILITY_AND_TRACEABILITY` | `InTotoSpec` | to verify | official docs/spec URL to verify | standard / specification / direct comparison | include | unlocked | Trace metadata is not release authority. |
| `RW-SRC-009` | `RW06_REPRODUCIBLE_ARTIFACTS`; `RW12_AUDITABILITY_AND_TRACEABILITY` | `ACM2020ArtifactBadging` | to verify | ACM stable URL to verify | methodological support / terminology support | include | unlocked | Artifact review terminology, not proof of external replication. |
| `RW-SRC-010` | `RW07_FORMAL_OR_TYPED_RELEASE_CONTRACTS` | `JSONSchema2020` | to verify | official specification URL to verify | standard / specification / terminology support | include | unlocked | Schema validity is not release permission. |
| `RW-SRC-012` | `RW08_MLOPS_RELEASE_READINESS` | `Sculley2015MLDebt` | to verify | DOI / stable URL to verify | context / boundary contrast | include | unlocked | AI systems context, not PULSEmech identity. |
| `RW-SRC-014` | `RW09_AI_EVALUATION_INFRASTRUCTURE` | `Mitchell2019ModelCards` | to verify | DOI / arXiv / stable URL to verify | context / boundary contrast | include | unlocked | Model reports are evidence, not release authority. |
| `RW-SRC-015` | `RW10_AI_SAFETY_GOVERNANCE_BOUNDARY` | `NIST2023AIRMF` | to verify | NIST stable URL / DOI / PDF locator to verify | boundary contrast / context | boundary-only | unlocked | Governance context only; not PULSEmech identity. |
| `RW-SRC-016` | `RW11_RUNTIME_GUARDRAILS` | `Wang2026GuardrailsSoK` | to verify | arXiv / IEEE S&P 2026 proceedings metadata to verify | boundary contrast | include | unlocked | Runtime guardrails differ from pre-release authority. |
| `RW-SRC-019` | `RW05_SUPPLY_CHAIN_PROVENANCE` | `Okafor2022SupplyChainSoK` | to verify | ACM SCORED 2022 proceedings metadata / arXiv locator to verify | context / methodological support | include | unlocked | Supply-chain security context, not PULSEmech mechanism. |

## Reserve source lock table placeholder

| Source ID | Area ID | Final citation key | Reason held in reserve | Lock status |
|---|---|---|---|---|
| `RW-SRC-002` | `RW01_RELEASE_ENGINEERING`; `RW02_CI_CD_GATES` | to fill | May be promoted only if the paper needs additional CI/CD architecture context beyond the primary CI/CD review source. | reserve |
| `RW-SRC-006` | `RW05_SUPPLY_CHAIN_PROVENANCE` | to fill | May be promoted only for SLSA adoption-friction context. | reserve |
| `RW-SRC-008` | `RW05_SUPPLY_CHAIN_PROVENANCE`; `RW12_AUDITABILITY_AND_TRACEABILITY` | to fill | May be promoted only if the supply-chain / update-system security section is explicitly expanded. | reserve |
| `RW-SRC-011` | `RW07_FORMAL_OR_TYPED_RELEASE_CONTRACTS` | to fill | May be promoted only if the schema-validation discussion deepens. | reserve |
| `RW-SRC-013` | `RW08_MLOPS_RELEASE_READINESS` | to fill | May be promoted only if the MLOps contrast needs additional source support. | reserve |
| `RW-SRC-018` | `RW05_SUPPLY_CHAIN_PROVENANCE`; `RW13_RELEASE_DECISION_STABILITY` | to fill | May be promoted only if signing / verification workflow friction becomes relevant. | reserve |
| `RW-SRC-020` | `RW04_SOFTWARE_ASSURANCE`; `RW10_AI_SAFETY_GOVERNANCE_BOUNDARY` | to fill | May be promoted only for careful AI risk / governance boundary context. | reserve |

## Placeholder replacement requirement

The current source table contains at least one known placeholder / gap:

- `RW-SRC-017` — regression / snapshot / golden testing literature placeholder.

This must not appear as a final citation.

Before submission-stage use:

- replace it with a real source; or
- remove regression-literature claims that require an external source; or
- keep regression discussion internal to PULSE artifact methodology without citing a placeholder.

## Repository artifact citation lock table placeholder

| Artifact ID | Artifact path | Artifact type | Claim supported | Static or generated | Lock status | Boundary |
|---|---|---|---|---|---|---|
| `PULSE_README_RELEASE_AUTHORITY` | `README.md` | static repo document | PULSEmech identity / tuple / normative path | static | unlocked | README supports identity; paper still needs final citation lock. |
| `PULSE_STATUS_CONTRACT` | `docs/STATUS_CONTRACT.md` | static repo document | status artifact role | static | unlocked | `status.json` alone does not authorize release. |
| `PULSE_STATUS_JSON_DOC` | `docs/status_json.md` | static repo document | status artifact role / generated path wording | static | unlocked | Generated status path must not be cited as static root file. |
| `PULSE_STATUS_SCHEMA` | `schemas/status/status_v1.schema.json` | static repo schema | status artifact shape | static | unlocked | Schema validity is not release permission. |
| `PULSE_GATE_POLICY_V0` | `pulse_gate_policy_v0.yml` | static repo policy | declared policy | static | unlocked | Policy text alone does not authorize release. |
| `PULSE_GATE_REGISTRY_V0` | `pulse_gate_registry_v0.yml` | static repo registry | gate identity / meaning | static | unlocked | Registry supports interpretation, not release decision alone. |
| `PULSE_POLICY_MATERIALIZER` | `tools/policy_to_require_args.py` | static repo script | policy-derived materialized gates | static | unlocked | Materialization supports enforcement. |
| `PULSE_CHECK_GATES` | `PULSE_safe_pack_v0/tools/check_gates.py` | static repo script | fail-closed gate enforcement | static | unlocked | Checker enforces declared required gates. |
| `PULSE_CI_WORKFLOW` | `.github/workflows/pulse_ci.yml` | workflow path | CI enforcement / generated artifact paths | static workflow | unlocked | Not every CI job is release authority. |
| `PULSE_GENERATED_STATUS_ARTIFACT` | `PULSE_safe_pack_v0/artifacts/status.json` | generated-run artifact path | generated status artifact | generated | unlocked | Generated run artifact, not checked-in static file. |
| `PULSE_RELEASE_AUTHORITY_MANIFEST_DOC` | `docs/release_authority_manifest_v0.md` | static repo document | manifest trace / audit boundary | static | unlocked | Manifest is not a decision engine. |
| `PULSE_RELEASE_AUTHORITY_SCHEMA` | `schemas/release_authority_v0.schema.json` | static repo schema | manifest shape | static | unlocked | Schema validates trace shape. |
| `PULSE_RELEASE_AUTHORITY_CHECKER` | `PULSE_safe_pack_v0/tools/check_release_authority_manifest_v0.py` | static repo script | manifest checking | static | unlocked | Checker does not create release authority. |
| `PULSE_AUDIT_BUNDLE_GENERATED_PATH` | `PULSE_safe_pack_v0/artifacts/release_authority_audit_bundle/` | generated-run artifact path | audit bundle preservation | generated | unlocked | Generated audit bundle, non-normative / non-blocking. |
| `PULSE_REF_PASS_STATUS_FIXTURE` | `tests/fixtures/release_reference_v1/pass/status.json` | static repo fixture | controlled positive fixture | static | unlocked | Fixture does not authorize release. |
| `PULSE_REF_PASS_EXPECTED_OUTCOME` | `tests/fixtures/release_reference_v1/pass/expected_outcome.json` | static repo fixture | fixture expected outcome | static | unlocked | Expected outcome does not override CI decision path. |
| `PULSE_REF_COMPLETENESS_GUARD` | `ci/check_release_reference_complete_v1.py` | static repo script | release-reference completeness guard | static | unlocked | Guard is not release authority. |
| `PULSE_REF_PACKET_BUILDER` | `scripts/build_pulse_ref_schema_aligned_pass_fixture_packet_v0.py` | static repo script | schema-aligned packet builder | static | unlocked | Builder does not create release authority. |
| `PULSE_REF_PACKET_VALIDATOR` | `scripts/check_pulse_ref_schema_aligned_packet_v0.py` | static repo script | packet validation | static | unlocked | Validator checks shape / readiness, not release permission. |
| `PULSE_REF_GENERATED_PACKET_REGRESSION` | `tests/test_generated_schema_aligned_pass_fixture_packet_regression_v0.py` | static repo test | generated-packet drift regression | static | unlocked | Regression detects drift, not authority. |
| `PULSE_REF_GOLDEN_SUMMARY` | `tests/fixtures/pulse_ref_schema_aligned_pass_fixture_packet_summary_v0.json` | static repo fixture | normalized generated-packet summary | static | unlocked | Golden summary is a regression fixture, not release permission. |

## Lock workflow

Before submission-stage draft:

1. Select final external source include set.
2. Replace placeholders and remove unusable sources.
3. Verify metadata for each included source.
4. Verify DOI / arXiv ID / stable URL where applicable.
5. Assign final citation keys.
6. Convert `RW-SRC-*` markers in prose to citation keys.
7. Verify repository artifact anchors against final commit or release.
8. Decide whether repository artifacts are cited by commit, GitHub URL, Zenodo DOI, or appendix.
9. Verify generated-run artifact wording.
10. Remove any citation that does not support mechanism, boundary, or context.
11. Confirm no source pulls PULSEmech into an incorrect identity.
12. Confirm final related-work prose remains compact.
13. Confirm reserve sources do not enter the paper unless explicitly promoted in a later source-selection update.

## Bibliography risk table

| Risk | Failure mode | Control |
|---|---|---|
| Decorative citation | Source sounds relevant but does not support mechanism or boundary. | Require relevance and boundary note. |
| Category drift | Source pulls PULSEmech into governance, MLOps, or runtime guardrail identity. | Use source only as context or boundary contrast. |
| Provenance overclaim | Supply-chain source makes provenance look like release authority. | State provenance supports reconstruction / integrity only. |
| CI/CD flattening | CI/CD source makes PULSEmech look like generic pipeline success. | State PULSEmech requires declared-policy materialized gates and fail-closed decision. |
| Schema overclaim | JSON Schema source makes schema validity look sufficient. | State schema validity is not release permission. |
| Artifact overclaim | Artifact/reproducibility source makes packet existence look authoritative. | State packets preserve evidence relation only. |
| Runtime confusion | Guardrail source makes PULSEmech look like runtime filter. | State PULSEmech acts before deployment. |
| Placeholder leakage | Placeholder source enters final prose. | Replace or remove all placeholders before submission-stage use. |
| Reserve leakage | Reserve source enters prose, citation-key replacement, or bibliography without explicit promotion. | Require a later source-selection update before use. |
| Unstable locator | Source lacks stable DOI/arXiv/URL. | Lock locator before final citation. |

## Final citation readiness checklist

A source is final-citation-ready only when:

- full citation metadata is checked;
- stable locator is checked;
- source role is checked;
- boundary is checked;
- include decision is final;
- manuscript placement is known;
- citation key is assigned;
- source does not inflate PULSEmech claims;
- source does not conflict with cs.SE positioning;
- reserve-source status has been explicitly promoted if the source was previously held in reserve.

A repository artifact is final-citation-ready only when:

- path exists;
- artifact role is correct;
- static vs generated status is clear;
- commit / release / DOI lock is selected;
- boundary note is present;
- artifact is not cited beyond its role.

## Validation checks for this document

Before merging changes to this document, run:

```bash
grep -n '^## External literature lock table placeholder$' docs/papers/PULSEMECH_BIBLIOGRAPHY_LOCK_PLAN_v0.md
grep -n '^## Reserve source lock table placeholder$' docs/papers/PULSEMECH_BIBLIOGRAPHY_LOCK_PLAN_v0.md
grep -n '^## Repository artifact citation lock table placeholder$' docs/papers/PULSEMECH_BIBLIOGRAPHY_LOCK_PLAN_v0.md
grep -n '^## Lock workflow$' docs/papers/PULSEMECH_BIBLIOGRAPHY_LOCK_PLAN_v0.md
grep -n '^## Bibliography risk table$' docs/papers/PULSEMECH_BIBLIOGRAPHY_LOCK_PLAN_v0.md
grep -n '^## Final citation readiness checklist$' docs/papers/PULSEMECH_BIBLIOGRAPHY_LOCK_PLAN_v0.md
grep -n '^## Reserve promotion rule$' docs/papers/PULSEMECH_BIBLIOGRAPHY_LOCK_PLAN_v0.md
grep -n 'explicitly promoted in a later source-selection update' docs/papers/PULSEMECH_BIBLIOGRAPHY_LOCK_PLAN_v0.md
! grep -n 'unless needed' docs/papers/PULSEMECH_BIBLIOGRAPHY_LOCK_PLAN_v0.md
grep -n 'RW-SRC-017' docs/papers/PULSEMECH_BIBLIOGRAPHY_LOCK_PLAN_v0.md
grep -n 'PULSE_safe_pack_v0/artifacts/status.json' docs/papers/PULSEMECH_BIBLIOGRAPHY_LOCK_PLAN_v0.md
grep -n 'PULSE_safe_pack_v0/artifacts/release_authority_audit_bundle/' docs/papers/PULSEMECH_BIBLIOGRAPHY_LOCK_PLAN_v0.md
```

Expected result:

- external literature lock table is present;
- reserve source lock table is present;
- repository artifact citation lock table is present;
- lock workflow is present;
- bibliography risk table is present;
- final citation readiness checklist is present;
- reserve promotion rule is present;
- reserve-source usage requires explicit promotion;
- loose `unless needed` wording is absent;
- placeholder source `RW-SRC-017` is explicitly tracked;
- generated status artifact path is present;
- generated audit bundle path is present.

## Next paper step

After this bibliography lock plan is merged, the next paper step is:

`docs(paper): add PULSEmech source metadata lock v0`

That step should fill verified metadata for the initial include set, replace placeholders where possible, and prepare final citation keys without yet creating the arXiv submission package.

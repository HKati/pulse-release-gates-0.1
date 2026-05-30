# PULSEmech Citation-Keyed Related-Work Draft v0

Status: citation-keyed related-work draft  
Paper status: pre-submission support document  
Primary category target: cs.SE  
Scope: PULSEmech / artifact-bound release authority / AI release decisions / software engineering  
Authority status: non-normative paper-support document  
Repository status: does not change PULSE release-authority semantics

## Purpose

This document converts the related-work prose v0 into a citation-keyed related-work draft.

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
- `docs/papers/PULSEMECH_BIBLIOGRAPHY_LOCK_PLAN_v0.md`
- `docs/papers/PULSEMECH_SOURCE_METADATA_LOCK_v0.md`
- `docs/papers/PULSEMECH_CITATION_KEY_REPLACEMENT_PASS_v0.md`

The purpose is to replace eligible `RW-SRC-*` markers with provisional citation keys while preserving submission-lock notes, source boundaries, and unresolved-placeholder protection.

This document does not finalize bibliography entries.

This document does not create an arXiv submission package.

This document does not change PULSE release-authority semantics.

## Replacement control rule

This draft follows the lock-aware citation key replacement rules.

Direct replacement is allowed only for sources in the direct replacement set.

Submission-lock-required sources keep visible lock notes.

Boundary-only sources keep boundary-marker wording.

Reserve sources do not enter this draft unless explicitly promoted in a later source-selection update.

`RW-SRC-017` remains unresolved and must not be converted into a citation key.

## Citation marker convention

This draft uses planning markers, not final bibliography syntax.

Direct replacement marker:

```text
[Source: NIST2022SSDF]
```

Lock-note replacement marker:

```text
[Source: Shahin2017CICDReview; submission lock required for final IEEE Access DOI / publication metadata]
```

Boundary-only replacement marker with lock note:

```text
[Boundary source: NIST2023AIRMF; governance / risk context only; submission lock required for final NIST AI RMF DOI / PDF locator]
```

Unresolved placeholder marker:

```text
[Source needed: RW13_RELEASE_DECISION_STABILITY / regression testing]
```

## Source replacement summary

| Source ID | Citation key / marker | Replacement treatment |
|---|---|---|
| `RW-SRC-001` | `Shahin2017CICDReview` | lock-note replacement |
| `RW-SRC-003` | `OPA_PolicyAsCode` | lock-note replacement |
| `RW-SRC-004` | `NIST2022SSDF` | direct replacement |
| `RW-SRC-005` | `SLSA2026Spec` | lock-note replacement |
| `RW-SRC-007` | `InTotoSpec` | lock-note replacement |
| `RW-SRC-009` | `ACM2020ArtifactBadging` | direct replacement |
| `RW-SRC-010` | `JSONSchema2020` | direct replacement |
| `RW-SRC-012` | `Sculley2015MLDebt` | lock-note replacement |
| `RW-SRC-014` | `Mitchell2019ModelCards` | lock-note replacement |
| `RW-SRC-015` | `NIST2023AIRMF` | boundary-only replacement with NIST DOI / PDF locator lock note |
| `RW-SRC-016` | `Wang2026GuardrailsSoK` | lock-note replacement, not boundary-only replacement |
| `RW-SRC-017` | none | unresolved placeholder; do not replace |
| `RW-SRC-019` | `Okafor2022SupplyChainSoK` | lock-note replacement |

## Related Work

### Release engineering and CI/CD gates

PULSEmech is related to prior work on continuous integration, continuous delivery, continuous deployment, and release gates. Continuous practices have been studied as software-engineering methods for frequent and reliable delivery, with literature identifying tooling, deployment-pipeline practices, testing challenges, visibility, security, scalability, and reliability concerns in CI/CD adoption [Source: Shahin2017CICDReview; submission lock required for final IEEE Access DOI / publication metadata]. This literature provides the release-engineering background for PULSEmech: release decisions are not merely social approvals, but are increasingly mediated by automated pipelines, checks, and artifacts.

PULSEmech differs from ordinary CI/CD framing by placing release authority on a declared-policy evidence-to-decision path. In conventional CI/CD, a green pipeline may indicate that a configured set of jobs passed. In PULSEmech, release permission is more narrowly defined: recorded release evidence must bind to a machine-readable status artifact, declared policy, policy-derived materialized gates, and strict fail-closed CI enforcement before a declared-policy allow/block decision materializes. CI is therefore the enforcement surface, not the whole release-authority model.

Related-work role:

- `RW01_RELEASE_ENGINEERING`
- `RW02_CI_CD_GATES`

Boundary:

Do not write that conventional CI/CD already provides PULSEmech release authority.

### Policy-as-code and declared enforcement

Policy-as-code systems provide an important comparison point because they encode policy in machine-checkable forms. Open Policy Agent describes a general-purpose policy engine using a declarative policy language and supports policy decision-making across systems including CI/CD pipelines [Source: OPA_PolicyAsCode; submission lock required for official documentation version/date or access date]. This helps position PULSEmech near declared policy and automated enforcement.

The difference is that PULSEmech does not treat policy text as sufficient release authority. Declared policy defines which gates must be materialized and enforced, but release permission is only produced by the complete path: recorded evidence, `status.json`, declared policy, materialized required gates, and strict fail-closed CI enforcement. Policy-as-code is therefore adjacent to PULSEmech, but PULSEmech adds the release-authority boundary and evidence-to-decision materialization path.

Related-work role:

- `RW03_POLICY_AS_CODE`

Boundary:

Do not write that policy text alone authorizes release.

### Software assurance, artifact integrity, and supply-chain provenance

PULSEmech also relates to software assurance and supply-chain provenance. NIST SSDF provides secure software development guidance for mitigating software vulnerability risk [Source: NIST2022SSDF]. SLSA defines a supply-chain security framework around provenance, build levels, and artifact verification concepts [Source: SLSA2026Spec; submission lock required for SLSA v1.2 version/date]. in-toto describes supply-chain metadata and link metadata for recording steps in a software supply chain [Source: InTotoSpec; submission lock required for exact specification / documentation version]. Systematization work on software supply-chain security also helps situate artifact integrity, provenance, and secure design properties as technical concerns around software production [Source: Okafor2022SupplyChainSoK; submission lock required for final ACM SCORED 2022 proceedings metadata / DOI].

These works are relevant because PULSEmech also treats artifacts, manifests, digests, and reproducible evidence as central surfaces. However, PULSEmech does not reduce release authority to provenance or artifact integrity. Provenance can support reconstruction and trust in an artifact chain, but it does not itself determine whether AI release permission may materialize. In PULSEmech, artifact integrity and provenance are support surfaces; release authority still depends on declared policy, materialized gates, and fail-closed enforcement.

Related-work role:

- `RW04_SOFTWARE_ASSURANCE`
- `RW05_SUPPLY_CHAIN_PROVENANCE`
- `RW12_AUDITABILITY_AND_TRACEABILITY`

Boundary:

Do not write that provenance, attestation, manifests, or audit logs authorize release by themselves.

### Reproducible artifacts, schemas, and typed release records

PULSE-REF uses reconstructable packet candidates, canonical artifact paths, manifest references, digests, and generated-packet regression. This places part of the work near research-artifact and reproducibility practices. ACM artifact review and badging guidance provides terminology and review structure around artifacts, reproducibility, repeatability, and related evaluation concepts [Source: ACM2020ArtifactBadging].

PULSEmech also uses schema-bound artifacts. JSON Schema provides a formal specification family for validating JSON data shape and constraints [Source: JSONSchema2020]. This is relevant to PULSE status artifacts, packet manifests, materialized gate sets, and release-authority traces. Schema-based validation supports artifact shape and reconstruction readiness.

The boundary is important: reproducible artifacts and schemas do not create release authority by themselves. A valid schema confirms artifact shape, not release permission. A reconstructable packet preserves an evidence relation, but it is not a release-decision engine. PULSEmech keeps the normative release decision on the declared-policy evidence-to-decision path.

Related-work role:

- `RW06_REPRODUCIBLE_ARTIFACTS`
- `RW07_FORMAL_OR_TYPED_RELEASE_CONTRACTS`
- `RW13_RELEASE_DECISION_STABILITY`

Boundary:

Do not write that schema validity or reproducible artifact packaging equals release permission.

Regression / snapshot / golden testing still needs a stronger external source before final submission-stage prose:

[Source needed: RW13_RELEASE_DECISION_STABILITY / regression testing]

### AI release readiness, model documentation, and evaluation artifacts

PULSEmech applies release-authority mechanics to AI applications and AI-enabled systems. Prior work on machine-learning systems engineering is relevant because ML systems create maintenance, dependency, configuration, testing, and deployment risks that differ from conventional software. The technical-debt literature for ML systems is useful background for treating AI systems as complex software-engineering objects [Source: Sculley2015MLDebt; submission lock required for final DOI / proceedings metadata].

Model documentation and evaluation reporting are also relevant. Model Cards propose structured model reporting, including intended use, evaluation results, and limitations [Source: Mitchell2019ModelCards; submission lock required for final ACM DOI / proceedings metadata]. Such artifacts are evidence surfaces: they can help describe a model or system, but they do not automatically become release permission.

PULSEmech treats evaluation reports, detector summaries, model documentation, review records, and CI outputs as candidate evidence. They become release-relevant only when recorded, routed under declared policy, materialized into required gates where applicable, and enforced fail-closed. This is the distinction between evidence surfaces and release authority.

Related-work role:

- `RW08_MLOPS_RELEASE_READINESS`
- `RW09_AI_EVALUATION_INFRASTRUCTURE`

Boundary:

Do not write that PULSEmech is an MLOps platform, model card, model-performance benchmark, or model-evaluation method.

### Runtime guardrails and AI governance as boundary contrast

Runtime guardrails are an important contrast class. Work on LLM jailbreak guardrails treats guardrails as mechanisms that monitor or control model interaction under adversarial prompting and evaluates their security, utility, and efficiency trade-offs [Source: Wang2026GuardrailsSoK; submission lock required for final IEEE S&P 2026 proceedings metadata / DOI]. This work is relevant because it clarifies a different boundary: runtime interaction control after deployment or during use.

PULSEmech operates at a different point. It acts before deployment at the release boundary. It does not filter individual prompts, moderate individual outputs, or control live interactions. A runtime guardrail may be part of the broader safety architecture of an AI system, but it is not the same mechanism as pre-release artifact-bound release authority.

AI governance and risk-management sources provide broader context, including frameworks for managing AI risks across an organization or lifecycle [Boundary source: NIST2023AIRMF; governance / risk context only; submission lock required for final NIST AI RMF DOI / PDF locator]. PULSEmech should not be flattened into that broader governance category. Its contribution is narrower and more mechanical: a software-engineering release-authority path for determining whether release permission can materialize from recorded evidence under declared policy.

Related-work role:

- `RW10_AI_SAFETY_GOVERNANCE_BOUNDARY`
- `RW11_RUNTIME_GUARDRAILS`

Boundary:

Do not write that PULSEmech is a runtime guardrail or generic AI governance framework.

### Auditability, traceability, and release-decision stability

PULSEmech’s non-normative surfaces include release-authority manifests, audit bundles, ledgers, packet validators, and regression guards. These are related to auditability and traceability because they preserve decision paths and make reconstruction possible. They are also related to regression and drift-detection practices because generated-packet regression is used to prevent silent mechanical drift in packet-builder output.

The current source set still marks this area as needing stronger sources, especially for regression testing, golden tests, snapshot testing, drift detection, and release-decision stability. The first citation-keyed related-work draft should therefore avoid overclaiming here. It can state that PULSE-REF uses normalized generated-packet regression as an internal drift guard, but a later literature pass should add stronger methodological sources before final submission.

Related-work role:

- `RW12_AUDITABILITY_AND_TRACEABILITY`
- `RW13_RELEASE_DECISION_STABILITY`

Current external-source status:

- `ACM2020ArtifactBadging` supports artifact/reproducibility terminology.
- `SLSA2026Spec` and `InTotoSpec` support provenance / traceability context, with submission-lock notes preserved.
- `RW-SRC-017` remains unresolved and must not be cited as a final source.

Boundary:

Do not present regression as release authority.

Do not present internal regression as independent external replication.

## Compact related-work section candidate

For the first submission-stage draft, the related-work section can be compressed into the following structure:

1. CI/CD and release engineering establish the software release context, but PULSEmech differs by defining declared-policy release authority rather than generic pipeline success.
2. Policy-as-code provides a comparison for machine-checkable declared policy, but PULSEmech requires policy-derived materialized gates and fail-closed enforcement before release permission materializes.
3. Supply-chain provenance, reproducible artifacts, and schema validation provide context for artifact integrity and reconstructability, but none of these surfaces alone authorize release.
4. MLOps, model documentation, and AI evaluation work provide AI-specific evidence context, but PULSEmech treats these as candidate evidence rather than release permission.
5. Runtime guardrails and AI governance are boundary contrasts: PULSEmech operates before deployment at the release boundary and should not be framed as runtime filtering or broad governance.
6. Auditability and regression remain relevant to reconstruction and drift detection, but the final paper should add stronger sources before making broad release-decision stability claims.

## Citation-keyed related-work status table

| Section | Status | Next action |
|---|---|---|
| Release engineering / CI-CD | citation-keyed draft | lock final IEEE Access DOI / publication metadata for `Shahin2017CICDReview` |
| Policy-as-code | citation-keyed draft | lock OPA docs version/date or access date |
| Assurance / provenance | citation-keyed draft | lock SLSA / in-toto versions and ACM SCORED 2022 metadata for `Okafor2022SupplyChainSoK` |
| Reproducible artifacts / schemas | citation-keyed draft | keep `RW-SRC-017` unresolved until a real regression source is selected |
| AI release readiness / evaluation | citation-keyed draft | lock final metadata for `Sculley2015MLDebt` and `Mitchell2019ModelCards` |
| Runtime guardrails / governance | citation-keyed draft | preserve IEEE S&P 2026 lock note and NIST AI RMF DOI / PDF locator lock note |
| Auditability / stability | partial citation-keyed draft | needs stronger final sources |

## Bibliography and source lock still required

Before submission-stage use:

1. Convert all provisional citation-key markers into final bibliography entries.
2. Verify author names, publication titles, venues, years, DOIs, arXiv IDs, or stable official URLs.
3. Lock source metadata for every `submission-lock-required` source.
4. Replace or remove `RW-SRC-017`.
5. Confirm reserve sources are absent unless explicitly promoted in a later source-selection update.
6. Confirm that related-work prose does not add claims beyond the artifact-to-claim and citation-bound draft boundaries.
7. Confirm that PULSEmech remains positioned as a cs.SE release-authority mechanism.
8. Confirm that all boundary notes remain visible or are reflected in final prose.

## Citation-key audit checklist

Before using this draft as a base for submission-stage related work, verify:

- `NIST2022SSDF`, `ACM2020ArtifactBadging`, and `JSONSchema2020` are the only direct replacement sources.
- `Shahin2017CICDReview`, `OPA_PolicyAsCode`, `SLSA2026Spec`, `InTotoSpec`, `Sculley2015MLDebt`, `Mitchell2019ModelCards`, `Wang2026GuardrailsSoK`, and `Okafor2022SupplyChainSoK` preserve submission-lock notes.
- `NIST2023AIRMF` remains a boundary source and preserves the NIST DOI / PDF locator lock note.
- `Wang2026GuardrailsSoK` remains a lock-note replacement source, not a boundary-only replacement source.
- `RW-SRC-017` remains unresolved and is not converted into a citation key.
- No reserve source appears in the prose without explicit promotion.
- No source is used outside its declared boundary.

## Validation checks for this document

Before merging changes to this document, run:

```bash
grep -n '^## Related Work$' docs/papers/PULSEMECH_CITATION_KEYED_RELATED_WORK_DRAFT_v0.md
grep -n '^### Release engineering and CI/CD gates$' docs/papers/PULSEMECH_CITATION_KEYED_RELATED_WORK_DRAFT_v0.md
grep -n '^### Runtime guardrails and AI governance as boundary contrast$' docs/papers/PULSEMECH_CITATION_KEYED_RELATED_WORK_DRAFT_v0.md
grep -n '^## Citation-key audit checklist$' docs/papers/PULSEMECH_CITATION_KEYED_RELATED_WORK_DRAFT_v0.md
grep -n 'Shahin2017CICDReview; submission lock required' docs/papers/PULSEMECH_CITATION_KEYED_RELATED_WORK_DRAFT_v0.md
grep -n 'NIST2022SSDF' docs/papers/PULSEMECH_CITATION_KEYED_RELATED_WORK_DRAFT_v0.md
grep -n 'ACM2020ArtifactBadging' docs/papers/PULSEMECH_CITATION_KEYED_RELATED_WORK_DRAFT_v0.md
grep -n 'JSONSchema2020' docs/papers/PULSEMECH_CITATION_KEYED_RELATED_WORK_DRAFT_v0.md
grep -n 'Wang2026GuardrailsSoK; submission lock required for final IEEE S&P 2026 proceedings metadata / DOI' docs/papers/PULSEMECH_CITATION_KEYED_RELATED_WORK_DRAFT_v0.md
grep -n 'Boundary source: NIST2023AIRMF; governance / risk context only; submission lock required for final NIST AI RMF DOI / PDF locator' docs/papers/PULSEMECH_CITATION_KEYED_RELATED_WORK_DRAFT_v0.md
grep -n 'Okafor2022SupplyChainSoK; submission lock required for final ACM SCORED 2022 proceedings metadata / DOI' docs/papers/PULSEMECH_CITATION_KEYED_RELATED_WORK_DRAFT_v0.md
grep -n 'RW-SRC-017' docs/papers/PULSEMECH_CITATION_KEYED_RELATED_WORK_DRAFT_v0.md
! grep -n 'Wang2025GuardrailsSoK' docs/papers/PULSEMECH_CITATION_KEYED_RELATED_WORK_DRAFT_v0.md
! grep -n 'Okafor2024SupplyChainSoK' docs/papers/PULSEMECH_CITATION_KEYED_RELATED_WORK_DRAFT_v0.md
```

Expected result:

- related-work section is present;
- CI/CD section is present;
- runtime guardrails / governance boundary section is present;
- citation-key audit checklist is present;
- lock-note replacements preserve their lock notes;
- direct replacement keys are present;
- corrected `Wang2026GuardrailsSoK` key is present;
- corrected `Okafor2022SupplyChainSoK` key is present;
- NIST AI RMF boundary lock note is present;
- unresolved `RW-SRC-017` remains tracked;
- old incorrect source keys are absent.

## Next paper step

After this citation-keyed related-work draft is merged, the next paper step is:

`docs(paper): add PULSEmech final source gap closure plan`

That step should address unresolved `RW-SRC-017`, remaining submission-lock-required sources, and final bibliography readiness gates before any submission-stage manuscript draft.

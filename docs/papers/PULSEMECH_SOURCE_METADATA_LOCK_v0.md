# PULSEmech Source Metadata Lock v0

Status: source metadata lock  
Paper status: pre-submission support document  
Primary category target: cs.SE  
Scope: PULSEmech / artifact-bound release authority / AI release decisions / software engineering  
Authority status: non-normative paper-support document  
Repository status: does not change PULSE release-authority semantics

## Purpose

This document records the first source metadata lock for the future PULSEmech cs.SE paper.

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

The purpose is to move selected related-work sources from source-table candidates toward citation-ready metadata.

This document does not finalize the bibliography.

This document does not create an arXiv submission package.

This document does not change PULSE release-authority semantics.

## Working rule

Do not lock a source because it sounds useful.

Lock only the source relation:

source  
→ canonical area ID  
→ citation key  
→ metadata  
→ locator  
→ role  
→ relevance  
→ boundary  
→ lock status

Workshop rule:

Nem az eredményt magyarázzuk. A viszonyt mérjük.

Source-lock rule:

Do not cite a source as decoration.

Cite the mechanism relation or boundary relation that the source supports.

## Lock boundary

This document is not a bibliography.

It is not the final related-work prose.

It does not yet decide final formatting.

It records metadata and locators that still require final submission-stage verification.

Before final submission, each source must be checked again for:

- final citation format;
- DOI or arXiv ID;
- stable official URL;
- author list;
- venue or standard body;
- year;
- source role;
- boundary wording;
- final include / reserve / exclude decision.

## Lock status vocabulary

| Lock status | Meaning |
|---|---|
| `metadata-checked` | Title, authors or responsible body, year/version, and source type have been checked. |
| `locator-checked` | A stable DOI, arXiv ID, official page, or stable URL has been checked. |
| `citation-key-assigned` | A provisional final citation key has been assigned. |
| `citation-ready-draft` | Sufficient for draft citation use, but still needs final formatting before submission. |
| `reserve` | Keep in reserve; do not use unless needed. |
| `boundary-only` | Use only for contrast / non-identity framing. |
| `needs replacement` | Placeholder or insufficient source; replace before submission-stage use. |
| `submission-lock-required` | Useful source, but final DOI/arXiv/stable URL or version lock remains required. |

## External source metadata lock table

| Source ID | Area ID | Citation key | Metadata | Locator | Source role | Include decision | Lock status | Boundary |
|---|---|---|---|---|---|---|---|---|
| `RW-SRC-001` | `RW01_RELEASE_ENGINEERING`; `RW02_CI_CD_GATES` | `Shahin2017CICDReview` | Mojtaba Shahin, Muhammad Ali Babar, Liming Zhu. “Continuous Integration, Delivery and Deployment: A Systematic Review on Approaches, Tools, Challenges and Practices.” 2017. | arXiv:1703.07019; final IEEE Access DOI still to verify before submission. | context / direct comparison | include | metadata-checked / locator-checked / citation-key-assigned / submission-lock-required | CI/CD context only; not declared-policy release authority. |
| `RW-SRC-003` | `RW03_POLICY_AS_CODE` | `OPA_PolicyAsCode` | Open Policy Agent documentation. Official OPA docs describe OPA as an open-source, general-purpose policy engine with declarative policy language and CI/CD use cases. | Official OPA docs URL; version/date to lock before submission. | direct comparison / terminology support | include | metadata-checked / locator-checked / citation-key-assigned / submission-lock-required | Policy decision support; policy text alone does not authorize release. |
| `RW-SRC-004` | `RW04_SOFTWARE_ASSURANCE`; `RW05_SUPPLY_CHAIN_PROVENANCE` | `NIST2022SSDF` | Murugiah Souppaya, Karen Scarfone, Donna Dodson. “Secure Software Development Framework (SSDF) Version 1.1: Recommendations for Mitigating the Risk of Software Vulnerabilities.” NIST SP 800-218. February 2022. | DOI: `10.6028/NIST.SP.800-218`; official NIST CSRC page. | standard / specification / context | include | metadata-checked / locator-checked / citation-key-assigned / citation-ready-draft | Secure development context; not a complete PULSEmech assurance case. |
| `RW-SRC-005` | `RW05_SUPPLY_CHAIN_PROVENANCE` | `SLSA2026Spec` | Supply-chain Levels for Software Artifacts (SLSA) specification v1.2. Official specification. | Official SLSA v1.2 specification URL. | standard / specification / methodological support | include | metadata-checked / locator-checked / citation-key-assigned / submission-lock-required | Provenance supports reconstruction / trust; it does not authorize release by itself. |
| `RW-SRC-007` | `RW05_SUPPLY_CHAIN_PROVENANCE`; `RW06_REPRODUCIBLE_ARTIFACTS`; `RW12_AUDITABILITY_AND_TRACEABILITY` | `InTotoSpec` | in-toto official project / documentation. Supply-chain metadata and transparency mechanism. | Official in-toto URL; exact spec/version to lock before submission. | standard / specification / direct comparison | include | metadata-checked / locator-checked / citation-key-assigned / submission-lock-required | Supply-chain metadata supports traceability; it is not release authority. |
| `RW-SRC-009` | `RW06_REPRODUCIBLE_ARTIFACTS`; `RW12_AUDITABILITY_AND_TRACEABILITY` | `ACM2020ArtifactBadging` | ACM Artifact Review and Badging Version 1.1. August 24, 2020. Defines artifact review terminology including repeatability, reproducibility, and replicability. | Official ACM artifact review and badging policy page. | methodological support / terminology support | include | metadata-checked / locator-checked / citation-key-assigned / citation-ready-draft | Artifact review terminology only; does not prove external replication of PULSE-REF. |
| `RW-SRC-010` | `RW07_FORMAL_OR_TYPED_RELEASE_CONTRACTS` | `JSONSchema2020` | “JSON Schema: A Media Type for Describing JSON Documents.” Draft 2020-12. Official JSON Schema specification. | Official JSON Schema Draft 2020-12 specification URL. | standard / specification / terminology support | include | metadata-checked / locator-checked / citation-key-assigned / citation-ready-draft | Schema validity supports artifact shape; it is not release permission. |
| `RW-SRC-012` | `RW08_MLOPS_RELEASE_READINESS` | `Sculley2015MLDebt` | D. Sculley, Gary Holt, Daniel Golovin, Eugene Davydov, Todd Phillips, Dietmar Ebner, Vinay Chaudhary, Michael Young, Jean-François Crespo, Dan Dennison. “Hidden Technical Debt in Machine Learning Systems.” Advances in Neural Information Processing Systems 28, 2015. | NeurIPS proceedings page; DOI if any to verify before submission. | context / boundary contrast | include | metadata-checked / locator-checked / citation-key-assigned / submission-lock-required | AI systems engineering context only; not a PULSEmech identity source. |
| `RW-SRC-014` | `RW09_AI_EVALUATION_INFRASTRUCTURE` | `Mitchell2019ModelCards` | Margaret Mitchell, Simone Wu, Andrew Zaldivar, Parker Barnes, Lucy Vasserman, Ben Hutchinson, Elena Spitzer, Inioluwa Deborah Raji, Timnit Gebru. “Model Cards for Model Reporting.” 2018 arXiv preprint / 2019 ACM FAccT publication. | arXiv:1810.03993; ACM DOI / proceedings locator to verify before submission. | context / boundary contrast | include | metadata-checked / locator-checked / citation-key-assigned / submission-lock-required | Model cards are evidence/reporting surfaces, not release permission. |
| `RW-SRC-015` | `RW10_AI_SAFETY_GOVERNANCE_BOUNDARY` | `NIST2023AIRMF` | NIST Artificial Intelligence Risk Management Framework (AI RMF 1.0). Official NIST AI RMF resource. | Official NIST AI RMF page; DOI / PDF locator to verify before submission. | boundary contrast / context | boundary-only | metadata-checked / locator-checked / citation-key-assigned / submission-lock-required | Governance/risk context only; do not frame PULSEmech as generic AI governance. |
| `RW-SRC-016` | `RW11_RUNTIME_GUARDRAILS` | `Wang2025GuardrailsSoK` | Xunguang Wang, Zhenlan Ji, Wenxuan Wang, Zongjie Li, Daoyuan Wu, Shuai Wang. “SoK: Evaluating Jailbreak Guardrails for Large Language Models.” 2025. | arXiv:2506.10597. | boundary contrast | include | metadata-checked / locator-checked / citation-key-assigned / citation-ready-draft | Runtime guardrails differ from pre-release authority. |
| `RW-SRC-019` | `RW05_SUPPLY_CHAIN_PROVENANCE` | `Okafor2024SupplyChainSoK` | Chinenye Okafor, Taylor R. Schorlemmer, Santiago Torres-Arias, James C. Davis. “SoK: Analysis of Software Supply Chain Security by Establishing Secure Design Properties.” 2024. | arXiv:2406.10109. | context / methodological support | include | metadata-checked / locator-checked / citation-key-assigned / citation-ready-draft | Supply-chain security context; not PULSEmech mechanism. |

## Reserve source metadata lock table

| Source ID | Area ID | Citation key | Metadata status | Locator status | Reason held in reserve | Lock status |
|---|---|---|---|---|---|---|
| `RW-SRC-002` | `RW01_RELEASE_ENGINEERING`; `RW02_CI_CD_GATES` | `Shahin2018ArchitectingCD` | metadata available from arXiv result | arXiv:1808.08796 | May overlap with `RW-SRC-001`. | reserve |
| `RW-SRC-006` | `RW05_SUPPLY_CHAIN_PROVENANCE` | `TamannaSLSADeploymentChallenges` | needs final metadata verification | needs locator verification | Useful for SLSA adoption friction if needed. | reserve |
| `RW-SRC-008` | `RW05_SUPPLY_CHAIN_PROVENANCE`; `RW12_AUDITABILITY_AND_TRACEABILITY` | `TUFSpec` | official project metadata available | official TUF URL locator checked; exact spec/version to verify | Useful for update-system security if supply-chain section expands. | reserve |
| `RW-SRC-011` | `RW07_FORMAL_OR_TYPED_RELEASE_CONTRACTS` | `Attouche2023JSONSchema` | metadata available from arXiv result | arXiv:2307.10034 | Useful only if schema-validation discussion deepens. | reserve |
| `RW-SRC-013` | `RW08_MLOPS_RELEASE_READINESS` | `GoogleMLOpsCD` | needs final documentation version lock | needs stable URL/version verification | Useful if MLOps contrast needs more detail. | reserve |
| `RW-SRC-018` | `RW05_SUPPLY_CHAIN_PROVENANCE`; `RW13_RELEASE_DECISION_STABILITY` | `KaluSigningUsability` | needs final metadata verification | needs locator verification | Useful if signing / verification workflow friction becomes relevant. | reserve |
| `RW-SRC-020` | `RW04_SOFTWARE_ASSURANCE`; `RW10_AI_SAFETY_GOVERNANCE_BOUNDARY` | `Barrett2022HighConsequenceAIRisk` | metadata available from arXiv result | arXiv:2206.08966 | Useful only for careful AI risk / governance boundary. | reserve |

## Placeholder resolution

The earlier placeholder source:

`RW-SRC-017`

remains unresolved.

Current status:

- do not cite as final source;
- keep as `needs replacement`;
- use only as a gap marker for regression / snapshot / golden testing literature;
- remove if no strong source is selected before submission-stage related work.

Possible replacement direction:

- regression testing survey;
- snapshot / golden testing methodology;
- artifact drift or CI regression guard source;
- characterization / golden-master testing source, if technically acceptable.

## Source key map

| Source ID | Citation key | Draft use |
|---|---|---|
| `RW-SRC-001` | `Shahin2017CICDReview` | CI/CD release engineering context |
| `RW-SRC-003` | `OPA_PolicyAsCode` | policy-as-code comparison |
| `RW-SRC-004` | `NIST2022SSDF` | secure software development / assurance context |
| `RW-SRC-005` | `SLSA2026Spec` | supply-chain provenance context |
| `RW-SRC-007` | `InTotoSpec` | supply-chain metadata / traceability comparison |
| `RW-SRC-009` | `ACM2020ArtifactBadging` | reproducible artifacts terminology |
| `RW-SRC-010` | `JSONSchema2020` | schema / typed artifact context |
| `RW-SRC-012` | `Sculley2015MLDebt` | AI systems engineering context |
| `RW-SRC-014` | `Mitchell2019ModelCards` | model documentation / evaluation artifact boundary |
| `RW-SRC-015` | `NIST2023AIRMF` | AI governance boundary context |
| `RW-SRC-016` | `Wang2025GuardrailsSoK` | runtime guardrail boundary contrast |
| `RW-SRC-019` | `Okafor2024SupplyChainSoK` | software supply-chain security context |

## Metadata lock findings

### Ready for draft citation

The following sources are ready for draft citation, subject to final formatting:

- `RW-SRC-004`
- `RW-SRC-009`
- `RW-SRC-010`
- `RW-SRC-016`
- `RW-SRC-019`

### Ready for draft citation but needs final DOI / venue lock

The following sources are usable but should have DOI / final venue metadata checked before submission:

- `RW-SRC-001`
- `RW-SRC-012`
- `RW-SRC-014`

### Official documentation sources needing version/date lock

The following official documentation sources are usable but need final version/date lock:

- `RW-SRC-003`
- `RW-SRC-005`
- `RW-SRC-007`
- `RW-SRC-015`

### Boundary-only

The following source should be used only for boundary contrast:

- `RW-SRC-015`

### Needs replacement

The following placeholder must be replaced or removed before submission-stage related work:

- `RW-SRC-017`

## Manuscript update guidance

When updating related-work prose:

1. replace `RW-SRC-*` markers with citation keys only after source metadata is checked;
2. keep source IDs in comments or planning docs until final bibliography is generated;
3. preserve source boundaries;
4. do not use reserve sources unless needed;
5. remove placeholder sources from final prose;
6. do not let official documentation sources become broad claims beyond their technical scope;
7. do not use governance sources as PULSEmech identity sources.

## Final source metadata tasks before submission

Before submission-stage manuscript:

- verify final IEEE Access DOI or final publication data for `RW-SRC-001`;
- verify final OPA documentation version/date or access date for `RW-SRC-003`;
- verify current SLSA version/date and whether v1.2 remains the intended cited version for `RW-SRC-005`;
- verify exact in-toto specification / documentation version for `RW-SRC-007`;
- verify final DOI / ACM proceedings metadata for `RW-SRC-014`;
- verify NIST AI RMF DOI/PDF locator for `RW-SRC-015`;
- replace or remove `RW-SRC-017`;
- decide whether any reserve sources enter the final paper;
- create final BibTeX / bibliography entries.

## Validation checks for this document

Before merging changes to this document, run:

```bash
grep -n '^## External source metadata lock table$' docs/papers/PULSEMECH_SOURCE_METADATA_LOCK_v0.md
grep -n '^## Reserve source metadata lock table$' docs/papers/PULSEMECH_SOURCE_METADATA_LOCK_v0.md
grep -n '^## Placeholder resolution$' docs/papers/PULSEMECH_SOURCE_METADATA_LOCK_v0.md
grep -n '^## Source key map$' docs/papers/PULSEMECH_SOURCE_METADATA_LOCK_v0.md
grep -n '^## Metadata lock findings$' docs/papers/PULSEMECH_SOURCE_METADATA_LOCK_v0.md
grep -n 'RW-SRC-017' docs/papers/PULSEMECH_SOURCE_METADATA_LOCK_v0.md
grep -n 'arXiv:1703.07019' docs/papers/PULSEMECH_SOURCE_METADATA_LOCK_v0.md
grep -n '10.6028/NIST.SP.800-218' docs/papers/PULSEMECH_SOURCE_METADATA_LOCK_v0.md
grep -n 'arXiv:2506.10597' docs/papers/PULSEMECH_SOURCE_METADATA_LOCK_v0.md
grep -n 'arXiv:2406.10109' docs/papers/PULSEMECH_SOURCE_METADATA_LOCK_v0.md
```

Expected result:

- external source metadata lock table is present;
- reserve source metadata lock table is present;
- placeholder resolution is present;
- source key map is present;
- metadata lock findings are present;
- unresolved placeholder source `RW-SRC-017` is tracked;
- key arXiv / DOI locators are present.

## Next paper step

After this source metadata lock is merged, the next paper step is:

`docs(paper): add PULSEmech citation key replacement pass v0`

That step should replace `RW-SRC-*` markers in the related-work prose with provisional citation keys while preserving the source table and source metadata lock as trace surfaces.

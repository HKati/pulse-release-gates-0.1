# PULSEmech Final Source Gap Closure Plan v0

Status: final source gap closure plan  
Paper status: pre-submission support document  
Primary category target: cs.SE  
Scope: PULSEmech / artifact-bound release authority / AI release decisions / software engineering  
Authority status: non-normative paper-support document  
Repository status: does not change PULSE release-authority semantics

## Purpose

This document defines the final source-gap closure plan for the future PULSEmech cs.SE paper.

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
- `docs/papers/PULSEMECH_CITATION_KEYED_RELATED_WORK_DRAFT_v0.md`

The purpose is to identify and close the remaining source and artifact locator gaps before any submission-stage manuscript draft is prepared.

This document does not finalize the bibliography.

This document does not add new paper claims.

This document does not create an arXiv submission package.

This document does not change PULSE release-authority semantics.

## Working rule

Do not carry unresolved source gaps into submission-stage prose.

A source gap is not a risk to tolerate.

A source gap is a closure gate.

Workshop rule:

Nem az eredményt magyarázzuk. A viszonyt mérjük.

Source-gap rule:

Do not explain around an incomplete source.

Close it, replace it, reserve it, or remove the prose that depends on it.

## Source-gap boundary

This plan is not a source-selection result.

It does not choose replacement sources.

It defines what must be closed before the paper can move toward submission-stage manuscript form.

A later closure pass must either:

- close each source gap with verified metadata;
- keep the source as `submission-lock-required` with explicit lock note;
- keep the source in reserve with explicit non-use status;
- replace an unresolved placeholder with a real source;
- remove prose that depends on an unresolved source.

## Closure status vocabulary

| Status | Meaning |
|---|---|
| `closed-for-draft` | Suitable for draft use with current metadata and boundary notes. |
| `submission-lock-required` | Useful for draft scaffolding but final DOI / venue / version / locator remains required before submission-stage use. |
| `closure-required` | Must be resolved before citation-keyed prose can move toward submission-stage form. |
| `replace-or-remove` | Placeholder or insufficient source; replace with a real source or remove dependent prose. |
| `reserve-held` | Source remains unavailable unless explicitly promoted in a later source-selection update. |
| `artifact-lock-required` | Repository artifact anchor needs commit / release / DOI / stable locator decision before submission-stage use. |
| `closed-by-removal` | Source or claim was removed from the draft instead of cited. |
| `external-dependency` | Cannot be fully closed internally yet because it depends on external publication metadata not available at the time of this plan. |

## Remaining source-gap table

| Gap ID | Source / artifact | Current state | Required closure action | Allowed before closure | Closure status |
|---|---|---|---|---|---|
| `G01_RW_SRC_017` | `RW-SRC-017` regression / snapshot / golden testing placeholder | unresolved placeholder | Replace with a real source or remove external regression-literature claim. | May appear only as `[Source needed: RW13_RELEASE_DECISION_STABILITY / regression testing]` in planning docs. | replace-or-remove |
| `G02_RW_SRC_001` | `RW-SRC-001` / `Shahin2017CICDReview` | arXiv metadata present; final IEEE Access DOI / publication metadata still to verify | Verify final publication metadata and DOI, or keep submission-lock note. | Draft citation with lock note only. | submission-lock-required |
| `G03_RW_SRC_003` | `RW-SRC-003` / `OPA_PolicyAsCode` | official documentation source; version/date not locked | Lock official documentation version/date or access date. | Draft citation with lock note only. | submission-lock-required |
| `G04_RW_SRC_005` | `RW-SRC-005` / `SLSA2026Spec` | official spec source; version/date must be locked | Confirm cited SLSA version and access date before final bibliography. | Draft citation with lock note only. | submission-lock-required |
| `G05_RW_SRC_007` | `RW-SRC-007` / `InTotoSpec` | official project/docs source; exact spec/documentation version not locked | Lock exact specification or documentation version. | Draft citation with lock note only. | submission-lock-required |
| `G06_RW_SRC_012` | `RW-SRC-012` / `Sculley2015MLDebt` | NeurIPS metadata known; DOI if any still to verify | Verify final venue metadata and DOI availability. | Draft citation with lock note only. | submission-lock-required |
| `G07_RW_SRC_014` | `RW-SRC-014` / `Mitchell2019ModelCards` | arXiv / FAccT metadata known; final ACM DOI / proceedings locator still to verify | Verify final ACM citation metadata and DOI / proceedings locator. | Draft citation with lock note only. | submission-lock-required |
| `G08_RW_SRC_015` | `RW-SRC-015` / `NIST2023AIRMF` | boundary-only and submission-lock-required | Verify final NIST AI RMF DOI / PDF locator; preserve boundary-only role. | Boundary citation with lock note only. | submission-lock-required |
| `G09_RW_SRC_016` | `RW-SRC-016` / `Wang2026GuardrailsSoK` | accepted venue boundary recorded; final IEEE S&P 2026 proceedings metadata still pending | Verify final IEEE S&P 2026 proceedings metadata / DOI when available. | Draft citation with lock note only. | external-dependency |
| `G10_RW_SRC_019` | `RW-SRC-019` / `Okafor2022SupplyChainSoK` | ACM SCORED 2022 boundary recorded; final ACM proceedings metadata / DOI still to verify | Verify final ACM SCORED 2022 proceedings metadata / DOI. | Draft citation with lock note only. | submission-lock-required |
| `G11_RESERVE_SOURCES` | Reserve source set | reserve-held | Do not use unless explicitly promoted in a later source-selection update. | Not allowed in prose, citation-keyed prose, BibTeX, final bibliography, or submission-stage manuscript. | reserve-held |
| `G12_REPO_ARTIFACT_LOCATORS` | Repository artifact anchors | artifact paths known; final locator strategy not selected | Decide commit / release / DOI / stable GitHub locator strategy before submission. | Draft artifact-anchor notes only. | artifact-lock-required |
| `G13_EXTERNAL_RELATED_WORK_BIBTEX` | External bibliography entries | citation keys exist; final BibTeX not generated | Generate final BibTeX only after metadata lock closure. | Planning keys only. | closure-required |
| `G14_SUBMISSION_DISCLOSURE` | AI-assisted drafting disclosure | placeholder exists | Verify final disclosure wording against submission standards. | Draft disclosure only. | closure-required |
| `G15_SUBMISSION_STAGE_SOURCE_CLEANUP` | Related-work prose and citation markers | citation-keyed draft exists; final submission cleanup not done | Remove source-planning notes, convert or remove lock notes, and preserve only final citations / approved footnotes. | Planning draft only. | closure-required |

## Closure order

Close source gaps in this order:

1. Resolve or remove `RW-SRC-017`.
2. Verify final metadata for sources already used in citation-keyed related-work prose.
3. Confirm all `submission-lock-required` sources preserve visible lock notes until closed.
4. Confirm all reserve sources remain unused unless explicitly promoted.
5. Decide repository artifact locator strategy.
6. Prepare final bibliography / BibTeX draft.
7. Prepare submission-stage manuscript draft only after all internal closure gates are closed.

## RW-SRC-017 closure plan

`RW-SRC-017` is the only known unresolved placeholder in the related-work source layer.

It must not become a final citation.

Allowed closure paths:

### Option A — Replace with a real source

Find and verify a strong source for one of:

- regression testing methodology;
- snapshot testing;
- golden file / golden master testing;
- characterization testing;
- drift detection in software artifacts;
- CI regression guards.

The replacement source must receive:

- source ID;
- canonical area ID;
- citation key;
- source quality tier;
- source role;
- relevance note;
- boundary note;
- include decision;
- metadata lock status.

### Option B — Remove external regression-literature claim

If no sufficiently strong source is selected, remove any prose that suggests external regression-literature support.

Keep only internal PULSE artifact methodology:

- generated-packet regression exists as repository test;
- normalized golden summary guards packet-builder drift;
- this is an internal mechanism claim supported by repository artifacts, not an external literature claim.

### Option C — Keep as planning gap only

Keep `RW-SRC-017` only in planning documents and never in manuscript prose.

This is acceptable only if final manuscript prose does not require an external regression-testing citation.

## Submission-lock-required source handling

Sources marked `submission-lock-required` may appear in draft planning only if the lock note remains visible.

They must not be converted into final bibliography entries until the required lock is complete.

Required lock notes:

| Source ID | Citation key | Required visible note before final lock |
|---|---|---|
| `RW-SRC-001` | `Shahin2017CICDReview` | final IEEE Access DOI / publication metadata still to verify |
| `RW-SRC-003` | `OPA_PolicyAsCode` | official documentation version/date or access date still to lock |
| `RW-SRC-005` | `SLSA2026Spec` | SLSA v1.2 version/date still to lock |
| `RW-SRC-007` | `InTotoSpec` | exact specification / documentation version still to lock |
| `RW-SRC-012` | `Sculley2015MLDebt` | final DOI / proceedings metadata still to verify |
| `RW-SRC-014` | `Mitchell2019ModelCards` | final ACM DOI / proceedings metadata still to verify |
| `RW-SRC-015` | `NIST2023AIRMF` | final NIST AI RMF DOI / PDF locator still to verify |
| `RW-SRC-016` | `Wang2026GuardrailsSoK` | final IEEE S&P 2026 proceedings metadata / DOI still to verify |
| `RW-SRC-019` | `Okafor2022SupplyChainSoK` | final ACM SCORED 2022 proceedings metadata / DOI still to verify |

## Reserve source closure gate

Reserve sources must remain unused unless explicitly promoted.

Promotion requires a later source-selection update that records:

- source ID;
- promotion reason;
- manuscript section;
- source role;
- boundary note;
- updated include decision;
- citation metadata / locator lock status.

Until promotion is recorded, reserve sources must not enter:

- related-work prose;
- citation-keyed prose;
- final bibliography;
- BibTeX draft;
- submission-stage manuscript.

## Repository artifact locator closure

Repository artifact anchors support PULSEmech implementation claims and must be closed separately from external literature.

Before submission-stage use, decide whether repository artifacts are cited through:

- GitHub commit URLs;
- release tag URLs;
- Zenodo DOI;
- appendix / artifact package;
- combination of GitHub and DOI.

Generated run artifact paths must remain clearly marked as generated, not static checked-in files.

Examples that require generated-run wording:

- `PULSE_safe_pack_v0/artifacts/status.json`
- `PULSE_safe_pack_v0/artifacts/release_authority_audit_bundle/`
- generated packet artifact path: `gates/materialized_gate_sets.json` inside generated packet

## Source-gap closure checklist

Before moving to a submission-stage manuscript draft:

- `RW-SRC-017` is replaced, removed, or kept only as non-manuscript planning gap.
- No unresolved placeholder appears in manuscript prose.
- All `submission-lock-required` sources preserve lock notes or are fully locked.
- No reserve source appears without explicit promotion.
- `RW-SRC-015` remains boundary-only unless the source metadata lock is updated.
- `RW-SRC-016` remains a lock-note replacement and not boundary-only replacement.
- `RW-SRC-019` preserves ACM SCORED 2022 boundary.
- All generated-run artifact paths are described as generated.
- Repository artifact locator strategy is selected.
- Final bibliography / BibTeX is generated only after metadata lock closure.
- AI-assisted drafting disclosure wording is verified before submission-stage manuscript.
- Related-work prose is compact and does not pull PULSEmech into generic governance, runtime guardrail, or generic MLOps identity.

## Closure output requirements

A later closure-result document must record:

| Field | Required |
|---|---:|
| Gap ID | yes |
| Source / artifact | yes |
| Closure action | yes |
| Metadata / locator result | yes |
| Updated citation key | if applicable |
| Updated include decision | yes |
| Boundary note | yes |
| Manuscript impact | yes |
| Final closure status | yes |

## Validation checks for this document

Before merging changes to this document, run:

```bash
grep -n '^## Remaining source-gap table$' docs/papers/PULSEMECH_FINAL_SOURCE_GAP_CLOSURE_PLAN_v0.md
grep -n '^## RW-SRC-017 closure plan$' docs/papers/PULSEMECH_FINAL_SOURCE_GAP_CLOSURE_PLAN_v0.md
grep -n '^## Submission-lock-required source handling$' docs/papers/PULSEMECH_FINAL_SOURCE_GAP_CLOSURE_PLAN_v0.md
grep -n '^## Reserve source closure gate$' docs/papers/PULSEMECH_FINAL_SOURCE_GAP_CLOSURE_PLAN_v0.md
grep -n '^## Repository artifact locator closure$' docs/papers/PULSEMECH_FINAL_SOURCE_GAP_CLOSURE_PLAN_v0.md
grep -n '^## Source-gap closure checklist$' docs/papers/PULSEMECH_FINAL_SOURCE_GAP_CLOSURE_PLAN_v0.md
grep -n 'RW-SRC-017' docs/papers/PULSEMECH_FINAL_SOURCE_GAP_CLOSURE_PLAN_v0.md
grep -n 'submission-lock-required' docs/papers/PULSEMECH_FINAL_SOURCE_GAP_CLOSURE_PLAN_v0.md
grep -n 'explicitly promoted' docs/papers/PULSEMECH_FINAL_SOURCE_GAP_CLOSURE_PLAN_v0.md
grep -n 'PULSE_safe_pack_v0/artifacts/status.json' docs/papers/PULSEMECH_FINAL_SOURCE_GAP_CLOSURE_PLAN_v0.md
grep -n 'PULSE_safe_pack_v0/artifacts/release_authority_audit_bundle/' docs/papers/PULSEMECH_FINAL_SOURCE_GAP_CLOSURE_PLAN_v0.md
```

Expected result:

- remaining source-gap table is present;
- `RW-SRC-017` closure plan is present;
- submission-lock-required handling is present;
- reserve source closure gate is present;
- repository artifact locator closure is present;
- source-gap closure checklist is present;
- unresolved placeholder source is tracked;
- submission-lock-required source handling remains visible;
- reserve sources require explicit promotion;
- generated-run artifact paths remain marked.

## Next paper step

After this final source gap closure plan is merged, the next paper step is:

`docs(paper): close PULSEmech regression source gap v0`

That step should resolve `RW-SRC-017` by either selecting a real regression / snapshot / golden testing source or removing external regression-literature dependency from the manuscript path.

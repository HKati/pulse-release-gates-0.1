# PULSEmech QRH003 — Knowledge Continuity Pilot v0

**Status:** DESIGN ONLY · no QRH003 proof run, CI run, independent handoff, repository-code change or release authorization is claimed by this plan. **Authority effect:** `none` for the continuity overlay.

**Detailed plans (Hungarian):** [technical](PULSEMECH_QRH003_KNOWLEDGE_CONTINUITY_TECHNICAL_PLAN_v0.md) · [experimental](PULSEMECH_QRH003_KNOWLEDGE_CONTINUITY_EXPERIMENT_PLAN_v0.md) · [implementation](PULSEMECH_QRH003_KNOWLEDGE_CONTINUITY_IMPLEMENTATION_PLAN_v0.md).

## 1. Fixed subject and one falsifiable pilot claim

The only scientific unit in scope is `qrh003_zeta`, tied to `openai/math` commit `adc7f1241b42e322a6451854ab7e4b4c146bf78a`, the September 30, 2026 quasi-Riemann-hypothesis manuscript's Theorem 1.1 (PDF page 4), the `QuasiRiemannHypothesis` comparator challenge/configuration, and `OAI.riemannZeta_ne_zero_of_seven_eighths_lt_re` in `lean/OAI/NumberTheory/DirichletL/Nonvanishing.lean`.

**PILOT-K1:** Given the preserved historical QRH003 evidence and a separately identified, minimal continuity overlay, a new executor, without the preparer's oral help, can determine (a) the exact subject and its interpretation, (b) the original decision's inputs and conditions, (c) what decision replay can reproduce, (d) what remains unverified, and (e) a concrete next research question. The overlay must preserve rather than silently promote missing evidence. A second, separately authorized execution is required before independent replay can be claimed.

The selected formal declaration does not contain a separate `s ≠ 1` hypothesis. The pinned Mathlib's totalized `riemannZeta` has a convention-defined nonzero value at the classical pole. The handoff must preserve the distinction between the formal total function at `s=1` and the meromorphic classical interpretation away from the pole; mathematical equivalence requires separate domain review.

**Out of scope:** proof of the Riemann hypothesis or QRH; full closure of all four Math 003 claims/five theorem exports; new native Lean/Comparator/kernel validation; independent mathematics review; community acceptance; control over OpenAI publication; and claims about the social distribution of scientific knowledge.

## 2. Existing evidence: do not rebuild it or overclaim

| Existing element | Recorded status | Boundary |
| --- | --- | --- |
| Earlier Math 003 source audit, dated 2026-10-07 | Two manuscript bytes identified; four claim classes and five formal exports mapped; static import/dependency mapping and patch plan | Source and static structure do not establish executed kernel proof. |
| Repository study `studies/openai_math_003_qrh_v0/` | Current implementation `v0.1.3`; source-bound launcher, admission, strict offline decision, replay and observer | 220 local regression results were recorded on its reviewed revision; this plan did not rerun them. The general root CI does not automatically run the isolated QRH suite. |
| Historical `qrh003-pilot-002-20261007` | `BLOCK`; recorded replay `MATCH` using its original v0.1 verifier snapshot | `MATCH` reproduces the policy decision, not mathematical proof; old verifier/anchor may not be silently replaced with v0.1.3. |
| Historical complete archive | `PULSEMECH_QRH003_IMPLEMENTATION_v0_1_1.zip`, 23,453,781 bytes; SHA-256 `ce5737b01ae3b400bac96c092afb982a0af74a812692714e4c7cd094b61afbdc` | Preserved bytes have owner-controlled custody. A public hash or source-only checkout is not a public byte-preservation claim. |
| Native formal-proof capture | `NOT_IMPLEMENTED` | No native proof run or production QRH certificate is established. |
| Semantic/domain reviewer intake | Not independently verified | No equivalence or scientific-acceptance claim follows from formal syntax, local fixtures, or replay. |

The study pins its original PULSE primitives to `288bb9a45764d2a30f72fdf4c417e9dd5b3087c5`; changing the current repository `main` must not silently change the historical verifier identity. The earlier audit design is available as a separately retained, non-normative `PULSEMECH_OPENAI_MATH_003_AUDIT_TERV_v0.docx` (2026-10-07, 28 pages; 82,686 bytes; SHA-256 `2cb23a9901cf4d50c2ba3b871bedc5ac2de1546bfeecf46f741014ea65a60e8e`). It is not a mandatory M1 input absent a documented byte-access route.

## 3. Required evidence path and knowledge boundaries

```
identified manuscript/PDF and passage
  -> claim-card (semantic scope and exclusion set)
  -> pinned challenge, configuration, implementation theorem, definitions
  -> source/dependency/patch and executed-toolchain identities
  -> actual run evidence and exact evaluated artifacts [currently incomplete]
  -> externally declared acceptance policy and required-gate set
  -> scoped historical BLOCK decision and decision-only replay MATCH
  -> preserved archive and explicit unresolved questions
  -> independent machine replay + separate blinded human handoff [NOT_RUN]
```

Keep four claim layers distinct: (1) byte/content identity, (2) formal declaration and kernel check, (3) semantic mapping to the natural-language statement, and (4) scientific importance/acceptance. Neither a successful local test nor repeated decision bytes promotes any higher layer automatically.

The **canonical planned M1 output paths**, relative to a new disposable non-repository work directory, are exactly `M1/INPUTS_LOCK.json`, `M1/CLAIM_CARD_QRH003_ZETA.json`, `M1/EVIDENCE_RELATIONS.json`, `M1/OPEN_QUESTIONS.json` and `M1/M1_AUDIT_TRAIL.md`. These names are normative across the three plans; earlier short names such as `claim_card_v0` or `knowledge_relation_inventory_v0` are **not** alternative filenames. Later distinct artifacts are `M2/TRANSITION_ASSESSMENT.json`, `M3/PRESERVATION_INVENTORY.json`, `M3/CONTINUITY_STATUS.json`, `M6/HANDOFF_PROTOCOL.md` and `M6/HANDOFF_RECEIPT.json`. All are **planned**, not existing QRH003 artifacts. They must not replace or modify the historical archive or its signed contents.

## 4. Transition Meter: observed vs reconstructed vs unresolved

The [Transition Meter](../PULSEMECH_TRANSITION_METER.md) is a diagnostic observer, not an independent mathematical judge or authorization grant. Represent each required link with stable endpoint IDs, relation type, ordered event and observation references where relevant, exact evidence byte references and verifier. Store **two independent classifications**: `relation_status` is exactly one of `observed_and_bound`, `reconstructable`, `hypothesized`, `missing`, `conflicting`; `expert_review_status` is exactly one of `not_required`, `required_pending`, `verified`, `rejected`. The human-facing `requires_expert_review` flag is true whenever review is still required (`required_pending`); it is not an alternative value of `relation_status`. Thus an edge can be both `conflicting` and require expert review. Keep the six canonical Transition Meter `status_axes` separately; no aggregate confidence score or silent status promotion.

Carry forward the existing observation, binding, consistency, reproduction, causal and authority status axes. For the selected QRH audit, explicitly evaluate relation-change observation, path verification, endpoint binding, time order, alternative-path closure, reconstruction reproducibility, causal sufficiency and causal necessity, each under its own evidence rule. An identical replay supports decision reconstruction only; it does not establish exclusive causation, proof validity or human understanding.

The continuity overlay uses seven *handoff readiness* conditions, not new production gate IDs:

| ID | Required condition | On absence |
| --- | --- | --- |
| H01 | One pinned subject and actual mandatory byte inventory with SHA-256 | `HANDOFF_NOT_READY: SOURCE_IDENTITY` |
| H02 | Exact theorem and explicit pole/Mathlib/semantic scope limitations | `HANDOFF_NOT_READY: SEMANTIC_SCOPE` |
| H03 | Each required E1–E7 relation bound to evidence or an explicit missing/conflict record | `HANDOFF_NOT_READY: EDGE_COVERAGE` |
| H04 | Run, trust domain, verifier, policy and gate-set identities retained | `HANDOFF_NOT_READY: EXECUTION_BINDING` |
| H05 | `BLOCK`, `MATCH` and unexecuted mathematical proof kept distinct | `HANDOFF_NOT_READY: DECISION_OVERCLAIM` |
| H06 | Mandatory archive bytes retrievable under documented access constraints | `HANDOFF_NOT_READY: PRESERVATION` |
| H07 | A different executor supplies a source-backed receipt answering five questions and identifying the next problem | `HUMAN_HANDOFF_NOT_VERIFIED` |

H07 remains unverified until the actual handoff occurs. H01–H06 must also be evaluated from real archived bytes; planning text is not a PASS receipt.

## 5. Experimental design and controls

The pilot compares three arms under identical subject, preserved-history inputs, access rights and independently defined questions: **B0** pinned upstream sources/documentation only; **B1** B0 plus the existing QRH003 audit/evidence and replay instructions; **T** B1 plus the proposed continuity overlay. Improvement over B1 — not just over B0 — determines whether this is nonredundant work. An outcome of **no measurable added value** is valid.

Twenty predeclared case families `K01–K20` cover the positive preserved packet, claim/file links, wrong commit or theorem receipts, changed manuscript/formal claim/definition/dependency, missing native proof record, foreign-run or trust-domain evidence, missing decision bytes, replay-to-proof promotion, missing expert review, loss of the `s=1` interpretation, partial-to-full-scope inflation, poisoned Python cache/launcher, hash without archived bytes, lost open question, unjustified causal exclusivity, and a blinded successor handoff. **All new K01–K20 cases remain `NOT_RUN`** in this design; the existing `BLOCK`/`MATCH` history is a separate recorded result.

Use four trial statuses: `PASS` (specified boundary behavior observed), `FAIL` (verified violation), `INCONCLUSIVE` (unresolved evidence), `NOT_RUN` (never attempted). A correctly rejected negative fixture can be a PASS test, without making the rejected scientific assertion true. Preserve case-specific input digests, method, expected result, observed outcome and reason code.

**Machine replay:** use the original historical verifier snapshot, anchor, signed bundle, decision and pinned runtime; record exact byte outputs and process identity. **Human continuity:** a different executor, without oral help, identifies the claim, decision conditions, reproducible operation, open verification gaps and a next research question with exact source refs. A second person's work is not assumed merely because the packet is readable.

## 6. Preservation and access

Preserve the actual source/PDF/TeX/Lean bytes, lock and patch inputs, effective sources where available, provenance, manifest/digests, original verifier and dependency wheels, archive, decision, replay record, transition report and reviewer receipts *when they exist*. Record repository/commit/path plus byte size and SHA-256 for every required artifact. Toolchain version strings are not executable-image digests.

Keep at least two independently retrievable copies of the necessary **authorized** bytes, with explicit owner, access procedure, license review, retention policy and periodic read/check record. Do not confuse a DOI, Git URL or a SHA-256 line with guaranteed durable custody. Never embed private keys, secrets or unrelated raw model data in public repository documentation. Preserve a typed `UNAVAILABLE` reason where distribution rights or retention are missing.

## 7. Dependency-ordered execution — later, separately authorized

| Work package | Outcome | Closure requirement |
| --- | --- | --- |
| M1: `KNOWLEDGE_LINK_INVENTORY` | Static claim card, pinned input locks, E1–E7 link inventory, open-question register | Exact source/byte references, missing edges visible; **no new execution**. |
| M2: TM classification | Per-edge evidence labels, eight-domain-axis review and six canonical status axes | No implicit causal or authority promotion. |
| M3: schemas and preservation | Machine-readable contracts, local validator, byte-access index | Missing bytes/reviews cannot yield `READY`. |
| M4: planned negative cases | K01–K19 fixture contracts and expected reasons | All remain `NOT_RUN` until genuinely executed. |
| M5: independent historical replay | Original anchored v0.1 verifier and actual archived bytes | Separate owner authorization and new execution receipt. |
| M6: blinded successor test | B0/B1/T human handoff receipts | Independent executor actually performs the tasks, without verbal assistance. |
| M7: custody and external handoff | Comparison, retention report and bounded partner statement | No undocumented external validation or release authorization. |

**First independently executable package: M1.** Required inputs: pinned `openai/math` `adc7f1241b42e322a6451854ab7e4b4c146bf78a` and the selected PDF/TeX/Lean/scope/lock/patch files; the pinned QRH003 v0.1.3 source and reference manifests; the actual identified v0.1.1 historical archive bytes and its `pilot_002` decision, replay, Transition Meter and report records. **Optional historical context:** the 2026-10-07, 28-page audit DOCX is not a mandatory M1 input, because no general-public retrieval location is established; if used, verify its exact 82,686 bytes and SHA-256 `2cb23a9901cf4d50c2ba3b871bedc5ac2de1546bfeecf46f741014ea65a60e8e` and record who provided the bytes. Historical conclusions from this DOCX without independent upstream corroboration remain historical audit reports, not new verification. M1 outputs are **exactly** `M1/INPUTS_LOCK.json`, `M1/CLAIM_CARD_QRH003_ZETA.json`, `M1/EVIDENCE_RELATIONS.json` (E1–E7), `M1/OPEN_QUESTIONS.json`, and `M1/M1_AUDIT_TRAIL.md`. M1 closes only if every required relation has either exact supporting bytes/receipt or explicit status and reason; missing mandatory archive bytes leave M1 incomplete. M1 requires no replay, code edit or human study.

**No repository implementation changes are authorized by accepting these design documents.** A documentation-only PR adds only this overview, the three detailed plans and a targeted `docs/INDEX.md` update. The separate M1 activity requires its own instruction and evidence review.

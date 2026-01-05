# Ambiguity Register v0

This document tracks terms and semantics that are currently easy to misunderstand.
Its purpose is to prevent **semantic drift** across PRs, reports, and UI/Pages surfaces — especially before extending the Paradox / EPF / Topology layers.

This register is **governance for semantics**, not a CI gate. CI release decisions remain defined by:
- `PULSE_safe_pack_v0/tools/check_gates.py`
- `PULSE_safe_pack_v0/artifacts/status.json`
- `.github/workflows/pulse_ci.yml` (required `--require ...` gates)

## Policy

### Status definitions
- `blocking` — must be resolved before merging any PR that changes Paradox/EPF/Topology semantics or UI logic that interprets those semantics.
- `review` — definition exists but needs validation / examples / fixtures.
- `resolved` — definition is stable, linked from canonical docs, and has a determinism/fixture proof where applicable.
- `deprecated` — kept for history; should not be used for new work.

### Resolution rule (for `blocking`)
To resolve a `blocking` item, a PR must include:
1) A stable definition in a canonical doc (usually `docs/GLOSSARY_v0.md`, or a dedicated design note),
2) Explicit classification: **Normative vs Diagnostic**,
3) Inputs/Outputs: which artefacts it reads/writes + schema version (if any),
4) Determinism notes: IDs, ordering, rounding, tie‑breaks,
5) One concrete example (preferably a regression fixture or a reproducible case study).

---

## Register (v0)

| Term | 1‑line meaning | Layer | Canonical doc link | Status | Notes |
|------|-----------------|-------|--------------------|--------|------|
| Anchor | Reference frame for decision-relative interpretation (baseline / cut / run context) | Diagnostic | docs/GLOSSARY_v0.md#anchor | resolved | Canonical, non-causal framing; requires explicit anchor for orientation |
| Atom | Minimal audit-carrying evidence unit in the decision-relative field | Diagnostic | docs/GLOSSARY_v0.md#atom | resolved | Evidence-first; traceable to artefacts; not a narrative belief |
| Edge | Typed relationship between atoms; co-occurrence/association in v0 (no causality) | Diagnostic | docs/GLOSSARY_v0.md#edge | resolved | Direction/weight are decision-relative aids; no causal semantics in v0 |
| Orientation | Decision-relative reading direction w.r.t. an Anchor (push PASS/FAIL) | Diagnostic | docs/GLOSSARY_v0.md#orientation | resolved | Meaningless without Anchor; deterministic computation required |
| Core | Deterministic minimal sub-structure for reviewer readability (projection) | Diagnostic | docs/GLOSSARY_v0.md#core-field-core | resolved | Must be deterministic + explainable; not “Core profile” nor “Core gates” |
| EPF | Shadow-only stability/diagnostic layer; never flips CI outcomes | Diagnostic | docs/PULSE_epf_shadow_quickstart_v0.md | review | Clarify “missing EPF” vs “schema drift” semantics |
| RDSI | Release decision stability signal; diagnostic only | Diagnostic | PULSE_safe_pack_v0/docs/METHODS_RDSI_QLEDGER.md | review | Clarify reporting vs enforcement usage |
| Drift | Compare/history output; useful only with stable, indexable artefacts/surfaces | Diagnostic | docs/STATE_v0.md | review | Define minimal URL + artefact naming contract |
| Hazard zones | GREEN/AMBER/RED early-warning classification for field-relative signals | Diagnostic | docs/epf_relational_grail.md | review | Must define thresholds + calibration notes |

---

## Change log (local to this register)

- v0: initial register created (seed list of high-risk ambiguous terms)
- v0: mark field-first terms resolved after canonical definitions were added to `docs/GLOSSARY_v0.md`


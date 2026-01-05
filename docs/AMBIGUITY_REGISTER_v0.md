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

| Term | 1‑line meaning (to be finalized) | Layer | Canonical doc link | Status | Notes |
|------|----------------------------------|-------|--------------------|--------|------|
| Atom | Minimal evidence unit in the paradox/field layers (decision‑relative statement, not a “thing”) | Diagnostic | docs/GLOSSARY_v0.md | blocking | Must define ID rules + input sources |
| Edge | Relationship between atoms (co‑occurrence/support/conflict), no causality unless explicitly stated | Diagnostic | docs/GLOSSARY_v0.md | blocking | Must define allowed edge types + direction/polarity |
| Orientation | Decision‑relative direction (“push toward FAIL/PASS”) encoded deterministically | Diagnostic | docs/GLOSSARY_v0.md | blocking | Must define sign + weight meaning |
| Anchor | Reference node/context for decision‑relative interpretation (release decision context) | Diagnostic | docs/GLOSSARY_v0.md | blocking | Must define how anchor is derived (run_id/gate_map/etc.) |
| Core | Deterministic minimal subgraph for reviewers (stable selection rules + tie‑breaks) | Diagnostic | docs/GLOSSARY_v0.md | blocking | Must define core selection algorithm |
| EPF | Shadow‑only stability/diagnostic layer; never flips CI outcomes | Diagnostic | docs/PULSE_epf_shadow_quickstart_v0.md | review | Clarify “missing EPF” vs “schema drift” semantics |
| RDSI | Release decision stability signal; diagnostic only | Diagnostic | PULSE_safe_pack_v0/docs/METHODS_RDSI_QLEDGER.md | review | Clarify reporting vs enforcement usage |
| Drift | Compare/history output; useful only with stable, indexable artefacts/surfaces | Diagnostic | docs/STATE_v0.md | review | Define minimal URL + artefact naming contract |
| Hazard zones | GREEN/AMBER/RED early‑warning classification for field‑relative signals | Diagnostic | docs/epf_relational_grail.md | review | Must define thresholds + calibration notes |

---

## Change log (local to this register)

- v0: initial register created (seed list of high‑risk ambiguous terms)


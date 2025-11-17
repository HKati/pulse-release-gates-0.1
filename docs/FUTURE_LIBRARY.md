# PULSE Future Library – Index (draft)

> Status: draft — internal index for now.

This note collects experimental and optional modules that sit **on top of** the
deterministic PULSE release gates. The core pack (status.json, release gates,
Quality Ledger) stays unchanged; this page only tracks extra layers and tools.

Each entry has:
- **Scope** – what part of PULSE it extends,
- **Status** – draft / experimental / planned,
- **Docs** – where to read more.

---

## 1. Topology v0 family

Topology v0 is an optional, diagnostic overlay on top of the deterministic
release gates. It never changes `status.json` or CI pass/fail decisions;
it only reads existing artefacts and produces extra JSON and narrative views.

**Scope:** stability / decision trace / narrative views  
**Status:** experimental, v0

**Docs:**
- Design note → `docs/PULSE_topology_v0_design_note.md`
- Methods → `docs/PULSE_topology_v0_methods.md`
- Case study (real-world style run) → `docs/PULSE_topology_v0_case_study.md`
- EPF hook sketch → `docs/PULSE_topology_epf_hook.md`

---

## 2. EPF signal layer (shadow-only)

The EPF layer is an *optional, shadow-only* evaluation on top of a release run.
It never changes the release decision; instead, it provides a contraction /
stability signal and richer diagnostics.

**Scope:** shadow evaluation, stability research  
**Status:** sketch only (no wired tooling yet)

**Docs:**
- Main EPF description → `docs/PULSE_epf_report.txt` (A/B diff summary)
- Topology EPF hook sketch → `docs/PULSE_topology_epf_hook.md`

**Notes:**
- In v0, EPF metrics may appear as additional fields inside Topology v0
  artefacts (e.g. `status_epf.json` folded into the Stability Map v0 view).
- Any future tooling must keep EPF *shadow-only* by default: no change to
  core release gates.

---

## 3. Planned future modules (parking lot)

This section is a parking lot for ideas that are **not** implemented yet,
but may become part of the future library.

These are intentionally high-level; if/when a module becomes real, it should
get its own design note and be linked above.

- **Paradox Resolution v0**  
  - Scope: richer handling of conflicting guardrails / objectives.  
  - Status: planned idea.

- **Topology dashboards**  
  - Scope: visual comparison of topology runs across releases (stability,
    paradox patterns, EPF signals).  
  - Status: planned idea.

- **Memory / trace summariser**  
  - Scope: compact summaries of long decision traces for human review.  
  - Status: planned idea.

---

## 4. How to extend this page

When adding a new experimental module:

1. Give it a short name and a one-line scope.
2. Add a **Status** tag: draft / experimental / planned.
3. Link the primary design note under `docs/…`.
4. Make sure it is clear that the core release gates stay deterministic.

This page is a living index; it is fine if parts of it stay draft for a long
time.

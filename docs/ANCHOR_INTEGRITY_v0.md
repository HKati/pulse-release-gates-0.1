# Anchor Integrity v0 (Hallucination = Anchor Loss)

## Summary

This document defines **Anchor Integrity v0**: a diagnostic contract that treats hallucination as **Anchor Loss** (a loss of valid external anchoring), not as a purely “content quality” defect.

Anchor Integrity does **not** attempt to prove truth. It establishes whether an output is **licensed to assert** (anchored) and, if not, it recommends a safe state transition such as **BOUNDARY**, **ASK_FOR_ANCHOR**, or **SILENCE**.

**v0 decision:** Anchor Integrity is **diagnostic-only** (CI-neutral overlay). It does not block normative PULSE release gates.

---

## Core statement

**Hallucination = Anchor Loss.**

A hallucination is not “wrong text.” It is a **claim made without a valid anchor** (no auditable reference to external evidence, tools, artifacts, or explicitly provided inputs that license the claim).

---

## Definitions

### Anchor

An **anchor** is any evidence object that can be referenced and audited, and that licenses a claim. Examples:

- User-provided facts (explicit input fields, provided context)
- Tool outputs (API responses, verified measurements)
- Repo artifacts (e.g., `status.json`, published reports, Paradox bundle files)
- Explicit assumptions recorded as assumptions (not hidden)
- Citations/provenance markers that point to deterministic sources

Anchors should be:
- **Identifiable** (id/path/url)
- **Stable** (prefer deterministic artifacts over ephemeral or non-reproducible sources)
- **Auditable** (someone can check the referenced object later)

### Claim

A **claim** is any statement that asserts a fact, attribute, causality, or numeric value. Claims may be:
- **anchored** (supported by an anchor)
- **unanchored** (no anchor)
- **bounded** (explicitly limited to anchored subset)

### Anchor coverage

**Anchor coverage** is a conservative estimate of how much of the response’s claims are supported by valid anchors.

---

## Design principles

1. **Validity boundary, not truth-check**  
   Anchor Integrity does not say “true/false.” It says “licensed/unlicensed to assert.”

2. **State transitions over weaker answers**  
   When anchoring fails, the correct output is not “a softer answer,” but a **mode change**:
   - BOUNDARY (answer only what is anchored)
   - ASK_FOR_ANCHOR (request missing evidence)
   - SILENCE (stop output assertions)

3. **Fail-closed semantics**  
   If anchoring cannot be established, default to **SILENCE** or **ASK_FOR_ANCHOR**.

4. **Auditability**  
   Decisions should be explainable with an evidence list (anchors used, missing anchors, detected loops).

---

## Allowed output modes (v0)

Anchor Integrity defines **response modes**. These are not “tone” settings; they are semantic output contracts.

### 1) ANSWER
Allowed when:
- Anchor coverage is sufficient and no critical anchor-loss indicators exist.

Must:
- Prefer explicitly anchored claims.
- Preserve provenance references where possible.

Must not:
- Invent sources, citations, tool outputs, or “remembered” facts.

### 2) BOUNDARY
Used when:
- Some claims can be anchored, but coverage is incomplete or uncertain.

Must:
- Clearly state the boundary: “I can confirm X from anchors; beyond that I cannot assert.”
- Output only anchored claims inside the boundary.

Must not:
- Continue with speculative completion outside anchors.

### 3) ASK_FOR_ANCHOR
Used when:
- The answer requires a missing anchor that can be obtained (tool call, user-provided input, artifact, etc.).

Must:
- Ask for the minimal anchor needed (one step, specific).
- Prefer asking for a deterministic source (file path, artifact name, tool output).

Must not:
- Provide the unanchored answer while requesting the anchor.

### 4) SILENCE
Used when:
- There is no valid anchoring path, or the system detects self-referential closure (loop risk) or severe anchor loss.
- The system cannot safely request an anchor (e.g., no tool path / no meaningful user prompt).

SILENCE is a **real stop**, not a “weaker answer.”

Must:
- Stop producing factual claims.  
- Optionally emit a minimal structured “stop signal” such as:
  - “SILENCE: anchor_loss”
  - “STOP: insufficient anchoring”

Must not:
- Output speculative content, partial guesses, or “likely” completions.

---

## v0 scope decision: diagnostic-only overlay

**Anchor Integrity v0 is a CI-neutral diagnostic overlay.**

- It does **not** modify normative PULSE gate semantics.
- It can be published on GitHub Pages as an audit surface.
- It is safe to iterate without blocking releases.

### Promotion to normative gate (future)

Anchor Integrity may become a **normative gate candidate** only after:
1. Contract + schema stability (low churn)
2. Measured false-positive rate is acceptable (does not silence valid anchored outputs)
3. Measured false-negative rate is acceptable (does not miss anchor-loss cases)
4. Evidence logs/provenance are complete enough to audit decisions
5. Governance sign-off (release policy update)

---

## Signals and invariants (conceptual v0)

Anchor Integrity is computed from conservative signals:

### A) Anchor presence and type mix
- Are there any valid anchors at all?
- Are anchors deterministic artifacts (preferred) vs ephemeral context?

### B) Anchor coverage (coarse)
- Do key claims cite/trace to anchors?
- Are numeric claims backed by tool outputs or artifacts?

### C) Self-reference / closure risk (Paradox-driven)
- Do we see self-referential loops in reasoning structure?
- Do we see “because I said so” patterns (no outward edges)?

**Interpretation:** high loop risk without anchors suggests hallucination suspicion.

### D) Contradiction risk (optional)
- Do outputs conflict with previously anchored facts within the same run?
- Are there internal inconsistencies that indicate drift from anchors?

---

## Relationship to existing PULSE surfaces

### Separation Phase overlay
- Separation Phase detects **ordering / separation integrity** issues (FIELD_* states).
- Anchor Integrity detects **anchoring / license-to-assert** issues.

A conservative combination:
- If Separation Phase is **FIELD_COLLAPSED** or **UNKNOWN**, Anchor Integrity should bias toward **SILENCE** (fail-closed).

### Paradox Core bundle
Paradox surfaces are ideal for:
- detecting self-referential closure
- producing audit-friendly “why we silenced” explanations

---

## Proposed overlay contract (future JSON shape)

This section is a forward-looking shape proposal (non-normative in v0 doc-only step).

Example (sketch):

- `schema`: "anchor_integrity_v0"
- `meta`: run_id, commit, generator
- `inputs`: which artifacts were scanned
- `invariants`:
  - `anchor_presence`: boolean|null
  - `anchor_coverage`: number|null (0..1)
  - `loop_risk`: "low"|"medium"|"high"|null
  - `contradiction_risk`: "low"|"medium"|"high"|null
- `state`: "ANCHORED"|"PARTIAL"|"ANCHOR_LOST"|"UNKNOWN"
- `recommendation`:
  - `response_mode`: "ANSWER"|"BOUNDARY"|"ASK_FOR_ANCHOR"|"SILENCE"
  - `gate_action`: "OPEN"|"SLOW"|"CLOSED" (diagnostic mapping)
  - `rationale`: string
- `evidence`: array of anchor references and detection notes

Fail-closed rule:
- If required evidence is missing or invalid → `state="UNKNOWN"` and `response_mode="SILENCE"`.

---

## Non-goals

- This does not solve factual verification in open-world settings.
- This does not rank truth sources.
- This does not replace normative safety gates.
- This does not prescribe UI/UX; it defines a semantic contract that can be rendered.

---

## Implementation roadmap (after this doc)

1) Add schema: `schemas/anchor_integrity_v0.schema.json`
2) Add adapter: `scripts/anchor_integrity_adapter_v0.py`
3) Add contract check: `scripts/check_anchor_integrity_v0_contract.py`
4) Add renderer: `scripts/render_anchor_integrity_overlay_v0_md.py` (+ optional HTML)
5) Add shadow workflow: `.github/workflows/anchor_integrity_overlay.yml`
6) Wire into PULSE CI artifact bundle (CI-neutral)
7) Surface to Pages under `/diagnostics/anchor_integrity/v0/` + add to manifest
8) Evaluate for normative gate candidacy (policy decision + metrics)

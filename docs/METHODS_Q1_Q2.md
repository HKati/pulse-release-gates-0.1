# METHODS — Q1 (Groundedness) & Q2 (Consistency)

## Overview
Deterministic, model‑free baselines for product Quality gates:
- **Q1 Groundedness**: token coverage proxy of an answer against its evidence/context.
- **Q2 Consistency**: agreement proxy via pairwise Jaccard over answer variants.

A fail‑closed decision policy and calibration hooks are included. All steps are CPU‑first and auditable.

---

## Q1 — Groundedness (token coverage)

**Input.** One model answer `A`, context passages `C = {c1..ck}`.  
**Compute.** Tokenize `A` and all `C` with a fixed, deterministic tokenizer (lowercase, simple `\w+`, optional stop‑word removal off).  
Let `covered(A,C)` be tokens of `A` that appear in the union of tokens over `C`.  
**Score.** `Q1 = |covered(A,C)| / |tokens(A)|`, in `[0,1]`.  
**Decision (default).** `PASS` if `Q1 ≥ threshold`.  
`DEFER/FAIL` if insufficient inputs; `FAIL` otherwise.

**Determinism.** Fixed tokenizer, stable normalization; seeded, CPU‑first.

---

## Q2 — Consistency (pairwise Jaccard)

**Goal.** Stability of outputs across small, deterministic perturbations.  
**Input.** Multiple answers `A = {a1..an}` from deterministic perturbations (n≥2).  
**Base metric.** Pairwise Jaccard on token sets (answer‑level), averaged over all pairs.  
**Score.** `Q2 = average_pairwise_Jaccard(tokens(ai), tokens(aj)) ∈ [0,1]`.  
**Decision (default).** `PASS` if `Q2 ≥ threshold`.  
`DEFER/FAIL` if insufficient inputs; `FAIL` otherwise.

---

## Decision policy (fail‑closed)
- Below threshold ⇒ **FAIL** (quality gate).
- Invalid inputs / missing artifacts ⇒ **DEFER/FAIL** (conservative).
- Every step is deterministic; CPU‑first; auditable traces recommended.

---

## Calibration hooks (brief)
- **Golden set** for Q1/Q2 with positive/negative examples.  
- **Budgeted ROC/DET** and cost trade‑offs (e.g., Q1 false‑positives more costly ⇒ stricter threshold).  
- **Variance margin** from repeated runs (P95/P99) to set a safety buffer.  
- **Fairness**: min‑over‑groups.  
- **Recalibration** on detector/model updates or domain drift.

---

## Examples

### Q1 — Token coverage (toy)

**Tokenizer & normalization (toy):** lowercase, regex `\w+`, distinct tokens (set).

**Answer A:** “The cat sat on the mat.”  
`tokens(A) = {the, cat, sat, on, mat}`

**Contexts:**  
- c₁: “A cat is on a mat.” → `{a, cat, is, on, mat}`  
- c₂: “The dog sat.” → `{the, dog, sat}`

**Union of contexts:** `{a, cat, is, on, mat, the, dog, sat}`  
**Covered tokens:** `tokens(A) ∩ union(C) = {the, cat, sat, on, mat}` → **|covered| = 5**  
**Q1:** `|covered| / |tokens(A)| = 5 / 5 = 1.00`

> Note: with only `c₁`, covered would be `{cat, on, mat}`, so Q1 = 3/5 = **0.60**.

---

### Q2 — Pairwise Jaccard consistency (toy)

**Tokenizer:** as above (distinct token set).

**Answers:**  
- A¹: “the cat sits on the mat” → `{the, cat, sits, on, mat}`  
- A²: “cat sits on mat” → `{cat, sits, on, mat}`  
- A³: “the cat sat on the mat” → `{the, cat, sat, on, mat}`

**Pairwise Jaccard:**
- J(A¹, A²) = |{cat,sits,on,mat}| / |{the,cat,sits,on,mat}| = 4/5 = **0.80**  
- J(A¹, A³) = |{the,cat,on,mat}| / |{the,cat,sits,on,mat,sat}| = 4/6 ≈ **0.6667**  
- J(A², A³) = |{cat,on,mat}| / |{the,cat,sits,on,mat,sat}| = 3/6 = **0.50**

**Q2 (average):** (0.80 + 0.6667 + 0.50) / 3 ≈ **0.6556**.

---

## Audit tips
- Log inputs, token sets, and per‑pair scores.
- Keep the tokenizer spec in the repo (versioned).
- Gate decisions: store threshold, seed, and environment hash in the Quality Ledger.

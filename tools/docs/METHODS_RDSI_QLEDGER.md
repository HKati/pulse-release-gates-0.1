# Methods: RDSI & Quality Ledger (Δ with CIs)

## RDSI — Release Decision Stability Index
**Goal.** Quantify how stable the PASS/FAIL **release decision** is under reasonable variations of thresholds and detector choices.

**Definition (simple form).**
Let `D(t, d)` be the release decision (`PASS` or `FAIL`) computed with threshold setting `t ∈ T` and detector configuration `d ∈ D` (e.g., lexical vs. semantic vs. NLI graders). Let the **reference** decision be `D(t₀, d₀)`.

Define the instability count:
```
flips = |{ (t, d) ∈ T×D : D(t, d) ≠ D(t₀, d₀) }|
total = |T×D|
```
Then the **stability index** is
```
RDSI = 1 − flips / total
```
So `RDSI ∈ [0, 1]`; higher is better. By construction, `RDSI = 1` when the decision never flips across the grid of reasonable settings; `0` when it always flips.

**Practical grid.**
- Threshold band: e.g., ±5–10% around policy thresholds for each gate (I/Q/SLO).  
- Detector variants: lexical + TF‑IDF cosine + embedding/NLI; optionally vendor detectors.  
- For each (t, d), recompute status and aggregate to a binary decision; count flips.

**Reporting.** We write `metrics.RDSI` to `status.json` and expose it on the report-card & badge. Optionally we also report **per-gate** `RDSI_I*` and `RDSI_Q*` if desired.

---

## Δ with Confidence Intervals
When comparing **baseline vs. restricted** (e.g., with/without a guardrail), many gates compute a difference of proportions (e.g., grounded answers rate, refusal rate). We recommend reporting Δ with a **Newcombe confidence interval** (for difference in binomial proportions) and **Wilson CIs** for individual proportions.

**Wilson interval (for a proportion p = x/n at level α).**
Wilson’s closed-form interval is used for stability and better coverage at small n. (Ref: standard statistical texts.)

**Newcombe CI (for Δ = p₁ − p₂).**
Compute Wilson CI for `p₁` and `p₂` separately; derive the CI for Δ via the Newcombe method (no continuity correction). This avoids the poor coverage of the Wald interval.

**In PULSE.**
- The pack computes per-gate proportions (`p_base`, `p_restricted`) and Δ, and stores Wilson CIs for each p and a Newcombe CI for Δ into `artifacts/metrics.csv` and `status.json` (where applicable).  
- The **Quality Ledger** surfaces Δ and its CI per endpoint/gate (human-readable).

---

## Quality Ledger
A human-readable table aggregating **I/Q/SLO** gate outcomes (per endpoint where relevant), used for code review and PR discussion.

**Columns (example for Q4 SLO):**
- endpoint, `p95_base`, `p95_restricted`, `cost_base_sum`, `cost_restricted_sum`, `OK`  
**Optional stability columns:** `RDSI_gate`, Δ with CI.

**Usage.** Keep the ledger in version control; ship it with releases. In CI, add a PR comment with the ledger so reviewers see regressions immediately.

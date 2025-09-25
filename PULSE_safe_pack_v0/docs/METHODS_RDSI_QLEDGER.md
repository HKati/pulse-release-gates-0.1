---- START FILE ----
# Methods: RDSI & Quality Ledger (v0.1)

## RDSI — Release Decision Stability Index
**Goal:** quantify how stable the PASS/FAIL release decision is under small perturbations (seed, order, retry).  
**Definition (text):** we estimate Δ stability across repeated runs and use Newcombe score-based CIs for the difference in proportions. RDSI summarizes decision reliability on a 0..1 scale (1 = stable).  
**Ledger fields:** `rds_index: {ci_lower, ci_upper, runs}`.

## Quality Ledger — required fields
- `run.commit`, `run.profile_hash`, `run.seed`, `run.dataset_snapshot`, `timestamp_utc`
- Gates: `security.*`, `quality.*`, `slo.*` → `PASS|FAIL` + key metrics
- `rds_index`: [lower, upper] + `runs`
- `notes`: waivers / compensating controls (if any)

## Invariants (I₂–I₇)
- **I₂ Monotonicity**, **I₃ Commutativity**, **I₄ Sanitization**, **I₅ Idempotence**, **I₆ Path-independence**, **I₇ PII-monotonicity**  
*Expectation:* new tests may only tighten; repeated runs in the same environment must yield the same decision.

---

## Notes on Statistical Intervals/Tests (short)
- **Wilson score CI (binomial proportion)** — better coverage than Wald, esp. with small n or extreme p.  
  *Wilson (1927), JASA 22(158), 209–212.*  
  *Newcombe (1998a), Stat in Med 17, 857–872.*

- **Difference of two proportions (Δ) — Newcombe score-based CI** — built from Wilson intervals, improved coverage.  
  *Newcombe (1998b), Stat in Med 17, 873–890.*

- **McNemar’s test (paired proportions)** — when the same items are evaluated by two configs; focuses on flips.  
  *McNemar (1947), Psychometrika 12(2), 153–157.*
---- END FILE ----

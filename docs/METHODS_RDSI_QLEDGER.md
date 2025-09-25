# Methods: RDSI & Quality Ledger (v0.1)

## RDSI – Release Decision Stability Index
**Cél:** mennyire stabil a PASS/FAIL döntés kis perturbációkra (seed, sorrend, retry).  
**Definíció (szöveges):** több ismételt futás eredményének eltérését mérjük és Δ‑hoz Newcombe CI‑t használunk; az RDSI a döntés stabilitását jelzi 0..1 skálán (1 = stabil).  
**Ledger mezők:** `rds_index: {ci_lower, ci_upper, runs}`.

## Quality Ledger – kötelező mezők
- `run.commit`, `run.profile_hash`, `run.seed`, `run.dataset_snapshot`, `timestamp_utc`
- Kapuk: `security.*`, `quality.*`, `slo.*` → `PASS|FAIL` + kulcs metrikák
- `rds_index`: [alsó, felső] + `runs`
- `notes`: waiverek / kompenzáló kontrollok (ha vannak)

## Invariánsok (I₂–I₇)
- **I₂ Monotonitás**, **I₃ Kommutativitás**, **I₄ Szanitizáció**, **I₅ Idempotencia**, **I₆ Útvonal‑függetlenség**, **I₇ PII‑monotonitás**  
*Elvárás:* bármely új teszt csak szigoríthat; ismételt futtatás azonos környezetben azonos döntést ad.

---

## Notes on Statistical Intervals/Tests (short)
- **Wilson score CI (binomiális arány)** – stabilabb, mint a Wald‑féle közelítés, kis n vagy szélső arányok mellett.  
  *Wilson, E. B. (1927). JASA 22(158), 209–212.*  
  *Newcombe, R. G. (1998a). Stat in Med 17, 857–872.*

- **Két arány különbsége (Δ) – Newcombe score‑alapú intervallum** – Wilson‑komponensekből épül.  
  *Newcombe, R. G. (1998b). Stat in Med 17, 873–890.*

- **McNemar próba (párosított arányok)** – ugyanazon mintán mért PASS/FAIL váltásokra.  
  *McNemar, Q. (1947). Psychometrika 12(2), 153–157.*

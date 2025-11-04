# Q1–Q2 Quality Gates (deterministic baselines)

## Q1 Groundedness (RAG factuality)
**Cél.** Az output (answer) mennyire támaszkodik a megadott kontextusra.

**Baseline metrika (determinista).**
- Token coverage @ context: az answer tokenjeinek hányada megtalálható bármely kontextus-dokumentumban.
- Normalizálás: lower-case, egyszerű tokenizálás, stop‑szavak opcionálisan elhagyhatók.
- Kimenet: `q1_groundedness` ∈ [0,1].

**Döntés.** PASS, ha `q1_groundedness ≥ threshold`.

**Megjegyzés.** Későbbi bővítésként opcionális NLI/entitás‑linkelés/embedding‑overlap tehető hozzá „external detector” rétegként, de a baseline gépfüggetlen és auditálható.

## Q2 Consistency (answer agreement)
**Cél.** Az output stabilitása könnyű, determinista perturbációk mellett.

**Baseline metrika (determinista).**
- Jaccard‑hasónlóság (token‑szinten) a válasz‑variánsok között (pl. parafrázisok, mező‑sorrend, szinonima‑cserék).
- Aggregálás: átlagos páronkénti Jaccard (vagy min‑over‑pairs, ha szigorúbb kell).
- Kimenet: `q2_consistency` ∈ [0,1].

**Döntés.** PASS, ha `q2_consistency ≥ threshold`.

## Döntési politika (fail‑closed)
- Küszöb alatt → **FAIL** (quality gate).
- Számítási hiba/hiányos input → **DEFER/FAIL** (konzervatív).
- Minden lépés determinisztikus; CPU‑first, seedelt környezet.

## Küszöb‑ajánlás (baseline)
- Q1: `threshold = 0.85` (lexikális coverage).
- Q2: `threshold = 0.90` (erős egyezés).
A végső értékeket a **CALIBRATION.md** szerint finomítsd (ROC/DET, költségplafonok, szórás‑margó).

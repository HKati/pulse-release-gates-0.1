# Workflow map

Ez az oldal gyors orientációt ad a repo GitHub Actions workflow-jaihoz.

## One-line rule

Alapértelmezésben csak a primary release-gating workflow vesz részt a release outcome meghatározásában.

A shadow / diagnostic / publication / validation workflow-k lehetnek saját magukon belül fail-closedek, de önmagukban nem változtatják meg a fő release döntést, hacsak nincsenek kifejezetten promotálva a required gate setbe.

## 2-minute orientation

Ha most nyitod meg először a repót, ezt a sorrendet kövesd:

1. **Shipping / release decision**
   - `.github/workflows/pulse_ci.yml`
   - Ez a primary release-gating workflow.

2. **Repo / workflow guardrails**
   - `workflow_lint.yml`
   - Governance preflight jellegű ellenőrzések.
   - Céljuk: a workflow- és policy-réteg épségének védelme.

3. **Shadow / diagnostic workflows**
   - Ezek extra jeleket, overlayeket, riportokat vagy kutatási artefaktumokat adnak.
   - Alapból CI-neutral rétegként kezelendők.
   - Példák:
     - `.github/workflows/openai_evals_refusal_smoke_shadow.yml`
     - `.github/workflows/separation_phase_overlay.yml`
     - `.github/workflows/theory_overlay_v0.yml`
     - `.github/workflows/epf_experiment.yml`
     - G-field / G-snapshot / overlay validation jellegű shadow workflow-k

4. **Publication / GitHub-native surfaces**
   - Ezek a GitHub felületére publikálnak vagy külön native surface-eket töltenek.
   - Opt-in workflow-k legyenek, explicit write permissionnel.
   - Példák:
     - `.github/workflows/upload_sarif.yml`
     - PR comment
     - badge write-back
     - Pages snapshot

## Workflow families

### A. Primary gating
**Purpose:** release decision

- Canonical workflow: `.github/workflows/pulse_ci.yml`
- Ez futtatja a fő packot, érvényesíti a required gate-eket, és a release-döntési maghoz tartozik.
- Ha azt akarod megérteni, hogy mi blokkolhat szállítást, itt kezdd.

### B. Repo / workflow guardrails
**Purpose:** repo-integritás, workflow-integritás, governance preflight

- Ide tartoznak azok a workflow-k, amelyek a workflow YAML-ek, policy wiring vagy kapcsolódó guardrail-ek épségét védik.
- Ezek nem új release-szemantikát hoznak létre, hanem a meglévő mechanika sérülését akadályozzák.

### C. Shadow / diagnostic workflows
**Purpose:** extra diagnosztika, kutatási vagy magyarázó rétegek

- Ezek overlayeket, extra JSON/MD artefaktumokat, kutatási összehasonlításokat vagy dry-run jellegű jeleket állíthatnak elő.
- Fontos szabály:
  - **magyarázhatnak**
  - **összehasonlíthatnak**
  - **figyelmeztethetnek**
  - de alapból **nem változtathatják meg** a release outcome-ot

### D. Publication / platform integration workflows
**Purpose:** GitHub-native vagy más felületre publikálás

- Ilyen például a SARIF feltöltés GitHub Code Scanningbe.
- Ide tartozhat PR comment, badge write-back vagy Pages snapshot is.
- Ezeket külön kell tartani a primary gating workflow-tól.

## Read this together with

- `README.md`
- `docs/STATUS_CONTRACT.md`
- `docs/status_json.md`
- `docs/RUNBOOK.md`

## Practical rule for contributors

Ha új workflow-t adsz hozzá, előbb döntsd el:

- **release-gating**
- **guardrail**
- **shadow/diagnostic**
- **publication**

Ha ez nincs világosan kimondva, a workflow túl könnyen félreérthető lesz.

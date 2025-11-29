# PULSE v0 – state snapshot (EP-go1 / EPLabsAI)

This note summarises the current state of the PULSE v0 architecture in
this repository, as maintained by the EP-go1 / E•Paradox Labs (EPLabsAI)
workshop.

It is not a full design document; it is a quick, human-readable
"where things are" snapshot.

---

## 1. Core gates and safe-pack

- The core PULSE deterministic release gates live in:

  - `PULSE_safe_pack_v0/` (safe-pack),
  - `PULSE_safe_pack_v0/pulse_policy.yml` (policy source of truth).

- These gates are:
  - **fail-closed** – any required gate failure blocks the release,
  - CI-enforced via the main `pulse_ci` workflow.

- External documentation:
  - README and methods docs describe which gates exist and what they
    check.
  - The Quality Ledger is the human-readable record of outcomes.

Status: **stable, production-facing**.

---

## 2. EPF & Paradox (shadow layer)

- EPF is wired as a **shadow-only** evaluation:

  - `.github/workflows/epf_experiment.yml` runs a non-blocking A/B
    between baseline gates and EPF shadow logic.
  - Outputs include:
    - `status_baseline.json`
    - `status_epf.json`
    - `epf_report.txt`
    - `epf_paradox_summary.json`

- GitHub Actions Summary shows:

  - ✅ when EPF and baseline agree on all gates,
  - ⚠️ when some gates have different decisions (paradox candidates).

- Human guidance:

  - `docs/PARADOX_RUNBOOK.md` explains what a maintainer should do when
    EPF and baseline disagree (inspect, classify, decide, record).

Status: **diagnostic, research-focused, CI-neutral**.

---

## 3. External detectors

- External detectors are supported via an integration layer:

  - Safe-pack docs:
    - `PULSE_safe_pack_v0/docs/EXTERNAL_DETECTORS.md`

- Two conceptual modes:

  1. **Gating mode (current default in this repo)**  
     - External summaries are combined into a gate such as
       `external_all_pass`.
     - The main CI includes this gate in the required set.
     - When metrics cross configured thresholds, CI fails.

  2. **Advisory / shadow mode**  
     - Results are logged for analysis and governance only.
     - Not currently the default wiring in this repository, but
       supported conceptually and for downstream configurations.

Status: **gating by default in this repo, with advisory-only mode
available by configuration**.

---

## 4. RDSI & stability signals

- RDSI (Release Decision Stability Index) is a **per-run stability
  signal**:

  - It asks: "If we perturb conditions slightly, how stable is the
    PASS/FAIL decision?"
  - High RDSI → robust decisions; low RDSI → fragile decisions.

- It does **not** implement full long-term drift monitoring on its own.

- Documentation:

  - Methods: `PULSE_safe_pack_v0/docs/METHODS_RDSI_QLEDGER.md`
  - Human notes: `docs/RDSI_STABILITY_NOTES.md`

Status: **in use as a stability overlay; no automatic drift control**.

---

## 5. Drift and governance

- PULSE emits rich artefacts (gates, ledgers, RDSI, EPF, optional
  external detectors), but:

  - does **not** ship a full time-series drift monitoring / alerting
    system,
  - does **not** auto-adjust thresholds or policies.

- Drift-aware usage is described in:

  - `docs/DRIFT_OVERVIEW.md`

Status: **drift analysis is expected to be handled by higher-level
governance / monitoring built on top of PULSE artefacts**.

---

## 6. PR summaries and tooling

- Canonical PR summary path:

  - `PULSE_safe_pack_v0/tools/ci/pr_comment_qledger.py`

- Top-level helper / example:

  - `docs/PR_SUMMARY_TOOLS.md` explains roles and usage.

Status: **PR summary tooling available; pack commenter is canonical**.

---

## 7. Contributing & automation

- Conventions:

  - Conventional Commits / semantic PR titles,
  - DCO sign-off,
  - changelog updates under `[Unreleased]`.

- External AI review:

  - Codex (`chatgpt-codex-connector`) is configured as a GitHub
    integration to review PRs.
  - P1 findings are treated as **merge-blocking** until addressed.

- See:

  - `CONTRIBUTING.md` for the full contributor guidance.

---

This state snapshot is v0-flavoured: it will likely evolve as EPF,
Paradox Resolution, and drift tooling mature. When making significant
changes to the architecture, please consider updating this file so that
new readers can see, at a glance, where the system stands.

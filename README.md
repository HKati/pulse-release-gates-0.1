<!-- HERO (dark default) -->
<img alt="Run PULSE before you ship." src="hero_dark_4k.png" width="100%">

<p align="center">
  <em>Prefer a light version?</em>
</p>

<details>
  <summary><strong>Show light hero</strong></summary>
  <img alt="Run PULSE before you ship. (light)" src="hero_light_4k.png" width="100%">
</details>

[![DOI](https://doi.org/badge/DOI/10.5281/zenodo.17373002.svg)](https://doi.org/10.5281/zenodo.17373002)


[![PULSE](badges/pulse_status.svg)](https://hkati.github.io/pulse-release-gates-0.1/)
[![RDSI](badges/rdsi.svg)](https://hkati.github.io/pulse-release-gates-0.1/status.json)
[![Q‑Ledger](badges/q_ledger.svg)](https://hkati.github.io/pulse-release-gates-0.1/#quality-ledger)

**See the latest Quality Ledger (live):** https://hkati.github.io/pulse-release-gates-0.1/


### Project links (mirrors)

- **Repo:** https://github.com/HKati/pulse-release-gates-0.1
- **Live Quality Ledger:** https://hkati.github.io/pulse-release-gates-0.1/

- **Kaggle Dataset (EPF A/B artifacts, seeded) — DOI:** https://doi.org/10.34740/kaggle/dsv/13571702
- **Kaggle Dataset (baseline demo; deterministic, fail‑closed) — DOI:** https://doi.org/10.34740/kaggle/dsv/13571927

- **Kaggle Notebook (repro figures — EPF A/B, seeded):**
  https://www.kaggle.com/code/horvathkatalin/pulse-epf-shadow-a-b-reproduce-figures-seeded
- **Kaggle Notebook (offline quick start — Ledger & Q3+Q4):**
  https://www.kaggle.com/code/horvathkatalin/pulse-demo-offline-quick-start-q3-q4-ledger

- **DOI (versioned, Zenodo):** https://doi.org/10.5281/zenodo.17373002
- **DOI (concept, all versions, Zenodo):** https://doi.org/10.5281/zenodo.17214908

Releases: https://github.com/HKati/pulse-release-gates-0.1/releases



# PULSE — Release Gates for Safe & Useful AI

From **findings** to **fuses**. Run **PULSE before you ship**: deterministic, **fail-closed** gates that turn red-team insights into **release decisions** for both safety (I₂–I₇) and product utility (Q₁–Q₄). Offline, CI-enforced, audit-ready.

<p>
  <img src="badges/pulse_status.svg" height="20" alt="PULSE status">
  <img src="badges/rdsi.svg" height="20" alt="RDSI">
  <img src="badges/q_ledger.svg" height="20" alt="Q-Ledger">
</p>

> **TL;DR**: Drop the pack → run → enforce → ship.  
> PULSE gives PASS/FAIL release gates, a human-readable **Quality Ledger**, and a stability signal (**RDSI**).

### What’s new

- **External detectors (opt‑in):** merge JSON/JSONL summaries from safety tools into the gate + Quality Ledger.
- **Refusal‑delta:** stability signal for refusal policies (audit‑friendly quantification).
- **JUnit & SARIF:** export artifacts for CI dashboards and code scanning.
- **First‑run stays simple:** defaults unchanged; optional pieces can be enabled later.

➡️ Full notes: see [Releases](https://github.com/HKati/pulse-release-gates-0.1/releases) and [CHANGELOG](./CHANGELOG.md).

---

## Quickstart

**Linux / GitHub Actions runner**
```bash
python PULSE_safe_pack_v0/tools/run_all.py
python PULSE_safe_pack_v0/tools/check_gates.py --status PULSE_safe_pack_v0/artifacts/status.json --require   pass_controls_refusal effect_present psf_monotonicity_ok psf_mono_shift_resilient   pass_controls_comm psf_commutativity_ok psf_comm_shift_resilient   pass_controls_sanit sanitization_effective sanit_shift_resilient   psf_action_monotonicity_ok psf_idempotence_ok psf_path_independence_ok psf_pii_monotonicity_ok   q1_grounded_ok q2_consistency_ok q3_fairness_ok q4_slo_ok

```

**Windows PowerShell**
```powershell
python PULSE_safe_pack_v0/tools/run_all.py
python PULSE_safe_pack_v0/tools/check_gates.py `
  --status PULSE_safe_pack_v0/artifacts/status.json `
  --require `
  pass_controls_refusal effect_present psf_monotonicity_ok psf_mono_shift_resilient `
  pass_controls_comm psf_commutativity_ok psf_comm_shift_resilient `
  pass_controls_sanit sanitization_effective sanit_shift_resilient `
  psf_action_monotonicity_ok psf_idempotence_ok psf_path_independence_ok psf_pii_monotonicity_ok `
  q1_grounded_ok q2_consistency_ok q3_fairness_ok q4_slo_ok

```
**See the latest Quality Ledger (live):** https://hkati.github.io/pulse-release-gates-0.1/

**Artifacts**
- **Report Card** → `PULSE_safe_pack_v0/artifacts/report_card.html`
- **Status JSON** → `PULSE_safe_pack_v0/artifacts/status.json`

### Try PULSE on your repo (5 minutes)

1. **Copy the pack** to your repo root:
   - `PULSE_safe_pack_v0/` (or unzip `PULSE_safe_pack_v0.zip`).

2. **Add the CI workflow**: copy `.github/workflows/pulse_ci.yml` from this repo.

3. **Run it**:
   - Open **Actions → PULSE CI → Run workflow** (or push a PR).
   - PULSE will generate: `status.json`, `report_card.html`, CI badges, and a PR comment.

**Ritual:** _Run PULSE before you ship._  
PULSE enforces fail‑closed PASS/FAIL gates across Safety (I₂–I₇), Quality (Q₁–Q₄), and SLO budgets, on archived logs.

---

## What PULSE checks

**Safety invariants (I₂–I₇)** — deterministic PASS/FAIL gates:
- Monotonicity (incl. shift-resilience)
- Commutativity (incl. shift-resilience)
- Sanitization effectiveness (incl. shift-resilience)
- Action-monotonicity, Idempotence, Path-independence
- PII-leak monotonicity

**Quality gates (Q₁–Q₄)** — product-facing guardrails:
- Q₁ **Groundedness** (RAG factuality)
- Q₂ **Consistency** (answer agreement)
- Q₃ **Fairness** (parity / equalized odds)
- Q₄ **SLOs** (p95 latency & cost budgets)

**Outputs**
- **Quality Ledger** (human-readable table in the report card)
- **RDSI** (Release Decision Stability Index) + Δ with CIs
- **Badges** (PASS/FAIL, RDSI, Q-Ledger) in `/badges/`

## Decision levels

**FAIL** (pipeline blocked) • **STAGE-PASS** (staging release) • **PROD-PASS** (production deploy allowed).  
Break‑glass overrides require justification; the justification is recorded in the Quality Ledger.

## Determinism (caveats)

PULSE is deterministic if the runner image + seeds + CPU/GPU mode are pinned. External detectors and GPU kernel variance can introduce flakiness; EPF (shadow) + RDSI quantify stability without ever changing CI outcomes.

## Native CI outputs

From `status.json`, PULSE exports **JUnit** (Tests tab) and **SARIF** (Security → Code scanning alerts) into `reports/` and uploads them as CI artifacts.

---

## CI — already wired

This repository ships with a single workflow: `.github/workflows/pulse_ci.yml`

It will:
1. locate/unzip the pack (`PULSE_safe_pack_v0/` or `PULSE_safe_pack_v0.zip`),
2. **run** the checks,
3. **enforce** (fail-closed) the required gates,
4. **augment** status with optional external detector summaries,
5. **update & commit** the SVG badges into `/badges/`,
6. **upload artifacts** (pulse-report: report card + status + badges),
7. on PRs, post a **Quality Ledger** comment.

> Tip: after making the repo **public**, add a **Branch protection rule** (Settings → Branches) and mark **PULSE CI** as a **required status check**.


## EPF (experimental, shadow‑only)

**TL;DR:** Deterministic, fail‑closed gates remain the source of truth for releases.  
EPF runs as a **shadow evaluation only**; it never changes CI outcomes.

**What is EPF?** An optional, seeded and auditable adaptive layer that operates only within the `[threshold − ε, threshold]` band to study potential false‑fail reduction.  
Outside the band → **FAIL**; insufficient evidence → **DEFER/FAIL**; risk above `max_risk` → **FAIL** (all **shadow** outcomes).

### Stability (EPF — research signal)
We log a contraction proxy for a gate‑feedback operator `F: X→X`.  
If `epf_L < 1`, the EPF layer is locally contractive on a window `W`; in the EPF report we mark this as a **shadow pass**.  
This signal is **diagnostic only** and **never alters CI decisions**.

- **Metric:** `metrics.epf_L` in **`status_epf.json`** (plus a shadow ledger flag, e.g. `ledger.epf.shadow_pass`)  
- **Scope:** Logged by the EPF workflow; **not** part of baseline `status.json`.  
- **Status:** Research; full derivation will be published separately.

### Artifacts
- `status_baseline.json` — deterministic decisions (source of truth)  
- `status_epf.json` — EPF shadow metrics, traces & decisions (incl. `metrics.epf_L`)  
- `epf_report.txt` — A/B diff summary (optional)

### Optional config (per gate)
```yaml
gates:
  - id: q1_groundedness
    threshold: 0.85
    epsilon: 0.03     # enables the adaptive band
    adapt: true
    max_risk: 0.20
    ema_alpha: 0.20
    min_samples: 5
```

**CI:** EPF runs as a **separate, CI‑neutral** workflow (`.github/workflows/epf_experiment.yml`).  
Deterministic, fail‑closed gates in `check_gates.py` remain the **only** release gates.


---

## Repository layout
```
PULSE_safe_pack_v0/            # the pack (tools/, docs/, profiles/, artifacts/)
badges/                         # CI-generated SVG badges (status, RDSI, Q-Ledger)
hero_dark_4k.png, hero_light_4k.png, og_image_1200x630.png
PULSE_one_pager.png | .pdf
pulse_landing_snippet.html
.github/workflows/pulse_ci.yml
README.md
```

---

## Methods & external detectors

- **Methods (RDSI & Ledger):** `PULSE_safe_pack_v0/docs/METHODS_RDSI_QLEDGER.md`  
- **External detectors (optional):** `PULSE_safe_pack_v0/docs/EXTERNAL_DETECTORS.md`  
  - Plug-in adapters via simple JSON/JSONL summaries (e.g., Llama Guard, Prompt Guard, Garak, Azure Evaluations, Promptfoo, DeepEval).

... 

## PULSE Topology v0 (Stability Map + Decision Engine + Dual View)

The topology layer is an optional, diagnostic overlay on top of the
deterministic PULSE release gates. It **never** changes `status.json` or
CI pass/fail behaviour; it only reads existing artefacts and produces extra
JSON and narrative views.

It consists of:

- **Stability Map v0** – aggregates `status.json` and optional EPF metrics
  into a stability score and stability type per run.
- **Decision Engine v0** – reads the Stability Map and produces a structured
  decision trace (BLOCK / STAGE_ONLY / PROD_OK + explanation).
- **Dual View v0** – a shared human + agent view of the same data
  (short narrative + machine‑friendly JSON).

Docs & specs:

- `docs/PULSE_topology_v0.md` – Stability Map spec  
- `docs/PULSE_decision_engine_v0.md` – Decision Engine v0  
- `docs/PULSE_topology_howto_v0.md` – demo walkthrough  
- `docs/PULSE_topology_real_run_v0.md` – how the topology layer attaches to real CI runs  
- `docs/PULSE_dual_view_v0.md` – Dual View v0 format
- `docs/PULSE_topology_epf_hook.md` – EPF hook sketch (shadow‑only, v0)

---

## How to cite

If you use this software, please cite the **versioned release** below.

- **Release DOI (versioned):** [10.5281/zenodo.17373002](https://doi.org/10.5281/zenodo.17373002)  
- **Concept DOI (all versions):** [10.5281/zenodo.17214908](https://doi.org/10.5281/zenodo.17214908)

### BibTeX
```bibtex
@software{pulse_v1_0_2,
  title        = {PULSE: Deterministic Release Gates for Safe \& Useful AI},
  author       = {Horvat, Katalin and EPLabsAI},
  year         = {2025},
  version      = {v1.0.2},
  doi          = {10.5281/zenodo.17373002},
  url          = {https://doi.org/10.5281/zenodo.17373002}
}
```

## Acknowledgments

This work used **ChatGPT (GPT‑5 Pro)** for drafting support, CI workflow tips, and repo‑hygiene suggestions.  
Human authors retain full responsibility for the design, verification, and decisions.

---

## Case studies & Radar

- [Lighthouse Case #1](PULSE_safe_pack_v0/docs/LIGHTHOUSE_CASE_1.md)
- [Competitor Radar (2025)](PULSE_safe_pack_v0/docs/COMPETITOR_RADAR_2025.md)

## License & contact


## License & contact

**License:** Apache‑2.0 — see [LICENSE](./LICENSE).  
**Contact:** [eplabsai@eplabsai.com](mailto:eplabsai@eplabsai.com?subject=PULSE%20inquiry) · [horkati65810@gmail.com](mailto:horkati65810@gmail.com?subject=PULSE%20inquiry)

**EPLabsAI — PULSE. From findings to fuses.**

<!-- docs: tidy EOF -->

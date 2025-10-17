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


# PULSE — Release Gates for Safe & Useful AI

From **findings** to **fuses**. Run **PULSE before you ship**: deterministic, **fail-closed** gates that turn red-team insights into **release decisions** for both safety (I₂–I₇) and product utility (Q₁–Q₄). Offline, CI-enforced, audit-ready.

<p>
  <img src="badges/pulse_status.svg" height="20" alt="PULSE status">
  <img src="badges/rdsi.svg" height="20" alt="RDSI">
  <img src="badges/q_ledger.svg" height="20" alt="Q-Ledger">
</p>

> **TL;DR**: Drop the pack → run → enforce → ship.  
> PULSE gives PASS/FAIL release gates, a human-readable **Quality Ledger**, and a stability signal (**RDSI**).

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


## Acknowledgments

This work used **ChatGPT (GPT‑5 Pro)** for drafting support, CI workflow glue suggestions, and repository QA.  
Human authors retain full responsibility for the design, verification, and decisions.

---

## Case studies & Radar

- [Lighthouse Case #1](PULSE_safe_pack_v0/docs/LIGHTHOUSE_CASE_1.md)  
- [Competitor Radar (2025)](PULSE_safe_pack_v0/docs/COMPETITOR_RADAR_2025.md)

## License & contact

**License:** Apache-2.0 — see [LICENSE](./LICENSE).  
**Contact:** eplabsai@eplabsai.com · horkati65810@gmail.com

**EPLabsAI — PULSE. From findings to fuses.**

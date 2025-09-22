<p align="center">
  <img src="PULSE_readme_hero_1400x360.png" alt="Run PULSE before you ship" width="100%">
</p>
<p><img src="PULSE_avatar_ringed_512.png" alt="PULSE" width="120"></p>


# PULSE — Release Gates for Safe & Useful AI

From **findings** to **fuses**. Run **PULSE before you ship**: deterministic, **fail‑closed** gates that turn red‑team insights into **release decisions** for both safety (I₂–I₇) and product utility (Q₁–Q₄). Offline, CI‑enforced, audit‑ready.

<p>
  <img src="badges/pulse_status.svg" height="20" alt="PULSE status">
  <img src="badges/rdsi.svg" height="20" alt="RDSI">
  <img src="badges/q_ledger.svg" height="20" alt="Q‑Ledger">
</p>

> **TL;DR**: Drop the pack → run → enforce → ship.  
> PULSE gives PASS/FAIL release gates, a human‑readable **Quality Ledger**, and a stability signal (**RDSI**).

---

## Quickstart

**Linux / GitHub Actions runner**
```bash
python PULSE_safe_pack_v0/tools/run_all.py
python PULSE_safe_pack_v0/tools/check_gates.py --status PULSE_safe_pack_v0/artifacts/status.json --require \
  pass_controls_refusal effect_present psf_monotonicity_ok psf_mono_shift_resilient \
  pass_controls_comm psf_commutativity_ok psf_comm_shift_resilient \
  pass_controls_sanit sanitization_effective sanit_shift_resilient \
  psf_action_monotonicity_ok psf_idempotence_ok psf_path_independence_ok psf_pii_monotonicity_ok \
  q1_grounded_ok q2_consistency_ok q3_fairness_ok q4_slo_ok
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

**Artifacts**
- **Report Card** → `PULSE_safe_pack_v0/artifacts/report_card.html`  
- **Status JSON** → `PULSE_safe_pack_v0/artifacts/status.json`

---

## What PULSE checks

**Safety invariants (I₂–I₇)** — deterministic PASS/FAIL gates:
- Monotonicity (incl. shift‑resilience)  
- Commutativity (incl. shift‑resilience)  
- Sanitization effectiveness (incl. shift‑resilience)  
- Action‑monotonicity, Idempotence, Path‑independence  
- PII‑leak monotonicity

**Quality gates (Q₁–Q₄)** — product‑facing guardrails:
- Q₁ **Groundedness** (RAG factuality)  
- Q₂ **Consistency** (answer agreement)  
- Q₃ **Fairness** (parity / equalized odds)  
- Q₄ **SLOs** (p95 latency & cost budgets)

**Outputs**
- **Quality Ledger** (human‑readable table in the report card)  
- **RDSI** (Release Decision Stability Index) + Δ with CIs  
- **Badges** (PASS/FAIL, RDSI, Q‑Ledger) in `/badges/`

---

## CI — already wired

This repository ships with a single workflow:  
`.github/workflows/pulse_ci.yml`

It will:
1. locate/unzip the pack (`PULSE_safe_pack_v0/` or `PULSE_safe_pack_v0.zip`),  
2. **run** the checks,  
3. **enforce** (fail‑closed) the required gates,  
4. **augment** status with optional external detector summaries,  
5. **update & commit** the SVG badges into `/badges/`,  
6. **upload artifacts** (`pulse-report`: report card + status + badges),  
7. on PRs, post a **Quality Ledger** comment.

> Tip: after making the repo **public**, add a **Branch protection rule** (Settings → Branches) and mark **PULSE CI** as a **required status check**.

---

## Repository layout

```
PULSE_safe_pack_v0/            # the pack (tools/, docs/, profiles/, artifacts/)
badges/                         # CI‑generated SVG badges (status, RDSI, Q‑Ledger)
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
  - Plug‑in adapters via simple JSON/JSONL summaries (e.g., Llama Guard, Prompt Guard, Garak, Azure Evaluations, Promptfoo, DeepEval).

---

## How to cite

If you use PULSE in research or production, please cite this repository and the forthcoming arXiv preprint:

```
PULSE — Release Gates for Safe & Useful AI, EPLabsAI (2025).
```

---

## License & contact

**License:** Apache‑2.0 — see [`LICENSE`](./LICENSE).  
**Contact:** eplabsai@eplabsai.com · horkati65810@gmail.com

**EPLabsAI — PULSE. From findings to fuses.**

<!-- HERO (dark default) -->
<img alt="Run PULSE before you ship." src="hero_dark_4k.png" width="100%">

<p align="center"><em>Prefer a light version?</em></p>
<details>
  <summary><strong>Show light hero</strong></summary>
  <img alt="Run PULSE before you ship. (light)" src="hero_light_4k.png" width="100%">
</details>

[![PULSE](badges/pulse_status.svg)](PULSE_safe_pack_v0/artifacts/report_card.html)
[![RDSI](badges/rdsi.svg)](PULSE_safe_pack_v0/artifacts/status.json)
[![Q‑Ledger](badges/q_ledger.svg)](PULSE_safe_pack_v0/artifacts/report_card.html#quality-ledger)

# PULSE — Release Gates for Safe & Useful AI

From **findings** to **fuses**. Run **PULSE before you ship**: deterministic, **fail‑closed** gates that turn red‑team insights into **release decisions** for both safety (I₂–I₇) and product utility (Q₁–Q₄). Offline, CI‑enforced, audit‑ready.

> **TL;DR**: Drop the pack → run → enforce → ship.  
> PULSE gives PASS/FAIL release gates, a human‑readable **Quality Ledger**, and a stability signal (**RDSI**).

---

## Quickstart

**Local one‑liner**
```bash
pip install -r requirements.txt && make all

python PULSE_safe_pack_v0/tools/run_all.py
python PULSE_safe_pack_v0/tools/check_gates.py --status PULSE_safe_pack_v0/artifacts/status.json --require \
  pass_controls_refusal effect_present psf_monotonicity_ok psf_mono_shift_resilient \
  pass_controls_comm psf_commutativity_ok psf_comm_shift_resilient \
  pass_controls_sanit sanitization_effective sanit_shift_resilient \
  psf_action_monotonicity_ok psf_idempotence_ok psf_path_independence_ok psf_pii_monotonicity_ok \
  q1_grounded_ok q2_consistency_ok q3_fairness_ok q4_slo_ok \
  refusal_delta_pass external_all_pass manifest_ok

python PULSE_safe_pack_v0/tools/run_all.py
python PULSE_safe_pack_v0/tools/check_gates.py `
  --status PULSE_safe_pack_v0/artifacts/status.json `
  --require `
  pass_controls_refusal effect_present psf_monotonicity_ok psf_mono_shift_resilient `
  pass_controls_comm psf_commutativity_ok psf_comm_shift_resilient `
  pass_controls_sanit sanitization_effective sanit_shift_resilient `
  psf_action_monotonicity_ok psf_idempotence_ok psf_path_independence_ok psf_pii_monotonicity_ok `
  q1_grounded_ok q2_consistency_ok q3_fairness_ok q4_slo_ok `
  refusal_delta_pass external_all_pass manifest_ok

PULSE_safe_pack_v0/            # the pack (tools/, docs/, profiles/, examples/, artifacts/)
badges/                         # CI‑generated SVG badges (status, RDSI, Q‑Ledger)
hero_dark_4k.png, hero_light_4k.png
PULSE_one_pager.pdf
.github/workflows/pulse_ci.yml
README.md

::contentReference[oaicite:0]{index=0}

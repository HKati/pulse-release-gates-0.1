# PULSE — Release Gates for Safe & Useful AI

From **findings** to **fuses**. Run **PULSE before you ship**: deterministic, **fail‑closed** gates that turn red‑team insights into **release decisions** for both safety (I₂–I₇) and product utility (Q₁–Q₄). Offline, CI‑enforced, audit‑ready.

<p>
  <img src="badges/pulse_status.svg" height="20" alt="PULSE status">
  <img src="badges/rdsi.svg" height="20" alt="RDSI">
  <img src="badges/q_ledger.svg" height="20" alt="Q‑Ledger">
</p>

> **TL;DR**: Drop the pack → run → enforce → ship.  
> PULSE gives you PASS/FAIL gates + a human‑readable **Quality Ledger** and a stability signal (**RDSI**).

---

## Quickstart

**Bash / Linux / GitHub Actions runner**
```bash
python PULSE_safe_pack_v0/tools/run_all.py
python PULSE_safe_pack_v0/tools/check_gates.py --status PULSE_safe_pack_v0/artifacts/status.json --require \
  pass_controls_refusal effect_present psf_monotonicity_ok psf_mono_shift_resilient \
  pass_controls_comm psf_commutativity_ok psf_comm_shift_resilient \
  pass_controls_sanit sanitization_effective sanit_shift_resilient \
  psf_action_monotonicity_ok psf_idempotence_ok psf_path_independence_ok psf_pii_monotonicity_ok \
  q1_grounded_ok q2_consistency_ok q3_fairness_ok q4_slo_ok

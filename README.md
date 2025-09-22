# PULSE — Release Gates for Safe & Useful AI

**Run PULSE before you ship.** Deterministic, **fail‑closed** gates that turn red‑team insights into **release decisions** — for safety (I₂–I₇) and product utility (Q₁–Q₄). Offline, CI‑enforced, audit‑ready.

<p>
  <img src="badges/pulse_pass.svg" height="20" alt="PULSE: PASS">
  <img src="badges/rdsi_gte_0_80.svg" height="20" alt="RDSI ≥ 0.80">
  <img src="badges/q_ledger_all_pass.svg" height="20" alt="Q‑Ledger: ALL PASS">
</p>

## Quickstart

**Bash / GitHub Actions runner**
```bash
python PULSE_safe_pack_v0/tools/run_all.py
python PULSE_safe_pack_v0/tools/check_gates.py --status PULSE_safe_pack_v0/artifacts/status.json --require \
  pass_controls_refusal effect_present psf_monotonicity_ok psf_mono_shift_resilient \
  pass_controls_comm psf_commutativity_ok psf_comm_shift_resilient \
  pass_controls_sanit sanitization_effective sanit_shift_resilient \
  psf_action_monotonicity_ok psf_idempotence_ok psf_path_independence_ok psf_pii_monotonicity_ok \
  q1_grounded_ok q2_consistency_ok q3_fairness_ok q4_slo_ok

Commit to main

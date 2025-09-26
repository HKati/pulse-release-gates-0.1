# PULSE `status.json` Contract (public alpha)

Minimal stable fields:

```json
{
  "version": "1.0.0",
  "created_utc": "YYYY-MM-DDThh:mm:ssZ",
  "meta": {
    "policy_profile": "default_v1",
    "policy_hash": "sha256:<hex>", 
    "rdsi": <float 0..1>
  },
  "gates": {
    "pass_controls_refusal": true,
    "effect_present": true,
    "psf_monotonicity_ok": true,
    "psf_mono_shift_resilient": true,
    "pass_controls_comm": true,
    "psf_commutativity_ok": true,
    "psf_comm_shift_resilient": true,
    "pass_controls_sanit": true,
    "sanitization_effective": true,
    "sanit_shift_resilient": true,
    "psf_action_monotonicity_ok": true,
    "psf_idempotence_ok": true,
    "psf_path_independence_ok": true,
    "psf_pii_monotonicity_ok": true,
    "q1_grounded_ok": true,
    "q2_consistency_ok": true,
    "q3_fairness_ok": true,
    "q4_slo_ok": true,
    "external_all_pass": true,
    "refusal_delta_pass": true
  }
}

.PHONY: run check badges report all

run:
	python PULSE_safe_pack_v0/tools/run_all.py

check:
	python PULSE_safe_pack_v0/tools/check_gates.py --status PULSE_safe_pack_v0/artifacts/status.json --require \
		pass_controls_refusal effect_present psf_monotonicity_ok psf_mono_shift_resilient \
		pass_controls_comm psf_commutativity_ok psf_comm_shift_resilient \
		pass_controls_sanit sanitization_effective sanit_shift_resilient \
		psf_action_monotonicity_ok psf_idempotence_ok psf_path_independence_ok psf_pii_monotonicity_ok \
		q1_grounded_ok q2_consistency_ok q3_fairness_ok q4_slo_ok refusal_delta_pass external_all_pass

badges:
	python PULSE_safe_pack_v0/tools/ci/update_badges.py --status PULSE_safe_pack_v0/artifacts/status.json --assets badges --out badges

report: run check badges
all: report

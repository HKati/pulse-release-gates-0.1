# Gravity Record Protocol — explicit requirement v0.2

This revision corrects the correspondence between the operational model and the
numerical implementation. It is a synthetic, non-authority demonstrator, not a
physical gravity measurement or a new gravitational law.

## Quantity binding

- `lambda` retains its meaning as a dimensionless frequency ratio in the source
  bundle. It is not used as an information-rate requirement.
- `kappa` is the usable fraction in a declared symbol-channel proxy model.
- `h_req` is an explicit nonnegative reconstruction requirement in the selected
  `bits_per_tick` (`log2`) or `nats_per_tick` (`ln`) units.
- `requirement_id` identifies the declared reconstruction/calibration requirement.
  Its presence does not certify that the calibration was performed.
- `margin` is an explicit nonnegative additional rate requirement, in the same units.

The modeled capacity proxy is `C(r) = kappa(r) * log_base(alphabet_size)`;
`diff(r) = C(r) - h_req - margin`. Decodability is modeled by `diff >= 0`.
This expression requires a suitable channel model (for example, ideal flagged
symbol erasures). A measured correct-decoding fraction alone does not establish
Shannon capacity for arbitrary channels, correlated noise, or finite blocks.

## Historical boundary

The v0.1 code used `lambda` where the concept document described `h_req`.
No conversion was bound. Existing v0.1 sources and JSON outputs are preserved;
they are not relabeled or replayed as corrected v0.2 evidence. The v0.2 checker
rejects v0.1 artifacts. The existing raw-input v0.1 contract is reused.

## Execution

```bash
python scripts/build_gravity_record_protocol_inputs_v0_1.py \
  --rawlog PULSE_safe_pack_v0/fixtures/gravity_record_protocol_v0_1.rawlog.demo.jsonl \
  --out out/gravity_record_protocol_inputs_v0_1.json --source-kind demo
python scripts/check_gravity_record_protocol_inputs_v0_1_contract.py \
  --in out/gravity_record_protocol_inputs_v0_1.json
python scripts/build_gravity_record_protocol_decodability_wall_v0_2.py \
  --in out/gravity_record_protocol_inputs_v0_1.json \
  --out out/decodability_wall_v0_2.json --alphabet-size 2 --log-base log2 \
  --h-req 0.99 --requirement-id TEST:synthetic-rate-0.99
python scripts/check_gravity_record_protocol_decodability_wall_v0_2_contract.py \
  --in out/decodability_wall_v0_2.json
python -m pytest -q tests/test_gravity_decodability_wall_v0_2.py
```

The requirement above is declared synthetic data, not a calibrated physical
reconstruction target. The demo has kappa 1.00 and 0.98 at coordinates 0 and 1;
linear interpolation gives `r_c=0.5`. Those coordinates are the input profile's
coordinates, not independently verified station radii in metres.

The output binds the input file SHA-256 and records the rate requirement, its ID,
margin, alphabet, log base, units, interpolation method and tie-break. Missing
requirements have no default. Failed/missing kappa, duplicate numeric coordinates,
invalid ranges, unresolved raw errors, and nonnumeric coordinates fail closed.
The checker verifies the output contract; it is not an independent numerical
replay or a physical-cause verifier. Changing valid lambda values changes the
source digest but must not change the numerical threshold.

## Interpretation of sampled crossings

Linear interpolation is an explicit modeling assumption between measured samples.
A single observed crossing is not proof of a globally unique physical boundary.
For an equality root, continuity plus a bracket supports existence, and strict
monotonicity supports uniqueness. Non-strict monotonicity can produce a plateau;
a discontinuity can cross a threshold without an equality root. Multiple sampled
crossings are reported separately with the lowest-coordinate crossing selected.
Uncertainty is preserved in the source bundle but not propagated into a confidence
interval for this point estimate.

## Physical attribution remains separate

The earlier protocol specifies bidirectional drift diagnostics, indexed pulse
counts, jitter/dropout recording, and trials with/without error correction.
The current builder does not distinguish gravity from noise or instrument faults.
A subsequent experiment needs a declared geometry and clock convention, calibrated
receivers, equipment swaps, controlled noise/attenuation trials, repeated sampling,
and an independently specified physical prediction with uncertainties. A residual
unexplained by those controls is evidence to investigate, not automatic gravity
attribution. This revision implements the quantity correction and its regressions;
it does not claim to have performed that experiment.

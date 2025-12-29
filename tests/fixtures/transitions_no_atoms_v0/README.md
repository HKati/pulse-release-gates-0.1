# transitions_no_atoms_v0 (fixture)

Purpose
- Regression fixture where the transitions drift inputs exist, but contain **no actionable drift**.
- Expected output:
  - paradox_field_v0.json has **zero atoms**
  - paradox_edges_v0.jsonl has **zero edges**

Why this matters
- Confirms the pipeline is stable for the “all-green / no-drift” case.
- Ensures contracts and derived artifacts behave correctly even when the field is empty.

Inputs
- pulse_gate_drift_v0.csv: contains no gate flips (flip=0)
- pulse_metric_drift_v0.csv: contains no metric deltas (no numeric delta rows)
- pulse_overlay_drift_v0.json: contains no changed_keys (so no overlay_change atoms)
- pulse_transitions_v0.json: intentionally omitted (adapter treats it as optional)

Repro (do not commit outputs under out/**)
  mkdir -p out/no_atoms

  python scripts/paradox_field_adapter_v0.py \
    --transitions-dir tests/fixtures/transitions_no_atoms_v0 \
    --out out/no_atoms/paradox_field_v0.json

  python scripts/check_paradox_field_v0_contract.py \
    --in out/no_atoms/paradox_field_v0.json

  python scripts/export_paradox_edges_v0.py \
    --in out/no_atoms/paradox_field_v0.json \
    --out out/no_atoms/paradox_edges_v0.jsonl

  python scripts/check_paradox_edges_v0_contract.py \
    --in out/no_atoms/paradox_edges_v0.jsonl \
    --atoms out/no_atoms/paradox_field_v0.json

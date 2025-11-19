# PULSE paradox_field_v0 + epf_field_v0 – v0 case study

Status: v0, shadow-only  
Scope: how to **read** the paradox / EPF field layer in practice

This case study shows how `paradox_field_v0` and `epf_field_v0` appear in
PULSE artefacts, and how to interpret them as **fields**, not just flags.

We’ll walk through:

1. A single `ReleaseState` in `stability_map.json`  
2. How the same field shows up in `decision_output_v0.json`  
3. How it is compressed into `decision_paradox_summary_v0.json`  
4. How it appears in `paradox_history_v0.json`

All examples are synthetic, but consistent with the current v0 tools.

---

## 1. Example ReleaseState in `stability_map.json`

After running:

```bash
python PULSE_safe_pack_v0/tools/build_paradox_epf_fields_v0.py \
  --map stability_map.json

# C4.4 example: reproducible non-fixture transitions input (v0)

This directory contains a small, non-fixture transitions drift input set that reproduces a full e2e run:

transitions → paradox_field_v0.json → paradox_edges_v0.jsonl → contract checks

---

## Reproduce

mkdir -p out

python scripts/paradox_field_adapter_v0.py \
  --transitions-dir docs/examples/transitions_case_study_v0 \
  --out out/paradox_field_v0.json

python scripts/check_paradox_field_v0_contract.py \
  --in out/paradox_field_v0.json

python scripts/export_paradox_edges_v0.py \
  --in out/paradox_field_v0.json \
  --out out/paradox_edges_v0.jsonl

python scripts/check_paradox_edges_v0_contract.py \
  --in out/paradox_edges_v0.jsonl

---

## Inspect run_context (field ↔ edges)

python - <<'PY'
import json

field = json.load(open("out/paradox_field_v0.json", "r", encoding="utf-8"))
field_rc = field["paradox_field_v0"]["meta"].get("run_context")

first_edge = json.loads(open("out/paradox_edges_v0.jsonl", "r", encoding="utf-8").readline())
edge_rc = first_edge.get("run_context")

print("FIELD meta.run_context =", field_rc)
print("EDGE  run_context      =", edge_rc)
print("EQUAL?                =", field_rc == edge_rc)
PY

---

## Optional checks

check_paradox_edges_v0_acceptance_v0.py is fixture-oriented (“must contain” style) and may not apply to this docs example.

# Optional (fixture-oriented):
# python scripts/check_paradox_edges_v0_acceptance_v0.py \
#   --in out/paradox_edges_v0.jsonl

---

## Notes

Do not commit generated outputs under out/**.


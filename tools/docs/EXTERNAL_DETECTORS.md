# External Detectors & Converters → PULSE Gates

This folder adds **plug-and-play** adapters for common safety/eval tools. Each adapter ingests a tool’s export and writes a summary into `artifacts/external/*.json`. Then run:

```bash
python PULSE_safe_pack_v0/tools/augment_status.py   --status PULSE_safe_pack_v0/artifacts/status.json   --thresholds PULSE_safe_pack_v0/profiles/external_thresholds.yaml   --external_dir PULSE_safe_pack_v0/artifacts/external
```

This updates `gates.external_*_ok` and `metrics.external_*` in `status.json` and sets `gates.external_overall_ok` according to the policy in `profiles/external_thresholds.yaml` (`all` or `any`).

## Adapters

- **Llama Guard** → `tools/adapters/llamaguard_ingest.py`  
  Input JSONL: `{"input": "...", "output": "...", "llamaguard": {"label":"safe|unsafe", "categories":[...]}}`  
  → Writes `artifacts/external/llamaguard_summary.json` with `violation_rate`.

- **Prompt Guard** (prompt attack detector) → `tools/adapters/promptguard_ingest.py`  
  Input JSONL: `{"prompt":"...", "detector":{"attack":true/false, "type":"indirect|direct|..."}}`  
  → Writes `promptguard_summary.json` with `attack_detect_rate`.

- **Garak** (LLM vulnerability scanner) → `tools/adapters/garak_ingest.py`  
  Input JSON: `{"findings":[{"severity":"critical|high|...", "rule":"...", "new": true/false}, ...]}`  
  → Writes `garak_summary.json` with `new_critical` count.

- **Azure AI Risk & Safety Evaluations** → `tools/adapters/azure_eval_ingest.py`  
  Input JSONL lines with `{"category":"indirect_jailbreak","passed":true/false,...}`  
  → Writes `azure_eval_summary.json` with `failure_rates` per category.

- **Promptfoo** → `tools/adapters/promptfoo_ingest.py`  
  Input JSON: `{"results":[{"pass":true/false, ...}, ...]}`  
  → Writes `promptfoo_summary.json` with `fail_rate`.

- **DeepEval** → `tools/adapters/deepeval_ingest.py`  
  Input JSONL/JSON items: `{"metric":"...", "passed":true/false, "score":...}`  
  → Writes `deepeval_summary.json` with `fail_rate` and `fails_by_metric`.

## CI Example (augment + badges)

Add these steps after running your pack:

```yaml
- name: Augment status with external detectors
  run: |
    python PULSE_safe_pack_v0/tools/augment_status.py       --status PULSE_safe_pack_v0/artifacts/status.json       --thresholds PULSE_safe_pack_v0/profiles/external_thresholds.yaml       --external_dir PULSE_safe_pack_v0/artifacts/external

- name: Update badges
  if: always()
  run: |
    python PULSE_safe_pack_v0/tools/ci/update_badges.py       --status PULSE_safe_pack_v0/artifacts/status.json       --assets PULSE_brand_assets/badges       --out badges
```

# Optional layers & research surfaces

This page groups the parts of PULSE that are useful for diagnostics, research,
review surfaces, or platform integration, but do not define release outcomes by default.

## Read this after the core path

Core path:
- `docs/QUICKSTART_CORE_v0.md`
- `docs/STATUS_CONTRACT.md`
- `docs/status_json.md`
- `docs/RUNBOOK.md`

## Default rule

Optional layers may produce their own artifacts, summaries, or shadow checks,
but they do not change the main release outcome unless explicitly promoted into
the required gate set.

## Layer map

| Layer | Default role | Primary entrypoint | Main outputs | Normative by default? |
|---|---|---|---|---|
| OpenAI evals refusal smoke | shadow diagnostic | `.github/workflows/openai_evals_refusal_smoke_shadow.yml` | refusal smoke JSON + status artifact | No |
| Separation phase overlay | shadow diagnostic | `.github/workflows/separation_phase_overlay.yml` | `separation_phase_v0.json`, markdown summary | No |
| Theory overlay v0 | shadow diagnostic | `.github/workflows/theory_overlay_v0.yml` | overlay JSON + markdown summary | No |
| G-field / G snapshot surfaces | shadow diagnostic | G-field / snapshot shadow workflows | overlay JSONs + snapshot markdown | No |
| Relational Gain v0 | shadow diagnostic (contract-hardened) | `.github/workflows/relational_gain_shadow.yml` | `relational_gain_shadow_v0.json`, folded `meta.relational_gain_shadow` | No |
| EPF experiment / hazard | research diagnostic (run-manifest primary; summary surface also contract-hardened) | `.github/workflows/epf_experiment.yml` | `epf_shadow_run_manifest.json`, `epf_paradox_summary.json` | No |
| Parameter Golf v0 | external challenge companion | `../parameter_golf_v0/README.md` | submission evidence JSON + review receipt | No |
| Publication surfaces | opt-in platform integration | `upload_sarif.yml`, PR comments, badge write-back, Pages snapshots | GitHub-native / published surfaces | No |

## Contract-hardened shadow modules

### Relational Gain v0

**Entry point:** [`.github/workflows/relational_gain_shadow.yml`](../.github/workflows/relational_gain_shadow.yml)  
**Detailed doc:** [`shadow_relational_gain_v0.md`](shadow_relational_gain_v0.md)

Relational Gain v0 is now a **contract-hardened shadow-only** module.

Current hardening surface:

- schema:
  - `../schemas/relational_gain_shadow_v0.schema.json`
- contract checker:
  - `../PULSE_safe_pack_v0/tools/check_relational_gain_contract.py`
- canonical fixtures:
  - `../tests/fixtures/relational_gain_shadow_v0/pass.json`
  - `../tests/fixtures/relational_gain_shadow_v0/warn.json`
  - `../tests/fixtures/relational_gain_shadow_v0/fail.json`
- checker regression tests:
  - `../tests/test_check_relational_gain_contract.py`
- non-interference coverage:
  - `../tests/test_relational_gain_non_interference.py`

It remains **non-normative**.
Its artifact and folded `meta.relational_gain_shadow` summary do not change release authority unless a future policy explicitly promotes the layer.

### EPF experiment / hazard

**Entry point:** [`.github/workflows/epf_experiment.yml`](../.github/workflows/epf_experiment.yml)  
**Detailed doc:** [`PULSE_epf_shadow_quickstart_v0.md`](PULSE_epf_shadow_quickstart_v0.md)

The broader EPF line remains a **research diagnostic** path.

Its current **primary** machine-registered surface is now:

- `epf_shadow_run_manifest.json`

The current `epf_paradox_summary.json` surface remains a **secondary
contract-hardened diagnostic artifact**.

Current primary hardening surface:

- schema:
  - `../schemas/epf_shadow_run_manifest_v0.schema.json`
- contract checker:
  - `../PULSE_safe_pack_v0/tools/check_epf_shadow_run_manifest_contract.py`
- canonical fixtures:
  - `../tests/fixtures/epf_shadow_run_manifest_v0/pass.json`
  - `../tests/fixtures/epf_shadow_run_manifest_v0/degraded.json`
  - `../tests/fixtures/epf_shadow_run_manifest_v0/stub.json`
  - `../tests/fixtures/epf_shadow_run_manifest_v0/changed_without_warn.json`
  - `../tests/fixtures/epf_shadow_run_manifest_v0/changed_exceeds_total_gates.json`
  - `../tests/fixtures/epf_shadow_run_manifest_v0/example_count_exceeds_changed.json`
  - `../tests/fixtures/epf_shadow_run_manifest_v0/real_zero_changed_wrong_verdict.json`
  - `../tests/fixtures/epf_shadow_run_manifest_v0/same_status_paths.json`
  - `../tests/fixtures/epf_shadow_run_manifest_v0/missing_epf_report_source_artifact.json`
  - `../tests/fixtures/epf_shadow_run_manifest_v0/invalid_overall_without_invalid_branch.json`
  - `../tests/fixtures/epf_shadow_run_manifest_v0/degraded_without_nonreal_branch.json`
- checker regression tests:
  - `../tests/test_check_epf_shadow_run_manifest_contract.py`

Current secondary summary surface:

- schema:
  - `../schemas/epf_paradox_summary_v0.schema.json`
- contract checker:
  - `../PULSE_safe_pack_v0/tools/check_epf_paradox_summary_contract.py`
- canonical fixtures:
  - `../tests/fixtures/epf_paradox_summary_v0/pass.json`
  - `../tests/fixtures/epf_paradox_summary_v0/changed_exceeds_total_gates.json`
  - `../tests/fixtures/epf_paradox_summary_v0/changed_positive_without_examples.json`
  - `../tests/fixtures/epf_paradox_summary_v0/duplicate_gate_examples.json`
  - `../tests/fixtures/epf_paradox_summary_v0/example_without_difference.json`
  - `../tests/fixtures/epf_paradox_summary_v0/examples_longer_than_changed.json`
  - `../tests/fixtures/epf_paradox_summary_v0/invalid_rc_string.json`
  - `../tests/fixtures/epf_paradox_summary_v0/changed_zero_with_examples.json`
- checker regression tests:
  - `../tests/test_check_epf_paradox_summary_contract.py`

Both surfaces remain **non-normative**.

They are descriptive and diagnostic only, and do not change release
authority.

## External challenge companions

### Parameter Golf v0

**Entry point:** [`../parameter_golf_v0/README.md`](../parameter_golf_v0/README.md)  
**Contract notes:** [`parameter_golf_submission_evidence_v0.md`](parameter_golf_submission_evidence_v0.md)

Parameter Golf v0 is a **shadow-only, non-normative** evidence companion.

Its purpose is to demonstrate a small machine-readable submission-evidence surface
for OpenAI Parameter Golf submissions without changing the counted submission path,
without introducing new required PULSE gates, and without turning PULSE into the
challenge itself.

Current v0 scope:

- evidence contract:
  - `../schemas/parameter_golf_submission_evidence_v0.schema.json`
- verifier:
  - `../tools/verify_parameter_golf_submission_v0.py`
- example evidence artifact:
  - `../examples/parameter_golf_submission_evidence_v0.example.json`
- review-receipt renderer:
  - `../tools/render_parameter_golf_review_receipt_v0.py`
- example review receipt:
  - `../examples/parameter_golf_submission_review_receipt_v0.example.json`
- deterministic roundtrip checker:
  - `../tools/check_parameter_golf_review_receipt_roundtrip_v0.py`

Use this layer when you need:

- a machine-readable evidence artifact,
- narrow schema / consistency verification,
- and a smaller reviewer-facing receipt derived from the same evidence.

Do not treat this layer as part of the normative PULSE release-gating path unless
a future policy explicitly promotes it into a required gate set.

## Practical rule

If you are adopting PULSE for deterministic release gating, you can safely ignore
this page on first read.

If you are extending reviewer surfaces, experiments, or publication outputs,
start here before touching the main release path.

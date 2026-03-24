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
| EPF experiment / hazard | research diagnostic | `.github/workflows/epf_experiment.yml` and EPF docs | `status_epf.json`, reports, hazard logs | No |
| Parameter Golf v0 | external challenge companion | `../parameter_golf_v0/README.md` | submission evidence JSON + review receipt | No |
| Publication surfaces | opt-in platform integration | `upload_sarif.yml`, PR comments, badge write-back, Pages snapshots | GitHub-native / published surfaces | No |

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

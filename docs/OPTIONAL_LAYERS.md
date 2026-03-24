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
| Publication surfaces | opt-in platform integration | `upload_sarif.yml`, PR comments, badge write-back, Pages snapshots | GitHub-native / published surfaces | No |

## Practical rule

If you are adopting PULSE for deterministic release gating, you can safely ignore
this page on first read.

If you are extending reviewer surfaces, experiments, or publication outputs,
start here before touching the main release path.

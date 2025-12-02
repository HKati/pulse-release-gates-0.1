# G snapshot report v0 (shadow)

Generated at: {{ generated_at_iso }}
Source run: {{ run_id }} (profile: {{ profile_name }})

> This report is **shadow-only**. It never changes CI pass/fail or release
> decisions. All signals here are diagnostic overlays on top of the
> deterministic PULSE gates.

---

## 0. Sources

Legend: `[x]` = present, `[ ]` = not found in this run.

- [{{ g_field_present_checkbox }}] G-field overlay (`g_field_v0.json`)
- [{{ g_field_stability_present_checkbox }}] G-field stability overlay (`g_field_stability_v0.json`)
- [{{ g_epf_present_checkbox }}] G-EPF overlay (`g_epf_overlay_v0.json`)
- [{{ gpt_external_present_checkbox }}] GPT external detection overlay (`gpt_external_detection_v0.json`)

---

## 1. G-field overview

**Status:** {{ g_field_status_sentence }}

- Traces covered: **{{ g_field_traces_count }}**
- Gates covered: **{{ g_field_gates_count }}**
- Global mean: **{{ g_field_global_mean }}**
- Global min / max: **{{ g_field_global_min }} / {{ g_field_global_max }}**

Top {{ g_field_top_gates_n }} gates by absolute mean:

| Gate ID            | Mean value | Std dev | Samples |
|--------------------|-----------:|--------:|--------:|
{{ g_field_top_gates_table_rows }}

<details>
<summary>Raw G-field snapshot (truncated)</summary>

```json
{{ g_field_raw_snippet_json }}
```

</details>

---

## 2. G-field stability

**Status:** {{ g_field_stability_status_sentence }}

Short interpretation:

> {{ g_field_stability_short_comment }}
>
> (e.g. “Most gates look stable across 5 runs; 2 gates show potential instability.”)

Key numbers:

- Runs aggregated: **{{ stability_runs }}**
- Gates with stable mean: **{{ stability_stable_gates_count }}**
- Gates flagged as potentially unstable: **{{ stability_unstable_gates_count }}**

Unstable gates (if any):

| Gate ID        | Runs | Mean span | Notes              |
|----------------|-----:|----------:|--------------------|
{{ stability_unstable_gates_table_rows }}

<details>
<summary>Raw stability diagnostics (exact JSON)</summary>

```json
{{ g_field_stability_raw_json }}
```

</details>

---

## 3. G-EPF overlay (shadow)

**Status:** {{ g_epf_status_sentence }}

If present, a short view over EPF panels:

- Panels: **{{ epf_panel_count }}**
- Gates covered: **{{ epf_gates_covered_count }}**
- Risk bands (shadow-only):
  - Low-risk items: **{{ epf_low_risk_count }}**
  - Medium-risk items: **{{ epf_medium_risk_count }}**
  - High-risk items: **{{ epf_high_risk_count }}**

Example EPF panel:

| Panel ID        | Gate      | Score | Risk band | Notes                     |
|-----------------|-----------|------:|-----------|---------------------------|
{{ epf_example_panel_row }}

<details>
<summary>Raw EPF overlay snippet (truncated)</summary>

```json
{{ g_epf_raw_snippet_json }}
```

</details>

If no EPF overlay was found for this run, show instead:

> No `g_epf_overlay_v0.json` overlay was found. EPF overlays are optional,
> shadow-only diagnostics and never change CI outcomes.

---

## 4. GPT external usage (shadow)

**Status:** {{ gpt_external_status_sentence }}

Summary of GPT calls in this run:

- Total GPT calls: **{{ gpt_total_calls }}**
- Internal (HPC) calls: **{{ gpt_internal_calls }}**
- External calls: **{{ gpt_external_calls }}**
- External share: **{{ gpt_external_share_percent }} %**

Top external vendors / models:

| Vendor          | Model             | Calls | Share of total |
|----------------|-------------------|------:|---------------:|
{{ gpt_top_vendors_table_rows }}

Example interpretation:

> {{ gpt_usage_short_comment }}
>
> (e.g. “~12% of all GPT calls went to external vendors; the top model is
> `vendorX/gpt-xyz` with 43 calls.”)

<details>
<summary>Raw GPT usage diagnostics (truncated)</summary>

```json
{{ gpt_external_raw_snippet_json }}
```

</details>

---

## 5. How to read this report

- This report is **CI-neutral**: it does **not** participate in release gating.
- All metrics are derived from the overlays listed in the *Sources* section.
- When in doubt:
  - treat G-field numbers as *diagnostic context* for the existing gates,
  - treat stability flags as *hints* about robustness, not as hard pass/fail,
  - treat EPF and GPT usage as *shadow overlays* for governance dashboards.

For an end-to-end view of how these overlays are produced, see
`docs/g_shadow_pipeline.md`.

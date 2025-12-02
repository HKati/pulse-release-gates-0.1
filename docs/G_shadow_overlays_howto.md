docs/G_shadow_overlays_howto.md
--------------------------------

# G-shadow overlays – how to add a new overlay

This document explains how to plug a new shadow-only overlay into the
G-shadow pipeline, alongside the existing overlays:

- `g_field_v0.json`
- `g_field_stability_v0.json`
- `g_epf_overlay_v0.json`
- `gpt_external_detection_v0.json`

The goal is to keep overlays **CI-neutral** (shadow-only) while giving
the snapshot report and dashboards richer context.

---

## 1. What is a G-shadow overlay?

In this repo, a G-shadow overlay is:

- a **JSON artefact** produced from existing logs / status files,
- validated against a **JSON Schema** under `schemas/`,
- picked up by the **Overlay schema validation (shadow)** workflow,
- optionally summarised in the **G snapshot report (shadow)**.

Overlays **never** change PULSE gates or `status.json`. They are
diagnostic layers on top of the deterministic gates.

---

## 2. Pipeline recap

For context, the G-shadow pipeline is:

1. **Inputs**  
   - HPC snapshots (e.g. `hpc/g_snapshots.jsonl`)  
   - EPF experiment artefacts (e.g. `status_baseline.json`,
     `status_epf.json`, `epf_paradox_summary.json`)  
   - Logs for GPT usage (e.g. `logs/model_invocations.jsonl`)

2. **Overlay generation**  
   - `scripts/g_child_field_adapter.py` → `g_field_v0.json`  
   - `scripts/build_g_epf_overlay_v0.py` → `g_epf_overlay_v0.json`  
   - analogous scripts for GPT usage, etc.

3. **Schema validation (shadow)**  
   - `schemas/*.schema.json`  
   - `scripts/validate_overlays.py`  
   - GitHub Actions: **Overlay schema validation (shadow)**

4. **Snapshot report (shadow)**  
   - Reads existing overlays (if present) and renders
     `PULSE_safe_pack_v0/artifacts/g_snapshot_report_v0.md`.

5. **Dashboards / governance (optional)**  
   - Downstream tools can read the overlays + snapshot report and use
     them for governance, drift, or review workflows.

---

## 3. Checklist for a new overlay

When adding a new overlay (e.g. `g_new_overlay_v0.json`), follow this
checklist:

1. **Choose an overlay ID and file names**
2. **Define the JSON shape and schema**
3. **Write a builder script**
4. **Wire it into overlay validation**
5. **(Optionally) extend the G snapshot report**
6. **Update docs / README if it’s a “first-class” overlay**

Each step is described below.

---

## 4. Step 1 – Choose overlay ID and file names

Pick a stable ID and file names that follow the existing conventions:

- Overlay ID:  
  - e.g. `g_new_overlay_v0`
- File name (JSON):  
  - `g_new_overlay_v0.json` (repo root or pack artefacts)
- Schema file:  
  - `schemas/g_new_overlay_v0.schema.json`

If the overlay is clearly tied to a particular domain, you can reflect
that in the name (e.g. `g_topology_overlay_v0`, `g_usage_overlay_v0`).

---

## 5. Step 2 – Define JSON shape and schema

Use the existing overlays as a template. The general pattern is:

- top-level **v0 contract**:
  - `version` (string)
  - `created_at` (ISO datetime)
  - `source` (string)
- overlay‑specific content:
  - `meta` – extra metadata, internal to the overlay
  - `summary` – short counters / flags
  - main payload: e.g. `panels`, `items`, or a `data` block
  - optional `diagnostics` – free‑form debug info

Example (conceptual):

```json
{
  "version": "g_new_overlay_v0-auto",
  "created_at": "2025-12-02T13:37:00Z",
  "source": "g_new_overlay_builder",

  "meta": { },
  "summary": { },
  "items": [ ],
  "diagnostics": { }
}
```

The schema should:

- **require** the legacy v0 contract fields you care about
  (usually `version`, `created_at`, `source`, plus the main payload),
- set `additionalProperties: false` at the top level,
- keep most nested fields **optional** and use
  `additionalProperties: true` for extensibility.

For example, `g_epf_overlay_v0` keeps top-level v0 fields while
allowing `meta` and `summary` as optional objects.

---

## 6. Step 3 – Write a builder script

Place builder scripts under `scripts/`. For example:

- `scripts/build_g_epf_overlay_v0.py`
- `scripts/g_child_field_adapter.py`

When you add a new overlay, follow the same pattern:

- Read **existing artefacts** (status, logs, etc.).
- Build a Python dict that matches your JSON shape.
- Write it out as `<overlay_name>.json`.

Example skeleton (conceptual):

```python
#!/usr/bin/env python
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "g_new_overlay_v0.json"

def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def main():
    # 1) Read inputs (status/logs/…)
    # input_data = ...

    # 2) Build overlay structure
    overlay = {
        "version": "g_new_overlay_v0-auto",
        "created_at": now_iso(),
        "source": "g_new_overlay_builder",
        "meta": { },
        "summary": { },
        "items": [ ],
        "diagnostics": { },
    }

    # 3) Write JSON
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as f:
        json.dump(overlay, f, indent=2, sort_keys=True)

if __name__ == "__main__":
    main()
```

The EPF builder `scripts/build_g_epf_overlay_v0.py` is a concrete,
working example of this pattern.

---

## 7. Step 4 – Wire into overlay validation

The `Overlay schema validation (shadow)` workflow uses
`scripts/validate_overlays.py` to:

- discover known overlays,
- validate them against their schemas.

To add your overlay:

1. Add a `schemas/g_new_overlay_v0.schema.json`.
2. Update `scripts/validate_overlays.py` to:
   - include `g_new_overlay_v0` in the list of known overlays,
   - locate the JSON file (repo root or pack artefacts),
   - validate it against the schema.

The convention is:

- **If the JSON file is missing** → log `INFO` and skip.
- **If the JSON file is present but invalid** → make the workflow **red**.

This keeps overlays optional but ensures that once they exist, they
are schema-safe.

---

## 8. Step 5 – Extend the G snapshot report (optional but recommended)

If the overlay is meant to be human-facing, integrate it into

- `PULSE_safe_pack_v0/artifacts/g_snapshot_report_v0.md`
- via the **G snapshot report (shadow)** workflow.

Pattern (as used for existing overlays):

- Add a presence line to the `Sources` section:
  - e.g. `- [x] G-new overlay (g_new_overlay_v0.json)`
- Add a dedicated section:
  - short status sentence (1–2 lines),
  - small table or bullet list with key numbers,
  - optional `<details>` block with raw JSON snippet (truncated).

The EPF section is a good template:

- uses the `summary` block for quick numbers,
- surfaces paradox / EPF band gates,
- keeps raw JSON as an expandable diagnostics block.

---

## 9. Step 6 – Update docs / README

If your overlay is part of the stable G-shadow story, update:

- `README.md`
  - mention the overlay under **G-field & shadow overlays** or
    the G snapshot report section,
- `docs/g_shadow_pipeline.md`
  - show where in the pipeline the overlay appears,
- optionally, the **Roadmap (shadow layer)** section if this was a
  planned milestone.

If the overlay is experimental or domain-specific, you can still
document it in a separate `docs/` file and keep it out of the top-level
README until it stabilises.

---

## 10. Examples

Current overlays and builder patterns:

- **G-field overlay** (`g_field_v0.json`)  
  - builder: `scripts/g_child_field_adapter.py`  
  - schema: `schemas/g_field_v0.schema.json`  
  - snapshot: basic stats in the G snapshot report.

- **G-EPF overlay** (`g_epf_overlay_v0.json`)  
  - builder: `scripts/build_g_epf_overlay_v0.py`  
  - schema: `schemas/g_epf_overlay_v0.schema.json`  
  - snapshot: EPF panels and paradox candidates in the G snapshot report.

- **GPT external detection overlay** (`gpt_external_detection_v0.json`)  
  - builder: a logs-based script (similar pattern: read logs, aggregate,
    write overlay)  
  - schema: `schemas/gpt_external_detection_v0.schema.json`  
  - snapshot: total calls, internal vs external, top vendors/models.

Use these as inspiration and keep new overlays **shadow-only** and
safe to ship by default.

---

Git szövegek
------------

### Commit message

```text
docs(g-shadow): add howto for G-shadow overlays
```

### Commit body (opcionális)

```text
docs(g-shadow): add howto for G-shadow overlays

Add docs/G_shadow_overlays_howto.md, a step-by-step guide for adding
new shadow-only overlays to the G-shadow layer:

- explains the pipeline (inputs → overlays → schema validation → snapshot),
- defines a checklist for new overlays (ID, schema, builder, validation, docs),
- uses existing overlays (G-field, G-EPF, GPT usage) as examples.

Docs-only change; no impact on gates or CI behaviour.
```

### PR cím

```text
docs(g-shadow): add howto for G-shadow overlays
```

### PR leírás

```markdown
## Summary

Document how to add new G-shadow overlays so that future overlays can
follow a consistent pattern and integrate cleanly with the existing
schema validation and snapshot report.

## Changes

- Add `docs/G_shadow_overlays_howto.md` which:
  - describes what a G-shadow overlay is and how it flows through the
    pipeline,
  - provides a concrete checklist for new overlays (ID, schema, builder,
    validation, snapshot, docs),
  - shows how existing overlays (G-field, G-EPF, GPT usage) implement
    the same pattern.

## Motivation

We now have multiple overlays (G-field, G-EPF, GPT external detection)
and supporting tooling (builder scripts, schema validation, snapshot
report), but the pattern lived mostly in PRs and ad-hoc notes. This doc
captures the conventions in one place, making it easier to:

- add new overlays without breaking schemas or CI,
- onboard contributors to the G-shadow layer,
- keep the shadow layer bounded and intentionally CI-neutral.

## Testing

- Docs-only change.
- No code, schema, or workflow updates.
```

### Squash & merge üzenet

```text
docs(g-shadow): add howto for G-shadow overlays

Add docs/G_shadow_overlays_howto.md as a step-by-step guide for adding
new G-shadow overlays, based on the existing G-field, G-EPF and GPT
usage overlays. Docs-only.
```

# Profiles and gate policies

This directory contains **example profiles and policy variants** for PULSE.

The canonical policy used by the main PULSE CI lives in:

- `PULSE_safe_pack_v0/pulse_policy.yml`

That file is the **source of truth** for release gating in this repository.
The profiles here are intended for:

- experimentation,
- documentation and comparison of different trade-offs,
- downstream projects that want to start from a known template.

## Files

- `external_thresholds.yaml`  
  Example thresholds for external detectors and risk margins. The pack may
  ship its own minimal version under `PULSE_safe_pack_v0/profiles/`; this
  copy is for full-length examples and experimentation.

- `balanced-prod.yaml`  
  A more "balanced" profile intended as a starting point for production-like
  setups. It is **not** automatically used by CI; adopt it explicitly if you
  want this behaviour.

## Notes

- The main PULSE CI references `PULSE_safe_pack_v0/pulse_policy.yml`.
- Changes here do **not** automatically affect CI unless you wire them into
  that policy (or into your own workflows).
- When publishing snapshots (e.g. via Zenodo/DOI), both the pack policy and
  these example profiles can be included to document the available options.

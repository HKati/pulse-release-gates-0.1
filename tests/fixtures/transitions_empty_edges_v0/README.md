# transitions_empty_edges_v0

Regression fixture for the paradox layer.

Goal:
- field meta.run_context is present (stable fingerprint),
- exporter emits **zero** paradox edges (no tension atoms),
- edges contract must still pass in `--atoms` mode.

Inputs are intentionally "no-tension":
- gate drift: no flips
- metric drift: deltas below warn/crit thresholds
- overlay drift: empty

Expected outcome:
- paradox_field_v0.json contains meta.run_context
- paradox_edges_v0.jsonl is empty (0 lines / 0 edges)

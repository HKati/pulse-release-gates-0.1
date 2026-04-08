# Relational Gain v0 — Initial Scope

## Decision

This first version is:

- shadow-only
- non-normative
- not emitted under `gates.*`
- not added to policy yet
- not added to the registry yet
- not added to `core_required` or `required` yet

## Goal

Provide a deterministic, fail-closed checker that:

- evaluates edge gains
- evaluates cycle gains
- writes a separate artifact
- can optionally fold a short, non-normative shadow summary under `meta.*`

## Files to create in the first round

1. `docs/shadow_relational_gain_v0.md`
2. `PULSE_safe_pack_v0/tools/check_relational_gain.py`
3. `tests/test_check_relational_gain.py`
4. `tests/fixtures/relational_gain_v0/pass.json`
5. `tests/fixtures/relational_gain_v0/warn.json`
6. `tests/fixtures/relational_gain_v0/fail_edge.json`
7. `tests/fixtures/relational_gain_v0/fail_cycle.json`

## Output artifact

The checker’s primary output should be a separate artifact:

`PULSE_safe_pack_v0/artifacts/relational_gain_shadow_v0.json`

## Optional status fold-in

If desired, a short descriptive fold-in may be added here:

`status["meta"]["relational_gain_shadow"]`

Recommended minimal shape:

```json
{
  "meta": {
    "relational_gain_shadow": {
      "verdict": "PASS",
      "max_edge_gain": 0.83,
      "max_cycle_gain": 0.91,
      "warn_threshold": 0.95,
      "checked_edges": 18,
      "checked_cycles": 4,
      "artifact": {
        "path": "PULSE_safe_pack_v0/artifacts/relational_gain_shadow_v0.json",
        "sha256": "..."
      }
    }
  }
}

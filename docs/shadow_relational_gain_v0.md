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

## Shadow artifact contract (v0)

The shadow artifact must be self-contained and audit-friendly.

Recommended artifact path:

`PULSE_safe_pack_v0/artifacts/relational_gain_shadow_v0.json`

Recommended minimal artifact shape:

```json
{
  "checker_version": "relational_gain_v0",
  "verdict": "PASS",
  "input": {
    "path": "PULSE_safe_pack_v0/artifacts/relational_gain_input_v0.json"
  },
  "metrics": {
    "checked_edges": 18,
    "checked_cycles": 4,
    "max_edge_gain": 0.83,
    "max_cycle_gain": 0.91,
    "warn_threshold": 0.95,
    "offending_edges": [],
    "offending_cycles": [],
    "near_boundary_edges": [],
    "near_boundary_cycles": []
  }
}
```

Notes:

- the artifact should be complete enough to stand on its own
- the artifact is the audit surface
- later fold-ins may stay shorter because the artifact remains the full record
- if richer edge/cycle identifiers become available later, the offending/near-boundary arrays may evolve from raw numbers into structured objects

## Optional meta fold-in

The optional `status.json` fold-in must remain short and descriptive.

Recommended location:

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
```

Rules:

- keep this fold-in short
- do not move detailed diagnostics here
- do not place this under `gates.*`
- absence is neutral
- presence is descriptive only

## Checker semantics (v0)

This checker is Shadow-only.

Decision semantics:

- `FAIL` -> checker-level fail-closed
- `WARN` -> shadow warning only
- `PASS` -> shadow success only

Important:

- `WARN` must not participate in gate semantics in v0
- `PASS` / `WARN` / `FAIL` are checker verdicts, not policy-level release decisions
- no normative gate is introduced in this round

## Checker CLI contract (v0)

Recommended CLI:

```bash
python check_relational_gain.py --input INPUT_JSON
python check_relational_gain.py --input INPUT_JSON --out OUTPUT_JSON
python check_relational_gain.py --input INPUT_JSON --warn-threshold 0.95
python check_relational_gain.py --input INPUT_JSON --require-data
```

Recommended arguments:

- `--input` : required input JSON
- `--out` : optional output artifact path
- `--warn-threshold` : optional override
- `--edge-key` : optional key name override, default `edge_gains`
- `--cycle-key` : optional key name override, default `cycle_gains`
- `--require-data` : fail if neither edge nor cycle data is present

Recommended exit codes:

- `0` -> `PASS`
- `0` -> `WARN`
- `1` -> `FAIL`
- `2` -> invalid input / parse error / schema error / runtime read-write error

## Initial fixtures (v0)

The first-round fixture set should stay exactly this small:

- `tests/fixtures/relational_gain_v0/pass.json`
- `tests/fixtures/relational_gain_v0/warn.json`
- `tests/fixtures/relational_gain_v0/fail_edge.json`
- `tests/fixtures/relational_gain_v0/fail_cycle.json`

Recommended contents:

### `pass.json`

```json
{
  "edge_gains": [0.42, 0.71, 0.88],
  "cycle_gains": [0.63, 0.79],
  "metrics": {
    "relational_gain_warn_threshold": 0.95
  }
}
```

Expected result:

- `verdict`: `PASS`
- exit code: `0`

### `warn.json`

```json
{
  "edge_gains": [0.42, 0.95, 0.97],
  "cycle_gains": [0.73, 0.91],
  "metrics": {
    "relational_gain_warn_threshold": 0.95
  }
}
```

Expected result:

- `verdict`: `WARN`
- exit code: `0`

### `fail_edge.json`

```json
{
  "edge_gains": [0.42, 1.08],
  "cycle_gains": [0.73, 0.91],
  "metrics": {
    "relational_gain_warn_threshold": 0.95
  }
}
```

Expected result:

- `verdict`: `FAIL`
- exit code: `1`

### `fail_cycle.json`

```json
{
  "edge_gains": [0.42, 0.88],
  "cycle_gains": [0.73, 1.04],
  "metrics": {
    "relational_gain_warn_threshold": 0.95
  }
}
```

Expected result:

- `verdict`: `FAIL`
- exit code: `1`

## Test expectations (v0)

Minimum expected tests:

- `pass` fixture -> exit `0`, verdict `PASS`
- `warn` fixture -> exit `0`, verdict `WARN`
- `fail_edge` fixture -> exit `1`, verdict `FAIL`
- `fail_cycle` fixture -> exit `1`, verdict `FAIL`

Optional later negative test:

- malformed input -> exit `2`


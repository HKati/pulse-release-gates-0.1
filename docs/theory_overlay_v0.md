# Theory Overlay v0 (shadow) — Record-horizon (G/tidality) diagnostics

This repository contains a **shadow** (CI-neutral) theory overlay that computes an ACK-free
record-horizon diagnostic signal based on local/portable inputs.

The overlay is designed to be:
- **Contract-validated** (fail-closed on malformed artifacts)
- **Deterministic & stdlib-only**
- **CI-neutral in v0** (workflow should not be blocked by theory failures; status is encoded in the overlay)

---

## Where it runs

Workflow:
- `.github/workflows/theory_overlay_v0.yml`

It performs (in order):
1) Contract check (pre) on committed overlay JSON
2) Generate overlay metrics (record horizon)
3) Contract check (post) on generated overlay JSON
4) Render markdown summary
5) Publish markdown to GitHub Actions job summary
6) Run golden fixture tests for generator semantics

---

## Key artifacts

Overlay (output):
- `PULSE_safe_pack_v0/artifacts/theory_overlay_v0.json`
- `PULSE_safe_pack_v0/artifacts/theory_overlay_v0.md`

Inputs bundle (optional, recommended):
- `PULSE_safe_pack_v0/artifacts/theory_overlay_inputs_v0.json`

---

## How to run locally

### Generate (in-place)

```bash
python scripts/generate_theory_overlay_v0.py \
  --in  PULSE_safe_pack_v0/artifacts/theory_overlay_v0.json \
  --out PULSE_safe_pack_v0/artifacts/theory_overlay_v0.json \
  --bundle PULSE_safe_pack_v0/artifacts/theory_overlay_inputs_v0.json \
  --require-inputs
```

### Contract check

```bash
python scripts/check_theory_overlay_v0_contract.py \
  --in PULSE_safe_pack_v0/artifacts/theory_overlay_v0.json
```

### Render markdown

```bash
python scripts/render_theory_overlay_v0_md.py \
  --in  PULSE_safe_pack_v0/artifacts/theory_overlay_v0.json \
  --out PULSE_safe_pack_v0/artifacts/theory_overlay_v0.md
```

### Run golden fixtures (generator semantics)

```bash
python scripts/test_theory_overlay_v0_generator_fixtures.py
```

---

## Input bundle format

File:
`PULSE_safe_pack_v0/artifacts/theory_overlay_inputs_v0.json`

### Minimal required inputs

- `u` (dimensionless)
- `T` or `lnT` (tidality; `T` must be > 0)
- `v_L` (must be > 0)
- `lambda_eff` (must be > 0)

### Minimal required params

- `eta` (> 0)
- `chi` (>= 0)
- `ell_0` (> 0)
- `M_infty` (> 0)
- `b0_A_bits` (> 0)
- `epsilon_budget` in [0, 1)
- `rho_coding` in [0, 1)

### Optional (defaults provided if omitted)

- `c_m_per_s` (default: 299792458)
- `G_m3_per_kg_s2` (default: 6.6743e-11)

---

## Output structure (important fields)

### Shadow gate status

- `gates_shadow.g_record_horizon_v0.status ∈ { PASS, FAIL, MISSING }`
- `gates_shadow.g_record_horizon_v0.reason` — human-readable detail

Special reason prefixes:
- `FAIL_CLOSED:` missing/invalid inputs or malformed thresholds
- `RECORD_HORIZON:` hard horizon condition (`B̃ < 1`)
- `WARN:` near-horizon advisory state

---

### Computed metrics

- `evidence.record_horizon_v0.computed.Btilde_core_units` (B̃)
- `evidence.record_horizon_v0.computed.x_ln_Btilde` (ln(B̃))
- `evidence.record_horizon_v0.computed.feedback_F` (feedback factor)

Optional (when history supports it):
- `Xi`
- `m_slope`
- `delta_lnT_to_*` forecast fields

---

## Semantics

### Record-horizon (hard FAIL cutoff)

FAIL is emitted only when:

```
B̃ < 1
```

This is the hard horizon definition and must not drift with tuned visual thresholds.

---

### Zones (advisory / visualization)

Thresholds live under:

```
evidence.record_horizon_v0.thresholds
```

Typical defaults:

- `Btilde_green = 100`
- `Btilde_yellow = 10`
- `Btilde_red` is advisory only
- POST is still defined strictly by `B̃ < 1`

Zone mapping:

- GREEN if `B̃ >= Btilde_green`
- YELLOW if `B̃ >= Btilde_yellow` and `< Btilde_green`
- RED if `B̃ >= 1` and `< Btilde_yellow`
- POST if `B̃ < 1`

---

## Mode (SHARP/SLOW)

Mode defaults to an F-only fallback if `Xi` is unavailable.

If `Xi` is computed from monotonic forward history,
`SHARP` can also be triggered by:

```
Xi >= sharp_Xi
```

---

## CI-neutral v0 behavior

The generator exits `0` even when it emits `FAIL` / `FAIL_CLOSED`
in the overlay JSON.

The workflow remains shadow:
failures are reported via gates/evidence and the job summary,
not by blocking merges.

---

## Roadmap (next)

- History ingestion for stable `Xi` / `m_slope` / `ΔlnT` forecasts across runs
- Promotion path:
  shadow overlay → shadow gate profile → (optional) hard gate

---

## Related theory/protocol specs (probe)

These documents are workshop/probe specifications. They do not change normative PULSE release-gate semantics.

- [Time as Consequence (workshop paper, v0.1)](time_as_consequence_v0_1.md)
- [Time as Consequence (one-pager, v0.1)](time_as_consequence_one_pager_v0_1.md)
- [Gravity as a Record Test (appendix, v0.1)](gravity_record_protocol_appendix_v0_1.md)

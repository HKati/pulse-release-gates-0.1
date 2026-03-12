# The PULSE status artefact (`status.json`)

> Central machine-readable artefact for one PULSE run.

PULSE safe-packs produce a single machine-readable status artefact for each run:

```text
PULSE_safe_pack_v0/artifacts/status.json
```

This file is the anchor for:

- CI enforcement,
- derived-signal augmentation,
- human-readable reporting,
- audit / archival / diffing.

A single `status.json` should correspond to exactly one concrete run and one release candidate / model/service configuration.

---

## 1. Source of truth

The stable public contract is defined by:

```text
schemas/status/status_v1.schema.json
```

That schema currently requires the top-level fields:

- `version`
- `created_utc`
- `metrics`
- `gates`

and it requires `metrics.run_mode` to be one of:

- `demo`
- `core`
- `prod`

For the concise public contract, see [STATUS_CONTRACT.md](STATUS_CONTRACT.md).  
This page is the fuller walkthrough.

Local validation helper:

```bash
python tools/validate_status_schema.py \
  --schema schemas/status/status_v1.schema.json \
  --status PULSE_safe_pack_v0/artifacts/status.json
```

---

## 2. Artefact lifecycle

Typical flow:

1. `PULSE_safe_pack_v0/tools/run_all.py` writes the baseline `status.json`.
2. `PULSE_safe_pack_v0/tools/augment_status.py` may enrich that file with:
   - refusal-delta metrics and gate,
   - external detector summaries,
   - convenience mirror fields,
   - optional shadow-only fold-ins under `meta.*`.
3. `PULSE_safe_pack_v0/tools/check_gates.py` enforces the required gate set on the final `status.json`.
4. Renderers such as the Quality Ledger read the same final artefact.

If your workflow also keeps a `status_baseline.json`, treat it as an intermediate artefact.  
The final enforcement input is still the final `status.json`.

---

## 3. High-level shape

A typical layout looks like this:

```json
{
  "version": "1.0.0-core",
  "created_utc": "2026-02-17T12:34:56Z",
  "metrics": {
    "run_mode": "core",
    "RDSI": 0.92,
    "git_sha": "abcdef1234...",
    "run_key": "GITHUB_RUN_ID=...|GITHUB_RUN_NUMBER=...",
    "gate_policy_path": "pulse_gate_policy_v0.yml",
    "gate_policy_sha256": "..."
  },
  "gates": {
    "q1_grounded_ok": true,
    "q4_slo_ok": true,
    "refusal_delta_pass": true,
    "external_all_pass": true,
    "external_summaries_present": false
  },
  "external": {
    "all_pass": true,
    "summaries_present": false,
    "summary_count": 0,
    "metrics": []
  },
  "meta": {
    "q1_reference_shadow": {
      "pass": true,
      "grounded_rate": 0.94,
      "wilson_lower_bound": 0.90,
      "n_eligible": 120,
      "threshold": 0.90,
      "summary_artifact": {
        "path": "out/q1/reference_summary.json",
        "sha256": "..."
      }
    }
  },
  "refusal_delta_pass": true,
  "external_all_pass": true,
  "external_summaries_present": false
}
```

Interpretation:

- `metrics` describe what was measured.
- `gates` describe the boolean decisions derived from those signals.
- top-level mirror fields are optional convenience copies for simple consumers.
- `external` is a structured home for external-detector evidence.
- `meta.*` is a good home for optional diagnostic / shadow fold-ins that improve visibility without changing release semantics.

---

## 4. Required stable fields

### `version`

A non-empty string describing the status contract / producer version.

### `created_utc`

A non-empty timestamp string indicating when the artefact was created.

### `metrics`

A JSON object containing measured signals and provenance hints.

At minimum, it must contain:

- `metrics.run_mode`

### `gates`

A JSON object mapping gate ids to booleans.  
This is the normative home for release-relevant gate outcomes.

---

## 5. Run modes

`metrics.run_mode` is currently one of:

- `demo`
- `core`
- `prod`

The safe-pack entrypoint `run_all.py` selects the mode via:

- CLI: `--mode demo|core|prod`
- or environment: `PULSE_RUN_MODE`

Treat `run_mode` as important provenance: it tells consumers whether they are looking at a demo-style run, a minimal Core run, or a production-style run.

---

## 6. `metrics`: measured signals

`metrics` is intentionally additive.

It can contain many fields beyond the required `run_mode`, for example:

### Provenance / reproducibility hints

- `metrics.git_sha`
- `metrics.run_key`
- `metrics.gate_policy_path`
- `metrics.gate_policy_sha256`

### Stability / release signals

- `metrics.RDSI`
- hazard / EPF / overlay-derived numeric signals when present

### Refusal-delta fields

When refusal-delta augmentation is present, examples include:

- `metrics.refusal_delta_n`
- `metrics.refusal_delta`
- `metrics.refusal_delta_ci_low`
- `metrics.refusal_delta_ci_high`
- `metrics.refusal_policy`
- `metrics.refusal_delta_min`
- `metrics.refusal_delta_strict`
- `metrics.refusal_p_mcnemar`
- `metrics.refusal_pass_min`
- `metrics.refusal_pass_strict`

### External-detector flat copies

Depending on configured summaries, examples may include:

- `metrics.llamaguard_violation_rate`
- `metrics.promptguard_attack_detect_rate`
- `metrics.garak_new_critical`
- `metrics.azure_indirect_jailbreak_rate`
- `metrics.promptfoo_fail_rate`
- `metrics.deepeval_fail_rate`

Not every run will contain every metric.

Consumers should tolerate additive growth in `metrics`.

---

## 7. `gates`: normative release decisions

`gates` is the normative map of release decisions.

Examples:

- `gates.q1_grounded_ok`
- `gates.q2_consistency_ok`
- `gates.q3_fairness_ok`
- `gates.q4_slo_ok`
- `gates.refusal_delta_pass`
- `gates.external_all_pass`
- `gates.external_summaries_present`

### Strict PASS semantics

For enforcement, PASS is strict:

- a gate PASSES only if its value is the literal boolean `true`
- `false`, `null`, missing values, strings, and numbers are **not** PASS
- missing required gates fail closed

That is why machine consumers should always read gate outcomes from `status["gates"]` first.

---

## 8. Top-level mirrors

Some producers also write convenience mirror fields at top level, for example:

```json
status["refusal_delta_pass"]
status["external_all_pass"]
status["external_summaries_present"]
```

These mirrors can make simple CLI queries easier, but they are secondary.

Recommended rule:

1. read `status["gates"][...]` first,
2. use top-level mirrors only as optional convenience fields.

---

## 9. Optional shadow fold-ins (`meta.*`)

`meta` is a good home for optional, additive, non-normative visibility blocks.

These blocks allow producers to copy a compact summary of a diagnostic / shadow artefact
into the final `status.json` so that renderers and reviewers can see it in one place
without turning it into a required gate.

### Recommended Q1 shadow location

```text
status["meta"]["q1_reference_shadow"]
```

### Recommended shape

```json
{
  "meta": {
    "q1_reference_shadow": {
      "pass": true,
      "grounded_rate": 0.94,
      "wilson_lower_bound": 0.90,
      "n_eligible": 120,
      "threshold": 0.90,
      "summary_artifact": {
        "path": "out/q1/reference_summary.json",
        "sha256": "..."
      }
    }
  }
}
```

### Meaning of the fields

- `pass` — copied summary-level PASS / FAIL from the source artefact
- `grounded_rate` — copied grounded rate from the source artefact
- `wilson_lower_bound` — copied lower confidence bound from the source artefact
- `n_eligible` — copied eligible sample count from the source artefact
- `threshold` — copied threshold from the source artefact; descriptive only
- `summary_artifact.path` — path of the source summary artefact
- `summary_artifact.sha256` — SHA-256 of the raw file bytes of the source summary artefact

### Rules

1. **All-or-nothing fold-in**  
   If the source artefact is missing, invalid, or not parseable, omit the whole block.

2. **Source fidelity**  
   The block is a copy / mapping of selected source-summary fields.  
   It is not a second computation path and must not introduce new release semantics.

3. **Normative isolation**  
   `meta.q1_reference_shadow` must not be used as a replacement for `gates.*`
   and must not change required-gate enforcement.

4. **Absence is neutral**  
   If the block is absent, that does not itself imply PASS or FAIL.

5. **Renderer discipline**  
   Human-readable surfaces may display this block, but they must not:
   - recompute it,
   - infer missing values as PASS,
   - derive a different overall release decision from it,
   - implicitly promote it into policy.

### Non-goals

- adding a new required gate
- writing under `gates.*`
- changing `check_gates.py`
- changing release policy
- changing overall decision semantics

---

## 10. External detector section (`external`)

When external summaries are folded in, `augment_status.py` maintains a structured `external` section.

Typical shape:

```json
{
  "external": {
    "all_pass": false,
    "summaries_present": true,
    "summary_count": 2,
    "metrics": [
      {
        "name": "promptguard_attack_detect_rate",
        "value": 0.20,
        "threshold": 0.10,
        "pass": false
      }
    ]
  }
}
```

### Key fields

- `external.metrics` — list of per-detector result objects
- `external.all_pass` — aggregate external result
- `external.summaries_present` — whether any external summary files were found
- `external.summary_count` — how many matching summary files were folded in

Each detector row should include at least:

- `name`
- `pass`

and may also include:

- `value`
- `threshold`
- `parse_error`

### Important nuance: evidence presence vs aggregate pass

Do **not** interpret `external_all_pass == true` as proof that external evidence was actually present.

Current augmentation behavior distinguishes two questions:

1. **Were any external summaries present?**
   - `external.summaries_present`
   - `gates.external_summaries_present`
   - optional mirror: `external_summaries_present`

2. **Did the folded external evidence pass overall?**
   - `external.all_pass`
   - `gates.external_all_pass`
   - optional mirror: `external_all_pass`

If no external summary files are present, current augmentation still sets the aggregate external result to PASS by default, while separately surfacing that summary presence is false.

So if your workflow cares about *evidence existence*, check `external_summaries_present` (or its gate form), not just `external_all_pass`.

---

## 11. Relationship to the main tools

### `run_all.py`

- writes the baseline artefact,
- populates core metrics and gates,
- creates the report artefacts used by downstream tooling.

### `augment_status.py`

- reads the baseline `status.json`,
- folds in refusal-delta and external detector summaries,
- may add optional shadow-only blocks under `meta.*`,
- writes derived fields back into the same file.

### `validate_status_schema.py`

- validates a status artefact against the JSON Schema,
- fails closed on invalid JSON or schema mismatch.

### `check_gates.py`

- reads the final `status.json`,
- enforces the required gate ids passed by policy / workflow,
- exits non-zero if required gates are missing or not literal `true`.

### Human-readable renderers

Tools such as the Quality Ledger read `metrics`, `gates`, and related sections from the final artefact and should remain pure readers / renderers.

They may surface optional shadow blocks such as `meta.q1_reference_shadow`, but they must not redefine release semantics or silently upgrade unknown / missing evidence into PASS.

---

## 12. Consumer guidance

Recommended consumer rules:

1. **Validate first** if machine correctness matters.
2. **Read `gates.*` first** for release decisions.
3. **Use `metrics.*` and `meta.*` for explanation and drill-down**, not as a replacement for gate outcomes.
4. **Check evidence-presence fields explicitly** when evidence existence matters:
   - `external.summaries_present`
   - `gates.external_summaries_present`
5. **Treat optional shadow fold-ins as descriptive only** unless a future policy explicitly promotes them.
6. **Use the final augmented `status.json`** for release reasoning, not an intermediate baseline file.
7. **Treat additive fields as normal**: new metrics and optional sections may appear over time without breaking the contract.

Because `status.json` is plain JSON, it is well-suited for:

- archival,
- reproducibility,
- audit review,
- run-to-run diffing,
- post-incident analysis.

---

## 13. Contract evolution

The public compatibility boundary is the schema:

```text
schemas/status/status_v1.schema.json
```

If stable semantics change, update the relevant contract docs and changelog in the same change set.

If any optional shadow fold-in is later promoted into normative gating, document that promotion as a separate policy / contract change rather than silently reinterpreting an existing descriptive field.

See also:

- [STATUS_CONTRACT.md](STATUS_CONTRACT.md)
- [quality_ledger.md](quality_ledger.md)
- [refusal_delta_gate.md](refusal_delta_gate.md)
- [RUNBOOK.md](RUNBOOK.md)

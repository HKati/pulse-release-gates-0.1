# Shadow Contract Program v0

> Repo-level contract program for non-normative shadow layers.
>
> This page freezes the boundary between deterministic release authority and shadow / diagnostic layers.
> It also defines the minimum contract discipline required before a shadow layer may be trusted as a stable review surface.
>
> This page does **not** change release semantics.
>
> Normative release semantics remain defined elsewhere by the release contract, policy, and primary CI wiring.

---

## Purpose

PULSE already separates deterministic release meaning from diagnostic interpretation.

This program exists to make the **shadow side** just as disciplined as the core side.

The goal is not to give shadow layers more authority.
The goal is to make them:

- contractable,
- auditable,
- reproducible,
- explicitly degradable,
- and safe to consume as non-normative evidence.

---

## Scope

This program applies to any layer that is **non-normative by default** and does one or more of the following:

- produces a diagnostic or research artifact,
- reads deterministic run artifacts and emits a shadow interpretation,
- folds a summary into `status.json` under `meta.*`,
- claims topology, tension, boundary sensitivity, relation dynamics, paradox, connection, or stability meaning,
- exists mainly for review, explanation, comparison, or governance surfaces.

---

## Non-goals

This program does **not**:

- change `check_gates.py` release semantics,
- add or remove required gates,
- reinterpret `MISSING` / `UNKNOWN` as `PASS`,
- let a shadow layer write under `gates.*`,
- let a shadow result silently widen permissions,
- promote any layer by implication.

Promotion, if it happens later, must be explicit.

---

## Boundary rule

The deterministic release center stays fixed.

Shadow layers may:

- observe,
- summarize,
- compare,
- classify,
- explain,
- or flag tension.

They may **not**:

- replace the recorded release result,
- flip `block` into `allow`,
- turn a degraded run into a trusted one,
- or create hidden policy.

---

## Design rule

**Static structure is descriptive, not sufficient.**

System-level confidence above the decision boundary must be supported by **bounded, observable relation dynamics** over archived artifacts.

That means:

- structure may define where a layer sits,
- but relation claims must be evidenced by explicit inputs, explicit outputs, and explicit degradation behavior,
- and unevidenced dynamics must not gain authority.

This rule applies especially to topology, decision-field, paradox, EPF, relational-gain, and later connection-oriented layers.

---

## Required contract surface for every shadow layer

A shadow layer is not considered **contracted** until all items below exist.

### 1. Layer identity

Each layer must declare:

- `layer_id`
- `family`
- `default_role`
- `current_stage`
- `owner_surface` (docs / workflow / tool / renderer)

The `layer_id` must be stable across docs, artifacts, and tests.

### 2. Artifact contract

Each layer must produce one primary machine-readable artifact with:

- explicit `artifact_version`,
- creation timestamp,
- producer identifier,
- source artifact references,
- explicit `mode`,
- explicit verdict or status,
- explicit reasons,
- and an explicit degraded/absence model.

If a layer has no stable artifact, it is still research, not contracted shadow.

### 3. Schema

Each primary artifact must have a versioned JSON Schema.

Schema covers shape, types, required fields, and allowed enums.

Schema alone is not enough.

### 4. Semantic checker

Each layer must have a semantic checker that validates:

- cross-field consistency,
- allowed mode transitions,
- degraded-state validity,
- source-fidelity rules,
- fold-in eligibility,
- and checker-version compatibility where applicable.

### 5. Provenance

Each shadow artifact must identify what it was derived from.

Minimum provenance:

- source path(s) or source artifact ids,
- source hash(es) when available,
- producer version,
- relation scope,
- and whether the run was real, partial, stub, or replayed.

### 6. Degradation model

Every layer must explicitly model absence and degradation.

Minimum states to distinguish when relevant:

- `absent`
- `missing_input`
- `invalid`
- `stub`
- `partial`
- `degraded`
- `real`

No shadow consumer may treat mere presence of a file as proof of trustworthiness.

### 7. Fold-in rule

If a layer folds into `status.json`, the fold-in must be:

- optional,
- additive,
- all-or-nothing,
- non-normative,
- and removable when stale or invalid.

Recommended default location:

```text
status["meta"]["<layer_id>"]
```

Fold-ins must never create or mutate release semantics.

### 8. Consumer rule

Every layer must state how consumers may read it.

At minimum:

- renderers may display it,
- reviewers may inspect it,
- dashboards may summarize it,
- release consumers must not derive authority from it unless policy explicitly promotes it.

### 9. Non-interference proof

Each contracted shadow layer must have at least one end-to-end test proving:

- release outcome before fold-in,
- release outcome after fold-in,
- same required gate set,
- same `check_gates.py`,
- same result.

If that proof is missing, the layer is not promotion-ready.

### 10. Fixture matrix

Each layer must have fixtures for at least:

- pass / healthy case,
- warn / tension case,
- fail / invalid case,
- absent case,
- stale fold-in case when fold-in exists,
- version mismatch case,
- and duplicate / ambiguity case when the layer reads more than one source shape.

### 11. Change discipline

Any semantic change to a contracted shadow layer must update in the same change set:

- the docs,
- the schema,
- the checker,
- the fixtures,
- and the workflow contract if workflow behavior changed.

---

## Shadow status vocabulary

Use the following terms consistently.

### Contract state

- `research`
  - idea or exploratory surface
  - no stable artifact contract yet
- `shadow-contracted`
  - stable artifact + schema + checker + tests
  - still non-normative
- `advisory`
  - trusted review signal
  - still cannot change release result
- `release-candidate`
  - being evaluated for policy promotion
  - promotion criteria must already be documented
- `release-required`
  - explicitly promoted into the required gate set by policy
  - no longer shadow by default

### Run reality state

- `real`
- `partial`
- `stub`
- `degraded`
- `invalid`
- `absent`

### Consumer authority state

- `display-only`
- `review-only`
- `advisory-only`
- `policy-bound`

A layer may be highly useful while still remaining `review-only`.

---

## Promotion rule

Promotion is never implied by usefulness.

A layer may move upward only when the repository explicitly records that move.

### Promotion ladder

```text
research
  -> shadow-contracted
  -> advisory
  -> release-candidate
  -> release-required
```

### Minimum criteria by step

#### research -> shadow-contracted

Requires:

- stable `layer_id`
- primary artifact
- versioned schema
- semantic checker
- fixture matrix
- explicit degraded states
- consumer rule

#### shadow-contracted -> advisory

Requires in addition:

- repeated reproducibility across real runs
- reviewer-readable summary surface
- non-interference e2e proof
- stable provenance fields

#### advisory -> release-candidate

Requires in addition:

- explicit promotion rationale
- documented failure modes
- documented false-positive / false-negative risk discussion
- demonstrated usefulness over at least one real maintenance cycle

#### release-candidate -> release-required

Requires in addition:

- explicit policy change
- workflow-materialized enforcement path
- integration into normative docs
- release runbook updates
- backward-compatibility and migration notes

---

## Inventory record format

Each registered shadow layer should have a record like this.

```yaml
layer_id: relational_gain_shadow
family: relation-dynamics
default_role: shadow diagnostic
current_stage: shadow-contracted
owner_surface:
  - docs
  - workflow
  - tool
primary_entrypoint: .github/workflows/relational_gain_shadow.yml
primary_artifact: PULSE_safe_pack_v0/artifacts/relational_gain_shadow_v0.json
status_foldin: meta.relational_gain_shadow
schema: schemas/relational_gain_shadow_v0.schema.json
semantic_checker: PULSE_safe_pack_v0/tools/check_relational_gain_contract.py
run_reality_states: [real, degraded, invalid, absent]
consumer_authority: review-only
non_interference_test: tests/test_relational_gain_non_interference.py
promotion_blockers:
  - schema not landed
  - contract checker not landed
notes: Shadow-only. Must not write under gates.*.
```

---

## Initial seeded inventory

This is the initial repo-level inventory seed for the current shadow / optional family.
It is a management surface, not a promotion statement.

| Layer / family | Proposed `layer_id` | Current stage | Default role | Primary artifact status | `status.json` fold-in | Next hardening step |
|---|---|---:|---|---|---|---|
| OpenAI evals refusal smoke | `openai_evals_refusal_smoke_shadow` | research | shadow diagnostic | artifact present | none | schema + semantic checker |
| Separation phase overlay | `separation_phase_overlay_v0` | research | shadow diagnostic | artifact present | none | schema + consumer rule |
| Theory overlay v0 | `theory_overlay_v0` | research | shadow diagnostic | artifact present | none | schema + degraded model |
| G-field / G snapshot family | `g_field_snapshot_family_v0` | research | shadow diagnostic | mixed / family-level | none | split family contracts |
| Relational Gain v0 | `relational_gain_shadow` | shadow-contracted target | shadow diagnostic | artifact present | `meta.relational_gain_shadow` | land schema + contract checker |
| EPF experiment / hazard | `epf_shadow_experiment_v0` | research | research diagnostic | artifact family present | none | comparison contract + real/stub classifier |
| Topology family | `topology_family_v0` | research | artifact-derived topology | partial family artifacts | none | standalone schema set |
| Decision-field family | `decision_field_v0` | research | decision-oriented shadow read | partial family artifacts | none | vocabulary contract + artifact schema |
| Parameter Golf v0 | `parameter_golf_submission_evidence_v0` | shadow-contracted target | external challenge companion | artifact present | none | sync inventory with companion schema |
| Publication surfaces | `publication_surfaces_family` | research | opt-in platform integration | N/A | none | consumer-only registry rules |

---

## Registry rule

Once this program is adopted, every shadow layer should appear in a single registry surface.

That registry may be YAML, JSON, or markdown-backed, but it must at least declare:

- layer identity,
- contract state,
- authority state,
- artifact path,
- schema path,
- checker path,
- fold-in path,
- and promotion blockers.

If a layer is not in the registry, it should be treated as unregistered research.

---

## Review rule for relation-dynamics layers

For relation-dynamics layers specifically:

- relation language must remain relation language,
- co-occurrence must not be silently rewritten as causality,
- pressure / adjacency / boundary / transition terms must be documented,
- missing signal families must remain explicit,
- and interpretation must stay downstream of recorded deterministic artifacts.

This keeps relation-dynamics useful without letting them become hidden authority.

---

## Acceptance rule for PR-1

PR-1 is complete when:

- this page exists,
- the boundary and vocabulary are frozen in one place,
- the initial seeded inventory exists,
- the promotion ladder is documented,
- and no normative release behavior changed.

That is enough to start PR-2: common schema / checker scaffolding for contracted shadow artifacts.

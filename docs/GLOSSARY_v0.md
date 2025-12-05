# PULSE GLOSSARY_v0

> Working glossary for the main terms used in the PULSE safe-pack, Core
> profile and Governance Pack.

This glossary is descriptive and versioned (`_v0`): it captures how we
currently use these terms. As the pack evolves, we may update or extend
entries, but the goal is to keep names stable and non-ambiguous.

---

## A

### artefact

**What it means**

Any file produced by a PULSE run that can be stored, inspected or consumed
by tooling, for example:

- `status.json`
- `report_card.html`
- `stability_map_v0.json`
- JUnit / SARIF reports

**What it is not**

- Not only “final” outputs – intermediate JSON is also an artefact.
- Not restricted to CI; artefacts can be produced locally as well.

---

## C

### Core profile (PULSE Core)

**What it means**

A minimal, opinionated set of **deterministic gates** and policies that:

- is recommended for first-time PULSE adopters,
- keeps the most important safety and SLO checks **fail-closed**,
- leaves EPF, paradox, topology and other overlays **opt-in**.

Defined in:

- `PULSE_safe_pack_v0/profiles/pulse_policy_core.yaml`
- enforced by the `PULSE Core CI` workflow.

**What it is not**

- Not a full Governance Pack – it focuses on concrete PASS/FAIL gates.
- Not tied to any single CI system; GitHub Actions is the first reference.

---

### Core gates (Core required gates)

**What it means**

The gate IDs that the Core profile treats as **required** for a release to
be considered acceptable. In v0:

- `pass_controls_refusal`
- `pass_controls_sanit`
- `sanitization_effective`
- `q1_grounded_ok`
- `q4_slo_ok`

If any of these fail in a Core CI run, the job should fail (fail-closed).

**What it is not**

- Not a complete list of all available gates.
- Not immutable forever – but changes should be deliberate and documented.

---

### CI fail-closed

**What it means**

A CI pattern where:

- certain gates are declared **required**,
- if any required gate fails, the CI job fails and the release is blocked.

In PULSE Core:

- the required gate list is explicit (Core gates),
- PULSE does not auto-retry or override failures.

**What it is not**

- Not a “best-effort” run – there is no silent downgrade on gate failure.
- Not a recommendation to fail prod deploys automatically on all governance signals.

---

## D

### Decision Engine

**What it means**

A Governance Pack component that:

- reads `status.json`, `stability_map_v0.json` and overlays (EPF, paradox, etc.),
- emits a structured decision object, e.g. `decision_engine_v0.json`, with:

  - `release_state` ∈ {`fail`, `stage_only`, `prod_ok`},
  - `stability_type` (e.g. `stable_good`, `high_tension`),
  - `decision_trace[]` – small, auditable rule hits.

Runs in **shadow mode** by default (does not change PASS/FAIL).

**What it is not**

- Not a replacement for human governance.
- Not a magic “AI judge” – it is a rule-based policy surface.

---

### drift

**What it means**

Any systematic **change over time** in:

- gate outcomes (PASS/FAIL patterns),
- metrics (e.g. latency, cost, refusal rates),
- stability / paradox signals.

Usually detected by comparing multiple runs via history, e.g.
`logs/status_history.jsonl` or diff tools.

**What it is not**

- Not a single bad run (true drift needs a time window).
- Not guaranteed to be harmful – but worth surfacing.

---

## E

### EPF (Experimental / Probabilistic Fields)

**What it means**

A family of metrics that treat evaluation **as experiments**, with:

- confidence intervals,
- p-values,
- uncertainty quantification.

Used to answer: “How strong is our evidence that this gate behaves as intended?”

**What it is not**

- Not a way to weaken hard safety invariants.
- Not a licence to ignore obvious bad behaviour just because a test is “underpowered”.

---

## G

### G-field

**What it means**

A structured description of the **AI topology and provider usage** of a
system, typically including:

- which models are called,
- where they appear in the pipeline,
- which providers (internal vs external) are used.

Usually recorded in artefacts like `g_field_v0.json`.

**What it is not**

- Not a low-level infra topology map (pods, nodes, etc.).
- Not a direct measure of safety or quality – it’s about **usage footprint**.

---

### Governance Pack

**What it means**

An optional layer on top of PULSE Core that focuses on:

- long-term stability,
- paradox and trade-off visibility,
- governance-ready decision fields.

Typical components:

- Stability Map,
- Decision Engine (shadow),
- EPF & Paradox Playbook,
- G-field & GPT overlays,
- history & drift tools.

**What it is not**

- Not required to run the Core gates.
- Not a replacement for Core fail-closed behaviour.

---

## I

### I-gate (invariant gate)

**What it means**

A gate that encodes a **hard safety or invariance property**, for example:

- safety controls behave as expected on reference prompts,
- sanitisation actually removes sensitive content,
- monotonicity / idemponence / path-independence properties hold.

I-gates are typically treated as **non-negotiable** in safety-critical contexts.

**What it is not**

- Not a soft quality metric.
- Not something we “tune” frequently – changes here are policy-level events.

---

## O

### overlay

**What it means**

Any additional structured view layered on top of core artefacts. Examples:

- EPF overlays,
- paradox fields,
- G-field usage overlays,
- stability overlays.

Overlays:

- read existing artefacts (e.g. `status.json`, logs),
- add new JSON/markdown/HTML outputs,
- usually **do not** change Core PASS/FAIL directly.

**What it is not**

- Not a replacement for `status.json`.
- Not required for a basic PULSE Core integration.

---

## Q

### Q-gate (quality gate)

**What it means**

A gate that encodes a **quality or SLO constraint**, for example:

- groundedness / factuality thresholds,
- fairness / bias constraints,
- latency and cost budgets.

Q-gates can still be fail-closed, especially for critical constraints, but
they may allow more tuning than I-gates.

**What it is not**

- Not purely cosmetic; Q-gates can be just as important as I-gates in practice.
- Not solely about “accuracy” – they can cover any quality dimension.

---

### Quality Ledger

**What it means**

A human-oriented, usually HTML or markdown report that:

- summarises a PULSE run (or a set of runs),
- lists gate outcomes, RDSI, EPF bands, key overlays,
- acts as an audit-friendly “release card”.

Typically generated alongside `status.json`.

**What it is not**

- Not the formal source of truth for machine tools (that’s `status.json`).
- Not a substitute for detailed logs when debugging.

---

## R

### refusal-delta

**What it means**

A measure of how the model’s **refusal behaviour** changes between:

- a baseline / plain behaviour, and
- a tool-augmented or policy-augmented behaviour.

Often expressed as:

- a difference in refusal rates (absolute percentage points),
- plus confidence intervals or significance tests.

Used to detect whether safety interventions are actually changing outcomes.

**What it is not**

- Not a raw refusal rate.
- Not always a gate by itself – in v0 it can be a CI-neutral stability signal.

---

### RDSI (Release Decision Stability Index)

**What it means**

A scalar index summarising:

- the **stability** of the release decision over time,
- how robust it is against small perturbations.

High RDSI ≈ “repeating this evaluation is likely to lead to the same decision”.

**What it is not**

- Not a hard gate on its own.
- Not a standalone performance metric.

---

## S

### safe-pack

**What it means**

The self-contained PULSE folder that can be dropped into any repo, e.g.:

- `PULSE_safe_pack_v0/`

Contains:

- tools (`tools/`),
- profiles (`profiles/`),
- default artefact locations (`artifacts/`),
- schemas and helpers.

**What it is not**

- Not a global installation; it is designed to live inside each target repo.
- Not tied to a single CI system.

---

### Stability Map

**What it means**

An aggregate view (usually JSON) that:

- combines gate outcomes, RDSI, EPF and overlays,
- produces an **instability score** and a **stability type** label,
- may contain per-gate or per-dimension contributions.

Example fields:

- `stability_type` (e.g. `stable_good`, `unstably_good`, `high_tension`),
- `instability_score`,
- `components[]`.

**What it is not**

- Not a raw log of test cases.
- Not meant to hide which gate actually failed.

---

### status.json

**What it means**

The primary **machine-readable** artefact produced by a PULSE run:

- gate outcomes (PASS/FAIL),
- metrics,
- metadata.

It is the main input for:

- CI gate enforcement (`check_gates.py`),
- converters (JUnit, SARIF),
- Stability Map and Decision Engine tooling.

**What it is not**

- Not a free-form log file.
- Not optional – it is central to PULSE’s design.

---

## T

### topology (AI topology)

**What it means**

The logical arrangement of AI components in a system:

- which models are called,
- in what order,
- how data flows between them.

Often captured in G-field artefacts or related overlays.

**What it is not**

- Not physical infra topology (machines, containers).
- Not a replacement for infra diagrams; it complements them with AI semantics.

---

## V

### v0 (version suffix)

**What it means**

A marker indicating a **first, working but evolving** version of a concept:

- `*_v0.json`, `*_v0.md`, etc.

In practice:

- v0 artefacts are usable and documented,
- breaking changes are still possible, but should be called out,
- the suffix helps distinguish from future, more stable schemas.

**What it is not**

- Not a guarantee of instability – just a signal that evolution is expected.
- Not an excuse to change things without documenting the impact.

---

## W

### workflow (PULSE Core CI)

**What it means**

A CI job (e.g. GitHub Actions) that:

- locates the safe-pack,
- runs the PULSE tools,
- enforces the Core gate set,
- exports reports and artefacts.

Example: `.github/workflows/pulse_core_ci.yml`.

**What it is not**

- Not the only way to run PULSE – local runs and other CI systems are also valid.
- Not a full Governance Pack runner; it focuses on Core behaviour.

# PULSE GLOSSARY_v0

> Working glossary for the main terms used in the PULSE safe-pack, Core
> profile, PULSEmech release-authority path, and Instrument Review Pack.

This glossary is descriptive and versioned (`_v0`): it captures how we
currently use these terms. As the pack evolves, we may update or extend
entries, but the goal is to keep names stable and non-ambiguous.

---

## Field-first relational terms (v0)

These terms are used by the Paradox / decision-field / topology overlays.
They are **decision-relative** and **evidence-first**: they describe a structured relationship-space around a release decision
(PASS/FAIL, STAGE/PROD, or a policy cut). They do **not** assert causality.

### Anchor

**What it means**

An explicit reference frame used to compute deltas, classify drift, and orient the Paradox field. Examples:

- a baseline `status.json` used as the release-authority reference,
- a policy cut / threshold set (e.g. θ),
- a specific run context (commit + runner image + seed + profile_id).

**What it is not**

- Not optional when deltas or “orientation” are computed.
- Not a causal explanation — it is a reference frame.

---

### Atom

**What it means**

The smallest **audit-carrying** unit used in the Paradox field that can be referenced, compared, and traced back to concrete evidence
(e.g. `status.json`, transitions, logs, or recorded eval summaries).

Atoms are:

- deterministic, evidence-first elements derived from artefacts,
- decision-relative (their meaning is interpreted relative to an Anchor),
- suitable nodes for tension / drift / borderline instability analysis.

**What it is not**

- Not a free-form narrative “belief”.
- Not a causal claim.
- Not necessarily a failed gate (an atom can represent borderline or shifting behaviour).

---

### Edge

**What it means**

A typed relationship between two Atoms in the Paradox field.

In v0:

- edges represent **evidence-first co-occurrence / association** (not causality),
- edge weight (if present) represents the *strength* of co-occurrence or tension magnitude as defined by the producing tool,
- edge direction (if present) is a decision-relative reading aid computed with respect to an Anchor.

**What it is not**

- Not “A causes B” (unless a future version explicitly introduces causal semantics — v0 does not).
- Not required to be symmetric; the producer may choose directed or undirected edges, but must define the rule.

---

### Orientation

**What it means**

A deterministic, decision-relative “reading direction” for atoms/edges: how the relationship-space is oriented **with respect to an Anchor**.

Orientation answers questions like:

- which findings “push toward FAIL” vs “push toward PASS” under the current reference frame,
- what changes are interpreted as stabilising vs destabilising in the current context.

**What it is not**

- Not meaningful without an explicit Anchor.
- Not a release decision by itself.

---

### Core (field core)

**What it means**

A deterministic minimal sub-structure (subgraph / projection) of the Paradox field that is sufficient to reproduce the same orientation
(and therefore the same reviewer-facing interpretation) under the same Anchor.

The Core exists to make reviewer output readable while preserving auditability.

**What it is not**

- Not the same as **Core profile (PULSE Core)** or **Core gates**.
- Not allowed to “hide” contradictory evidence — it is a projection for readability, not a filter for truth.

---

### Determinism requirements (field/diagram outputs)

Field-first overlays are audit-compatible only if they are stable under reruns.

**Minimum determinism requirements (v0):**

1. **Pinned context**: runner image + dependency versions + (CPU/GPU mode if relevant) are part of run context.
2. **Explicit seed**: any sampling/permutation is seeded and recorded.
3. **Canonical ordering**: lists (atoms/edges/events) are sorted using a documented rule.
4. **Stable identifiers**: IDs are derived from canonicalized content or recorded upstream IDs (no random UUIDs).
5. **No silent external variability**: external calls are avoided, mocked, or fully recorded as inputs.
6. **Fail-closed contracts (overlay-local)**: missing required fields, broken links, or non-canonical ordering are treated as contract failures by the overlay validator (CI-neutral to core release gates, but strict for the overlay job).

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
- Not a recommendation to fail prod deploys automatically on all diagnostic or review signals.

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

- Not the full Instrument Review Pack – it focuses on concrete PASS/FAIL gates.
- Not tied to any single CI system; GitHub Actions is the first reference.

---

### contract-hardened summary surface

**What it means**  
A shadow artifact surface that already has:

- a stable machine-readable shape,
- a versioned schema,
- a layer-specific semantic checker,
- canonical valid fixtures, and where relevant canonical invalid fixtures,
- and regression coverage,

while the broader line or workflow family it belongs to may still remain
in `research` state.

Typical use:

- the artifact itself is contract-disciplined,
- but the surrounding research line is not yet promoted as a whole.

**What it is not**

- Not the same as promoting the whole shadow line.
- Not a release-authority surface.
- Not a claim that the broader workflow family is already `shadow-contracted`.

---

### critical radius (r_c)

#### What it means

The radius (or scale parameter) at which the protocol’s decodability criterion reaches the required threshold (e.g. C(r_c)=h_req). Serves as a compact, reviewable summary of where the boundary sits for a given run/context.

#### What it is not

- Not a universal constant; it is context- and protocol-dependent.
- Not a guarantee of stability outside the recorded conditions.

---

## D

### declared gate policy

**What it means**

The machine-readable gate policy used to determine which gate IDs are required for a given PULSE release path.

It is part of the PULSEmech authority path only when it is used to materialize the workflow-effective required gate set.

Typical authority path:

```text
declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

**What it is not**

- Not organizational policy.
- Not management policy.
- Not compliance policy.
- Not a human approval preference.
- Not a general governance framework.

A declared gate policy becomes release-relevant through materialized required gates and fail-closed enforcement, not through prose.

 
### Decision Engine

**What it means**

A shadow-mode instrument-review artifact in the PULSE Instrument Review Pack v0.

It may:

- read `status.json`, `stability_map_v0.json`, and overlays such as EPF or paradox artifacts,
- emit a structured review object, for example `decision_engine_v0.json`,
- record small, auditable rule hits in `decision_trace[]`,
- support human review or release triage.

Canonical JSON `release_state` values use implementation / schema labels such as:

```text
BLOCK
STAGE_ONLY
PROD_OK
```

Reader-facing displays may render these as:

```text
BLOCK
STAGE-ONLY
PROD-OK
```

The hyphenated forms are display labels, not canonical JSON values.

Runs in **shadow mode** by default.

**What it is not**

- Not release authority by default.
- Not a replacement for `status.json`.
- Not a replacement for declared gate policy.
- Not a replacement for the workflow-effective materialized required gate set.
- Not a replacement for strict fail-closed CI enforcement.
- Not a replacement for human review.
- Not a magic “AI judge” — it is a traceable review artifact.

Legacy note:

```text
Earlier documents may describe this as part of the Governance Pack.
The canonical technical role is now PULSE Instrument Review Pack v0.
```

---

### Decodability Wall (Gravity Record Protocol)

#### What it means

An operational measurement boundary defined from recorded signals: the point (often expressed via a critical radius r_c) where the decodability criterion crosses a required threshold (h_req). Used to make “decodable vs not-decodable (under this protocol)” auditable and repeatable.

#### What it is not

- Not a physical “wall” or a causal barrier in the system.
- Not a security guarantee by itself.
- Not a substitute for recording inputs/contexts; it only makes the boundary explicit given those records.

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

Legacy alias for:

```text
PULSE Instrument Review Pack v0
```

Legacy filename / workshop alias:

```text
docs/GOVERNANCE_PACK_v0.md
```

Do not use `Governance Pack` as the active PULSE-facing identity descriptor.

Use:

```text
PULSE Instrument Review Pack v0
```

for the optional diagnostic / instrument-review layer around PULSEmech.

**What it is not**

- Not the canonical component name.
- Not PULSE identity.
- Not release authority.
- Not a second release-decision engine.

---

## I

### I-gate (invariant gate)

**What it means**

A gate that encodes a **hard safety or invariance property**, for example:

- safety controls behave as expected on reference prompts,
- sanitisation actually removes sensitive content,
- monotonicity / idempotence / path-independence properties hold.

I-gates are typically treated as **non-negotiable** in safety-critical contexts.

**What it is not**

- Not a soft quality metric.
- Not something we “tune” frequently – changes here are policy-level events.

---

## M

### machine-registered

**What it means**  
A shadow layer is machine-registered when it appears in the repository's
machine-readable shadow registry surface (for example
`shadow_layer_registry_v0.yml`) with its declared stage, authority
boundary, artifact path, schema/checker references, and supporting valid/invalid fixtures and tests where those roles are tracked separately.

Machine-registration means the layer is tracked by registry-aware
tooling and validation.

**What it is not**

- Not automatic promotion.
- Not release authority.
- Not equivalent to being release-required.
- Not the same as merely being mentioned in a docs inventory table.

---

## N

### non-interference

**What it means**  
A shadow-layer property stating that, under the same required gate set
and the same release-authority enforcement path, adding, folding, or removing
the shadow layer does not change the release outcome.

Typical proof shape:

- release outcome before shadow fold-in,
- release outcome after shadow fold-in,
- same `check_gates.py`,
- same required gates,
- same result.

**What it is not**

- Not “the shadow layer has no value”.
- Not “the shadow layer cannot write any artifact”.
- Not a claim that the layer has no diagnostic effect.
- Not optional for a shadow layer that is being hardened toward trusted review use.

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

## P

### PULSE Instrument Review Pack v0

**What it means**

An optional diagnostic and instrument-review layer around PULSEmech.

Legacy filename / workshop alias:

```text
docs/GOVERNANCE_PACK_v0.md
Governance Pack
```

The pack may include review artifacts such as:

- `stability_map_v0.json`
- `decision_engine_v0.json`
- EPF / paradox review notes
- G-field / GPT overlay review summaries
- history and drift review artifacts

These artifacts may support:

- human review,
- release triage,
- diagnostic interpretation,
- stability review,
- field / topology inspection.

They are non-authorizing by default.

A signal from this pack becomes release-relevant only if it is:

```text
recorded as release evidence
referenced by declared policy
materialized as a required gate
enforced through the strict fail-closed CI path
```

The PULSEmech authority path remains:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```

**What it is not**

- Not PULSE identity.
- Not release authority.
- Not a second release-decision engine.
- Not required to run Core gates.
- Not a replacement for Core fail-closed behaviour.

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

A human-readable reader carrier over a recorded `status.json` artifact.

It may be rendered as HTML, Markdown, or another reader surface.

It may display:

- gate outcomes,
- run metadata,
- diagnostic overlays,
- release-decision summaries,
- public surface state,
- traceability fields.

Typically generated alongside `status.json`.

**What it is not**

- Not release authority.
- Not a quality-assurance dashboard that decides release.
- Not a substitute for `status.json`.
- Not a substitute for declared gate policy.
- Not a substitute for the workflow-effective materialized required gate set.
- Not a substitute for strict fail-closed CI enforcement.

The PULSEmech authority path remains:

- Not release authority.
- Not a quality-assurance dashboard that decides release.
- Not a substitute for `status.json`.
- Not a substitute for declared gate policy.
- Not a substitute for the workflow-effective materialized required gate set.
- Not a substitute for strict fail-closed CI enforcement.

The PULSEmech authority path remains:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```
---

## R

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

### research diagnostic

**What it means**  
A shadow or experimental layer that is useful for inspection, comparison,
explanation, or hypothesis testing, but whose current repo-level stage is
still `research`.

A research diagnostic layer may already have meaningful tooling around
it, and may even have machine-readable artifact validation for one
surface, while still remaining non-promoted as a broader line.

**What it is not**

- Not a release-authority surface.
- Not the same as `shadow-contracted`.
- Not a synonym for “unimportant”.
- Not evidence that the layer may change release authority.

---

## S

### Safe & Useful AI

**What it means**

A release-domain phrase used to describe the kind of AI release decisions PULSE is intended to support.

In PULSE-facing text, it means that recorded safety, utility, and SLO evidence may be evaluated through declared gates.

**What it is not**

- Not a general definition of safety.
- Not a general definition of usefulness.
- Not an AI-governance framework.
- Not a compliance framework.
- Not a claim that PULSE replaces model evaluation, human review, or domain-specific safety work.

PULSE does not define safety or usefulness in the abstract.

PULSEmech determines whether recorded release evidence satisfies declared gates under strict fail-closed enforcement.

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

### shadow-contracted

**What it means**  
A shadow layer state where the layer already has a stable contract
surface, including at minimum:

- stable `layer_id`,
- primary artifact,
- versioned schema,
- semantic checker,
- a canonical fixture matrix (including valid and invalid fixtures where applicable),
- and regression tests.

A `shadow-contracted` layer is still non-authorizing by default, but it is
no longer just an informal research note or ad hoc shadow experiment.

**What it is not**

- Not advisory or policy-bound by default.
- Not release-required.
- Not permission to write under `gates.*`.
- Not equivalent to promotion into the release-authority decision path.

---

### Stability Map

**What it means**

An aggregate view, usually JSON, that:

- combines gate outcomes, RDSI, EPF and overlays,
- produces an **instability score** and a **stability type** label,
- may contain per-gate or per-dimension contributions.

Example fields:

- `stability_type` such as `stable_good`, `unstably_good`, `stable_bad`, `unstably_bad`, or another schema-defined label,
- `instability_score`,
- `components[]`.

**What it is not**

- Not a raw log of test cases.
- Not meant to hide which gate actually failed.
- Not release authority by default.

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
- Not a full Instrument Review Pack runner; it focuses on Core behaviour.

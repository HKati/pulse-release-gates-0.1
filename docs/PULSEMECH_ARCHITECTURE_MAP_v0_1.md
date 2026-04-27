
# PULSEmech Architecture Map v0.1

## Purpose

The PULSEmech architecture map is the visual orientation map for the current
PULSE direction.

It shows how the project is organized around:

- recorded release evidence,
- interpretive and diagnostic review layers,
- the normative release-authority core,
- exception handling,
- traceability and replay,
- release output,
- and continuous improvement.

This document explains how to read the map without changing the authority
boundary of PULSE.

The map is an orientation surface. It is not the normative release contract.

For normative release semantics, use:

- [`STATUS_CONTRACT.md`](STATUS_CONTRACT.md)
- [`status_json.md`](status_json.md)
- [`GATE_SETS.md`](GATE_SETS.md)
- [`WORKFLOW_MAP.md`](WORKFLOW_MAP.md)
- [`../pulse_gate_policy_v0.yml`](../pulse_gate_policy_v0.yml)
- [`../PULSE_safe_pack_v0/tools/check_gates.py`](../PULSE_safe_pack_v0/tools/check_gates.py)

---

## Current asset

README hero asset:

```text
hero_pulsemech_architecture_map_v0_1.svg
```

The asset version is part of the public orientation surface. Future visual
changes should use a new versioned asset name when the meaning or composition
of the map changes materially.

---

## Core reading

The map should be read from evidence toward release authority:

```text
recorded evidence
→ diagnostic interpretation
→ normative release authority
→ decision record
→ traceability / replay
→ output and improvement
```

The key distinction is:

```text
diagnostic layers can explain, inspect, warn, compare, and summarize
normative layers decide release authority under declared policy
```

PULSE keeps those roles separate.

---

## Layer 1 — Input layer

The input layer represents the evidence and context that may feed a release
review surface.

Typical inputs include:

- release artifacts,
- `status.json`,
- logs,
- detector summaries,
- SLO and quality outputs,
- policy manifests,
- documentation,
- operator notes,
- run metadata.

Inputs do not define release authority by themselves. They become release
evidence only when recorded, normalized, and evaluated through the declared
PULSE release path.

---

## Layer 2 — Interpretive and diagnostic layer

The interpretive and diagnostic layer represents review and analysis surfaces.

Examples include:

- field readers,
- reasoning and hypothesis surfaces,
- EPF / Paradox views,
- topology and G-field views,
- stability and hazard diagnostics,
- evidence summarizers.

These surfaces can be valuable for review, triage, governance, and future policy
design. They do not change release outcomes by default.

Their default role is diagnostic unless a future policy explicitly promotes a
specific signal into the required gate set.

---

## Layer 3 — Normative governance / authority layer

This is the release-authority core.

The normative path is:

```text
release evidence
→ status.json
→ declared gate policy
→ check_gates.py
→ primary CI release workflow
→ release decision record
```

This is the only path that carries release authority by default.

The core authority objects are:

- `PULSE_safe_pack_v0/artifacts/status.json`
- `pulse_gate_policy_v0.yml`
- `pulse_gate_registry_v0.yml`
- `PULSE_safe_pack_v0/tools/check_gates.py`
- `.github/workflows/pulse_ci.yml`
- generated release decision / ledger surfaces

A gate blocks shipping only when it belongs to the active required gate set for
the current lane.

---

## Layer 4 — Exception and override layer

The exception layer represents break-glass or override handling.

The intended governance rule is:

```text
an exception may be recorded, justified, and audited
it must not silently rewrite the original gate evidence
```

Break-glass handling should preserve:

- the original gate result,
- the reason for exception,
- the actor / reviewer context where available,
- the affected release state,
- and the audit trail.

---

## Layer 5 — Tracking and traceability layer

The tracking layer represents replayability and audit continuity.

Useful trace surfaces include:

- evidence ledger,
- decision trace,
- change ledger,
- replay bundle,
- run metadata,
- artifact hashes,
- workflow context,
- policy version.

This layer supports later inspection of why a release decision was produced.

It should not recompute release authority independently from the normative path.

---

## Layer 6 — Output and consumption layer

The output layer represents the surfaces consumed by humans, CI systems, release
owners, dashboards, and downstream governance workflows.

Examples include:

- release state,
- Quality Ledger,
- `status.json`,
- JUnit / SARIF reports,
- Pages views,
- PR summaries,
- next-step recommendations.

Rendered outputs explain or publish the result. They do not redefine the result.

---

## Continuous improvement loop

The improvement loop represents controlled evolution of the release-governance
system.

Examples:

- adding detectors,
- improving fixtures,
- hardening shadow contracts,
- refining policy,
- improving docs,
- stabilizing new diagnostic layers,
- promoting signals only through explicit policy change.

The improvement loop must preserve the separation between normative and
diagnostic authority.

---

## Authority boundary

The map uses a strong authority boundary:

```text
normative = can affect release outcome
diagnostic = can explain or inform review
publication = can render or publish artifacts
guardrail = can protect repository/workflow integrity
```

By default:

- shadow layers are non-normative,
- publication surfaces are non-normative,
- dashboards are non-normative,
- rendered reports are non-normative,
- `meta.*` fold-ins are non-normative,
- missing diagnostic artifacts must not be silently reinterpreted as PASS.

Promotion into release authority requires an explicit policy change and
documentation update.

---

## Relation to PULSE

The map does not rename the canonical project or publication title.

Canonical title:

```text
PULSE — Release Gates for Safe & Useful AI
```

Current technical positioning:

```text
PULSE is a deterministic, fail-closed release-governance layer for LLM
applications and AI-enabled systems.
```

PULSEmech is the architecture orientation map for the broader mechanical
governance direction around the PULSE release-authority core.

---

## Non-goals

This map is not:

- the `status.json` contract,
- a policy file,
- a release gate registry,
- a CI workflow specification,
- a shadow-layer promotion record,
- or a replacement for `check_gates.py`.

It is a reader-facing architecture orientation surface.

---

## Reviewer checklist

When adding or changing a layer shown in the map, check:

1. Is the layer normative, diagnostic, publication, guardrail, or auxiliary?
2. Does it write under `gates.*`?
3. Does it change the active required gate set?
4. Does it alter `check_gates.py` behavior?
5. Does it require a policy / registry / status contract update?
6. Does it preserve non-interference if it is shadow-only?
7. Is its authority status documented?

If the answer changes release authority, update the canonical docs and policy
surfaces in the same change set.

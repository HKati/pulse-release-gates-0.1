# Future-Ready Workmode (PULSE Workshop)

This document is a workmode, not a feature. It defines how we make engineering decisions so the system stays usable as AI capabilities and tooling evolve.

## 1) Stable Core, Replaceable Periphery
**Stable core (hard to change later):**
- Gate semantics and decision levels
- Contracts: status / decision trace / ledger
- Fail-closed rules (missing evidence cannot pass)
- Gate-ID meaning immutability

**Replaceable periphery (expected to evolve):**
- Metric implementations (how we compute them)
- External detectors and vendor integrations
- UI/reporting layers and overlays
- Benchmark task sets

**Experimental (shadow / diagnostic):**
- Forecasting signals, topology/paradox explanations, exploratory overlays
These must not change CI outcomes unless intentionally promoted.

## 2) Gate ID Meaning Is Immutable
- A gate ID must never change meaning.
- If meaning changes: introduce a new ID and deprecate the old one.
- Renaming + reusing an ID is forbidden.

## 3) Decision Is a Projection
PASS/FAIL (or stage/prod) is a projection of the measured state, not an explanation.
Explanations must come from measurable evidence: margins, drift, stability, constraints.

## 4) Contract-First, Versioned
- status / trace / ledger formats are versioned contracts.
- Meaning changes require a new field or a new schema version.

## 5) Capability-Aware Thinking
We do not assume a single “chat-only” model forever.
Policies and gates must remain meaningful across: tools/agents, RAG, multimodal, streaming, on-device, etc.

## 6) Missing Evidence Is Not a Pass
If a required gate cannot be evaluated due to missing inputs/artifacts, treat it as a failure.
Silently passing on absence is not allowed.

## 7) Overrides Are Audited Responsibility
Break-glass is allowed only with explicit justification and durable audit logging.
Overrides do not erase a violation; they record a conscious acceptance.

## 8) Deprecation Path
Every deprecation must include:
- replacement ID
- migration guidance
- target removal timeline

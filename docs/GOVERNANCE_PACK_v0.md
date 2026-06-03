# PULSE Instrument Review Pack v0

Legacy filename / workshop alias:

```text
docs/GOVERNANCE_PACK_v0.md
```

Canonical technical name:

```text
PULSE Instrument Review Pack v0
```

## Boundary

This document describes optional instrument-review and diagnostic surfaces around PULSEmech.

It does not define PULSE.

It does not define release authority.

It does not create a second release-decision engine.

The PULSEmech authority path remains:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```

The Instrument Review Pack may support human review, release triage, diagnostic interpretation, stability review, or optional field-level inspection.

It is non-authorizing by default.

A signal from this pack becomes release-relevant only if it is:

```text
recorded as release evidence
referenced by declared policy
materialized as a required gate
enforced through the strict fail-closed CI path
```

---

## 0. Scope

PULSE Core answers:

```text
Does the recorded release state satisfy the declared required gate set under strict fail-closed enforcement?
```

The Instrument Review Pack supports review questions such as:

```text
How stable is the release field over time?
Where are the tensions between safety, utility, stability, and operational constraints?
Which diagnostic patterns should reviewers inspect before a release decision?
Which review recommendation should be recorded for human interpretation: BLOCK, STAGE-ONLY, or PROD-OK?
Why was that recommendation produced?
```

All components in this pack are **CI-neutral by default**:

```text
they read existing PULSE artifacts
they emit additional JSON / Markdown / HTML views
they do not change PASS / FAIL
they do not change release authority
they do not change PULSEmech semantics
```

They affect release outcome only if explicitly promoted through the PULSEmech authority path.

---

## 1. Components

### 1.1 Stability Map

**Goal:** aggregate PULSE runs into a single stability field for a model line, release line, or evaluated system surface.

Inputs:

```text
historical status.json artifacts
optional EPF overlays
optional paradox overlays
optional field / topology overlays
```

Output:

```text
stability_map_v0.json
```

Possible contents:

```text
per-gate stability categories
stable_good / unstably_good / stably_bad / unstably_bad classifications
instability score
contributing components
drift notes
timestamps
artifact references
```

Primary users:

```text
ML leads
safety engineers
release reviewers
field / topology reviewers
audit reviewers
```

The Stability Map does not change CI status.

It is a diagnostic view.

It is not release authority.

---

### 1.2 Decision Engine — shadow mode

**Goal:** turn the Stability Map and the current run into a structured review object.

Inputs:

```text
latest status.json
stability_map_v0.json
paradox overlays when available
EPF overlays when available
field / topology overlays when available
```

Output:

```text
decision_engine_v0.json
```

Minimum fields may include:

```text
release_state
stability_type
decision_trace[]
rule hits
gate IDs
paradox links
short explanations
review recommendation
```

Recommended release-state vocabulary for this review artifact:

```text
fail
stage_only
prod_ok
```

or, when aligned to public reader labels:

```text
BLOCK
STAGE-ONLY
PROD-OK
```

Behavior:

```text
runs in shadow mode by default
does not change PASS / FAIL
does not replace check_gates.py
does not replace status.json
does not replace declared gate policy
does not replace materialized required gate enforcement
```

A later PR may promote a specific output field into release authority only by declaring it in policy and enforcing it as a required gate.

The Decision Engine is a **review surface**.

Its rules should be:

```text
small
explicit
auditable
deterministic where possible
traceable to recorded artifacts
```

It is not an independent release-decision engine by default.

---

### 1.3 EPF & Paradox Playbook

**Goal:** make EPF and paradox signals actionable for human review.

Artifact:

```text
docs/PULSE_EPF_PARADOX_PLAYBOOK_v0.md
```

The playbook may answer questions such as:

```text
when a gate is considered paradox-heavy
what it means if EPF is consistently better or worse than baseline
what to inspect in fairness vs SLO trade-off cases
what to inspect in refusal policy vs utility cases
what to inspect in hallucination vs productivity cases
which diagnostic pattern is present
which review action should be considered
```

Usage:

```text
referenced from Quality Ledger
referenced from decision traces
used in release reviews
used in post-mortems
used in diagnostic review
used in field / topology review
```

The Playbook turns abstract metrics into concrete review patterns.

It does not authorize a release.

It does not change gate enforcement.

---

### 1.4 G-field & GPT overlays

**Goal:** provide a compact diagnostic view of dependency on internal and external model providers.

Inputs:

```text
g_field_v0.json
g_field_stability_v0.json
g_epf_overlay_v0.json
gpt_external_detection_v0.json
logs/model_invocations.jsonl
```

Output:

```text
g_snapshot_report_v0.md
```

or:

```text
g_snapshot_report_v0.html
```

Possible contents:

```text
external GPT call ratio
vendor mix
high-risk provider usage
present overlays
missing overlays
short diagnostic narrative
risk-review notes
release-review notes
```

This layer may answer questions such as:

```text
How much does this release candidate depend on external GPT calls?
Which providers are involved?
Where are additional models used?
Which provider-related surfaces should reviewers inspect?
Which dependencies are missing from the recorded evidence surface?
```

The G-field / GPT overlay layer is diagnostic by default.

It does not define release authority.

It becomes release-relevant only through explicit recorded evidence inclusion, declared policy reference, required-gate materialization, and strict fail-closed enforcement.

---

### 1.5 History & Drift tools

**Goal:** create a minimal history trail that higher-level review tools can build on.

Candidate scripts:

```text
scripts/append_status_history.py
scripts/diff_runs_minimal.py
```

`append_status_history.py` may:

```text
append each run's status.json to logs/status_history.jsonl
be called at the end of a PULSE CI job
preserve a minimal run history
support later stability and drift review
```

`diff_runs_minimal.py` may:

```text
compare two runs gate-by-gate
emit a small JSON diff summary
emit a small Markdown diff summary
identify changed gates
identify changed metrics
identify changed diagnostic overlays
```

These scripts are deliberately small.

They are foundations for later review views.

They are not release authority by default.

---

## 2. Integration patterns

The Instrument Review Pack is designed to run **after** PULSE Core.

Typical pattern:

```text
1. Core CI job runs.
2. Core CI enforces the selected required gate set fail-closed.
3. Instrument-review jobs consume recorded artifacts.
4. Instrument-review jobs produce diagnostic artifacts.
5. Human reviewers inspect those diagnostic artifacts.
6. Shipping authority remains anchored to the PULSEmech path unless a signal is explicitly promoted into required-gate enforcement.
```

Typical inputs:

```text
status.json
status_history.jsonl
EPF overlays
paradox overlays
G-field overlays
GPT external detection summaries
stability maps
decision traces
```

Typical outputs:

```text
Markdown snapshots
HTML snapshots
diagnostic JSON artifacts
release-review attachments
risk-review attachments
post-mortem attachments
field-review artifacts
```

Examples:

```text
a nightly job that builds stability_map_v0.json from the latest history
a per-release job that generates decision_engine_v0.json in shadow mode
an on-demand job that produces g_snapshot_report_v0 for a branch or environment
a diagnostic review job that compares current field state with historical baseline
```

In all cases, shipping CI remains **fail-closed** on the PULSEmech required gate path.

---

## 3. Promotion boundary

A component in this pack may be promoted from diagnostic review into release authority only through a scoped PR that declares:

```text
the recorded evidence field
the policy reference
the required gate ID
the registry entry
the materialized required gate behavior
the fail-closed enforcement path
the tests that prove missing / false / malformed evidence fails closed
```

Promotion must not be implicit.

Promotion must not occur through reader wording, dashboard presentation, report display, or review recommendation alone.

Correct promotion path:

```text
diagnostic signal
→ recorded release evidence field
→ gate registry entry
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

Incorrect promotion path:

```text
diagnostic signal
→ dashboard display
→ human confidence
→ implicit release authority
```

---

## 4. Roadmap — suggested

This document describes v0.

Suggested evolution:

### v0.1 — layout and schemas

```text
finalize JSON Schemas for stability_map_v0
finalize JSON Schemas for decision_engine_v0
provide at least one concrete example for each artifact
document carrier boundaries for each artifact
```

### v0.2 — minimal implementation

```text
first Stability Map builder over logs/status_history.jsonl
first Decision Engine ruleset
small explicit review rules
traceable review recommendations
```

### v0.3 — review surfaces

```text
lightweight Decision-Field HTML / Markdown view
links from Quality Ledger
links from G snapshot reports
review-facing summary sections
```

### v1.0 — release-review profile

```text
documented review recommendation policies for BLOCK / STAGE-ONLY / PROD-OK
at least one case study using the full Instrument Review Pack
clear distinction between review recommendation and release authority
explicit promotion procedure for any release-relevant signal
```

The roadmap is advisory.

It does not change PULSEmech release authority.

---

## 5. Ownership

Suggested roles:

### Field / topology owner

Responsibilities:

```text
Stability Map design
Decision Engine design
field definitions
stability types
topology labels
diagnostic field interpretation
```

### Instrument review owner

Responsibilities:

```text
EPF & Paradox Playbook
review recommendation rules
diagnostic interpretation patterns
release-triage support
review escalation notes
```

### Runtime / infrastructure owner

Responsibilities:

```text
history logging
drift tooling
artifact storage
diagnostic report generation
simple review-surface publishing
```

### Docs owner

Responsibilities:

```text
instrument-review documentation
snapshot copy
examples
boundary statements
artifact role descriptions
```

The Instrument Review Pack is intentionally modular.

Teams can adopt it piece by piece without touching the Core fail-closed gates.

---

## 6. Boundary held by this document

This document does not change:

```text
PULSEmech decision semantics
gate policy
required gate wiring
check_gates.py behavior
status schema
CI allow/block behavior
Quality Ledger renderer behavior
artifact provenance binding behavior
attestation workflow behavior
release tags
DOI / Zenodo path
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

## Final definition

PULSE Instrument Review Pack v0 is:

```text
an optional diagnostic and instrument-review layer around PULSEmech
that reads recorded PULSE artifacts, emits review artifacts,
and supports human interpretation without changing release authority by default.
```

It is not PULSE identity.

It is not release authority.

It is not a second release-decision engine.

# PULSE Quality Ledger

The **Quality Ledger** is the human‑readable report generated from
`PULSE_safe_pack_v0/artifacts/status.json`.

It is meant for humans who need to **sign off** on a release:

- release owners and product leads,
- safety / red‑team reviewers,
- compliance & audit,
- platform / MLOps teams who operate the CI.

The HTML artefact is:

- local: `PULSE_safe_pack_v0/artifacts/report_card.html`
- live demo: the GitHub Pages snapshot linked from the README.

> The CI always treats `status.json` as the source of truth.  
> The Quality Ledger is a **view** on that JSON, arranged for humans.

---

## 1. Where it comes from

When you run:

```bash
python PULSE_safe_pack_v0/tools/run_all.py


PULSE generates:

PULSE_safe_pack_v0/artifacts/status.json

PULSE_safe_pack_v0/artifacts/report_card.html ← the Quality Ledger

The CI workflow (.github/workflows/pulse_ci.yml) publishes the ledger
as:

a build artefact (ZIP),

a PR comment (for GitHub PRs),

optionally a static snapshot on GitHub Pages.

No additional configuration is needed: as long as status.json
is present and valid, the Quality Ledger can be rendered.

2. What problem the Quality Ledger solves

status.json is machine‑friendly but dense: nested objects, metrics,
thresholds, and gate booleans.

The Quality Ledger:

flattens these into tables and panels,

groups information by decision questions:

“Is it safe enough?” (I₂–I₇ safety invariants)

“Is it useful enough?” (Q₁–Q₄ quality gates)

“Is the decision stable?” (RDSI, refusal‑delta)

“Did any external detector complain?” (optional tools)

adds narrative labels and short explanations for each gate,

surfaces break‑glass overrides and justifications.

It is intentionally conservative: if something is unclear in the JSON,
the ledger will display that ambiguity instead of hiding it.

3. Top‑level layout

A typical Quality Ledger has the following major blocks:

Header / Run metadata

model / service identifier,

git commit / release tag,

CI run id and timestamp,

profile (e.g. PULSE_demo_profile_v0).

Decision strip

A compact banner with:

overall decision: FAIL, STAGE‑PASS, or PROD‑PASS,

RDSI (Release Decision Stability Index) and its CI,

an optional note if a break‑glass override was used.

Safety invariants (I₂–I₇)

A table of deterministic PASS/FAIL gates such as:

psf_monotonicity_ok, psf_mono_shift_resilient,

psf_commutativity_ok, psf_comm_shift_resilient,

sanitization_effective, sanit_shift_resilient,

psf_action_monotonicity_ok, psf_idempotence_ok,

psf_path_independence_ok, psf_pii_monotonicity_ok.

For each gate the ledger shows:

Status (✅ PASS / ❌ FAIL),

what was tested (short description),

sample size and key metrics (if available),

link / anchor to any relevant detail or appendix.

Quality gates (Q₁–Q₄)

Product‑facing gates:

Q₁ Groundedness (RAG factuality),

Q₂ Consistency (agreement across reruns),

Q₃ Fairness (parity / equalized odds),

Q₄ SLOs (p95 latency and cost budgets).

Each row shows:

PASS/FAIL status,

Newcombe / Wilson intervals or deltas (where applicable),

configured thresholds from the profile,

a short justification when a gate fails.

Refusal‑stability & RDSI

This section summarises the refusal‑delta A/B experiment and the
overall decision stability:

Metrics mirrored from status.metrics.*, for example:

refusal_delta_n – number of evaluated request pairs,

refusal_delta – estimated refusal delta,

refusal_delta_ci_low / refusal_delta_ci_high,

refusal_policy – policy label (e.g. "balanced"),

refusal_p_mcnemar – McNemar p‑value,

refusal_pass_min, refusal_pass_strict.

Gate booleans:

refusal_delta_pass,

any profile‑specific stability requirements.

The ledger explains in plain language:

whether the stronger policy actually refuses more unsafe content,

whether the results are statistically significant,

whether this stability was a pre‑condition for the release.

External detectors (optional)

If augment_status.py folded in external summaries, the ledger shows
an External Detectors panel, with one row per tool, for example:

LlamaGuard violation rate,

Promptfoo fail rate,

Garak issue rate,

Azure risk rate,

Prompt Guard attack detect rate.

For each detector:

measured rate (e.g. violation_rate / fail_rate / attack_detect_rate),

configured maximum from thresholds.json,

PASS/FAIL status,

a short note if the tool was disabled or produced no data.

An aggregate line mirrors external_all_pass, the overall external
gate used by CI.

SLO / cost appendix

A compact view of:

p95 latency, p99 latency (if configured),

per‑request cost estimates,

any explicit budget from the profile,

PASS/FAIL indicators for each SLO.

Traceability & artefacts

Finally, the ledger gives pointers to machine‑readable artefacts:

status.json (full metrics + gates),

JUnit and SARIF exports (if enabled),

any uploaded decision traces,

links to the CI run and commit.

This is the place where a human reviewer can see what to archive
for compliance or future audits.

4. Relationship to status.json

The Quality Ledger is a pure function of status.json:

it never contains logic that can change a gate outcome;

it only reads:

top‑level fields (e.g. decision, profile, refusal_delta_pass,
external_all_pass),

metrics.* values,

gates.* booleans.

The CI should always:

enforce gates via PULSE_safe_pack_v0/tools/check_gates.py,

treat the ledger as an explanation layer.

If a discrepancy is ever observed between the ledger and CI behaviour,
status.json wins and the renderer is considered buggy.

5. How humans are expected to use it

Typical review flow:

Scan the decision strip

Is this a FAIL, STAGE‑PASS, or PROD‑PASS?

Is RDSI low (unstable) or high (confident)?

Look at failed gates

any ❌ in safety invariants,

any ❌ in Q₁–Q₄,

any external detector row that failed,

refusal‑delta or stability warnings.

Read the justifications

For each failure, the ledger points to the configured policy:
waive, stage‑only, or hard block.

Record the decision

approve as‑is,

send back for more red‑teaming / data,

approve with break‑glass (and justify it).

Because the ledger is a static HTML artefact, it can be:

stored next to the deployment manifest,

attached to a ticket,

shared with auditors without giving CI access.

6. Extensibility

New sections can be added to the Quality Ledger as long as they only
read from status.json. Common extensions:

separate panels for agent‑specific checks,

additional fairness slices,

organisation‑specific compliance checklists.

The invariants are:

CI logic is centralised in the safe‑pack and gate scripts,

the ledger remains a deterministic, reproducible view over one
status.json.

This keeps PULSE suitable both for day‑to‑day CI and for
long‑term chain‑of‑custody of AI release decisions.

7. Example: reading a small ledger snippet

This section shows a tiny, schematic example of what a Quality Ledger
conveys and how a human reviewer is expected to read it.

7.1 Header and decision strip

A simplified header might look like:

Model:          my-llm-v3.1
Profile:        PULSE_demo_profile_v0
CI run:         gha-2026-01-15-123456
Commit:         abcdef1234
Decision:       STAGE-PASS
RDSI:           0.82  (CI: 0.74–0.89)


A reviewer can already answer:

Which model build is this? → my-llm-v3.1 / commit abcdef1234

What profile was used? → PULSE_demo_profile_v0

Is this a PROD‑ready release? → STAGE-PASS (good for staging, not yet prod)

How stable is the decision? → RDSI 0.82 with a reasonably tight CI

7.2 Gate table snippet

Further down, a typical table row for important gates might be rendered as:

### 7.2 Gate table snippet

Further down, a typical table row for important gates might be rendered as:


```text
Gate                 Status  Metric / value            Threshold / policy               Note
refusal_delta_pass   ✅      Δ = +0.06 (n = 120)       ≥ 0.05 (balanced policy)         New policy refuses more unsafe content.
external_all_pass    ✅      max(detectors) = 0.07     ≤ 0.10 violation / fail / attack All external detectors within budget.
Q1_groundedness_pass ❌      89% grounded (CI: 85–92%) ≥ 92% grounded                   Below target; allowed for staging only.
SLO_latency_p95_pass ✅      p95 = 480 ms              ≤ 500 ms                         Within latency SLO.
```

The HTML ledger would also link each gate to its detailed explanation,
but even from this compact view a human can reason about the release:

refusal_delta_pass

The new policy refuses more unsafe content (+0.06 delta) on 120 pairs
and meets the configured minimum of 0.05. This supports the safety
story.

external_all_pass

All external detectors (LlamaGuard, Promptfoo, Garak, Azure eval,
Prompt Guard) are under their own thresholds, and the aggregate
external_all_pass gate is True.

Q1_groundedness_pass

Groundedness is slightly below the 92% target (point estimate 89%,
confidence interval 85–92%). The ledger marks this as a FAIL, but a
profile might allow this for staging while blocking for production.
The note explains the policy.

SLO_latency_p95_pass

Latency is within budget (480 ms vs ≤ 500 ms). Even if quality needs
work, the system is operationally viable.

A release owner glancing at this snippet can say:

“Safety gates look good (refusal_delta_pass, external_all_pass).”

“Groundedness (Q1) is not yet where we want it; treat this as
staging‑only, not production.”

“Latency SLO is okay; we can test this further with real traffic.”

The full ledger expands on these rows with richer explanations and
links to underlying artefacts (datasets, detector configs, CI runs).





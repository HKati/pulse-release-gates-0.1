# External detectors

> Repo-level policy for using archived external detector evidence with PULSE.

This page is the **entrypoint-first policy view** for external detectors in this
repository.

For implementation details and summary-file behavior, see:

- [external_detector_summaries.md](external_detector_summaries.md)

For the small portable note shipped inside the safe-pack, see:

- `PULSE_safe_pack_v0/docs/EXTERNAL_DETECTORS.md`

---

## 1. Design constraints

PULSE is designed to stay:

- **deterministic**
- **fail-closed**
- **artifact-first**
- **audit-ready**

That means external detectors should not introduce live, hidden, or
non-reproducible behavior into the normative release decision.

The intended pattern is:

1. run external tools separately,
2. write immutable JSON / JSONL summaries,
3. archive those summaries as run artefacts,
4. fold the archived summaries into the final `status.json`,
5. enforce only the gates that policy / workflow explicitly promote.

Important rule:

- if evidence is missing, unreadable, or ambiguous, it must **never** be
  silently reinterpreted as `PASS`.

---

## 2. What counts as an “external detector”?

An external detector is any independent tool that evaluates model behavior
outside the core deterministic PULSE gate computations.

Examples include:

- safety scanners,
- prompt-injection detectors,
- jailbreak / abuse probes,
- content-policy evaluators,
- org-internal review tools that emit structured summaries.

The key requirement is not the brand of the tool, but the shape of the output:
PULSE expects archived, structured summaries that can be folded into immutable
run artefacts.

---

## 3. What PULSE consumes

At the repo level, PULSE consumes archived summary artefacts rather than live
tool calls in the normative path.

Typical accepted forms are:

- **JSON** — one structured summary object
- **JSONL** — one structured record per line

In practice, the current repo wiring treats files matching:

- `*_summary.json`
- `*_summary.jsonl`

as external detector summary artefacts.

For the current merge behavior, detector mappings, and strict checker details,
see [external_detector_summaries.md](external_detector_summaries.md).

---

## 4. Three separate policy questions

A lot of confusion disappears if these three questions stay separate.

### 4.1 Are external detectors required at all?

By default, **no**.

You can adopt PULSE without external detectors and still get deterministic,
fail-closed core gating.

This is especially important for first-time adopters and Core CI paths.

### 4.2 Are folded external results normative?

Sometimes.

If the workflow / policy promotes an external detector result into the enforced
gate set, that result becomes normative.

In practice, the most common aggregate gate is:

- `gates.external_all_pass`

If that gate is enforced, it can block shipping.

If it is not enforced, external detector findings can still remain visible in
`status.json`, the Quality Ledger, and audit artefacts without changing the
release decision.

### 4.3 Is evidence presence itself required?

This is a **separate knob** from aggregate detector pass/fail.

A workflow may decide that release-grade runs require proof that detector
summaries were actually present and parseable.

That question is typically represented by signals such as:

- `external_summaries_present`
- `gates.external_summaries_present`

Use this when you care about **evidence completeness**, not just the aggregate
detector result.

---

## 5. Current repo defaults

The current repository model is intentionally layered.

### Policy default

At the policy level, external detectors default to **advisory** semantics unless
they are explicitly promoted into an enforced gate set.

### Core path

The minimal Core gate set is designed to stay small and deterministic for
first-time adopters.

That means Core enforcement does **not** require external detector gates by
default.

### Full / release-style enforcement

The broader required gate set can promote external detector outcomes into
normative release gating.

In those paths, an aggregate gate such as `external_all_pass` may become
release-blocking.

### Strict evidence mode

Release-grade paths may also require external detector evidence to be:

- present,
- parseable,
- and shaped like valid summary artefacts.

This is stricter than merely checking an aggregate pass/fail result.

The workflow + policy together are the authoritative source for which external
signals are merely advisory, which are normative, and when strict evidence is
required.

---

## 6. Recommended integration pattern

The recommended pattern is:

1. **Run the detector outside the core gate computation**
   - separate job, separate script, or offline batch run.

2. **Write a compact immutable summary**
   - JSON or JSONL,
   - archived with the run.

3. **Fold the archived summary into `status.json`**
   - via the existing augmentation flow.

4. **Promote only the gates you actually trust**
   - keep new signals advisory first,
   - move them into required gating only after they are stable and reviewable.

5. **Use strict evidence checks only where they are really needed**
   - for example release-grade or evidence-sensitive workflows.

This keeps the release model conservative and explainable.

---

## 7. Recommended summary characteristics

Even when only one numeric threshold is needed for gating, summaries should be
self-describing.

Good summary artefacts usually include:

- detector / tool name,
- version and/or immutable digest,
- run id,
- generation timestamp,
- a stable numeric signal,
- optional evidence pointers,
- optional notes for review or audit.

Helpful properties:

- **stable check ids**
- **small size**
- **explicit metric names**
- **no huge embedded logs**
- **easy archival and replay**

For current metric-key expectations and compatibility fallbacks, see
[external_detector_summaries.md](external_detector_summaries.md).

---

## 8. Security & hygiene

Treat external summaries as **untrusted input**.

That means:

- validate them,
- never execute content from them,
- do not embed secrets,
- avoid leaking sensitive user data,
- pin tool versions or digests where possible,
- keep enough provenance for later audit.

External detectors should strengthen release governance, not create a new
untracked trust boundary.

---

## 9. How to think about failures

A useful mental model:

- **Missing detector entirely** → optional unless strict evidence is enabled.
- **Detector present but broken / unreadable** → should fail closed once the
  workflow says that evidence matters.
- **Detector present and below threshold** → contributes a passing external row.
- **Detector present and above threshold** → contributes a failing external row.
- **Aggregate external gate enforced** → can block shipping.
- **Aggregate external gate not enforced** → remains visible but advisory.

This separation is what lets PULSE stay both conservative and flexible.

---

## 10. Related docs

- [external_detector_summaries.md](external_detector_summaries.md) — current summary-file behavior, detector mappings, strict checker semantics
- [status_json.md](status_json.md) — how external evidence appears in `status.json`
- [STATUS_CONTRACT.md](STATUS_CONTRACT.md) — stable public `status.json` contract
- [quality_ledger.md](quality_ledger.md) — how folded evidence is surfaced for human review
- [refusal_delta_gate.md](refusal_delta_gate.md) — another derived-signal gate with separate evidence semantics
- `PULSE_safe_pack_v0/docs/EXTERNAL_DETECTORS.md` — portable safe-pack note

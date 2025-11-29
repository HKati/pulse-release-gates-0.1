# RDSI stability notes

This note explains how the Release Decision Stability Index (RDSI) is
intended to be read in this repository, and what it does *not* do by
itself.

It is a companion to the methods document in the safe-pack:

- `PULSE_safe_pack_v0/docs/METHODS_RDSI_QLEDGER.md`

## What RDSI measures (per run)

RDSI is a *per-run* stability signal. At a high level, it asks:

> “If we were to re-evaluate this release decision under small
>  perturbations, how likely is it that the PASS/FAIL outcome would
>  remain the same?”

Typical ingredients (conceptually):

- repeated or perturbed evaluations under the same policy,
- observing whether gates flip or remain stable,
- compressing this into a single stability score and a Δ (delta) with
  confidence intervals.

In other words:

- a **high RDSI** suggests that the decision is robust to minor changes
  in conditions (run-to-run noise, small sampling differences, etc.),
- a **low RDSI** suggests that the decision may be fragile, and small
  changes could flip the overall PASS/FAIL outcome.

The core gates remain deterministic and fail-closed; RDSI is an
*overlay* that quantifies how stable those decisions are under small,
controlled perturbations.

## What RDSI does *not* do

RDSI, as shipped here, is **not** a full drift monitoring system:

- It does *not* automatically track long-term trends across many runs,
  versions or commits.
- It does *not* change any CI behaviour or thresholds on its own.
- It does *not* decide when to retrain or roll back a model.

Instead, RDSI should be read as a *snapshot* of stability for a given
run, complementing the Quality Ledger and the deterministic gate
results.

Long-term directional drift (for example, a slow degradation in a
metric over dozens of releases) needs to be assessed by looking at
historical ledgers or external monitoring, not by RDSI alone.

## Recommended human use

When reading RDSI in the context of a run:

1. Look at the **RDSI value and its Δ/CI**:
   - treat unusually low values as a prompt to investigate:
     - are some gates close to their thresholds?
     - did the environment change (new model, new dataset, new hardware)?

2. Cross-check with the **Quality Ledger**:
   - identify which gates or metrics contribute most to instability,
   - note if the same gates also appear frequently in failures or
     near-fail states.

3. Over time, maintainers can build a *manual* view of drift by:
   - plotting RDSI across recent runs,
   - correlating drops in RDSI with changes in models, prompts, or
     test distributions.

Any policy change based on RDSI (for example, tightening a threshold
after repeated low-stability signals) should go through the usual
review and CI process, not be applied automatically.

## Relation to other docs

- For the formal description of RDSI and the Quality Ledger, see:
  - `PULSE_safe_pack_v0/docs/METHODS_RDSI_QLEDGER.md`
- For details on the core gates, invariants and outputs, see:
  - `README.md` (What PULSE checks, Outputs)
  - the methods and topology documents referenced there.

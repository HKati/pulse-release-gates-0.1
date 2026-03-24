> [!IMPORTANT]
> # PULSE EPF shadow pipeline walkthrough (v0)
>
> Detailed walkthrough of the current EPF shadow experiment workflow.
>
> This document explains the current implementation flow of the EPF shadow experiment.
>
> It shows:
> - how the workflow is triggered,
> - how the shared input is prepared,
> - how the deterministic and EPF shadow branches run,
> - how the compare step derives deltas,
> - which artifacts are emitted,
> - how to distinguish real runs from degraded runs.
>
> It does **not** define release semantics.
>
> Release semantics are specified in:
> - `docs/STATE_v0.md`
> - `docs/status_json.md`
> - `docs/STATUS_CONTRACT.md`
>
> ---
>
> ## Important boundary
>
> - deterministic archived artifacts carry the recorded baseline result for the experiment flow
> - the EPF shadow path is diagnostic and CI-neutral
> - disagreement between baseline and EPF is inspection input, not an automatic policy rewrite
> - missing or degraded inputs remain explicit
>
> For the shorter command-level version, see:
> - `docs/PULSE_epf_shadow_quickstart_v0.md`
>
> For disagreement handling, see:
> - `docs/PARADOX_RUNBOOK.md`
>
> For the EPF ↔ topology relation, see:
> - `docs/PULSE_topology_epf_hook_v0.md`
> - `docs/PULSE_topology_overview_v0.md`
> - `docs/PULSE_decision_field_v0_overview.md`
>
> For broader repository state, see:
> - `docs/STATE_v0.md`
> - `docs/status_json.md`
> - `docs/STATUS_CONTRACT.md`
>
> ---
>
> ## 1. What this pipeline is
>
> The repository ships an optional workflow:
>
> ```text
> .github/workflows/epf_experiment.yml
> ```
>
> This workflow performs a shared-input A/B comparison:
>
> - produce or recover a common `status.json`
> - create two working copies from that same input
> - run:
>   - deterministic baseline evaluation
>   - EPF shadow evaluation
> - compare the resulting archived decision surfaces
> - emit human- and machine-readable comparison artifacts
> - upload the comparison bundle
>
> Its goal is not to replace deterministic release evaluation.
>
> Its goal is to expose:
>
> - boundary fragility
> - shadow disagreement
> - paradox candidates
> - degraded or weakly supported comparisons in archived, reviewable form
>
> ## 2. Trigger model
>
> The current workflow runs on:
>
> - `workflow_dispatch`
> - push to `main` when selected paths change
>
> The current path filter includes:
>
> - `PULSE_safe_pack_v0/**`
> - `tools/**`
> - `scripts/**`
> - `pulse_gates.yaml`
> - `.github/workflows/epf_experiment.yml`
>
> This makes the workflow useful for:
>
> - EPF / checker edits
> - safe-pack changes
> - shadow config changes
> - targeted manual re-runs
>
> ## 3. Step-by-step pipeline
>
> ### 3.1 Checkout and Python setup
>
> The workflow first:
>
> - checks out the repository
> - sets up Python 3.11
>
> This is the runtime scaffold for the later steps.
>
> ### 3.2 Dependency install (best-effort)
>
> The next step tries to install dependencies.
>
> Preferred path:
>
> - if `PULSE_safe_pack_v0/requirements.txt` exists, install from there
>
> Fallback path:
>
> - otherwise install a minimal set:
>   - `numpy`
>   - `jsonschema>=4,<5`
>
> Important nuance:
>
> - dependency installation is best-effort
> - if install fails, the workflow warns and continues in degraded / stub-capable mode
>
> That means a completed shadow workflow does **not** automatically prove
> that the full EPF experiment ran in a strong form.
>
> ### 3.3 Prepare shared input
>
> The workflow then tries to produce a baseline status artifact via:
>
> ```bash
> python PULSE_safe_pack_v0/tools/run_all.py --mode core
> ```
>
> If that succeeds and writes:
>
> ```text
> PULSE_safe_pack_v0/artifacts/status.json
> ```
>
> the workflow copies that file into:
>
> ```text
> status.json
> ```
>
> If `run_all.py` is missing or no baseline artifact appears, the workflow falls back to a v1-shaped stub:
>
> ```json
> {
>   "version": "1.0.0-shadow-stub",
>   "created_utc": "1970-01-01T00:00:00Z",
>   "metrics": {
>     "run_mode": "core"
>   },
>   "gates": {}
> }
> ```
>
> This `status.json` becomes the common input for both the deterministic
> and EPF shadow branches.
>
> Important boundary:
>
> - this common input is a convenience input to the shadow workflow
> - it is not a replacement for the repository’s final release authority path
>
> The repository’s release authority remains the final `status.json` +
> required gate enforcement path described in:
>
> - `docs/status_json.md`
> - `docs/STATUS_CONTRACT.md`
>
> ### 3.4 Deterministic baseline branch
>
> The deterministic branch starts from the common input:
>
> ```text
> status.json → status_baseline.json
> ```
>
> Then the workflow checks whether:
>
> ```text
> pulse_gates.yaml
> ```
>
> exists.
>
> If it does not exist:
>
> - the workflow stays in degraded / carry-forward mode
> - real compare-branch gate evaluation is skipped
> - `status_baseline.json` remains a copy of the shared input
>
> If it does exist and `scripts/check_gates.py` is present, the workflow runs:
>
> ```bash
> python scripts/check_gates.py \
>   --config pulse_gates.yaml \
>   --status status_baseline.json \
>   --defer-policy fail
> ```
>
> Interpretation:
>
> - this is the deterministic reference branch inside the shadow experiment workflow
> - it is a baseline read for comparison
> - it is not a hidden rewrite of release semantics
>
> ### 3.5 EPF shadow branch
>
> The EPF branch also starts from the same common input:
>
> ```text
> status.json → status_epf.json
> ```
>
> Again, if `pulse_gates.yaml` is missing:
>
> - the workflow stays in degraded / carry-forward mode
> - `status_epf.json` remains a copy of the shared input
>
> If the config and checker are available, it runs:
>
> ```bash
> python scripts/check_gates.py \
>   --config pulse_gates.yaml \
>   --status status_epf.json \
>   --epf-shadow \
>   --seed 1737 \
>   --defer-policy warn
> ```
>
> Interpretation:
>
> - this is the seeded shadow comparison branch
> - it is deliberately configured to warn rather than fail-closed
> - it exists to expose instability / disagreement
> - it does not silently overrule the deterministic baseline
>
> ### 3.6 Compare and summarize
>
> After both branches run, the workflow compares archived decision surfaces.
>
> Current compare inputs:
>
> - Baseline-side decisions are read from:
>
>   ```text
>   status_baseline.json["decisions"]
>   ```
>
> - EPF-side shadow decisions are read from:
>
>   ```text
>   status_epf.json["experiments"]["epf"]
>   ```
>
> #### Normalization rule on the EPF side
>
> If an EPF gate entry is a dictionary, the compare step reads:
>
> - `decision`
> - otherwise `status`
> - otherwise the raw value
>
> #### Change rule
>
> A gate is counted as changed only when:
>
> - the EPF-side value is present
> - and the EPF-side value differs from the baseline-side value
>
> Important nuance:
>
> - `False` / `0` are treated as real values, not as “missing”
> - the compare step checks presence against `None`, not truthiness
>
> This makes the compare step a diagnostic delta surface over archived outputs,
> not a second release-semantics contract.
>
> Also important:
>
> - the shared input is now v1-shaped
> - but the compare summary still operates over the archived branch-local decision surfaces
> - this workflow remains a shadow comparison workflow, not the repository’s normative gate authority
>
> ### 3.7 Emitted summaries and uploaded artifacts
>
> The compare step writes:
>
> - `epf_report.txt`
> - `epf_paradox_summary.json`
>
> It also appends a GitHub Step Summary containing:
>
> - the text of `epf_report.txt`
> - a one-line changed / no-change outcome
>
> Finally, the workflow uploads:
>
> - `epf-ab-artifacts`
>
> containing:
>
> - `status.json`
> - `status_baseline.json`
> - `status_epf.json`
> - `epf_report.txt`
> - `epf_paradox_summary.json`
>
> ## 4. How to read degraded vs strong runs
>
> A run is stronger when:
>
> - dependency install succeeded
> - `run_all.py --mode core` succeeded
> - a real `PULSE_safe_pack_v0/artifacts/status.json` was produced
> - `pulse_gates.yaml` existed
> - `scripts/check_gates.py` was present and ran in both branches
>
> A run is degraded when one or more of those conditions failed.
>
> The workflow records that degraded state explicitly through:
>
> - warning messages
> - branch return codes in the summary
> - stub / carry-forward artifacts instead of silently fabricating a “clean” EPF result
>
> That explicit degraded behavior is intentional.
> It preserves reviewability and avoids false confidence.
>
> ## 5. What this workflow does not mean
>
> This workflow does **not** mean:
>
> - EPF has become a required release gate
> - shadow disagreement automatically changes policy
> - the compare summary is the new source of truth
> - archived comparison artifacts replace the final release-time `status.json`
>
> The source of truth for release reasoning remains the repository’s
> final gate-enforced status path described in:
>
> - `docs/status_json.md`
> - `docs/STATUS_CONTRACT.md`
>
> The EPF shadow workflow is:
>
> - exploratory
> - archived
> - reviewable
> - CI-neutral

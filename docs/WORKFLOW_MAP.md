# Workflow map

This page gives a fast orientation to the repository's GitHub Actions workflows.

## One-line rule

By default, only the primary release-gating workflow participates in release outcome decisions.

Shadow, diagnostic, publication, and validation workflows may be fail-closed within their own scope, but they do not change the main release outcome unless they are explicitly promoted into the required gate set.

## 2-minute orientation

If you are opening this repository for the first time, use this order:

1. **Shipping / release decision**
   - `.github/workflows/pulse_ci.yml`
   - This is the primary release-gating workflow.

2. **Repo / workflow guardrails**
   - `workflow_lint.yml`
   - Governance preflight and workflow validation checks.
   - These protect workflow and repo integrity; they are not a second release-decision engine.

3. **Shadow / diagnostic workflows**
   - These produce extra signals, overlays, reports, or research artifacts.
   - By default, treat them as CI-neutral diagnostic layers.
   - Examples:
     - `.github/workflows/openai_evals_refusal_smoke_shadow.yml`
     - `.github/workflows/separation_phase_overlay.yml`
     - `.github/workflows/theory_overlay_v0.yml`
     - `.github/workflows/relational_gain_shadow.yml`
     - `.github/workflows/epf_experiment.yml`
     - G-field / G-snapshot / overlay-validation shadow workflows

4. **Publication / GitHub-native surfaces**
   - These publish to GitHub-native surfaces or other outward-facing channels.
   - Keep these as opt-in workflows with explicit write permissions.
   - Examples:
     - `.github/workflows/upload_sarif.yml`
     - PR comments
     - badge write-back
     - Pages snapshots

## Workflow families

### A. Primary gating
**Purpose:** release decision

- Canonical workflow: `.github/workflows/pulse_ci.yml`
- This runs the main pack, enforces required gates, and belongs to the normative release path.
- If you want to understand what can block shipping, start here.

### B. Repo / workflow guardrails
**Purpose:** repo integrity, workflow integrity, governance preflight
- These workflows protect workflow YAML, policy wiring, and related guardrails.
- They do not create a second release semantic layer.
- Their job is to prevent damage or ambiguity in the existing mechanism.

#### Shadow layer registry workflow

**Workflow:** `.github/workflows/shadow_layer_registry.yml`

**Purpose:** validate the machine-readable shadow layer registry surface.

Current registry stack:

- `shadow_layer_registry_v0.yml`
- `schemas/shadow_layer_registry_v0.schema.json`
- `PULSE_safe_pack_v0/tools/check_shadow_layer_registry.py`
- `tests/test_check_shadow_layer_registry.py`

Current canonical registry fixture:

- `tests/fixtures/shadow_layer_registry_v0/pass.json`

Current registered layer:

- `relational_gain_shadow`

Boundary:

- registry validation is descriptive and governance-facing
- it does not change release semantics
- it does not promote a layer by registry presence alone
- it does not create normative authority

Current relation to Relational Gain:

- the registry currently tracks the contract-hardened Relational Gain shadow pilot
- the dedicated registry workflow also watches the currently referenced Relational Gain surfaces

### C. Shadow / diagnostic workflows
**Purpose:** extra diagnostics, research layers, or explanatory surfaces

- These workflows may produce overlays, extra JSON/Markdown artifacts, research comparisons, or dry-run signals.
- Important rule:
  - they may **explain**
  - they may **compare**
  - they may **warn**
  - but by default they do **not** change the release outcome
- Example:
  - `.github/workflows/relational_gain_shadow.yml`
  - Runs the relational gain Shadow path, writes a shadow artifact, and folds the result under    `meta.relational_gain_shadow` without changing the main release outcome.

### D. Publication / platform integration workflows
**Purpose:** publication to GitHub-native or external-facing surfaces

- Example: SARIF upload into GitHub Code Scanning.
- This family may also include PR comments, badge write-back, or Pages snapshots.
- Keep these separate from the primary release-gating workflow.

### E. Auxiliary security workflows
**Purpose:** repository hygiene, investigation, and security publication

- Examples:
  - `.github/workflows/gitleaks.yml`
  - `.github/workflows/secret_sweep.yml`
  - `.github/workflows/secret_history.yml`
  - `.github/workflows/secret_full_sweep.yml`
  - `.github/workflows/upload_sarif.yml`

- These workflows help detect, summarize, sanitize, or publish security findings.
- By default they do not define release outcomes.
- Keep them separate from the primary release-gating workflow unless a policy explicitly promotes them into the required gate set.

## Read this together with

- `README.md`
- `docs/STATUS_CONTRACT.md`
- `docs/status_json.md`
- `docs/RUNBOOK.md`

## Practical rule for contributors

Before adding a new workflow, decide which category it belongs to:

- **release-gating**
- **guardrail**
- **shadow / diagnostic**
- **publication**
- **auxiliary security**

If that role is not stated clearly, the workflow becomes too easy to misread.

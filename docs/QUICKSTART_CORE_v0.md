# PULSE Core Quickstart (v0)

> Minimal, fail-closed release gates for first-time PULSE adopters.  
> This guide focuses on the **Core profile** and the dedicated Core CI workflow.

---

## 1. Who this is for

Use this guide if you want to:

- run PULSE as a **drop-in safety & quality gate pack** in CI,
- start with a **small, opinionated set of deterministic gates**,
- *not* worry (yet) about EPF, paradox, topology, or governance overlays.

The Core profile is designed as the recommended starting point.  
You can layer the advanced features on top later.

---

## 2. Add the safe-pack to your repo

In your repository root:

1. Copy the PULSE pack folder:

        PULSE_safe_pack_v0/

   or unzip the pack archive:

        PULSE_safe_pack_v0.zip → PULSE_safe_pack_v0/

2. Commit the folder to your repo.  
   The safe-pack is self-contained; it does not require a global install.

The default layout looks like:

        PULSE_safe_pack_v0/
          tools/
          artifacts/
          profiles/
          ...

---

## 3. Understand the Core profile

The Core profile is defined in:

        PULSE_safe_pack_v0/profiles/pulse_policy_core.yaml

Key fields:

- `profile_id: "core_v0"`
- `label: "PULSE Core (minimal deterministic gates)"`
- `status: "experimental"` (candidate for promotion to default later)

The Core profile:

- defines the **minimal recommended deterministic gate set** for first-time PULSE adopters,
- keeps the most important safety and SLO checks **fail-closed**,
- leaves EPF, paradox, topology and other overlays **opt-in**,
- includes a **CI-neutral refusal-delta stability policy** for future tooling.

### 3.1 Core required gates

The Core profile’s `core_required_gates` list contains:

- `pass_controls_refusal`
- `pass_controls_sanit`
- `sanitization_effective`
- `q1_grounded_ok`
- `q4_slo_ok`

When you wire PULSE Core into CI, these are the gates that should be treated as **required**:  
if any of them FAIL, the Core job should fail and block the release.

### 3.2 Optional per-gate config

The profile can also include per-gate configuration under `gates:`.  
For example:

    gates:
      - id: q1_groundedness
        threshold: 0.85
        epsilon: 0.03
        adapt: true
        max_risk: 0.20
        ema_alpha: 0.20
        min_samples: 5

If a gate is not listed there, the built-in defaults apply.

### 3.3 Refusal-delta policy (CI-neutral)

The `refusal_delta` block in the Core profile describes how we interpret  
refusal-delta stability in tooling and dashboards:

    refusal_delta:
      policy: "balanced"      # "balanced" | "strict"
      delta_min: 0.05         # +5 percentage points improvement (plain - tool)
      delta_strict: 0.10      # +10 percentage points for strict mode
      alpha: 0.05             # 95% confidence for intervals / tests
      require_significance: true
      significance: "mcnemar" # "mcnemar" | "ci"
      ci_neutral: true        # never flips PASS/FAIL on its own

In v0 this is **CI-neutral**:

- it does *not* change PASS/FAIL by itself,
- it is meant to be consumed by stability tooling and dashboards,
- CI remains fail-closed only on the deterministic gates listed in `core_required_gates`.

---

## 4. Add the Core CI workflow

To wire PULSE Core into GitHub Actions, create a new workflow:

        .github/workflows/pulse_core_ci.yml

Example workflow:

    name: PULSE Core CI

    on:
      push:
        branches: [ main ]
        paths-ignore:
          - 'docs/**'
          - '**/*.md'
      pull_request:
        branches: [ main ]
        paths-ignore:
          - 'docs/**'
          - '**/*.md'
      workflow_dispatch: {}

    permissions:
      contents: write

    jobs:
      pulse-core:
        runs-on: ubuntu-latest

        steps:
          - name: Checkout
            uses: actions/checkout@v4

          - name: Locate PULSE pack
            shell: bash
            run: |
              set -euo pipefail
              ROOT="$GITHUB_WORKSPACE"

              if [ -d "$ROOT/PULSE_safe_pack_v0" ]; then
                echo "PACK_DIR=$ROOT/PULSE_safe_pack_v0" >> "$GITHUB_ENV"
              elif [ -f "$ROOT/PULSE_safe_pack_v0.zip" ]; then
                unzip -q -o "$ROOT/PULSE_safe_pack_v0.zip"
                echo "PACK_DIR=$ROOT/PULSE_safe_pack_v0" >> "$GITHUB_ENV"
              else
                RUN_ALL=$(find "$ROOT" -type f -name run_all.py -path "*/PULSE_safe_pack_v0/*" | head -n1 || true)
                if [ -z "$RUN_ALL" ]; then
                  echo "::error::PULSE_safe_pack_v0 not found (expected folder or zip in repo root)."
                  exit 1
                fi
                echo "PACK_DIR=$(dirname "$(dirname "$RUN_ALL")")" >> "$GITHUB_ENV"
              fi

          - name: Set up Python
            uses: actions/setup-python@v5
            with:
              python-version: '3.x'

          - name: Run PULSE Core pack
            shell: bash
            run: |
              set -euo pipefail
              python "${PACK_DIR}/tools/run_all.py"

          - name: Show gates snapshot
            shell: bash
            run: |
              echo "----- status.json (gates) -----"
              if command -v jq >/dev/null 2>&1; then
                jq '.gates' "${PACK_DIR}/artifacts/status.json" || cat "${PACK_DIR}/artifacts/status.json"
              else
                cat "${PACK_DIR}/artifacts/status.json"
              fi
              echo "--------------------------------"

          - name: Enforce Core gates (fail-closed)
            shell: bash
            run: |
              set -euo pipefail

              # Core profile: minimal deterministic gates for first-time adopters
              REQ=(
                pass_controls_refusal
                pass_controls_sanit
                sanitization_effective
                q1_grounded_ok
                q4_slo_ok
              )

              python "${PACK_DIR}/tools/check_gates.py" \
                --status "${PACK_DIR}/artifacts/status.json" \
                --require "${REQ[@]}"

          - name: Export JUnit & SARIF
            if: always()
            shell: bash
            run: |
              set -euo pipefail
              mkdir -p reports

              # PULSE converters expect status.json in cwd
              cp "${PACK_DIR}/artifacts/status.json" status.json

              python "${PACK_DIR}/tools/status_to_junit.py" || echo "JUnit export failed (optional)"
              python "${PACK_DIR}/tools/status_to_sarif.py" || echo "SARIF export failed (optional)"

              if [ -f junit.xml ]; then
                mv junit.xml reports/junit.xml
              fi
              if [ -f sarif.json ]; then
                mv sarif.json reports/sarif.json
              fi

          - name: Upload PULSE Core artefacts
            if: always()
            uses: actions/upload-artifact@v4
            with:
              name: pulse-core-report
              path: |
                ${{ env.PACK_DIR }}/artifacts/**
                reports/junit.xml
                reports/sarif.json

This job:

1. locates the PULSE safe-pack,
2. runs the pack (`tools/run_all.py`),
3. enforces **only** the Core gate set (fail-closed),
4. exports JUnit + SARIF,
5. uploads artefacts for later inspection.

---

## 5. Interpreting the results

After a Core run you get at least:

- `PULSE_safe_pack_v0/artifacts/status.json`  
  → machine-readable gate outcomes and metrics.
- `PULSE_safe_pack_v0/artifacts/report_card.html`  
  → human-readable Quality Ledger excerpt for the run.
- `reports/junit.xml`  
  → gates surfaced as tests in the CI “Tests” tab.
- `reports/sarif.json`  
  → optional code-scanning style issues (if your CI supports SARIF).

Typical flow:

- **All Core gates PASS**  
  → the Core job succeeds, and the release can continue.

- **Any Core gate FAILS**  
  → the Core job fails, and the release is blocked until:
  - the underlying issue is fixed, or
  - thresholds / policies are consciously updated in your own process.

---

## 6. What’s next?

Once the Core profile feels stable in your pipeline, you can gradually enable:

- EPF / paradox overlays,
- Stability Map generation,
- the Decision Engine in shadow mode,
- G-field / GPT overlays for governance views.

These advanced layers are part of the broader governance and topology story  
and can be adopted incrementally **without weakening** the Core fail-closed gates.

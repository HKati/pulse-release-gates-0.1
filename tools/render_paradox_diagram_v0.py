name: Pulse • Paradox Gate (shadow)

on:
  pull_request: {}
  push:
    branches: [ main ]

# Default to least privilege; PR commenting job overrides as needed.
permissions:
  contents: read

concurrency:
  group: paradox-gate-${{ github.ref }}
  cancel-in-progress: true

env:
  GATE_REPO: HKati/pulse-release-gates-0.1
  GATE_REF: gate-v0-zip   # pin to the released tag (consider pinning to a commit SHA for stronger supply-chain)

jobs:
  paradox_gate:
    name: Run Paradox Gate (shadow)
    runs-on: ubuntu-latest
    timeout-minutes: 10

    outputs:
      summary_present: ${{ steps.export.outputs.summary_present }}
      summary_b64: ${{ steps.export.outputs.summary_b64 }}
      metrics_src: ${{ steps.metrics_src.outputs.src }}
      gate_rc: ${{ steps.run_gate.outputs.rc }}

    steps:
      - name: Checkout Pulse repo
        uses: actions/checkout@8e8c483db84b4bee98b60c0593521ed34d9990e8 # v6.0.1
        with:
          fetch-depth: 1
          persist-credentials: false

      - name: Checkout gate repo (tag)
        uses: actions/checkout@8e8c483db84b4bee98b60c0593521ed34d9990e8 # v6.0.1
        with:
          repository: ${{ env.GATE_REPO }}
          ref: ${{ env.GATE_REF }}
          path: ./.gates
          fetch-depth: 1
          persist-credentials: false

      - name: Verify gate kit exists
        shell: bash
        run: |
          set -euo pipefail
          test -f ./.gates/pulse_paradox_gate_ci_v1.zip || {
            echo "::error::Missing ./.gates/pulse_paradox_gate_ci_v1.zip in gate repo checkout."
            ls -la ./.gates || true
            exit 1
          }

      - name: Unpack Paradox Gate kit
        shell: bash
        run: |
          set -euo pipefail
          rm -rf ./.gates/_ex
          unzip -q ./.gates/pulse_paradox_gate_ci_v1.zip -d ./.gates/_ex

          G=".gates/_ex/pulse_paradox_gate_ci_v1/pulse/gates/paradox"
          test -f "$G/gate.py" || {
            echo "::error::gate.py not found after unzip at: $G/gate.py"
            find ./.gates/_ex -maxdepth 5 -type f | sed 's/^/ - /' || true
            exit 1
          }

      - name: Decide metrics source (log vs env fallback)
        id: metrics_src
        shell: bash
        run: |
          set -euo pipefail
          if [ -f "logs/decision_log.ndjson" ]; then
            echo "src=log" >> "$GITHUB_OUTPUT"
            echo "PF_DECISION_LOG=logs/decision_log.ndjson" >> "$GITHUB_ENV"
            echo "Using Decision Log at logs/decision_log.ndjson"
          else
            echo "src=env" >> "$GITHUB_OUTPUT"
            echo "PF_PARADOX_DENSITY=0.0" >> "$GITHUB_ENV"
            echo "PF_SETTLE_P95_MS=0" >> "$GITHUB_ENV"
            echo "PF_DOWNSTREAM_ERROR_RATE=0.0" >> "$GITHUB_ENV"
            echo "No decision log found; using env fallback metrics."
          fi

      - name: Set up Python
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405 # v6.2.0
        with:
          python-version: "3.11"

      - name: Install minimal deps (gate runtime)
        shell: bash
        run: |
          set -euo pipefail
          python -m pip install -U pip
          python -m pip install pyyaml

      - name: Run Paradox Gate (shadow, non-blocking)
        id: run_gate
        shell: bash
        continue-on-error: true
        run: |
          set -euo pipefail
          mkdir -p artifacts

          G=".gates/_ex/pulse_paradox_gate_ci_v1/pulse/gates/paradox"

          rc=0
          set +e
          python "$G/gate.py" --mode shadow --policy "$G/policy.yaml"
          rc=$?
          set -e

          echo "rc=$rc" >> "$GITHUB_OUTPUT"
          if [ "$rc" -ne 0 ]; then
            echo "::warning::Paradox gate exited non-zero (rc=$rc) in shadow mode."
          fi

      - name: Workflow summary (paradox gate)
        if: always()
        shell: bash
        run: |
          set -euo pipefail

          echo "## Paradox gate (shadow)" >> "$GITHUB_STEP_SUMMARY"
          echo "" >> "$GITHUB_STEP_SUMMARY"
          echo "- metrics source: \`${{ steps.metrics_src.outputs.src }}\`" >> "$GITHUB_STEP_SUMMARY"
          echo "- gate rc: \`${{ steps.run_gate.outputs.rc }}\`" >> "$GITHUB_STEP_SUMMARY"

          if [ -f "artifacts/pulse_paradox_gate_summary.json" ]; then
            echo "- summary: \`artifacts/pulse_paradox_gate_summary.json\` (present)" >> "$GITHUB_STEP_SUMMARY"
          else
            echo "- summary: _missing_" >> "$GITHUB_STEP_SUMMARY"
          fi

      - name: Export summary for PR comment job (base64)
        id: export
        if: always()
        shell: bash
        run: |
          set -euo pipefail
          f="artifacts/pulse_paradox_gate_summary.json"
          if [ -f "$f" ]; then
            b64="$(base64 -w 0 "$f")"
            echo "summary_present=true" >> "$GITHUB_OUTPUT"
            echo "summary_b64=$b64" >> "$GITHUB_OUTPUT"
          else
            echo "summary_present=false" >> "$GITHUB_OUTPUT"
            echo "summary_b64=" >> "$GITHUB_OUTPUT"
          fi

      - name: Upload Paradox Gate summary (artifact)
        if: always()
        uses: actions/upload-artifact@b7c566a772e6b6bfb58ed0dc250532a479d7789f # v6.0.0
        with:
          name: pulse-paradox-gate-summary
          if-no-files-found: warn
          path: artifacts/pulse_paradox_gate_summary.json

  pr_comment:
    name: PR triage comment (shadow)
    if: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.repo.full_name == github.repository }}
    needs: [paradox_gate]
    runs-on: ubuntu-latest
    timeout-minutes: 5

    permissions:
      contents: read
      pull-requests: write
      issues: write

    steps:
      - name: Checkout base (safe tools for commenting)
        uses: actions/checkout@8e8c483db84b4bee98b60c0593521ed34d9990e8 # v6.0.1
        with:
          ref: ${{ github.event.pull_request.base.sha }}
          fetch-depth: 1
          persist-credentials: false

      - name: Set up Python
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405 # v6.2.0
        with:
          python-version: "3.11"

      - name: Rehydrate paradox gate summary (if present)
        shell: bash
        run: |
          set -euo pipefail
          mkdir -p artifacts

          if [ "${{ needs.paradox_gate.outputs.summary_present }}" = "true" ]; then
            echo "${{ needs.paradox_gate.outputs.summary_b64 }}" | base64 -d > artifacts/pulse_paradox_gate_summary.json
            echo "Rehydrated artifacts/pulse_paradox_gate_summary.json"
          else
            echo "::warning::No paradox gate summary produced; will post a minimal triage note."
          fi

      - name: Generate PR triage comment (why it failed / what to fix)
        id: triage
        shell: bash
        continue-on-error: true
        run: |
          set -euo pipefail

          marker="<!-- pulse-triage -->"
          out="triage_comment.md"

          if [ "${{ needs.paradox_gate.outputs.summary_present }}" != "true" ]; then
            cat > "$out" <<EOF
          ${marker}
          ### Paradox Gate (shadow) — no summary produced

          The shadow gate did not produce \`artifacts/pulse_paradox_gate_summary.json\`.

          - metrics source: \`${{ needs.paradox_gate.outputs.metrics_src }}\`
          - gate rc: \`${{ needs.paradox_gate.outputs.gate_rc }}\`

          Please check the workflow logs for unzip/runtime failures.
          EOF
            exit 0
          fi

          if [ ! -f "tools/gh_pr_comment_triage.py" ]; then
            cat > "$out" <<EOF
          ${marker}
          ### Paradox Gate (shadow) — triage tool missing

          \`tools/gh_pr_comment_triage.py\` is missing on the base branch checkout, so no detailed triage comment was generated.
          EOF
            exit 0
          fi

          python tools/gh_pr_comment_triage.py \
            --summary artifacts/pulse_paradox_gate_summary.json \
            --out "$out"

      - name: Contract check (paradox diagram input v0)
        if: always()
        shell: bash
        run: |
          set -euo pipefail
          f="PULSE_safe_pack_v0/artifacts/paradox_diagram_input_v0.json"
          if [[ ! -f "$f" ]]; then
            echo "::warning::missing $f (triage did not produce diagram input)"
            exit 0
          fi
          python scripts/check_paradox_diagram_input_v0_contract.py --in "$f" || \
            echo "::warning::paradox diagram input contract check failed (shadow; non-gating)"

      - name: Render Paradox diagram (v0 SVG)
        if: always()
        shell: bash
        run: |
          set -euo pipefail

          IN="PULSE_safe_pack_v0/artifacts/paradox_diagram_input_v0.json"
          OUT="PULSE_safe_pack_v0/artifacts/paradox_diagram_v0.svg"

          if [[ ! -f "$IN" ]]; then
            echo "::warning::missing $IN; skipping Paradox diagram render"
            exit 0
          fi

          # Best-effort: never fail the job because SVG rendering failed.
          if ! python tools/render_paradox_diagram_v0.py --in "$IN" --out "$OUT"; then
            echo "::warning::Paradox diagram render failed; skipping SVG artifact"
            exit 0
          fi

          if [[ ! -f "$OUT" ]]; then
            echo "::warning::renderer did not produce $OUT"
            exit 0
          fi

      - name: Upload paradox diagram input (v0)
        if: always()
        uses: actions/upload-artifact@b7c566a772e6b6bfb58ed0dc250532a479d7789f # pinned
        with:
          name: paradox-diagram-input-v0
          if-no-files-found: warn
          path: |
            PULSE_safe_pack_v0/artifacts/paradox_diagram_input_v0.json
            PULSE_safe_pack_v0/artifacts/paradox_diagram_v0.svg

      - name: Post or update PR comment
        continue-on-error: true
        uses: actions/github-script@ed597411d8f924073f98dfc5c65a23a2325f34cd # v8.0.0
        with:
          script: |
            const fs = require('fs');
            const path = 'triage_comment.md';
            if (!fs.existsSync(path)) {
              console.log('No triage_comment.md found — skipping PR comment.');
            } else {
              const body = fs.readFileSync(path, 'utf8');
              const marker = '<!-- pulse-triage -->';
              const { data: comments } = await github.rest.issues.listComments({
                owner: context.repo.owner,
                repo: context.repo.repo,
                issue_number: context.issue.number
              });
              const existing = comments.find((c) => c.body && c.body.includes(marker));
              if (existing) {
                await github.rest.issues.updateComment({
                  owner: context.repo.owner,
                  repo: context.repo.repo,
                  comment_id: existing.id,
                  body
                });
              } else {
                await github.rest.issues.createComment({
                  owner: context.repo.owner,
                  repo: context.repo.repo,
                  issue_number: context.issue.number,
                  body
                });
              }
            }

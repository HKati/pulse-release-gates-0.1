# PULSE Runbook — 5‑minute quickstart (+ governance triage)

This page shows the minimal, copy‑pasteable way to run PULSE locally and where to find the outputs.
No external runners are required.

## Local (Linux/macOS, Python 3.11)

Run:

    python PULSE_safe_pack_v0/tools/run_all.py

Outputs (always):

    PULSE_safe_pack_v0/artifacts/status.json
    PULSE_safe_pack_v0/artifacts/report_card.html

Optional outputs (if exporters are wired in your run/CI):

    reports/junit.xml
    reports/sarif.json


## When CI is red: fastest path

1) Open the failing job logs and look for a short code or a clear failure reason.
2) If the failure is a governance guard, use the section below (GOV‑00x).
3) Apply the fix and re-run CI.

Governance guards are intentionally fail‑closed: they exist to prevent silent semantic drift.


## Governance failures (fail‑closed guards)

### GOV‑001 — Unreleased coverage missing (semantic changelog enforcement)

Meaning:
- A release‑meaning file changed, but `docs/policy/CHANGELOG.md` has no entry under `Unreleased`.

Typical triggers:
- `pulse_gate_policy_v0.yml`
- `metrics/specs/**`
- dataset‑manifest contracts / specs / schemas (repo‑specific “release‑meaning” set)

Fix:
1) Add a short entry under `Unreleased` in `docs/policy/CHANGELOG.md` describing:
   - what changed
   - why it changed
   - (if applicable) the spec id/version that changed
2) Re-run CI.

Notes:
- This guard is an audit trail: it forces the semantic delta to be explicit.


### GOV‑002 — Duplicate YAML key found (unique‑keys guard)

Meaning:
- A YAML mapping contains duplicate keys; some YAML parsers silently overwrite earlier keys (“last wins” drift).

Fix:
- Remove/merge the duplicate keys in the reported YAML file(s).

Local preflight:

    python tools/check_yaml_unique_keys.py pulse_gate_registry_v0.yml pulse_gate_policy_v0.yml


### GOV‑003 — Gate id missing in registry (status.json ↔ registry sync)

Meaning:
- `status.json` emitted a gate id that is not present in `pulse_gate_registry_v0.yml`.

Why this exists:
- Prevents “new gates” from being introduced without a registry entry (name/intent/metadata).

Fix options:
- Register the new gate id in `pulse_gate_registry_v0.yml` (preferred), or
- Stop emitting the gate id from the producer/augmenter.

Local preflight (see `--help` for expected args, if any):

    python tools/check_gate_registry_sync.py --help


### GOV‑004 — Policy ↔ registry mismatch (consistency guard)

Meaning:
- Policy requires a gate that does not exist in the registry (or does not match expected registry metadata).

Fix:
- Update policy or registry so required gates are registered consistently.

Local preflight:

    python tools/tools/check_policy_registry_consistency.py --help


### GOV‑005 —  Strict external evidence required (manual or version tag)

Meaning:
- The run required external evidence (e.g. an “evidence present” gate), but evidence was missing/empty.

When it happens:
- Typically on workflow dispatch with `strict_external_evidence=true`, or other release‑like enforcement modes.

Fix:
- Provide the expected external summaries/artifacts for the run, then re-run CI.
- Only disable strict mode for non‑release runs where external tools are intentionally not connected.

Triage tip:

- Check the job summary: it prints require_set and strict_external_evidence with event/ref context.
 
Rule of thumb:
- “Missing evidence” is acceptable only when the pipeline is explicitly configured to be non‑strict for that run type.


### GOV‑006 — External evidence parse error (fail‑closed parsing)

Meaning:
- An external evidence file exists but is invalid/unreadable JSON.

Fix:
- Regenerate the evidence artifact and ensure it is valid JSON before re-running CI.

Rule:
- “Present but broken” must never be treated as PASS.


GOV‑007 — Workflow YAML parse failure (unquoted ':' in step name)
Meaning:

A GitHub Actions workflow YAML file failed to parse. A common footgun is an unquoted ':' followed by whitespace inside a step name.

Typical symptoms:

- "Unquoted ':' in step name. Quote the value of - name: ..."
- "YAML parse error: mapping values are not allowed here"

Fix:

- Prefer avoiding ':' in step names, or quote the entire step name using ASCII quotes.
- If your editor tends to auto-replace quotes, use a block scalar (most robust):

  - name: >-
      Enforce external evidence presence (strict: manual OR version tag)

Notes:

This is a deterministic, fail-closed guard to prevent broken workflows from silently slipping through.


## Local governance preflight (quick checks)

From repo root, these should mirror what CI enforces:

YAML unique keys:

    python tools/check_yaml_unique_keys.py pulse_gate_registry_v0.yml pulse_gate_policy_v0.yml

Gate registry sync (status.json ↔ registry):

    python tools/check_gate_registry_sync.py --help

Policy ↔ registry consistency:

    python tools/tools/check_policy_registry_consistency.py --help


## Practical tips

- If you change anything “release‑meaning” (policy/spec/contract), update `docs/policy/CHANGELOG.md` under `Unreleased` in the same PR.
- Keep diagnostic overlays CI‑neutral unless explicitly promoted into the required gate set.
- If you must break-glass, record the justification in the appropriate audit surface (ledger/changelog) per repo policy.

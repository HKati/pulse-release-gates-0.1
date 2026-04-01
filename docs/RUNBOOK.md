# PULSE Runbook

> Shortest truthful path when CI is red.  
> This page documents the current operational path, not an aspirational one.  
> If this page and the committed workflow disagree, follow the workflow and update this page in the same PR.

---

## 1. Start with the right lane

For v0 triage and drift reproduction, the reference execution lane is:

```text
.github/workflows/pulse_core_ci.yml
```

This is not the same question as:

> Which workflow is the repo’s primary release gate?

Keep the split clear:

- **Reference triage lane:** `.github/workflows/pulse_core_ci.yml`
- **Repo-level primary release gate:** `.github/workflows/pulse_ci.yml`

Use this rule:

- reproducing a red build, baseline drift, or local-vs-CI mismatch → start with the Core lane
- reasoning about repo-level shipping behavior → inspect the active release workflow and its required gate set

Reference lane facts for the current repo state:

- runner: `ubuntu-latest`
- Python: `3.11`
- install path: `python -m pip install -r requirements.txt pytest`
- `requirements.txt` is the canonical minimal core runtime contract
- `environment.yml` is a broader convenience environment and is not by itself the reference runtime

Normative reading order:

1. `PULSE_safe_pack_v0/artifacts/status.json`
2. materialized required gate set from policy
3. `PULSE_safe_pack_v0/tools/check_gates.py`
4. `PULSE_safe_pack_v0/artifacts/report_card.html`

If these disagree, treat steps 1–3 as authoritative.

---

## 2. Fastest truthful reproduction of the reference lane

From repo root, on a bash-like shell:

```bash
set -euo pipefail

PACK_DIR="PULSE_safe_pack_v0"
STATUS="${PACK_DIR}/artifacts/status.json"

python -m pip install --upgrade pip
python -m pip install -r requirements.txt pytest

python -m pytest -q tests/test_core_baseline_v0.py

python tools/check_yaml_unique_keys.py \
  pulse_gate_registry_v0.yml \
  pulse_gate_policy_v0.yml

python "${PACK_DIR}/tools/run_all.py" --mode core

python - "$STATUS" <<'PY'
import json
from pathlib import Path
import sys

status_path = Path(sys.argv[1])
status = json.loads(status_path.read_text(encoding="utf-8"))
run_mode = ((status.get("metrics") or {}).get("run_mode"))

if run_mode != "core":
    raise SystemExit(f"Expected metrics.run_mode='core', got {run_mode!r}")

print(f"Verified metrics.run_mode={run_mode}")
PY

python tools/validate_status_schema.py \
  --schema schemas/status/status_v1.schema.json \
  --status "$STATUS"

python tools/check_gate_registry_sync.py \
  --status "$STATUS" \
  --registry pulse_gate_registry_v0.yml \
  --emit-stubs

mapfile -t REQ < <(
  python tools/policy_to_require_args.py \
    --policy pulse_gate_policy_v0.yml \
    --set core_required \
    --format newline
)

python "${PACK_DIR}/tools/check_gates.py" \
  --status "$STATUS" \
  --require "${REQ[@]}"
```

Expected core artefacts:

- `PULSE_safe_pack_v0/artifacts/status.json`
- `PULSE_safe_pack_v0/artifacts/report_card.html`

Optional reporting exports:

```bash
mkdir -p reports

python PULSE_safe_pack_v0/tools/status_to_junit.py \
  --status PULSE_safe_pack_v0/artifacts/status.json \
  --out reports/junit.xml

python PULSE_safe_pack_v0/tools/status_to_sarif.py \
  --status PULSE_safe_pack_v0/artifacts/status.json \
  --out reports/sarif.json
```

Use this section first when CI is red.  
It mirrors the current Core reference lane closely enough to be the default local truth path.

---

## 3. Pack-only smoke run (useful, but not canonical)

If you only want a quick local smoke run:

```bash
python PULSE_safe_pack_v0/tools/run_all.py
```

This is useful for fast inspection, but it is **not** the canonical Core reproduction path by itself.

It does not, by itself:

- reproduce the reference lane end-to-end
- prove you ran the pack in `core` mode
- materialize the `core_required` gate set from policy
- enforce the required gates

Rule:  
do not use a pack-only smoke run to overrule a failing Core lane.

---

## 4. How to read the result

Read outcomes in this order:

1. `status.json`
2. the materialized required gate set
3. the exit result of `check_gates.py`
4. the Quality Ledger HTML

For gate enforcement, only literal `true` counts as PASS.

`check_gates.py` exit codes:

- `0` — all required gates PASS
- `1` — one or more required gates are present but not literal `true`
- `2` — `status.json` is missing/invalid or one or more required gates are missing

The ledger is descriptive.  
`status.json` + required gates + `check_gates.py` remain authoritative.

---

## 5. When CI is red: shortest diagnosis order

1. Open the first failing job, not the last noisy one.
2. Decide which class of failure you are looking at:
   - baseline drift
   - governance guard
   - status/schema failure
   - gate enforcement failure
   - reporting/export failure
3. Reproduce the Core lane locally using section 2.
4. Fix the earliest real failure.
5. Re-run the narrowest relevant workflow first.

Bias toward the first broken invariant, not the loudest downstream symptom.

---

## 6. RUN-001 — Core run mode mismatch

### Meaning

You produced a `status.json`, but it is not marked as:

```json
"metrics": {
  "run_mode": "core"
}
```

That means you are not reproducing the current Core reference lane truthfully.

### Typical causes

- `run_all.py` was run without `--mode core`
- an older artefact was inspected by mistake
- the wrong `PACK_DIR` or artifact directory was used

### Fix

Re-run explicitly in core mode and verify the artefact again:

```bash
python PULSE_safe_pack_v0/tools/run_all.py --mode core
python - <<'PY'
import json
from pathlib import Path

status = json.loads(Path("PULSE_safe_pack_v0/artifacts/status.json").read_text(encoding="utf-8"))
print((status.get("metrics") or {}).get("run_mode"))
PY
```

Expected output:

```text
core
```

---

## 7. Governance failures (fail-closed guards)

### GOV-001 — Unreleased coverage missing

#### Meaning

A release-meaningful file changed, but `docs/policy/CHANGELOG.md` has no matching entry under **Unreleased**.

#### Typical triggers

- `pulse_gate_policy_v0.yml`
- `metrics/specs/**`
- dataset manifest contracts / schemas / examples
- status schema / contract changes

#### Fix

Add a short entry under **Unreleased** in `docs/policy/CHANGELOG.md`.

Describe:

- what changed
- why it changed
- and, when applicable, the spec / policy id and version

Re-run CI.

#### Why this guard exists

It forces semantic deltas to be explicit and reviewable.

---

### GOV-002 — Duplicate YAML key found

#### Meaning

A YAML mapping contains duplicate keys.  
Some parsers silently keep the last one, which can change meaning without an obvious diff.

#### Fix

Remove or merge the duplicate keys in the reported file.

#### Local preflight

```bash
python tools/check_yaml_unique_keys.py \
  pulse_gate_registry_v0.yml \
  pulse_gate_policy_v0.yml
```

---

### GOV-003 — Gate id missing in registry

#### Meaning

`status.json` emitted a gate id that is not registered in `pulse_gate_registry_v0.yml`.

#### Why this guard exists

It prevents new gates from appearing in enforcement or reporting without registry metadata.

#### Fix options

- register the new gate id in `pulse_gate_registry_v0.yml`, or
- stop emitting the gate id from the producer / augmenter

#### Local preflight

```bash
python tools/check_gate_registry_sync.py \
  --status PULSE_safe_pack_v0/artifacts/status.json \
  --registry pulse_gate_registry_v0.yml \
  --emit-stubs
```

---

### GOV-004 — Policy ↔ registry mismatch

#### Meaning

Policy requires a gate that is missing from the registry,  
or requires a gate that is marked non-normative by default.

#### Fix

Update policy and registry so required gates are registry-backed and remain normative by design.

If you are trying to promote a shadow signal into a blocking lane,  
do it intentionally with a new or explicitly promoted gate path.  
Do not silently repurpose an existing diagnostic signal.

#### Local preflight

```bash
python tools/tools/check_policy_registry_consistency.py \
  --registry pulse_gate_registry_v0.yml \
  --policy pulse_gate_policy_v0.yml \
  --sets required core_required
```

If you are touching release-only policy, also check `release_required`.

---

### GOV-005 — Strict external evidence required

#### Meaning

The run required external evidence, but evidence was missing or empty.

#### When it happens

Typically on:

- `workflow_dispatch` runs with `strict_external_evidence=true`
- version tag pushes such as `v*` or `V*`

#### Fix

Provide the expected external summaries / artefacts for the run, then re-run CI.

#### Rule of thumb

Missing evidence is acceptable only when the pipeline is explicitly running in a non-strict mode.

---

### GOV-006 — External evidence parse error

#### Meaning

An external evidence file exists, but the JSON is invalid or unreadable.

#### Fix

Regenerate the evidence artefact and ensure it is valid JSON before re-running CI.

#### Rule

Present-but-broken evidence must never be treated as PASS.

---

### GOV-007 — Workflow YAML parse failure

#### Meaning

A GitHub Actions workflow file failed to parse.

A common footgun is an unquoted `:` followed by whitespace inside a step name.

#### Typical symptoms

- unquoted `:` in step name
- `YAML parse error: mapping values are not allowed here`

#### Fix

- avoid `:` in step names when possible, or
- quote the whole step name using plain ASCII quotes, or
- use a block scalar when the name is long

#### Robust example

```yaml
- name: >-
    Enforce external evidence presence (strict: manual OR version tag)
```

---

## 8. Targeted local preflight commands

Use these when you do not need the full reference lane first.

### YAML duplicate-key guard

```bash
python tools/check_yaml_unique_keys.py \
  pulse_gate_registry_v0.yml \
  pulse_gate_policy_v0.yml
```

### Status schema validation

```bash
python tools/validate_status_schema.py \
  --schema schemas/status/status_v1.schema.json \
  --status PULSE_safe_pack_v0/artifacts/status.json
```

### Gate registry sync

```bash
python tools/check_gate_registry_sync.py \
  --status PULSE_safe_pack_v0/artifacts/status.json \
  --registry pulse_gate_registry_v0.yml
```

### Policy ↔ registry consistency

```bash
python tools/tools/check_policy_registry_consistency.py \
  --registry pulse_gate_registry_v0.yml \
  --policy pulse_gate_policy_v0.yml \
  --sets required core_required
```

### Materialize Core required gates from policy

```bash
python tools/policy_to_require_args.py \
  --policy pulse_gate_policy_v0.yml \
  --set core_required \
  --format newline
```

---

## 9. Practical operating rules

- If the workflow and the docs disagree, follow the workflow and fix the docs.
- If a pack-only smoke run and the Core lane disagree, trust the Core lane first.
- Treat `requirements.txt` as the current canonical core runtime contract.
- Treat `environment.yml` as convenience, not authority.
- Keep diagnostic overlays CI-neutral unless they are explicitly promoted into the required gate set.
- If you change release-meaningful semantics, update `docs/policy/CHANGELOG.md` under **Unreleased** in the same PR.
- Fix the first broken invariant before spending time on derived report failures.

---

## 10. Related docs

- `docs/STATUS_CONTRACT.md`
- `docs/status_json.md`
- `docs/QUICKSTART_CORE_v0.md`
- `docs/quality_ledger.md`
- `docs/EXTERNAL_DETECTORS.md`
- `docs/external_detector_summaries.md`
- `README.md`

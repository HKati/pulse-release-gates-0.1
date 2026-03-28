# PULSE Runbook

Minimal local run, fastest CI triage path, and fail-closed governance fixes.

---

## 1. Fastest local run

From repo root:

```bash
python PULSE_safe_pack_v0/tools/run_all.py
```

Expected outputs:

- `PULSE_safe_pack_v0/artifacts/status.json`
- `PULSE_safe_pack_v0/artifacts/report_card.html`

Optional outputs (when exporters are wired and succeed):

- `reports/junit.xml`
- `reports/sarif.json`

Recommended immediate validation:

```bash
python tools/validate_status_schema.py \
  --schema schemas/status/status_v1.schema.json \
  --status PULSE_safe_pack_v0/artifacts/status.json
```

---

## 1.5 Reference execution lane (v0)

For v0, the reference execution lane is the GitHub-hosted **PULSE Core CI**
lane.

Use it as the default reference when reproducing CI results, triaging drift, or
deciding whether a local run disagrees with the instrument’s canonical runtime
envelope.

Reference lane facts for the current repo state:

- runner: `ubuntu-latest`
- Python: `3.11`
- workflow: `.github/workflows/pulse_core_ci.yml`

Runtime notes:

- `requirements.txt` is intentionally thin and currently documents the minimal
  core dependency contract
- `environment.yml` is a broader convenience environment and must not be read as
  the primary reference lane by itself

Practical rule:

If a local run disagrees with CI, treat the reference lane first as authoritative
for v0 triage unless the discrepancy is itself the bug under investigation.

---

---

## 2. When CI is red: fastest path

1. Open the failing job logs and find the first clear failure reason.
2. If the failure is a governance guard, jump to the matching GOV-00x section below.
3. Apply the fix locally.
4. Re-run the relevant workflow.

Governance guards are intentionally fail-closed: they exist to prevent silent semantic drift.

---

## 3. Governance failures (fail-closed guards)

---

### GOV-001 — Unreleased coverage missing

#### Meaning

A release-meaning file changed, but `docs/policy/CHANGELOG.md` has no matching entry under **Unreleased**.

#### Typical triggers

- `pulse_gate_policy_v0.yml`
- `metrics/specs/**`
- dataset manifest contracts / schemas / examples
- status schema / contract changes

#### Fix

Add a short entry under **Unreleased** in `docs/policy/CHANGELOG.md`.

Describe:

- what changed,
- why it changed,
- and, when applicable, the spec / policy id and version.

Re-run CI.

#### Why this guard exists

It forces semantic deltas to be explicit and reviewable.

---

### GOV-002 — Duplicate YAML key found

#### Meaning

A YAML mapping contains duplicate keys. Some parsers silently keep the last one, which can change meaning without an obvious diff.

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

- Register the new gate id in `pulse_gate_registry_v0.yml`, or
- Stop emitting the gate id from the producer / augmenter.

#### Local preflight

```bash
python tools/check_gate_registry_sync.py \
  --status PULSE_safe_pack_v0/artifacts/status.json \
  --registry pulse_gate_registry_v0.yml
```

---

### GOV-004 — Policy ↔ registry mismatch

#### Meaning

Policy requires a gate that is missing from the registry, or requires a gate that is marked non-normative by default.

#### Fix

Update policy and registry so required gates are registered consistently and remain normative by design.

#### Local preflight

```bash
python tools/tools/check_policy_registry_consistency.py \
  --registry pulse_gate_registry_v0.yml \
  --policy pulse_gate_policy_v0.yml \
  --sets required core_required
```

---

### GOV-005 — Strict external evidence required

#### Meaning

The run required external evidence, but evidence was missing or empty.

#### When it happens

Typically on:

- `workflow_dispatch` runs with `strict_external_evidence=true`, or
- version tag pushes such as `v*` / `V*`.

#### Fix

Provide the expected external summaries / artifacts for the run.

Re-run CI.

#### Rule of thumb

Missing evidence is acceptable only when the pipeline is explicitly running in a non-strict mode.

---

### GOV-006 — External evidence parse error

#### Meaning

An external evidence file exists, but the JSON is invalid or unreadable.

#### Fix

Regenerate the evidence artifact and ensure it is valid JSON before re-running CI.

#### Rule

Present-but-broken evidence must never be treated as PASS.

---

### GOV-007 — Workflow YAML parse failure

#### Meaning

A GitHub Actions workflow file failed to parse.

A common footgun is an unquoted `:` followed by whitespace inside a step name.

#### Typical symptoms

- Unquoted `:` in step name
- `YAML parse error: mapping values are not allowed here`

#### Fix

- Prefer avoiding `:` in step names, or
- Quote the whole step name using plain ASCII quotes, or
- Use a block scalar when the name is long.

#### Robust example

```yaml
- name: >-
    Enforce external evidence presence (strict: manual OR version tag)
```

---

## 4. Local governance preflight

From repo root, these checks mirror the core fail-closed governance path:

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

---

## 5. Practical tips

- If you change anything release-meaningful, update `docs/policy/CHANGELOG.md` under **Unreleased** in the same PR.
- Keep diagnostic overlays CI-neutral unless they are explicitly promoted into the required gate set.
- If you must break-glass, record the justification in the appropriate audit surface for the repo.
- If a local preflight command fails, fix that first before re-running the full workflow.

---

## 6. Related docs

- `docs/status_json.md` — how to read `status.json`
- `docs/STATUS_CONTRACT.md` — stable public contract for `status.json`
- `docs/QUICKSTART_CORE_v0.md` — minimal Core CI wiring
- `README.md` — repo-level overview and CI model

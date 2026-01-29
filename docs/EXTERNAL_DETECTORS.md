# External detector summaries

This page explains how PULSE folds **external detector summaries** into PULSE run artefacts
(e.g., `status.json` and the Quality Ledger / report card).

This repo-level page is intentionally **entrypoint-first**.
The **canonical specification** (schemas, discovery rules, merge semantics, and any strict contracts)
lives in the safe-pack:

- `PULSE_safe_pack_v0/docs/EXTERNAL_DETECTORS.md`


## Design constraints

PULSE aims to be **deterministic** and **fail-closed**. That only works if release semantics remain stable.

External detectors must not introduce non-determinism into the *normative* release decision.
The intended pattern is:

1. Run external tools *separately* (offline or in a controlled CI job).
2. Archive their outputs as immutable artefacts (**JSON / JSONL summaries**).
3. Have PULSE **read and merge the archived summaries** into `status.json` and the Quality Ledger.

Important:
- If a diagnostic artefact is missing, reports may show `MISSING/UNKNOWN`, but it must **never**
  be silently interpreted as `PASS`.


## What is an “external detector”?

An external detector is any independent tool that produces a structured assessment of model behavior
(safety policy checks, prompt-injection resilience, harmful content, jailbreak susceptibility, etc.).

Examples (not exhaustive): Llama Guard / Guardrails, Prompt Guard, Garak, Azure Evaluations,
Promptfoo, DeepEval, custom org-internal scanners.


## What PULSE consumes (high level)

PULSE can consume one or more external summaries in:

- **JSON**: a single summary object
- **JSONL**: one record per line (events/check records)

The authoritative accepted formats and merge behavior are defined in:
- `PULSE_safe_pack_v0/docs/EXTERNAL_DETECTORS.md`

Recommended characteristics for summaries:
- **Self-describing**: tool name + version + run id
- **Stable check IDs**: so results can be compared over time
- **Per-check outcomes**: pass/fail or scored, plus severity
- **Evidence pointers**: link to artefacts/log snippets rather than embedding huge blobs


### Minimal JSON example (illustrative — not a contract)

```json
{
  "tool": "example-detector",
  "tool_version": "1.2.3",
  "run_id": "ci-12345",
  "generated_at": "2026-01-29T12:00:00Z",
  "checks": [
    {
      "id": "prompt_injection",
      "pass": true,
      "severity": "low",
      "summary": "No successful injections observed in the evaluated set.",
      "evidence": {
        "artifact": "reports/example-detector.jsonl",
        "sample_count": 200
      }
    }
  ]
}
```


### Minimal JSONL example (illustrative)

Each line is a JSON object (event/check record):

```jsonl
{"check_id":"prompt_injection","pass":true,"severity":"low","note":"..."}
{"check_id":"toxicity","pass":false,"severity":"high","note":"...","evidence":{"example":"..."}}
```


## How summaries appear in PULSE outputs

When provided, external summaries are:
- merged into `status.json` as structured evidence, and
- surfaced in the Quality Ledger / report card for human review.

If you enable strict evidence requirements (see below), missing summaries become a **release blocker**
(fail-closed), not merely a diagnostic warning.


## Gating semantics

By default, external summaries are optional: you can adopt PULSE without them.

When you want “evidence required” semantics, enable **strict external evidence** in CI.
In this repo’s CI wiring, strict external evidence is typically enabled:
- on version tag pushes (`v*` / `V*`), and/or
- via workflow-dispatch input (e.g., `strict_external_evidence=true`).

In strict mode, CI additionally requires gates such as:
- `external_summaries_present`
- `external_all_pass`

(Use the workflow + gate policy as the authoritative required gate set.)


## External Detectors Policy (v0.1)

The following policy describes recommended hardening when external detectors are used.

- **Allow-list:** only call detectors hosted on domains listed under `profiles/*` →
  `external_detectors.allow_domains`.
- **Timeouts:** enforce `timeout_ms_per_call` and `timeout_ms_overall`; on timeout/network error →
  deterministic `FAIL` (fail-closed).
- **Versioning:** record each detector as `name@sha256:...` inside `status.json`.
- **Audit:** include number/status of calls and total wall time in the Quality Ledger notes.


## Security & hygiene

- Treat external summaries as **untrusted input**:
  validate schema and never execute content from them.
- Do not embed secrets (API keys) or sensitive user data in summaries.
- Prefer immutable artefacts (CI artifacts, pinned datasets/registries, checksums) to preserve auditability.
- Pin tool versions and/or binary digests to avoid silent behavior changes.


## Where to go next

- Canonical external detector spec:
  `PULSE_safe_pack_v0/docs/EXTERNAL_DETECTORS.md`
- `status.json` contract: `docs/STATUS_CONTRACT.md`
- `status.json` reading guide: `docs/status_json.md`
- Quality Ledger layout: `docs/quality_ledger.md`
- Related external signal: `docs/refusal_delta_gate.md`

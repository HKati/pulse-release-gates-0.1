# README Deep Terminology Cleanup Backlog — 2026-05-23

Status: deferred cleanup backlog  
Scope: README deep sections / terminology hygiene / non-urgent recognition-surface cleanup  
Authority status: non-normative documentation backlog

## Core statement

The README front-door release-authority category signal has been restored.

The current README first-screen / front-door section should remain anchored on:

- PULSE as an evolving artifact-bound release-authority field instrument;
- the structural gap between probabilistic AI behavior and deterministic software release permission;
- the break from process-based trust to evidence-state release authority;
- PULSEmech as an artifact-bound, policy-declared, gate-materialized, CI-enforced evidence-to-decision path;
- the declared-policy gate-enforcement CI outcome as the release decision.

This backlog records remaining deeper README terminology cleanup items.

These items are not urgent release-authority issues.

They are known terminology debt in older / deeper README sections.

## Why this is deferred

The urgent front-door correction has already been handled.

The remaining terms appear mainly in deeper shadow / EPF / topology / historical / optional sections.

They can still create mild recognition-surface noise if a machine reader consumes the full README, but they do not redefine the normative PULSE release-authority path.

This cleanup is therefore postponed until there is time or until a sufficiently reliable Codex pass can handle it without rewriting the PULSE identity.

## Non-negotiable boundary

This cleanup must not change release mechanics.

Do not touch:

- `.zenodo.json`;
- `CITATION.cff`;
- GitHub release notes;
- DOI records;
- Zenodo metadata;
- release policy;
- gate registry;
- `check_gates.py`;
- status schemas;
- workflow release-gating semantics;
- Quality Ledger authority status;
- release authority manifest authority status;
- audit bundle authority status;
- release semantics.

This backlog is documentation-only.

It does not authorize, block, override, or create release authority.

## Normative release-authority path

The normative PULSE release decision remains:

recorded release evidence  
→ `status.json`  
→ declared gate policy  
→ materialized required gate set  
→ strict fail-closed CI gate enforcement  
→ declared-policy CI allow/block release decision

All cleanup work must preserve this path.

## Known deeper README terminology debt

The following terms may still appear in deeper README sections and can be cleaned later.

### 1. `layer`

Potential replacement:

- `diagnostic surface`;
- `diagnostic field point`;
- `authority-status surface`;
- `optional analysis surface`.

Use judgment.

Do not rename files, schemas, workflow names, tool names, or historical document titles just because they contain `layer`.

### 2. `shadow layer`

Potential replacement:

- `shadow diagnostic surface`;
- `shadow diagnostic field point`;
- `non-normative diagnostic surface`.

Preserve `shadow` where it identifies an existing workflow, artifact, or registry name.

The cleanup target is the false architectural implication of a core/layer system, not the removal of all shadow terminology.

### 3. `diagnostic layer`

Potential replacement:

- `diagnostic surface`;
- `CI-neutral diagnostic surface`;
- `non-normative diagnostic field point`.

### 4. `EPF layer`

Potential replacement:

- `EPF diagnostic surface`;
- `EPF shadow diagnostic surface`;
- `EPF non-normative field point`.

### 5. `hazard layer`

Potential replacement:

- `hazard diagnostic surface`;
- `EPF hazard diagnostic overlay`.

### 6. `topology layer`

Potential replacement:

- `topology diagnostic surface`;
- `topology field-state diagnostic surface`.

### 7. `governance dashboards`

Potential replacement:

- `diagnostic dashboards`;
- `reader dashboards`;
- `review dashboards`.

Avoid making governance the dominant category signal for PULSE.

### 8. `release-governance layer`

Potential replacement:

- `release-authority field`;
- `release-authority materialization path`;
- `release-authority evidence field`.

### 9. `pipeline`

Potential replacement where appropriate:

- `workflow execution path`;
- `diagnostic processing path`;
- `release-authority materialization path`.

Do not ban the word `pipeline` where it describes an actual implementation path.

Only replace it when it causes PULSE itself to be read as a pipeline identity.

### 10. `architecture`

Potential replacement where appropriate:

- `materialization map`;
- `evidence-to-decision map`;
- `authority-boundary map`;
- `field map`.

Do not rename historical files unless a separate review approves that change.

## Cleanup rule

Do not perform blind global search-and-replace.

Every change must preserve:

- technical meaning;
- existing file paths;
- existing workflow names;
- existing artifact names;
- existing schema names;
- existing documented references;
- authority-boundary semantics.

## Recommended future PR scope

Suggested PR title:

`docs: clean deep README diagnostic terminology`

Suggested changed files:

- `README.md`
- optional test / anchor note only if needed

Suggested non-changes:

- no Zenodo;
- no citation metadata;
- no releases;
- no policy;
- no gates;
- no workflows;
- no schemas.

## Suggested Codex instruction for future cleanup

When this task is assigned to Codex, use this instruction:

```text
Task: Deep README terminology cleanup.

Do not change the README front-door section.

Do not change `.zenodo.json`, `CITATION.cff`, release notes, DOI records, policy, gates, schemas, workflows, or release mechanics.

Work only on deeper README sections below the front-door / Start here area.

Replace misleading core/layer/framework/governance terminology only where it falsely suggests that PULSE is a governance framework, layer system, or dashboard.

Preserve existing file paths, tool names, workflow names, schema names, and artifact names.

Preferred replacements:

- layer -> diagnostic surface / field point
- shadow layer -> shadow diagnostic surface / non-normative diagnostic field point
- diagnostic layer -> diagnostic surface
- EPF layer -> EPF diagnostic surface
- topology layer -> topology diagnostic surface
- governance dashboards -> diagnostic dashboards / reader dashboards
- release-governance layer -> release-authority field / release-authority materialization path

Do not perform blind global replacement.

After edits, run the README front-door category-signal guard and verify that the front-door anchors remain unchanged.
```

## Acceptance criteria for future cleanup

A future cleanup PR is acceptable only if:

- the README front-door release-authority section remains intact;
- the README still says what PULSE mechanically is;
- no release-authority semantics change;
- no Zenodo / citation / DOI / release metadata changes;
- no workflow / gate / policy / schema changes;
- no file paths are broken;
- diagnostic surfaces remain non-normative unless explicitly policy-routed.

## Current status

Front-door category signal:

closed / restored

Deep README terminology cleanup:

known / deferred / non-urgent

Release-authority mechanics:

unchanged

Zenodo:

untouched

## Summary

The important work is done: the README front door now starts from the PULSE release-authority mechanics.

The remaining deep README terminology cleanup is useful but not urgent.

It should be treated as documentation hygiene, not as a release-authority repair.

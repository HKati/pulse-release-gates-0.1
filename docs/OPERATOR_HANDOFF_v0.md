# PULSE Operator Handoff v0

## Purpose

This document defines the minimum operator handoff evidence for PULSE.

The goal is to make the release-authority path reproducible from repository
artifacts, policies, schemas, fixtures, workflows, and deterministic checks
without relying on private maintainer memory.

This document does not define a new release gate.

It defines how a new operator can reconstruct the PULSE release-decision
mechanics from the repository state.

## Scope

This handoff protocol covers:

- the normative release-authority path,
- the separation between release authority and diagnostic surfaces,
- the minimum checks a new operator should run,
- the artifacts and policies that must be inspectable,
- the conditions under which an operator handoff is mechanically reproducible.

This handoff protocol does not cover:

- project ownership,
- repository governance roles,
- maintainer approval rights,
- publication permissions,
- emergency organizational decisions.

Those remain human governance concerns.

## Core principle

PULSE separates human stewardship from release authority.

Human maintainers may review, merge, curate, and operate the repository.

Release decisions, however, are defined by mechanical state:

- artifact-level status,
- materialized gate requirements,
- policy and registry files,
- schemas,
- fixtures,
- workflows,
- and deterministic checkers.

A maintainer may operate the system, but private maintainer memory is not
release authority.

If a release decision cannot be reconstructed from repository artifacts and
deterministic checks, it is not a complete PULSE release-authority record.

## Release-authority path

The normative PULSE release-authority path is reconstructed from:

- `PULSE_safe_pack_v0/artifacts/status.json`
- the workflow-materialized required gate set
- `PULSE_safe_pack_v0/tools/check_gates.py`
- `pulse_gate_policy_v0.yml`
- `pulse_gate_registry_v0.yml`
- the primary release-gating workflow:
  - `.github/workflows/pulse_ci.yml`

The release-authority path is artifact-defined.

Shadow outputs, overlays, diagnostic summaries, registry entries, Pages
views, dashboards, and publication surfaces do not define release outcomes
unless explicitly promoted into the required gate set by policy and workflow.

## Status artifact prerequisite

A clean checkout does not by itself guarantee the presence of the live
release-authority artifact:

- `PULSE_safe_pack_v0/artifacts/status.json`

Before running gate reconstruction commands, the operator must either:

1. generate a local Core status artifact, or
2. provide an archived `status.json` from the CI/release run being inspected.

The handoff record must state which artifact source was used.

A locally generated Core artifact is suitable for Core-lane reconstruction.

A release-grade handoff requires a release-grade status artifact from the
relevant workflow run, or an equivalent locally produced release-grade artifact
with the same evidence conditions.

A Core-only status artifact must not be treated as release-grade evidence.

## Operator handoff condition

An operator handoff is mechanically reproducible when a new operator can,
from a clean checkout plus a generated or archived `status.json` artifact:

1. identify the primary release-gating workflow,
2. identify which workflows are diagnostic or publication-only,
3. inspect the current `status.json`,
4. materialize the relevant gate set from policy,
5. run `check_gates.py` against the materialized gate set,
6. validate the gate registry / policy consistency path,
7. validate the shadow layer registry,
8. identify which shadow surfaces are non-normative,
9. inspect the Quality Ledger or generated report artifacts when present,
10. explain which artifact and gate set defined the release decision.

The practical test is not whether the original maintainer is available.

The practical test is whether the release-decision mechanics can be
reconstructed from repository state and the relevant release artifact.

## Minimum handoff checklist

A new operator should be able to answer the following questions.

### 1. What blocks shipping?

The operator must identify:

- `.github/workflows/pulse_ci.yml`
- `PULSE_safe_pack_v0/tools/check_gates.py`
- `PULSE_safe_pack_v0/artifacts/status.json`
- the materialized required gate set used by the workflow

The operator must not treat shadow workflows, renderers, Pages outputs,
or diagnostic overlays as release-authority sources.

### 2. What is the current gate policy?

The operator must inspect:

- `pulse_gate_policy_v0.yml`
- `pulse_gate_registry_v0.yml`
- `docs/GATE_SETS.md`
- `docs/STATUS_CONTRACT.md`
- `docs/status_json.md`

The operator should be able to distinguish:

- `core_required`
- `required`
- `release_required`
- advisory / diagnostic gates

### 3. What artifact defines the current decision?

The operator must inspect:

- `PULSE_safe_pack_v0/artifacts/status.json`

The operator must understand that the normative gate state is read from:

- `status["gates"]`

Top-level mirrors, dashboards, rendered HTML, Pages output, and `meta.*`
diagnostics are not the release authority unless explicitly specified by
policy and workflow.

### 4. How is the gate set materialized?

The operator should be able to run the policy materialization helper:

```bash
python tools/policy_to_require_args.py \
  --policy pulse_gate_policy_v0.yml \
  --set core_required
```

For release-grade reconstruction, the operator must also materialize:

```bash
python tools/policy_to_require_args.py \
  --policy pulse_gate_policy_v0.yml \
  --set required
```

and:

```bash
python tools/policy_to_require_args.py \
  --policy pulse_gate_policy_v0.yml \
  --set release_required
```

The resulting gate list is the input to the deterministic gate checker.

### 5. Can the Core gate decision be reproduced?

For a Core-lane handoff, the operator should be able to generate or provide a
Core `status.json` artifact, materialize `core_required`, and run:

```bash
python PULSE_safe_pack_v0/tools/check_gates.py \
  --status PULSE_safe_pack_v0/artifacts/status.json \
  --require $(python tools/policy_to_require_args.py --policy pulse_gate_policy_v0.yml --set core_required)
```

A failing required gate or missing required gate must fail closed.

A missing or malformed release-authority artifact must not be silently
interpreted as PASS.

### 6. Can the release-grade gate decision be reproduced?

For a release-grade handoff, `core_required` alone is not sufficient.

The effective release-grade gate set is:

```text
required + release_required
```

The operator must use a release-grade `status.json` artifact from the
relevant workflow run, or an equivalent locally produced release-grade artifact
with the same evidence conditions.

The operator must not report a release-grade decision from a Core-only artifact
or a Core-only gate set.

### 7. Which surfaces are diagnostic only?

The operator must identify diagnostic / shadow surfaces, including but not
limited to:

- EPF shadow outputs,
- paradox summaries,
- topology overlays,
- G-field overlays,
- Relational Gain shadow artifacts,
- shadow layer registry entries,
- Pages or rendered views,
- publication workflows.

These surfaces may explain, inspect, or validate their own contracts.

They do not change release outcomes by default.

### 8. Can the shadow registry be validated?

The operator should be able to run:

```bash
python PULSE_safe_pack_v0/tools/check_shadow_layer_registry.py \
  --input shadow_layer_registry_v0.yml
```

The shadow layer registry is governance-facing and machine-readable.

Registry presence does not promote a shadow layer into release authority.

### 9. Are fixture roles clear?

The operator must understand the registry fixture-role model:

- `valid_fixtures` contains contract-valid examples,
- `invalid_fixtures` contains deliberate contract-breaking or consistency-failing examples,
- `fixtures` is a transitional alias for `valid_fixtures`,
- `fixtures` and `valid_fixtures` must not be used together in the same layer entry.

The canonical registry self-check fixtures are documented in:

- `docs/shadow_layer_registry_v0.md`

### 10. Can EPF surfaces be classified correctly?

The operator must be able to identify the current EPF split:

- `epf_shadow_run_manifest.json`
  - primary registered EPF run-manifest surface
  - diagnostic and non-normative by default

- `epf_paradox_summary.json`
  - secondary contract-hardened EPF diagnostic summary
  - diagnostic and non-normative by default

Neither EPF surface participates in release gating unless explicitly
promoted into the required gate set.

### 11. Can the Quality Ledger be inspected?

When present, the operator should inspect:

- `PULSE_safe_pack_v0/artifacts/report_card.html`
- Quality Ledger fields derived from `status.json`

The Quality Ledger is a human-readable explanation surface.

It does not override the normative `status["gates"]` decision.

## Recommended local handoff commands

A clean checkout does not by itself contain the live release-authority
`status.json` artifact.

Before running gate reconstruction commands, the operator must either:

1. generate a local Core status artifact, or
2. provide an archived `status.json` from the CI/release run being inspected.

The handoff command path must state which artifact source was used.

### Prepare a local Core status artifact

For a local Core handoff smoke, generate `status.json` first:

```bash
python PULSE_safe_pack_v0/tools/run_all.py \
  --mode core \
  --pack_dir PULSE_safe_pack_v0 \
  --gate_policy pulse_gate_policy_v0.yml
```

This writes:

```text
PULSE_safe_pack_v0/artifacts/status.json
```

The generated artifact is suitable for Core-lane reconstruction.

It is not, by itself, proof of a release-grade run.

### Core release-authority reconstruction

For the Core lane, materialize `core_required`:

```bash
python tools/policy_to_require_args.py \
  --policy pulse_gate_policy_v0.yml \
  --set core_required
```

Then run the deterministic gate checker against the generated Core
`status.json`:

```bash
python PULSE_safe_pack_v0/tools/check_gates.py \
  --status PULSE_safe_pack_v0/artifacts/status.json \
  --require $(python tools/policy_to_require_args.py --policy pulse_gate_policy_v0.yml --set core_required)
```

This reconstructs the Core lane only.

### Release-grade reconstruction

Release-grade reconstruction must not use `core_required` alone.

For a release-grade handoff, the operator must use a release-grade
`status.json` artifact from the relevant workflow run, or an equivalent
locally produced release-grade artifact with the same evidence conditions.

If the archived release-grade artifact is not located at the default path,
copy it into the expected location or set `STATUS_PATH` explicitly:

```bash
STATUS_PATH="PULSE_safe_pack_v0/artifacts/status.json"
```

The effective release-grade gate set is:

```text
required + release_required
```

Materialize and enforce that combined set:

```bash
REQ_STR="$(python tools/policy_to_require_args.py \
  --policy pulse_gate_policy_v0.yml \
  --set required \
  --format space)"

RELEASE_REQ_STR="$(python tools/policy_to_require_args.py \
  --policy pulse_gate_policy_v0.yml \
  --set release_required \
  --format space)"

read -r -a REQ <<< "$REQ_STR"
read -r -a RELEASE_REQ <<< "$RELEASE_REQ_STR"

STATUS_PATH="${STATUS_PATH:-PULSE_safe_pack_v0/artifacts/status.json}"

python PULSE_safe_pack_v0/tools/check_gates.py \
  --status "$STATUS_PATH" \
  --require "${REQ[@]}" "${RELEASE_REQ[@]}"
```

A release-grade handoff is incomplete if it omits `release_required` or uses
a Core-only status artifact as if it were release-grade evidence.

### Shadow registry validation

```bash
python PULSE_safe_pack_v0/tools/check_shadow_layer_registry.py \
  --input shadow_layer_registry_v0.yml
```

### Registry regression coverage

```bash
pytest -q tests/test_check_shadow_layer_registry.py
```

### EPF run-manifest contract coverage

```bash
pytest -q tests/test_check_epf_shadow_run_manifest_contract.py
```

### EPF paradox-summary contract coverage

```bash
pytest -q tests/test_check_epf_paradox_summary_contract.py
```

## Evidence expected from a handoff run

A complete handoff run should preserve or make inspectable:

- the exact commit SHA,
- the checked `status.json`,
- the source of the `status.json` artifact:
  - locally generated Core artifact, or
  - archived CI/release artifact,
- the materialized required gate list,
- whether the reconstruction was Core or release-grade,
- the `check_gates.py` result,
- the shadow registry checker result,
- relevant pytest results,
- the Quality Ledger or report artifact when present,
- any failure output needed to explain a non-PASS result.

A handoff record should be sufficient for another operator to determine:

- what was checked,
- which artifacts were used,
- which gate set was enforced,
- what failed or passed,
- which surfaces were diagnostic only,
- and why the release decision was or was not allowed.

## Failure conditions

A handoff is not mechanically complete if any of the following are true:

- the release decision depends on undocumented maintainer knowledge,
- the required gate set cannot be reconstructed,
- `status.json` cannot be located, generated, provided, or validated,
- a Core-only artifact is treated as release-grade evidence,
- a release-grade reconstruction omits `release_required`,
- required gates are missing and not treated as failure,
- a diagnostic surface is treated as release authority without policy promotion,
- a rendered view contradicts `status["gates"]` and is treated as authoritative,
- shadow registry entries are interpreted as normative by registry presence alone,
- fixture-role semantics are ambiguous,
- the operator cannot identify the primary release-gating workflow.

## Human responsibility

Operator reproducibility does not remove human responsibility.

Human maintainers remain responsible for:

- reviewing changes,
- approving policy changes,
- interpreting evidence,
- deciding whether to promote a diagnostic layer,
- maintaining documentation quality,
- handling security or governance exceptions.

The purpose of operator handoff is narrower:

to ensure that the release-authority mechanics are not private, implicit, or
person-bound.

## Non-goals

This document does not claim:

- that the repository has no maintainership risk,
- that human review is unnecessary,
- that all diagnostic surfaces are release-ready,
- that shadow workflows define release decisions,
- that rendered documentation is normative,
- that a clean checkout alone contains the live release artifact,
- that a Core-lane reconstruction is equivalent to release-grade reconstruction,
- that external environments have been validated unless separately documented.

This document only defines the handoff evidence required to reconstruct the
PULSE release-authority path from repository state and the relevant status
artifact.

## Maintenance rule

Any change to the release-authority path should update this document if it
changes one of the following:

- the primary release-gating workflow,
- the policy file used to materialize required gates,
- the gate registry or gate-set semantics,
- the location or semantics of `status.json`,
- the gate checker path or behavior,
- the release-grade gate-set composition,
- the shadow registry validation path,
- the EPF primary / secondary surface split,
- fixture-role semantics,
- operator handoff commands.

If the mechanics change, the handoff record must change with them.

## Summary

PULSE release authority is operator-reproducible when the release decision can
be reconstructed from repository artifacts, a generated or archived status
artifact, materialized gate requirements, schemas, fixtures, policies,
workflows, and deterministic checks.

The maintainer operates the system.

The artifacts and checks carry the release-authority path.

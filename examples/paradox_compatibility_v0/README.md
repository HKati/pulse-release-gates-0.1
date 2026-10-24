# Paradoxon PD-SM-01 — explicit-interpreter compatibility experiment

**Profile:** `PD-SM-01-E2-compat-v0`  
**Role:** opt-in research validation tooling; not a release gate  
**Historical source snapshot:** `102145d1f1c321811c52d9d20f92cc7289127b2b`  
**Historical semantic snapshot:** `cbeab94d8532482d34ab857bf38e9e56ae265f84`  
**Authority effect:** `none`

This directory makes the existing E0 experiment repeatable under four separately
observed CPython interpreters. It does not assert that the four-version experiment
has already run. It does not change the source-mapping document's historical
`NOT_RUN` status: new executions have their own records.

## Exact scope

The requested versions are **3.11.14, 3.12.12, 3.13.5 and 3.14.3**, on Linux
x86_64. They are explicit comparison references retained from the prior
compatibility proposal, not recommendations to deploy old patch releases or
claims that these versions are the latest releases.

Each interpreter must execute the same eight E0 scenarios, six control groups
and eighteen regression test methods. The six control methods are included in
the eighteen; they are not eighteen additional tests. A completed E0 run retains
48 child-invocation receipts, including the controls' deliberate negative probes.

The experiment covers the named artifact relations and proof-applicability
assessments only. It does not test arbitrary Python programs, other operating
systems, all future versions, E1's larger finite profiles, MON-1 confinement,
physical causality or a physical PULSEbox. No protected production operation is
performed and no PULSEmech `ALLOW` verdict is created.

## What is reused unchanged?

`core/` contains the five original E0 files. Their SHA-256 values, the original
source manifest and the historical environment-revision record are pinned in
`matrix_contract.json`.

- `independent_reference.py` evaluates records and admitted evidence, without
  importing producer/checker helpers or using a scenario label as a premise.
- `case_expectations.json` keeps the original expectations separate from actual
  observations. It is not rewritten after a test result.
- `test_harness.py` provides the existing eighteen regression methods.
- `run_cases.py` is the historical E0 coordinator, preserved as delivered.
- `core/README.md` documents the historical E0 package. **This README is the
  entrypoint for the new matrix**, not the old package-layout instructions.

For each actual runtime, the matrix makes a separate scratch copy. Only three
exact strings in the copied coordinator are adapted: its interpreter-version
guard, that guard's diagnostic, and the individual-runtime scope description.
The applied `environment_gate.diff` and both original/adapted code hashes are
retained. The evaluator, test cases, expectations, six existing programs and
four source inputs do not change.

`ENVIRONMENT_PROFILE_REVISION.json` preserves the original owner-approved E0
3.13.5 revision as history. A new per-runtime revision record binds the explicit
matrix execution; the historical record is not silently rewritten in this tree.

## The eight scenarios

| Scenario | Expected distinction |
|---|---|
| E00 | Complete baseline; latency relation and fixture-source construction justified. |
| E10 | Mathematical enumeration changes, with carrier bytes unchanged. |
| E11 | Same relation; the field checker rejects noncanonical Atom order. |
| E12 | Same relation; the edge checker rejects noncanonical edge order. |
| E13 | Independent canonical restoration, without rerunning producers. |
| E20 | A single changed destination violates its unchanged tension binding. |
| E30 | Unchanged carriers can pass existing output checks while missing admitted source evidence leaves provenance unresolved. |
| E40 | The existing CPU target needs its own proof; the latency certificate is not transferable unchanged. |

A correct experimental `MATCH` includes the intended E20 violation and E30
uncertainty. It never means that every variant preserves the requirement.
An absent source reconstruction is represented explicitly as absent; it is not
converted into an empty list meaning that reconstruction found no differences.

## Completion and comparison rules

`matrix.py` requires all four exact versions, CPython identity, Linux and x86_64
from actual interpreter probes. It records interpreter executable hashes,
compiler/build details, cache tag and SOABI. A path label is not proof of a
version. An alias to the same interpreter with a different version label fails.

Each row must have complete, matching E0 case/control outcomes, eighteen distinct
successful regression method records, all required stages/logs, exact source
bindings, and unchanged code/input identities. Recorded file references are
checked against their retained bytes and hashes. Timeout, crash, missing stage,
wrong rejection reason and missing interpreter cannot become a successful row.

The cross-runtime semantic projection includes joint bindings, protected
subjects, premise availability, witnesses, source assessment, proof applicability,
certificates, canonicality assessments and relevant actual process return codes.
Machine-specific paths and timestamps are not equated. Carrier digests are
reported separately; semantic agreement is not a universal byte-identity claim.

An overall `MATCH` is possible only when all four complete, valid rows have the
same semantic projection. It supports compatibility of this exact experiment
on the recorded builds, not unrestricted portability. A missing row produces
`INCOMPLETE`; a completed semantic disagreement produces `MISMATCH`.

The matrix controller returns zero only for overall `MATCH`. A run with only a
successful 3.13.5 row deliberately returns nonzero and reports `INCOMPLETE`.
Synthetic rows in `test_matrix.py` test this decision logic; they are not
substitutes for actual interpreter observations.

## Manual hosted execution

The workflow is
[`.github/workflows/paradox_compatibility_v0.yml`](../../.github/workflows/paradox_compatibility_v0.yml).
It has **only `workflow_dispatch`**, not `push` or `pull_request` triggers.
Uploading this change may still trigger the repository's existing PR checks;
that does not launch this matrix automatically.

After review and merge, the owner selects **main** in Actions, opens
**Paradoxon PD-SM-01 compatibility (manual)** and supplies `source_commit` as the
full forty-character **current main commit containing the reviewed workflow**.
This is the new integration commit, not the historical `102145d1...` source pin.
The input must equal `GITHUB_SHA` and `GITHUB_WORKFLOW_SHA`. The workflow also
checks repository, owner identity, main ref and initial run attempt before
checkout. A later retry uses a new explicit dispatch; attempts other than one
are rejected by this profile.

Two checkouts have deliberately different roles:

1. `tooling/` contains the reviewed matrix implementation at the dispatched
   commit. Its exact commit and code hashes identify the new experiment.
2. `frozen_source/` contains only the named historical source slice at
   `102145d1f1c321811c52d9d20f92cc7289127b2b`. All twelve file blobs are checked
   against `SOURCE_BINDINGS.json`; floating `main` is not substituted.

Checkout credentials are not persisted. Workflow permissions are `contents:
read`; no repository write, PR operation, release publication or model call is
part of the workflow. Actions use the repository's already pinned action
commits. Setup uses four explicit versions, does not change the ambient PATH,
and passes each action's absolute `python-path` output to the runner.

Interpreter-acquisition steps alone use `continue-on-error: true` so missing
runtimes can be recorded together. **The experiment step does not continue on
error:** missing or failed rows prevent matrix success. If even the 3.13.5
controller cannot be acquired, the workflow fails and retains an `INCOMPLETE`
setup record. There is no interpreter-version fallback.

The experiment processes use a clean environment, immutable source copies and
the original E0 network-denial control. Runtime acquisition and artifact upload
necessarily use network access outside those processes. This is not a claim that
the whole hosted job is air-gapped or a filesystem security sandbox. The runner,
controller, action implementations and source acquisition remain trusted parts
of the bounded experiment.

The workflow uploads `pd-sm-01-e2-<run_id>-<attempt>` for both successful and failed
runs after the invocation guard passes. Retention is 30 days; this is not a durable
owner-custody guarantee. Preserve the downloaded evidence before its expiry.

## Repository hygiene integration

The repository's ordinary workflow Python requirement is unchanged, as are all
existing Q2 exact patch pins. The sole additional exception recognizes this
exact manual workflow path, one `compatibility` job, four exact setup-step IDs
and the four literal versions above. Extra jobs, triggers, missing/duplicate
setup steps, altered versions or dynamic version declarations are rejected.
Other workflow paths do not inherit the exception.

`test_workflow_guard.py` executes the actual Python guard embedded in
[repo_hygiene.yml](../../.github/workflows/repo_hygiene.yml) against seventeen
bounded fixtures, including ordinary/Q2 drift and malformed versions. It runs
in the existing hygiene job using that job's existing PyYAML installation.
The E0 and matrix programs themselves use only the standard library; PyYAML is
only a workflow-guard test dependency, not a new experiment dependency.

The matrix workflow is optional to the existing synthetic Q2 guard fixtures.
If the matrix is present, the exact exception is checked. Existing mandatory Q2
workflow paths remain mandatory. This avoids silently expanding unrelated
fixture contracts while preserving their previous fail-closed rules.

## Local use

Provide a separately acquired, blob-verified historical source slice and actual
interpreter paths. No interpreter installation or network retrieval is performed
by this command:

```bash
/path/to/python3.13.5 -I -S -B examples/paradox_compatibility_v0/matrix.py \
  --source-root /absolute/path/to/frozen_source \
  --output /absolute/path/to/new-evidence-directory \
  --interpreter 3.11.14=/absolute/path/to/python3.11.14 \
  --interpreter 3.12.12=/absolute/path/to/python3.12.12 \
  --interpreter 3.13.5=/absolute/path/to/python3.13.5 \
  --interpreter 3.14.3=/absolute/path/to/python3.14.3
```

The output directory must not exist and must be outside the implementation and
source inputs. Omitting a runtime is permitted only to record its absence; it
prevents overall success. The checked source files are copied without modifying
the supplied checkout. Scratch results and generated outputs are not committed.

Controller regression command:

```bash
python -I -S -B examples/paradox_compatibility_v0/test_matrix.py
```

Workflow integration regression command, in an environment already containing
PyYAML as the existing hygiene job does:

```bash
python -B examples/paradox_compatibility_v0/test_workflow_guard.py
```

## Evidence layout

`MATRIX.json` distinguishes requested, observed, absent and failed runtime rows.
Each completed row retains `PREFLIGHT.json`, `probe.json`, `RUN.json`,
`environment_gate.diff`, `SEMANTIC_VIEW.json`, unchanged source copies, adapted
coordinator copy and the complete E0 `execution/` result/log tree. `INVOCATION.json`
records controller and hosted invocation identity. `SHA256SUMS` inventories the
retained output files; it is an integrity inventory, not an authority signature.

Historical receipts contain absolute paths from the producing environment.
Their bytes must be preserved. Inspection after download uses the retained
relative file layout plus an explicit path-prefix mapping; do not rewrite the
original receipts or claim that paths alone authenticate an artifact.

## Preparation validation versus hosted evidence

During preparation, the final controller completed the full E0 suite on the
available CPython 3.13.5 Linux x86_64 interpreter: eight matching scenarios, six
control groups and eighteen successful methods. The other three requested
interpreters were unavailable. The matrix correctly returned `INCOMPLETE`, not a
compatibility claim. Thirty-three controller regressions and seventeen actual
hygiene-guard regressions passed locally. The local guard tests used PyYAML 6.0.3;
the existing hosted hygiene job retains its own 6.0.2 pin. Hosted checks were not
run during preparation.

Two earlier development attempts are retained in the separate delivery evidence:
one wrapper failure on a legitimate absent E30 source-reconstruction field, and
one externally interrupted attempt without final completion. Neither is counted
as a completed matrix. Three additional regressions cover absence versus empty
source reconstruction in the corrected wrapper. The E0 core and expectations
were not modified to resolve the wrapper issue.

**Hosted four-version execution remains `NOT_RUN` at delivery.** Its result must
be supplied by a new, exact-run-bound artifact after explicit owner dispatch.
No release authority, full Paradoxon-mechanics closure or MON-1 portability is
implied by merging these files or by passing repository CI.

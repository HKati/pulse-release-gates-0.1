# PD-SM-02 — source-bound pre-execution impact companion v0

Status: **implementation prepared; pilot execution NOT_RUN**.  
Profile: `PD-SM-02-preexecution-impact-v0`.  
Authority effect: `none`.

This directory implements the first bounded source-to-relation companion for the
Paradoxon Diagram pre-execution impact study. It is not a general Python verifier,
a production launcher, a release gate, or a replacement for the existing
PULSEmech authority path.

The implementation answers a deliberately narrow question:

> For a closed MON-1-derived orchestration language, do the exact candidate
> source bytes preserve the declared source, request, monitoring, audit,
> acknowledgement, single-use and useful-operation relations before a protected
> scratch-file effect can occur?

The source model is derived from candidate bytes. Case IDs and expected outcomes
exist only in `fixtures.json` as test-driver metadata; they are not supplied to
the mapper or checker.

## Source and evidence basis

The design and source mapping are bound to:

```text
reviewed design snapshot:
a9de035d1b3ac227359ca78a98274abe4c9ee186

implementation preparation snapshot:
34431ec8ebe305a83273ffd39b78f083219f03e6

original E1 archive SHA-256:
88db43b1d42b98fa3fbfd63f1ce87e5e5ee787495732489c8e5a460a5fea1b21

archived enforcement_probe.py SHA-256:
7219702636681fa7109072ff532ed1dc73c5585fe45eb02d613cd9d8538c89b6
```

`profile.json` retains all thirteen inspected source-region bindings from the
reviewed PD-SM-02 source map. Those bindings are design inputs; this companion
does not rewrite the historical E1 archive or claim that the source-to-model
mapping is complete outside the closed language implemented here.

## Files

| File | Role |
|---|---|
| `profile.json` | Fixed source language, primitive semantics, domains, protected relation, finite environments and launch boundary. |
| `fixtures.json` | Exact candidate source texts, contexts and 24 separately specified test obligations. All pilot execution fields remain `NOT_RUN`. |
| `source_model.py` | Non-executing AST recognizer and typed source-derived model builder. It emits no impact verdict. |
| `check_impact.py` | Independent parser, model checker and finite relational evaluator. It does not import the mapper or candidate code. |
| `run_local.py` | Preflight by default; separately authorized scratch-only exact-byte launcher. Not executed during preparation. |
| `test_preexecution.py` | Static, record, mapping, binding, false-block and negative regressions. |

## Closed candidate language

A candidate is one zero-argument function named `candidate`. Its body may contain
only:

- single-assignment private string constants; and
- calls to the exact primitives declared in `profile.json`.

Imports, attributes, subscripts, reflection, `eval`/`exec`, loops, recursion,
conditionals, comprehensions, exception handling, arbitrary calls and native
calls are unsupported. Unsupported source is `UNRESOLVED`; it is never treated
as safe. The mapper and both independent parsers decode the bound bytes with the
profile encoding. The launcher compiles that same decoded text rather than asking
Python to reinterpret an encoding cookie in the original bytes.

The recognized primitives encode:

```text
actor and request roles
exact protected request binding
source-evidence admission
request equality and single-use checks
reservation
one-request monitor interaction
exact or deliberately weak ACK/audit checks
broker-mediated append effects
explicit direct sink routes used as negative witnesses
```

The mapper preserves every recognized effect occurrence and its source location.
It does not apply the desired invariant while constructing the model.

## Independent assessment

`check_impact.py` reparses the exact candidate bytes using a separate
implementation and checks the complete supplied model. It then enumerates the
fixed finite environments in `profile.json`, including:

```text
healthy monitoring
monitor absence
monitor exit before acknowledgement
acknowledgement without record
wrong acknowledgement
request target substitution
request payload substitution
two request attempts with one-request monitor lifetime
ACK/audit joint-identity mismatch
```

The simulation applies `bind_request`, request guards and reservations at their
actual operation positions. A reservation is request-specific, and an effect is
useful only when the effect, bound request, submitted request, reservation, ACK
and audit identify the same request.

For every modeled effect occurrence it checks jointly:

```text
source justification
exact program/request/target binding
matching intent record
matching acknowledgement
matching audit record
required source/control dependencies
single-use effect count
admitted broker effect route
```

The result separates source binding, supported-language coverage, model
nonemptiness, invariant preservation, useful operation, model counterexamples,
proof applicability and unresolved critical obligations. A model witness is not
reported as a native observation.

## Twenty-four obligations

The fixture family contains:

```text
5 positive / false-block controls
11 negative relation/effect controls
3 coverage and mapping controls
3 binding-reuse controls
2 observer and pre-execution-boundary controls
```

Notable distinctions:

- Removing only the replay-membership check is not automatically unsafe while
  the fixed monitor accepts only one request. The result is
  `PROPERTY_DEPENDENT`, not a syntactic false block.
- A later valid audit does not erase an append that occurred before monitor
  support.
- Separate true ACK and audit flags do not establish one joint witness when
  they refer to different requests.
- Losing one evidence derivation does not block the candidate when a separately
  bound grounded alternative proves the same obligation.
- A positive evidence cycle without a grounded base does not create support.
- Eliminating every effect path may satisfy safety but fails the separate useful
  operation requirement.

All entries in `fixtures.json` retain:

```text
pilot_execution_status: NOT_RUN
observed_result: null
```

## Local static and record checks

From this directory:

```sh
python -I -B -m pytest -q test_preexecution.py
```

Preparation result after the coordinated source/runtime-consistency fixes on
CPython 3.13.5/Linux:

```text
112 passed
```

These are implementation regressions. They are not 24 native pilot passes and
not a repository-wide CI result. No archived E1 program, candidate scratch
effect or GitHub workflow was executed during preparation.

Example non-executing assessment sequence:

```sh
python -I -S -B source_model.py \
  --profile profile.json \
  --candidate candidate.py \
  --output model.json

python -I -S -B check_impact.py \
  --profile profile.json \
  --candidate candidate.py \
  --model model.json \
  --context context.json \
  --output assessment.json

python -I -S -B run_local.py \
  --profile profile.json \
  --candidate candidate.py \
  --assessment assessment.json \
  --context context.json \
  --output preflight.json \
  --preflight-only
```

## Scratch launcher boundary

`run_local.py` does not launch by default. Actual execution additionally
requires:

- the exact authorization literal stored in `profile.json`;
- an independently replayed eligible assessment;
- the exact candidate, profile and context digests;
- the exact subject/request/environment binding;
- a sealed in-memory source copy; and
- a new empty output directory.

The CLI execution path also requires `--model` and replays
`check_impact.py`; the supplied assessment must be byte-equivalent under
canonical JSON to that fresh result. The launcher executes only the closed AST
language with an empty builtins namespace and scratch-only primitives.

This launcher has **not been executed in this preparation**. Its use requires a
separate owner authorization. It is not a complete sandbox, physical PULSEbox,
production enforcement boundary or release authority.

## Boundaries

```text
implementation_status: PREPARED_NOT_PUBLISHED
pilot_execution_status: NOT_RUN
production_integration_status: NOT_IMPLEMENTED
status_json_mutation: none
registered_gate: none
workflow_registration: none
authority_effect: none
```

The existing E0 evaluator, E1/MON-1 evidence, E2 compatibility result, policies,
release checker and repository workflows remain unchanged.

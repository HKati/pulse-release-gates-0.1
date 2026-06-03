# Normative vs Shadow Inventory Report Artifact Policy v0

## Purpose

Normative vs Shadow Inventory Report Artifact Policy v0 defines how generated normative/shadow inventory reports are produced, reviewed, and treated as audit evidence.

The policy prevents generated inventory output files from being mistaken for:

```text
source files
repository-state authority
release-authority artifacts
routine commit targets
```

The inventory report is a review carrier.

Generated inventory reports are evidence-review outputs, not repository state authority.

The inventory report does not create an independent release-decision engine.

## Scope

This policy applies to generated outputs from:

```text
scripts/build_normative_shadow_inventory_v0.py
```

Primary generated outputs:

```text
normative_shadow_inventory_v0.json
normative_shadow_inventory_v0.md
```

Example generated paths:

```text
out/normative_shadow_inventory_v0.json
out/normative_shadow_inventory_v0.md
```

These outputs are generated review artifacts.

They are not automatically source artifacts.

They are not repository-state authority carriers.

## Authority carrier

The PULSEmech authority carrier remains:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

The normative/shadow inventory report reviews repository surfaces around that path.

It does not alter release authority.

## Policy decision

The default policy is:

```text
run-on-demand reviewer output
```

This means:

```text
The generated inventory report is produced on demand for a declared repository state.
The generated report is reviewed as an audit / evidence-review artifact.
The generated report is not committed by default.
The generated report must not be treated as a source file merely because it was produced by a verification command.
The generated report must not be treated as repository-state authority merely because it describes repository surfaces.
```

## Generated output boundary

Generated inventory outputs are evidence-review artifacts.

They may be used to inspect:

```text
workflow classification
carrier class
authority-impacting status
drift findings
unclassified workflow warnings
publication / reader / diagnostic / shadow boundary
```

Generated inventory outputs must not silently become:

```text
source files
release authority artifacts
required gate inputs
policy artifacts
status artifacts
publication metadata
repository-state authority carriers
DOI / Zenodo artifacts
```

## Default generation location

Generated reports should be written outside the repository tree during routine review.

Recommended command:

```bash
TMPDIR="$(mktemp -d)"

python scripts/build_normative_shadow_inventory_v0.py \
  --repo-root . \
  --out-json "$TMPDIR/normative_shadow_inventory_v0.json" \
  --out-md "$TMPDIR/normative_shadow_inventory_v0.md"

git status --short
```

Expected result:

```text
working tree clean
```

The generated files should exist only under the temporary directory.

## Repository-local output

Repository-local output paths such as:

```text
out/normative_shadow_inventory_v0.json
out/normative_shadow_inventory_v0.md
```

may be used manually for inspection only when explicitly intended.

They must not be committed unless a dedicated PR declares that the repository is adopting a checked-in generated report artifact.

Routine verification must prefer temporary output paths.

## Commit boundary

Generated inventory output may be committed only when all of the following are true:

```text
the PR explicitly declares a checked-in generated report artifact
the report is generated from the intended commit / HEAD
the generated timestamp and repository identity are expected and reviewed
the PR explains why checked-in output is preferred over run-on-demand output
the generated output path is included in the declared scope
the closure matrix or related docs are updated consistently
```

Otherwise, generated inventory outputs should remain untracked review artifacts.

## Current audit record model

Current model:

```text
run-on-demand reviewer output
```

Under this model, a valid audit record is a review note containing:

```text
repository
commit / HEAD
commands run
generated output location
drift findings result
working tree status
reviewer conclusion
```

A generated report does not need to be checked into the repository for the audit result to be meaningful, as long as the run is tied to a specific commit and the working tree remains clean.

The generated report is evidence for the review run.

It is not the repository-state authority.

## Valid run-on-demand verification

A valid run-on-demand verification should include:

```bash
python -m py_compile scripts/build_normative_shadow_inventory_v0.py

python -m pytest -q tests/test_build_normative_shadow_inventory_v0.py

TMPDIR="$(mktemp -d)"

python scripts/build_normative_shadow_inventory_v0.py \
  --repo-root . \
  --out-json "$TMPDIR/normative_shadow_inventory_v0.json" \
  --out-md "$TMPDIR/normative_shadow_inventory_v0.md"

git status --short
```

The reviewer should confirm:

```text
builder compiles
inventory tests pass
JSON report is generated
Markdown report is generated
generated files are outside the repository tree
working tree is clean
unclassified workflow drift findings are absent or explicitly accepted
```

## Unclassified drift result

The generated report should be inspected for:

```text
workflow requires explicit carrier-role classification
```

If no such findings are present, the report may be summarized as:

```text
No unclassified workflow drift findings for the reviewed commit.
```

If such findings are present, the report may be summarized as:

```text
Inventory report generated, but workflow classification drift remains.
```

The finding should then be handled in a separate scoped PR.

## Closure matrix boundary

The Deep Search Critique Closure Matrix may mark the normative/shadow inventory item as internally closed only when the repository clearly states which audit-record model is used.

Accepted audit-record models:

```text
checked-in generated report artifact
stable linked generated report artifact
run-on-demand reviewer output
```

Current selected model:

```text
run-on-demand reviewer output
```

Under this model, closure is based on:

```text
builder exists
tests exist
workflow-family classifier coverage exists
reviewer can generate a clean report for a declared commit
working tree remains clean after generation
```

The closure matrix should not imply that generated `out/...` files are source artifacts.

The closure matrix should not imply that a generated inventory report is repository-state authority.

## Reviewer report format

A run-on-demand reviewer report should use this form:

```text
Normative/shadow inventory verification:
- Repository:
- Commit / HEAD:
- Builder command:
- Test command:
- Output location:
- JSON report generated: yes / no
- Markdown report generated: yes / no
- Unclassified workflow drift findings: none / listed
- Working tree clean after run: yes / no
- Conclusion:
```

Example:

```text
Normative/shadow inventory verification:
- Repository: HKati/pulse-release-gates-0.1
- Commit / HEAD: <sha>
- Builder command: scripts/build_normative_shadow_inventory_v0.py
- Test command: tests/test_build_normative_shadow_inventory_v0.py
- Output location: /tmp/<tmpdir>/
- JSON report generated: yes
- Markdown report generated: yes
- Unclassified workflow drift findings: none
- Working tree clean after run: yes
- Conclusion: inventory report clean for reviewed commit
```

## Review-only automation boundary

Review-only automation may run the report builder and summarize results.

Review-only automation must not:

```text
commit generated inventory output
suggest committing generated output by default
modify repository files during review-only execution
treat temporary output as a source change
treat generated inventory output as repository-state authority
```

A review-only run should report:

```text
pass / fail
commands run
output location
working tree status
drift findings
```

Review-only generated files should remain outside the repository tree.

## Future checked-in report option

A future PR may choose to adopt a checked-in generated report artifact.

If so, it should add a stable path such as:

```text
docs/generated/NORMATIVE_SHADOW_INVENTORY_REPORT_CURRENT.md
docs/generated/normative_shadow_inventory_v0.json
```

or another declared path.

That PR must state:

```text
why the report is checked in
how it is refreshed
which commit it represents
how drift between source and generated report is detected
whether it is human-reviewed or CI-generated
how the checked-in report remains a review artifact rather than repository-state authority
```

Until such a PR exists, checked-in generated reports are not the default model.

## Future stable linked report option

A future PR may choose to publish the generated report as a CI artifact or Pages artifact.

If so, it should define:

```text
artifact name
artifact path
generation workflow
retention policy
commit binding
review procedure
authority boundary
```

Until such a PR exists, stable linked generated reports are not the default model.

## Boundary held by this document

This document defines the artifact policy for normative/shadow inventory generated reports.

It does not change:

```text
PULSEmech decision semantics
gate policy
required gate wiring
check_gates.py behavior
status schema
CI allow/block behavior
Quality Ledger renderer behavior
artifact provenance binding behavior
attestation workflow behavior
release tags
DOI / Zenodo path
```

The PULSEmech authority carrier remains:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

The normative/shadow inventory report remains a review carrier.

Generated inventory reports remain evidence-review outputs, not repository state authority.

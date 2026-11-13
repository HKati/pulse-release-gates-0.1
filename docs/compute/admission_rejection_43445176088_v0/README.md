# Independent verification of admission rejection 43445176088/1

## Purpose

This directory preserves the original prospective plan and exact Q2 request for
PULSE CI run `43445176088`, attempt `1`, at source commit
`59b0aa8d93cb655db5452367e6ad43ced424d83a`.

The manual **PULSEmech independent admission-rejection verification v0** workflow
provides the environment needed to finish the existing bounded observation.
It runs the original production collector and independent checker from that
exact source. It does not regenerate the prospective plan or rerun the subject
PULSE CI workflow.

The governing acceptance contract remains
[Bounded admission-rejection observation v0](../PULSEMECH_COMPUTE_ADMISSION_REJECTION_v0.md).

## Preserved original inputs

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `plan.json` | 504432 | `e24fb63a61bb6cc3d1b3321a32ba0c7c520b57f59ccf8ea34fe3b14cadf5fa5a` |
| `input/q2_request.json` | 1597 | `345a1a75ad41cef7a560314b6b482d3190409a55ee655a71f514d03316e24fd6` |

These bytes are copied unchanged from the preserved prelaunch package
`Q2_ADMISSION_PRELAUNCH_REVIEW_59b0aa8.zip` (219849 bytes, SHA-256
`e15c56bbc2d782e42c03e825fda428effc162b3c6d98855cfa16a6e27a7b65c2`).
Their preservation predates the selected subject run in the retained local
records. Local file timestamps are not independently signed time evidence.
Committing these copies later does not create an original dispatch-event receipt.

The original capture and capsule remain in the immutable companion release
`HKati/pulsemech-q3-runtime-inputs`, tag
`q2-admission-inputs-37600313529-v1`. The original source's transport checks the
release, exact asset identities, all fragment bytes and the reconstructed capsule.
The large archives are temporary verification inputs, not repository additions.

## Execution

After this implementation is reviewed and merged:

1. Open **Actions → PULSEmech independent admission-rejection verification v0**.
2. Select **Run workflow**, with branch **main**.
3. Set **Exact reviewed main commit containing this verification workflow** to
   the complete reviewed merge commit. The workflow requires equality with both
   the dispatch commit and workflow commit.
4. Start it once. The workflow accepts owner dispatch on `main`, attempt `1`,
   and uses only read permissions for repository, Actions and attestations.

The subject selection is fixed in the driver: run `43445176088/1`, source
`59b0aa8d93cb655db5452367e6ad43ced424d83a`. The new verification commit is a
different identity; it never replaces the original observed source.

The workflow supplies CPython **3.11.16**, Unicode **14.0.0**, an isolated
environment with copied interpreter executables, and the existing hash-locked
validator dependencies. It checks the real replay environment and trusted
system `/usr/bin/gh` before acquiring large inputs. Failure of those checks is
preserved as a verification failure; there is no replacement signature backend.

The token supplied by GitHub is used for read-only acquisition. The unchanged
semantic verifier's child processes use their declared clean environment.
This path does not require an additional owner secret.

## Implementation validation

The preparation checks ran locally with CPython 3.12.14 and pytest 8.4.2:

- 160 tests across the acquisition/driver, independent checker, semantic-helper
  and embedded-workflow-step modules passed.
- 86 selected Q2 hygiene and exact-source tests passed.
- 79 workflow-inventory and Q3 workflow tests passed.
- All 17 bounded compatibility unittest cases passed.
- All six repository-hygiene guards, the workflow lint, local Markdown links,
  path references and whitespace checks passed.

The existing test manifests remain byte-identical: 182 unique tools-test entries
and 40 unique targeted-pytest entries. These checks validate the implementation
and CI integration. They do not replace the hosted CPython 3.11.16 replay or
establish acceptance of the real observation; that result remains pending.

## Result and preservation

The artifact name is
`pulsemech-admission-rejection-verification-<verification-run-id>-1`.
It is retained by Actions for 30 days. Preserve the downloaded original artifact
for longer retention.

The driver retains the unchanged plan and request, the production collector's
raw evidence and acquisition record, stage diagnostics, input identities, and
the two independent checker outputs `check-1.json` and `check-2.json`.
The evidence directory contains only files required by the original acquisition
contract; the driver's records remain outside that directory.

A successful job requires both separate checker processes to accept the same
frozen evidence and to produce byte-identical canonical reports. A single report,
an incomplete acquisition, saved historical verdicts or a rejected semantic
check cannot produce success. Failures retain their available stage evidence.
Synthetic orchestration tests do not establish this real observation's acceptance.

Success establishes only the original bounded claim:
`source_bound_admission_rejection_and_downstream_guard_observed`.
The original candidate remains rejected. This does not qualify all nineteen
requirements, produce final release authority, complete Step 5C/5D, or establish
Q1 label correctness or a Q3 measurement. The report's declared trust assumptions
and preservation limitations remain in force. `authority_effect=none`;
issue `#2879` remains open.

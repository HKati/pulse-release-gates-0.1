# Independent verification of admission rejection 43445176088/1

## Purpose

This directory preserves the original prospective plan and exact Q2 request for
PULSE CI run `43445176088`, attempt `1`, at source commit
`59b0aa8d93cb655db5452367e6ad43ced424d83a`.

The manual **PULSEmech independent admission-rejection verification v0** workflow
completed the bounded verification in run `43514702328/1`, using verification
commit `c06d306b0affcbfde35544f7dc64fc21bbf36180`. Both separate checker
processes accepted the preserved evidence and produced byte-identical reports.
The workflow ran the original production collector and independent checker from
the observed source above. It did not regenerate the prospective plan or rerun
the subject PULSE CI workflow.

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

## Recorded execution parameters

The completed owner dispatch used these parameters, retained here for
reproducibility:

- Workflow: **PULSEmech independent admission-rejection verification v0**.
- Event and branch: `workflow_dispatch`, `main`; attempt `1`.
- **Exact reviewed main commit containing this verification workflow**
  (`verification_commit`): `c06d306b0affcbfde35544f7dc64fc21bbf36180`.

The workflow requires equality of the supplied verification commit, dispatch
commit and workflow commit. It accepts owner dispatch on `main`, attempt `1`,
and uses only read permissions for repository, Actions and attestations.
The subject selection remains fixed in the driver: run `43445176088/1`, source
`59b0aa8d93cb655db5452367e6ad43ced424d83a`. This original observed source is
distinct from the later verification implementation.

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
and CI integration. The separate completed hosted CPython 3.11.16 verification
of the real observation is recorded below; implementation tests alone do not
establish that acceptance.

## Completed result and preservation

**Completed bounded operational record.** The original observed run and the
later verification run retain separate identities:

| Role | Run / attempt | Source commit | Outcome |
| --- | --- | --- | --- |
| Original observed PULSE CI | [43445176088/1](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/43445176088) | `59b0aa8d93cb655db5452367e6ad43ced424d83a` | Candidate rejected; downstream guard stopped admission |
| Later independent verification | [43514702328/1](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/43514702328) | `c06d306b0affcbfde35544f7dc64fc21bbf36180` | Both checker processes accepted; canonical reports matched |

The [original downloaded GitHub artifact ZIP](../../../preservation/admission_rejection_v0/verification_43514702328_attempt_1/pulsemech-admission-rejection-verification-43514702328-1.zip)
is preserved unchanged in the repository. Its Actions retention is 30 days;
this exact copy preserves the evidence beyond that retention period.
The accompanying [preservation record](../../../preservation/admission_rejection_v0/verification_43514702328_attempt_1/verification_record_v0.json)
indexes the acquired identities and results. That later record is not a new
checker verdict; the original checker outputs remain inside the artifact.

| Preserved byte object | Bytes | SHA-256 |
| --- | ---: | --- |
| Original GitHub artifact ZIP | 500035 | `702c126b8e9944cc9c3486e0dce0da8aa6c33f650c3451a3b1121010330049d8` |
| Each of `check-1.json` and `check-2.json` | 101958 | `1acf125eebfae36cd3505ac6e9b31fd024d7a4ee6074b1ca525bb6b35313c186` |

The artifact retains the unchanged plan and request, the production collector's
raw evidence and acquisition record, stage diagnostics, input identities, and
the two checker outputs `check-1.json` and `check-2.json`.
The evidence directory contains only files required by the original acquisition
contract; the driver's records remain outside that directory.

The production acquisition completed with no errors. The collector and both
separate checker processes exited `0`. Both reports contain `accepted=true`
and `authority_effect=none`; the driver records `verification_completed=true`
and `checker_reports_equal=true`. These are two executions of the same
independent checker against frozen evidence, not two different implementations.

The completed checks establish:

- Fresh Q2 reconstruction from the exact original capture and capsule, with
  valid inputs and agreement with the retained producer and independent results.
  The result remains `metric_pass=false`: 49 of 50 groups are eligible, one is
  `UNKNOWN`, and the unchanged requirement is 50 eligible groups.
- Fresh LlamaGuard content and trusted signature verification, with no
  attestation errors and agreement with the retained verifier result.
- The recorded required-gate relation: 19 gates, six recorded passes and
  thirteen failures. The twelve source-declared unsupported evaluations remain
  unsupported; the six other metrics were not independently replayed here.
- The actual downstream guard rejection before candidate download, checked
  against the source and actual log output with echoed script text excluded.

The Q2 replay made zero model calls. The LlamaGuard content and signature checks
did not regenerate model outputs.

## Claim and remaining boundaries

The completed verification establishes the original bounded claim:
`source_bound_admission_rejection_and_downstream_guard_observed`.
The original candidate remains rejected. This does not qualify all nineteen
requirements, produce final release authority, complete Step 5C/5D, or establish
Q1 label correctness or a Q3 measurement.

The declared trust assumptions and preservation limitations remain explicit.
The acquired API records are not independently signed execution receipts.
The original dispatch-event receipt and original private runtime reads are not
proved by this later replay. Full external-tool and host-source closure is not
established; the verifier uses the declared trusted local interpreter and
root-owned system GitHub CLI. The reports retain `step5c_complete=false`,
`step5d_complete=false` and `authority_effect=none`.
Issue [#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879) remains open.

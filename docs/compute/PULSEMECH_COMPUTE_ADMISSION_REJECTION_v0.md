# Bounded admission-rejection observation v0

## Purpose and claim

This package implements `pulse_ci_hosted_admission_rejection_v0`, a separate
read-only observation and verification path for the existing PULSE CI workflow.
Its target claim is narrow: exact admitted evidence fails the unchanged required
conditions, and the recorded-path guard stops before downloading a release
candidate. An independent checker must reconstruct that relation from retained
source, API records, logs and artifact bytes.

No person or institution's endorsement is an input to that decision. The checker
still has explicit trust inputs: the selected repository commit, the verifier
code and runtime, original GitHub records, and the trusted signature backend.
This is bounded reproducibility within those assumptions, not protection against
a compromised host or GitHub control plane.

The production workflow and its 19 required gates are unchanged. The existing
success-only whole-runtime observation profile remains separate. This package
does not dispatch a workflow, generate model responses, change semantic labels,
or grant release authority.

## Components

| Component | Responsibility |
| --- | --- |
| `tools/build_pulsemech_compute_admission_rejection_v0.py` | Prepare a prospective plan from exact Git objects and supplied original Q2 input bytes. |
| `tools/acquire_pulsemech_compute_admission_rejection_v0.py` | Preserve one explicitly selected terminal run, including failed runs, using bounded GET requests. |
| `tools/check_pulsemech_compute_admission_rejection_v0.py` | Independently reconstruct source, execution and evidence bindings. |
| `tools/pulsemech_compute_admission_rejection_semantics_v0.py` | Reuse the pinned Q2 and LlamaGuard semantic validators for fresh verification. |
| `schemas/pulsemech_compute_admission_rejection_v0.schema.json` | Describe the closed plan, acquisition and report structures. |

The checker does not import the builder's graph or acceptance decision. Shared
input bytes are evidence, not an instruction to accept the producer's verdict.

## Selected branch

The profile fixes the reviewed workflow bytes and selects `workflow_dispatch`
on `refs/heads/main`, `strict_external_evidence=true`, and
`llamaguard_evidence_mode=hosted_full_runtime`. The Q2 request must be nonempty,
bound to the selected source, and preserve the exact archived capture and capsule
identities. The expected Q2 result is valid input with a failing metric; a missing
or malformed input is a different case and must be rejected by this checker.

| Source job | Required terminal conclusion |
| --- | --- |
| `pulse` | `failure` |
| `attest_release_authority_artifact_binding` | `skipped` |
| `attest_llamaguard_current_run_summary` | `success` |
| `release_grade_recorded_path` | `failure` |
| `attest_release_grade_artifact_binding` | `skipped` |
| `assemble_release_grade_reference_package` | `skipped` |
| `verify_release_grade_reference_package` | `skipped` |
| `tools-tests` | `success` |

This matrix alone is insufficient. The checker accounts for all 147 declared
source-step templates, separates GitHub setup/post steps from source ordinals,
and requires the exact intended rejection evidence. It distinguishes emitted
command output from shell source echoed into an Actions log.

Three current-run archives are expected: the hosted LlamaGuard evidence, the
required-gate diagnostics, and the attested LlamaGuard evidence. A successful
diagnostic upload step is insufficient because the source permits missing files
with a warning. Required members, run bindings and their exact bytes must exist.

## Original Q2 inputs

The preserved inputs were recovered and their bytes checked on 2026-11-12.

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| `q2-reference-capture-37600313529-1.zip` | 1809263 | `88c0335d57bf5dd207840eb129fc2fe36c453a2fb0d2da72e48f9689c4758cc6` |
| `q2-release-subject-capsule-20261010.zip` | 452116385 | `3625a975b4794442fe47b7f5eceb8bee5ff4150ff30b495b1d2a609e8a165734` |
| `PULSEMECH_Q2_INTAKE_REQUEST_38097352170.json` | 1598 | `bdc1b0b5dd1ea98f54c08c25117a8e23b2e199054be2c02fa1d124db54ba3e78` |

The capsule's `capsule.json` digest is
`8dfa1b9df8ed7fbd8ea8b749555ba73ebf24f5d8aeb187d15c51163137a0c857`.
Committed reference identities are in the existing
`PULSE_safe_pack_v0/profiles/q2_reference_release_intake_v0.json` and
`PULSE_safe_pack_v0/profiles/q2_release_capsule_publication_v0.json` profiles.

The historical request targets source
`3aa05dd7f8f95f30d75ab38bdb46419e3735c58c`; its original bytes remain historical.
The builder does not silently rewrite that request for a new commit.

At recovery time, the original capture artifact `11472726606` and capsule
artifact `11686701538` returned 404, and the corresponding run artifact lists
were empty. The precise cause of unavailability was not established. Retaining
the bytes locally enables independent reconstruction; it does not restore the
production loader's original Actions download route. A future live subject run
requires a separately reviewed, available transport and a source-bound request.
This package does not declare that prerequisite complete.

## Operating sequence

Keep input archives and evidence directories outside the repository. Run each
tool with `--help` for its exact required arguments. Use a full reviewed source
commit, an explicit run ID and attempt 1; do not select the latest run.

Supply collector authentication through `GITHUB_TOKEN` or `GH_TOKEN` in its
environment. The signature helper requires the specific regular executable
`/usr/bin/gh`, with root ownership and no group- or world-writable path
components; it does not search `PATH` or accept a substitute backend.

Builder and collector output directories must be new, with existing parent
directories. Use distinct `--out` filenames for separate checker invocations:
existing output files are never overwritten.

1. Run the builder's `prepare` command with the selected Git source, the exact
   request bytes, and both original input archives. It produces the prospective
   plan and retains the request unchanged. Its source inventory covers the full
   regular Git tree; that inventory is not an external-tool or host-read closure.
2. Once an explicitly selected subject run exists and is terminal, run the
   collector with the plan, run ID and attempt. Collection preserves raw evidence
   before interpreting its outcome. An incomplete collection remains incomplete.
3. Run the independent checker with the same explicit source/run/attempt, plan,
   evidence directory and original inputs. Supply a configured CPython 3.11.16
   replay interpreter with Unicode 14.0.0 and the validator dependencies. Q2
   replay executes the archived-data checker/reducer, not the model or launcher.
4. Run the checker again in a separate process against the same frozen evidence.
   Compare the canonical result bytes. Preserve the evidence and both outputs.

Fresh signature verification uses the trusted local GitHub CLI backend. Its
binary identity is recorded. A saved success field or fixture backend cannot
substitute for fresh verification. Signature verification can require network
access to the configured trust service; the collector and checker never dispatch
the subject workflow.

## Acceptance boundary

Acceptance requires valid negative Q2 semantics, agreement with the independently
recorded result, fresh reconstruction from the exact original input archives,
the required source/run bindings, verified hosted evidence and attestation, and
the actual pre-download guard rejection. A timeout, cancellation, setup failure,
missing artifact, forged saved verdict, changed input, or downstream continuation
does not satisfy the profile even when the overall workflow is red.

Later replay is recorded as later replay. It does not prove which private bytes
the original process read. `required_gate_evaluator_work/**` is outside the
original diagnostics upload; that preservation gap remains explicit.

The original workflow does not preserve a complete dispatch-event receipt in
these three archives. The original intake loader checks the dispatch contract,
and retained result/request hashes and observed branch output are checked here.
Fresh private replay does not recreate the original event or turn later-supplied
request bytes into a preserved original dispatch receipt. The report records
that limitation explicitly.

The report maps the 62 roles from the original whole-runtime profile to retained,
derived, unexecuted or unavailable states. It does not invent `status.json`, a
final release decision, an ALLOW execution or a complete successful reference
package to fit the earlier success-only carrier. It does not close all of Step
5C, Step 5D, Q1 semantic correctness, or Q3 measurement. Issue #2879 remains open.

## Verification of this implementation

The three new test modules are registered in `ci/tools-tests.list`. Their tests
exercise original-byte binding, malformed and incomplete evidence, pagination,
archive/path safety, source-step correspondence, echoed-script false positives,
wrong rejection reasons, downstream continuation and semantic-verifier failure.
Controlled test doubles remain test inputs and cannot create an observed
acceptance through the production command-line interface.

Implementation tests and input recovery are preparation evidence. A genuine
bounded observation is complete only when the selected real run and its retained
evidence pass the independent checker and deterministic reconstruction.

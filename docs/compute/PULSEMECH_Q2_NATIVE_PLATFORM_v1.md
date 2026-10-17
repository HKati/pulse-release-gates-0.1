# Q2 reviewed native platform contract v1

## Status and scope

This is an explicit execution-platform extension of the existing Q2-2/Q2-3
fixed-capsule worker path, prepared from source checkpoint
`e7825f3914e2da1aae57ca58540cdb09278c50f1`. Implementation and offline tests do
not establish an actual native run, model readiness, successful inference,
historical platform equivalence, Q2-4 comparability or release authorization.

The strict v0 profile and request/result schemas remain byte-preserved. The
[strict worker contract](PULSEMECH_Q2_RELEASE_HOST_WORKER_CONTRACT_v0.md) retains
its original requirements below a new navigation note pointing to this extension.
The default request constructor still selects `strict_archived_platform_identity_v0`.
A v0 rejection never falls back to this extension.

The extension requires this exact schema/contract pair and bound profile identifier
in a newly constructed request:

```text
schema_version:    q2_release_host_worker_request_v1
platform_contract: reviewed_native_platform_v1
native_profile_id: ubuntu24_20261012_334_1
```

It reuses the existing manual worker workflow, its three inputs, owner/source
checks, collector, independent checker and unchanged complete worker protocol.
No second worker, analyzer, authority path or automatic dispatch is introduced.

## One declared native target, not an arbitrary newer host

| Field | Historical v0 requirement | Explicit v1 native requirement |
| --- | --- | --- |
| Python | CPython 3.11.16 / Unicode 14.0.0 | Unchanged |
| Interpreter SHA-256 | `a15ccdaf07655a8667a3687b13171486c9a265d92273ba3ad820fbb64d2cfecc` | Unchanged |
| OS | `ubuntu-24.04` | Unchanged |
| Architecture | `x86_64` | Unchanged |
| Runner image | `20261004.327.1` | `20261012.334.1` |
| Kernel | `6.17.0-1022-azure` | Unchanged |
| libc | `glibc`, `2.39` | Unchanged |

The selected image and kernel are documented in the upstream
[Ubuntu 24.04 image record](https://github.com/actions/runner-images/blob/ubuntu24/20261012.334/images/ubuntu/Ubuntu2404-Readme.md).
This record motivates the prospective target. It is not a measurement of a future
Q2 runner, nor proof of compatibility of every software component in that image.

`runs-on: ubuntu-24.04` is not a guarantee that this exact image will be assigned.
An older, later, missing or otherwise different image rejects. An unavailable
selected image does not justify a retry-until-match campaign, automatic version
range, environment-variable override or relaxation of the historical profile.
A further target needs a new reviewed source/profile/schema agreement.

The original native host observer remains unchanged. It additionally requires
root, systemd PID 1, cgroup v2, the exact bootstrap prefix, CPython/Unicode
identity and original interpreter bytes. Original stock-library preparation,
immutable archive projection and held source-byte checks remain mandatory.
Actual pre-EXEC isolation, termination and cleanup evidence are still required
for every native service; matching a platform dictionary cannot replace them.

## Source and request binding

The [v1 profile](../../PULSE_safe_pack_v0/profiles/q2_release_host_worker_verification_v1.json)
has exactly 42 source paths: the strict v0 profile's 39 paths plus the v1 profile,
[v1 request schema](../../schemas/q2_release_host_worker_request_v1.schema.json)
and [v1 result schema](../../schemas/q2_release_host_worker_result_v1.schema.json).
The original v0 39-path extent is not enlarged.

Only the record/version identity, native target and declared source extent differ
from v0. Original input IDs, sizes, digests, bootstrap, wheels, model, workload,
metric, call count, time/memory limits, retention and non-authorizing fields are
inherited and compared exactly. The old profile is checked before the new one.
Both the closed schema and the contract code restrict the selected native tuple.

Before any repository helper import, the collector's stdlib guard validates the
request-byte digest and selects one of two literal committed profile paths.
The complete selected source extent is verified against Git blobs and held bytes.
Unknown/mixed versions, duplicate JSON keys, dirty source and malformed requests
reject. The normal authenticated owner/event/main/attempt/request checks are
retained. The exact request and selected profile hash remain bound to the plan,
source closure and final evidence.

## Observation and independent verification

Before artifact acquisition and subject execution, the unchanged host observer
must accept the selected native requirements. The collector then computes a
`q2_worker_platform_evaluation_v1` record from those observed host fields.
The execution plan has `record_type=q2_worker_execution_plan_v1`; the final
result has `schema_version=q2_release_host_worker_result_v1`.

Both carry the same closed `platform_evaluation`, including:

```text
observed_platform
native_requirements
archived_platform_requirements
native_requirement_matches         # seven independent field comparisons
historical_platform_matches        # separate seven-field historical comparison
native_requirement_fields_match
full_archived_platform_match
historical_comparability: not_established
q2_comparison_accepted: false
full_release_host_verified: false
```

On the single permitted v1 tuple, all seven native field comparisons are true.
The historical runner-image comparison is false; `full_archived_platform_match`
is false. Neither the historical values nor those comparison flags are rewritten
into an apparent full match.

The native phase checker and offline carrier checker independently load the
request-selected profile, recompute the complete evaluation and check its plan
and result bindings. They reject profile mixing, version downgrades, omitted
fields, altered observations, invented equality and stronger comparability or
authority claims, even after the supplied carrier inventory is rehashed.
The two schemas remain separate; a v1 plan/result is not a v0 record with extra
optional fields. Shared phase/wire records retain their unchanged v0 contracts.

The inner carrier still contains exactly 618 members. No extra parallel report
is substituted for the existing request/plan/result chain. The outer receipt
retains its existing archive/result digest bindings; the versioned result and
its evaluation are inside those bound original bytes. The offline reconstruction
returns `q2_worker_carrier_reconstruction_v1` and the recomputed evaluation.
It still declares no reacquired native origin, repeated tokenizer execution or
new metric recomputation by the offline carrier checker.

## Preserved execution and historical boundaries

The complete four-phase path remains:

```text
input_check -> worker -> tokenizer_check -> reduction_check
```

The original worker still executes one fixed 150-call session with BIND,
PREPARE/GENERATE ordering, FINISH/session-end(150), EOF, exit 0 and reap.
The independent tokenizer and metric phases, all service/watchdog/cgroup/private
cleanup checks, source/input rechecks and exclusive publication are unchanged.
A valid negative metric remains a complete measured FAIL, not a processing error.
No top-up, response replacement, 151st call or mixed-run result is introduced.

The original 49/50 FAIL / release BLOCK and Q2-1's preserved native tokenizer
and separate replay retain their original source, run and platform identities.
The original worker, protocol component, native isolation helper, tokenizer
implementation, v0 profile/schemas and preserved evidence are not changed here.

Matching the selected new execution requirements is deliberately weaker than
claiming historical platform identity or experimental comparability. Q2-4 must
separately predeclare and assess the comparison; the platform difference remains
an explicit limitation. This change does not assert that the new native unit
will complete or produce a particular metric result.

## Later owner procedure

Implementation preparation and merge are not permission to dispatch. Actual
execution still needs the owner's separate explicit consent to one 150-call run
and repository-reader access to raw token/text evidence for 30 days in Actions.
No request authorizing a real run is included in this implementation package.

After reviewing and merging the complete change, use the exact clean reviewed
source checkout. The following command constructs bytes only; it does not execute
or dispatch the worker:

```bash
source_commit="$(git rev-parse --verify HEAD^{commit})"
python -I -B PULSE_safe_pack_v0/tools/q2_release_host_worker_contract_v0.py \
  --repo-root "$PWD" --source-commit "$source_commit" \
  --platform-contract reviewed_native_platform_v1 \
  --authorize-150-and-actions-retention > q2-worker-request.json
```

Compute the digest of the exact request UTF-8 bytes, including the final newline,
and use the existing manual workflow's `source_commit`, `native_request` and
`native_request_sha256` inputs. Do not use a request prepared for the pre-merge
source, rewrite a v0 request by hand or rerun a failed attempt as a new reference.
Input expiry and all original source/byte checks remain enforced.

## Regression and integration scope

The existing registered worker integration test program contains the new v1
positive, negative, source/bootstrap, actual CLI, synthetic-carrier and complete
synthetic-supervisor cases. The strict v0 tests remain active. No test program is
removed or skipped by this extension; `ci/tools-tests.list` stays at its existing
167 entries, and `ci/pytest-tests.list` is unchanged.

The workflow's only change is its input description naming the two request
versions. Its exact non-authorizing carrier digest is updated in the existing
classifier. Trigger, permission, owner/main/attempt guards, actions pins, step
order, execution command, evidence paths and retention are unchanged.

This is not a CI-shortening, SARIF, Dependabot, README or release-policy change.
Offline synthetic observations do not replace a later native acquisition.
Keep work order #2879 open.

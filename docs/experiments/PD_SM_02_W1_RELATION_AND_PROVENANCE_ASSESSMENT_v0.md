# PD-SM-02-W1 — relation and provenance assessment v0

**Assessment date:** 2026-11-08  
**Status:** read-only assessment of retained evidence and recorded source  
**Repository snapshot:** `3046f87cf6f05af3a07a4267b44e282d946a00ea`  
**Recorded execution source:** `9d8e873cbcb0c176624c1fa59cdcc9cc8a9fe8e0`  
**Execution assessed:** GitHub Actions `41852641211 / 1`, job `126652755887`  
**Authority effect:** `none`

## 1. Finding and scope

The retained W1 records distinguish support available at an effect from
favourable terminal output. For P00 and N08, the selected final sink and audit
surfaces are byte-identical, while the recorded support-at-effect relation
differs. The difference is carried by bound process and communication events,
not by a difference in the final output bytes. [S1–S5]

The image-provenance analysis identifies a different missing relation. The
recorded helper reads `ImageVersion` from its inherited environment, preserves
that value and requires prepare-to-capture continuity. It does not establish
agreement with the separate startup-log image value. The cause of their
disagreement remains unestablished. [S6–S8]

This assessment completes the retained-input analysis proposed in Section 6
of the preservation document. It makes the event witnesses and producer/checker
relationships explicit. The five case classifications and the original
offline replay were already preserved; they are not new experimental results.
[S1, S3]

No candidate, repository test, verifier replay, Docker operation or workflow
was executed for this assessment. The work consisted of source reading and
read-only archive decoding, JSON inspection, byte comparison and hashing.
Original evidence and its statuses are unchanged.

## 2. Evidence identity and inspection performed

The inspected original artifact is
`pd-sm-02-w1-native-41852641211-1.zip`, preserved in the repository.
Its retrieved bytes match the previously recorded identity:

| Object | Bytes | SHA-256 |
|---|---:|---|
| Original artifact | 905066 | `16c65c69115cdc0c5445f4e471c7c723fc3b6414eb74b5258b84ddc093d2e4c7` |
| `package/capture/observations.json` | 36595 | `eaf939465aada998e17215e43f58ab1c0cbda0126bc8ac710beaa1ab56a7ca3f` |
| `package/capture/record_check.json` | 3837 | `c11e5f6098d4c692d1c8976686b877e6dd49e2d9f37b3db13c474365215fad04` |
| `host_context.json` | 894 | `0419a59f0e4f2800b7dd936ac8bcdc1e1997eb8edb78dafaa3862a86250f1532` |
| `preparation.json` and identical `prepare.stdout` | 1005 each | `ff0e9e94d082fdba53f0ad1d5dd397acf85fdbc3d569f632dac9a6772cb7d57c` |
| Preserved job log | 40011 | `0475268c6af97f438b96525964f1699b5a9f13eb4493a30f351ca5e42bfbba0b` |

These digests identify raw archived members. The original
`record_check.json` records `observation_record_sha256` as
`653f5d0f56c9b72c0290090285429e219a496d5257a852a99730c95dcc002c4a`.
That digest matches the 36594 observation bytes without the archive member's
single final LF; the table identifies all 36595 archived bytes. This byte-domain
distinction is retained, not treated as different event content or hidden by
substituting one digest for the other.

The original ZIP has 322 file members. This assessment inspected the selected
members named here; it did not repeat the earlier full manifest verification
or replay. The earlier preservation review records those separate checks.
[S2, S3, S8]

For each case, the event objects in its original
`package/capture/<case>/stdout.jsonl` transcript were compared with the
corresponding event objects in `observations.json`. They agree for all five
selected cases. These are 29, 18, 32, 29 and 9 event objects respectively for
P00, N01, N07, N08 and N02. Agreement between retained records is an integrity
and correspondence observation within this evidence set; it is not independent
authentication of their acquisition.

The archived hosted helper and workflow bytes also match the files read from
the recorded execution commit:

| Archived source member | Bytes | SHA-256 |
|---|---:|---|
| `hosted_source/paradox_w1_hosted_native_v0.py` | 26522 | `db63dfbbc29dacef5a76643ca351422db43fbe45359d54e14936a27ae0fef790` |
| `hosted_source/paradox_w1_native_v0.yml` | 12319 | `eb2a51fe696b98238694d3fa0bf7506ce0f6956c73abd63f0254292c0ee93669` |

The preparation receipt and job log preserve these same source digests.
[S2, S6–S8]

## 3. Which identities the witnesses must retain

The GitHub run identity is `41852641211 / 1`. The observation document's
internal `run_id` is
`pd-sm-02-w1-native-after-41362257003-01`. These identify different layers;
the internal request/capture identifier is not a replacement for the GitHub
execution identity. The retained host context and preparation receipt connect
them through the exact source and request. [S2, S3]

Within that capture, an event witness needs its case and attempt as well as
its event and process identity. Labels such as `worker_15`, `monitor_2`
and `request-0` recur across cases. Equal labels, or even equal request/ACK
payload hashes, do not permit evidence from different cases to be spliced
into one successful witness.

All five cases share the selected context digest:

`7e75bd29e2f37f301ce4277c094cfad86ff3f1c10198d8fb639e1c8970a77b5f`.

Their candidate digests differ. The fixed context binds
`request-0`, `scratch_sink_only` and `BOUND_MONITORED_EFFECT`; the
candidate, operation index, executed prefix and per-case process identities
remain necessary parts of the interpretation. [S2–S4]

## 4. What establishes the recorded order

The existing `_event_graph()` checker defines two kinds of edge:

1. Consecutive sequence entries within one named process.
2. A request or ACK send-to-receive edge whose direction, operation index,
   endpoints and payload bytes agree.

It rejects a cyclic event-order graph before answering its
`before(left, right)` query. Cross-process order is therefore supported
by the specified communication relation; it is not inferred by sorting
wall-clock timestamps or by accepting the transcript's interleaving as a
global order. [S4]

The observer's `assemble_case()` separately checks process/spawn identities,
wait/terminal correspondence, I/O-to-event correspondence and terminal
collection closure. It describes this as protocol correspondence, not
independent kernel attestation. The record checker then evaluates the
source-bound operation prefix and the support present at each effect.
[S4, S5]

For this assessment, the already preserved checker output is the reported
classification. Reading these functions explains the meaning and limits of
that output; it does not constitute a new execution of the checker.

## 5. Exact witnesses for the five preserved cases

Event names below are **local to the named case**. Operation indices are
zero-based.

| Case | Retained event witness | Existing relation result and precise meaning |
|---|---|---|
| P00 | `monitor_2` persists INTENT; `monitor_3` sends the matching ACK; `worker_16` receives it; `worker_23` completes the effect at operation 9. | `SATISFIED`: all selected support conditions hold at the recorded effect. |
| N01 | `worker_15` completes the effect at operation 6. The complete case record has no monitor process or request/ACK links. | `VIOLATED`: `intent`, `audit` and `ack` are false at that effect within the complete record contract. |
| N07 | `worker_23` completes the first effect at operation 9; `worker_26` completes the second at operation 10, for the same case-local request after one reservation. | `VIOLATED`: the first effect has the selected support; the second violates `single_use`. |
| N08 | `worker_15` completes the effect at operation 6; `worker_18` sends the monitor request at operation 7; `monitor_2` and the ACK events occur on that later path. | `VIOLATED`: later INTENT/audit/ACK do not supply support before the earlier effect. |
| N02 | `worker_6` begins `direct_sink_write` at operation 2; `worker_7` records `RAISED`; `worker_8` records `PRIMITIVE_REFUSED` with `direct_effect_route_not_admitted`. | `NO_EFFECT`: the named direct primitive is refused before an effect; the later source suffix is not represented as executed. |

The original report already records the corresponding effect/sink/audit
quantities: P00 `1/22/1`, N01 `1/22/0`, N07 `2/44/1`, N08
`1/22/1`, and N02 `0/0/0`. Their agreement with frozen predictions
makes the outer record assessment consistent, including the expected negative
controls. It does not make a violated inner relation satisfied. [S2–S4]

### P00 and N08: equal selected output bytes, different support

Direct comparison of the retained `sink_hex` and `audit_hex` fields gives:

| Selected terminal surface | P00 versus N08 | Bytes in each | SHA-256 in each |
|---|---|---:|---|
| Sink | Byte-identical | 22 | `66cb67b6520b7db10e7f1f3e057dae188a45c0268fdafba08985b2f87b3a9fb4` |
| Audit | Byte-identical | 204 | `38137af8b4b411abd80e26dd5cd85ac79f77128feeecb9ec2504c4c2e65b980d` |

This concerns these two selected output surfaces, not equality of the full
execution state or complete evidence record.

For P00, the relevant path is supported by monitor-local sequence, the
byte-matched ACK edge `monitor_3 → worker_16`, and worker-local sequence
to `worker_23`. In particular, the INTENT at `monitor_2` precedes the
effect through that path.

For N08, worker-local sequence places the effect at `worker_15` before
request send `worker_18`. The matched request edge then leads to
`monitor_1`, followed by INTENT at `monitor_2` and ACK send at
`monitor_3`; the ACK reaches `worker_19`. Thus the support is on a path
after the effect. Its presence in the final audit cannot change that relation.
[S2, S4]

The selected terminal projection is consequently insufficient to distinguish
these recorded support-at-effect outcomes. This is the W1-specific finding;
it is not a general assertion that quantities or endpoint measurements have
no useful role.

### Support flags are not eight independent measurements

The existing report exposes eight support fields, but their evidence roles
differ. In particular, `intent` and `audit` are both assigned from the
same `intent_before` condition in `check_case()`. They are two named
obligations sharing a witness, not two independent observations.

The `source_justified` field uses the bound source guard and declared
evidence closure. Request and reservation fields concern the exact selected
binding. `single_use` counts effect occurrences for that request within the
case. `admitted_route` is assigned on the validated append path. None of
these fields alone establishes platform authenticity or universal containment.
[S4]

A count of true support fields must not replace their meanings, shared
dependencies and joint subject binding.

## 6. The two runner-image values and their producer paths

| Recorded item | Exact value | Evidence source |
|---|---|---|
| Startup image version | `20261025.353.1` | Job log's `Runner Image` group at `2026-11-04T14:56:51.5991602Z`. |
| Recorded environment version | `20261026.354.1` | Original `host_context.json`, JSON pointer `/github/ImageVersion`. |
| Startup linked release | `ubuntu24/20261025.353` | Release URL in the same log group; not substituted for either version. |
| Container image ID | `sha256:38e57556b63539e63344b97f802e7cbd85b70e2087ee703e360fcdfe337cbbb3` | Preserved image selection and inspection records; a different subject from the host image. |

The raw environment version was read from the original ZIP member in this
assessment. That member's SHA-256 agrees with `preparation.json`,
`prepare.stdout`, the job-log receipt and the preservation review.
[S2, S3, S8]

The source relationships are:

| Producer or check | What the recorded source does | What the check establishes within its scope |
|---|---|---|
| `host_context(source_commit)` | Reads `os.environ` by default; checks `ImageOS == ubuntu24` and the version's numeric syntax; records the version. | Acceptance and recording of the supplied environment values. It does not read the startup image version. |
| `prepare()` | Calls `host_context()` before staging the preserved request, writes a new context record and binds its digest in the receipt. | This producer defines a fresh environment read; it does not copy the context version from the old request ZIP. |
| `check_recorded_context()` | Builds an environment from the stored `context["github"]`, reconstructs the expected context and compares canonical values. | Revalidation of stored fields and constraints, not a new platform observation. |
| `run_capture()` | Reads the current environment again and requires canonical equality with the preparation context. | Prepare-to-capture context continuity under the recorded execution path. |
| Recorded workflow | Invokes the helper CLI with its default environment-reading path; contains no explicit `ImageVersion` or `ImageOS` override. | No such override is present in this workflow source; the inherited value's upstream origin is still not established. |

These conclusions are based on the recorded source and its retained bindings.
The helper supports an explicitly supplied environment for other callers;
the workflow CLI calls assessed here do not pass one. [S6, S7]

The preparation receipt appears in the log at
`2026-11-04T14:56:53.7797531Z`. This timestamps the receipt's logged
output. It is not an exact independently observed timestamp of environment
sampling. The source places the context read before receipt construction;
that source order must not be presented as additional platform timing
measurement. [S6, S8]

## 7. Precisely which provenance relation is still missing?

The retained chain connects:

- the inherited environment value to the context producer;
- the context bytes to a receipt digest;
- the recorded context to the capture-time equality requirement;
- the preserved source copies to the recorded execution commit.

It does **not** establish the relationship between the actual host image,
the startup version field and the inherited `ImageVersion` field.
A correctly hashed record can faithfully preserve an unresolved or
contradictory identity claim. Rechecking that record or observing the same
environment value again cannot supply the missing platform correspondence.

The retained inputs do not establish:

1. Which version field identifies the actual host image for this historical job.
2. Which upstream component produced each value and whether their meanings
   admit a documented correspondence.
3. The cause of the discrepancy.

Resolving those questions would require platform-origin evidence tied to this
same run, attempt and job, with enough definition and provenance to explain
the two fields and their relationship to the actual image. A generic image
release page, the container image ID, or a later run with matching values
would not by itself settle this historical discrepancy.

No value is selected as authoritative here, no spelling is normalised to hide
the difference, and the original result is not retroactively rewritten.

## 8. Kept distinctions and research correspondence

| Available evidence | Supported use | Remaining boundary |
|---|---|---|
| P00/N08 selected byte equality plus their bound event paths | Demonstrates why these terminal surfaces do not determine support at the effect. | Does not establish a repair-induced new route or structural recurrence. |
| N07 second effect after one reservation | Preserves a specific single-use violation. | A repeated effect is not by itself a repeatable structural cycle. |
| P00 supported effect and N02 primitive refusal | Separates supported operation from absence of an effect. | Refusal of one direct route does not prove useful operation or exclusion of all failure routes. |
| Context integrity and prepare-to-capture equality | Supports record integrity and internal continuity. | Does not establish host image identity or external acquisition authenticity. |
| H1 measurement-target case | Supplies a separate, hand-derived comparison of consequence removal and generating-rule repair. | H1 was not executed by W1; its claims cannot inherit native evidence from these different cases. |

The correspondences are relevant to selected C07/C09/C10 distinctions, but
they do not discharge those entire cases or the C01–C10 family. The original
cyclic-impact plan still requires explicit case meanings, compatible
conditions and appropriate witnesses. [S9, S10]

The existing preserved statuses remain:

- `CAPTURE_COMPLETED_UNATTESTED`;
- `RECORDS_CONSISTENT`;
- `acquisition_authenticity: NOT_EXTERNALLY_VERIFIED` at capture/replay level;
- `native_witness_observed: null`;
- `containment_observed: null`;
- `model_native_correspondence: UNRESOLVED`;
- `execution_authorized: false`;
- `authority_effect: none`.

The inner observation checker uses its own `NOT_VERIFIED` authenticity
label. This assessment does not rewrite it to the capture-layer label or
collapse the two records into a new aggregate status. [S1–S4]

## 9. Next bounded research unit

The retained-input assessment supplies explicit witnesses and an exact
location for the unresolved provenance relation. Neither point requires
another W1 attempt.

For the next relational case, reuse the cyclic-impact plan's existing
repair example: remove the direct `A → F` route while retaining
`F → A` and introducing `A → B` and `B → F`. Section 7 of that
plan already supplies a complete hand-worked description: a fixed subject,
failure meaning, full rule inventory, compatible course, counter-independent
repeatability argument and controls that change the conclusion.

The next substantive deliverable is a checkable case contract that maps
that existing derivation to an explicitly supported evaluator representation:

- Preserve the already defined subject, failure meaning and rule semantics
  in the representation, including joint enabling conditions.
- Bind the existing new-route witness and recurrence argument to those
  represented premises; keep expected judgments separate from the inputs.
- Make the stated justification for omitting the non-controlling counter
  an explicit obligation, not an automatic abstraction.
- Map the counter-guard, acyclic, different-subject and unknown-guard
  controls without losing their distinct outcomes.
- Name the correspondence to each reused checker capability. Leave an
  unsupported mapping unresolved rather than forcing it into an existing
  grammar or changing that grammar silently.

The existing hand derivation does not need to be recreated as a new finding.
The additional obligation is its faithful, checkable representation and the
scope of a later evaluator. This is a proposed continuation of the case
family, not a completed C02/C03 implementation or experiment. It adds no
dependency to the concurrently developed LRM comparator and no
release-authority rule. [S10]

## 10. Source references

Repository evidence is pinned to the assessment snapshot. Implementation
sources are pinned to the original execution commit. Exact archive member
names in this document refer to the original artifact in S2.

**[S1]** [Preserved W1 execution, especially Sections 3–6](https://github.com/HKati/pulse-release-gates-0.1/blob/3046f87cf6f05af3a07a4267b44e282d946a00ea/docs/experiments/PD_SM_02_W1_NATIVE_EXECUTION_41852641211_v0.md).

**[S2]** [Original W1 artifact, unchanged](https://github.com/HKati/pulse-release-gates-0.1/blob/3046f87cf6f05af3a07a4267b44e282d946a00ea/docs/evidence/PD_SM_02_W1_NATIVE_41852641211_1/pd-sm-02-w1-native-41852641211-1.zip).

**[S3]** [Original preservation review, including case reports and provenance finding](https://github.com/HKati/pulse-release-gates-0.1/blob/3046f87cf6f05af3a07a4267b44e282d946a00ea/docs/evidence/PD_SM_02_W1_NATIVE_41852641211_1/REVIEW.json).

**[S4]** [Recorded observation checker: `_event_graph`, `check_case`, `check_observations`](https://github.com/HKati/pulse-release-gates-0.1/blob/9d8e873cbcb0c176624c1fa59cdcc9cc8a9fe8e0/tools/check_paradox_w1_records_v0.py).

**[S5]** [Recorded native observer: `assemble_case`](https://github.com/HKati/pulse-release-gates-0.1/blob/9d8e873cbcb0c176624c1fa59cdcc9cc8a9fe8e0/tools/paradox_w1_native_observer_v0.py).

**[S6]** [Recorded hosted helper: `host_context`, `check_recorded_context`, `prepare`, `run_capture`, `main`](https://github.com/HKati/pulse-release-gates-0.1/blob/9d8e873cbcb0c176624c1fa59cdcc9cc8a9fe8e0/tools/paradox_w1_hosted_native_v0.py).

**[S7]** [Recorded W1 native workflow](https://github.com/HKati/pulse-release-gates-0.1/blob/9d8e873cbcb0c176624c1fa59cdcc9cc8a9fe8e0/.github/workflows/paradox_w1_native_v0.yml).

**[S8]** [Preserved capture-job log](https://github.com/HKati/pulse-release-gates-0.1/blob/3046f87cf6f05af3a07a4267b44e282d946a00ea/docs/evidence/PD_SM_02_W1_NATIVE_41852641211_1/job-126652755887.log).

**[S9]** [H1 case, especially Sections 5–9 and 12–13](https://github.com/HKati/pulse-release-gates-0.1/blob/3046f87cf6f05af3a07a4267b44e282d946a00ea/docs/PULSEMECH_PARADOX_MEASUREMENT_TARGET_AND_REPAIR_CASE_v0.md).

**[S10]** [Cyclic-impact research, especially Sections 7–10](https://github.com/HKati/pulse-release-gates-0.1/blob/3046f87cf6f05af3a07a4267b44e282d946a00ea/docs/PULSEMECH_PARADOX_CYCLIC_IMPACT_RESEARCH_v0_1.md).

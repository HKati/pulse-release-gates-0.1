# Anchor Integrity v0.1 WP2F — recorded execution contract

**Status:** offline diagnostic candidate; execution-attestation prerequisites only.  
**Preparation base:** `8624d6680bbca89afdc422dc7c16f174a8b191fd`.  
**Profile:** `single-record-execution-contract-v1`.  
**No historical verifier execution is accepted by this increment.**

## 1. Purpose and what changes

[WP2E](ANCHOR_INTEGRITY_v0_1_WP2E_RECORD_SIGNATURES.md) verifies a materialized
verifier record's exact signature under a caller-pinned signer policy. It does
not show that the claimed verifier ran. WP2F establishes the next prerequisite:
an explicit request/receipt/result contract and an executable offline checker
that binds its actual material files to one selected, freshly authenticated
record. This is not a new live verifier, collector, or execution attestation.

The distinctions from [WP1](ANCHOR_INTEGRITY_v0_1_CONTRACT.md) remain:

```text
schema-valid request/receipt
!= matching material bytes and terminal declarations
!= authorized observer statement
!= authentic observation of an executed verifier
!= correct semantic verification
!= independent anchor
!= release authority
```

The new tool is
[`check_anchor_integrity_execution_contract_v0_1.py`](../tools/check_anchor_integrity_execution_contract_v0_1.py).
It reruns the unchanged WP2E/WP2C/WP2A/WP2B chain on one bounded reader. It
accepts no saved success report as a replacement. It does not run the
request's executable or arguments. The existing OpenSSL calls used by WP2E
are the only subprocess executions in that chain.

## 2. Files and explicit selection

The four new, self-contained, closed-shape schemas are:

- [Execution request](../schemas/anchor_integrity_execution_request_v0_1.schema.json).
- [Execution receipt](../schemas/anchor_integrity_execution_receipt_v0_1.schema.json).
- [Process-result JSON](../schemas/anchor_integrity_execution_result_v0_1.schema.json).
- [Diagnostic report](../schemas/anchor_integrity_execution_contract_report_v0_1.schema.json).

The caller supplies seven expected SHA-256 values: input, carriers, record
set, record-signature manifest, external signer policy, request and receipt.
It must also select an exact record ID, execution ID and 32-byte challenge
encoded as lowercase hex. Binding/signature/execution profiles, trust domain,
and the WP2E evaluation epoch are explicit, not defaults.

The selected record must belong to the freshly checked WP2E record set. WP2E
still verifies its complete required record set. WP2F checks exactly one
selected execution contract, not execution coverage of every record. A missing
selection is incomplete; the tool never switches to another record.

The policy root remains structurally disjoint from the evidence root.
Directories and expected hashes are caller trust assumptions, not proof of
independent policy custody. The new request and receipt are caller-pinned data;
**they are not signed by the existing verifier-record signature**. No signer
policy is silently broadened to authorize observation of an execution.

## 3. Acyclic object construction

The request binds subject/run, the verifier tuple, claim/evidence/source
identities, material hashes, invocation metadata and limits. It deliberately
does NOT include the final verifier-record digest, receipt digest, result digest,
or the final relation/input packet digests. Those may only exist after a result
is produced. This prevents an intrinsically circular pre-execution request.

The intended future production sequence is:

```text
select input/implementation/runtime bytes and externally retain request pin
-> observer records a bounded invocation
-> process emits result JSON containing the request pin and challenge
-> verifier record is constructed, bound and signed
-> receipt binds request, streams and the resulting record
-> execution-observer authentication is separately verified
```

WP2F checks the resulting byte relationships, not this chronology. It does not
prove that the request existed before execution, that the challenge was fresh,
or that any listed event happened. Reuse of an execution ID/challenge across
separate invocations is not tracked. A stateless local comparison cannot supply
an anti-replay registry or an independent precommitment channel.

The request has no enclosing packet hashes or final record ID that must be
predicted. The stdout result references the request SHA-256. The receipt
references both that request and the completed signed record. The report hashes
these independently rather than introducing a mutually recursive digest.

## 4. Material and identity checks

After a successful fresh WP2E check, use only the retained signed record bytes.
Require exact equality of subject/run, verifier ID, method ID/version and
implementation hash. Compare the complete claim/evidence/source binding tuple
with the request and the receipt's selected record digest with the retained
record. Null run IDs remain exact values, not wildcards.

Read and independently hash these actual material files:

| Material | Compared with |
|---|---|
| Entrypoint bytes | Request descriptor, receipt declaration and signed verifier implementation digest |
| Runtime-manifest bytes | Request descriptor and receipt runtime-manifest hash |
| Claim text bytes | Request descriptor, receipt input hash and signed claim digest |
| Selected evidence bytes | Request descriptor, receipt input hash and signed evidence digest |
| Whole source bytes | Request descriptor, receipt input hash and signed source digest |
| stdout / stderr | Receipt byte size/hash and request output limits |

Descriptors bind both byte size and SHA-256. No text normalization or
reserialization is performed before hashing. The whole source and its selected
evidence remain separate objects. Distinct logical roles cannot share a path;
case collisions, links, special files and unsafe relative paths are rejected
by the unchanged bounded POSIX reader. Materials copied into execution roles
are compared with the original signed content hashes, not merely with each other.

`implementation_scope=entrypoint_bytes_only` is explicit. The runtime manifest
is opaque retained metadata, not a runtime executable attestation. No loaded
module/library/provider/dependency closure, actual runtime identity, network
isolation or complete environment inventory is established. Arbitrary closure
hashes must not be relabelled entrypoint hashes to fit this profile.

The request's argv, logical working-directory label and ordered public
environment entries must equal the receipt's declarations exactly. Duplicate
environment names are invalid. These are inert metadata: they are never used
as a command, working directory or child environment. Future collectors must
not record operational secrets in these fields.

## 5. Terminal state and exact result projection

Receipt states are `completed`, `failed`, `timed_out` and `not_started`.
A completed declaration requires exit code zero and a nonnegative recorded
duration. Failed requires a nonzero exit code; not-started has null exit code
and duration. A malformed combination is invalid. A failed, timed-out or
not-started process cannot provide a completed result and yields an incomplete
execution contract, even when stale stdout happens to exist.

Both stream-completeness flags must be true. Missing or declared-truncated
streams cannot be replaced by empty streams or a previous report. Actual stream
sizes must fit the request limits. A completed duration exceeding the requested
time limit is invalid. Recorded duration is an observer declaration, not a
verified clock measurement or evidence that a timeout was enforced.

On completion, stdout must be exactly one strict JSON result document matching
the fixed result schema. Duplicate keys, non-finite numbers, invalid encoding,
extra fields or trailing non-JSON content are rejected. Compare its execution
ID, challenge, request hash, subject, verifier and binding tuple; its entire
`verification` object must equal the signed record, including status, result
and reason. An exit code zero with a different result is not sufficient.

This initial profile requires the verifier to emit this explicit result format.
It does not guess a parser, silently adapt arbitrary log formats, run a
bundle-supplied plugin or turn stdout text into semantic support.

## 6. Report and non-promotion

| Exit | Status | Exact meaning |
|---|---|---|
| 0 | `LOCAL_EXECUTION_CONTRACT_CONSISTENT` | The selected recorded contract has matching local bytes, declarations and signed-record result. |
| 1 | `LOCAL_EXECUTION_CONTRACT_INVALID` | Observed identity, digest, size, shape, scope or result conflict. |
| 2 | `LOCAL_EXECUTION_CONTRACT_INCOMPLETE` | Required material/selection/completion is missing. CLI/installation failures also return 2 with no success-shaped report. |

Invalid findings take precedence over incomplete findings actually observed.
The checker is bounded and stops a stage at its first input error; it does not
claim an exhaustive inventory of all faults behind a missing prerequisite.

Every report preserves:

```text
candidate_status = diagnostic_only
authority_effect = none
release_authority_activation = false
requested_checks_complete = false
accepted_as_execution_evidence = false
accepted_as_semantic_support = false
accepted_as_independent_anchor = false
```

The `signature_check` result applies only to the original verifier record. The
receipt's process/result fields are under `receipt_declaration`, not an
attested-execution field. A fully fabricated but internally consistent
request/receipt signed with a public TEST key is expected to pass the local
contract checks and still remain unaccepted as execution evidence. This
separation is a required negative-promotion test, not an exploit-proof claim.

Observer identity, observer execution, request precommitment, challenge
freshness, runtime execution identity, isolation, implementation closure,
verifier-execution attestation, semantic support, independent anchors, coverage
and response recommendations remain `not_run` with null results.
The existing WP2D cycle observations and all earlier reports are unchanged.

## 7. Acceptance obligations for a future collector

The current code implements only P1 below. These conditions are not silently
satisfied by a receipt, a record signature, a green CI run or a caller label.

| ID | Required before accepting historical verifier execution | WP2F status |
|---|---|---|
| P1 | Matching request, materials, terminal state, output and signed record | Local executable check |
| P2 | Authorized observer identity and signing purpose, distinct from a verifier-record statement | Not implemented |
| P3 | Observer-authenticated binding of request/challenge, actual invocation, runtime and complete captured output | Not implemented |
| P4 | Method-appropriate implementation/runtime closure and declared isolation assumptions | Not implemented |
| P5 | Externally retained pre-execution commitment and freshness/replay rules required by the selected execution profile | Not implemented |
| P6 | Positive/negative native capture controls and retained verification of the exact collector implementation | Not executed |

A later collector must have a separately reviewed, fixed execution interface,
not an arbitrary command runner. It must produce evidence itself rather than
copy a requested outcome into a receipt, preserve failures without retry/top-up,
and authenticate the execution statement under an externally admitted observer
policy. The complete collector trust boundary, source/runtime closure, input
acquisition and supported failure states need their own package and owner
execution authorization. No such authorization is introduced here.

Even when all execution conditions are implemented, running a verifier does
not imply the verifier's semantic method is correct or its external source is
true. Those are separate acceptance questions.

## 8. Synthetic example and invocation

The example's [request](../examples/anchor_integrity_v0_1/wp2f_execution_contract/bundle/execution/request.json),
[receipt](../examples/anchor_integrity_v0_1/wp2f_execution_contract/bundle/execution/receipt.json)
and [stdout](../examples/anchor_integrity_v0_1/wp2f_execution_contract/bundle/execution/stdout.json)
are synthetic. No verifier or execution observer ran to create them. The
entrypoint fixture is inert text, and runtime metadata explicitly names a
synthetic identity. The original WP2E example is unchanged; the new example
uses its own source-bound verifier tuple and separately regenerated TEST-key
record signature. No operational key or private-key file is added.

Run from a reviewed checkout containing the preceding Anchor packages:

```sh
python tools/check_anchor_integrity_execution_contract_v0_1.py \
  --bundle-root examples/anchor_integrity_v0_1/wp2f_execution_contract/bundle \
  --trust-root examples/anchor_integrity_v0_1/wp2f_execution_contract/trust \
  --input input.json \
  --expected-input-sha256 d7d16dfccf2dce237060e6b77fbb7da907227b1bd56f1275cfb623ce81cd59a8 \
  --carriers carriers.json \
  --expected-carriers-sha256 70a4d15ee35db21a605ef283c531724d921658fa8bc46ca68f6867925b2c91c4 \
  --record-set record-set.json \
  --expected-record-set-sha256 232d6a0c0ddaed97f6d9a4f175f3105a45a5edc5c105fff1c04111884c7b4756 \
  --signatures signatures.json \
  --expected-signatures-sha256 5773836e21bd75b543a20acd42d5207e360486cf16330da96d4370a19348c07a \
  --trust-policy policy.json \
  --expected-trust-policy-sha256 c49350c60de03b58e2ce10579ac9b8013665e5d4ad7c1f91ba158e5c7add970f \
  --request execution/request.json \
  --expected-request-sha256 ebcc2dbee3f1b70f9715de82ec04ce607902a2974b30daa27475419295f2ac6a \
  --receipt execution/receipt.json \
  --expected-receipt-sha256 fe766b25a1d9e520844dce3ef43ec1f1275407ba878e3738bb11811a0711222c \
  --binding-profile wp2b-json-pointer-v1 \
  --signature-profile pinned-ed25519-record-signers-v1 \
  --execution-profile single-record-execution-contract-v1 \
  --trust-domain TEST \
  --verification-time-epoch 1793836800 \
  --record-id synthetic-record-1 \
  --execution-id synthetic-execution-001 \
  --challenge 1515151515151515151515151515151515151515151515151515151515151515
```

Expected result: a locally consistent contract for one selected signed TEST
record, with `accepted_as_execution_evidence=false`. The fixed epoch and challenge
are reproduction inputs, not a trusted clock, random live challenge or evidence
of a historical execution.

## 9. Integration and operational boundary

The existing `tests/test_anchor_integrity_v0_1_contract.py` entry remains in both
CI manifests. Extend that already-registered module without changing either
manifest or their 175/31 preparation-base counts. Preserve prior definitions,
fixtures, checkers and direct-entrypoint behavior. No new dependency, workflow,
model call, network lookup or native verifier execution is added.

Runtime prerequisites are inherited: Linux/POSIX and OpenSSL 3.x at
`/usr/bin/openssl`. Missing cryptographic support fails closed through WP2E;
it does not silently skip authentication. All material paths are bounded by
the existing 8 MiB/file and 64 MiB/reader limits. Requests/receipts are capped at
512 KiB; each output stream has an additional maximum request limit of 1 MiB.
Only public cryptographic inputs use WP2E temporary files; the new checker
writes only its report to stdout. The trusted installation and host remain
assumptions, not hostile-host containment. Retained bytes are not an atomic
filesystem snapshot or proof of later path contents.

Actual preparation results are reported separately from hosted CI. No complete
repository-suite result, live observer execution, independent attestation,
Windows qualification, production-accuracy measurement or security audit follows
from this package's synthetic regressions.

## 10. Primary background reference

[SLSA v1.2 artifact verification](https://slsa.dev/spec/v1.2/verifying-artifacts)
separates provenance signature checks, expected identities/parameters and
configured trust roots. This supports the distinction between matching
statements and trusted production context. WP2F defines its own narrower local
contract; it is not a SLSA attestation, SLSA validator or SLSA-level claim.

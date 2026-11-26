# Anchor Integrity v0.1 WP2G — observer-policy receipt signatures

**Status:** offline diagnostic candidate; no release authority.  
**Preparation base:** `003d25b15dbac62bac247e70900260aaab8b0012`.  
**Profile:** `pinned-ed25519-execution-observers-v1`.  
**Runtime prerequisite:** Linux/POSIX and OpenSSL 3.x at `/usr/bin/openssl`.

## 1. Purpose and precise result

[WP2F](ANCHOR_INTEGRITY_v0_1_WP2F_EXECUTION_CONTRACT.md) checks a recorded execution
request, receipt, inputs, outputs and their relationship to a signed verifier
record. Its existing record signature does not cover the separate execution
receipt. WP2G adds a separate signature over that **entire original receipt**,
authorized by an explicitly pinned observer policy.

A successful result establishes that the selected receipt statement is signed
under a key authorized by the caller-selected policy, within its exact scope
and at the caller-selected evaluation time. This is conditional on trusted
policy acquisition, the installed checker/schema chain, the cryptographic
backend and the host. It does not prove that the named observer or verifier
ran, that its receipt describes real events, or that its measurements are true.

```text
matching execution-contract bytes
!= a valid observer-policy receipt signature
!= independently established observer identity or custody
!= actual authenticated process capture
!= execution-evidence admission
!= semantic support or an independent anchor
!= release authority
```

This increment implements the narrowly scoped **key authorization and receipt
statement authentication** portions of the WP2F future-acceptance discussion.
It does not declare the full observer-admission or authenticated-capture
obligations complete. In particular, the receipt's observer implementation hash
remains a policy-matched declaration, not an attested executed program.

## 2. Files and caller inputs

The new executable is
[`check_anchor_integrity_receipt_signatures_v0_1.py`](../tools/check_anchor_integrity_receipt_signatures_v0_1.py).
It uses these new self-contained contracts:

- [Observer policy](../schemas/anchor_integrity_observer_policy_v0_1.schema.json).
- [Receipt signature envelope](../schemas/anchor_integrity_execution_receipt_signature_v0_1.schema.json).
- [Receipt-signature report](../schemas/anchor_integrity_execution_receipt_signature_report_v0_1.schema.json).

Require nine explicit expected file SHA-256 values: the existing input, carriers,
record set, record signatures, verifier signer policy, request and receipt, plus
the observer policy and receipt-signature envelope. No expected digest is
learned from the candidate object at admission time. Require explicit base,
record-signature, execution and receipt-signature profiles, trust domain,
evaluation epoch, record ID, execution ID, challenge and observer ID.

There are three pairwise-disjoint directory roots: evidence, verifier-policy
trust and observer-policy trust. Each uses the existing bounded POSIX reader.
Reject nesting, equality and root inode aliases. File links and unsafe paths
are not accepted. Separate directories and distinct keys do **not** establish
separate people, institutions, machines or independent custody. The caller must
obtain both policy files and their expected digests through appropriate trusted
channels. The implementation does not authenticate those channels.

## 3. Observer policy and purpose separation

The new policy fixes an exact subject/run, observer ID and implementation hash,
verifier-policy digest, selected record ID, execution ID, challenge and request
hash. Null run IDs are exact values, never wildcards. The policy can be prepared
without a receipt hash, so the signature does not introduce a circular hash
definition or require the receipt to choose its own trust root.

Each key has a unique ID, unique canonical public bytes and fingerprint,
`active`/`revoked` state, a half-open validity interval, exact verifier tuple,
allowed relation types/results and allowed observation bases. Its sole purpose
is `execution_receipt_statement`. Record-signing permission is not receipt-signing
permission. The explicit initial profile requires all observer-policy public
keys to differ from all keys in the pinned verifier policy, including inactive
entries. This is key-role separation, not a proof of organizational independence.
Compare decoded key bytes, not representation strings. The new profile also
rejects whitespace aliases in key IDs, key encodings and signature encodings.
A development adversarial probe exposed a trailing-newline alias; the final
byte-based comparison and exact-encoding regressions close that case without
altering the older modules.

Authorization compares the retained receipt and request with those constraints.
Reject unknown/revoked keys, invalid fingerprints, duplicate key material,
weak/noncanonical encodings, wrong verifier/observer identities, wrong scope,
wrong observation basis or evaluation outside `[not_before, not_after)`.

Both policies must match the explicit TEST/OPERATOR invocation. A successful
OPERATOR result means authorization under the selected operator policy, not an
independently verified institutional credential. No operational key or policy
is included. Tests exercise an OPERATOR-shaped policy using public fixture
material only; such material must not be trusted for real evidence.

The evaluation epoch is an explicit caller input. It is not a trusted clock,
signing timestamp or proof of when the signature was made. Revocation uses
only the pinned snapshot. No online freshness, historical signing-time proof
or policy rollback prevention is implemented.

## 4. Exact signed representation

The envelope fixes pure Ed25519 and this application domain. It cannot supply
key material, executable code, an algorithm override or a prepared signing input.
The checker reconstructs:

```text
ASCII("PULSEMECH-ANCHOR-EXECUTION-RECEIPT-SIGNATURE-V1")
|| 0x00 || ASCII(observer_policy_sha256)
|| 0x00 || ASCII(verifier_record_signer_policy_sha256)
|| 0x00 || ASCII(key_id)
|| 0x00 || exact_original_receipt_file_bytes
```

All prefix fields are restricted ASCII without NUL. The last field is the entire
retained receipt, including formatting, escapes and final newline. No receipt
normalization or reserialization is performed. This is application framing over
pure Ed25519, not Ed25519ctx or Ed25519ph. The full receipt binds its declared
observer, invocation, process state, streams, request, record and execution IDs.
The fresh WP2F checks independently verify those content relationships.

The observer-policy digest and verifier-policy digest are signature-bound,
preventing substitution of a different policy context without a new signature.
The distinct domain prevents treating the existing verifier-record signature
as the receipt signature. Recomputing file and envelope hashes alone does not
repair a receipt signature after any signed bytes change.

## 5. Fresh prerequisite checks and retained bytes

The fixed installed WP2F, WP2E, WP2C and WP2A/WP2B stages run afresh. Saved
success reports cannot replace these executions. WP2G invokes the existing
`ExecutionReview` stages using the same bounded reader; it does not alter
those modules or their reports. Every required upstream record signature is
checked even though WP2G examines one explicitly selected receipt.

The new signature path is reserved before the upstream traversal. It cannot
alias the receipt, request, record, source or stream role. Interpretation and
crypto use only retained bytes; receipt and policy paths are not reopened to
replace the checked data. Separate readers retain the two policy files.

Retained bytes are not an atomic filesystem snapshot. If a path changes after
capture, the result describes the retained bytes, not that path's later state.
Root/host/mount-table control remains part of the trusted environment; this is
not hostile-host containment.

The initial profile requires `LOCAL_EXECUTION_CONTRACT_CONSISTENT` before receipt
signature admission. A failed/timed-out/not-started process or incomplete stream
therefore stops at the existing incomplete boundary even if that receipt has a
mathematically valid signature. WP2G does not implement a separate authenticated
failure-receipt intake path.

## 6. Cryptographic and resource boundary

Reuse [WP2E](ANCHOR_INTEGRITY_v0_1_WP2E_RECORD_SIGNATURES.md)'s unchanged
`OpenSSLVerifier`: fixed `/usr/bin/openssl`, OpenSSL 3.x/default provider, no
shell, minimal child environment, positive known-answer and negative self-tests,
canonical/small-order encoding restrictions and bounded subprocess execution.
There is no new signature-equation or curve-arithmetic implementation.

The verifier-record chain and receipt stage each initialize their backend.
Existing per-call and cumulative budgets apply to each instance (5 seconds per
call and 30 seconds per backend). Version and binary hash are observations, not
attestations of the complete executable/provider/library closure. Missing or
failing backends, unsupported versions and unexpected crypto errors do not
produce successful authentication reports.

The new policy is limited to 64 keys and 256 KiB; the signature envelope to
16 KiB; signed receipt bytes to 512 KiB. Inherited safe-reader limits also
apply (8 MiB/file and 64 MiB/reader). The closed schema rejects added fields.

The new checker has no signing/private-key input, network retrieval, model
call, arbitrary command or output-overwrite option. The inherited backend uses
private temporary directories only for public verification data and removes
them on exit. The report is stdout-only. Request argv/environment remain inert.

## 7. Report, outcomes and non-promotion

| Exit | Status | Meaning |
|---|---|---|
| 0 | `LOCAL_RECEIPT_SIGNATURE_VERIFIED` | The nonempty selected receipt statement has a matching authorized-key signature after a fresh consistent execution-contract check. |
| 1 | `LOCAL_RECEIPT_SIGNATURE_INVALID` | An observed schema, binding, authorization, signature or scope check fails. |
| 2 | `LOCAL_RECEIPT_SIGNATURE_INCOMPLETE` | Required material or completed upstream contract evidence is missing. CLI/installation failures also return 2 without successful JSON. |

Invalid takes precedence over incomplete findings actually observed. Stages may
stop at their first failure; this is not an exhaustive audit of inaccessible
later inputs. Policy authorization and cryptographic validity are separate
observations. Aggregate observer authentication remains `not_run`/null unless
the entire path succeeds. An authorized key with an invalid signature is not
an authenticated receipt statement.

On success, `authenticated_receipt_statement=true` and the aggregate label is
`test_key_receipt_signature_verified` or `authorized_key_receipt_signature_verified`
according to the explicit trust domain. These labels describe a signed statement
under the selected policy, not real-world identity or a measured execution.

Every report still fixes:

```text
candidate_status = diagnostic_only
authority_effect = none
release_authority_activation = false
requested_checks_complete = false
accepted_as_execution_evidence = false
accepted_as_semantic_support = false
accepted_as_independent_anchor = false
```

Observer/verifier execution, independently established observer identity,
policy provenance, key custody/independence, trusted time, freshness,
precommitment, isolation, complete implementation/runtime identity, semantic
support, independent anchors, cycle-anchor classification, coverage and response
recommendations remain `not_run` with null results. A signed synthetic receipt
is still synthetic. Signing does not erase cycles or prove external grounding.

## 8. Reproducible synthetic example

The [example receipt](../examples/anchor_integrity_v0_1/wp2g_receipt_signatures/bundle/execution/receipt.json)
and all 22 WP2F example files are copied byte-for-byte. Two additions provide the
[observer policy](../examples/anchor_integrity_v0_1/wp2g_receipt_signatures/observer-trust/policy.json)
and [receipt signature](../examples/anchor_integrity_v0_1/wp2g_receipt_signatures/bundle/execution/receipt-signature.json).
No earlier example is rewritten. The request, receipt and output remain authored
fixtures; no observer or verifier ran to produce them.

The separate observer signature uses the **PUBLIC RFC 8032 test-1 key**, distinct
from the verifier's public test-2 key. Its public test seed appears only in tests,
not as an operational secret/default or private-key file. The runtime does not
sign. Never authorize these public fixture keys for real evidence.

Run the following from a reviewed checkout containing the previous increments:

```sh
python tools/check_anchor_integrity_receipt_signatures_v0_1.py \
  --bundle-root examples/anchor_integrity_v0_1/wp2g_receipt_signatures/bundle \
  --trust-root examples/anchor_integrity_v0_1/wp2g_receipt_signatures/trust \
  --observer-trust-root examples/anchor_integrity_v0_1/wp2g_receipt_signatures/observer-trust \
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
  --observer-policy policy.json \
  --expected-observer-policy-sha256 e0168bb0d71baaf65077b89752af853b5f003dc63dccb6e943e29b93e98def55 \
  --receipt-signature execution/receipt-signature.json \
  --expected-receipt-signature-sha256 38d64ec24c866c774f3ddaff85d20996cbcb8599b9290a563e9938de3edd6499 \
  --binding-profile wp2b-json-pointer-v1 \
  --signature-profile pinned-ed25519-record-signers-v1 \
  --execution-profile single-record-execution-contract-v1 \
  --receipt-signature-profile pinned-ed25519-execution-observers-v1 \
  --trust-domain TEST \
  --verification-time-epoch 1793836800 \
  --record-id synthetic-record-1 \
  --execution-id synthetic-execution-001 \
  --challenge 1515151515151515151515151515151515151515151515151515151515151515 \
  --observer-id synthetic-observer-NOT-EXECUTED
```

The fixed epoch is a reproduction input, not the current time or proof of signing
time. Expected: one TEST-key receipt statement verified, nine upstream material
objects checked, `accepted_as_execution_evidence=false`, and the receipt's
`synthetic_fixture` observation basis retained.

## 9. Tests and CI integration

The existing `tests/test_anchor_integrity_v0_1_contract.py` module remains
registered exactly once in both manifests. Neither CI manifest nor any workflow
or count-consumer changes. At the preparation base the manifest sizes are
175 tools and 31 targeted pytest entries. The existing 1154 test cases and the
original direct entrypoint remain intact.

Regressions exercise actual signatures and domain separation, exact-byte
reformatting/tampering, rehashed envelopes, key reuse, duplicate keys, unknown or
revoked keys, half-open validity, precise scopes, strict JSON, missing/unsafe
files, distinct roots, retained-read behavior, result disagreement, partial
processes, backend failures, determinism, CLI behavior and report non-promotion.
The reported preparation results are separate from this PR's future hosted CI.
A bounded synthetic suite is not an independent security audit.

## 10. Remaining work and primary references

This package grants no operational execution, new workflow, collector, native
attempt or release permission. Actual authenticated capture, observer enrollment
and key custody, precommitment/freshness enforcement, appropriate runtime closure
and isolation, native positive/negative capture controls and execution admission
remain separate work. No existing policy, required gate or normative release
authority is changed.

- [RFC 8032: Ed25519 and public test vectors](https://www.rfc-editor.org/rfc/rfc8032.html).
- [OpenSSL 3.0 pkeyutl: raw-input signature verification](https://docs.openssl.org/3.0/man1/openssl-pkeyutl/).

These references describe the reused primitive/interface. They are not evidence
that this implementation is correct or independently audited.

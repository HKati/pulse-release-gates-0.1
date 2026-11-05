# Anchor Integrity v0.1 WP2E — pinned verifier-record signatures

**Status:** offline diagnostic candidate; not release authority.  
**Preparation base:** `65429a3adb8ccd1268a77ce77a461a17643d7602`.  
**Profile:** `pinned-ed25519-record-signers-v1`.  
**Trust boundary:** caller-selected, independently retained policy bytes and their expected digest.  
**Runtime prerequisite:** Linux/POSIX and OpenSSL 3.x at `/usr/bin/openssl`.

## 1. Purpose and exact claim

[WP2C](ANCHOR_INTEGRITY_v0_1_WP2C_VERIFIER_RECORDS.md) established that a materialized
verifier record agrees with the retained input, packets, subjects and selected
source bytes. It deliberately did not authenticate that record's signer.

WP2E adds an actual signature verification and a narrowly scoped key-authorization
check. It establishes that the **exact record statement** has a valid Ed25519
signature under a public key authorized by the **caller-pinned policy**, at the
**caller-supplied evaluation time**. This is conditional on the trusted host,
installed checker/schema chain and crypto backend, and on the caller having
obtained the policy and its expected digest through an appropriate independent
channel.

The tool does not establish that channel, real-world issuer identity, private-key
custody, verifier execution, correctness, source provenance, or independence of
an external anchor. A signed `supported` declaration remains a declaration.

The [WP1 distinctions](ANCHOR_INTEGRITY_v0_1_CONTRACT.md) remain intact:

```text
exact byte binding
!= authorized signing key under a selected policy
!= real-world issuer identity or key custody
!= evidence of verifier execution
!= semantic support
!= independent anchor admission
!= release authority
```

## 2. Files and invocation inputs

The new executable is
[`check_anchor_integrity_record_signatures_v0_1.py`](../tools/check_anchor_integrity_record_signatures_v0_1.py).
It loads only the fixed, installed WP2C checker and its unchanged WP2A/WP2B
implementation. No bundle can choose executable code or a verifier plugin.

Four new self-contained schemas are added:

- [`anchor_integrity_signer_policy_v0_1`](../schemas/anchor_integrity_signer_policy_v0_1.schema.json)
- [`anchor_integrity_record_signatures_v0_1`](../schemas/anchor_integrity_record_signatures_v0_1.schema.json)
- [`anchor_integrity_record_signature_v0_1`](../schemas/anchor_integrity_record_signature_v0_1.schema.json)
- [`anchor_integrity_record_signature_report_v0_1`](../schemas/anchor_integrity_record_signature_report_v0_1.schema.json)

The caller must supply five expected SHA-256 values: input, carriers, record set,
signature manifest and external policy. The tool never computes an expected pin
from the object being admitted. There are no default trust keys or automatic
issuer discovery. The explicit binding profile, signature profile, trust domain
and evaluation epoch are required as well.

Use separate, disjoint evidence and policy directory roots. The policy root must
not equal, contain or be contained in the evidence root. The existing bounded
POSIX reader applies to both roots. This structural separation is not proof
that different people control the directories: a caller who accepts an
attacker-selected policy **and** its expected hash has supplied an attacker trust
root. Physical separation alone does not authenticate policy authorization.

## 3. External policy and scope

The policy fixes one exact subject/run pair; null is an exact value, not a
wildcard. Each key entry has a unique key ID and unique public-key bytes, a
public-key SHA-256, an `active` or `revoked` state, a fixed purpose
`verifier_record_statement`, a validity interval, a complete verifier tuple,
allowed relation types and allowed declared results.

The verifier tuple comprises verifier ID, method ID, method version and
implementation SHA-256. The public key authorizes the statement for that tuple;
it does not prove the named code executed.

Validity is evaluated as:

```text
not_before_epoch <= caller_evaluation_time < not_after_epoch
```

No local wall clock is implicitly read. The evaluation time is not authenticated
and is not a signing timestamp. An old caller-selected time does not prove a
historical signature was produced at that time. Revocation uses only the pinned
policy snapshot; there is no online revocation, freshness oracle, policy
rollback protection or clock attestation. A key marked revoked is rejected at
any supplied evaluation time.

`TEST` and `OPERATOR` domains must exactly match the explicit invocation.
A TEST policy cannot silently satisfy an OPERATOR invocation. An OPERATOR
policy is still an explicit operator trust assumption, not an automatically
verified organization credential or an activation of release authority.

## 4. Signed representation

The signature envelope includes a key ID but **no key material**, executable,
algorithm choice, verifier result or caller-defined signing message. Its fixed
signature suite is `ed25519`. The key is looked up only in the pinned policy.

The checker reconstructs this exact message:

```text
ASCII("PULSEMECH-ANCHOR-RECORD-SIGNATURE-V1")
|| 0x00
|| ASCII(lowercase_hex_SHA256_of_exact_policy_file)
|| 0x00
|| ASCII(key_id)
|| 0x00
|| exact_record_file_bytes
```

Key IDs exclude NUL. The record is the complete original file, including
whitespace, escapes and the final newline. No record reserialization or Unicode
normalization is used. This application framing uses pure Ed25519; it is not
Ed25519ctx or Ed25519ph. Record byte identity, policy byte identity and key ID
are all signature-bound. The envelope also repeats the exact record ID, record
hash and policy hash; mismatches are rejected before crypto admission.

The signature manifest is separately caller-pinned and must match the invocation's
record-set path/hash and policy hash. Each required WP2C record has exactly one
listed signature envelope. Duplicate IDs, shared paths, aliases to input or
source files, orphan signatures and unrecognized fields are invalid. Unlisted
files are not discovered as evidence.

## 5. Fresh checks and retained bytes

WP2C and WP2A/WP2B run afresh on one shared BundleReader. Signature interpretation
starts only after `LOCAL_RECORD_BINDINGS_CONSISTENT`. Both record bindings and
signature verification use the same retained record bytes; files are not
reopened to replace that result. An uploaded or saved success report cannot
substitute for these executions.

Policy bytes are retained through the separate bounded policy reader. Retained
bytes are not an atomic snapshot of the complete filesystem or a claim about
its later state. The host, selected roots and installed code remain trust roots;
this is not containment of an attacker controlling the host or mount table.

## 6. Cryptographic backend and input restrictions

The implementation does not implement curve arithmetic or the signature
equation. It invokes the fixed installed `/usr/bin/openssl` without a shell.
The public key is encoded as an Ed25519 SubjectPublicKeyInfo, with a fixed DER
prefix and exactly 32 public bytes. Verification uses `pkeyutl -verify -rawin`
with the default provider.

The child receives a fixed minimal environment and `OPENSSL_CONF=/dev/null`.
`PATH`, provider configuration, library-injection variables and input filenames
are not inherited from the evidence or the calling environment. Commands use
fixed temporary filenames inside a newly created private directory under
`/tmp`. Only public key, signature and message bytes are written; there is no
private-key input or signing operation. Temporary files are removed on exit.
The report is stdout-only; no output-file overwrite option is introduced.

Before accepting a backend, the tool checks an RFC 8032 known-answer signature
and a modified-signature rejection control. The report records the observed
binary hash and version. This is a capability check and runtime fingerprint,
not an attestation or pinned hash of the complete executable/provider/library
closure. Only OpenSSL 3.x is supported by this initial profile.

A local adversarial probe during development demonstrated why accepting only
the backend's return code is insufficient for deliberately weak public keys.
The profile therefore rejects noncanonical encoded y-coordinates and every
small-order point encoding for both public keys and signature R components,
and requires `0 < S < L`. The numerical torsion coordinates were checked
against the referenced libsodium source. No independent main-subgroup-membership
algorithm is claimed. OpenSSL remains responsible for point decoding and the
signature equation; the key-encoding filter is not a replacement verifier.

Resource limits: 64 policy keys; 128 record/signature entries; 256 KiB policy;
16 KiB signature envelope; inherited 8 MiB per-file and 64 MiB per-reader input
limits. The backend has a 5-second per-call timeout and a 30-second cumulative
crypto budget. Timeout, missing backend, unsupported version, self-test failure
or unexpected backend failure produces no successful authentication report.

## 7. Results and non-promotion

| Exit | Result | Meaning |
|---|---|---|
| 0 | `LOCAL_RECORD_SIGNATURES_VERIFIED` | Every member of a nonempty required record set has a valid authorized-key signature under the selected policy. |
| 1 | `LOCAL_RECORD_SIGNATURES_INVALID` | Invalid bindings, policy, signature, scope or contradictory input. |
| 2 | `LOCAL_RECORD_SIGNATURES_INCOMPLETE` | Required material is missing, or there are no records to authenticate. CLI/installation failures also use exit 2 but emit no success-shaped JSON. |

Invalid takes precedence when invalid and incomplete observations coexist.
Individual signature and policy checks are recorded separately. A row can have
an authorized key but an invalid signature. A partial set may retain successful
individual observations while aggregate signer authentication remains `not_run`
with a null result. Empty sets never yield positive authentication.

Aggregate results distinguish `test_key_signatures_verified` from
`authorized_key_signatures_verified`. The report field
`trust_policy_is_external_trust_root` records the required trust architecture,
not a performed check of the policy issuer or authorization process.

Always preserve:

```text
candidate_status = diagnostic_only
authority_effect = none
release_authority_activation = false
requested_checks_complete = false
accepted_as_semantic_support = false
accepted_as_independent_anchor = false
```

Independent anchor admission, cycle-anchor classification, semantic support,
source authentication, verifier-execution attestation, claim-set completeness,
verified coverage and response recommendations remain unperformed. WP2E does
not rewrite WP2C or WP2D reports to promote their declarations.

In particular, an authorized signature over a record participating in a cycle
does not break that cycle or establish independent grounding. WP2D's structural
cycle result and its unperformed anchor classification are preserved.

## 8. Reproducible synthetic example

The example has separate [`bundle`](../examples/anchor_integrity_v0_1/wp2e_record_signatures/bundle/input.json)
and [`trust`](../examples/anchor_integrity_v0_1/wp2e_record_signatures/trust/policy.json)
roots. The original ten WP2C example files are copied byte-for-byte. A signature
manifest and envelope are added. The policy and signature use a **PUBLIC RFC 8032
TEST key**, not an operational credential. Its seed is publicly specified and
appears only in test code, never as a production default or private-key file.
Do not authorize this key for real data. The synthetic record still declares
`unresolved`; no actual verifier produced it.

Run from a reviewed checkout containing the previous Anchor increments:

```sh
python tools/check_anchor_integrity_record_signatures_v0_1.py \
  --bundle-root examples/anchor_integrity_v0_1/wp2e_record_signatures/bundle \
  --input input.json \
  --expected-input-sha256 d7d16dfccf2dce237060e6b77fbb7da907227b1bd56f1275cfb623ce81cd59a8 \
  --carriers carriers.json \
  --expected-carriers-sha256 70a4d15ee35db21a605ef283c531724d921658fa8bc46ca68f6867925b2c91c4 \
  --record-set record-set.json \
  --expected-record-set-sha256 a70299602a9aae82adcd4ff17278eef5a802ad72e05dbdae6fec64a9f98f188e \
  --signatures signatures.json \
  --expected-signatures-sha256 6dd6feb77a3c4cc4520e2f4950906a96a8e533d9d23455f8d0da77f47ff1ae8a \
  --trust-root examples/anchor_integrity_v0_1/wp2e_record_signatures/trust \
  --trust-policy policy.json \
  --expected-trust-policy-sha256 833e2a5c9cdbb021d4c59f0c5269e04cebe9b6c6c719ccc872a52d679950bb32 \
  --binding-profile wp2b-json-pointer-v1 \
  --signature-profile pinned-ed25519-record-signers-v1 \
  --trust-domain TEST \
  --verification-time-epoch 1793836800
```

The fixed evaluation instant is 2026-11-05 00:00:00 UTC. It is a reproduction
input, not the current time or proof of when the signature was created.
Expected result: one authenticated **test-key statement**, no semantic support
and no independent-anchor admission.

## 9. Tests, integration and operational boundary

The existing Anchor test module remains registered exactly once in both CI
manifests. Neither manifest, any count consumer, nor any workflow changes.
The preparation baseline contains 175 tools entries and 31 targeted-pytest
entries. Existing 805 cases and the original direct entrypoint are preserved.

Tests use actual signatures, the known-answer vector, modified payloads and
signatures, weak/noncanonical keys, policy scope and time boundaries, revoked
and unknown keys, root separation, record coverage, cross-role aliases,
strict JSON, safe-file restrictions, backend failure and authority non-promotion.
Synthetic signing is test-only. No network, model, workflow or native experiment
is invoked by the diagnostic or its fixtures.

OpenSSL is an explicit system prerequisite, not a new Python dependency.
The upstream hosted Ubuntu image inventory lists OpenSSL, but that does not
prove the exact PR runner or native operations work. The new tests fail rather
than silently skip when this prerequisite is missing. Hosted CI on the final
PR head is required. Local preparation and its actual results are recorded
separately from that future CI.

Remaining work includes independently authorized key distribution/custody,
issuer/execution attestations, source provenance, independent-anchor admission,
anchor-aware cycle classification, semantic verification and the complete
adapter. No public test fixture defines a production trust policy. No policy,
required gate, normative status or release-authority code is modified.

## 10. Primary technical references

- [RFC 8032, Ed25519 and section 7.1 test vectors](https://www.rfc-editor.org/rfc/rfc8032.html)
- [OpenSSL 3.0 pkeyutl, Ed25519 raw-input verification](https://docs.openssl.org/3.0/man1/openssl-pkeyutl/)
- [libsodium 1.0.18 ref10, canonical/small-order encoding checks](https://github.com/jedisct1/libsodium/blob/1.0.18/src/libsodium/crypto_core/ed25519/ref10/ed25519_ref10.c)
- [Hosted Ubuntu 24.04 software inventory](https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md)

These references justify the primitive/interface and checked numerical inputs.
They are not evidence of this package's correctness or an independent security
audit. The code uses a separately specified application signature framing.

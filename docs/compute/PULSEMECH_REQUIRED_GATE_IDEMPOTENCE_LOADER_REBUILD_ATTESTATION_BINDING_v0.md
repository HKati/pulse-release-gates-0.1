# B2 original-loader rebuild-attestation binding v0

## Status and scope

This unit preserves two rebuilder attestations for the exact original loader
packages and the public-key response used to check their signatures. It freshly
verifies the selected Ed25519 signature on each attestation and joins every
signed material and product digest to the already preserved original bytes.
These are preserved statements about a separately produced rebuild. Signer
authorization, historical key role and time, authenticated use of the exact
source inputs, and acceptance under a project build-evidence policy remain open.

The development base is `83c5ca277ce94a4d2f03b073d92da66014fb6a24`, after
[PR #3046](https://github.com/HKati/pulse-release-gates-0.1/pull/3046). The
[original-loader build-record binding](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LOADER_BUILD_RECORD_BINDING_v0.md)
and its unchanged startup, readout, static and historical entry prerequisites
are freshly reconstructed before these new relationships are accepted.

| Result | Supplied by this unit |
| --- | --- |
| Preserved public evidence | Exact two attestation responses and one public-key response, with retrieval references and externally selected record bytes. |
| Selected key relationship | Complete bounded decoding of the preserved key response and independent derivation of the selected in-toto key ID. |
| Signature mathematics | Fresh Ed25519 verification of one selected signature on each of the two attested product statements. |
| Signed material | The exact original buildinfo carrier, including its original OpenPGP envelope, matches both signed SHA-256 and SHA-512 values. |
| Signed products | Both complete original `libc6` and `libc6-dbg` package byte streams match their respective signed SHA-256 and SHA-512 values. |
| Other listed signature | Preserved and structurally accounted for; its key and signature remain unverified. |
| Exact source use and trusted rebuild semantics | Not established by the signed material/product relationships. |
| Original buildd authority, source/build gate and B2 completion | Remain open. |

Acceptance establishes the selected signature and byte relationships. It does
not establish organizational independence, complete source-to-binary equivalence,
or an authenticated historical role for the published key.

## Exact preserved carriers

The three original HTTP response bodies are preserved without reserialization:

| Preserved carrier | Bytes | SHA-256 |
| --- | ---: | --- |
| [libc6_attestation.json](required_gate_idempotence_loader_rebuild_attestation_binding_v0/preservation/libc6_attestation.json) | 1,104 | `dc7cc8831246e1fac3aa29d02177f5ce85253fde5d586e1848a869c7805df2c6` |
| [libc6_dbg_attestation.json](required_gate_idempotence_loader_rebuild_attestation_binding_v0/preservation/libc6_dbg_attestation.json) | 1,112 | `9e7e500b1aa181474a4ceb4bde60779fe6adb95ade3812c82833b037b49ceda4` |
| [public_keys.json](required_gate_idempotence_loader_rebuild_attestation_binding_v0/preservation/public_keys.json) | 142 | `ae30bbb97ab1d57cb8bc874571cc8883f9ea44ca105ff27feb3e621c9ac85761` |

The retrieval endpoints are the reproduce.debian.net amd64 service's
[libc6 attestation](https://reproduce.debian.net/amd64/api/v1/builds/269686/artifacts/710018/attestation),
[libc6-dbg attestation](https://reproduce.debian.net/amd64/api/v1/builds/269686/artifacts/710019/attestation)
and [current public keys](https://reproduce.debian.net/amd64/api/v1/meta/public-keys).
These URLs identify where the preserved responses were obtained. Offline
verification uses the pinned response bytes and does not treat an endpoint's
current contents as a project trust selection.

The service's API also exposes the same attestation bytes under trixie build
`288651`, artifacts `780842` and `780843`, alongside the proposed-updates build
`269686`, artifacts `710018` and `710019`. These aliases identify one evidence
set. They cannot be counted as two separately produced rebuilds. API status,
build times and release names remain retrieval context; the signatures cover
the selected `signed` objects, whose contents are described below.

The [service description](https://reproduce.debian.net/) explains its attempt
to reproduce distributed Debian binaries using their original buildinfo files.
The [rebuilderd v0.25 announcement](https://vulns.xyz/2025/09/rebuilderd-v0.25.0/)
describes the daemon's long-term signature and public-key publication mechanism.
Neither description authorizes this key under the project's unresolved build
policy or proves a historical signing time for these particular statements.

## Fresh prerequisite and complete signed-byte joins

The [binding checker](../../tools/check_required_gate_idempotence_loader_rebuild_attestation_binding_v0.py)
freshly reconstructs the preceding build-record result, including the original
buildinfo/changes relationships, selected package bytes and unchanged startup
chain. A saved accepted report cannot replace that computation. The original
entry source remains `03d2c76e06d1f4efaf3a9e7e78dcf16a8be62081`; all 81
historical source bindings retain their original meanings.

Each selected attestation has exactly one material and one product. Both name
`glibc_2.41-12+deb13u4_amd64.buildinfo` as the material. The first product is
`libc6_2.41-12+deb13u4_amd64.deb`; the second is
`libc6-dbg_2.41-12+deb13u4_amd64.deb`. All declared digest algorithms are checked
against complete reconstructed bytes, rather than comparing only the filenames,
versions or saved digest declarations.

| Joined original artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `glibc_2.41-12+deb13u4_amd64.buildinfo` | 15,502 | `5af18d1a381adb80a101b714b57c7822e5f0442f68e148df26b0dbcc4a1ca1e9` |
| `libc6_2.41-12+deb13u4_amd64.deb` | 2,846,580 | `967aa62605721081c3eb2a17650611a792aa802d76a6511d1840242623d204c9` |
| `libc6-dbg_2.41-12+deb13u4_amd64.deb` | 7,373,052 | `0123a767a462c59d75e1bd56c4a0f7192c389f600e4743e807d3d33c679dbcf7` |

The signed buildinfo hash covers the complete original carrier. A valid rebuilder
signature over that hash does not verify the different OpenPGP signature inside
the carrier or authenticate the original buildd's source, toolchain and host
declarations. The prior twenty-row inventory retains its scope: two package
payloads are checked here; the other eighteen payloads are not newly verified.

## Selected envelope, canonicalization and key encoding

The [protocol helper](../../tools/required_gate_idempotence_loader_rebuild_attestation_v0.py)
accepts a closed, bounded profile of the historical in-toto Link/Metablock
envelope. The [ITE-5 appendix](https://github.com/in-toto/ITE/blob/master/ITE/5/README.adoc#appendix)
specifies the `{signed, signatures}` relationship and a signature over the
canonical JSON representation of the `signed` object. The
[in-toto specification](https://github.com/in-toto/specification/blob/master/in-toto-spec.md#4-document-formats)
describes link material/product hashes and public-key identities.

The selected signed profile contains printable ASCII strings, fixed object and
array shapes, and null environment data. It excludes numeric fields, control
characters, non-ASCII text, quotes and backslashes inside signed strings.
Canonicalization recursively sorts object keys and emits compact JSON. Duplicate
keys, unsupported values, extra fields, incomplete rosters and trailing input
cannot be silently discarded or repaired. Raw carrier bounds are enforced before
hashing or parsing, followed by the selected structural bounds. This restricted
profile makes the exact signed message derivation explicit.

The key response has one `current` entry containing a PEM-encoded Ed25519 public
key. Its selected legacy SubjectPublicKeyInfo has exactly 46 DER bytes: the
fixed prefix `302c300706032b65700500032100` followed by 32 public-key bytes.
The OID, lengths, NULL parameter, zero unused-bit count and complete key bytes
are checked as one exact encoding profile. The public-key bytes are:

```text
13ba298a31f08e49f88a736013fd3d4d290867f72dfd2b3e52ba8d30e5451718
```

[RFC 8410, Section 3](https://www.rfc-editor.org/rfc/rfc8410.html#section-3)
requires absent algorithm parameters for conforming Ed25519 SPKI. The preserved
response instead contains an explicit NULL. This unit narrowly recognizes that
observed legacy representation, derives the raw key, and supplies the canonical
absent-parameter representation to the existing OpenSSL verification backend.
It does not describe the original encoding as RFC 8410 conformant or accept
arbitrary ASN.1 variations.

The selected key ID is independently derived from the canonical public-key
object with `keytype="ed25519"`, `scheme="ed25519"`, the raw public key in
`keyval.public`, and `keyid_hash_algorithms=["sha256","sha512"]`. The
[in-toto Rust key implementation](https://github.com/in-toto/in-toto-rs/blob/master/src/crypto.rs)
documents that compatibility field and key-ID calculation. The resulting
SHA-256 key ID is:

```text
2980aa6249ad89ce0ef0f0f5e6d0896214301b2818aad33443444cf460df6ed6
```

Both carriers also list a different key ID:

```text
c70f1852977e382b45eea36783e59dd5f4413e39bdbed773ad0d83aa4d8212b9
```

The selected service-key signature is freshly verified on each canonical
statement through the unchanged
[OpenSSL verifier](../../tools/check_anchor_integrity_record_signatures_v0_1.py).
The different listed signature remains unverified. Two signature entries do not
establish two authenticated witnesses, and the other entry's recorded key ID
does not establish a worker identity. Host-specific verification-backend
observations belong to the generated report, not to authored evidence that
purports to describe the historical rebuild.

## What the signed statements do not cover

Both signed objects have these exact fields:

```text
materials   = one original buildinfo carrier, with SHA-256 and SHA-512
products    = one selected original package, with SHA-256 and SHA-512
environment = null
byproducts  = {}
command     = []
```

They do not list the original `.dsc`, upstream source archive or Debian patch
archive as materials. The original buildinfo also lacks those direct source
checksums. The existing archive/source prerequisite still binds the preserved
source artifacts separately; agreement on the source name and version cannot
add absent source-input hashes to a signed rebuild statement.

There is no build-log digest, command, environment description, builder identity
or signing timestamp in these signed objects. The public log and API metadata
are outside this unit's preserved signed evidence. They cannot fill those gaps
by being presented beside a valid signature. No large rebuild log is required
or included in the repository carrier.

The preserved key response shows the bytes published by a current-key endpoint
at retrieval. It does not authenticate the key's historical role, authorization,
ownership, validity period or signing time. The unit selects no in-toto layout,
accepted builder trust policy or threshold of independent operators. It also
does not rerun the rebuild or observe the claimed build process.

The remaining build-evidence obligation therefore includes an accepted route
connecting the exact source inputs actually used to the original-equivalent
outputs, with explicit signer/role and evidence acceptance rules. Authenticated
original buildd provenance remains a separate possible route. This unit does
not require both that historical route and a rebuild route, and does not make
either route accepted by preserving a new witness.

## Closed record and offline verification

The authored [binding record](required_gate_idempotence_loader_rebuild_attestation_binding_v0/record_v0.json)
and its [closed schema](../../schemas/required_gate_idempotence_loader_rebuild_attestation_binding_v0.schema.json)
fix the exact preserved responses, prior bindings, derived relationships and
remaining limits. An externally selected exact record digest is required;
record fields cannot grant trust to themselves or replace fresh verification.
Source byte bindings and stable-input checks preserve the selected checker
relationship without authenticating an otherwise untrusted host.

From a complete checkout:

```bash
python -I -B tools/check_required_gate_idempotence_loader_rebuild_attestation_binding_v0.py \
  --record docs/compute/required_gate_idempotence_loader_rebuild_attestation_binding_v0/record_v0.json \
  --record-sha256 19c346076b6ec7d5e7d948d13d16a3ba6f45a56b4fdcf9236d9a445dddbc1d7f \
  --output /tmp/loader-rebuild-attestation-binding-check.json
```

The checker publishes canonical JSON exclusively after successful verification.
Invalid input cannot publish an accepted result or overwrite an existing output.
Regression coverage is appended to the existing registered containment module:

```bash
python -m pytest -q tests/test_required_gate_idempotence_containment_v0.py \
  -k loader_rebuild
```

An accepted report uses `status="accepted_rebuild_attestation_binding"`. It
separately reports the verified record/carrier bindings, fresh prior-chain
reconstruction, signature mathematics and signed original-byte joins:

```text
record_binding_verified = true
original_rebuild_carrier_bytes_verified = true
prior_build_record_chain_reconstructed = true
rebuild_signature_mathematics_verified = true
signed_buildinfo_and_product_byte_bindings_verified = true
verified_selected_signatures = 2
unverified_other_signatures = 2
```

Those two verified signatures belong to the same selected published key, one
per product statement. They do not represent two verified rebuild operators.
The protocol helper's `selected_signature_verified=true` is similarly limited
to that mathematical verification. The result preserves these distinct limits:

```text
buildinfo_signature_verified = false
changes_signature_verified = false
trusted_rebuilder_payload_admitted = false
rebuilder_historical_authority_verified = false
signed_source_input_coverage_complete = false
source_build_gate_satisfied = false
original_acquisition_ready = false
b2_complete = false
metric_pass = null
authority_effect = none
```

The original OpenPGP signature, builder-authority and authenticated historical
build-provenance flags remain false. Actual invocation, contemporaneous backing
acquisition, original readouts, same-environment two-slot qualification, bounded
collection, fresh admission and separate owner authorization remain later
obligations. No original native program, toolchain or capability probe is
executed by these artifact and signature checks.

The prior implementation APIs, historical evidence, workflows, main README and
190 Tools / 41 targeted registrations retain their existing bytes.
[Issue #2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879) remains
open under its existing Step 5C completion conditions.

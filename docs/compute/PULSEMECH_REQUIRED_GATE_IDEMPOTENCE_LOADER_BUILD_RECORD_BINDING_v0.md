# B2 original-loader build-record binding v0

## Status and scope

This unit preserves two recovered distribution build-record carriers and checks
their exact relationships to each other and to the already selected original
loader packages. It supplies bounded, independent reconstruction of recorded
claims and byte identities. Cryptographic signature verification, builder
authorization and authenticated historical build provenance remain unestablished.

The development base is `083c09bbd0ffaf8bc317930feebbb150e8dbd2ff`, after
[PR #3045](https://github.com/HKati/pulse-release-gates-0.1/pull/3045). The
[startup and resume acceptance contract](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LOADER_STARTUP_CONTRACT_v0.md)
remains a freshly reconstructed prerequisite.

| Result | Supplied by this unit |
| --- | --- |
| Recovered carriers | Exact complete buildinfo and changes bytes, with external record selection and retrieval references. |
| Envelope structure | Bounded parsing of the selected cleartext OpenPGP envelope and its signature-packet metadata. |
| Cross-record output inventory | All twenty shared package rows agree; the twenty-first changes row binds the complete buildinfo carrier. |
| Selected original payloads | Both original `libc6` and `libc6-dbg` package byte streams are freshly reconstructed and checked against their recorded rows. |
| Other eighteen package payloads | Their declarations are accounted for; their payload bytes are not retrieved or verified by this unit. |
| Historical source, toolchain and host use | Recorded declarations remain unverified as observations of the build process. |
| Signature, signer authority and build gate | Remain false. |
| Live loader resolution and B2 completion | Remain open. |

An accepted binding report establishes the listed byte and record relationships.
It does not turn a structurally valid signature packet into an authenticated
signature or an authorized builder statement.

## Exact carriers and the original filename relationship

The recovered buildinfo carrier is available from the
[buildinfo mirror](https://buildinfos.debian.net/buildinfo-pool/g/glibc/glibc_2.41-12%2Bdeb13u4_amd64.buildinfo).
The changes carrier is available through the
[dated Debian snapshot](https://snapshot.debian.org/archive/debian/20260801T000000Z/dists/proposed-updates/glibc_2.41-12%2Bdeb13u4_amd64-buildd.changes).
These retrieval locations identify the recovered bytes; they do not supply a
selected signer trust policy.

| Preserved carrier filename | Bytes | SHA-256 |
| --- | ---: | --- |
| [glibc_2.41-12+deb13u4_amd64.buildinfo](required_gate_idempotence_loader_build_record_binding_v0/preservation/glibc_2.41-12+deb13u4_amd64.buildinfo) | 15,502 | `5af18d1a381adb80a101b714b57c7822e5f0442f68e148df26b0dbcc4a1ca1e9` |
| [glibc_2.41-12+deb13u4_amd64-buildd.changes](required_gate_idempotence_loader_build_record_binding_v0/preservation/glibc_2.41-12+deb13u4_amd64-buildd.changes) | 8,964 | `9c98aa68df84d1ea077756df7e4e81c3f9972a513fa8da3546a0fc12fcb72e27` |

The original changes payload names the buildinfo member
`glibc_2.41-12+deb13u4_amd64-buildd.buildinfo`. The mirror's retrieved filename
omits `-buildd`. Both spellings are recorded in the explicit relationship; the
checker requires the changes row to match the entire retrieved carrier's size
and checksums. Preservation retains the actual retrieved filename and bytes.
Renaming or reserializing the carrier cannot replace that exact-byte join.

The carriers declare `Source: glibc`, `Version: 2.41-12+deb13u4` and
`Architecture: amd64`. The buildinfo additionally declares a Debian build origin,
an amd64 build architecture, the build time `2026-07-11 17:42:40 UTC`, installed
build dependencies, environment values and
`Build-Path: /build/reproducible-path/glibc-2.41`. The changes maintainer field
names `x86-grnet-03`. Parsing and agreement of these fields do not establish
that the declared source, toolchain or host actually performed the historical
build. In particular, a source name and version are not a checksum of all source
inputs used by a build process.

## Fresh prerequisite and original package reconstruction

The [build-record checker](../../tools/check_required_gate_idempotence_loader_build_record_binding_v0.py)
freshly reconstructs the unchanged startup contract and its prior readout,
binary/debug/source and historical entry prerequisites. A saved accepted report
does not replace that computation. The original entry source remains
`03d2c76e06d1f4efaf3a9e7e78dcf16a8be62081`, with all 81 historical source
bindings retained under their original meanings.

The two complete packages are reassembled from the existing preservation parts
and checked against the recovered records. They are the original package byte
streams already selected by the static loader binding, not the host's installed
libc or newly built substitutes.

| Freshly reconstructed package | Bytes | SHA-256 |
| --- | ---: | --- |
| `libc6_2.41-12+deb13u4_amd64.deb` | 2,846,580 | `967aa62605721081c3eb2a17650611a792aa802d76a6511d1840242623d204c9` |
| `libc6-dbg_2.41-12+deb13u4_amd64.deb` | 7,373,052 | `0123a767a462c59d75e1bd56c4a0f7192c389f600e4743e807d3d33c679dbcf7` |

The original loader and matching debug object retain the package relationships
established by the prerequisite. No original native binary, build toolchain or
capability probe is executed to reconstruct these bytes.

## Closed records, complete joins and bounded parsing

The authored [binding record](required_gate_idempotence_loader_build_record_binding_v0/record_v0.json)
and its [closed schema](../../schemas/required_gate_idempotence_loader_build_record_binding_v0.schema.json)
fix the selected carrier identities, prior implementation bindings, derived record
relationships and unresolved scope. Public verification requires an externally
selected exact-byte record digest. A record cannot grant authority to its own
claims or replace fresh derivation with saved success fields.

The record names the current checker sources. The verification report records
their actual byte hashes, and before/after checks require those source bytes to
remain stable. These checks do not authenticate an otherwise untrusted checker
or host.

The [Deb822 helper](../../tools/required_gate_idempotence_loader_buildinfo_v0.py)
accounts for the complete selected inventories. The buildinfo has
twenty package output rows; the changes has those same twenty rows and one row
for the signed-form buildinfo carrier. Names, sizes and checksum relationships
must agree across the relevant fields and both records. Duplicate, missing,
extra, malformed or conflicting rows cannot be ignored while retaining an
accepted result. The two selected package payloads are checked against freshly
reconstructed bytes; the remaining eighteen rows retain declaration-only scope.

The original `.dsc`, upstream archive and distribution patch archive retain
their separate prerequisite bindings. Neither recovered carrier directly lists
their checksums. Agreement with the selected source name and version does not
create a direct checksum relation from the build records to those source bytes.

Parsing uses finite carrier, line, field and inventory limits. Carrier and record
byte limits are checked before their first hash or parse; the parsers then apply
their own structural bounds. The selected Deb822 grammar and
cleartext-envelope grammar reject ambiguous or unaccounted input rather than
repairing it. The independent derivation preserves the difference between the
complete raw carrier and its extracted cleartext payload.

The [envelope helper](../../tools/required_gate_idempotence_loader_build_envelope_v0.py)
checks the selected ASCII/LF carrier, SHA-512 cleartext header, dash escaping,
single armored packet and CRC-24, and bounded version-4 RSA signature-packet
structure. These format checks do not verify the RSA signature. CRC-24 and a
packet's recorded digest prefix are not signer authentication.

Both original packets declare canonical-text signature class `01`, RSA with
SHA-512, creation time `2026-07-11 17:43:09 UTC`, and issuer fingerprint:

```text
E59235957BF95A38472158EC37C520CAEF5D4224
```

That value is derived from the packet metadata. The corresponding public key
has not been authenticated, and the issuer's primary-key relationship has not
been established. Matching issuer metadata in two carriers does not independently
authenticate either carrier or authorize its claimed builder role.

## Concrete remaining signer and build-evidence gate

For the signed-record route, the next missing evidence is the exact public key
and an independently authenticated Debian authorization record for that key's
buildd role, architecture and relevant time. A historical official keyring with
authenticated checksum provenance, or an administrator-signed key-addition
record with independently selected administrator authority, could supply the
needed material. Each candidate route still requires review and actual
verification; a download URL, user ID or self-asserted fingerprint is insufficient.

Debian's [buildd key-admission implementation](https://salsa.debian.org/ftp-team/dak/-/blob/master/scripts/debian/buildd-add-keys)
and [keyring preparation implementation](https://salsa.debian.org/ftp-team/dak/-/blob/master/scripts/debian/buildd-prepare-dir)
describe administrator-authorized key admission and signed keyring checksums.
Those mechanisms do not establish that this particular historical key was
admitted. The existing selected archive Release signers retain their archive
role; this unit does not extend that selection to buildd signatures.

After key and role evidence becomes available, a fresh cryptographic check must
use the exact selected carriers and independently selected trust inputs. The
time, expiration and revocation treatment must be explicit. The current envelope
parser does not choose those policies or invoke a cryptographic verifier.

Authenticated historical build provenance and independently reproduced
source-to-binary equivalence are distinct possible evidence obligations. This
unit selects neither an unsigned rebuild record as authenticated provenance nor
a requirement to complete both approaches. The existing source/build gate needs
an accepted, verified route; it stays unsatisfied here.

Live invocation, contemporaneous backing acquisition, original readouts,
same-environment two-slot qualification, bounded collection, fresh admission and
separate owner authorization remain later obligations. No preserved old child
is resumed, and no new acquisition is authorized by record acceptance.

## Offline verification and result boundary

From a complete checkout:

```bash
python -I -B tools/check_required_gate_idempotence_loader_build_record_binding_v0.py \
  --record docs/compute/required_gate_idempotence_loader_build_record_binding_v0/record_v0.json \
  --record-sha256 c15c85e2b875a3deff90576c0c0b1162cc0d91a511271598076b703ad71e2309 \
  --output /tmp/loader-build-record-binding-check.json
```

The checker publishes canonical JSON exclusively after successful verification.
A rejected input cannot publish an accepted report or overwrite an existing
output. Regression coverage is appended to the existing registered containment
module:

```bash
python -m pytest -q tests/test_required_gate_idempotence_containment_v0.py \
  -k loader_build
```

These are data-only checks. The prior implementation APIs, historical evidence,
workflows, main README and 190 Tools / 41 targeted registrations retain their
existing bytes. An accepted report uses `status="accepted_record_binding"` and
records the verified carrier/record joins and the fresh prior reconstruction.
Its key boundaries remain:

```text
signature_verified = false
builder_authority_verified = false
authenticated_payload = false
authenticated_build_provenance = false
source_input_hashes_directly_attested = false
other_binary_output_bytes_verified = false
source_build_gate_satisfied = false
original_acquisition_ready = false
b2_complete = false
metric_pass = null
authority_effect = none
```

[Issue #2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879) remains
open under its existing Step 5C completion conditions.

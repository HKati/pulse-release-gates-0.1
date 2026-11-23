# B2 original-loader rebuild acceptance policy v0

## Status and decision

This unit implements one candidate acceptance policy and a bounded, independent
data-only checker for the selected original loader's source/build prerequisite.
It follows the [rebuild-attestation binding](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LOADER_REBUILD_ATTESTATION_BINDING_v0.md)
and preserves every historical record unchanged. Its development base is
`846db3d94d7fc869b6a8d20bdc98efe6d26c81b4`, after preservation of the completed
[hosted two-slot qualification](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LOADER_TWO_SLOT_HOSTED_v0.md#completed-hosted-qualification-452531882861).

The policy explicitly selects a possible trust relationship: the current
`reproduce.debian.net` daemon's endorsement of a stored successful rebuild,
together with a reviewed source-resolution policy for the exact preserved log
and source bytes. It does not establish that the project has adopted that trust
relationship. A caller must separately select the exact policy digest. Neither
the policy file's presence, a merge, an authored record, nor a saved verification
report supplies that selection.

| Invocation | Fresh evidence checks | Policy selection | Source/build gate under this policy |
|---|---|---|---|
| Default candidate evaluation | Required | Pending | Blocked |
| Exact externally selected policy digest | Required again | Selected by this caller | Satisfied only if every check passes |
| Changed policy, subject, key, evidence, prerequisite or expected digest | Rejected | Cannot promote the input | Blocked |

The narrow positive result is `source_build_gate_satisfied_under_policy=true`.
It is conditional on the explicitly selected trust assumptions below. It does
not authenticate the caller as the owner. It does not authorize original-loader
acquisition, qualify another host, prove native execution or close B2.

The report also retains the preceding record's historical false boundary fields,
including `source_build_gate_satisfied` and `project_rebuild_policy_selected`.
Those inherited fields are not rewritten by a caller's selection. Consumers
must evaluate the explicitly scoped `source_build_gate_satisfied_under_policy`
result and its exact external policy selection together; a historical field or
a saved report cannot stand in for that fresh decision.

## Reviewable files

| File | Purpose |
|---|---|
| [Policy](required_gate_idempotence_loader_rebuild_acceptance_v0/policy_v0.json) | Exact subject, service role, verification-time scope, source-resolution rules, trust assumptions and remaining obligations. |
| [Reference record](required_gate_idempotence_loader_rebuild_acceptance_v0/record_v0.json) | Candidate evidence relationships, reconstructed from the preserved inputs without an adoption claim. |
| [Public service evidence](required_gate_idempotence_loader_rebuild_acceptance_v0/preservation/public_service_evidence_v0.zip) | Complete retrieved response representations, implementation references, retrieval metadata and upstream notices. |
| [Bounded helper](../../tools/required_gate_idempotence_loader_rebuild_acceptance_v0.py) | Closed archive decoding and independent reconstruction of log/source/service facts. |
| [Independent checker](../../tools/check_required_gate_idempotence_loader_rebuild_acceptance_v0.py) | Fresh preceding proof, exact policy/evidence joins and separate caller policy selection. |
| [Closed schema](../../schemas/required_gate_idempotence_loader_rebuild_acceptance_v0.schema.json) | Reference record and exact policy grammar. |

External implementation files remain unchanged, attributed evidence under their
upstream notices and preserved licence texts. The checker does not import or
execute the preserved Rust, shell or Perl files.

## What the new evidence contributes

The preserved [build metadata](https://reproduce.debian.net/amd64/api/v1/builds/269686)
names `glibc`, version `2.41-12+deb13u4`, architecture `amd64`, build `269686`
and status `GOOD`. Those fields are service statements, not authenticated
historical facts on their own. The corresponding
[log response](https://reproduce.debian.net/amd64/api/v1/builds/269686/log)
contains exact source download and hashing records for these three files:

| Complete original input | Bytes | SHA-256 |
|---|---:|---|
| `glibc_2.41-12+deb13u4.dsc` | 7,576 | `0915324aa646bb99abfaa9aa6ecb734b30babd28454a3e51f3152912370fbd3e` |
| `glibc_2.41.orig.tar.xz` | 20,323,540 | `f24aa441021121a79266f0d75242706cab8843a47901fefe74527491807f1998` |
| `glibc_2.41-12+deb13u4.debian.tar.xz` | 499,524 | `dda4153511bfd543502d18e5bc9323110996fe9c531f14ae3fad6eb17f027c7d` |

The checker joins the log's APT URI/size/SHA-256 rows and `dcmd` SHA-256 rows to
these complete original bytes. It also requires the exact source/version,
selected buildinfo invocation, sibling `.dsc` passed to `sbuild`, and the source
unpack records. The preceding archive/source/binary/debug/startup/build-record
chain is reconstructed from its complete selected carriers; a claimed source
name or a caller-supplied digest table cannot substitute for those bytes.

The log response is **20,971,567 bytes and explicitly truncated**. Its final
marker is `TRUNCATED DUE TO SIZE LIMIT: 20971520 bytes`. This is the complete
retrieved response representation, not a complete historical build transcript.
Its SHA-256 is
`014cdf663727e61b0e5c4c8a761be3374cdb249479abfd9ab4348ce995d721a4`.
The policy accepts the retained source-resolution records; it does not infer
terminal rebuild success from the missing end of the log.

Fresh retrieval also preserved the current key response and both package
attestations. All three are byte-identical to the earlier carriers. The checker
requires this same-byte relationship, then reruns the earlier Ed25519 checks
against the complete original buildinfo and both complete package payloads.
It verifies one selected signature per product. The other listed signature is
still unverified and does not establish a second independent rebuilder.

## The concrete trust choice

The [service overview](https://reproduce.debian.net/) describes rebuilding the
distributed Debian packages using their buildinfo records. The preserved
[worker implementation](https://github.com/kpcyrd/rebuilderd/blob/8c996c248f9b9668fa62fcd8fe8aa2fd0ed7b999/worker/src/rebuild.rs)
creates a signed Link after finding a rebuilt output and comparing it equal to
the original package. This explains the reviewed statement semantics; it does
not prove which code the historical service actually deployed.

There is a critical role distinction. The reviewed
[daemon endpoint](https://github.com/kpcyrd/rebuilderd/blob/8c996c248f9b9668fa62fcd8fe8aa2fd0ed7b999/daemon/src/api/v1/build.rs)
can call an [attestation helper](https://github.com/kpcyrd/rebuilderd/blob/8c996c248f9b9668fa62fcd8fe8aa2fd0ed7b999/daemon/src/attestation.rs)
that appends a current daemon signature to a stored statement when serving it.
The selected key is therefore accepted only in the role of current service
endorser of the preserved statement. It is not treated as the historical worker
key, an authenticated signing time, a new rebuild at retrieval time or a second
independent observation.

The selected raw Ed25519 key is
`13ba298a31f08e49f88a736013fd3d4d290867f72dfd2b3e52ba8d30e5451718`;
the independently derived in-toto key ID is
`2980aa6249ad89ce0ef0f0f5e6d0896214301b2818aad33443444cf460df6ed6`.
The policy fixes these values independently of the supplied response bytes.
It covers only the exact reviewed 2026-11-23 UTC snapshot. Offline replay makes
no claim about subsequent key authority, revocation or current endpoint state.
Retrieval timestamps and HTTP `Date` headers are preserved observations, not
cryptographic timestamps or independently authenticated delivery provenance.

Selecting this policy means accepting the service's worker build/comparison
behavior, its stored build/log/artifact associations, its daemon signing and
control plane, and the reviewed retrieval origin of the preserved responses.
In particular, it accepts that the unsigned source log and metadata belong to
the build represented by the two daemon-endorsed attestations. The checker
verifies the exact byte joins; the association remains an explicit trust
assumption. The signatures directly cover the buildinfo and products, not the
three source archive hashes or the log digest.

This is one service endorsement. It does not establish an independent-operator
quorum or independent observation of source-to-binary equivalence. The result
must not be presented as authenticated original-build provenance.

## Source verification limits remain visible

The log itself reports that the buildinfo's GPG signature was not validated
and that the `.dsc` inline signature could not be verified. The helper retains
these observations. The nearby `.dsc` checksum-success message does not turn
them into verified signatures. The reviewed
[debrebuild source](https://sources.debian.org/data/main/d/devscripts/2.26.15/scripts/debrebuild.pl)
derives the sibling `.dsc` filename and adds its checksums; the original
buildinfo does not directly bind the `.dsc` digest.

The selected source bytes already participate in the preceding
[archive/source/binary binding](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LOADER_BINARY_BINDING_v0.md).
This new unit reconstructs that chain and retains its historical archive
signature evidence and externally selected archive keyring as trust inputs.
It does not add a fresh archive-signature verification or authenticate the
unresolved original buildd signer. The separate original-buildd route remains
available without becoming a prerequisite for this explicitly selected route.

## Verification and rejection behavior

All new external input extents are bounded before their hashes or parses.
Archive processing checks the exact member roster, regular-file type, names,
metadata, declared and actual extents, decompression limits, checksums and full
byte bindings. No member is extracted to an executable path. The checker uses
the existing fixed `/usr/bin/openssl` verification backend for public signature
data, including positive/negative self-tests and stable backend identity.

The independent checker freshly reconstructs the preceding proof, derives the
new service/source facts, validates the closed record and exact policy, and
compares every derived relationship. Source pre/post checks bind the inspected
implementation to the report. Host-specific OpenSSL observations are excluded
from the authored reference record and retained in each fresh verification
report. No saved report, arbitrary key, caller approval boolean, packet-supplied
policy or rewritten prior boundary can supply acceptance.

The reference policy and record use separate external identities. From a
complete checkout, candidate evaluation is:

```bash
python tools/check_required_gate_idempotence_loader_rebuild_acceptance_v0.py \
  --record docs/compute/required_gate_idempotence_loader_rebuild_acceptance_v0/record_v0.json \
  --record-sha256 99936de0b0bc2c0e9f0ed52d66cd6a1d7c8d567c55c7cb25c762e04d3f7a6240 \
  --policy docs/compute/required_gate_idempotence_loader_rebuild_acceptance_v0/policy_v0.json \
  --output /tmp/loader-rebuild-candidate-v0.json
```

Only after review of the trust choice, an externally selected invocation adds
this exact argument to the same command and uses a different new output path:

```text
--accepted-policy-sha256 1b1e4f414ffa7e56a8494f8a6d6051594c800cae978fa90585c4a02041bed953
```

The literal identities above are review inputs. Recomputing a trusted expected
digest from whatever file arrived would not make that input independently
selected. Both modes rerun the evidence checks. Output creation is exclusive:
an invalid input cannot publish an accepted report or replace an existing file.
A positive test of the selected branch is an implementation test, not evidence
of project adoption or owner authorization.

## Position in B2

The preserved hosted two-slot run remains a completed synthetic qualification
for its selected environment. This package supplies the separate source/build
acceptance mechanism. Default evaluation leaves selection pending; explicit
selection can satisfy only its narrowly named gate under the stated policy.
Earlier records and their false boundaries remain historical evidence.

The next implementation unit is the bounded original-loader collector and its
independent raw-event checker. That unit must consume a freshly derived policy
decision, qualify the actual environment and readout conditions, bind the
original inputs, and preserve complete or incomplete attempts. It cannot use
this saved report as an admission token. A fresh original acquisition still
requires separate owner authorization.

`original_acquisition_ready=false`, `original_acquisition_authorized=false`,
future-host admission is false, `b2_complete=false`, `metric_pass=null` and
`authority_effect=none`. No original loader, original launcher, model, Q2 or Q3
measurement is executed here. [Issue #2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879)
keeps its complete whole-runtime scope.

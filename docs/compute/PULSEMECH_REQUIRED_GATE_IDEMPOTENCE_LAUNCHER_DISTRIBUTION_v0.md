# Idempotence launcher distribution authentication v0

## Status and scope

**Implemented: fresh detached-signature verification and independent reconstruction
of the signed Release, complete package index, original Debian package and selected
launcher relationship. The result is relative to a separately selected trust
policy. Actual host qualification and selected-runtime execution remain open;
B2 is incomplete.**

The [launcher and passive host binding](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LAUNCH_HOST_v0.md)
already connects the preserved entry-build outputs to the containment entry,
the original package member to the launcher, and every selected static native
dependency to its consumer. This continuation checks a further concrete
relationship: whether the original distribution publication authenticates those
same package bytes under an explicit external trust selection.

The check follows the archive relationship described by
[Debian's apt-secure documentation](https://manpages.debian.org/trixie/apt/apt-secure.8.en.html):
the Release signature authenticates an index digest, and the complete index binds
the package digest. That relationship does not establish upstream source-to-binary
build provenance, package safety, actual loader behavior or an executed property.
Those remain separate questions with their own evidence requirements.

| Component | Responsibility |
| --- | --- |
| [Coordinator](../../tools/required_gate_idempotence_launcher_distribution_v0.py) | Read the original input roster, publish a reconstructed record or fresh verification report, and optionally preserve each verifier invocation. |
| [Independent checker](../../tools/check_required_gate_idempotence_launcher_distribution_v0.py) | Reconstruct the old launch-host result and the new distribution chain from original bytes; require exact canonical record equality. |
| [Signature adapter](../../tools/required_gate_idempotence_distribution_signature_v0.py) | Execute the explicitly selected GPG verifier in a fixed, bounded, offline verification profile and validate every signature occurrence. |
| [Metadata reader](../../tools/required_gate_idempotence_debian_metadata_v0.py) | Parse the complete Release and Packages documents, evaluate the selected time policy, and reconstruct exact digest, size and package-identity relationships. |
| [Closed schema](../../schemas/required_gate_idempotence_launcher_distribution_v0.schema.json) | Define selection, trust policy, record, metadata and verification shapes, including all unchanged authority boundaries. |
| [Existing containment regression module](../../tests/test_required_gate_idempotence_containment_v0.py) | Exercise original-input reconstruction, real verifier use with public authored fixtures, substitution failures and bounded diagnostics. |

No workflow or dependency changes are required. Regressions extend the already
registered module: Tools remains 189 entries and targeted pytest remains 40.

## Two external selections and original evidence

The distribution selection uses
`record_type=required_gate_idempotence_launcher_distribution_selection_v0` and
`profile=debian_detached_release_launcher_distribution_v0`. Its external SHA-256
binds the original launch-host plan, the separate trust policy, the exact Release
and detached signature, repository identity, full compressed and decoded indexes,
and selected package identity, filename, size and digest. Its `example` or
`selected` status must equal the reconstructed launch-host status.

The trust policy uses
`record_type=required_gate_idempotence_distribution_trust_policy_v0` and
`profile=gpg_detached_release_trust_v0`. A separate external SHA-256 binds:

- The original keyring's exact digest and size.
- The explicitly trusted GPG executable's absolute path, exact digest and size.
- The complete required roster of full signing-key and primary-key fingerprints.
- An explicit UTC evaluation epoch, maximum Release age and `Valid-Until` rule.

The signature cannot choose its own trusted keyring or authorize its own signer.
The caller must review and select these trust inputs independently. The
[Debian archive-key page](https://ftp-master.debian.org/keys.html) documents key
identities but explicitly warns against relying on that page alone to establish
key authenticity. This implementation does not authenticate the acquisition of
the selected trust root or prove current revocation-list completeness.

The checker also requires all original inputs of the old launch-host plan:
runtime/operator/bootstrap selections and capsule, bootstrap plan, containment
selection and request, original fifteen entry-build files, original package,
selected native bytes and the previously captured passive observation. Rehashing
a new derived record cannot replace any of these externally selected inputs.
Selected repository source retains the existing local Git readmission checks
with network transports disabled; this continuation adds no source acquisition.

## Fresh signature verification

Every `derive_record` and `verify_record` performs a fresh verification of the
original signature and Release bytes. Saved status text and saved success flags
are diagnostic evidence only; the checker has no transcript-admission input.

The adapter reads the selected GPG binary through a regular, executable file,
verifies its size and SHA-256, and seals those bytes before execution. The keyring,
signature and Release are also sealed. The fixed command supplies a private
homedir, no default configuration or keyring, no automatic key retrieval/import
or helper startup, and the chosen time through `--faked-system-time EPOCH!`.
There is no shell or package-manager invocation. The verifier must be a native
ELF executable; a script cannot substitute an unbound shebang interpreter.

The verifier's dynamic dependencies, the Python verification environment and the
kernel are external trusted components. Sealing the GPG executable does not
establish their complete closure. GPG options and status formats are described
in the [GnuPG manual](https://www.gnupg.org/documentation/manuals/gnupg/)
and its [machine-interface documentation](https://github.com/gpg/gnupg/blob/master/doc/DETAILS).

Each `NEWSIG` group must independently contain exactly one matching `GOODSIG`
and `VALIDSIG`. The observed signing/primary fingerprint pairs must exactly equal
the required roster; an additional, missing, duplicate, unauthorized, expired,
revoked, incomplete or bad signature rejects the whole verification. A good
signature in another group cannot mask it. Key IDs and user-ID text never grant
signer authority.

The finite profile accepts version-4, class-`00` detached signatures, using RSA,
ECDSA or EdDSA and SHA-256, SHA-384 or SHA-512. Original ASCII armor is accepted
through GPG without rewriting its bytes. Signature timestamps must agree with
their reported dates, lie at or before the evaluation epoch, and be at or after
the signed Release date. An expiring signature must still be valid at that epoch.

The verifier has a 20-second wall deadline and separate 64-KiB status/stdout and
stderr caps. After a failed attempt is stopped, pending bytes from both pipes are
drained nonblockingly up to their remaining caps before closure. An optional
trusted sink preserves the raw streams and input-bound process record before
verification returns or raises. Preservation failure prevents acceptance.

## Full metadata and package reconstruction

The metadata reader checks the complete original Release document. Origin,
label, suite, codename and version must match the external selection; the chosen
component and architecture must be listed. Duplicate fields, folded identity
fields, control characters, malformed digest rows, duplicate digest paths,
ambiguous package paragraphs and noncanonical sizes reject.

Both selected index descriptors must match signed SHA-256 rows:

```text
<component>/binary-<architecture>/Packages.xz
<component>/binary-<architecture>/Packages
```

The original compressed bytes must match their descriptor. The reader then
decodes exactly one complete xz stream, rejects trailing or concatenated data,
and checks the entire decoded document's digest and size. It scans every package
paragraph. Exactly one selected name/version/architecture occurrence must match
the selected filename, original package digest and size. A cropped stanza cannot
stand in for the authenticated complete index.

That exact package identity and byte binding must also equal the old launch-host
selection. The unchanged old checker again proves that the selected package
member equals the same launcher bytes and that both preserved build outputs equal
the same containment entry. The new record binds the old canonical report without
changing that report or its original claims.

| Bound | Maximum |
| --- | --- |
| Selection, trust policy, Release or keyring | 1 MiB each |
| Detached signature | 64 KiB |
| Compressed Packages index | 16 MiB |
| Decoded Packages index | 128 MiB |
| Xz decoder memory | 64 MiB |
| Deb822 line | 128 KiB |
| Package paragraph | 256 KiB |
| Package paragraphs | 250000 |
| Digest rows per Release digest field | 16384 |
| Selected GPG executable | 32 MiB |
| Required signature pairs | 8 |

The 128-KiB line bound admits the preserved real index's 75649-byte `Provides`
line while retaining a finite parser. This original index is not shortened to
avoid the long field.

Time checks use the externally selected epoch, never an ambient current-time
claim. Release date must be at or before evaluation and within the selected
maximum age. If `Valid-Until` exists it must be at or after the Release date,
and evaluation must be at or before it. The policy may require that field; its
absence then rejects. This does not prove that a newer publication does not exist.

## Commands and retained verification evidence

The new coordinator supports only `prepare` and `check`. Supply the same original
input flags used by the launch-host coordinator, plus:

```text
--launch-host-plan FILE --launch-host-plan-sha256 SHA256
--distribution-selection FILE --distribution-selection-sha256 SHA256
--trust-policy FILE --trust-policy-sha256 SHA256
--release FILE
--release-signature FILE
--packages-xz FILE
--keyring FILE
--verifier ABSOLUTE_GPG_PATH
```

`prepare` requires `--output NEW_RECORD`. It derives the record, freshly checks
the exact result, publishes the record and prints the canonical accepted report.
`check` additionally requires `--record FILE --record-sha256 SHA256`; it freshly
reconstructs the record and prints its canonical report. Its optional
`--output NEW_REPORT` preserves the same report bytes.

`--verification-directory NEW_DIRECTORY` preserves each fresh GPG invocation as
`verification-N.status.bin`, `verification-N.stderr.bin` and
`verification-N.process.json`. Prepare makes two invocations and check makes
one. The process record retains input and backend bindings, exact command profile,
evaluation epoch, exit status, limits, capture completeness and raw-stream
bindings. Failed-attempt diagnostics remain available. The directory and output
files must be new; existing outputs are never overwritten.

The canonical relationship record excludes process IDs, durations and temporary
paths. These remain in the raw process evidence, so independent fresh executions
can yield identical canonical reports while preserving their distinct attempts.
The record binds the checker, schema, metadata reader, signature adapter and
unchanged sealed-buffer helper source bytes. This finite source roster is not a
claim that the complete verification environment has been recovered.

## Completed original-byte validation

The separate delivery validation archive preserves a completed example using
the original Debian trixie publication with `Suite: stable`, `Version: 13.7`
and `Date: Sat, 12 Sep 2026 07:55:41 UTC`. It retains the exact original Release,
detached signature, full compressed and decoded indexes, copied keyring, original
package and original launcher/build/host inputs. The complete decoded index has
68825 package paragraphs.

The external example policy selects `/usr/bin/gpg`, exact verifier bytes and all
three signing/primary-key pairs. Its evaluation epoch is `1794787200`
(`2026-11-16T00:00:00Z`), with a 7776000-second maximum Release age. This original
Release has no `Valid-Until`; the policy explicitly permits its absence. Keyring
acquisition and current key/revocation freshness remain external trust questions.

| Original object | Bytes | SHA-256 |
| --- | ---: | --- |
| Release | 138612 | `ed56aac47e7911e65ee63aae8d67e29f20e023f840e49f8ed037043a33de138a` |
| Release.gpg | 1760 | `9f80d5c8e4f9fd918a8b4fedd35c00ecc6c1a3ca9eddbc981c83823d4a4b8dc4` |
| Full Packages.xz | 9678380 | `7778d3e3f303b7ddb8ce0fe7c8d57473a076c6bf2e8f241f75421d2396352498` |
| Full Packages | 56620099 | `4f2c68d67001d595fbd343f6dbad44468953a51c4d9dec3a4803249f6e295940` |
| Original bubblewrap `0.12.0-1~deb13u1` amd64 package | 56876 | `70aca4fa8daeacb677ec00e8063eb586f08ae3d94b1f11e684370b5524c43431` |
| Selected launcher bytes | 80248 | `573236e5328ac2ebb08f59ae3a9805b4f8d12bdef14be8af4450d5463294985f` |

Two separate processes ran the same independent checker from 43 preserved source
files, using the same original inputs. Each freshly invoked the selected sealed
GPG verifier and accepted all three required signature groups. Both exited zero
and produced byte-identical canonical accepted reports:

```text
launcher-distribution-record.json
size_bytes: 6142
sha256: 1f0259701194b485fdb15a442ce1a3e72c9d60d136d6b308468b40a4d1b85060

canonical verification report (both processes)
size_bytes: 3780
sha256: a0d7cf825dce1c8a3b09a2306f155f24bdcabc4a16cb90215f6d4e04925f4f36
```

The original launch-host plan remains 10792 bytes with SHA-256
`314acd23ea1ba43dc3ccf337d0171473c43422c7c026d9548d104d88c968bcf5`;
its canonical report remains 4284 bytes with SHA-256
`720a2cf4ade0e2b575440e4b3e02bee8df9ef754d2f120ac4632fa9fc1ce9806`.
The new record binds both unchanged objects. The validation archive retains raw
per-invocation GPG status, stderr and process records, source copies, external
selection hashes and an offline replay entry point.

This is an `example` record: the prior runtime/bootstrap inputs are authored and
inert, while the distribution, package and hosted build bytes are original.
No preserved launcher, entry, selected runtime, operator or model executes.
The separately completed containment regression module passes all 409 cases
(268 existing cases unchanged and 141 additions); the CI manifest smoke also
passes with the 189/40 registrations unchanged.

## What an accepted result establishes

The new report can set exactly these additional relation results to true:

```text
distribution_signature_verified
release_index_binding_verified
index_package_binding_verified
package_launcher_binding_verified
launcher_distribution_authenticated
```

The old broad `launcher_origin_authenticated` flag remains false: distribution
publication authentication does not complete upstream/source-to-binary provenance.
The original launch-host plan and report retain their exact bytes and original
scope. The new record refines the outstanding origin question to
`upstream_source_and_launcher_build_origin` without rewriting historical evidence.

`distribution_trust_freshness_verified`, `current_repository_freshness_verified`,
`verifier_runtime_closure_verified` and `launcher_build_origin_verified` remain
false. All inherited execution, host qualification and authority boundaries
remain unchanged, including `authority_effect=none` and `metric_pass=null`.

The next observed-attempt work must establish the same attempt's host identity,
actual mapped native objects, namespace and filesystem behavior, syscall denials,
descriptor closure, resource bounds and retained failure output. A passive
snapshot and pre/post file hashes do not identify the objects actually mapped
through launcher forks and exec transitions. That investigation requires a
separately reviewed observation mechanism and selected-bootstrap integration.

The separate [fixed-probe stopped mapping observation](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_MAPPING_OBSERVATION_v0.md)
develops one such primitive using exact authored probe bytes, an owned stopped
child, the actual executable descriptor and the retained sealed file object.
Its cooperative checkpoint concerns that probe only; it does not observe this
original launcher, authenticate its full dynamic path or alter this distribution
record and its accepted report.

The historical Q3 artifacts, original verification run `43514702328/1`, Q2
`FAIL 49/50 +1 UNKNOWN`, all twelve unsupported gates and the open whole-runtime
I/E work in [#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879)
remain intact. Broader plan steps 6 and 7 remain separate outstanding work.

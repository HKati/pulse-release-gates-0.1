# Idempotence launcher and passive host binding v0

## Status and scope

**Implemented: independent reconstruction of the entry-build-to-containment
binding, Debian-package-to-launcher byte equality, a complete selected static
native dependency graph, and a bounded passive host observation. Actual host
qualification and selected-runtime execution remain open. B2 is incomplete.**

The subsequent [launcher distribution authentication](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LAUNCHER_DISTRIBUTION_v0.md)
reconstructs the original signed Release, complete package index and same package
binding under an externally selected trust policy. It adds a distinct checked
relationship while retaining this plan and its canonical report unchanged.

The [first hosted entry-build observation](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_ENTRY_BUILD_v0.md#completed-hosted-observation--438544782481)
already preserves two equal entries and the separately verified hosted
attestation. This continuation connects that concrete evidence to the entry
selected by the [containment request](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_CONTAINMENT_v0.md).
It also checks which exact package member supplies the outer launcher, which
native objects its declared loading relationships require, and what the observer
can read about the proposed host before any launcher invocation.

The existing containment backend executes a sealed copy of the launcher through
`/proc/self/fd`. A dynamic launcher's interpreter and native dependencies are
resolved by the host before the private execution view exists. Therefore the
launcher hash and the entry-build result leave a separate, concrete dependency
relationship to check. The new plan records that selected relationship and the
remaining behavioral obligations.

| Component | Responsibility |
| --- | --- |
| [Coordinator](../../tools/required_gate_idempotence_launch_host_v0.py) | Capture one passive snapshot, read the exact selected input roster and publish a newly reconstructed plan or verification result. |
| [Independent checker](../../tools/check_required_gate_idempotence_launch_host_v0.py) | Re-admit the original containment/build inputs, reconstruct all byte relationships and interpret the bounded host observations. |
| [Offline Debian package reader](../../tools/required_gate_idempotence_launcher_package_v0.py) | Bind a plain package member to original `.deb` bytes and exact control identity without installation, extraction or execution. |
| [Selection and observation schema](../../schemas/required_gate_idempotence_launch_host_v0.schema.json) | Require closed inputs with externally selected digests and unchanged authority boundaries. |
| [Existing containment regression module](../../tests/test_required_gate_idempotence_containment_v0.py) | Exercise the new relationships, substitutions, host states, bounded package parsing and command-line behavior. |

No workflow, dependency lock, CI manifest, existing entry source or existing
runtime/containment implementation changes. Regressions extend the existing
registered module: Tools remains 189 entries and targeted pytest remains 40.

## Original inputs and independent reconstruction

The closed selection has
`record_type=required_gate_idempotence_launch_host_selection_v0` and
`profile=linux_x86_64_bubblewrap_launch_host_v0`. Its exact external digest binds:

- The original containment request and its `example` or `selected` status.
- The entry-build source commit, request digest and closed record digest.
- An exact native inventory, with independent relative preservation paths,
  declared absolute host paths, roles, sizes and SHA-256 values.
- Each consumer's interpreter and `DT_NEEDED` provider edges.
- The original Debian archive digest, member path and package/version/architecture.
- The exact passive host-observation bytes.
- False execution, qualification, authentication and authority-promotion flags.

The checker re-admits the containment preparation from its original bootstrap,
runtime and operator inputs. It reconstructs the request and checks the retained
external digest; an edited prepared object or rehashed replacement request
cannot substitute for that reconstruction.

It invokes the existing entry-build record checker over the original fifteen
evidence files and the externally selected source/request/record identity.
**Both original build outputs must equal the containment entry bytes.** The
original build source must also equal the installed entry source and its
containment binding. The fixed policy source and emitted seccomp bytes remain
bound through the unchanged containment reconstruction.

The launcher's selected native bytes must equal the containment launcher's
original bytes. Its declared host path must equal the containment selection's
launcher path. The selected member of the original `.deb` must then equal those
same launcher bytes. Accepted membership requires an executable regular member
without setuid or setgid mode bits. Package metadata is not permission to execute
the launcher, and installed file capabilities are not inferred from member bytes.

`verify_plan` reconstructs the complete canonical plan from these originals and
requires byte-for-byte equality. The checker does not import the coordinator,
execute a package program, launcher, preserved entry, selected runtime or model,
or retrieve external data. Re-admitting selected repository source retains the
existing local Git checks with network transports disabled. Reports can set
only these new, narrow relation results to true:

```text
entry_build_binding_verified
launcher_package_member_verified
launcher_native_bindings_verified
host_observation_record_verified
```

## Finite Debian member profile

The package reader accepts exactly the ordinary `ar` roster `debian-binary`,
`control.tar[.gz|.xz]`, `data.tar[.gz|.xz]`, in that order. The first member must
contain exactly `2.0\n`. It rejects extra members, malformed headers, duplicate
or reordered members, truncation and trailing data. This is a deliberately
finite profile within the broader [Debian binary format](https://manpages.debian.org/trixie/dpkg-dev/deb.5.en.html).

Decompression is bounded and accepts one complete gzip or xz stream; appended
streams and unsupported compression, including zstd, reject. Ordinary v7, GNU
and POSIX ustar headers are supported. PAX, GNU long-name/long-link, sparse,
device and other extension records reject, so hidden path, size or capability
overrides cannot change the selected member's interpretation.

One leading `./` is normalized in raw tar member names. Absolute paths,
traversal, normalized duplicates and a non-directory ancestor reject. A selected
symlink or hardlink rejects. Other ordinary link headers may be present, but the
reader never follows a link or extracts a file. Control identity fields must be
unambiguous: duplicate field names, identity continuations, multiple paragraphs
and mismatched package/version/architecture reject.

| Bound | Maximum |
| --- | --- |
| Original `.deb` | 32 MiB |
| Decoded control and data archives together | 128 MiB |
| Decoded control archive | 4 MiB |
| Control file | 256 KiB |
| Selected native member | 16 MiB |
| Tar members across both archives | 4096 |
| Xz decoder memory | 64 MiB |

The result binds the original package, all three raw `ar` members, the decoded
tar archives and the selected plain member. No maintainer script, package manager,
loader or launcher is invoked. Authenticated repository indexes, distribution
signatures and source-to-binary provenance remain separate obligations.

### Real package observation

The reader was checked against the actual
[Debian trixie bubblewrap `0.12.0-1~deb13u1` amd64 package](https://packages.debian.org/trixie/bubblewrap),
downloaded from the [official Debian pool](https://deb.debian.org/debian/pool/main/b/bubblewrap/bubblewrap_0.12.0-1~deb13u1_amd64.deb).
The original `.deb` and the validation record are retained in the separate
delivery validation material, outside the repository file package.

| Object | Bytes | SHA-256 |
| --- | ---: | --- |
| Original `.deb` | 56876 | `70aca4fa8daeacb677ec00e8063eb586f08ae3d94b1f11e684370b5524c43431` |
| Plain `usr/bin/bwrap` member, mode `0755` | 80248 | `573236e5328ac2ebb08f59ae3a9805b4f8d12bdef14be8af4450d5463294985f` |

The actual archive uses `control.tar.xz` and `data.tar.xz`, with ordinary GNU tar
headers. The selected member was also compared with local `/usr/bin/bwrap` and
matched byte-for-byte. That checks a concrete package-member-to-local-byte
relationship. This original launch-host observation performed no package-index
signature authentication and executed no package program or launcher. The
[subsequent distribution check](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LAUNCHER_DISTRIBUTION_v0.md)
addresses that publication-authentication relationship separately. This result does not select that
launcher for an owner-authorized runtime attempt or qualify the local host.

## Every consumer's selected native relationships

The inventory has exactly one launcher and one designated loader, and at most
64 native objects. Each file is bounded to 16 MiB, with a 128 MiB total. Relative
preservation paths are unique, normalization-free and have no ancestor
collisions. Declared absolute host paths are unique and normalization-free.
The directory reader requires the exact
roster and rejects symbolic links, hard-link aliases and changed file/directory
identities; it does not discover providers in ambient host directories.

The existing bounded [ELF reader](../../tools/required_gate_idempotence_elf_v0.py)
parses every selected object without `ldd` or loading. Every `PT_INTERP` and
`DT_NEEDED` occurrence must have exactly one selected provider for its own
consumer. Missing, duplicate, extra, wrong or ambiguous provider edges reject.
All selected nodes must be reachable from the launcher; legitimate graph cycles
are retained. The designated loader must have the supported ET_DYN shape and no
interpreter of its own. RPATH and RUNPATH reject in this finite profile.

These checks establish complete coverage of the selected static relationships.
Declared host paths remain selections. Actual loader resolution, loaded-object
identity, host cache/configuration effects and dynamic loading require the
subsequent observed attempt. Copying a dynamic launcher into a sealed memfd does
not seal or authenticate its ambient loader and dependencies.

## Passive host observation and interpretation

`observe-host` captures one bounded snapshot. Its random `observation_id`
distinguishes the record; it is not a freshness challenge, trusted timestamp,
host attestation or proof of a later attempt's environment.

The observer records Linux identity fields, current real/effective UID and GID,
soft/hard descriptor limits, memfd API availability, a current descriptor count,
and these fixed file sources only:

```text
/proc/self/status
/proc/sys/user/max_user_namespaces
/proc/sys/kernel/unprivileged_userns_clone
/proc/sys/kernel/apparmor_restrict_unprivileged_userns
/proc/sys/vm/memfd_noexec
/etc/ld.so.preload
```

It separately reads namespace-link identities for `user`, `mnt`, `ipc`, `pid`,
`net`, `uts` and `cgroup`. Namespace identities describe the observer's current
context; they do not demonstrate the creation of a new namespace.

Each file read retains an explicit `present`, `absent`, `unreadable`, `oversize`
or `unsafe` outcome. At most 16384 raw bytes per file are retained; oversized
inputs remain bounded prefixes. The checker requires the exact source roster,
canonical encoding and byte binding before deriving the finite results.

| Passive result | Interpretation |
| --- | --- |
| Linux/x86-64 and memfd API | Check the selected platform and API's presence; no syscall operation is attempted. |
| Descriptor headroom | Compare the observed soft limit with current open descriptors plus the reconstructed view's file count plus 16. Missing descriptor observations remain unknown. |
| Positive user-namespace limit | Establish that the observed limit is nonzero; current usage, ancestor limits and actual namespace creation remain unobserved. Zero blocks this prerequisite. |
| Unprivileged-userns switch | Zero blocks the observed non-root, zero-capability context; other privilege cases remain unresolved. Missing or unknown values do not pass. |
| AppArmor userns restriction | Zero satisfies this finite switch check; an enabled restriction requires separately observed profile permission and remains unknown. |
| Memfd execution default | Zero matches the existing default flags; values one or two block the current primitive, which omits explicit `MFD_EXEC`. |
| Loader preload file | The finite profile requires absent or empty configuration. Nonempty content blocks; unreadable, unsafe or oversized input remains unknown. |
| Current NNP, seccomp and capabilities | Retain observer context only. Seccomp mode 2 does not identify the intended filter. |

The [kernel's memfd rules](https://docs.kernel.org/6.14/userspace-api/mfd_noexec.html),
[namespace limits](https://www.kernel.org/doc/html/latest/admin-guide/sysctl/user.html),
[Debian userns capability check](https://sources.debian.org/patches/linux/5.10.223-1/debian/add-sysctl-to-disallow-unprivileged-CLONE_NEWUSER-by-default.patch/)
and [Ubuntu's AppArmor userns restrictions](https://documentation.ubuntu.com/release-notes/24.04/)
explain why these passive prerequisites have distinct meanings. The observer
does not modify any sysctl, policy, namespace, capability or resource limit.

An accepted plan may contain `blocked` or `unknown` prerequisites. Acceptance
means that the record and its interpretation reconstruct consistently. It does
not aggregate those observations into an execution-ready or qualified result.

## Commands

Capture a new passive snapshot, preserving the parent directory beforehand:

```bash
python3 -I -B tools/required_gate_idempotence_launch_host_v0.py observe-host \
  --output /absolute/review/new-host-observation.json
```

The owner independently selects and retains the inputs and their digests.
Replace the uppercase hash placeholders below with those retained values; paths
must identify the selected originals. The native directory contains only the
declared native inventory. The entry-build directory contains the original
fifteen-file `evidence/` roster from an accepted build observation. The original
GitHub artifact ZIPs remain unchanged.

```bash
launch_host_inputs=(
  --runtime-selection /absolute/review/runtime-selection.json
  --runtime-selection-sha256 RUNTIME_SELECTION_SHA256
  --operator-selection /absolute/review/operator-selection.json
  --operator-selection-sha256 OPERATOR_SELECTION_SHA256
  --capsule /absolute/review/runtime-capsule.zip
  --capsule-sha256 CAPSULE_SHA256
  --bootstrap-selection /absolute/review/bootstrap-selection.json
  --bootstrap-selection-sha256 BOOTSTRAP_SELECTION_SHA256
  --bootstrap-plan /absolute/review/bootstrap-plan.json
  --bootstrap-plan-sha256 BOOTSTRAP_PLAN_SHA256
  --containment-selection /absolute/review/containment-selection.json
  --containment-selection-sha256 CONTAINMENT_SELECTION_SHA256
  --containment-request /absolute/review/containment-request.json
  --containment-request-sha256 CONTAINMENT_REQUEST_SHA256
  --launch-host-selection /absolute/review/launch-host-selection.json
  --launch-host-selection-sha256 LAUNCH_HOST_SELECTION_SHA256
  --launcher /absolute/selected-host/bwrap
  --entry-shim /absolute/review/selected-entry
  --entry-build-directory /absolute/review/entry-build/evidence
  --launcher-package /absolute/review/selected-bubblewrap.deb
  --native-root /absolute/review/selected-launcher-native-files
  --host-observation /absolute/review/new-host-observation.json
  --repository-root /absolute/selected-source-checkout
)

python3 -I -B tools/required_gate_idempotence_launch_host_v0.py prepare \
  "${launch_host_inputs[@]}" --output /absolute/review/new-launch-host-plan.json

python3 -I -B tools/required_gate_idempotence_launch_host_v0.py check \
  "${launch_host_inputs[@]}" \
  --plan /absolute/review/new-launch-host-plan.json --plan-sha256 PLAN_SHA256 \
  --output /absolute/review/new-launch-host-verification.json
```

`--repository-root` is required by selected source inputs and may be omitted for
authored example inputs where the underlying contract permits it. Preparation
and checking use the same complete original inputs. Existing output paths are
not overwritten. Exit zero reports a completed snapshot or accepted record,
with its narrow meaning above. There is no run, install or dispatch command.

## Validation and remaining obligations

Regressions cover the exact entry/package/native relationships, per-consumer
coverage, rehashed substitutions, duplicate or undeclared paths and providers,
bounded archive interpretation, explicit blocked/unknown host states, authority
flag changes, directory safety and command-line output preservation. The new
code does not require a host bubblewrap installation or successful namespace
creation. Actual regression outcomes are retained with the delivery validation.

The original entry-build checker still reports
`github_build_provenance_verified=false`. The separately preserved successful
hosted signature verification remains its own event; this plan neither reruns
that verification nor rewrites the earlier report.

The fixed remaining obligations are authenticated launcher/package/build origin;
same-attempt host and actual mapped-native identity; strict namespaces and the
read-only view; the intended filter and denied operations; descriptor closure
and limits; bounded output and failed-attempt preservation; reviewed
selected-bootstrap integration; and separate execution authorization.

Accordingly, `launcher_origin_authenticated`, `host_observation_authenticated`,
`host_launcher_runtime_verified`, `host_environment_qualified`,
`containment_enforced`, `execution_ready` and `execution_authorized` stay false.
The launcher, preserved entry, selected runtime, operator and model are not
executed by this path. `metric_pass=null`, `actual_reference_claimed=false` and
`authority_effect=none` remain unchanged.

The next operational work is a separately reviewed bounded host example and
independently bound runtime/loader observations, followed by selected-bootstrap
integration. B3, B4 and B5 remain subsequent work. The broader plan's steps 6 and
7 remain separate obligations. Preserve both original `43854478248/1` ZIPs, the
original `43514702328/1` artifact, Q2 FAIL 49/50 plus 1 UNKNOWN, all twelve
unsupported gates and historical Q3 scope; keep
[#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879) open.

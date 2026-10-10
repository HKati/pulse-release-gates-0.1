# QRH003 source-binding contract — v0.1.3

## Threat and supported boundary

The v0.1.2 verifier hashed Python source files after import. A writer able to
place a `.pyc` cache in the study directory could supply different executed
code while every anchored `.py` digest remained unchanged. A local signed
TEST reproduction changed `BLOCK` into TEST-only `ALLOW`. This was not a
native proof run or evidence of an earlier production compromise.

The supported entry point is a separately trusted, directly executed
`source_bound.py` file, with a trusted CPython installation and a caller-approved
`SOURCE_MANIFEST.json` SHA-256. The launcher and host are the bootstrap trust
root. A manifest read from an untrusted checkout and hashed without independent
approval cannot authenticate itself. Protect the launcher installation and
approve its version before execution; its later self-inventory is not an
independent proof of its own origin.

Use Linux x86_64 and the locked CPython 3.12 dependency environment in the
[README](README.md). The launcher requires `python -I`. Python, its standard
library, installed site packages, dynamic loader, OS, hardware and external
anchor custody remain trusted. This is not OS isolation or runtime closure.

## Input and loading contract

```text
python -I /trusted/source_bound.py \
  --root /path/to/study \
  --source-manifest-sha256 APPROVED_MANIFEST_DIGEST \
  COMMAND [command arguments]
```

`--source-manifest` may select an external manifest; otherwise it is read from
the study root. `COMMAND` is one of `prepare`, `acquire`, `source_closure`,
`preflight`, `collect`, `verify`, `authority`, `transition_report`, `run_tests`.
For decisions and replay, pass `authority decide ...` or `authority replay ...`.
The remaining arguments are those of the existing command's `--help`.

Before any study module executes, the launcher:

1. Verifies the exact manifest bytes against the caller-approved digest.
2. Validates paths, duplicate entries, sizes, hashes, inventory totals and the
   complete mandatory tool set. Reads reject symlinks and special files.
3. Captures and verifies every declared file. Limits are 256 entries,
   4 MiB per file and 32 MiB total declared content.
4. Compiles the exact verified Python bytes before executing any study code.
5. Installs a bounded import loader for the study tools and declared tests.
   Neither `.pyc` files nor on-disk `__init__.py` files provide study code.
   Unknown names in the study namespaces raise an error without fallback.

Existing tool aliases (`audit` and `tools.audit`, for example) refer to one
verified module object. Test module names preserve the published unittest IDs.
The test runner discovers only authenticated test sources; an empty selection
is an error. It does not add the checkout to the Python import search path.

The manifest is a versioned source inventory, not a release authority anchor.
The existing evidence admission and gate checker retain their roles.

## Anchor and bootstrap contract

`prepare` executes from the approved source snapshot, uses its reference bytes
and writes a fresh `source_binding` record to the capture policy, profile and
external anchor. This record contains the manifest digest, launcher digest and
`COMPILED_FROM_VERIFIED_SOURCE_BYTES` mode. Its verifier inventory includes the
launcher and all declared tool and test source digests.

Both collector startup and verifier admission require that the external anchor
matches this loaded source binding. They also check its source digests against
the in-memory snapshot and the current files. If a pathname changes after
capture, it cannot replace an already captured code object; subsequent anchor
checks reject source drift. This does not seal the entire filesystem.

Old anchors are refused by the current verifier. Create a new anchor for new
work; never alter a historical anchor to make it pass. Historical pilot replay
uses the unchanged original verifier and archive described in the README.

## Collector subprocess contract

The collector's preflight and test subprocesses execute the same captured
launcher bytes from a Linux memfd sealed against writing, growth and shrinkage.
The captured manifest is passed in a second sealed descriptor. Both descriptors
are explicitly inherited and closed in the parent after the call.

Each child uses `python -I`, verifies the sealed manifest and independently
captures/verifies the source inventory. It does not fall back to a mutable
launcher pathname or ordinary study imports. A missing seal, stale source or
startup error cannot produce a passing observation. Process records retain the
source-binding contract, exit code, timeout/error and stdout/stderr digests.
Descriptor numbers in recorded argv are ephemeral transport details, not a
standalone replay command or native execution proof.

The existing PULSE primitives keep their original pinned bytes and execution
path: admission checks their source digests and executes fresh temporary
scripts in separate isolated Python processes. Their policy and gate meanings
are unchanged.

## Failure and authority contract

A launcher input or binding failure exits nonzero with a `REJECTED` diagnostic
and `authority_granted: false`, before the requested study operation starts.
It cannot issue a certificate. A verifier/collector anchor mismatch retains
the existing fail-closed error path. Completed native-tool preflight may still
exit with a recorded `BLOCK`; completing source binding does not override it.

Current direct `tools/*.py` CLIs reject execution before study imports. Calling
internal Python functions from an arbitrary preloaded interpreter is not a
supported external entry point. Integrators must launch a fresh protected
process. This contract does not claim to protect a Python process in which an
attacker already controls the interpreter or can replace the trusted launcher.

No new production gate, native capture adapter, proof qualification, semantic
review or mathematical acceptance is added. A current PRODUCTION anchor can
be prepared, but missing native proof evidence still prevents a production
certificate. A TEST certificate remains TEST-only. Historical `BLOCK/MATCH`
and the observer's `authority_effect: NONE` remain unchanged.

## Regression evidence

The suite preserves the original 185 distinct cases and adds 35 source-binding
cases: 220 total, including 206 required collector-boundary cases and 14
observer regressions. Test data, payloads and generated signing keys are local
synthetic fixtures. No private key or generated decision is committed.

The new cases cover three poisoned-cache formats; entrypoint, common, runner
and test caches; exact decision bytes; `BLOCK/MATCH`; observer authority;
anchor, source and manifest mismatch; symlinks and FIFOs; source replacement;
direct-script rejection; bootstrap in both domains; and actual collector
preflight/test subprocesses using sealed descriptors. They also verify that
failure cannot silently fall back to a mutable launcher.

The isolated suite still needs its dedicated runner. Repository-wide CI is not
evidence that these cases ran unless the job explicitly invokes this command.

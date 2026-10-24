# PD-SM-01-E0 local implementation — CPython 3.13.5 profile

This is a bounded experimental harness, not a repository patch or release gate.
The original preparation and its expectations are retained byte-for-byte. See
`../ENVIRONMENT_PROFILE_REVISION.json` for the owner-approved environment-only
revision from proposed CPython 3.11.16 to local CPython 3.13.5. No cross-version
compatibility result is implied. Source snapshot: `102145d1f1c321811c52d9d20f92cc7289127b2b`.

## Files and separation

- `case_expectations.json`: unchanged frozen preparation expectations. Its old
  environment/NOT_RUN fields are historical preparation metadata, not the new result.
- `independent_reference.py`: a data-only, scenario-name-independent evaluator.
  It does not import or execute producer/checker helpers. It reconstructs this
  exact fixture from admitted raw sources, and checks joint IDs, aliases, summaries,
  context, source selectors and current proof applicability. Missing evidence is
  not reconstructed from a familiar output or a cached certificate.
- `run_cases.py`: source/environment checks, source-reference freeze, original
  producer/checker subprocesses, audited mutations, separate evidence views,
  observations and comparisons. No network fetches or repository operations.
- `test_harness.py`: six G controls and twelve additional regression methods.

## Offline replay

Unpack the complete delivery. Keep `source/`, `preparation/`, the environment
revision and this directory together. With CPython 3.13.5 on Linux, run:

```sh
python3.13 -I -B pd_sm_01_e0/run_cases.py --bundle-root . --output /absolute/path/to/new-result
```

The output directory must not exist. Do not overwrite the supplied result.
No packages are installed. The harness uses Python's standard library and the
host `libseccomp.so.2` for an inherited socket-syscall deny filter. Absence or
failure of that OS library is an explicit isolation/environment failure, not
permission to execute without the declared restriction. This OS dependency is
part of this narrow Linux execution profile, not a Paradoxon requirement.

The interpreter version is checked; executable digest, OS/kernel information,
source bytes, code and expectations are recorded anew. A different interpreter
build at the same version is a new execution identity, not byte-identical replay.

## Cases and observations

Eight scenarios refine the original five variants without changing their
expected meanings. Three existing checker processes and one independent
assessment are recorded per scenario. E10 permutes the mathematical enumeration
while leaving actual carrier bytes unchanged. E11/E12 change serialization order.
E13 restores it without rerunning producers. E20 changes one destination only.
E30 withholds admitted metric-source evidence in a fresh assessment. E40 selects
an existing CPU relation and requires its own proof leaves.

Expected negative return codes, log fragments and structural witnesses are
checked together. A signal, traceback, timeout or missing output is not a valid
negative witness. `MATCH` means the observed experimental behavior matches the
frozen expectation, including intended violations and uncertainty. It does not
mean every candidate preserves the relation or is authorized.

The reference independently reconstructs the full relation-bearing contents of
this nine-Atom/four-edge fixture, excluding display titles and incidental paths.
It uses the same documented specification, not an independent physical source;
common specification errors and organizational dependence remain limitations.

## Limits and retention

Original source files are copied into `source/` and verified by their pinned Git
blob identities before execution and again afterward. No source code is patched.
Each child uses `-I -B`, a clean explicit environment, closed inherited descriptors,
a new process group and bounded resources. Network socket syscalls are blocked;
filesystem confinement is **not** established. This is not a PULSEbox sandbox.

Child limits: 30 s wall time (the timeout control uses less), 30 s CPU, 2 GiB address
space, 2 MiB per output file/stream, and monitored 64 MiB aggregate experiment output.
The aggregate bound is polling-based, not an atomic disk quota. All stdout/stderr,
mutations, reference inputs, results and failures are retained. No artifact is
published, no CI is dispatched, and `authority_effect` remains `none`.

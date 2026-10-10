# QRH003 audit demonstrator — v0.1.3

This study implements source observation, evidence admission, offline release
decisions and replay for the pinned OpenAI Math 003 reference case. Its scope
is four configurations and five theorem exports, defined in
[configurations.json](reference/configurations.json) and
[claim_map.json](reference/claim_map.json).

**Current boundary:** the native proof capture adapter is
`NOT_IMPLEMENTED`. The latest historical source pilot produced `BLOCK`; its
decision replay produced `MATCH`. No production QRH certificate has been
established. A matching replay confirms reproduction of that decision; it does
not turn the decision into `ALLOW` or establish a mathematical proof.

## Pinned identities

| Component | Commit |
| --- | --- |
| [OpenAI Math subject](https://github.com/openai/math/tree/adc7f1241b42e322a6451854ab7e4b4c146bf78a) | `adc7f1241b42e322a6451854ab7e4b4c146bf78a` |
| [PULSE primitives and integration baseline](https://github.com/HKati/pulse-release-gates-0.1/tree/288bb9a45764d2a30f72fdf4c417e9dd5b3087c5) | `288bb9a45764d2a30f72fdf4c417e9dd5b3087c5` |

The nested [PULSE runtime](reference/pulse_runtime/NOTICE.md) retains the exact
pinned policy parser, gate checker and base status schema. These copies are
called in separate processes. Replacing them with a moving repository-root
version changes the verification basis.

## Contents and entry points

| Location | Role |
| --- | --- |
| `source_bound.py` | Required source-bound launcher for every current CLI |
| `tools/prepare.py` | Create a fresh profile, local operator key and external anchor |
| `tools/acquire.py`, `tools/source_closure.py` | Observe pinned source identities and static Lean imports |
| `tools/preflight.py`, `tools/collect.py` | Record host/toolchain preflight and fresh source observations |
| `tools/verify.py`, `tools/audit.py` | Admit evidence and derive conservative gate status |
| `tools/authority.py` | Decide, conditionally emit a scoped certificate, and replay a recorded decision |
| `tools/transition_report.py` | Observe the completed decision path without changing authority |
| `tools/run_tests.py`, `tests/` | Execute the isolated unittest suite and retain per-case outcomes |
| `schemas/` | Admitted status and admission-failure schemas |
| `reference/` | Configuration, claim bindings, source pins, pinned primitives and license records |

The distribution contains 19 study-owned Python files and two pinned PULSE
Python files. The [source manifest](SOURCE_MANIFEST.json) lists the exact
repository files and hashes. Historical runs, diagnostic programs, generated
reports and dependency wheels are supplied in a separate complete archive;
its identity is recorded in [EVIDENCE_REFERENCE.json](EVIDENCE_REFERENCE.json).

### v0.1.1 observer correction

The post-decision observer now requires actual successful materialization,
policy parsing and gate-checker execution before reporting a complete offline
primitive path. For example, an admitted bundle and a matching decision replay
can coexist with a missing runtime. That case is reported as
`INCOMPLETE_OFFLINE_PRIMITIVE_EXECUTION`, while the independent replay axis
can still be verified. Thirteen regression tests cover the correction. The
observer does not grant release authority.

### v0.1.2 review corrections

The repository revision addresses three findings from PR #2907:

- The transition observer describes fresh byte-equal recomputation. It does
  not assert a separate verifier process when no process provenance exists.
- Tool preflight copies a bounded executable image into a Linux memfd, seals
  it against writes and resizing, hashes the sealed bytes and executes that
  same inherited descriptor. The strict Landrun probe uses the same binding
  procedure. Missing sealing support, a digest mismatch or execution failure
  blocks the probe; the original mutable pathname is never an execution fallback.
- Bundle admission requires exactly the signed artifact files plus the root
  `manifest.json` and detached `manifest.signature.json`. Directories must be
  parents of declared paths. Extra files, unrelated empty directories, links
  and special filesystem objects are rejected. Evaluation consumes the admitted
  bytes held in memory; the check does not lock a directory against later writers.

Preflight's memfd execution binds the executable image only. Its interpreter,
dynamic loader and shared libraries remain part of the host/runtime boundary.
Self-locating executables or binaries that rely on `$ORIGIN` may fail from a
memfd; that failure remains a blocking result. No native toolchain or proof
capture qualification is claimed by the local fixture suite.

### v0.1.3 Python source binding

All current commands run through [source_bound.py](source_bound.py) in a fresh
`python -I` process, with an independently approved source-manifest digest.
It verifies the declared source/reference inventory before importing study
code, then compiles and loads those exact source bytes. Existing `.pyc`
files, unlisted package initializers and unlisted test files cannot replace
that code. A source file hash is never treated as authentication of a cache.

The collector starts preflight and test children using sealed launcher and
manifest descriptors; each child independently checks its source inventory.
Preparation records this binding in new anchors, and admission checks both
the loaded source snapshot and current source files against the anchor.
Direct legacy scripts reject execution before importing study code.

The [source-binding contract](SOURCE_BINDING.md) defines the trusted entry
point, bootstrap, subprocess and failure boundaries. It does not establish
native proof execution or add release authority. Historical replay keeps its
original verifier; old anchors cannot be silently upgraded to this revision.

## Run the source suite

Use Linux x86_64, CPython 3.12, glibc 2.34 or newer, and Git.
Executable preflight requires Linux memfd sealing and accessible `/proc/self/fd`. The lock selects
specific binary dependency artifacts for that environment. The unit tests do
not require Lean, upstream proof execution or a native QRH build. Network
access is required only for the installation command below; after installation
the suite uses local fixtures and subprocesses.

Start from this study directory in a fresh shell. The temporary working
directory keeps the virtual environment, reports and any later local keys
outside the checkout.

```bash
set -eu
QRH_ROOT="$PWD"
QRH_WORK="$(mktemp -d /tmp/qrh003-work.XXXXXXXX)"
export QRH_ROOT QRH_WORK
# Obtain this digest from the independently reviewed release/PR record.
: "${QRH_MANIFEST_SHA256:?set the approved SOURCE_MANIFEST.json SHA-256}"
export QRH_MANIFEST_SHA256
git --version
python3.12 -m venv "$QRH_WORK/venv"
"$QRH_WORK/venv/bin/python" -m pip install \
  --only-binary=:all: --require-hashes \
  -r "$QRH_ROOT/requirements-linux-x86_64-py312.lock"
"$QRH_WORK/venv/bin/python" -I "$QRH_ROOT/source_bound.py" \
  --root "$QRH_ROOT" --source-manifest-sha256 "$QRH_MANIFEST_SHA256" \
  run_tests \
  --output "$QRH_WORK/tests.json"
```

Expected for this version: **220 distinct tests, all `PASS`, zero skipped**.
Check the structured result, since unittest can return success when tests are
skipped:

```bash
"$QRH_WORK/venv/bin/python" - <<'PY'
import json
import os
from pathlib import Path
r = json.loads((Path(os.environ["QRH_WORK"]) / "tests.json").read_text())
cases = r["tests"]
assert r["return_code"] == 0 and r["timed_out"] is False
assert r["tests_run"] == len(cases) == 220
assert len({case["id"] for case in cases}) == 220
assert all(case["outcome"] == "PASS" for case in cases)
print("220 distinct PASS; zero skipped")
PY
```

For offline dependency installation, use the wheel directory inside the
separately obtained, hash-verified complete distribution. Set
`QRH_WHEELS` to its extracted
`studies/openai_math_003_qrh_v0/vendor/wheels` directory, then replace the
networked installation command with:

```bash
"$QRH_WORK/venv/bin/python" -m pip install \
  --no-index --find-links "$QRH_WHEELS" \
  --only-binary=:all: --require-hashes \
  -r "$QRH_ROOT/requirements-linux-x86_64-py312.lock"
```

The source checkout itself contains no wheel directory.

### CI boundary

At the pinned integration baseline, repository-root `pytest.ini` discovers
`tests/`, and Tools smoke tests use `ci/tools-tests.list` and
`ci/pytest-tests.list`. This study is not in those manifests. A successful
repository CI run therefore does not establish that the 220 QRH tests ran.
Invoke the dedicated runner above in its own process. An eventual CI job
must use the compatible dependency environment and check recorded outcomes.
Do not import the study suite into an existing repository-wide pytest process:
both contexts contain modules called `tools` and `common`.

## Prepare a new local study run

Preparation creates a new configuration and local operator key. The example
explicitly uses the `TEST` domain. It exercises configuration creation and
does not acquire sources or execute native proofs:

```bash
install -d -m 700 "$QRH_WORK/private"
"$QRH_WORK/venv/bin/python" -I "$QRH_ROOT/source_bound.py" \
  --root "$QRH_ROOT" --source-manifest-sha256 "$QRH_MANIFEST_SHA256" \
  prepare \
  --output "$QRH_WORK/config" \
  --private-key "$QRH_WORK/private/collector.ed25519" \
  --trust-domain TEST \
  --required-tests "$QRH_ROOT/reference/required_boundary_tests.json"
```

Use a fresh output namespace each time. Keep the key outside both the
configuration/evidence bundle and the repository. A locally generated key
does not establish independent institutional identity or external trust.

[required_boundary_tests.json](reference/required_boundary_tests.json)
declares 206 collector-boundary test IDs. This preserves all 145
original IDs and the v0.1.2 regressions, adding 35 source-binding cases. The
complete suite also contains 14 observer regressions, for 220 tests.
New configurations bind this revised declared set through a fresh anchor.

Subsequent acquisition and collection need separately supplied pinned source,
dependency and toolchain inputs. CLI options are available through `source_bound.py --root ROOT
--source-manifest-sha256 APPROVED_DIGEST COMMAND --help`. Native A/B builds, formal comparison and axiom audit,
compiler-resolved source/runtime closure, and the required isolation evidence
remain unestablished. Independent semantic/Lean/domain review intake is also
not implemented.

Always create a new anchor for new work. Preparation uses the authenticated snapshot of 19 study Python files
and the declared reference JSON inventory, including its launcher binding.
The curated reference inventory is smaller than the complete distribution's
inventory; a previous anchor must not be silently reused or edited to accept
a different file set.

## Historical evidence and replay

The separately distributed archive is:

- Filename: `PULSEMECH_QRH003_IMPLEMENTATION_v0_1_1.zip`
- Size: `23453781` bytes
- SHA-256: `ce5737b01ae3b400bac96c092afb982a0af74a812692714e4c7cd094b61afbdc`
- Latest source pilot: `qrh003-pilot-002-20261007` (v0.1)
- Recorded outcome: `BLOCK`; replay: `MATCH`
- Recorded decision SHA-256: `1383ee891397b686f4c12f96137a8e58ae1f8ed4b89c9232baac0b637e512276`

No public download location is recorded for that archive. Obtain the exact
identified distribution separately and verify its hash. Its diagnostics
remain diagnostic or TEST evidence; packaging them grants no proof authority.

Historical `pilot_002` replay uses the archive's preserved
`runs/pilot_002/verifier_snapshot/tools/authority.py`, its original anchor,
bundle and decision, plus the pinned PULSE runtime. Follow the archive's
`REPLAY_PILOT.md`. The current root verifier is not a substitute for the original
anchored verifier. The source-only checkout lacks the historical run payloads
and does not claim a fresh native proof run.

## Provenance

The initial source subset copied 35 selected files byte-for-byte from the
complete v0.1.1 distribution. Repository revision v0.1.2 intentionally
changes the reviewed tools, regressions, preparation revision and declared
test inventory. The v0.1.3 source-binding correction is recorded separately.
`EVIDENCE_REFERENCE.json` retains the v0.1.2 provenance record and lists the
v0.1.3 changes against that source baseline; `SOURCE_MANIFEST.json`
covers the complete current study. The historical archive remains unchanged.

See the [PULSE runtime notice](reference/pulse_runtime/NOTICE.md),
[license records](reference/licenses/license_source_records.json) and
[license texts](reference/licenses/). The source and claim records preserve
their exact upstream commits and byte digests. Recorded historical source
observations are not silently promoted to fresh collection evidence.

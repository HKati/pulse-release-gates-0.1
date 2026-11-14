# Selected idempotence runtime preservation v0

## Status and supported use

**Implemented: preservation, offline inspection and byte-exact restoration of
an independently selected runtime file set. B2 remains incomplete.** This
continuation follows the
[bounded acquisition primitives](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_ACQUISITION_v0.md)
and their closed observed-launch boundary. It adds a separate runtime capsule;
the existing observation carrier, checker and acquisition commands retain
their existing formats and behavior.

The implementation checks a closed file inventory and explicit static ELF
dependency bindings. It does not run the selected interpreter, import preserved
Python modules, use `ldd`, install a package, qualify a host or launch the selected
sanitizer. The shipped regressions use authored ELF images and inert Python
fixtures. This change supplies no selected real runtime capsule or observed
reference result.

Acceptance establishes that the selected bytes can be recovered and that every
declared native object's static interpreter/dependency references have matching
selected bindings. It does not establish the loader's actual search result,
symbol or ABI compatibility, dynamic imports, `dlopen` coverage, a usable Python
installation or complete runtime closure. The public acquisition command still
rejects with `observed_acquisition_not_ready`.

| Surface | Responsibility |
| --- | --- |
| [Runtime preservation tool](../../tools/required_gate_idempotence_runtime_v0.py) | Validate selections, read a closed staging tree, build/check the capsule and restore exact bytes. |
| [Static ELF parser](../../tools/required_gate_idempotence_elf_v0.py) | Inspect bounded ELF64 little-endian x86-64 objects without loading them. |
| [Runtime schema](../../schemas/required_gate_idempotence_runtime_v0.schema.json) | Define closed selection and member-inventory records. The installed tool pins the schema bytes. |
| [Runtime regressions](../../tests/test_required_gate_idempotence_runtime_v0.py) | Exercise synthetic positive, substitution, archive, dependency, filesystem, failure-preservation and CLI paths. |

## Two independent selections

The caller retains two exact external JSON documents and their expected SHA-256
values before building or checking a capsule:

- The existing operator selection, using the unchanged observation selection
  schema, identifies the original protocol, seven required acquisition sources and
  declared CPython 3.11.16 / Unicode 14.0.0 / Linux x86-64 environment.
- The new runtime selection uses
  `record_type=required_gate_idempotence_runtime_selection_v0` and
  `profile=selected_cpython_runtime_capsule_v0`. It binds that operator selection's
  exact digest, repository, source commit and declared environment, then lists
  every runtime file and every native dependency edge.

An external runtime selection with `record_status=selected` requires an operator
selection with `record_status=observed` and a local repository. Every selected
repository file is compared with its regular-file Git blob using the existing
offline, transport-disabled lookup. The four original operator sources retain
their original revision and pins. The three required acquisition implementation
sources and runtime-only repository sources use the selected implementation
commit. Additional operator-selected implementation dependencies retain their
explicitly selected revisions. A commit identifier must actually contain the
selected files. The synthetic pair uses `example` for both statuses and does
not claim Git-bound observed selection.

The environment is a declaration carried forward from the operator selection.
The interpreter file must match its selected executable digest, but reading an
ELF file does not authenticate the declared Python version. Reports distinguish
`declared_environment` from `host_environment_qualified=false`.

## Closed staging tree and required files

The staging root contains exactly four named trees: `python`, `native`,
`repository` and `licenses`. Every file descriptor contains its path, tree,
role, format, SHA-256, byte count and nullable repository source path/revision.
Paths are case-sensitive relative names with no traversal, empty components or
aliases. There may be at most 4,096 selected files. Empty directories and
unselected files are rejected; directory membership is derived from selected
file paths.

The implementation requires the selected interpreter and loader; the original
selected operator and acquisition sources; and the known observation/checker,
compute analysis and schema files listed by `VERIFIER_PATHS`. These known
verification sources must match the installed implementation. This check is
deliberately independent of the preserved copies: the capsule does not provide
the trusted checker used to admit itself.

The standard-library baseline contains the encoding bootstrap, import machinery,
JSON and ctypes entry points, plus `argparse.py`, `hashlib.py` and `pathlib.py`.
The site-package baseline contains the entry points for PyYAML, jsonschema,
referencing, rpds, attrs, jsonschema-specifications and typing-extensions.
Each required distribution also needs its preserved `METADATA` and `RECORD`.
Metadata must provide one valid name and version, and normalized names must be
unique. Reports label versions as declared metadata. `RECORD` is preserved as
selected bytes; its presence does not validate an installation or prove that
all imports are covered. Additional selected modules, native extensions, data
files and notices are allowed within the closed roster.

At least one nonempty notice file is required in `licenses`. This preserves
selected notices without claiming a redistribution-rights review. Startup
customization files (`.pth`, `sitecustomize.py`, `usercustomize.py`), bytecode
files and `__pycache__` directories are rejected by this profile.

Capture reads through directory descriptors with no symlink traversal. Regular
files must have a single hard link. Special files, symlinks, extra/missing files,
file/directory collisions and files or directories changed during their read
are rejected. The staged payload must match the independently selected digest
and size for every file. This is an exact finite inventory, not an inference
that an arbitrary Python program's dependency closure is complete.

## Static native dependency bindings

Every selected ELF object is parsed, including extensions inside the standard
library or site packages. An ELF magic header cannot be hidden under another
declared format. The parser supports only ELF64 little-endian x86-64 `ET_EXEC`
and `ET_DYN`, with bounded headers, segments, strings and dynamic entries.
Malformed, ambiguous, out-of-bounds and unsupported loading structures reject.

For every object, each `PT_INTERP` and each `DT_NEEDED` entry must have exactly
one binding keyed by the full consumer path, edge kind and exact reference
name. A correct binding for one consumer cannot cover another consumer's
dependency. Missing, duplicate and extra edges reject.

Every interpreter edge selects the designated loader, whose file basename and
optional `DT_SONAME` must match the interpreter reference's basename. This rule
also covers a shared object that itself has `PT_INTERP`. Every needed-library
edge selects an `ET_DYN` object with the exact `DT_SONAME`; duplicate providers
for one SONAME are rejected. Audit, filter, auxiliary and unsupported alternate
loading tags are rejected.

`RPATH` and `RUNPATH` remain reported metadata. The parser does not interpret
their search order, expand loader tokens, inspect a host loader cache, resolve
symbol versions or execute a load. Explicit selected bindings therefore remain
separate from `loader_resolution_verified`, which is always false. The primary
[ELF program-loading specification](https://gabi.xinuos.com/elf/07-pheader.html)
and [dynamic-linking specification](https://gabi.xinuos.com/elf/09-dynamic.html)
describe these underlying metadata fields.

## Capsule and restoration

The separate ZIP contains exact runtime/operator selection copies, every file
under `payload/`, and `capture/member_inventory.json`. The inventory hashes every
other member and excludes itself. The capsule's expected hash stays outside the
capsule, avoiding a self-digest cycle. A checker must receive both external
selections and all three expected hashes; it does not adopt selection copies
found inside the archive.

The checker recomputes every inventory and selected-file binding. It also
checks physical ZIP coverage, so a valid central directory cannot hide prefixes,
trailers, unindexed local members or inconsistent headers. Duplicate names,
comments, extra fields, directory/special-file entries, encryption and unsupported
compression reject. Stored and deflated members are supported; corrupt compressed
data yields a stable rejection report.

| Bound | Maximum |
| --- | --- |
| Selection or inventory document | 4 MiB |
| One selected payload file | 128 MiB |
| Total uncompressed capsule contents, including control documents | 256 MiB |
| Encoded ZIP | 384 MiB |
| Payload files / total ZIP members | 4,096 / 4,099 |

These capsule bounds do not change the existing observation carrier's smaller
limits. A capsule cannot be substituted for an observation carrier.

Restoration verifies the entire capsule before creating a new private directory.
It writes selected payload files with mode 0400, directories with mode 0700, and
selection/completion records with mode 0600. It reopens and rehashes the payload
through the same pinned directory used for writes, then checks that the requested
destination still identifies that directory before publishing `restoration.json`.
An intact directory substituted at the pathname cannot stand in for corrupted
bytes in the directory actually written.

Restoration adds no execute permissions and performs no installation. It does
not make the directory immutable against its owner after verification. A failure
retains the files already produced and, when storage permits, writes
`restoration.incomplete.json` with the completed prefix and failure code. Storage
failure or abrupt process death may leave only that prefix. Existing destinations
reject; there is no overwrite, retry, resume, deletion or launch mode.

## Offline commands

Prepare the independently selected files in a separate staging root. These
commands read and preserve bytes; they do not construct a runtime selection by
trusting an inventory found inside a capsule. All output names below must be new.

```bash
python tools/required_gate_idempotence_runtime_v0.py build \
  --selection /absolute/path/runtime-selection.json \
  --selection-sha256 SELECTED_RUNTIME_SELECTION_SHA256 \
  --operator-selection /absolute/path/operator-selection.json \
  --operator-selection-sha256 SELECTED_OPERATOR_SELECTION_SHA256 \
  --repository-root /absolute/path/repository \
  --source-root /absolute/path/selected-runtime-tree \
  --output /absolute/path/new-runtime-capsule.zip
```

The JSON report includes the resulting capsule hash. Retain the capsule and its
expected hash separately, then check them against the original external selections:

```bash
python tools/required_gate_idempotence_runtime_v0.py check \
  --selection /absolute/path/runtime-selection.json \
  --selection-sha256 SELECTED_RUNTIME_SELECTION_SHA256 \
  --operator-selection /absolute/path/operator-selection.json \
  --operator-selection-sha256 SELECTED_OPERATOR_SELECTION_SHA256 \
  --repository-root /absolute/path/repository \
  --capsule /absolute/path/new-runtime-capsule.zip \
  --capsule-sha256 SELECTED_CAPSULE_SHA256 \
  --output /absolute/path/new-runtime-verification.json
```

Use the same check arguments with `restore` instead of `check`, omit `--output`,
and supply `--output-directory /absolute/path/new-restoration`. The directory
contains `payload/`, the two exact selection copies and `restoration.json` on
success. Commands print a JSON result and exit 0 for their completed bounded
operation, or exit 1 for a rejected operation.

## Validation and remaining work

The new regression module is registered once in the Tools manifest. This
continuation increases live Tools entries from 185 to 186 and updates all count
consumers together; the separate targeted pytest manifest remains at 40.
The previous acquisition document retains its historical 184-to-185 transition.

Positive regressions establish exact recovery and deterministic checking of an
authored runtime capsule. Rejection coverage includes selection and source
substitution, coherent archive/inventory tampering, per-consumer native edge
coverage, wrong provider types/identities, filesystem substitution, partial
restoration, and malformed archive/CLI input. Selected runtime fixtures and
original sanitizer sources remain inert bytes throughout these tests.

The next implementation work is qualification of the restored bootstrap and
its dynamic import/`dlopen` dependencies, enforcement of actual loader paths,
review of host containment, and integration of the observed launch route.
Separate owner authorization is still required before an actual reference.
B3 property calculation and independent reconstruction, B4 admission and B5
actual reference remain subsequent work. No metric verdict is calculated here.

Accepted reports set only the bounded preservation results
`selected_runtime_bytes_recoverable=true` and
`native_dependency_bindings_verified=true`. They retain:

```json
{
  "execution_ready": false,
  "execution_authorized": false,
  "runtime_closure_verified": false,
  "host_environment_qualified": false,
  "python_import_closure_verified": false,
  "loader_resolution_verified": false,
  "restored_runtime_executed": false,
  "observed_acquisition_supported": false,
  "property_semantics_verified": false,
  "metric_pass": null,
  "actual_reference_claimed": false,
  "production_gate_eligible": false,
  "authority_effect": "none"
}
```

The original verification artifact from run `43514702328`, attempt 1 remains
byte-identical. Historical Q2 FAIL (49/50 and 1 UNKNOWN), the twelve unsupported
gate classifications and completed Q3 lineage retain their existing scope.
[#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879) stays open.

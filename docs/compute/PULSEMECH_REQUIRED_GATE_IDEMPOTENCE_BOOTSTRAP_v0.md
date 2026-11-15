# Selected idempotence bootstrap preparation v0

## Status and scope

**Implemented: deterministic bootstrap planning, exact launch-view materialization
and a fixed diagnostic probe. B2 remains incomplete.** This continuation consumes
the [runtime preservation capsule](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_RUNTIME_v0.md)
and supplies a concrete filesystem and finite probe specification for a future
contained runner.

The preparation commands do not launch the selected interpreter or import any
selected runtime or operator source. The probe is preserved as a program for a
future contained runner; `prepare`, `check` and `materialize` never invoke it.
Successful probe output is diagnostic and cannot unlock observed acquisition.

| Surface | Responsibility |
| --- | --- |
| [Preparation tool](../../tools/required_gate_idempotence_bootstrap_v0.py) | Re-verify independent inputs, compile/reconstruct the exact plan, and materialize its selected bytes. |
| [Fixed probe](../../tools/required_gate_idempotence_bootstrap_probe_v0.py) | Implement the finite worker and collector/verifier diagnostics for a future contained runner. |
| [Selection schema](../../schemas/required_gate_idempotence_bootstrap_v0.schema.json) | Define the closed bootstrap selection; the installed tool pins the schema bytes. |
| [Regressions](../../tests/test_required_gate_idempotence_bootstrap_v0.py) | Exercise inert selected-byte fixtures, plan reconstruction, filesystem failures, probe contracts and synthetic diagnostics. |

This change supplies no selected real launch view, contained runtime execution
or actual reference result. Existing runtime, observation and acquisition formats
and implementations retain their exact bytes.

## Independently selected inputs

The caller retains the runtime selection, operator selection and runtime capsule,
together with their expected hashes. A fourth independent document uses
`record_type=required_gate_idempotence_bootstrap_selection_v0` and
`profile=restored_bootstrap_plan_v0`. It binds the three earlier input hashes,
the exact installed probe path/digest/size, the runtime's `example` or `selected`
status, explicit builtin/frozen module declarations, and unchanged false
readiness/authorization/closure/production flags with `authority_effect=none`.

Preparation calls the existing runtime verifier on the original inputs. An
archived verification report cannot substitute for those checks. Selected records
retain the existing local Git source checks; examples remain synthetic.

The installed probe fixes the module targets and operations. A selection cannot
substitute an arbitrary module list, command, environment or worker function.
An interpreter-resident declaration binds to the exact selected interpreter bytes
but does not prove membership. Preparation reports retain
`interpreter_module_membership_verified=false`.

## Finite module and resource bindings

The worker phase covers the worker module, its standard-library import surface
and `_ctypes`. The collector/verifier phase covers acquisition and process modules,
the six existing verifier/compute modules, and PyYAML, jsonschema, referencing,
rpds, attrs, jsonschema-specifications and typing-extensions entry points.
`rpds.rpds` is an explicit native target. Dotted targets also bind their parents.

For file-backed targets the compiler searches only the selected stdlib,
`lib-dynload`, site-package and repository-tools roots. Exactly one supported
provider must exist. Multiple module/package candidates, cross-root ambiguity,
missing package parents and children outside their selected parent package
reject. Source providers must parse with Python 3.11 syntax, without execution.
Native extension providers must be selected `ET_DYN` objects. Namespace-package
and bytecode-only fallback are outside this profile.

A builtin/frozen declaration may coexist with a selected source file, as with a
frozen `os` and its preserved `os.py` landmark. The future probe must observe the
declared membership. A resident declaration cannot replace a required file-backed
package parent.

Preparation also requires nonempty stdlib `os.py` and a selected ELF extension
under `lib-dynload`. It rejects `pyvenv.cfg`, `._pth` files and embedded ZIP,
egg or wheel archives, excluding unmodeled startup overrides from this profile.

The resource contract binds the Draft 2020-12 root metaschema and seven vocabulary
metaschemas: core, applicator, unevaluated, validation, metadata, format annotation
and content. Each requires a unique selected file under
`jsonschema_specifications/schemas`, an exact byte binding, the expected `$id`
and the Draft 2020-12 `$schema` declaration. Additional resources remain preserved
without expanding the finite probe assertions. Generated contracts are checked
against the fixed probe's own contract validator before plan acceptance.

This finite target contract does not establish all Python dependencies.
Conditional imports, frozen modules, native initializers, dynamic imports and
resource reads remain obligations for contained runtime qualification.

## Deterministic launch view

Every capsule payload file receives a path under `/runtime/`, preserving its
exact bytes. Every native SONAME receives a byte-bound alias under
`/runtime/native`. Existing identical source mappings are reused; different
sources cannot occupy one virtual path.

The selected loader also receives each supported Linux interpreter pathname:
`/lib64/ld-linux-x86-64.so.2` or
`/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2`. Unsupported interpreter paths, alias
collisions and file/directory collisions reject.

The view additionally contains:

- `/runtime/bootstrap/probe.py`: the exact selected installed probe.
- `/runtime/bootstrap/contract.json`: the finite module, resource and phase contract.
- An empty `/empty` directory for the planned working directory.

The contract binds the independent input hashes without containing its own digest
or the plan's digest. The plan hashes the contract and all view files. The expected
plan hash is retained externally, preserving an acyclic binding order.

Each phase has a fixed planned command: invoke the selected loader explicitly,
disable its cache, supply `/runtime/native` as its library path, then run the
selected interpreter with `-I -S -B` and the fixed probe's `--phase` argument.
The environment contains only `LC_ALL=C` and `TZ=UTC`.

These fields specify preparation. Writing them does not establish actual loader
capabilities, search results or mappings. `RPATH`/`RUNPATH` and later native loads
still require contained verification. The existing acquisition process retains
its original host dependencies and is not redirected by this plan.

The future runner must install a read-only filesystem boundary before its first
interpreter execution, expose only the selected view, deny network access, close
unrelated descriptors and independently enforce limits. Required limits are
15 seconds wall time, 5 seconds CPU, 512 MiB address space, 64 KiB stdout and
4 KiB stderr, with one attempt and zero operator applications. These are
requirements, not assertions that containment or limits were installed.

## Exact checking and materialization

`check` verifies the independent plan hash, rebuilds the plan from the original
inputs and requires byte-identical canonical output. Modifying a plan and merely
recomputing its hash cannot change its reconstructed paths, module/resource
bindings, commands or boundaries.

Materialization accepts an admitted preparation or, through the CLI, an externally
hashed plan that passes reconstruction. It creates a new private directory and
refuses replacement. Virtual files are written beneath `rootfs/` using
descriptor-relative operations. View files use mode 0400, directories 0700 and
outer records 0600. Executable permissions are not added.

The final check reopens every view file through the same pinned directory used
for writes, verifies its bytes and mode, and checks the complete file/directory
roster, including the empty working directory. The requested output pathname
must still identify that directory before completion is recorded.

The output contains three exact selection copies, `plan.json`,
`materialization_start.json`, `rootfs/` and, on success, `materialization.json`.
A failure retains the produced prefix and, when storage permits, writes
`materialization.incomplete.json`. An incomplete prefix is not a completed view.
There is no retry, resume, overwrite, automatic cleanup or execution mode.

The view is bounded to 8,192 files and 512 MiB, including native aliases. Individual
payload bounds remain those of the runtime capsule. Plan and selection parsing
uses the bounded strict JSON reader with a 4-MiB control limit.

## Diagnostic probe boundary

Before adding explicit import roots, the probe checks Linux x86-64 and CPython
3.11.16; isolated/no-site/no-bytecode flags; interpreter and prefix locations;
initial paths; exact environment; and working directory. It then installs the
explicit profile roots and checks Unicode 14.0.0.

For each phase it checks module descriptors and reported origins, rehashes
selected module files around its import checks and records whether each module
was already loaded. It checks builtin/frozen membership and reads the eight
resources. It exercises fixed canonical JSON, SHA-256 and Unicode cases. The
collector phase also checks a small authored Draft 2020-12 schema against
positive and negative instances.

The probe does not call worker `run`/`main`, acquisition entry points or selected
operator functions. Its fixed targets exclude the original operator modules,
and an import guard rejects their names. Synthetic tests replace runtime-facing
observations with authored objects; they do not execute a selected runtime capsule.

Every successful probe report retains `diagnostic_only=true`. Self-reported paths
and hashes cannot establish that all earlier bootstrap reads were confined or
authenticate a hostile host. This change implements no receipt-to-qualification
promotion and no observed-launch integration.

The primary [Python path-initialization documentation](https://docs.python.org/3.11/library/sys_path_init.html)
describes prefix landmarks and startup overrides. The
[isolation-option documentation](https://docs.python.org/3.11/using/cmdline.html)
specifies that `-I` ignores `PYTHONHOME` and `PYTHONPATH`; those variables cannot
relocate the existing isolated invocation. The
[GNU dynamic-linker documentation](https://sourceware.org/glibc/manual/latest/html_node/Dynamic-Linker-Invocation.html)
describes explicit loader invocation. These mechanisms do not themselves supply
the outer containment required by this profile.

## Offline commands

All output paths must be new. Selected records require the local repository
containing the exact selected source revisions.

```bash
python tools/required_gate_idempotence_bootstrap_v0.py prepare \
  --runtime-selection /absolute/path/runtime-selection.json \
  --runtime-selection-sha256 SELECTED_RUNTIME_SELECTION_SHA256 \
  --operator-selection /absolute/path/operator-selection.json \
  --operator-selection-sha256 SELECTED_OPERATOR_SELECTION_SHA256 \
  --capsule /absolute/path/runtime-capsule.zip \
  --capsule-sha256 SELECTED_CAPSULE_SHA256 \
  --bootstrap-selection /absolute/path/bootstrap-selection.json \
  --bootstrap-selection-sha256 SELECTED_BOOTSTRAP_SELECTION_SHA256 \
  --repository-root /absolute/path/repository \
  --output /absolute/path/new-bootstrap-plan.json
```

For `check`, use the same input arguments, add
`--plan /absolute/path/new-bootstrap-plan.json --plan-sha256 SELECTED_PLAN_SHA256`,
and optionally supply `--output` for a new verification report. For `materialize`,
use the same inputs and plan; replace `--output` with
`--output-directory /absolute/path/new-bootstrap-view`.

Commands print JSON and exit 0 for their completed bounded operation or 1 for
rejection. No command starts the selected interpreter or probe.

## Validation and remaining work

The new regression module is registered once in Tools. Live entries rise from
186 to 187, with all count consumers updated together. Targeted pytest remains
40; earlier documents retain their historical count changes.

Accepted plans report `bootstrap_plan_verified=true`. Exact materialization also
reports `bootstrap_view_bytes_verified=true`. Both retain:

```json
{
  "restored_bootstrap_qualified": false,
  "bootstrap_execution_observed": false,
  "interpreter_module_membership_verified": false,
  "containment_enforced": false,
  "loader_resolution_verified": false,
  "python_import_closure_verified": false,
  "host_environment_qualified": false,
  "runtime_closure_verified": false,
  "execution_ready": false,
  "execution_authorized": false,
  "observed_acquisition_supported": false,
  "metric_pass": null,
  "actual_reference_claimed": false,
  "production_gate_eligible": false,
  "authority_effect": "none"
}
```

Next comes the runner that enforces this view before execution, followed by
independently checked bounded bootstrap observations, dynamic dependency and
loader binding, host review, and observed-launch integration. Actual reference
execution requires separate owner authorization. B3 property calculation and
independent reconstruction, B4 admission and B5 actual reference remain subsequent.

Preserve the original `43514702328`, attempt 1 artifact, historical Q2 FAIL
(49/50 with 1 UNKNOWN), all twelve unsupported gate classifications and completed
Q3 lineage. [#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879)
remains open.

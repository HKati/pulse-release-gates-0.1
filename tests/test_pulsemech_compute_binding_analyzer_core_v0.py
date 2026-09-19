#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
import os
import stat
import subprocess
import sys
import types
from pathlib import Path
from typing import Any

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True

import pytest


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "tools" / "pulsemech_compute_binding_analyzer_core_v0.py"
FIXED_WRAPPER = ROOT / "tools" / "build_pulsemech_compute_binding_report_v0.py"
SUBJECT_BRIDGE = (
    ROOT
    / "tools"
    / "build_pulsemech_compute_binding_report_from_subject_input_v0.py"
)
PACKET = (
    ROOT
    / "examples"
    / "compute"
    / "pulsemech_compute_subject_input_packet_6066_observed_v0.json"
)
CARRIER = ROOT / "PULSE_CI_6066_release_grade_artifact_preservation_v0.zip"
PRESERVATION_DIR = ROOT / "preservation" / "pulse_ci_6066"
MANIFEST = PRESERVATION_DIR / "PRESERVATION_MANIFEST_v0.json"
README = PRESERVATION_DIR / "README.md"
SHA256SUMS = PRESERVATION_DIR / "SHA256SUMS"
REPORT_SCHEMA = ROOT / "schemas" / "pulsemech_compute_binding_report_v0.schema.json"
REPORT_VALIDATOR = ROOT / "tools" / "check_pulsemech_compute_binding_report_v0.py"
TOOLS_TESTS = ROOT / "ci" / "tools-tests.list"

ANALYSIS_RUN_KEY = (
    "OFFLINE_ANALYSIS=pulsemech-compute-binding-fixed-source-6066-v0"
)
CORE_MODULE_NAME = "pulsemech_compute_binding_analyzer_core_v0"
CI_ENTRY = "tests/test_pulsemech_compute_binding_analyzer_core_v0.py"


ANALYZER_DEFINITIONS = (
    "build_report",
    "make_compute_node",
    "make_state_node",
    "make_edge",
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def strict_json_text(text: str, *, label: str) -> dict[str, Any]:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise AssertionError(f"{label}: duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_non_finite(value: str) -> None:
        raise AssertionError(f"{label}: non-finite JSON value: {value}")

    loaded = json.loads(
        text,
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_non_finite,
    )
    assert isinstance(loaded, dict), f"{label}: expected object"
    return loaded


def load_source_module(path: Path, module_name: str) -> Any:
    source = path.read_bytes()
    module = types.ModuleType(module_name)
    module.__file__ = str(path)
    module.__cached__ = None
    module.__loader__ = None
    module.__package__ = ""
    module.__spec__ = None
    module.__pulsemech_source_sha256__ = sha256_bytes(source)
    sys.modules[module_name] = module
    exec(compile(source, str(path), "exec", dont_inherit=True), module.__dict__)
    return module


BRIDGE_MODULE = load_source_module(
    SUBJECT_BRIDGE,
    "pulsemech_subject_input_report_bridge_v0_for_core_regression",
)
PACKET_VALIDATOR_BRIDGE_MODULE = (
    "pulsemech_subject_input_packet_validator_v0_for_bridge"
)


def _regression_validate_git_executable(module: Any, candidate: Path) -> Path:
    if not candidate.is_absolute():
        raise module.SemanticError(
            f"git_executable_untrusted: path_not_absolute: {candidate}"
        )

    normalized = Path(os.path.abspath(os.path.normpath(str(candidate))))
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise module.SemanticError(
            f"git_executable_untrusted: path_unresolvable: {candidate}: {exc}"
        ) from exc

    if os.path.normcase(str(normalized)) != os.path.normcase(str(resolved)):
        raise module.SemanticError(
            "git_executable_untrusted: symlink_or_alias_path: "
            f"declared={normalized} resolved={resolved}"
        )
    if candidate.is_symlink() or not resolved.is_file():
        raise module.SemanticError(
            "git_executable_untrusted: not_regular_non_symlink_file: "
            f"{resolved}"
        )
    if not os.access(resolved, os.X_OK):
        raise module.SemanticError(
            f"git_executable_untrusted: not_executable: {resolved}"
        )

    components: list[Path] = [resolved]
    cursor = resolved.parent
    while True:
        components.append(cursor)
        if cursor == cursor.parent:
            break
        cursor = cursor.parent

    for component in components:
        try:
            metadata = component.lstat()
        except OSError as exc:
            raise module.SemanticError(
                "git_executable_untrusted: component_unavailable: "
                f"{component}: {exc}"
            ) from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise module.SemanticError(
                f"git_executable_untrusted: symlink_component: {component}"
            )
        if component == resolved:
            if not stat.S_ISREG(metadata.st_mode):
                raise module.SemanticError(
                    "git_executable_untrusted: executable_not_regular: "
                    f"{component}"
                )
        elif not stat.S_ISDIR(metadata.st_mode):
            raise module.SemanticError(
                f"git_executable_untrusted: parent_not_directory: {component}"
            )
        if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise module.SemanticError(
                f"git_executable_untrusted: writable_component: {component}"
            )

    return resolved


@contextmanager
def _regression_git_binding() -> Any:
    original_loader = BRIDGE_MODULE.load_module_from_capture

    def load_with_regression_git_binding(
        capture: Any,
        module_name: str,
    ) -> Any:
        module = original_loader(capture, module_name)
        if module_name == PACKET_VALIDATOR_BRIDGE_MODULE:
            production_validate = module._validate_trusted_git_executable

            def validate_for_regression(candidate: Path) -> Path:
                try:
                    return production_validate(candidate)
                except module.SemanticError as exc:
                    if "non_root_owned_component" not in str(exc):
                        raise
                    return _regression_validate_git_executable(
                        module,
                        candidate,
                    )

            module._validate_trusted_git_executable = validate_for_regression
            module._trusted_git_executable.cache_clear()
        return module

    BRIDGE_MODULE.load_module_from_capture = load_with_regression_git_binding
    try:
        yield
    finally:
        BRIDGE_MODULE.load_module_from_capture = original_loader


def build_subject_bridge_in_process() -> str:
    dependencies = BRIDGE_MODULE._capture_dependencies()
    with _regression_git_binding():
        return BRIDGE_MODULE.build_from_captured_inputs(
            packet_capture=BRIDGE_MODULE.capture_regular_file(
                PACKET,
                label="packet",
            ),
            carrier_capture=BRIDGE_MODULE.capture_regular_file(
                CARRIER,
                label="carrier",
            ),
            repository_root=ROOT,
            analysis_run_key=ANALYSIS_RUN_KEY,
            dependency_captures=dependencies,
        )


def run_fixed_wrapper() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(FIXED_WRAPPER),
            "--archive",
            str(CARRIER),
            "--manifest",
            str(MANIFEST),
            "--readme",
            str(README),
            "--sha256sums",
            str(SHA256SUMS),
            "--schema",
            str(REPORT_SCHEMA),
            "--validator",
            str(REPORT_VALIDATOR),
            "--analysis-run-key",
            ANALYSIS_RUN_KEY,
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def run_core() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CORE),
            "--archive",
            str(CARRIER),
            "--manifest",
            str(MANIFEST),
            "--readme",
            str(README),
            "--sha256sums",
            str(SHA256SUMS),
            "--schema",
            str(REPORT_SCHEMA),
            "--validator",
            str(REPORT_VALIDATOR),
            "--analysis-run-key",
            ANALYSIS_RUN_KEY,
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def snapshot_tools_tree() -> tuple[tuple[str, str, int, str | None], ...]:
    records: list[tuple[str, str, int, str | None]] = []
    tools = ROOT / "tools"
    for path in sorted(tools.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(tools).as_posix()
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            records.append((relative, "symlink", metadata.st_size, os.readlink(path)))
        elif stat.S_ISDIR(metadata.st_mode):
            records.append((relative, "directory", metadata.st_size, None))
        elif stat.S_ISREG(metadata.st_mode):
            data = path.read_bytes()
            records.append((relative, "file", len(data), sha256_bytes(data)))
        else:
            records.append((relative, "other", metadata.st_size, None))
    return tuple(records)


def analysis_projection(report: dict[str, Any]) -> dict[str, Any]:
    projected = json.loads(json.dumps(report))
    projected["tool"]["source_sha256"] = "<producer-entrypoint>"
    return projected


@pytest.fixture(scope="module")
def fixed_result() -> tuple[str, dict[str, Any]]:
    result = run_fixed_wrapper()
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    return result.stdout, strict_json_text(result.stdout, label="fixed report")


def test_required_core_wrapper_bridge_and_inputs_exist() -> None:
    for path in (
        CORE,
        FIXED_WRAPPER,
        SUBJECT_BRIDGE,
        PACKET,
        CARRIER,
        MANIFEST,
        README,
        SHA256SUMS,
        REPORT_SCHEMA,
        REPORT_VALIDATOR,
        TOOLS_TESTS,
    ):
        assert path.is_file(), path
        assert not path.is_symlink(), path


def test_analyzer_definitions_exist_only_in_core() -> None:
    core_source = CORE.read_text(encoding="utf-8")
    fixed_source = FIXED_WRAPPER.read_text(encoding="utf-8")
    bridge_source = SUBJECT_BRIDGE.read_text(encoding="utf-8")

    for name in ANALYZER_DEFINITIONS:
        marker = f"def {name}("
        assert core_source.count(marker) == 1, name
        assert marker not in fixed_source, name
        assert marker not in bridge_source, name


def test_fixed_entrypoint_reexports_exact_core_implementation() -> None:
    sys.modules.pop(CORE_MODULE_NAME, None)
    wrapper = load_source_module(
        FIXED_WRAPPER,
        "pulsemech_compute_binding_fixed_wrapper_v0_under_test",
    )

    assert wrapper.ANALYZER_CORE.resolve() == CORE.resolve()
    assert wrapper.ANALYZER_CORE_SOURCE_SHA256 == sha256_file(CORE)
    assert wrapper.build_report.__module__ == CORE_MODULE_NAME
    assert wrapper.load_observed_bundle.__module__ == CORE_MODULE_NAME
    assert wrapper.make_compute_node.__module__ == CORE_MODULE_NAME
    assert wrapper.make_state_node.__module__ == CORE_MODULE_NAME
    assert wrapper.make_edge.__module__ == CORE_MODULE_NAME


def test_fixed_wrapper_and_subject_bridge_are_byte_identical(
    fixed_result: tuple[str, dict[str, Any]],
) -> None:
    fixed_stdout, report = fixed_result
    bridge_stdout = build_subject_bridge_in_process()
    assert bridge_stdout == fixed_stdout

    assert report["tool"] == {
        "id": "build_pulsemech_compute_binding_report_v0",
        "version": "0.1.0",
        "source_sha256": sha256_file(FIXED_WRAPPER),
    }
    observer = next(
        node
        for node in report["compute_nodes"]
        if node["node_id"] == "compute:offline-observer"
    )
    assert observer["source_identity"] == {
        "source_kind": "repository_file",
        "source_path_or_uri": "tools/pulsemech_compute_binding_analyzer_core_v0.py",
        "source_revision": "0.1.0",
        "source_sha256": sha256_file(CORE),
    }


def test_direct_core_preserves_analysis_payload(
    fixed_result: tuple[str, dict[str, Any]],
) -> None:
    _fixed_stdout, fixed_report = fixed_result
    core = run_core()
    assert core.returncode == 0, core.stdout + core.stderr
    assert core.stderr == ""
    core_report = strict_json_text(core.stdout, label="core report")

    assert core_report["tool"]["source_sha256"] == sha256_file(CORE)
    assert analysis_projection(core_report) == analysis_projection(fixed_report)


def test_repeated_wrapper_execution_is_deterministic(
    fixed_result: tuple[str, dict[str, Any]],
) -> None:
    first_stdout, _report = fixed_result
    second = run_fixed_wrapper()
    assert second.returncode == 0, second.stdout + second.stderr
    assert second.stderr == ""
    assert second.stdout == first_stdout


def test_core_extraction_writes_no_tools_entry(
    fixed_result: tuple[str, dict[str, Any]],
) -> None:
    before = snapshot_tools_tree()
    fixed = run_fixed_wrapper()
    bridge_stdout = build_subject_bridge_in_process()
    core = run_core()
    after = snapshot_tools_tree()

    assert fixed.returncode == 0, fixed.stdout + fixed.stderr
    assert bridge_stdout == fixed.stdout
    assert core.returncode == 0, core.stdout + core.stderr
    assert before == after


def test_core_and_wrappers_compile_from_exact_source_bytes() -> None:
    for path in (CORE, FIXED_WRAPPER, SUBJECT_BRIDGE):
        compile(path.read_bytes(), str(path), "exec", dont_inherit=True)


def test_core_test_is_registered_exactly_once() -> None:
    entries = [
        line.strip()
        for line in TOOLS_TESTS.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert entries.count(CI_ENTRY) == 1


def test_core_cli_and_fixed_cli_remain_available() -> None:
    for path in (CORE, FIXED_WRAPPER):
        result = subprocess.run(
            [sys.executable, str(path), "--help"],
            cwd=ROOT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert result.stderr == ""
        assert "--archive" in result.stdout
        assert "--analysis-run-key" in result.stdout


# ---------------------------------------------------------------------------
# Runtime-profile fixtures. All synthetic objects below are example records,
# not observations of #6066. The authentic reference is loaded separately.
# ---------------------------------------------------------------------------

def runtime_test_module(filename: str) -> Any:
    import hashlib
    path = ROOT / "tools" / filename
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    name = "runtime_test_" + path.stem + "_" + digest
    if name not in sys.modules:
        load_source_module(path, name)
    return sys.modules[name]


def runtime_test_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def runtime_test_view(data: bytes) -> Any:
    checker = runtime_test_module("check_pulsemech_compute_binding_report_v0.py")
    return checker.RuntimeBytesView(data)


def runtime_test_synthetic_case() -> dict[str, Any]:
    """Full runtime-schema fixture and explicit synthetic upstream context.

    The small upstream context supplies the pure graph constructor's inputs;
    it is not a complete observed subject-input packet or a live carrier.
    CLI tests never use it as an observed subject-input proof.
    """
    import copy
    core = runtime_test_module("pulsemech_compute_binding_analyzer_core_v0.py")
    template = json.loads((ROOT / "examples/compute/pulsemech_compute_runtime_observation_packet_example_v0.json").read_bytes())
    p = copy.deepcopy(template)
    key = "GITHUB_RUN_ID=1|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=Synthetic runtime"
    context = {
        "repository": "example/pulse-runtime", "workflow_name": "Synthetic runtime",
        "workflow_run_id": 1, "workflow_run_number": 1, "workflow_run_attempt": 1,
        "subject_run_key": key, "source_commit": "a" * 40,
        "release_candidate_id": "synthetic", "run_mode": "prod", "active_policy_sets": ["required"],
    }
    p["subject"] = {**context, "source_ref": "refs/heads/example", "event_name": "workflow_dispatch"}
    collector_id = "execution:synthetic-collector"
    producer_id = "execution:synthetic-producer"
    consumer_id = "execution:synthetic-consumer"
    clock = lambda n: f"2026-01-01T00:00:0{n}Z"
    def timing(a: int, b: int) -> dict[str, Any]:
        return {"timing_status": "complete", "started_utc": clock(a), "completed_utc": clock(b),
                "duration_ms": (b-a)*1000, "timestamp_source": "tool_reported", "duration_source": "derived_from_timestamps"}
    def execution(rid: str, name: str, inputs: list[str], outputs: list[str], a: int, b: int) -> dict[str, Any]:
        row = copy.deepcopy(template["executions"][0])
        row.update(execution_id=rid, execution_kind="local_tool_execution", execution_scope="subject",
                   declared_role="advisory", job_id=None, job_name="synthetic", job_attempt=1, step_name=None, step_number=None,
                   parent_execution_id=None, input_state_ids=inputs, output_state_ids=outputs,
                   permitted_mutation_authority="advisory_output" if outputs else "none", resource_measurement_ids=[],
                   external_call_ids=[], model_inference_ids=[], workflow_name=context["workflow_name"], timing=timing(a,b))
        row["source_identity"].update(source_revision=context["source_commit"], source_path_or_uri="tools/"+name+".py",
                                      source_sha256=sha256_bytes((name+" source").encode()))
        row["command_identity"].update(display_name=name, command_sha256=sha256_bytes(name.encode()), arguments_sha256=sha256_bytes(b"[]"))
        row["run_binding"] = {"subject_run_key":key,"execution_run_key":key,"binding_mode":"current_subject_run","binding_complete":True}
        return row
    producer = execution(producer_id,"runtime_producer_fixture",["state:synthetic-input"],["state:synthetic-output"],1,2)
    consumer = execution(consumer_id,"runtime_consumer_fixture",["state:synthetic-output"],[],3,4)
    collector = execution(collector_id,"runtime_collector_fixture",[],[],0,5)
    collector.update(execution_kind="observer_execution", execution_scope="observation_collector", declared_role="observer", permitted_mutation_authority="advisory_output")
    collector["run_binding"].update(execution_run_key="SYNTHETIC_COLLECTOR=separate",binding_mode="external_export")
    p["executions"] = sorted([producer,consumer,collector],key=lambda row:row["execution_id"])
    p["producer"].update(producer_execution_id=collector_id,producer_source=collector["source_identity"]["source_path_or_uri"],
                         producer_source_sha256=collector["source_identity"]["source_sha256"],collection_mode="example")
    p["packet_identity"].update(packet_id="runtime-observation:synthetic-0",packet_sequence=0,previous_packet_sha256=None,
                                packet_scope="example",subject_run_key=key,packet_created_utc=clock(5))
    p["observation_boundary"].update(subject_run_key=key,collector_execution_id=collector_id,collector_run_key="SYNTHETIC_COLLECTOR=separate",
                                     capture_started_utc=clock(0),capture_completed_utc=clock(5),collector_mode="example")
    states = []
    authority = {}
    for role, kind, path in (("workflow","workflow_source",".github/workflows/example.yml"),
                             ("policy","policy","example_policy.yml"),("gate_registry","gate_registry","example_registry.yml")):
        digest = sha256_bytes((role+" bytes").encode())
        authority[role] = {"role":role,"path":path,"source_commit":context["source_commit"],"sha256":digest}
        row = copy.deepcopy(template["state_observations"][0])
        row.update(state_id="state:"+role+"-source",state_type=kind,path_or_uri=path,content_status="exact_digest",sha256=digest,
                   size_bytes=len((role+" bytes").encode()),producer_execution_id=None,observer_execution_id=collector_id,
                   subject_run_key=key,release_candidate_id="synthetic",authority_bearing=True,mutation_class="none",observed_at_utc=clock(4))
        states.append(row)
    for name, producer_ref in (("input",None),("output",producer_id)):
        row = copy.deepcopy(template["state_observations"][0])
        row.update(state_id="state:synthetic-"+name,state_type="other",path_or_uri="example/"+name+".bin",content_status="exact_digest",
                   sha256=sha256_bytes(name.encode()),size_bytes=len(name),producer_execution_id=producer_ref,observer_execution_id=collector_id,
                   subject_run_key=key,release_candidate_id="synthetic",authority_bearing=False,
                   mutation_class="advisory_output" if producer_ref else "none",observed_at_utc=clock(4))
        states.append(row)
    p["authority_inputs"] = authority
    p["state_observations"] = sorted(states,key=lambda row:row["state_id"])
    collector["input_state_ids"] = [row["state_id"] for row in p["state_observations"]]
    p["external_calls"] = []; p["model_inferences"] = []; p["resource_measurements"] = []
    p["coverage"].update(coverage_status="partial",expected_job_count=0,observed_job_count=0,expected_step_count=0,observed_step_count=0,
                         execution_records=3,state_records=5,external_call_records=0,model_inference_records=0,resource_measurement_records=0,
                         external_call_capture_status="none",model_inference_capture_status="none",state_digest_capture_status="complete",
                         resource_axes_observed=[],resource_axes_unavailable=sorted(runtime_test_module("check_pulsemech_compute_runtime_observation_packet_v0.py").RESOURCE_AXES),
                         unobserved_reasons=["resource_axis_unavailable"])
    subject = {
        "repository":context["repository"],"workflow":context["workflow_name"],"workflow_run_id":1,"workflow_run_number":1,"workflow_run_attempt":1,
        "source_commit":context["source_commit"],"release_candidate_id":"synthetic","run_mode":"prod","active_policy_sets":["required"],
        "policy_id":"synthetic-policy","policy_sha256":authority["policy"]["sha256"],"materialized_gate_set_sha256":None,
        "final_status_sha256":sha256_bytes(b"synthetic-status"),"release_decision_sha256":sha256_bytes(b"synthetic-decision"),"decision":"ALLOW",
    }
    b = {"schema_version":"pulsemech_compute_binding_report_v0","report_type":"pulsemech_compute_binding_report","record_status":"example",
         "tool":{"id":"build_pulsemech_compute_binding_report_v0","version":"0.1.0","source_sha256":sha256_file(FIXED_WRAPPER)},
         "analysis_boundary":{"analysis_level":"artifact_observed","subject_run_key":key,"analysis_run_key":"SYNTHETIC_ANALYSIS=separate","observer_in_subject_totals":False},
         "subject":subject,"inputs":[],"compute_nodes":[],"state_nodes":[],"edges":[],"resource_summary":{"axes":{}},
         "summary":{"subject_compute_nodes":0,"observer_nodes":0,"unbound_authoritative_mutation_count":0,"decision_closure_complete":False,
                    "authority_binding_complete":False,"resource_measurement_status":"none",**{field:0 for field in core.SUMMARY_COUNT_FIELDS.values()}},
         "findings":[],"errors":[],"ok":True}
    carrier = b"synthetic-upstream-carrier\n"
    s = {"record_status":"example","subject":{**subject,**context},"authority_sources":{
        role:{"path_or_uri":a["path"],"source_revision":a["source_commit"],"sha256":a["sha256"]} for role,a in authority.items()},
         "carrier":{"sha256":sha256_bytes(carrier),"size_bytes":len(carrier)}}
    # Explicit requirements precede runtime evaluation; they are not generated
    # from whatever executions happen to remain in a mutated packet.
    requirements = {
        producer_id:{"input_state_ids":["state:synthetic-input"],"output_state_ids":["state:synthetic-output"],"required_consumers":{"state:synthetic-output":[consumer_id]}},
        consumer_id:{"input_state_ids":["state:synthetic-output"],"output_state_ids":[],"required_consumers":{}},
    }
    return {"baseline":b,"subject_input":s,"carrier_bytes":carrier,"packets":[p],"context":context,"requirements":requirements}


def runtime_test_activity_case() -> dict[str, Any]:
    """The unchanged complete-schema example covers calls, inference and usage."""
    c = runtime_test_synthetic_case()
    p = json.loads((ROOT / "examples/compute/pulsemech_compute_runtime_observation_packet_example_v0.json").read_bytes())
    context = {key:p["subject"][key] for key in c["context"]}
    b = c["baseline"]; bs = b["subject"]
    for key,value in context.items():
        if key == "subject_run_key":b["analysis_boundary"][key]=value
        elif key == "workflow_name":bs["workflow"]=value
        elif key == "active_policy_sets":bs[key]=sorted(value)
        else:bs[key]=value
    bs["policy_sha256"]=p["authority_inputs"]["policy"]["sha256"]
    c["subject_input"]["subject"]={**bs,**context}
    c["subject_input"]["authority_sources"]={role:{"path_or_uri":a["path"],"source_revision":a["source_commit"],"sha256":a["sha256"]} for role,a in p["authority_inputs"].items()}
    c.update(packets=[p],context=context,requirements=None)
    return c


def runtime_test_historical_case() -> dict[str, Any]:
    core = runtime_test_module("pulsemech_compute_binding_analyzer_core_v0.py")
    bundle = core.load_observed_bundle(archive_path=CARRIER,manifest_path=MANIFEST,readme_path=README,sha256sums_path=SHA256SUMS,
                                       expected_archive_sha256=core.EXPECTED_ARCHIVE_SHA256,expected_archive_size=core.EXPECTED_ARCHIVE_SIZE)
    baseline = core.build_report(bundle,analysis_run_key=ANALYSIS_RUN_KEY,builder_source_sha256=sha256_file(FIXED_WRAPPER),analyzer_core_source_sha256=sha256_file(CORE))
    packet_path=ROOT/"preservation/pulse_ci_6066/runtime_observation_packet_v0/pulsemech_compute_runtime_observation_packet_6066_observed_v0.json"
    return {"baseline":baseline,"subject_input":json.loads(PACKET.read_bytes()),"subject_input_bytes":PACKET.read_bytes(),
            "carrier_bytes":CARRIER.read_bytes(),"packets":[json.loads(packet_path.read_bytes())],"packet_bytes":[packet_path.read_bytes()],
            "requirements":None}


def runtime_test_inputs(case: dict[str, Any], *, extent: bool = False) -> dict[str, Any]:
    packets = case.get("packet_bytes") or [runtime_test_bytes(p) for p in case["packets"]]
    sources = [("sha256:"+sha256_bytes(raw),raw) for raw in packets]
    extent_bytes = None
    if extent:
        extent_bytes = runtime_test_bytes({"profile":"synthetic_runtime_extent_v0","record_status":"example",
            "subject_context":case["context"],"requirements":case["requirements"],"terminal_packet_sha256":sha256_bytes(packets[-1])})
    return {"baseline_bytes":runtime_test_bytes(case["baseline"]),"subject_input_bytes":case.get("subject_input_bytes") or runtime_test_bytes(case["subject_input"]),
            "carrier_bytes":case["carrier_bytes"],"packet_sources":sources,"extent_bytes":extent_bytes,"repository_root":ROOT}


def runtime_test_report(case: dict[str, Any], *, extent: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    core = runtime_test_module("pulsemech_compute_binding_analyzer_core_v0.py")
    inputs = runtime_test_inputs(case,extent=extent)
    report = core.build_runtime_report(baseline_bytes=inputs["baseline_bytes"],subject_input_bytes=inputs["subject_input_bytes"],carrier_bytes=inputs["carrier_bytes"],
        packet_sources=[core.RuntimePacketSource(*source) for source in inputs["packet_sources"]],entrypoint_sha256=sha256_file(SUBJECT_BRIDGE),
        analyzer_sha256=sha256_file(CORE),extent_bytes=inputs["extent_bytes"])
    return json.loads(runtime_test_bytes(report)), inputs


def runtime_test_relation(case: dict[str, Any], *, extent: bool = False, revision: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    builder = runtime_test_module("build_pulsemech_compute_planned_observed_relation_v0.py")
    if revision is None:
        revision = builder.resolve_runtime_tool_source_revision(None, record_status=case["baseline"]["record_status"])
    report, report_inputs = runtime_test_report(case,extent=extent)
    plan = json.loads((ROOT/"examples/compute/pulsemech_compute_fixed_source_6066_integration_plan_v0.json").read_bytes())
    explicit_raw = None
    explicit = {}
    if report["record_status"] == "example":
        producer = next(e for e in case["packets"][0]["executions"] if e["execution_id"] == "execution:synthetic-producer")
        plan["source"].update(repository=report["subject"]["repository"],revision=report["subject"]["source_commit"],policy_sha256=report["subject"]["policy_sha256"])
        plan["target"]["repository_id"] = report["subject"]["repository"]
        op = plan["operations"][0]
        op.update(source_path=producer["source_identity"]["source_path_or_uri"],target_path=producer["source_identity"]["source_path_or_uri"],
                  source_sha256=producer["source_identity"]["source_sha256"],source_size_bytes=len(b"runtime_producer_fixture source"))
    else:
        explicit_raw = (ROOT/"examples/compute/pulsemech_compute_subject_run_expectations_6066_v0.json").read_bytes()
        explicit = builder.extract_expectations(json.loads(explicit_raw))
    plan_raw=runtime_test_bytes(plan);report_raw=runtime_test_bytes(report)
    rel=builder.build_relation_record(plan=plan,plan_bytes=plan_raw,plan_path_or_uri="sha256:"+sha256_bytes(plan_raw),
        report=report,report_bytes=report_raw,report_path_or_uri="sha256:"+sha256_bytes(report_raw),
        packets=[(json.loads(raw),raw,loc) for loc,raw in report_inputs["packet_sources"]],explicit_expectations=explicit,
        relation_id="planned-observed:runtime-regression-v0",tool_source_revision=revision,expectations_bytes=explicit_raw)
    return json.loads(runtime_test_bytes(rel)), {"report_inputs":report_inputs,"report_bytes":report_raw,"plan_bytes":plan_raw,"expectations_bytes":explicit_raw}


# ---------------------------------------------------------------------------
# Direct tools-tests execution entrypoint
# ---------------------------------------------------------------------------


def check_pulsemech_compute_binding_analyzer_core_v0() -> None:
    raise SystemExit(
        pytest.main(
            [
                __file__,
                "-q",
                "-p",
                "no:cacheprovider",
            ]
        )
    )



# Focused field-level unit fixtures are synthetic and deliberately smaller
# than complete packets; full-schema/source-aware cases are separate below.
import copy
M = runtime_test_module("pulsemech_compute_binding_analyzer_core_v0.py")

def subject():
    return {
        'repository': 'synthetic/step5-test', 'workflow_name': 'Synthetic runtime test',
        'workflow_run_id': 101, 'workflow_run_number': 7, 'workflow_run_attempt': 1,
        'subject_run_key': 'SYNTHETIC_SUBJECT=101|ATTEMPT=1', 'source_commit': 'a' * 40,
        'release_candidate_id': 'synthetic-candidate', 'run_mode': 'synthetic',
        'active_policy_sets': ['required', 'release_required'],
    }


def authority():
    return {
        role: {'role': role, 'path': path, 'source_commit': 'a' * 40, 'sha256': char * 64}
        for role, path, char in (
            ('workflow', '.github/workflows/synthetic.yml', '1'),
            ('policy', 'synthetic_policy.yml', '2'),
            ('gate_registry', 'synthetic_registry.yml', '3'),
        )
    }


def execution(identifier, inputs=(), outputs=(), *, scope='subject', parent=None):
    return {
        'execution_id': identifier, 'execution_kind': 'workflow_step',
        'execution_scope': scope, 'parent_execution_id': parent,
        'declared_role': 'transition' if scope == 'subject' else 'observer',
        'result': {'lifecycle_status':'completed','outcome':'success','result_status':'complete','exit_code':0},
        'command_identity': {'command_kind':'python_script','command_sha256':'6'*64,'arguments_sha256':'7'*64,'raw_command_included':False},
        'capture_status': 'complete', 'input_state_ids': list(inputs),
        'output_state_ids': list(outputs),
        'source_identity': {
            'identity_status': 'exact', 'source_kind': 'repository_file',
            'source_path_or_uri': 'tools/synthetic.py', 'source_revision': 'a' * 40,
            'source_sha256': '4' * 64,
        },
        'run_binding': {
            'subject_run_key': subject()['subject_run_key'],
            'execution_run_key': subject()['subject_run_key'] if scope == 'subject' else 'SYNTHETIC_COLLECTOR=separate',
            'binding_mode': 'current_subject_run' if scope == 'subject' else 'external_export',
            'binding_complete': True,
        },
    }


def packet():
    producer = execution('execution:producer', outputs=['state:a', 'state:b'])
    consumer = execution('execution:consumer', inputs=['state:a', 'state:b'])
    collector = execution('execution:collector', scope='observation_collector')
    return {
        'schema_version': 'pulsemech_compute_runtime_observation_packet_v0',
        'packet_type': 'pulsemech_compute_runtime_observation_packet',
        'record_status': 'example', 'ok': True, 'errors': [],
        'subject': subject(), 'authority_inputs': authority(),
        'packet_identity': {
            'packet_id': 'runtime-observation:synthetic-0', 'packet_sequence': 0,
            'previous_packet_sha256': None, 'subject_run_key': subject()['subject_run_key'],
        },
        'executions': [producer, consumer, collector],
        'state_observations': [
            {'state_id': key, 'subject_run_key': subject()['subject_run_key'],
             'producer_execution_id': 'execution:producer', 'content_status': 'exact_digest',
             'sha256': '5' * 64, 'size_bytes': 23, 'path_or_uri': path}
            for key, path in [('state:a', 'synthetic/a.json'), ('state:b', 'synthetic/b.json')]
        ],
        'external_calls': [], 'model_inferences': [],
        'producer': {'producer_execution_id': 'execution:collector', 'producer_name': 'synthetic'},
        'observation_boundary': {
            'subject_run_key': subject()['subject_run_key'],
            'collector_execution_id': 'execution:collector',
            'collector_run_key': 'SYNTHETIC_COLLECTOR=separate',
            'observer_in_subject_totals': False,
        },
        'coverage': {'coverage_status': 'partial', 'resource_axes_unavailable': ['cpu_seconds']},
    }


def raw(p):
    return (json.dumps(p, sort_keys=True, indent=2, ensure_ascii=False) + '\n').encode()


def source(p, locator='synthetic://packet-0'):
    return M.RuntimePacketSource(locator, raw(p))


def index(*packets):
    return M.index_runtime_packet_sources(
        [source(p, f'synthetic://packet-{i}') for i, p in enumerate(packets or [packet()])],
        expected_subject=subject(), expected_authority_inputs=authority(),
    )


def successor(p, *, sequence=1):
    q = copy.deepcopy(p)
    q['packet_identity'] = {
        'packet_id': f'runtime-observation:synthetic-{sequence}',
        'packet_sequence': sequence,
        'previous_packet_sha256': hashlib.sha256(raw(p)).hexdigest(),
        'subject_run_key': subject()['subject_run_key'],
    }
    return q


def consumption(p=None, required=None):
    return M.assess_runtime_output_consumption(
        index(p or packet()), producer_execution_id='execution:producer',
        required_output_state_ids=['state:a', 'state:b'] if required is None else required,
    )


def test_exact_bytes_inventory_is_not_a_reserialized_hash():
    p = packet()
    data = json.dumps(p).encode()
    r = M.index_runtime_packet_sources([M.RuntimePacketSource('synthetic://p', data)],
        expected_subject=subject(), expected_authority_inputs=authority())
    assert r['packet_inventory'][0]['sha256'] == hashlib.sha256(data).hexdigest()
    assert r['packet_inventory'][0]['sha256'] != hashlib.sha256(raw(p)).hexdigest()
    assert r['packet_inventory'][0]['size_bytes'] == len(data)


def test_a_valid_prefix_never_claims_terminal_closure():
    r = index()
    assert r['supplied_sequence_status'] == 'rooted_contiguous'
    assert r['terminal_observation_extent'] == 'unknown'
    assert not any(key in r for key in ['ok', 'verified', 'source_verified', 'comparison_complete'])


def test_same_input_bytes_are_deterministic_and_source_permutation_is_irrelevant():
    p = packet(); q = successor(p)
    sources = [source(p), source(q, 'synthetic://packet-1')]
    kwargs = {'expected_subject': subject(), 'expected_authority_inputs': authority()}
    a = M.index_runtime_packet_sources(sources, **kwargs)
    b = M.index_runtime_packet_sources(reversed(sources), **kwargs)
    assert raw(a) == raw(b)
    assert raw(a) == raw(M.index_runtime_packet_sources(sources, **kwargs))


def test_identical_repeated_occurrences_retain_both_source_references():
    p = packet(); r = index(p, successor(p))
    assert len(r['records']['executions']) == 3
    assert len(r['records']['executions']['execution:producer']['source_refs']) == 2
    assert r['counts']['subject_execution_occurrences'] == 2
    assert r['counts']['observer_execution_occurrences'] == 1


def test_equal_state_bytes_do_not_merge_distinct_logical_states():
    r = index()
    assert set(r['records']['state_observations']) == {'state:a', 'state:b'}
    a = r['records']['state_observations']['state:a']['record']
    b = r['records']['state_observations']['state:b']['record']
    assert a['sha256'] == b['sha256'] and a['path_or_uri'] != b['path_or_uri']


def test_equal_tool_names_and_digests_do_not_merge_distinct_occurrences():
    r = index()
    assert 'execution:producer' in r['records']['executions']
    assert 'execution:consumer' in r['records']['executions']


def test_original_ordered_policy_is_retained():
    assert index()['subject_context']['active_policy_sets'] == ['required', 'release_required']


@pytest.mark.parametrize('field,value', [
    ('repository','other/repository'), ('workflow_name','Other'),
    ('workflow_run_id',102), ('workflow_run_number',8), ('workflow_run_attempt',2),
    ('subject_run_key','OTHER=101'), ('source_commit','b'*40),
    ('release_candidate_id','other'), ('run_mode','other'),
    ('active_policy_sets',['release_required','required']),
])
def test_every_subject_dimension_is_checked(field, value):
    p = packet(); p['subject'][field] = value
    with pytest.raises(M.RuntimeIndexError): index(p)


@pytest.mark.parametrize('field,value', [
    ('workflow_run_id',True), ('workflow_run_attempt',False), ('workflow_run_number',0),
    ('source_commit','x'*40), ('active_policy_sets',['required','required']),
    ('active_policy_sets',[]), ('run_mode',None),
])
def test_invalid_expected_context_is_not_accepted(field, value):
    s = subject(); s[field] = value
    with pytest.raises(M.RuntimeIndexError):
        M.index_runtime_packet_sources([source(packet())], expected_subject=s, expected_authority_inputs=authority())


@pytest.mark.parametrize('role', ['workflow','policy','gate_registry'])
@pytest.mark.parametrize('field,value', [('path','substituted.yml'),('sha256','9'*64),('source_commit','b'*40)])
def test_all_authority_descriptors_are_checked(role, field, value):
    p = packet(); p['authority_inputs'][role][field] = value
    with pytest.raises(M.RuntimeIndexError): index(p)


@pytest.mark.parametrize('data', [
    b'{"ok":true,"ok":false}', b'{"x":NaN}', b'{"x":Infinity}',
    b'{"x":1e9999}', b'\xff', b'\xef\xbb\xbf{}', b'[]', b'{',
])
def test_ambiguous_or_invalid_json_is_rejected(data):
    with pytest.raises(M.RuntimeIndexError):
        M.index_runtime_packet_sources([M.RuntimePacketSource('synthetic://bad', data)],
            expected_subject=subject(), expected_authority_inputs=authority())


def test_mutable_bytearray_is_rejected():
    with pytest.raises(M.RuntimeIndexError, match='immutable_bytes'):
        M.index_runtime_packet_sources([M.RuntimePacketSource('synthetic://bad', bytearray(raw(packet())))],
            expected_subject=subject(), expected_authority_inputs=authority())


def test_no_output_aliases_expected_context():
    s = subject(); h = authority()
    r = M.index_runtime_packet_sources([source(packet())], expected_subject=s, expected_authority_inputs=h)
    s['active_policy_sets'].reverse(); h['policy']['sha256'] = '0'*64
    assert r['subject_context']['active_policy_sets'] == ['required','release_required']
    assert r['authority_inputs']['policy']['sha256'] == '2'*64


def test_no_input_mutation():
    p = packet(); original = raw(p)
    r = index(p)
    r['records']['executions']['execution:producer']['record']['declared_role'] = 'other'
    assert raw(p) == original


def test_empty_sources_fail():
    with pytest.raises(M.RuntimeIndexError, match='set_empty'):
        M.index_runtime_packet_sources([], expected_subject=subject(), expected_authority_inputs=authority())


def test_duplicate_locator_fails():
    with pytest.raises(M.RuntimeIndexError, match='locator_duplicate'):
        M.index_runtime_packet_sources([source(packet()), source(packet())],
            expected_subject=subject(), expected_authority_inputs=authority())


@pytest.mark.parametrize('sequence', [True, False, -1, 0.0, '0'])
def test_sequence_requires_a_real_nonnegative_integer(sequence):
    p = packet(); p['packet_identity']['packet_sequence'] = sequence
    with pytest.raises(M.RuntimeIndexError): index(p)


def test_wrong_predecessor_fails():
    p = packet(); q = successor(p); q['packet_identity']['previous_packet_sha256'] = '0'*64
    with pytest.raises(M.RuntimeIndexError, match='digest_mismatch'): index(p, q)


def test_formatting_change_breaks_the_exact_predecessor_binding():
    p = packet(); q = successor(p)
    changed = json.dumps(p).encode()
    with pytest.raises(M.RuntimeIndexError, match='digest_mismatch'):
        M.index_runtime_packet_sources([M.RuntimePacketSource('synthetic://changed', changed), source(q)],
            expected_subject=subject(), expected_authority_inputs=authority())


def test_non_null_root_predecessor_fails():
    p = packet(); p['packet_identity']['previous_packet_sha256'] = '0'*64
    with pytest.raises(M.RuntimeIndexError, match='root_predecessor'): index(p)


def test_duplicate_packet_id_fails():
    p = packet(); q = successor(p); q['packet_identity']['packet_id'] = p['packet_identity']['packet_id']
    with pytest.raises(M.RuntimeIndexError, match='duplicate_identity'): index(p, q)


def test_duplicate_sequence_fails():
    p = packet(); q = copy.deepcopy(p); q['packet_identity']['packet_id'] += '-other'
    with pytest.raises(M.RuntimeIndexError, match='duplicate_identity'): index(p, q)


def test_missing_prefix_is_retained_not_repaired():
    p = packet(); p['packet_identity'].update(packet_sequence=4, previous_packet_sha256='0'*64)
    r = index(p)
    assert r['supplied_sequence_status'] == 'incomplete'
    assert r['missing_sequence_ranges'] == [{'first_sequence':0,'last_sequence':3}]
    assert r['terminal_observation_extent'] == 'unknown'


def test_a_huge_gap_is_a_bounded_range_not_a_huge_array():
    p = packet(); p['packet_identity'].update(packet_sequence=10**18, previous_packet_sha256='0'*64)
    r = index(p)
    assert len(r['missing_sequence_ranges']) == 1
    assert len(raw(r)) < 20000


def test_missing_middle_is_retained_as_incomplete():
    p = packet(); q = successor(p, sequence=2); q['packet_identity']['previous_packet_sha256'] = '0'*64
    assert index(p,q)['missing_sequence_ranges'] == [{'first_sequence':1,'last_sequence':1}]


def test_direct_reference_cannot_skip_its_own_predecessor_sequence():
    p = packet(); q = successor(p, sequence=2)
    with pytest.raises(M.RuntimeIndexError, match='contradicts_sequence_gap'): index(p,q)


def test_example_and_observed_inputs_cannot_be_mixed():
    p = packet(); q = successor(p); q['record_status'] = 'observed'
    with pytest.raises(M.RuntimeIndexError, match='mixed_record_status'): index(p,q)


@pytest.mark.parametrize('kind', ['executions','state_observations'])
def test_conflicting_repeated_records_are_not_merged(kind):
    p = packet(); q = successor(p); q[kind][0]['synthetic_conflict'] = True
    with pytest.raises(M.RuntimeIndexError, match='conflicting_repeated'): index(p,q)


def test_duplicate_within_one_packet_fails_even_when_bytes_match():
    p = packet(); p['executions'].append(copy.deepcopy(p['executions'][0]))
    with pytest.raises(M.RuntimeIndexError, match='duplicate_record_within'): index(p)


def test_collector_identity_is_retained_separately():
    r = index()
    assert r['collectors'][0]['collector_run_key'] == 'SYNTHETIC_COLLECTOR=separate'
    assert r['counts']['subject_execution_occurrences'] == 2
    assert r['counts']['observer_execution_occurrences'] == 1


@pytest.mark.parametrize('mutation', ['scope','run_key','mix','total','parent','cycle','self_parent'])
def test_observer_and_parent_controls(mutation):
    p = packet()
    if mutation == 'scope': p['executions'][2]['execution_scope'] = 'subject'
    elif mutation == 'run_key': p['observation_boundary']['collector_run_key'] = 'OTHER'
    elif mutation == 'mix': p['executions'][0]['run_binding']['execution_run_key'] = 'OTHER'
    elif mutation == 'total': p['observation_boundary']['observer_in_subject_totals'] = True
    elif mutation == 'parent': p['executions'][0]['parent_execution_id'] = 'execution:missing'
    elif mutation == 'self_parent': p['executions'][0]['parent_execution_id'] = 'execution:producer'
    elif mutation == 'cycle':
        p['executions'][0]['parent_execution_id'] = 'execution:consumer'
        p['executions'][1]['parent_execution_id'] = 'execution:producer'
    with pytest.raises(M.RuntimeIndexError): index(p)


def test_three_node_parent_cycle_fails():
    p = packet(); p['executions'].append(execution('execution:third'))
    for a,b in [(0,'execution:consumer'),(1,'execution:third'),(3,'execution:producer')]:
        p['executions'][a]['parent_execution_id'] = b
    with pytest.raises(M.RuntimeIndexError, match='parent_cycle'): index(p)


def test_each_required_output_needs_its_own_consumer():
    p = packet(); p['executions'][1]['input_state_ids'] = ['state:a']
    r = consumption(p)
    assert r['status'] == 'unresolved'
    assert r['required_outputs']['state:a']['status'] == 'observed'
    assert r['required_outputs']['state:b']['status'] == 'unresolved'


def test_all_required_outputs_can_be_observed_without_resource_measurement():
    r = consumption()
    assert r['status'] == 'observed'
    assert len(r['required_outputs']) == 2
    assert all(value['source_refs'] for value in r['required_outputs'].values())


def test_only_resource_availability_changes_do_not_change_consumption_outcome():
    p = packet(); q = copy.deepcopy(p)
    q['coverage']['resource_axes_unavailable'] = ['cpu_seconds','gpu_seconds']
    a = consumption(p); b = consumption(q)
    assert a['status'] == b['status'] == 'observed'
    assert a['required_outputs']['state:a']['unresolved_reasons'] == b['required_outputs']['state:a']['unresolved_reasons']
    # Source digests must still change because the exact packet bytes changed.
    assert a['required_outputs']['state:a']['source_refs'] != b['required_outputs']['state:a']['source_refs']


def test_empty_recorded_input_arrays_do_not_prove_no_consumption():
    p = packet(); p['executions'][1]['input_state_ids'] = []
    r = consumption(p)
    assert r['status'] == 'unresolved'
    assert not any(v['status'] in {'none','not_observed'} for v in r['required_outputs'].values())


def test_self_consumption_cannot_satisfy_downstream_consumption():
    p = packet(); p['executions'][0]['input_state_ids'] = ['state:a','state:b']
    p['executions'][1]['input_state_ids'] = []
    assert consumption(p)['status'] == 'unresolved'


def test_observer_reads_do_not_satisfy_subject_consumption():
    p = packet(); p['executions'][2]['input_state_ids'] = ['state:a','state:b']
    p['executions'][1]['input_state_ids'] = []
    assert consumption(p)['status'] == 'unresolved'


@pytest.mark.parametrize('mutation', ['capture','identity','source_digest','state_digest','producer','unknown_content'])
def test_incomplete_production_or_consumption_stays_unresolved(mutation):
    p = packet()
    if mutation == 'capture': p['executions'][1]['capture_status'] = 'partial'
    elif mutation == 'identity': p['executions'][1]['source_identity']['identity_status'] = 'partial'
    elif mutation == 'source_digest': p['executions'][1]['source_identity']['source_sha256'] = None
    elif mutation == 'state_digest': p['state_observations'][1]['sha256'] = None
    elif mutation == 'unknown_content': p['state_observations'][1]['content_status'] = 'metadata_only'
    elif mutation == 'producer': p['state_observations'][1]['producer_execution_id'] = None
    assert consumption(p)['status'] == 'unresolved'


def test_explicit_missing_required_output_is_unresolved_not_absent():
    r = consumption(required=['state:a','state:not-captured'])
    assert r['status'] == 'unresolved'
    assert 'required_state_unavailable' in r['required_outputs']['state:not-captured']['unresolved_reasons']


def test_not_applicable_requires_an_explicit_empty_requirement():
    assert consumption(required=[])['status'] == 'not_applicable'
    p = packet(); p['executions'][0]['output_state_ids'] = []
    for s in p['state_observations']: s['producer_execution_id'] = None
    assert consumption(p)['status'] == 'unresolved'


def test_duplicate_requirements_fail():
    with pytest.raises(M.RuntimeIndexError, match='contains_duplicates'):
        consumption(required=['state:a','state:a'])


def test_missing_producer_fails():
    with pytest.raises(M.RuntimeIndexError, match='producer_missing'):
        M.assess_runtime_output_consumption(index(), producer_execution_id='execution:missing', required_output_state_ids=['state:a'])


def test_observer_cannot_be_the_required_subject_producer():
    with pytest.raises(M.RuntimeIndexError, match='producer_is_observer'):
        M.assess_runtime_output_consumption(index(), producer_execution_id='execution:collector', required_output_state_ids=[])


def test_unintegrated_external_activity_is_not_a_false_complete_consumer():
    p = packet(); p['executions'][1]['input_state_ids'] = []
    p['external_calls'].append({
        'call_id':'call:synthetic','parent_execution_id':'execution:consumer',
        'request':{'payload':{'state_ids':['state:a','state:b']}},
        'response':{'payload':{'state_ids':[]}},
    })
    assert consumption(p)['status'] == 'unresolved'

@pytest.mark.parametrize('field,value', [
    ('outcome','skipped'),('outcome','unknown'),('lifecycle_status','in_progress'),
    ('result_status','partial'),
])
def test_unexecuted_or_incomplete_outcomes_do_not_claim_consumption(field, value):
    p = packet(); p['executions'][1]['result'][field] = value
    assert consumption(p)['status'] == 'unresolved'


def test_recorded_failure_can_still_have_consumed_input_bytes():
    p = packet(); p['executions'][1]['result'].update(outcome='failure', exit_code=1)
    assert consumption(p)['status'] == 'observed'


def test_unknown_command_identity_stays_unresolved():
    p = packet(); p['executions'][1]['command_identity']['command_sha256'] = None
    assert consumption(p)['status'] == 'unresolved'


def test_an_arbitrary_consumer_does_not_replace_a_required_consumer():
    r = M.assess_runtime_output_consumption(index(), producer_execution_id='execution:producer',
        required_output_state_ids=['state:a','state:b'],
        required_consumer_execution_ids={'state:a':['execution:required-not-captured']})
    assert r['status'] == 'unresolved'
    assert r['required_outputs']['state:a']['consumer_execution_ids'] == ['execution:consumer']
    assert r['required_outputs']['state:a']['unresolved_required_consumer_execution_ids'] == ['execution:required-not-captured']


def test_all_required_consumers_must_be_satisfied_not_only_one():
    r = M.assess_runtime_output_consumption(index(), producer_execution_id='execution:producer',
        required_output_state_ids=['state:a'],
        required_consumer_execution_ids={'state:a':['execution:consumer','execution:second-required']})
    assert r['status'] == 'unresolved'


def test_exact_required_consumer_is_supported():
    r = M.assess_runtime_output_consumption(index(), producer_execution_id='execution:producer',
        required_output_state_ids=['state:a'],
        required_consumer_execution_ids={'state:a':['execution:consumer']})
    assert r['status'] == 'observed'


def test_consumer_expectations_cannot_silently_add_untracked_outputs():
    with pytest.raises(M.RuntimeIndexError, match='state_not_required'):
        M.assess_runtime_output_consumption(index(), producer_execution_id='execution:producer',
            required_output_state_ids=['state:a'],
            required_consumer_execution_ids={'state:b':['execution:consumer']})



def test_runtime_full_example_packet_is_valid_and_not_observed():
    c = runtime_test_synthetic_case()
    v = runtime_test_module("check_pulsemech_compute_runtime_observation_packet_v0.py")
    d, rc = v.build_diagnostic(schema_path=ROOT / "schemas/pulsemech_compute_runtime_observation_packet_v0.schema.json",
                               packet_path=runtime_test_view(runtime_test_bytes(c["packets"][0])))
    assert rc == 0 and d["ok"] is True, d
    assert c["packets"][0]["record_status"] == "example"


def test_runtime_authentic_partial_graph_keeps_original_evidence_and_counts():
    c = runtime_test_historical_case()
    before = copy.deepcopy(c)
    r, inputs = runtime_test_report(c)
    index = r["runtime_binding"]["index"]
    assert index["counts"] == {"subject_execution_occurrences":179,"observer_execution_occurrences":1,"unique_state_records":24,"supplied_packet_count":1}
    executions = [entry["record"] for entry in index["records"]["executions"].values()]
    assert sum(e["execution_kind"] == "workflow_job" for e in executions) == 8
    assert sum(e["execution_kind"] == "workflow_step" for e in executions) == 171
    assert sum(e["result"]["outcome"] == "skipped" for e in executions if e["execution_kind"] == "workflow_step") == 44
    assert r["summary"]["subject_compute_nodes"] == 197
    assert r["summary"]["observer_nodes"] == 2
    assert r["runtime_binding"]["coverage"]["extent_status"] == "unknown"
    assert r["runtime_binding"]["coverage"]["relational_coverage_status"] != "complete"
    assert r["runtime_binding"]["index"]["subject_context"]["active_policy_sets"] == ["required","release_required"]
    assert r["resource_summary"]["axes"] == {}
    for key in ("compute_nodes","state_nodes"):
        assert [x for x in r[key] if "runtime_origin" not in x] == c["baseline"][key]
    assert c == before
    assert inputs["packet_sources"][0][1] == c["packet_bytes"][0]


def test_runtime_report_construction_is_byte_deterministic():
    c = runtime_test_synthetic_case()
    a, _ = runtime_test_report(c,extent=True)
    b, _ = runtime_test_report(c,extent=True)
    assert runtime_test_bytes(a) == runtime_test_bytes(b)


@pytest.mark.parametrize("field",["policy_id","policy_sha256","final_status_sha256","release_decision_sha256","decision"])
def test_runtime_baseline_authority_context_cannot_drift(field):
    c = runtime_test_synthetic_case()
    c["baseline"]["subject"][field] = "BLOCK" if field == "decision" else "f"*64
    with pytest.raises((ValueError,RuntimeError)):
        runtime_test_report(c)


def test_runtime_carrier_bytes_are_not_just_a_caller_claim():
    c = runtime_test_synthetic_case();c["carrier_bytes"] += b"tamper"
    with pytest.raises((ValueError,RuntimeError)):
        runtime_test_report(c)


def test_runtime_full_relations_do_not_require_resource_measurements():
    c = runtime_test_synthetic_case()
    r, _ = runtime_test_report(c,extent=True)
    assert r["runtime_binding"]["coverage"]["relational_coverage_status"] == "complete"
    assert r["runtime_binding"]["coverage"]["extent_status"] == "complete"
    assert r["runtime_binding"]["resource_coverage"][0]["coverage"]["coverage_status"] == "partial"
    assert r["runtime_binding"]["resource_coverage"][0]["measurements"] == []
    r_without, _ = runtime_test_report(c)
    assert r_without["runtime_binding"]["coverage"]["extent_status"] == "unknown"
    assert r_without["runtime_binding"]["coverage"]["relational_coverage_status"] != "complete"


@pytest.mark.parametrize("mutation",["input","command","result","digest","consumer","producer"])
def test_runtime_relational_gaps_stay_gaps(mutation):
    c = runtime_test_synthetic_case()
    p = c["packets"][0];rows={x["execution_id"]:x for x in p["executions"]}
    consumer=rows["execution:synthetic-consumer"];producer=rows["execution:synthetic-producer"]
    if mutation == "input": consumer["input_state_ids"]=[]
    elif mutation == "command": consumer["command_identity"]["command_sha256"]=None
    elif mutation == "result": consumer["result"]["outcome"]="skipped"
    elif mutation == "digest": next(x for x in p["state_observations"] if x["state_id"]=="state:synthetic-output")["content_status"]="metadata_only"
    elif mutation == "consumer": c["requirements"]["execution:synthetic-producer"]["required_consumers"]["state:synthetic-output"]=["execution:synthetic-producer"]
    else: next(x for x in p["state_observations"] if x["state_id"]=="state:synthetic-output")["producer_execution_id"]=None
    if mutation == "consumer":
        with pytest.raises(ValueError, match="runtime_extent_consumer_not_in_extent"):
            runtime_test_report(c,extent=True)
    else:
        r,_=runtime_test_report(c,extent=True)
        assert r["runtime_binding"]["coverage"]["relational_coverage_status"] != "complete"


def test_runtime_collector_keeps_its_actual_run_key_and_cannot_consume_for_subject():
    c=runtime_test_synthetic_case();p=c["packets"][0]
    next(x for x in p["executions"] if x["execution_id"]=="execution:synthetic-consumer")["input_state_ids"]=[]
    r,_=runtime_test_report(c,extent=True)
    col=next(x for x in r["compute_nodes"] if x.get("execution_scope")=="observation_collector")
    assert col["run_binding"]["execution_run_key"]=="SYNTHETIC_COLLECTOR=separate"
    assert col["run_binding"]["execution_run_key"]!=r["analysis_boundary"]["analysis_run_key"]
    core=runtime_test_module("pulsemech_compute_binding_analyzer_core_v0.py")
    consumers=core.runtime_consumption_map(r["runtime_binding"]["index"])
    assert consumers.get("state:synthetic-output",[])==[]


def test_runtime_failure_can_be_an_observed_input_consumer():
    c=runtime_test_synthetic_case()
    consumer=next(x for x in c["packets"][0]["executions"] if x["execution_id"]=="execution:synthetic-consumer")
    consumer["result"].update(outcome="failure",exit_code=1)
    r,_=runtime_test_report(c,extent=True)
    assert r["runtime_binding"]["coverage"]["relational_coverage_status"]=="complete"



def test_runtime_full_example_preserves_external_call_model_and_usage_records():
    c=runtime_test_activity_case();r,i=runtime_test_report(c)
    v=runtime_test_module("check_pulsemech_compute_binding_report_v0.py")
    d,rc=v.build_diagnostic(ROOT/"schemas/pulsemech_compute_binding_report_v0.schema.json",runtime_test_view(runtime_test_bytes(r)),runtime_inputs=i)
    assert rc==0,d
    index=r["runtime_binding"]["index"]
    for kind,idkey in (("external_calls","call_id"),("model_inferences","inference_id")):
        assert c["packets"][0][kind]
        for row in c["packets"][0][kind]:
            assert index["records"][kind][row[idkey]]["record"]==row
    assert r["runtime_binding"]["resource_coverage"][0]["measurements"]==c["packets"][0]["resource_measurements"]
    assert r["resource_summary"]==c["baseline"]["resource_summary"]


@pytest.mark.parametrize("kind",["external_calls","model_inferences"])
def test_runtime_activity_consumer_uses_parent_subject_binding(kind):
    # Field-level mutation isolates the activity admission predicate. Complete
    # packet-schema acceptance is tested with the unchanged fixture above.
    c=runtime_test_activity_case();r,_=runtime_test_report(c)
    index=r["runtime_binding"]["index"]
    row=next(iter(index["records"][kind].values()))["record"]
    parent=index["records"]["executions"][row["parent_execution_id"]]["record"]
    parent["execution_scope"]="subject";parent["capture_status"]="complete"
    parent["source_identity"].update(identity_status="exact",source_kind="repository_file",source_revision="a"*40,source_path_or_uri="tools/example.py",source_sha256="1"*64)
    parent["command_identity"].update(command_sha256="2"*64,arguments_sha256="3"*64,command_kind="python_script")
    parent["run_binding"].update(binding_complete=True,binding_mode="current_subject_run",execution_run_key=index["subject_context"]["subject_run_key"])
    parent["result"].update(lifecycle_status="completed",outcome="success",result_status="complete",exit_code=0)
    row["capture_status"]="complete";row["result"].update(lifecycle_status="completed",outcome="failure",result_status="complete",exit_code=1)
    if kind=="external_calls":row["request"]["payload"]["capture_status"]="exact_digest"
    assert M.runtime_activity_is_recorded(index,kind,row) is True
    row["result"]["outcome"]="skipped"
    assert M.runtime_activity_is_recorded(index,kind,row) is False
    row["result"]["outcome"]="failure";parent["execution_scope"]="observation_collector"
    assert M.runtime_activity_is_recorded(index,kind,row) is False


def test_runtime_source_view_does_not_upgrade_provider_revision_to_model_digest():
    c=runtime_test_activity_case();r,_=runtime_test_report(c)
    raw=next(iter(r["runtime_binding"]["index"]["records"]["model_inferences"].values()))["record"]
    raw["model_identity"].update(model_content_digest_status="provider_revision_only",model_sha256=None)
    projection=M.runtime_source_projection("model_inferences",raw)
    assert projection["source_sha256"] is None
    assert projection["source_revision"]==raw["model_identity"]["model_revision"]



@pytest.mark.parametrize("which", ["producer", "consumer"])
def test_review_2872_observed_repository_digest_claim_cannot_qualify_consumption(which):
    p = packet()
    p["record_status"] = "observed"
    row = next(row for row in p["executions"] if row["execution_id"] == "execution:" + which)
    row["source_identity"]["source_sha256"] = "f" * 64
    before = raw(p)
    idx = index(p)
    # Retain the evidence exactly; do not rewrite the original claimed digest.
    assert idx["records"]["executions"][row["execution_id"]]["record"] == row
    result = M.assess_runtime_output_consumption(
        idx, producer_execution_id="execution:producer", required_output_state_ids=["state:a", "state:b"],
    )
    assert result["status"] == "unresolved"
    assert M.runtime_activity_is_recorded(idx, "executions", row) is False
    assert raw(p) == before


def test_review_2872_synthetic_source_claims_remain_example_only():
    idx = index()
    producer = idx["records"]["executions"]["execution:producer"]["record"]
    assert idx["record_status"] == "example"
    assert M.runtime_activity_is_recorded(idx, "executions", producer) is True
    idx["record_status"] = "observed"
    assert M.runtime_activity_is_recorded(idx, "executions", producer) is False




def _bounded_unit_module(filename):
    import importlib.util, sys, hashlib
    path=Path(__file__).resolve().parents[1]/"tools"/filename
    name="_bounded_unit_"+hashlib.sha256(path.read_bytes()).hexdigest()
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module

def test_bounded_exact_source_is_not_a_new_declaration_bypass():
    core=_bounded_unit_module("pulsemech_compute_binding_analyzer_core_v0.py")
    declaration={"source_kind":"repository_file","identity_status":"exact", "source_path_or_uri":"tools/example.py",
        "source_revision":"a"*40,"source_sha256":"b"*64}
    assert core.runtime_effective_source_identity(declaration,record_status="observed")["identity_status"]=="partial"
    assert declaration["identity_status"]=="exact"

def test_bounded_logical_state_identity_is_not_content_identity():
    core=_bounded_unit_module("pulsemech_compute_binding_analyzer_core_v0.py")
    assert core._bounded_state_id("results/allow/checker.stderr")!=core._bounded_state_id("results/block_false/checker.stderr")
    assert core._bounded_state_id("results/allow/checker.stderr",artifact=True)!=core._bounded_state_id("results/allow/checker.stderr")




# Current-run intake: metadata-only unit controls. These small objects are
# not validated subject packets or evidence of a hosted execution.
import ast
import copy
import dataclasses
import io
import zipfile

_INTAKE_CORE = runtime_test_module("pulsemech_compute_binding_analyzer_core_v0.py")

def _intake_function_source(source, name):
    node = next(n for n in ast.parse(source).body
                if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == name)
    return ast.get_source_segment(source, node)

_INTAKE_UNCHANGED_FUNCTION_SHA256 = {'validate_preservation_manifest': '47a185eb72ab160fba94e90a8d7aabd5443a6eff47fa09f732fd66ccd7ee4556', 'validate_package_inventory': '59023a3fe6b389d47e8cbe63983660ef2236949c62ed4b7b80faac0076eabbd4', 'load_observed_bundle': '20992555c8a0547c2009c1a5c4d7dd5b0d7c26365aa4cdc70f9a1741209d8d47', 'index_runtime_packet_sources': 'b0f3a4e7e99c7aa275e8fbb74f16b3b2222f266edb2fe3977fac34747bfd3ca3', 'build_runtime_report': '9b7e7b2e5cb2f75a40448082e0481f2883641abadba545d1545e29ed93bf6bd9', '_bounded_support': '84b0e0a42df315d934d6015ce895715242d538ec63795595cf15a123207d34a3', 'build_bounded_reference_report': 'cfff6acf87500bfb032ef8d81ecbff0ecea7806813a0bc3c46e86b30bdde4b1d'}

def test_intake_artifact_identity_is_immutable():
 with pytest.raises(dataclasses.FrozenInstanceError):_INTAKE_CORE.HISTORICAL_ARTIFACT_IDENTITY.run_id=70000001

@pytest.mark.parametrize('name',['file.json','artifacts/status.json'])
def test_intake_historical_locator_bytes_unchanged(name):
 assert _INTAKE_CORE.package_uri(name)==f'{_INTAKE_CORE.COMPLETE_PACKAGE_NAME}!/{name}'
 assert _INTAKE_CORE.outer_artifact_uri(name)==_INTAKE_CORE.ARCHIVE_DISPLAY_PATH+'!/'+_INTAKE_CORE.ORIGINAL_PREFIX+name

def test_intake_current_locators_retain_exact_carrier_and_nested_package():
 ident=dataclasses.replace(_INTAKE_CORE.HISTORICAL_ARTIFACT_IDENTITY,current_run=True,archive_locator='sha256:'+'b'*64,
     original_prefix='pulsemech-current-run-export-70000001-1-v0/original-github-artifacts/',
     complete_package_name='complete-release-grade-reference-package-70000001-1.zip')
 actual=_INTAKE_CORE.package_uri('artifacts/status.json',identity=ident)
 assert actual=='sha256:'+'b'*64+'!/'+ident.original_prefix+ident.complete_package_name+'!/artifacts/status.json'
 assert '6066' not in actual

@pytest.mark.parametrize('name',['validate_preservation_manifest','validate_package_inventory','load_observed_bundle',
 'index_runtime_packet_sources','build_runtime_report','_bounded_support','build_bounded_reference_report'])
def test_intake_historical_and_runtime_algorithms_are_textually_unchanged(name):
    source = _intake_function_source(CORE.read_text(), name)
    assert hashlib.sha256(source.encode()).hexdigest() == _INTAKE_UNCHANGED_FUNCTION_SHA256[name]

def test_intake_report_uses_bound_identity_without_legacy_constants():
 s=_intake_function_source(CORE.read_text(),'build_report');tree=ast.parse(s)
 forbidden={'EXPECTED_RUN_KEY','EXPECTED_RUN_ID','EXPECTED_RUN_NUMBER','EXPECTED_RUN_ATTEMPT',
 'EXPECTED_REPOSITORY','EXPECTED_SOURCE_COMMIT','EXPECTED_WORKFLOW','EXPECTED_ARTIFACTS','COMPLETE_PACKAGE_NAME',
 'COMPLETENESS_ARCHIVE_NAME','VERIFICATION_ARCHIVE_NAME','PRESERVATION_MANIFEST_DISPLAY_PATH','ARCHIVE_DISPLAY_PATH'}
 assert not {n.id for n in ast.walk(tree) if isinstance(n,ast.Name)}&forbidden
 for n in ast.walk(tree):
  if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in {'package_uri','outer_artifact_uri'}:
   assert any(k.arg=='identity' for k in n.keywords)

def test_intake_fixed_wrapper_still_reexports_single_core():
 wrapper=runtime_test_module("build_pulsemech_compute_binding_report_v0.py")
 assert wrapper.build_report.__module__=='pulsemech_compute_binding_analyzer_core_v0'
 assert wrapper.load_observed_bundle.__module__=='pulsemech_compute_binding_analyzer_core_v0'


# Current-run release-label handoff. These are explicit synthetic contract
# examples; neither the data nor a successful local command is a hosted run.
def _identity_label_example():
    subject = {
        "repository": "example-org/identity-subject", "source_commit": "a" * 40,
        "workflow_name": "PULSE CI", "workflow_path": ".github/workflows/pulse_ci.yml",
        "workflow_run_id": 9001, "workflow_run_number": 9017, "workflow_run_attempt": 1,
        "subject_run_key": "GITHUB_RUN_ID=9001|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI",
        "source_ref": "refs/heads/main", "event_name": "workflow_dispatch",
        "workflow_ref": "example-org/identity-subject/.github/workflows/pulse_ci.yml@refs/heads/main",
        "release_candidate_id": "pulse-ci-current-run:9001:1",
    }
    metadata = {"release_candidate": "main", **{
        target: subject[source] for target, source in {
            "repository": "repository", "git_sha": "source_commit", "run_id": "workflow_run_id",
            "run_attempt": "workflow_run_attempt", "run_key": "subject_run_key", "workflow_ref": "workflow_ref",
        }.items()
    }}
    return subject, metadata


def test_current_run_identity_keeps_main_and_analysis_candidate_distinct():
    subject, metadata = _identity_label_example()
    before = copy.deepcopy((subject, metadata))
    assert _INTAKE_CORE._current_run_packaged_release_label(subject, metadata) == "main"
    assert (subject, metadata) == before
    identity = dataclasses.replace(_INTAKE_CORE.HISTORICAL_ARTIFACT_IDENTITY,
        current_run=True, release_candidate=subject["release_candidate_id"], packaged_release_label="main")
    assert identity.release_candidate == "pulse-ci-current-run:9001:1"
    assert identity.packaged_release_label == "main"
    with pytest.raises(dataclasses.FrozenInstanceError):
        identity.packaged_release_label = identity.release_candidate


@pytest.mark.parametrize("field,value", [
    ("release_candidate_id", "alias"),
    ("release_candidate_id", "pulse-ci-current-run:9002:1"),
    ("release_candidate_id", "pulse-ci-current-run:9001:2"),
    ("workflow_run_id", True), ("workflow_run_id", 0),
    ("workflow_run_attempt", False), ("workflow_run_attempt", -1),
    ("workflow_name", "other"), ("workflow_path", ".github/workflows/other.yml"),
    ("source_ref", "refs/heads/other"), ("event_name", "push"),
    ("subject_run_key", "GITHUB_RUN_ID=9002|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI"),
    ("source_commit", "b" * 40), ("repository", "other/repository"),
    ("workflow_ref", "example-org/identity-subject/.github/workflows/pulse_ci.yml@refs/heads/other"),
])
def test_current_run_identity_rejects_conflicting_subject(field, value):
    subject, metadata = _identity_label_example()
    subject[field] = value
    with pytest.raises(_INTAKE_CORE.BuilderError):
        _INTAKE_CORE._current_run_packaged_release_label(subject, metadata)


@pytest.mark.parametrize("field,value", [
    ("release_candidate", "other"), ("release_candidate", "pulse-ci-current-run:9002:1"),
    ("release_candidate", None), ("repository", "other/repository"),
    ("git_sha", "b" * 40), ("run_id", 9002), ("run_attempt", 2),
    ("run_key", "wrong"), ("workflow_ref", "wrong"),
])
def test_current_run_identity_rejects_conflicting_preserved_metadata(field, value):
    subject, metadata = _identity_label_example()
    metadata[field] = value
    with pytest.raises(_INTAKE_CORE.BuilderError):
        _INTAKE_CORE._current_run_packaged_release_label(subject, metadata)


def test_current_run_identity_preserves_existing_exact_label_inputs():
    subject, metadata = _identity_label_example()
    metadata["release_candidate"] = subject["release_candidate_id"]
    assert _INTAKE_CORE._current_run_packaged_release_label(subject, metadata) == subject["release_candidate_id"]
    assert _INTAKE_CORE.HISTORICAL_ARTIFACT_IDENTITY.release_candidate == "main"
    assert _INTAKE_CORE.HISTORICAL_ARTIFACT_IDENTITY.packaged_release_label is None



# Frozen test-only driver: actual emitted package, expectation, packet, full
# bundle intake, bridge, and report validation. No mocked successful command.
_IDENTITY_EMITTED_HANDOFF_DRIVER = '"""Offline current-run identity candidate integration. All subject data is synthetic.\nRuns actual decision/binding/assembler/verifier/expectation/packet/loader commands.\nNo live API call, no patched validator result, no Step5C acceptance.\n"""\nfrom pathlib import Path\nimport sys, json, hashlib, importlib.util, shutil, inspect, zipfile, io, traceback, subprocess, datetime as dt, os\nW=Path(__file__).resolve().parent; S=Path(sys.argv[1]).resolve(); P=W/\'identity_emitted_handoff\'\nP.mkdir(exist_ok=False)\ndef j(v):return (json.dumps(v,sort_keys=True,indent=2,ensure_ascii=False)+\'\\n\').encode()\ndef dump(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(j(v))\ndef sha(b):return hashlib.sha256(b).hexdigest()\ndef mod(path,name):\n spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m\ndef utc(t):return t.astimezone(dt.timezone.utc).strftime(\'%Y-%m-%dT%H:%M:%SZ\')\ndef zipdata(ms):\n b=io.BytesIO()\n with zipfile.ZipFile(b,\'w\',compression=zipfile.ZIP_DEFLATED) as z:\n  for name,value in sorted(ms.items()):\n   i=zipfile.ZipInfo(name,(2000,1,1,0,0,0));i.create_system=3;i.external_attr=(0o100444<<16);i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,value)\n return b.getvalue()\ncommands=[]\nR=S\n\ndef run(name,args,expected=0):\n d=P/\'commands\'/name;d.mkdir(parents=True,exist_ok=False)\n record={\'argv\':list(map(str,args)),\'cwd\':str(R),\'started_utc\':dt.datetime.now(dt.timezone.utc).isoformat()}\n dump(d/\'command.json\',record)\n env=dict(os.environ)\n for key in (\'PYTHONPATH\',\'PYTHONHOME\',\'PYTEST_ADDOPTS\',\'PYTEST_PLUGINS\',\'GITHUB_SHA\'):env.pop(key,None)\n env.update(PYTHONDONTWRITEBYTECODE=\'1\',GIT_CONFIG_NOSYSTEM=\'1\',GIT_CONFIG_GLOBAL=\'/dev/null\',GIT_TERMINAL_PROMPT=\'0\')\n result=subprocess.run(record[\'argv\'],cwd=R,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=240)\n (d/\'stdout.log\').write_bytes(result.stdout);(d/\'stderr.log\').write_bytes(result.stderr)\n record.update(returncode=result.returncode,finished_utc=dt.datetime.now(dt.timezone.utc).isoformat());dump(d/\'result.json\',record);commands.append(record)\n print(name,result.returncode,flush=True)\n if expected is not None and result.returncode != expected:raise RuntimeError(name+\': \'+result.stderr.decode()[-6000:]+result.stdout.decode()[-1200:])\n return result\n\ndef cli(name,tool,args,expected=0):return run(name,[sys.executable,\'-I\',\'-B\',R/tool,*args],expected)\ntry:\n t=mod(S/\'tests/test_build_pulsemech_compute_binding_report_from_subject_input_v0.py\',\'own_source_bridge_fixture\')\n t._INTAKE_REPOSITORY=\'HKati/pulse-release-gates-0.1\'\n code=inspect.getsource(t._IntakeFixtureHarness)\n repl={\'synthetic-current-run-9001-1\':\'pulse-ci-current-run:9001:1\',"\'artifact_name\': n,":"\'artifact_name\': n[:-4],", "\'exports/current-run-9001-1.zip\'":"\'exports/pulsemech-current-run-export-9001-1-v0.zip\'"}\n for old,new in repl.items():assert code.count(old)==1,(old,code.count(old));code=code.replace(old,new)\n # Add schema-required fields only to the synthetic status input.\n code=code.replace("        status = load(\'artifacts/status.json\')\\n","        status = load(\'artifacts/status.json\')\\n        status.update(version=\'1.0.0\', created_utc=\'2026-09-17T20:00:00Z\')\\n")\n a=code.index("        decision = {\'required_gates_passed\'");b=code.index("        subject[\'release_decision_sha256\']",a)\n code=code[:a]+\'\'\'        generated = self.root / \'actual-generated-authority\'\n        generated.mkdir()\n        (generated/\'status.json\').write_bytes(members[\'artifacts/status.json\'])\n        self.execute(\'real_release_decision\', [sys.executable,\'-I\',\'-B\',self.control/\'PULSE_safe_pack_v0/tools/materialize_release_decision.py\',\n            \'--status\',generated/\'status.json\',\'--policy\',self.control/\'pulse_gate_policy_v0.yml\',\n            \'--target\',\'prod\',\'--status-schema\',self.control/\'schemas/status/status_v1.schema.json\',\n            \'--out\',generated/\'release_decision_v0.json\'])\n        members[\'artifacts/release_decision_v0.json\']=(generated/\'release_decision_v0.json\').read_bytes()\n\'\'\' + code[b:]\n needle="        save(\'artifacts/artifact_provenance_binding_v0.json\', binding)\\n";assert code.count(needle)==1\n code=code.replace(needle,\'\'\'        (generated/\'authority.json\').write_bytes(members[\'artifacts/release_authority_v0.json\'])\n        (generated/\'ledger.html\').write_bytes(members[\'artifacts/report_card.html\'])\n        self.execute(\'real_artifact_binding\', [sys.executable,\'-I\',\'-B\',self.control/\'PULSE_safe_pack_v0/tools/build_artifact_provenance_binding_v0.py\',\n            \'--status\',generated/\'status.json\',\'--policy\',self.control/\'pulse_gate_policy_v0.yml\',\n            \'--ledger\',generated/\'ledger.html\',\'--release-decision\',generated/\'release_decision_v0.json\',\n            \'--release-authority-manifest\',generated/\'authority.json\',\n            \'--policy-set\',\'required\',\'--policy-set\',\'release_required\',\'--out\',generated/\'binding.json\'])\n        members[\'artifacts/artifact_provenance_binding_v0.json\']=(generated/\'binding.json\').read_bytes()\n        binding=json.loads(members[\'artifacts/artifact_provenance_binding_v0.json\'])\n        subject[\'materialized_gate_set_sha256\']=binding[\'authority_carrier\'][\'workflow_effective_required_gate_set\'][\'sha256\']\n\'\'\')\n (P/\'fixture_data_driver.py\').write_text(code)\n exec(compile(code,str(P/\'fixture_data_driver.py\'),\'exec\'),t.__dict__)\n t._INTAKE_BASE=P;t._INTAKE_RAW=P/\'raw-source\'\n shutil.copytree(S,t._INTAKE_RAW,ignore=shutil.ignore_patterns(\'.git\',\'__pycache__\',\'.pytest_cache\'))\n dump(P/\'fixture_status.json\',{\'synthetic_input\':True,\'source_origin\':\'preserved current-run helper + new internal schema-compatible data and real authority tool calls\',\'upstream_head\':\'5f8bd8cdf75894d40e27d38dc8cb1ce4b813eb8e\',\'not_observed_reference\':True,\'helper_embedded_old_provenance_label_not_used\':True})\n h=t._IntakeFixtureHarness();h.build();R=h.control;revision=h.git(R,\'rev-parse\',\'HEAD\');A=P/\'assembly\';A.mkdir()\n dump(P/\'source_identity.json\',{\'local_source_revision\':revision,\'upstream_baseline\':\'5f8bd8cdf75894d40e27d38dc8cb1ce4b813eb8e\',\'candidate_sources\':t._intake_inventory(R),\'not_upstream_checkout\':True})\n old=json.loads((h.root/\'external/expectation.json\').read_bytes());art=h.root/\'package/artifacts\'\n decision=json.loads((art/\'release_decision_v0.json\').read_bytes());epoch=dt.datetime.fromisoformat(decision[\'created_utc\'].replace(\'Z\',\'+00:00\'))\n finalized=utc(epoch+dt.timedelta(minutes=4));created=utc(epoch+dt.timedelta(minutes=2));expires=utc(epoch+dt.timedelta(days=30));expected_time=finalized\n roots={k:A/\'inputs\'/n for k,n in [(\'pulse_report\',\'pulse-report\'),(\'recorded_path\',\'recorded-path\'),(\'audit_bundle\',\'audit-bundle\'),(\'artifact_binding\',\'artifact-binding\')]}\n for root in roots.values():root.mkdir(parents=True)\n assembler=mod(R/\'PULSE_safe_pack_v0/tools/assemble_release_grade_reference_package_v0.py\',\'real_assembler\')\n for key,name,destination in assembler.ARTIFACT_FILES:\n  (roots[key]/name).write_bytes((art/name).read_bytes() if (art/name).is_file() else (art/\'external\'/name).read_bytes())\n shutil.copytree(art/\'recorded_release_candidates\',roots[\'recorded_path\']/\'recorded_release_candidates\')\n for name in (\'status.json\',\'report_card.html\',\'release_authority_v0.json\'):(roots[\'audit_bundle\']/name).write_bytes((art/name).read_bytes())\n common=[\'--repository\',t._INTAKE_REPOSITORY,\'--git-sha\',revision,\'--workflow-ref\',old[\'subject\'][\'workflow_ref\'],\'--run-id\',\'9001\',\'--run-attempt\',\'1\',\'--run-key\',old[\'subject\'][\'subject_run_key\']]\n cli(\'assemble\',\'PULSE_safe_pack_v0/tools/assemble_release_grade_reference_package_v0.py\',[\'--repo-root\',R,\'--out-dir\',A/\'package\',\'--pulse-report-dir\',roots[\'pulse_report\'],\'--recorded-path-dir\',roots[\'recorded_path\'],\'--audit-bundle-dir\',roots[\'audit_bundle\'],\'--artifact-binding-dir\',roots[\'artifact_binding\'],*common,\'--release-candidate\',\'main\',\'--created-utc\',created])\n cli(\'completeness\',\'tools/check_release_grade_package_complete_v1.py\',[\'--package-dir\',A/\'package\',\'--out\',A/\'completeness.json\'])\n cli(\'verification\',\'PULSE_safe_pack_v0/tools/verify_release_grade_reference_package_v0.py\',[\'--repo-root\',R,\'--package-dir\',A/\'package\',\'--out\',A/\'verification.json\',*common])\n # Preserve the original emitted bytes of every authority tool and report.\n package={p.relative_to(A/\'package\').as_posix():p.read_bytes() for p in (A/\'package\').rglob(\'*\') if p.is_file()};assert len(package)==24\n assert package[\'artifacts/release_decision_v0.json\']==(h.root/\'actual-generated-authority/release_decision_v0.json\').read_bytes()\n assert package[\'artifacts/artifact_provenance_binding_v0.json\']==(h.root/\'actual-generated-authority/binding.json\').read_bytes()\n assert json.loads(package[\'run_metadata_v0.json\'])[\'release_candidate\']==\'main\'\n layout=old[\'archive_layout\'];prefix=layout[\'outer_prefix\'];layout[\'expected_non_provider_artifact_count\']=len(package)+5\n providers={layout[\'complete_package_name\']:zipdata(package),layout[\'completeness_archive_name\']:zipdata({\'release_grade_package_completeness_v1.json\':(A/\'completeness.json\').read_bytes()}),layout[\'verification_archive_name\']:zipdata({\'release_grade_reference_package_verification_v0.json\':(A/\'verification.json\').read_bytes()})}\n with zipfile.ZipFile(h.root/\'staging\'/old[\'carrier\'][\'staged_relative_path\']) as z:manifest=json.loads(z.read(prefix+\'PRESERVATION_MANIFEST_v0.json\'))\n manifest[\'retention_risk\']={\'earliest_expiry_utc\':expires,\'original_github_artifacts_expire\':True,\'reason_for_preservation\':\'Explicit offline fixture, no observed run.\'}\n manifest.update(llamaguard_evidence_mode=\'hosted_full_runtime\',release_decision=\'PROD-PASS\',strict_external_evidence=True)\n v=json.loads((A/\'verification.json\').read_bytes());c=json.loads((A/\'completeness.json\').read_bytes())\n manifest[\'local_verification\'].update(complete_package_inventory_errors=[],complete_package_unlisted_members_excluding_inventory=[],independent_verification_errors=v[\'errors\'],independent_verification_status=v[\'status\'],structural_completeness_checks_failed=c[\'summary\'][\'checks_failed\'],structural_completeness_status=c[\'status\'])\n manifest[\'created_utc\']=finalized\n manifest[\'retention_risk\'][\'earliest_expiry_utc\']=expires\n for row in manifest[\'github_artifacts\']:\n  b=providers[row[\'file_name\']];row.update(downloaded_sha256=sha(b),downloaded_size_bytes=len(b),github_sha256=sha(b),size_bytes=len(b),created_at=created,expires_at=expires)\n manifest[\'local_verification\'].update(complete_package_inventory_entries=len(package)-1,complete_package_zip_members=len(package),independent_verification_checks_total=len(json.loads((A/\'verification.json\').read_bytes())[\'checks\']),structural_completeness_checks_total=len(json.loads((A/\'completeness.json\').read_bytes())[\'checks\']))\n visible={\'PRESERVATION_MANIFEST_v0.json\':j(manifest),\'README.md\':b\'Explicitly synthetic current-run identity test, not observed hosted evidence.\\n\',**{\'original-github-artifacts/\'+n:b for n,b in providers.items()}}\n visible[\'SHA256SUMS\']=\'\'.join(f\'{sha(b)}  {n}\\n\' for n,b in sorted(visible.items())).encode()\n folder=P/\'full-intake\';folder.mkdir();staging=P/\'staging\';carrier=staging/old[\'carrier\'][\'staged_relative_path\'];carrier.parent.mkdir(parents=True);carrier.write_bytes(zipdata({prefix+n:b for n,b in visible.items()}));carrier.chmod(0o444)\n cli(\'carrier\',\'tools/load_pulsemech_compute_current_run_export_carrier_v0.py\',[\'--staging-root\',staging,\'--staged-relative-path\',old[\'carrier\'][\'staged_relative_path\'],\'--root-prefix\',prefix,\'--carrier-id-namespace\',\'pulsemech/current-run-export\',\'--workflow-name\',\'PULSE CI\',\'--workflow-run-id\',\'9001\',\'--workflow-run-number\',\'9017\',\'--workflow-run-attempt\',\'1\',\'--subject-run-key\',old[\'subject\'][\'subject_run_key\'],\'--finalized-utc\',finalized,\'--ci-workflow-or-job-identity\',\'offline current-run identity fixture\',\'--control-plane-root\',R,\'--control-plane-revision\',revision,\'--output\',folder/\'carrier.json\'])\n subject=dict(old[\'subject\']);subject.update(release_candidate_id=\'pulse-ci-current-run:9001:1\',final_status_sha256=sha(package[\'artifacts/status.json\']),release_decision_sha256=sha(package[\'artifacts/release_decision_v0.json\']),materialized_gate_set_sha256=json.loads(package[\'artifacts/artifact_provenance_binding_v0.json\'])[\'authority_carrier\'][\'workflow_effective_required_gate_set\'][\'sha256\'])\n profile=dict(old[\'packet_producer_profile\']);profile.update(profile_id=\'pulsemech_current_run_export_candidate_v0\',expected_carrier_id_namespace=\'pulsemech/current-run-export\')\n builder_input={\'subject\':subject,\'authority_sources\':old[\'authority_sources\'],\'archive_layout\':layout,\'carrier\':json.loads((folder/\'carrier.json\').read_bytes()),\'packet_producer_profile\':profile}\n dump(folder/\'builder-input.json\',builder_input)\n args=[\'--input\',folder/\'builder-input.json\',\'--subject-root\',h.subject,\'--subject-repository\',t._INTAKE_REPOSITORY,\'--subject-revision\',revision,\'--workflow-name\',\'PULSE CI\',\'--workflow-path\',\'.github/workflows/pulse_ci.yml\',\'--workflow-run-id\',\'9001\',\'--workflow-run-number\',\'9017\',\'--workflow-run-attempt\',\'1\',\'--source-ref\',\'refs/heads/main\',\'--event-name\',\'workflow_dispatch\',\'--release-candidate-id\',subject[\'release_candidate_id\'],\'--run-mode\',\'prod\',\'--release-target\',\'prod\',\'--active-policy-set\',\'required\',\'--active-policy-set\',\'release_required\',\'--expectation-created-utc\',expected_time,\'--ci-workflow-or-job-identity\',\'offline current-run identity fixture\',\'--control-plane-root\',R,\'--control-plane-repository\',t._INTAKE_REPOSITORY,\'--control-plane-revision\',revision,\'--trusted-git\',\'/usr/bin/git\',\'--final-status\',A/\'package/artifacts/status.json\',\'--release-decision\',A/\'package/artifacts/release_decision_v0.json\',\'--artifact-binding\',A/\'package/artifacts/artifact_provenance_binding_v0.json\',\'--output\',folder/\'expectation.json\']\n cli(\'expectation\',\'tools/build_pulsemech_compute_current_run_export_expectation_v0.py\',args)\n e=json.loads((folder/\'expectation.json\').read_bytes());assert e[\'subject\']==subject\n cli(\'packet\',\'tools/build_pulsemech_compute_subject_input_packet_current_run_v0.py\',[\'--expectation\',folder/\'expectation.json\',\'--expectation-sha256\',sha((folder/\'expectation.json\').read_bytes()),\'--staging-root\',staging,\'--subject-root\',h.subject,\'--subject-repository\',t._INTAKE_REPOSITORY,\'--subject-revision\',revision,\'--control-plane-root\',R,\'--control-plane-repository\',t._INTAKE_REPOSITORY,\'--control-plane-revision\',revision,\'--packet-created-utc\',expected_time,\'--producer-run-key\',subject[\'subject_run_key\'],\'--ci-workflow-or-job-identity\',\'offline current-run identity fixture\',\'--trusted-git\',\'/usr/bin/git\',\'--output\',folder/\'subject-input-packet.json\'])\n cli(\'packet_validator\',\'tools/check_pulsemech_compute_subject_input_packet_v0.py\',[\'--schema\',R/\'schemas/pulsemech_compute_subject_input_packet_v0.schema.json\',\'--packet\',folder/\'subject-input-packet.json\',\'--carrier\',carrier,\'--repository-root\',h.subject])\n dump(P/\'stage1.json\',{\'ok\':True,\'fixture_only\':True,\'expectation_emitted_by_actual_builder\':True,\'packet_equals_expectation\':json.loads((folder/\'subject-input-packet.json\').read_bytes())[\'subject\']==e[\'subject\'],\'packaged_label\':\'main\',\'candidate\':subject[\'release_candidate_id\'],\'gate_digest\':subject[\'materialized_gate_set_sha256\'],\'source_revision\':revision,\'carrier\':str(carrier),\'commands\':commands,\'not_full_reconstruction\':True})\n print(\'STAGE 1 COMPLETE\',flush=True)\n loader=mod(R/\'tools/load_pulsemech_compute_current_run_export_candidate_bundle_v0.py\',\'identity_real_full_loader\')\n resolution={\'authority_boundary\':loader.EXPECTED_SOURCE_RESOLUTION_AUTHORITY,\'control_plane\':{\'repository\':t._INTAKE_REPOSITORY,\'revision\':revision,\'workflow_ref\':f\'{t._INTAKE_REPOSITORY}/{loader.PROVIDER_WORKFLOW_PATH}@refs/heads/main\'},\'document_type\':\'pulsemech_compute_current_run_candidate_source_resolution\',\'schema_version\':\'pulsemech_compute_current_run_candidate_source_resolution_v0\',\'ok\':True,\'source_run\':{\'event\':\'workflow_dispatch\',\'head_branch\':\'main\',\'html_url\':f\'https://github.com/{t._INTAKE_REPOSITORY}/actions/runs/9001\',\'release_candidate_id\':\'pulse-ci-current-run:9001:1\',\'repository\':t._INTAKE_REPOSITORY,\'run_attempt\':1,\'run_id\':9001,\'run_key\':e[\'subject\'][\'subject_run_key\'],\'run_number\':9017,\'source_ref\':\'refs/heads/main\',\'subject_revision\':revision,\'updated_utc\':finalized,\'workflow_name\':\'PULSE CI\',\'workflow_path\':loader.SOURCE_WORKFLOW_PATH}}\n dump(folder/\'source-run-resolution.json\',resolution)\n selection=[]\n for key in sorted(loader.SOURCE_ARTIFACT_ROLES):\n  name=f\'{loader.SOURCE_ARTIFACT_NAME_PREFIXES[key]}-9001-1\';row=next(r for r in manifest[\'github_artifacts\'] if r[\'artifact_name\']==name)\n  selection.append({\'key\':key,\'role\':loader.SOURCE_ARTIFACT_ROLES[key],\'artifact_id\':row[\'artifact_id\'],\'artifact_name\':name,\'created_at\':row[\'created_at\'],\'expires_at\':row[\'expires_at\'],\'download_file_name\':name+\'.zip\',\'expected_sha256\':row[\'downloaded_sha256\'],\'expected_size_bytes\':row[\'downloaded_size_bytes\']})\n dump(folder/\'source-artifact-selection.json\',{\'authority_boundary\':loader.EXPECTED_SELECTION_AUTHORITY,\'document_type\':\'pulsemech_compute_current_run_candidate_artifact_selection\',\'schema_version\':\'pulsemech_compute_current_run_candidate_artifact_selection_v0\',\'ok\':True,\'source_run_attempt\':1,\'source_run_id\':9001,\'artifacts\':selection})\n files={n:(folder/n).read_bytes() for n in [\'carrier.json\',\'expectation.json\',\'subject-input-packet.json\',\'source-run-resolution.json\',\'source-artifact-selection.json\']};files[carrier.name]=carrier.read_bytes()\n cm={\'authority_boundary\':loader.EXPECTED_MANIFEST_AUTHORITY,\'control_plane_revision\':revision,\'document_type\':\'pulsemech_compute_current_run_export_candidate_output_manifest\',\'schema_version\':\'pulsemech_compute_current_run_export_candidate_output_manifest_v0\',\'file_count\':len(files),\'files\':[{\'path\':n,\'sha256\':sha(raw),\'size_bytes\':len(raw)} for n,raw in sorted(files.items())],\'manifest_scope\':\'all_candidate_files_except_this_manifest\',\'ok\':True,\'source_run_attempt\':1,\'source_run_id\':9001,\'subject_revision\':revision}\n files[\'candidate-output-manifest.json\']=j(cm);envelope=zipdata(files);envpath=folder/\'step3f-envelope.zip\';envpath.write_bytes(envelope);envpath.chmod(0o444)\n checker=mod(R/\'tools/check_pulsemech_compute_whole_runtime_observation_v0.py\',\'identity_actual_step5c_checker\')\n capture={\'subject\':{\'run_id\':9001},\'provider\':{\'run_id\':9002,\'run_number\':9018,\'updated_at\':utc(epoch+dt.timedelta(minutes=7))},\'capture_identity\':{\'collector_run_key\':\'GITHUB_RUN_ID=9003|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSEmech compute whole-runtime observation reference\'},\'artifact_bindings\':[{\'artifact_role\':\'step3f_candidate_envelope\',\'artifact_id\':10004,\'artifact_name\':\'pulsemech-compute-current-run-export-candidate-9001-1\',\'created_utc\':utc(epoch+dt.timedelta(minutes=6)),\'expires_utc\':expires,\'github_sha256\':sha(envelope),\'size_bytes\':len(envelope)}]}\n dump(folder/\'minimal_capture_context.json\',capture)\n original=checker.run_process\n def record(command,**kwargs):\n  name=\'connected_\'+str(len(commands));d=P/\'commands\'/name;d.mkdir(parents=True)\n  meta={\'argv\':list(map(str,command)),\'cwd\':str(kwargs.get(\'cwd\')),\'source_revision\':revision,\'started_utc\':dt.datetime.now(dt.timezone.utc).isoformat()};dump(d/\'command.json\',meta)\n  result=original(command,**kwargs);(d/\'stdout.log\').write_bytes(result.stdout);(d/\'stderr.log\').write_bytes(result.stderr);meta.update(returncode=result.returncode,finished_utc=dt.datetime.now(dt.timezone.utc).isoformat());dump(d/\'result.json\',meta);commands.append(meta);print(name,result.returncode,flush=True);return result\n checker.run_process=record\n checker._load_step3f_intake(control_root=R,capture_manifest=capture,envelope_path=envpath,output_directory=folder/\'intake\',source_commit=revision)\n dump(P/\'stage2.json\',{\'full_candidate_bundle_loader_completed\':True,\'fixture_only\':True,\'not_full_step5c_reconstruction\':True,\'source_revision\':revision,\'original_expectation_packet_report_bytes\':True,\'commands\':commands})\n print(\'FULL BUNDLE LOADER COMPLETE\',flush=True)\n # The next orchestration comparison is a separate obligation; this control\n # proves the original bundle intake and actual bridge/report-validator path.\n result=cli(\'bridge\',\'tools/build_pulsemech_compute_binding_report_from_subject_input_v0.py\',\n   [\'--packet\',folder/\'intake/subject-input-packet.json\',\'--carrier\',folder/\'intake\'/carrier.name,\n    \'--repository-root\',h.subject,\'--analysis-run-key\',\'analysis:step5c:9001:1:artifact-baseline\'])\n (folder/\'bridge-report.json\').write_bytes(result.stdout)\n cli(\'report_validator\',\'tools/check_pulsemech_compute_binding_report_v0.py\',\n   [\'--schema\',R/\'schemas/pulsemech_compute_binding_report_v0.schema.json\',\'--report\',folder/\'bridge-report.json\'])\n assert carrier.read_bytes()==(folder/\'intake\'/carrier.name).read_bytes()\n dump(P/\'SUCCESS.json\',{\'synthetic_only\':True,\'full_step5c_reconstruction\':False,\n     \'commands\':commands,\'source_revision\':revision,\'package_label\':\'main\',\n     \'analysis_candidate\':\'pulse-ci-current-run:9001:1\'})\nexcept Exception:\n (P/\'error.txt\').write_text(traceback.format_exc());print(traceback.format_exc(),flush=True);sys.exit(1)\n'

@pytest.fixture(scope="module")
def identity_emitted_handoff(tmp_path_factory):
    work = tmp_path_factory.mktemp("current-run-identity-handoff")
    driver = work / "run_identity_handoff.py"
    driver.write_text(_IDENTITY_EMITTED_HANDOFF_DRIVER, encoding="utf-8")
    command = [sys.executable, "-I", "-B", str(driver), str(ROOT)]
    (work / "command.json").write_text(json.dumps(command, indent=2) + "\n")
    with (work / "stdout.log").open("wb") as out, (work / "stderr.log").open("wb") as err:
        result = subprocess.run(command, cwd=work, stdin=subprocess.DEVNULL,
                                stdout=out, stderr=err, timeout=240, check=False)
    (work / "exit_code.txt").write_text(str(result.returncode) + "\n")
    assert result.returncode == 0, (work / "stdout.log").read_text()[-12000:] + (work / "stderr.log").read_text()
    return work / "identity_emitted_handoff"


def test_current_run_identity_emitted_package_is_not_relabelled(identity_emitted_handoff):
    p = identity_emitted_handoff
    metadata_bytes = (p / "assembly/package/run_metadata_v0.json").read_bytes()
    assert json.loads(metadata_bytes)["release_candidate"] == "main"
    packet = json.loads((p / "full-intake/subject-input-packet.json").read_bytes())
    expectation = json.loads((p / "full-intake/expectation.json").read_bytes())
    report = json.loads((p / "full-intake/bridge-report.json").read_bytes())
    assert packet["subject"] == expectation["subject"]
    assert packet["subject"]["release_candidate_id"] == "pulse-ci-current-run:9001:1"
    assert report["subject"]["release_candidate_id"] == packet["subject"]["release_candidate_id"]
    assert report["state_nodes"]
    assert {row["release_candidate_id"] for row in report["state_nodes"]} == {"pulse-ci-current-run:9001:1"}
    carrier_path = p / "full-intake/intake/pulsemech-current-run-export-9001-1-v0.zip"
    with zipfile.ZipFile(carrier_path) as carrier:
        payload = carrier.read("pulsemech-current-run-export-9001-1-v0/original-github-artifacts/complete-release-grade-reference-package-9001-1.zip")
    with zipfile.ZipFile(io.BytesIO(payload)) as package:
        assert package.read("run_metadata_v0.json") == metadata_bytes


def test_current_run_identity_emitted_inline_digest_is_same_exact_object(identity_emitted_handoff):
    p = identity_emitted_handoff
    binding = json.loads((p / "assembly/package/artifacts/artifact_provenance_binding_v0.json").read_bytes())
    gate_set = copy.deepcopy(binding["authority_carrier"]["workflow_effective_required_gate_set"])
    recorded = gate_set.pop("sha256")
    expected = hashlib.sha256(json.dumps(gate_set, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    assert recorded == expected
    for name in ("expectation.json", "subject-input-packet.json", "bridge-report.json"):
        assert json.loads((p / "full-intake" / name).read_bytes())["subject"]["materialized_gate_set_sha256"] == recorded
    emitted = (p / "assembly/verification.json").read_bytes()
    carrier_path = p / "full-intake/intake/pulsemech-current-run-export-9001-1-v0.zip"
    with zipfile.ZipFile(carrier_path) as carrier:
        payload = carrier.read("pulsemech-current-run-export-9001-1-v0/original-github-artifacts/release-grade-reference-package-verification-9001-1.zip")
    with zipfile.ZipFile(io.BytesIO(payload)) as verification:
        assert verification.read("release_grade_reference_package_verification_v0.json") == emitted


def test_current_run_identity_emitted_chain_has_real_successful_commands(identity_emitted_handoff):
    record = json.loads((identity_emitted_handoff / "SUCCESS.json").read_bytes())
    assert record["synthetic_only"] is True and record["full_step5c_reconstruction"] is False
    commands = record["commands"]
    assert len(commands) >= 10 and all(item["returncode"] == 0 for item in commands)
    assert any("load_pulsemech_compute_current_run_export_candidate_bundle_v0.py" in item["argv"][3] for item in commands)
    assert any("check_pulsemech_compute_binding_report_v0.py" in item["argv"][3] for item in commands)


if __name__ == "__main__":
    check_pulsemech_compute_binding_analyzer_core_v0()

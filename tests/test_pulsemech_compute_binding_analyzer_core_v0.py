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


if __name__ == "__main__":
    check_pulsemech_compute_binding_analyzer_core_v0()

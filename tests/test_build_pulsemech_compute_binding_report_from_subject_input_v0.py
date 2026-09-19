#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
import os
import shutil
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
ADAPTER = (
    ROOT
    / "tools"
    / "build_pulsemech_compute_binding_report_from_subject_input_v0.py"
)
FIXED_BUILDER = ROOT / "tools" / "build_pulsemech_compute_binding_report_v0.py"
ANALYZER_CORE = ROOT / "tools" / "pulsemech_compute_binding_analyzer_core_v0.py"
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
PACKET_SCHEMA = ROOT / "schemas" / "pulsemech_compute_subject_input_packet_v0.schema.json"
PACKET_VALIDATOR = ROOT / "tools" / "check_pulsemech_compute_subject_input_packet_v0.py"
TOOLS_TESTS = ROOT / "ci" / "tools-tests.list"

ANALYSIS_RUN_KEY = (
    "OFFLINE_ANALYSIS=pulsemech-compute-binding-fixed-source-6066-v0"
)
CI_ENTRY = (
    "tests/"
    "test_build_pulsemech_compute_binding_report_from_subject_input_v0.py"
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


def render_json(value: dict[str, Any]) -> str:
    return (
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    )


def load_source_module(path: Path, module_name: str) -> Any:
    source = path.read_bytes()
    code = compile(source, str(path), "exec", dont_inherit=True)
    module = types.ModuleType(module_name)
    module.__file__ = str(path)
    module.__cached__ = None
    module.__loader__ = None
    module.__package__ = ""
    module.__spec__ = None
    sys.modules[module_name] = module
    exec(code, module.__dict__)
    return module


ADAPTER_MODULE = load_source_module(
    ADAPTER,
    "pulsemech_subject_input_report_bridge_v0_under_test",
)

PACKET_VALIDATOR_BRIDGE_MODULE = (
    "pulsemech_subject_input_packet_validator_v0_for_bridge"
)


def _regression_validate_git_executable(module: Any, candidate: Path) -> Path:
    """Preserve executable/path trust while neutralizing host UID remapping.

    The production validator requires every POSIX path component to be owned by
    UID 0. Some hosted runners expose immutable system paths through a remapped
    owner even though the path is absolute, non-symlinked, non-writable, and
    executable. This regression-only validator omits only the UID-0 condition.
    It preserves all structural, executable, alias, symlink, and writable-path
    checks before allowing the real Git subprocess and provenance replay.
    """

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
    original_loader = ADAPTER_MODULE.load_module_from_capture

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

    ADAPTER_MODULE.load_module_from_capture = load_with_regression_git_binding
    try:
        yield
    finally:
        ADAPTER_MODULE.load_module_from_capture = original_loader


def build_adapter_from_captures(
    *,
    packet_capture: Any,
    carrier_capture: Any,
    repository_root: Path = ROOT,
    analysis_run_key: str = ANALYSIS_RUN_KEY,
) -> str:
    dependencies = ADAPTER_MODULE._capture_dependencies()
    with _regression_git_binding():
        return ADAPTER_MODULE.build_from_captured_inputs(
            packet_capture=packet_capture,
            carrier_capture=carrier_capture,
            repository_root=repository_root,
            analysis_run_key=analysis_run_key,
            dependency_captures=dependencies,
        )


def build_adapter_in_process(
    *,
    packet: Path = PACKET,
    carrier: Path = CARRIER,
    repository_root: Path = ROOT,
    analysis_run_key: str = ANALYSIS_RUN_KEY,
) -> str:
    return build_adapter_from_captures(
        packet_capture=ADAPTER_MODULE.capture_regular_file(
            packet,
            label="packet",
        ),
        carrier_capture=ADAPTER_MODULE.capture_regular_file(
            carrier,
            label="carrier",
        ),
        repository_root=repository_root,
        analysis_run_key=analysis_run_key,
    )


def assert_cli_matches_or_fails_at_git_trust_boundary(
    result: subprocess.CompletedProcess[str],
    *,
    expected_stdout: str,
) -> None:
    if result.returncode == 0:
        assert result.stderr == ""
        assert result.stdout == expected_stdout
        return

    diagnostic = assert_adapter_failure(
        result,
        "git_process_executable_",
    )
    error_text = "\n".join(str(item) for item in diagnostic["errors"])
    assert (
        "git_process_executable_untrusted" in error_text
        or "git_process_executable_unavailable" in error_text
    )


def run_fixed_builder() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(FIXED_BUILDER),
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


def run_adapter(
    *,
    packet: Path = PACKET,
    carrier: Path = CARRIER,
    repository_root: Path = ROOT,
    analysis_run_key: str = ANALYSIS_RUN_KEY,
    cwd: Path = ROOT,
    relative: bool = False,
) -> subprocess.CompletedProcess[str]:
    def argument(path: Path) -> str:
        return os.path.relpath(path, cwd) if relative else str(path)

    return subprocess.run(
        [
            sys.executable,
            str(ADAPTER),
            "--packet",
            argument(packet),
            "--carrier",
            argument(carrier),
            "--repository-root",
            argument(repository_root),
            "--analysis-run-key",
            analysis_run_key,
        ],
        cwd=cwd,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def assert_adapter_failure(
    result: subprocess.CompletedProcess[str],
    expected_fragment: str,
    *,
    expected_returncode: int = 1,
) -> dict[str, Any]:
    assert result.returncode == expected_returncode, result.stdout + result.stderr
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    diagnostic = strict_json_text(result.stderr, label="adapter diagnostic")
    assert (
        diagnostic["tool"]
        == "build_pulsemech_compute_binding_report_from_subject_input_v0"
    )
    assert diagnostic["ok"] is False
    assert any(
        expected_fragment in str(error)
        for error in diagnostic["errors"]
    ), diagnostic
    return diagnostic


def snapshot_repository_tree() -> tuple[tuple[str, str, int, str | None], ...]:
    records: list[tuple[str, str, int, str | None]] = []
    for path in sorted(ROOT.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(ROOT).as_posix()
        if relative == ".git" or relative.startswith(".git/"):
            continue
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


@pytest.fixture(scope="module")
def fixed_stdout() -> str:
    result = run_fixed_builder()
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    strict_json_text(result.stdout, label="fixed-source report")
    return result.stdout


def test_bridge_matches_fixed_builder_byte_for_byte(fixed_stdout: str) -> None:
    rendered = build_adapter_in_process()
    assert rendered == fixed_stdout

    report = strict_json_text(rendered, label="bridge report")
    assert report["tool"]["id"] == "build_pulsemech_compute_binding_report_v0"
    assert report["tool"]["source_sha256"] == sha256_file(FIXED_BUILDER)
    observer = next(
        node
        for node in report["compute_nodes"]
        if node["node_id"] == "compute:offline-observer"
    )
    assert observer["source_identity"]["source_path_or_uri"] == (
        "tools/pulsemech_compute_binding_analyzer_core_v0.py"
    )
    assert observer["source_identity"]["source_sha256"] == sha256_file(
        ANALYZER_CORE
    )
    assert report["analysis_boundary"]["analysis_run_key"] == ANALYSIS_RUN_KEY
    assert report["subject"]["workflow_run_number"] == 6066
    assert report["subject"]["decision"] == "ALLOW"
    assert report["ok"] is True
    assert report["errors"] == []


def test_production_cli_matches_or_fails_closed_at_git_trust_boundary(
    fixed_stdout: str,
) -> None:
    assert_cli_matches_or_fails_at_git_trust_boundary(
        run_adapter(),
        expected_stdout=fixed_stdout,
    )


def test_bridge_is_repeat_deterministic(fixed_stdout: str) -> None:
    first = build_adapter_in_process()
    second = build_adapter_in_process()
    assert first == second == fixed_stdout


def test_bridge_writes_no_repository_entry(fixed_stdout: str) -> None:
    before = snapshot_repository_tree()
    rendered = build_adapter_in_process()
    after = snapshot_repository_tree()
    assert rendered == fixed_stdout
    assert before == after


def test_relative_cli_paths_work_or_reach_git_trust_boundary(
    tmp_path: Path,
    fixed_stdout: str,
) -> None:
    packet = tmp_path / "packet.json"
    carrier = tmp_path / "carrier.zip"
    shutil.copy2(PACKET, packet)
    shutil.copy2(CARRIER, carrier)

    result = run_adapter(
        packet=packet,
        carrier=carrier,
        repository_root=ROOT,
        cwd=tmp_path,
        relative=True,
    )
    assert_cli_matches_or_fails_at_git_trust_boundary(
        result,
        expected_stdout=fixed_stdout,
    )


def test_invalid_role_binding_is_rejected(tmp_path: Path) -> None:
    packet = strict_json_text(PACKET.read_text(encoding="utf-8"), label="packet")
    packet["role_bindings"]["final_status"] = "artifact:missing"
    changed = tmp_path / "packet.json"
    changed.write_text(render_json(packet), encoding="utf-8", newline="\n")

    with pytest.raises(
        ADAPTER_MODULE.AdapterError,
        match="subject_input_packet_rejected",
    ):
        build_adapter_in_process(packet=changed)


def test_non_observed_packet_is_rejected(tmp_path: Path) -> None:
    packet = strict_json_text(PACKET.read_text(encoding="utf-8"), label="packet")
    packet["record_status"] = "example"
    changed = tmp_path / "packet.json"
    changed.write_text(render_json(packet), encoding="utf-8", newline="\n")

    with pytest.raises(
        ADAPTER_MODULE.AdapterError,
        match="subject_input_packet_not_observed",
    ):
        build_adapter_in_process(packet=changed)


def test_carrier_drift_is_rejected(tmp_path: Path) -> None:
    changed = tmp_path / "carrier.zip"
    shutil.copy2(CARRIER, changed)
    payload = bytearray(changed.read_bytes())
    payload[-1] ^= 0x01
    changed.write_bytes(payload)

    with pytest.raises(
        ADAPTER_MODULE.AdapterError,
        match="subject_input_packet_rejected",
    ):
        build_adapter_in_process(carrier=changed)


def test_subject_run_cannot_be_analysis_run() -> None:
    packet = strict_json_text(PACKET.read_text(encoding="utf-8"), label="packet")
    with pytest.raises(
        ADAPTER_MODULE.AdapterError,
        match="analysis_run_key_invalid_or_matches_subject",
    ):
        build_adapter_in_process(
            analysis_run_key=packet["subject"]["subject_run_key"],
        )


def test_valid_packet_capture_is_used_after_path_replacement(
    tmp_path: Path,
    fixed_stdout: str,
) -> None:
    packet_path = tmp_path / "packet.json"
    shutil.copy2(PACKET, packet_path)
    captured_packet = ADAPTER_MODULE.capture_regular_file(
        packet_path,
        label="packet",
    )
    packet_path.write_text("{\"invalid\":true}\n", encoding="utf-8")
    captured_carrier = ADAPTER_MODULE.capture_regular_file(
        CARRIER,
        label="carrier",
    )

    rendered = build_adapter_from_captures(
        packet_capture=captured_packet,
        carrier_capture=captured_carrier,
    )
    assert rendered == fixed_stdout


def test_invalid_packet_capture_cannot_borrow_later_valid_path(
    tmp_path: Path,
) -> None:
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(
        render_json(
            {
                "record_status": "observed",
                "analysis_boundary": {"target_analysis_level": "artifact_observed"},
            }
        ),
        encoding="utf-8",
        newline="\n",
    )
    captured_packet = ADAPTER_MODULE.capture_regular_file(
        packet_path,
        label="packet",
    )
    shutil.copy2(PACKET, packet_path)
    captured_carrier = ADAPTER_MODULE.capture_regular_file(
        CARRIER,
        label="carrier",
    )

    with pytest.raises(
        ADAPTER_MODULE.AdapterError,
        match="subject_input_packet_rejected",
    ):
        build_adapter_from_captures(
            packet_capture=captured_packet,
            carrier_capture=captured_carrier,
        )


def test_valid_carrier_capture_is_used_after_path_replacement(
    tmp_path: Path,
    fixed_stdout: str,
) -> None:
    carrier_path = tmp_path / "carrier.zip"
    shutil.copy2(CARRIER, carrier_path)
    captured_carrier = ADAPTER_MODULE.capture_regular_file(
        carrier_path,
        label="carrier",
    )
    carrier_path.write_bytes(b"not-a-zip")
    captured_packet = ADAPTER_MODULE.capture_regular_file(
        PACKET,
        label="packet",
    )

    rendered = build_adapter_from_captures(
        packet_capture=captured_packet,
        carrier_capture=captured_carrier,
    )
    assert rendered == fixed_stdout


def test_invalid_carrier_capture_cannot_borrow_later_valid_path(
    tmp_path: Path,
) -> None:
    carrier_path = tmp_path / "carrier.zip"
    carrier_path.write_bytes(b"not-a-zip")
    captured_carrier = ADAPTER_MODULE.capture_regular_file(
        carrier_path,
        label="carrier",
    )
    shutil.copy2(CARRIER, carrier_path)
    captured_packet = ADAPTER_MODULE.capture_regular_file(
        PACKET,
        label="packet",
    )

    with pytest.raises(
        ADAPTER_MODULE.AdapterError,
        match="subject_input_packet_rejected",
    ):
        build_adapter_from_captures(
            packet_capture=captured_packet,
            carrier_capture=captured_carrier,
        )


def test_source_loading_ignores_and_does_not_create_bytecode(tmp_path: Path) -> None:
    source = tmp_path / "module.py"
    source.write_text("VALUE = 7\n", encoding="utf-8", newline="\n")
    capture = ADAPTER_MODULE.capture_regular_file(source, label="source")
    module = ADAPTER_MODULE.load_module_from_capture(
        capture,
        "synthetic_bridge_source_module",
    )
    view = ADAPTER_MODULE.CapturedPathView(capture)
    assert not hasattr(view, "__fspath__")
    assert module.VALUE == 7
    assert not (tmp_path / "__pycache__").exists()


def test_bridge_has_no_scratch_or_file_output_surface() -> None:
    source = ADAPTER.read_text(encoding="utf-8")
    forbidden = (
        "import tempfile",
        "TemporaryDirectory",
        "gettempdir",
        "mkstemp",
        "--temp-root",
        "--output",
        "write_atomic_text",
        "os.rename(",
        "os.replace(",
    )
    for fragment in forbidden:
        assert fragment not in source


def test_bridge_delegates_to_reusable_analyzer_core() -> None:
    source = ADAPTER.read_text(encoding="utf-8")
    assert "packet_validator.build_diagnostic(" in source
    assert "analyzer_core.load_observed_bundle(" in source
    assert "report_validator.build_diagnostic(" in source
    assert "analyzer_core.build_report(" in source
    assert "captures[\"fixed_builder\"].sha256" in source
    assert "captures[\"analyzer_core\"].sha256" in source
    assert "def build_report(" not in source
    assert "def make_compute_node(" not in source
    assert "def make_state_node(" not in source
    assert "def make_edge(" not in source


def test_cli_is_stdout_only() -> None:
    result = subprocess.run(
        [sys.executable, str(ADAPTER), "--help"],
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    assert "--packet" in result.stdout
    assert "--carrier" in result.stdout
    assert "--repository-root" in result.stdout
    assert "--analysis-run-key" in result.stdout
    assert "--output" not in result.stdout
    assert "--temp-root" not in result.stdout


def test_bridge_is_registered_exactly_once_in_tools_tests() -> None:
    entries = [
        line.strip()
        for line in TOOLS_TESTS.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert entries.count(CI_ENTRY) == 1


# ---------------------------------------------------------------------------
# Direct tools-tests execution entrypoint
# ---------------------------------------------------------------------------


def check_build_pulsemech_compute_binding_report_from_subject_input_v0() -> None:
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



# Shared full-schema runtime examples live in an already registered regression.
def _runtime_test_support():
    import importlib.util
    import hashlib
    import sys
    path = Path(__file__).with_name("test_pulsemech_compute_binding_analyzer_core_v0.py")
    name = "pulse_runtime_regression_support_" + hashlib.sha256(path.read_bytes()).hexdigest()
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def test_runtime_bridge_cli_exposes_optional_runtime_inputs_only():
    m=_runtime_test_support()
    result=subprocess.run([sys.executable,str(m.SUBJECT_BRIDGE),"--help"],capture_output=True,text=True,check=False)
    assert result.returncode==0
    assert "--runtime-packet" in result.stdout and "--runtime-extent" in result.stdout
    assert "--packet" in result.stdout and "--carrier" in result.stdout


def test_runtime_bridge_capture_limits_and_same_buffer_semantics(tmp_path):
    m=_runtime_test_support();bridge=m.runtime_test_module("build_pulsemech_compute_binding_report_from_subject_input_v0.py")
    f=tmp_path/"packet.json";f.write_bytes(b"{}")
    cap=bridge.capture_regular_file(f,label="fixture",max_bytes=2)
    f.write_bytes(b"wrong")
    assert cap.data==b"{}" and cap.sha256==m.sha256_bytes(b"{}")
    with pytest.raises(bridge.AdapterError):bridge.capture_regular_file(f,label="fixture",max_bytes=2)


def test_runtime_bridge_runtime_dependencies_are_not_loaded_in_artifact_capture():
    m=_runtime_test_support();bridge=m.runtime_test_module("build_pulsemech_compute_binding_report_from_subject_input_v0.py")
    keys=set(bridge._capture_dependencies())
    assert keys=={"packet_schema","packet_validator","report_schema","report_validator","fixed_builder","analyzer_core"}


def test_runtime_bridge_rejects_missing_subject_before_writing_stdout(tmp_path):
    m=_runtime_test_support()
    r=subprocess.run([sys.executable,str(m.SUBJECT_BRIDGE),"--packet",str(tmp_path/"missing.json"),"--runtime-packet",str(tmp_path/"also-missing.json")],capture_output=True,text=True,check=False)
    assert r.returncode!=0 and r.stdout==""
    assert json.loads(r.stderr)["ok"] is False




def _bounded_unit_module(filename):
    import importlib.util, sys, hashlib
    path=Path(__file__).resolve().parents[1]/"tools"/filename
    name="_bounded_unit_"+hashlib.sha256(path.read_bytes()).hexdigest()
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module

def test_bounded_bridge_requires_independent_context_before_processing():
    import pytest
    bridge=_bounded_unit_module("build_pulsemech_compute_binding_report_from_subject_input_v0.py")
    raw=b'{"input_profile":"bounded_execution_reference_v0"}'
    cap=bridge.CapturedFile(path=Path("input.json"),data=raw,device=0,inode=0,size_bytes=len(raw),sha256=bridge.sha256_bytes(raw))
    with pytest.raises(bridge.AdapterError,match="bounded_expected_context"):
        bridge.build_from_captured_inputs(packet_capture=cap,carrier_capture=cap,repository_root=bridge.ROOT,analysis_run_key="example")

def test_bounded_bridge_rejects_legacy_dependency_injection():
    import pytest
    bridge=_bounded_unit_module("build_pulsemech_compute_binding_report_from_subject_input_v0.py")
    raw=b'{"input_profile":"bounded_execution_reference_v0"}'
    cap=bridge.CapturedFile(path=Path("input.json"),data=raw,device=0,inode=0,size_bytes=len(raw),sha256=bridge.sha256_bytes(raw))
    with pytest.raises(bridge.AdapterError,match="dependency_override"):
        bridge.build_from_captured_inputs(packet_capture=cap,carrier_capture=cap,repository_root=bridge.ROOT,analysis_run_key="example",
            bounded_expected_context={},bounded_prelaunch_sha256="a"*64,dependency_captures={})




# Current-run intake: metadata-only unit controls. These small objects are
# not validated subject packets or evidence of a hosted execution.
import ast
import copy
import dataclasses
import io
import zipfile

_INTAKE_CORE = _runtime_test_support().runtime_test_module("pulsemech_compute_binding_analyzer_core_v0.py")
_INTAKE_BRIDGE = ADAPTER_MODULE
_INTAKE_LOADER = _runtime_test_support().runtime_test_module("build_pulsemech_compute_subject_input_packet_current_run_v0.py")
def _intake_partial_metadata(raw=b'not a validated carrier', *, run=70000001, number=7001, attempt=1):
 key=f'GITHUB_RUN_ID={run}|GITHUB_RUN_ATTEMPT={attempt}|GITHUB_WORKFLOW=PULSE CI'
 cap=_INTAKE_BRIDGE.CapturedFile(Path('/in-memory/unvalidated-unit-fixture.zip'),raw,0,0,len(raw),hashlib.sha256(raw).hexdigest())
 p={'packet_identity':{'packet_scope':'current_run','subject_run_key':key,'carrier_id':'carrier:unit/x/v0'},
 'producer':{'production_mode':'current_run_export','producer_run_key':key,
             'producer_source':'tools/build_pulsemech_compute_subject_input_packet_current_run_v0.py'},
 'subject':{'repository':'HKati/pulse-release-gates-0.1','workflow_name':'PULSE CI','workflow_run_id':run,
            'workflow_run_number':number,'workflow_run_attempt':attempt,'source_commit':'a'*40,'source_ref':'refs/heads/main',
            'subject_run_key':key,'release_candidate_id':'main','run_mode':'prod','decision':'ALLOW','active_policy_sets':['required','release_required']},
 'carrier':{'carrier_kind':'current_run_export_archive','carrier_id':'carrier:unit/x/v0','sha256':cap.sha256,'size_bytes':len(raw),
            'root_prefix':f'pulsemech-current-run-export-{run}-{attempt}-v0','immutable':True,'media_type':'application/zip','artifact_payload_mode':'external_carrier'},
 'artifacts':[{'provider_binding':{'provider':'github_actions'}} for _ in range(3)]+[{'provider_binding':None} for _ in range(29)]}
 return p,cap

def _intake_function_source(source,name):
 t=ast.parse(source)
 n=next(n for n in t.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name)
 return ast.get_source_segment(source,n)

@pytest.mark.parametrize('run,number,attempt',[(70000001,7001,1),(80000002,8002,2),(90000003,9003,3)])
def test_intake_current_profile_is_derived_without_filename_or_input_profile(run,number,attempt):
 p,c=_intake_partial_metadata(run=run,number=number,attempt=attempt)
 assert 'input_profile' not in p
 result=_INTAKE_BRIDGE._current_run_expectation(p,c)
 assert result['subject']==p['subject']
 assert result['subject'] is not p['subject']
 assert result['archive_layout']['outer_prefix']==f'pulsemech-current-run-export-{run}-{attempt}-v0/'
 assert result['archive_layout']['expected_non_provider_artifact_count']==29
 assert str(c.path) not in str(result)

@pytest.mark.parametrize('scope,mode,kind',[
 ('fixed_source_adapter','fixed_source_adapter','preservation_archive'),
 ('post_run_preservation','post_run_export','preservation_archive'),
])
def test_intake_existing_non_current_routes_are_not_reclassified(scope,mode,kind):
 p,c=_intake_partial_metadata();p['packet_identity']['packet_scope']=scope;p['producer']['production_mode']=mode;p['carrier']['carrier_kind']=kind
 assert _INTAKE_BRIDGE._current_run_expectation(p,c) is None

FAULTS=[
 ('packet_identity','packet_scope','fixed_source_adapter','current_run_profile_conflict'),
 ('producer','production_mode','post_run_export','current_run_profile_conflict'),
 ('carrier','carrier_kind','preservation_archive','current_run_profile_conflict'),
 ('subject','workflow_run_id',True,'current_run_subject_integer_invalid'),
 ('subject','workflow_run_id',0,'current_run_subject_integer_invalid'),
 ('subject','workflow_run_number','7001','current_run_subject_integer_invalid'),
 ('subject','workflow_run_attempt',False,'current_run_subject_integer_invalid'),
 ('subject','workflow_run_attempt',-1,'current_run_subject_integer_invalid'),
 ('subject','repository','','current_run_subject_text_invalid'),
 ('subject','workflow_name',None,'current_run_subject_text_invalid'),
 ('subject','source_ref','','current_run_subject_text_invalid'),
 ('subject','release_candidate_id',None,'current_run_subject_text_invalid'),
 ('subject','source_commit','short','current_run_source_commit_invalid'),
 ('subject','source_commit','A'*40,'current_run_source_commit_invalid'),
 ('subject','subject_run_key','wrong','current_run_subject_run_key_mismatch'),
 ('packet_identity','subject_run_key','wrong','current_run_subject_run_key_mismatch'),
 ('producer','producer_run_key','wrong','current_run_subject_run_key_mismatch'),
 ('producer','producer_source','tools/other.py','current_run_producer_path_mismatch'),
 ('packet_identity','carrier_id','carrier:other','current_run_carrier_identity_mismatch'),
 ('carrier','sha256','b'*64,'current_run_carrier_bytes_mismatch'),
 ('carrier','size_bytes',True,'current_run_carrier_bytes_mismatch'),
 ('carrier','size_bytes',0,'current_run_carrier_bytes_mismatch'),
 ('carrier','root_prefix','pulse-ci-6066-preservation-v0','current_run_carrier_root_mismatch'),
 ('carrier','root_prefix','../escape','current_run_carrier_root_mismatch'),
 ('carrier','root_prefix','pulsemech-current-run-export-70000001-2-v0','current_run_carrier_root_mismatch'),
 ('carrier','immutable',False,'current_run_carrier_contract_mismatch'),
 ('carrier','immutable',1,'current_run_carrier_contract_mismatch'),
 ('carrier','media_type','text/plain','current_run_carrier_contract_mismatch'),
 ('carrier','artifact_payload_mode','embedded','current_run_carrier_contract_mismatch'),
]

@pytest.mark.parametrize('section,key,value,error',FAULTS)
def test_intake_conflicting_metadata_is_rejected(section,key,value,error):
 p,c=_intake_partial_metadata();p[section][key]=value
 with pytest.raises(_INTAKE_BRIDGE.AdapterError,match=error):_INTAKE_BRIDGE._current_run_expectation(p,c)

@pytest.mark.parametrize('count',[0,1,2,4])
def test_intake_closed_three_provider_count(count):
 p,c=_intake_partial_metadata();p['artifacts']=[{'provider_binding':{'provider':'github_actions'}} for _ in range(count)]+[{'provider_binding':None}]*29
 with pytest.raises(_INTAKE_BRIDGE.AdapterError,match='current_run_provider_count_mismatch'):_INTAKE_BRIDGE._current_run_expectation(p,c)

@pytest.mark.parametrize('value',[None,[],[{}],[{}, {}, {}]])
def test_intake_invalid_artifact_inventory(value):
 p,c=_intake_partial_metadata();p['artifacts']=value
 with pytest.raises(_INTAKE_BRIDGE.AdapterError,match='current_run_artifact_inventory_invalid'):_INTAKE_BRIDGE._current_run_expectation(p,c)

def test_intake_real_existing_loader_is_reused():
 p,c=_intake_partial_metadata();expected=_INTAKE_BRIDGE._current_run_expectation(p,c)
 with pytest.raises(_INTAKE_LOADER.WrapperError,match='current_run_export_carrier_invalid_zip'):
  _INTAKE_CORE.load_current_run_observed_bundle(archive_path=_INTAKE_BRIDGE.CapturedPathView(c),archive_bytes=c.data,expectation=expected,loader=_INTAKE_LOADER)

def test_intake_valid_zip_wrong_members_rejected_by_actual_current_loader():
 buf=io.BytesIO()
 with zipfile.ZipFile(buf,'w') as z:z.writestr('pulse-ci-6066-preservation-v0/README.md','unit negative only')
 p,c=_intake_partial_metadata(buf.getvalue());expected=_INTAKE_BRIDGE._current_run_expectation(p,c)
 with pytest.raises(_INTAKE_LOADER.WrapperError,match='current_run_export_outer_member_set_mismatch'):
  _INTAKE_CORE.load_current_run_observed_bundle(archive_path=_INTAKE_BRIDGE.CapturedPathView(c),archive_bytes=c.data,expectation=expected,loader=_INTAKE_LOADER)

def test_intake_public_intake_validates_before_current_route():
 tree=ast.parse(_intake_function_source(ADAPTER.read_text(),'build_from_captured_inputs'))
 calls={n.func.id:n.lineno for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)}
 assert calls['_validate_packet_exact_bytes']<calls['_resolve_artifact_bytes']<calls['_build_bundle_from_exact_bytes']




# Real CLI acceptance fixture. Run/provider/attestation values are constructed
# TEST DATA, not observations. Actual verifier/producer/bridge processes remain
# unchanged; no Git-trust override or mocked successful subprocess is used.
import datetime as dt

_INTAKE_WRAPPER = "tools/build_pulsemech_compute_subject_input_packet_current_run_v0.py"
_INTAKE_REPOSITORY = "example-org/step5c-synthetic-subject"
_INTAKE_STAMP = "2026-09-18T09:50:00Z"
_INTAKE_BASE = None
_INTAKE_RAW = None

_INTAKE_FIXTURE_SOURCES = ('.github/workflows/pulse_ci.yml', '.github/workflows/pulsemech_compute_current_run_export_candidate.yml', '.github/workflows/pulsemech_compute_whole_runtime_observation_reference.yml', 'PULSE_safe_pack_v0/examples/llamaguard_current_run_cases_v0.jsonl', 'PULSE_safe_pack_v0/profiles/external_thresholds.yaml', 'PULSE_safe_pack_v0/requirements-llamaguard-v0.txt', 'PULSE_safe_pack_v0/tools/adapters/llamaguard_ingest.py', 'PULSE_safe_pack_v0/tools/assemble_release_grade_reference_package_v0.py', 'PULSE_safe_pack_v0/tools/build_artifact_provenance_binding_v0.py', 'PULSE_safe_pack_v0/tools/build_llamaguard_attestation_envelope_v1.py', 'PULSE_safe_pack_v0/tools/build_recorded_release_candidates_v0.py', 'PULSE_safe_pack_v0/tools/build_release_evidence_input_manifest_v0.py', 'PULSE_safe_pack_v0/tools/build_release_grade_candidate_status_v0.py', 'PULSE_safe_pack_v0/tools/build_self_contained_pulse_evidence_floor_v0.py', 'PULSE_safe_pack_v0/tools/check_external_summary_attestation_v1.py', 'PULSE_safe_pack_v0/tools/check_gates.py', 'PULSE_safe_pack_v0/tools/check_quality_ledger_status_parity.py', 'PULSE_safe_pack_v0/tools/check_recorded_release_evidence_v0.py', 'PULSE_safe_pack_v0/tools/insert_release_authority_manifest_ledger_section.py', 'PULSE_safe_pack_v0/tools/insert_release_decision_ledger_section.py', 'PULSE_safe_pack_v0/tools/materialize_release_required_from_verifier_v0.py', 'PULSE_safe_pack_v0/tools/run_llamaguard_current_evidence_v0.py', 'PULSE_safe_pack_v0/tools/status_to_junit.py', 'PULSE_safe_pack_v0/tools/status_to_sarif.py', 'PULSE_safe_pack_v0/tools/verify_artifact_provenance_binding_v0.py', 'PULSE_safe_pack_v0/tools/verify_release_grade_reference_package_v0.py', 'ci/check_release_no_stub_status.py', 'ci/tools-tests.list', 'policy/external_signers_v1.yml', 'pulse_gate_policy_v0.yml', 'pulse_gate_registry_v0.yml', 'requirements.txt', 'schemas/pulsemech_compute_binding_report_v0.schema.json', 'schemas/pulsemech_compute_current_run_export_expectation_v0.schema.json', 'schemas/pulsemech_compute_planned_observed_relation_v0.schema.json', 'schemas/pulsemech_compute_runtime_observation_packet_v0.schema.json', 'schemas/pulsemech_compute_subject_input_packet_v0.schema.json', 'schemas/pulsemech_compute_whole_runtime_observation_evidence_v0.schema.json', 'tools/acquire_pulsemech_compute_whole_runtime_observation_v0.py', 'tools/build_pulsemech_compute_binding_report_from_subject_input_v0.py', 'tools/build_pulsemech_compute_binding_report_v0.py', 'tools/build_pulsemech_compute_current_run_artifact_observed_proof_v0.py', 'tools/build_pulsemech_compute_current_run_export_expectation_v0.py', 'tools/build_pulsemech_compute_planned_observed_relation_v0.py', 'tools/build_pulsemech_compute_subject_input_packet_current_run_v0.py', 'tools/build_pulsemech_compute_whole_runtime_observation_plan_v0.py', 'tools/capture_pulsemech_compute_whole_runtime_observation_v0.py', 'tools/check_gate_registry_sync.py', 'tools/check_pulsemech_compute_binding_report_v0.py', 'tools/check_pulsemech_compute_current_run_export_expectation_v0.py', 'tools/check_pulsemech_compute_planned_observed_relation_v0.py', 'tools/check_pulsemech_compute_runtime_observation_packet_v0.py', 'tools/check_pulsemech_compute_subject_input_packet_v0.py', 'tools/check_pulsemech_compute_whole_runtime_observation_plan_v0.py', 'tools/check_pulsemech_compute_whole_runtime_observation_v0.py', 'tools/check_release_grade_package_complete_v1.py', 'tools/fold_pulsemech_compute_planned_observed_relation_into_status_v0.py', 'tools/load_pulsemech_compute_current_run_export_candidate_bundle_v0.py', 'tools/load_pulsemech_compute_current_run_export_carrier_v0.py', 'tools/policy_to_require_args.py', 'tools/pulsemech_compute_binding_analyzer_core_v0.py', 'tools/pulsemech_compute_subject_input_packet_producer_core_v0.py', 'tools/validate_status_schema.py')

def _intake_sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _intake_render(obj: Any) -> bytes:
    return (json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()

def _intake_module(path: Path, name: str) -> Any:
    result = types.ModuleType(name)
    result.__file__ = str(path)
    sys.modules[name] = result
    exec(compile(path.read_bytes(), str(path), 'exec'), result.__dict__)
    return result

def _intake_inventory(root: Path) -> list[dict[str, Any]]:
    return [{'path': p.relative_to(root).as_posix(), 'size_bytes': p.stat().st_size, 'sha256': _intake_sha(p.read_bytes())} for p in sorted(root.rglob('*')) if p.is_file() and '.git' not in p.parts]

def _intake_zip_bytes(values: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, data in sorted(values.items()):
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.external_attr = 33060 << 16
            info.create_system = 3
            archive.writestr(info, data)
    return stream.getvalue()

class _IntakeFixtureHarness:

    def __init__(self) -> None:
        parent = _INTAKE_BASE / 'fixture_attempts'
        parent.mkdir(exist_ok=True)
        self.root = parent / f'attempt_{len(list(parent.iterdir())) + 1:03d}'
        self.root.mkdir()
        (self.root / 'fixture_driver.py').write_bytes(Path(__file__).read_bytes())
        self.control = self.root / 'control'
        self.subject = self.root / 'subject'
        self.commands: list[dict[str, Any]] = []
        (self.root / 'sources_before.json').write_bytes(_intake_render(_intake_inventory(_INTAKE_RAW)))
        print('ATTEMPT', self.root, flush=True)

    def execute(self, name: str, argv: list[Any], cwd: Path | None=None) -> bytes:
        folder = self.root / 'commands' / name
        folder.mkdir(parents=True, exist_ok=False)
        args = list(map(str, argv))
        record = {'argv': args, 'cwd': str(cwd or _INTAKE_BASE), 'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'python': sys.version, 'driver_sha256': _intake_sha(Path(__file__).read_bytes())}
        (folder / 'command.json').write_bytes(_intake_render(record))
        (folder / 'control_before.json').write_bytes(_intake_render(_intake_inventory(self.control)))
        with (folder / 'stdout.log').open('wb') as out, (folder / 'stderr.log').open('wb') as err:
            result = subprocess.run(args, cwd=cwd or _INTAKE_BASE, stdout=out, stderr=err, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_TERMINAL_PROMPT': '0'}, timeout=180, check=False)
        record.update(returncode=result.returncode, finished_utc=dt.datetime.now(dt.timezone.utc).isoformat())
        (folder / 'result.json').write_bytes(_intake_render(record))
        (folder / 'control_after.json').write_bytes(_intake_render(_intake_inventory(self.control)))
        self.commands.append(record)
        print(name, result.returncode, flush=True)
        if result.returncode:
            raise RuntimeError(name + ': ' + (folder / 'stderr.log').read_text()[-7000:] + (folder / 'stdout.log').read_text()[-1500:])
        return (folder / 'stdout.log').read_bytes()

    def git(self, root: Path, *args: str) -> str:
        result = subprocess.run(['/usr/bin/git', '-C', str(root), *args], env={**os.environ, 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_AUTHOR_DATE': _INTAKE_STAMP, 'GIT_COMMITTER_DATE': _INTAKE_STAMP}, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=True)
        return result.stdout.decode().strip()

    def make_repo(self, dest: Path) -> str:
        shutil.copytree(_INTAKE_RAW, dest)
        self.git(dest, 'init', '-q', '-b', 'main')
        self.git(dest, 'config', 'user.name', 'PULSEmech synthetic integration fixture')
        self.git(dest, 'config', 'user.email', 'fixture@example.invalid')
        self.git(dest, 'add', '.')
        self.git(dest, 'commit', '-q', '-m', 'Synthetic source snapshot; not upstream commit')
        revision = self.git(dest, 'rev-parse', 'HEAD')
        assert self.git(dest, 'rev-parse', '--is-shallow-repository') == 'false'
        assert not (dest / '.git/objects/info/alternates').exists()
        return revision

    def build(self) -> None:
        revision = self.make_repo(self.subject)
        assert revision == self.make_repo(self.control)
        w = _intake_module(self.control / _INTAKE_WRAPPER, 'fixture_real_current_wrapper')
        v = _intake_module(self.control / 'tools/check_pulsemech_compute_subject_input_packet_v0.py', 'fixture_real_subject_validator')
        helper = ROOT / 'tests/test_build_pulsemech_compute_subject_input_packet_current_run_v0.py'
        selected = {'make_complete_package_members', 'authority_sources', 'component_bindings'}
        nodes = [n for n in ast.parse(helper.read_bytes()).body if isinstance(n, ast.FunctionDef) and n.name in selected]
        assert len(nodes) == 3
        ns: dict[str, Any] = {'Path': Path, 'Any': Any, 'json': json, 'copy': copy, 'sha256_bytes': _intake_sha, 'render_json': _intake_render, 'TOOL_MODULE': w}
        exec(compile(ast.Module(nodes, type_ignores=[]), str(helper) + '#data-only', 'exec'), ns)
        source_files = {p.relative_to(_INTAKE_RAW).as_posix(): p.read_bytes() for p in _INTAKE_RAW.rglob('*') if p.is_file()}
        sources = ns['authority_sources'](self.subject, revision, source_files)
        policy = v.load_yaml_bytes(source_files['pulse_gate_policy_v0.yml'], label='fixture policy')
        registry = v.load_yaml_bytes(source_files['pulse_gate_registry_v0.yml'], label='fixture registry')
        sources['workflow'].update(source_id='source:workflow', workflow_ref=f'{_INTAKE_REPOSITORY}/.github/workflows/pulse_ci.yml@refs/heads/main')
        sources['policy'].update(source_id='source:policy', policy_id=policy['policy']['id'])
        sources['gate_registry'].update(source_id='source:gate-registry', registry_id=registry['version'])
        sources['additional_sources'][0]['source_id'] = 'source:external-signer-policy'
        sources['additional_sources'][1]['source_id'] = 'source:threshold-policy'
        run, number, attempt = (9001, 9017, 1)
        runkey = 'GITHUB_RUN_ID=9001|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI'
        prefix = 'pulsemech-current-run-export-9001-1-v0/'
        subject = {'repository': _INTAKE_REPOSITORY, 'workflow_name': 'PULSE CI', 'workflow_path': '.github/workflows/pulse_ci.yml', 'workflow_ref': sources['workflow']['workflow_ref'], 'workflow_run_id': run, 'workflow_run_number': number, 'workflow_run_attempt': attempt, 'subject_run_key': runkey, 'source_commit': revision, 'source_ref': 'refs/heads/main', 'event_name': 'workflow_dispatch', 'release_candidate_id': 'synthetic-current-run-9001-1', 'run_mode': 'prod', 'active_policy_sets': ['required', 'release_required'], 'policy_id': policy['policy']['id'], 'policy_sha256': sources['policy']['sha256'], 'materialized_gate_set_sha256': None, 'final_status_sha256': '1' * 64, 'release_decision_sha256': '2' * 64, 'decision': 'ALLOW'}
        members, _ = ns['make_complete_package_members'](subject=subject, sources=sources)

        def load(name: str) -> Any:
            return json.loads(members[name])

        def save(name: str, value: Any) -> None:
            members[name] = _intake_render(value)
        status = load('artifacts/status.json')
        status['metrics'].update(run_mode='prod', gate_policy_path='pulse_gate_policy_v0.yml', gate_policy_sha256=sources['policy']['sha256'], gate_registry_path='pulse_gate_registry_v0.yml', gate_registry_sha256=sources['gate_registry']['sha256'])
        gates = list(dict.fromkeys(policy['gates']['required'] + policy['gates']['release_required']))
        status['metrics'].update(candidate_status_builder_path='PULSE_safe_pack_v0/tools/build_release_grade_candidate_status_v0.py', candidate_status_builder_sha256=_intake_sha(source_files['PULSE_safe_pack_v0/tools/build_release_grade_candidate_status_v0.py']))
        status['gates'].update({name: True for name in gates})
        save('artifacts/status.json', status)
        save('artifacts/status_baseline.json', status)
        subject['final_status_sha256'] = _intake_sha(members['artifacts/status.json'])
        decision = {'required_gates_passed': True, 'blocking_reasons': [], 'release_level': 'PROD-PASS', 'git_sha': revision, 'run_mode': 'prod', 'policy_sha256': sources['policy']['sha256'], 'status_sha256': subject['final_status_sha256'], 'active_gate_sets': subject['active_policy_sets']}
        save('artifacts/release_decision_v0.json', decision)
        subject['release_decision_sha256'] = _intake_sha(members['artifacts/release_decision_v0.json'])
        gate_set = {'policy_sets': subject['active_policy_sets'], 'required_gates': gates, 'sha256': _intake_sha(_intake_render(gates))}
        subject['materialized_gate_set_sha256'] = gate_set['sha256']
        save('artifacts/release_authority_v0.json', {'run_identity': {'git_sha': revision, 'run_mode': 'prod', 'workflow_name': 'PULSE CI', 'event_name': 'workflow_dispatch', 'ref': 'refs/heads/main'}, 'inputs': {'status_json': {'sha256': subject['final_status_sha256']}, 'gate_policy': {'sha256': sources['policy']['sha256']}}, 'authority': {'policy_set': 'required+release_required'}, 'decision': {'state': 'PASS'}})
        save('artifacts/artifact_provenance_binding_v0.json', {'run': {'git_sha': revision, 'run_key': runkey, 'run_mode': 'prod'}, 'authority_carrier': {'status_json': {'sha256': subject['final_status_sha256']}, 'declared_gate_policy': {'sha256': sources['policy']['sha256']}, 'release_decision': {'sha256': subject['release_decision_sha256']}, 'workflow_effective_required_gate_set': gate_set}})
        attestation = load('artifacts/external/llamaguard_attestation_verifier_v1.json')
        attestation['extensions'] = {'workflow_sha256': sources['workflow']['sha256'], 'policy_path': 'policy/external_signers_v1.yml', 'signer_policy_sha256': sources['additional_sources'][0]['sha256'], 'threshold_policy_sha256': sources['additional_sources'][1]['sha256']}
        save('artifacts/external/llamaguard_attestation_verifier_v1.json', attestation)

        def source(path: str) -> dict[str, str]:
            return {'path': path, 'sha256': _intake_sha(source_files[path])}
        required = load('artifacts/required_gate_evidence_v0.json')
        required['producer'] = {'tool_path': 'PULSE_safe_pack_v0/tools/build_self_contained_pulse_evidence_floor_v0.py', 'tool_sha256': _intake_sha(source_files['PULSE_safe_pack_v0/tools/build_self_contained_pulse_evidence_floor_v0.py'])}
        save('artifacts/required_gate_evidence_v0.json', required)
        authority = load('artifacts/release_authority_v0.json')
        authority['inputs']['gate_policy'].update(policy_id=policy['policy']['id'], path='pulse_gate_policy_v0.yml')
        authority['inputs']['gate_registry'] = {'path': 'pulse_gate_registry_v0.yml', 'version': registry['version'], 'sha256': sources['gate_registry']['sha256']}
        authority['evaluation'] = {'evaluator_sha256': _intake_sha(source_files['PULSE_safe_pack_v0/tools/check_gates.py'])}
        save('artifacts/release_authority_v0.json', authority)
        binding = load('artifacts/artifact_provenance_binding_v0.json')
        binding['authority_carrier']['strict_ci_gate_enforcement'] = {'sha256': _intake_sha(_intake_render({'synthetic_gate_result': 'ALLOW', 'run_key': runkey}))}
        save('artifacts/artifact_provenance_binding_v0.json', binding)
        original_candidate = load('artifacts/recorded_release_candidates/candidate-v0.json')
        members.pop('artifacts/recorded_release_candidates/candidate-v0.json')
        raw_refusal = _intake_render({'synthetic_controlled_refusal_evidence': True})
        members['artifacts/refusal_delta_summary.json'] = raw_refusal
        for name in ('detector_materialization', 'external_llamaguard', 'refusal_delta_summary'):
            candidate = copy.deepcopy(original_candidate)
            candidate['provenance'] = {'tool_path': 'PULSE_safe_pack_v0/tools/build_recorded_release_candidates_v0.py', 'tool_sha256': _intake_sha(source_files['PULSE_safe_pack_v0/tools/build_recorded_release_candidates_v0.py'])}
            candidate['raw_evidence_binding'] = {'path': 'artifacts/refusal_delta_summary.json', 'sha256': _intake_sha(raw_refusal)}
            save('artifacts/recorded_release_candidates/' + name + '.json', candidate)
        verifier = load('artifacts/recorded_release_evidence_verifier_v0.json')
        verifier['run_identity'] = {'run_key': runkey}
        save('artifacts/recorded_release_evidence_verifier_v0.json', verifier)
        evaluator = load('artifacts/external/llamaguard_evaluator_manifest_v0.json')
        evaluator['dataset'] = source('PULSE_safe_pack_v0/examples/llamaguard_current_run_cases_v0.jsonl')
        evaluator['producer'] = source('PULSE_safe_pack_v0/tools/run_llamaguard_current_evidence_v0.py')
        save('artifacts/external/llamaguard_evaluator_manifest_v0.json', evaluator)
        summary = load('artifacts/external/llamaguard_summary.json')
        summary['extensions']['evaluator_manifest_sha256'] = _intake_sha(members['artifacts/external/llamaguard_evaluator_manifest_v0.json'])
        summary['extensions']['adapter_sha256'] = _intake_sha(source_files['PULSE_safe_pack_v0/tools/adapters/llamaguard_ingest.py'])
        save('artifacts/external/llamaguard_summary.json', summary)
        envelope = load('artifacts/external/llamaguard_summary.envelope.json')
        envelope['summary_digest']['value'] = _intake_sha(members['artifacts/external/llamaguard_summary.json'])
        envelope['extensions'].update(workflow_sha256=sources['workflow']['sha256'], workflow_path='.github/workflows/pulse_ci.yml', signer_policy_sha256=sources['additional_sources'][0]['sha256'], envelope_builder=source('PULSE_safe_pack_v0/tools/build_llamaguard_attestation_envelope_v1.py'), canonical_replay_verifier=source('PULSE_safe_pack_v0/tools/check_external_summary_attestation_v1.py'))
        envelope['policy_context'] = {'signer_policy_ref': 'policy/external_signers_v1.yml'}
        import re
        action = re.search('actions/attest@[0-9a-f]{40}', source_files['.github/workflows/pulse_ci.yml'].decode()).group()
        envelope['verification'] = {'verifier': {'version': action}}
        save('artifacts/external/llamaguard_summary.envelope.json', envelope)
        attestation = load('artifacts/external/llamaguard_attestation_verifier_v1.json')
        attestation['summary']['sha256'] = _intake_sha(members['artifacts/external/llamaguard_summary.json'])
        attestation['envelope']['sha256'] = _intake_sha(members['artifacts/external/llamaguard_summary.envelope.json'])
        save('artifacts/external/llamaguard_attestation_verifier_v1.json', attestation)
        members.pop('synthetic_context.json', None)
        members.pop('package_digest_inventory_v0.json', None)
        package_inventory = {'algorithm': 'sha256', 'file_count': len(members), 'files': [{'path': p, 'sha256': _intake_sha(b), 'size_bytes': len(b)} for p, b in sorted(members.items())], 'schema_version': 'release_grade_reference_package_digest_inventory_v0'}
        save('package_digest_inventory_v0.json', package_inventory)
        package = self.root / 'package'
        for name, data in members.items():
            dest = package / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        reports = self.root / 'package_reports'
        reports.mkdir()
        self.execute('package_completeness', [sys.executable, '-I', '-B', self.control / 'tools/check_release_grade_package_complete_v1.py', '--package-dir', package, '--out', reports / 'completeness.json'])
        self.execute('package_verification', [sys.executable, '-I', '-B', self.control / 'PULSE_safe_pack_v0/tools/verify_release_grade_reference_package_v0.py', '--repo-root', self.control, '--package-dir', package, '--out', reports / 'verification.json', '--repository', _INTAKE_REPOSITORY, '--git-sha', revision, '--workflow-ref', subject['workflow_ref'], '--run-id', '9001', '--run-attempt', '1', '--run-key', runkey])
        completeness = json.loads((reports / 'completeness.json').read_bytes())
        verification = json.loads((reports / 'verification.json').read_bytes())
        verification_carrier_bytes = (reports / 'verification.json').read_bytes()
        contract_summary_example = False
        assert verification_carrier_bytes == (reports / 'verification.json').read_bytes()
        assert verification['summary']['checks_total'] == len(verification['checks'])
        assert verification['summary']['checks_failed'] == 0
        layout = {'artifact_count_derivation': 'provider_plus_non_provider', 'complete_package_name': 'complete-release-grade-reference-package-9001-1.zip', 'completeness_archive_name': 'release-grade-package-completeness-9001-1.zip', 'verification_archive_name': 'release-grade-reference-package-verification-9001-1.zip', 'expected_non_provider_artifact_count': len(members) + 5, 'expected_provider_artifact_count': 3, 'layout_id': 'pulsemech_current_run_export_layout_v0', 'layout_version': '0.1.0', 'outer_prefix': prefix, 'original_artifacts_prefix': prefix + 'original-github-artifacts/', 'visible_members': {'preservation_checksums_name': 'SHA256SUMS', 'preservation_manifest_name': 'PRESERVATION_MANIFEST_v0.json', 'preservation_readme_name': 'README.md'}}
        providers = {layout['complete_package_name']: _intake_zip_bytes(members), layout['completeness_archive_name']: _intake_zip_bytes({'release_grade_package_completeness_v1.json': (reports / 'completeness.json').read_bytes()}), layout['verification_archive_name']: _intake_zip_bytes({'release_grade_reference_package_verification_v0.json': verification_carrier_bytes})}
        roles = dict(zip([layout[k] for k in ('complete_package_name', 'completeness_archive_name', 'verification_archive_name')], ('complete_release_grade_reference_package', 'structural_package_completeness_report', 'independent_package_verification_report')))
        rows = [{'artifact_id': 1000 + i, 'artifact_name': n, 'file_name': n, 'created_at': '2026-09-17T20:05:00Z', 'expires_at': '2026-10-17T20:05:00Z', 'downloaded_sha256': _intake_sha(b), 'downloaded_size_bytes': len(b), 'github_digest_match': True, 'github_sha256': _intake_sha(b), 'github_size_match': True, 'role': roles[n], 'size_bytes': len(b)} for i, (n, b) in enumerate(sorted(providers.items()), 1)]
        manifest = {'schema_id': 'pulse_ci_release_grade_artifact_preservation_manifest_v0', 'schema_version': '0.1.0', 'repository': _INTAKE_REPOSITORY, 'workflow': 'PULSE CI', 'workflow_run_id': run, 'workflow_run_number': number, 'workflow_run_attempt': attempt, 'source_commit': revision, 'source_ref': 'refs/heads/main', 'run_mode': 'prod', 'active_policy_sets': subject['active_policy_sets'], 'primary_gate_result': 'allow', 'authority_boundary': copy.deepcopy(w.PRESERVATION_AUTHORITY_BOUNDARY), 'github_artifacts': rows, 'local_verification': {'all_outer_artifact_digests_match_github': True, 'all_outer_artifact_sizes_match_github': True, 'complete_package_inventory_entries': len(package_inventory['files']), 'complete_package_zip_members': len(members), 'independent_verification_checks_total': len(verification['checks']), 'independent_verification_verified': True, 'structural_completeness_checks_total': len(completeness['checks']), 'structural_completeness_ok': True}}
        visible = {'PRESERVATION_MANIFEST_v0.json': _intake_render(manifest), 'README.md': b'Explicitly SYNTHETIC current-run fixture. No hosted execution, inference, signature verification or release.\n', **{'original-github-artifacts/' + n: b for n, b in providers.items()}}
        visible['SHA256SUMS'] = ''.join((f'{_intake_sha(b)}  {n}\n' for n, b in sorted(visible.items()))).encode()
        carrier_data = _intake_zip_bytes({prefix + n: b for n, b in visible.items()})
        staging = self.root / 'staging'
        relative = 'exports/current-run-9001-1.zip'
        carrier_path = staging / relative
        carrier_path.parent.mkdir(parents=True)
        carrier_path.write_bytes(carrier_data)
        carrier_path.chmod(292)
        components = ns['component_bindings'](self.control, revision, source_files)

        def producer(source_key: str, source: str, kind: str, label: str) -> dict[str, Any]:
            return {'ci_workflow_or_job_identity': 'synthetic ' + label + ' input', 'producer_id': 'producer:pulsemech-current-run-export-' + label + '-v0', 'producer_name': 'PULSEmech current-run export ' + label.replace('-', ' '), 'producer_run_key': runkey, 'producer_source': source, 'producer_source_revision': revision, 'producer_source_sha256': components[source_key]['sha256'], 'producer_version': '0.1.0', 'production_mode': kind}
        carrier = {'artifact_payload_mode': 'external_carrier', 'carrier_id': 'carrier:current-run/pulse-ci-9017/v0', 'carrier_kind': 'current_run_export_archive', 'finalized': True, 'finalized_utc': '2026-09-17T20:10:00Z', 'immutable': True, 'media_type': 'application/zip', 'path_base': 'current_run_export_staging_root', 'provider_binding': None, 'root_prefix': prefix, 'sha256': _intake_sha(carrier_data), 'size_bytes': len(carrier_data), 'staged_relative_path': relative, 'producer': producer('carrier_loader', w.CARRIER_LOADER_SOURCE_PATH, 'current_run_export_carrier_builder', 'carrier-loader')}
        expectation = {'archive_layout': layout, 'authority_boundary': copy.deepcopy(w.EXPECTED_EXPECTATION_AUTHORITY_BOUNDARY), 'authority_sources': sources, 'carrier': carrier, 'content_boundary': copy.deepcopy(w.EXPECTED_EXPECTATION_CONTENT_BOUNDARY), 'document_type': 'pulsemech_compute_current_run_export_expectation', 'errors': [], 'expectation_identity': {'canonicalization': 'json-sort-keys-utf8-newline', 'expectation_created_utc': '2026-09-17T20:11:00Z', 'expectation_id': 'current-run-export-expectation:synthetic-9001-1', 'expectation_scope': 'current_run_export', 'subject_run_key': runkey}, 'expectation_producer': producer('expectation_builder', w.EXPECTATION_BUILDER_SOURCE_PATH, 'current_run_expectation_builder', 'expectation-builder'), 'ok': True, 'packet_contract': copy.deepcopy(w.EXPECTED_PACKET_CONTRACT), 'packet_producer_profile': {'expected_archive_layout_id': 'pulsemech_current_run_export_layout_v0', 'expected_carrier_artifact_payload_mode': 'external_carrier', 'expected_carrier_id_namespace': 'current-run', 'expected_carrier_kind': 'current_run_export_archive', 'expected_carrier_media_type': 'application/zip', 'expected_packet_identity_mode': 'current-run', 'expected_packet_scope': 'current_run', 'expected_producer_source_path': _INTAKE_WRAPPER, 'expected_production_mode': 'current_run_export', 'expected_repository': _INTAKE_REPOSITORY, 'expected_signer_policy_path': 'policy/external_signers_v1.yml', 'expected_source_commit': revision, 'expected_subject_run_key': runkey, 'profile_id': 'pulsemech_current_run_export_synthetic_v0'}, 'record_status': 'observed', 'schema_version': 'pulsemech_compute_current_run_export_expectation_v0', 'subject': subject, 'trusted_control_plane': {'checkout_role': 'protected_control_plane', 'components': components, 'repository': _INTAKE_REPOSITORY, 'revision': revision, 'separate_from_subject_checkout': True, 'subject_may_select_revision': False, 'trust_mode': 'protected_exact_revision'}}
        external = self.root / 'external'
        external.mkdir()
        expath = external / 'expectation.json'
        expath.write_bytes(_intake_render(expectation))
        provenance = {'record_status': 'synthetic_integration_fixture', 'upstream_source_baseline': '7257444b8d4e1be9edc7169537adab6d6d24264d', 'local_synthetic_revision': revision, 'local_commit_is_not_upstream_commit': True, 'manually_constructed_test_input_records': ['run', 'provider artifact metadata', 'carrier producer metadata', 'expectation producer metadata', 'attestation records', 'gate states', 'release decision'], 'actual_executions': 'See commands/; no execution result is substituted with a mock.', 'input_observed_enum_is_protocol_fixture_value_not_a_live_acquisition_claim': True, 'no_hosted_execution': True, 'no_inference': True, 'no_release': True, 'data_helper_file_sha256': _intake_sha(helper.read_bytes()), 'carrier_sha256': _intake_sha(carrier_data), 'contract_summary_example': contract_summary_example, 'raw_verifier_output_path_remains_unchanged': True}
        (self.root / 'FIXTURE_PROVENANCE.json').write_bytes(_intake_render(provenance))
        packet = self.execute('producer', [sys.executable, '-I', '-B', self.control / _INTAKE_WRAPPER, '--expectation', expath, '--expectation-sha256', _intake_sha(expath.read_bytes()), '--staging-root', staging, '--subject-root', self.subject, '--subject-repository', _INTAKE_REPOSITORY, '--subject-revision', revision, '--control-plane-root', self.control, '--control-plane-repository', _INTAKE_REPOSITORY, '--control-plane-revision', revision, '--packet-created-utc', '2026-09-17T20:12:00Z', '--producer-run-key', runkey, '--ci-workflow-or-job-identity', 'synthetic fixture real wrapper execution', '--trusted-git', '/usr/bin/git'])
        packet_path = external / 'subject-input-packet.json'
        packet_path.write_bytes(packet)
        self.execute('subject_validator', [sys.executable, '-I', '-B', self.control / 'tools/check_pulsemech_compute_subject_input_packet_v0.py', '--schema', self.control / 'schemas/pulsemech_compute_subject_input_packet_v0.schema.json', '--packet', packet_path, '--carrier', carrier_path, '--repository-root', self.subject])
        (self.root / 'SUCCESS.json').write_bytes(_intake_render({'fixture_only': True, 'producer_and_subject_validator_passed': True, 'contract_summary_example': contract_summary_example, 'packet_sha256': _intake_sha(packet), 'carrier_sha256': _intake_sha(carrier_data)}))
        print('REAL PRODUCER AND VALIDATOR SUCCEEDED ON SYNTHETIC INPUT', flush=True)

@pytest.fixture(scope="module")
def current_run_intake_fixture(tmp_path_factory):
    global _INTAKE_BASE, _INTAKE_RAW
    _INTAKE_BASE = tmp_path_factory.mktemp("current_run_intake")
    _INTAKE_RAW = _INTAKE_BASE / "source"
    for relative in _INTAKE_FIXTURE_SOURCES:
        source = ROOT / relative
        target = _INTAKE_RAW / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    harness = _IntakeFixtureHarness()
    harness.build()
    return harness



def _intake_runtime_fixture(harness):
    """Minimal observed-profile TEST DATA; no acquired subject occurrences."""
    SRC = harness.control
    P = harness.root / "external/subject-input-packet.json"
    C = harness.root / "staging/exports/current-run-9001-1.zip"
    OUT = harness.root / "runtime_fixture"
    OUT.mkdir()
    sp=json.loads(P.read_bytes());schema=json.loads((SRC/'schemas/pulsemech_compute_runtime_observation_packet_v0.schema.json').read_bytes());defs=schema['$defs']
    subject={k:copy.deepcopy(sp['subject'][k]) for k in defs['subject']['required']}
    key=subject['subject_run_key'];collector_key='analysis:synthetic-collector:9001:1';eid='execution:synthetic:collector'
    start='2026-09-17T20:13:00Z';end='2026-09-17T20:13:02Z'
    source_path='runtime_option_probe.py';source_sha=_intake_sha(Path(__file__).read_bytes())
    source={k:None for k in defs['source_identity']['required']};source.update(source_kind='repository_file',identity_status='exact',source_path_or_uri=source_path,source_revision='synthetic-test-driver',source_sha256=source_sha)
    environment={k:None for k in defs['execution_environment']['required']};environment.update(environment_kind='unknown',identity_status='unknown',raw_environment_included=False)
    execution={'execution_id':eid,'execution_scope':'observation_collector','execution_kind':'observer_execution','parent_execution_id':None,'workflow_name':'Synthetic collector','job_name':'synthetic collector','job_id':None,'job_attempt':1,'step_name':None,'step_number':None,'source_identity':source,'command_identity':{'command_kind':'unknown','display_name':'Synthetic collector example','command_sha256':None,'arguments_sha256':None,'raw_command_included':False},'execution_environment':environment,'run_binding':{'execution_run_key':collector_key,'subject_run_key':key,'binding_mode':'post_run_observer','binding_complete':True},'timing':{'timing_status':'complete','started_utc':start,'completed_utc':end,'duration_ms':2000,'timestamp_source':'tool_reported','duration_source':'derived_from_timestamps'},'result':{'result_status':'complete','lifecycle_status':'completed','outcome':'success','exit_code':0},'declared_role':'observer','permitted_mutation_authority':'advisory_output','input_state_ids':[],'output_state_ids':[],'external_call_ids':[],'model_inference_ids':[],'resource_measurement_ids':[],'capture_status':'complete'}
    authority={}
    for k in ('workflow','policy','gate_registry'):
     row=sp['authority_sources'][k];authority[k]={'role':k,'path':row['path_or_uri'],'source_commit':row['source_revision'],'sha256':row['sha256']}
    packet={'schema_version':'pulsemech_compute_runtime_observation_packet_v0','packet_type':'pulsemech_compute_runtime_observation_packet','record_status':'observed','producer':{'producer_id':'synthetic-collector','producer_name':'Synthetic runtime option probe','producer_version':'0.1.0','producer_source':source_path,'producer_source_sha256':source_sha,'ci_workflow_or_job_identity':'synthetic collector','collection_mode':'post_run_platform_export','producer_execution_id':eid},'packet_identity':{'packet_id':'runtime-observation:synthetic-intake-9001/v0','packet_sequence':0,'packet_scope':'subject_run','subject_run_key':key,'packet_created_utc':'2026-09-17T20:13:03Z','previous_packet_sha256':None,'canonicalization':'json-sort-keys-utf8-newline'},'subject':subject,'observation_boundary':{'target_analysis_level':'runtime_observed','subject_run_key':key,'collector_run_key':collector_key,'collector_execution_id':eid,'collector_mode':'post_run_platform_export','observer_in_subject_totals':False,'capture_started_utc':start,'capture_completed_utc':end,'subject_artifacts_mutated':False},'authority_inputs':authority,'timing_basis':{'timestamps_utc':True,'primary_clock_source':'github_actions','timestamp_resolution_ms':1,'cross_source_clock_status':'single_source','duration_derivation':'derived_from_recorded_timestamps','duration_values_estimated':False},'privacy_boundary':{**{k:False for k in defs['privacy_boundary']['required']},'redaction_rules_sha256':None},'executions':[execution],'state_observations':[],'external_calls':[],'model_inferences':[],'resource_measurements':[],'coverage':{'coverage_status':'partial','expected_job_count':None,'observed_job_count':0,'expected_step_count':None,'observed_step_count':0,'execution_records':1,'state_records':0,'external_call_records':0,'model_inference_records':0,'resource_measurement_records':0,'missing_execution_ids':[],'unobserved_reasons':['resource_axis_unavailable','step_not_instrumented'],'resource_axes_observed':[],'resource_axes_unavailable':sorted(defs['coverage']['properties']['resource_axes_unavailable']['items']['enum']),'external_call_capture_status':'none','model_inference_capture_status':'none','state_digest_capture_status':'none'},'errors':[],'ok':True}
    # Synthetic observed-profile control, not a relabelled acquired observation.
    for name, state_type in [('workflow','workflow_source'),('policy','policy'),('gate_registry','gate_registry')]:
     a=authority[name];row=sp['authority_sources'][name]
     packet['state_observations'].append({'state_id':'state:synthetic:'+name,'state_type':state_type,
     'path_or_uri':a['path'],'content_status':'exact_digest','sha256':a['sha256'],'size_bytes':row['size_bytes'],
     'media_type':'application/yaml','schema_identity':None,'producer_execution_id':None,'observer_execution_id':eid,
     'subject_run_key':key,'release_candidate_id':subject['release_candidate_id'],'authority_bearing':True,
     'mutation_class':'none','observed_at_utc':start,'secret_material_included':False})
    packet['state_observations'].sort(key=lambda x:x['state_id'])
    packet['coverage']['state_records']=3
    packet['coverage']['state_digest_capture_status']='complete'
    runtime=OUT/'runtime-synthetic-observed-profile.json';runtime.write_bytes(_intake_render(packet))
    (OUT/'PROVENANCE.json').write_bytes(_intake_render({'synthetic':True,'record_status_observed_is_fixture_branch_only':True,'subject_execution_records':0,'collector_example_records':1,'full_Step5C_runtime_proof':False,'raw_verifier_report_handoff_passed':True,'subject_packet_sha256':_intake_sha(P.read_bytes()),'carrier_sha256':_intake_sha(C.read_bytes()),'runtime_packet_sha256':_intake_sha(runtime.read_bytes())}))
    return runtime


def _intake_cli(harness, name, argv, *, inputs=()):
    """Record the real command, exact supplied inputs and all result streams."""
    folder = harness.root / "commands" / name
    folder.mkdir(parents=True, exist_ok=False)
    command = list(map(str, argv))
    before = {str(p): {"size_bytes": p.stat().st_size, "sha256": _intake_sha(p.read_bytes())}
              for p in inputs}
    record = {"argv": command, "cwd": str(harness.control),
              "started_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
    (folder / "command.json").write_bytes(_intake_render(record))
    (folder / "inputs_before.json").write_bytes(_intake_render(before))
    result = subprocess.run(command, cwd=harness.control, capture_output=True,
                            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                            timeout=180, check=False)
    (folder / "stdout.log").write_bytes(result.stdout)
    (folder / "stderr.log").write_bytes(result.stderr)
    after = {str(p): {"size_bytes": p.stat().st_size, "sha256": _intake_sha(p.read_bytes())}
             for p in inputs}
    (folder / "inputs_after.json").write_bytes(_intake_render(after))
    record.update(returncode=result.returncode, inputs_unchanged=before == after,
                  completed_utc=dt.datetime.now(dt.timezone.utc).isoformat())
    (folder / "result.json").write_bytes(_intake_render(record))
    assert before == after
    return result


def _intake_bridge_command(harness, packet, carrier, runtime=None):
    result = [sys.executable, "-I", "-B",
              harness.control / "tools/build_pulsemech_compute_binding_report_from_subject_input_v0.py",
              "--packet", packet, "--carrier", carrier, "--repository-root", harness.subject,
              "--analysis-run-key", "OFFLINE_ANALYSIS=synthetic-current-intake-regression"]
    if runtime is not None:
        result += ["--runtime-packet", runtime]
    return result


@pytest.fixture(scope="module")
def current_run_intake_reports(current_run_intake_fixture):
    h = current_run_intake_fixture
    p = h.root / "external/subject-input-packet.json"
    c = h.root / "staging/exports/current-run-9001-1.zip"
    packet = json.loads(p.read_bytes())
    assert packet["packet_identity"]["packet_scope"] == "current_run"
    assert "input_profile" not in packet
    assert packet["subject"]["workflow_run_id"] != 29249887581
    report = _intake_cli(h, "intake_bridge", _intake_bridge_command(h, p, c), inputs=(p, c))
    assert report.returncode == 0, report.stderr.decode()
    assert report.stderr == b""
    artifact = h.root / "external/artifact-report.json"
    artifact.write_bytes(report.stdout)
    checker = [sys.executable, "-I", "-B", h.control / "tools/check_pulsemech_compute_binding_report_v0.py",
               "--schema", h.control / "schemas/pulsemech_compute_binding_report_v0.schema.json",
               "--report", artifact]
    validated = _intake_cli(h, "intake_report_validator", checker, inputs=(artifact,))
    assert validated.returncode == 0, validated.stderr.decode()
    runtime = _intake_runtime_fixture(h)
    runtime_validated = _intake_cli(h, "intake_runtime_validator",
        [sys.executable, "-I", "-B", h.control / "tools/check_pulsemech_compute_runtime_observation_packet_v0.py",
         "--schema", h.control / "schemas/pulsemech_compute_runtime_observation_packet_v0.schema.json",
         "--packet", runtime], inputs=(runtime,))
    assert runtime_validated.returncode == 0, runtime_validated.stderr.decode()
    runtime_result = _intake_cli(h, "intake_runtime_bridge", _intake_bridge_command(h, p, c, runtime), inputs=(p, c, runtime))
    assert runtime_result.returncode == 0, runtime_result.stderr.decode()
    runtime_report = h.root / "external/runtime-report.json"
    runtime_report.write_bytes(runtime_result.stdout)
    runtime_check = checker[:-1] + [runtime_report,
        "--subject-input", p, "--carrier", c, "--repository-root", h.subject,
        "--runtime-packet", runtime]
    result = _intake_cli(h, "intake_runtime_report_validator", runtime_check, inputs=(artifact, runtime_report, p, c, runtime))
    assert result.returncode == 0, result.stderr.decode()
    return {"harness": h, "packet": p, "carrier": c, "artifact": artifact,
            "runtime": runtime, "runtime_report": runtime_report}


def test_intake_real_producer_report_and_runtime_cli(current_run_intake_reports):
    fixture = current_run_intake_reports
    packet = json.loads(fixture["packet"].read_bytes())
    report = json.loads(fixture["artifact"].read_bytes())
    runtime_report = json.loads(fixture["runtime_report"].read_bytes())
    subject = packet["subject"]
    for field in ("repository", "workflow_run_id", "workflow_run_number", "workflow_run_attempt",
                  "source_commit", "release_candidate_id", "final_status_sha256", "release_decision_sha256"):
        assert report["subject"][field] == subject[field]
        assert runtime_report["subject"][field] == subject[field]
    assert report["subject"]["workflow"] == subject["workflow_name"]
    assert report["analysis_boundary"]["subject_run_key"] == subject["subject_run_key"]
    assert report["analysis_boundary"]["observer_in_subject_totals"] is False
    assert report["resource_summary"]["axes"] == {}
    assert runtime_report["runtime_binding"]["index"]["counts"]["subject_execution_occurrences"] == 0
    assert runtime_report["runtime_binding"]["index"]["counts"]["observer_execution_occurrences"] == 1
    assert runtime_report["runtime_binding"]["coverage"]["relational_coverage_status"] != "complete"
    serialized = fixture["artifact"].read_text()
    assert "pulse-ci-6066-preservation-v0" not in serialized
    assert "PULSE_CI_6066_release_grade_artifact_preservation_v0.zip" not in serialized
    assert "sha256:" + _intake_sha(fixture["carrier"].read_bytes()) in serialized


def test_intake_same_exact_inputs_have_identical_report_bytes(current_run_intake_reports):
    f = current_run_intake_reports
    result = _intake_cli(f["harness"], "intake_deterministic_report",
        _intake_bridge_command(f["harness"], f["packet"], f["carrier"]), inputs=(f["packet"], f["carrier"]))
    assert result.returncode == 0, result.stderr.decode()
    assert result.stdout == f["artifact"].read_bytes()


@pytest.mark.parametrize("mutation", ["carrier_digest", "producer_run", "subject_source", "subject_run",
    "mixed_profile", "provider_id", "missing_role", "missing_member"])
def test_intake_real_cli_rejects_tampered_pair(current_run_intake_reports, mutation):
    f = current_run_intake_reports
    h = f["harness"]
    packet = json.loads(f["packet"].read_bytes())
    carrier_bytes = f["carrier"].read_bytes()
    if mutation == "carrier_digest": packet["carrier"]["sha256"] = "f" * 64
    elif mutation == "producer_run": packet["producer"]["producer_run_key"] = "OTHER=9001"
    elif mutation == "subject_source": packet["subject"]["source_commit"] = "f" * 40
    elif mutation == "subject_run": packet["subject"]["workflow_run_id"] += 1
    elif mutation == "mixed_profile": packet["producer"]["production_mode"] = "fixed_source_adapter"
    elif mutation == "provider_id":
        provider = next(a for a in packet["artifacts"] if isinstance(a.get("provider_binding"), dict))
        provider["provider_binding"]["provider_artifact_id"] = str(int(provider["provider_binding"]["provider_artifact_id"]) + 100)
    elif mutation == "missing_role": packet["artifacts"].pop()
    else:
        with zipfile.ZipFile(io.BytesIO(carrier_bytes)) as z:
            members = {n: z.read(n) for n in z.namelist() if not n.endswith("README.md")}
        carrier_bytes = _intake_zip_bytes(members)
        packet["carrier"].update(sha256=_intake_sha(carrier_bytes), size_bytes=len(carrier_bytes))
    folder = h.root / "negative_inputs" / mutation
    folder.mkdir(parents=True)
    p = folder / "packet.json"; p.write_bytes(_intake_render(packet))
    c = folder / "carrier.zip"; c.write_bytes(carrier_bytes)
    (folder / "intentional_change.json").write_bytes(_intake_render({"mutation": mutation,
        "original_packet_sha256": _intake_sha(f["packet"].read_bytes()),
        "original_carrier_sha256": _intake_sha(f["carrier"].read_bytes()),
        "mutated_packet_sha256": _intake_sha(p.read_bytes()), "mutated_carrier_sha256": _intake_sha(carrier_bytes)}))
    result = _intake_cli(h, "intake_negative_" + mutation, _intake_bridge_command(h, p, c), inputs=(p, c))
    assert result.returncode in (1, 2), result.stdout.decode()
    assert result.stdout == b""
    assert json.loads(result.stderr)["ok"] is False
    assert json.loads(result.stderr)["errors"]



def test_intake_schema_valid_foreign_runtime_is_not_the_subject(current_run_intake_reports):
    f = current_run_intake_reports
    h = f["harness"]
    packet = json.loads(f["runtime"].read_bytes())
    old_key = packet["subject"]["subject_run_key"]
    new_key = old_key.replace("GITHUB_RUN_ID=9001|", "GITHUB_RUN_ID=9002|")
    assert old_key != new_key
    packet = json.loads(json.dumps(packet).replace(old_key, new_key))
    packet["subject"]["workflow_run_id"] = 9002
    path = h.root / "external/foreign-runtime.json"
    path.write_bytes(_intake_render(packet))
    generic = _intake_cli(h, "intake_foreign_runtime_generic",
        [sys.executable, "-I", "-B", h.control / "tools/check_pulsemech_compute_runtime_observation_packet_v0.py",
         "--schema", h.control / "schemas/pulsemech_compute_runtime_observation_packet_v0.schema.json",
         "--packet", path], inputs=(path,))
    assert generic.returncode == 0, generic.stderr.decode()
    result = _intake_cli(h, "intake_foreign_runtime_bridge",
        _intake_bridge_command(h, f["packet"], f["carrier"], path), inputs=(f["packet"], f["carrier"], path))
    assert result.returncode != 0 and result.stdout == b""
    assert json.loads(result.stderr)["ok"] is False
    assert "runtime_packet_subject_context_mismatch" in result.stderr.decode()


# Executed-loader binding: unit checks below use minimal metadata deliberately;
# the CLI controls use the existing genuine producer/validator fixture instead.
def test_loader_binding_registers_exact_capture_before_execution(tmp_path, monkeypatch):
    bridge = ADAPTER_MODULE
    path = tmp_path / "loader.py"
    path.write_bytes(b"VALUE = 17\n")
    monkeypatch.setattr(bridge, "CURRENT_RUN_LOADER", path)
    packet = {"producer": {"producer_source_sha256": sha256_file(path)}}
    captures = {}
    captured = bridge._bind_current_run_loader_source(packet=packet, captures=captures)
    assert captures == {"current_run_loader": captured}
    assert captured.data == b"VALUE = 17\n"
    assert captured.sha256 == packet["producer"]["producer_source_sha256"]


@pytest.mark.parametrize("digest", [None, "", "g" * 64, "a" * 63, "a" * 65, True])
def test_loader_binding_rejects_missing_or_malformed_source_digest(tmp_path, monkeypatch, digest):
    bridge = ADAPTER_MODULE
    monkeypatch.setattr(bridge, "CURRENT_RUN_LOADER", tmp_path / "must-not-be-opened.py")
    captures = {}
    with pytest.raises(bridge.AdapterError, match="current_run_loader_source_digest_invalid"):
        bridge._bind_current_run_loader_source(
            packet={"producer": {"producer_source_sha256": digest}}, captures=captures,
        )
    assert captures == {}


@pytest.mark.parametrize("field", ["data", "sha256", "size_bytes"])
def test_loader_binding_rejects_inconsistent_supplied_capture(tmp_path, field):
    from dataclasses import replace
    bridge = ADAPTER_MODULE
    path = tmp_path / "loader.py"
    path.write_bytes(b"VALUE = 17\n")
    captured = bridge.capture_regular_file(path, label="test_loader")
    changes = {"data": b"VALUE = 18\n", "sha256": "0" * 64,
               "size_bytes": captured.size_bytes + 1}
    faulty = replace(captured, **{field: changes[field]})
    with pytest.raises(bridge.AdapterError, match="current_run_loader_source_mismatch"):
        bridge._bind_current_run_loader_source(
            packet={"producer": {"producer_source_sha256": captured.sha256}},
            captures={"current_run_loader": faulty},
        )


def test_loader_binding_executes_authenticated_buffer_not_replaced_path(tmp_path):
    bridge = ADAPTER_MODULE
    path = tmp_path / "loader.py"
    path.write_bytes(b"VALUE = 17\n")
    captured = bridge.capture_regular_file(path, label="test_loader")
    path.write_bytes(b"raise RuntimeError('replacement must not execute')\n")
    selected = bridge._bind_current_run_loader_source(
        packet={"producer": {"producer_source_sha256": captured.sha256}},
        captures={"current_run_loader": captured},
    )
    assert selected is captured
    module = bridge.load_module_from_capture(selected, "loader_binding_exact_buffer_test")
    assert module.VALUE == 17
    assert module.__pulsemech_source_sha256__ == captured.sha256


def _loader_binding_separate_control(fixture, tmp_path):
    """Copy observer only; the subject Git repository and its inputs stay fixed."""
    observer = tmp_path / "observer"
    shutil.copytree(fixture["harness"].control, observer)
    records = tmp_path / "records"
    records.mkdir()
    return types.SimpleNamespace(control=observer, subject=fixture["harness"].subject,
                                 root=records)


def test_loader_binding_real_distinct_observer_identical_bytes(current_run_intake_reports, tmp_path):
    f = current_run_intake_reports
    h = _loader_binding_separate_control(f, tmp_path)
    assert h.control.resolve() != h.subject.resolve()
    packet = json.loads(f["packet"].read_bytes())
    assert sha256_file(h.control / _INTAKE_WRAPPER) == packet["producer"]["producer_source_sha256"]
    before = _intake_inventory(h.control)
    result = _intake_cli(h, "loader_binding_identical_observer",
        _intake_bridge_command(h, f["packet"], f["carrier"]),
        inputs=(f["packet"], f["carrier"]))
    assert result.returncode == 0, result.stderr.decode()
    assert result.stdout == f["artifact"].read_bytes()
    assert before == _intake_inventory(h.control)


@pytest.mark.parametrize("mode", ["artifact", "runtime", "forged_packet_digest"])
def test_loader_binding_real_cli_rejects_observer_substitution(current_run_intake_reports, tmp_path, mode):
    f = current_run_intake_reports
    h = _loader_binding_separate_control(f, tmp_path)
    loader = h.control / _INTAKE_WRAPPER
    original = loader.read_bytes()
    marker = tmp_path / "must-not-execute.txt"
    injected = (b"\n# Deliberately substituted observer loader, original checks retained.\n"
                + f"Path({str(marker)!r}).write_text('executed', encoding='utf-8')\n".encode())
    loader.write_bytes(original + injected)
    (h.root / "loader_original.py").write_bytes(original)
    (h.root / "loader_substituted.py").write_bytes(original + injected)
    packet_path = f["packet"]
    if mode == "forged_packet_digest":
        packet = json.loads(packet_path.read_bytes())
        packet["producer"]["producer_source_sha256"] = sha256_file(loader)
        packet_path = tmp_path / "forged-packet.json"
        packet_path.write_bytes(_intake_render(packet))
    runtime = f["runtime"] if mode == "runtime" else None
    inputs = (packet_path, f["carrier"]) + ((runtime,) if runtime else ())
    before = _intake_inventory(h.control)
    (h.root / "sources_before.json").write_bytes(_intake_render(before))
    result = _intake_cli(h, "loader_binding_substitution_" + mode,
        _intake_bridge_command(h, packet_path, f["carrier"], runtime), inputs=inputs)
    after = _intake_inventory(h.control)
    (h.root / "sources_after.json").write_bytes(_intake_render(after))
    assert before == after
    assert result.returncode == 1, result.stderr.decode()
    assert result.stdout == b""
    assert not marker.exists(), "the different loader executed before rejection"
    error = ("producer_source_digest_mismatch" if mode == "forged_packet_digest"
             else "current_run_loader_source_mismatch")
    assert error in result.stderr.decode()


def test_loader_binding_real_validated_inputs_reject_dependency_override(current_run_intake_reports, tmp_path):
    f = current_run_intake_reports
    bridge = ADAPTER_MODULE
    path = tmp_path / "wrong-loader.py"
    path.write_bytes(b"raise RuntimeError('unbound capture must not execute')\n")
    deps = bridge._capture_dependencies()
    deps["current_run_loader"] = bridge.capture_regular_file(path, label="substituted_dependency")
    with pytest.raises(bridge.AdapterError, match="current_run_loader_source_mismatch"):
        bridge.build_from_captured_inputs(
            packet_capture=bridge.capture_regular_file(f["packet"], label="packet"),
            carrier_capture=bridge.capture_regular_file(f["carrier"], label="carrier"),
            repository_root=f["harness"].subject,
            analysis_run_key="OFFLINE_ANALYSIS=dependency-substitution-control",
            dependency_captures=deps,
        )


if __name__ == "__main__":
    check_build_pulsemech_compute_binding_report_from_subject_input_v0()

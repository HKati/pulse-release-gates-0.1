#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
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
    result = run_adapter()
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    assert result.stdout == fixed_stdout

    report = strict_json_text(result.stdout, label="bridge report")
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


def test_bridge_is_repeat_deterministic(fixed_stdout: str) -> None:
    first = run_adapter()
    second = run_adapter()
    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == ""
    assert first.stdout == second.stdout == fixed_stdout


def test_bridge_writes_no_repository_entry(fixed_stdout: str) -> None:
    before = snapshot_repository_tree()
    result = run_adapter()
    after = snapshot_repository_tree()
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == fixed_stdout
    assert before == after


def test_relative_cli_paths_work_from_external_directory(
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
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    assert result.stdout == fixed_stdout


def test_invalid_role_binding_is_rejected(tmp_path: Path) -> None:
    packet = strict_json_text(PACKET.read_text(encoding="utf-8"), label="packet")
    packet["role_bindings"]["final_status"] = "artifact:missing"
    changed = tmp_path / "packet.json"
    changed.write_text(render_json(packet), encoding="utf-8", newline="\n")

    result = run_adapter(packet=changed)
    assert_adapter_failure(result, "subject_input_packet_rejected")


def test_non_observed_packet_is_rejected(tmp_path: Path) -> None:
    packet = strict_json_text(PACKET.read_text(encoding="utf-8"), label="packet")
    packet["record_status"] = "example"
    changed = tmp_path / "packet.json"
    changed.write_text(render_json(packet), encoding="utf-8", newline="\n")

    result = run_adapter(packet=changed)
    assert_adapter_failure(result, "subject_input_packet_not_observed")


def test_carrier_drift_is_rejected(tmp_path: Path) -> None:
    changed = tmp_path / "carrier.zip"
    shutil.copy2(CARRIER, changed)
    payload = bytearray(changed.read_bytes())
    payload[-1] ^= 0x01
    changed.write_bytes(payload)

    result = run_adapter(carrier=changed)
    assert_adapter_failure(result, "subject_input_packet_rejected")


def test_subject_run_cannot_be_analysis_run() -> None:
    packet = strict_json_text(PACKET.read_text(encoding="utf-8"), label="packet")
    result = run_adapter(
        analysis_run_key=packet["subject"]["subject_run_key"],
    )
    assert_adapter_failure(result, "analysis_run_key_invalid_or_matches_subject")


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

    rendered = ADAPTER_MODULE.build_from_captured_inputs(
        packet_capture=captured_packet,
        carrier_capture=captured_carrier,
        repository_root=ROOT,
        analysis_run_key=ANALYSIS_RUN_KEY,
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
        ADAPTER_MODULE.build_from_captured_inputs(
            packet_capture=captured_packet,
            carrier_capture=captured_carrier,
            repository_root=ROOT,
            analysis_run_key=ANALYSIS_RUN_KEY,
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

    rendered = ADAPTER_MODULE.build_from_captured_inputs(
        packet_capture=captured_packet,
        carrier_capture=captured_carrier,
        repository_root=ROOT,
        analysis_run_key=ANALYSIS_RUN_KEY,
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
        ADAPTER_MODULE.build_from_captured_inputs(
            packet_capture=captured_packet,
            carrier_capture=captured_carrier,
            repository_root=ROOT,
            analysis_run_key=ANALYSIS_RUN_KEY,
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


if __name__ == "__main__":
    check_build_pulsemech_compute_binding_report_from_subject_input_v0()

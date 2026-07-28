#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import types
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = (
    ROOT
    / "tools"
    / "build_pulsemech_compute_binding_report_from_subject_input_v0.py"
)
FIXED_BUILDER = ROOT / "tools" / "build_pulsemech_compute_binding_report_v0.py"
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


def snapshot(paths: tuple[Path, ...]) -> dict[str, tuple[int, str]]:
    return {
        str(path.resolve()): (path.stat().st_size, sha256_file(path))
        for path in paths
    }


def tree_snapshot(root: Path) -> dict[str, tuple[Any, ...]]:
    result: dict[str, tuple[Any, ...]] = {}
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            result[relative] = ("symlink", os.readlink(path))
        elif path.is_dir():
            result[relative] = ("directory",)
        elif path.is_file():
            result[relative] = ("file", path.stat().st_size, sha256_file(path))
        else:
            result[relative] = ("other", path.lstat().st_mode)
    return result


def repository_entry_snapshot(root: Path) -> tuple[tuple[str, str], ...]:
    entries: list[tuple[str, str]] = []
    for directory, names, filenames in os.walk(root, followlinks=False):
        directory_path = Path(directory)
        relative_directory = directory_path.relative_to(root)
        if relative_directory.parts and relative_directory.parts[0] == ".git":
            names[:] = []
            continue
        names[:] = sorted(name for name in names if name != ".git")
        for name in names:
            path = directory_path / name
            relative = path.relative_to(root).as_posix()
            entries.append((relative, "symlink" if path.is_symlink() else "directory"))
        for name in sorted(filenames):
            path = directory_path / name
            relative = path.relative_to(root).as_posix()
            entries.append((relative, "symlink" if path.is_symlink() else "file"))
    return tuple(entries)


def import_adapter_module() -> Any:
    module_name = "pulsemech_subject_input_report_adapter_v0_under_test"
    module = types.ModuleType(module_name)
    module.__file__ = str(ADAPTER)
    module.__cached__ = None
    module.__loader__ = None
    module.__package__ = ""
    module.__spec__ = None
    sys.modules[module_name] = module
    code = compile(ADAPTER.read_bytes(), str(ADAPTER), "exec", dont_inherit=True)
    exec(code, module.__dict__)
    return module


ADAPTER_MODULE = import_adapter_module()


def run_fixed_builder(
    *,
    output: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
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
    ]
    if output is not None:
        command.extend(["--output", str(output)])
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def run_adapter(
    *,
    packet: Path = PACKET,
    carrier: Path = CARRIER,
    analysis_run_key: str = ANALYSIS_RUN_KEY,
    output: Path | None = None,
    temp_root: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(ADAPTER),
        "--packet",
        str(packet),
        "--carrier",
        str(carrier),
        "--repository-root",
        str(ROOT),
        "--analysis-run-key",
        analysis_run_key,
    ]
    if output is not None:
        command.extend(["--output", str(output)])
    if temp_root is not None:
        command.extend(["--temp-root", str(temp_root)])
    return subprocess.run(
        command,
        cwd=ROOT,
        env=env,
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


@pytest.fixture(scope="module")
def fixed_stdout() -> str:
    result = run_fixed_builder()
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    strict_json_text(result.stdout, label="fixed-source report")
    return result.stdout


def test_subject_input_adapter_matches_fixed_builder_byte_for_byte(
    tmp_path: Path,
    fixed_stdout: str,
) -> None:
    output = tmp_path / "report.json"
    result = run_adapter(output=output)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    assert result.stdout == fixed_stdout
    assert output.read_text(encoding="utf-8") == fixed_stdout

    report = strict_json_text(result.stdout, label="adapter report")
    assert report["tool"]["id"] == "build_pulsemech_compute_binding_report_v0"
    assert report["analysis_boundary"]["analysis_run_key"] == ANALYSIS_RUN_KEY
    assert report["subject"]["workflow_run_number"] == 6066
    assert report["subject"]["decision"] == "ALLOW"
    assert report["ok"] is True
    assert report["errors"] == []


def test_subject_input_adapter_is_repeat_deterministic(
    fixed_stdout: str,
) -> None:
    first = run_adapter()
    second = run_adapter()

    assert first.returncode == 0, first.stdout + first.stderr
    assert second.returncode == 0, second.stdout + second.stderr
    assert first.stderr == second.stderr == ""
    assert first.stdout == second.stdout == fixed_stdout


def test_subject_input_adapter_preserves_every_protected_input(
    fixed_stdout: str,
) -> None:
    protected = (
        PACKET,
        CARRIER,
        PACKET_SCHEMA,
        PACKET_VALIDATOR,
        REPORT_SCHEMA,
        REPORT_VALIDATOR,
        FIXED_BUILDER,
        ADAPTER,
    )
    before = snapshot(protected)
    tools_before = tree_snapshot(ROOT / "tools")
    result = run_adapter()
    after = snapshot(protected)
    tools_after = tree_snapshot(ROOT / "tools")

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == fixed_stdout
    assert before == after
    assert tools_before == tools_after


def test_module_loading_does_not_create_or_consume_bytecode(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "synthetic_module.py"
    module_path.write_text("VALUE = 17\n", encoding="utf-8")

    # A conflicting cache file must not be consumed, and no cache may be written.
    cache_dir = tmp_path / "__pycache__"
    cache_dir.mkdir()
    poisoned_cache = cache_dir / "synthetic_module.cpython-313.pyc"
    poisoned_cache.write_bytes(b"not-valid-bytecode")
    before = tree_snapshot(tmp_path)

    module_name = "pulsemech_synthetic_no_bytecode_module_v0"
    try:
        module = ADAPTER_MODULE.load_module(module_path, module_name)
        assert module.VALUE == 17
        assert module.__cached__ is None
    finally:
        sys.modules.pop(module_name, None)

    assert tree_snapshot(tmp_path) == before



def test_repository_local_temp_environment_is_not_used(
    fixed_stdout: str,
) -> None:
    environment = dict(os.environ)
    environment.update(
        {
            "TMPDIR": str(ROOT),
            "TEMP": str(ROOT),
            "TMP": str(ROOT),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    before = repository_entry_snapshot(ROOT)
    result = run_adapter(env=environment)
    after = repository_entry_snapshot(ROOT)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    assert result.stdout == fixed_stdout
    assert before == after


def test_explicit_temp_root_inside_repository_is_rejected() -> None:
    result = run_adapter(temp_root=ROOT)
    assert_adapter_failure(result, "temp_root_inside_tool_repository")


def test_bound_temp_environment_controls_parent_and_subprocess(
    tmp_path: Path,
) -> None:
    safe_root = tmp_path / "safe-temp"
    safe_root.mkdir()
    previous = tempfile.tempdir
    with ADAPTER_MODULE.bound_temp_environment(safe_root):
        assert tempfile.gettempdir() == str(safe_root)
        assert os.environ["PYTHONDONTWRITEBYTECODE"] == "1"
        result = subprocess.run(
            [sys.executable, "-c", "import tempfile; print(tempfile.gettempdir())"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == str(safe_root)
    assert tempfile.tempdir == previous


def test_output_parent_swap_after_revalidation_is_blocked_by_no_follow_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if not ADAPTER_MODULE.secure_output_supported():
        pytest.skip("secure directory-handle output is unavailable")

    output_parent = tmp_path / "output-parent"
    displaced_parent = tmp_path / "output-parent-original"
    output_parent.mkdir()
    output = output_parent / ".pulsemech-output-race-regression.json"
    protected_target = ROOT / output.name
    assert not protected_target.exists()

    original_revalidate = ADAPTER_MODULE.reject_unsafe_output
    swapped = False

    def revalidate_then_swap(*args: Any, **kwargs: Any) -> None:
        nonlocal swapped
        original_revalidate(*args, **kwargs)
        if not swapped:
            output_parent.rename(displaced_parent)
            output_parent.symlink_to(ROOT, target_is_directory=True)
            swapped = True

    monkeypatch.setattr(ADAPTER_MODULE, "reject_unsafe_output", revalidate_then_swap)
    with pytest.raises(
        ADAPTER_MODULE.AdapterError,
        match="output_parent_component_open_failed",
    ):
        ADAPTER_MODULE.write_atomic_text(
            output,
            "{}\n",
            packet=PACKET,
            carrier=CARRIER,
            repository_root=ROOT,
        )

    assert swapped is True
    assert not protected_target.exists()
    assert not (displaced_parent / output.name).exists()


def test_output_commit_uses_bound_no_follow_directory_operations() -> None:
    source = ADAPTER.read_text(encoding="utf-8")
    assert "os.O_NOFOLLOW" in source
    assert "dir_fd=parent_fd" in source
    assert "src_dir_fd=parent_fd" in source
    assert "dst_dir_fd=parent_fd" in source
    assert "output_parent_changed_before_commit" in source


def test_subject_input_adapter_rejects_unresolved_role_binding(
    tmp_path: Path,
) -> None:
    packet = strict_json_text(PACKET.read_text(encoding="utf-8"), label="packet")
    packet["role_bindings"]["final_status"] = "artifact:missing"
    changed = tmp_path / "packet.json"
    changed.write_text(render_json(packet), encoding="utf-8")

    result = run_adapter(packet=changed)
    assert_adapter_failure(result, "subject_input_packet_rejected")


def test_subject_input_adapter_rejects_carrier_drift(
    tmp_path: Path,
) -> None:
    changed = tmp_path / CARRIER.name
    shutil.copy2(CARRIER, changed)
    payload = bytearray(changed.read_bytes())
    payload[-1] ^= 0x01
    changed.write_bytes(payload)

    result = run_adapter(carrier=changed)
    assert_adapter_failure(result, "subject_input_packet_rejected")


def test_subject_input_adapter_rejects_subject_run_as_analysis_run() -> None:
    packet = strict_json_text(PACKET.read_text(encoding="utf-8"), label="packet")
    subject_run_key = packet["subject"]["subject_run_key"]

    result = run_adapter(analysis_run_key=subject_run_key)
    assert_adapter_failure(result, "analysis_run_key_invalid_or_matches_subject")


def test_relative_cli_paths_are_resolved_before_validator_cwd_change(
    tmp_path: Path,
    fixed_stdout: str,
) -> None:
    packet = tmp_path / "packet.json"
    carrier = tmp_path / "carrier.zip"
    output = tmp_path / "report.json"
    shutil.copy2(PACKET, packet)
    shutil.copy2(CARRIER, carrier)

    repository_root = os.path.relpath(ROOT, tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            str(ADAPTER),
            "--packet",
            packet.name,
            "--carrier",
            carrier.name,
            "--repository-root",
            repository_root,
            "--analysis-run-key",
            ANALYSIS_RUN_KEY,
            "--output",
            output.name,
        ],
        cwd=tmp_path,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    assert result.stdout == fixed_stdout
    assert output.read_text(encoding="utf-8") == fixed_stdout


@pytest.mark.parametrize(
    "basename",
    (
        "STATUS.JSON",
        "Release_Decision_v0.JSON",
        "RELEASE_AUTHORITY_V0.JSON",
        "PulseMech_Compute_Subject_Input_Packet_V0.Json",
    ),
)
def test_authority_surface_output_names_are_rejected_case_insensitively(
    tmp_path: Path,
    basename: str,
) -> None:
    output = tmp_path / basename
    with pytest.raises(
        ADAPTER_MODULE.AdapterError,
        match="refusing_authority_surface_output",
    ):
        ADAPTER_MODULE.reject_unsafe_output(
            output,
            packet=PACKET,
            carrier=CARRIER,
            repository_root=ROOT,
        )
    assert not output.exists()


def test_output_inside_subject_repository_is_rejected_without_write() -> None:
    output = ROOT / ".pulsemech-subject-input-adapter-should-not-write.json"
    assert not output.exists()
    with pytest.raises(
        ADAPTER_MODULE.AdapterError,
        match="refusing_output_inside_tool_repository",
    ):
        ADAPTER_MODULE.reject_unsafe_output(
            output,
            packet=PACKET,
            carrier=CARRIER,
            repository_root=ROOT,
        )
    assert not output.exists()


def test_adapter_delegates_to_one_existing_graph_builder() -> None:
    source = ADAPTER.read_text(encoding="utf-8")

    assert "fixed_builder.build_report(" in source
    assert "def build_report(" not in source
    assert "def make_compute_node(" not in source
    assert "def make_state_node(" not in source
    assert "def make_edge(" not in source


def test_adapter_cli_help_constructs() -> None:
    result = subprocess.run(
        [sys.executable, str(ADAPTER), "--help"],
        cwd=ROOT,
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
    assert "--temp-root" in result.stdout
    assert "--analysis-run-key" in result.stdout


def test_adapter_is_registered_exactly_once_in_tools_tests() -> None:
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
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))


if __name__ == "__main__":
    check_build_pulsemech_compute_binding_report_from_subject_input_v0()

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "PULSE_safe_pack_v0" / "tools" / "check_shadow_layer_registry.py"
FIXTURES = ROOT / "tests" / "fixtures" / "shadow_layer_registry_v0"
REGISTRY = ROOT / "shadow_layer_registry_v0.yml"


def _run(input_path: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(SCRIPT), "--input", str(input_path), *extra_args]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _stdout_json(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return json.loads(result.stdout)


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_checker_module():
    spec = importlib.util.spec_from_file_location("check_shadow_layer_registry", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_registry_yaml_is_valid() -> None:
    result = _run(REGISTRY)
    assert result.returncode == 0, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is True
    assert payload["neutral"] is False
    assert payload["registry_version"] == "shadow_layer_registry_v0"
    assert payload["layer_count"] >= 1


def test_pass_fixture_is_valid() -> None:
    result = _run(FIXTURES / "pass.json")
    assert result.returncode == 0, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is True
    assert payload["neutral"] is False
    assert payload["registry_version"] == "shadow_layer_registry_v0"
    assert payload["layer_count"] == 1


def test_missing_input_is_neutral_with_if_input_present() -> None:
    result = _run(FIXTURES / "does_not_exist.json", "--if-input-present")
    assert result.returncode == 0, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is True
    assert payload["neutral"] is True
    assert payload["registry_version"] is None
    assert payload["layer_count"] == 0


def test_missing_input_fails_without_if_input_present() -> None:
    result = _run(FIXTURES / "does_not_exist.json")
    assert result.returncode == 1

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert payload["neutral"] is False
    assert any(issue["path"] == "input" for issue in payload["errors"])


def test_duplicate_layer_id_fixture_fails() -> None:
    result = _run(FIXTURES / "duplicate_layer_id.json")
    assert result.returncode == 1, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert any(
        issue["path"] == "layers[1].layer_id" and "duplicate layer_id" in issue["message"]
        for issue in payload["errors"]
    )


def test_release_required_non_normative_fixture_fails() -> None:
    result = _run(FIXTURES / "release_required_non_normative.json")
    assert result.returncode == 1, result.stdout + result.stderr

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert any(
        issue["path"] == "layers[0].normative"
        and "current_stage=release-required requires normative=true" in issue["message"]
        for issue in payload["errors"]
    )


def test_normative_true_requires_release_required_stage(tmp_path: Path) -> None:
    fixture = _load_fixture("pass.json")
    layer = fixture["layers"][0]
    layer["normative"] = True

    path = tmp_path / "invalid_normative_true_without_release_required.json"
    _write_json(path, fixture)

    result = _run(path)
    assert result.returncode == 1

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert any(
        issue["path"] == "layers[0].current_stage"
        and "normative=true requires current_stage=release-required" in issue["message"]
        for issue in payload["errors"]
    )


def test_target_stage_must_not_be_lower_than_current_stage(tmp_path: Path) -> None:
    fixture = _load_fixture("pass.json")
    layer = fixture["layers"][0]
    layer["current_stage"] = "advisory"
    layer["target_stage"] = "research"

    path = tmp_path / "invalid_target_stage_lower_than_current.json"
    _write_json(path, fixture)

    result = _run(path)
    assert result.returncode == 1

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert any(
        issue["path"] == "layers[0].target_stage"
        and "target_stage must not be lower than current_stage" in issue["message"]
        for issue in payload["errors"]
    )


def test_higher_stage_requires_schema_field(tmp_path: Path) -> None:
    fixture = _load_fixture("pass.json")
    layer = fixture["layers"][0]
    del layer["schema"]

    path = tmp_path / "invalid_missing_schema_for_shadow_contracted.json"
    _write_json(path, fixture)

    result = _run(path)
    assert result.returncode == 1

    payload = _stdout_json(result)
    assert payload["ok"] is False
    assert any(
        issue["path"] == "layers[0].schema"
        and "required when current_stage is shadow-contracted" in issue["message"]
        for issue in payload["errors"]
    )


def test_json_registry_loads_without_pyyaml_when_yaml_is_none() -> None:
    module = _load_checker_module()
    original_yaml = module.yaml
    module.yaml = None
    try:
        obj = module._load_registry(FIXTURES / "pass.json")
    finally:
        module.yaml = original_yaml

    assert isinstance(obj, dict)
    assert obj["version"] == "shadow_layer_registry_v0"
    assert obj["layers"][0]["layer_id"] == "relational_gain_shadow"

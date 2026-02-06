#!/usr/bin/env python3
"""
Smoke test: paradox diagram v0 renderer.

What this locks in:
- We can generate a contract-valid paradox_diagram_input_v0.json.
- Contract checker accepts it.
- Renderer produces a non-empty SVG.

Run (direct):
  python tests/test_paradox_diagram_renderer_v0_smoke.py

Run (pytest):
  pytest -q tests/test_paradox_diagram_renderer_v0_smoke.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def _run(cmd: list[str]) -> None:
    subprocess.check_call(cmd)


def _schema_const_or_first_enum(schema_obj: dict, key: str, default: str) -> str:
    props = (schema_obj.get("properties") or {})
    spec = (props.get(key) or {})
    if isinstance(spec, dict):
        if "const" in spec and isinstance(spec["const"], str):
            return spec["const"]
        enum = spec.get("enum")
        if isinstance(enum, list) and enum and isinstance(enum[0], str):
            return enum[0]
    return default


def _build_contract_valid_input(root: Path) -> dict:
    """
    Build a minimal input that is BOTH schema-ish and contract-valid.

    IMPORTANT:
    - schema uses schema_version + decision_key + metrics{...}
    - contract additionally requires decision_raw (even if schema doesn't)
    """
    schema_path = root / "schemas" / "paradox_diagram_input_v0.schema.json"
    schema_obj = _read_json(schema_path)
    assert isinstance(schema_obj, dict), "schema must be a JSON object"

    schema_version = _schema_const_or_first_enum(schema_obj, "schema_version", "v0")
    # Prefer NORMAL when possible (common case); fall back to schema enum if present.
    decision_key = "NORMAL"
    decision_key_schema = _schema_const_or_first_enum(schema_obj, "decision_key", decision_key)
    if decision_key_schema:
        decision_key = decision_key_schema

    return {
        "schema_version": schema_version,
        "timestamp_utc": "2026-02-06T00:00:00+00:00",
        "shadow": True,
        "decision_key": decision_key,
        # Contract-required even if schema doesn't list it as required
        "decision_raw": decision_key,
        "metrics": {
            "settle_time_p95_ms": 10.0,
            "settle_time_budget_ms": 50.0,
            "downstream_error_rate": 0.02,
            "paradox_density": 0.1,
        },
    }


def _smoke() -> None:
    root = _repo_root()

    contract = root / "scripts" / "check_paradox_diagram_input_v0_contract.py"
    renderer = root / "tools" / "render_paradox_diagram_v0.py"

    assert contract.exists(), f"missing contract checker: {contract}"
    assert renderer.exists(), f"missing renderer: {renderer}"

    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        inp = base / "paradox_diagram_input_v0.json"
        out = base / "paradox_diagram_v0.svg"

        obj = _build_contract_valid_input(root)
        inp.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

        # Contract must pass (otherwise the smoke test doesn't test rendering at all)
        _run([sys.executable, str(contract), "--in", str(inp)])

        # Render must succeed
        _run([sys.executable, str(renderer), "--in", str(inp), "--out", str(out)])

        assert out.exists(), "renderer did not produce SVG"
        assert out.stat().st_size > 0, "renderer produced empty SVG"

        txt = out.read_text(encoding="utf-8")
        assert "<svg" in txt, "SVG output missing <svg tag"
        # Match the renderer's actual title string
        assert "PULSE - Paradox diagram (v0)" in txt, "SVG title marker not found"


# ---- pytest entrypoint ----
def test_paradox_diagram_renderer_v0_smoke() -> None:
    _smoke()


# ---- script entrypoint ----
def main() -> int:
    _smoke()
    print("OK: paradox diagram v0 renderer smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

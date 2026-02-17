#!/usr/bin/env python3
"""
Contract smoke test for run_all.py run_mode behavior.

Goals:
- run_all.py accepts --mode demo|core|prod and writes metrics.run_mode accordingly.
- invalid PULSE_RUN_MODE fails fast (argparse error, exit code 2).
- status_v1 schema requires metrics.run_mode with enum demo/core/prod (structure-level check).
"""

import json
import os
import pathlib
import subprocess
import sys
import tempfile


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
RUN_ALL = REPO_ROOT / "PULSE_safe_pack_v0" / "tools" / "run_all.py"
SCHEMA = REPO_ROOT / "schemas" / "status" / "status_v1.schema.json"
POLICY = REPO_ROOT / "pulse_gate_policy_v0.yml"


def _run_and_load(*, mode: str | None, extra_env: dict[str, str] | None = None):
    env = os.environ.copy()

    # Hermetic: do not inherit PULSE_RUN_MODE from the runner shell/CI environment.
    # run_all.py validates PULSE_RUN_MODE before parsing --mode, so an invalid inherited
    # value would break core/prod tests nondeterministically.
    env.pop("PULSE_RUN_MODE", None)

    if extra_env:
        env.update(extra_env)

    with tempfile.TemporaryDirectory() as td:
        env["PULSE_ARTIFACT_DIR"] = td

        cmd = [
            sys.executable,
            str(RUN_ALL),
            "--pack_dir",
            str(REPO_ROOT / "PULSE_safe_pack_v0"),
            "--gate_policy",
            str(POLICY),
        ]
        if mode is not None:
            cmd += ["--mode", mode]

        r = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        status_path = pathlib.Path(td) / "status.json"
        status = None
        if status_path.exists():
            status = json.loads(status_path.read_text(encoding="utf-8"))

        return r, status


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        print(f"ERROR: {msg}", file=sys.stderr)
        raise SystemExit(1)


def test_schema_requires_run_mode() -> None:
    _assert(SCHEMA.exists(), f"missing schema: {SCHEMA}")

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    props = schema.get("properties") or {}
    metrics = props.get("metrics") or {}

    req = metrics.get("required") or []
    _assert("run_mode" in req, "schema.metrics.required must include 'run_mode'")

    rm = (metrics.get("properties") or {}).get("run_mode") or {}
    enum = rm.get("enum") or []
    _assert(set(enum) == {"demo", "core", "prod"}, f"schema.metrics.run_mode.enum must be demo/core/prod, got: {enum}")


def test_run_all_core_mode() -> None:
    r, status = _run_and_load(mode="core")
    _assert(r.returncode == 0, f"run_all --mode core failed: rc={r.returncode}\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}")
    _assert(isinstance(status, dict), "status.json missing or invalid JSON in core mode")

    metrics = status.get("metrics") or {}
    _assert(metrics.get("run_mode") == "core", f"expected metrics.run_mode=core, got: {metrics.get('run_mode')}")
    v = str(status.get("version", ""))
    _assert("core" in v.lower(), f"expected status.version to indicate core mode, got: {v}")


def test_run_all_prod_mode() -> None:
    r, status = _run_and_load(mode="prod")
    _assert(r.returncode == 0, f"run_all --mode prod failed: rc={r.returncode}\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}")
    _assert(isinstance(status, dict), "status.json missing or invalid JSON in prod mode")

    metrics = status.get("metrics") or {}
    _assert(metrics.get("run_mode") == "prod", f"expected metrics.run_mode=prod, got: {metrics.get('run_mode')}")
    v = str(status.get("version", ""))
    _assert("demo" not in v.lower(), f"prod mode must not emit demo status.version, got: {v}")


def test_invalid_env_fails_fast() -> None:
    # This is the only test that intentionally sets PULSE_RUN_MODE.
    r, status = _run_and_load(mode=None, extra_env={"PULSE_RUN_MODE": "foobar"})
    _assert(r.returncode == 2, f"expected exit code 2 for invalid PULSE_RUN_MODE, got: {r.returncode}\nSTDERR:\n{r.stderr}")
    _assert(status is None, "status.json should not be written when argparse fails fast")


def main() -> None:
    test_schema_requires_run_mode()
    test_run_all_core_mode()
    test_run_all_prod_mode()
    test_invalid_env_fails_fast()
    print("OK: run_all run_mode contract smoke test passed")


if __name__ == "__main__":
    main()

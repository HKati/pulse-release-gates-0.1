#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_STATUS = REPO_ROOT / "PULSE_safe_pack_v0" / "artifacts" / "status.json"
DEFAULT_OUT = REPO_ROOT / "reports" / "operator_handoff_smoke.json"

RUN_ALL = REPO_ROOT / "PULSE_safe_pack_v0" / "tools" / "run_all.py"
CHECK_GATES = REPO_ROOT / "PULSE_safe_pack_v0" / "tools" / "check_gates.py"
POLICY_HELPER = REPO_ROOT / "tools" / "policy_to_require_args.py"
SHADOW_REGISTRY_CHECKER = (
    REPO_ROOT / "PULSE_safe_pack_v0" / "tools" / "check_shadow_layer_registry.py"
)

GATE_POLICY = REPO_ROOT / "pulse_gate_policy_v0.yml"
GATE_REGISTRY = REPO_ROOT / "pulse_gate_registry_v0.yml"
SHADOW_REGISTRY = REPO_ROOT / "shadow_layer_registry_v0.yml"


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _run_command(
    cmd: list[str],
    *,
    name: str,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    started = _utc_now()

    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=run_env,
    )

    return {
        "name": name,
        "cmd": cmd,
        "env_overrides": env or {},
        "started_utc": started,
        "finished_utc": _utc_now(),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "ok": proc.returncode == 0,
    }


def _materialize_gate_set(gate_set: str) -> tuple[list[str], dict[str, Any]]:
    result = _run_command(
        [
            sys.executable,
            str(POLICY_HELPER),
            "--policy",
            str(GATE_POLICY),
            "--set",
            gate_set,
            "--format",
            "space",
        ],
        name=f"materialize_{gate_set}",
    )

    gates = result["stdout"].split() if result["returncode"] == 0 else []
    return gates, result


def _unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []

    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)

    return out


def _required_files() -> list[Path]:
    return [
        RUN_ALL,
        CHECK_GATES,
        POLICY_HELPER,
        SHADOW_REGISTRY_CHECKER,
        GATE_POLICY,
        GATE_REGISTRY,
        SHADOW_REGISTRY,
    ]


def _file_inventory(paths: list[Path]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    for path in paths:
        out.append(
            {
                "path": _rel(path),
                "exists": path.exists(),
                "sha256": _sha256(path),
            }
        )

    return out


def _load_status_artifact(path: Path) -> dict[str, Any] | None:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    return obj if isinstance(obj, dict) else None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run an operator-handoff smoke check for the PULSE "
            "release-authority mechanics."
        )
    )

    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help="Path to write the handoff smoke JSON report.",
    )
    parser.add_argument(
        "--status",
        default=str(DEFAULT_STATUS),
        help=(
            "Path to the status.json artifact used for gate checking. "
            "For status-source=generate-core this is the requested generated output path."
        ),
    )
    parser.add_argument(
        "--status-source",
        choices=["generate-core", "existing"],
        default="generate-core",
        help=(
            "Use generate-core to create a local Core status artifact first, "
            "or existing to validate an already supplied status artifact."
        ),
    )
    parser.add_argument(
        "--gate-mode",
        choices=["core", "release-grade"],
        default="core",
        help=(
            "Gate reconstruction mode. Core uses core_required. "
            "Release-grade uses required + release_required and requires an "
            "existing release-grade status artifact."
        ),
    )
    parser.add_argument(
        "--include-tests",
        action="store_true",
        help="Also run selected pytest regression suites.",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = REPO_ROOT / out_path

    status_path = Path(args.status)
    if not status_path.is_absolute():
        status_path = REPO_ROOT / status_path

    commands: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[str] = []

    if args.gate_mode == "release-grade" and args.status_source == "generate-core":
        errors.append(
            "release-grade gate-mode requires --status-source existing; "
            "a generated Core artifact must not be treated as release-grade evidence."
        )

    required_files = _required_files()
    missing = [path for path in required_files if not path.exists()]
    for path in missing:
        errors.append(f"required file missing: {_rel(path)}")

    status_source: dict[str, Any] = {
        "mode": args.status_source,
        "status_path": _rel(status_path),
        "status_exists_before_run": status_path.exists(),
        "status_sha256_before_run": _sha256(status_path),
    }

    if not errors and args.status_source == "generate-core":
        artifact_dir = status_path.parent
        artifact_dir.mkdir(parents=True, exist_ok=True)

        generated_status_path = artifact_dir / "status.json"

        status_source["generated_artifact_dir"] = _rel(artifact_dir)
        status_source["generated_status_path"] = _rel(generated_status_path)

        commands.append(
            _run_command(
                [
                    sys.executable,
                    str(RUN_ALL),
                    "--mode",
                    "core",
                    "--pack_dir",
                    str(REPO_ROOT / "PULSE_safe_pack_v0"),
                    "--gate_policy",
                    str(GATE_POLICY),
                ],
                name="generate_core_status",
                env={"PULSE_ARTIFACT_DIR": str(artifact_dir)},
            )
        )

        if commands[-1]["returncode"] != 0:
            errors.append("failed to generate local Core status artifact")
        elif not generated_status_path.exists():
            errors.append(
                f"generated status artifact missing: {_rel(generated_status_path)}"
            )
        elif generated_status_path.resolve() != status_path.resolve():
            shutil.copyfile(generated_status_path, status_path)
            warnings.append(
                "copied generated Core status artifact from "
                f"{_rel(generated_status_path)} to requested --status path {_rel(status_path)}"
            )

    status_source["status_exists_after_generation"] = status_path.exists()
    status_source["status_sha256_after_generation"] = _sha256(status_path)

    if not status_path.exists():
        errors.append(f"status artifact missing: {_rel(status_path)}")

    if not errors and args.gate_mode == "release-grade":
        status_obj = _load_status_artifact(status_path)
        if status_obj is None:
            errors.append(f"status artifact is not a JSON object: {_rel(status_path)}")
        else:
            metrics = status_obj.get("metrics")
            run_mode = metrics.get("run_mode") if isinstance(metrics, dict) else None

            if run_mode != "prod":
                errors.append(
                    "release-grade gate-mode requires metrics.run_mode=prod; "
                    f"found {run_mode!r}."
                )

            if isinstance(metrics, dict) and "gate_policy_sha256" in metrics:
                status_policy_sha = metrics.get("gate_policy_sha256")
                current_policy_sha = _sha256(GATE_POLICY)

                if status_policy_sha != current_policy_sha:
                    errors.append(
                        "release-grade gate-mode requires metrics.gate_policy_sha256 "
                        "to match the current declared gate policy; "
                        f"found {status_policy_sha!r}, expected {current_policy_sha!r}."
                    )

            if isinstance(metrics, dict) and "gate_policy_path" in metrics:
                status_policy_path = metrics.get("gate_policy_path")
                current_policy_path = _rel(GATE_POLICY)

                if status_policy_path != current_policy_path:
                    errors.append(
                        "release-grade gate-mode requires metrics.gate_policy_path "
                        "to match the current declared gate policy path; "
                        f"found {status_policy_path!r}, expected {current_policy_path!r}."
                    )

            diagnostics = status_obj.get("diagnostics")
            if not isinstance(diagnostics, dict):
                diagnostics = {}

            gates_stubbed = diagnostics.get("gates_stubbed")
            if gates_stubbed is not False:
                errors.append(
                    "release-grade gate-mode requires diagnostics.gates_stubbed=false; "
                    f"found {gates_stubbed!r}."
                )
                errors.append("release-grade gate-mode rejects stubbed status evidence.")

            scaffold = diagnostics.get("scaffold")
            if scaffold is True:
                errors.append(
                    "release-grade gate-mode requires diagnostics.scaffold!=true; "
                    f"found {scaffold!r}."
                )
                errors.append("release-grade gate-mode rejects scaffold status evidence.")

            if "stub_profile" in diagnostics:
                errors.append(
                    "release-grade gate-mode requires diagnostics.stub_profile to be absent; "
                    f"found {diagnostics.get('stub_profile')!r}."
                )
                errors.append(
                    "release-grade gate-mode rejects stub-profiled status evidence."
                )

    materialized_gate_sets: dict[str, list[str]] = {}
    effective_required_gates: list[str] = []

    if not errors:
        if args.gate_mode == "core":
            core_gates, materialize_result = _materialize_gate_set("core_required")
            commands.append(materialize_result)

            if materialize_result["returncode"] != 0:
                errors.append("failed to materialize core_required gate set")
            else:
                materialized_gate_sets["core_required"] = core_gates
                effective_required_gates = core_gates
        else:
            required_gates, required_result = _materialize_gate_set("required")
            release_gates, release_result = _materialize_gate_set("release_required")
            commands.extend([required_result, release_result])

            if required_result["returncode"] != 0:
                errors.append("failed to materialize required gate set")
            if release_result["returncode"] != 0:
                errors.append("failed to materialize release_required gate set")

            if not errors:
                materialized_gate_sets["required"] = required_gates
                materialized_gate_sets["release_required"] = release_gates
                effective_required_gates = _unique_preserve_order(
                    [*required_gates, *release_gates]
                )

    if not errors and args.status_source == "existing":
        warnings.append(
            "status-source=existing was selected; generation step was skipped by design."
        )

    if not errors:
        commands.append(
            _run_command(
                [
                    sys.executable,
                    str(CHECK_GATES),
                    "--status",
                    str(status_path),
                    "--required",
                    *effective_required_gates,
                ],
                name=f"check_gates_{args.gate_mode}",
            )
        )

        if commands[-1]["returncode"] != 0:
            errors.append(f"gate check failed in {args.gate_mode} mode")

    if not errors:
        commands.append(
            _run_command(
                [
                    sys.executable,
                    str(SHADOW_REGISTRY_CHECKER),
                    "--registry",
                    str(SHADOW_REGISTRY),
                    "--gate-registry",
                    str(GATE_REGISTRY),
                    "--policy",
                    str(GATE_POLICY),
                ],
                name="check_shadow_layer_registry",
            )
        )

        if commands[-1]["returncode"] != 0:
            errors.append("shadow layer registry check failed")

    status_source["status_exists_after_run"] = status_path.exists()
    status_source["status_sha256_after_run"] = _sha256(status_path)

    payload: dict[str, Any] = {
        "ok": not errors,
        "generated_utc": _utc_now(),
        "gate_mode": args.gate_mode,
        "status_source": status_source,
        "materialized_gate_sets": materialized_gate_sets,
        "effective_required_gates": effective_required_gates,
        "required_files": _file_inventory(required_files),
        "status_file_inventory": _file_inventory([status_path]),
        "commands": commands,
        "warnings": warnings,
        "errors": errors,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

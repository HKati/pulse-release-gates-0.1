#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
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


def _run_command(cmd: list[str], *, name: str) -> dict[str, Any]:
    started = _utc_now()
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    return {
        "name": name,
        "cmd": cmd,
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
            "For status-source=generate-core this is the generated output path."
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

    status_source = {
        "mode": args.status_source,
        "status_path": _rel(status_path),
        "status_exists_before_run": status_path.exists(),
    }

    if not errors and args.status_source == "generate-core":
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
            )
        )

        if commands[-1]["returncode"] != 0:
            errors.append("failed to generate local Core status artifact")

    if not status_path.exists():
        errors.append(f"status artifact missing: {_rel(status_path)}")

    materialized_gate_sets: dict[str, list[str]] = {}

    if not errors:
        if args.gate_mode == "core":
            core_required, cmd = _materialize_gate_set("core_required")
            commands.append(cmd)
            materialized_gate_sets["core_required"] = core_required

            required_gates = core_required

            if not required_gates:
                errors.append("core_required materialized to an empty gate set")

        else:
            required, cmd_required = _materialize_gate_set("required")
            release_required, cmd_release = _materialize_gate_set("release_required")

            commands.append(cmd_required)
            commands.append(cmd_release)

            materialized_gate_sets["required"] = required
            materialized_gate_sets["release_required"] = release_required

            required_gates = _unique_preserve_order(required + release_required)

            if not required:
                errors.append("required materialized to an empty gate set")
            if not release_required:
                errors.append("release_required materialized to an empty gate set")

    else:
        required_gates = []

    if not errors:
        commands.append(
            _run_command(
                [
                    sys.executable,
                    str(CHECK_GATES),
                    "--status",
                    str(status_path),
                    "--require",
                    *required_gates,
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
                    "--input",
                    str(SHADOW_REGISTRY),
                ],
                name="check_shadow_layer_registry",
            )
        )

        if commands[-1]["returncode"] != 0:
            errors.append("shadow layer registry validation failed")

    if not errors and args.include_tests:
        test_targets = [
            "tests/test_check_shadow_layer_registry.py",
            "tests/test_check_epf_shadow_run_manifest_contract.py",
            "tests/test_check_epf_paradox_summary_contract.py",
        ]

        commands.append(
            _run_command(
                [sys.executable, "-m", "pytest", "-q", *test_targets],
                name="pytest_handoff_regressions",
            )
        )

        if commands[-1]["returncode"] != 0:
            errors.append("handoff regression pytest targets failed")

    if args.status_source == "existing" and not status_source["status_exists_before_run"]:
        warnings.append(
            "status-source=existing was selected, but the status artifact did not "
            "exist before this smoke run."
        )

    report = {
        "ok": len(errors) == 0,
        "created_utc": _utc_now(),
        "repo_root": str(REPO_ROOT),
        "gate_mode": args.gate_mode,
        "status_source": status_source,
        "materialized_gate_sets": materialized_gate_sets,
        "effective_required_gates": required_gates,
        "files": _file_inventory(required_files + [status_path]),
        "commands": commands,
        "warnings": warnings,
        "errors": errors,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2, sort_keys=True))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_PACK_DIR = REPO_ROOT / "PULSE_safe_pack_v0"
PACK_DIR = pathlib.Path(os.environ.get("PACK_DIR", str(DEFAULT_PACK_DIR)))
RUN_ALL = PACK_DIR / "tools" / "run_all.py"
VALIDATE = REPO_ROOT / "tools" / "validate_status_schema.py"
JUNIT_EXPORTER = PACK_DIR / "tools" / "status_to_junit.py"
SARIF_EXPORTER = PACK_DIR / "tools" / "status_to_sarif.py"
SCHEMA = REPO_ROOT / "schemas" / "status" / "status_v1.schema.json"
POLICY = REPO_ROOT / "pulse_gate_policy_v0.yml"

GOLDEN_DIR = REPO_ROOT / "tests" / "fixtures" / "core_baseline_v0"
STATUS_GOLDEN = GOLDEN_DIR / "status.normalized.json"
JUNIT_GOLDEN = GOLDEN_DIR / "junit.normalized.xml"
SARIF_GOLDEN = GOLDEN_DIR / "sarif.normalized.json"

SENTINEL_TS = "1970-01-01T00:00:00Z"


def _run(cmd: list[str], *, env: dict[str, str]) -> None:
    result = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"Command failed: {' '.join(cmd)}\n\n"
            f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
        )


def _load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _normalize_status(data: dict[str, Any]) -> dict[str, Any]:
    norm = json.loads(json.dumps(data))

    if "created_utc" in norm:
        norm["created_utc"] = SENTINEL_TS

    metrics = norm.get("metrics")
    if isinstance(metrics, dict):
        if "build_time" in metrics:
            metrics["build_time"] = SENTINEL_TS
        if "gate_policy_path" in metrics:
            metrics["gate_policy_path"] = "pulse_gate_policy_v0.yml"
        if "hazard_stability_map_path" in metrics:
            metrics["hazard_stability_map_path"] = "epf_stability_map_v0.json"
        if "git_sha" in metrics:
            metrics["git_sha"] = "<GIT_SHA>"
        if "run_key" in metrics:
            metrics["run_key"] = "<RUN_KEY>"

    return norm


def _get_testsuite_root(root: ET.Element) -> ET.Element:
    if root.tag == "testsuite":
        return root
    ts = root.find("testsuite")
    if ts is None:
        raise SystemExit("Could not find <testsuite> in JUnit XML.")
    return ts


def _normalize_junit(xml_text: str) -> str:
    root = ET.fromstring(xml_text)
    testsuite = _get_testsuite_root(root)

    testsuite.set("timestamp", SENTINEL_TS)

    props = testsuite.find("properties")
    if props is not None:
        for prop in props.findall("property"):
            name = prop.attrib.get("name", "")
            if name == "status_path":
                prop.set("value", "status.json")
            elif name == "created_utc":
                prop.set("value", SENTINEL_TS)

    tree = ET.ElementTree(root)
    try:
        ET.indent(tree, space="  ", level=0)
    except Exception:
        pass

    buf = io.BytesIO()
    tree.write(buf, encoding="utf-8", xml_declaration=True)
    return buf.getvalue().decode("utf-8") + "\n"


def _normalize_sarif(data: dict[str, Any]) -> dict[str, Any]:
    norm = json.loads(json.dumps(data))

    for run in norm.get("runs") or []:
        for inv in run.get("invocations") or []:
            inv["startTimeUtc"] = SENTINEL_TS

        for result in run.get("results") or []:
            props = result.get("properties")
            if isinstance(props, dict) and "created_utc" in props:
                props["created_utc"] = SENTINEL_TS

            for loc in result.get("locations") or []:
                physical = loc.get("physicalLocation")
                if not isinstance(physical, dict):
                    continue
                artifact = physical.get("artifactLocation")
                if not isinstance(artifact, dict):
                    continue
                if "uri" in artifact:
                    artifact["uri"] = "status.json"

    return norm


def _generate_normalized_outputs() -> tuple[str, str, str]:
    with tempfile.TemporaryDirectory() as td:
        td_path = pathlib.Path(td)
        artifacts_dir = td_path / "artifacts"
        reports_dir = td_path / "reports"

        status_path = artifacts_dir / "status.json"
        junit_path = reports_dir / "junit.xml"
        sarif_path = reports_dir / "sarif.json"

        env = os.environ.copy()
        for key in (
            "PULSE_RUN_MODE",
            "PULSE_STATUS",
            "PULSE_JUNIT",
            "PULSE_SARIF",
            "PULSE_ARTIFACT_DIR",
            "EPF_HAZARD_ENFORCE",
        ):
            env.pop(key, None)

        env["PULSE_ARTIFACT_DIR"] = str(artifacts_dir)

        _run(
            [
                sys.executable,
                str(RUN_ALL),
                "--mode",
                "core",
                "--pack_dir",
                str(PACK_DIR),
                "--gate_policy",
                str(POLICY),
            ],
            env=env,
        )

        _run(
            [
                sys.executable,
                str(VALIDATE),
                "--schema",
                str(SCHEMA),
                "--status",
                str(status_path),
            ],
            env=env,
        )

        _run(
            [
                sys.executable,
                str(JUNIT_EXPORTER),
                "--status",
                str(status_path),
                "--out",
                str(junit_path),
            ],
            env=env,
        )

        _run(
            [
                sys.executable,
                str(SARIF_EXPORTER),
                "--status",
                str(status_path),
                "--out",
                str(sarif_path),
            ],
            env=env,
        )

        status_norm = _dump_json(_normalize_status(_load_json(status_path)))
        junit_norm = _normalize_junit(junit_path.read_text(encoding="utf-8"))
        sarif_norm = _dump_json(_normalize_sarif(_load_json(sarif_path)))

        return status_norm, junit_norm, sarif_norm


def _write_file(path: pathlib.Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _diff(expected: str, actual: str, name: str) -> str:
    return "".join(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            fromfile=f"{name} (golden)",
            tofile=f"{name} (generated)",
        )
    )


def write_golden() -> int:
    status_norm, junit_norm, sarif_norm = _generate_normalized_outputs()
    _write_file(STATUS_GOLDEN, status_norm)
    _write_file(JUNIT_GOLDEN, junit_norm)
    _write_file(SARIF_GOLDEN, sarif_norm)
    print("OK: wrote baseline golden files")
    return 0


def check_golden() -> int:
    missing = [p for p in (STATUS_GOLDEN, JUNIT_GOLDEN, SARIF_GOLDEN) if not p.exists()]
    if missing:
        raise SystemExit(
            "Missing golden file(s):\n- " + "\n- ".join(str(p) for p in missing)
        )

    status_norm, junit_norm, sarif_norm = _generate_normalized_outputs()

    checks = [
        (STATUS_GOLDEN, status_norm, "status.normalized.json"),
        (JUNIT_GOLDEN, junit_norm, "junit.normalized.xml"),
        (SARIF_GOLDEN, sarif_norm, "sarif.normalized.json"),
    ]

    any_diff = False
    for golden_path, actual, name in checks:
        expected = golden_path.read_text(encoding="utf-8")
        if expected != actual:
            any_diff = True
            print(_diff(expected, actual, name))

    if any_diff:
        print("ERROR: baseline drift detected", file=sys.stderr)
        return 1

    print("OK: baseline matches golden files")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-golden", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if args.write_golden == args.check:
        raise SystemExit("Use exactly one of: --write-golden or --check")

    if args.write_golden:
        return write_golden()
    return check_golden()


if __name__ == "__main__":
    raise SystemExit(main())

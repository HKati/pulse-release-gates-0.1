import os
import json
import subprocess
import pathlib
import sys
import xml.etree.ElementTree as ET


ROOT = pathlib.Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "status_min.json"
OUT = ROOT / "tests" / "out"
OUT.mkdir(parents=True, exist_ok=True)


def run(cmd, env=None):
    """
    Run a command in repo root with optional env overrides.
    Accepts either a string (shell=True) or a list (shell=False).
    """
    e = os.environ.copy()
    if env:
        e.update(env)

    if isinstance(cmd, str):
        subprocess.check_call(cmd, shell=True, cwd=str(ROOT), env=e)
    else:
        subprocess.check_call(cmd, cwd=str(ROOT), env=e)


def test_junit_exporter_smoke():
    """
    Env-default invocation (legacy wrapper style) for JUnit exporter:
    - No CLI flags, relies on PULSE_STATUS / PULSE_JUNIT
    - Uses a v1-compatible status payload so we validate real gate->JUnit mapping
    """
    junit = OUT / "junit.xml"
    status = OUT / "status_v1_for_junit_env_smoke.json"

    if junit.exists():
        junit.unlink()
    if status.exists():
        status.unlink()

    payload = {
        "version": "1.0.0-test",
        "created_utc": "2026-02-18T00:00:00Z",
        "metrics": {"run_mode": "core"},
        "gates": {"gate_a": True, "gate_b": False},
    }
    status.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    env = {"PULSE_STATUS": str(status), "PULSE_JUNIT": str(junit)}
    run([sys.executable, "PULSE_safe_pack_v0/tools/status_to_junit.py"], env=env)

    assert junit.exists()
    xml_text = junit.read_text(encoding="utf-8")
    assert "<testsuite" in xml_text

    # Stronger checks: parse and assert counts + failing gate presence
    root = ET.fromstring(xml_text)
    assert root.tag == "testsuite"

    tests = int(root.attrib.get("tests", "0"))
    failures = int(root.attrib.get("failures", "0"))
    assert tests >= 2
    assert failures >= 1

    # Ensure the failing gate shows up in at least one failing testcase
    failing_names = []
    for tc in root.findall("testcase"):
        if tc.find("failure") is not None:
            failing_names.append(tc.attrib.get("name", ""))

    assert any("gate_b" in name for name in failing_names), f"Expected gate_b failure, got: {failing_names}"


def test_sarif_exporter_env_smoke():
    """
    Env-default invocation (legacy wrapper style) for SARIF exporter:
    - No CLI flags, relies on PULSE_STATUS / PULSE_SARIF
    - Uses a v1-compatible status payload so we can assert real gate->result mapping
    """
    sarif = OUT / "sarif.json"
    status = OUT / "status_v1_for_sarif_env_smoke.json"

    if sarif.exists():
        sarif.unlink()
    if status.exists():
        status.unlink()

    payload = {
        "version": "1.0.0-test",
        "created_utc": "2026-02-18T00:00:00Z",
        "metrics": {"run_mode": "core"},
        "gates": {"gate_a": True, "gate_b": False},
    }
    status.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    env = {"PULSE_STATUS": str(status), "PULSE_SARIF": str(sarif)}
    run([sys.executable, "PULSE_safe_pack_v0/tools/status_to_sarif.py"], env=env)

    assert sarif.exists()
    data = json.loads(sarif.read_text(encoding="utf-8"))

    assert data.get("version") == "2.1.0"
    runs = data.get("runs")
    assert isinstance(runs, list) and len(runs) >= 1

    results = runs[0].get("results") or []
    rule_ids = [r.get("ruleId") for r in results]
    assert "gate_b" in rule_ids


def main():
    test_junit_exporter_smoke()
    test_sarif_exporter_env_smoke()
    print("OK: exporters smoke passed")


if __name__ == "__main__":
    main()

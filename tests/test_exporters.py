import os, json, subprocess, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "status_min.json"
OUT = ROOT / "tests" / "out"
OUT.mkdir(parents=True, exist_ok=True)

def run(cmd, env=None):
    e = os.environ.copy()
    if env:
        e.update(env)
    subprocess.check_call(cmd, shell=True, cwd=str(ROOT), env=e)

def test_junit_exporter_smoke():
    junit = OUT / "junit.xml"
    env = {"PULSE_STATUS": str(FIX), "PULSE_JUNIT": str(junit)}
    run("python PULSE_safe_pack_v0/tools/status_to_junit.py", env=env)
    assert junit.exists()
    text = junit.read_text(encoding="utf-8")
    assert "<testsuite" in text

def test_sarif_exporter_smoke():
    sarif = OUT / "sarif.json"
    env = {"PULSE_STATUS": str(FIX), "PULSE_SARIF": str(sarif)}
    run("python PULSE_safe_pack_v0/tools/status_to_sarif.py", env=env)
    assert sarif.exists()
    data = json.loads(sarif.read_text(encoding="utf-8"))
    assert "version" in data and "runs" in data

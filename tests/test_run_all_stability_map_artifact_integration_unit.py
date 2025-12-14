import json
import os
import pathlib
import subprocess
import sys


def test_run_all_writes_stability_map_artifact(tmp_path):
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    script = repo_root / "PULSE_safe_pack_v0" / "tools" / "run_all.py"

    art_dir = tmp_path / "artifacts"
    env = os.environ.copy()
    env["PULSE_ARTIFACT_DIR"] = str(art_dir)

    subprocess.check_call([sys.executable, str(script)], env=env)

    p = art_dir / "epf_stability_map_v0.json"
    assert p.exists(), "expected Stability Map artifact to be written"

    data = json.loads(p.read_text(encoding="utf-8"))
    assert data.get("schema") == "epf_stability_map_v0"
    assert isinstance(data.get("gate_id"), str) and data["gate_id"]
    assert isinstance(data.get("topology_region"), str) and data["topology_region"]

    hazard = data.get("hazard", {})
    assert isinstance(hazard, dict)
    assert "zone" in hazard
    assert "E" in hazard

    series = data.get("series", {})
    assert isinstance(series, dict)
    assert isinstance(series.get("history_E", []), list)
    assert isinstance(series.get("history_T", []), list)

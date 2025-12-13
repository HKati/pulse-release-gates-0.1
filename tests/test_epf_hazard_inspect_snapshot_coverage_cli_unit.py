import json
import pathlib
import subprocess
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_inspector_emits_snapshot_coverage_summary(tmp_path):
    log_path = tmp_path / "epf_hazard_log.jsonl"
    out_json = tmp_path / "summary.json"

    # 5 snapshot-bearing entries:
    # - a: present in all 5 -> missing 0
    # - b: present in 3/5 -> missing 2 (coverage 0.6)
    # - c: present in 1/5 -> missing 4 (coverage 0.2)
    lines = []
    for i in range(5):
        snap = {"a": 1.0}
        if i < 3:
            snap["b"] = 2.0
        if i == 0:
            snap["c"] = 3.0

        ev = {
            "gate_id": "G1",
            "timestamp": "2025-01-01T00:00:00Z",
            "hazard": {"E": 0.1, "zone": "GREEN"},
            "snapshot_current": snap,
        }
        lines.append(json.dumps(ev))

    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    inspector = REPO_ROOT / "PULSE_safe_pack_v0" / "tools" / "epf_hazard_inspect.py"
    assert inspector.exists(), f"missing inspector script: {inspector}"

    cmd = [
        sys.executable,
        str(inspector),
        "--log",
        str(log_path),
        "--tail",
        "0",
        "--coverage-top",
        "10",
        "--out-json",
        str(out_json),
    ]

    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"inspect failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"

    data = json.loads(out_json.read_text(encoding="utf-8"))
    sc = data.get("snapshot_coverage", {})
    assert sc.get("snapshot_event_count") == 5
    assert sc.get("unique_features") >= 3

    top = sc.get("coverage_top_missing", [])
    by_key = {row["key"]: row for row in top}

    assert "b" in by_key
    assert by_key["b"]["present"] == 3
    assert by_key["b"]["missing"] == 2
    assert abs(by_key["b"]["coverage"] - 0.6) < 1e-9

    assert "c" in by_key
    assert by_key["c"]["present"] == 1
    assert by_key["c"]["missing"] == 4
    assert abs(by_key["c"]["coverage"] - 0.2) < 1e-9

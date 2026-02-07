import json
import subprocess
import sys
from pathlib import Path


def test_contract_rejects_bool_metric(tmp_path: Path) -> None:
    bad = {
        "schema_version": "v0",
        "timestamp_utc": "2026-02-06T00:00:00+00:00",
        "shadow": True,
        "decision_key": "NORMAL",
        "decision_raw": "NORMAL",
        "metrics": {
            "settle_time_p95_ms": 10.0,
            "settle_time_budget_ms": 50.0,
            "downstream_error_rate": True,   # <-- a lényeg
            "paradox_density": 0.1,
        },
    }

    p = tmp_path / "bad.json"
    p.write_text(json.dumps(bad, indent=2) + "\n", encoding="utf-8")

    r = subprocess.run(
        [
            sys.executable,
            "scripts/check_paradox_diagram_input_v0_contract.py",
            "--in",
            str(p),
        ],
        capture_output=True,
        text=True,
    )

    assert r.returncode != 0, f"expected non-zero exit, got {r.returncode}\nstdout={r.stdout}\nstderr={r.stderr}"

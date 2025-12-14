import json
import pathlib
import sys

# Ensure repo root is on sys.path (pytest prepends tests/ by default)
HERE = pathlib.Path(__file__).resolve()
REPO_ROOT = HERE.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.epf.epf_stability_map import (
    build_stability_map_from_log,
    compute_topology_region,
)


def test_compute_topology_region():
    assert compute_topology_region(True, "GREEN") == "stably_good"
    assert compute_topology_region(True, "AMBER") == "unstably_good"
    assert compute_topology_region(True, "RED") == "unstably_good"
    assert compute_topology_region(False, "GREEN") == "stably_bad"
    assert compute_topology_region(False, "RED") == "unstably_bad"
    assert compute_topology_region(None, "GREEN") == "unknown"
    assert compute_topology_region(None, "???") == "unknown"


def test_build_stability_map_from_log_filters_gate_and_max_points(tmp_path):
    log_path = tmp_path / "epf_hazard_log.jsonl"

    events = [
        {
            "gate_id": "A",
            "timestamp": "t1",
            "hazard": {"E": 0.1, "T": 0.2, "S": 0.9, "D": 0.01, "zone": "GREEN"},
            "snapshot_current": {"gates.g1": 1.0, "gates.g2": 1.0},
            "meta": {"git_sha": "sha1", "run_key": "rk1"},
        },
        {
            "gate_id": "A",
            "timestamp": "t2",
            "hazard": {"E": 0.6, "T": 0.8, "S": 0.4, "D": 0.10, "zone": "AMBER"},
            "snapshot_current": {"gates.g1": 1.0, "gates.g2": 1.0},
        },
        {
            "gate_id": "B",
            "timestamp": "tb",
            "hazard": {"E": 0.9, "zone": "RED"},
            "snapshot_current": {"gates.g1": 0.0},
        },
        {
            "gate_id": "A",
            "timestamp": "t3",
            "hazard": {"E": 0.9, "zone": "RED"},
            "snapshot_current": {"gates.g1": 0.0, "gates.g2": 1.0},
        },
    ]

    with log_path.open("w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")

    payload = build_stability_map_from_log(
        log_path=log_path,
        gate_id="A",
        created_utc="now",
        max_points=2,
    )

    assert payload["schema"] == "epf_stability_map_v0"
    assert payload["gate_id"] == "A"
    assert payload["window"]["points"] == 2

    pts = payload["points"]
    # last 2 points for A are t2 and t3
    assert pts[0]["timestamp"] == "t2"
    assert pts[1]["timestamp"] == "t3"

    # topology
    assert pts[0]["topology_region"] == "unstably_good"  # baseline_ok True + AMBER
    assert pts[1]["topology_region"] == "unstably_bad"   # baseline_ok False + RED


def test_missing_snapshot_current_yields_unknown_topology(tmp_path):
    log_path = tmp_path / "epf_hazard_log.jsonl"
    ev = {
        "gate_id": "A",
        "timestamp": "t1",
        "hazard": {"E": 0.2, "zone": "GREEN"},
        # snapshot_current omitted
    }
    log_path.write_text(json.dumps(ev) + "\n", encoding="utf-8")

    payload = build_stability_map_from_log(
        log_path=log_path,
        gate_id="A",
        created_utc="now",
        max_points=10,
    )
    assert payload["window"]["points"] == 1
    assert payload["points"][0]["baseline_ok"] is None
    assert payload["points"][0]["topology_region"] == "unknown"

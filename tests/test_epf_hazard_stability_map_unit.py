import json
import pathlib
import sys
import tempfile

# Ensure repo root on sys.path (pytest often prepends tests/).
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.epf.epf_hazard_stability_map import build_stability_map_from_log


def _write_jsonl(path: pathlib.Path, objs: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for o in objs:
            f.write(json.dumps(o) + "\n")


def test_stability_map_regimes_and_zone_counts():
    with tempfile.TemporaryDirectory() as td:
        log_path = pathlib.Path(td) / "epf_hazard_log.jsonl"

        events = [
            {
                "gate_id": "G_stable",
                "timestamp": "2025-01-01T00:00:00Z",
                "hazard": {"E": 0.10, "T": 0.1, "S": 0.95, "D": 0.02, "zone": "GREEN"},
            },
            {
                "gate_id": "G_amber_good",
                "timestamp": "2025-01-01T00:00:01Z",
                "hazard": {"E": 0.50, "T": 0.6, "S": 0.90, "D": 0.40, "zone": "AMBER"},
            },
            {
                "gate_id": "G_amber_bad",
                "timestamp": "2025-01-01T00:00:02Z",
                "hazard": {"E": 0.55, "T": 0.7, "S": 0.20, "D": 0.05, "zone": "AMBER"},
            },
            {
                "gate_id": "G_hazard",
                "timestamp": "2025-01-01T00:00:03Z",
                "hazard": {"E": 0.95, "T": 1.2, "S": 0.10, "D": 0.20, "zone": "RED"},
            },
        ]
        _write_jsonl(log_path, events)

        artifact = build_stability_map_from_log(log_path, tail=20, max_per_gate=1000)
        assert artifact["schema"] == "epf_hazard_stability_map_v0"
        gates = artifact["gates"]
        assert set(gates.keys()) == {"G_stable", "G_amber_good", "G_amber_bad", "G_hazard"}

        assert gates["G_stable"]["regime"] == "stable"
        assert gates["G_hazard"]["regime"] == "hazard"

        # AMBER refined by drift vs stability-loss
        assert gates["G_amber_good"]["regime"] == "unstably_good"
        assert gates["G_amber_bad"]["regime"] == "unstably_bad"

        # Zone counts exist and include the correct last zone
        assert gates["G_stable"]["zone_counts_tail"]["GREEN"] == 1
        assert gates["G_hazard"]["zone_counts_tail"]["RED"] == 1
        assert gates["G_amber_good"]["zone_counts_tail"]["AMBER"] == 1


def test_stability_map_missing_log_is_fail_open():
    with tempfile.TemporaryDirectory() as td:
        log_path = pathlib.Path(td) / "missing.jsonl"
        artifact = build_stability_map_from_log(log_path, tail=10, max_per_gate=10)
        assert artifact["gates"] == {}

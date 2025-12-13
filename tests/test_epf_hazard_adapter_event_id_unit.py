import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.epf.epf_hazard_adapter import (
    HazardRuntimeState,
    probe_hazard_and_append_log,
    LOG_FILENAME_DEFAULT,
)


def _read_lines(log_dir: pathlib.Path):
    p = log_dir / LOG_FILENAME_DEFAULT
    text = p.read_text(encoding="utf-8").strip()
    assert text, "expected non-empty hazard log"
    return [json.loads(x) for x in text.splitlines()]


def test_hazard_event_id_present_and_stable(tmp_path: pathlib.Path):
    log_dir = tmp_path / "artifacts"
    log_dir.mkdir(parents=True, exist_ok=True)

    ts = "2025-01-01T00:00:00Z"
    meta = {"run_key": "gh:1:1", "git_sha": "abc", "status_version": "demo"}

    runtime1 = HazardRuntimeState.empty()
    probe_hazard_and_append_log(
        gate_id="G1",
        current_snapshot={"x": 1.0},
        reference_snapshot={"x": 0.0},
        stability_metrics={"RDSI": 1.0},
        runtime_state=runtime1,
        log_dir=log_dir,
        timestamp=ts,
        extra_meta=meta,
        log_snapshots=False,
    )

    runtime2 = HazardRuntimeState.empty()
    probe_hazard_and_append_log(
        gate_id="G1",
        current_snapshot={"x": 2.0},
        reference_snapshot={"x": 0.0},
        stability_metrics={"RDSI": 1.0},
        runtime_state=runtime2,
        log_dir=log_dir,
        timestamp=ts,
        extra_meta=meta,
        log_snapshots=False,
    )

    entries = _read_lines(log_dir)
    assert len(entries) >= 2

    e1 = entries[-2]
    e2 = entries[-1]

    assert e1.get("schema") == "epf_hazard_log_v1"
    assert "event_id" in e1 and isinstance(e1["event_id"], str)
    assert len(e1["event_id"]) == 16

    # Same (gate_id, timestamp, provenance) => stable id
    assert e1["event_id"] == e2["event_id"]


def test_hazard_event_id_changes_with_provenance(tmp_path: pathlib.Path):
    log_dir = tmp_path / "artifacts"
    log_dir.mkdir(parents=True, exist_ok=True)

    ts = "2025-01-01T00:00:00Z"
    meta_a = {"run_key": "gh:1:1", "git_sha": "abc", "status_version": "demo"}
    meta_b = {"run_key": "gh:2:1", "git_sha": "abc", "status_version": "demo"}

    runtime = HazardRuntimeState.empty()
    probe_hazard_and_append_log(
        gate_id="G1",
        current_snapshot={"x": 1.0},
        reference_snapshot={"x": 0.0},
        stability_metrics={"RDSI": 1.0},
        runtime_state=runtime,
        log_dir=log_dir,
        timestamp=ts,
        extra_meta=meta_a,
        log_snapshots=False,
    )
    probe_hazard_and_append_log(
        gate_id="G1",
        current_snapshot={"x": 1.0},
        reference_snapshot={"x": 0.0},
        stability_metrics={"RDSI": 1.0},
        runtime_state=runtime,
        log_dir=log_dir,
        timestamp=ts,
        extra_meta=meta_b,
        log_snapshots=False,
    )

    entries = _read_lines(log_dir)
    e1 = entries[-2]["event_id"]
    e2 = entries[-1]["event_id"]
    assert e1 != e2

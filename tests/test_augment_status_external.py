import json
import subprocess
import sys
from pathlib import Path


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


def run_augment_status(repo_root: Path, status_path: Path, thresholds_path: Path, external_dir: Path):
    script = repo_root / "PULSE_safe_pack_v0" / "tools" / "augment_status.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--status",
            str(status_path),
            "--thresholds",
            str(thresholds_path),
            "--external_dir",
            str(external_dir),
        ],
        cwd=str(repo_root),
        check=True,
        capture_output=True,
        text=True,
    )
    return result


def test_promptguard_attack_detect_rate_is_used(tmp_path: Path):
    """
    Prompt Guard summaries expose `attack_detect_rate`. We expect augment_status
    to read this field, compare it to the configured threshold and reflect it
    both in `external.metrics` and in `external_all_pass` / gates.
    """
    repo_root = Path(__file__).resolve().parents[1]

    status_path = tmp_path / "status.json"
    thresholds_path = tmp_path / "thresholds.json"
    external_dir = tmp_path / "external"
    external_dir.mkdir(parents=True, exist_ok=True)

    # minimal starting status
    write_json(status_path, {})

    # set a low threshold so that 0.2 clearly fails
    write_json(
        thresholds_path,
        {
            "promptguard_attack_detect_rate_max": 0.10,
            "external_overall_policy": "all",
        },
    )

    # Prompt Guard adapter writes `attack_detect_rate`
    write_json(
        external_dir / "promptguard_summary.json",
        {
            "attack_detect_rate": 0.20,
        },
    )

    run_augment_status(repo_root, status_path, thresholds_path, external_dir)

    data = json.loads(status_path.read_text(encoding="utf-8"))

    # Top-level mirrors
    assert data["external_all_pass"] is False
    assert data["gates"]["external_all_pass"] is False

    # Metrics entry for Prompt Guard
    ext = data["external"]
    assert isinstance(ext["metrics"], list)
    pg_entries = [
        m
        for m in ext["metrics"]
        if m.get("name") == "promptguard_attack_detect_rate"
    ]
    assert pg_entries, "expected a promptguard_attack_detect_rate metric entry"

    pg = pg_entries[0]
    assert pg["value"] == 0.20
    assert pg["threshold"] == 0.10
    assert pg["pass"] is False

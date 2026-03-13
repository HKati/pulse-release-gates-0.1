import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional


SCRIPT = Path(__file__).resolve().parents[1] / "PULSE_safe_pack_v0" / "tools" / "augment_status.py"


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def prepare_case(case_dir: Path, *, meta: Optional[Dict[str, Any]] = None) -> tuple[Path, Path, Path]:
    case_dir.mkdir(parents=True, exist_ok=True)

    status_path = case_dir / "status.json"
    thresholds_path = case_dir / "external_thresholds.yaml"
    external_dir = case_dir / "external"
    external_dir.mkdir()

    status: Dict[str, Any] = {
        "version": "1.0.0-core",
        "created_utc": "2026-02-17T12:34:56Z",
        "metrics": {"run_mode": "core"},
        "gates": {
            "q1_grounded_ok": True,
            "q4_slo_ok": True,
        },
    }
    if meta is not None:
        status["meta"] = meta

    write_json(status_path, status)

    write_json(
        case_dir / "refusal_delta_summary.json",
        {
            "n": 12,
            "delta": 0.25,
            "ci_low": 0.10,
            "ci_high": 0.40,
            "policy": "balanced",
            "delta_min": 0.10,
            "delta_strict": 0.10,
            "p_mcnemar": 0.03,
            "pass_min": True,
            "pass_strict": True,
            "pass": True,
        },
    )

    thresholds_path.write_text("external_overall_policy: all\n", encoding="utf-8")
    return status_path, thresholds_path, external_dir


def run_augment(
    status_path: Path,
    thresholds_path: Path,
    external_dir: Path,
    *,
    q1_reference_summary: Optional[Path] = None,
) -> Dict[str, Any]:
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--status",
        str(status_path),
        "--thresholds",
        str(thresholds_path),
        "--external_dir",
        str(external_dir),
    ]
    if q1_reference_summary is not None:
          cmd.extend(["--q1_reference_summary", str(q1_reference_summary)])

    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr or result.stdout
    return read_json(status_path)


def valid_q1_raw_bytes() -> bytes:
    return (
        b'{\n'
        b'  "pass": true,\n'
        b'  "grounded_rate": 0.94,\n'
        b'  "wilson_lower_bound": 0.90,\n'
        b'  "n_eligible": 120,\n'
        b'  "threshold": 0.90\n'
        b'}\n'
    )


def test_valid_q1_reference_shadow_fold_in(tmp_path: Path) -> None:
    status_path, thresholds_path, external_dir = prepare_case(tmp_path)

    q1_path = tmp_path / "q1_reference_summary.json"
    raw = valid_q1_raw_bytes()
    q1_path.write_bytes(raw)

    status = run_augment(
        status_path,
        thresholds_path,
        external_dir,
        q1_reference_summary=q1_path,
    )

    assert status["meta"]["q1_reference_shadow"] == {
        "pass": True,
        "grounded_rate": 0.94,
        "wilson_lower_bound": 0.90,
        "n_eligible": 120,
        "threshold": 0.90,
        "summary_artifact": {
            "path": str(q1_path.resolve()),
            "sha256": hashlib.sha256(raw).hexdigest(),
        },
    }


def test_no_q1_flag_keeps_q1_shadow_absent(tmp_path: Path) -> None:
    status_path, thresholds_path, external_dir = prepare_case(tmp_path)

    status = run_augment(status_path, thresholds_path, external_dir)

    assert "q1_reference_shadow" not in status.get("meta", {})


def test_invalid_q1_json_omits_shadow_block(tmp_path: Path) -> None:
    status_path, thresholds_path, external_dir = prepare_case(tmp_path)

    q1_path = tmp_path / "q1_reference_summary.json"
    q1_path.write_bytes(b'{"pass": true, invalid')

    status = run_augment(
        status_path,
        thresholds_path,
        external_dir,
        q1_reference_summary=q1_path,
    )

    assert "q1_reference_shadow" not in status.get("meta", {})


def test_missing_required_q1_fields_omits_shadow_block(tmp_path: Path) -> None:
    status_path, thresholds_path, external_dir = prepare_case(tmp_path)

    q1_path = tmp_path / "q1_reference_summary.json"
    write_json(
        q1_path,
        {
            "pass": True,
            "grounded_rate": 0.94,
            "wilson_lower_bound": 0.90,
            "n_eligible": 120,
            # threshold intentionally missing
        },
    )

    status = run_augment(
        status_path,
        thresholds_path,
        external_dir,
        q1_reference_summary=q1_path,
    )

    assert "q1_reference_shadow" not in status.get("meta", {})


def test_existing_meta_siblings_are_preserved(tmp_path: Path) -> None:
    status_path, thresholds_path, external_dir = prepare_case(
        tmp_path,
        meta={"existing_panel": {"ok": True}},
    )

    q1_path = tmp_path / "q1_reference_summary.json"
    q1_path.write_bytes(valid_q1_raw_bytes())

    status = run_augment(
        status_path,
        thresholds_path,
        external_dir,
        q1_reference_summary=q1_path,
    )

    assert status["meta"]["existing_panel"] == {"ok": True}
    assert "q1_reference_shadow" in status["meta"]


def test_q1_shadow_does_not_change_gates(tmp_path: Path) -> None:
    no_q1_dir = tmp_path / "no_q1"
    with_q1_dir = tmp_path / "with_q1"

    status_path_a, thresholds_path_a, external_dir_a = prepare_case(no_q1_dir)
    status_path_b, thresholds_path_b, external_dir_b = prepare_case(with_q1_dir)

    q1_path = with_q1_dir / "q1_reference_summary.json"
    q1_path.write_bytes(valid_q1_raw_bytes())

    status_a = run_augment(status_path_a, thresholds_path_a, external_dir_a)
    status_b = run_augment(
        status_path_b,
        thresholds_path_b,
        external_dir_b,
        q1_reference_summary=q1_path,
    )

    assert status_a["gates"] == status_b["gates"]
    assert status_a["refusal_delta_pass"] == status_b["refusal_delta_pass"]
    assert status_a["external_all_pass"] == status_b["external_all_pass"]
    assert status_a["external_summaries_present"] == status_b["external_summaries_present"]


def test_q1_shadow_sha256_uses_raw_file_bytes(tmp_path: Path) -> None:
    status_path, thresholds_path, external_dir = prepare_case(tmp_path)

    raw = (
        b'{"threshold":0.90,"n_eligible":120,"wilson_lower_bound":0.90,'
        b'"grounded_rate":0.94,"pass":true}\n'
    )
    q1_path = tmp_path / "q1_reference_summary.json"
    q1_path.write_bytes(raw)

    status = run_augment(
        status_path,
        thresholds_path,
        external_dir,
        q1_reference_summary=q1_path,
    )

    assert (
        status["meta"]["q1_reference_shadow"]["summary_artifact"]["sha256"]
        == hashlib.sha256(raw).hexdigest()
    )

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.tools.check_gates import main as check_gates_main  # noqa: E402
from PULSE_safe_pack_v0.tools.render_quality_ledger import (  # noqa: E402
    decision_from_status,
    select_required_gates,
)


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_policy(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                'id: pulse-gate-policy-v0',
                'version: "0.1.1"',
                'gates:',
                '  required:',
                '    - prod_gate_ok',
                '    - prod_second_ok',
                '  core_required:',
                '    - core_gate_ok',
                '    - q1_grounded_ok',
                '  custom_shadow:',
                '    - shadow_gate_ok',
                '  advisory: []',
                '',
            ]
        ),
        encoding="utf-8",
    )


def status_payload(
    *,
    run_mode: str,
    gates: dict,
    gate_policy_path: Path | None = None,
    required_gates: list[str] | None = None,
    required_gate_set: str | None = None,
) -> dict:
    metrics: dict = {
        "run_mode": run_mode,
        "RDSI": 0.93,
    }
    if gate_policy_path is not None:
        metrics["gate_policy_path"] = str(gate_policy_path)
    if required_gates is not None:
        metrics["required_gates"] = required_gates
    if required_gate_set is not None:
        metrics["required_gate_set"] = required_gate_set

    return {
        "version": f"1.0.0-{run_mode}",
        "created_utc": "2026-02-17T12:34:56Z",
        "metrics": metrics,
        "gates": gates,
    }


def run_check_gates(status_path: Path, required_gate_ids: list[str]) -> int:
    return check_gates_main(
        [
            "--status",
            str(status_path),
            "--require",
            *required_gate_ids,
        ]
    )


def test_core_required_pass_matches_check_gates_exit_zero(tmp_path: Path) -> None:
    policy_path = tmp_path / "pulse_gate_policy_v0.yml"
    status_path = tmp_path / "status.json"

    write_policy(policy_path)
    status = status_payload(
        run_mode="core",
        gate_policy_path=policy_path,
        gates={
            "core_gate_ok": True,
            "q1_grounded_ok": True,
        },
    )
    write_json(status_path, status)

    required_gate_ids, source = select_required_gates(status, status_path=status_path)
    assert source == "policy:core_required"
    assert required_gate_ids == ["core_gate_ok", "q1_grounded_ok"]

    assert decision_from_status(status, status_path=status_path) == (
        "STAGE-PASS",
        "badge-pass",
    )
    assert run_check_gates(status_path, required_gate_ids) == 0


def test_core_required_fail_matches_check_gates_exit_one(tmp_path: Path) -> None:
    policy_path = tmp_path / "pulse_gate_policy_v0.yml"
    status_path = tmp_path / "status.json"

    write_policy(policy_path)
    status = status_payload(
        run_mode="core",
        gate_policy_path=policy_path,
        gates={
            "core_gate_ok": True,
            "q1_grounded_ok": False,
        },
    )
    write_json(status_path, status)

    required_gate_ids, source = select_required_gates(status, status_path=status_path)
    assert source == "policy:core_required"
    assert required_gate_ids == ["core_gate_ok", "q1_grounded_ok"]

    assert decision_from_status(status, status_path=status_path) == (
        "FAIL",
        "badge-fail",
    )
    assert run_check_gates(status_path, required_gate_ids) == 1


def test_explicit_required_gates_override_matches_check_gates(tmp_path: Path) -> None:
    policy_path = tmp_path / "pulse_gate_policy_v0.yml"
    status_path = tmp_path / "status.json"

    write_policy(policy_path)
    status = status_payload(
        run_mode="core",
        gate_policy_path=policy_path,
        required_gates=["shadow_gate_ok"],
        gates={
            "shadow_gate_ok": True,
            "core_gate_ok": False,
            "q1_grounded_ok": False,
        },
    )
    write_json(status_path, status)

    required_gate_ids, source = select_required_gates(status, status_path=status_path)
    assert source == "metrics.required_gates"
    assert required_gate_ids == ["shadow_gate_ok"]

    assert decision_from_status(status, status_path=status_path) == (
        "STAGE-PASS",
        "badge-pass",
    )
    assert run_check_gates(status_path, required_gate_ids) == 0


def test_unresolved_gate_selection_yields_unknown_without_check_gates(
    tmp_path: Path,
) -> None:
    policy_path = tmp_path / "pulse_gate_policy_v0.yml"
    status_path = tmp_path / "status.json"

    write_policy(policy_path)
    status = status_payload(
        run_mode="core",
        gate_policy_path=policy_path,
        required_gate_set="missing_set",
        gates={"core_gate_ok": True, "q1_grounded_ok": True},
    )
    write_json(status_path, status)

    required_gate_ids, source = select_required_gates(status, status_path=status_path)
    assert source == "unresolved"
    assert required_gate_ids == []

    assert decision_from_status(status, status_path=status_path) == (
        "UNKNOWN",
        "badge-unknown",
    )

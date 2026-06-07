import json
import os
import pathlib
import subprocess
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.tools.check_release_grade_reference_run_v0 import (
    check_release_grade_reference_run,
)


RUN_ALL = REPO_ROOT / "PULSE_safe_pack_v0" / "tools" / "run_all.py"
POLICY = REPO_ROOT / "pulse_gate_policy_v0.yml"
AUDIT_BUNDLE_DIRNAME = "release_authority_audit_bundle"

MATERIALIZED_GATES = {
    "pass_controls_refusal": True,
    "effect_present": True,
    "psf_monotonicity_ok": True,
    "psf_mono_shift_resilient": True,
    "pass_controls_comm": True,
    "psf_commutativity_ok": True,
    "psf_comm_shift_resilient": True,
    "pass_controls_sanit": True,
    "sanitization_effective": True,
    "sanit_shift_resilient": True,
    "psf_action_monotonicity_ok": True,
    "psf_idempotence_ok": True,
    "psf_path_independence_ok": True,
    "psf_pii_monotonicity_ok": True,
    "q1_grounded_ok": True,
    "q2_consistency_ok": True,
    "q3_fairness_ok": True,
    "q4_slo_ok": True,
}


def _write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _read_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return f"{result.stdout}\n{result.stderr}"


def _prepare_release_grade_inputs(
    art: pathlib.Path,
    *,
    detector_evidence: bool = True,
    detector_evidence_path: str = "detector_evidence.json",
    detector_manifest_extra: dict[str, Any] | None = None,
    external: dict[str, Any] | None = None,
    refusal_n: int = 1,
    refusal_pass: bool = True,
) -> None:
    if detector_evidence:
        _write_json(
            art / detector_evidence_path,
            {"source": "unit-test detector evidence"},
        )

    detector_manifest: dict[str, Any] = {
        "schema_version": "detector_materialization_v0",
        "materialized": True,
        "gates_stubbed": False,
        "scaffold": False,
        "gates": MATERIALIZED_GATES,
        "evidence": [{"path": detector_evidence_path}],
    }
    if detector_manifest_extra:
        detector_manifest.update(detector_manifest_extra)

    _write_json(art / "detector_materialization_v0.json", detector_manifest)

    if external is not None:
        _write_json(art / "external" / "llamaguard_summary.json", external)

    _write_json(
        art / "refusal_delta_summary.json",
        {
            "n": refusal_n,
            "pass": refusal_pass,
            "delta": 0.2,
            "ci_low": 0.1,
            "ci_high": 0.3,
        },
    )


def _run_prod(
    art: pathlib.Path,
    *,
    release_grade_materialized: bool = False,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("PULSE_RUN_MODE", None)
    env.pop("PULSE_RELEASE_GRADE_MATERIALIZED", None)
    env["PULSE_ARTIFACT_DIR"] = str(art)

    cmd = [
        sys.executable,
        str(RUN_ALL),
        "--mode",
        "prod",
        "--pack_dir",
        str(REPO_ROOT / "PULSE_safe_pack_v0"),
        "--gate_policy",
        str(POLICY),
    ]

    if release_grade_materialized:
        cmd.append("--release-grade-materialized")
        env["PULSE_RELEASE_GRADE_MATERIALIZED"] = "1"

    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _run_mode(
    art: pathlib.Path,
    *,
    mode: str,
    release_grade_materialized: bool = False,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("PULSE_RUN_MODE", None)
    env.pop("PULSE_RELEASE_GRADE_MATERIALIZED", None)
    env["PULSE_ARTIFACT_DIR"] = str(art)

    cmd = [
        sys.executable,
        str(RUN_ALL),
        "--mode",
        mode,
        "--pack_dir",
        str(REPO_ROOT / "PULSE_safe_pack_v0"),
        "--gate_policy",
        str(POLICY),
    ]

    if release_grade_materialized:
        cmd.append("--release-grade-materialized")
        env["PULSE_RELEASE_GRADE_MATERIALIZED"] = "1"

    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _load_status(art: pathlib.Path) -> dict[str, Any]:
    return _read_json(art / "status.json")


def test_plain_prod_fails_closed_without_explicit_materialized_opt_in(
    tmp_path: pathlib.Path,
) -> None:
    result = _run_prod(tmp_path)

    assert result.returncode != 0
    output = _combined_output(result).lower()
    assert "release-grade" in output
    assert "materialized" in output
    assert not (tmp_path / "status.json").exists()


def test_release_grade_materialized_opt_in_is_prod_only(
    tmp_path: pathlib.Path,
) -> None:
    result = _run_mode(
        tmp_path,
        mode="core",
        release_grade_materialized=True,
    )

    assert result.returncode != 0
    output = _combined_output(result).lower()
    assert "prod" in output
    assert not (tmp_path / "status.json").exists()


def test_prod_release_grade_materialized_opt_in_fails_closed_until_verifier_exists(
    tmp_path: pathlib.Path,
) -> None:
    result = _run_prod(tmp_path, release_grade_materialized=True)

    assert result.returncode != 0
    def test_prod_release_grade_self_declared_artifacts_do_not_materialize_gates(
    assert not (tmp_path / "status.json").exists()


def test_prod_release_grade_non_stubbed_candidate_materializes_required_artifacts(
    tmp_path: pathlib.Path,
) -> None:
    _prepare_release_grade_inputs(tmp_path, external={"rate": 0.0})

    result = _run_prod(tmp_path, release_grade_materialized=True)

    assert result.returncode != 0
    output = _combined_output(result).lower()
    assert "release-evidence verifier" in output
    assert "self-declared artifacts" in output
    assert "detector_materialization_v0.json" in output
    assert "external/llamaguard_summary.json" in output
    assert "refusal_delta_summary.json" in output
    assert not (tmp_path / "status.json").exists()
    assert not (tmp_path / "release_authority_v0.json").exists()
    assert not (tmp_path / AUDIT_BUNDLE_DIRNAME).exists()


def test_detectors_materialized_ok_requires_existing_detector_evidence(
    tmp_path: pathlib.Path,
) -> None:
    _prepare_release_grade_inputs(
        tmp_path,
        detector_evidence=False,
        detector_evidence_path="missing_detector_evidence.json",
        external={"rate": 0.0},
    )

    result = _run_prod(tmp_path, release_grade_materialized=True)

    assert result.returncode != 0
    assert "release-evidence verifier" in _combined_output(result).lower()
    assert not (tmp_path / "status.json").exists()


def test_prod_rejects_stubbed_detector_materialization_manifest(
    tmp_path: pathlib.Path,
) -> None:
    _prepare_release_grade_inputs(tmp_path, external={"rate": 0.0})

    manifest_path = tmp_path / "detector_materialization_v0.json"
    manifest = _read_json(manifest_path)
    manifest["gates_stubbed"] = True
    _write_json(manifest_path, manifest)

    result = _run_prod(tmp_path, release_grade_materialized=True)

    assert result.returncode != 0
    assert "release-evidence verifier" in _combined_output(result).lower()
    assert not (tmp_path / "status.json").exists()


def test_prod_rejects_scaffold_detector_materialization_manifest(
    tmp_path: pathlib.Path,
) -> None:
    _prepare_release_grade_inputs(tmp_path, external={"rate": 0.0})

    manifest_path = tmp_path / "detector_materialization_v0.json"
    manifest = _read_json(manifest_path)
    manifest["scaffold"] = True
    _write_json(manifest_path, manifest)

    result = _run_prod(tmp_path, release_grade_materialized=True)

    assert result.returncode != 0
    assert "release-evidence verifier" in _combined_output(result).lower()
    assert not (tmp_path / "status.json").exists()


def test_prod_rejects_non_boolean_materialized_gate_outcome(
    tmp_path: pathlib.Path,
) -> None:
    _prepare_release_grade_inputs(tmp_path, external={"rate": 0.0})

    manifest_path = tmp_path / "detector_materialization_v0.json"
    manifest = _read_json(manifest_path)
    manifest["gates"]["q1_grounded_ok"] = "true"
    _write_json(manifest_path, manifest)

    result = _run_prod(tmp_path, release_grade_materialized=True)

    assert result.returncode != 0
    output = _combined_output(result).lower()
    assert "release-evidence verifier" in output
    assert not (tmp_path / "status.json").exists()


def test_prod_rejects_materialization_manifest_without_materialized_true(
    tmp_path: pathlib.Path,
) -> None:
    _prepare_release_grade_inputs(tmp_path, external={"rate": 0.0})

    manifest_path = tmp_path / "detector_materialization_v0.json"
    manifest = _read_json(manifest_path)
    manifest["materialized"] = False
    _write_json(manifest_path, manifest)

    result = _run_prod(tmp_path, release_grade_materialized=True)

    assert result.returncode != 0
    output = _combined_output(result).lower()
    assert "release-evidence verifier" in output
    assert not (tmp_path / "status.json").exists()


def test_external_release_gates_require_real_canonical_parseable_summary(
    tmp_path: pathlib.Path,
) -> None:
    _prepare_release_grade_inputs(tmp_path, external=None)
    _write_json(tmp_path / "external" / "decoy_summary.json", {"rate": 0.0})

    result = _run_prod(tmp_path, release_grade_materialized=True)

    assert result.returncode != 0
    assert "release-evidence verifier" in _combined_output(result).lower()

    assert not (tmp_path / "release_authority_v0.json").exists()


def test_external_release_gates_reject_malformed_canonical_summary(
    tmp_path: pathlib.Path,
) -> None:
    _prepare_release_grade_inputs(tmp_path, external=None)
    external_path = tmp_path / "external" / "llamaguard_summary.json"
    external_path.parent.mkdir(parents=True, exist_ok=True)
    external_path.write_text("{not valid json", encoding="utf-8")

    result = _run_prod(tmp_path, release_grade_materialized=True)

    assert result.returncode != 0
    output = _combined_output(result).lower()
    assert "release-evidence verifier" in output   
    assert not (tmp_path / "release_authority_v0.json").exists()


def test_refusal_delta_evidence_requires_summary_with_positive_n(
    tmp_path: pathlib.Path,
) -> None:
    _prepare_release_grade_inputs(tmp_path, external={"rate": 0.0}, refusal_n=0)

    result = _run_prod(tmp_path, release_grade_materialized=True)

    assert result.returncode != 0
    assert "release-evidence verifier" in _combined_output(result).lower()
    assert not (tmp_path / "release_authority_v0.json").exists()


def test_refusal_delta_evidence_requires_passing_summary(
    tmp_path: pathlib.Path,
) -> None:
    _prepare_release_grade_inputs(
        tmp_path,
        external={"rate": 0.0},
        refusal_n=1,
        refusal_pass=False,
    )

    result = _run_prod(tmp_path, release_grade_materialized=True)

    assert result.returncode != 0
    output = _combined_output(result).lower()
    assert "release-evidence verifier" in output
    assert not (tmp_path / "release_authority_v0.json").exists()


def test_release_grade_checker_reports_missing_manifest_and_audit_bundle_files(
    tmp_path: pathlib.Path,
) -> None:
    status_path = tmp_path / "status.json"
    report_path = tmp_path / "report_card.html"

    manifest_path = tmp_path / "release_authority_v0.json"

    bundle = tmp_path / AUDIT_BUNDLE_DIRNAME
    (

      _write_json(
        status_path,
        {
            "metrics": {"run_mode": "prod"},
            "diagnostics": {"gates_stubbed": False, "scaffold": False},
            "gates": {
                "detectors_materialized_ok": True,
                "external_summaries_present": True,
                "external_all_pass": True,
                "refusal_delta_evidence_present": True,
            },
        },
    )
    report_path.write_text("<html></html>", encoding="utf-8")
    bundle.mkdir(parents=True)
    _write_json(bundle / "status.json", {"copied": "status"})
    _write_json(bundle / "release_authority_v0.json", {"copied": "manifest"})      
  
     errors = check_release_grade_reference_run(
        status_path=status_path,
        manifest_path=manifest_path,
        report_path=report_path,
        audit_bundle_dir=bundle,
    )

    assert any("release_authority_v0.json not found" in error for error in errors)
    assert any(
        "release authority audit bundle missing report_card.html" in error
        for error in errors
    )

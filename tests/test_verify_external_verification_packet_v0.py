import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILDER = REPO_ROOT / "scripts" / "build_external_verification_packet_v0.py"
VERIFIER = REPO_ROOT / "scripts" / "verify_external_verification_packet_v0.py"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def git_commit_all(repo: Path, message: str) -> None:
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def make_minimal_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"

    write(
        repo / "PULSE_safe_pack_v0" / "artifacts" / "status.json",
        json.dumps(
            {
                "version": "1.0.0-core",
                "created_utc": "2026-06-03T00:00:00Z",
                "metrics": {
                    "run_mode": "core",
                    "git_sha": "0" * 40,
                    "run_key": (
                        "GITHUB_RUN_ID=1|GITHUB_RUN_NUMBER=1|"
                        "GITHUB_WORKFLOW=PULSE CI"
                    ),
                },
                "gates": {"core_gate": True},
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )

    write(
        repo / "pulse_gate_policy_v0.yml",
        "gates:\n  core_required:\n    - core_gate\n",
    )
    write(
        repo / "pulse_gate_registry_v0.yml",
        "gates:\n  core_gate:\n    intent: test\n",
    )

    subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.PIPE)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo,
        check=True,
    )
    git_commit_all(repo, "fixture")

    return repo


def build_packet(repo: Path, tmp_path: Path) -> Path:
    out_json = tmp_path / "external_verification_packet_v0.json"
    out_md = tmp_path / "external_verification_packet_v0.md"

    subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--repo-root",
            str(repo),
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
            "--repository-name",
            "HKati/pulse-release-gates-0.1",
        ],
        check=True,
    )

    return out_json


def run_verifier(
    repo: Path,
    packet: Path,
    tmp_path: Path,
) -> tuple[subprocess.CompletedProcess[str], dict]:
    out_report = tmp_path / "external_verification_packet_verify_report.json"

    proc = subprocess.run(
        [
            sys.executable,
            str(VERIFIER),
            "--packet",
            str(packet),
            "--repo-root",
            str(repo),
            "--out-json",
            str(out_report),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    report = json.loads(out_report.read_text(encoding="utf-8"))
    return proc, report


def issue_codes(report: dict) -> set[str]:
    return {item["code"] for item in report["issues"]}


def test_external_verification_packet_verifier_accepts_builder_output(
    tmp_path: Path,
) -> None:
    repo = make_minimal_repo(tmp_path)
    packet = build_packet(repo, tmp_path)

    proc, report = run_verifier(repo, packet, tmp_path)

    assert proc.returncode == 0
    assert report["verified"] is True
    assert report["error_count"] == 0
    assert report["recorded_packet_status"] == "partially_verified"
    assert report["expected_packet_status"] == "partially_verified"


def test_external_verification_packet_verifier_detects_sha256_mismatch(
    tmp_path: Path,
) -> None:
    repo = make_minimal_repo(tmp_path)
    packet = build_packet(repo, tmp_path)

    write(
        repo / "pulse_gate_policy_v0.yml",
        "gates:\n  core_required:\n    - changed_gate\n",
    )

    proc, report = run_verifier(repo, packet, tmp_path)

    assert proc.returncode == 1
    assert report["verified"] is False
    assert "artifact_sha256_mismatch" in issue_codes(report)


def test_external_verification_packet_verifier_detects_missing_required_artifact(
    tmp_path: Path,
) -> None:
    repo = make_minimal_repo(tmp_path)
    packet = build_packet(repo, tmp_path)

    (repo / "PULSE_safe_pack_v0" / "artifacts" / "status.json").unlink()

    proc, report = run_verifier(repo, packet, tmp_path)

    assert proc.returncode == 1
    assert report["verified"] is False

    codes = issue_codes(report)
    assert "artifact_exists_mismatch" in codes
    assert "required_artifact_missing" in codes
    assert "packet_status_mismatch" in codes


def test_external_verification_packet_verifier_rejects_path_escape(
    tmp_path: Path,
) -> None:
    repo = make_minimal_repo(tmp_path)
    packet = build_packet(repo, tmp_path)

    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["artifact_records"][0]["path"] = "../outside.json"
    packet.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    proc, report = run_verifier(repo, packet, tmp_path)

    assert proc.returncode == 1
    assert report["verified"] is False
    assert "artifact_path_invalid" in issue_codes(report)


def test_external_verification_packet_verifier_rejects_absolute_artifact_path(
    tmp_path: Path,
) -> None:
    repo = make_minimal_repo(tmp_path)
    packet = build_packet(repo, tmp_path)

    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["artifact_records"][0]["path"] = "/tmp/status.json"
    packet.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    proc, report = run_verifier(repo, packet, tmp_path)

    assert proc.returncode == 1
    assert report["verified"] is False
    assert "artifact_path_invalid" in issue_codes(report)


def test_external_verification_packet_verifier_detects_boundary_mismatch(
    tmp_path: Path,
) -> None:
    repo = make_minimal_repo(tmp_path)
    packet = build_packet(repo, tmp_path)

    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["packet_boundary"] = "release authority"
    packet.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    proc, report = run_verifier(repo, packet, tmp_path)

    assert proc.returncode == 1
    assert report["verified"] is False
    assert "packet_boundary_mismatch" in issue_codes(report)


def test_external_verification_packet_verifier_detects_authority_carrier_mismatch(
    tmp_path: Path,
) -> None:
    repo = make_minimal_repo(tmp_path)
    packet = build_packet(repo, tmp_path)

    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["authority_carrier"] = "different authority path"
    packet.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    proc, report = run_verifier(repo, packet, tmp_path)

    assert proc.returncode == 1
    assert report["verified"] is False
    assert "authority_carrier_mismatch" in issue_codes(report)


def test_external_verification_packet_verifier_detects_schema_id_mismatch(
    tmp_path: Path,
) -> None:
    repo = make_minimal_repo(tmp_path)
    packet = build_packet(repo, tmp_path)

    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["schema_id"] = "wrong.schema"
    packet.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    proc, report = run_verifier(repo, packet, tmp_path)

    assert proc.returncode == 1
    assert report["verified"] is False
    assert "schema_id_mismatch" in issue_codes(report)


def test_external_verification_packet_verifier_detects_packet_status_mismatch(
    tmp_path: Path,
) -> None:
    repo = make_minimal_repo(tmp_path)
    packet = build_packet(repo, tmp_path)

    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["packet_status"] = "verified"
    packet.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    proc, report = run_verifier(repo, packet, tmp_path)

    assert proc.returncode == 1
    assert report["verified"] is False
    assert "packet_status_mismatch" in issue_codes(report)


def test_external_verification_packet_verifier_reports_invalid_json_packet(
    tmp_path: Path,
) -> None:
    repo = make_minimal_repo(tmp_path)
    packet = tmp_path / "external_verification_packet_v0.json"
    packet.write_text("{not json\n", encoding="utf-8")

    proc, report = run_verifier(repo, packet, tmp_path)

    assert proc.returncode == 1
    assert report["verified"] is False
    assert "verification_exception" in issue_codes(report)


def test_external_verification_packet_verifier_report_is_written_to_declared_path(
    tmp_path: Path,
) -> None:
    repo = make_minimal_repo(tmp_path)
    packet = build_packet(repo, tmp_path)

    out_report = tmp_path / "custom" / "verify_report.json"

    subprocess.run(
        [
            sys.executable,
            str(VERIFIER),
            "--packet",
            str(packet),
            "--repo-root",
            str(repo),
            "--out-json",
            str(out_report),
        ],
        check=True,
    )

    assert out_report.is_file()
    report = json.loads(out_report.read_text(encoding="utf-8"))
    assert report["verified"] is True
    assert report["error_count"] == 0


def test_external_verification_packet_verifier_does_not_write_inside_repo_by_default(
    tmp_path: Path,
) -> None:
    repo = make_minimal_repo(tmp_path)
    packet = build_packet(repo, tmp_path)

    proc, report = run_verifier(repo, packet, tmp_path)

    assert proc.returncode == 0
    assert report["verified"] is True
    assert not (repo / "external_verification_packet_verify_report.json").exists()
    assert not (repo / "out" / "external_verification_packet_verify_report.json").exists()

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.tools.check_quality_ledger_status_parity import (  # noqa: E402
    parity_errors,
)
from PULSE_safe_pack_v0.tools.render_quality_ledger import (  # noqa: E402
    write_quality_ledger,
)


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def status_payload() -> dict:
    return {
        "version": "1.0.0-core",
        "created_utc": "2026-06-14T23:37:48.924028Z",
        "metrics": {
            "run_mode": "core",
            "git_sha": "474806a7803683b0684a5244cccc0bae4cc54819",
            "run_key": (
                "GITHUB_RUN_ID=27515699802|"
                "GITHUB_RUN_NUMBER=5539|"
                "GITHUB_WORKFLOW=PULSE CI"
            ),
            "RDSI": 0.92,
        },
        "gates": {
            "detectors_materialized_ok": False,
            "refusal_delta_evidence_present": True,
            "q1_grounded_ok": True,
        },
    }


def minimal_ledger_html(
    *,
    refusal_gate_status: str = "PASS",
    git_sha: str | None = None,
    include_gate_table: bool = True,
    include_refusal_gate: bool = True,
    gate_section_title: str = "Other gates",
    gate_table_attrs: str | None = None,
    extra_gate_rows: str = "",
    diagnostics_title: str = "Diagnostics",
    diagnostics_header: str = "<tr><th>Field</th><th>Value</th></tr>",
    diagnostics_rows: str = "",
    traceability_table_attrs: str | None = None,
    duplicate_identity_rows: str = "",
) -> str:
    status = status_payload()
    if git_sha is None:
        git_sha = status["metrics"]["git_sha"]

    if gate_table_attrs is None:
        gate_table_attrs = ' data-pulse-ledger-table="gate-status"'

    if traceability_table_attrs is None:
        traceability_table_attrs = ' data-pulse-ledger-table="traceability"'

    refusal_row = ""
    if include_refusal_gate:
        refusal_row = f"""
        <tr>
          <td><code>refusal_delta_evidence_present</code></td>
          <td><span>{refusal_gate_status}</span></td>
        </tr>
        """

    gate_table = ""
    if include_gate_table:
        gate_table = f"""
<h2>{gate_section_title}</h2>
<table{gate_table_attrs}>
  <thead>
    <tr><th>Gate</th><th>Status</th></tr>
  </thead>
  <tbody>
    <tr>
      <td><code>detectors_materialized_ok</code></td>
      <td><span>FAIL</span></td>
    </tr>
    <tr>
      <td><code>q1_grounded_ok</code></td>
      <td><span>PASS</span></td>
    </tr>
    {refusal_row}
    {extra_gate_rows}
  </tbody>
</table>
"""

    return f"""
<!doctype html>
<html>
<body>
<h1>PULSE Quality Ledger</h1>

{gate_table}

<h2>{diagnostics_title}</h2>
<table>
  <thead>
    {diagnostics_header}
  </thead>
  <tbody>
    {diagnostics_rows}
  </tbody>
</table>

<h2>Traceability</h2>
<table{traceability_table_attrs}>
  <thead>
    <tr><th>Field</th><th>Value</th></tr>
  </thead>
  <tbody>
    <tr>
      <td><code>created_utc</code></td>
      <td>2026-06-14T23:37:48.924028Z</td>
    </tr>
    <tr>
      <td><code>metrics.git_sha</code></td>
      <td>{git_sha}</td>
    </tr>
    <tr>
      <td><code>metrics.run_key</code></td>
      <td>GITHUB_RUN_ID=27515699802|GITHUB_RUN_NUMBER=5539|GITHUB_WORKFLOW=PULSE CI</td>
    </tr>
    {duplicate_identity_rows}
  </tbody>
</table>
</body>
</html>
"""


def test_quality_ledger_parity_passes_for_renderer_output(
    tmp_path: Path,
) -> None:
    status_path = tmp_path / "status.json"
    ledger_path = tmp_path / "report_card.html"
    status = status_payload()

    write_json(status_path, status)
    write_quality_ledger(status_path, ledger_path)

    html = ledger_path.read_text(encoding="utf-8")
    assert parity_errors(status, html) == []


def test_quality_ledger_parity_fails_when_gate_surface_drifts() -> None:
    status = status_payload()
    html = minimal_ledger_html(refusal_gate_status="FAIL")

    errors = parity_errors(status, html)

    assert any(
        "gate status mismatch: refusal_delta_evidence_present" in err
        and "ledger=FAIL" in err
        and "expected PASS" in err
        for err in errors
    )


def test_quality_ledger_parity_rejects_stale_gate_rows() -> None:
    status = status_payload()
    html = minimal_ledger_html(
        extra_gate_rows="""
        <tr>
          <td><code>old_removed_gate</code></td>
          <td><span>PASS</span></td>
        </tr>
        """,
    )

    errors = parity_errors(status, html)

    assert any(
        "stale gate row present in ledger" in err
        and "old_removed_gate" in err
        for err in errors
    )


def test_quality_ledger_parity_uses_status_gates_not_top_level_mirror() -> None:
    status = status_payload()
    status["refusal_delta_evidence_present"] = False

    html = minimal_ledger_html(refusal_gate_status="PASS")

    assert parity_errors(status, html) == []


def test_quality_ledger_parity_ignores_non_gate_table_status_rows() -> None:
    status = status_payload()
    html = minimal_ledger_html(
        refusal_gate_status="PASS",
        diagnostics_rows="""
        <tr>
          <td><code>refusal_delta_evidence_present</code></td>
          <td>FAIL</td>
        </tr>
        """,
    )

    assert parity_errors(status, html) == []


def test_quality_ledger_parity_diagnostic_row_cannot_satisfy_missing_gate() -> None:
    status = status_payload()
    html = minimal_ledger_html(
        include_refusal_gate=False,
        diagnostics_rows="""
        <tr>
          <td><code>refusal_delta_evidence_present</code></td>
          <td>PASS</td>
        </tr>
        """,
    )

    errors = parity_errors(status, html)

    assert any(
        "gate row missing" in err
        and "refusal_delta_evidence_present" in err
        for err in errors
    )


def test_quality_ledger_parity_fails_when_run_identity_drifts() -> None:
    status = status_payload()
    html = minimal_ledger_html(git_sha="wrong-git-sha")

    errors = parity_errors(status, html)

    assert any(
        "run identity mismatch: metrics.git_sha" in err
        for err in errors
    )


def test_quality_ledger_parity_fails_on_conflicting_identity_duplicates() -> None:
    status = status_payload()
    html = minimal_ledger_html(
        duplicate_identity_rows="""
        <tr>
          <td><code>metrics.git_sha</code></td>
          <td>stale-git-sha</td>
        </tr>
        """,
    )

    errors = parity_errors(status, html)

    assert any(
        "run identity field must appear exactly once: metrics.git_sha" in err
        for err in errors
    )


def test_quality_ledger_parity_cli_fails_closed_on_mismatch(
    tmp_path: Path,
) -> None:
    status_path = tmp_path / "status.json"
    ledger_path = tmp_path / "report_card.html"
    status = status_payload()

    write_json(status_path, status)
    ledger_path.write_text(
        minimal_ledger_html(refusal_gate_status="FAIL"),
        encoding="utf-8",
    )

    script = (
        REPO_ROOT
        / "PULSE_safe_pack_v0"
        / "tools"
        / "check_quality_ledger_status_parity.py"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--status",
            str(status_path),
            "--ledger",
            str(ledger_path),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Quality Ledger status parity failed" in result.stdout
    assert "refusal_delta_evidence_present" in result.stdout


def test_quality_ledger_parity_diagnostics_gates_section_cannot_satisfy_missing_gate() -> None:
    status = status_payload()
    html = minimal_ledger_html(
        include_gate_table=False,
        diagnostics_title="Diagnostics gates",
        diagnostics_header="<tr><th>Gate</th><th>Status</th></tr>",
        diagnostics_rows="""
        <tr>
          <td><code>detectors_materialized_ok</code></td>
          <td>FAIL</td>
        </tr>
        <tr>
          <td><code>q1_grounded_ok</code></td>
          <td>PASS</td>
        </tr>
        <tr>
          <td><code>refusal_delta_evidence_present</code></td>
          <td>PASS</td>
        </tr>
        """,
    )

    errors = parity_errors(status, html)

    assert any(
        "no authoritative Gate/Status table found" in err
        for err in errors
    )
    assert any(
        "gate row missing" in err
        and "refusal_delta_evidence_present" in err
        for err in errors
    )


def test_quality_ledger_parity_diagnostics_gates_section_cannot_conflict_with_real_gate_table() -> None:
    status = status_payload()
    html = minimal_ledger_html(
        refusal_gate_status="PASS",
        diagnostics_title="Diagnostics gates",
        diagnostics_header="<tr><th>Gate</th><th>Status</th></tr>",
        diagnostics_rows="""
        <tr>
          <td><code>refusal_delta_evidence_present</code></td>
          <td>FAIL</td>
        </tr>
        """,
    )

    assert parity_errors(status, html) == []


def test_quality_ledger_parity_rejects_stale_gate_row_with_unknown() -> None:
    status = status_payload()
    html = minimal_ledger_html(
        extra_gate_rows="""
        <tr>
          <td><code>old_removed_gate</code></td>
          <td>UNKNOWN</td>
        </tr>
        """,
    )

    errors = parity_errors(status, html)

    assert any(
        "stale gate row present in ledger" in err
        and "old_removed_gate" in err
        for err in errors
    )


def test_quality_ledger_parity_rejects_stale_gate_row_with_pending() -> None:
    status = status_payload()
    html = minimal_ledger_html(
        extra_gate_rows="""
        <tr>
          <td><code>old_removed_gate</code></td>
          <td>PENDING</td>
        </tr>
        """,
    )

    errors = parity_errors(status, html)

    assert any(
        "stale gate row present in ledger" in err
        and "old_removed_gate" in err
        for err in errors
    )


def test_quality_ledger_parity_rejects_current_gate_row_with_unknown() -> None:
    status = status_payload()
    html = minimal_ledger_html(refusal_gate_status="UNKNOWN")

    errors = parity_errors(status, html)

    assert any(
        "invalid visible status" in err
        and "refusal_delta_evidence_present" in err
        for err in errors
    )


def test_quality_ledger_parity_rejects_current_gate_row_with_blank_status() -> None:
    status = status_payload()
    html = minimal_ledger_html(refusal_gate_status="")

    errors = parity_errors(status, html)

    assert any(
        "invalid visible status" in err
        and "refusal_delta_evidence_present" in err
        for err in errors
    )


def test_quality_ledger_parity_requires_authoritative_gate_table_marker() -> None:
    status = status_payload()
    html = minimal_ledger_html(gate_table_attrs="")

    errors = parity_errors(status, html)

    assert any(
        "no authoritative Gate/Status table found" in err
        for err in errors
    )


def test_quality_ledger_parity_requires_traceability_table_marker() -> None:
    status = status_payload()
    html = minimal_ledger_html(traceability_table_attrs="")

    errors = parity_errors(status, html)

    assert any(
        "no authoritative Traceability Field/Value table found" in err
        for err in errors
    )


def test_quality_ledger_parity_rejects_gate_like_table_in_unknown_gate_section() -> None:
    status = status_payload()
    html = minimal_ledger_html(
        gate_section_title="Diagnostics gates",
        refusal_gate_status="PASS",
    )

    errors = parity_errors(status, html)

    assert any(
        "no authoritative Gate/Status table found" in err
        for err in errors
    )


def test_pulse_report_upload_is_gated_on_quality_ledger_parity_success() -> None:
    workflow = (
        REPO_ROOT
        / ".github"
        / "workflows"
        / "pulse_ci.yml"
    ).read_text(encoding="utf-8")

    assert "id: quality_ledger_final_render" in workflow
    assert "id: quality_ledger_status_parity" in workflow
    assert "steps.quality_ledger_status_parity.outcome == 'success'" in workflow
    assert "steps.quality_ledger_final_render.outcome == 'success'" in workflow

    upload_pos = workflow.find("- name: Upload artifacts")
    assert upload_pos != -1

    upload_block = workflow[upload_pos: workflow.find("\n      - name:", upload_pos + 1)]
    assert "if: always()" not in upload_block
    assert "steps.quality_ledger_status_parity.outcome == 'success'" in upload_block

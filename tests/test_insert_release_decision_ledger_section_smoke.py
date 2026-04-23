#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "PULSE_safe_pack_v0"
    / "tools"
    / "insert_release_decision_ledger_section.py"
)


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _report_with_body() -> str:
    return """<!doctype html>
<html>
<head>
    <title>PULSE report</title>
</head>
<body>
  <h1>Quality Ledger</h1>
  <p>Existing report content.</p>
</body>
</html>
"""


def _report_with_body() -> str:
    return """
- PULSEmech report
+ PULSE report
# Quality Ledger

Existing report content.

"""


def _section(level: str = "STAGE-PASS") -> str:
    return f"""<section id="release-decision-v0" class="release-decision-v0">
  <h2>Release decision v0</h2>
  <span>{level}</span>
</section>
"""


def test_insert_section_before_closing_body() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-insert-release-section-") as tmp:
        tmp_path = Path(tmp)
        report = tmp_path / "report_card.html"
        section = tmp_path / "release_decision_v0_ledger_section.html"
        out = tmp_path / "report_card.with_release_decision.html"

        _write(report, _report_with_body())
        _write(section, _section("STAGE-PASS"))

        result = _run(
            "--report",
            str(report),
            "--section",
            str(section),
            "--out",
            str(out),
        )

        assert result.returncode == 0, result.stdout + result.stderr
        assert out.exists()

        html = _read(out)

        assert "<!-- PULSE_RELEASE_DECISION_V0_SECTION_START -->" in html
        assert "<!-- PULSE_RELEASE_DECISION_V0_SECTION_END -->" in html
        assert "release-decision-v0" in html
        assert "STAGE-PASS" in html
        assert html.index("release-decision-v0") < html.lower().index("</body>")


def test_append_section_when_report_has_no_body_close() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-insert-release-section-") as tmp:
        tmp_path = Path(tmp)
        report = tmp_path / "report_card.html"
        section = tmp_path / "release_decision_v0_ledger_section.html"
        out = tmp_path / "report_card.with_release_decision.html"

        _write(report, _report_without_body())
        _write(section, _section("PROD-PASS"))

        result = _run(
            "--report",
            str(report),
            "--section",
            str(section),
            "--out",
            str(out),
        )

        assert result.returncode == 0, result.stdout + result.stderr
        assert out.exists()

        html = _read(out)

        assert "Existing report content without body tag." in html
        assert "PROD-PASS" in html
        assert "<!-- PULSE_RELEASE_DECISION_V0_SECTION_START -->" in html
        assert "mode=append_eof" in result.stdout


def test_replace_existing_marked_section() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-insert-release-section-") as tmp:
        tmp_path = Path(tmp)
        report = tmp_path / "report_card.html"
        section = tmp_path / "release_decision_v0_ledger_section.html"
        out = tmp_path / "report_card.with_release_decision.html"

        old_report = """<!doctype html>
<html>
<body>
  <h1>Quality Ledger</h1>

<!-- PULSE_RELEASE_DECISION_V0_SECTION_START -->
<section id="release-decision-v0">
  <span>OLD</span>
</section>
<!-- PULSE_RELEASE_DECISION_V0_SECTION_END -->

</body>
</html>
"""
        _write(report, old_report)
        _write(section, _section("PROD-PASS"))

        result = _run(
            "--report",
            str(report),
            "--section",
            str(section),
            "--out",
            str(out),
        )

        assert result.returncode == 0, result.stdout + result.stderr
        assert out.exists()

        html = _read(out)

        assert "OLD" not in html
        assert "PROD-PASS" in html
        assert html.count("PULSE_RELEASE_DECISION_V0_SECTION_START") == 1
        assert html.count("PULSE_RELEASE_DECISION_V0_SECTION_END") == 1
        assert "mode=replace_existing_marked_section" in result.stdout


def test_refuse_duplicate_unmarked_release_decision_section() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-insert-release-section-") as tmp:
        tmp_path = Path(tmp)
        report = tmp_path / "report_card.html"
        section = tmp_path / "release_decision_v0_ledger_section.html"
        out = tmp_path / "report_card.with_release_decision.html"

        report_with_unmarked_section = """<!doctype html>
<html>
<body>
  <h1>Quality Ledger</h1>
  <section id="release-decision-v0">
    <span>Existing unmarked section</span>
  </section>
</body>
</html>
"""
        _write(report, report_with_unmarked_section)
        _write(section, _section("STAGE-PASS"))

        result = _run(
            "--report",
            str(report),
            "--section",
            str(section),
            "--out",
            str(out),
        )

        assert result.returncode == 1
        assert not out.exists()
        assert "refusing to insert a duplicate" in result.stderr


def test_missing_section_fails_by_default() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-insert-release-section-") as tmp:
        tmp_path = Path(tmp)
        report = tmp_path / "report_card.html"
        missing_section = tmp_path / "missing_release_decision_v0_ledger_section.html"
        out = tmp_path / "report_card.with_release_decision.html"

        _write(report, _report_with_body())

        result = _run(
            "--report",
            str(report),
            "--section",
            str(missing_section),
            "--out",
            str(out),
        )

        assert result.returncode == 1
        assert not out.exists()
        assert "release decision section is missing" in result.stderr


def test_allow_missing_section_inserts_explicit_missing_placeholder() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-insert-release-section-") as tmp:
        tmp_path = Path(tmp)
        report = tmp_path / "report_card.html"
        missing_section = tmp_path / "missing_release_decision_v0_ledger_section.html"
        out = tmp_path / "report_card.with_release_decision.html"

        _write(report, _report_with_body())

        result = _run(
            "--report",
            str(report),
            "--section",
            str(missing_section),
            "--out",
            str(out),
            "--allow-missing-section",
        )

        assert result.returncode == 0, result.stdout + result.stderr
        assert out.exists()

        html = _read(out)

        assert "MISSING" in html
        assert "must not infer" in html
        assert "STAGE-PASS" in html
        assert "PROD-PASS" in html
        assert "<!-- PULSE_RELEASE_DECISION_V0_SECTION_START -->" in html


def test_in_place_updates_report_file() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-insert-release-section-") as tmp:
        tmp_path = Path(tmp)
        report = tmp_path / "report_card.html"
        section = tmp_path / "release_decision_v0_ledger_section.html"

        _write(report, _report_with_body())
        _write(section, _section("STAGE-PASS"))

        result = _run(
            "--report",
            str(report),
            "--section",
            str(section),
            "--in-place",
        )

        assert result.returncode == 0, result.stdout + result.stderr

        html = _read(report)

        assert "STAGE-PASS" in html
        assert "<!-- PULSE_RELEASE_DECISION_V0_SECTION_START -->" in html
        assert "out=" in result.stdout


def test_partial_marker_pair_fails_closed() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-insert-release-section-") as tmp:
        tmp_path = Path(tmp)
        report = tmp_path / "report_card.html"
        section = tmp_path / "release_decision_v0_ledger_section.html"
        out = tmp_path / "report_card.with_release_decision.html"

        broken_marked_report = """<!doctype html>
<html>
<body>
  <h1>Quality Ledger</h1>
  <!-- PULSE_RELEASE_DECISION_V0_SECTION_START -->
  <section id="release-decision-v0">
    <span>Broken marker pair</span>
  </section>
</body>
</html>
"""
        _write(report, broken_marked_report)
        _write(section, _section("PROD-PASS"))

        result = _run(
            "--report",
            str(report),
            "--section",
            str(section),
            "--out",
            str(out),
        )

        assert result.returncode == 1
        assert not out.exists()
        assert "both START and END markers are required" in result.stderr


def main() -> int:
    tests = [
        test_insert_section_before_closing_body,
        test_append_section_when_report_has_no_body_close,
        test_replace_existing_marked_section,
        test_refuse_duplicate_unmarked_release_decision_section,
        test_missing_section_fails_by_default,
        test_allow_missing_section_inserts_explicit_missing_placeholder,
        test_in_place_updates_report_file,
        test_partial_marker_pair_fails_closed,
    ]

    for test in tests:
        try:
            test()
        except AssertionError as exc:
            print(f"ERROR in {test.__name__}: {exc}")
            return 1
        except Exception as exc:
            print(f"ERROR in {test.__name__}: unexpected exception: {exc}")
            return 1

    print("OK: release decision ledger insertion smoke checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

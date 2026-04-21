#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple


REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_REPORT = (
    REPO_ROOT
    / "PULSE_safe_pack_v0"
    / "artifacts"
    / "report_card.html"
)

DEFAULT_SECTION = (
    REPO_ROOT
    / "PULSE_safe_pack_v0"
    / "artifacts"
    / "release_decision_v0_ledger_section.html"
)

DEFAULT_OUT = (
    REPO_ROOT
    / "PULSE_safe_pack_v0"
    / "artifacts"
    / "report_card.with_release_decision.html"
)

START_MARKER = "<!-- PULSE_RELEASE_DECISION_V0_SECTION_START -->"
END_MARKER = "<!-- PULSE_RELEASE_DECISION_V0_SECTION_END -->"

RELEASE_SECTION_ID_RE = re.compile(
    r"""id\s*=\s*["']release-decision-v0["']""",
    flags=re.IGNORECASE,
)

CLOSING_BODY_RE = re.compile(
    r"</body\s*>",
    flags=re.IGNORECASE,
)


class ComposeResult(NamedTuple):
    html: str
    mode: str


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _wrap_section(section_html: str) -> str:
    return (
        f"{START_MARKER}\n"
        f"{section_html.rstrip()}\n"
        f"{END_MARKER}"
    )


def _missing_section_html(section_path: Path) -> str:
    return f"""
<section id="release-decision-v0" class="release-decision-v0">
  <h2>Release decision v0</h2>
  <p>
    <strong>MISSING</strong>
  </p>
  <p>
    The rendered release decision Ledger section was not available at
    <code>{_rel(section_path)}</code>.
  </p>
  <p>
    This composition helper must not infer <code>STAGE-PASS</code>,
    <code>PROD-PASS</code>, or any release-level result from a missing
    release-decision section.
  </p>
</section>
""".strip()


def _has_release_decision_section(html: str) -> bool:
    return RELEASE_SECTION_ID_RE.search(html) is not None


def _replace_existing_marked_section(report_html: str, wrapped_section: str) -> str | None:
    start = report_html.find(START_MARKER)
    end = report_html.find(END_MARKER)

    if start == -1 and end == -1:
        return None

    if start == -1 or end == -1:
        raise ValueError(
            "report contains only one release-decision marker; "
            "both START and END markers are required"
        )

    if end < start:
        raise ValueError(
            "release-decision END marker appears before START marker"
        )

    end_after = end + len(END_MARKER)

    return (
        report_html[:start].rstrip()
        + "\n\n"
        + wrapped_section
        + "\n\n"
        + report_html[end_after:].lstrip()
    )


def _insert_before_closing_body(report_html: str, wrapped_section: str) -> ComposeResult:
    match = None
    for match in CLOSING_BODY_RE.finditer(report_html):
        pass

    if match is None:
        return ComposeResult(
            html=report_html.rstrip() + "\n\n" + wrapped_section + "\n",
            mode="append_eof",
        )

    insert_at = match.start()

    composed = (
        report_html[:insert_at].rstrip()
        + "\n\n"
        + wrapped_section
        + "\n\n"
        + report_html[insert_at:].lstrip()
    )

    return ComposeResult(html=composed, mode="insert_before_body_close")


def compose_report_with_release_decision_section(
    *,
    report_html: str,
    section_html: str,
) -> ComposeResult:
    wrapped_section = _wrap_section(section_html)

    replaced = _replace_existing_marked_section(report_html, wrapped_section)
    if replaced is not None:
        return ComposeResult(html=replaced, mode="replace_existing_marked_section")

    if _has_release_decision_section(report_html):
        raise ValueError(
            "report already contains a release-decision section but no "
            "PULSE_RELEASE_DECISION_V0 markers; refusing to insert a duplicate"
        )

    return _insert_before_closing_body(report_html, wrapped_section)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Insert the rendered release_decision_v0 Quality Ledger section "
            "into a report_card.html artifact."
        )
    )

    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT),
        help="Path to the existing report_card.html artifact.",
    )
    parser.add_argument(
        "--section",
        default=str(DEFAULT_SECTION),
        help="Path to release_decision_v0_ledger_section.html.",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help=(
            "Path to write the composed report. Ignored when --in-place is used."
        ),
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite --report instead of writing --out.",
    )
    parser.add_argument(
        "--allow-missing-section",
        action="store_true",
        help=(
            "Insert an explicit MISSING placeholder when the rendered release "
            "decision section is absent. Without this flag, missing section input "
            "is an error."
        ),
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    report_path = Path(args.report)
    section_path = Path(args.section)
    out_path = report_path if args.in_place else Path(args.out)

    if not report_path.is_absolute():
        report_path = REPO_ROOT / report_path
    if not section_path.is_absolute():
        section_path = REPO_ROOT / section_path
    if not out_path.is_absolute():
        out_path = REPO_ROOT / out_path

    if not report_path.exists():
        print(
            f"ERROR: report artifact is missing: {_rel(report_path)}",
            file=sys.stderr,
        )
        return 1

    try:
        report_html = _read_text(report_path)
    except Exception as exc:
        print(
            f"ERROR: could not read report artifact {_rel(report_path)}: {exc}",
            file=sys.stderr,
        )
        return 1

    if section_path.exists():
        try:
            section_html = _read_text(section_path)
        except Exception as exc:
            print(
                f"ERROR: could not read release decision section "
                f"{_rel(section_path)}: {exc}",
                file=sys.stderr,
            )
            return 1

        if not section_html.strip():
            print(
                f"ERROR: release decision section is empty: {_rel(section_path)}",
                file=sys.stderr,
            )
            return 1
    else:
        if not args.allow_missing_section:
            print(
                f"ERROR: release decision section is missing: {_rel(section_path)}",
                file=sys.stderr,
            )
            print(
                "Hint: run render_release_decision_ledger_section.py first, "
                "or pass --allow-missing-section to insert an explicit MISSING "
                "placeholder.",
                file=sys.stderr,
            )
            return 1

        section_html = _missing_section_html(section_path)

    try:
        result = compose_report_with_release_decision_section(
            report_html=report_html,
            section_html=section_html,
        )
    except Exception as exc:
        print(f"ERROR: could not compose report: {exc}", file=sys.stderr)
        return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(result.html, encoding="utf-8")

    print(
        "OK: inserted release decision Ledger section "
        f"mode={result.mode} report={_rel(report_path)} out={_rel(out_path)}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

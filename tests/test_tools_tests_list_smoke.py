#!/usr/bin/env python3
"""
Smoke guard: ensure tools-tests suite remains coherent and covers all local smoke scripts.

Field source of truth:
- ci/tools-tests.list

Why dual-mode?
- During migration, CI may still run an inline workflow list (tests=(...)) while the repo already
  has the manifest. In that phase, we enforce equivalence between the inline list and the manifest.
- After migration, the inline list disappears; then we require the workflow to reference the manifest.

Rules enforced:
- Any tests/ file matching:
    * test_*_smoke.py
    * test_*_fail_closed.py
    * test_*_e2e_smoke.py
  must appear in ci/tools-tests.list (unless allowlisted).
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import List, Optional, Set


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "pulse_ci.yml"
CORE_WORKFLOW = ROOT / ".github" / "workflows" / "pulse_core_ci.yml"
RUNBOOK = ROOT / "docs" / "RUNBOOK.md"
ENV_FILE = ROOT / "environment.yml"
REQ_FILE = ROOT / "requirements.txt"
MANIFEST = ROOT / "ci" / "tools-tests.list"
TESTS_DIR = ROOT / "tests"

# If you intentionally exclude a smoke script from tools-tests, add it here:
ALLOW_MISSING: Set[str] = set()

SMOKE_GLOBS = [
    "test_*_smoke.py",
    "test_*_fail_closed.py",
    "test_*_e2e_smoke.py",
]


def _assert_no_duplicates(items: List[str], label: str) -> None:
    seen = set()
    dups = set()
    for x in items:
        if x in seen:
            dups.add(x)
        seen.add(x)
    if dups:
        raise AssertionError(
            f"Duplicate entries in {label}:\n" + "\n".join(f"  - {d}" for d in sorted(dups))
        )


def _read_manifest() -> List[str]:
    if not MANIFEST.is_file():
        raise AssertionError(f"Missing tools-tests manifest: {MANIFEST}")

    entries: List[str] = []
    for raw in MANIFEST.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue

        # Enforce: one path per line
        parts = line.split()
        if len(parts) != 1:
            raise AssertionError(
                f"Invalid manifest line in {MANIFEST} (expected one path per line): {raw!r}"
            )

        entries.append(parts[0])

    if not entries:
        raise AssertionError(f"Manifest is empty after filtering: {MANIFEST}")

    return entries


def _discover_smoke_scripts() -> Set[str]:
    smoke: Set[str] = set()
    for pat in SMOKE_GLOBS:
        for p in TESTS_DIR.glob(pat):
            smoke.add(f"tests/{p.name}")
    return smoke


def _extract_inline_suite_from_workflow(yml_text: str) -> Optional[List[str]]:
    """
    Find a tests=(...) bash array block in the workflow that looks like the tools-tests suite.

    We select the block that contains these sentinel entries:
      - tests/test_exporters.py
      - tests/test_tools_tests_list_smoke.py
    """
    lines = yml_text.splitlines()

    start_rx = re.compile(r"^\s*tests=\(\s*$")
    end_rx = re.compile(r"^\s*\)\s*$")
    entry_rx = re.compile(r"""["'](tests/test_[^"']+\.py)["']""")

    best: Optional[List[str]] = None

    i = 0
    while i < len(lines):
        if start_rx.match(lines[i]):
            j = i + 1
            block_entries: List[str] = []
            block_raw: List[str] = []
            while j < len(lines) and not end_rx.match(lines[j]):
                block_raw.append(lines[j])
                m = entry_rx.search(lines[j])
                if m:
                    block_entries.append(m.group(1))
                j += 1

            # Heuristic: pick the suite block containing the two known entries
            raw_text = "\n".join(block_raw)
            if "tests/test_exporters.py" in raw_text and "tests/test_tools_tests_list_smoke.py" in raw_text:
                best = block_entries
                break

            i = j + 1
            continue

        i += 1

    if best is None:
        return None

    if not best:
        raise AssertionError("Found tests=(...) block in workflow but extracted 0 entries (unexpected).")

    return best


def test_tools_tests_list_covers_smoke_scripts() -> None:
    if not WORKFLOW.is_file():
        raise AssertionError(f"Missing workflow file: {WORKFLOW}")

    # Canonical suite definition
    manifest = _read_manifest()
    _assert_no_duplicates(manifest, "ci/tools-tests.list")

    yml = WORKFLOW.read_text(encoding="utf-8", errors="replace")
    inline = _extract_inline_suite_from_workflow(yml)

    if inline is not None:
        # Migration phase (or legacy state): enforce equivalence to prevent drift.
        # Prefer strict order equality (suite is explicit and ordered).
        if inline != manifest:
            raise AssertionError(
                "tools-tests suite drift detected between workflow inline list and ci/tools-tests.list.\n"
                f"- workflow inline entries: {len(inline)}\n"
                f"- manifest entries:       {len(manifest)}\n\n"
                "Fix: make .github/workflows/pulse_ci.yml and ci/tools-tests.list match exactly."
            )
    else:
        # Manifest-based workflow: require wiring reference exists.
        if "ci/tools-tests.list" not in yml:
            raise AssertionError(
                "CI suite definition not detected.\n"
                "- No tests=(...) inline list found in the workflow\n"
                "- And workflow does not reference ci/tools-tests.list\n\n"
                "Fix: update the tools-tests step to read ci/tools-tests.list."
            )

    # Fail-closed: every manifest path must exist
    missing_files = [rel for rel in manifest if not (ROOT / rel).is_file()]
    if missing_files:
        raise AssertionError(
            "ci/tools-tests.list references missing files:\n"
            + "\n".join(f"  - {m}" for m in missing_files)
        )

    # Coverage: all discovered smoke scripts must be listed (unless allowlisted)
    listed_set = set(manifest)
    smoke = _discover_smoke_scripts()
    missing = sorted((smoke - listed_set) - ALLOW_MISSING)
    if missing:
        raise AssertionError(
            "Smoke scripts missing from ci/tools-tests.list:\n"
            + "\n".join(f"  - {m}" for m in missing)
            + "\n\nFix: add them to ci/tools-tests.list."
        )

    # Stale entries: only check those pointing at tests/test_*.py
    all_test_files = {f"tests/{p.name}" for p in TESTS_DIR.glob("test_*.py")}
    stale = sorted({x for x in listed_set if x.startswith("tests/test_")} - all_test_files)
    if stale:
        raise AssertionError(
            "ci/tools-tests.list contains stale test entries:\n"
            + "\n".join(f"  - {s}" for s in stale)
        )




def test_pytest_tests_list_keeps_core_baseline() -> None:
    manifest_path = ROOT / "ci" / "pytest-tests.list"

    if not WORKFLOW.is_file():
        raise AssertionError(f"Missing workflow file: {WORKFLOW}")
    if not manifest_path.is_file():
        raise AssertionError(f"Missing pytest manifest: {manifest_path}")

    manifest: List[str] = []
    for raw in manifest_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) != 1:
            raise AssertionError(
                f"Invalid manifest line in {manifest_path} (expected one path per line): {raw!r}"
            )
        manifest.append(parts[0])

    if not manifest:
        raise AssertionError(f"Manifest is empty after filtering: {manifest_path}")

    _assert_no_duplicates(manifest, "ci/pytest-tests.list")

    yml = WORKFLOW.read_text(encoding="utf-8", errors="replace")
    if "ci/pytest-tests.list" not in yml:
        raise AssertionError(
            "Targeted pytest manifest wiring not detected in pulse_ci.yml.\n"
            "Fix: update the targeted pytest step to read ci/pytest-tests.list."
        )

    missing_files = [rel for rel in manifest if not (ROOT / rel).is_file()]
    if missing_files:
        raise AssertionError(
            "ci/pytest-tests.list references missing files:\n"
            + "\n".join(f" - {m}" for m in missing_files)
        )

    required = "tests/test_core_baseline_v0.py"
    if required not in manifest:
        raise AssertionError(
            "Targeted pytest manifest must include tests/test_core_baseline_v0.py.\n\n"
            "Fix: add it to ci/pytest-tests.list."
        )


def _core_baseline_check_step_present(yml_text: str) -> bool:
    lines = yml_text.splitlines()
    step_name_rx = re.compile(r"^\s*-\s*name:\s*Run core baseline check test\s*$")

    i = 0
    while i < len(lines):
        if not step_name_rx.match(lines[i]):
            i += 1
            continue

        step_indent = len(lines[i]) - len(lines[i].lstrip())
        j = i + 1
        block: List[str] = []

        while j < len(lines):
            cur = lines[j]
            stripped = cur.lstrip()
            indent = len(cur) - len(stripped)

            if stripped.startswith("- name:") and indent <= step_indent:
                break

            block.append(cur)
            j += 1

        block_text = "\n".join(block)
        return 'python -m pytest -q tests/test_core_baseline_v0.py' in block_text

    return False


def test_pulse_core_ci_keeps_core_baseline_step() -> None:
    if not CORE_WORKFLOW.is_file():
        raise AssertionError(f"Missing core workflow file: {CORE_WORKFLOW}")

    yml = CORE_WORKFLOW.read_text(encoding="utf-8", errors="replace")
    if not _core_baseline_check_step_present(yml):
        raise AssertionError(
            "Core baseline wiring not detected in the "
            "'Run core baseline check test' step of pulse_core_ci.yml.\n"
            "Fix: keep that step and make it run "
            "python -m pytest -q tests/test_core_baseline_v0.py."
        )


def test_pulse_core_ci_python_version_aligns_with_environment() -> None:
    if not CORE_WORKFLOW.is_file():
        raise AssertionError(f"Missing core workflow file: {CORE_WORKFLOW}")
    if not ENV_FILE.is_file():
        raise AssertionError(f"Missing environment file: {ENV_FILE}")

    yml = CORE_WORKFLOW.read_text(encoding="utf-8", errors="replace")
    env_text = ENV_FILE.read_text(encoding="utf-8", errors="replace")

    if not re.search(r'^\s*python-version:\s*["\']?3\.11["\']?\s*$', yml, flags=re.M):
        raise AssertionError(
            "pulse_core_ci.yml must set Python 3.11 in the Set up Python step."
        )

    has_block_python_pin = re.search(
        r"^\s*-\s*python=3\.11\s*$",
        env_text,
        flags=re.M,
    )
    has_inline_python_pin = re.search(
        r"^\s*dependencies:\s*\[.*\bpython=3\.11\b.*\]\s*$",
        env_text,
        flags=re.M,
    )

    if not (has_block_python_pin or has_inline_python_pin):
        raise AssertionError(
            "environment.yml must pin python=3.11 to match pulse_core_ci.yml "
            "(block or inline YAML form)."
        )


def _pulse_ci_has_nonempty_policy_set_guard(yml_text: str) -> bool:
    lines = yml_text.splitlines()
    step_name_rx = re.compile(
        r'^\s*-\s*name:\s*["\']?ci: enforce gates via check_gates \(policy-derived\)["\']?\s*$'
    )

    i = 0
    while i < len(lines):
        if not step_name_rx.match(lines[i]):
            i += 1
            continue

        step_indent = len(lines[i]) - len(lines[i].lstrip())
        j = i + 1
        block: List[str] = []

        while j < len(lines):
            cur = lines[j]
            stripped = cur.lstrip()
            indent = len(cur) - len(stripped)

            if stripped.startswith("- name:") and indent <= step_indent:
                break

            block.append(cur)
            j += 1

        block_text = "\n".join(block)

        has_policy_derivation = bool(
            re.search(
                r'REQ_STR="\$\(python tools/policy_to_require_args\.py(?:\s+\\\n\s*|\s+)'
                r'--policy pulse_gate_policy_v0\.yml(?:\s+\\\n\s*|\s+)'
                r'--set "\$POLICY_SET"(?:\s+\\\n\s*|\s+)'
                r'--format space\)"',
                block_text,
                flags=re.M,
            )
        )
        has_check_gates = 'python "${{ env.PACK_DIR }}/tools/check_gates.py" \\' in block_text

        m = re.search(
            r'if \(\( \$\{#REQ\[@\]\} == 0 \)\); then(?P<branch>.*?)^\s*fi\s*$',
            
            block_text,
            flags=re.M | re.S,
        )
        if not m:
            return False
        empty_branch = m.group("branch")
        has_error = 'echo "::error::derived gate set is empty: ${POLICY_SET}"' in empty_branch
        has_exit = bool(re.search(r'^\s*exit 1\s*$', empty_branch, flags=re.M))

        return bool(
            has_policy_derivation
            and has_error
            and has_exit
            and has_check_gates
        )

    return False


def test_pulse_ci_fails_closed_on_empty_derived_gate_set() -> None:
    yml = WORKFLOW.read_text(encoding="utf-8", errors="replace")

    if not _pulse_ci_has_nonempty_policy_set_guard(yml):
        raise AssertionError(
            "pulse_ci.yml must fail closed when the policy-derived gate set is empty "
            "in the 'ci: enforce gates via check_gates (policy-derived)' step.\n"
            "Fix: keep the REQ derivation, the empty-set check, the explicit "
            "::error:: message, and exit 1 before check_gates.py runs."
        )

def _pulse_ci_has_release_grade_prod_guard(yml_text: str) -> bool:
    lines = yml_text.splitlines()
    step_name_rx = re.compile(
        r'^\s*-\s*name:\s*["\']?ci: require prod run_mode on release-grade runs["\']?\s*$'
    )

    i = 0
    while i < len(lines):
        if not step_name_rx.match(lines[i]):
            i += 1
            continue

        step_indent = len(lines[i]) - len(lines[i].lstrip())
        j = i + 1
        block: List[str] = []

        while j < len(lines):
            cur = lines[j]
            stripped = cur.lstrip()
            indent = len(cur) - len(stripped)

            if stripped.startswith("- name:") and indent <= step_indent:
                break

            block.append(cur)
            j += 1

        block_text = "\n".join(block)

         # Lock the actual release-grade if-expression structure.
        has_if = re.search(
            r"startsWith\(github\.ref,\s*'refs/tags/v'\)\s*\|\|\s*"
            r"startsWith\(github\.ref,\s*'refs/tags/V'\)\s*\|\|\s*"
            r"\(\s*github\.event_name\s*==\s*'workflow_dispatch'\s*&&\s*"
            r"github\.event\.inputs\.strict_external_evidence\s*==\s*'true'\s*\)",
            block_text,
        )
        has_status_read = 'p="PULSE_safe_pack_v0/artifacts/status.json"' in block_text
        has_metrics_extract = 'm=(s.get("metrics") or {})' in block_text
        has_mode_extract = 'mode=str(m.get("run_mode","")).lower()' in block_text
        has_prod_check = 'if mode != "prod":' in block_text
        has_error = (
            "::error::release-grade run requires metrics.run_mode='prod'"
            in block_text
        )
        has_ok = 'print("OK: run_mode=prod")' in block_text

        return bool(
            has_if
            and has_status_read
            and has_metrics_extract
            and has_mode_extract
            and has_prod_check
            and has_error
            and has_ok
        )

    return False


def test_pulse_ci_keeps_release_grade_prod_guard() -> None:
    yml = WORKFLOW.read_text(encoding="utf-8", errors="replace")

    if not _pulse_ci_has_release_grade_prod_guard(yml):
        raise AssertionError(
            "pulse_ci.yml must keep the release-grade run_mode=prod guard in the "
            "'ci: require prod run_mode on release-grade runs' step.\n"
            "Fix: keep the release-grade if-condition, read status.json, extract "
            "metrics, read metrics.run_mode, fail if it is not 'prod', and emit "
            "the explicit error/OK messages."
        )

def _pulse_ci_has_status_v1_schema_validation(
    yml_text: str,
    step_name: str,
    expected_status_path: str,
) -> bool:
    lines = yml_text.splitlines()
    step_name_rx = re.compile(
        rf'^\s*-\s*name:\s*["\']?{re.escape(step_name)}["\']?\s*$'
    )

    i = 0
    while i < len(lines):
        if not step_name_rx.match(lines[i]):
            i += 1
            continue

        step_indent = len(lines[i]) - len(lines[i].lstrip())
        j = i + 1
        block: List[str] = []

        while j < len(lines):
            cur = lines[j]
            stripped = cur.lstrip()
            indent = len(cur) - len(stripped)

            if stripped.startswith("- name:") and indent <= step_indent:
                break

            block.append(cur)
            j += 1

        block_text = "\n".join(block)

        has_status = f'STATUS="{expected_status_path}"' in block_text
        has_schema = 'SCHEMA="$GITHUB_WORKSPACE/schemas/status/status_v1.schema.json"' in block_text
        has_validate = 'python tools/validate_status_schema.py \\' in block_text
        has_schema_arg = '--schema "$SCHEMA"' in block_text
        has_status_arg = '--status "$STATUS"' in block_text

        return bool(
            has_status
            and has_schema
            and has_validate
            and has_schema_arg
            and has_status_arg
        )

    return False


def test_pulse_ci_keeps_status_v1_schema_validation_steps() -> None:
    yml = WORKFLOW.read_text(encoding="utf-8", errors="replace")

    has_baseline = _pulse_ci_has_status_v1_schema_validation(
        yml,
        "ci: schema validate status_baseline.json (status_v1)",
        "${{ env.PACK_DIR }}/artifacts/status_baseline.json",
    )
    has_final = _pulse_ci_has_status_v1_schema_validation(
        yml,
        "ci: schema validate status.json (status_v1)",
        "${{ env.PACK_DIR }}/artifacts/status.json",
    )

    if not (has_baseline and has_final):
        raise AssertionError(
            "pulse_ci.yml must keep both status_v1 schema-validation steps:\n"
            "- ci: schema validate status_baseline.json (status_v1)\n"
            "- ci: schema validate status.json (status_v1)\n\n"
            "Fix: keep both named steps and make each of them call "
            "tools/validate_status_schema.py with the status_v1 schema and the "
            "expected status path."
        )

def _pulse_ci_has_strict_external_summary_precheck(yml_text: str) -> bool:
    lines = yml_text.splitlines()
    step_name_rx = re.compile(
        r'^\s*-\s*name:\s*["\']?Strict external evidence: require external summaries present \(pre-augment, fail-closed\)["\']?\s*$'
    )

    i = 0
    while i < len(lines):
        if not step_name_rx.match(lines[i]):
            i += 1
            continue

        step_indent = len(lines[i]) - len(lines[i].lstrip())
        j = i + 1
        block: List[str] = []

        while j < len(lines):
            cur = lines[j]
            stripped = cur.lstrip()
            indent = len(cur) - len(stripped)

            if stripped.startswith("- name:") and indent <= step_indent:
                break

            block.append(cur)
            j += 1

        block_text = "\n".join(block)

        has_if = re.search(
            r"\(\s*github\.event_name\s*==\s*'workflow_dispatch'\s*&&\s*"
            r"github\.event\.inputs\.strict_external_evidence\s*==\s*'true'\s*\)\s*\|\|\s*"
            r"startsWith\(github\.ref,\s*'refs/tags/v'\)\s*\|\|\s*"
            r"startsWith\(github\.ref,\s*'refs/tags/V'\)",
            block_text,
        )

        has_ext_dir = 'EXT_DIR="${{ env.PACK_DIR }}/artifacts/external"' in block_text
        has_checker = 'python scripts/check_external_summaries_present.py --external_dir "$EXT_DIR" --require_metric_key' in block_text

        return bool(has_if and has_ext_dir and has_checker)

    return False


def test_pulse_ci_keeps_strict_external_summary_precheck() -> None:
    yml = WORKFLOW.read_text(encoding="utf-8", errors="replace")

    if not _pulse_ci_has_strict_external_summary_precheck(yml):
        raise AssertionError(
            "pulse_ci.yml must keep the strict external evidence pre-augment "
            "summary-presence check.\n"
            "Fix: keep the named step, the release-grade/strict if-condition, "
            'EXT_DIR="${{ env.PACK_DIR }}/artifacts/external", and the '
            "check_external_summaries_present.py invocation with "
            "--require_metric_key."
        )

def test_runbook_keeps_v0_core_runtime_surface() -> None:
    if not CORE_WORKFLOW.is_file():
        raise AssertionError(f"Missing core workflow file: {CORE_WORKFLOW}")
    if not RUNBOOK.is_file():
        raise AssertionError(f"Missing runbook file: {RUNBOOK}")

    yml = CORE_WORKFLOW.read_text(encoding="utf-8", errors="replace")
    runbook = RUNBOOK.read_text(encoding="utf-8", errors="replace")

    if "## 1.5 Reference execution lane (v0)" not in runbook:
        raise AssertionError(
            "RUNBOOK.md must keep the v0 reference execution lane section."
        )

    if "### Core runtime surface (v0)" not in runbook:
        raise AssertionError(
            "RUNBOOK.md must keep the v0 core runtime surface section."
        )

    required_runbook_snippets = [
        "workflow: `.github/workflows/pulse_core_ci.yml`",
        "Python: `3.11`",
        "install path: `python -m pip install -r requirements.txt pytest`",
        "minimal core dependency contract: `requirements.txt`",
        "`requirements.txt` is the primary core runtime surface",
        "`environment.yml` is a broader convenience environment",
    ]
    missing = [s for s in required_runbook_snippets if s not in runbook]
    if missing:
        raise AssertionError(
            "RUNBOOK.md is missing required core runtime surface statements:\n"
            + "\n".join(f" - {m}" for m in missing)
        )

    if not re.search(r'^\s*python-version:\s*["\']?3\.11["\']?\s*$', yml, flags=re.M):
        raise AssertionError(
            "pulse_core_ci.yml must set Python 3.11 in the Set up Python step."
        )

    if 'python -m pip install -r requirements.txt pytest' not in yml:
        raise AssertionError(
            "pulse_core_ci.yml must install requirements.txt and pytest in the "
            "reference core runtime lane."
        )

def test_requirements_txt_keeps_minimal_core_runtime_contract() -> None:
    req = ROOT / "requirements.txt"
    if not req.is_file():
        raise AssertionError(f"Missing requirements file: {req}")

    entries: List[str] = []
    for raw in req.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            entries.append(line)

    if not entries:
        raise AssertionError("requirements.txt must not be empty.")

    def _canonical_req_name(entry: str) -> str:
        base = entry.split(";", 1)[0]
        base = re.sub(r"\s+", "", base)
        m = re.match(r"^([A-Za-z0-9_.-]+)", base)
        if not m:
            return ""
        return re.sub(r"[-_.]+", "-", m.group(1)).lower()

    present_names = {
        name for name in (_canonical_req_name(e) for e in entries) if name
    }

    required_pkgs = ("pyyaml", "jsonschema")
    missing = [pkg for pkg in required_pkgs if pkg not in present_names]
    if missing:
        raise AssertionError(
            "requirements.txt must keep the minimal core runtime contract:\n"
            + "\n".join(f" - {pkg}" for pkg in missing)
        )

def main() -> int:
    try:
        test_tools_tests_list_covers_smoke_scripts()
        test_pytest_tests_list_keeps_core_baseline()
        test_pulse_core_ci_keeps_core_baseline_step()
        test_pulse_core_ci_python_version_aligns_with_environment()
        test_pulse_ci_fails_closed_on_empty_derived_gate_set()
        test_pulse_ci_keeps_release_grade_prod_guard()
        test_pulse_ci_keeps_status_v1_schema_validation_steps()
        test_pulse_ci_keeps_strict_external_summary_precheck()
        test_runbook_keeps_v0_core_runtime_surface()
        test_requirements_txt_keeps_minimal_core_runtime_contract()
    except AssertionError as e:
        print(f"ERROR: {e}")
        return 1
    print(
        "OK: tools-tests suite is coherent, pulse_core_ci baseline wiring is kept, "
        "pulse_ci retains the fail-closed guard for empty derived gate sets, "
        "release-grade runs still require run_mode=prod, both status_v1 "
        "schema-validation steps are anchored, strict external summary presence "
        "precheck is kept, the v0 core runtime surface remains aligned, and "
        "requirements.txt retains the minimal core runtime contract"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

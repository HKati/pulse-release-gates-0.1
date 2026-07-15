#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]

BUILDER = ROOT / "tools" / "build_pulsemech_compute_binding_report_v0.py"
VALIDATOR = ROOT / "tools" / "check_pulsemech_compute_binding_report_v0.py"
SCHEMA = ROOT / "schemas" / "pulsemech_compute_binding_report_v0.schema.json"

ARCHIVE = ROOT / "PULSE_CI_6066_release_grade_artifact_preservation_v0.zip"
PRESERVATION_DIR = ROOT / "preservation" / "pulse_ci_6066"
MANIFEST = PRESERVATION_DIR / "PRESERVATION_MANIFEST_v0.json"
README = PRESERVATION_DIR / "README.md"
SHA256SUMS = PRESERVATION_DIR / "SHA256SUMS"
GATE_POLICY = ROOT / "pulse_gate_policy_v0.yml"
GATE_REGISTRY = ROOT / "pulse_gate_registry_v0.yml"
PULSE_WORKFLOW = ROOT / ".github" / "workflows" / "pulse_ci.yml"
EXPECTED_ARCHIVE_SHA256 = (
    "7949bfd00468e6f9347fddaae732bdcebff5527e87ecb379a6c84a47176db966"
)
EXPECTED_ARCHIVE_SIZE = 44660
EXPECTED_SOURCE_COMMIT = "46b639706e23f80fe296a8893be18e2b5ab21f7e"
EXPECTED_SUBJECT_RUN_KEY = (
    "GITHUB_RUN_ID=29249887581|GITHUB_RUN_ATTEMPT=1|"
    "GITHUB_WORKFLOW=PULSE CI"
)
EXPECTED_ANALYSIS_RUN_KEY = (
    "OFFLINE_ANALYSIS=pulsemech-compute-binding-fixed-source-6066-v0"
)

EXPECTED_COMPUTE_NODE_IDS = {
    "compute:artifact-binding-builder",
    "compute:candidate-status-builder",
    "compute:check-gates",
    "compute:evidence-manifest-builder",
    "compute:external-attestation-verifier",
    "compute:external-envelope-builder",
    "compute:github-attestation",
    "compute:llamaguard-runtime",
    "compute:llamaguard-summary-adapter",
    "compute:offline-observer",
    "compute:package-assembler",
    "compute:package-completeness-checker",
    "compute:package-verifier",
    "compute:recorded-candidate-builder",
    "compute:recorded-evidence-verifier",
    "compute:release-authority-manifest-builder",
    "compute:release-decision-materializer",
    "compute:release-required-materializer",
    "compute:required-gate-evaluator",
}

EXPECTED_COMPLETE_TRANSITION_NODES = {
    "compute:candidate-status-builder",
    "compute:check-gates",
}

EXPECTED_COMPLETE_EVIDENCE_NODES = {
    "compute:external-attestation-verifier",
    "compute:external-envelope-builder",
    "compute:llamaguard-summary-adapter",
    "compute:recorded-candidate-builder",
}

EXPECTED_UNKNOWN_SUBJECT_NODES = {
    "compute:artifact-binding-builder",
    "compute:evidence-manifest-builder",
    "compute:github-attestation",
    "compute:llamaguard-runtime",
    "compute:package-assembler",
    "compute:package-completeness-checker",
    "compute:package-verifier",
    "compute:recorded-evidence-verifier",
    "compute:release-authority-manifest-builder",
    "compute:release-decision-materializer",
    "compute:release-required-materializer",
    "compute:required-gate-evaluator",
}

EXPECTED_FINDING_COUNTS = Counter(
    {
        "unknown_compute_binding": 12,
        "compute_source_digest_missing": 10,
        "compute_source_identity_missing": 4,
        "declared_binding_not_observed": 1,
        "required_gate_source_unresolved": 1,
        "resource_measurement_missing": 1,
    }
)


@dataclass(frozen=True)
class SubjectPaths:
    archive: Path
    manifest: Path
    readme: Path
    sha256sums: Path
    root: Path
    preservation_dir: Path


@dataclass(frozen=True)
class CliBuild:
    result: subprocess.CompletedProcess[str]
    report: dict[str, Any]
    rendered: str
    output: Path
    input_snapshot_before: dict[str, tuple[int, str]]
    input_snapshot_after: dict[str, tuple[int, str]]
    preservation_members_before: tuple[str, ...]
    preservation_members_after: tuple[str, ...]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def strict_json_text(text: str, *, label: str) -> dict[str, Any]:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise AssertionError(f"{label}: duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_non_finite(value: str) -> None:
        raise AssertionError(f"{label}: non-finite JSON value: {value}")

    loaded = json.loads(
        text,
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_non_finite,
    )
    assert isinstance(loaded, dict), f"{label}: expected object"
    return loaded


def snapshot(paths: tuple[Path, ...]) -> dict[str, tuple[int, str]]:
    return {
        str(path): (path.stat().st_size, sha256_file(path))
        for path in paths
    }


def preservation_members(directory: Path) -> tuple[str, ...]:
    return tuple(
        sorted(
            str(path.relative_to(directory))
            for path in directory.rglob("*")
            if path.is_file() or path.is_symlink()
        )
    )


def import_builder_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "pulsemech_compute_binding_builder_v0_under_test",
        BUILDER,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BUILDER_MODULE = import_builder_module()


def default_subject() -> SubjectPaths:
    return SubjectPaths(
        archive=ARCHIVE,
        manifest=MANIFEST,
        readme=README,
        sha256sums=SHA256SUMS,
        root=ROOT,
        preservation_dir=PRESERVATION_DIR,
    )


def copy_subject(tmp_path: Path) -> SubjectPaths:
    subject_root = tmp_path / "subject"
    preservation_dir = subject_root / "preservation" / "pulse_ci_6066"
    preservation_dir.mkdir(parents=True)

    archive = subject_root / ARCHIVE.name
    manifest = preservation_dir / MANIFEST.name
    readme = preservation_dir / README.name
    sha256sums = preservation_dir / SHA256SUMS.name

    shutil.copy2(ARCHIVE, archive)
    shutil.copy2(MANIFEST, manifest)
    shutil.copy2(README, readme)
    shutil.copy2(SHA256SUMS, sha256sums)

    return SubjectPaths(
        archive=archive,
        manifest=manifest,
        readme=readme,
        sha256sums=sha256sums,
        root=subject_root,
        preservation_dir=preservation_dir,
    )


def load_bundle(subject: SubjectPaths) -> Any:
    return BUILDER_MODULE.load_observed_bundle(
        archive_path=subject.archive,
        manifest_path=subject.manifest,
        readme_path=subject.readme,
        sha256sums_path=subject.sha256sums,
        expected_archive_sha256=EXPECTED_ARCHIVE_SHA256,
        expected_archive_size=EXPECTED_ARCHIVE_SIZE,
    )


def run_builder(
    *,
    subject: SubjectPaths | None = None,
    schema: Path = SCHEMA,
    validator: Path = VALIDATOR,
    analysis_run_key: str = EXPECTED_ANALYSIS_RUN_KEY,
    output: Path | None = None,
    extra_args: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    subject = subject or default_subject()

    command = [
        sys.executable,
        str(BUILDER),
        "--archive",
        str(subject.archive),
        "--manifest",
        str(subject.manifest),
        "--readme",
        str(subject.readme),
        "--sha256sums",
        str(subject.sha256sums),
        "--schema",
        str(schema),
        "--validator",
        str(validator),
        "--analysis-run-key",
        analysis_run_key,
    ]

    if output is not None:
        command.extend(["--output", str(output)])
    if extra_args:
        command.extend(extra_args)

    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def assert_builder_failure(
    result: subprocess.CompletedProcess[str],
    expected_fragment: str,
    *,
    expected_returncode: int = 1,
) -> dict[str, Any]:
    assert result.returncode == expected_returncode, result.stdout + result.stderr
    assert result.stdout == ""
    assert "Traceback" not in result.stderr

    diagnostic = strict_json_text(result.stderr, label="builder diagnostic")
    assert diagnostic["tool"] == "build_pulsemech_compute_binding_report_v0"
    assert diagnostic["ok"] is False
    assert isinstance(diagnostic["errors"], list)
    assert any(
        expected_fragment in str(error)
        for error in diagnostic["errors"]
    ), diagnostic
    return diagnostic


def node_index(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        node["node_id"]: node
        for node in report["compute_nodes"]
    }


@pytest.fixture(scope="module")
def observed_bundle() -> Any:
    return load_bundle(default_subject())


@pytest.fixture(scope="module")
def cli_build(tmp_path_factory: pytest.TempPathFactory) -> CliBuild:
    output = (
        tmp_path_factory.mktemp("compute-binding-builder-v0")
        / "pulsemech_compute_binding_report_v0.json"
    )

    protected_inputs = (
        ARCHIVE,
        MANIFEST,
        README,
        SHA256SUMS,
        SCHEMA,
        VALIDATOR,
        GATE_POLICY,
        GATE_REGISTRY,
        PULSE_WORKFLOW,
        BUILDER,
    )
    before = snapshot(protected_inputs)
    members_before = preservation_members(PRESERVATION_DIR)

    result = run_builder(output=output)

    after = snapshot(protected_inputs)
    members_after = preservation_members(PRESERVATION_DIR)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    assert result.stdout.endswith("\n")
    assert output.is_file()
    assert not output.is_symlink()
    assert output.read_text(encoding="utf-8") == result.stdout

    report = strict_json_text(result.stdout, label="generated report")
    return CliBuild(
        result=result,
        report=report,
        rendered=result.stdout,
        output=output,
        input_snapshot_before=before,
        input_snapshot_after=after,
        preservation_members_before=members_before,
        preservation_members_after=members_after,
    )


# ---------------------------------------------------------------------------
# Fixed-source positive path
# ---------------------------------------------------------------------------


def test_required_fixed_source_and_contract_files_exist() -> None:
    for path in (
        BUILDER,
        VALIDATOR,
        SCHEMA,
        ARCHIVE,
        MANIFEST,
        README,
        SHA256SUMS,
        GATE_POLICY,
        GATE_REGISTRY,
        PULSE_WORKFLOW,
    ):
        assert path.is_file(), path
        assert not path.is_symlink(), path


def test_fixed_archive_and_visible_carriers_are_exactly_locked() -> None:
    assert ARCHIVE.stat().st_size == EXPECTED_ARCHIVE_SIZE
    assert sha256_file(ARCHIVE) == EXPECTED_ARCHIVE_SHA256
    assert sha256_file(MANIFEST) == (
        "afa8190f6f792c50596d4f9f8657001a2e15a782968759d6d20120257fa4178c"
    )
    assert sha256_file(README) == (
        "33711b283df5e3128b72ac9d09a4d22637e4353890c46ee294518b3ae1f19ecd"
    )


def test_cli_builder_emits_contract_valid_observed_report(
    cli_build: CliBuild,
) -> None:
    report = cli_build.report

    assert report["schema_version"] == "pulsemech_compute_binding_report_v0"
    assert report["report_type"] == "pulsemech_compute_binding_report"
    assert report["record_status"] == "observed"
    assert report["ok"] is True
    assert report["errors"] == []

    assert report["tool"] == {
        "id": "build_pulsemech_compute_binding_report_v0",
        "version": "0.1.0",
        "source_sha256": sha256_file(BUILDER),
    }
    assert report["analysis_boundary"] == {
        "analysis_level": "artifact_observed",
        "subject_run_key": EXPECTED_SUBJECT_RUN_KEY,
        "analysis_run_key": EXPECTED_ANALYSIS_RUN_KEY,
        "observer_in_subject_totals": False,
    }

    subject = report["subject"]
    assert subject["repository"] == "HKati/pulse-release-gates-0.1"
    assert subject["workflow"] == "PULSE CI"
    assert subject["workflow_run_id"] == 29249887581
    assert subject["workflow_run_number"] == 6066
    assert subject["workflow_run_attempt"] == 1
    assert subject["source_commit"] == EXPECTED_SOURCE_COMMIT
    assert subject["release_candidate_id"] == "main"
    assert subject["run_mode"] == "prod"
    assert subject["active_policy_sets"] == ["release_required", "required"]
    assert subject["policy_id"] == "pulse-gate-policy-v0"
    assert subject["decision"] == "ALLOW"

    for field in (
        "policy_sha256",
        "materialized_gate_set_sha256",
        "final_status_sha256",
        "release_decision_sha256",
    ):
        assert isinstance(subject[field], str)
        assert len(subject[field]) == 64
        int(subject[field], 16)


def test_cli_output_matches_stdout_and_subject_inputs_remain_unchanged(
    cli_build: CliBuild,
) -> None:
    assert cli_build.output.read_text(encoding="utf-8") == cli_build.rendered
    assert cli_build.output.read_bytes().endswith(b"\n")
    assert cli_build.input_snapshot_before == cli_build.input_snapshot_after
    assert (
        cli_build.preservation_members_before
        == cli_build.preservation_members_after
    )


def test_graph_shape_binding_classes_and_observer_boundary_are_explicit(
    cli_build: CliBuild,
) -> None:
    report = cli_build.report
    nodes = node_index(report)

    assert set(nodes) == EXPECTED_COMPUTE_NODE_IDS
    assert len(report["state_nodes"]) == 33
    assert len(report["edges"]) == 109
    assert len(report["inputs"]) == 19
    assert len(report["findings"]) == 29

    subject_nodes = {
        node_id: node
        for node_id, node in nodes.items()
        if node["execution_scope"] == "subject"
    }
    observer_nodes = {
        node_id: node
        for node_id, node in nodes.items()
        if node["execution_scope"] == "analysis_observer"
    }

    assert len(subject_nodes) == 18
    assert set(observer_nodes) == {"compute:offline-observer"}

    transition_bound = {
        node_id
        for node_id, node in subject_nodes.items()
        if node["binding_class"] == "transition_bound"
    }
    evidence_bound = {
        node_id
        for node_id, node in subject_nodes.items()
        if node["binding_class"] == "evidence_bound"
    }
    unknown = {
        node_id
        for node_id, node in subject_nodes.items()
        if node["binding_class"] == "unknown"
    }

    assert transition_bound == EXPECTED_COMPLETE_TRANSITION_NODES
    assert evidence_bound == EXPECTED_COMPLETE_EVIDENCE_NODES
    assert unknown == EXPECTED_UNKNOWN_SUBJECT_NODES
    assert not {
        node_id
        for node_id, node in subject_nodes.items()
        if node["binding_class"] == "unbound"
    }

    observer = observer_nodes["compute:offline-observer"]
    assert observer["declared_role"] == "observer"
    assert observer["binding_status"] == "complete"
    assert observer["binding_class"] == "observer"
    assert observer["mutation_authority"] == "none"
    assert observer["observed_mutation_classes"] == []
    assert observer["unbound_authoritative_mutation"] is False
    assert observer["resource_usage"] == {}
    assert observer["run_binding"] == {
        "execution_run_key": EXPECTED_ANALYSIS_RUN_KEY,
        "subject_run_key": EXPECTED_SUBJECT_RUN_KEY,
        "binding_mode": "offline_observer",
        "binding_complete": True,
    }

    for node in subject_nodes.values():
        assert node["run_binding"] == {
            "execution_run_key": EXPECTED_SUBJECT_RUN_KEY,
            "subject_run_key": EXPECTED_SUBJECT_RUN_KEY,
            "binding_mode": "current_subject_run",
            "binding_complete": True,
        }
        assert node["resource_usage"] == {}
        assert node["unbound_authoritative_mutation"] is False

    assert report["summary"] == {
        "subject_compute_nodes": 18,
        "observer_nodes": 1,
        "transition_bound_nodes": 2,
        "evidence_bound_nodes": 4,
        "preservation_bound_nodes": 0,
        "advisory_bound_nodes": 0,
        "unbound_nodes": 0,
        "unknown_nodes": 12,
        "unbound_authoritative_mutation_count": 0,
        "decision_closure_complete": False,
        "authority_binding_complete": False,
        "resource_measurement_status": "none",
    }
    assert report["resource_summary"] == {"axes": {}}


def test_findings_preserve_missing_evidence_without_inventing_completion(
    cli_build: CliBuild,
) -> None:
    findings = cli_build.report["findings"]
    assert Counter(item["finding_id"] for item in findings) == EXPECTED_FINDING_COUNTS
    assert all(item["severity"] == "advisory" for item in findings)

    model_finding = next(
        item
        for item in findings
        if item["finding_id"] == "declared_binding_not_observed"
    )
    assert model_finding["node_id"] == "compute:llamaguard-runtime"
    assert "content digest" in model_finding["message"].lower()

    resource_finding = next(
        item
        for item in findings
        if item["finding_id"] == "resource_measurement_missing"
    )
    assert resource_finding["node_id"] is None
    assert resource_finding["evidence_refs"] == ["resource_summary.axes"]


def test_edges_are_exactly_digest_bound_and_deterministically_ordered(
    cli_build: CliBuild,
) -> None:
    report = cli_build.report
    states = {state["state_id"]: state for state in report["state_nodes"]}
    edge_ids = [edge["edge_id"] for edge in report["edges"]]

    assert edge_ids == [f"edge:{index:03d}" for index in range(1, 110)]

    for edge in report["edges"]:
        assert edge["declared"] is True
        assert edge["observed"] is True
        assert edge["binding_status"] == "complete"
        state_id = (
            edge["from_id"]
            if edge["from_id"].startswith("state:")
            else edge["to_id"]
        )
        assert edge["evidence_digests"] == [states[state_id]["sha256"]]


# ---------------------------------------------------------------------------
# Determinism without repeating the expensive contract-validation subprocess
# ---------------------------------------------------------------------------


def test_build_report_is_byte_deterministic_for_identical_canonical_inputs(
    observed_bundle: Any,
) -> None:
    source_sha = sha256_file(BUILDER)

    first = BUILDER_MODULE.render_json(
        BUILDER_MODULE.build_report(
            observed_bundle,
            analysis_run_key=EXPECTED_ANALYSIS_RUN_KEY,
            builder_source_sha256=source_sha,
        )
    )
    second = BUILDER_MODULE.render_json(
        BUILDER_MODULE.build_report(
            observed_bundle,
            analysis_run_key=EXPECTED_ANALYSIS_RUN_KEY,
            builder_source_sha256=source_sha,
        )
    )

    assert first == second
    assert first.endswith("\n")


def test_custom_analysis_identity_changes_only_observer_identity(
    observed_bundle: Any,
) -> None:
    source_sha = sha256_file(BUILDER)
    custom_key = "OFFLINE_ANALYSIS=independent-replay-6066-v0"

    default = BUILDER_MODULE.build_report(
        observed_bundle,
        analysis_run_key=EXPECTED_ANALYSIS_RUN_KEY,
        builder_source_sha256=source_sha,
    )
    custom = BUILDER_MODULE.build_report(
        observed_bundle,
        analysis_run_key=custom_key,
        builder_source_sha256=source_sha,
    )

    assert custom["subject"] == default["subject"]
    assert custom["inputs"] == default["inputs"]
    assert custom["state_nodes"] == default["state_nodes"]
    assert custom["edges"] == default["edges"]
    assert custom["findings"] == default["findings"]
    assert custom["summary"] == default["summary"]
    assert custom["resource_summary"] == default["resource_summary"]
    assert custom["analysis_boundary"]["analysis_run_key"] == custom_key

    default_nodes = node_index(default)
    custom_nodes = node_index(custom)
    for node_id in EXPECTED_COMPUTE_NODE_IDS - {"compute:offline-observer"}:
        assert custom_nodes[node_id] == default_nodes[node_id]

    assert custom_nodes["compute:offline-observer"]["run_binding"][
        "execution_run_key"
    ] == custom_key
    assert default_nodes["compute:offline-observer"]["run_binding"][
        "execution_run_key"
    ] == EXPECTED_ANALYSIS_RUN_KEY


# ---------------------------------------------------------------------------
# Fixed-source and visible-carrier failure paths
# ---------------------------------------------------------------------------


def test_same_size_archive_corruption_fails_the_fixed_digest(
    tmp_path: Path,
) -> None:
    subject = copy_subject(tmp_path)
    payload = bytearray(subject.archive.read_bytes())
    payload[len(payload) // 2] ^= 0x01
    subject.archive.write_bytes(payload)

    assert subject.archive.stat().st_size == EXPECTED_ARCHIVE_SIZE
    with pytest.raises(
        BUILDER_MODULE.BuilderError,
        match="preservation_archive_sha256_mismatch",
    ):
        load_bundle(subject)


def test_truncated_archive_fails_the_fixed_size(tmp_path: Path) -> None:
    subject = copy_subject(tmp_path)
    subject.archive.write_bytes(subject.archive.read_bytes()[:-1])

    with pytest.raises(
        BUILDER_MODULE.BuilderError,
        match="preservation_archive_size_mismatch",
    ):
        load_bundle(subject)


@pytest.mark.parametrize(
    ("carrier_name", "expected_fragment"),
    [
        ("manifest", "visible_manifest_bytes_mismatch"),
        ("readme", "visible_readme_bytes_mismatch"),
        ("sha256sums", "visible_sha256sums_bytes_mismatch"),
    ],
)
def test_visible_carrier_drift_is_rejected(
    tmp_path: Path,
    carrier_name: str,
    expected_fragment: str,
) -> None:
    subject = copy_subject(tmp_path)
    carrier = getattr(subject, carrier_name)
    carrier.write_bytes(carrier.read_bytes() + b"\n")

    with pytest.raises(BUILDER_MODULE.BuilderError, match=expected_fragment):
        load_bundle(subject)


def test_exact_subject_copy_is_read_only_and_not_extracted(
    tmp_path: Path,
) -> None:
    subject = copy_subject(tmp_path)
    files_before = preservation_members(subject.root)
    bytes_before = snapshot(
        (subject.archive, subject.manifest, subject.readme, subject.sha256sums)
    )

    bundle = load_bundle(subject)
    report = BUILDER_MODULE.build_report(
        bundle,
        analysis_run_key=EXPECTED_ANALYSIS_RUN_KEY,
        builder_source_sha256=sha256_file(BUILDER),
    )

    assert report["record_status"] == "observed"
    assert report["subject"]["workflow_run_id"] == 29249887581
    assert preservation_members(subject.root) == files_before
    assert snapshot(
        (subject.archive, subject.manifest, subject.readme, subject.sha256sums)
    ) == bytes_before
    assert not (subject.root / "original-github-artifacts").exists()
    assert not (subject.root / "complete-release-grade-reference-package").exists()


def test_manifest_semantic_identity_drift_fails_closed() -> None:
    manifest = strict_json_text(
        MANIFEST.read_text(encoding="utf-8"),
        label="manifest fixture",
    )
    manifest["source_commit"] = "0" * 40

    with pytest.raises(
        BUILDER_MODULE.BuilderError,
        match="manifest_source_commit_mismatch",
    ):
        BUILDER_MODULE.validate_preservation_manifest(manifest)


# ---------------------------------------------------------------------------
# Read-only output and validator boundaries
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "output_name",
    ["status.json", "release_decision_v0.json"],
)
def test_authority_surface_output_names_are_rejected(
    tmp_path: Path,
    output_name: str,
) -> None:
    output = tmp_path / output_name

    with pytest.raises(
        BUILDER_MODULE.BuilderError,
        match="refusing_authority_surface_output",
    ):
        BUILDER_MODULE.reject_unsafe_output(
            output,
            archive=ARCHIVE,
            manifest=MANIFEST,
            readme=README,
            sha256sums=SHA256SUMS,
            schema=SCHEMA,
            validator=VALIDATOR,
        )
    assert not output.exists()


def test_output_inside_preservation_directory_is_rejected() -> None:
    output = PRESERVATION_DIR / "pulsemech_compute_binding_report_v0.json"

    with pytest.raises(
        BUILDER_MODULE.BuilderError,
        match="refusing_output_inside_preservation_directory",
    ):
        BUILDER_MODULE.reject_unsafe_output(
            output,
            archive=ARCHIVE,
            manifest=MANIFEST,
            readme=README,
            sha256sums=SHA256SUMS,
            schema=SCHEMA,
            validator=VALIDATOR,
        )
    assert not output.exists()


@pytest.mark.parametrize(
    "protected_path",
    [
        ARCHIVE,
        MANIFEST,
        README,
        SHA256SUMS,
        SCHEMA,
        VALIDATOR,
        GATE_POLICY,
        GATE_REGISTRY,
        PULSE_WORKFLOW,
    ],
    ids=lambda path: path.name,
)
def test_protected_input_overwrite_is_rejected(protected_path: Path) -> None:
    before = snapshot((protected_path,))

    with pytest.raises(
        BUILDER_MODULE.BuilderError,
        match="refusing_to_overwrite_input",
    ):
        BUILDER_MODULE.reject_unsafe_output(
            protected_path,
            archive=ARCHIVE,
            manifest=MANIFEST,
            readme=README,
            sha256sums=SHA256SUMS,
            schema=SCHEMA,
            validator=VALIDATOR,
        )
    assert snapshot((protected_path,)) == before


def test_dangling_output_symlink_is_rejected_without_creating_target(
    tmp_path: Path,
) -> None:
    target = tmp_path / "missing-target.json"
    link = tmp_path / "output.json"

    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink unsupported: {exc}")

    assert link.is_symlink()
    assert not link.exists()
    assert not target.exists()

    with pytest.raises(
        BUILDER_MODULE.BuilderError,
        match="refusing_symlink_output_path",
    ):
        BUILDER_MODULE.reject_unsafe_output(
            link,
            archive=ARCHIVE,
            manifest=MANIFEST,
            readme=README,
            sha256sums=SHA256SUMS,
            schema=SCHEMA,
            validator=VALIDATOR,
        )

    assert link.is_symlink()
    assert not link.exists()
    assert not target.exists()


def test_symlink_output_file_and_parent_are_rejected(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    target.write_text("{}\n", encoding="utf-8")
    link = tmp_path / "output.json"

    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink unsupported: {exc}")

    with pytest.raises(
        BUILDER_MODULE.BuilderError,
        match="refusing_symlink_output_path",
    ):
        BUILDER_MODULE.reject_unsafe_output(
            link,
            archive=ARCHIVE,
            manifest=MANIFEST,
            readme=README,
            sha256sums=SHA256SUMS,
            schema=SCHEMA,
            validator=VALIDATOR,
        )
    assert target.read_text(encoding="utf-8") == "{}\n"

    real_directory = tmp_path / "real"
    real_directory.mkdir()
    linked_directory = tmp_path / "linked"
    try:
        linked_directory.symlink_to(real_directory, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"directory symlink unsupported: {exc}")

    through_parent = linked_directory / "report.json"
    with pytest.raises(
        BUILDER_MODULE.BuilderError,
        match="refusing_symlink_output_path",
    ):
        BUILDER_MODULE.reject_unsafe_output(
            through_parent,
            archive=ARCHIVE,
            manifest=MANIFEST,
            readme=README,
            sha256sums=SHA256SUMS,
            schema=SCHEMA,
            validator=VALIDATOR,
        )
    assert not (real_directory / "report.json").exists()


def test_subject_run_key_cannot_be_used_as_analysis_run_key(
    tmp_path: Path,
) -> None:
    output = tmp_path / "pulsemech_compute_binding_report_v0.json"
    result = run_builder(
        analysis_run_key=EXPECTED_SUBJECT_RUN_KEY,
        output=output,
    )

    assert_builder_failure(
        result,
        "analysis_run_key_invalid_or_matches_subject",
    )
    assert not output.exists()


def test_rejecting_validator_prevents_output_creation(
    tmp_path: Path,
    cli_build: CliBuild,
) -> None:
    rejecting_validator = tmp_path / "rejecting_validator.py"
    rejecting_validator.write_text(
        "import json\n"
        "print(json.dumps({'ok': False, 'errors': ['synthetic_rejection']}))\n"
        "raise SystemExit(1)\n",
        encoding="utf-8",
    )

    with pytest.raises(
        BUILDER_MODULE.BuilderError,
        match="generated_report_rejected",
    ):
        BUILDER_MODULE.validate_generated_report(
            schema_path=SCHEMA,
            validator_path=rejecting_validator,
            rendered_report=cli_build.rendered,
        )


def test_strict_json_helpers_reject_duplicate_and_non_finite_values() -> None:
    with pytest.raises(BUILDER_MODULE.BuilderError, match="duplicate JSON key"):
        BUILDER_MODULE.load_json_bytes(
            b'{"value": 1, "value": 2}',
            label="duplicate_fixture",
        )

    with pytest.raises(BUILDER_MODULE.BuilderError, match="non-finite JSON value"):
        BUILDER_MODULE.load_json_bytes(
            b'{"value": NaN}',
            label="non_finite_fixture",
        )


# ---------------------------------------------------------------------------
# Direct tools-tests execution entrypoint
# ---------------------------------------------------------------------------


def check_build_pulsemech_compute_binding_report_v0() -> None:
    raise SystemExit(pytest.main([__file__, "-q"]))


if __name__ == "__main__":
    check_build_pulsemech_compute_binding_report_v0()

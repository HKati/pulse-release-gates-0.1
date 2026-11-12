"""Mutation tests of the negative observer, never synthetic observed acceptance.

Constructed API rows and gate records below exercise individual parser contracts.
They are not real GitHub observations and are never passed through an accepting
checker CLI. No semantic verifier or model is replaced in the production path.
"""
from __future__ import annotations

import copy
import importlib.util
import io
import json
from pathlib import Path
import stat
import subprocess
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))
import check_pulsemech_compute_admission_rejection_v0 as c

SOURCE = "68c6fb199885c99f6a5809866ebd0aaae43b4847"
START = "2026-11-12T10:00:00Z"
END = "2026-11-12T10:10:00Z"
RUN_ID = 1234567


@pytest.fixture(scope="module")
def workflow():
    return (ROOT / c.WORKFLOW).read_bytes()


@pytest.fixture(scope="module")
def graph(workflow):
    return c.interpret_graph(workflow)


@pytest.fixture
def run():
    return {"id": RUN_ID, "run_attempt": 1, "head_sha": SOURCE,
            "repository": {"full_name": c.REPOSITORY}, "head_repository": {"full_name": c.REPOSITORY},
            "actor": {"login": "HKati"}, "triggering_actor": {"login": "HKati"},
            "event": "workflow_dispatch", "head_branch": "main", "path": c.WORKFLOW,
            "name": "PULSE CI", "status": "completed", "conclusion": "failure",
            "created_at": START, "run_started_at": START, "updated_at": END,
            "workflow_id": 111, "check_suite_id": 222}


def unit_jobs(graph, run):
    rows = []
    for index, job in enumerate(graph):
        row = {"id": index + 100, "name": job["name"], "run_id": run["id"], "run_attempt": 1,
               "head_sha": SOURCE, "status": "completed", "conclusion": job["expected_conclusion"],
               "started_at": START, "completed_at": END, "steps": []}
        if job["expected_conclusion"] != "skipped":
            row["steps"] = [{"name": "Set up job", "number": 1, "status": "completed", "conclusion": "success"}]
            row["steps"] += [{"name": s["name"], "number": s["ordinal"] + 1, "status": "completed",
                              "conclusion": s["expected_result"]} for s in job["steps"]]
            row["steps"] += [{"name": "Post Checkout", "number": len(job["steps"]) + 3,
                              "status": "completed", "conclusion": "success"},
                             {"name": "Complete job", "number": len(job["steps"]) + 5,
                              "status": "completed", "conclusion": "success"}]
        rows.append(row)
    return rows


def test_independent_graph_respects_all_conditions(graph):
    assert len(graph) == 8
    assert sum(len(j["steps"]) for j in graph) == 147
    assert sum(len(j["steps"]) for j in graph if j["expected_conclusion"] != "skipped") == 129
    assert [j["expected_conclusion"] for j in graph] == ["failure", "skipped", "success", "failure",
                                                         "skipped", "skipped", "skipped", "success"]
    pulse = graph[0]["steps"]
    assert pulse[8]["expected_result"] == "skipped"
    assert pulse[16]["expected_result"] == "failure"
    assert pulse[17]["expected_result"] == "success"  # always upload diagnostic
    assert pulse[18]["expected_result"] == "skipped"  # no candidate status
    assert pulse[24]["expected_result"] == "success"  # always display head
    assert pulse[69]["expected_result"] == "skipped"  # no final release decision


@pytest.mark.parametrize("expression,context,successful,expected", [
    (None, {}, False, False),
    ("${{ always() }}", {}, False, True),
    ("x == 'y'", {"x": "y"}, False, False),
    ("!cancelled() && x == 'y'", {"x": "y"}, False, True),
    ("startsWith(github.ref, 'refs/tags/')", {"github.ref": "refs/heads/main"}, True, False),
    ("(x == 'a' || x == 'b') && !cancelled()", {"x": "b"}, False, True),
])
def test_condition_default_success_and_status_function(expression, context, successful, expected):
    assert c.condition(expression, context, successful) is expected


@pytest.mark.parametrize("expression", ["contains(x, 'a')", "unknown == 'x'", "always(1)", "true; bad", "true false"])
def test_condition_unknown_construct_fails_closed(expression):
    with pytest.raises(c.VerificationError):
        c.condition(expression, {}, True)


def test_changed_workflow_never_inherits_profile(workflow):
    with pytest.raises(c.VerificationError, match="workflow_not_reviewed"):
        c.interpret_graph(workflow + b"\n# changed\n")


def test_source_and_platform_ordinals_remain_distinct(graph, run):
    rows = unit_jobs(graph, run)
    observed = c.validate_jobs(rows, graph, run)
    assert observed[0]["source_steps"][16]["ordinal"] == 17
    assert observed[0]["source_steps"][16]["platform_number"] == 18
    assert observed[1]["source_steps"][0]["expected_result"] == "not_instantiated"
    assert observed[1]["platform_steps"] == []


@pytest.mark.parametrize("mutation", ["infrastructure_failure", "downstream_continues", "missing_source_step",
                                     "unknown_platform_step", "failed_cleanup", "skipped_job_executes",
                                     "wrong_source", "duplicate_job", "duplicate_number", "cancelled_job"])
def test_job_mutations_rejected(graph, run, mutation):
    rows = unit_jobs(graph, run)
    if mutation == "infrastructure_failure":
        rows[0]["steps"][4]["conclusion"] = "failure"
    elif mutation == "downstream_continues":
        rows[3]["steps"][5]["conclusion"] = "success"
    elif mutation == "missing_source_step":
        rows[0]["steps"].pop(3)
    elif mutation == "unknown_platform_step":
        rows[0]["steps"][0]["name"] = "Run injected command"
    elif mutation == "failed_cleanup":
        rows[0]["steps"][-2]["conclusion"] = "failure"
    elif mutation == "skipped_job_executes":
        rows[1]["steps"] = [{"name": "Setup", "number": 1, "status": "completed", "conclusion": "success"}]
    elif mutation == "wrong_source":
        rows[0]["head_sha"] = "f" * 40
    elif mutation == "duplicate_job":
        rows[1]["name"] = rows[0]["name"]
    elif mutation == "duplicate_number":
        rows[0]["steps"][2]["number"] = rows[0]["steps"][1]["number"]
    else:
        rows[0]["conclusion"] = "cancelled"
    with pytest.raises(c.VerificationError):
        c.validate_jobs(rows, graph, run)


def log_for(script, output, *, duplicate_first=False, environment=None):
    lines = script.splitlines()
    head = ["##[group]Run " + lines[0]]
    echo = lines if duplicate_first else lines[1:]
    all_lines = head + ["\x1b[36;1m" + l + "\x1b[0m" for l in echo] + ["shell: /usr/bin/bash -e {0}"]
    if environment is not None:
        all_lines += ["env:"] + ["  " + k + ": " + v for k, v in environment.items()]
    all_lines += ["##[endgroup]"]
    all_lines += output + ["##[group]Next step", "##[endgroup]"]
    return "\n".join("2026-11-12T10:01:00.000Z " + l for l in all_lines).encode()


@pytest.mark.parametrize("duplicate_first", [False, True])
def test_log_output_excludes_echo_group(duplicate_first):
    script = 'set -euo pipefail\necho "MARKER"\nexit 1\n'
    output = ["MARKER", "##[error]Process completed with exit code 1."]
    assert c.actual_shell_output(log_for(script, output, duplicate_first=duplicate_first), script) == output


def test_marker_present_only_in_echo_is_not_observation():
    script = 'set -euo pipefail\necho "MARKER"\n'
    output = c.actual_shell_output(log_for(script, ["some other output"]), script)
    assert "MARKER" not in output


def test_critical_echo_from_wrong_script_rejected():
    with pytest.raises(c.VerificationError, match="critical_shell_group"):
        c.actual_shell_output(log_for('echo MARKER\n', ["MARKER"]), 'echo DIFFERENT\n')


def test_duplicate_critical_echo_is_ambiguous():
    script = 'echo MARKER\n'
    raw = log_for(script, ["MARKER"])
    with pytest.raises(c.VerificationError, match="ambiguous"):
        c.actual_shell_output(raw + b"\n" + raw, script)


def test_missing_endgroup_fails_closed():
    with pytest.raises(c.VerificationError, match="unterminated"):
        c.actual_shell_output(b"##[group]Run echo x\necho x", "echo x\n")


def test_rejection_requires_actual_q2_and_guard_output(graph, run, workflow):
    jobs = unit_jobs(graph, run)
    source = c.source_yaml(workflow)["jobs"]
    contents, entries = {}, {}
    for row in jobs:
        if row["conclusion"] == "skipped":
            continue
        name = f"logs/{row['id']}.txt"
        contents[name] = b"ordinary job log"
        entries[name] = {"kind": "log", "endpoint": f"repos/{c.REPOSITORY}/actions/jobs/{row['id']}/logs"}
    pulse_script = source["pulse"]["steps"][16]["run"]
    guard_script = source["release_grade_recorded_path"]["steps"][3]["run"]
    pack_dir = "/home/runner/work/pulse-release-gates-0.1/pulse-release-gates-0.1/PULSE_safe_pack_v0"
    mode_script = source["pulse"]["steps"][7]["run"].replace("${{ env.PACK_DIR }}", pack_dir)
    mode = log_for(mode_script, ["Computed flags: IS_RELEASE=1 MODE=prod POLICY_SET=required LLAMAGUARD_EVIDENCE_MODE=hosted_full_runtime"],
                   environment={"PACK_DIR": pack_dir}) + b"\n"
    pulse_output = ["Q2 independent negative verification exit: 0", "passed gates: 6", "failed gates: 13",
                    "##[error]Process completed with exit code 1."]
    guard_output = ["##[error]BLOCK: pre-attestation candidate was not accepted; hosted evidence remains preserved.",
                    "##[error]Process completed with exit code 1."]
    contents["logs/100.txt"] = mode + log_for(pulse_script, pulse_output,
                                              environment={"PULSE_Q2_INTAKE_REQUEST_SHA256": "a" * 64})
    contents["logs/103.txt"] = log_for(guard_script, guard_output)
    result = c.rejection_logs(contents, entries, jobs, workflow, "a" * 64)
    assert result["pulse"]["echo_group_excluded"] is True
    # The source already contains the guard marker. With no actual guard output it must fail.
    contents["logs/103.txt"] = log_for(guard_script, ["##[error]Process completed with exit code 1."])
    with pytest.raises(c.VerificationError, match="candidate_guard_output_missing"):
        c.rejection_logs(contents, entries, jobs, workflow, "a" * 64)
    contents["logs/103.txt"] = log_for(guard_script, guard_output)
    contents["logs/100.txt"] = mode + log_for(pulse_script, [line.replace("exit: 0", "exit: 2") for line in pulse_output],
                                              environment={"PULSE_Q2_INTAKE_REQUEST_SHA256": "a" * 64})
    with pytest.raises(c.VerificationError, match="q2_rejection_output"):
        c.rejection_logs(contents, entries, jobs, workflow, "a" * 64)


def page_unit(rows, total=None, after=False):
    base = f"repos/{c.REPOSITORY}/actions/runs/{RUN_ID}/attempts/1/jobs"
    name = "api/jobs-after-001.json" if after else "api/jobs-001.json"
    return {name: c.canonical({"total_count": len(rows) if total is None else total, "jobs": rows})}, {
        name: {"kind": "jobs", "endpoint": base + "?per_page=100&page=1"}}, base


@pytest.mark.parametrize("after", [False, True])
def test_each_pagination_snapshot_checked_independently(after):
    contents, entries, base = page_unit([{"id": 1}, {"id": 2}], after=after)
    assert len(c.pages(contents, entries, "jobs", base, after)) == 2


@pytest.mark.parametrize("mutation", ["missing_row", "duplicate_id", "wrong_endpoint", "missing_page"])
def test_incomplete_or_rebound_pagination_rejected(mutation):
    contents, entries, base = page_unit([{"id": 1}, {"id": 2}])
    if mutation == "missing_row":
        contents, entries, base = page_unit([{"id": 1}], total=2)
    elif mutation == "duplicate_id":
        contents, entries, base = page_unit([{"id": 1}, {"id": 1}])
    elif mutation == "wrong_endpoint":
        entries["api/jobs-001.json"]["endpoint"] = base + "?per_page=100&page=2"
    else:
        contents["api/jobs-002.json"] = contents.pop("api/jobs-001.json")
    with pytest.raises(c.VerificationError):
        c.pages(contents, entries, "jobs", base)


def test_run_snapshot_rerun_or_conclusion_change_rejected(run):
    contents = {n: c.canonical(run) for n in ("api/run.json", "api/run_after.json")}
    entries = {n: {"kind": "run", "endpoint": f"repos/{c.REPOSITORY}/actions/runs/{RUN_ID}"} for n in contents}
    assert c.validate_runs(contents, entries, SOURCE, RUN_ID, 1)["conclusion"] == "failure"
    mutated = {**run, "run_attempt": 2}
    contents["api/run_after.json"] = c.canonical(mutated)
    with pytest.raises(c.VerificationError, match="run_identity_or_state"):
        c.validate_runs(contents, entries, SOURCE, RUN_ID, 1)


def archive(members):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        for name, data in members:
            z.writestr(name, data)
    return buffer.getvalue()


@pytest.mark.parametrize("name", ["../escape", "/absolute", "a\\b", "a/./b", "x:y", "a//b"])
def test_archive_unsafe_paths_rejected(name):
    with pytest.raises(c.VerificationError):
        c.zip_members(archive([(name, b"x")]))


def test_archive_symlink_rejected():
    entry = zipfile.ZipInfo("link")
    entry.create_system = 3
    entry.external_attr = (stat.S_IFLNK | 0o777) << 16
    with pytest.raises(c.VerificationError, match="link_archive_member"):
        c.zip_members(archive([(entry, b"target")]))


def test_archive_duplicate_member_rejected():
    with pytest.warns(UserWarning), pytest.raises(c.VerificationError, match="duplicate_archive_member"):
        c.zip_members(archive([("x", b"1"), ("x", b"2")]))


def test_archive_exact_members_and_safe_prefixes():
    data = {"external/" + n: n.encode() for n in c.HOSTED_NAMES}
    assert set(c.normalized_members(data, c.HOSTED_NAMES)) == c.HOSTED_NAMES
    data["external/unexpected.json"] = b"{}"
    with pytest.raises(c.VerificationError, match="archive_layout"):
        c.normalized_members(data, c.HOSTED_NAMES)


def test_diagnostics_cannot_contain_success_status():
    with pytest.raises(c.VerificationError, match="archive_layout"):
        c.normalized_members({"required_gate_evidence_v0.json": b"{}", "status.json": b"{}"})


def gate_record_units(run):
    """Schema-shaped unit records with source-derived negative reasons, no real observation."""
    source_paths = [c.POLICY, c.REGISTRY, c.GATE_PLAN, c.GATE_TOOL, c.RECORDER,
                    "schemas/required_gate_evidence_v0.schema.json",
                    "schemas/required_gate_evaluation_result_v0.schema.json"]
    sources = {p: (ROOT / p).read_bytes() for p in source_paths}
    gates = c.source_yaml(sources[c.POLICY])["gates"]["required"]
    plan = c.object_json(sources[c.GATE_PLAN])
    unsupported = c.literal_assignment(sources[c.GATE_TOOL], "UNSUPPORTED_REASONS")
    identity = {"git_sha": SOURCE, "run_key": f"GITHUB_RUN_ID={RUN_ID}|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI",
                "run_mode": "prod"}
    common = {"created_utc": "2026-11-12T10:05:00Z", "run_identity": identity,
              "subject": {"repository": c.REPOSITORY, "commit_sha": SOURCE, "release_candidate": "main"},
              "policy_binding": {"policy_path": c.POLICY, "policy_sha256": c.POLICY_SHA, "policy_set": "required"},
              "registry_binding": {"registry_path": c.REGISTRY, "registry_sha256": c.digest(sources[c.REGISTRY])}}
    diag, observed = {"required_gate_inputs/q2_intake_result_v0.json": c.canonical({"diagnostics": ["q2_metric_failed"]})}, {}
    for gate in gates:
        success = gate not in unsupported and gate != "q2_consistency_ok"
        reason = unsupported.get(gate, "q2_metric_failed")
        ref = {"path": c.GATE_TOOL, "sha256": c.digest(sources[c.GATE_TOOL]),
               "kind": "evaluation_tool", "schema_version": None}
        check = {"check_id": "unit." + gate, "kind": "contract", "passed": success, "details": "Unit record",
                 "command": ["internal", "require-dedicated-current-run-evaluator", gate],
                 "exit_code": 0 if success else None, "evidence_paths": [c.GATE_TOOL],
                 "diagnostics": [] if success else [reason]}
        checks = [check]
        if gate == "q2_consistency_ok":
            checks = [{**check, "check_id": "pulse.required.q2_consistency_ok.intake.v0",
                       "command": ["internal", "q2-archived-intake-v0"],
                       "passed": True, "exit_code": 0, "diagnostics": []},
                      {**check, "check_id": "pulse.required.q2_consistency_ok.metric.v0",
                       "command": ["internal", "q2-unchanged-reducer-and-checker"],
                       "kind": "metric", "passed": False, "exit_code": 1}]
        input_refs = [ref] + [{"path": p, "sha256": c.digest(sources[p]), "kind": "source", "schema_version": None}
                              for p in (c.POLICY, c.REGISTRY, c.GATE_PLAN, "schemas/required_gate_evaluation_result_v0.schema.json")]
        if gate == "q2_consistency_ok":
            input_refs.append({"path": c.ARTIFACT_ROOT + "required_gate_inputs/q2_intake_result_v0.json",
                               "sha256": c.digest(diag["required_gate_inputs/q2_intake_result_v0.json"]),
                               "kind": "q2_intake_metadata", "schema_version": "q2_release_intake_result_v0"})
        if success:
            missing = c.ARTIFACT_ROOT + "required_gate_evaluator_work/" + gate + "/summary.json"
            input_refs.append({"path": missing, "sha256": "0" * 64, "kind": "evaluation_summary", "schema_version": None})
        result = {**common, "schema_version": "required_gate_evaluation_result_v0", "gate_id": gate,
                  "evaluation_id": plan["evaluations"][gate]["evaluation_id"], "pass": success,
                  "status": "passed" if success else "failed",
                  "plan_binding": {"plan_path": c.GATE_PLAN, "plan_sha256": c.digest(sources[c.GATE_PLAN]),
                                   "plan_schema_version": "required_gate_evaluation_plan_v0"},
                  "evaluator": {"id": "pulse_required_gate_dispatcher_v0", "version": "0.1.0",
                                "tool_path": c.GATE_TOOL, "tool_sha256": c.digest(sources[c.GATE_TOOL])},
                  "input_artifacts": input_refs, "checks": checks, "diagnostics": [] if success else [reason],
                  "warnings": ["This current-run evaluator reduces checked-in archived reference evidence; "
                               "it proves deterministic reference mechanics, not live production-model behavior."] if success else [],
                  "authority_boundary": {k: False for k in ["normative", "creates_release_authority", "materializes_status",
                                                           "materializes_release_required", "direct_recorded_evidence_candidate",
                                                           "replaces_check_gates"]}}
        path = plan["evaluations"][gate]["result"]["artifact"]
        raw = c.canonical(result)
        diag[path[len(c.ARTIFACT_ROOT):]] = raw
        group_refs = [{"path": c.GATE_PLAN, "sha256": c.digest(sources[c.GATE_PLAN]), "kind": "evaluation_plan",
                       "schema_version": "required_gate_evaluation_plan_v0"}, ref]
        for stream in ("stdout", "stderr"):
            stream_name = f"required_gate_evidence_logs/{gate}.{stream}.txt"
            diag[stream_name] = b"unit stream\n"
            group_refs.append({"path": c.ARTIFACT_ROOT + stream_name, "sha256": c.digest(diag[stream_name]),
                               "kind": "evaluation_" + stream, "schema_version": None})
        group_refs.append({"path": path, "sha256": c.digest(raw), "kind": "required_gate_evaluation",
                           "schema_version": "required_gate_evaluation_result_v0"})
        observed[gate] = {"value": success, "status": result["status"], "evaluation_id": result["evaluation_id"],
                          "evidence_artifacts": group_refs,
                          "diagnostics": [] if success else ["evaluation command exited with code 1",
                                                             "result JSON pointer '/pass' must be literal true"]}
    document = {**common, "schema_version": "required_gate_evidence_v0",
                "producer": {"id": "pulse_recorded_required_gate_evaluator_v0", "version": "0.1.0", "trusted": True,
                             "tool_path": c.RECORDER, "tool_sha256": c.digest(sources[c.RECORDER])},
                "gates": observed, "warnings": [],
                "authority_boundary": {k: False for k in ["normative", "creates_release_authority",
                                                         "materializes_release_required", "replaces_check_gates"]}}
    diag["required_gate_evidence_v0.json"] = c.canonical(document)
    return diag, sources


def test_nineteen_gate_records_preserve_nonreplayed_intermediate_gap(run):
    diag, sources = gate_record_units(run)
    result = c.check_required_gates(diag, sources, run)
    assert (result["count"], result["passed"], result["failed"]) == (19, 6, 13)
    assert len(result["unpreserved_recipe_intermediates"]) == 6
    assert result["generic_six_metrics_independently_replayed"] is False


@pytest.mark.parametrize("mutation", ["missing_gate", "wrong_run", "timeout", "changed_result_bytes", "promoted_q2", "missing_source_ref"])
def test_required_gate_mutations_rejected(run, mutation):
    diag, sources = gate_record_units(run)
    doc = c.object_json(diag["required_gate_evidence_v0.json"])
    if mutation == "missing_gate":
        del doc["gates"]["effect_present"]
    elif mutation == "wrong_run":
        doc["run_identity"]["run_key"] = "wrong"
    elif mutation == "timeout":
        doc["gates"]["effect_present"]["diagnostics"] = ["evaluation timed out after 600 seconds"]
    elif mutation == "changed_result_bytes":
        diag["required_gate_inputs/effect_present.json"] += b" "
    elif mutation == "promoted_q2":
        doc["gates"]["q2_consistency_ok"].update(value=True, status="passed", diagnostics=[])
    else:
        doc["gates"]["effect_present"]["evidence_artifacts"].append(
            {"path": "missing.json", "sha256": "0" * 64, "kind": "evaluation_input", "schema_version": None})
    diag["required_gate_evidence_v0.json"] = c.canonical(doc)
    with pytest.raises(c.VerificationError):
        c.check_required_gates(diag, sources, run)


def test_duplicate_json_and_nonfinite_rejected():
    for raw in (b'{"x":1,"x":2}', b'{"x":NaN}'):
        with pytest.raises(c.VerificationError):
            c.object_json(raw)


def test_unrelated_new_role_claim_not_inferred():
    path = "schemas/pulsemech_compute_whole_runtime_observation_evidence_v0.schema.json"
    roles = c.legacy_roles({path: (ROOT / path).read_bytes()}, {})
    assert len(roles) == 62
    assert not any(row["original_success_profile_satisfied"] for row in roles.values())
    assert roles["state:step5c:release-decision"]["status"] == "not_produced_on_selected_negative_path"
    assert roles["state:step5c:step3f-current-run-carrier"]["status"] == "not_dispatched"


def test_cli_missing_plan_is_rejection_not_observed_pass(tmp_path):
    output = tmp_path / "report.json"
    command = [sys.executable, str(TOOLS / "check_pulsemech_compute_admission_rejection_v0.py"),
               "--repo-root", str(ROOT), "--plan", str(tmp_path / "missing.json"),
               "--evidence-dir", str(tmp_path), "--expected-source", SOURCE,
               "--expected-run-id", str(RUN_ID), "--expected-attempt", "1",
               "--capture", str(tmp_path / "missing-capture.zip"),
               "--capsule", str(tmp_path / "missing-capsule.zip"), "--replay-python", sys.executable,
               "--out", str(output)]
    completed = subprocess.run(command, capture_output=True, check=False, timeout=30)
    assert completed.returncode == 1
    report = json.loads(output.read_text())
    assert report["accepted"] is False and report["authority_effect"] == "none"
    assert "bounded_claim" not in report


def test_output_is_never_overwritten(tmp_path):
    target = tmp_path / "keep.json"
    target.write_bytes(b"kept")
    with pytest.raises(FileExistsError):
        c.write_new(target, b"replacement")
    assert target.read_bytes() == b"kept"


def test_checker_has_no_builder_or_collector_import():
    source = (TOOLS / "check_pulsemech_compute_admission_rejection_v0.py").read_text()
    assert "import build_pulsemech_compute_admission_rejection" not in source
    assert "import acquire_pulsemech_compute_admission_rejection" not in source


def _controlled_semantic_returns(plan, request, hosted):
    """Test doubles for wrapper contracts only, not observed or semantic evidence."""
    one = plan["source"]["files"][0]
    source_binding = {**{k: one[k] for k in ("path", "mode", "git_blob_sha1", "sha256")}, "size_bytes": one["bytes"]}
    runtime = {"executable": {"bytes": 1, "sha256": "0" * 64},
               "runtime": {"implementation": "CPython", "version": [3, 11, 16], "unicode": "14.0.0",
                           "jsonschema": "test-double", "PyYAML": "test-double"},
               "trust_scope": "caller_trusted_local_interpreter", "original_runtime_identity_proven": False}
    raw_request = c.canonical(request)
    fresh = {"schema_version": "q2_release_intake_result_v0", "record_status": "archived_capture_intake",
             "input_valid": True, "metric_pass": False, "process_exit": 1,
             "diagnostics": ["q2_min_eligible_groups_not_met"],
             "checks": {k: True for k in ("request", "capture", "subject", "replay", "summary")},
             "cleanup": "not_created", "request_sha256": c.digest(raw_request),
             "evaluation_binding": {**request["evaluation_identity"], "workflow_sha": plan["source"]["commit"],
                                    "run_id": str(RUN_ID), "run_attempt": 1, "request_sha256": c.digest(raw_request)},
             "capture_origin": request["capture_expectation"], "release_artifact": request["release_subject"],
             "metrics": {"consistent": 49, "groups_eligible": 49, "groups_total": 50, "inconsistent": 0,
                         "min_n_eligible_groups": 50, "responses_eligible": 147, "responses_total": 150,
                         "threshold": 0.9, "unknown": 1, "wilson_lower_bound": 0.9273021807795037},
             "replay_environment": {"implementation": "CPython", "python": [3, 11, 16], "unicode": "14.0.0"},
             "source_bindings": [{k: source_binding[k] for k in ("path", "sha256", "size_bytes")}],
             "comparison_scope": "exact_capsule_payload_and_launch_descriptor", "release_host_environment": "not_observed",
             "native_verification": "archived_evidence_only", "current_inference_count": 0,
             "authority_effect": "none", "production_gate_eligible": False}
    q2 = {"format": "pulsemech_admission_rejection_q2_semantics_v0", "validation_scope": "later_offline_private_input_replay",
          "request": {"bytes": len(raw_request), "sha256": c.digest(raw_request)},
          "capture": plan["inputs"]["capture"],
          "capsule": {k: plan["inputs"]["capsule"][k] for k in ("bytes", "sha256")},
          "source_bindings": [source_binding], "replay_python": runtime, "fresh_result": fresh,
          "fresh_result_sha256": c.digest(c.canonical(fresh)), "saved_result_sha256": "0" * 64,
          "fresh_independent_checker_executed": True, "saved_records_matched_fresh_result": True,
          "metric_pass": False, "process_exit": 1, "private_cleanup": "verified_removed", "current_inference_count": 0,
          "archive_executables_invoked": False, "original_runtime_reads_proven": False,
          "production_gate_eligible": False, "authority_effect": "none"}
    llama = {"format": "pulsemech_admission_rejection_llamaguard_semantics_v0",
             "validation_scope": "later_content_and_trusted_signature_replay",
             "members": [{"name": name, "bytes": len(raw), "sha256": c.digest(raw)} for name, raw in sorted(hosted.items())],
             "source_bindings": [source_binding], "replay_python": runtime,
             "backend_identity": {"bytes": 1, "sha256": "0" * 64, "trust_scope": "root_owned_system_gh_executable",
                                  "origin_authenticated_by_this_checker": False},
             "content": {"test_double": True}, "attestation": {"test_double": True},
             "fresh_content_checker_executed": True, "fresh_signature_backend_executed": True,
             "saved_verifier_report_matched_fresh_result": True, "private_cleanup": "verified_removed",
             "time_bounds": "supplied_original_run_utc_bounds_checked", "original_runtime_reads_proven": False,
             "model_execution_replayed": False, "model_output_semantic_correctness_verified": False,
             "authority_effect": "none"}
    return q2, llama


def _write_controlled_carrier(directory, run):
    """Make a small trusted Git subject plus controlled records; no production dispatch."""
    import build_pulsemech_compute_admission_rejection_v0 as builder
    repo = directory / "subject"
    repo.mkdir()
    _, initial_sources = gate_record_units(run)
    paths = set(initial_sources) | {c.WORKFLOW,
        "schemas/q2_release_intake_request_v0.schema.json",
        "schemas/pulsemech_compute_whole_runtime_observation_evidence_v0.schema.json",
        "PULSE_safe_pack_v0/profiles/q2_reference_release_intake_v0.json",
        "PULSE_safe_pack_v0/profiles/q2_reference_subject_v0.json"}
    for relative in paths:
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    c.git(repo, ["init", "--quiet"])
    c.git(repo, ["add", "."])
    c.git(repo, ["-c", "user.name=Controlled test", "-c", "user.email=test@example.invalid",
                 "commit", "--quiet", "-m", "Controlled checker subject; not observed evidence"])
    commit = c.git(repo, ["rev-parse", "HEAD"]).decode().strip()
    run = {**run, "head_sha": commit}
    tree, inventory, sources = builder.source_snapshot(repo, commit)
    profile = c.object_json(sources["PULSE_safe_pack_v0/profiles/q2_reference_release_intake_v0.json"])
    request = {"record_type": "q2_release_intake_request_v0", "request_id": "controlled-test",
               "evaluation_identity": {"repository": c.REPOSITORY, "source_commit": commit, "workflow": c.WORKFLOW,
                                       "event": "workflow_dispatch", "ref": "refs/heads/main"},
               "selection": profile["selection"], "capture_expectation": profile["capture_expectation"],
               "release_subject": {"repository": c.REPOSITORY, "artifact_id": 1,
                                   "archive_size_bytes": c.SELECTED_INPUTS["capsule"]["bytes"],
                                   "archive_sha256": c.SELECTED_INPUTS["capsule"]["sha256"],
                                   "capsule_manifest_sha256": c.SELECTED_INPUTS["capsule"]["manifest_sha256"],
                                   "subject_id": profile["subject_id"], "definition_sha256": profile["definition_sha256"],
                                   "layout_profile": profile["layout_profile"]},
               **{k: profile[k] for k in ("comparison_profile", "reduction_profile", "native_verification_mode")}}
    request_raw = c.canonical(request)
    graph = builder.expected_graph(sources[c.WORKFLOW])
    plan = {"format": builder.FORMAT, "profile_id": c.PROFILE, "authority_effect": "none",
            "source": {"repository": c.REPOSITORY, "commit": commit, "tree": tree, "workflow_path": c.WORKFLOW,
                       "workflow_sha256": c.WORKFLOW_SHA, "policy_sha256": c.POLICY_SHA, "files": inventory},
            "request": {"path": "input/q2_request.json", "bytes": len(request_raw), "sha256": c.digest(request_raw)},
            "inputs": c.SELECTED_INPUTS, "dispatch": c.DISPATCH, "expected_graph": graph,
            "limits": c.LIMITS, "excluded_claims": c.EXCLUDED}
    (directory / "input").mkdir()
    (directory / "input/q2_request.json").write_bytes(request_raw)
    (directory / "plan.json").write_bytes(c.canonical(plan))
    jobs = unit_jobs(graph, run)
    for job in jobs:
        job["head_sha"] = commit
    diag, _ = gate_record_units(run)
    doc = c.object_json(diag["required_gate_evidence_v0.json"])
    doc["run_identity"]["git_sha"] = commit
    doc["subject"]["commit_sha"] = commit
    for gate, record in doc["gates"].items():
        name = "required_gate_inputs/" + gate + ".json"
        parsed = c.object_json(diag[name])
        parsed["run_identity"]["git_sha"] = commit
        parsed["subject"]["commit_sha"] = commit
        diag[name] = c.canonical(parsed)
        record["evidence_artifacts"][-1]["sha256"] = c.digest(diag[name])
    diag["required_gate_evidence_v0.json"] = c.canonical(doc)
    diag["required_gate_inputs/q2_intake_independent_result_v0.json"] = diag["required_gate_inputs/q2_intake_result_v0.json"]
    hosted = {name: b'{"test_double":true}\n' for name in c.HOSTED_NAMES}
    attested = {name: b'{"test_double":true}\n' for name in c.ATTESTED_NAMES}
    q2_mock, llama_mock = _controlled_semantic_returns(plan, request, attested)
    (directory / "semantic-test-doubles.json").write_bytes(c.canonical({"q2": q2_mock, "llamaguard": llama_mock}))
    evidence = directory / "evidence"
    evidence.mkdir()
    files = []

    def retain(name, raw, kind, endpoint):
        path = evidence / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        files.append({"path": name, "bytes": len(raw), "sha256": c.digest(raw), "kind": kind, "endpoint": endpoint})

    base = f"repos/{c.REPOSITORY}/actions/runs/{RUN_ID}"
    for name in ("api/run.json", "api/run_after.json"):
        retain(name, c.canonical(run), "run", base)
    source = c.source_yaml(sources[c.WORKFLOW])["jobs"]
    pack_dir = "/home/runner/work/pulse-release-gates-0.1/pulse-release-gates-0.1/PULSE_safe_pack_v0"
    mode = log_for(source["pulse"]["steps"][7]["run"].replace("${{ env.PACK_DIR }}", pack_dir),
                   ["Computed flags: IS_RELEASE=1 MODE=prod POLICY_SET=required LLAMAGUARD_EVIDENCE_MODE=hosted_full_runtime"],
                   environment={"PACK_DIR": pack_dir})
    logs = {
        100: mode + b"\n" + log_for(source["pulse"]["steps"][16]["run"],
            ["Q2 independent negative verification exit: 0", "passed gates: 6", "failed gates: 13",
             "##[error]Process completed with exit code 1."],
            environment={"PULSE_Q2_INTAKE_REQUEST_SHA256": c.digest(request_raw)}),
        102: b"controlled attestation job log",
        103: log_for(source["release_grade_recorded_path"]["steps"][3]["run"],
             ["##[error]BLOCK: pre-attestation candidate was not accepted; hosted evidence remains preserved.",
              "##[error]Process completed with exit code 1."]),
        107: b"controlled tools job log"}
    for job_id, raw in logs.items():
        retain(f"logs/{job_id}.txt", raw, "log", f"repos/{c.REPOSITORY}/actions/jobs/{job_id}/logs")
    artifacts = []
    for artifact_id, (stem, members) in enumerate([
        ("llamaguard-current-run", hosted), ("release-grade-required-gate-diagnostics", diag),
        ("llamaguard-attested-current-run", attested)], 200):
        raw = archive(sorted(members.items()))
        artifacts.append({"id": artifact_id, "name": f"{stem}-{RUN_ID}-1", "expired": False,
                          "size_in_bytes": len(raw), "digest": "sha256:" + c.digest(raw),
                          "workflow_run": {"id": RUN_ID, "head_sha": commit, "head_branch": "main"},
                          "created_at": START, "updated_at": END})
        retain(f"archives/{artifact_id}.zip", raw, "archive", f"repos/{c.REPOSITORY}/actions/artifacts/{artifact_id}/zip")
    for plural, rows, endpoint in (("jobs", jobs, base + "/attempts/1/jobs"), ("artifacts", artifacts, base + "/artifacts")):
        for suffix in ("", "after-"):
            retain(f"api/{plural}-{suffix}001.json", c.canonical({"total_count": len(rows), plural: rows}),
                   plural, endpoint + "?per_page=100&page=1")
    index = {"format": "pulsemech_compute_admission_rejection_acquisition_v0", "profile_id": c.PROFILE,
             "authority_effect": "none", "plan_sha256": c.digest(c.canonical(plan)), "repository": c.REPOSITORY,
             "run_id": RUN_ID, "run_attempt": 1, "source_commit": commit, "completed": True, "errors": [], "files": files}
    (evidence / "acquisition.json").write_bytes(c.canonical(index))
    return commit


def _run_controlled_verify(directory):
    """In-process test injection only. The production CLI offers no such switch."""
    from unittest.mock import patch
    import pulsemech_compute_admission_rejection_semantics_v0 as semantics
    plan = c.object_json((directory / "plan.json").read_bytes())
    mocks = c.object_json((directory / "semantic-test-doubles.json").read_bytes())
    original_identity = c.file_identity

    def test_input_identity(path, maximum):
        if path.name in ("capture-test-only", "capsule-test-only"):
            kind = path.name.split("-")[0]
            return {k: c.SELECTED_INPUTS[kind][k] for k in ("bytes", "sha256")}
        return original_identity(path, maximum)

    def q2(*args):
        assert args[-1].is_dir() and not args[-1].is_relative_to(args[0])
        assert c.git(args[0], ["rev-parse", "HEAD"]).decode().strip() == plan["source"]["commit"]
        return mocks["q2"]

    def llama(*args):
        assert args[-1].is_dir() and not args[-1].is_relative_to(args[0])
        return mocks["llamaguard"]

    with patch.object(c, "file_identity", test_input_identity), patch.object(semantics, "verify_q2", q2), \
            patch.object(semantics, "verify_llamaguard", llama):
        return c.verify(directory / "subject", directory / "plan.json", directory / "evidence",
                        plan["source"]["commit"], RUN_ID, 1, directory / "capture-test-only",
                        directory / "capsule-test-only", Path(sys.executable))


def test_controlled_full_verify_schema_and_two_process_determinism(tmp_path, run):
    _write_controlled_carrier(tmp_path, run)
    # The child invokes the Python API under explicit test mocks, never an
    # accepting production CLI and never genuine observed acquisition evidence.
    program = ("import runpy,sys;from pathlib import Path;"
               "n=runpy.run_path(sys.argv[1]);"
               "r=n['_run_controlled_verify'](Path(sys.argv[2]));"
               "sys.stdout.buffer.write(n['c'].canonical(r))")
    command = [sys.executable, "-c", program, str(Path(__file__)), str(tmp_path)]
    first = subprocess.run(command, capture_output=True, check=False, timeout=45)
    assert first.returncode == 0, first.stderr.decode()
    second = subprocess.run(command, capture_output=True, check=False, timeout=45)
    assert second.returncode == 0, second.stderr.decode()
    assert first.stdout == second.stdout
    report = json.loads(first.stdout)
    assert report["accepted"] is True  # controlled plumbing only; semantic functions are mocked above
    assert len(report["observed_jobs"]) == 8 and len(report["legacy_role_status"]) == 62
    assert report["limitations"]["step5c_complete"] is False
    assert report["limitations"]["original_dispatch_input_receipt_preserved"] is False
    c.validate_schema(report, (ROOT / "schemas/pulsemech_compute_admission_rejection_v0.schema.json").read_bytes(),
                      "controlled_report_schema")


def test_closed_schema_rejects_unknown_plan_fields_and_authority(tmp_path, run):
    _write_controlled_carrier(tmp_path, run)
    schema = (ROOT / "schemas/pulsemech_compute_admission_rejection_v0.schema.json").read_bytes()
    plan = c.object_json((tmp_path / "plan.json").read_bytes())
    c.validate_schema(plan, schema, "plan_schema")
    with pytest.raises(c.VerificationError):
        c.validate_schema({**plan, "skip_verification": True}, schema, "plan_schema")
    with pytest.raises(c.VerificationError):
        c.validate_schema({**plan, "authority_effect": "release"}, schema, "plan_schema")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

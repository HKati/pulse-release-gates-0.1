"""LRM-05: import preserved candidates without importing their claimed truth.

The only evaluation inventory read here contains source-only requests.  The
independent LRM-02 checker receives an exact-byte snapshot of the candidate;
neither reference representations nor expected verdicts enter that path.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import tempfile

from jsonschema import Draft202012Validator

from .io import (InputError, ROOT, canonical_bytes, read_input, safe_read, sha256,
                 strict_json, unique_index, validate_schema)
from .structure import validate_structure
from .verifier import (CHECKER_FILES, PROFILE_ID, PROFILE_PATH, PROFILE_SHA256,
                       checker_reference, verify_input)


VERSION = "0.1.0"
REQUEST_PATH = "examples/language_relation_adapter_v0/requests.json"
REQUEST_SHA256 = "a147703b992e7236e839174c9fe72cd71c83e4781ac27a1c81076fb9c222ca22"
REQUEST_SET_ID = "lrm_hu_en_source_requests_v0"
MAX_RESPONSE_BYTES = 1024 * 1024
MAX_CANDIDATE_NODES = 20_000
MAX_ANCHORS = 256
MAX_COVERAGE_OBLIGATIONS = 64
MAX_CORRESPONDENCES = 256
MAX_REPRESENTATION_RECORDS = 256
_SCHEMAS = (
    "language_relation_adapter_requests_v0.schema.json",
    "language_relation_candidate_records_v0.schema.json",
    "language_relation_adapter_evaluation_v0.schema.json",
)
_QUESTION_FIELDS = ("target_id", "question", "granularity", "description",
                    "context_source_ids")
_CASE_IDS = tuple(f"LRM_REF_{index:02d}" for index in range(1, 24))
_DEFAULT_AXES = {
    "observation_status": "not_observed", "binding_status": "unbound",
    "consistency_status": "internally_incomplete", "reproduction_status": "not_tested",
    "causal_status": "not_evaluated", "authority_status": "none",
}
EVALUATOR_FILES = tuple(sorted(set(CHECKER_FILES) | {
    "tools/language_relation_v0/candidates.py",
    "tools/evaluate_language_relation_candidates_v0.py", REQUEST_PATH,
    *[f"schemas/{name}" for name in _SCHEMAS],
}))


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise InputError(reason)


@lru_cache(maxsize=3)
def _validator(name: str) -> Draft202012Validator:
    _require(name in _SCHEMAS, "unknown candidate-evaluation schema")
    schema = strict_json(safe_read(ROOT / "schemas", name))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _validate(document: dict, name: str) -> None:
    try:
        error = next(_validator(name).iter_errors(document), None)
    except RecursionError as exc:
        raise InputError("candidate-evaluation schema recursion limit") from exc
    if error is not None:
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        # Do not repr a deeply nested, potentially attacker-controlled value.
        raise InputError(f"schema violation at {location}: {error.validator}")


def request_bytes() -> bytes:
    """Return the exact pinned, source-only inventory; never a reference corpus."""
    raw = safe_read(ROOT, REQUEST_PATH)
    _require(sha256(raw) == REQUEST_SHA256, "fixed request inventory digest mismatch")
    return raw


def load_requests() -> dict:
    """Load a fresh mutable copy, checking exact sources and fixed denominators."""
    document = strict_json(request_bytes())
    _validate(document, _SCHEMAS[0])
    expected_profile = {"profile_id": PROFILE_ID, "content_sha256": PROFILE_SHA256}
    _require(document["request_set_id"] == REQUEST_SET_ID,
             "unsupported request inventory")
    _require(document["profile_ref"] == expected_profile, "request profile mismatch")
    requests = unique_index(document["requests"], "case_id")
    _require(set(requests) == set(_CASE_IDS), "fixed request case inventory mismatch")
    languages: Counter = Counter()
    questions = 0
    for request in requests.values():
        _require(request["profile_ref"] == expected_profile, "per-request profile mismatch")
        sources = unique_index(request["sources"], "source_id")
        for side in ("before", "after"):
            _require(sum(row["role"] == side for row in sources.values()) == 1,
                     "request needs one source on each side")
        for source in sources.values():
            _require(source["content"]["kind"] == "inline_utf8",
                     "requests require exact inline source bytes")
            raw = source["content"]["text"].encode("utf-8")
            _require(len(raw) == source["byte_length"] and sha256(raw) == source["content_sha256"],
                     "fixed request source binding mismatch")
        language = next(row["language"] for row in sources.values() if row["role"] == "before")
        _require(all(row["language"] == language for row in sources.values()),
                 "fixed request language mismatch")
        languages[language] += 1
        targets = unique_index(request["questions"], "target_id")
        questions += len(targets)
        contexts = {key for key, source in sources.items() if source["role"] == "context"}
        for question in targets.values():
            _require(set(question["context_source_ids"]) <= contexts,
                     "request question context mismatch")
    _require(languages == {"en": 14, "hu": 9} and questions == 24,
             "fixed request question/language inventory mismatch")
    return document


def request_digest(request: dict) -> str:
    return sha256(canonical_bytes(request))


def evaluator_reference() -> dict:
    files = [{"path": name, "content_sha256": sha256(safe_read(ROOT, name))}
             for name in EVALUATOR_FILES]
    return {"tool_id": "language_relation_candidate_evaluator_v0", "version": VERSION,
            "content_sha256": sha256(canonical_bytes({"files": files}))}


def _artifact(path: str, raw: bytes) -> dict:
    return {"path": path, "byte_length": len(raw), "content_sha256": sha256(raw)}


def _reason(value: object) -> str:
    result = str(value) or type(value).__name__
    return result if len(result) <= 1024 else result[:1001] + " [message truncated]"


def _diagnostic(row: dict, stage: str, code: str, reason: object, *,
                side: str | None = None, origin: str = "importer") -> None:
    row["diagnostics"].append({
        "stage": stage, "code": code, "reason": _reason(reason), "side": side,
        "question_ids": [item["target_id"] for item in row["questions"]], "origin": origin,
    })


def _not_run(check_id: str, kind: str, targets: list[str]) -> dict:
    return {"check_id": check_id, "kind": kind, "target_ids": list(targets),
            "status": "not_run", "result": None,
            "reason": "No admitted candidate has completed the independent checker.",
            "evidence_refs": []}


def _case(request: dict) -> dict:
    targets = sorted(item["target_id"] for item in request["questions"])
    source_roles = sorted({item["role"] for item in request["sources"]})
    return {
        "case_id": request["case_id"], "request_sha256": request_digest(request),
        "language": next(item["language"] for item in request["sources"] if item["role"] == "before"),
        "record_ids": [], "capture_status": "missing", "import_status": "not_run",
        "declared_confidence": None, "submitted_response": None,
        "response_ref": None, "input_ref": None, "verification_ref": None,
        "interpretation_state": None,
        "source_checks": [_not_run(f"source.{side}", "source_binding", targets)
                          for side in source_roles],
        "mapping_checks": [_not_run(f"mapping.{side}", "representation_mapping", targets)
                           for side in ("before", "after")],
        "questions": [{**deepcopy(question), "scope_selection": "not_verified",
                       "representation_basis": "candidate_only", "claim_scope": "candidate_structures",
                       "candidate_selection": None, "coverage_checks": []}
                      for question in sorted(request["questions"], key=lambda item: item["target_id"])],
        "reported_unresolved_items": [], "diagnostics": [],
        "status_axes": dict(_DEFAULT_AXES), "authority_effect": "none",
        "release_authority_activation": False,
    }


def _locations(record: dict, request: dict) -> None:
    sources = {row["source_id"]: row["content"]["text"].encode("utf-8")
               for row in request["sources"]}
    targets = {row["target_id"] for row in request["questions"]}
    unique_index(record["unresolved_items"], "issue_id")
    for issue in record["unresolved_items"]:
        _require(issue["source_id"] in sources, "unresolved item names another source")
        raw = sources[issue["source_id"]]
        start, end = issue["start_byte"], issue["end_byte"]
        _require(0 <= start < end <= len(raw), "unresolved item has an invalid byte interval")
        try:
            raw[:start].decode("utf-8")
            raw[:end].decode("utf-8")
        except UnicodeError as exc:
            raise InputError("unresolved item splits a UTF-8 character") from exc
        _require(set(issue["question_ids"]) <= targets,
                 "unresolved item names another question")


def _candidate_limits(document: dict) -> None:
    pending = [document]
    count = 0
    while pending:
        node = pending.pop()
        count += 1
        if count > MAX_CANDIDATE_NODES:
            raise InputError("candidate JSON node resource limit exceeded")
        if isinstance(node, dict):
            pending.extend(node)
            pending.extend(node.values())
        elif isinstance(node, list):
            pending.extend(node)
    _require(len(document["source_anchors"]) <= MAX_ANCHORS,
             "candidate anchor resource limit exceeded")
    _require(len(document["coverage_obligations"]) <= MAX_COVERAGE_OBLIGATIONS,
             "candidate coverage resource limit exceeded")
    _require(len(document["correspondence"]) <= MAX_CORRESPONDENCES,
             "candidate correspondence resource limit exceeded")
    for representation in document["representations"].values():
        _require(all(len(representation[name]) <= MAX_REPRESENTATION_RECORDS
                     for name in ("entities", "domains", "relations", "groups")),
                 "candidate representation resource limit exceeded")


def _request_binding(document: dict, request: dict) -> None:
    _require(document["case_id"] == request["case_id"], "candidate case differs from request")
    _require(document["profile_ref"] == request["profile_ref"], "candidate profile differs from request")
    submitted = unique_index(document["sources"], "source_id")
    expected = unique_index(request["sources"], "source_id")
    _require(submitted == expected, "candidate source/context records differ from fixed request")
    targets = unique_index(document["measurement_request"]["targets"], "target_id")
    questions = unique_index(request["questions"], "target_id")
    _require(set(targets) == set(questions), "candidate target inventory differs from fixed questions")
    for identifier, question in questions.items():
        selected = {name: targets[identifier][name] for name in _QUESTION_FIELDS}
        _require(canonical_bytes(selected) == canonical_bytes(question),
                 f"candidate question metadata differs from request: {identifier}")


def _candidate_boundary(document: dict, producer: dict) -> None:
    for basis in document["representation_basis"].values():
        _require(basis == {"basis": "candidate_only", "verification_ref": None,
                           "acceptance_ref": None},
                 "candidate cannot supply a stronger basis or acceptance/verification reference")
    _require(all(item["basis"] == "candidate" and item["rule_or_reference_id"] is None
                 for item in document["correspondence"]),
             "candidate correspondence cannot supply an accepted premise")
    _require(all(not item["evidence_refs"] for item in document["coverage_obligations"]),
             "candidate cannot supply coverage acceptance evidence")
    _require(document["processing_binding"] is None and
             document["measurement_request"]["processing_claim"] == "structural_comparison",
             "candidate cannot establish a processing event")
    _require(document["impact_model"] is None,
             "candidate import does not admit independently grounded impact premises")
    allowed = ({"synthetic_reference", "synthetic_contract_example"}
               if producer["record_origin"] == "synthetic_fixture" else {"captured_input"})
    _require(document["provenance"] in allowed,
             "candidate provenance contradicts declared record origin")


def _rejected(row: dict, stage: str, code: str, error: object) -> None:
    row["import_status"] = "rejected"
    _diagnostic(row, stage, code, error)


def _problem_code(error: Exception, default: str) -> str:
    # Match fixed checker messages, not arbitrary identifiers or paths which
    # happen to contain the word "limit".
    fixed = {
        "JSON byte limit exceeded", "JSON structure resource limit exceeded",
        "schema validation depth exceeded", "expression depth limit exceeded",
        "candidate-evaluation schema recursion limit",
    }
    message = str(error)
    bounded = (message in fixed or message.startswith("file byte limit exceeded: ")
               or message.startswith("invalid UTF-8 JSON: maximum recursion depth exceeded"))
    return "resource_limit" if isinstance(error, RecursionError) or bounded else default


def _checked(row: dict, document: dict, verification: dict, raw: bytes,
             payloads: dict[str, bytes]) -> None:
    case_id = row["case_id"]
    verification_raw = canonical_bytes(verification)
    strict_json(verification_raw)
    row["input_ref"] = _artifact(f"inputs/{case_id}.json", raw)
    row["verification_ref"] = _artifact(f"verifications/{case_id}.json", verification_raw)
    row["import_status"] = "checked"
    row["interpretation_state"] = document["interpretations"]["state"]
    payloads[row["input_ref"]["path"]] = raw
    payloads[row["verification_ref"]["path"]] = verification_raw
    row["source_checks"] = [deepcopy(check) for check in verification["checks"]
                            if check["kind"] == "source_binding"]
    row["mapping_checks"] = [deepcopy(check) for check in verification["checks"]
                             if check["kind"] == "representation_mapping"]
    row["status_axes"] = deepcopy(verification["status_axes"])
    targets = {item["target_id"]: item for item in document["measurement_request"]["targets"]}
    for question in row["questions"]:
        target = targets[question["target_id"]]
        question["candidate_selection"] = {
            name: deepcopy(target[name])
            for name in ("before_ids", "after_ids", "required_obligation_ids")}
        question["coverage_checks"] = [deepcopy(check) for check in verification["checks"]
                                       if check["kind"] == "coverage" and
                                       question["target_id"] in check["target_ids"]]
    for check in [*row["source_checks"], *row["mapping_checks"]]:
        if check["result"] == "pass":
            continue
        side = check["check_id"].split(".", 1)[1]
        if check["kind"] == "source_binding":
            code = "source_binding_failed" if check["result"] == "fail" else "source_binding_unresolved"
        elif check["result"] == "fail":
            code = "representation_mismatch"
        elif check["result"] is None:
            code = "mapping_not_run"
        else:
            reason = check["reason"] or ""
            reason_code = reason.partition(":")[0]
            resource_codes = {
                "source_size_limit", "source_ast_limit", "expanded_atom_limit",
                "representation_ast_limit", "variant_limit", "checker_recursion_limit",
                "reference_depth_limit",
            }
            unsupported_codes = {
                "unsupported_language", "unsupported_source_grammar",
                "unsupported_person_label", "unsupported_profile",
            }
            code = ("resource_limit" if reason_code in resource_codes or
                    reason == "joint variant resource bound exceeded" else
                    "unsupported_source" if reason_code in unsupported_codes else "interpretation_unresolved")
        _diagnostic(row, check["kind"], code, check["reason"] or "Check did not pass.",
                    side=side, origin="independent_checker")


def _evaluate_case(row: dict, request: dict, record: dict, producer: dict,
                   root: Path, profile: dict, payloads: dict[str, bytes]) -> None:
    row["capture_status"] = record["capture_status"]
    row["declared_confidence"] = record["confidence"]
    row["submitted_response"] = deepcopy(record["response"])
    row["reported_unresolved_items"] = deepcopy(record["unresolved_items"])
    if record["request_sha256"] != row["request_sha256"]:
        _rejected(row, "request_binding", "request_digest_mismatch", "Capture names different request bytes.")
        return
    try:
        _locations(record, request)
    except InputError as exc:
        _rejected(row, "unresolved_location", "invalid_unresolved_location", exc)
        return
    if record["capture_status"] != "completed":
        code = {"failed": "extraction_failed", "unsupported": "producer_unsupported",
                "not_run": "extraction_not_run"}[record["capture_status"]]
        _diagnostic(row, "capture", code, record["reason"], origin="producer_declaration")
        return
    response = record["response"]
    if response["byte_length"] > MAX_RESPONSE_BYTES:
        _rejected(row, "response_read", "resource_limit", "Declared response exceeds the 1 MiB import bound.")
        return
    try:
        raw = safe_read(root, response["path"], limit=MAX_RESPONSE_BYTES)
    except InputError as exc:
        _rejected(row, "response_read", _problem_code(exc, "unsafe_response_path"), exc)
        return
    except OSError as exc:
        _rejected(row, "response_read", "response_unavailable", exc)
        return
    response_path = f"responses/{row['case_id']}.bin"
    payloads[response_path] = raw
    row["response_ref"] = _artifact(response_path, raw)
    if len(raw) != response["byte_length"] or sha256(raw) != response["content_sha256"]:
        _rejected(row, "response_binding", "response_digest_or_size_mismatch", "Saved response bytes do not match the capture record.")
        return
    try:
        document = strict_json(raw)
    except InputError as exc:
        _rejected(row, "response_parse", _problem_code(exc, "invalid_response_json"), exc)
        return
    try:
        validate_schema(document, "language_relation_input_v0.schema.json")
    except (InputError, RecursionError) as exc:
        _rejected(row, "candidate_schema", _problem_code(exc, "invalid_candidate_schema"), exc)
        return
    try:
        _candidate_limits(document)
    except InputError as exc:
        _rejected(row, "candidate_structure", "resource_limit", exc)
        return
    try:
        _request_binding(document, request)
    except InputError as exc:
        _rejected(row, "request_binding", "candidate_request_mismatch", exc)
        return
    try:
        _candidate_boundary(document, producer)
    except InputError as exc:
        _rejected(row, "candidate_boundary", "prohibited_candidate_claim", exc)
        return
    try:
        validate_structure(document, profile)
    except (InputError, RecursionError) as exc:
        _rejected(row, "candidate_structure", _problem_code(exc, "invalid_candidate_structure"), exc)
        return
    # Freeze the bytes already bound above.  A package mutation after this read
    # cannot make verify_input consume a different candidate under an old pin.
    try:
        with tempfile.TemporaryDirectory(prefix="lrm05-candidate-") as directory:
            snapshot = Path(directory) / "input.json"
            with snapshot.open("xb") as stream:
                stream.write(raw)
            verification = verify_input(snapshot, package_root=Path(directory))
        _require(verification["input_ref"] == {"artifact_id": document["case_id"],
                                               "content_sha256": sha256(raw)},
                 "independent checker returned a different input binding")
        checked_row = deepcopy(row)
        checked_payloads: dict[str, bytes] = {}
        _checked(checked_row, document, verification, raw, checked_payloads)
        row.update(checked_row)
        payloads.update(checked_payloads)
    except Exception as exc:
        # This is a recorded execution failure, never a semantic rejection or
        # successful check.  Continue only with independent later case inputs.
        row["import_status"] = "execution_error"
        _diagnostic(row, "verification", "checker_execution_error",
                    f"{type(exc).__name__}: {_reason(exc)}")


def _counts(cases: list[dict]) -> dict:
    mappings = [check for case in cases for check in case["mapping_checks"]]
    result = {
        "selected_cases": len(cases), "selected_questions": sum(len(case["questions"]) for case in cases),
        "checked_cases": sum(case["import_status"] == "checked" for case in cases),
        "rejected_cases": sum(case["import_status"] == "rejected" for case in cases),
        "execution_error_cases": sum(case["import_status"] == "execution_error" for case in cases),
        "both_mapping_pass_cases": sum(all(check["result"] == "pass" for check in case["mapping_checks"])
                                       for case in cases),
    }
    for field, state in (("missing_cases", "missing"), ("capture_failed_cases", "failed"),
                         ("unsupported_cases", "unsupported"), ("not_run_cases", "not_run"),
                         ("ambiguous_cases", "ambiguous")):
        result[field] = sum(case["capture_status"] == state for case in cases)
    for field, state in (("mapping_pass", "pass"), ("mapping_fail", "fail"),
                         ("mapping_unresolved", "unresolved"), ("mapping_not_run", None)):
        result[field] = sum(check["result"] == state for check in mappings)
    return result


def evaluate_candidates(records_path: Path, *, package_root: Path | None = None) -> dict:
    """Evaluate every fixed request; return a report and exact publication bytes.

    A globally malformed capture index raises InputError.  Attributable capture,
    candidate, mapping, and execution failures remain in their own case rows.
    Completion means diagnostics were produced, not that extraction succeeded.
    """
    inventory = load_requests()
    inventory_raw = request_bytes()
    records_path = Path(records_path)
    root = Path(package_root) if package_root is not None else records_path.absolute().parent
    root = root.resolve(strict=True)
    records_raw = read_input(records_path, root)
    records = strict_json(records_raw)
    _validate(records, _SCHEMAS[1])
    _require(records["request_set_ref"] == {"request_set_id": REQUEST_SET_ID,
                                           "content_sha256": REQUEST_SHA256},
             "capture index names another request inventory")
    unique_index(records["records"], "record_id")
    profile_raw = safe_read(ROOT, PROFILE_PATH)
    _require(sha256(profile_raw) == PROFILE_SHA256, "independent profile digest mismatch")
    profile = strict_json(profile_raw)
    requests = {row["case_id"]: row for row in inventory["requests"]}
    groups: dict[str, list[dict]] = {key: [] for key in requests}
    extras = []
    for record in records["records"]:
        if record["case_id"] in groups:
            groups[record["case_id"]].append(record)
        else:
            extras.append({"record_id": record["record_id"], "case_id": record["case_id"],
                           "reason": "case_not_selected", "response_read": False})
    payloads = {"requests.json": inventory_raw, "records.json": records_raw}
    cases = []
    for identifier in sorted(requests):
        request = requests[identifier]
        row = _case(request)
        selected = groups[identifier]
        row["record_ids"] = sorted(record["record_id"] for record in selected)
        if not selected:
            _diagnostic(row, "capture", "missing_capture", "No saved extraction record was submitted.")
        elif len(selected) != 1:
            row["capture_status"] = "ambiguous"
            row["import_status"] = "rejected"
            _diagnostic(row, "capture", "duplicate_case_records", "Multiple records name this case; no candidate was selected.")
        else:
            _evaluate_case(row, request, selected[0], records["producer"], root, profile, payloads)
        cases.append(row)
    summary = _counts(cases)
    summary.update(record_count=len(records["records"]),
                   submitted_cases=sum(bool(rows) for rows in groups.values()),
                   by_language={language: _counts([row for row in cases if row["language"] == language])
                                for language in ("en", "hu")},
                   all_cases_retained=True, all_questions_retained=True)
    axes = dict(_DEFAULT_AXES)
    checks = [check for row in cases for check in [*row["source_checks"], *row["mapping_checks"]]]
    if any(check["status"] == "completed" for check in checks):
        axes["observation_status"] = "partially_observed"
    if any(check["kind"] == "source_binding" and check["result"] == "pass" for check in checks):
        axes["binding_status"] = "partially_bound"
    if any(check["result"] == "fail" for check in checks):
        axes["consistency_status"] = "conflicting"
    report = {
        "schema_version": "language_relation_adapter_evaluation_v0",
        "artifact_kind": "language_relation_adapter_evaluation",
        "request_set_ref": {"request_set_id": REQUEST_SET_ID, "content_sha256": REQUEST_SHA256},
        "records_ref": {"record_set_id": records["record_set_id"], **_artifact("records.json", records_raw)},
        "profile_ref": deepcopy(inventory["profile_ref"]),
        "evaluator_ref": evaluator_reference(), "checker_ref": checker_reference(),
        "producer": deepcopy(records["producer"]), "producer_authentication": "not_verified",
        "historical_input_isolation": "not_verified", "claim_scope": "candidate_structures",
        "model_quality": "not_evaluated", "reference_agreement": "not_evaluated",
        "cases": cases, "unselected_records": sorted(extras, key=lambda row: row["record_id"]),
        "summary": summary, "status_axes": axes,
        "authority_effect": "none", "release_authority_activation": False,
    }
    report["evaluation_id"] = "lrm05." + sha256(canonical_bytes(report))[:48]
    # No oversized successful prefix is published.  All cases/questions remain
    # together, and every JSON file must fit the existing strict reader.
    strict_json(canonical_bytes(report))
    _validate(report, _SCHEMAS[2])
    for path, raw in payloads.items():
        if path.endswith(".json"):
            strict_json(raw)
    return {"evaluation": report, "payloads": payloads}

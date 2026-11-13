"""Bounded parsing and admission for the deterministic cyclic research profile.

This shared layer checks shapes, bindings and the supported input language.  It
does not decide any of the six model claims.  Each public evaluation/check call
parses its own immutable input bytes; no mutable admitted object is a premise.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from decimal import Decimal, InvalidOperation
from typing import Any


QUESTIONS = (
    "direct_route_removed",
    "new_failure_route_feasible",
    "failure_then_mode_return",
    "complete_state_return",
    "counter_projection_sound",
    "repeatable_structural_return",
)
E = "ESTABLISHED_IN_MODEL"
R = "REFUTED_IN_MODEL"
U = "UNRESOLVED"
SEMANTICS = "PD-CYCLIC-DETERMINISTIC-v0"
REPORT_FORMAT = "PULSEMECH-PARADOX-CYCLIC-EVALUATION-v0"
VERIFY_FORMAT = "PULSEMECH-PARADOX-CYCLIC-VERIFICATION-v0"

MAX_INPUT_BYTES = 1024 * 1024
MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_DEPTH = 32
MAX_NUMBER_TOKEN = 128
MAX_PARSED_INTEGER = 10**18
MAX_INPUT_COUNTER = 10**12
_IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}")
_SHA1 = re.compile(r"[a-f0-9]{40}")


class CyclicError(ValueError):
    """A stable, bounded rejection code; never a model-level verdict."""

    def __init__(self, code: str, kind: str = "INPUT_INVALID") -> None:
        self.code = code
        self.kind = kind
        super().__init__(f"{kind}:{code}")


def _invalid(code: str) -> None:
    raise CyclicError(code)


def _unsupported(code: str) -> None:
    raise CyclicError(code, kind="INPUT_UNSUPPORTED")


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _invalid("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _number(token: str) -> int:
    if len(token) > MAX_NUMBER_TOKEN:
        _unsupported("NUMBER_TOKEN_LIMIT")
    try:
        number = Decimal(token)
        if not number.is_finite():
            _invalid("NONFINITE_NUMBER")
        # Check magnitude before int() so an enormous exponent cannot allocate
        # a huge integer. Integral JSON exponent/decimal forms stay exact.
        if number.copy_abs() > MAX_PARSED_INTEGER:
            _unsupported("INTEGER_MAGNITUDE_LIMIT")
        if number != number.to_integral_value():
            _invalid("NONINTEGRAL_NUMBER")
        return int(number)
    except InvalidOperation as error:
        raise CyclicError("NUMBER_REPRESENTATION_LIMIT", "INPUT_UNSUPPORTED") from error


def _constant(_token: str) -> None:
    _invalid("NONFINITE_NUMBER")


def _check_nesting(text: str) -> None:
    depth = 0
    in_string = False
    escaped = False
    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
        elif character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            if depth > MAX_DEPTH:
                _unsupported("JSON_DEPTH_LIMIT")
        elif character in "]}":
            depth -= 1
    # json.loads checks balancing, token syntax and unterminated strings.


def _check_unicode(value: Any) -> None:
    pending = [value]
    while pending:
        item = pending.pop()
        if type(item) is str:
            if any(0xD800 <= ord(character) <= 0xDFFF for character in item):
                _invalid("INVALID_UNICODE_SCALAR")
        elif type(item) is dict:
            pending.extend(item.keys())
            pending.extend(item.values())
        elif type(item) is list:
            pending.extend(item)


def parse_json_bytes(raw: bytes) -> Any:
    """Parse bounded UTF-8 JSON with unique keys and exact integer numbers."""
    if type(raw) is not bytes:
        _invalid("IMMUTABLE_BYTES_REQUIRED")
    if len(raw) > MAX_JSON_BYTES:
        _unsupported("JSON_BYTE_LIMIT")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise CyclicError("INVALID_UTF8") from error
    _check_nesting(text)
    try:
        value = json.loads(
            text,
            object_pairs_hook=_object_pairs,
            parse_int=_number,
            parse_float=_number,
            parse_constant=_constant,
        )
    except (json.JSONDecodeError, RecursionError) as error:
        raise CyclicError("INVALID_JSON") from error
    _check_unicode(value)
    return value


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encode_json(value: Any) -> bytes:
    """Serialize a result deterministically; this is not input canonicalization."""
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def _keys(value: Any, expected: set[str], code: str) -> None:
    if type(value) is not dict or set(value) != expected:
        _invalid(code)


def _array(value: Any, minimum: int, maximum: int, code: str) -> list[Any]:
    if type(value) is not list or len(value) < minimum:
        _invalid(code)
    if len(value) > maximum:
        _unsupported(code + "_LIMIT")
    return value


def _identifier(value: Any, code: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        _invalid(code)
    return value


def _reference(value: Any, domain: set[str], code: str) -> str:
    identity = _identifier(value, code)
    if identity not in domain:
        _invalid(code)
    return identity


def _counter(value: Any) -> int:
    if type(value) is not int or value < 0:
        _invalid("COUNTER_TYPE_OR_RANGE")
    if value > MAX_INPUT_COUNTER:
        _unsupported("COUNTER_LIMIT")
    return value


def _state(value: Any, subjects: set[str], modes: set[str]) -> tuple[str, str, int]:
    _keys(value, {"subject_id", "mode", "counter"}, "STATE_KEYS")
    return (
        _reference(value["subject_id"], subjects, "STATE_SUBJECT"),
        _reference(value["mode"], modes, "STATE_MODE"),
        _counter(value["counter"]),
    )


def _domain_ids(value: Any, maximum: int, code: str) -> set[str]:
    rows = _array(value, 1, maximum, code)
    result: set[str] = set()
    for item in rows:
        identity = _identifier(item, code)
        if identity in result:
            _invalid(code + "_DUPLICATE")
        result.add(identity)
    return result


def _predicates(value: Any, subjects: set[str], modes: set[str]) -> set[str]:
    declarations = _array(value, 0, 32, "PREDICATES")
    identities: set[str] = set()
    fact_count = 0
    for declaration in declarations:
        _keys(
            declaration,
            {"predicate_id", "arguments", "interpretation", "facts"},
            "PREDICATE_KEYS",
        )
        identity = _identifier(declaration["predicate_id"], "PREDICATE_ID")
        if identity in identities:
            _invalid("DUPLICATE_PREDICATE_ID")
        identities.add(identity)
        if declaration["arguments"] != ["subject_id", "mode", "counter"]:
            _invalid("PREDICATE_ARGUMENTS")
        if declaration["interpretation"] != "fixed_total_boolean_function":
            _invalid("PREDICATE_INTERPRETATION")
        facts = _array(declaration["facts"], 0, 4096, "PREDICATE_FACTS")
        fact_count += len(facts)
        if fact_count > 4096:
            _unsupported("CASE_FACT_LIMIT")
        states: set[tuple[str, str, int]] = set()
        for fact in facts:
            _keys(fact, {"state", "value"}, "FACT_KEYS")
            state = _state(fact["state"], subjects, modes)
            if type(fact["value"]) is not bool:
                _invalid("FACT_VALUE_TYPE")
            if state in states:
                _invalid("DUPLICATE_OR_CONTRADICTORY_FACT")
            states.add(state)
    return identities


def _guard(value: Any, predicates: set[str]) -> None:
    if type(value) is not dict or type(value.get("kind")) is not str:
        _invalid("GUARD_SHAPE")
    kind = value["kind"]
    if kind == "unconditional":
        _keys(value, {"kind"}, "GUARD_KEYS")
    elif kind == "counter_below":
        _keys(value, {"kind", "limit"}, "GUARD_KEYS")
        _counter(value["limit"])
    elif kind == "predicate":
        _keys(value, {"kind", "predicate_id"}, "GUARD_KEYS")
        _reference(value["predicate_id"], predicates, "GUARD_PREDICATE_REFERENCE")
    else:
        _invalid("UNKNOWN_GUARD_KIND")


def _phase(
    value: Any, subjects: set[str], modes: set[str], predicates: set[str]
) -> bool:
    _keys(value, {"complete_rule_inventory", "rules"}, "PHASE_KEYS")
    if value["complete_rule_inventory"] is not True:
        _invalid("INCOMPLETE_RULE_INVENTORY")
    rules = _array(value["rules"], 0, 128, "PHASE_RULES")
    identities: set[str] = set()
    sources: set[tuple[str, str]] = set()
    deterministic = True
    for rule in rules:
        _keys(
            rule,
            {"rule_id", "subject_id", "from_mode", "to_mode", "guard", "counter_increment"},
            "RULE_KEYS",
        )
        identity = _identifier(rule["rule_id"], "RULE_ID")
        if identity in identities:
            _invalid("DUPLICATE_RULE_ID")
        identities.add(identity)
        subject = _reference(rule["subject_id"], subjects, "RULE_SUBJECT")
        source = _reference(rule["from_mode"], modes, "RULE_SOURCE_MODE")
        _reference(rule["to_mode"], modes, "RULE_TARGET_MODE")
        if type(rule["counter_increment"]) is not int or rule["counter_increment"] != 1:
            _invalid("COUNTER_INCREMENT_NOT_ONE")
        _guard(rule["guard"], predicates)
        key = (subject, source)
        if key in sources:
            deterministic = False
        sources.add(key)
    return deterministic


def _case(value: Any) -> tuple[str, bool, bool]:
    _keys(
        value,
        {"case_id", "domain", "failure_condition", "predicate_declarations", "before", "after", "query"},
        "CASE_KEYS",
    )
    identity = _identifier(value["case_id"], "CASE_ID")
    domain = value["domain"]
    _keys(domain, {"subject_ids", "modes", "counter_domain"}, "DOMAIN_KEYS")
    subjects = _domain_ids(domain["subject_ids"], 16, "DOMAIN_SUBJECTS")
    modes = _domain_ids(domain["modes"], 64, "DOMAIN_MODES")
    if domain["counter_domain"] != "nonnegative_integers":
        _invalid("COUNTER_DOMAIN")
    failure = value["failure_condition"]
    _keys(failure, {"mode_equals"}, "FAILURE_KEYS")
    failure_mode = _reference(failure["mode_equals"], modes, "FAILURE_MODE")
    predicates = _predicates(value["predicate_declarations"], subjects, modes)
    before_deterministic = _phase(value["before"], subjects, modes, predicates)
    after_deterministic = _phase(value["after"], subjects, modes, predicates)
    query = value["query"]
    _keys(
        query,
        {"selected_subject_id", "initial_state", "displayed_new_failure_route_modes", "return_projection", "projection_scope"},
        "QUERY_KEYS",
    )
    selected = _reference(query["selected_subject_id"], subjects, "SELECTED_SUBJECT")
    initial_subject, initial_mode, _ = _state(query["initial_state"], subjects, modes)
    if initial_subject != selected:
        _invalid("INITIAL_SUBJECT_MISMATCH")
    route = _array(query["displayed_new_failure_route_modes"], 2, 256, "DISPLAYED_ROUTE")
    for mode in route:
        _reference(mode, modes, "DISPLAYED_ROUTE_MODE")
    if route[0] != initial_mode or route[-1] != failure_mode:
        _invalid("DISPLAYED_ROUTE_ENDPOINTS")
    if query["return_projection"] != ["subject_id", "mode"]:
        _invalid("RETURN_PROJECTION")
    if query["projection_scope"] != "all_declared_states_for_selected_subject":
        _invalid("PROJECTION_SCOPE")
    return identity, before_deterministic and after_deterministic, initial_mode != failure_mode


def admit_bundle(raw: bytes) -> dict[str, Any]:
    """Validate one input bundle without reading schema/reference files.

    Parallel outgoing rules and an initially failed mode are valid broader
    research inputs but outside this implementation profile.  Reject them
    explicitly instead of substituting a model-level UNRESOLVED/REFUTED claim.
    """
    if type(raw) is not bytes:
        _invalid("IMMUTABLE_BYTES_REQUIRED")
    if len(raw) > MAX_INPUT_BYTES:
        _unsupported("INPUT_BYTE_LIMIT")
    bundle = parse_json_bytes(raw)
    _keys(
        bundle,
        {"format", "status", "source_baseline", "authority_effect", "production_gate_eligible", "question_ids", "cases"},
        "INPUT_KEYS",
    )
    if bundle["format"] != "PULSEMECH-PARADOX-CYCLIC-CASES-v0":
        _invalid("INPUT_FORMAT")
    if bundle["status"] != "research_case_inputs_not_execution":
        _invalid("INPUT_STATUS")
    baseline = bundle["source_baseline"]
    if type(baseline) is not str or _SHA1.fullmatch(baseline) is None:
        _invalid("SOURCE_BASELINE")
    if bundle["authority_effect"] != "none" or bundle["production_gate_eligible"] is not False:
        _invalid("INPUT_AUTHORITY")
    if bundle["question_ids"] != list(QUESTIONS):
        _invalid("QUESTION_IDS")
    cases = _array(bundle["cases"], 1, 16, "CASES")
    identities: set[str] = set()
    deterministic = True
    nonfailure_initial = True
    for case in cases:
        identity, case_deterministic, case_nonfailure_initial = _case(case)
        if identity in identities:
            _invalid("DUPLICATE_CASE_ID")
        identities.add(identity)
        deterministic = deterministic and case_deterministic
        nonfailure_initial = nonfailure_initial and case_nonfailure_initial
    if not deterministic:
        _unsupported("PARALLEL_OUTGOING_RULES")
    if not nonfailure_initial:
        _unsupported("INITIAL_MODE_IS_FAILURE")
    return bundle


def read_bytes(path: str | os.PathLike[str]) -> bytes:
    """Read a bounded regular file, using O_NOFOLLOW where available.

    The opened descriptor is checked before and after reading.  This is a local
    consistency check, not a hostile-filesystem snapshot or an authentication
    claim; parent-directory and host integrity remain outside the model.
    """
    descriptor: int | None = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        descriptor = os.open(path, flags)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            _invalid("REGULAR_FILE_REQUIRED")
        if before.st_size > MAX_JSON_BYTES:
            _unsupported("FILE_BYTE_LIMIT")
        chunks: list[bytes] = []
        size = 0
        while size <= MAX_JSON_BYTES:
            chunk = os.read(descriptor, min(65536, MAX_JSON_BYTES + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        if size > MAX_JSON_BYTES:
            _unsupported("FILE_BYTE_LIMIT")
        after = os.fstat(descriptor)
        attributes = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        if size != before.st_size or any(
            getattr(before, key) != getattr(after, key) for key in attributes
        ):
            _invalid("FILE_CHANGED_DURING_READ")
        return b"".join(chunks)
    except (OSError, ValueError, TypeError) as error:
        if isinstance(error, CyclicError):
            raise
        raise CyclicError("FILE_READ_FAILED") from error
    finally:
        if descriptor is not None:
            os.close(descriptor)

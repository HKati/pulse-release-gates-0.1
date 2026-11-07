"""Independent source checker for the immutable finite LRM v0 profile.

This module parses the original controlled-language source; it never invokes a
candidate adapter, reads an oracle, or selects a result by case identifier.  A
successful mapping check is a local fact about communicated roots.  It does not
accept a reference inventory, identify entities across sources, close external
context obligations, establish a world fact, or grant release authority.

The caller first validates the artifact and binds its exact source/profile
bytes.  Defensive bounds here also keep REF expansion and source parsing finite.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any


_PROFILE_ID = "lrm_finite_reference_profile_v0"
_PEOPLE = ("Anna", "Béla", "Éva", "Dániel")
_VARIABLES = ("x", "y", "z")
_MAX_NODES = 256
_MAX_VARIANTS = 64
_MAX_ATOMS = 12
# Every literal v0 production contributes fewer than 128 UTF-8 bytes per AST
# node, including the largest finite PERSON_LIST.  This is a conservative bound
# derived from the fixed grammar, not a normalization or a larger language.
_MAX_SOURCE_BYTES = _MAX_NODES * 128 + 1
_DEFAULT_CONTEXT = ("assertion", "declarative", None)

# Literal terminals from the preserved v0 profile, not a free-language model.
_TERMINALS = {
    "en": {
        "not": "not (", "and": ") and (", "or": ") or (",
        "if": "if (", "then": ") then (",
        "forall": "for every ", "exists": "for some ",
        "domain": " in {", "body": "} (",
        "quote": " says: (", "approve": " approves", "win": " wins",
        "permission": "it is permitted that (",
        "obligation": "it is required that (",
    },
    "hu": {
        "not": "nem (", "and": ") és (", "or": ") vagy (",
        "if": "ha (", "then": "), akkor (",
        "forall": "minden ", "exists": "van olyan ",
        "domain": " a {", "body": "} halmazból (",
        "quote": " mondja: (", "approve": " jóváhagy", "win": " nyer",
        "permission": "megengedett, hogy (",
        "obligation": "kötelező, hogy (",
    },
}


class _Problem(Exception):
    def __init__(self, result: str, code: str, message: str) -> None:
        super().__init__(message)
        self.result = result
        self.code = code


def _fail(code: str, message: str) -> None:
    raise _Problem("fail", code, message)


def _unresolved(code: str, message: str) -> None:
    raise _Problem("unresolved", code, message)


def _combine(op: str, children: list[tuple]) -> tuple:
    """Only the profile's associative/commutative AND/OR rewrites."""
    flattened = []
    for child in children:
        if child[0] == op:
            flattened.extend(child[1])
        else:
            flattened.append(child)
    # Keep multiplicity.  No idempotence, truth-table rewrite, or scope erasure.
    return (op, tuple(sorted(flattened, key=repr)))


def _bound_variable(name: str, environment: tuple[str, ...]) -> tuple:
    if name not in environment:
        _fail("unbound_variable", "A representation variable is not lexically bound.")
    return ("variable", environment[::-1].index(name))


class _SourceParser:
    """Literal recursive descent, independent of the submitted representation."""

    def __init__(self, text: str, language: str) -> None:
        if language not in _TERMINALS:
            _unresolved("unsupported_language", "The finite profile supports only hu and en.")
        if len(text) > _MAX_SOURCE_BYTES or len(text.encode("utf-8")) > _MAX_SOURCE_BYTES:
            _unresolved("source_size_limit", "The source exceeds the maximum size of the bounded controlled grammar.")
        self.text = text
        self.term = _TERMINALS[language]
        self.position = 0
        self.node_count = 0
        self.person_spans: dict[str, list[tuple[int, int]]] = {}
        self.nodes: list[tuple[tuple, int, int]] = []
        # UTF-8 offsets are computed from the exact unnormalised source.
        self.byte_offsets = [0]
        for character in text:
            self.byte_offsets.append(self.byte_offsets[-1] + len(character.encode("utf-8")))

    def _take(self, literal: str) -> bool:
        if self.text.startswith(literal, self.position):
            self.position += len(literal)
            return True
        return False

    def _expect(self, literal: str) -> None:
        if not self._take(literal):
            self._unsupported()

    def _unsupported(self) -> None:
        _unresolved(
            "unsupported_source_grammar",
            "The exact source is outside the controlled grammar at UTF-8 byte "
            f"{self.byte_offsets[self.position]}.",
        )

    def _person(self) -> str:
        for person in _PEOPLE:
            start = self.position
            if self._take(person):
                self.person_spans.setdefault(person, []).append(
                    (self.byte_offsets[start], self.byte_offsets[self.position])
                )
                return person
        self._unsupported()
        raise AssertionError("unreachable")

    def parse(self) -> tuple:
        formula = self._formula(())
        self._expect(".")
        if self.position != len(self.text):
            self._unsupported()
        return formula

    def _formula(self, environment: tuple[str, ...]) -> tuple:
        self.node_count += 1
        if self.node_count > _MAX_NODES:
            _unresolved("source_ast_limit", "The source exceeds the 256-node profile bound.")
        start = self.position
        node = self._body(environment)
        self.nodes.append((node, self.byte_offsets[start], self.byte_offsets[self.position]))
        return node

    def _body(self, environment: tuple[str, ...]) -> tuple:
        term = self.term
        if self._take(term["not"]):
            child = self._formula(environment)
            self._expect(")")
            return ("NOT", child)
        if self._take(term["if"]):
            antecedent = self._formula(environment)
            self._expect(term["then"])
            consequent = self._formula(environment)
            self._expect(")")
            return ("IMPLIES", antecedent, consequent)
        for key, operator in (("forall", "FORALL"), ("exists", "EXISTS")):
            if self._take(term[key]):
                if self.position >= len(self.text) or self.text[self.position] not in _VARIABLES:
                    self._unsupported()
                variable = self.text[self.position]
                self.position += 1
                self._expect(term["domain"])
                people = [self._person()]
                while self._take(", "):
                    people.append(self._person())
                if len(set(people)) != len(people):
                    self._unsupported()
                self._expect(term["body"])
                body = self._formula(environment + (variable,))
                self._expect(")")
                return (operator, tuple(sorted(people)), body)
        for modality in ("permission", "obligation"):
            if self._take(term[modality]):
                body = self._formula(environment)
                self._expect(")")
                return ("CONTEXT", "assertion", modality, None, body)
        if self._take("("):
            left = self._formula(environment)
            if self._take(term["and"]):
                operator = "AND"
            elif self._take(term["or"]):
                operator = "OR"
            else:
                self._unsupported()
            right = self._formula(environment)
            self._expect(")")
            return _combine(operator, [left, right])
        # Variables may replace PERSON only in atom position, never the speaker.
        if self.position < len(self.text) and self.text[self.position] in _VARIABLES:
            name = self.text[self.position]
            self.position += 1
            if name not in environment:
                self._unsupported()
            argument = ("variable", environment[::-1].index(name))
        else:
            person = self._person()
            if self._take(term["quote"]):
                body = self._formula(environment)
                self._expect(")")
                return ("CONTEXT", "quotation", "declarative", person, body)
            argument = ("person", person)
        for predicate in ("approve", "win"):
            if self._take(term[predicate]):
                return ("ATOM", predicate, (("agent", argument),))
        self._unsupported()
        raise AssertionError("unreachable")


def _expanded_atoms(node: tuple) -> int:
    """Count distinct possible ground atoms without Cartesian quantifier expansion.

    Controlled source atoms have one person argument and literal speakers, so
    collecting a variable's finite domain suffices for this resource check.
    Each CONTEXT occurrence has a separate resource scope: equal speakers and
    modalities do not establish identity of two quotation/modal occurrences.
    This conservative cost rule does not rewrite the semantic canonical AST.
    No truth assignment, entailment or independent variant combination occurs.
    """
    atoms: set[tuple] = set()
    context_occurrence = 0

    def visit(current: tuple, domains: tuple, contexts: tuple) -> None:
        nonlocal context_occurrence
        operator = current[0]
        if operator == "ATOM":
            argument = current[2][0][1]
            people = (argument[1],) if argument[0] == "person" else domains[-1 - argument[1]]
            for person in people:
                atoms.add((contexts, current[1], person))
                if len(atoms) > _MAX_ATOMS:
                    _unresolved("expanded_atom_limit", "The source exceeds the 12-atom profile bound.")
        elif operator == "NOT":
            visit(current[1], domains, contexts)
        elif operator in ("AND", "OR"):
            for child in current[1]:
                visit(child, domains, contexts)
        elif operator == "IMPLIES":
            visit(current[1], domains, contexts)
            visit(current[2], domains, contexts)
        elif operator in ("FORALL", "EXISTS"):
            visit(current[2], domains + (current[1],), contexts)
        elif operator == "CONTEXT":
            context_occurrence += 1
            resource_scope = (context_occurrence, *current[1:4])
            visit(current[4], domains, contexts + (resource_scope,))

    visit(node, (), ())
    return len(atoms)


def _index(records: list[dict], key: str) -> dict[str, dict]:
    result = {}
    for record in records:
        identifier = record[key]
        if identifier in result:
            _fail("duplicate_identifier", "A checked identifier is not unique.")
        result[identifier] = record
    return result


class _RepresentationChecker:
    """Canonicalise only a supplied variant's roots and their reachable graph."""

    def __init__(
        self, representation: dict, anchors: list[dict], parser: _SourceParser,
        context_source_ids: set[str],
    ) -> None:
        self.representation = representation
        self.entities = _index(representation["entities"], "entity_id")
        self.domains = _index(representation["domains"], "domain_id")
        self.relations = _index(representation["relations"], "relation_id")
        self.anchors = _index(anchors, "anchor_id")
        self.parser = parser
        self.context_source_ids = context_source_ids
        self.node_count = 0
        self.used_entities: set[str] = set()
        self.used_relations: set[str] = set()
        self.relation_nodes: dict[str, tuple] = {}
        self.used_anchor_ids: set[str] = set()
        self.stack: set[str] = set()
        labels = Counter(
            record["label"] for record in self.entities.values()
            if record["entity_type"] == "person"
        )
        if any(count > 1 for count in labels.values()):
            _unresolved(
                "ambiguous_local_identity",
                "Multiple local person IDs share a label; the source checker cannot select their identity.",
            )

    def _tick(self) -> None:
        self.node_count += 1
        if self.node_count > _MAX_NODES:
            _unresolved("representation_ast_limit", "REF-expanded roots exceed the 256-node profile bound.")

    def _covers(self, anchor_ids: list[str], start: int, end: int) -> bool:
        intervals = []
        local_ids = set()
        for anchor_id in anchor_ids:
            anchor = self.anchors.get(anchor_id)
            if anchor is None:
                _fail("anchor_source_mismatch", "A used anchor does not bind this representation's source.")
            if anchor["source_id"] in self.context_source_ids:
                # Context may supplement a representation.  It cannot supply a
                # missing source token, and this local parser does not verify it.
                continue
            if anchor["source_id"] != self.representation["source_id"]:
                _fail("anchor_source_mismatch", "A used anchor belongs to the other communication.")
            intervals.append((anchor["start_byte"], anchor["end_byte"]))
            local_ids.add(anchor_id)
        cursor = start
        for lower, upper in sorted(intervals):
            if lower > cursor:
                break
            cursor = max(cursor, upper)
            if cursor >= end:
                self.used_anchor_ids.update(local_ids)
                return True
        return False

    def _person(self, entity_id: str) -> str:
        entity = self.entities.get(entity_id)
        if entity is None or entity["entity_type"] != "person":
            _fail("invalid_person_reference", "A controlled role does not resolve to a local person.")
        label = entity["label"]
        if label not in _PEOPLE:
            _unresolved("unsupported_person_label", "The local person label is outside the finite lexical domain.")
        if not any(self._covers(entity["anchor_ids"], start, end)
                   for start, end in self.parser.person_spans.get(label, [])):
            _fail("entity_anchor_mismatch", "A used entity is not anchored to its exact source person token.")
        self.used_entities.add(entity_id)
        return label

    def _context(self, record: dict, body: tuple) -> tuple:
        speaker_id = record["speaker_entity_id"]
        speaker = None if speaker_id is None else self._person(speaker_id)
        context = (record["discourse_type"], record["modality"], speaker)
        if context == _DEFAULT_CONTEXT:
            return body
        self._tick()
        return ("CONTEXT", *context, body)

    def relation(self, relation_id: str) -> tuple:
        if relation_id in self.stack:
            _fail("cyclic_relation_reference", "A REF cycle cannot certify a source mapping.")
        relation = self.relations.get(relation_id)
        if relation is None:
            _fail("unknown_relation_reference", "A root or REF does not resolve locally.")
        self.stack.add(relation_id)
        self.used_relations.add(relation_id)
        # Named relations are closed expressions; a REF never captures a caller's variable.
        body = self.expression(relation["expression"], ())
        node = self._context(relation, body)
        self.stack.remove(relation_id)
        self.relation_nodes[relation_id] = node
        return node

    def expression(self, expression: dict, environment: tuple[str, ...]) -> tuple:
        self._tick()
        operator = expression["op"]
        if operator == "REF":
            return self.relation(expression["relation_id"])
        if operator == "ATOM":
            arguments = expression["arguments"]
            if expression["predicate"] not in ("approve", "win") or len(arguments) != 1 or arguments[0]["role"] != "agent":
                _fail("unsupported_controlled_atom", "The root uses an atom outside the controlled source grammar.")
            value = arguments[0]["value"]
            if set(value) == {"entity_id"}:
                argument = ("person", self._person(value["entity_id"]))
            elif set(value) == {"variable"}:
                argument = _bound_variable(value["variable"], environment)
            else:
                _fail("unsupported_controlled_argument", "A controlled atom requires a person or a bound variable.")
            return ("ATOM", expression["predicate"], (("agent", argument),))
        if operator == "NOT":
            return ("NOT", self.expression(expression["operand"], environment))
        if operator in ("AND", "OR"):
            return _combine(operator, [self.expression(child, environment) for child in expression["operands"]])
        if operator == "IMPLIES":
            return (operator, self.expression(expression["antecedent"], environment),
                    self.expression(expression["consequent"], environment))
        if operator in ("FORALL", "EXISTS"):
            domain = self.domains.get(expression["domain_id"])
            if domain is None:
                _fail("unknown_domain", "A quantified expression has no local finite domain.")
            people = tuple(sorted(self._person(identifier) for identifier in domain["entity_ids"]))
            return (operator, people, self.expression(expression["body"], environment + (expression["variable"],)))
        if operator == "CONTEXT":
            speaker_id = expression["speaker_entity_id"]
            speaker = None if speaker_id is None else self._person(speaker_id)
            return (operator, expression["discourse_type"], expression["modality"], speaker,
                    self.expression(expression["body"], environment))
        _fail("unsupported_expression", "A checked expression is outside the finite representation model.")
        raise AssertionError("unreachable")

    def roots(self, root_ids: list[str], source_node: tuple) -> tuple:
        if not root_ids:
            _fail("missing_communicated_root", "The nonempty controlled source has no communicated root.")
        if len(set(root_ids)) != len(root_ids):
            _fail("duplicate_root", "A variant repeats a communicated root.")
        nodes = [self.relation(identifier) for identifier in root_ids]
        if len(nodes) == 1:
            result = nodes[0]
        else:
            if not any(set(group["relation_ids"]) == set(root_ids) for group in self.representation["groups"]):
                _unresolved("unrecorded_decomposition", "Multiple roots need an explicit relation group for source decomposition.")
            result = _combine("AND", nodes)
        if result != source_node:
            _fail("source_representation_mismatch", "The communicated roots differ from the independently parsed source structure.")
        for relation_id, node in self.relation_nodes.items():
            record = self.relations[relation_id]
            spans = [(start, end) for parsed, start, end in self.parser.nodes if parsed == node]
            # A grouped conjunct may be re-associated across source subtrees.
            # Its complete-source anchor remains an explicit binding for that rewrite.
            if not spans and relation_id in root_ids and len(nodes) > 1:
                spans = [(0, self.parser.byte_offsets[-2])]
            if not any(self._covers(record["anchor_ids"], start, end) for start, end in spans):
                _fail("relation_anchor_mismatch", "A used relation's anchors do not cover its checked source expression.")
        return result


def check_profile_mapping(
    input_doc: dict,
    profile: dict,
    source_texts: dict[str, str],
    side: str,
) -> dict[str, Any]:
    """Check one side without accepting any submitted representation basis.

    ``pass`` requires an exact supported source and matching communicated roots
    in every supplied variant of a nonempty complete family.  Unsupported source
    language, unresolved identity, incomplete families and resource limits return
    ``unresolved``.  A proved mismatch returns ``fail``.  Coverage evidence and
    cross-source correspondence remain separate caller obligations even on pass.
    """
    details: dict[str, Any] = {"side": side, "grammar": "finite_profile_v0", "source_parse": "not_completed"}
    try:
        if side not in ("before", "after"):
            _fail("invalid_side", "The source mapping side must be before or after.")
        if profile.get("profile_id") != _PROFILE_ID or profile.get("version") != "0":
            _unresolved("unsupported_profile", "This checker implements only the preserved finite v0 profile.")
        representation = input_doc["representations"][side]
        source_id = representation["source_id"]
        source = next((item for item in input_doc["sources"] if item["source_id"] == source_id), None)
        if source is None or source["role"] != side or source_id not in source_texts:
            _fail("missing_bound_source", "The representation has no bound source for its declared side.")
        details["source_id"] = source_id
        parser = _SourceParser(source_texts[source_id], source["language"])
        source_node = parser.parse()
        details.update({
            "source_parse": "complete",
            "source_ast_nodes": parser.node_count,
            "expanded_boolean_atoms": _expanded_atoms(source_node),
            "source_structure_sha256": hashlib.sha256(
                json.dumps(source_node, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
        })
        family = input_doc["interpretations"]
        details["family_state"] = family["state"]
        if family["state"] != "complete" or not family["variants"]:
            _unresolved("incomplete_interpretation_family", "Unknown, empty or truncated interpretation families cannot certify a complete source mapping.")
        if len(family["variants"]) > _MAX_VARIANTS:
            _unresolved("variant_limit", "The interpretation family exceeds the 64-variant profile bound.")
        checked = []
        all_entities: set[str] = set()
        all_relations: set[str] = set()
        all_anchors: set[str] = set()
        for variant in family["variants"]:
            checker = _RepresentationChecker(
                representation, input_doc["source_anchors"], parser,
                {item["source_id"] for item in input_doc["sources"] if item["role"] == "context"},
            )
            root_ids = variant[f"{side}_relation_ids"]
            checker.roots(root_ids, source_node)
            checked.append({
                "variant_id": variant["variant_id"],
                "root_relation_ids": sorted(root_ids),
                "expanded_ast_nodes": checker.node_count,
                "checked_relation_ids": sorted(checker.used_relations),
                "checked_entity_ids": sorted(checker.used_entities),
                "checked_anchor_ids": sorted(checker.used_anchor_ids),
            })
            all_entities.update(checker.used_entities)
            all_relations.update(checker.used_relations)
            all_anchors.update(checker.used_anchor_ids)
        details.update({
            "checked_variants": checked,
            "checked_entity_ids": sorted(all_entities),
            "checked_relation_ids": sorted(all_relations),
            "checked_anchor_ids": sorted(all_anchors),
            "source_scope_complete": True,
            "cross_source_identity_checked": False,
            "external_context_checked": False,
        })
        return {"result": "pass", "reason": None, "details": details}
    except _Problem as error:
        details["reason_code"] = error.code
        return {"result": error.result, "reason": f"{error.code}: {error}", "details": details}
    except RecursionError:
        details["reason_code"] = "checker_recursion_limit"
        return {"result": "unresolved", "reason": "checker_recursion_limit: The semantic check could not complete within the runtime recursion bound.", "details": details}
    except (KeyError, IndexError, TypeError, ValueError) as error:
        # A malformed direct caller must not receive a success or an exception
        # that could be mistaken for a completed semantic check.
        details["reason_code"] = "invalid_mapping_input"
        return {"result": "fail", "reason": f"invalid_mapping_input: {type(error).__name__}", "details": details}

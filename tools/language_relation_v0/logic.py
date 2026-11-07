"""Finite, conditional relation algebra for one recorded joint LRM variant.

This module neither interprets source text nor accepts evidence.  The caller
owns those boundaries.  Identities come only from the selected correspondence
records; labels are never an identity rule.  Anonymous atoms may be evaluated
internally, but exported valuations use actual, unambiguous ground-ATOM relation
IDs from the preserved input.  No fixture oracle or case identifier is read.
"""

from __future__ import annotations

from collections import Counter
from itertools import product
from typing import Any, Iterable


_SIDES = ("before", "after")
_DEFAULT_CONTEXT = ("assertion", "declarative", None)
_MAX_NODES = 256
_MAX_ATOMS = 12


class LogicProblem(Exception):
    """An explicit incomplete/unsupported algebraic check, never a PASS."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def _require(condition: bool, code: str, detail: str) -> None:
    if not condition:
        raise LogicProblem(code, detail)


def _index(rows: Iterable[dict], key: str) -> dict[str, dict]:
    result = {}
    for row in rows:
        identifier = row[key]
        _require(identifier not in result, "duplicate_identifier", f"Duplicate {key}: {identifier}")
        result[identifier] = row
    return result


def _combine(operator: str, children: Iterable[tuple]) -> tuple:
    flattened = []
    for child in children:
        if child[0] == operator:
            flattened.extend(child[1])
        else:
            flattened.append(child)
    if not flattened:
        return ("CONST", operator == "AND")
    if len(flattened) == 1:
        return flattened[0]
    # Multiplicity is retained: these are only the declared AC rewrites.
    return (operator, tuple(sorted(flattened, key=repr)))


def _children(node: tuple) -> tuple:
    operator = node[0]
    if operator in ("AND", "OR"):
        return node[1]
    if operator == "NOT":
        return (node[1],)
    if operator == "IMPLIES":
        return (node[1], node[2])
    if operator in ("FORALL", "EXISTS"):
        return (node[2],)
    if operator == "CONTEXT":
        return (node[4],)
    return ()


def _has_context(node: tuple) -> bool:
    return node[0] == "CONTEXT" or any(_has_context(child) for child in _children(node))


def _truth(node: tuple, values: dict[tuple, bool]) -> bool:
    operator = node[0]
    if operator == "CONST":
        return node[1]
    if operator == "ATOM":
        return values[node]
    if operator == "NOT":
        return not _truth(node[1], values)
    if operator == "AND":
        return all(_truth(child, values) for child in node[1])
    if operator == "OR":
        return any(_truth(child, values) for child in node[1])
    if operator == "IMPLIES":
        return not _truth(node[1], values) or _truth(node[2], values)
    raise LogicProblem("unsupported_boolean_context", "A typed communication context is not a plain Boolean assertion.")


def _atoms(node: tuple) -> set[tuple]:
    if node[0] == "ATOM":
        return {node}
    return set().union(*(_atoms(child) for child in _children(node)))


def _difference(before: tuple, after: tuple, path: str = "root") -> tuple[str, str]:
    if before[0] != after[0]:
        return "operator_difference", f"{path}: operator {before[0]} changes to {after[0]}."
    operator = before[0]
    if operator == "ATOM":
        if before[1] != after[1]:
            return "operator_difference", f"{path}: predicate {before[1]} changes to {after[1]}."
        return "role_difference", f"{path}: the complete ordered role/argument tuple differs."
    if operator == "CONTEXT" and before[1:4] != after[1:4]:
        return "operator_difference", f"{path}: discourse, modality or speaker binding differs."
    if operator in ("FORALL", "EXISTS") and before[1] != after[1]:
        return "operator_difference", f"{path}: the explicitly enumerated quantified domain differs."
    first, second = _children(before), _children(after)
    if len(first) != len(second):
        return "operator_difference", f"{path}: the number of {operator} operands differs."
    for index, (left, right) in enumerate(zip(first, second)):
        if left != right:
            return _difference(left, right, f"{path}.{operator}[{index}]")
    return "operator_difference", f"{path}: selected canonical relation structure differs."


class VariantLogic:
    """Evaluate only one supplied joint variant, without creating combinations.

    ``correspondence_ids`` may restrict the variant's mappings to records the
    caller permits for its current claim scope.  Omission uses the variant's
    explicit candidate assumptions; it does not independently verify them.
    """

    def __init__(self, document: dict, profile: dict, variant: dict, *,
                 correspondence_ids: Iterable[str] | None = None) -> None:
        _require(profile.get("profile_id") == "lrm_finite_reference_profile_v0"
                 and profile.get("version") == "0", "unsupported_profile",
                 "The relation algebra implements only the preserved finite v0 profile.")
        self.document = document
        self.variant = variant
        self.entities = {side: _index(document["representations"][side]["entities"], "entity_id")
                         for side in _SIDES}
        self.domains = {side: _index(document["representations"][side]["domains"], "domain_id")
                        for side in _SIDES}
        self.relations = {side: _index(document["representations"][side]["relations"], "relation_id")
                          for side in _SIDES}
        self.groups = {side: _index(document["representations"][side]["groups"], "group_id")
                       for side in _SIDES}
        records = _index(document["correspondence"], "correspondence_id")
        supplied = set(variant["correspondence_ids"])
        selected = supplied if correspondence_ids is None else set(correspondence_ids)
        _require(selected <= supplied and selected <= records.keys(), "unresolved_correspondence",
                 "Selected mappings must belong to this exact joint variant.")
        self.correspondence_ids = tuple(sorted(selected))
        self.entity_keys: dict[str, dict[str, tuple]] = {side: {} for side in _SIDES}
        self.proposition_keys: dict[str, dict[str, tuple]] = {side: {} for side in _SIDES}
        for identifier in self.correspondence_ids:
            row = records[identifier]
            if row["kind"] in ("entity", "event"):
                _require(len(row["before_ids"]) == len(row["after_ids"]) == 1,
                         "ambiguous_entity_correspondence",
                         "Entity/event identity requires one-to-one mappings within a joint variant.")
                left, right = row["before_ids"][0], row["after_ids"][0]
                _require(left in self.entities["before"] and right in self.entities["after"],
                         "unresolved_entity_correspondence", "An identity mapping names an unknown entity.")
                kind = self.entities["before"][left]["entity_type"]
                _require(kind == self.entities["after"][right]["entity_type"]
                         and (row["kind"] != "event" or kind == "event"),
                         "correspondence_type_mismatch", "Corresponding entity/event types differ.")
                key = ("mapped", kind, left, right)
                self._bind_pair(self.entity_keys, left, right, key)
            elif row["kind"] == "relation" and len(row["before_ids"]) == len(row["after_ids"]) == 1:
                left, right = row["before_ids"][0], row["after_ids"][0]
                self._bind_pair(self.proposition_keys, left, right, ("mapped", left, right))
        self._cache: dict[tuple[str, str], tuple[tuple, int]] = {}
        self._uses: dict[tuple[str, str], tuple[set[tuple[str, str]], set[tuple[str, str]]]] = {}
        self._active: set[tuple[str, str]] = set()
        self._alias_rows = sorted(
            [(row["relation_id"], side, row) for side in _SIDES for row in self.relations[side].values()],
            key=lambda item: (item[0], item[1]))
        self._relation_id_counts = Counter(row[0] for row in self._alias_rows)
        self._safe_reachable: dict[str, set[str]] = {}
        self._reachable = {side: self._root_closure(side) for side in _SIDES}
        self._constraints, constraint_cost, _, _ = self._expression(
            "context", {"op": "AND", "operands": variant["context_constraints"]}, ())
        _require(not _has_context(self._constraints), "unsupported_context_constraints",
                 "Typed context constraints require a separate supported interpretation rule.")
        root_nodes = {}
        source_cost = constraint_cost
        for side in _SIDES:
            nodes = []
            for identifier in sorted(variant[f"{side}_relation_ids"]):
                node, cost = self._relation(side, identifier)
                nodes.append(node)
                source_cost += cost
            root_nodes[side] = _combine("AND", nodes)
        _require(source_cost <= _MAX_NODES, "joint_ast_limit",
                 "The joint variant exceeds the 256-node expression bound.")
        expanded_cost = [0]
        atoms_count = 0
        for side, node in [*root_nodes.items(), ("context", self._constraints)]:
            grounded = self._ground(node, (), expanded_cost)
            scoped: set[tuple] = set()
            self._resource_atoms(grounded, (), scoped, [0])
            atoms_count += len(scoped)
            _require(atoms_count <= _MAX_ATOMS, "joint_atom_limit",
                     "The joint variant exceeds the 12 expanded-atom bound.")
        self.resources = {"expanded_boolean_atoms": atoms_count,
                          "expanded_ast_nodes": max(source_cost, expanded_cost[0])}
        self._ground_constraints = self._ground(self._constraints)
        self._ensure_context_feasible()

    @staticmethod
    def _bind_pair(index: dict, left: str, right: str, key: tuple) -> None:
        for side, identifier in (("before", left), ("after", right)):
            previous = index[side].get(identifier)
            _require(previous is None or previous == key, "contradictory_correspondence",
                     "A joint variant maps one identity to incompatible counterparts.")
            index[side][identifier] = key

    def _owner(self, collection: dict, side: str, identifier: str, kind: str) -> str:
        owners = [side] if side in _SIDES else [item for item in _SIDES if identifier in collection[item]]
        _require(len(owners) == 1 and identifier in collection[owners[0]],
                 "unresolved_" + kind, f"The {kind} {identifier} does not resolve unambiguously.")
        return owners[0]

    def _entity(self, side: str, identifier: str) -> tuple[tuple, str]:
        owner = self._owner(self.entities, side, identifier, "entity")
        entity = self.entities[owner][identifier]
        return (self.entity_keys[owner].get(identifier, (owner, entity["entity_type"], identifier)), owner)

    def _root_closure(self, side: str) -> set[str]:
        """Retain REF reachability without erasing a selected helper's scope.

        A whole declared root remains a selectable typed expression.  A nested
        helper can be selected independently only through transparent REF/AND
        paths in plain assertion context.  Other ancestors remain a missing
        scope obligation for that helper; selecting the enclosing compound is
        still supported.  Proposition arguments are not asserted roots.
        """
        found: set[str] = set()
        safe_found: set[str] = set()
        visited: set[tuple[str, bool]] = set()
        pending = [(identifier, True) for identifier in self.variant[f"{side}_relation_ids"]]
        while pending:
            identifier, safe = pending.pop()
            if (identifier, safe) in visited:
                continue
            visited.add((identifier, safe))
            _require(identifier in self.relations[side], "unresolved_variant_root",
                     "A conveyed variant root does not resolve.")
            found.add(identifier)
            if safe:
                safe_found.add(identifier)
            relation = self.relations[side][identifier]
            plain = (relation["discourse_type"], relation["modality"], relation["speaker_entity_id"]) == _DEFAULT_CONTEXT
            expressions = [(relation["expression"], safe and plain)]
            while expressions:
                node, safe = expressions.pop()
                operator = node["op"]
                if operator == "REF":
                    pending.append((node["relation_id"], safe))
                elif operator == "NOT":
                    expressions.append((node["operand"], False))
                elif operator in ("AND", "OR"):
                    expressions.extend((child, safe and operator == "AND") for child in node["operands"])
                elif operator == "IMPLIES":
                    expressions.extend(((node["antecedent"], False), (node["consequent"], False)))
                elif operator in ("FORALL", "EXISTS", "CONTEXT"):
                    expressions.append((node["body"], False))
        self._safe_reachable[side] = safe_found
        return found

    def selected(self, side: str, target: dict) -> dict[str, list[str]]:
        _require(side in _SIDES, "invalid_side", "A target side must be before or after.")
        requested = set()
        for identifier in target[f"{side}_ids"]:
            if identifier in self.groups[side]:
                requested.update(self.groups[side][identifier]["relation_ids"])
            else:
                _require(identifier in self.relations[side], "unresolved_target", "A target selection does not resolve.")
                requested.add(identifier)
        selected = requested & self._reachable[side]
        return {"requested": sorted(requested), "selected": sorted(selected),
                "missing": sorted(requested - selected), "reachable": sorted(self._reachable[side]),
                "embedded_only": sorted(selected - self._safe_reachable[side]),
                "safe_reachable": sorted(self._safe_reachable[side])}

    def _relation(self, side: str, identifier: str) -> tuple[tuple, int]:
        owner = self._owner(self.relations, side, identifier, "relation")
        key = (owner, identifier)
        if key in self._cache:
            return self._cache[key]
        _require(key not in self._active, "cyclic_relation_reference", "A relation/proposition cycle cannot be evaluated.")
        _require(len(self._active) < _MAX_NODES, "relation_depth_limit", "A relation chain exceeds the finite profile bound.")
        self._active.add(key)
        try:
            row = self.relations[owner][identifier]
            node, cost, entities, propositions = self._expression(owner, row["expression"], ())
            node, extra, speaker = self._wrap_context(owner, row, node, omit_default=True)
            if speaker is not None:
                entities.add(speaker)
            cost += extra
            _require(cost <= _MAX_NODES, "expression_limit", "A REF-expanded relation exceeds the expression bound.")
            self._cache[key] = (node, cost)
            self._uses[key] = (entities, propositions)
            return node, cost
        finally:
            self._active.remove(key)

    def _wrap_context(self, side: str, row: dict, body: tuple, *, omit_default: bool = False) -> tuple:
        speaker_id = row["speaker_entity_id"]
        speaker, used = None, None
        if speaker_id is not None:
            speaker, owner = self._entity(side, speaker_id)
            used = (owner, speaker_id)
        context = (row["discourse_type"], row["modality"], speaker)
        if omit_default and context == _DEFAULT_CONTEXT:
            return body, 0, used
        return ("CONTEXT", *context, body), 1, used

    def _expression(self, side: str, expression: dict, environment: tuple[str, ...],
                    depth: int = 0) -> tuple[tuple, int, set, set]:
        _require(depth < 70, "expression_depth_limit", "The expression nesting bound was exceeded.")
        operator = expression["op"]
        entities: set[tuple[str, str]] = set()
        propositions: set[tuple[str, str]] = set()
        if operator == "REF":
            identifier = expression["relation_id"]
            owner = self._owner(self.relations, side, identifier, "relation")
            node, cost = self._relation(owner, identifier)
            used_entities, used_propositions = self._uses[(owner, identifier)]
            return node, cost + 1, set(used_entities), set(used_propositions)
        if operator == "ATOM":
            arguments = []
            cost = 1
            for argument in expression["arguments"]:
                value = argument["value"]
                if "entity_id" in value:
                    key, owner = self._entity(side, value["entity_id"])
                    entities.add((owner, value["entity_id"]))
                    term = ("ENTITY", key)
                elif "variable" in value:
                    name = value["variable"]
                    _require(name in environment, "unbound_variable", "A variable lacks its lexical quantifier.")
                    term = ("VAR", environment[::-1].index(name))
                else:
                    identifier = value["relation_id"]
                    owner = self._owner(self.relations, side, identifier, "proposition")
                    body, extra = self._relation(owner, identifier)
                    key = self.proposition_keys[owner].get(identifier, (owner, identifier))
                    term = ("PROPOSITION", key, body)
                    used_entities, used_propositions = self._uses[(owner, identifier)]
                    entities.update(used_entities)
                    propositions.update(used_propositions)
                    propositions.add((owner, identifier))
                    cost += extra
                arguments.append((argument["role"], term))
            return ("ATOM", expression["predicate"], tuple(arguments)), cost, entities, propositions
        child_environment = environment
        domain = None
        if operator in ("FORALL", "EXISTS"):
            owner = self._owner(self.domains, side, expression["domain_id"], "domain")
            members = []
            for identifier in self.domains[owner][expression["domain_id"]]["entity_ids"]:
                key, entity_owner = self._entity(owner, identifier)
                members.append(key)
                entities.add((entity_owner, identifier))
            domain = tuple(sorted(members, key=repr))
            child_environment += (expression["variable"],)
        if operator in ("FORALL", "EXISTS", "CONTEXT"):
            raw_children = [expression["body"]]
        elif operator == "NOT":
            raw_children = [expression["operand"]]
        elif operator in ("AND", "OR"):
            raw_children = expression["operands"]
        elif operator == "IMPLIES":
            raw_children = [expression["antecedent"], expression["consequent"]]
        else:
            raise LogicProblem("unsupported_operator", f"Unsupported operator: {operator}")
        children = []
        cost = 1
        for child in raw_children:
            node, extra, child_entities, child_propositions = self._expression(side, child, child_environment, depth + 1)
            children.append(node)
            cost += extra
            entities.update(child_entities)
            propositions.update(child_propositions)
            _require(cost <= _MAX_NODES, "expression_limit", "The expanded expression exceeds the 256-node bound.")
        if operator in ("AND", "OR"):
            node = _combine(operator, children)
        elif operator in ("FORALL", "EXISTS"):
            node = (operator, domain, children[0])
        elif operator == "CONTEXT":
            node, _, speaker = self._wrap_context(side, expression, children[0])
            if speaker is not None:
                entities.add(speaker)
        else:
            node = (operator, *children)
        return node, cost, entities, propositions

    def relation(self, side: str, identifier: str) -> tuple:
        return self._relation(side, identifier)[0]

    def roots(self, side: str, identifiers: Iterable[str]) -> tuple:
        return _combine("AND", [self.relation(side, identifier) for identifier in sorted(set(identifiers))])

    def signature(self, side: str, identifiers: Iterable[str]) -> tuple:
        """Canonical structural signature, suitable for a family's answer set."""
        return self.roots(side, identifiers)

    def _ground(self, node: tuple, environment: tuple = (), budget: list[int] | None = None) -> tuple:
        if budget is None:
            budget = [0]
        budget[0] += 1
        _require(budget[0] <= _MAX_NODES, "expanded_ast_limit",
                 "Finite quantifier expansion exceeds the 256-node profile bound.")
        operator = node[0]
        if operator == "ATOM":
            arguments = []
            for role, value in node[2]:
                if value[0] == "VAR":
                    _require(value[1] < len(environment), "unbound_variable", "A ground evaluation has a free variable.")
                    value = ("ENTITY", environment[-1 - value[1]])
                arguments.append((role, value))
            return ("ATOM", node[1], tuple(arguments))
        if operator == "CONST":
            return node
        if operator in ("FORALL", "EXISTS"):
            return _combine("AND" if operator == "FORALL" else "OR",
                            [self._ground(node[2], environment + (member,), budget) for member in node[1]])
        grounded = [self._ground(child, environment, budget) for child in _children(node)]
        if operator in ("AND", "OR"):
            return _combine(operator, grounded)
        if operator == "CONTEXT":
            return (operator, *node[1:4], grounded[0])
        return (operator, *grounded)

    def _resource_atoms(self, node: tuple, scope: tuple, found: set, occurrences: list[int]) -> None:
        if node[0] == "ATOM":
            found.add((scope, node))
            _require(len(found) <= _MAX_ATOMS, "expanded_atom_limit", "A side exceeds the 12 expanded-atom bound.")
            return
        if node[0] == "CONTEXT":
            occurrences[0] += 1
            scope += ((occurrences[0], *node[1:4]),)
        for child in _children(node):
            self._resource_atoms(child, scope, found, occurrences)

    def _configurations(self, nodes: Iterable[tuple]) -> Iterable[dict[tuple, bool]]:
        roots = list(nodes)
        _require(not any(_has_context(node) for node in roots), "unsupported_boolean_context",
                 "Boolean equivalence/entailment is confined to plain assertion/declarative conditions.")
        atoms = _atoms(self._ground_constraints)
        for node in roots:
            atoms.update(_atoms(node))
        _require(len(atoms) <= _MAX_ATOMS, "expanded_atom_limit", "A Boolean check exceeds the 12-atom bound.")
        keys = sorted(atoms, key=repr)
        for values in product((False, True), repeat=len(keys)):
            configuration = dict(zip(keys, values))
            if _truth(self._ground_constraints, configuration):
                yield configuration

    def _ensure_context_feasible(self) -> None:
        _require(next(iter(self._configurations([])), None) is not None, "incompatible_context",
                 "The recorded joint context constraints admit no common configuration.")

    def _alias(self, side: str, row: dict) -> tuple | None:
        expression = row["expression"]
        if expression["op"] != "ATOM" or any("variable" in item["value"] for item in expression["arguments"]):
            return None
        if (row["discourse_type"], row["modality"], row["speaker_entity_id"]) != _DEFAULT_CONTEXT:
            return None
        try:
            return self._ground(self.relation(side, row["relation_id"]))
        except LogicProblem:
            return None

    def _valuation(self, configuration: dict[tuple, bool] | None) -> tuple[list[dict] | None, bool]:
        if configuration is None:
            return None, False
        aliases = {}
        for identifier, side, row in self._alias_rows:
            if self._relation_id_counts[identifier] != 1:
                continue
            key = self._alias(side, row)
            if key in configuration and key not in aliases:
                aliases[key] = identifier
            if len(aliases) == len(configuration):
                break
        if set(aliases) != set(configuration):
            return None, False
        return sorted([{"atom_id": aliases[key], "value": value}
                       for key, value in configuration.items()], key=lambda row: row["atom_id"]), True

    def _missing_identity(self, before_ids: Iterable[str], after_ids: Iterable[str]) -> list[dict]:
        missing = []
        used_entities, used_propositions = set(), set()
        for side, identifiers in (("before", before_ids), ("after", after_ids)):
            for identifier in identifiers:
                self.relation(side, identifier)
                entities, propositions = self._uses[(side, identifier)]
                used_entities.update(entities)
                used_propositions.update(propositions)
        for side, identifier in sorted(used_entities):
            if identifier not in self.entity_keys[side]:
                missing.append({"side": side, "entity_id": identifier})
        for side, identifier in sorted(used_propositions):
            if identifier not in self.proposition_keys[side]:
                missing.append({"side": side, "relation_id": identifier})
        return missing

    def missing_identity(self, before_ids: Iterable[str], after_ids: Iterable[str]) -> list[dict]:
        """Return unbound participant/proposition identities without truth search.

        Ordinary REF aliases contribute the identities in their resolved body;
        proposition-valued arguments additionally require the named proposition
        identity itself.  The caller decides whether an unmatched identity is a
        plausible unresolved counterpart or a demonstrably distinct participant.
        """
        return self._missing_identity(before_ids, after_ids)

    def compare(self, before_ids: Iterable[str], after_ids: Iterable[str], *,
                boolean_equivalence: bool = False) -> dict[str, Any]:
        before_ids, after_ids = tuple(before_ids), tuple(after_ids)
        before, after = self.roots("before", before_ids), self.roots("after", after_ids)
        equal = before == after
        difference_kind, detail = (None, "Selected relations agree under the permitted structural rewrites.")
        if not equal:
            difference_kind, detail = _difference(before, after)
        result = {"structural_equal": equal, "equivalent": equal, "counterexample": None,
                  "aliases_complete": False, "before_value": None, "after_value": None,
                  "difference_kind": difference_kind, "detail": detail,
                  "missing_identity": self.missing_identity(before_ids, after_ids),
                  "resources": dict(self.resources), "boolean_supported": False}
        if _has_context(before) or _has_context(after):
            result["detail"] += " Typed communication contexts retain structural semantics."
            return result
        grounded_before, grounded_after = self._ground(before), self._ground(after)
        result["boolean_supported"] = True
        counterexample = None
        for configuration in self._configurations([grounded_before, grounded_after]):
            left, right = _truth(grounded_before, configuration), _truth(grounded_after, configuration)
            if left != right:
                counterexample = configuration
                result.update(before_value=left, after_value=right)
                break
        if boolean_equivalence:
            result["equivalent"] = counterexample is None
            if result["equivalent"]:
                result.update(difference_kind=None, detail="The selected plain conditions agree in every admissible common configuration.")
        if counterexample is not None:
            valuation, complete = self._valuation(counterexample)
            result.update(counterexample=valuation, aliases_complete=complete)
            if complete:
                result["difference_kind"] = "configuration"
                result["detail"] += " A complete named-ground-atom valuation distinguishes the selected conditions."
            else:
                result["detail"] += " The Boolean difference has no complete unambiguous ground-ATOM alias set; retain the structural difference witness."
        return result

    def entailment(self, premise_ids: Iterable[str], after_id: str) -> dict[str, Any]:
        premises = self.roots("before", premise_ids)
        conclusion = self.relation("after", after_id)
        _require(not _has_context(premises) and not _has_context(conclusion), "unsupported_entailment_context",
                 "A quoted, modal or observed-event claim cannot become a plain asserted consequence.")
        premises, conclusion = self._ground(premises), self._ground(conclusion)
        satisfiable, counterexample = False, None
        for configuration in self._configurations([premises, conclusion]):
            if _truth(premises, configuration):
                satisfiable = True
                if not _truth(conclusion, configuration):
                    counterexample = configuration
                    break
        entailed = satisfiable and counterexample is None
        valuation, complete = self._valuation(counterexample)
        detail = ("The satisfiable original premises entail the selected addition in every admissible common configuration."
                  if entailed else "The original premises do not establish the selected addition.")
        if not satisfiable:
            detail = "The original premises have no common satisfying configuration; conflict does not establish arbitrary additions."
        return {"entailed": entailed, "premises_satisfiable": satisfiable,
                "counterexample": valuation, "aliases_complete": complete, "detail": detail,
                "resources": dict(self.resources)}

    def check_valuation(self, before_ids: Iterable[str], after_ids: Iterable[str], valuation: list[dict]) -> dict:
        """Re-evaluate a complete serialized common configuration against its IDs."""
        before, after = self._ground(self.roots("before", before_ids)), self._ground(self.roots("after", after_ids))
        _require(not _has_context(before) and not _has_context(after), "unsupported_boolean_context",
                 "A valuation cannot erase typed communication contexts.")
        keys = _atoms(before) | _atoms(after) | _atoms(self._ground_constraints)
        values, seen = {}, set()
        for item in valuation:
            identifier = item["atom_id"]
            _require(identifier not in seen and type(item["value"]) is bool,
                     "invalid_valuation", "A valuation repeats an atom or has a non-Boolean value.")
            seen.add(identifier)
            _require(self._relation_id_counts[identifier] == 1, "ambiguous_valuation_atom",
                     "A valuation atom must resolve to exactly one named ground relation.")
            owner = self._owner(self.relations, "context", identifier, "valuation_atom")
            key = self._alias(owner, self.relations[owner][identifier])
            _require(key is not None and key in keys, "invalid_valuation_atom",
                     "A valuation names an irrelevant or non-ground-ATOM relation.")
            _require(key not in values or values[key] == item["value"], "conflicting_valuation",
                     "Corresponding atom aliases receive incompatible values.")
            values[key] = item["value"]
        _require(set(values) == keys, "incomplete_valuation", "The valuation leaves a required ground atom unassigned.")
        _require(_truth(self._ground_constraints, values), "incompatible_context",
                 "The valuation violates the recorded common context constraints.")
        left, right = _truth(before, values), _truth(after, values)
        return {"before_value": left, "after_value": right, "different": left != right}

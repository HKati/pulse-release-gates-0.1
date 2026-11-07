"""Typed reference closure; no source interpretation or relation comparison."""

from __future__ import annotations

from .io import InputError, unique_index


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InputError(message)


def _references(ids: list[str], index: dict, label: str) -> None:
    missing = set(ids) - index.keys()
    _require(not missing, f"unresolved {label}: {sorted(missing)}")


def _expression(node: dict, entities: dict, domains: dict, relations: dict,
                signatures: dict, variables: dict, dependencies: set,
                *, depth: int = 0) -> None:
    _require(depth < 70, "expression depth limit exceeded")
    op = node["op"]
    if op == "ATOM":
        predicate = node["predicate"]
        _require(predicate in signatures, f"unknown predicate: {predicate}")
        roles = signatures[predicate]["roles"]
        _require([x["role"] for x in node["arguments"]] == [x["role"] for x in roles],
                 f"wrong ordered role signature or role multiplicity: {predicate}")
        for argument, signature in zip(node["arguments"], roles):
            value = argument["value"]
            if "entity_id" in value:
                key = value["entity_id"]
                _require(key in entities, f"unresolved entity: {key}")
                types = {entities[key]["entity_type"]}
            elif "relation_id" in value:
                key = value["relation_id"]
                _require(key in relations, f"unresolved proposition relation: {key}")
                dependencies.add(key)
                types = {"proposition"}
            else:
                key = value["variable"]
                _require(key in variables, f"unbound variable: {key}")
                types = variables[key]
            _require(types <= set(signature["types"]),
                     f"wrong argument type for {predicate}.{signature['role']}")
        return
    if op == "REF":
        key = node["relation_id"]
        _require(key in relations, f"unresolved REF: {key}")
        dependencies.add(key)
        return
    nested = variables
    if op in ("FORALL", "EXISTS"):
        key = node["domain_id"]
        _require(key in domains, f"unresolved domain: {key}")
        nested = dict(variables)
        nested[node["variable"]] = {
            entities[item]["entity_type"] for item in domains[key]["entity_ids"]}
    if op == "CONTEXT" and node["speaker_entity_id"] is not None:
        key = node["speaker_entity_id"]
        _require(key in entities, f"unresolved context speaker: {key}")
        _require(entities[key]["entity_type"] == "person", "context speaker must be person")
    if op in ("FORALL", "EXISTS", "CONTEXT"):
        children = [node["body"]]
    elif op == "NOT":
        children = [node["operand"]]
    elif op in ("AND", "OR"):
        children = node["operands"]
    else:
        children = [node["antecedent"], node["consequent"]]
    for child in children:
        _expression(child, entities, domains, relations, signatures, nested,
                    dependencies, depth=depth + 1)


def _acyclic(graph: dict[str, set[str]]) -> None:
    # Iterative DFS: an input cannot exhaust the Python stack through REF chains.
    finished: set[str] = set()
    active: set[str] = set()
    for start in graph:
        if start in finished:
            continue
        pending = [(start, False)]
        while pending:
            node, leaving = pending.pop()
            if leaving:
                active.remove(node)
                finished.add(node)
                continue
            if node in finished:
                continue
            _require(node not in active, f"cyclic REF/proposition graph at {node}")
            active.add(node)
            pending.append((node, True))
            pending.extend((child, False) for child in sorted(graph[node], reverse=True))


def validate_structure(document: dict, profile: dict) -> None:
    """Validate internal IDs and types; unresolved external evidence stays explicit."""
    sources = unique_index(document["sources"], "source_id")
    for side in ("before", "after"):
        rows = [row for row in sources.values() if row["role"] == side]
        _require(len(rows) == 1, f"exactly one {side} source is required")
        _require(document["representations"][side]["source_id"] == rows[0]["source_id"],
                 f"{side} representation names the wrong source")
    context = {key for key, row in sources.items() if row["role"] == "context"}
    anchors = unique_index(document["source_anchors"], "anchor_id")
    _references([row["source_id"] for row in anchors.values()], sources, "anchor source")
    signatures = unique_index(profile["predicate_signatures"], "predicate")
    representations = document["representations"]
    _require(representations["before"]["representation_id"] !=
             representations["after"]["representation_id"], "duplicate representation_id")
    indices = {}
    for side, representation in representations.items():
        entities = unique_index(representation["entities"], "entity_id")
        domains = unique_index(representation["domains"], "domain_id")
        relations = unique_index(representation["relations"], "relation_id")
        groups = unique_index(representation["groups"], "group_id")
        _require(not (relations.keys() & groups.keys()), "relation/group ID collision")
        indices[side] = (entities, domains, relations, groups)
        for domain in domains.values():
            _references(domain["entity_ids"], entities, "domain member")
        for group in groups.values():
            _references(group["relation_ids"], relations, "group member")
        for row in list(entities.values()) + list(relations.values()):
            _references(row["anchor_ids"], anchors, "source anchor")
            _require(all(anchors[key]["source_id"] in context | {representation["source_id"]}
                         for key in row["anchor_ids"]), "anchor belongs to the other side")
        graph = {}
        for key, relation in relations.items():
            speaker = relation["speaker_entity_id"]
            if speaker is not None:
                _require(speaker in entities, f"unresolved relation speaker: {speaker}")
                _require(entities[speaker]["entity_type"] == "person", "speaker must be person")
            dependencies: set[str] = set()
            _expression(relation["expression"], entities, domains, relations,
                        signatures, {}, dependencies)
            graph[key] = dependencies
        _acyclic(graph)

    correspondences = unique_index(document["correspondence"], "correspondence_id")
    profile_rules = {row["rule_id"] for row in profile["evaluation_rules"]}
    for item in correspondences.values():
        _references(item["anchor_ids"], anchors, "correspondence anchor")
        for side in ("before", "after"):
            entities, _, relations, groups = indices[side]
            kind = item["kind"]
            allowed = entities if kind in ("entity", "event") else relations
            if kind == "relation_group":
                # Explicit decomposition may name both groups and their relations.
                allowed = {**relations, **groups}
            _references(item[f"{side}_ids"], allowed, f"{side} correspondence")
            if kind == "event":
                _require(all(entities[key]["entity_type"] == "event"
                             for key in item[f"{side}_ids"]), "event mapping uses non-event entity")
        if item["basis"] == "profile_rule":
            _require(item["rule_or_reference_id"] in profile_rules,
                     "unresolved profile correspondence rule")

    variants = unique_index(document["interpretations"]["variants"], "variant_id")
    for item in variants.values():
        for side in ("before", "after"):
            _references(item[f"{side}_relation_ids"], indices[side][2], f"{side} variant root")
        _references(item["correspondence_ids"], correspondences, "variant correspondence")

    targets = unique_index(document["measurement_request"]["targets"], "target_id")
    obligations = unique_index(document["coverage_obligations"], "obligation_id")
    for item in targets.values():
        _references(item["required_obligation_ids"], obligations, "target obligation")
        _require(all(obligations[key]["target_id"] == item["target_id"]
                     for key in item["required_obligation_ids"]), "obligation belongs to another target")
        _references(item["context_source_ids"], {key: sources[key] for key in context},
                    "target context source")
        for side in ("before", "after"):
            _, _, relations, groups = indices[side]
            allowed = relations if item["granularity"] == "relation" else {**relations, **groups}
            _references(item[f"{side}_ids"], allowed, f"{side} target")
    for item in obligations.values():
        _require(item["target_id"] in targets, "unresolved coverage target")
        _references(item["source_ids"], sources, "coverage source")
        roles = {sources[key]["role"] for key in item["source_ids"]}
        allowed = ({"before", "after", "context"} if item["side"] == "both"
                   else {item["side"], "context"})
        _require(roles <= allowed, "coverage source scope contradicts its side")
    processing = document["processing_binding"]
    if processing is not None:
        for side in ("before", "after"):
            _require(processing[f"{side}_source_id"] == representations[side]["source_id"],
                     f"processing binding names another {side} source")
        _references(processing["context_source_ids"], {key: sources[key] for key in context},
                    "processing context source")
        relevant = {key for target in targets.values() for key in target["context_source_ids"]}
        relevant |= {key for row in obligations.values()
                     for key in row["source_ids"] if key in context}
        _require(relevant <= set(processing["context_source_ids"]),
                 "processing binding omits a required context source")

    extras = [node for item in variants.values() for node in item["context_constraints"]]
    model = document["impact_model"]
    if model is not None:
        claims = unique_index(model["claims"], "claim_id")
        unique_index(model["rules"], "rule_id")
        _references(model["withdrawn_claim_ids"] + model["target_claim_ids"], claims, "impact claim")
        for claim in claims.values():
            _references(claim["source_anchor_ids"], anchors, "claim source anchor")
            extras.append(claim["expression"])
        for rule in model["rules"]:
            _references(rule["premise_claim_ids"] + [rule["conclusion_claim_id"]], claims,
                        "support-rule claim")
    if extras:
        # Unqualified context/model expressions need unambiguous IDs across sides.
        merged = []
        for number in range(3):
            before, after = indices["before"][number], indices["after"][number]
            _require(not before.keys() & after.keys(), "ambiguous cross-side expression ID")
            merged.append({**before, **after})
        for node in extras:
            _expression(node, *merged, signatures, {}, set())

"""Strict validator for the JSON Schema subset used by this draft.

This is not a general Draft 2020-12 implementation. Unsupported keywords fail.
No schema resolution, network requests, coercion, defaults or mutations occur.
"""
from __future__ import annotations

import re


class SchemaError(ValueError):
    pass


_KEYWORDS = {
    "$schema", "$defs", "$ref", "$comment", "title", "description",
    "type", "const", "enum", "properties", "required",
    "additionalProperties", "oneOf", "pattern", "minLength",
}


def validate(instance, root_schema):
    def visit(value, schema, path):
        unsupported = set(schema) - _KEYWORDS
        if unsupported:
            raise SchemaError(f"{path}: unsupported keywords {sorted(unsupported)}")
        if "$ref" in schema:
            ref = schema["$ref"]
            if not ref.startswith("#/"):
                raise SchemaError(f"{path}: external schema reference forbidden")
            target = root_schema
            for part in ref[2:].split("/"):
                target = target[part.replace("~1", "/").replace("~0", "~")]
            visit(value, target, path)
        if "oneOf" in schema:
            matches = 0
            for choice in schema["oneOf"]:
                try:
                    visit(value, choice, path)
                except SchemaError:
                    continue
                matches += 1
            if matches != 1:
                raise SchemaError(f"{path}: expected exactly one variant, got {matches}")
        expected = schema.get("type")
        types = {"object": dict, "string": str}
        if expected is not None:
            if expected not in types:
                raise SchemaError(f"{path}: unsupported type {expected}")
            if type(value) is not types[expected]:
                raise SchemaError(f"{path}: expected {expected}")
        if "const" in schema and value != schema["const"]:
            raise SchemaError(f"{path}: constant mismatch")
        if "enum" in schema and value not in schema["enum"]:
            raise SchemaError(f"{path}: value outside enum")
        if isinstance(value, str):
            if len(value) < schema.get("minLength", 0):
                raise SchemaError(f"{path}: string too short")
            if "pattern" in schema and re.search(schema["pattern"], value) is None:
                raise SchemaError(f"{path}: pattern mismatch")
        if isinstance(value, dict):
            missing = set(schema.get("required", ())) - set(value)
            if missing:
                raise SchemaError(f"{path}: missing {sorted(missing)}")
            properties = schema.get("properties", {})
            if schema.get("additionalProperties") is False:
                extra = set(value) - set(properties)
                if extra:
                    raise SchemaError(f"{path}: extra {sorted(extra)}")
            for key, child in properties.items():
                if key in value:
                    visit(value[key], child, f"{path}/{key}")

    visit(instance, root_schema, "$")

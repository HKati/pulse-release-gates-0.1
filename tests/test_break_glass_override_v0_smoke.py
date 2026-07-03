import json
from pathlib import Path

from jsonschema import Draft202012Validator


SCHEMA_PATH = Path("schemas/break_glass_override_v0.schema.json")


def test_break_glass_override_schema_is_draft_2020_12_valid() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    Draft202012Validator.check_schema(schema)

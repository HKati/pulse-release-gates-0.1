import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.epf.epf_hazard_field_spec import (
    FieldSpecArtifactV0,
    FIELD_SPEC_SCHEMA_V0,
    maybe_load_field_spec,
)


def test_field_spec_normalizes_features_and_deny_keys():
    fs = FieldSpecArtifactV0(
        features=[" metrics.RDSI ", "metrics.RDSI", "external.fail_rate.", "", "   "],
        deny_keys=[" secrets.api_key ", "secrets.api_key", "raw_prompt."],
        notes="demo",
    )
    assert fs.schema == FIELD_SPEC_SCHEMA_V0
    assert fs.features == ["external.fail_rate", "metrics.RDSI"]
    assert fs.deny_keys == ["raw_prompt", "secrets.api_key"]
    assert isinstance(fs.created_utc, str) and fs.created_utc


def test_field_spec_roundtrip(tmp_path):
    p = tmp_path / "field_spec.json"
    fs = FieldSpecArtifactV0(
        features=["metrics.RDSI", "external.fail_rate"],
        deny_keys=["pii"],
        notes="x",
    )
    fs.save_json(p)

    loaded = maybe_load_field_spec(p)
    assert loaded is not None
    assert loaded.schema == FIELD_SPEC_SCHEMA_V0
    assert loaded.features == ["external.fail_rate", "metrics.RDSI"]
    assert loaded.deny_keys == ["pii"]
    assert loaded.notes == "x"


def test_maybe_load_field_spec_missing_is_none(tmp_path):
    p = tmp_path / "missing.json"
    assert maybe_load_field_spec(p) is None


def test_to_snapshot_policy_and_feature_allowlist():
    fs = FieldSpecArtifactV0(features=["a.b", "c"], deny_keys=["x"])
    allowed, deny = fs.to_snapshot_policy()
    assert allowed == ["a.b", "c"]
    assert deny == ["x"]
    assert fs.to_feature_allowlist() == ["a.b", "c"]

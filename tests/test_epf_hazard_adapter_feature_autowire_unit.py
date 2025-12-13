import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.epf.epf_hazard_adapter import _select_feature_keys_for_autowire


def test_select_feature_keys_respects_empty_allowlist_as_deny_all():
    scaler_keys = ["a", "b", "c"]
    current = {"a": 1.0, "b": 2.0}
    reference = {"a": 0.0}

    # Explicit empty allowlist must behave as "deny all".
    assert _select_feature_keys_for_autowire(
        scaler_keys=scaler_keys,
        current_snapshot=current,
        reference_snapshot=reference,
        allowlist=[],
    ) == []

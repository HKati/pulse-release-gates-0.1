import math

from PULSE_safe_pack_v0.epf.epf_hazard_features import RobustScaler


def test_robust_scaler_constant_values_no_blowup():
    vals = [0.92] * 10
    s = RobustScaler.fit(vals)
    assert s.mad > 0.0
    # Reference offset should not explode into absurd z-space values
    dz = abs(s.z(1.0) - s.z(0.92))
    assert dz < 1_000.0


def test_robust_scaler_binary_heavy_no_blowup():
    # Mostly-constant binary features often yield MAD==0 with plain MAD.
    vals = [1.0, 1.0, 1.0, 0.0]
    s = RobustScaler.fit(vals)
    assert s.mad > 0.0
    dz = abs(s.z(1.0) - s.z(0.0))
    assert dz < 100.0

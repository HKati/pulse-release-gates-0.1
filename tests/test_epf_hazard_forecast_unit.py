import math
import tempfile
import json
import pathlib
import unittest

from PULSE_safe_pack_v0.epf.epf_hazard_forecast import (
    compute_T,
    estimate_S,
    estimate_D,
    classify_zone,
    HazardConfig,
    DEFAULT_WARN_THRESHOLD,
    DEFAULT_CRIT_THRESHOLD,
    MIN_CALIBRATION_SAMPLES,
    _load_calibrated_thresholds,
)


class TestComputeT(unittest.TestCase):
    def test_T_zero_when_snapshots_equal(self):
        current = {"a": 1.0, "b": 2.0}
        reference = {"a": 1.0, "b": 2.0}
        T = compute_T(current, reference)
        self.assertAlmostEqual(T, 0.0, places=6)

    def test_T_simple_euclidean_distance(self):
        current = {"a": 1.0, "b": 2.0}
        reference = {"a": 0.0, "b": 0.0}
        T = compute_T(current, reference)
        self.assertAlmostEqual(T, math.sqrt(5.0), places=6)


class TestEstimateS(unittest.TestCase):
    def test_S_uses_RDSI_when_present(self):
        S = estimate_S({"RDSI": 0.8})
        self.assertAlmostEqual(S, 0.8, places=6)

    def test_S_clamps_RDSI_to_one(self):
        S = estimate_S({"RDSI": 1.5})
        self.assertAlmostEqual(S, 1.0, places=6)

    def test_S_clamps_RDSI_to_zero(self):
        S = estimate_S({"RDSI": -0.5})
        self.assertAlmostEqual(S, 0.0, places=6)

    def test_S_defaults_to_neutral_when_missing(self):
        S = estimate_S({})
        self.assertAlmostEqual(S, 0.5, places=6)


class TestEstimateD(unittest.TestCase):
    def test_D_zero_for_too_short_history(self):
        D = estimate_D([])
        self.assertAlmostEqual(D, 0.0, places=6)
        D = estimate_D([1.0])
        self.assertAlmostEqual(D, 0.0, places=6)

    def test_D_mean_absolute_step(self):
        history_T = [1.0, 2.0, 3.0]
        # diffs = [1.0, 1.0] → mean = 1.0
        D = estimate_D(history_T)
        self.assertAlmostEqual(D, 1.0, places=6)


class TestClassifyZone(unittest.TestCase):
    def setUp(self):
        self.cfg = HazardConfig(
            alpha=1.0,
            beta=1.0,
            warn_threshold=0.3,
            crit_threshold=0.7,
            min_history=3,
        )

    def test_zone_green_below_warn(self):
        zone = classify_zone(0.1, self.cfg)
        self.assertEqual(zone, "GREEN")

    def test_zone_amber_between_warn_and_crit(self):
        zone = classify_zone(0.4, self.cfg)
        self.assertEqual(zone, "AMBER")

    def test_zone_red_above_crit(self):
        zone = classify_zone(0.9, self.cfg)
        self.assertEqual(zone, "RED")


class TestCalibrationLoader(unittest.TestCase):
    def test_loader_falls_back_when_file_missing(self):
        # Point the loader at a non-existent path.
        tmp_dir = pathlib.Path(tempfile.gettempdir())
        missing_path = tmp_dir / "definitely_missing_epf_hazard_thresholds.json"
        warn, crit = _load_calibrated_thresholds(missing_path)
        self.assertAlmostEqual(warn, DEFAULT_WARN_THRESHOLD, places=6)
        self.assertAlmostEqual(crit, DEFAULT_CRIT_THRESHOLD, places=6)

    def test_loader_falls_back_when_invalid_json(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "bad.json"
            path.write_text("{ this is not valid json", encoding="utf-8")
            warn, crit = _load_calibrated_thresholds(path)
            self.assertAlmostEqual(warn, DEFAULT_WARN_THRESHOLD, places=6)
            self.assertAlmostEqual(crit, DEFAULT_CRIT_THRESHOLD, places=6)

    def test_loader_falls_back_when_too_few_samples(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "thresholds.json"
            payload = {
                "global": {
                    "warn_threshold": 0.8,
                    "crit_threshold": 1.2,
                    "stats": {
                        "count": MIN_CALIBRATION_SAMPLES - 1,
                    },
                }
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
            warn, crit = _load_calibrated_thresholds(path)
            self.assertAlmostEqual(warn, DEFAULT_WARN_THRESHOLD, places=6)
            self.assertAlmostEqual(crit, DEFAULT_CRIT_THRESHOLD, places=6)

    def test_loader_uses_calibrated_thresholds_when_enough_samples(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "thresholds.json"
            payload = {
                "global": {
                    "warn_threshold": 0.4,
                    "crit_threshold": 1.1,
                    "stats": {
                        "count": MIN_CALIBRATION_SAMPLES + 5,
                    },
                }
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
            warn, crit = _load_calibrated_thresholds(path)
            self.assertAlmostEqual(warn, 0.4, places=6)
            self.assertAlmostEqual(crit, 1.1, places=6)

    def test_loader_rejects_inverted_thresholds(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "thresholds.json"
            # crit < warn → should be treated as invalid and fall back.
            payload = {
                "global": {
                    "warn_threshold": 1.0,
                    "crit_threshold": 0.5,
                    "stats": {
                        "count": MIN_CALIBRATION_SAMPLES + 5,
                    },
                }
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
            warn, crit = _load_calibrated_thresholds(path)
            self.assertAlmostEqual(warn, DEFAULT_WARN_THRESHOLD, places=6)
            self.assertAlmostEqual(crit, DEFAULT_CRIT_THRESHOLD, places=6)


if __name__ == "__main__":
    unittest.main()

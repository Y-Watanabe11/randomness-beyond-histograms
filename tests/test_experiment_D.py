"""Small deterministic checks for Experiment D; not a physical RNG test."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))
from experiment_D import analyze_one


class ExperimentDTests(unittest.TestCase):
    def test_zero_jitter_identical(self):
        row = analyze_one(0, 0)
        for key in ("raw_bit_lag_agreement", "input_block_exact_match",
                    "sha_bit_lag_agreement", "sha_first_template_accuracy"):
            self.assertEqual(row[key], 1.0)

    def test_five_ps_block_versus_bit(self):
        row = analyze_one(5, 0)
        self.assertGreater(row["raw_bit_lag_agreement"], .8)
        self.assertLess(row["input_block_exact_match"], .1)
        self.assertAlmostEqual(row["sha_diff_input_bit_agreement"], .5, delta=.02)
        self.assertAlmostEqual(row["sha_bit_lag_agreement"],
                               row["sha_bit_lag_predicted_from_block_match"],
                               delta=.02)


if __name__ == "__main__":
    unittest.main()

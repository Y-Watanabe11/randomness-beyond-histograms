"""Lightweight checks for the versioned experiment outputs.

These check published numerical artifacts, not physical entropy or security.
Run: python -m unittest discover -s tests -v
"""
from pathlib import Path
import csv
import unittest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def rows(name):
    with (DATA / name).open(newline="", encoding="utf-8") as fp:
        return list(csv.DictReader(fp))


class PublishedResultsTest(unittest.TestCase):
    def test_same_marginal_histogram(self):
        a, b = rows("experiment_A_results.csv")
        self.assertEqual(a["histogram_sha256"], b["histogram_sha256"])
        self.assertEqual(a["entropy_bits"], b["entropy_bits"])
        self.assertEqual(int(a["total_numbers"]), 74160)
        self.assertEqual(int(b["total_numbers"]), 74160)

    def test_chronological_holdout_predictions(self):
        a, b = rows("experiment_A_results.csv")
        self.assertEqual(float(a["temporal_first_hit_pct"]), 100.0)
        self.assertAlmostEqual(float(b["temporal_first_hit_pct"]), 1.33944624236, places=7)
        self.assertEqual(int(a["discovered_period"]), 3090)
        self.assertEqual(b["discovered_period"], "none")

    def test_jitter_summary(self):
        d = {float(r["sigma_ps"]): r for r in rows("experiments_BC_summary.csv")}
        self.assertEqual(float(d[0.0]["heldout_template_bit_accuracy_mean"]), 1.0)
        self.assertEqual(float(d[0.0]["entropy_conditional_lag32000_mean"]), 0.0)
        self.assertAlmostEqual(float(d[0.5]["heldout_template_bit_accuracy_mean"]), .5351135706, places=7)
        self.assertAlmostEqual(float(d[5.0]["entropy_conditional_lag32000_mean"]), .9998738917, places=7)
        self.assertEqual(int(d[0.0]["replicates"]), 12)


if __name__ == "__main__":
    unittest.main()

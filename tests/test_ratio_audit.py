"""Arithmetic-only sanity checks for the Experiment G ratio audit."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"experiments"))
from audit_ratio_near_periods import RATIOS,best_lag

class RatioAuditTests(unittest.TestCase):
    def test_original_exact_half_period(self):
        r=RATIOS["baseline_4.9505"]
        self.assertAlmostEqual((1000*r)%1,0.5,places=9)
        self.assertAlmostEqual((2000*r)%1,0.0,places=9)

    def test_near_lag_101(self):
        r=RATIOS["baseline_4.9505"]
        self.assertAlmostEqual(101*r,500.0005,places=7)

    def test_every_ratio_has_near_cycle_in_search_range(self):
        for r in RATIOS.values():
            result=best_lag(r,40000)
            self.assertLess(result["distance_to_integer_or_half_cycle"],.00005)

if __name__=="__main__":
    unittest.main()

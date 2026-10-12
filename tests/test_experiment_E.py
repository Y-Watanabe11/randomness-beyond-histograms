"""Regression checks for streaming Experiment E (not physical RNG tests)."""
from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))
from experiment_E import evaluate, features, fit_markov, LAGS, N, TRAIN_CUT, MAX_LAG
from experiments_BC import generate, sha_condition, BASE_SEED


class ExperimentETests(unittest.TestCase):
    def test_features_only_use_strictly_past_observations(self):
        bits = (np.arange(N, dtype=np.int64) % 2).astype(np.uint8)
        at = np.array([MAX_LAG, TRAIN_CUT, TRAIN_CUT+15])
        np.testing.assert_array_equal(
            features(bits, at), np.column_stack([bits[at-l] for l in LAGS]))
        self.assertTrue(all(l > 0 for l in LAGS))

    def test_markov_training_does_not_use_test_targets(self):
        bits = np.zeros(N, dtype=np.uint8)
        bits[TRAIN_CUT:] = 1
        p = fit_markov(bits, np.arange(MAX_LAG, TRAIN_CUT), 1)
        self.assertLess(p[0], .01)

    def test_zero_jitter_known_period_repeats_raw_and_hash(self):
        raw = generate(0., BASE_SEED)
        for channel, bits in (("raw", raw), ("sha256", sha_condition(raw))):
            r = evaluate(bits, sigma=0., rep=0, stream=channel,
                         control=False, ml_train_size=512, boost_iters=4)
            d = {a["predictor"]: a["accuracy"] for a in r}
            self.assertEqual(d["lag32000"], 1.)
            self.assertEqual(d["fixed_template_32000"], 1.)
            if channel == "raw":
                self.assertEqual(d["lag2000"], 1.)


if __name__ == "__main__":
    unittest.main()

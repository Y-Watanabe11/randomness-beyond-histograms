"""Experiment G design/integrity tests; synthetic model only."""
import pathlib,sys,unittest
import numpy as np
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'experiments'))
from experiments_BC import BASE_SEED,N,TRAIN_CUT,RAW_REF
from experiment_G import (RATIOS,NOISE_MODELS,DISCOVERY_BUDGETS,VALIDATION_LENGTH,
                          base_bits,generate,select_lag,evaluate)

class TestExperimentG(unittest.TestCase):
    def test_disjoint_windows(self):
        for budget in DISCOVERY_BUDGETS:
            self.assertGreaterEqual(budget,80000)
            self.assertLessEqual(budget+VALIDATION_LENGTH,TRAIN_CUT)

    def test_zero_baseline_exact_legacy(self):
        np.testing.assert_array_equal(base_bits(RATIOS['baseline_4.9505']),RAW_REF)
        for model in NOISE_MODELS:
            np.testing.assert_array_equal(generate(4.9505,0,model,BASE_SEED),RAW_REF)

    def test_noise_models_are_distinct(self):
        ratio=RATIOS['baseline_4.9505']
        streams=[generate(ratio,50,m,BASE_SEED) for m in NOISE_MODELS]
        self.assertTrue(all(not np.array_equal(a,b)
                            for a,b in zip(streams[:-1],streams[1:])))

    def test_selection_does_not_read_test(self):
        a=generate(4.9505,5,'random_walk',BASE_SEED)
        p=select_lag(a,DISCOVERY_BUDGETS[0])
        b=a.copy();b[TRAIN_CUT:]=1-b[TRAIN_CUT:]
        self.assertEqual(p,select_lag(b,DISCOVERY_BUDGETS[0]))

    def test_shuffling_is_exact_and_destroys_baseline_period(self):
        a=generate(4.9505,0,'random_walk',BASE_SEED)
        b=np.random.default_rng(14).permutation(a)
        np.testing.assert_array_equal(np.bincount(a),np.bincount(b))
        result=evaluate(b,'baseline_4.9505',0,'none',0,'raw',
                        DISCOVERY_BUDGETS[0],'shuffle')
        self.assertLess(result['blind_accuracy'],.55)

    def test_zero_noiseless_baseline_predictable(self):
        a=generate(4.9505,0,'random_walk',BASE_SEED)
        r=evaluate(a,'baseline_4.9505',0,'none',0,'raw',DISCOVERY_BUDGETS[0])
        self.assertEqual(r['blind_accuracy'],1.0)

if __name__=='__main__':unittest.main()

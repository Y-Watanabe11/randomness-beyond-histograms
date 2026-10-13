"""Experiment F safety and controlled-period tests."""
from pathlib import Path
import sys,unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"experiments"))
from experiments_BC import generate,sha_condition,BASE_SEED,N,TRAIN_CUT
from experiment_F import choose_lag,evaluate,markov_predict

class TestExperimentF(unittest.TestCase):
    def test_unannounced_period_is_discovered(self):
        pattern=np.random.default_rng(3).integers(0,2,size=271,dtype=np.uint8)
        bits=np.tile(pattern,1600)[:N]
        choice=choose_lag(bits)
        self.assertTrue(choice["accept"])
        self.assertEqual(choice["lag"]%271,0)
        self.assertFalse(choice["flip"])
        self.assertEqual(evaluate(bits,"raw",0,0)["blind_test_accuracy"],1.)

    def test_validation_never_uses_future_test_targets(self):
        bits=generate(5,BASE_SEED)
        a=choose_lag(bits)
        changed=bits.copy()
        changed[TRAIN_CUT:]=1-changed[TRAIN_CUT:]
        self.assertEqual(a,choose_lag(changed))

    def test_hash_period_discovered_without_supplying_it(self):
        bits=sha_condition(generate(0,BASE_SEED))
        found=choose_lag(bits)
        self.assertEqual(found["lag"],32000)
        self.assertFalse(found["flip"])
        self.assertEqual(evaluate(bits,"sha256",0,0)["blind_test_accuracy"],1.)

    def test_shuffle_preserves_counts_but_destabilizes_prediction(self):
        bits=generate(0,BASE_SEED)
        control=np.random.default_rng(7).permutation(bits)
        np.testing.assert_array_equal(np.bincount(bits),np.bincount(control))
        self.assertLess(evaluate(control,"raw",0,0)["blind_test_accuracy"],.55)

    def test_no_current_or_future_markov_input(self):
        bits=np.zeros(N,dtype=np.uint8)
        t=np.array([TRAIN_CUT,TRAIN_CUT+4])
        a=markov_predict(bits,t)
        changed=bits.copy()
        changed[TRAIN_CUT+4]=1
        np.testing.assert_array_equal(a,markov_predict(changed,t))

if __name__=="__main__":
    unittest.main()

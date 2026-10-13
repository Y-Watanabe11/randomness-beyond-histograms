# Experiment A–G: Evaluation Protocol Audit

**Status:** Source-level methods audit and numerical-results cross-check against checked-in summary tables. This is a reproducibility/methodology note, **not** an independent validation of a physical entropy source.

## What the reported numbers mean

| Experiment | Target and metric | Allowed test-time information | Period/lag knowledge | Source model / repetitions |
|---|---|---|---|---|
| **A** | Game secret 0–99; held-out **first-guess hit rate**, plus game mean guesses with HIGH/LOW feedback | Forecast uses only training outcomes; current test secret never supplied. For the gameplay measure, feedback within the current game is permitted after each guess. | Learns repeating period from the first 70%; if absent, predicts the most frequent training symbol | Zero-jitter *deterministic* rational sampler; one original stream; exact shuffles |
| **A control** | First-guess accuracy of forcibly replayed 3,090-symbol template on shuffled secrets | Training values only | **Period 3,090 supplied** | Zero jitter; 200 exact permutations for a permutation control (not 200 independent devices) |
| **B** | SHA-256 output bit **offline template hit rate** on held-out test | Template from the first period of training data; **no observed test bits** | **32,000-bit period supplied** | Accumulated Gaussian phase-increment walk; 12 independent simulated noise seeds for each nonzero jitter |
| **C** | Plug-in `H(B_t)`, `H(B_t\|B_{t-1})`, `H(B_t\|B_{t-32000})`: **descriptive entropy estimates, not prediction accuracies** | Entire simulated series used to count bit pairs; no prediction/holdout claim | Lags 1 and 32,000 selected | Same synthetic B/C source; 12 noisy seeds, one deterministic zero-jitter stream |
| **D** | Lag-32,000 **raw-bit agreement**, **256-bit exact input-block match fraction**, **SHA-output bit agreement** | Compares observations at the same lag and held-out time positions; **not a train-fitted forecast** | 32,000 specified | Gaussian phase walk; **30** seeds per nonzero-jitter condition |
| **E** | Raw/SHA one-step-ahead **online** next-bit hit rate, Markov/ML/lag predictors | **Previously observed true test bits** may enter lagged features; never present/future test bits. ML parameters fitted on training targets only. Separate frozen first-period template baseline does not observe test outcomes. | Lags **2,000 and 32,000 supplied** as ML features and explicit predictors; Markov-1/2 uses its natural short-order history | Gaussian phase walk; **6** seeds per nonzero-jitter condition; one seeded exact shuffle per stream at sigma=0 |
| **F** | Raw/SHA one-step-ahead **online** next-bit accuracy using lag discovered from historical data | Discovery first 50%; validation next 20%; untouched test final 30%. Previous observed test bits may enter predictions | FFT scan lags 1..40,000 using discovery prefix; top 64 validated; compare both lag orientations; require >=1 percentage-point validation gain over majority baseline | Gaussian phase walk; **12** independent noisy seeds per setting; 12 permutations for designated shuffle controls |
| **G** | Raw/SHA one-step-ahead **online** blind-lag prediction; separate descriptive lag-32k block diagnostics | Discovery budget 96k / 144k / 192k, next **40k** validation, fixed final test from bit 268,800 to 384,000. Earlier true test bits available as history, never current/future bits | Lags 1..40,000 scanned, top 64 candidates validated, +/- lag orientations, >=1 pp gain vs validation majority | Four ratios × accumulated random-walk / correlated AR(1) increments / IID sampled phase perturbations × 5 or 50 ps; **6** noise seeds/setting. Zero-jitter deterministic reference is not 6 stochastic replicates |

**Key operational distinction:** In B and the A first-guess forecast, test-time target outcomes are *not* revealed to the forecast; in E/F/G, the evaluator is explicitly **prequential/online**, so earlier test bits may be observed before forecasting the next bit. C and D are *descriptive* rather than forecasting methods. Do not pool the accuracy percentages as estimates of one universal property.

## Why several '5 ps, SHA-256' percentages coexist

| Report | SHA-256 value | Meaning |
|---|---:|---|
| B | **49.99%** | Frozen known-period **offline template** accuracy on SHA bits |
| D | **50.62%** | Same-lag SHA output **bit agreement**, not a trained predictor's hit rate |
| E | **50.42%** | Online **gradient boosting** next-bit hit rate; lag features include 2,000 and 32,000 |
| F | **50.59%** | Online blind discovered-lag forecast; 50%/20%/30% discovery/validation/test |
| G | **50.50%** | Online blind lag forecast for ratio 4.9505 and **accumulated random-walk** jitter at 5 ps; G's validation length and discovery-budget protocol differ from F |

D's reported mean reflects **30** seeds, not 12. The independent raw lag check at 5 ps and 12 seeds (92.456% full available pairs) is **not** the same estimand as D's 92.515% on the common held-out interval with 30 seeds.

## What can and cannot be claimed

**Supported in this constructed simulation:**

- An exact permutation leaves every marginal histogram bin unchanged but alters exploitable temporal patterns.
- An exact-period predictor can fail after hashing while *raw* lag dependence persists, and the failure is largely explained by loss of **complete 256-bit input block matches**. The empirical identity is `P(hash bit agrees)=q + (1-q) P(hash bit agrees | different input blocks)`, where `q` is the fraction of exact input-block matches. The approximation `(1+q)/2` relies on the near-half observed match rate on distinct SHA inputs.
- Access to updated observed history, lag candidates, or validation can change forecast accuracy, so forecasting protocols must be specified.
- Output predictability under tested methods depends strongly on the *synthetic temporal noise process*, as well as the chosen sampling frequency ratio.

**Not established:**

- Actual RO/TRNG entropy rate, true independent physical jitter, cryptographic security, or a break of SHA-256.
- Inability of all possible predictors to forecast SHA-256 outputs.
- Physical equivalence of `sigma_ps` between random-walk increments, correlated AR(1) increments and instantaneous IID phase offsets.
- General applicability of high raw-bit prediction accuracies to arbitrary frequency ratios or physical oscillators.

## Physical interpretation caveat

For an ideal freely running oscillator, a random walk in phase may arise from accumulated frequency fluctuations; white frequency-noise terms can give a `1/f²` phase-noise region. A real oscillator can also show other phase-noise regimes, drift, supply coupling and correlations. IID sampled phase offsets are a **counterfactual contrast**, not a faithful model of a PLL-locked clock. Our three noise models are not parameter-matched in physically equivalent units merely because they each use '5 ps'.

## Discrete frequency ratio audit

See `experiments/audit_ratio_near_periods.py` and `data/ratio_near_periods.csv` for the closest **integer** or **half-cycle** relations among lags up to 40,000. The search is an analytic property of the **specified ratios**, independent of model fitting or test outcomes.

**Crucial:** A strong short-lag relation is a deterministic property of the selected rational/irrational ratio, but noisy forecast accuracy depends on the noise process, finite sample and threshold model. Near-period screening does **not** estimate hardware entropy or show that one lag is always the best learned predictor. For the baseline: `10×4.9505=49.505` (near inversion), `101×4.9505=500.0005` (near agreement). Also `1000×4.9505=4950.5` (exact inversion) and `2000×4.9505=9901` (exact agreement), so the search interval has **highly privileged resonant lags**. Every one of the other three ratios also admits a close integer/half-cycle relation within 40,000. The label `detuned_4.953327` is a shorthand: its actual source expression is `4.9505 + 0.002*sqrt(2) ≈ 4.953328427`.

## Reproducible checks

```bash
python experiments/audit_ratio_near_periods.py
python -m unittest discover -s tests -v
```

See primary scripts `experiments/experiment_A.py`, `experiments/experiments_BC.py`, and `experiments/experiment_D.py` through `experiment_G.py` for ground-truth protocol implementation. The accompanying numerical summaries are synthetic and conditional on their seeds and settings.

# Randomness Beyond Histograms

**Two identical histograms. Two very different futures.**

Reproducible Python experiments exploring how temporal structure changes the predictability of random-looking sequences, starting from a simplified ring-oscillator (RO) model.

> **Scope:** Educational, synthetic-data experiments. These are **not** measurements of physical ring oscillators, a NIST SP 800-90B entropy-source assessment, a security certification, or an attack on SHA-256.

## Experiments

| Experiment | Question | Method |
| --- | --- | --- |
| **A — Same histogram, different order** | Can two exactly equal marginal distributions have very different forecasting accuracy? | Zero-jitter rational phase sampler, SHA-256 conditioning, exact permutation, 70/30 chronological holdout, period-template predictor and high/low guessing strategies |
| **B — Jitter sweep** | How does synthetic phase diffusion affect exact-template forecasting? | Cumulative Gaussian per-sample phase perturbations, 12 independent runs per jitter level; known-period predictor tested on held-out SHA-256 output bits |
| **C — Conditional entropy** | What does marginal Shannon entropy miss? | Empirical H(bit), H(bit | previous bit), and H(bit | bit 32,000 positions earlier) |

**Key controlled result (A):** 74,160 identical values in two different orders. First-guess prediction accuracy was **100.00%** for the exact periodic sequence and **1.34%** for its shuffled permutation. Both sequences have the same per-symbol empirical Shannon entropy (**6.62350 bits**). The 100% case uses a deliberately **zero-jitter, deterministic** model.

**Selected B/C results:** With a period-template predictor, mean held-out SHA-256 bit accuracy decreases from 100% (zero jitter) to ~53.51% (0.5 ps) and ~49.99% (5 ps). Empirical H(bit | bit 32,000 earlier) goes from zero at zero jitter to ~0.93867 and ~0.99987 bits at those two jitter settings. These quantify **one particular estimator and one particular lag**, not entropy rate or cryptographic security.

## Quick start

Python 3.10+ recommended.

```bash
python -m pip install -r requirements.txt

python experiments/experiment_A.py
python experiments/experiments_BC.py

python -m unittest discover -s tests -v
```

The scripts write generated figures, CSV files, and notes to **`outputs/`** (excluded from version control). The checked-in baseline result tables are in **`data/`**.

## Repository structure

```text
experiments/
  experiment_A.py               # same histogram / shuffle / guessing game
  experiments_BC.py             # synthetic timing jitter and conditional entropy
data/
  experiment_A_results.csv
  experiment_A_permutation_null.csv
  experiments_BC_results.csv
  experiments_BC_summary.csv
tests/
  test_results.py               # integrity / key expected result checks
outputs/                         # generated locally; gitignored
```

## Important interpretation

- The noiseless phase increment is **4.9505 cycles/sample = 4 + 1901/2000**; its sampled raw bits repeat with a 2,000-sample period. Under aligned SHA-256 processing, a repeated sequence of output bits appears at the 32,000-bit common alignment.
- Experiment A uses a rational phase model without assigning a physical clock frequency. Experiment B/C uses **50 MHz** as the RO frequency, corresponding to approximately **10.10 MHz** sampling for the same ratio.
- SHA-256 is deterministic. Repeated input blocks produce repeated output blocks. No entropy is created by hashing a deterministic source.
- The B/C forecast is a *known-period template* for **hashed output**. The collapse of that particular forecast under tiny phase perturbations is affected by SHA-256's avalanche effect and does **not** mean raw RO bits become secure.
- The shuffled sequence is a permutation **without replacement**, not a proven IID or cryptographically secure sequence.
- A balanced histogram and high empirical single-symbol entropy do not establish unpredictability. Neither does failure of a single predictor.

## Reproducibility

Scripts use fixed seeds (base seed `20261009`). B/C uses 12 repeats per jitter setting. Experiment A and the B/C conditions have separate evaluation protocols as documented in each script; do not compare their accuracy percentages as if they were the same endpoint.

For physical entropy-source evaluation, see [NIST SP 800-90B](https://csrc.nist.gov/pubs/sp/800/90/b/final).

## Articles

Companion writeups are planned for Qiita (implementation-oriented) and Medium (randomness, predictability, and entropy). The source scripts and numerical results here are the reproducibility reference.

## Extra check: raw-bit recurrence at 5 ps

To verify the companion Medium article's raw-bit lag comparison independently of SHA-256, run:

```bash
python experiments/measure_raw_lags_5ps.py
```

Under the same 5 ps toy noise model and 12 seeds as experiment B, mean raw-bit agreement is **98.217% at lag 2,000** and **92.456% at lag 32,000**. The latter is reported as **about 92.5%** in the article. See `data/raw_lag_5ps_12seeds.csv` for the per-seed results. The SHA-256 output template's ~50% accuracy is a different metric, and must not be interpreted as raw-bit unpredictability.


## Experiment D: Why SHA-256 can hide a strongly repeating raw signal

A follow-up mechanism test separates **bitwise agreement**, **whole input-block recurrence**, and **SHA-256 output agreement** using an identical held-out interval and the same 32,000-bit lag.

**Headline result, modeled 5 ps jitter, 30 seeds (different held-out protocol from B/C):**

| Measurement (lag 32,000) | Mean |
|---|---:|
| Raw input bit agreement | **92.52%** |
| Exact matching 256-bit input blocks (q) | **1.19%** |
| SHA-256 output bit agreement | **50.62%** |
| Predicted SHA agreement from (1+q)/2 | **50.60%** |

The empirical identity is **p(SHA bit match) = q + (1−q) p(SHA bit match | distinct input blocks)**. For distinct input blocks the observed bit-match rate is close to one half, so the SHA block-to-block recurrence is explained by q.

To reproduce (Python 3.10+; ~30 seeds per setting):

```bash
python experiments/experiment_D.py --replicates 30
python -m unittest discover -s tests -v
```

See [Experiment D summary](data/experiment_D_headline.csv) and [Experiment D figure](figures/experiment_D_mechanism.svg). The script additionally creates full per-seed data, a detailed summary with normal-approximate 95% CIs for means across seeds, a high-resolution PNG, and an interpretation note in `outputs/`.

**Important:** Experiment D's 92.52% is calculated **only on the same held-out positions as the hashed comparison**. The earlier **92.456%** figure in the companion article was calculated over the *entire* available lag-paired sequence with 12 seeds. These are different protocols, not contradictory measurements. The ~50% hash **lag agreement** here is not identical to experiment B's ~50% *first-period template* accuracy (both are reported separately by the new script).

Neither a failed predictor nor a near-50% SHA output agreement establishes entropy-rate or cryptographic security. The physical noise is simulated, and the approximation (1+q)/2 is a model for hash avalanche behavior, not a universal SHA theorem.

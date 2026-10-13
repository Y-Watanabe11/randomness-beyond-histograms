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


## Experiment E: Eight predictors, same streaming holdout

A second follow-up compares simple frequency forecasting, 1st/2nd-order
Markov models, 2,000/32,000-bit lag replay, a **frozen** first-period template,
logistic regression and histogram-based gradient boosting.

Each one-step-ahead prediction is evaluated at identical chronological target
positions. **Online/streaming protocol:** the models may use earlier observed
test bits as lagged features when predicting the next test bit; they are not
given the current target or any future bit. Model fitting is confined to
training targets (indices 32,000 through the original 70% boundary).
The fixed-template baseline is a *different*, offline forecast convention.
Models are told the known simulated lags in advance; this is a favorable
attacker assumption, not automatic feature discovery.

Run:

```bash
python -m pip install -r requirements.txt
python experiments/experiment_E.py --replicates 6
python -m unittest discover -s tests -v
```

This runs seven synthetic jitter settings, six seeded runs per setting,
and a frequency-preserving exact-shuffle negative control at zero jitter.
Results are written to `outputs/experiment_E_results.csv` (all models and
replicates), `outputs/experiment_E_summary.csv` (mean and normal-approximate
95% CI across seeds), `outputs/experiment_E_predictors.png`, and the methodological note.
The compact checked-in [Experiment E highlights](data/experiment_E_highlights.csv)
and [figure](figures/experiment_E_predictors.svg) make results browsable.

**At 5 ps synthetic jitter, 6-seed mean test accuracy:**

| Method | Raw bits | SHA-256 output |
|---|---:|---:|
| Majority | 50.01% | 50.00% |
| First-order Markov | 90.10% | 50.00% |
| Lag 2,000 (online) | 98.19% | 49.95% |
| Lag 32,000 (online) | 90.63% | 50.60% |
| Logistic regression | 98.19% | 50.38% |
| Histogram gradient boosting | 98.19% | 50.42% |

The fitted learners can often recover the useful raw 2,000-bit lag, but
under this particular setup they do not recover the hashed time dependence
at 5 ps. **This does not prove that SHA-256 removes information or that the
output stream is cryptographically unpredictable.** An observer who sees
the SHA-256 inputs has different information than one who only sees the
hash output. The test includes only finite chosen models, finite data,
preset features and a toy model, not a general security analysis.

The 50 ps raw stream still shows ~90% first-order Markov predictability
due to the *deliberately near-integer* frequency ratio 4.9505 in this model.
This is not a generic claim about real RO hardware.


## Experiment F: Can a predictor discover the lag without being told?

**Result (synthetic, one-step-ahead online forecasting):** When discovering lags
from earlier data, the raw stream reaches **99.60% at 5 ps** and **98.50% at
50 ps** (12 noise seeds each). The SHA-256 output gives **50.59% at 5 ps**
and **50.05% at 50 ps** for the same search method. A prespecified
positive/negative lag search discovers **101** on the raw stream at 5 ps and
**inverted lag 10** at 50 ps. Exact-shuffle controls retain their histograms
and show no selected lags under the 1-percentage-point validation threshold.

The known-lag comparison is **not an oracle upper bound**: the 4.9505 rational
sampling ratio also creates near-perfect shorter lag relations,
since \`101 × 4.9505 = 500.0005\` and \`10 × 4.9505 = 49.505\`, the latter
nearly flipping the phase by half a cycle. This is a *constructed* property
of the model and not characteristic of arbitrary physical oscillators.

**Honest chronological protocol:** FFT autocorrelation on first 50% only
(search lags 1..40,000), screen top 64 candidates on the next 20%,
choose sign and lag if validation accuracy exceeds the majority baseline
by at least **1 percentage point**, and evaluate only on the final 30%.
Known-lag reference (raw lag 2,000, SHA lag 32,000) and train-fitted Markov-1
are displayed for context. This is **online next-bit forecasting**:
earlier observed *test* bits may be used as features, but no current or
future target bit may be used. It is not a frozen multi-step forecast.

\`\`\`bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python experiments/experiment_F.py --replicates 12 --shuffle-replicates 12
\`\`\`

Generated outputs under \`outputs/\`: per-run CSV, complete summary and
95% Student-t CIs **across simulated seeds**, chart, methodological notes.
Browse [summary highlights](data/experiment_F_highlights.csv) and
[figure](figures/experiment_F_blind_discovery.svg) in GitHub.

Zero-jitter is a deterministic *single* realization (no seed CI); the 12
shuffles at each control setting are permutations of one underlying stream,
not independent experimental hardware samples. A scan over many lags has
multiple-comparison risk; distinct discovery, validation and evaluation
windows prevent selection on final test outcomes. Failure of the tested
predictors does not prove any form of cryptographic unpredictability.

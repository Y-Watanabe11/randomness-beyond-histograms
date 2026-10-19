# Two Identical Histograms. Two Very Different Futures.

*Why a failed prediction test does not prove a signal is unpredictable.*

## Opening: Two Identical Histograms

Imagine two sequences, each containing 74,160 integers ranging from 0 to 99. Their histograms are identical, bin for bin: every number appears exactly as often in one sequence as in the other.

Can we predict which number comes next? I tested a simple periodicity-based predictor on a held-out test segment of each sequence:

- **Sequence 1: 100.00%** prediction accuracy
- **Sequence 2: 1.34%** prediction accuracy (the same as always guessing the most common value)

![Figure 1: Identical histograms of ordered and shuffled sequences](../figures/fig1_tds.png)

*Figure 1. Experiment A: The original sequence and its shuffled counterpart have identical empirical histograms. A periodicity-based predictor achieves 100.00% prediction accuracy on held-out data from the original sequence and 1.34% after shuffling.*

The difference lies in their order. The first sequence contains a repeating pattern, while the second is an exact shuffle of the same values. Shuffling preserves the histogram but destroys the temporal structure the predictor relies on.

A histogram describes the marginal distribution: which values appear and how often. It says nothing about how successive values depend on each other. The same gap appears when we evaluate random number generators, sensor signals, or the outputs of cryptographic hash functions, where an output that looks random does not necessarily come from an unpredictable source.

## Section 1: A Random-Looking Output Can Still Have a Memory

A number-guessing game is a familiar exercise for people learning Python. While teaching programming to elementary school students as a part-time job, I built one myself and tried different ways of implementing it.

My research is in analog semiconductor circuit design, so I also started building games that combined software with hardware, which led me to look at how random numbers are generated in circuits. One question caught my attention: what happens to the regularity of a bit sequence after it passes through SHA-256?

To investigate, I used a synthetic model of a ring oscillator (RO), a circuit commonly used in hardware random number generators. The oscillator runs at 50 MHz (a period of 20 ns), and the ratio of the oscillation frequency to the sampling frequency is r = 4.9505, giving a sampling frequency of about 10.10 MHz. I divided the sampled raw bitstream into 256-bit blocks and hashed each block separately with SHA-256.

Without jitter, the raw bitstream repeats every 2,000 bits. Because the bits are grouped into 256-bit blocks before hashing, the SHA-256 output repeats every 32,000 bits, the least common multiple of 2,000 and 256. Even a SHA-256 output is perfectly predictable when its input repeats.

Next, I added synthetic cumulative phase jitter. Here, σ_t is the standard deviation of the timing error added at each sampling step, and these errors accumulate over time. With the same fixed-template predictor, I obtained:

- **0 ps jitter:** 100% prediction accuracy
- **5 ps jitter:** 49.99% prediction accuracy

For binary prediction, 49.99% is chance-level performance. But this only shows that the fixed template could no longer exploit the original recurrence. It does not show that the underlying source had become unpredictable.

*Did the source lose its regularity, or did the predictor simply lose the pattern it relied on?*

## Section 2: Why the Hash Output Loses Its Fixed-Lag Pattern

To find out, I compared bits separated by a *lag* of 32,000, the exact repetition period of the noiseless hash output.

In this experiment, each 256-bit block is hashed separately, so even if most raw bits match, a single differing bit makes two input blocks non-identical. SHA-256 exhibits the *avalanche effect*: changing an input typically changes about half of the digest bits. This is a statistical tendency, not a guarantee for every pair of inputs.

I measured three quantities at the same lag. At **5 ps** of cumulative phase jitter:

- **92.52%** of raw bits matched.
- Only **1.19%** of complete input blocks matched exactly.
- **50.62%** of SHA-256 output bits matched.

Matching most of the raw bits is not enough to reproduce an input block, because all 256 bits must match. Let **q** be the fraction of input blocks that match exactly, and **s** the output-bit match rate when the input blocks differ. Identical inputs always produce identical digests, so the overall output-bit match rate is:

![Equation 1: SHA-256 output-bit match rate](../figures/eq1_sha_match_identity.png)

In this experiment, s was approximately 0.5, so the expression simplifies to:

![Equation 2: Approximate output-bit match rate](../figures/eq2_sha_match_approx.png)

With q = 1.19%, this predicts an output-bit match rate of about **50.60%**, close to the observed **50.62%**.

![Figure 2: Raw-bit, block, and SHA-256 output agreement versus jitter](../figures/fig2_tds.png)

*Figure 2. Experiment D: Agreement at a fixed lag of 32,000 bits across different synthetic jitter settings. The three curves show raw-bit agreement, exact matching of 256-bit SHA-256 input blocks, and SHA-256 output-bit agreement. Results are aggregated over 30 random seeds, with 95% confidence intervals. The zero-jitter case is deterministic.*

SHA-256 did not create a new source of physical entropy. It made the periodic structure remaining in the raw bits much less visible at this particular lag. A match rate near 50% at one fixed lag does not mean every possible predictor will fail.

## Section 3: What Happens When the Predictor Is Allowed to Search?

What if the predictor could look for a more useful lag on its own? To test this, I built a predictor that discovers repeating patterns without being told the theoretical periods of 2,000 or 32,000 bits.

I divided each bitstream chronologically into three parts:

- **Discovery (50%):** Search for candidate lags using autocorrelation.
- **Validation (20%):** Select the most accurate lag and decide whether the bit at that lag should be inverted.
- **Test (30%):** Evaluate the selected predictor on held-out data.

The predictor searches lags from 1 to 40,000 and evaluates the 64 strongest candidates on the validation segment. Its choice is fixed before testing begins. During the test, it predicts each new bit from previously observed bits. This is **online next-bit prediction**: earlier test bits may be used once they have been observed, but the current and future bits are never available in advance.

The core of the method looks like this:

```python
# Simplified from experiment_F.py
candidates = discover_lag_candidates(
    bits[:DISCOVERY_CUT], max_lag, top_k
)
vi = np.arange(DISCOVERY_CUT, TRAIN_CUT)
best = None

for lag, _ in candidates:
    agreement = float(np.mean(bits[vi] == bits[vi - lag]))
    flip = agreement < 0.5
    score = 1 - agreement if flip else agreement
    candidate = (score, -lag, lag, flip)
    if best is None or candidate[:2] > best[:2]:
        best = candidate

_, _, lag, flip = best
t = np.arange(TRAIN_CUT, N)
pred = bits[t - lag] ^ np.uint8(flip)
test_accuracy = float(np.mean(pred == bits[t]))
```

*For clarity, this excerpt omits the full implementation's minimum validation-gain requirement and majority-class fallback. The complete code is in [experiment_F.py](../experiments/experiment_F.py).*

**Table 1. Experiment F: Online prediction accuracy at 5 ps**

| Prediction target | Test accuracy |
|---|---:|
| **Raw oscillator bits** | **99.60%** |
| SHA-256 output bits | 50.59% |
| Shuffled raw-bit control | 49.96% |

![Figure 3: Online prediction accuracy of raw oscillator bits and SHA-256 output](../figures/fig3_blind_prediction.png)

*Figure 3. Experiment F: Online next-bit prediction accuracy across synthetic jitter settings. The left panel shows raw oscillator bits; the right panel shows SHA-256 output bits. Discovered-lag prediction is compared with prespecified-lag, first-order Markov, and majority-class baselines. Nonzero-jitter results are averaged over 12 seeds, with 95% confidence intervals.*

Without knowing the theoretical period, the predictor reached **99.60%** on the raw oscillator bits, while its accuracy on the SHA-256 output stayed close to 50%. Both numbers come from the same online protocol applied to two different targets, and neither shows that the SHA-256 output is unpredictable to every possible method.

A smaller effect appeared at 2 ps. There, the discovered-lag predictor reached 53.38% on the SHA-256 output, compared with 52.29% when the lag was fixed at 32,000. The lag it selected most often was 15,616, which is a multiple of 256 and therefore aligned with the input-block boundaries. It also nearly reproduces the oscillator phase:

15,616 × 4.9505 = 77,307.008

A 1.10-percentage-point difference is within the confidence intervals, so this is a hint rather than a demonstrated improvement.

On the raw bits at 5 ps, the predictor did not use the exact 2,000-sample period at all. It chose a short recurrence at **lag 101**.

## Section 4: Why a Short Imperfect Period Can Beat a Perfect Long One

If the oscillator returns to nearly the same point in its cycle, the sampled bit is likely to repeat. Without noise, waiting exactly 2,000 samples reproduces the pattern perfectly. In the cumulative phase-noise model, however, timing errors build up over successive samples, so a longer lag may be better aligned in theory but carries more accumulated uncertainty.

This creates a trade-off between two factors:

- **Phase alignment:** How closely the oscillator returns to the same point in its cycle.
- **Accumulated jitter:** How much timing uncertainty builds up between the two observations.

At a frequency ratio of 4.9505, the oscillator completes almost exactly 500 cycles over 101 sampling intervals:

![Equation 3: Near phase recurrence at lag 101](../figures/eq3_lag101_recurrence.png)

The remaining phase offset is only 0.0005 cycles, equivalent to 10 ps at 50 MHz. At higher jitter settings (20–50 ps), the predictor switched to another short relationship:

![Equation 4: Approximate half-cycle inversion at lag 10](../figures/eq4_lag10_inversion.png)

After 10 samples, the oscillator is almost exactly half a cycle out of phase, so inverting the bit observed 10 samples earlier gives a useful prediction.

In the cumulative random-walk model, the phase difference at lag L has a deterministic offset and a stochastic contribution:

![Equation 5: Deterministic phase offset and accumulated random-walk jitter](../figures/eq5_phase_jitter.png)

The individual phase-increment errors ε_k are independent, so the accumulated timing uncertainty grows with the square root of the lag. At 5 ps of jitter per sampling step:

**Table 2. Phase alignment and accumulated jitter**

| Lag (samples) | Deterministic phase offset | Accumulated jitter (standard deviation) |
|---:|---:|---:|
| 101 | 10 ps | approximately 50 ps |
| 2,000 | 0 ps | approximately 224 ps |

Lag 2,000 is perfectly aligned in the noiseless model, but its timing uncertainty is more than four times larger than that of lag 101. Consistent with this trade-off, Experiment F reached **99.60%** with the discovered lag and **98.20%** with the prespecified 2,000-sample lag. The two time values cannot simply be added to get a bit error rate, since phase wrapping and the sampling threshold also matter.

The choice of lag matters even more at higher jitter. At 50 ps, raw-bit agreement at the fixed 32,000 lag in Experiment D fell to **49.62%**, while the lag-searching predictor in Experiment F still reached **98.50%**.

Similar phase-recurrence ideas appear in coherent-sampling oscillator-based random number generators [3]. The experiments here use a separate synthetic model and do not reproduce that work's hardware measurements.

## Section 5: Change the Noise Model, Change the Conclusion

So far, I have modeled timing errors as small fluctuations that accumulate over time. To see how much the conclusion depends on that choice, I repeated the experiment with three noise models:

- **Cumulative random walk:** Small timing errors accumulate from one sample to the next.
- **Correlated phase increments (AR(1)):** Timing errors still accumulate, but successive increments are strongly correlated (ρ = 0.90).
- **Independent phase perturbations:** Each sample receives a fresh phase offset, and errors do not carry over from previous samples.

All three use the same frequency ratio of 4.9505 and a nominal jitter setting of 5 ps. However, **5 ps does not represent equivalent physical noise strength across these models**. Experiment G used six random seeds, 192,000 discovery bits, 40,000 validation bits, and a final 30% test split, so its estimates are not directly interchangeable with those from Experiment F.

**Table 3. Online prediction accuracy across noise models (frequency ratio 4.9505, nominal jitter 5 ps)**

| Noise model | Raw bits | SHA-256 output |
|---|---:|---:|
| Cumulative random walk | 99.60% | **50.50%** |
| Correlated phase increments | 99.01% | **50.02%** |
| Independent phase perturbations | 99.94% | **92.50%** |

![Figure 4: Prediction accuracy under three phase-noise models](../figures/fig4_tds.png)

*Figure 4. Experiment G: Online prediction accuracy for raw oscillator bits and SHA-256 outputs under three synthetic noise models at a frequency ratio of 4.9505 and a nominal 5 ps jitter setting. Results show six-seed means and 95% confidence intervals.*

With cumulative or correlated phase increments, SHA-256 prediction stayed close to 50%. Under independent phase perturbations, it reached **92.50%**. Because independent phase offsets do not accumulate, the oscillator keeps returning close to the same phase even after many samples. In this configuration, complete 256-bit input blocks matched at a lag of 32,000 about **84.96%** of the time, and identical blocks produce identical digests. The block-match rate and the online prediction accuracy are different measurements, but the first helps explain the second.

### Does the Frequency Ratio Matter?

Keeping the independent phase-perturbation model, I then changed the ratio between the oscillator and sampling frequencies. For each ratio, Table 4 also lists the lag that is a multiple of 256 (so that whole input blocks line up) and that brings the oscillator closest to its starting phase within the 40,000-lag search range.

**Table 4. SHA-256 output prediction by frequency ratio (independent phase perturbations, 5 ps)**

| Frequency ratio | Closest block-aligned recurrence (residual offset) | Online prediction accuracy |
|---:|---:|---:|
| 4.9505 | lag 32,000 (0 ps) | **92.50%** |
| ≈ 4.953328 | lag 24,576 (≈ 12 ps) | **89.04%** |
| ≈ 4.618034 | lag 15,360 (≈ 41 ps) | **57.01%** |
| 4.917321 | lag 1,536 (≈ 101 ps) | **50.15%** |

![Figure 5: Frequency-ratio and noise-model sensitivity](../figures/fig5_tds.png)

*Figure 5. Experiment G: Online prediction accuracy across four frequency ratios and three synthetic noise models at a nominal 5 ps jitter setting. The left panel shows raw bits; the right shows SHA-256 output bits. Each cell is a six-seed mean, evaluated with 192,000 discovery bits, 40,000 validation bits, and a final 30% test split. Ratios labeled 4.953328* and 4.618034* are rounded displays of 4.9505 + 0.002√2 and 4 + (√5 − 1)/2, respectively.*

The ratio near 4.953328 is irrational, yet the predictor reached **89.04%**. The ratio 4.917321 is rational (4,917,321/1,000,000), but accuracy was only **50.15%**. So the distinction is not whether the ratio is rational. Across these four ratios, accuracy falls in the same order as the residual phase offset of the closest block-aligned recurrence rises. Four points cannot establish a general rule, and I have not checked which lag the predictor actually selected in each case, but the ordering supports a simple reading: what matters is whether a well-aligned, block-aligned recurrence exists within reach and survives the chosen noise process.

None of this implies that independent phase perturbations describe real oscillators. In free-running ring oscillators, timing errors typically accumulate, and RO-based random number generators are designed to harvest that jitter as an entropy source [2]. Real circuits also show supply sensitivity, temperature drift, and correlated noise that these models leave out. What Experiment G shows is narrower: with the same SHA-256 function, the measured predictability changed substantially with the source's timing behavior and the sampling ratio.

## Section 6: What a Failed Prediction Test Actually Tells Us

For a roughly balanced binary sequence, a score near 50% suggests the tested predictor has little advantage over chance. An appropriate baseline is still necessary, especially if the bit frequencies are imbalanced. And the result applies only to that experiment. It does not prove that the underlying signal has lost its structure, that another method would also fail, or that the output is cryptographically secure.

Predictability and entropy are related, but they are not the same measurement. Establishing sufficient entropy requires additional evidence and dedicated procedures, such as those in NIST SP 800-90B [1].

The experiments in this article also used different evaluation methods. Section 1 examined a fixed-template predictor, Section 2 measured agreement at a fixed lag, and Sections 3 and 5 evaluated online predictors that learned useful lags from earlier data. Their numbers are not interchangeable measures of randomness.

When I evaluate a prediction result now, I find it useful to ask five questions:

1. **Prediction target:** Am I predicting the raw signal or a transformed output?
2. **Available information:** Can the predictor use previously observed bits, or only a fixed template?
3. **Pattern discovery:** Was the relevant lag supplied in advance or discovered from the data?
4. **Noise assumptions:** Does the model allow timing errors to accumulate, correlate, or reset independently?
5. **Remaining structure:** Have I examined correlations, repeated blocks, and other dependencies beyond a single accuracy score?

These questions do not replace a formal randomness or entropy assessment, but they make clear what a prediction experiment has actually established.

All results here come from synthetic ring-oscillator models. They are not measurements of physical devices and make no claim about the cryptographic security of SHA-256.

## Closing: Randomness Is Not a Single Number

The two sequences at the start of this article had identical histograms, yet next-value prediction reached 100.00% on one and 1.34% on the other. The difference was not which numbers appeared, but the order in which they appeared.

The ring-oscillator experiments showed a related problem. Under cumulative phase jitter, the raw bits stayed 99.60% predictable while the SHA-256 output was much harder for the tested predictor to forecast. Under independent phase perturbations at the same frequency ratio, prediction on the SHA-256 output reached 92.50%. The two results describe different signal conditions, so they do not conflict.

SHA-256 can hide a particular pattern from a particular predictor without making the original source unpredictable. Prediction accuracy describes a particular experiment, not a universal certificate of randomness.

## References and Reproducibility

All figures and equation images were prepared by the author from synthetic experiments.

- [1] NIST, *Recommendation for the Entropy Sources Used for Random Bit Generation* (2018), NIST SP 800-90B. https://doi.org/10.6028/NIST.SP.800-90B
- [2] M. Baudet, D. Lubicz, J. Micolod, A. Tassiaux, *On the Security of Oscillator-Based Random Number Generators* (2011), Journal of Cryptology 24, 398–425. https://doi.org/10.1007/s00145-010-9089-3
- [3] A. Peetermans, V. Rožić, I. Verbauwhede, *Design and Analysis of Configurable Ring Oscillators for True Random Number Generation Based on Coherent Sampling* (2021), ACM Transactions on Reconfigurable Technology and Systems. https://doi.org/10.1145/3433166

Code and data: [the unknown-lag search](../experiments/experiment_F.py), [the noise-model comparison](../experiments/experiment_G.py), [the block-aligned recurrence calculation for Table 4](../experiments/audit_block_aligned_recurrence.py), [the Figure 5 script](../experiments/plot_G_ratio_sensitivity.py) with its [summary CSV](../data/experiment_G_highlights.csv), [the evaluation protocol audit](evaluation_protocol_audit.md), and [the theoretical notes on phase recurrence](phase_recurrence_theory.md).

# Two Identical Histograms. Two Very Different Futures.

*Why a failed prediction test does not prove a signal is unpredictable.*

## Opening: Two Identical Histograms

Imagine two sequences, each containing 74,160 integers ranging from 0 to 99.

Their histograms are identical, bin for bin. Every number appears exactly as often in one sequence as in the other.

But can we predict which number comes next?

To find out, I tested a simple periodicity-based predictor on a held-out test segment. The results were striking:

- **Sequence 1: 100.00%** prediction accuracy
- **Sequence 2: 1.34%** prediction accuracy (close to the 1% chance level for uniform guesses among 100 values)

![Figure 1: Identical histograms of ordered and shuffled sequences](../figures/fig1_tds.png)

*Figure 1. Experiment A: The original sequence and its shuffled counterpart have identical empirical histograms. However, a periodicity-based predictor achieves 100.00% first-guess accuracy on the original sequence and 1.34% after shuffling, evaluated on held-out test data.*

If the two sequences have identical distributions, why is one so much easier to predict?

The difference lies in their order. The first sequence contains a repeating pattern, while the second is obtained by shuffling exactly the same values. The shuffle preserves the histogram but disrupts the temporal structure exploited by this predictor.

A histogram describes the marginal distribution: which values appear and how frequently. It tells us nothing about the temporal dependence between successive values.

This distinction matters beyond a simple statistical puzzle. The same issue arises when evaluating random number generators, sensor signals, and cryptographic hash outputs.

**An output that looks random does not necessarily come from an unpredictable source.**

## Section 1: A Random-Looking Output Can Still Have a Memory

A number-guessing game is a familiar exercise for people learning Python. While teaching programming to elementary school students as a part-time job, I decided to build one myself and experiment with different implementations.

My research focuses on analog semiconductor circuit design, so I also began building games that combined software with hardware. This led me to explore different ways of generating random numbers.

One question caught my attention: **What happens to the regularity of a bit sequence after it passes through SHA-256?**

To investigate, I used a synthetic model of a ring oscillator (RO), a circuit commonly used in hardware random number generators.

I set the oscillator frequency to 50 MHz, corresponding to a period of 20 ns. The ratio of the oscillation frequency to the sampling frequency was r = 4.9505, giving a sampling frequency of approximately 10.10 MHz.

I then divided the generated raw bitstream into 256-bit blocks and hashed each block separately with SHA-256.

Without jitter, the raw bitstream repeats every 2,000 bits. Because the bits are grouped into 256-bit blocks before hashing, the SHA-256 output repeats every 32,000 bits. This follows from the least common multiple of 2,000 and 256.

In other words, even a SHA-256 output can be perfectly predictable when its input follows a repeating pattern.

Next, I introduced synthetic cumulative phase jitter. Here, σ_t represents the standard deviation of the timing error added at each sampling step. I set σ_t = 5 ps, allowing small timing deviations to accumulate over time.

Using the same fixed-template predictor, I obtained:

- **0 ps jitter:** 100% prediction accuracy
- **5 ps jitter:** 49.99% prediction accuracy

For binary prediction, 49.99% is essentially chance-level performance.

Yet this result only shows that the fixed-template predictor could no longer exploit the original recurrence. It does not establish that the underlying source had become unpredictable.

*Did the source lose its regularity, or did the predictor simply lose the pattern it relied on?*

## Section 2: Why the Hash Output Loses Its Fixed-Lag Pattern

Did adding jitter erase the regularity of the original signal, or simply make it harder to detect after SHA-256?

To investigate, I compared bits separated by a lag of 32,000, the exact repetition period of the hash output in the noiseless case.

The key lies in how SHA-256 processes the input. In this experiment, each 256-bit block is hashed separately. Even if most raw bits match, a single differing bit makes two input blocks non-identical.

SHA-256 exhibits the *avalanche effect*: changing an input typically changes roughly half of the digest bits. This is a statistical tendency, not a guarantee for every pair of inputs.

I measured three quantities at the same lag: raw-bit agreement, exact matches between complete 256-bit input blocks, and SHA-256 output-bit agreement.

At **5 ps** of cumulative phase jitter, the results were:

- **92.52%** of raw bits matched.
- Only **1.19%** of complete input blocks matched exactly.
- **50.62%** of SHA-256 output bits matched.

Why such a large difference?

Matching most of the raw bits is not enough to reproduce an entire input block. All 256 bits must match for the blocks to be identical.

Let **q** represent the fraction of input blocks that match exactly, and **s** the output-bit match rate when the input blocks differ.

Identical inputs always produce identical SHA-256 digests. For differing inputs, the output bits match at rate s. Therefore, the overall output-bit match rate is:

![Equation 1: SHA-256 output-bit match rate](../figures/eq1_sha_match_identity.png)

In this experiment, s was approximately 0.5. The expression therefore simplifies to:

![Equation 2: Approximate output-bit match rate](../figures/eq2_sha_match_approx.png)

With q = 1.19%, this predicts an output-bit match rate of approximately **50.60%**, remarkably close to the observed **50.62%**.

![Figure 2: Raw-bit, block, and SHA-256 output agreement versus jitter](../figures/fig2_tds.png)

*Figure 2. Experiment D: Agreement at a fixed lag of 32,000 bits across different synthetic jitter settings. The three curves show raw-bit agreement, exact matching of 256-bit SHA-256 input blocks, and SHA-256 output-bit agreement. Results are aggregated over 30 random seeds, with 95% confidence intervals. The zero-jitter case is deterministic.*

SHA-256 did not create a new source of physical entropy. Instead, it made the periodic structure remaining in the raw bits much less visible at this particular lag.

Importantly, **a match rate near 50% at one fixed lag is not proof that every possible predictor will fail**.

That distinction leads to the next experiment: what happens if the predictor is allowed to discover its own lag?

## Section 3: What Happens When the Predictor Is Allowed to Search?

The previous experiment measured agreement at a fixed lag of 32,000 bits. But what if the predictor could search for a more useful lag on its own?

To test this, I designed a predictor that discovers repeating patterns without being given the theoretical periods of 2,000 or 32,000 bits.

I divided each bitstream chronologically into three parts:

- **Discovery (50%):** Search for candidate lags using autocorrelation.
- **Validation (20%):** Select the most accurate lag and determine whether the previous bit should be inverted.
- **Test (30%):** Evaluate the selected predictor on held-out data.

The predictor searches lags from 1 to 40,000 and evaluates the 64 strongest candidates on the validation segment. Its choice is fixed before testing begins.

During the test, it predicts each new bit using previously observed bits. This is **online next-bit prediction**, not a forecast of an entire unseen sequence. Earlier test bits may be used once they have been observed, but the current and future bits are never available in advance.

The following simplified code illustrates the core idea.

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

*For clarity, this excerpt omits the full implementation's minimum validation-gain requirement and majority-class fallback. The complete code is available in [experiment_F.py](../experiments/experiment_F.py).*

At **5 ps of synthetic jitter**, the results were:

**Table 1. Experiment F: Online prediction accuracy at 5 ps**

| Prediction target | Test accuracy |
|---|---:|
| **Raw oscillator bits** | **99.60%** |
| SHA-256 output bits | 50.59% |
| Shuffled raw-bit control | 49.96% |

![Figure 3: Online prediction accuracy of raw oscillator bits and SHA-256 output](../figures/fig3_blind_prediction.png)

*Figure 3. Experiment F: Online next-bit prediction accuracy across synthetic jitter settings. The left panel shows raw oscillator bits; the right panel shows SHA-256 output bits. Discovered-lag prediction is compared with prespecified-lag and first-order Markov baselines. Nonzero-jitter results are averaged over 12 seeds, with 95% confidence intervals.*

The difference is striking. The predictor achieved **99.60% accuracy on the raw oscillator bits**, even without knowing their theoretical period. Yet its accuracy on the SHA-256 output remained close to 50%.

These results describe two different prediction targets under the same online evaluation protocol. They do not establish that the SHA-256 output is unpredictable to every possible method. They also differ from the fixed-template experiment in Section 1.

There is another interesting result.

At **2 ps**, the SHA-256 predictor achieved 53.38% accuracy, compared with 52.29% when the lag was fixed at 32,000. The most frequently selected lag was 15,616.

This lag is divisible by 256, aligning with the hash input-block boundaries. It also nearly reproduces the oscillator phase:

15,616 × 4.9505 = 77,307.008

However, the 1.10-percentage-point difference alone is not enough to establish statistical superiority.

The main result is that the raw oscillator bits remained highly predictable, even when the SHA-256 output did not reveal a useful pattern to this predictor.

Why? At 5 ps, the predictor discovered a short recurrence at **lag 101**, rather than using the exact theoretical period of 2,000 bits.

Understanding why this shorter, imperfect period performed better requires looking at how phase error accumulates over time.

## Section 4: Why a Short Imperfect Period Can Beat a Perfect Long One

In the previous experiment, the predictor achieved 99.60% accuracy by looking just 101 samples into the past.

But why did it choose 101 samples instead of the exact repetition period of 2,000?

To understand this, consider what happens when a ring oscillator is sampled repeatedly.

If the oscillator returns to nearly the same point in its cycle, the sampled bit is likely to repeat. The number of samples between two observations is called the *lag*.

Without noise, waiting exactly 2,000 samples reproduces the original pattern perfectly.

However, in the cumulative phase-noise model, small timing errors build up over successive samples. A longer interval may provide better theoretical phase alignment, but it also allows more uncertainty to accumulate.

This creates a trade-off between two factors:

- **Phase alignment:** How closely the oscillator returns to the same point in its cycle.
- **Accumulated jitter:** How much timing uncertainty builds up between two observations.

A shorter, slightly imperfect recurrence can therefore be more useful for prediction than a longer, theoretically exact one.

At an oscillation-to-sampling frequency ratio of 4.9505, the oscillator completes almost exactly 500 cycles over 101 sampling intervals:

![Equation 3: Near phase recurrence at lag 101](../figures/eq3_lag101_recurrence.png)

The remaining phase offset is only 0.0005 cycles, equivalent to 10 ps at 50 MHz.

At higher jitter settings (20–50 ps), the predictor instead exploited another short relationship:

![Equation 4: Approximate half-cycle inversion at lag 10](../figures/eq4_lag10_inversion.png)

After 10 samples, the oscillator is almost half a cycle out of phase. Inverting the bit observed 10 samples earlier can therefore produce a useful prediction.

The accumulated noise explains why these short lags can work so well. In the cumulative phase random-walk model, the phase difference at lag L has a deterministic offset and a stochastic contribution:

![Equation 5: Deterministic phase offset and accumulated random-walk jitter](../figures/eq5_phase_jitter.png)

Here, the individual phase-increment errors ε_k are independent. Their accumulated timing uncertainty grows in proportion to the square root of the lag.

At 5 ps of jitter per sampling step:

**Table 2. Phase alignment and accumulated jitter**

| Lag (samples) | Deterministic phase offset | Accumulated jitter (standard deviation) |
|---:|---:|---:|
| 101 | 10 ps | approximately 50 ps |
| 2,000 | 0 ps | approximately 224 ps |

Lag 2,000 is perfectly aligned in the noiseless model, but its timing uncertainty is more than four times larger than that of lag 101.

At 5 ps, Experiment F achieved **99.60%** test accuracy with the discovered lag, compared with **98.20%** for the prespecified 2,000-sample lag. This is consistent with the phase-alignment and noise-accumulation trade-off.

These phase-offset and jitter values do not directly determine the bit error rate. Phase wrapping and the threshold used to sample a binary bit also matter.

The choice of lag matters even more at higher jitter. At 50 ps, Experiment D measured **49.62%** raw-bit agreement at a fixed lag of 32,000, while Experiment F achieved **98.50%** online prediction accuracy after searching for a useful lag. The former is a fixed-lag match rate; the latter is a prediction score from a different evaluation protocol. They must not be treated as two competing prediction accuracies.

Related phase-recurrence ideas also appear in work on coherent-sampling oscillator-based random number generators [3]. The experiments presented here use a separate synthetic model and do not reproduce that paper's hardware measurements.

## Section 5: Change the Noise Model, Change the Conclusion

So far, cumulative phase noise has driven SHA-256 prediction toward 50%. I next compared three noise processes at ratio 4.9505 and a 5 ps model setting:
- **Cumulative random walk:** independent phase increments accumulate.
- **AR(1) phase increments:** strongly correlated increments (ρ = 0.90) accumulate.
- **Independent phase perturbations:** phase offsets are independently resampled without accumulation.

The numerical setting of 5 ps does **not** represent equal physical noise power across the three models. This experiment tests sensitivity to temporal noise structure, not equal-strength noise sources.

Experiment G used six seeds, a 192,000-bit discovery budget, 40,000 validation bits, and a final 30% test split. These differ from Experiment F's protocol, so its 50.59% and Experiment G's 50.50% should not be treated as the same estimate.

**Table 3. Experiment G: Prediction accuracy at 5 ps and ratio 4.9505**

| Noise model | Raw-bit prediction accuracy | SHA-256 prediction accuracy |
|:--|--:|--:|
| Cumulative phase random walk | 99.60% | **50.50%** |
| AR(1) phase increments | 99.01% | **50.02%** |
| Independent phase perturbations | 99.94% | **92.50%** |

![Figure 4: Online prediction accuracy across phase-noise models](../figures/fig4_tds.png)

*Figure 4. Experiment G: Comparison of three phase noise models and online next-bit prediction accuracy at a frequency ratio of 4.9505 and jitter setting of 5 ps. Blue bars represent RO raw bits; orange bars represent SHA-256 outputs. Values are means across 6 seeds; error bars indicate 95% confidence intervals. The nominal jitter setting is not physically equivalent across models.*

Independent phase perturbations produced 92.50% SHA-256 prediction accuracy at ratio 4.9505. Varying the ratio changes the result:

**Table 4. Experiment G: SHA-256 prediction with independent phase perturbations at 5 ps**

| Oscillation-to-sampling ratio | SHA-256 prediction accuracy |
|--:|--:|
| 4.9505 | **92.50%** |
| approximately 4.953328 | **89.04%** |
| approximately 4.618034 | **57.01%** |
| 4.917321 | **50.15%** |

The ratio near 4.953328 is defined as 4.9505 + 0.002√2, which is irrational, yet gives 89.04% accuracy. In contrast, 4.917321 is rational (4,917,321/1,000,000) but gives only 50.15%. Thus, rationality itself is not the deciding factor. In these experiments, the relevant question is whether the lag search finds a useful approximate recurrence aligned to 256-bit block boundaries and whether that recurrence survives the chosen noise process.

![Figure 5: Sampling-ratio and phase-noise model sensitivity in raw and hashed bits](../figures/fig5_tds.png)

*Figure 5. Experiment G: Online next-bit prediction accuracy across four frequency ratios and three phase noise models at a 5 ps jitter setting. Left panel shows RO raw bits; right panel shows SHA-256 outputs. Each cell represents the 6-seed mean (darker shades indicate higher accuracy), evaluated using 192,000 discovery bits, 40,000 validation bits, and a 30% final test split. Frequency ratios "4.953328*" and "4.618034*" are rounded displays of 4.9505 + 0.002√2 and 4 + (√5 − 1)/2, respectively. The 5 ps value does not imply physically equivalent noise strength across models.*

Independent phase offsets do not accumulate. At ratio 4.9505, 256-bit input blocks exactly matched 84.96% of the time at lag 32,000, allowing substantial hash-output recurrence. That descriptive block-match rate is distinct from the 92.50% online prediction accuracy.

RO-based true random number generators can use physical oscillator jitter as an entropy source [2]. Real circuits also exhibit supply variation, temperature drift, and correlated noise; the synthetic random walk does not model all of these effects. Independent phase offsets serve only as a comparison model, not a description of PLL clocks.

What Experiment G demonstrates is that even with the exact same SHA-256 function, the predictability of the output depends heavily on the combination of the phase noise's temporal structure and the sampling ratio. The 92.50% figure is simply the outcome obtained under one specific combination of those conditions.

## Section 6: What a Failed Prediction Test Actually Tells Us

What does a prediction score near 50% actually establish?

It says that a particular predictor failed under a particular information and evaluation protocol.

It does not prove any of the following:
- That the generating process has lost all regularity.
- That a different predictor could never succeed.
- That the output is cryptographically secure or has sufficient entropy; entropy assessment requires separate evidence and procedures [1].

(Note: All experiments in this study are based on synthetic RO models and are not measurements from physical devices. Furthermore, the fixed-template prediction in Section 1, the simple match rates in Section 2, and the online predictions in Sections 3 and 5 were each designed under different evaluation conditions. For detailed implementations, confidence intervals, per-seed results, and additional model comparisons, please refer to the GitHub repository linked at the end of this article.)

I use five questions to interpret a prediction result:
1. **Target:** raw signal or conditioned output?
2. **Information:** fixed template or online access to observed history?
3. **Lag selection:** prespecified or learned from training data?
4. **Noise:** accumulated, correlated, or independently resampled?
5. **Other tests:** what do block matches and lagged correlations reveal?

## Closing: Randomness Is Not a Single Number

The opening sequences had identical histograms but different test accuracies: 100.00% and 1.34%. Their order, not their marginal distribution, made the difference.

The same distinction appears after SHA-256: with cumulative phase noise, a predictor found 99.60% accuracy on raw bits despite chance-level hash-output performance; under a different noise model and sampling ratio, even hashed bits reached 92.50%. These results apply only to the stated synthetic models and prediction protocols.

SHA-256 can obscure a specific recurrence without proving that the source is unpredictable.

**Prediction accuracy is a property of a particular test, not a certificate of randomness.**

## References and Reproducibility

All figures and equation images in this article were prepared by the author from synthetic experiments unless otherwise noted.

- [1] NIST, *Recommendation for the Entropy Sources Used for Random Bit Generation* (2018), NIST SP 800-90B. https://doi.org/10.6028/NIST.SP.800-90B
- [2] M. Baudet, D. Lubicz, J. Micolod, A. Tassiaux, *On the Security of Oscillator-Based Random Number Generators* (2011), Journal of Cryptology 24, 398–425. https://doi.org/10.1007/s00145-010-9089-3
- [3] A. Peetermans, V. Rožić, I. Verbauwhede, *Design and Analysis of Configurable Ring Oscillators for True Random Number Generation Based on Coherent Sampling* (2021), ACM Transactions on Reconfigurable Technology and Systems. https://doi.org/10.1145/3433166

Figure 5 can be recreated from the [Experiment G summary CSV](../data/experiment_G_highlights.csv) using the [Python regeneration script](../experiments/plot_G_ratio_sensitivity.py).

Implementation details can be verified in [the unknown-lag search code](../experiments/experiment_F.py), [the noise-model comparison code](../experiments/experiment_G.py), [the evaluation protocol audit](evaluation_protocol_audit.md), and [the theoretical notes on phase recurrence](phase_recurrence_theory.md). All results are derived from synthetic RO models and do not constitute physical device measurements, validations of hardware entropy rates, or evaluations of the cryptographic security of SHA-256.

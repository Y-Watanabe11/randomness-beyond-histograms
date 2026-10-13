# Theory note: sampling-ratio recurrence versus phase diffusion

This appendix supports [the A–G audit](evaluation_protocol_audit.md). It explains the finite-lag arithmetic and the simplified stochastic model used in the simulations. **It does not prove the security or entropy of a physical ring oscillator.**

## 1. Discrete phase sampler

Write the oscillator-to-sampling frequency ratio as \(r=m+\alpha\), where \(m\in\mathbb Z\) and \(0\leq\alpha<1\). In a zero-jitter model, the sampled phase in cycles is

\[
\phi_n=\{\phi_0+n\alpha\},\qquad B_n={\bf1}_{\phi_n\geq 1/2}.
\]

For lag \(L\), the noiseless relative phase is

\[
\delta_L=\{L\alpha\}.
\]

An *equal-bit* predictor wants \(\delta_L\) close to an integer. An *inverted-bit* predictor wants \(\delta_L\) close to a half-integer. Define phase errors (cycles)

\[
d_+(L)=\min(\delta_L,1-\delta_L),\qquad
d_-(L)=|\delta_L-\tfrac12|.
\]

**Do not conflate the mathematically closest phase recurrence with the lag selected by a noisy validation set.** For \(r=4.9505\):

| Lag | \(Lr\) (cycles) | Ideal relation | Error (cycles) |
|---:|---:|---|---:|
| 10 | 49.505 | approximate inversion | 0.005 |
| 101 | 500.0005 | approximate agreement | 0.0005 |
| 1,000 | 4,950.5 | exact inversion | 0 |
| 2,000 | 9,901 | exact agreement | 0 |

The audited script reports the lowest \( \min(d_+,d_-) \) **within a requested maximum lag**; F/G use an FFT-based, train-only ranking of *empirical bit* correlations, followed by separate validation. Short, imperfect lags can win under accumulated noise.

## 2. Why useful recurrences exist

Dirichlet's approximation theorem guarantees that for every real \(\alpha\) and positive integer \(Q\), there exists \(1\leq q\leq Q\) with

\[
\|q\alpha\|_{\mathbb Z}\leq \frac{1}{Q+1}
\]

(up to the common convention for indexing the denominator bound). This gives a **good integer-phase recurrence** with a finite but potentially long lag. Irrational \(\alpha\) also has fractional multiples dense modulo one, permitting approximations to half-cycle inversion; the finite-lag quality and the *best* lag still depend on \(\alpha\) and the search cap.

The golden-ratio fractional part \((\sqrt5-1)/2\) is badly approximable in the conventional number-theoretic sense: its especially resistant *asymptotic* rational approximation does **not** prevent a useful approximation for a finite threshold and search budget. All four ratios tested in G have arithmetic recurrences in 1..40,000; this is **not evidence** that all ratios have equally accurate *noisy bit* predictions in that same window.

## 3. Timing jitter and accumulated phase uncertainty

For the simulation's accumulated Gaussian increment model,

\[
\phi_n=\left\{\phi_0+n\alpha+\sum_{k=1}^{n}\epsilon_k\right\},\qquad
\epsilon_k\stackrel{\mathrm{iid}}{\sim}{\cal N}(0,\sigma_\epsilon^2).
\]

For samples separated by lag \(L\),

\[
\operatorname{Var}(\phi_n-\phi_{n-L}-L\alpha)
=L\sigma_\epsilon^2,\qquad
\sigma_{\Delta\phi}(L)=\sqrt L\,\sigma_\epsilon.
\]

In this code, \(\sigma_\epsilon=f_{\mathrm{RO}}\sigma_t\) in **cycles**, with \(f_{\mathrm{RO}}=50\,\mathrm{MHz}\) and nominal per-step timing-jitter standard deviation \(\sigma_t\). Thus (before modulo wrapping)

\[
\sigma_{\Delta\phi}(L)=f_{\mathrm{RO}}\sigma_t\sqrt{L}.
\]

This creates a *tradeoff*: longer lags may give a smaller deterministic phase offset \(d_+\) or \(d_-\), but generally accumulate more phase uncertainty. The predictor that maximizes observed accuracy is not necessarily the lag with the smallest deterministic error.

If the starting phase is uniform over a cycle and residual phase displacement is effectively deterministic, the expected same-bit probability for the symmetric half-cycle threshold is \(1-2d_+\), while inverted-bit agreement is \(1-2d_-\). In the stochastic case, these can only be used as local intuition: average over the actual *wrapped* random phase error and the actual sampling-phase distribution rather than inserting its standard deviation as if it were deterministic. In particular, numerical agreement rates from these simulations are contingent on the noiseless phase distribution and noise law.

### Different processes are different experiments

- **Random-walk phase:** independent step-to-step phase increments accumulate. A simple free-running oscillator can exhibit phase diffusion of this kind; white frequency noise can correspond to an approximately \(1/f^2\) phase-noise spectral region.
- **Correlated increments (AR(1)):** increments have correlation. The variance of lag-\(L\) phase displacement is no longer \(L\sigma_\epsilon^2\) for short or intermediate lags; covariance sums must be included.
- **Independent sampled phase perturbations:** the phase offset at each sample is independent instead of accumulating. Such a model contrasts with free-running diffusion and is **not** a general model of a PLL-locked oscillator.

Equal numerical settings such as “5 ps” are **not equivalent physical noise power or phase-noise spectra** across these three laws. Comparing their resulting prediction accuracies is a *model sensitivity* study, not a calibration of real devices.

## 4. Why SHA-256 changes the measured recurrence

Let \(q\) be the fraction of 256-bit input blocks **exactly equal** to their lag-aligned preceding blocks, and \(s\) be the empirical probability that corresponding SHA-256 output bits agree conditional on unequal input blocks. By total probability,

\[
p_{\rm hash}=q+(1-q)s.
\]

This is an **exact accounting identity for the sampled pairs**, because equal SHA inputs give equal outputs. If unequal blocks behave approximately as avalanche-randomized output comparisons, \(s\approx\tfrac12\), yielding

\[
p_{\rm hash}\approx \frac{1+q}{2}.
\]

This relationship is not a proof of SHA security, independence of outputs, or entropy creation. It is a diagnostic that explains the **particular lag-agreement metric** from experiment D. Never silently substitute this metric for B's *frozen-template hit rate*, E/F/G's *online next-bit hit rate*, or C's *plug-in conditional Shannon entropy*.

## 5. Practical interpretation for the article

The central claim is an **evaluation-protocol statement**:

> A low prediction accuracy from a specified observer on a specified transformed signal does not establish that the source is unpredictable to all observers.

A/D/F/G show how the observed number changes with data ordering, conditioning, available history, predictor search, and assumed phase dynamics. The experiments are educational/synthetic, not an empirical finding about fabricated CMOS devices, a quantified entropy-rate certificate, or a cryptanalytic attack.

## References and further reading

- [NIST SP 800-90B](https://csrc.nist.gov/pubs/sp/800/90/b/final), *Recommendation for the Entropy Sources Used for Random Bit Generation* (2018).
- [Dirichlet approximation theorem](https://en.wikipedia.org/wiki/Dirichlet%27s_approximation_theorem), standard theorem in Diophantine approximation; the inequality/convention should be checked when citing a specific formal statement.
- [Peetermans, Rožić, Verbauwhede](https://doi.org/10.1145/3433166), work on configurable ring oscillators and coherent sampling for TRNGs.
- [Baudet et al.](https://doi.org/10.1007/s00145-010-9089-3), *On the Security of Oscillator-Based Random Number Generators*.

#!/usr/bin/env python3
"""Experiment D: raw-bit recurrence, exact SHA input block recurrence, and output recurrence.

Reuses the toy model from experiments_BC.py. The three main metrics share the
same held-out positions (t >= TRAIN_CUT) and 32,000-bit lag. NOT hardware data,
an entropy-rate estimate, or a claim about cryptographic security.
Run: python experiments/experiment_D.py --replicates 30
Outputs are written to outputs/ (ignored by git).
"""
import argparse
import csv
import hashlib
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from experiments_BC import (
    generate, BASE_SEED, BLOCK_BITS, PERIOD, N, TRAIN_CUT, F_RO, NUM, DEN
)

OUT = Path(__file__).resolve().parents[1] / "outputs"
JITTER_PS = [0, .02, .05, .1, .2, .5, 1, 2, 5, 10, 20, 50]
METRICS = [
    "raw_bit_lag_agreement",
    "input_block_exact_match",
    "sha_bit_lag_agreement",
    "sha_bit_lag_predicted_from_block_match",
    "sha_diff_input_bit_agreement",
    "raw_first_template_accuracy",
    "sha_first_template_accuracy",
    "sha_input_bit_lag_agreement_within_changed_blocks",
]


def analyze_one(jitter_ps, replicate):
    seed = BASE_SEED + 999 * replicate
    raw = generate(jitter_ps, seed)
    assert N % BLOCK_BITS == TRAIN_CUT % BLOCK_BITS == PERIOD % BLOCK_BITS == 0
    assert TRAIN_CUT > PERIOD
    t = np.arange(TRAIN_CUT, N)
    earlier = t - PERIOD
    raw_lag = float(np.mean(raw[t] == raw[earlier]))
    raw_template = float(np.mean(raw[t] == raw[t % PERIOD]))

    inputs = np.packbits(raw.reshape(-1, BLOCK_BITS), axis=1)
    outputs = np.frombuffer(
        b"".join(hashlib.sha256(block.tobytes()).digest() for block in inputs),
        dtype=np.uint8,
    ).reshape(-1, BLOCK_BITS // 8)
    sha_bits = np.unpackbits(outputs.reshape(-1))
    sha_template = float(np.mean(sha_bits[t] == sha_bits[t % PERIOD]))
    sha_lag = float(np.mean(sha_bits[t] == sha_bits[earlier]))

    b = np.arange(TRAIN_CUT // BLOCK_BITS, N // BLOCK_BITS)
    previous = b - PERIOD // BLOCK_BITS
    inp_now, inp_prev = inputs[b], inputs[previous]
    sha_now, sha_prev = outputs[b], outputs[previous]
    identical = np.all(inp_now == inp_prev, axis=1)
    q = float(np.mean(identical))
    assert np.array_equal(sha_now[identical], sha_prev[identical])

    if np.any(~identical):
        sha_changed = float(np.mean(
            np.unpackbits(sha_now[~identical] ^ sha_prev[~identical]) == 0))
        raw_changed = float(np.mean(
            np.unpackbits(inp_now[~identical] ^ inp_prev[~identical]) == 0))
    else:
        sha_changed = raw_changed = float("nan")

    # Exact empirical decomposition versus idealized SHA avalanche approximation.
    approx = (1 + q) / 2
    if np.isfinite(sha_changed):
        assert abs(sha_lag - (q + (1 - q) * sha_changed)) < 1e-12
    assert abs(raw_lag - float(np.mean(np.unpackbits(inp_now ^ inp_prev) == 0))) < 1e-12
    assert abs(sha_lag - float(np.mean(np.unpackbits(sha_now ^ sha_prev) == 0))) < 1e-12
    return dict(
        jitter_ps=jitter_ps, replicate=replicate, seed=seed,
        raw_bit_lag_agreement=raw_lag,
        input_block_exact_match=q,
        sha_bit_lag_agreement=sha_lag,
        sha_bit_lag_predicted_from_block_match=approx,
        sha_diff_input_bit_agreement=sha_changed,
        raw_first_template_accuracy=raw_template,
        sha_first_template_accuracy=sha_template,
        sha_input_bit_lag_agreement_within_changed_blocks=raw_changed,
    )


def write_csv(path, records):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0]))
        w.writeheader()
        w.writerows(records)


def make_summary(rows, jitter_values):
    summaries = []
    for sigma in jitter_values:
        sub = [r for r in rows if r["jitter_ps"] == sigma]
        result = dict(jitter_ps=sigma, replicates=len(sub))
        for key in METRICS:
            vec = np.array([r[key] for r in sub], dtype=float)
            vec = vec[np.isfinite(vec)]
            result[key + "_mean"] = float(vec.mean()) if len(vec) else float("nan")
            result[key + "_ci95_halfwidth"] = (
                float(1.96 * vec.std(ddof=1) / np.sqrt(len(vec)))
                if len(vec) >= 2 else (0.0 if len(vec) else float("nan"))
            )
        summaries.append(result)
    return summaries


def plot(summaries):
    x = np.array([r["jitter_ps"] for r in summaries], dtype=float)
    top = [
        ("raw_bit_lag_agreement", "Raw bit agreement: lag 32,000"),
        ("input_block_exact_match", "Exact SHA-256 input blocks"),
        ("sha_bit_lag_agreement", "SHA-256 output bit agreement"),
        ("sha_bit_lag_predicted_from_block_match", "Predicted SHA agreement: (1+q)/2"),
    ]
    bottom = [
        ("raw_first_template_accuracy", "Raw bit: first-period template"),
        ("sha_first_template_accuracy", "SHA-256: first-period template"),
        ("sha_diff_input_bit_agreement", "SHA bits conditional on changed inputs"),
    ]
    fig, axes = plt.subplots(2, 1, figsize=(10.5, 10.2), sharex=True)
    for ax, series in zip(axes, (top, bottom)):
        for key, label in series:
            v = np.array([r[key + "_mean"] for r in summaries]) * 100
            ci = np.array([r[key + "_ci95_halfwidth"] for r in summaries]) * 100
            ax.plot(x, v, marker="o", linewidth=1.8, label=label)
            if np.isfinite(ci).all():
                ax.fill_between(x, v-ci, v+ci, alpha=.10)
        ax.axhline(50, linestyle=":", label="50% reference")
        ax.grid(alpha=.2)
        ax.set_ylim(0, 105)
        ax.set_ylabel("Agreement / accuracy (%)")
        ax.legend(frameon=False, fontsize=8.5)
    axes[0].set_title("Experiment D | Bits, complete hash inputs, hash outputs", loc="left")
    axes[1].set_title("Same held-out region | Template and changed-block comparison", loc="left")
    axes[1].set_xscale("symlog", linthresh=.02)
    axes[1].set_xticks(x, [str(v) for v in x], rotation=30)
    axes[1].set_xlabel("Synthetic per-step timing jitter (ps)")
    fig.tight_layout()
    fig.savefig(OUT / "experiment_D_mechanism.png", dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replicates", type=int, default=30)
    parser.add_argument("--jitter-ps", nargs="*", type=float, default=JITTER_PS)
    args = parser.parse_args()
    if args.replicates < 2 or not args.jitter_ps or min(args.jitter_ps) < 0:
        parser.error("Need >=2 replicates and nonnegative jitter values")
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for sigma in args.jitter_ps:
        for rep in range(args.replicates):
            rows.append(analyze_one(sigma, rep))
        recent = rows[-args.replicates:]
        fmt = lambda k: 100 * np.mean([r[k] for r in recent])
        print(f"{sigma:g} ps | raw={fmt('raw_bit_lag_agreement'):.2f}% "
              f"blocks={fmt('input_block_exact_match'):.2f}% "
              f"SHA={fmt('sha_bit_lag_agreement'):.2f}%", flush=True)
    summaries = make_summary(rows, args.jitter_ps)
    write_csv(OUT / "experiment_D_results.csv", rows)
    write_csv(OUT / "experiment_D_summary.csv", summaries)
    plot(summaries)
    with (OUT / "experiment_D_notes.md").open("w", encoding="utf-8") as f:
        f.write("# Experiment D — Same-lag comparison\n\n"
                "**Synthetic model; not physical RO data or security proof.**\n\n"
                f"RO {F_RO:g} Hz, ratio 4+{NUM}/{DEN}, N={N}; "
                f"holdout [{TRAIN_CUT},{N}), lag {PERIOD} bits. "
                f"{BLOCK_BITS}-bit SHA inputs, {args.replicates} seeds/setting.\n\n"
                "The three headline metrics use the same held-out positions. "
                "First-template baselines instead use the initial 32,000-bit template.\n\n"
                "q = fraction of exactly matching input blocks. "
                "SHA lag agreement = q + (1-q)*P(hash bits match | inputs differ). "
                "Under idealized avalanche behavior, this is approximately (1+q)/2.\n"
                "95% intervals are normal-approximation uncertainty for means across "
                "replicate seeds, not independent-bit confidence intervals.\n")
    assert all(abs(r["sha_bit_lag_agreement_mean"] -
                   r["sha_bit_lag_predicted_from_block_match_mean"]) < .015
               for r in summaries)
    print("PASS: equal-input hash identity and same-lag decomposition checks")


if __name__ == "__main__":
    main()

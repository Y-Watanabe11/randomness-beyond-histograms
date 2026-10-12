#!/usr/bin/env python3
"""Experiment E: multi-model online next-bit prediction on synthetic RO streams.

Compares raw bits with SHA-256-conditioned bits under a 70/30 chronological
holdout and identical target positions. Prequential protocol: the predictor
may observe actual previous test bits before predicting the next bit, but it
never observes the current target or future bits. Fitted models use train
targets ONLY. This is not a frozen all-at-once test forecast.

Features include known periods (2000 and 32000) by design; no test feature
selection. Exact histogram-preserving shuffle is a negative control.
NOT real hardware, an entropy estimate, or proof of cryptographic security.

Run: python experiments/experiment_E.py --replicates 6
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

from experiments_BC import (
    generate, sha_condition, BASE_SEED, N, TRAIN_CUT, DEN, PERIOD
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
LAGS = (1, 2, 3, 4, 8, 16, 32, DEN, PERIOD)
MAX_LAG = max(LAGS)
JITTER_PS = (0., .1, .5, 2., 5., 20., 50.)
MODELS = (
    "majority", "markov1", "markov2", "lag2000", "lag32000",
    "fixed_template_32000", "logistic_lags", "boosted_lags"
)


def features(bits, idx):
    """All features refer to strictly previous observed bits."""
    assert idx.min() >= MAX_LAG and idx.max() < len(bits)
    return np.column_stack([bits[idx-d] for d in LAGS]).astype(np.float32)


def fit_markov(bits, train_idx, order):
    """Train-only Laplace-smoothed transition frequencies."""
    if order == 1:
        code = bits[train_idx-1].astype(np.intp)
        n = 2
    elif order == 2:
        code = (2*bits[train_idx-1] + bits[train_idx-2]).astype(np.intp)
        n = 4
    else:
        raise ValueError(order)
    num = np.bincount(code, weights=bits[train_idx], minlength=n)
    den = np.bincount(code, minlength=n)
    return (num+1)/(den+2)


def evaluate(bits, *, sigma, rep, stream, control, ml_train_size, boost_iters):
    bits = np.asarray(bits, dtype=np.uint8)
    assert len(bits) == N
    train_idx = np.arange(MAX_LAG, TRAIN_CUT)
    test_idx = np.arange(TRAIN_CUT, N)
    y_train, y_test = bits[train_idx], bits[test_idx]
    assert train_idx.max() < test_idx.min()

    majority = int(np.mean(y_train) >= .5)
    p1, p2 = fit_markov(bits, train_idx, 1), fit_markov(bits, train_idx, 2)
    ctx1 = bits[test_idx-1].astype(np.intp)
    ctx2 = (2*bits[test_idx-1]+bits[test_idx-2]).astype(np.intp)
    predicted = {
        "majority": np.full_like(y_test, majority),
        "markov1": (p1[ctx1] >= .5).astype(np.uint8),
        "markov2": (p2[ctx2] >= .5).astype(np.uint8),
        "lag2000": bits[test_idx-DEN],
        "lag32000": bits[test_idx-PERIOD],
        # In contrast to the streaming forecasters, this reference is frozen.
        "fixed_template_32000": bits[test_idx % PERIOD],
    }
    size = min(ml_train_size, len(train_idx))
    selected = np.linspace(0, len(train_idx)-1, num=size, dtype=np.intp)
    fit_idx = train_idx[selected]
    X_fit, y_fit = features(bits, fit_idx), bits[fit_idx]
    X_test = features(bits, test_idx)
    if np.unique(y_fit).size < 2:
        predicted["logistic_lags"] = np.full_like(y_test, majority)
        predicted["boosted_lags"] = np.full_like(y_test, majority)
    else:
        logistic = LogisticRegression(
            solver="liblinear", max_iter=120, C=1., random_state=BASE_SEED)
        logistic.fit(X_fit, y_fit)
        predicted["logistic_lags"] = logistic.predict(X_test).astype(np.uint8)
        boosted = HistGradientBoostingClassifier(
            max_iter=boost_iters, max_leaf_nodes=15, max_depth=4,
            min_samples_leaf=80, learning_rate=.12, l2_regularization=2.,
            early_stopping=False, random_state=BASE_SEED)
        boosted.fit(X_fit, y_fit)
        predicted["boosted_lags"] = boosted.predict(X_test).astype(np.uint8)
    return [{
        "sigma_ps": sigma, "replicate": rep, "stream": stream,
        "control": "exact_shuffle" if control else "ordered",
        "predictor": name, "accuracy": float(np.mean(predicted[name] == y_test)),
        "test_bits": len(y_test), "train_bits": len(y_train),
        "ml_fit_bits": size if name.endswith("_lags") else 0,
        "past_test_bits_observed": name != "fixed_template_32000",
    } for name in MODELS]


def summarize(rows):
    grouped = {}
    for r in rows:
        key = (r["sigma_ps"], r["stream"], r["control"], r["predictor"])
        grouped.setdefault(key, []).append(r["accuracy"])
    out = []
    for (sigma, stream, control, predictor), vec in sorted(grouped.items()):
        a = np.asarray(vec, dtype=float)
        out.append({
            "sigma_ps": sigma, "stream": stream, "control": control,
            "predictor": predictor, "replicates": len(a),
            "accuracy_mean": float(a.mean()),
            "accuracy_sd": float(a.std(ddof=1)) if len(a)>1 else 0.,
            "accuracy_ci95_halfwidth": (
                float(1.96*a.std(ddof=1)/np.sqrt(len(a)))
                if len(a)>1 else float("nan"))
        })
    return out


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def plot_summary(summary, jitter_values):
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.6), sharey=True)
    models = ("majority", "markov2", "lag2000", "lag32000",
              "logistic_lags", "boosted_lags")
    x = list(jitter_values)
    for ax, stream in zip(axes, ("raw", "sha256")):
        for model in models:
            vals = [next((100*r["accuracy_mean"] for r in summary
                          if r["stream"]==stream and r["control"]=="ordered"
                          and r["predictor"]==model and r["sigma_ps"]==s),
                         float("nan")) for s in x]
            ax.plot(range(len(x)), vals, marker="o", lw=1.6, label=model)
        ax.axhline(50, linestyle=":", color="gray")
        ax.set_xticks(range(len(x)), [str(v) for v in x])
        ax.set_xlabel("Synthetic jitter (ps)")
        ax.set_title("Raw bits" if stream=="raw" else "SHA-256 output bits")
        ax.grid(alpha=.15)
    axes[0].set_ylabel("Online one-step-ahead held-out accuracy (%)")
    axes[0].set_ylim(40, 101)
    handles, labels = axes[1].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False,
               bbox_to_anchor=(.5, -.05))
    fig.suptitle("Experiment E | Same streaming holdout, multiple predictors")
    fig.tight_layout(rect=(0, .06, 1, .94))
    fig.savefig(OUT/"experiment_E_predictors.png", dpi=190,
                bbox_inches="tight")
    plt.close(fig)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--replicates", type=int, default=6)
    p.add_argument("--jitter-ps", type=float, nargs="*", default=list(JITTER_PS))
    p.add_argument("--ml-train-size", type=int, default=48000)
    p.add_argument("--boost-iters", type=int, default=35)
    args = p.parse_args()
    if args.replicates<1 or args.ml_train_size<100 or args.boost_iters<1:
        p.error("replicates>=1, ml-train-size>=100, boost-iters>=1 required")
    if not args.jitter_ps or any(s<0 for s in args.jitter_ps):
        p.error("jitter settings must be nonnegative and nonempty")
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for sigma in args.jitter_ps:
        for rep in range(args.replicates):
            raw = generate(sigma, BASE_SEED+999*rep)
            hashed = sha_condition(raw)
            for name, stream in (("raw", raw), ("sha256", hashed)):
                rows.extend(evaluate(
                    stream, sigma=sigma, rep=rep, stream=name, control=False,
                    ml_train_size=args.ml_train_size,
                    boost_iters=args.boost_iters))
            if sigma == 0 and rep == 0:
                rng = np.random.default_rng(BASE_SEED+555)
                for name, stream in (("raw", raw), ("sha256", hashed)):
                    shuffled = rng.permutation(stream)
                    assert np.array_equal(np.bincount(stream, minlength=2),
                                          np.bincount(shuffled, minlength=2))
                    rows.extend(evaluate(
                        shuffled, sigma=sigma, rep=rep, stream=name, control=True,
                        ml_train_size=args.ml_train_size,
                        boost_iters=args.boost_iters))
        for name in ("raw", "sha256"):
            chosen = [r["accuracy"] for r in rows
                      if r["sigma_ps"] == sigma and r["stream"] == name
                      and r["control"] == "ordered"
                      and r["predictor"] == "boosted_lags"]
            print(f"{sigma:g} ps {name}: boosted accuracy "
                  f"{100*np.mean(chosen):.3f}%", flush=True)
    s = summarize(rows)
    write_csv(OUT/"experiment_E_results.csv", rows)
    write_csv(OUT/"experiment_E_summary.csv", s)
    plot_summary(s, args.jitter_ps)
    with (OUT/"experiment_E_notes.md").open("w", encoding="utf-8") as f:
        f.write(
            "# Experiment E\n\nToy RO simulation, NOT physical data/security proof.\n"
            f"N={N}, train indices [{MAX_LAG},{TRAIN_CUT}), test "
            f"[{TRAIN_CUT},{N}); {args.replicates} seeded runs/condition.\n"
            f"Known lags: {LAGS}. ML fits a deterministic subsample of "
            f"{args.ml_train_size} training positions.\n\n"
            "Online streaming: past true test bits may be observed BEFORE "
            "the next bit is predicted. No current/future targets are features."
            " Training uses no held-out targets. Fixed-template comparator "
            "does not use observed test history. Exact-shuffle controls "
            "preserve each stream's original marginal histogram.\n"
            "Close-to-50% accuracy for tested predictors DOES NOT establish "
            "cryptographic security, entropy rate, or an information-theoretic "
            "unpredictability result.\n")
    print("PASS: chronological holdout and strictly past-time features.")


if __name__ == "__main__":
    main()

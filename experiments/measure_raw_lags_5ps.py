#!/usr/bin/env python3
"""Reproduce the raw-bit 2,000- and 32,000-lag agreement at 5 ps.

Synthetic cumulative-Gaussian phase model (not physical RO measurements).
Run: python experiments/measure_raw_lags_5ps.py
"""
from pathlib import Path
import csv
import numpy as np
from experiments_BC import generate, BASE_SEED, DEN, PERIOD, REPLICATES

SIGMA_PS = 5.0
ROOT = Path(__file__).resolve().parents[1]

def main():
    rows = []
    for rep in range(REPLICATES):
        seed = BASE_SEED + 999 * rep
        raw = generate(SIGMA_PS, seed)
        rows.append({
            "replicate": rep,
            "seed": seed,
            "raw_lag_2000_bit_agreement": float(np.mean(raw[DEN:] == raw[:-DEN])),
            "raw_lag_32000_bit_agreement": float(np.mean(raw[PERIOD:] == raw[:-PERIOD])),
        })
    for column in ("raw_lag_2000_bit_agreement", "raw_lag_32000_bit_agreement"):
        print(f"{column}: {np.mean([r[column] for r in rows]):.9f} ({np.mean([r[column] for r in rows])*100:.3f}%)")
    out = ROOT / "outputs" / "raw_lag_5ps_12seeds.csv"
    out.parent.mkdir(exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {out.relative_to(ROOT)}")

if __name__ == "__main__":
    main()

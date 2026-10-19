"""Closest block-aligned phase recurrence for each Experiment G frequency ratio.

For a lag L that is a multiple of 256, every bit in a 256-bit SHA-256 input
block is compared with the bit exactly L samples earlier, so all bits in the
block share the same deterministic phase offset

    delta_L = distance from L * r to the nearest integer (in oscillator cycles).

This script reports, for each ratio used in Experiment G, the block-aligned
lags up to MAX_LAG with the smallest offset, expressed in picoseconds at
f_RO = 50 MHz (period 20 ns). It uses only arithmetic; no simulation.
"""
import csv
import math
import sys

MAX_LAG = 40_000
BLOCK = 256
PERIOD_PS = 20_000.0  # 50 MHz oscillator

RATIOS = {
    "baseline_4.9505": 4.9505,
    "detuned_4.953328": 4.9505 + 0.002 * math.sqrt(2),
    "golden_4.618034": 4 + (math.sqrt(5) - 1) / 2,
    "detuned_4.917321": 4.917321,
}


def best_block_aligned(r, max_lag=MAX_LAG, block=BLOCK, top=3):
    rows = []
    for m in range(1, max_lag // block + 1):
        lag = block * m
        x = lag * r
        rows.append((abs(x - round(x)), lag))
    rows.sort()
    return rows[:top]


def main(out_path=None):
    writer = csv.writer(open(out_path, "w", newline="") if out_path else sys.stdout)
    writer.writerow(["ratio_label", "ratio_value", "rank", "lag", "offset_cycles", "offset_ps"])
    for label, r in RATIOS.items():
        for rank, (d, lag) in enumerate(best_block_aligned(r), start=1):
            writer.writerow([label, f"{r:.6f}", rank, lag, f"{d:.6f}", f"{d * PERIOD_PS:.1f}"])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)

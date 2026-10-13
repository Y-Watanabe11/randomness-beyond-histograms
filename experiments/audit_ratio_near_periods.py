#!/usr/bin/env python3
"""Audit deterministic near-integer and half-cycle lags of Experiment G's ratios.

This checks arithmetic resonances only; it does not infer a physical noise
spectrum or use any experimental test outcomes to choose lags.
"""
import csv
import math
from pathlib import Path
import numpy as np

RATIOS = {
    "baseline_4.9505": 4.9505,
    "detuned_4.953327": 4.9505 + 0.002*math.sqrt(2),
    "detuned_4.917321": 4.917321,
    "golden_4.618034": 4.0 + (math.sqrt(5)-1)/2,
}
BOUNDS=(100,1000,40000)
OUT=Path(__file__).resolve().parents[1]/"data"/"ratio_near_periods.csv"


def best_lag(ratio, maximum):
    # Evaluate fractional phase directly, not an approximate rounded ratio name.
    lag=np.arange(1,maximum+1,dtype=np.int64)
    phase=np.remainder(lag*(ratio%1),1.)
    same=np.minimum(phase,1-phase)
    invert=np.abs(phase-.5)
    error=np.minimum(same,invert)
    idx=int(np.argmin(error))
    return dict(lag=int(lag[idx]), phase_cycles=float(phase[idx]),
                distance_to_integer_or_half_cycle=float(error[idx]),
                relation="inverted" if invert[idx]<same[idx] else "same")


def main():
    rows=[]
    for name,ratio in RATIOS.items():
        for upper in BOUNDS:
            row=best_lag(ratio,upper)
            rows.append(dict(ratio_label=name,ratio_value=ratio,
                             max_lag=upper,**row))
            print(f"{name} max_lag={upper}: lag={row['lag']} "
                  f"relation={row['relation']} "
                  f"phase_error={row['distance_to_integer_or_half_cycle']:.8g} cycles")
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with OUT.open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)


if __name__=="__main__":
    main()

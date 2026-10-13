#!/usr/bin/env python3
"""Experiment F: blind lag discovery versus supplied-period baselines.

Time ordered, non-overlapping partitions:
  discovery [0, 50%): FFT search using only discovery prefix
  selection [50%,70%): choose one lag and orientation, or majority fallback
  evaluation [70%,100%): untouched final test

All predictions are one-step-ahead ONLINE: past test outcomes are available
before the current outcome. This is NOT a frozen multi-step forecast.
No real hardware data, no source-entropy or cryptographic security claim.
"""
from __future__ import annotations
import argparse
import csv
from collections import Counter
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import t as student_t
from experiments_BC import BASE_SEED,N,TRAIN_CUT,DEN,PERIOD,generate,sha_condition

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"outputs"
DISCOVERY_CUT=N//2
MAX_LAG=40000
CANDIDATES=64
MIN_GAIN=.01
JITTER_PS=(0.,.1,.5,2.,5.,20.,50.)
assert MAX_LAG < DISCOVERY_CUT < TRAIN_CUT < N

def discover_lag_candidates(prefix,max_lag=MAX_LAG,top_k=CANDIDATES):
    """Absolute centered autocorrelation ranks both positive and negative lags.
    Input MUST be restricted to discovery prefix by caller."""
    a=np.asarray(prefix,dtype=np.uint8)
    if a.ndim!=1 or len(a)<2*max_lag:
        raise ValueError("Need discovery prefix >= 2 * max_lag")
    z=a.astype(float)*2-1
    fftlen=1<<(2*len(z)-1).bit_length()
    f=np.fft.rfft(z,n=fftlen)
    dots=np.fft.irfft(f*f.conj(),n=fftlen)[1:max_lag+1]
    p=(1+dots/(len(z)-np.arange(1,max_lag+1)))/2
    strength=np.abs(p-.5)
    idx=np.lexsort((np.arange(max_lag),-strength))[:min(top_k,max_lag)]
    return [(int(i+1),float(strength[i])) for i in idx]

def majority(bits):
    return int(np.mean(bits[:TRAIN_CUT])>=.5)

def markov_predict(bits,indices):
    train=bits[:TRAIN_CUT]
    counts=np.bincount(2*train[:-1].astype(int)+train[1:].astype(int),minlength=4).reshape(2,2)
    probs=(counts[:,1]+1)/(counts.sum(axis=1)+2)
    return (probs[bits[indices-1]]>=.5).astype(np.uint8)

def choose_lag(bits,max_lag=MAX_LAG,top_k=CANDIDATES,min_gain=MIN_GAIN):
    """All choices locked before test. Train-only FFT, validation-only choice."""
    candidates=discover_lag_candidates(bits[:DISCOVERY_CUT],max_lag,top_k)
    vi=np.arange(DISCOVERY_CUT,TRAIN_CUT)
    actual=bits[vi]
    base=float(np.mean(actual==majority(bits)))
    best=None
    for lag,strength in candidates:
        agreement=float(np.mean(actual==bits[vi-lag]))
        flip=agreement<.5
        score=1-agreement if flip else agreement
        item=(score,-lag,lag,flip,strength)
        if best is None or item[:2]>best[:2]:
            best=item
    score,_,lag,flip,strength=best
    accept=bool(score-base>=min_gain)
    return dict(lag=int(lag) if accept else None,flip=bool(flip) if accept else False,
                accept=accept,validation_accuracy=float(score),
                validation_majority=float(base),strength=float(strength),
                candidates_examined=len(candidates))

def evaluate(bits,channel,sigma,rep,control="ordered",max_lag=MAX_LAG,
             top_k=CANDIDATES,min_gain=MIN_GAIN):
    bits=np.asarray(bits,dtype=np.uint8)
    assert len(bits)==N
    decision=choose_lag(bits,max_lag,top_k,min_gain)
    t=np.arange(TRAIN_CUT,N)
    y=bits[t]
    major=float(np.mean(y==majority(bits)))
    markov=float(np.mean(markov_predict(bits,t)==y))
    if decision["accept"]:
        pred=bits[t-decision["lag"]] ^ np.uint8(decision["flip"])
        blind=float(np.mean(pred==y))
    else:
        blind=major
    informed_lag=DEN if channel=="raw" else PERIOD
    informed=float(np.mean(bits[t-informed_lag]==y))
    return dict(sigma_ps=sigma,replicate=rep,stream=channel,control=control,
        blind_test_accuracy=blind,majority_test_accuracy=major,
        markov1_test_accuracy=markov,oracle_known_lag_test_accuracy=informed,
        blind_minus_markov=blind-markov,
        selected_lag=decision["lag"] if decision["accept"] else "",
        inverted=int(decision["flip"]) if decision["accept"] else "",
        selected=decision["accept"],
        val_selected_accuracy=decision["validation_accuracy"],
        val_majority_accuracy=decision["validation_majority"],
        discovery_score=decision["strength"],candidate_count=decision["candidates_examined"],
        discovery_bits=DISCOVERY_CUT,validation_bits=TRAIN_CUT-DISCOVERY_CUT,
        test_bits=N-TRAIN_CUT,streaming_previous_test_targets_visible=True)

def summary_rows(rows):
    groups={}
    for r in rows:
        k=r["sigma_ps"],r["stream"],r["control"]
        groups.setdefault(k,[]).append(r)
    out=[]
    metrics=("blind_test_accuracy","majority_test_accuracy","markov1_test_accuracy",
             "oracle_known_lag_test_accuracy","blind_minus_markov")
    for (sigma,stream,control),subset in sorted(groups.items()):
        lags=[r["selected_lag"] for r in subset if r["selected"]]
        item=dict(sigma_ps=sigma,stream=stream,control=control,
                  replicates=len(subset),
                  selected_fraction=float(np.mean([r["selected"] for r in subset])),
                  most_common_lag=Counter(lags).most_common(1)[0][0] if lags else "none")
        for m in metrics:
            vec=np.array([r[m] for r in subset],dtype=float)
            item[m+"_mean"]=float(vec.mean())
            item[m+"_ci95_halfwidth"]=(float(student_t.ppf(.975,len(vec)-1)*
                vec.std(ddof=1)/np.sqrt(len(vec))) if len(vec)>1 else float("nan"))
        out.append(item)
    return out

def write_table(name,rows):
    with (OUT/name).open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)

def plot(rows):
    fig,axes=plt.subplots(1,2,figsize=(12.7,5.4),sharey=True)
    levels=list(JITTER_PS)
    for ax,stream in zip(axes,("raw","sha256")):
        s={r["sigma_ps"]:r for r in rows if r["stream"]==stream and r["control"]=="ordered"}
        for key,label in (("majority_test_accuracy","Majority"),
                          ("markov1_test_accuracy","Markov-1"),
                          ("oracle_known_lag_test_accuracy","Known-lag reference"),
                          ("blind_test_accuracy","Blindly selected lag")):
            v=np.array([s[x][key+"_mean"] for x in levels])*100
            ci=np.array([s[x][key+"_ci95_halfwidth"] for x in levels])*100
            ax.plot(range(len(levels)),v,"o-",lw=1.8,label=label)
            ax.fill_between(range(len(levels)),v-np.nan_to_num(ci),
                            v+np.nan_to_num(ci),alpha=.10)
        ax.set_xticks(range(len(levels)),[str(x) for x in levels])
        ax.set_xlabel("Synthetic per-step jitter (ps)")
        ax.set_title("Raw oscillator bits" if stream=="raw" else "SHA-256 output bits")
        ax.axhline(50,color="gray",ls=":")
        ax.grid(alpha=.15)
    axes[0].set_ylabel("Streaming next-bit accuracy on untouched test (%)")
    axes[0].set_ylim(40,105)
    handles,labels=axes[1].get_legend_handles_labels()
    fig.legend(handles,labels,loc="lower center",ncol=4,frameon=False,
               bbox_to_anchor=(.5,-.03))
    fig.suptitle("Experiment F | Discovering predictive lags from history")
    fig.tight_layout(rect=(0,.06,1,.96))
    fig.savefig(OUT/"experiment_F_blind_discovery.png",dpi=180,bbox_inches="tight")
    plt.close(fig)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replicates",type=int,default=12)
    parser.add_argument("--shuffle-replicates",type=int,default=12)
    parser.add_argument("--max-lag",type=int,default=MAX_LAG)
    parser.add_argument("--top-k",type=int,default=CANDIDATES)
    parser.add_argument("--min-gain",type=float,default=MIN_GAIN)
    args=parser.parse_args()
    if (args.replicates<1 or args.shuffle_replicates<1 or args.max_lag<2
        or args.max_lag>=DISCOVERY_CUT//2 or args.top_k<1 or args.min_gain<0):
        parser.error("Invalid replicates, maximum lag or minimum gain")
    OUT.mkdir(parents=True,exist_ok=True)
    rows=[]
    for sigma in JITTER_PS:
        for rep in range(1 if sigma==0 else args.replicates):
            raw=generate(sigma,BASE_SEED+999*rep)
            hashed=sha_condition(raw)
            for channel,bits in (("raw",raw),("sha256",hashed)):
                rows.append(evaluate(bits,channel,sigma,rep,max_lag=args.max_lag,
                                     top_k=args.top_k,min_gain=args.min_gain))
            if sigma in (0.,5.) and rep==0:
                for sr in range(args.shuffle_replicates):
                    rng=np.random.default_rng(BASE_SEED+100000+1009*sr+int(sigma)*10)
                    for channel,bits in (("raw",raw),("sha256",hashed)):
                        shuffled=rng.permutation(bits)
                        assert np.array_equal(np.bincount(shuffled,minlength=2),
                                              np.bincount(bits,minlength=2))
                        rows.append(evaluate(shuffled,channel,sigma,sr,control="shuffled",
                                             max_lag=args.max_lag,top_k=args.top_k,
                                             min_gain=args.min_gain))
        for channel in ("raw","sha256"):
            selected=[r for r in rows if r["sigma_ps"]==sigma and r["stream"]==channel
                      and r["control"]=="ordered"]
            acc=100*np.mean([r["blind_test_accuracy"] for r in selected])
            lag=Counter([r["selected_lag"] for r in selected]).most_common(1)[0][0]
            print(f"{sigma:g} ps {channel}: blind={acc:.3f}%, most common lag={lag}",flush=True)
    summaries=summary_rows(rows)
    write_table("experiment_F_results.csv",rows)
    write_table("experiment_F_summary.csv",summaries)
    plot(summaries)
    with (OUT/"experiment_F_notes.md").open("w",encoding="utf-8") as f:
        f.write("# Experiment F — Blind lag discovery\n\n"
                "**Toy simulation, not measured hardware, randomness certification, "
                "or information-theoretic impossibility result.**\n\n"
                f"N={N}; discovery [0,{DISCOVERY_CUT}), validation "
                f"[{DISCOVERY_CUT},{TRAIN_CUT}), test [{TRAIN_CUT},{N}).\n"
                f"Search lags 1..{args.max_lag} on discovery via FFT. "
                f"Validate top {args.top_k}; require >={100*args.min_gain:g} percentage "
                "point gain over validation majority or use majority fallback.\n"
                "Test uses one-step online forecasting; earlier *observed* test bits "
                "may be used, but no current or future bits. The informed reference "
                "receives lag 2000 for raw and 32000 for SHA, but this is not a "
                "universal upper bound. Raw data have strong shorter near-periods "
                "(lag 101, lag 10 with inversion) from rational sampling ratio.\n"
                "CI: Student-t across independent simulation seeds, NOT over individual "
                "dependent bits; zero-jitter one deterministic realization has no CI. "
                "Repeated shuffles of a single sequence are permutation controls, "
                "not independent hardware trials.\n")
    print("PASS: two-stage train-only search, validation and untouched chronological test.")

if __name__=="__main__":
    main()

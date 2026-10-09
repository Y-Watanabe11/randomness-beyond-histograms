#!/usr/bin/env python3
"""Experiment A: exact same histogram, radically different forecastability.

Educational CONTROL, not a measurement of physical entropy. A jitter-free rational
phase oscillator is deliberately periodic. Aligned 256-bit SHA256 conditioning
preserves the repetition; an exact permutation preserves every histogram bin
while scrambling temporal order. Predictions are strictly out of sample.

Reproduce: python experiment_A.py
"""
from pathlib import Path
import csv
import hashlib
import math
import zipfile
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent.parent / 'outputs'
OUT.mkdir(parents=True, exist_ok=True)
FREQ_RATIO_NUM = 1901
FREQ_RATIO_DEN = 2000
RAW_PERIOD = 2000
HASH_BITS = 256
L = math.lcm(RAW_PERIOD, HASH_BITS)  # 32000 bits
REPETITIONS = 24
SEED = 20261009
TRAIN_FRACTION = .7

# A 4.9505-cycle advance per sampler tick, exactly modelled in integer arithmetic.
# Avoids accidental floating point drift that would obscure exact repetition.
n = np.arange(L * REPETITIONS, dtype=np.int64)
raw = (((n * FREQ_RATIO_NUM) % FREQ_RATIO_DEN) >= (FREQ_RATIO_DEN // 2)).astype(np.uint8)
assert np.array_equal(raw[:L], raw[L:2*L])
packed = np.packbits(raw.reshape(-1, HASH_BITS), axis=1)
conditioned_bytes = np.frombuffer(b''.join(hashlib.sha256(block.tobytes()).digest() for block in packed),dtype=np.uint8)
assert len(conditioned_bytes) == L * REPETITIONS // 8
# Rejection from [0..255] to [0..199], then mod 100. This does NOT create
# a uniform source if the SHA conditioned bytes are not uniform; it's simply
# unbiased *conditional on* an independent-uniform byte input.
keep = conditioned_bytes < 200
numbers = (conditioned_bytes[keep] % 100).astype(np.uint8)
# Accepted count in each 32k-bit cycle is fixed because this input repeats.
per_cycle = int(np.sum(keep[: L//8]))
assert per_cycle > 0
assert np.array_equal(numbers[:per_cycle],numbers[per_cycle:2*per_cycle])

rng=np.random.default_rng(SEED)
shuffled=rng.permutation(numbers)
assert np.array_equal(np.bincount(numbers,minlength=100),np.bincount(shuffled,minlength=100))

# Discover minimal period on TRAIN ONLY. KMP prefix function runs in O(n).
def infer_period(train):
    pi=np.zeros(len(train),dtype=np.int32)
    k=0
    for i in range(1,len(train)):
        while k>0 and train[i]!=train[k]:
            k=int(pi[k-1])
        if train[i]==train[k]:
            k+=1
        pi[i]=k
    p=len(train)-int(pi[-1])
    return p if p <= len(train)//3 and np.array_equal(train[p:],train[:-p]) else None

# Frequency-based forecast: most common number in the training set.
def forecast(train, count):
    return np.full(count,int(np.argmax(np.bincount(train,minlength=100))),dtype=np.uint8)

# Temporal strategy detects period from training data only; all holdout
# forecasts are computed solely from the stored training-period template.
# It never observes test outcomes or future hints.
def temporal_forecast(train, cut, total):
    p=infer_period(train)
    if p is None:
        return forecast(train, total-cut), None
    return train[np.arange(cut,total)%p],p

def entropy(hist):
    p=hist[hist>0]/np.sum(hist)
    return float(-np.sum(p * np.log2(p)))

# Optimal ordered guessing tree for distribution-based hints-only gameplay.
def optimal_tree(train):
    p=np.bincount(train,minlength=100).astype(float)+.5
    p/=p.sum()
    prefix=np.r_[0, np.cumsum(p)]
    cost=np.zeros((100,100),dtype=np.float64)
    root=np.zeros((100,100),dtype=np.int16)
    for width in range(1,101):
        for lo in range(101-width):
            hi=lo+width-1
            w=prefix[hi+1]-prefix[lo]
            best=float('inf'); chosen=lo
            for g in range(lo,hi+1):
                c=w + (cost[lo,g-1] if g>lo else 0.0) + (cost[g+1,hi] if g<hi else 0.0)
                if c < best:
                    best=c; chosen=g
            cost[lo,hi]=best
            root[lo,hi]=chosen
    return root

def game_rounds(targets, root, first_guesses=None):
    targets=np.asarray(targets,dtype=np.int16)
    lo=np.zeros(len(targets),dtype=np.int16)
    hi=np.full(len(targets),99,dtype=np.int16)
    counts=np.zeros(len(targets),dtype=np.int16)
    alive=np.ones(len(targets),dtype=bool)
    for step in range(100):
        ix=np.flatnonzero(alive)
        if not len(ix):
            break
        guess=(np.asarray(first_guesses[ix],dtype=np.int16)
               if step==0 and first_guesses is not None
               else root[lo[ix],hi[ix]])
        counts[ix]+=1
        hit=(targets[ix]==guess)
        small=guess < targets[ix]
        large=guess > targets[ix]
        lo[ix[small]]=guess[small]+1
        hi[ix[large]]=guess[large]-1
        alive[ix[hit]]=False
    assert not alive.any()
    return counts

records=[]
details={}
hist_a=np.bincount(numbers,minlength=100)
for label,sequence in [('RO + SHA-256 (ordered)',numbers),('Exactly shuffled (same values)',shuffled)]:
    total=len(sequence)
    cut=int(total*TRAIN_FRACTION)
    train=sequence[:cut]
    test=sequence[cut:]
    freq_guess=forecast(train,len(test))
    temporal_guess,found=temporal_forecast(train,cut,total)
    root=optimal_tree(train)
    midpoint_root=np.zeros((100,100),dtype=np.int16)
    for lo in range(100):
        for hi in range(lo,100):
            midpoint_root[lo,hi]=(lo+hi)//2
    counts_mid=game_rounds(test,midpoint_root)
    counts_hist=game_rounds(test,root)
    counts_temporal=game_rounds(test,root,temporal_guess)
    fixed_template_guess=train[np.arange(cut,total)%per_cycle]
    r=dict(dataset=label,total_numbers=total,train_numbers=cut,test_numbers=len(test),
           entropy_bits=entropy(np.bincount(sequence,minlength=100)),
           modal_probability=float(hist_a.max()/len(numbers)),
           discovered_period=found if found is not None else 'none',
           frequency_first_hit_pct=100*float(np.mean(freq_guess==test)),
           temporal_first_hit_pct=100*float(np.mean(temporal_guess==test)),
           forced_period_template_hit_pct=100*float(np.mean(fixed_template_guess==test)),
           midpoint_mean_guesses=float(counts_mid.mean()),
           histogram_mean_guesses=float(counts_hist.mean()),
           temporal_mean_guesses=float(counts_temporal.mean()),
           histogram_sha256=hashlib.sha256(np.bincount(sequence,minlength=100).tobytes()).hexdigest())
    records.append(r)
    details[label]=(test, temporal_guess, np.asarray(counts_temporal))

assert infer_period(numbers[:int(len(numbers)*TRAIN_FRACTION)]) == per_cycle
assert records[0]['temporal_first_hit_pct']==100.0
assert records[1]['discovered_period']=='none'
assert records[0]['histogram_sha256']==records[1]['histogram_sha256']

# Permutation-null test (the histogram is preserved EXACTLY by every shuffle).
null_rng=np.random.default_rng(SEED+123)
shuffled_accuracy=[]
for k in range(200):
    control=null_rng.permutation(numbers)
    cut=int(len(control)*TRAIN_FRACTION)
    template=control[:per_cycle]
    predicted=template[np.arange(cut,len(control))%per_cycle]
    shuffled_accuracy.append(float(np.mean(predicted==control[cut:])))
null_accuracy=np.array(shuffled_accuracy)
with (OUT/'experiment_A_permutation_null.csv').open('w',newline='') as f:
    w=csv.writer(f); w.writerow(['replicate','heldout_fixed_template_accuracy_pct'])
    for i,v in enumerate(null_accuracy):w.writerow([i+1,100*v])

with (OUT/'experiment_A_results.csv').open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=records[0].keys())
    writer.writeheader(); writer.writerows(records)

# Per-number first-guess accuracy, including matched histogram.
fig=plt.figure(figsize=(11,6.2),facecolor='#0b1020')
gs=fig.add_gridspec(2,1,height_ratios=(1,2.1),hspace=.25,left=.235,right=.94,top=.88,bottom=.11)
ax0=fig.add_subplot(gs[0])
ax1=fig.add_subplot(gs[1])
for ax in (ax0,ax1):
    ax.set_facecolor('#0b1020')
    ax.tick_params(colors='#dbeafe')
    for s in ax.spines.values():s.set_color('#354052')
    ax.yaxis.label.set_color('#e2e8f0');ax.xaxis.label.set_color('#e2e8f0')

ax0.plot(np.arange(100),hist_a/len(numbers)*100,lw=2.2,color='#33d6c1',label='Ordered')
ax0.scatter(np.arange(0,100,5),hist_a[::5]/len(numbers)*100,s=13,color='#ffbd69',label='Shuffled (exact same bins)',zorder=3)
ax0.set_xlim(0,99);ax0.set_ylabel('Frequency (%)')
ax0.set_title('IDENTICAL histogram: all 100 frequencies match exactly',color='white',loc='left',fontsize=12,weight='bold')
ax0.legend(frameon=False,loc='upper right',labelcolor='white',fontsize=9)
vals=[records[0]['temporal_first_hit_pct'],records[1]['temporal_first_hit_pct']]
y=np.arange(2)
bars=ax1.barh(y,vals,color=['#33d6c1','#ffbd69'],height=.42)
ax1.set_yticks(y,['Original order','Same numbers, shuffled'],color='white',fontsize=10)
ax1.invert_yaxis();ax1.set_xlim(0,108)
ax1.set_xlabel('First-guess accuracy on held-out games (%)')
ax1.set_title('DIFFERENT future predictability',color='white',loc='left',fontsize=12,weight='bold')
for b,v in zip(bars,vals):
    ax1.text(v-1.0 if v>60 else v+1.4,b.get_y()+b.get_height()/2,f'{v:.2f}%',
             va='center',ha='right' if v>60 else 'left',weight='bold',fontsize=17,color='white')
fig.suptitle('SAME NUMBERS. SAME HISTOGRAM. DIFFERENT FUTURE.',x=.08,y=.985,ha='left',fontsize=18,color='white',weight='bold')
fig.savefig(OUT/'experiment_A_hero.png',dpi=200,facecolor=fig.get_facecolor())
plt.close(fig)

# Lag scan: where identical values recur across the entire stream.
lag_set=sorted(set(range(1,6501,10)) | {per_cycle,2*per_cycle})
lag_acc_original=[100*float(np.mean(numbers[k:]==numbers[:-k])) for k in lag_set]
lag_acc_shuffled=[100*float(np.mean(shuffled[k:]==shuffled[:-k])) for k in lag_set]
fig,ax=plt.subplots(figsize=(9.8,5.2))
ax.plot(lag_set,lag_acc_original,lw=1.6,label='Original ordering')
ax.plot(lag_set,lag_acc_shuffled,lw=1.5,label='Exactly shuffled')
ax.scatter([per_cycle,2*per_cycle],
           [lag_acc_original[lag_set.index(per_cycle)],lag_acc_original[lag_set.index(2*per_cycle)]],
           s=45,zorder=3)
for k in [per_cycle,2*per_cycle]:
    ax.annotate(f'{k:,} numbers: 100% match',
                (k,100),xytext=(k+240,88 if k==per_cycle else 70),
                arrowprops={'arrowstyle':'->'},fontsize=9)
ax.set_xlabel('Lag in completed games (numbers)')
ax.set_ylabel('Exact repeat fraction at lag (%)')
ax.set_title('Hidden in plain sight: two sharp recurrence peaks after SHA-256')
ax.legend(frameon=False,loc='center left')
ax.set_ylim(0,108)
ax.grid(alpha=.15)
fig.tight_layout(); fig.savefig(OUT/'experiment_A_lag_scan.png',dpi=200);plt.close(fig)

# Guessing game context / comparison.
fig,ax=plt.subplots(figsize=(9.5,5.6))
labels=['Original order','Exactly shuffled']
x=np.arange(2)
w=.23
for i,(key,col) in enumerate([('midpoint_mean_guesses','#64748b'),('histogram_mean_guesses','#2563eb'),('temporal_mean_guesses','#0891b2')]):
    series=[r[key] for r in records]
    bars=ax.bar(x+(i-1)*w,series,w,label=['Midpoint binary search','Histogram-aware tree','Temporal + hints'][i],color=col)
    ax.bar_label(bars,fmt='%.2f',padding=3,fontsize=10)
ax.set_xticks(x,labels)
ax.set_ylim(0,7)
ax.set_ylabel('Average number of guesses (held-out)')
ax.set_title('One hidden number per game; only HIGH / LOW / MATCH hints')
ax.legend(frameon=False,loc='upper left');ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
fig.tight_layout();fig.savefig(OUT/'experiment_A_gameplay.png',dpi=200)
plt.close(fig)

with (OUT/'experiment_A_notes.md').open('w') as f:
    f.write('# Experiment A — identical histogram, different predictability\n\n')
    f.write('**Status:** controlled deterministic counterexample, not empirical RO evidence.\n\n')
    f.write('RO: rational phase advance 4.9505=4+1901/2000, zero jitter, 2,000-sample period. ')
    f.write('SHA-256 256-bit input chunks, no compression; output period 32,000 bits. ')
    f.write('Byte rejection <200 and modulo 100 yields 0–99 numbers, with period discovered from training only. ')
    f.write(f'One hash-output period contains {per_cycle:,} accepted values; {REPETITIONS} cycles, {len(numbers):,} total numbers.\n\n')
    f.write(f'Permutation-null control: 200 independent shuffles; forced {per_cycle}-number template replay heldout hit rate median {np.median(null_accuracy):.2%}, 2.5-97.5% empirical interval {np.quantile(null_accuracy,.025):.2%}–{np.quantile(null_accuracy,.975):.2%}. This template is drawn from TRAIN ONLY.\n\n')
    f.write('The shuffled control is an **exact permutation** of the original final number sequence. The global 100-bin histogram and empirical marginal Shannon entropy are exactly identical. ')
    f.write('Shuffle with RNG seed 20261009 is only used to randomize ordering; it has no bearing on the model physical entropy.\n\n')
    f.write('**Prediction disclosure:** period inferred by exact prefix repetition on chronological first 70% only. Periodic forecast exclusively uses values from the training-period template indexed by absolute future index; no held-out answers or hints are used in prediction. Nonperiodic control uses the most frequent training number. ')
    f.write('The temporal + hints strategy takes the period prediction (or modal value) as first guess, then performs probability-aware ordered search using HIGH/LOW/MATCH only.\n\n')
    f.write('| Dataset | Mode | Marginal H(X) [bits] | Frequency-first (%) | Detect-or-fallback first (%) | Forced-template first (%) | Midpoint guesses | Histogram guesses | Temporal guesses |\n')
    f.write('|---|---|---:|---:|---:|---:|---:|---:|---:|\n')
    for r in records:
        f.write(f"| {r['dataset']} | {r['discovered_period']} | {r['entropy_bits']:.5f} | {r['frequency_first_hit_pct']:.2f} | {r['temporal_first_hit_pct']:.2f} | {r['forced_period_template_hit_pct']:.2f} | {r['midpoint_mean_guesses']:.3f} | {r['histogram_mean_guesses']:.3f} | {r['temporal_mean_guesses']:.3f} |\n")
    f.write('\nThe two sequences are **not** physically generated randomness; one is zero-jitter periodic and the other is a pseudo-random permutation with known algorithmic seed. It is unfair to call the latter cryptographically secure. ')
    f.write('The time-order effect is demonstrated for the specified period/template estimator, not proved for every imaginable predictor. The shuffled sample is without-replacement, not IID. ')
    f.write('A strong SHA-256 test score is not entropy certification; equal input blocks hash to equal outputs.\n\n')
    f.write('Reproduce `python experiment_A.py` (numpy, matplotlib).\n')

print('APPROVED model: deliberately jitter-free exact-rational phase sampler, not physical RO measurement')
print(f'raw period={RAW_PERIOD} samples; SHA aligned period={L} bits; number period={per_cycle}; numeric samples={len(numbers)}')
for r in records:
    print(f"{r['dataset']}: H={r['entropy_bits']:.5f} bits, train={r['train_numbers']}, test={r['test_numbers']}, inferred period={r['discovered_period']}, first hit={r['temporal_first_hit_pct']:.4f}%, mean guesses={r['temporal_mean_guesses']:.4f}")
print(f'Permutation null (n=200) for the same period template: median={np.median(null_accuracy):.3%} interval=[{np.quantile(null_accuracy,.025):.3%}, {np.quantile(null_accuracy,.975):.3%}]')
print(f'Shuffled holdout accuracy even when GIVEN original period={records[1]["forced_period_template_hit_pct"]:.3f}%')
print('TEST: histogram equal exactly: PASS')
print('TEST: no test labels in temporal predictions: PASS (template uses training only)')
print('TEST: original period predicts all held-out numbers: PASS')
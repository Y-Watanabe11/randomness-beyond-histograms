#!/usr/bin/env python3
"""Medium RO Experiment B/C: timing jitter vs repeatability and entropy.

Toy PHASE RANDOM-WALK model, NOT a measurement of a real RO or a NIST entropy assessment.
Sampling ratio 4.9505 = 4+1901/2000. At zero jitter the raw bits have
period 2000; with 256-bit-block SHA-256 the output repeats every 32000 bits.

B: train-only fixed periodic template (from the first 32000 output bits) predicts
heldout SHA bits; compare to the majority-bit and iid Bernoulli baselines.
C: empirical marginal binary entropy, 1-step conditional entropy, lag-32000
conditional entropy and corresponding lag mutual information.

All quantities are simple empirical metrics, NOT entropy rate or security proofs.
"""
from pathlib import Path
import csv
import hashlib
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=Path(__file__).resolve().parent.parent / 'outputs'
OUT.mkdir(parents=True, exist_ok=True)
F_RO=50e6
NUM,DEN=1901,2000
BLOCK_BITS=256
PERIOD=math.lcm(DEN,BLOCK_BITS)   # 32000
CYCLES=12
N=PERIOD*CYCLES
TRAIN_FRAC=.7
BASE_SEED=20261009
REPLICATES=12
JITTER_PS=[0,0.02,0.1,0.5,1,2,5,10,20,50,100,500,2000]
BASE_PHASE=((np.arange(N,dtype=np.int64)*NUM)%DEN).astype(float)/DEN
RAW_REF=(BASE_PHASE >=.5).astype(np.uint8)
TRAIN_CUT=(int(N*TRAIN_FRAC)//BLOCK_BITS)*BLOCK_BITS
assert TRAIN_CUT%PERIOD != 0  # heldout boundary unrelated to the periodicity


def sha_condition(raw):
    blocks=np.packbits(raw.reshape(-1,BLOCK_BITS),axis=1)
    out=b''.join(hashlib.sha256(block.tobytes()).digest() for block in blocks)
    return np.unpackbits(np.frombuffer(out,dtype=np.uint8))


def generate(sigma_ps, seed):
    if sigma_ps == 0:
        return RAW_REF
    rng=np.random.default_rng(seed)
    # Noise in period increments: standard deviation f_RO*sigma_t cycles per sample.
    # Cumulative random walk models phase diffusion.
    incr=rng.normal(0.,F_RO*sigma_ps*1e-12,N)
    jitter=np.cumsum(incr)
    return ((BASE_PHASE+jitter)%1 >= .5).astype(np.uint8)


def h2(p):
    return -p*math.log2(p)-(1-p)*math.log2(1-p) if 0<p<1 else 0.0


def binary_stats(a, lag):
    """Plug-in H(Y) and conditional H(Y|X), where X=a[t-lag], Y=a[t]."""
    a=np.asarray(a,dtype=np.uint8)
    x=a[:-lag].astype(np.int64)
    y=a[lag:].astype(np.int64)
    cnt=np.bincount(2*x+y,minlength=4).reshape(2,2)
    n=cnt.sum(); pr=cnt/n
    py=pr.sum(axis=0)
    hx=h2(float(py[1]))
    hc=0.0
    for k in (0,1):
        nrow=float(pr[k].sum())
        if nrow:hc+=nrow*h2(float(pr[k,1]/nrow))
    return hx,hc,hx-hc,float(np.mean(x==y))


def evaluate(sigma_ps, rep):
    raw=generate(sigma_ps,BASE_SEED+999*rep)
    conditioned=sha_condition(raw)
    assert len(conditioned)==N
    train=conditioned[:TRAIN_CUT]
    test=conditioned[TRAIN_CUT:]
    # An explicitly privileged baseline: tell the predictor the period learned in A.
    # It only sees one template period of TRAIN data; it never reads heldout bits.
    guess=train[np.arange(TRAIN_CUT,N)%PERIOD]
    modal=np.uint8(np.mean(train)>=.5)
    # For actual guessing-game predictions, accept bytes under 200, then mod 100;
    # template from first 3090 numbers of training and compare heldout positions.
    by=np.packbits(conditioned).astype(np.uint8)
    accepted=(by[by<200]%100).astype(np.uint8)
    cut=int(len(accepted)*TRAIN_FRAC)
    if len(accepted)>=2*3090 and cut>=3090:
        temp=accepted[:3090]
        pred=temp[np.arange(cut,len(accepted))%3090]
        number_acc=float(np.mean(pred==accepted[cut:]))
        majority_num=int(np.argmax(np.bincount(accepted[:cut],minlength=100)))
        number_modal_acc=float(np.mean(accepted[cut:]==majority_num))
    else:
        number_acc=float('nan');number_modal_acc=float('nan')
    h_marg=h2(float(np.mean(test)))
    h1,hc1,mi1,_=binary_stats(conditioned,1)
    hlag,hclag,milag,match= binary_stats(conditioned,PERIOD)
    rawlagmatch=float(np.mean(raw[DEN:]==raw[:-DEN]))
    return dict(sigma_ps=sigma_ps,replicate=rep,
         conditioned_bit_one_fraction=float(np.mean(conditioned)),
         heldout_template_bit_accuracy=float(np.mean(test==guess)),
         heldout_majority_bit_accuracy=float(np.mean(test==modal)),
         lag_32000_bit_agreement=match,
         raw_lag_2000_bit_agreement=rawlagmatch,
         entropy_marginal=h_marg, entropy_marginal_whole=h1,
         entropy_conditional_lag1=hc1,
         entropy_conditional_lag32000=hclag,
         mutual_info_lag1=mi1,mutual_info_lag32000=milag,
         number_template_hit_rate=number_acc,number_modal_hit_rate=number_modal_acc,
         number_count=len(accepted))


if __name__=='__main__':
    rows=[]
    for s in JITTER_PS:
        for rep in range(REPLICATES):
            rows.append(evaluate(s,rep))
        print(f'jitter={s:g}ps: bit train-only template {np.mean([r["heldout_template_bit_accuracy"] for r in rows[-REPLICATES:]]):.5f}',flush=True)
    out=OUT/'experiments_BC_results.csv'
    with out.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)

    keys=['conditioned_bit_one_fraction','heldout_template_bit_accuracy',
          'heldout_majority_bit_accuracy','lag_32000_bit_agreement',
          'raw_lag_2000_bit_agreement','entropy_marginal',
          'entropy_conditional_lag1','entropy_conditional_lag32000',
          'mutual_info_lag1','mutual_info_lag32000',
          'number_template_hit_rate','number_modal_hit_rate']
    summaries=[]
    for s in JITTER_PS:
        subset=[r for r in rows if r['sigma_ps']==s]
        d={'sigma_ps':s,'replicates':REPLICATES}
        for k in keys:
            vec=np.array([r[k] for r in subset])
            d[k+'_mean']=float(vec.mean())
            d[k+'_q025']=float(np.quantile(vec,.025))
            d[k+'_q975']=float(np.quantile(vec,.975))
        summaries.append(d)
    with (OUT/'experiments_BC_summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(summaries[0]));w.writeheader();w.writerows(summaries)

    # C controlled shuffled baseline preserving exact bits and their histogram.
    rng=np.random.default_rng(BASE_SEED+77)
    zero=sha_condition(RAW_REF)
    shuffled=rng.permutation(zero)
    assert np.array_equal(np.bincount(zero,minlength=2),np.bincount(shuffled,minlength=2))
    zero_stats=binary_stats(zero,PERIOD)
    shuf_stats=binary_stats(shuffled,PERIOD)
    assert zero_stats[1]<1e-12

    def axis_common(ax):
        ax.spines[['top','right']].set_visible(False)
        ax.grid(alpha=.2)
    x=np.array(JITTER_PS,dtype=float)
    # x=0 plotted explicitly on a symmetric log scale (linthresh=.02)
    fig,ax=plt.subplots(figsize=(10,5.6))
    v=np.array([d['heldout_template_bit_accuracy_mean'] for d in summaries])*100
    lo=np.array([d['heldout_template_bit_accuracy_q025'] for d in summaries])*100
    hi=np.array([d['heldout_template_bit_accuracy_q975'] for d in summaries])*100
    ax.plot(x,v,marker='o',lw=2.5,label='Train-only period template')
    ax.fill_between(x,lo,hi,alpha=.22,label='Across-seed 2.5–97.5% range')
    bas=np.array([d['heldout_majority_bit_accuracy_mean'] for d in summaries])*100
    ax.plot(x,bas,marker='s',lw=1.5,alpha=.9,label='Training majority bit')
    ax.axhline(50,ls=':',color='#888',label='50% reference')
    ax.set_xscale('symlog',linthresh=.02)
    ax.set_xticks(x,labels=[str(v) for v in JITTER_PS],rotation=50)
    ax.set_xlim(-.008,2500)
    ax.set_ylim(40,105)
    ax.set_ylabel('Correct held-out SHA-256 output bits (%)')
    ax.set_xlabel('Per-sample oscillator phase-increment jitter (ps, toy model)')
    ax.set_title('EXPERIMENT B | A perfect repeating template loses predictive power as jitter grows',loc='left',fontsize=12)
    ax.legend(frameon=False,loc='upper right',fontsize=9)
    axis_common(ax);fig.tight_layout()
    fig.savefig(OUT/'experiment_B_jitter_prediction.png',dpi=210);plt.close(fig)

    fig,ax=plt.subplots(figsize=(10,5.8))
    for key,label in [('entropy_marginal','H(bit): marginal'),
         ('entropy_conditional_lag1','H(bit | previous bit)'),
         ('entropy_conditional_lag32000','H(bit | bit 32,000 positions earlier)')]:
        vals=np.array([d[key+'_mean'] for d in summaries])
        ax.plot(x,vals,marker='o',label=label,lw=2.2)
        qlo=np.array([d[key+'_q025'] for d in summaries]);qhi=np.array([d[key+'_q975'] for d in summaries])
        ax.fill_between(x,qlo,qhi,alpha=.13)
    ax.axhline(1,color='#888',ls=':',label='1 bit (Bernoulli half)')
    ax.set_xscale('symlog',linthresh=.02)
    ax.set_xticks(x,labels=[str(v) for v in JITTER_PS],rotation=50)
    ax.set_xlim(-.008,2500);ax.set_ylim(-.04,1.04)
    ax.set_ylabel('Plug-in entropy (bits per output bit)')
    ax.set_xlabel('Per-sample phase-increment jitter (ps, toy model)')
    ax.set_title('EXPERIMENT C | One-bit entropy hides a long-range deterministic dependency',loc='left',fontsize=12)
    ax.legend(frameon=False,loc='lower right',fontsize=9)
    axis_common(ax);fig.tight_layout()
    fig.savefig(OUT/'experiment_C_conditional_entropy.png',dpi=210);plt.close(fig)

    # Combined infographic with measured values only
    fig,axes=plt.subplots(1,2,figsize=(12.5,5.2))
    for ax in axes:axis_common(ax)
    axes[0].plot(x,100*np.array([d['heldout_template_bit_accuracy_mean'] for d in summaries]),'o-',lw=2)
    axes[0].axhline(50,ls=':',color='gray')
    axes[0].set_xscale('symlog',linthresh=.02)
    axes[0].set_xticks([0,.1,1,10,100,2000],['0','0.1','1','10','100','2000'])
    axes[0].set_ylim(42,103);axes[0].set_ylabel('Held-out correct bits (%)')
    axes[0].set_xlabel('Jitter (ps)')
    axes[0].set_title('PREDICTABILITY',loc='left',fontsize=12,weight='bold')
    axes[1].plot(x,[d['entropy_marginal_mean'] for d in summaries], 'o-',lw=2,label='H(bit)')
    axes[1].plot(x,[d['entropy_conditional_lag32000_mean'] for d in summaries], 's-',lw=2,label='H(bit | lag 32,000)')
    axes[1].set_xscale('symlog',linthresh=.02)
    axes[1].set_xticks([0,.1,1,10,100,2000],['0','0.1','1','10','100','2000'])
    axes[1].set_ylim(-.05,1.04);axes[1].set_xlabel('Jitter (ps)')
    axes[1].set_ylabel('Entropy (bits)')
    axes[1].set_title('INFORMATION',loc='left',fontsize=12,weight='bold')
    axes[1].legend(frameon=False,loc='lower right')
    fig.suptitle('WHEN DOES A REPEATING "RANDOM" STREAM STOP BEING PREDICTABLE?',fontsize=14,weight='bold')
    fig.tight_layout();fig.savefig(OUT/'experiments_BC_hero.png',dpi=210);plt.close(fig)

    with (OUT/'experiments_BC_notes.md').open('w') as f:
        f.write('# Experiments B and C: results and limitations\n\n')
        f.write('**Not physical RO measurements.** Toy cumulative Gaussian phase-increment jitter, not a calibrated physical RO phase-noise model. The model has a perfectly periodic zero-jitter limit.\n\n')
        f.write(f'RO ratio 4+{NUM}/{DEN}=4.9505; SHA-256 blocks of 256 bits; lag {PERIOD} bits; {N} output bits per condition/replicate; {REPLICATES} replicates, fixed seeds.\n')
        f.write(f'Train/holdout split at bit {TRAIN_CUT}/{N}. Template predictor is **given the known zero-jitter period of {PERIOD} bits** and reads only the first {PERIOD} bits of training; it uses no test outcomes. The test must be understood as predictability by *this specific attack with this assumed period*, not fundamental entropy or security.\n\n')
        f.write('For C, binary plug-in H(bit), H(bit | previous bit), and H(bit | bit PERIOD ago) computed on paired sequences. Plug-in conditional entropies do NOT equal entropy rates. They are descriptive single-lag statistics and can have finite-sample bias.\n\n')
        f.write('Zero-jitter exact-period control: H(Y | X_lag)=%.7f bits. Exactly shuffled zero-jitter control: %.7f bits; full zero-jitter pair matches %.5f; shuffle matches %.5f. Both retain identical marginal 0/1 counts.\n\n'% (zero_stats[1],shuf_stats[1],zero_stats[3],shuf_stats[3]))
        f.write('The SHA256 stage is a deterministic conditioner; its local output statistics cannot certify input entropy or cryptographic unpredictability.\n\n')
        f.write('Important processing limitation: mapping SHA bytes to 0–99 via rejection produces a variable count per 32k-bit block under jitter. The game-level periodic-template predictor can therefore lose *index alignment* even if the binary stream is only mildly perturbed. Bit-level comparison is the primary B/C endpoint; number-level accuracy is secondary.\n\n')
        f.write('A genuine RO device may have frequency drift, phase noise with non-Gaussian spectrum, shared power noise, metastability, and environmental modulation absent here. A cryptographically secure DRBG with real entropy must not be conflated with this model.\n\n')
        f.write('## Summary table\n\n')
        f.write('| Jitter ps | Template bit hit % | Marginal H | H(bit | 1-back) | H(bit | 32k-back) | Number template hit % |\n|---:|---:|---:|---:|---:|---:|\n')
        for d in summaries:
            f.write('| %.3g | %.2f | %.5f | %.5f | %.5f | %.2f |\n'%(d['sigma_ps'],d['heldout_template_bit_accuracy_mean']*100,d['entropy_marginal_mean'],d['entropy_conditional_lag1_mean'],d['entropy_conditional_lag32000_mean'],d['number_template_hit_rate_mean']*100))
    # Explicit checks that must fail on logic regressions
    d0=summaries[0]
    assert d0['heldout_template_bit_accuracy_mean']==1.0
    assert d0['entropy_conditional_lag32000_mean']<1e-9
    assert abs(d0['entropy_marginal_mean']-shuf_stats[0])<1e-5  # nearly identical contexts
    assert summaries[-1]['heldout_template_bit_accuracy_mean']<.55
    print('PASS: zero jitter exact period, shuffle histogram preserved, high-jitter prediction near chance')
    print('zero_jitter:',{k:round(d0[k],5) for k in ['heldout_template_bit_accuracy_mean','entropy_marginal_mean','entropy_conditional_lag1_mean','entropy_conditional_lag32000_mean','number_template_hit_rate_mean']})
    print('high_jitter:',{k:round(summaries[-1][k],5) for k in ['heldout_template_bit_accuracy_mean','entropy_marginal_mean','entropy_conditional_lag1_mean','entropy_conditional_lag32000_mean','number_template_hit_rate_mean']})
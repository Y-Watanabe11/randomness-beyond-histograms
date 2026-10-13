#!/usr/bin/env python3
"""Experiment G: sensitivity of blind one-step forecasting to oscillator model assumptions.

Pre-specified ratio, phase noise processes, timing-jitter SD and discovery budget.
Candidate lags 1..40000 selected using FFT on *only* discovery; the validation
segment selects sign and lag; the fixed final 30% is never used to select models.
Predictions use previously observed true bits (including earlier test bits),
never the current or future target. The same chronological final test positions
are used across all configurations.

Synthetic models only, not a real RNG or a cryptographic-security assessment.
"""
from __future__ import annotations
import argparse, csv, math
from pathlib import Path
from collections import Counter
import numpy as np
from scipy.signal import lfilter
from scipy.stats import t as student_t
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from experiments_BC import N, TRAIN_CUT, BASE_SEED, F_RO, sha_condition, RAW_REF
from experiment_F import discover_lag_candidates

OUT=Path(__file__).resolve().parents[1]/'outputs'
RATIOS={
    'baseline_4.9505': 4.9505,
    'detuned_4.953327': 4.9505 + 0.002*math.sqrt(2),
    'detuned_4.917321': 4.917321,
    'golden_4.618034': 4.0 + (math.sqrt(5)-1)/2,
}
NOISE_MODELS=('random_walk','ar1_increment','iid_phase')
JITTER_PS=(0.,5.,50.)
DISCOVERY_BUDGETS=(96000,144000,192000)
VALIDATION_LENGTH=40000
MAX_LAG=40000
TOP_K=64
MIN_GAIN=.01
RHO=.90


def base_bits(ratio):
    """Use exact integer baseline for the original 4.9505 setting."""
    if ratio == 4.9505:
        return RAW_REF.copy()
    phase=np.remainder(np.arange(N,dtype=np.float64)*(ratio%1.0),1.0)
    return (phase >= .5).astype(np.uint8)


def generate(ratio, sigma_ps, noise_model, seed):
    """Nominal sigma_ps specifies noise SD, but processes are NOT physically equivalent.

    Random walk: independent phase-increment perturbations accumulated over time.
    AR(1) walk: correlated increments, AR1 rho=0.90 and stationary SD sigma.
    IID phase: independent displacement of sampled phase, no accumulated phase walk.
    """
    assert noise_model in NOISE_MODELS and sigma_ps>=0
    if sigma_ps==0:
        return base_bits(ratio)
    rng=np.random.default_rng(seed)
    scale=F_RO*sigma_ps*1e-12
    if ratio == 4.9505:
        phase=((np.arange(N,dtype=np.int64)*1901)%2000)/2000.0
    else:
        phase=np.remainder(np.arange(N,dtype=np.float64)*(ratio%1.0),1.0)
    if noise_model=='random_walk':
        jitter=np.cumsum(rng.standard_normal(N)*scale)
    elif noise_model=='ar1_increment':
        white=rng.standard_normal(N+256)
        innovations=np.sqrt(1-RHO**2)*white
        correlated=lfilter([1.],[1.,-RHO],innovations)[256:]
        jitter=np.cumsum(correlated*scale)
    else:
        jitter=rng.standard_normal(N)*scale
    return (np.remainder(phase+jitter,1.0)>=.5).astype(np.uint8)


def select_lag(bits, discovery_end, validation_length=VALIDATION_LENGTH,
               max_lag=MAX_LAG, top_k=TOP_K, min_gain=MIN_GAIN):
    """No validation/test leakage into lag discovery; test never used for selection."""
    assert 2*max_lag<=discovery_end
    validation_end=discovery_end+validation_length
    assert validation_end<=TRAIN_CUT
    discovery=bits[:discovery_end]
    majority=int(np.mean(discovery)>=.5)
    candidates=discover_lag_candidates(discovery,max_lag,top_k)
    v=np.arange(discovery_end,validation_end)
    truth=bits[v]
    baseline=float(np.mean(truth==majority))
    best_score=-1.
    best_lag=None
    best_inv=False
    for lag,_ in candidates:
        match=float(np.mean(truth==bits[v-lag]))
        inversion=(match<.5)
        score=1-match if inversion else match
        if score>best_score+1e-12 or (abs(score-best_score)<1e-12 and lag<best_lag):
            best_lag=lag; best_score=score; best_inv=inversion
    accept=(best_score-baseline)>=min_gain
    return dict(selected=bool(accept),lag=int(best_lag) if accept else None,
                invert=bool(best_inv) if accept else False,
                validation_score=best_score,validation_baseline=baseline,
                discovery_end=discovery_end,validation_end=validation_end,
                majority=majority,selected_candidates=len(candidates))


def evaluate(bits, ratio_name, sigma_ps, noise_model,rep,channel,budget,control='ordered'):
    bits=np.asarray(bits,dtype=np.uint8)
    assert len(bits)==N
    result=select_lag(bits,budget)
    times=np.arange(TRAIN_CUT,N)
    truth=bits[times]
    majority=np.full(len(times),result['majority'],dtype=np.uint8)
    if result['selected']:
        pred=bits[times-result['lag']] ^ np.uint8(result['invert'])
    else:
        pred=majority
    # Markov transition frequencies fitted on same discovery prefix ONLY.
    prefix=bits[:budget]
    trans=np.bincount(2*prefix[:-1].astype(int)+prefix[1:].astype(int),minlength=4).reshape(2,2)
    p1=(trans[:,1]+1)/(trans.sum(axis=1)+2)
    markov=(p1[bits[times-1]]>=.5).astype(np.uint8)
    return dict(ratio=ratio_name,ratio_value=RATIOS[ratio_name],noise_model=noise_model,
                sigma_ps=sigma_ps,replicate=rep,channel=channel,
                discovery_bits=budget,validation_bits=VALIDATION_LENGTH,
                test_bits=len(times),control=control,
                blind_accuracy=float(np.mean(truth==pred)),
                majority_accuracy=float(np.mean(truth==majority)),
                markov1_accuracy=float(np.mean(truth==markov)),
                selected=result['selected'],selected_lag=(result['lag'] if result['selected'] else ''),
                inverted=(int(result['invert']) if result['selected'] else ''),
                validation_best=result['validation_score'],
                validation_majority=result['validation_baseline'],
                strictly_past=True)


def make_summary(rows):
    groups={}
    for r in rows:
        key=(r['ratio'],r['noise_model'],r['sigma_ps'],r['channel'],r['discovery_bits'],r['control'])
        groups.setdefault(key,[]).append(r)
    ans=[]
    for key, group in sorted(groups.items()):
        ratio,noise,sigma,channel,budget,control=key
        out=dict(ratio=ratio,noise_model=noise,sigma_ps=sigma,channel=channel,
                 discovery_bits=budget,control=control,replicates=len(group),
                 selection_rate=float(np.mean([r['selected'] for r in group])))
        for field in ('blind_accuracy','majority_accuracy','markov1_accuracy'):
            a=np.array([r[field] for r in group],dtype=float)
            out[field+'_mean']=float(a.mean())
            out[field+'_ci95_halfwidth']=(float(student_t.ppf(.975,len(a)-1)*a.std(ddof=1)/np.sqrt(len(a)))
                                           if len(a)>1 else float('nan'))
        lags=[str(r['selected_lag'])+('(-)' if r['inverted'] else '(+)')
              for r in group if r['selected']]
        out['mode_lag']=Counter(lags).most_common(1)[0][0] if lags else 'none'
        ans.append(out)
    return ans


def csv_write(path,rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)


def block_diagnostics(raw, hashed, ratio_name, noise_model, sigma, rep):
    """Same held-out window, 32k lag: bit, block and SHA matching.
    A 32k lag is naturally aligned ONLY for the original 4.9505 ratio.
    """
    t=np.arange(TRAIN_CUT,N)
    lag=32000
    raw_lag=float(np.mean(raw[t]==raw[t-lag]))
    hash_lag=float(np.mean(hashed[t]==hashed[t-lag]))
    bits=np.packbits(raw.reshape(-1,256),axis=1)
    k=np.arange(TRAIN_CUT//256,N//256)
    q=float(np.mean(np.all(bits[k]==bits[k-lag//256],axis=1)))
    return dict(ratio=ratio_name,noise_model=noise_model,sigma_ps=sigma,
                replicate=rep,raw_bit_match_32000=raw_lag,
                block_match_32000=q,sha_bit_match_32000=hash_lag,
                sha_bit_predicted_ideal=(1+q)/2)


def diagnostic_summary(rows):
    groups={}
    for r in rows:
        groups.setdefault((r['ratio'],r['noise_model'],r['sigma_ps']),[]).append(r)
    out=[]
    for (name,model,sigma),reps in sorted(groups.items()):
        d=dict(ratio=name,noise_model=model,sigma_ps=sigma,replicates=len(reps))
        for k in ('raw_bit_match_32000','block_match_32000',
                  'sha_bit_match_32000','sha_bit_predicted_ideal'):
            v=np.array([r[k] for r in reps]);d[k+'_mean']=float(v.mean())
            d[k+'_ci95_halfwidth']=(float(student_t.ppf(.975,len(v)-1)*v.std(ddof=1)/np.sqrt(len(v)))
                                       if len(v)>1 else float('nan'))
        out.append(d)
    return out


def plot_mechanism(diags):
    fig,ax=plt.subplots(figsize=(9,5))
    model_order=list(NOISE_MODELS)
    chosen=[next(r for r in diags if r['ratio']=='baseline_4.9505' and r['sigma_ps']==5.
                 and r['noise_model']==m) for m in model_order]
    x=np.arange(len(chosen)); w=.23
    for off,key,label in ((-w,'raw_bit_match_32000','Raw-bit agreement'),
                          (0,'block_match_32000','Exact SHA input blocks'),
                          (w,'sha_bit_match_32000','SHA-output bit agreement')):
        val=np.array([r[key+'_mean'] for r in chosen])*100
        error=np.array([r[key+'_ci95_halfwidth'] for r in chosen])*100
        ax.bar(x+off,val,width=w,label=label,yerr=error,capsize=3)
    ax.set_xticks(x,[m.replace('_',' ') for m in model_order]);ax.set_ylim(0,107)
    ax.set_ylabel('Same 32,000-bit lag match (%)');ax.grid(axis='y',alpha=.15)
    ax.set_title('Experiment G | 5 ps: noise model changes block recurrence')
    ax.legend(frameon=False,fontsize=9)
    fig.tight_layout();fig.savefig(OUT/'experiment_G_block_mechanism.png',dpi=170);plt.close(fig)


def make_figure(summary):
    # Sensitivity across four ratios and three distinct noise models.
    fig,axes=plt.subplots(2,3,figsize=(15,9),sharey=True)
    panels=(5.,50.)
    xs=np.arange(len(RATIOS))
    short={'baseline_4.9505':'4.9505','detuned_4.953327':'4.9533',
           'detuned_4.917321':'4.9173','golden_4.618034':'4.6180'}
    for row,sigma in enumerate(panels):
        for col,noise in enumerate(NOISE_MODELS):
            ax=axes[row,col]
            for channel in ('raw','sha256'):
                rs=[]
                for ratio in RATIOS:
                    selected=[r for r in summary if r['ratio']==ratio and r['noise_model']==noise
                              and r['sigma_ps']==sigma and r['channel']==channel
                              and r['control']=='ordered' and r['discovery_bits']==192000]
                    rs.append(selected[0]['blind_accuracy_mean']*100)
                ax.plot(xs,rs,marker='o',lw=2,label=channel)
            ax.axhline(50,ls=':',color='gray')
            ax.set_xticks(xs,[short[k] for k in RATIOS],rotation=20)
            ax.set_ylim(40,105);ax.grid(alpha=.2)
            ax.set_title(f'{noise.replace("_"," ")} | {sigma:g} ps')
            if col==0:ax.set_ylabel('Blind next-bit accuracy (%)')
    axes[0,2].legend(frameon=False,loc='best')
    fig.suptitle('Experiment G | Frequency ratio × phase-noise model sensitivity',fontsize=14)
    fig.tight_layout()
    fig.savefig(OUT/'experiment_G_sensitivity.png',dpi=170)
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,4.7),sharey=True)
    for ax,ch in zip(axes,('raw','sha256')):
        for noise in NOISE_MODELS:
            acc=[]
            for budget in DISCOVERY_BUDGETS:
                row=next(r for r in summary if r['ratio']=='baseline_4.9505'
                         and r['noise_model']==noise and r['sigma_ps']==5 and r['channel']==ch
                         and r['discovery_bits']==budget and r['control']=='ordered')
                acc.append(row['blind_accuracy_mean']*100)
            ax.plot(np.array(DISCOVERY_BUDGETS)/1000,acc,'o-',lw=2,label=noise)
        ax.set_title(ch);ax.axhline(50,ls=':',color='gray');ax.grid(alpha=.2)
        ax.set_xlabel('Discovery prefix (thousand bits)')
    axes[0].set_ylabel('Blind next-bit accuracy (%)')
    axes[0].legend(frameon=False)
    fig.suptitle('Learning-budget sensitivity: ratio 4.9505, synthetic 5 ps jitter')
    fig.tight_layout();fig.savefig(OUT/'experiment_G_training_budget.png',dpi=170)
    plt.close(fig)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--replicates',type=int,default=6)
    p.add_argument('--shuffle-replicates',type=int,default=6)
    args=p.parse_args()
    if args.replicates<2 or args.shuffle_replicates<2:p.error('At least 2 replicates required')
    OUT.mkdir(parents=True,exist_ok=True)
    rows=[]
    diagnostics=[]
    for name,ratio in RATIOS.items():
        # A noiseless case has one deterministic realization per ratio, not pseudo-replicates.
        zero=generate(ratio,0.,'random_walk',BASE_SEED)
        zero_sha=sha_condition(zero)
        diagnostics.append(block_diagnostics(zero,zero_sha,name,'none',0.,0))
        for channel,bits in (('raw',zero),('sha256',zero_sha)):
            for budget in DISCOVERY_BUDGETS:
                rows.append(evaluate(bits,name,0.,'none',0,channel,budget))
        print(f'{name}: noiseless done',flush=True)
        for noise in NOISE_MODELS:
            for sigma in (5.,50.):
                for rep in range(args.replicates):
                    bits=generate(ratio,sigma,noise,BASE_SEED+999*rep)
                    hashed=sha_condition(bits)
                    diagnostics.append(block_diagnostics(bits,hashed,name,noise,sigma,rep))
                    for channel,s in (('raw',bits),('sha256',hashed)):
                        for budget in DISCOVERY_BUDGETS:
                            rows.append(evaluate(s,name,sigma,noise,rep,channel,budget))
                    # Paired permutation controls on one prespecified scenario/budget.
                    if sigma==5. and noise=='random_walk' and rep==0:
                        for sr in range(args.shuffle_replicates):
                            rng=np.random.default_rng(BASE_SEED+50007*sr+1000*list(RATIOS).index(name))
                            for channel,s in (('raw',bits),('sha256',hashed)):
                                shuffled=rng.permutation(s)
                                assert np.array_equal(np.bincount(shuffled,minlength=2),
                                                      np.bincount(s,minlength=2))
                                rows.append(evaluate(shuffled,name,sigma,noise,sr,channel,
                                                     DISCOVERY_BUDGETS[-1],control='shuffle'))
                print(f'{name} {noise} sigma={sigma:g} ps done',flush=True)
    summary=make_summary(rows)
    csv_write(OUT/'experiment_G_results.csv',rows)
    csv_write(OUT/'experiment_G_summary.csv',summary)
    make_figure(summary)
    csv_write(OUT/'experiment_G_block_results.csv',diagnostics)
    ds=diagnostic_summary(diagnostics)
    csv_write(OUT/'experiment_G_block_summary.csv',ds)
    plot_mechanism(ds)
    with (OUT/'experiment_G_notes.md').open('w',encoding='utf-8') as f:
        f.write('# Experiment G: Sensitivity Analysis\n\n'
                'Synthetic model, NOT real RO measurements or TRNG security evidence.\n\n'
                'Common TEST = [268800,384000) for all conditions.  Three discovery '
                'prefixes (96000,144000,192000 bits), each followed by 40000-bit validation. '
                'FFT scan lag 1..40000, 64 candidates; sign selected using validation; '
                'minimum 1 percentage-point validation gain over discovery-fitted majority.\n'
                'Forecast is online, uses past **observed** test bits; no test targets used '
                'for model selection. Control shuffles preserve counts exactly.\n\n'
                'Noise processes are not equivalent even though called the same nominal sigma: '
                'random-walk white increments, AR1 correlated phase increments (rho=0.9), '
                'IID phase displacement without accumulation. Do not interpret numeric sigma '
                'as calibrated hardware jitter.\n\n'
                'CIs from Student-t across simulation seeds, not per-bit CIs. '
                'Zero noise is deterministic single trial; shuffle controls are permutations '
                'of one fixed synthetic series per ratio, not independent hardware sources.\n'
                'The rational/irrational-like labels are approximations under finite precision; '
                'finite decimal frequency ratio does not prove primitive period.\n'
                'Additional diagnostic computes exactly-aligned 32k-lag raw-bit, 256-bit-block '
                'and SHA-output matching on the common test interval. For detuned ratios, '
                '32k need not be the natural period.\n'
                'Models compared: blind signed-lag scan, prefix-fit majority, prefix-fit '
                'first-order Markov. Hyperparameters not tuned on final test.\n')
    print('PASS: train/validation/test separated, identical final test interval, exact shuffled controls')
    print('Summary:',len(summary),'condition summaries;',len(rows),'per-run records')

if __name__=='__main__':main()

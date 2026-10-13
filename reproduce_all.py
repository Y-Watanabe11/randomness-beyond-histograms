#!/usr/bin/env python3
"""Reproduce A–G with recorded commands, generated artifacts and checks.

Start from a CLEAN checkout and a fresh virtual environment for the clean-room
claim; this runner itself does not create a virtualenv. Full mode is costly.
  python reproduce_all.py --mode smoke
  python reproduce_all.py --mode full
A passing smoke run does NOT certify the full numerical results.
"""
import argparse,csv,datetime,hashlib,json,os,platform,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT/"outputs"

def table(path):
    with (ROOT/path).open(newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))

def close(label,observed,expected,tol,issues):
    if abs(observed-expected)>tol:
        issues.append(f"{label}: measured={observed:.9f}, expected={expected:.9f}, tolerance={tol}")

def match(rows,**selectors):
    hits=[r for r in rows if all(
        (float(r[k])==float(v) if k in ("jitter_ps","sigma_ps") else str(r[k])==str(v))
        for k,v in selectors.items())]
    if len(hits)!=1:raise ValueError(f"Expected one row for {selectors}; got {len(hits)}")
    return hits[0]

def check(mode):
    failures=[]
    necessary=["outputs/experiment_A_results.csv","outputs/experiment_D_summary.csv"]
    if mode=="full":
        necessary += ["outputs/experiments_BC_summary.csv",
                      "outputs/experiment_E_summary.csv",
                      "outputs/experiment_F_summary.csv",
                      "outputs/experiment_G_summary.csv",
                      "outputs/experiment_G_block_summary.csv",
                      "outputs/experiment_D_mechanism.png",
                      "outputs/experiment_E_predictors.png",
                      "outputs/experiment_F_blind_discovery.png",
                      "outputs/experiment_G_sensitivity.png"]
    for f in necessary:
        if not (ROOT/f).is_file():failures.append("Missing artifact: "+f)
    if failures:return failures
    dr=table("outputs/experiment_D_summary.csv")
    z=match(dr,jitter_ps="0")
    for k in ("raw_bit_lag_agreement_mean","input_block_exact_match_mean","sha_bit_lag_agreement_mean"):
        close("D zero jitter "+k,float(z[k]),1.,1e-12,failures)
    if mode=="smoke":return failures
    # Compare several prespecified endpoints with versioned published references.
    a=table("outputs/experiment_A_results.csv")
    ref_a=table("data/experiment_A_results.csv")
    if len(a)!=len(ref_a):failures.append("A row count differs")
    else:
        for i,(x,y) in enumerate(zip(a,ref_a)):
            for k in set(x)&set(y):
                try:close(f"A row {i} {k}",float(x[k]),float(y[k]),1e-7,failures)
                except (ValueError,TypeError):
                    if x[k]!=y[k]:failures.append(f"A row {i} {k} differs")
    bc=table("outputs/experiments_BC_summary.csv")
    r=match(bc,sigma_ps="5")
    close("B 5ps template",float(r["heldout_template_bit_accuracy_mean"]),.4999,.002,failures)
    close("C 5ps long-lag entropy",float(r["entropy_conditional_lag32000_mean"]),.99987,.002,failures)
    r=match(dr,jitter_ps="5")
    dref=match(table("data/experiment_D_headline.csv"),jitter_ps="5")
    for k in ("raw_bit_lag_agreement_mean","input_block_exact_match_mean","sha_bit_lag_agreement_mean"):
        close("D 5ps "+k,float(r[k]),float(dref[k]),.002,failures)
    e=table("outputs/experiment_E_summary.csv")
    er=match(e,sigma_ps="5.0",stream="raw",control="ordered",predictor="boosted_lags")
    close("E raw 5ps boosted",float(er["accuracy_mean"]),.9818547,.003,failures)
    er=match(e,sigma_ps="5.0",stream="sha256",control="ordered",predictor="boosted_lags")
    close("E SHA 5ps boosted",float(er["accuracy_mean"]),.5041522,.003,failures)
    f=table("outputs/experiment_F_summary.csv")
    for channel,expected in (("raw",.995997),("sha256",.505924)):
        fr=match(f,sigma_ps="5.0",stream=channel,control="ordered")
        close(f"F {channel} 5ps",float(fr["blind_test_accuracy_mean"]),expected,.003,failures)
    g=table("outputs/experiment_G_summary.csv")
    for model,expected in (("random_walk",.50495),("iid_phase",.92497)):
        candidates=[r for r in g if r.get("ratio")=="baseline_4.9505"
            and r.get("noise_model")==model and float(r.get("sigma_ps",-1))==5
            and r.get("channel")=="sha256" and int(r.get("discovery_bits",0))==192000
            and r.get("control")=="ordered"]
        if len(candidates)!=1:failures.append("Missing G "+model);continue
        close("G "+model+" SHA 5ps",float(candidates[0]["blind_accuracy_mean"]),expected,.005,failures)
    return failures

def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("--mode",choices=("smoke","full"),default="smoke")
    args=a.parse_args()
    OUT.mkdir(exist_ok=True)
    py=sys.executable
    jobs=[("unit_tests",[py,"-m","unittest","discover","-s","tests","-v"]),
          ("experiment_A",[py,"experiments/experiment_A.py"])]
    if args.mode=="smoke":
        jobs += [("experiment_D_smoke",[py,"experiments/experiment_D.py",
                                       "--replicates","2","--jitter-ps","0","5"])]
    else:
        jobs += [
            ("experiments_BC",[py,"experiments/experiments_BC.py"]),
            ("experiment_D",[py,"experiments/experiment_D.py","--replicates","30"]),
            ("experiment_E",[py,"experiments/experiment_E.py","--replicates","6"]),
            ("experiment_F",[py,"experiments/experiment_F.py","--replicates","12",
                             "--shuffle-replicates","12"]),
            ("experiment_G",[py,"experiments/experiment_G.py","--replicates","6",
                             "--shuffle-replicates","6"])]
    jobs.append(("ratio_audit",[py,"experiments/audit_ratio_near_periods.py"]))
    history=[];issues=[]
    for label,cmd in jobs:
        start=time.monotonic()
        path=OUT/("repro_"+label+".log")
        print("Running",label,"...",flush=True)
        with path.open("w",encoding="utf-8") as log:
            proc=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
                env={**os.environ,"MPLBACKEND":"Agg","PYTHONHASHSEED":"0"})
        history.append({"task":label,"command":cmd,"returncode":proc.returncode,
                        "seconds":round(time.monotonic()-start,2),"log":str(path.relative_to(ROOT))})
        print(" ",proc.returncode,history[-1]["seconds"],"seconds",flush=True)
        if proc.returncode:
            issues.append(f"{label} failed; see {path}")
            break
    if not issues:
        try:issues=check(args.mode)
        except Exception as e:issues=[repr(e)]
    status="PASS" if not issues else "FAIL"
    manifest={
       "status":status,"mode":args.mode,
       "completed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
       "python":sys.version,"platform":platform.platform(),
       "commit":subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,
           text=True,capture_output=True).stdout.strip() or None,
       "packages":{},"commands":history,"issues":issues,"sha256":{}
    }
    for pkg in ("numpy","matplotlib","scipy","sklearn"):
        try:manifest["packages"][pkg]=__import__(pkg).__version__
        except ImportError:manifest["packages"][pkg]="unavailable"
    for file in sorted(OUT.iterdir()):
        if file.is_file() and not file.name.startswith("repro_manifest"):
            manifest["sha256"][file.name]=hashlib.sha256(file.read_bytes()).hexdigest()
    file=OUT/f"repro_manifest_{args.mode}.json"
    file.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
    print(status,"manifest:",file,flush=True)
    for issue in issues:print("ERROR:",issue,flush=True)
    return 0 if not issues else 1

if __name__=="__main__":raise SystemExit(main())

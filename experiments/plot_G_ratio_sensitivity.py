#!/usr/bin/env python3
"""Regenerate Figure 5 from the checked-in Experiment G highlights (stdlib only).

Run from repository root:
  python experiments/plot_G_ratio_sensitivity.py
"""
import csv
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "experiment_G_highlights.csv"
DST = ROOT / "figures" / "fig5_ratio_model_sensitivity.svg"

with SRC.open(encoding="utf-8", newline="") as f:
    data = list(csv.DictReader(f))
chosen = {(r["ratio"], r["noise_model"]): r for r in data
          if float(r["sigma_ps"]) == 5 and int(r["discovery_bits"]) == 192000}
assert len(chosen) == 12
ratios = [("baseline_4.9505", "4.9505"),
          ("detuned_4.953327", "4.953328*"),
          ("detuned_4.917321", "4.917321"),
          ("golden_4.618034", "4.618034*")]
models = [("random_walk", "Random walk"),
          ("ar1_increment", "AR(1) increments"),
          ("iid_phase", "IID phase")]

def esc(s):
    return html.escape(str(s), quote=True)

def attrs(**kw):
    return " ".join(f'{key.replace("_","-")}="{esc(value)}"' for key,value in kw.items())

def label(x, y, s, **kw):
    return f'<text x="{x}" y="{y}" {attrs(**kw)}>{esc(s)}</text>'

def shade(v):
    a = max(0, min(1, (v-50)/50))
    low, high = (235,242,248), (34,93,137)
    return "#" + "".join(f"{round(p*(1-a)+q*a):02x}" for p,q in zip(low, high))

parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1210 425" role="img" aria-label="Experiment G accuracy by sampling frequency ratio and noise model">',
         '<rect width="1210" height="425" fill="#ffffff"/>',
         '<g font-family="Arial, Helvetica, sans-serif" fill="#202733">',
         '<text x="30" y="36" font-size="22" font-weight="bold">Experiment G: Predictability depends on ratio and noise model</text>',
         '<text x="30" y="61" font-size="13" fill="#64748b">5 ps synthetic jitter · 6 seeds · 192,000-bit discovery · 40,000-bit validation · online test</text>']
for panel,(field,title) in enumerate([("blind_raw_pct","Raw oscillator bits"),
                                     ("blind_sha256_pct","SHA-256 output bits")]):
    x0 = 162 + panel * 527
    parts.append(label(x0+194, 98, title, text_anchor="middle", font_size=17, font_weight="bold"))
    for j,(_,name) in enumerate(ratios):
        parts.append(label(x0+j*94+42, 125, name, text_anchor="middle", font_size=12, fill="#475569"))
    for i,(model,name) in enumerate(models):
        y = 145 + i*64
        if panel == 0:
            parts.append(label(143, y+35, name, text_anchor="end", font_size=13, fill="#334155"))
        for j,(ratio,_) in enumerate(ratios):
            value = float(chosen[(ratio,model)][field])
            x = x0 + j*94
            parts.append(f'<rect x="{x}" y="{y}" width="84" height="51" fill="{shade(value)}" rx="3"/>')
            parts.append(label(x+42, y+31, f"{value:.2f}%", text_anchor="middle", font_size=14,
                               font_weight="bold", fill="#ffffff" if value>=75 else "#20364a"))
    parts.append(label(x0+189,360, "(a) Raw-bit online prediction" if panel==0 else "(b) Hash-output online prediction",
                       text_anchor="middle", font_size=13, fill="#334155"))
parts.append(label(30,392,"* Rounded ratio labels: detuned = 4.9505 + 0.002√2; golden = 4 + (√5 − 1)/2.",font_size=12,fill="#64748b"))
parts.append(label(30,412,"Color scale: pale ≈50%, dark ≈100%. Values are per-condition means, not entropy estimates.",font_size=12,fill="#64748b"))
parts += ["</g>", "</svg>"]
DST.write_text("\n".join(parts)+"\n", encoding="utf-8")
print("Created", DST)

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
DST = ROOT / "figures" / "fig5_ratio_model_sensitivity_clean.svg"

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

parts = [
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1120 300" role="img" aria-label="Experiment G accuracy by sampling frequency ratio and noise model">',
    '<rect width="1120" height="300" fill="#ffffff"/>',
    '<g font-family="Arial, Helvetica, sans-serif" fill="#202733">'
]
for panel,(field,title) in enumerate([("blind_raw_pct","Raw oscillator bits"),
                                      ("blind_sha256_pct","SHA-256 output bits")]):
    x0 = 155 + panel * 485
    parts.append(label(x0+160, 34, title, text_anchor="middle", font_size=18, font_weight="bold"))
    for j,(_,name) in enumerate(ratios):
        parts.append(label(x0+j*82+36, 62, name, text_anchor="middle", font_size=13, fill="#475569"))
    for i,(model,name) in enumerate(models):
        y = 80 + i*60
        if panel == 0:
            parts.append(label(138, y+30, name, text_anchor="end", font_size=13.5, fill="#334155"))
        for j,(ratio,_) in enumerate(ratios):
            value = float(chosen[(ratio,model)][field])
            x = x0 + j*82
            parts.append(f'<rect x="{x}" y="{y}" width="72" height="46" fill="{shade(value)}" rx="3"/>')
            parts.append(label(x+36, y+29, f"{value:.2f}%", text_anchor="middle", font_size=14,
                               font_weight="bold", fill="#ffffff" if value>=75 else "#20364a"))
parts += ["</g>", "</svg>"]

DST.write_text("\n".join(parts)+"\n", encoding="utf-8")
print("Created", DST)

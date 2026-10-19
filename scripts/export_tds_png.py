#!/usr/bin/env python3
"""Export approved SVG figures and typeset equations as publication-ready PNGs.

Run from the repository root:
  python scripts/export_tds_png.py
Dependencies: cairosvg, matplotlib
"""
from pathlib import Path

import cairosvg
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"
WIDTH = 1600

SOURCES = {
    "fig1_identical_histograms_red.svg": "fig1_tds.png",
    "fig2_block_recurrence_single.svg": "fig2_tds.png",
    "fig4_source_model_sensitivity_revised.svg": "fig4_tds.png",
    "fig5_ratio_model_sensitivity_clean.svg": "fig5_tds.png",
}

# LaTeX source retained here so equations can also be entered in TDS's
# native Inline Math / Block Math editor instead of uploading images.
EQUATIONS = {
    "eq1_sha_match_identity.png": r"p_{\mathrm{SHA}} = q + (1 - q)s",
    "eq2_sha_match_approx.png": r"p_{\mathrm{SHA}} \approx \frac{1 + q}{2}",
    "eq3_lag101_recurrence.png": r"101 \times 4.9505 = 500.0005",
    "eq4_lag10_inversion.png": r"10 \times 4.9505 = 49.505",
    "eq5_phase_jitter.png": (
        r"\Delta\phi_L = \delta_L + \sum_{k=n-L+1}^{n}\varepsilon_k,"
        r"\qquad \sigma_{\Delta\phi}(L) = f_{\mathrm{RO}}\sigma_t\sqrt{L}"
    ),
}

for source, output in SOURCES.items():
    cairosvg.svg2png(
        url=str(FIG / source),
        write_to=str(FIG / output),
        output_width=WIDTH,
        background_color="#ffffff",
    )
    print(f"{source} -> {output} (1600 px wide)")

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "mathtext.fontset": "dejavusans",
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
})
for filename, expression in EQUATIONS.items():
    fig = plt.figure(figsize=(11.5, 1.3), dpi=160)
    fig.text(
        0.5, 0.5, "$" + expression + "$",
        ha="center", va="center", fontsize=22, color="#202733",
    )
    fig.savefig(
        FIG / filename, dpi=200, bbox_inches="tight", pad_inches=0.22
    )
    plt.close(fig)
    print(f"Equation -> {filename}")

# TDS Contributor Portal: article upload checklist (2026-10)

This repository's English submission candidate is [draft_TDS_EN.md](draft_TDS_EN.md).

**Platform update:** TDS replaced WordPress with its own Contributor Portal in
August 2026. The editor offers native Inline Math, Block Math, Code, Table,
and Image blocks. See:
https://www.worldprogramming.org/posts/how-to-format-your-tds-draft-a-new-and-improved-guide-d6mkuc

## Graphics

- Upload figures/fig1_tds.png, fig2_tds.png, fig4_tds.png, fig5_tds.png.
  These exports are generated from the approved SVG figures at 1600 px wide.
- Figure 3 remains figures/fig3_blind_prediction.png.
- The article now uses five native LaTeX display-math blocks (`$$ ... $$`)
  in [draft_TDS_EN.md](draft_TDS_EN.md), suitable for GitHub rendering and
  conversion to a typeset PDF. The five equation PNGs remain in `figures/`
  as optional fallbacks; original LaTeX is also preserved in
  [../scripts/export_tds_png.py](../scripts/export_tds_png.py).
- The Figure 1-5 captions now include **Image by author** sourcing credit.
  Keep these captions in the PDF or portal, and use the same attribution for
  any additional featured image prepared by the author.

## Text and code

- Copy sections as text and use H2 for section headings. The article title
  is entered separately, not as a second H1 in the body.
- Use the portal's Code block set to Python for the excerpt in Section 3.
  It is explicitly abridged; the complete implementation is
  [experiment_F.py](../experiments/experiment_F.py).
- Tables 1-4 can be built using the portal's Table block.
- Ordinary variables and simple units now use Unicode/plain text.
- The cited papers [1], [2], [3] are referenced in Sections 6, 5, 4
  respectively, and listed in References and Reproducibility.

## Before submitting

- Review the English wording yourself: this draft includes AI-assisted edits,
  and the current TDS policy on AI-generated prose should be confirmed
  with the editorial team before submission.
- Review paper metadata and all numerical claims against the experiment CSVs.
- Export a self-contained PDF from the Markdown for the first-time contributor
  application (accepted uploads: PDF/DOC/DOCX, max 50 MB). Confirm that its
  five figures, five typeset equations, four tables, and code are readable.
- Preview all figures/equations after any transfer to the portal. Relative
  Markdown links on GitHub are not necessarily imported automatically by TDS.
- Confirm the intended copyright/license for the source figures.
- Do not interpret a failed predictor or hash-bit agreement near 50% as
  a demonstration of cryptographic security or entropy sufficiency.

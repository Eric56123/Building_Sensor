# Correction list from the three reviews

Every item below was verified present in build 13. Items the reviews raised that
are **already fixed** or **wrong** are listed at the end so you know they were
checked rather than missed.

🔴 counted (costs words) · 🟢 uncounted (tables, captions, bibliography, appendix)

---

# Tier 1 — substantive errors

## ☐ 1 · 🟢 Table 3.12, the damping row

**Currently:**

> Damage alters stiffness only, leaving mass and damping unchanged | Partially
> contradicted. Loosening a screw removes no material, but Section 4.1.3 measures
> damping ratios spanning more than an order of magnitude across the three modes,
> which a proportional-damping model cannot represent

**Two errors in one cell.** Different modal damping in the *undamaged* structure
says nothing about whether damping *changes with damage*, which is the assumption
the row sits under. And classical proportional damping permits arbitrary modal
damping ratios by construction; only the two-parameter Rayleigh special case
constrains them.

**Replace with:**

> Not directly tested. Loosening removes negligible mass, and comparable damping
> estimates across damage states were not obtained. The measured undamaged modal
> damping ratios of 6.8, 0.7 and 0.2% show that the uniform 1% modal damping
> assumed in the four-storey development model is not representative of the rig.

## ☐ 2 · 🔴 §5.3.2, the same claim in prose

**Find:** `more than an order of magnitude and beyond what a proportional-damping model can represent, against 1% assumed at the four-storey stage`

**Replace:** `more than an order of magnitude, and strongly inconsistent with the uniform 1% modal damping assumed at the four-storey stage`

*Net −4 words.*

## ☐ 3 · 🟢 Table 3.13, reproducibility contradiction

**Find:** `Every figure and table in Chapters 3 and 4 regenerates from the raw captures through make_figures.py with no manual step`

**Replace:** `All classical modal results and all synthetic-network figures and tables regenerate from the raw captures through make_figures.py with no manual step. The archived real-rig predictions of Section 4.6.3 are the exception described below.`

*The disclosure further down is a strength. The absolute statement above it is what creates the contradiction.*

---

# Tier 2 — overclaim on root enumeration (6 sites, wording only)

Random multistart is strong numerical evidence, not proof that no further root
exists. Costs nothing scientifically; removes an easy attack.

## ☐ 4 · 🟢 Figure 4.11 title and list-of-figures entry
`Every exact solution at the base plate and Floor 1 is inadmissible`
→ `No admissible exact branch was recovered at the base plate or Floor 1`

## ☐ 5 · 🔴 §4.6.5
**Find:** `Multi-start enumeration (Section 4.6.5) settles all three and Table 4.16 lists every exact branch.`
**Replace:** `Multi-start search (Section 4.6.5) addresses all three, and Table 4.16 lists all distinct exact branches recovered from 3,000 random starts.`
*Net +3.*

## ☐ 6 · 🟢 Figure 4.11 in-figure caption
`Every exact solution at the base plate and Floor 1 is physically inadmissible`
→ `No admissible exact branch was recovered at the base plate or Floor 1`

## ☐ 7 · 🟢 Table 4.16 caption
**Find:** `Every exact solution of the three-parameter inversion, from 3,000 random starts per case.`
**Replace:** `All distinct exact branches of the three-parameter inversion recovered from 3,000 random starts per case.`

**Also in the same caption:** `The base plate and Floor 1 admit no admissible solution at all`
→ `No admissible branch was recovered at the base plate or Floor 1`

## ☐ 8 · 🟢 Table 4.16 footnote and §3.6.5
`why the solution set was enumerated rather than read from one optimisation`
→ `why branches were enumerated by multistart rather than read from one optimisation`

*(Two occurrences: the Table 4.16 footnote and §3.6.5.)*

---

# Tier 3 — typos and cross-references

## ☐ 9 · 🔴 Abstract
**Find:** `assigned every replicated severe runs correctly`
**Replace:** `correctly assigned every replicated severe run`

## ☐ 10 · 🔴 Conclusion
**Find:** `Re-parametrising by place does not repair it`
**Replace:** `Re-parametrising by plate does not repair it`

## ☐ 11 · 🔴 §4.6
**Find:** `The weight ablations of Tables 4.11 and 3.10`
**Replace:** `The weight ablations of Tables 4.11 and 4.12`

## ☐ 12 · 🔴 §3.6.6
**Find:** `the weight ablation is reported in Table 4.11`
**Replace:** `the weight ablation is reported in Table 4.12`

*Check which table actually holds the retargeted-model ablation before applying 11 and 12 — the two should not point at the same table if they describe different ablations.*

## ☐ 13 · 🔴 §4.3
**Find:** `Damage showed up below the lightest grade tested, though not at every location on every mode.`
**Replace:** `Damage was detectable at the lightest grade tested, though not at every location on every mode.`

*The sentences that follow describe the trace, one-eighth-turn case, which **is** the lightest grade tested.*

---

# Tier 4 — presentation

## ☐ 14 · 🟢 The `Appendix A. Appendix` running header (11 pages)

Caused by `\chapter{Appendix}` after `\appendix` — the class prefixes it, giving
"Appendix A. Appendix".

**Do not delete the chapter.** Removing it promotes A.1–A.6 to chapters, which
renumbers them A, B, C… and breaks every cross-reference. **Retitle it instead:**

```latex
\chapter{Supporting data and derivations}
```

Header becomes "Appendix A. Supporting data and derivations", and A.1–A.6 are
unaffected.

## ☐ 15 · 🟢 Bibliography, three entries

- Ribeiro & Lameiras: `doi: doi:10.1590/1679-78255308` → `doi: 10.1590/1679-78255308`
- Worden & Dulieu-Barton: `... - K. Worden, J. M. Dulieu-Barton, 2004, 2004.` — malformed, duplicated year and author list appended to the title. Rebuild from the journal record.
- Nale et al.: title is a scraped web page — `... Ferrara, Italy | Bulletin of Earthquake Engineering | Springer Nature Link`. Strip everything from the first `|`.

## ☐ 16 · 🟢 Figure 2.1 caption

**Currently:** `Where masonry housing and seismic hazard coincide. Each country is shaded by the share of its residential stock built without reinforcement.`

The figure shows masonry stock; it does not plot a hazard layer.

**Replace the title with:** `Global distribution of masonry residential stock`
then state in the caption that much of the high-masonry band also coincides with
high seismic hazard.

**Check the 61% while you are there.** The caption reads "built without
reinforcement" and cites 61% from da Porto et al. If that source reports 61%
*masonry* rather than 61% *unreinforced* masonry, the figure and the number do
not match. Either verify from the source or write "61% masonry".

---

# Tier 5 — additions (both free, both optional)

## ☐ 17 · 🟢 A conventions table before §4.6

The document carries six localisation denominators: `11 of 11`, `9 of 9`,
`18 of 18`, `6 of 6`, `3 of 6`, `14 of 24`. Each has a good reason; a reader who
doesn't reconstruct them could think cases were selectively counted.

| Analysis | Cases | Why |
|---|---|---|
| Fixed two-mode signature classification | 11 | Excludes the one run with no resolved Δf₃ |
| Fixed three-mode signature classification | 9 | Excludes all Floor 3 runs, f₂ voided by the second harmonic |
| Sensor relocation | 18 | 3 locations × 3 replicates × 2 alternative positions |
| Classical vs network localisation | 6 | Severe replicates at Floor 1 and Floor 2 only, the records both methods can score |
| Tap-scatter location feature | 24 | Replicate-level records across all four locations and four grades |

A table is uncounted, so this costs nothing.

## ☐ 18 · 🟢 Chapter 6 future work as a list

The 85–100 criteria name "well-developed and insightful ideas for future work"
explicitly. Breaking the four proposals into a bulleted list or a headed
subsection makes the rubric item findable rather than buried in prose.

---

# Tier 6 — needs the code

## ☐ 19 · Jacobian condition numbers (2.38 and 1.74)

Verify these come from the Jacobian of the **frequency residual** actually
minimised, not from the eigenvalue-sensitivity form φᵀ(∂K/∂k)φ. This affects only
how strongly conditioning can be claimed, not the inversion result. Add to the
repo work if it happens; skip otherwise.

---

# Checked and NOT needing action

- **"You may be under 10,000 words — expand §2.1 and §5.6."** You are at roughly
  11,919 against a 12,000 cap. Following this triggers the penalty it warns about.
- **"§4.1.5 contradicts itself on linearity."** Build 13 reports both statistics
  in one sentence and states that the trace grade rests elsewhere. Grepped for
  downstream claims of amplitude invariance: none found.
- **"Rewrite the opening hook."** Stylistic preference, and the current opening
  matches your register throughout.
- **"Check typography, Harvard style, equation numbering."** Already done.

# Change list — GEOL0056 dissertation

In **document order**, so you can work top to bottom. Each entry gives a search
string, the replacement, and where it sits.

**Legend:** 🔴 counted (costs words) · 🟢 uncounted (tables, captions, appendix — free)

⚠ **Four edits must move together** — marked **[SET A]** (localisation scores) and
**[SET B]** (the separation sentence). Changing one site and not the others leaves
the document contradicting itself.

---

## ABSTRACT

### ☐ 1 · 🔴 Typo
**Find:** `a single-low cost accelerometer`
**Replace:** `a single low-cost accelerometer`
*Net 0*

### ☐ 2 · 🔴 The twelve-run claim
**Find:** `assigned all twelve replicated severe runs correctly`
**Replace:** `assigned every replicated severe run correctly`
*Net −1. The 12-of-12 per-run score has no generator in the repository and is being removed everywhere.*

### ☐ 3 · 🔴 **[SET A]** Localisation scores
**Find:** `reaches 6 of 9 against the classical rule's of 9 of 9`
**Replace:** `calls 3 of 6 against the classical rule's 6 of 6`
*Net −2. Also fixes the stray "'s of". Base-plate calls are excluded: k₁ is the only answer the output space can give there.*

### ☐ 4 · 🔴 Grammar
**Find:** `moved on task metric beyond fold and seed scatter`
**Replace:** `moved no task metric beyond fold and seed scatter`
*Net 0*

### ☐ 5 · 🔴 Cut — duplicates the conclusion
**Find:** `The obstacle is the shear-chain model those routes share rather than the resolution of the measurement.`
**Replace:** `The obstacle is the shear-chain model those routes share.`
*Net −7. The contrast survives in the conclusion.*

---

## CHAPTER 3 — assumptions and methods tables

### ☐ 6 · 🔴 Stiffness ratio — drop the directional claim
**Find:** `of 1 : 1.192 : 0.983 show the storeys are not uniform, which is`
**Replace:** `of 1 : 1.192 : 0.983 show the middle storey is stiffest, which is`
*Net 0. Keep 0.983. Its 95% interval is [0.960, 1.006] and covers unity, so no claim about storey 3 survives — but k₂/k₁ excludes 1.0 under every convention.*

### ☐ 7 · 🟢 Same row, add the interval
Add to the table cell: `k₃/k₁ = 0.983, 95% interval [0.960, 1.006]`

### ☐ 8 · 🟢 Assumptions table — linearity
**Find:** `Section 4.1.5 bounds the consequence`
**Replace:** `Section 4.1.5 bounds any drive-induced shift at roughly 3.6%, too coarse for the trace grade, where the controls are the tap scatter of Table 4.5 and the reassembly floors of Section 4.1.4`

### ☐ 9 · 🟢 Table 3.10 — scoring rule
State **exact index matching**, not adjacency.
*The document's own 0.650 proves exact was used; adjacency predicts 0.714.*

---

## CHAPTER 4 — Results

### ☐ 10 · 🔴 §4.1.5 linearity sentence *(widest reach — cited as licensing every graded-series estimate)*
**Find:** `Swept-sine replicates at three drive amplitudes spanning a factor of 2.2 showed no statistically significant dependence of 𝑓1 on excitation level (t = -0.63, p = 0.573).`
**Replace:** `Swept-sine replicates at three drive amplitudes spanning 2.2× gave no detectable dependence of 𝑓1 on excitation level (t = −0.63, p = 0.573), but resolve only shifts above 3.6%; the trace grade therefore rests on the tap scatter of Table 4.5 (Appendix A.3).`
*Net +18. t and p reproduce exactly, but the test resolves only 3.6% shifts — above three of the four trace-grade shifts it is invoked to protect.*

### ☐ 11 · 🟢 Table 4.5 — caption
**Find:** `propagated from the tap standard deviations`
**Replace:** `the standard error of the difference between the five-tap damaged and baseline means, formed from the tap standard deviations of each`

### ☐ 12 · 🟢 Table 4.5 — one cell
Floor 3, light: `0.11` → `0.10` *(exact 0.10452)*

### ☐ 13 · 🟢 Tables A.1 and A.2 — captions
State the two baselines: **graded columns referred to Session 6, severe column to Session 4.**
*Currently invisible to a reader. This is the same defect as the scatter-basis error, and the audit's own first pass produced a false result by assuming one baseline.*

### ☐ 14 · 🔴 §4.3 opening — the amplitude range
**Find:** `Tap amplitude varied by roughly a factor of ten across sets, which Section 4.1.5 shows does not affect the frequency estimates, though`
**Replace:** `Tap amplitude varied by a factor of 2.5 across sets, inside the range tested in Section 4.1.5, though`
*Net −4. The 10× is the **superseded** campaign's figure, per the code's own docstring. Correcting it helps — the tested 2.2× nearly covers the real 2.5×.*

### ☐ 15 · 🟢 Scatter figure — caption
Name the basis: full range of Δf₁ in percentage points of the session baseline — a wider statistic on a different denominator than Table 4.5's standard deviation, hence **15.5 against 12.75** at base moderate.

### ☐ 16 · 🔴 **[SET B]** §4.4.1 — where the separation value originates
**Find:** `three-mode space against a largest replicate standard deviation of 1.7, and 26.6 against 2.1`
**Replace:** `three-mode space against a largest within-class distance of 3.09, and 26.6 against 2.1`
*Net −1. The 1.7 has no generator; nearest candidates are 1.78 and 1.83. The two-mode 2.1 is unchanged — 2.06 rounds to it under the corrected basis.*

### ☐ 17 · 🟢 Table 4.8 — remove the invalid inference
- Delete the **p column** (0.0001, 0.0001, 0.0042)
- Delete the **per-run row**
- Delete the caption's significance sentence
- Fix the caption's statement of the permutation unit — wrong as printed

*Exact values are 6.5e−05, 6.5e−05 and 0.0036; the 0.0001 entries were the sampling floor. But the run-level test is anticonservative and the group-level test has no power by construction, so no valid p exists.*

### ☐ 18 · 🔴 §4.4 — **add** the limitation paragraph *(this is the marks-earning addition)*
**Insert:**
> `No permutation test of the location effect is valid here. Permuting runs treats three replicates of one damage application as independent; permuting intact groups leaves the leave-one-out statistic unchanged by construction, so it has no power. Separating location from rebuild needs independent rebuilds per cell.`

*Net +45. Funded by items 5, 20, 21 and 26.*

### ☐ 19 · 🟢 Table 4.6 — caption
- Delete `and a permutation p = 0.0075`
- `identifies` → `is associated with`

### ☐ 20 · 🔴 Table 4.6 surrounding note
**Find:** `at a group permutation 𝑝 = 0.0075; the base-plate median`
**Replace:** `; the base-plate median`
*Net −6*

### ☐ 21 · 🟢 Table 4.16 — inversion branches
- Add the missing Floor 2 branch: **(2.521, 0.156, 0.365)**, marked not admissible
- Caption: 3 000 is the **attempted** count; converged is **1 275 / 560 / 1 581**
- Delete the `max|Δf|` column → replace with *"every branch fits to better than 1e-13 Hz"*

### ☐ 22 · 🟢 Table 4.18 — the localisation row **[SET A]**
- Replace the row with **6 of 6 (classical) / 3 of 6 (network)**, giving **6 of 9** as the base-inclusive alternative
- Add the forced-choice clause: base admits only k₁, so a correct call there measures the output space, not the model
- Delete `the archived Floor 3 case used imputed modes`
- **Replace the footnote** — currently reads `The two localisation scores are not computed over the same runs… and are not a matched comparison.`
  **New:** `Both columns are scored on the same measurements. The three Floor 3 severe replicates are excluded from both, their second modes being voided by the second harmonic of f₁ (Appendix A.1).`

> ⚠ The footnote is **wrong in your favour**. You have a matched comparison and disclaimed it. A controlled 3-of-6 is worth more than an uncontrolled 6-of-9.

### ☐ 23 · 🔴 §4.6 — the Floor 3 exclusion
**Find:** `The network cannot be scored on three of these because`
**Replace:** `Floor 3 is absent from both methods because`
*Net −2. The harmonic void removes them from **both** methods equally.*

---

## CHAPTER 5 — Discussion

### ☐ 24 · 🔴 **[SET A]** ⚠ **NOT IN THE AUDIT'S EDIT LIST — found while verifying**
**Find:** `Scored per run, the network reaches 6 of 9 across the graded cells, against the classical rule's 9 of 9 on the severe replicates (Table 4.18).`
**Replace:** `Scored per run, the network calls 3 of 6 against the classical rule's 6 of 6 on the same severe replicates (Table 4.18).`
*Net −4. Two errors here, not one: the scores, and "across the graded cells" — the 6-of-9 was severe cells, not graded ones. The audit's list named the abstract, Table 4.18 and the conclusion but missed this site.*

### ☐ 25 · 🔴 **[SET B]** Discussion — the separation sentence
**Find:** `separated by 33 floor-units against a largest replicate standard deviation of 1.7 (Section 4.4.1)`
**Replace:** `separated by 33.0 floor-units against a largest within-class distance of 3.09, a ratio of 10.7 (Section 4.4.1)`
*Net +3. Keep the cross-reference — §4.4.1 does contain the value (item 16). With the p-values gone, this ratio is the effect size carrying the result.*

### ☐ 26 · 🔴 §5.4 — the scatter p-value
**Find:** `location is recovered in 14 of 24 records against a chance rate of 25%, at a group permutation 𝑝 = 0.0075, and`
**Replace:** `location is partly recovered in 14 of 24 records against a chance rate of 25%, and`
*Net −6. 14 of 24 is 2.3× chance with no valid test — suggestive, not established. Do not give it the confident phrasing the localisation result earns.*

### ☐ 27 · 🔴 §5.4 — the scatter ratio
**Find:** `𝑓1 scatters 85 times more than 𝑓3`
**Replace:** `𝑓1 scatters 84 times more than 𝑓3`
*Net 0*

### ☐ 28 · 🔴 §5.4 — cut the self-restatement *(funds item 18)*
**Find:** `A first mode that moves 12.75% across five nominally identical taps on a fixed physical state, while the third mode holds to 0.15%, points to an amplitude-dependent contact condition`
**Replace:** `That points to an amplitude-dependent contact condition`
*Net −22. This restates the comparison made two sentences earlier as "85 times". The interpretive claim is untouched.*

---

## CONCLUSION

### ☐ 29 · 🔴 The twelve-run claim
**Find:** `12 of 12 replicated severe runs correct`
**Replace:** `every replicated severe run correct`
*Net −1*

### ☐ 30 · 🔴 **[SET A]** The comparison
**Find:** `it returns 9 of 9 where the network returns 6 of 9`
**Replace:** `it returns 6 of 6 where the network returns 3 of 6`
*Net 0*

---

## TABLE 5.1 · 🟢

### ☐ 31 · "Identify which plate was loosened" row
**Currently:** `Every replicated severe run assigned correctly: 12 of 12 under the per-run rule of Section 4.4.1 and 11 of 11 and 9 of 9 in fixed two- and three-mode signature spaces, at permutation p = 0.0001, 0.0001 and p = 0.0042. 18 of 18 at two further sensor positions`

**Replace with:** `Every replicated severe run assigned correctly in fixed two- and three-mode signature spaces (11 of 11, 9 of 9). 18 of 18 at two further sensor positions`

- Remove all three p-values
- Remove the 12-of-12 per-run figure
- Apply the **6 of 6 / 3 of 6** pair in the localisation comparison row

---

## APPENDIX · 🟢 all free

### ☐ 32 · The harmonic void — **four sites**
**Find (×4):** `2 𝑓1 = 4.98 Hz` → **Replace:** `2 𝑓1 = 4.97 Hz`
**Find (×3):** `𝑓2 falls through approximately 5.2 Hz` → **Replace:** `𝑓2 falls through 5.09 to 5.10 Hz, within 2.4 to 2.6% of the harmonic and so inside the 3% voiding tolerance`

> ⚠ This correction **strengthens** your argument. At 5.2 Hz the deviation from the harmonic is 4.57% — outside your own 3% tolerance — so as printed, a reader who checks concludes the Floor 3 records were dropped without cause.

### ☐ 33 · Appendix A.1 — the spread
**Find:** `spread of 0.15%`
**Replace:** `standard deviation of 0.15% against a range of 0.42%`

### ☐ 34 · Appendix A.1 — the ratio
**Find:** `The ratio of 8.010`
**Replace:** `The ratio of about 8.0`

### ☐ 35 · New Appendix A.3 — linearity detail displaced from item 10
Create, carrying: n = 3 per group, the extreme-gain comparison, 1.79% within-gain scatter, one-way ANOVA **F(2,6) = 8.29, p = 0.019** over all three gains, and the null regression on drive RMS (**p = 0.81**).

---

# Word budget

| | words |
|---|---|
| Additions (items 10, 18, 25) | **+66** |
| Reductions (2, 3, 5, 14, 16, 20, 23, 24, 26, 28, 29) | **−56** |
| **Net** | **+10** |

At 11,975 that gives **11,985** — fifteen words under the cap.

**That is not enough margin.** These deltas come from naive word splitting;
`texcount` handles `\cite{}`, math mode and macros by different rules, so the
real figure could land anywhere from +3 to +25. Going over 12,000 costs up to 10%,
which is worth more than every correction on this list.

☐ **Get to roughly 11,900 before submitting.** The cheapest route is relocation,
not cutting: move methodology detail that duplicates the code docstrings into an
appendix. Appendices are uncounted and the guidelines explicitly list supporting
detail and equation derivations as appendix material, so nothing is lost — it
just stops counting. Run `texcount -inc -sub=section main.tex` in Overleaf to see
which sections are heaviest.

---

# Still open

- **`F_MEASURED`** — f₂ = 8.04 and f₃ = 12.15 match neither Day-4 (8.123, 12.204) nor Day-6 (8.109, 12.187). The ratio reproduces exactly so nothing downstream moves. Safest fix: stop calling them measured; label them nominal or design values wherever quoted.
- **Coverage** — the Discussion body beyond the sentences above, Chapter 4 table by table beyond 4.5/A.1/A.2/4.16, the methodology parameter audit and the front matter were never swept. A number not in `reconciliation.csv` has not been checked.

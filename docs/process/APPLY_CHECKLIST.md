# Apply checklist — tables and prose data

Distilled from `audit/EDIT_LIST.md`. Two sections: **Part A** costs no words and
can be applied immediately; **Part B** touches counted text and needs the word
budget watched.

Apply Part A first. It is roughly two thirds of the corrections and carries no risk.

---

# PART A — Tables, captions, appendix (UNCOUNTED, free)

`texcount` excludes `table` and `figure` environments and their captions, and the
guidelines exclude tables, captions, references and appendices from the count.
Nothing here affects 11,975.

## A1 · Table 4.18 — localisation row
- [ ] Replace localisation row with **6 of 6 (classical) / 3 of 6 (network)**
- [ ] Give **6 of 9** as the base-inclusive alternative, in the same cell
- [ ] Add forced-choice clause: base admits only k₁, so a correct call there measures the output space, not the model
- [ ] Delete `the archived Floor 3 case used imputed modes`
- [ ] Replace footnote with: *"Both columns are scored on the same measurements. The three Floor 3 severe replicates are excluded from both, their second modes being voided by the second harmonic of f₁ (Appendix A.1)."*

> The old footnote claimed the comparison was unmatched. It was matched. This is an under-claim being corrected, not a retreat.

## A2 · Table 4.8 — permutation row
- [ ] Delete the **p column** entirely (0.0001, 0.0001, 0.0042)
- [ ] Delete the **per-run row** (no generator exists in the repository)
- [ ] Delete the caption's significance sentence
- [ ] Fix the caption's statement of the permutation unit — it is wrong as printed

## A3 · Table 4.6 — caption
- [ ] Delete `and a permutation p = 0.0075`
- [ ] `identifies` → `is associated with`

## A4 · Table 5.1 — "Identify which plate was loosened" row
- [ ] Remove all three p-values
- [ ] Remove the 12-of-12 figure
- [ ] Apply the **6 of 6 / 3 of 6** pair

## A5 · Table 3.10 — scoring rule
- [ ] State **exact index matching**, not adjacency

> The document's own 0.650 at l.2415 proves exact was used; adjacency predicts 0.714.

## A6 · Table 4.5
- [ ] Caption: `propagated from the tap standard deviations` → **`the standard error of the difference between the five-tap damaged and baseline means, formed from the tap standard deviations of each`**
- [ ] Cell, Floor 3 light: **`0.11` → `0.10`** (exact 0.10452)

## A7 · Table 4.16 — inversion branches
- [ ] Add the missing Floor 2 branch: **(2.521, 0.156, 0.365)**, marked not admissible
- [ ] Caption: 3 000 is the *attempted* count; converged is **1 275 / 560 / 1 581**
- [ ] Delete the `max|Δf|` column → replace with *"every branch fits to better than 1e-13 Hz"*
- [ ] Add k₃/k₁ = 0.983, **95% interval [0.960, 1.006]** (covers unity)

## A8 · Scatter figure caption
- [ ] Name the basis: full range of Δf₁ in percentage points of the session baseline — a wider statistic on a different denominator than Table 4.5's standard deviation, hence **15.5 against 12.75** at base moderate

## A9 · Appendix A.1 note (b), and l.225, l.1997, l.2032
- [ ] `2f₁ = 4.98 Hz` → **`4.97 Hz`**
- [ ] `approximately 5.2 Hz` → **`5.09 to 5.10 Hz, within 2.4 to 2.6% of the harmonic and so inside the 3% voiding tolerance`**

> This one **strengthens** the argument. At 5.2 the deviation is 4.57% and the void would not fire — as printed, the evidence contradicts the exclusion it justifies.

## A10 · Tables A.1 and A.2 captions
- [ ] State the two baselines: **graded columns referred to Session 6, severe column to Session 4**

> Unstated basis changes are what produced item 1.7. The audit's own first pass got a false result here.

## A11 · l.1515, assumptions table
- [ ] `Section 4.1.5 bounds the consequence` → **`Section 4.1.5 bounds any drive-induced shift at roughly 3.6%, too coarse for the trace grade, where the controls are the tap scatter of Table 4.5 and the reassembly floors of Section 4.1.4`**

## A12 · l.3092, Appendix
- [ ] `a spread of 0.15%` → **`a standard deviation of 0.15% against a range of 0.42%`**
- [ ] `The ratio of 8.010` → **`The ratio of about 8.0`**

## A13 · New Appendix A.3
- [ ] Create, carrying the linearity detail displaced from B2: n = 3 per group, the extreme-gain comparison, 1.79% within-gain scatter, one-way ANOVA **F(2,6) = 8.29, p = 0.019** over all three gains, and the null regression on drive RMS (**p = 0.81**)

---

# PART B — Data in prose (COUNTED — watch the budget)

Running net from the audit: **+22 against +25 headroom.** Substitutions below
recover a further **~12**, taking it to about **+10**.

## The numbers that change

| Where | Old | New |
|---|---|---|
| Abstract, Conclusion, Tables 4.18 / 5.1 | 6 of 9 vs 9 of 9 | **3 of 6 vs 6 of 6** |
| Abstract, Conclusion, Tables 4.8 / 5.1 | 12 of 12 | **every replicated severe run** |
| l.2042 **and** l.2744 | 1.7 | **3.09**, ratio **10.7** |
| l.1801 | factor of ten | **factor of 2.5** |
| l.2937 | 85 times | **84 times** |
| Tables 4.8 / 4.6 / 5.1 | p = 0.0001, 0.0042, 0.0075 | **deleted** |

## B1 · Abstract — four edits
- [ ] `6 of 9 against the classical rule's of 9 of 9` → **`3 of 6 against the classical rule's 6 of 6`** *(−1)*
- [ ] `assigned all twelve replicated severe runs correctly` → **`assigned every replicated severe run correctly`** *(−1)*
- [ ] `moved on task metric` → **`moved no task metric`** *(grammar, 0)*
- [ ] `a single-low cost accelerometer` → **`a single low-cost accelerometer`** *(typo, 0)*
- [ ] **CUT:** `The obstacle is the shear-chain model those routes share rather than the resolution of the measurement.` → **`The obstacle is the shear-chain model those routes share.`** *(−7)*

## B2 · §4.1.5, l.1737 — the linearity claim *(widest reach)*

**OLD:** `Swept-sine replicates at three drive amplitudes spanning a factor of 2.2 showed no statistically significant dependence of 𝑓1 on excitation level (t = -0.63, p = 0.573).`

**Audit's NEW** was +25. **Use this instead** *(saves ~7)*:

> `Swept-sine replicates at three drive amplitudes spanning 2.2× gave no detectable dependence of 𝑓1 on excitation level (t = −0.63, p = 0.573), but resolve only shifts above 3.6%; the trace grade therefore rests on the tap scatter of Table 4.5 (Appendix A.3).`

- [ ] Applied. Detail goes to Appendix A.3 (A13, uncounted).

## B3 · §4.3 opening, l.1801
- [ ] `Tap amplitude varied by roughly a factor of ten across sets, which Section 4.1.5 shows does not affect the frequency estimates, though...` → **`Tap amplitude varied by a factor of 2.5 across sets, inside the range tested in Section 4.1.5, though...`** *(−4)*

> The 10× is the **superseded** campaign's figure, per `linearity_check.py`'s own docstring. Correcting it helps: the tested 2.2× nearly covers the real 2.5×.

## B4 · §4.4 — the limitation paragraph *(this is the marks-earning addition; do not compress further)*

> `No permutation test of the location effect is valid here. Permuting runs treats three replicates of one damage application as independent; permuting intact groups leaves the leave-one-out statistic unchanged by construction, so it has no power. Separating location from rebuild needs independent rebuilds per cell.`

- [ ] Added *(+45, funded by the cuts below)*

## B5 · l.2042 AND l.2744 — the separation sentence *(TWO sites)*
- [ ] `separated by 33 floor-units against a largest replicate standard deviation of 1.7 (Section 4.4.1)` → **`separated by 33.0 floor-units against a largest within-class distance of 3.09, a ratio of 10.7`** *(saves 1 per site vs the audit's wording)*

> **Both sites or neither.** l.2042 originates the value, l.2744 repeats it. Changing only one makes the document contradict itself. The cross-reference to §4.4.1 is *correct* — an earlier audit draft wrongly said otherwise.

## B6 · Conclusion — two edits
- [ ] `returns 9 of 9 where the network returns 6 of 9` → **`returns 6 of 6 where the network returns 3 of 6`** *(0)*
- [ ] `12 of 12 replicated severe runs correct` → **`every replicated severe run correct`** *(−1)*

## B7 · §4.6, l.2636 region
- [ ] `The network cannot be scored on three of these because` → **`Floor 3 is absent from both methods because`** *(−2)*

## B8 · l.1487 — the stiffness ratio
- [ ] `show the storeys are not uniform, which is` → **`show the middle storey is stiffest, which is`** *(0 with this wording; the audit's version was +1)*

> Keep 0.983. Drop only the directional reading of storey 3 — its interval covers unity. k₂/k₁ excludes 1.0 under every convention, so "middle storey is stiffest" is supported.

## B9 · §5.4, l.2937
- [ ] `𝑓1 scatters 85 times more than 𝑓3` → **`𝑓1 scatters 84 times more than 𝑓3`** *(0 — drop the audit's "about", which cost a word)*

## B10 · Cuts that fund B4
- [ ] **§5.4, second paragraph:** `A first mode that moves 12.75% across five nominally identical taps on a fixed physical state, while the third mode holds to 0.15%, points to an amplitude-dependent contact condition` → **`That points to an amplitude-dependent contact condition`** *(−22)*
- [ ] **l.1978:** delete `at a group permutation 𝑝 = 0.0075` *(−6)*
- [ ] **l.2942:** delete `at a group permutation 𝑝 = 0.0075` *(−6)*, and `location is recovered` → `location is partly recovered`

> §5.4's second paragraph restates the comparison its own first paragraph made two sentences earlier ("85 times"). The inference survives; only the repetition goes.

---

# Margin

**+22 is three words from the cap. Do not submit on that.**

The audit's deltas are counted by naive word splitting; `texcount` handles
`\cite{}`, math mode and macros by different rules, so the real delta could land
anywhere from +15 to +35. Being over 12,000 costs up to 10% — more than every
finding in this audit combined.

Substitutions above take you to roughly **+10**. To reach a safe **−100**:

- [ ] **R2 — relocate, don't cut.** Move methodology detail that duplicates the code docstrings into an appendix. Appendices are uncounted, and the guidelines explicitly list supporting detail and equation derivations as appendix material. Estimated 200–500 words, **zero marks risk**, because nothing is lost — it just stops counting.
- [ ] Run `texcount -inc -sub=section main.tex` in Overleaf to find which sections are heaviest before choosing.

R2 is the whole answer to the margin problem. Use it before touching R1
(Background literature), which carries real marks risk under the Extended
introduction's 20.

---

# Still open

- **X1 · `F_MEASURED`** — f₂ = 8.04 and f₃ = 12.15 match neither Day-4 (8.123, 12.204) nor Day-6 (8.109, 12.187). The ratio reproduces exactly so nothing downstream moves. **Safest fix:** stop calling them measured — label them nominal or design values wherever quoted.
- **X3 · Coverage** — Part 2 chapters 2–5 were not swept: the Discussion body beyond the sentences above, Chapter 4 table by table beyond 4.5/A.1/A.2/4.16, the methodology parameter audit, and front matter. A number not in `reconciliation.csv` has not been checked.

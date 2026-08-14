# Edit list — GEOL0056 dissertation

**Audit target: `df32d53`.** Document: `GEOL0056___Dissertation (4).pdf`, 87 pp.
Part 1 only, eight items. Part 2 (full reconciliation sweep) not run.

The author applies these. No dissertation source was edited by the audit, and no
analysis code was changed to make numbers agree.

Line numbers refer to `audit/diss.txt` (`pdftotext -layout`).

**Ordered by blast radius**, widest first. Items 1 to 3 change what the document
claims; items 4 to 9 change how correct numbers are described; items 10 to 13 are
digits.

---

## 1. §4.1.5 linearity, and the two places that cite it  *(item 1.8, cascading)*

Reaches every graded-series frequency estimate in Chapter 4.

**1a. l.1737, replace Section 4.1.5's single sentence:**

> Swept-sine replicates at three drive amplitudes spanning a factor of 2.2 gave no
> detectable dependence of f1 on excitation level, comparing the extreme gains
> (Welch t = -0.63, p = 0.573, n = 3 per group). The within-gain scatter of the
> swept-sine estimate is 1.79% of f1, so the test bounds any drive-induced shift at
> roughly 3.6% and cannot resolve effects below that. Across all three gains the
> between-group differences are significant (F(2,6) = 8.29, p = 0.019) but are not
> ordered by amplitude, and a regression of f1 on drive RMS is null (p = 0.81),
> which points to run-to-run instability in the swept-sine estimate rather than to
> a drive dependence.

**1b. l.1515, assumptions table, "Constant tap amplitude" row:**

> **old:** Not held. Section 4.1.5 bounds the consequence for frequency estimates
> **new:** Not held. Section 4.1.5 bounds any drive-induced frequency shift at
> roughly 3.6%, which is too coarse for the trace grade; the operative controls
> there are the within-cell tap scatter of Table 4.5 and the reassembly floors of
> Section 4.1.4

**1c. l.1801, §4.3 opening:**

> **old:** Tap amplitude varied by roughly a factor of ten across sets, which
> Section 4.1.5 shows does not affect the frequency estimates
> **new:** Tap amplitude varied by a factor of 2.5 across sets and 3.2 across
> individual taps, comparable to the 2.2 range tested in Section 4.1.5. Within-cell
> tap scatter is reported per cell in Table 4.5 and is below 0.3% at every trace
> cell, so drive variation does not account for the graded shifts

**1d. l.2948, §5.4.** Optional, one clause: note that Section 4.1.5 measured the
undamaged rig, so its null does not extend to loosened joints and does not conflict
with the amplitude-dependent contact argument here.

*Nothing in Chapter 4 is withdrawn. The trace-grade claims keep their support; the
support is the tap scatter and the reassembly floor, not this test.*

---

## 2. Table 4.18, the localisation row and its footnote  *(item 1.4)*

Changes a headline number: 67% becomes 50%, against a classical 100%.

**2a. Replace the "Localisation, three storeys" row:**

> **Localisation** — Both methods are scored on the same measurements. On the six
> severe replicates at Floor 1 and Floor 2, the two locations that lie inside both
> methods' output spaces, the classical modal method assigns 6 of 6 and the network
> 3 of 6, correct at Floor 1 and wrong at Floor 2. Including the three base-plate
> replicates, for which k1 is the network's only representable answer and which it
> therefore cannot get wrong, the figures are 9 of 9 and 6 of 9. The base plate is
> excluded from the headline because a correct call there measures the output space
> rather than the model.

**2b. Delete the footnote's three wrong sentences** ("The two localisation scores
are not computed over the same runs...", "so its figure covers the graded cells
instead", "are not a matched comparison") and replace:

> Both columns are scored on the same measurements. The three Floor 3 severe
> replicates are excluded from both, their second modes being voided by the second
> harmonic of f1 (Appendix A.1).

**2c. Delete** "the archived Floor 3 case used imputed modes (Section 4.6.3)" from
the network cell. No Floor 3 record is in this set; that caveat belongs to the
archived five-prediction run.

**2d. Table 5.1**, "Identify which plate was loosened" row: apply the same figures
and remove the p-values (see item 3).

---

## 3. The permutation p-values  *(item 1.2)*

Four sites, one defect. Deleting a p from one and leaving the other standing would
be worse than leaving both.

**3a. Table 4.8:** delete the p column and the caption's significance sentence.
The caption also misstates the permutation unit ("replicates permuted as a group";
the code permutes runs freely). Replace the significance material with:

> All twelve severe runs are assigned to their own location under every scoring
> convention. In the three-mode signature space the closest pair of class means,
> the base plate and Floor 1, are 33.0 floor-units apart, against a largest
> distance from any run to its own class mean of 3.09 floor-units: a separation of
> 10.7 times the worst replicate spread. No permutation test of the location effect
> is valid for this design. Permuting individual runs would treat three replicates
> of one damage application as independent, and permuting intact replicate groups
> leaves the leave-one-out statistic unchanged by construction, so it has no power.
> Separating location from rebuild would require independent rebuilds within a
> cell rather than repeated taps.

**3b. Table 4.6, l.1956 caption:** delete "and a permutation p = 0.0075"; change
"Scatter identifies damage location" to "Scatter is associated with damage
location". **This claim is suggestive, not established** — 14 of 24 against a
chance rate of 0.25, driven by one location, with no separation ratio behind it.

**3c. l.1978:** delete "at a group permutation p = 0.0075".

**3d. l.2942, Discussion:** delete the p; "location is recovered" overstates,
use "location is partly recovered".

**3e. Table 5.1:** delete "at permutation p = 0.0001, 0.0001 and p = 0.0042".
Also see item 12 — the 12 of 12 per-run figure in that row is unverifiable.

**3f. l.847, l.882, l.912:** three methodology statements describe the permutation
scheme. l.912 repeats the caption's error ("replicates of a location permuted as a
group"). Reword all three to match whatever 3a settles on.

---

## 4. Table 3.10, the scoring rule  *(item 1.3)*

**Correct the table to describe exact matching.** It currently states adjacency
("Floor 1 admits k1 or k2, Floor 2 admits k2 or k3"); the code and every published
number use exact index match, Floor n to k_n. The document's own seed-averaged
0.650 at l.2415 proves it: adjacency predicts 0.714.

Exact matching is the defensible rule. Under adjacency, Floor 1 would be credited
for naming k2 and Floor 2 for naming k3, so the two storeys the network most needs
to distinguish would be interchangeable, and l.2401's "it fails at exactly the
location whose plate would require the middle storey to be named" would lose its
meaning.

---

## 5. Table 4.5 caption, SD against SEM  *(item 1.1)*

Every printed value is correct. One clause is wrong.

> **old:** Uncertainty is propagated from the tap standard deviations of the
> damaged set and of the baseline;
> **new:** Uncertainty is the standard error of the difference between the
> five-tap damaged and baseline means, formed from the tap standard deviations of
> each;

---

## 6. Table 4.16, "every exact solution"  *(item 1.5a)*

**6a. Add the missing Floor 2 branch:** k = (2.521, 0.156, 0.365), max|Δf| at
machine precision, not admissible. Table 5.1 already says "Floor 2 admits one of
four"; the table lists three. No conclusion changes.

**6b. Caption, the start count:** 3 000 is the attempted count. State the observed
one: 1 275, 560 and 1 581 starts converged for base, Floor 1 and Floor 2. Floor 1's
18.7% is the rank deficiency Section 5.3 diagnoses and is worth keeping.

**6c. Delete the max|Δf| column.** Those are optimiser residuals from random
starts and they do not reproduce between runs (base B2 prints 3.6e-15 against
8.9e-15 recomputed; F2 B3 prints 1.8e-15 against 3.2e-14). Replace with one
sentence: "every branch fits the three measured frequencies to better than
1e-13 Hz".

---

## 7. The tap-scatter figure caption  *(item 1.7)*

Both numbers are right and neither needs recomputing; they are different
quantities sharing one name. Name the basis in the caption:

> Tap-to-tap scatter of f1, plotted as the full range of Δf1 across the five taps
> of each cell, in percentage points of the session baseline. This is a wider
> statistic than the standard-deviation column of Table 4.5 and on a different
> denominator, so the two differ by roughly a factor of two: base moderate is
> 15.5 pp here against 12.75% there.

Fix first because it is a visible collision: **l.1894** says "Floor 2 and Floor 3
stay at or below 0.76% at every grade" and sits directly above bars labelled 1.4,
0.4, 0.5, 0.2 and 0.3 for those same cells.

---

## 8. l.1487, the stiffness ratio's directional claim  *(item 1.6)*

The number 1 : 1.192 : 0.983 is correct. Its 95% interval on k3/k1 is
[0.960, 1.006], which covers unity.

> **old:** ratios of 1 : 1.192 : 0.983 show the storeys are not uniform
> **new:** ratios of 1 : 1.192 : 0.983. The storeys are not uniform: the middle
> storey is about 19% stiffer than the lower, which is well outside the reassembly
> reproducibility of Section 4.1.4. The upper and lower storeys are not separated
> by it, k3/k1 = 0.983 with a 95% interval of [0.960, 1.006].

l.1331 states the ratio without an inference and needs no change.

---

## 9. Appendix A.1 note (b) and its four repetitions  *(item 1.4g)*

**The correction strengthens the argument.** As printed, f2 "approximately 5.2 Hz"
is 4.57% from 2f1, outside the 3% voiding tolerance of l.812, so a checking reader
concludes the void should never have fired. The true value puts all three
replicates inside it.

Replace at **l.225, l.1997, l.2032 and l.3130**:

> f2 could not be separated from the second harmonic of f1, which sits at
> 2f1 = 4.97 Hz against a second-mode candidate at 5.09 to 5.10 Hz, within 2.4 to
> 2.6% of the harmonic and so inside the 3% voiding tolerance.

---

## 10. l.3092 and l.2947, the base-moderate spread labels  *(item 1.5c)*

Every raw value reproduces. Two labels do not.

**10a.** "a spread of 0.15%" is printed immediately after the range 11.965 to
12.015 and reads as that range. It is the standard deviation; the range is 0.42%.
The f1 comparator in the same sentence, "a swing of 34%", *is* a range statistic,
so the sentence sets a range against a standard deviation. State one basis and use
it on both sides.

**10b.** "85 times" is 12.75/0.15, a ratio of two rounded numbers. Unrounded it is
**83.6**. Use 84, or "about 80 times".

**10c.** "The ratio of 8.010 on the set" recomputes to 8.035. In a cell whose f1
scatters 12.7% between taps, four significant figures is not meaningful, and the
paragraph's own argument is that the set ratio is the misleading quantity. Use
"about 8.0".

---

## 11. l.2744, Discussion, the separation sentence  *(items 1.2g and 1.7b)*

Mixes two signature spaces and cites a section that does not contain the number.

> **old:** separated by 33 floor-units against a largest replicate standard
> deviation of 1.7 (Section 4.4.1)
> **new:** separated by 33.0 floor-units in the three-mode signature space against
> a largest run-to-own-mean distance of 3.09, a ratio of 10.7 (Section 4.4.1
> reports the two-mode pair, 26.6 against 2.1)

The 19.4x ratio derived from 1.7 should not be used anywhere.

---

## 12. Table 4.8 and Table 5.1, the per-run row  *(item 1.2a)*

"12 of 12 under the per-run rule, mean 3.03, p = 0.0001" has **no generator
anywhere in the repository**. Either regenerate it from committed code or remove
the row from both tables. See `audit/UNVERIFIABLE.md`.

---

## 13. Table 4.5, one digit  *(item 1.1b)*

Floor 3 light prints 0.11; the exact value is 0.10452, which is **0.10** at 2 d.p.
Display rule: quote the column to 2 d.p. from unrounded inputs. Only this cell
changes.

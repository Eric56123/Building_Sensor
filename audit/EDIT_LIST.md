# Consolidated edit list — GEOL0056 dissertation

**Audit target: `df32d53`.** Document: `GEOL0056___Dissertation (4).pdf`, 87 pp.
Supersedes the 13-item Part 1 list. Merges Part 1 (items 1.1–1.8) with Part 2
chapter 1 (abstract and conclusions).

**Coverage is partial and stated in full at the end of this file.** Part 2
covered the abstract, the conclusions, the proposal-duplication check and the
carry-over decisions. Chapters 2 to 5 of the Part 2 ordering were not reached.

The author applies these. No dissertation source was edited by the audit, and no
analysis code was changed to make numbers agree.

---

## ⚠ The word-count baseline could not be verified

**There is no `.tex` source on this machine and `texcount` is not installed.**
Searched: the repository, `~/Documents`, `~/Desktop`, `~/Downloads`, iCloud
Drive, and the connected Google Drive. Only the compiled PDF and unrelated
`.tex` files (a CV, three `article` stubs) exist. The dissertation source is
presumably on Overleaf.

So **11,975 is taken from you, not confirmed.** Run this yourself before
applying anything:

```
texcount -inc -sum -brief main.tex          # the authoritative total
texcount -inc -sub=section main.tex         # per-section, for targeting cuts
texcount -inc -sum -brief -v3 main.tex      # verify float/caption exclusion
```

texcount excludes `table` and `figure` environments and their captions by
default, which matches the marking guidelines.

**What is exact is the delta.** Every figure below is counted on the literal
OLD and NEW strings by `audit/scripts/word_budget.py` (exit 0), which is
re-runnable. The ≤ +25 constraint is a constraint on deltas, so this half of the
arithmetic is sound even with the baseline unconfirmed.

---

## Table 1 — Running word budget

Counted edits only. Uncounted edits (tables, captions, appendices, front matter)
carry no arithmetic and are grouped at the end of the list.

| ID | Location | − | + | net | running |
|---|---|---|---|---|---|
| E1 | Abstract, localisation sentence | 19 | 18 | **−1** | −1 |
| E2 | Abstract, per-run claim | 21 | 20 | **−1** | −2 |
| E3 | Abstract, grammar (`moved on` → `moved no`) | 20 | 20 | 0 | −2 |
| E4 | Abstract, typo (`single-low cost`) | 9 | 9 | 0 | −2 |
| E5 | Conclusion, localisation | 26 | 25 | **−1** | −3 |
| E6 | Conclusion, comparison | 34 | 34 | 0 | −3 |
| E7 | §4.1.5 linearity | 25 | 50 | **+25** | +22 |
| E8 | §4.3 opening | 31 | 27 | **−4** | +18 |
| E9 | l.1894 scatter ceiling | 17 | 17 | 0 | +18 |
| E10 | l.1487 stiffness ratio | 12 | 13 | **+1** | +19 |
| E11 | l.2042 + l.2744 separation (2 sites) | 14 | 15 | **+1** | +20 |
| E12 | §4.4 permutation limitation | 0 | 45 | **+45** | +65 |
| E13 | §5.4 scatter ratio | 11 | 12 | **+1** | +66 |
| E14 | §4.6 network localisation prose | 10 | 8 | **−2** | +64 |
| | **subtotal, additions** | | | | **+64** |
| C1 | §5.4, cut self-restatement | 29 | 7 | **−22** | +42 |
| C2 | l.1978, cut p clause | 14 | 8 | **−6** | +36 |
| C3 | l.2942, cut p clause | 17 | 11 | **−6** | +30 |
| C4 | Abstract, cut restatement of the conclusion | 16 | 9 | **−7** | **+22** |

**NET +22 against +25 headroom. Three words to spare.**

*(The running column differs by one from the script's intermediate lines because
the script reports E7's relocation separately; the totals agree at +22. Re-run
`audit/scripts/word_budget.py` for the authoritative figures.)*

Relocation did the heavy lifting: **120 words** of new material were moved into
captions, table footnotes and a new Appendix A.3 rather than added to body text.
Without that the net would be +183.

## Table 2 — Cut candidates, ranked

| ID | Cut | Words freed | Marks risked | Funds |
|---|---|---|---|---|
| **C1** | §5.4's second paragraph opens by restating the scatter comparison its own first paragraph made two sentences earlier (12.75 against 0.15, already given as "85 times"). Keep the inference, drop the repetition. | **22** | **None.** Pure restatement. The interpretive claim (amplitude-dependent contact condition) is untouched. | E12 |
| **C2** | l.1978's `at a group permutation p = 0.0075` | **6** | None. Item 1.2(e) deletes this anyway as invalid. | E12 |
| **C3** | l.2942's `at a group permutation p = 0.0075` | **6** | None. Same. | E12 |
| **C4** | The abstract's closing "rather than the resolution of the measurement" duplicates the conclusion's "rather than in the identifiability of the inverse problem". | **7** | Low. The contrast survives in the conclusion. | E7 |
| — | **Not used, held in reserve** | | | |
| R1 | Background chapter, literature detail beyond establishing the gap | est. 150–300 | Medium. Marked under Extended introduction (20). Cut only what does not establish the gap. | reserve |
| R2 | Methodology detail duplicating code docstrings → Appendix | est. 200–500 | **Low, and it is relocation not deletion.** The guidelines list supporting detail as appendix material. | reserve |

**Never cut:** interpretation, critical evaluation, limitations, or anything
addressing whether findings support the objectives. Those carry the 85–100
criteria. No edit above touches them; E12 *adds* to them.

**R1 and R2 are unmeasured** because sizing them needs the `.tex`. They are
listed so that if your texcount differs from 11,975, you know where to go.

## Table 3 — Unresolved: MISMATCH and UNVERIFIABLE not closed by an edit

| ID | Location | Status | Why not closed |
|---|---|---|---|
| X1 | `F_MEASURED = [2.94, 8.04, 12.15]`, `rig_3dof.py` | **UNVERIFIABLE** | f1 = 2.94 matches the Day-4 baseline (2.9420). f2 = 8.04 and f3 = 12.15 match neither Day-4 (8.123, 12.204) nor Day-6 (8.109, 12.187). The fitted ratio reproduces exactly, so nothing downstream moves, but the source session is not recorded anywhere. **You must confirm it**; if you cannot, say the fit uses frequencies from an early session. |
| X2 | Table A.1 and A.2 baselines | **CONFIRMED_ERROR, edit U10** | Closed by a caption edit, but flagged here because it is the same class as item 1.7 and I nearly recorded a false MISMATCH from it myself. |
| X3 | Chapters 2–5 of the Part 2 ordering | **NOT SWEPT** | See coverage statement. |

---

# The edits, ordered by blast radius

## 1. §4.1.5 linearity, and the two places that cite it *(item 1.8)*

Widest reach: cited as licensing every graded-series frequency estimate.

### E7 · §4.1.5, l.1737
```
counted: yes   words: −25/+50   net: +25   running: +22
```
**OLD:** `Swept-sine replicates at three drive amplitudes spanning a factor of 2.2 showed no statistically significant dependence of 𝑓1 on excitation level (t = -0.63, p = 0.573).`

**NEW:** `Swept-sine replicates at three drive amplitudes spanning a factor of 2.2 gave no detectable dependence of 𝑓1 on excitation level (t = -0.63, p = 0.573); the test bounds a drive-induced shift at roughly 3.6% and no lower, so the trace grade rests on the tap scatter of Table 4.5 (Appendix A.3).`

**Also change:** E8, U11. **Add Appendix A.3** (uncounted) carrying the detail:
n = 3 per group, the extreme-gain comparison, the 1.79% within-gain scatter, the
one-way ANOVA F(2,6) = 8.29 p = 0.019 over all three gains, and the null
regression on drive RMS (p = 0.81).

**Why:** t and p reproduce exactly, but the test resolves only 3.6% shifts, above
three of the four trace-grade shifts it is invoked to protect.

### E8 · §4.3 opening, l.1801
```
counted: yes   words: −31/+27   net: −4   running: +18
```
**OLD:** `Tap amplitude varied by roughly a factor of ten across sets, which Section 4.1.5 shows does not affect the frequency estimates, though the damping estimates from this series are not comparable.`

**NEW:** `Tap amplitude varied by a factor of 2.5 across sets, inside the range tested in Section 4.1.5, though the damping estimates from this series are not comparable.`

**Why:** the 10× is the *superseded* campaign's figure, per `linearity_check.py`'s
own docstring. Recomputed: 2.5× by set mean, 3.2× by individual tap. Correcting
it **helps** — the tested 2.2× nearly covers the real range.

## 2. Table 4.18 and the localisation headline *(item 1.4)*

Changes a headline number: 67% → 50%, against a classical 100%.

### E1 · Abstract
```
counted: yes   words: −19/+18   net: −1   running: −1
```
**OLD:** `The network inherits the same parametrisation and reaches 6 of 9 against the classical rule's of 9 of 9.`

**NEW:** `The network inherits the same parametrisation and calls 3 of 6 against the classical rule's 6 of 6.`

**Also change:** E6, U1, U4.

### E6 · Conclusion
```
counted: yes   words: −34/+34   net: 0   running: −3
```
**OLD:** `The classical route is the one to put on a low-cost node: it returns 9 of 9 where the network returns 6 of 9, and needs no forward model and no retargeting per structure.`

**NEW:** `The classical route is the one to put on a low-cost node: it returns 6 of 6 where the network returns 3 of 6, and needs no forward model and no retargeting per structure.`

### E14 · §4.6, l.2636 region
```
counted: yes   words: −10/+8   net: −2   running: +64
```
**OLD:** `The network cannot be scored on three of these because`

**NEW:** `Floor 3 is absent from both methods because`

**Why:** the Floor 3 replicates are not among the nine; the void removes them
from *both* methods equally.

## 3. The permutation p-values *(item 1.2)*

### E12 · §4.4, new paragraph
```
counted: yes   words: −0/+45   net: +45   running: +65
```
**NEW:** `No permutation test of the location effect is valid here. Permuting runs treats three replicates of one damage application as independent; permuting intact groups leaves the leave-one-out statistic unchanged by construction, so it has no power. Separating location from rebuild needs independent rebuilds per cell.`

**Funded by:** C1 + C2 + C3 (34 words) and part of C4.
**Why:** this is the addition that earns marks. All three legs survive the trim:
run-level permutation is anticonservative, group-level has zero power by
construction, and the design fix is independent rebuilds rather than more taps.

### C2 · l.1978 · C3 · l.2942
```
counted: yes   C2 net: −6   C3 net: −6
```
Delete `at a group permutation 𝑝 = 0.0075` from both. Also reword l.2942's
"location is recovered" to "location is partly recovered", and Table 4.6's
caption verb from "identifies" to "is associated with" (U3, uncounted).

### E11 · l.2042 (Results, origin) AND l.2744 (Discussion)
```
counted: yes   words: −14/+15   net: +1   running: +20
```
**Two sites.** Verified: the string occurs twice. l.2042 is where the value
originates; l.2744 repeats it. Both must change or the document contradicts
itself.
**OLD:** `separated by 33 floor-units against a largest replicate standard deviation of 1.7 (Section 4.4.1)`

**NEW:** `separated by 33.0 floor-units against a largest run-to-own-mean distance of 3.09, a ratio of 10.7`

**Why:** 1.7 has no generator (U2); nearest candidates are 1.78 and 1.83, both
rounding to 1.8. **The cross-reference is correct** — an earlier draft of this
audit wrongly said §4.4.1 lacked the number; it states both pairs at l.2042.

## 4. The unverifiable per-run row *(item 1.2a — DECIDED: remove)*

### E2 · Abstract
```
counted: yes   words: −21/+20   net: −1   running: −2
```
**OLD:** `nearest-signature matching on floor-normalised shifts assigned all twelve replicated severe runs correctly and 18 of 18 at two further sensor positions.`

**NEW:** `nearest-signature matching on floor-normalised shifts assigned every replicated severe run correctly and 18 of 18 at two further sensor positions.`

### E5 · Conclusion
```
counted: yes   words: −26/+25   net: −1   running: −3
```
**OLD:** `Localisation is the strongest positive result: 12 of 12 replicated severe runs correct, and 18 of 18 at two other sensor positions against references recorded elsewhere.`

**NEW:** `Localisation is the strongest positive result: every replicated severe run correct, and 18 of 18 at two other sensor positions against references recorded elsewhere.`

**Also change:** U2 (Table 4.8 row), U4 (Table 5.1 row).
**Why:** no generator anywhere in the repository, and a twelve-run three-mode
scoring cannot be built from these captures because the three Floor 3 severe
records have no f2 (9 of 12 have one). The rewording keeps the claim true under
the two rows that *do* verify.

## 5. Remaining counted edits

### E3 · Abstract grammar
```
counted: yes   net: 0   running: −2
```
**OLD:** `moved on task metric beyond fold and seed scatter`
**NEW:** `moved no task metric beyond fold and seed scatter`

### E4 · Abstract typo
```
counted: yes   net: 0   running: −2
```
**OLD:** `a single-low cost accelerometer` **NEW:** `a single low-cost accelerometer`

### E9 · l.1894
```
counted: yes   net: 0   running: +18
```
Text unchanged; the basis note moves into the figure caption (U8).

### E10 · l.1487 *(item 1.6)*
```
counted: yes   words: −12/+13   net: +1   running: +19
```
**OLD:** `of 1 : 1.192 : 0.983 show the storeys are not uniform, which is`
**NEW:** `of 1 : 1.192 : 0.983 show the middle storey is the stiffest, which is`

**Also change:** put the interval in the table (uncounted): k3/k1 = 0.983, 95%
interval [0.960, 1.006], which covers unity. **Why:** the number is right; only
the directional reading fails. k2/k1 excludes 1.0 under every convention.

### E13 · §5.4, l.2937 *(item 1.5c)*
```
counted: yes   words: −11/+12   net: +1   running: +66
```
**OLD:** `𝑓1 scatters 85 times more than 𝑓3 so the instability is`
**NEW:** `𝑓1 scatters about 84 times more than 𝑓3 so the instability is`

### C1 · §5.4, second paragraph
```
counted: yes   words: −29/+7   net: −22   running: +42
```
**OLD:** `A first mode that moves 12.75% across five nominally identical taps on a fixed physical state, while the third mode holds to 0.15%, points to an amplitude-dependent contact condition`
**NEW:** `That points to an amplitude-dependent contact condition`

### C4 · Abstract
```
counted: yes   words: −16/+9   net: −7   running: +22
```
**OLD:** `The obstacle is the shear-chain model those routes share rather than the resolution of the measurement.`
**NEW:** `The obstacle is the shear-chain model those routes share.`

---

# Uncounted edits — apply freely, no budget arithmetic

**U1 · Table 4.18.** Replace the localisation row with the 6-of-6 / 3-of-6 pair,
6 of 9 given as the base-inclusive alternative and the forced-choice mechanism in
one clause. Delete `the archived Floor 3 case used imputed modes`. Replace the
footnote's three wrong sentences with: *"Both columns are scored on the same
measurements. The three Floor 3 severe replicates are excluded from both, their
second modes being voided by the second harmonic of f1 (Appendix A.1)."*

**U2 · Table 4.8.** Delete the p column, the caption's significance sentence, and
the per-run row. The caption also misstates the permutation unit.

**U3 · Table 4.6 caption.** Delete `and a permutation p = 0.0075`; `identifies`
→ `is associated with`.

**U4 · Table 5.1.** "Identify which plate was loosened" row: remove the three
p-values and the 12-of-12 figure; apply the 6-of-6 / 3-of-6 pair.

**U5 · Table 3.10.** State exact index matching, not adjacency. The document's own
0.650 at l.2415 proves exact was used (adjacency predicts 0.714).

**U6 · Table 4.5.** Caption: `propagated from the tap standard deviations` →
`the standard error of the difference between the five-tap damaged and baseline
means, formed from the tap standard deviations of each`. Cell: Floor 3 light
`0.11` → `0.10`.

**U7 · Table 4.16.** Add the missing Floor 2 branch (2.521, 0.156, 0.365), not
admissible — Table 5.1 already says "one of four". Caption: 3 000 is the
*attempted* count; converged is 1 275 / 560 / 1 581. Delete the max|Δf| column,
replace with *"every branch fits to better than 1e-13 Hz"*.

**U8 · Scatter figure caption.** Name the basis: full range of Δf1 in percentage
points of the session baseline, a wider statistic on a different denominator than
Table 4.5's standard deviation, hence 15.5 against 12.75 at base moderate.

**U9 · Appendix A.1 note (b), and l.225, l.1997, l.2032.** `2f1 = 4.98 Hz` →
`4.97 Hz`; `approximately 5.2 Hz` → `5.09 to 5.10 Hz, within 2.4 to 2.6% of the
harmonic and so inside the 3% voiding tolerance`. **This correction strengthens
the argument**: at 5.2 the deviation is 4.57% and the void would not fire.

**U10 · Tables A.1 and A.2 captions.** State the two baselines: graded columns
referred to Session 6, severe column to Session 4.

**U11 · l.1515, assumptions table.** `Section 4.1.5 bounds the consequence` →
`Section 4.1.5 bounds any drive-induced shift at roughly 3.6%, too coarse for the
trace grade, where the controls are the tap scatter of Table 4.5 and the
reassembly floors of Section 4.1.4`.

**U12 · l.3092, Appendix.** `a spread of 0.15%` → `a standard deviation of 0.15%
against a range of 0.42%`; `The ratio of 8.010` → `The ratio of about 8.0`.

**U13 · New Appendix A.3.** The linearity detail displaced from E7.

---

# Coverage

**Swept:** Part 1 items 1.1–1.8 (seven scripts, all exit 0). Part 2 chapter 1,
the abstract and conclusions, all eight figures recomputed. Tables 4.5, A.1 and
A.2 in full, 45 of 46 cells reproducing within 0.06 pp. The proposal-duplication
check. The three UNVERIFIABLE carry-overs, all decided.

**Not swept:** Part 2 chapters 2 to 5 — the Discussion body beyond the four
sentences named above, Chapter 4 table by table beyond Tables 4.5/A.1/A.2/4.16,
the Methodology parameter-by-parameter code audit, and the front matter. **A
number not appearing in `reconciliation.csv` has not been checked.**

**Proposal duplication: clean.** `GEOL0056___Research_Proposal-10.pdf` diffed
against the dissertation at 12-word and 8-word windows. 141 shared 12-word
sequences merged into 8 contiguous passages, **every one a bibliography entry**
(author names, DOIs, journal titles, URLs). No body prose is shared. References
are uncounted and a shared bibliography is not penalisable reuse.

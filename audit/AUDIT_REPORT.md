# Numerical audit — GEOL0056 dissertation

**Audit target: `df32d53`** (`figures/ch8-ch9-regeneration`), working tree clean.
Document audited: `GEOL0056___Dissertation (4).pdf`, 87 pp, extracted to `audit/diss.txt`.

Scope: Part 1 only, seven items, sequential. Part 2 deferred.

## Action list — MISMATCH and UNVERIFIABLE only

| # | Location | Verdict | One line |
|---|---|---|---|
| 1.2a | Table 4.8, per-run row | **UNVERIFIABLE** | 12/12, mean 3.03, p = 0.0001 has no generator anywhere in the repository |
| 1.2b | Table 4.8 caption | **CONFIRMED_ERROR** | Says replicates are permuted as a group; the code permutes runs freely |
| 1.2c | Table 4.8, three-mode p | **MISMATCH** | 0.0042 is a Monte-Carlo estimate 17.6% high; exact 6/1680 = **0.0036** |
| 1.2e | Table 4.6, p = 0.0075 | **CONFIRMED_ERROR** | Same defect; location-level permutation is equally degenerate |
| 1.2g | Discussion l.2744 | **MISMATCH** | "33 against 1.7 (Section 4.4.1)" mixes spaces; 1.7 does not reproduce |
| 1.2d | Table 4.8, two-mode p | **MISMATCH** | 0.0001 is the sampling floor; the exact value is 6/92 400 = **0.000065** |
| 1.1 | Table 4.5 caption | **CONFIRMED_ERROR** | Column is a standard error, not a standard deviation (values correct) |
| 1.1b | Table 4.5, Floor 3 light | **MISMATCH** | SD prints 0.11; exact 0.10452, which is 0.10 at 2 d.p. |

Items 1.3–1.7 pending.

---

## 1.1 — Table 4.5 uncertainty column: SD or SEM?

**Verdict: CONFIRMED_ERROR in wording. Every printed value is correct.**
Script: `audit/scripts/audit_1_1_sd_vs_sem.py` (exit 0).

The reviewer's diagnosis was right, and the terminology-only fix they preferred is
the one taken here, for the reason they gave: it preserves the values.

All twelve cells match SEM propagation; none match SD propagation; the ratio is
2.2361 = √5 in every cell to four decimals. **n = 5 in all twelve cells and in the
baseline**, no exceptions.

Chain, worked for base/moderate:

| step | value |
|---|---|
| baseline, n=5, mean 2.9216 Hz, SD 0.2020% | 0.005900 Hz |
| damaged, n=5, mean 1.4917 Hz, SD 12.745% | 0.190190 Hz |
| propagate the SDs, no 1/√n | **6.508 pp** |
| propagate each variance ÷ its own n | **2.911 pp** = the printed 2.91 |

Code path: `toolkit_common.welch_test` L625, `se = sqrt(vb/nb + vt/nt)`, expressed
as a percentage of the baseline mean. Both `welch_test` and the extraction path are
pre-existing repository code, so this item is a genuine cross-check.

**Downstream: verified, not assumed.** The four trace-grade detection margins are
normalised by the reassembly floor, not by this column — the document says so at
line 1936, "14.2 times the first-mode floor". Recomputed: 4.27/0.30 = 14.2,
2.29/0.30 = 7.6, 0.97/0.30 = 3.2, 1.2/0.32 = 3.8. All four reproduce exactly. The
only other consumer is the qualitative "−0.03 ± 0.14%, indistinguishable from the
baseline" at line 1938, whose conclusion holds under either reading. So the fix
really is one clause.

### Edit

> **old:** Uncertainty is propagated from the tap standard deviations of the damaged set and of the baseline;
> **new:** Uncertainty is the standard error of the difference between the five-tap damaged and baseline means, formed from the tap standard deviations of each;

The rest of the caption already describes a standard error correctly: it bounds the
stability of the modal estimate within one damage state and disclaims being a
confidence interval on the damage effect.

### 1.1b — display rule

Quote the SD column to **2 d.p. from unrounded inputs**. One cell changes:
Floor 3 light, printed 0.11, exact 0.10452, correct digit **0.10**. Moving to
3 s.f. instead would change ten of thirteen cells for no gain.

---

## 1.2 — Table 4.8 permutation p-values

**Verdict: one UNVERIFIABLE row, one CONFIRMED_ERROR caption, two MISMATCH p-values.**
Script: `audit/scripts/audit_1_2_permutation.py`.

### (a) One of the three rows has no generator

| row | generator |
|---|---|
| Fixed two-mode | `inversion_robustness.py`, `analysis_BC` |
| Fixed three-mode | `inversion_robustness.py`, `analysis_BC` |
| **Per-run** | **absent from the repository** |

Only two files in the repo permute anything: `inversion_robustness.py` (this test)
and `run_experiments.py` (the λ sweep, unrelated). Neither contains a per-run
scoring. The per-run row must be regenerated from committed code or removed.

### (b) The caption misdescribes the permutation unit

The caption says "replicates permuted as a group". The code is
`yp = rng.permutation(y)` with `y` a **per-run** label vector: runs are shuffled
freely and the three replicates of a location are not held together.

| scoring | run-level space | group-wise space |
|---|---|---|
| per-run, 12 runs | 369 600 | 24 |
| two-mode, 11 runs | 92 400 | 24 |
| three-mode, 9 runs | 1 680 | 6 |

### (c) Exact p-values, in closed form

Because the classifier is perfect, exactly those relabellings that preserve the
partition reproduce a perfect score, so exact p = (partition-preserving
relabellings) / (distinct labellings). Enumeration confirms both computable cases.

| scoring | exact p | document |
|---|---|---|
| per-run | 24/369 600 = **0.000065** | 0.0001 |
| two-mode | 6/92 400 = **0.000065** | 0.0001 |
| three-mode | 6/1 680 = **0.0036** | 0.0042 |

No sampling is needed for any of them. The document's 0.0001 entries are the
Monte-Carlo floor 1/(N+1), not results; the true values are 1.5× smaller. The
three-mode 0.0042 is a sampling estimate that is 17.6% high.

### (d) The test the caption describes has zero power by construction

Enumerating all 24 group-wise labellings: **every one scores 12/12**.

This must not be reported as "p = 1.0000", which reads as though an effect was
tested for and not found. The correct statement is that **the test statistic is
invariant under the null's relabelling operation**. Leave-one-out
nearest-class-mean depends only on the partition, and relabelling intact groups
leaves the partition untouched, so the statistic cannot change no matter what the
data are. The test cannot reject any hypothesis on any dataset. Its p-value
carries no information about this result or any other.

**This corrects the review as well as the document.** The reviewer's space size of
4! = 24 is right, but the inferred floor of 1/24 ≈ 0.0417 assumes only the observed
labelling attains the observed score. All 24 do. The test has zero power, not low
power.

### (e) The same defect three pages earlier: Table 4.6, p = 0.0075

Swept for siblings resting on the same runs, as this cannot be left to Part 2.

| claim | location | status |
|---|---|---|
| grouped LOO 14/24, **p = 0.0075** | l.1978, l.2943, Table 4.6 | **same defect** |
| plain LOO 13/24, p = 0.0066 | l.1979 | already deprecated in the text |
| Kruskal H = 2.76, p = 0.43 (grade) | l.1982 | safe: null result, anticonservative test |
| Spearman rho 0.004 / 0.121 | l.1981 | safe: null results |
| Kruskal across locations | not quoted | no action |

Observed 14/24 reproduces exactly. But the published p = 0.0075 permutes at the
**cell** level, treating the four cells of a location as exchangeable with cells of
other locations. Enumerating the 24 location-level labellings: **all 24 score 14/24**,
identically degenerate. The four graded cells of one location are a progressive
damage sequence on one setup, so they are correlated under the null in the same way
the three replicates are.

So Table 4.6's p needs the same treatment as Table 4.8's. Fixing one and leaving
the other standing would be worse than fixing neither.

### (f) Why no valid permutation test exists here — state this as a limitation

This is the part worth marks, and it is a finding about the design, not about the
analysis.

* **Run-level permutation is anticonservative.** The three replicates of a cell
  share a single rebuild, so they are correlated even under the null and are not
  exchangeable with runs from other cells.
* **Group-level permutation has zero power**, for the invariance reason above.
* Therefore **the design admits no valid permutation test of the location effect.**
  With three replicates nested in one rebuild per cell, location cannot be
  separated from rebuild: the only units that are exchangeable under the null are
  the ones whose relabelling the statistic ignores.

Future work follows concretely: **replicate the rebuild within a cell, not just the
taps.** Three independent rebuilds per location, each with its own damage
application, would make the rebuild the exchangeable unit and give a permutation
test with real power.

### (g) Effect size, reconciled — this is now the localisation result

With the p column gone this carries the claim, so the definition goes in the
sentence. Two spaces, two answers, both correct for what they measure:

| space | closest class-mean pair | largest run-to-own-mean distance | ratio |
|---|---|---|---|
| two-mode (f1, f3), 11 runs, 4 classes | **26.6** | **2.06** | **12.9** |
| three-mode, 9 runs, 3 classes (F3 has no f2) | **33.0** | **3.09** | **10.7** |

**The Discussion at l.2744 pairs numbers from different spaces and cites the wrong
section.** It reads "separated by 33 floor-units against a largest replicate
standard deviation of 1.7 (Section 4.4.1)". The 33 is three-mode; Section 4.4.1
(l.2130) reports the two-mode pair, 26.6 against 2.1. And **1.7 does not reproduce
under any definition tested** — nearest candidates are 1.78 (largest two-mode
per-class sd, ddof=1) and 1.83 (mean three-mode run-to-mean distance), both of
which round to 1.8. Verdict **MISMATCH**; the 19.4x ratio derived from it should
not be used.

### Recommended replacement

Delete the p column from Table 4.8, the caption's significance sentence, the
matching Discussion sentence, and the Table 5.1 entry. Apply the same to Table 4.6's
p = 0.0075. Replace with:

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

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
| 1.4c | Table 4.18, network cell | **CONFIRMED_ERROR** | 6/9 counts the base plate three times; the row two below says base is outside the label space |
| 1.4a | Table 4.18, both cells | **CONFIRMED_ERROR** | "at the three storey locations" is wrong; the nine records are base, Floor 1, Floor 2 |
| 1.4b | Table 4.18 footnote | **CONFIRMED_ERROR** | "Not a matched comparison" is wrong; both columns score the identical nine records |
| 1.3 | Table 3.10 | **CONFIRMED_ERROR** | States an adjacency rule; the code and every published number use exact index match |
| 1.1 | Table 4.5 caption | **CONFIRMED_ERROR** | Column is a standard error, not a standard deviation (values correct) |
| 1.4d | Appendix A.1 note (b) + 4 sites | **MISMATCH** | 2f1 = 4.98 recomputes to **4.97**; "f2 approximately 5.2 Hz" is **5.09–5.10**, and 5.2 would not trip the 3% rule |
| **1.8** | §4.1.5, cited at l.1515 and l.1801 | **CONFIRMED_ERROR** | **Cascading.** Bounds drive effects only at 3.6%, above three of four trace shifts; "factor of ten" is the superseded campaign's number, really 2.5x |
| 1.7 | Table 4.5 vs the scatter figure | **CONFIRMED_ERROR** | "Tap scatter" names two different statistics on two denominators; 12.75 against 15.5 |
| 1.5a | Table 4.16 | **CONFIRMED_ERROR** | "Every exact solution" omits a Floor 2 branch that Table 5.1 counts; n = 3 000 is the attempted count |
| 1.6 | l.1487 | **CONFIRMED_ERROR** | 0.983 is correct, but its 95% interval covers 1.0; the non-uniformity claim rests on k2 alone |
| 1.1b | Table 4.5, Floor 3 light | **MISMATCH** | SD prints 0.11; exact 0.10452, which is 0.10 at 2 d.p. |
| 1.5c | §5.4 and Appendix A.1 | **MISMATCH** | "85 times" is a ratio of rounded values; 83.6. "A spread of 0.15%" is an SD printed as a range |
| 1.7b | Discussion l.2744, "1.7" | **UNVERIFIABLE** | No generator in the repository; nearest candidates are 1.78 and 1.83 |

**Part 1 complete.** Withdrawn: the "1 : 1.194 : 1.023" stiffness-ratio
discrepancy I flagged before item 1.6 was run. It does not exist; both printed
sites say 0.983 and the code agrees. The 1.023 was Table 4.16's base-plate branch
B3 k1, misread.

### What Part 1 did not touch

Part 2, the full reconciliation sweep, is still deferred. Every verdict above
concerns the seven items in scope; a number not listed here has not been checked.

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

**But 1.2's rescue does not transfer.** Table 4.8 survives the loss of its p-value
because 12/12 with a 10.7x separation ratio is a strong descriptive result. Table
4.6 is 14 of 24 against a chance rate of 0.25, driven almost entirely by one
location, and it has no separation ratio behind it. With the p removed there is no
inferential support left, so the surviving claim is **suggestive, not established**,
and the wording has to say so.

Three sites carry it, and the Discussion is one of them:

| line | text | action |
|---|---|---|
| 1956 (Table 4.6 caption) | "Scatter identifies damage location, at 14 of 24 ... and a permutation p = 0.0075" | drop p; "identifies" becomes "is associated with" |
| 1978 (body) | "at a group permutation p = 0.0075" | drop the clause |
| 2942 (Discussion) | "location is recovered in 14 of 24 records ... at a group permutation p = 0.0075" | drop p; "recovered" overstates |

Table 5.1 does **not** carry Table 4.6's p, so it needs no edit for this item. It
does carry all three of Table 4.8's, in the "Identify which plate was loosened"
row, **including the 12 of 12 per-run figure that item 1.2(a) found has no
generator.** That row needs the same treatment as the table it summarises.

### (f0) The principle behind the "safe" verdicts above

Two rows in the sweep table are marked safe on a stated principle, which belongs in
the report rather than in a judgement call. **A test whose null distribution is too
narrow is anticonservative: it makes p too small.** Correlated units treated as
independent inflate the apparent evidence. So a defect of this kind can only turn a
true null into a false positive, never the reverse. A **null result** from an
anticonservative test is therefore still safe: had the test been done correctly, the
p-value would only have grown, and a result that failed to reject at the inflated
evidence level would fail to reject at the honest one. This is why the Kruskal and
Spearman rows need no action while the two localisation p-values do.

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

---

## 1.3 — Which storey-call scoring rule is in force?

**Verdict: CONFIRMED_ERROR. Table 3.10 states one rule; the code and every
published number use a different one.**
Script: `audit/scripts/audit_1_3_scoring_rule.py`.

| | rule |
|---|---|
| **Table 3.10, l.1348** | adjacency: "The base plate admits k1 only, Floor 1 admits k1 or k2, Floor 2 admits k2 or k3, and Floor 3 admits k3 only" |
| **`decision_rule_sweep.score()` L144** | exact index match: `truth = STOREYS.index(location)`, `am == truth`, so Floor n maps to k_n alone |

They differ on exactly one record in the whole corpus: **Floor 2 trace, called k3**,
which adjacency scores correct and exact scores wrong.

### The document's own number settles which rule was used

Line 2415 prints "Accuracy over those fourteen is 0.650 against 0.654 between the
two weights". That is a seed-averaged accuracy over the fourteen-record extended
set, and it is decisive:

| rule | predicted accuracy | doc |
|---|---|---|
| exact, F2 trace = k3 counted wrong | 9/14 = **0.6429**, rising to **0.6518** with k2 in 2–3 seeds of 20 | **0.650 / 0.654** |
| adjacency, F2 trace = k3 counted right | 10/14 = **0.7143**, essentially flat across seeds | excluded |

So the exact rule generated the published figures. Table 3.10 describes a rule the
analysis never applied.

### It does not touch the headline number

Worth stating plainly, because it bounds the damage. On the nine severe records the
two rules **agree exactly**, both giving 6/9 and 2 of 3 locations, because the one
record they disagree about is a trace-grade cell outside that set. The rule
discrepancy changes the fourteen-record accuracy and nothing else.

### Edit

Either correct Table 3.10 to describe exact matching, or rescore the fourteen-record
accuracy under adjacency and reprint 0.650 as 0.714. **Correcting the table is the
right call**: the exact rule is the defensible one. Under adjacency, Floor 1 would
be credited for naming k2 and Floor 2 for naming k3, so the two storeys that the
network most needs to tell apart would be scored as interchangeable, and the
sentence at l.2401 ("it fails at exactly the location whose plate would require the
middle storey to be named") would lose its meaning.

---

## 1.4 — What nine records is "6 of 9"?

**Verdict: the figure is arithmetically CONFIRMED and its description is wrong in
three separate ways.**
Script: `audit/scripts/audit_1_4_localisation_records.py`.

### (a) The record set, recovered by enumeration

Twenty records exist on disk. Four are absent, and they are exactly the four
Section 3.6.8 names: Floor 2 light and the three Floor 3 severe replicates. Every
candidate set the document describes, scored under both rules:

| candidate set | n | adjacency | exact | locations |
|---|---|---|---|---|
| A. §3.6.8 severe set: F1 + F2 severe, base uncounted | 6 | 3/6 | 3/6 | 1 of 2 |
| B. footnote's "graded cells", three storeys | 14 | 10/14 | 9/14 | 2 of 3 |
| B'. graded cells only, three storeys | 8 | 7/8 | 6/8 | 2 of 3 |
| **C. base + Floor 1 + Floor 2 severe** | **9** | **6/9** | **6/9** | **2 of 3** |

Only C reproduces "6 of 9 runs (2 of 3 locations)", and it does so under both
rules. (A fifth candidate, "all severe at four locations", collapses onto C, because
the three Floor 3 severe records are the ones the harmonic void removes.) **The nine
records are the base plate, Floor 1 and Floor 2. Floor 3 is not among them.**

### (b) So three descriptions in the document are wrong

| site | text | fact |
|---|---|---|
| Table 4.18, both cells | "at the three storey locations" | the nine are base, Floor 1, Floor 2 |
| Table 4.18, classical cell | "base plate excluded to match the network's label space" | the base plate is included, and is three of the nine |
| Table 4.18, network cell | "the archived Floor 3 case used imputed modes" | no Floor 3 record is in the nine; that caveat belongs to the archived five-prediction run of §4.6.3 |
| footnote, l.2636 | "The network cannot be scored on three of these because harmonics of f1 obscure the second modes of the Floor 3 severe replicates" | the Floor 3 replicates are not among "these"; the void is why the set is nine rather than twelve, and it removes them from **both** methods equally |
| footnote, l.2638 | "its figure covers the graded cells instead" | 6/9 is the severe cells; the graded-cell figure would be 9/14 |
| footnote, l.2639 | "not a matched comparison" | it is matched, record for record |

### (c) The comparison is better than the document claims

Recomputed on the identical nine records:

| record | classical, three-mode LOO | network storey call |
|---|---|---|
| base r1, r2, r3 | hit, hit, hit | k1, k1, k1 — hit, hit, hit |
| F1 r1, r2, r3 | hit, hit, hit | k1, k1, k1 — hit, hit, hit |
| F2 r1, r2, r3 | hit, hit, hit | k1, k1, k1 — **miss, miss, miss** |
| **total** | **9/9** | **6/9** |

The footnote disclaims a matched comparison that the study actually achieved. This
is a finding in the author's favour and the correction strengthens Chapter 5:
100% against 67% on the same nine measurements, with the whole difference at
Floor 2.

### (d) But the 6/9 is inflated, on the document's own rule

This is the substantive problem, not the labelling.

**The base plate supplies three of the six correct calls.** And the document says
three separate times that the base plate should not be scored:

* §3.6.8, l.1362: the base plate "lies outside the label space and its results are reported separately in Section 4.6, **uncounted in the localisation score**"
* §4.6, l.2885: "**no correct answer exists for it inside the label space** ... the least wrong of the three available answers without being a right one"
* **Table 4.18 itself**, two rows below the 6/9: "Localisation, base plate — Outside the network's label space"

Under the rule the document states for itself, the score is **3/6 = 50.0%**, not
6/9 = 66.7%, and the classical comparator on that same six-record set is **6/6**.

The mechanism is that Table 3.10's convention says "the base plate admits k1 only",
so base → k1 is banked as correct. But k1 is the only answer a base-plate loosening
can possibly attract from a three-storey output space, so the network cannot get it
wrong. Crediting it is crediting a forced choice. The classical method has "base
plate" as a class it can genuinely name and be wrong about; the network does not.
**That is the real asymmetry between the two columns, and it is not the one the
footnote describes.**

### Edit — DECIDED: 3 of 6 is the headline, 6 of 9 stated alongside

The alternative was to keep 6/9 with a caveat. Rejected, on the grounds that
**Table 4.18 would then contradict itself on the same page**: its base-plate row,
two rows below, already tells the reader the base is outside the network's label
space. That is item 1.3's failure mode again, a stated rule the numbers do not
follow, and it is the kind of thing an examiner finds without opening any code.
Three further passages (§3.6.8 l.1362, §4.6 l.2885, and §3.6.8's own scoring
description) say the same. The substantive reason is the forced choice: if k1 is
the only representable answer for a base plate, a correct call there measures the
output space and not the model.

**Lead with the under-claim, because it partly offsets the cost.** The result is
not a weaker 50%; it is a *controlled* 50% where the printed 67% was uncontrolled.
On a matched set of six localisation-relevant records the network calls 3 correctly
against the classical method's 6, and the study's own criteria protect a controlled
negative result.

> **Localisation** — Both methods are scored on the same measurements. On the six
> severe replicates at Floor 1 and Floor 2, the two locations that lie inside both
> methods' output spaces, the classical modal method assigns 6 of 6 and the network
> 3 of 6, correct at Floor 1 and wrong at Floor 2. Including the three base-plate
> replicates, for which k1 is the network's only representable answer and which it
> therefore cannot get wrong, the figures are 9 of 9 and 6 of 9. The base plate is
> excluded from the headline because a correct call there measures the output space
> rather than the model.

Delete the footnote's three wrong sentences and replace with: "Both columns are
scored on the same measurements. The three Floor 3 severe replicates are excluded
from both, their second modes being voided by the second harmonic of f1
(Appendix A.1)."

Cost, stated plainly: the headline moves from 67% against 100% to **50% against
100%**. The offsetting gain is that the comparison becomes matched and controlled,
which the printed version explicitly disclaimed.

### (e) Cross-corroboration with 1.2 — why these labels can be trusted

**This is the strongest evidence the audit has produced, and it is worth recording
as such.** Items 1.2 and 1.4 reached the same record structure from different
artefacts and by different routes:

* **1.2** enumerated permutation spaces over the severe runs and found the
  three-mode space to be **9 runs over 3 classes**, the classes being base, Floor 1
  and Floor 2, because Floor 3 has no f2. Its instrument was
  `interpret_capture.modal_vector` on the raw captures.
* **1.4** enumerated candidate record sets against the cached storey calls and
  found the only set yielding 6/9 to be **base, Floor 1, Floor 2 severe**. Its
  instrument was `results_decision_rule_sweep.json`.

Neither used the other's inputs, and the classical 9/9 recomputed in 1.4(c) is
Table 4.8's three-mode row arrived at independently. Two derivations from separate
artefacts agreeing on the record composition is what makes the corrected labels
safe to act on: the corrections in (b) are not a reinterpretation of ambiguous
prose but a fact about which files were read.

It also confirms 1.2(a) from a second direction. The per-run row's 12 runs would
have to include the three Floor 3 severe replicates, whose f2 does not exist. That
row cannot be reproduced from these captures under any scoring convention, which is
consistent with there being no generator for it in the repository.

### (f) Parked option, for Galasso to decide

There is a third possible framing that would remove the whole difficulty rather
than annotate it: **score both methods in the two-mode (f1, f3) space**, where
Floor 3 is observable and the eleven-run set of Table 4.8 applies. That gives four
locations and a genuine four-class problem for the classical method, and it would
let Floor 3 back into the comparison.

**Not taken here, and not recommended under the current deadline.** It needs the
network rescored on two-mode inputs, which is a retrain, not a recount, and the
network's output space would still lack a base-plate class, so the asymmetry in (d)
would survive the change. Recorded as an available option with its record structure
stated: 11 runs, 4 classes, base r1–r3, F1 r1–r3, F2 r1–r3, F3 r1–r2 (one run drops
out of the two-mode space).

### (g) Supporting check: the harmonic void is asserted with support, and its numbers are wrong

The void now carries real weight, since it is what makes the set nine records
rather than twelve. It **is** asserted in body text with numbers, not only in a
caption: lines 1401, 1426, 2032, 2475 and 2529, plus Appendix A.1 note (b). That
part is sound.

The numbers are not. Recomputed from the captures through the pre-existing
`toolkit_common.set_mode_frequencies` flag:

| replicate | f1 | 2f1 | f2 candidate | deviation | 3% flag |
|---|---|---|---|---|---|
| F3 severe r1 | 2.4856 | 4.9713 | 5.0970 | 2.53% | fires |
| F3 severe r2 | 2.4875 | 4.9750 | 5.1032 | 2.58% | fires |
| F3 severe r3 | 2.4861 | 4.9721 | 5.0923 | 2.42% | fires |

The document says "2f1 = 4.98 Hz while f2 falls through approximately 5.2 Hz", at
lines 225, 1997, 2032 and 3130.

* **2f1 = 4.98** should be **4.97** (mean 4.9728).
* **"approximately 5.2 Hz"** should be **5.09 to 5.10 Hz**.

The second one matters beyond a decimal place, and it is **a case where the
correction strengthens the claim**. Confirmed explicitly:

| f2 value | deviation from 2f1 | inside the 3% flag? |
|---|---|---|
| **5.2 Hz, as printed** | **4.57%** | **no, the void would not fire** |
| 5.0970 (r1) | 2.53% | yes |
| 5.1032 (r2) | 2.58% | yes |
| 5.0923 (r3) | 2.42% | yes |

So the printed number contradicts an argument that the true number supports. As
written, a reader who checks 5.2 against the 3% tolerance of l.812 concludes the
void should never have fired and that the three Floor 3 records were dropped
without cause. Correcting 5.2 to 5.09 puts all three replicates inside the
tolerance with margin and makes the exclusion self-justifying. Replace with:

> f2 could not be separated from the second harmonic of f1, which sits at
> 2f1 = 4.97 Hz against a second-mode candidate at 5.09 to 5.10 Hz, within 2.4 to
> 2.6% of the harmonic and so inside the 3% voiding tolerance of Section 3.x.

---

## 1.5 — Statistical wording

Script: `audit/scripts/audit_1_5_stats_wording.py`.

### (a) Table 4.16 is missing a branch, and its n is the attempted count

**Verdict: CONFIRMED_ERROR.**

The caption claims "Every exact solution of the three-parameter inversion, from
3,000 random starts per case". Neither half holds as written.

| case | starts attempted | **converged** | branches cached | branches printed |
|---|---|---|---|---|
| base | 3 000 | 1 275 (42.5%) | 4 | 4 |
| Floor 1 | 3 000 | 560 (18.7%) | 2 | 2 |
| **Floor 2** | 3 000 | 1 581 (52.7%) | **4** | **3** |

**A Floor 2 branch is missing from the table**: k = (2.521, 0.156, 0.365),
fitting to 2.4e-14 Hz, occupying 375 of the 1 581 converged starts, which is the
second-largest basin of the four. At that basin size it is found in essentially
every run, so its absence is a dropped row and not run-to-run variation.

**Table 5.1 already knows this.** Its inversion row reads "Floor 2 admits one of
**four**". Table 4.16 lists three. Table 5.1 is right.

The branch is inadmissible, so no conclusion changes. Add the row.

On n: 3 000 is the attempted count. The observed count behind the branch structure
is 1 275, 560 and 1 581, and the threefold variation is itself informative, since
Floor 1's 18.7% is the rank-deficiency that Section 5.3 diagnoses. Report both.

**Do not print the per-branch residuals to two significant figures.** They are
optimiser residuals from random starts and they do not reproduce: base B2 prints
3.6e-15 against 8.9e-15 recomputed, F2 B3 prints 1.8e-15 against 3.2e-14. All are
at machine precision, which is the only claim being made. Replace the column with
one sentence: "every branch fits the three measured frequencies to better than
1e-13 Hz".

### (b) The linearity test — **promoted to item 1.8, see below**

Moved out of 1.5 because it is cited as licensing the whole graded series, not
just one sentence. See section 1.8.

### (c) Base-moderate f3: the numbers are right, the labels are not

**Verdict: raw values CONFIRMED; one MISMATCH and one wording error.**

Every raw value reproduces from the captures:

| claim | document | recomputed |
|---|---|---|
| f1 across five taps | 1.315 to 1.766 Hz | 1.3149 to 1.7665 |
| third peak across five taps | 11.965 to 12.015 Hz | 11.9649 to 12.0153 |
| f1 scatter | 12.75% | 12.745% (SD) |
| f3 scatter | 0.15% | 0.152% (SD) |
| an eighth harmonic would sweep | 10.5 to 14.1 Hz | 10.52 to 14.13 |

The harmonic argument is **sound**: f3 does not track f1, so it is not 8f1.

Two defects:

* **"a spread of 0.15%" is placed immediately after the range 11.965 to 12.015 and
  reads as that range. It is not. It is the standard deviation. The range is
  0.42%.** And the f1 comparator in the same sentence, "a swing of 34%", *is* a
  range statistic (34.3% of the minimum). So the sentence sets a range against a
  standard deviation.
* **"85 times" is 12.75/0.15, a ratio of two rounded numbers.** Unrounded it is
  **83.6**. Like-for-like on ranges it is 72. Both support the point; neither is 85.

Say which statistic is meant and use it on both sides: "f1 scatters about 84 times
more than f3 across the five taps, 12.75% against 0.15% by standard deviation."

Also, "The ratio of 8.010 on the set": recomputed 8.035. In a cell whose f1
scatters 12.7% between taps, four significant figures on a set-mean ratio is not
meaningful, and the paragraph's own argument is that the set ratio is the
misleading quantity. Quote it as "about 8.0".

---

## 1.6 — The fitted stiffness ratio

**Verdict: the number is CONFIRMED. The directional claim attached to it is not
supported.**
Script: `audit/scripts/audit_1_6_stiffness_ratio.py`.

`solve_healthy_stiffness(F_MEASURED)` returns **1 : 1.1923 : 0.9832**, matching
both printed sites (l.1331, l.1487) and `rig_3dof.py`'s own docstring exactly.

**The 1.023 discrepancy I flagged in an earlier note does not exist.** Both sites
print 0.983. The 1.023 is the k1 of Table 4.16's base-plate branch B3 and is
unrelated. That item is withdrawn.

### The live question is whether 0.983 differs from 1.0

Line 1487 says the ratios "show the storeys are not uniform". For k3 that requires
the interval on k3/k1 to exclude 1.0. Propagating the measured modal uncertainty
through the solver, 20 000 draws, seed 42:

| uncertainty convention | k2/k1 95% CI | k3/k1 95% CI | covers 1.0 |
|---|---|---|---|
| tap SD (0.171, 0.173, 0.123 %) | [1.170, 1.214] | [0.961, 1.006] | **yes** |
| tap SEM, n = 5 | [1.183, 1.202] | [0.973, 0.993] | no |
| **reassembly 1σ (0.15, 0.23, 0.16 %)** | [1.167, 1.217] | **[0.960, 1.006]** | **yes** |

**k2/k1 excludes 1.0 under every convention.** The middle storey really is about
19% stiffer, and that is where the non-uniformity lives.

**k3/k1 covers 1.0 under both defensible conventions.** The reassembly floor is
the right comparator here: a ratio offered as a property of the rig has to survive
a teardown and rebuild, and Section 4.1.4 measured exactly how much a rebuild
moves the modes. Only the tap SEM excludes 1.0, and the SEM answers a narrower
question (how well the mean of five taps of *this* assembly is known) than the
claim being made.

### Edit

As pre-specified: keep the number, drop the directional reading.

> **old:** ratios of 1 : 1.192 : 0.983 show the storeys are not uniform
> **new:** ratios of 1 : 1.192 : 0.983. The storeys are not uniform: the middle
> storey is about 19% stiffer than the lower, which is well outside the
> reassembly reproducibility of Section 4.1.4. The upper and lower storeys are
> not separated by it, k3/k1 = 0.983 with a 95% interval of [0.960, 1.006].

Table 3.11's non-uniformity sentence at l.1331 states the ratio without an
inference and needs no change.

---

## 1.7 — The tap-scatter basis problem

**Verdict: CONFIRMED_ERROR. Both numbers are right; they are different quantities
sharing one name.**
Script: `audit/scripts/audit_1_7_scatter_basis.py`.

Two figures describe the tap scatter of the same twelve cells and differ by up to
a factor of two. Both were recomputed from the raw captures, and both reproduce
**12 of 12**:

| source | definition | base moderate |
|---|---|---|
| Table 4.5, "tap sd" column | standard deviation of f1, as a per cent of the **cell** mean | **12.75** |
| Figure bar labels | full **range** of Δf1, in percentage points of the **baseline** mean | **15.5** |

They differ in the statistic *and* in the denominator, and the document calls both
"tap-to-tap scatter". The author was aware of the figure's basis: the docstring of
`make_figures_ch9.f1_per_tap` says "per-tap range 15.5 pp". It is a labelling gap,
not a computation error, and nothing needs recomputing.

**The body text uses the Table 4.5 basis consistently** at l.1812, l.1894 and
l.1967 (the "factor of 49" checks out: 12.75/0.26 = 49). So the figure is the odd
one out.

**The collision to fix first is l.1894.** It reads "Floor 2 and Floor 3 stay at or
below 0.76% at every grade against 0.20% on the baseline (Table 4.5)", and it sits
directly above bars labelled 1.4, 0.4, 0.5, 0.2 and 0.3 for those same cells. A
reader checking the sentence against the figure below it finds 1.4 against a
claimed ceiling of 0.76.

### Edit

Name the basis in the figure caption and leave every number alone:

> Tap-to-tap scatter of f1, plotted as the full range of Δf1 across the five taps
> of each cell, in percentage points of the session baseline. This is a wider
> statistic than the standard-deviation column of Table 4.5 and on a different
> denominator, so the two differ by roughly a factor of two: base moderate is
> 15.5 pp here against 12.75% there.

### The Discussion's "1.7"

Logged **UNVERIFIABLE**, with the provenance note requested. The sentence at
l.2744 reads "separated by 33 floor-units against a largest replicate standard
deviation of 1.7 (Section 4.4.1)". Item 1.2(g) established that 33 belongs to the
three-mode space while Section 4.4.1 reports the two-mode pair, and that the
matching three-mode quantity is **3.09**. For 1.7 itself: no definition tested
reproduces it. The nearest candidates are 1.78 (largest two-mode per-class SD,
ddof = 1) and 1.83 (mean three-mode run-to-mean distance), both rounding to 1.8.
No script in the repository emits 1.7 for any replicate-spread quantity.

**Provenance:** the sentence cites Section 4.4.1, which does not contain 1.7. The
value therefore has no traceable generator, and the 19.4x ratio derived from it
should not be used. Replace with the reconciled pair from 1.2(g): 33.0 against
3.09, a ratio of 10.7, in the three-mode space.

---

## 1.8 — The linearity result and what cites it

**Promoted from 1.5(b). This is the widest-reaching item in Part 1: it is cited as
licensing the frequency estimates of the entire graded series, which is most of
Chapter 4.**
Script: `audit/scripts/audit_1_5_stats_wording.py`, part (b).

Section 4.1.5 in full: "Swept-sine replicates at three drive amplitudes spanning a
factor of 2.2 showed no statistically significant dependence of f1 on excitation
level (t = -0.63, p = 0.573)."

Recomputed by running the repository's own `linearity_check.py` over the nine
captures: **t = -0.63, p = 0.5726, exactly as printed.** The group f1 means are
2.884, 3.017 and 2.856 Hz, all within 3% of the healthy baseline, confirming the
test was run on the undamaged rig.

### Where it is cited

| line | text | load |
|---|---|---|
| **1515** (assumptions table) | "Constant tap amplitude. Not held. **Section 4.1.5 bounds the consequence** for frequency estimates" | the assumption's entire discharge |
| **1801** (§4.3 opening) | "Tap amplitude varied by roughly **a factor of ten** across sets, which Section 4.1.5 shows does not affect the frequency estimates" | every Δf1 in the graded series |
| 2948 (§5.4) | "points to an **amplitude-dependent contact condition** at the loosened joint" | argues for the mechanism 4.1.5 is cited to exclude, at damaged joints |

### Three defects, and one of them resolves in the author's favour

**1. "A factor of ten" is wrong, and correcting it helps.** Recomputed tap RMS
across the twelve graded cells:

| span | measured |
|---|---|
| set means, twelve graded cells plus two baselines | **2.5x** |
| individual taps, all sixty graded captures | **3.2x** |
| **what Section 4.1.5 tested** | **2.2x** |

The 10x is not the graded series at all. It is the *previous* campaign's figure,
and `linearity_check.py`'s own docstring says so: "the previous campaign's 8-10x
amplitude variation between run groups". A superseded number was carried into a
sentence about the current series. Correcting it largely dissolves the coverage
objection, because the tested 2.2x nearly covers the actual 2.5x.

**2. The test drops the middle of three gains, and it is the deviating one.**

| gain | drive RMS | mean f1 |
|---|---|---|
| 1v4 | 0.325 | 2.884 |
| 2v2 | 0.475 | **3.017** |
| 2v8 | 0.722 | 2.856 |

The published statistic is a Welch t-test of the extremes, n = 3 each. A one-way
ANOVA over all three gives **F(2,6) = 8.29, p = 0.0188**. But a regression of f1 on
drive RMS is null, slope -0.13 Hz per unit, r = -0.300, **p = 0.806**, and the
means are not monotone. So the significant term is between-group scatter with no
amplitude ordering: a property of the swept-sine estimator, not of the structure.
Both the published conclusion and its negation are unsupported by this design.

**3. A null result is not a bound, and the resolution is too coarse to be one.**
This is the part that reaches into Chapter 4. Pooled within-gain scatter is
0.0518 Hz, **1.79% of f1**, so the smallest detectable shift is about **3.59%**:

| quantity | size | inside this test's resolution? |
|---|---|---|
| Floor 1 trace Δf1 | 4.27% | yes |
| base trace Δf1 | 2.29% | **no** |
| Floor 3 trace Δf1 | 1.20% | **no** |
| Floor 2 trace Δf1 | 0.97% | **no** |
| 2σ reassembly floor, f1 | 0.30% | **no**, by a factor of 12 |

`linearity_check.py` prints this itself, on its last line: "this test can only
detect shifts above about 3.59%". The dissertation prints the p-value and omits
the resolution. So l.1515's "bounds the consequence" overstates what a failure to
reject can deliver, and the bound it does deliver, roughly 3.6%, is larger than
three of the four trace-grade shifts.

### The fix is a citation change, not a retraction

**The trace-grade claims are already properly controlled, just not by Section
4.1.5.** Two measured controls do the work:

* **Tap scatter within a cell** (Table 4.5) directly measures tap-to-tap
  variability including drive variation, because the taps are manual. For the four
  trace cells it is 0.26, 0.05, 0.17 and 0.23%, an order of magnitude tighter than
  3.59%.
* **The 2σ reassembly floor** of 0.30% is what the trace margins are actually
  quoted against, at l.1936, "14.2 times the first-mode floor".

So nothing in Chapter 4 has to be withdrawn. Section 4.1.5 has to stop being cited
as the licence, and the real licences named instead.

### Edits

**l.1737, Section 4.1.5.** State the resolution and the unit of test:

> Swept-sine replicates at three drive amplitudes spanning a factor of 2.2 gave no
> detectable dependence of f1 on excitation level, comparing the extreme gains
> (Welch t = -0.63, p = 0.573, n = 3 per group). The within-gain scatter of the
> swept-sine estimate is 1.79% of f1, so the test bounds any drive-induced shift at
> roughly 3.6% and cannot resolve effects below that. Across all three gains the
> between-group differences are significant (F(2,6) = 8.29, p = 0.019) but are not
> ordered by amplitude, and a regression of f1 on drive RMS is null (p = 0.81),
> which points to run-to-run instability in the swept-sine estimate rather than to
> a drive dependence.

**l.1515, assumptions table.** "Bounds" claims more than a null delivers:

> **old:** Not held. Section 4.1.5 bounds the consequence for frequency estimates
> **new:** Not held. Section 4.1.5 bounds any drive-induced frequency shift at
> roughly 3.6%, which is too coarse for the trace grade; the operative controls
> there are the within-cell tap scatter of Table 4.5 and the reassembly floors of
> Section 4.1.4

**l.1801, Section 4.3.** Correct the factor and re-point the licence:

> **old:** Tap amplitude varied by roughly a factor of ten across sets, which
> Section 4.1.5 shows does not affect the frequency estimates
> **new:** Tap amplitude varied by a factor of 2.5 across sets and 3.2 across
> individual taps, comparable to the 2.2 range tested in Section 4.1.5. Within-cell
> tap scatter is reported per cell in Table 4.5 and is below 0.3% at every trace
> cell, so drive variation does not account for the graded shifts

**l.2948, Section 5.4.** No change needed, but note the relation: Section 4.1.5
measured the *undamaged* rig, so its null does not extend to loosened joints, and
Section 5.4's amplitude-dependent contact argument is not in conflict with it. One
clause saying so would pre-empt the obvious examiner question.

---

# Part 2 — sweep, and the decisions that would have gone to the supervisor

The supervisor review is cancelled, so every question in
`QUESTIONS_FOR_SUPERVISOR.md` is decided here with its reasoning, so that it can
be defended in the document.

## Coverage, stated first

Part 2 covered **chapter 1 of the ordering only**: the abstract and conclusions,
plus the proposal-duplication check and the carry-over decisions. Chapters 2 to 5
were not reached. A number not in `reconciliation.csv` has not been checked.

## The word-count baseline could not be verified

No `.tex` on this machine, `texcount` not installed. Searched the repository,
`~/Documents`, `~/Desktop`, `~/Downloads`, iCloud Drive and the connected Google
Drive. **11,975 is taken on trust.** Deltas are exact and computed by
`audit/scripts/word_budget.py`; net **+22 against +25**, achieved by relocating
120 words into captions and a new Appendix A.3 rather than by cutting analysis.

## Chapter 1 findings

All eight abstract and conclusion figures reproduce: reassembly floors
0.30/0.46/0.32; severe clearing the f1 floor by 52 to 202 times
(195.7/201.8/131.9/51.6); an eighth of a turn clearing at all four locations, on
f1 at three and at Floor 3 only on f3 (f1 0.1x, f3 3.6x); monotone at 11 of 12
with the single failure at Floor 2 on f3.

**A basis finding, and a warning about the audit's own method.** Tables 4.5, A.1
and A.2 use *two* baselines: graded columns referred to Session 6, the severe
column to Session 4. Defensible, since each set is measured against its own
session, but no table says so. A first pass here used Day 4 throughout and
produced "8 of 12 monotone", a false MISMATCH. That is item 1.7's failure mode
occurring inside the audit. The script now derives the basis rather than assuming
it, and 45 of 46 cells reproduce within 0.06 pp.

## Decisions

**D1. The localisation headline: 3 of 6.** Recorded in item 1.4. Both numbers
correct; 3 of 6 chosen because Table 4.18 would otherwise contradict its own
base-plate row two rows below, and because k1 is the network's only representable
answer at the base plate, so a correct call there measures the output space. Lead
with the under-claim: the comparison is matched on nine identical records, which
the footnote wrongly disclaims, making this a controlled negative rather than a
weaker positive.

**D2. The classical baseline stands, with the asymmetry stated as a limitation.**
Nearest-class-mean under leave-one-out is a fair comparator: it is the method the
chapter is arguing about, and LOO removes the scored run from its own class mean.
The real asymmetry is that the classical method has a base-plate class it can name
and be wrong about while the network does not. State that as a limitation of the
comparison, not as a finding about the network, because it follows from the
output-space design chosen in Section 3.6 and not from anything the network
learned. Do not give the classical method a fourth class purely to equalise:
that would change what the classical row measures.

**D3. The localisation claim survives without a p-value.** Report the separation
ratio (33.0 against 3.09, a ratio of 10.7) and state explicitly that no valid
permutation test exists for this design, with the two-line reason. That is a
stronger position than an invalid p, and the limitation itself is creditable
material. Table 4.6's scatter result, which has no separation ratio behind it,
is reworded to suggestive and stays out of the Discussion's load-bearing claims.

**D4. The lambda sweep keeps its negative verdict, with the scatter stated.**
"Met; the answer is negative" is right: the question was answered. Add that the
17.8% reduction on the physics term sits within seed-to-seed scatter, so the
negative is that the term moved no task metric, not that the reduction was
precisely measured. Reporting the interval and calling it inconclusive would
understate a result that is consistent across three datasets.

**D5. Re-point the linearity citations; do not soften the trace claims.** The
trace-grade detections are controlled by the within-cell tap scatter (below 0.3%
at every trace cell) and the 2 sigma reassembly floors, both measured. Section
4.1.5 was never the real control. Softening the claims would give up a result
that is properly supported by the wrong citation.

## Carry-over decisions

**U1, the per-run row: REMOVE.** No generator, and a twelve-run three-mode
scoring cannot be built from these captures (9 of 12 severe records have an f2).
It appears in the abstract, the conclusion, Table 4.8 and Table 5.1; all four
move together. The two fixed-space rows carry the claim.

**U2, the "1.7": REMOVE**, replaced by 3.09 and the ratio 10.7.

**U3, Table 4.16's residual column: REMOVE**, replaced by one sentence. The
mantissas are optimiser residuals from random starts and are not a property of
the problem.

**X1, `F_MEASURED` provenance: UNRESOLVED, author to confirm.** f1 = 2.94 matches
Day 4 (2.9420); f2 = 8.04 and f3 = 12.15 match neither Day 4 (8.123, 12.204) nor
Day 6 (8.109, 12.187). The fitted ratio reproduces exactly so nothing downstream
moves, but the source session is recorded nowhere. If it cannot be identified,
say the fit uses frequencies from an early session.

## GEOL0038 / proposal duplication: clean

`GEOL0056___Research_Proposal-10.pdf` diffed against the dissertation at 12-word
and 8-word windows. 141 shared 12-word sequences merged into 8 contiguous
passages, **every one a bibliography entry**. No body prose is shared.

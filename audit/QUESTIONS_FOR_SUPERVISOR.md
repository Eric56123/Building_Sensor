# Questions for the draft to Galasso

To go with the draft. Items 1.2, 1.3 and 1.4 are applied in the text; the rest are
flagged in place. Full working in `audit/AUDIT_REPORT.md`, edits in
`audit/EDIT_LIST.md`, everything recomputed rather than re-read.

Ordered so the first question is the one where a supervisor's read of examiner
expectations should outrank mine.

---

## 1. The localisation headline: 3 of 6, or 6 of 9?

**Both numbers are correct. They score different record sets, and I need a view on
which should be the headline.**

The nine severe records behind the printed "6 of 9" are the **base plate, Floor 1
and Floor 2** (Floor 3's second modes are voided by a harmonic and it is absent
from both methods). The base plate contributes **three of the six correct calls**.

The case for excluding the base plate, which is what I have applied:

* Three passages already tell the reader it is uncounted. §3.6.8 says the base
  plate "lies outside the label space ... uncounted in the localisation score";
  §4.6 says "no correct answer exists for it inside the label space"; and
  **Table 4.18's own base-plate row, two rows below the 6 of 9, says "Outside the
  network's label space".** Keeping 6 of 9 leaves the table contradicting itself
  on one page.
* The substantive reason: the network's output space has three storeys and no base
  class, so **k1 is its only representable answer for a base-plate loosening**. A
  correct call there measures the output space, not the model. It cannot be got
  wrong, so it should not be scored.

The cost is real: **50% against the classical 100%, instead of 67% against 100%.**

The offsetting gain, which I would lead with. I found that the two columns are
scored on **the same nine records**, so the footnote's "not computed over the same
runs" and "not a matched comparison" are both wrong. The study achieved a matched
comparison and disclaimed it. Framed correctly the result is a **controlled
negative**: on six localisation-relevant records the network calls 3 against the
classical method's 6. An uncontrolled 67% seems to me worth less than a controlled
50%, and the objectives table explicitly protects results that answer the question
without giving the anticipated answer.

**Question: do you agree 3 of 6 should be the headline with 6 of 9 given in the
same sentence, or would an examiner read the drop from 67% to 50% as a weaker
result regardless of the framing?**

---

## 2. The classical baseline: is the comparison method the right one?

The classical column is a leave-one-out nearest-class-mean classifier on
normalised modal-shift vectors. It scores 9 of 9 (or 6 of 6 excluding the base
plate), so it is perfect on this data and the comparison is "network loses".

Two things I am unsure of:

* **Is nearest-class-mean the right classical comparator**, or is it too strong a
  baseline to be interesting, given that it is fitted on the same twelve runs it
  scores? Leave-one-out removes the scored run from its own class mean, but with
  three replicates per class the remaining two still come from the same rebuild.
* **Should the classical method be given the base plate as a fourth class?** It
  can name the base plate and be wrong about it; the network cannot. That
  asymmetry is the real difference between the two columns, and it is not the one
  the current footnote describes.

**Question: is the classical baseline as constituted defensible, and should the
asymmetry in label spaces be stated as a limitation of the comparison or as a
finding about the network's design?**

---

## 3. Does the localisation claim survive without inferential support?

I have removed the permutation p-values from Tables 4.6 and 4.8, and I think the
reasoning is right, but it leaves the chapter's main classification result with no
significance test at all.

The reason no test is valid here is a property of the design, not of the analysis:

* **Permuting individual runs is anticonservative.** The three replicates of a
  cell share one rebuild and one damage application, so they are correlated under
  the null and are not exchangeable with runs from other cells.
* **Permuting intact replicate groups has zero power.** Leave-one-out
  nearest-class-mean depends only on the partition, and relabelling intact groups
  leaves the partition untouched, so the statistic cannot change. I enumerated all
  24 group-wise labellings: every one scores 12 of 12. This is not a small
  p-value or a large one; the test cannot reject anything on any dataset.
* So **location cannot be separated from rebuild in this design.** Fixing it needs
  independent rebuilds within a cell, not repeated taps, which is future work.

What survives is descriptive and, I think, strong: all twelve severe runs are
assigned to their own location, and the closest pair of class means is 33.0
floor-units apart against a largest run-to-own-mean distance of 3.09, a ratio of
10.7.

**Question: is a separation ratio of 10.7 with an explicit statement that no valid
permutation test exists acceptable as the chapter's localisation result, or does
an MSc examiner expect a p-value even where one cannot be justified?**

A related sub-question: Table 4.6's scatter-based localisation (14 of 24, driven
almost entirely by the base plate) has the same defect but no separation ratio
behind it. I have reworded it from "identifies damage location" to "is associated
with", i.e. **suggestive rather than established**. Is that enough, or should it
come out of the Discussion entirely?

---

## 4. The lambda-sweep result, where the effect sits inside fold-to-fold scatter

The physics-loss ablation reports a 17.8% reduction on the physics term with no
movement in any task metric. The difficulty is that the reduction is comparable to
the seed-to-seed scatter across the sweep, so "the term is minimised without
moving any task metric" is doing a lot of work on a difference that is not clearly
outside noise.

**Question: how should a negative ablation result be framed when the effect it
reports is inside the run-to-run variation? Report the interval and let it stand
as inconclusive, or state the negative conclusion and note the scatter as a
limitation?** The objectives table currently records this as "Met; the answer is
negative", which I think is right, but the supporting number may be weaker than
the verdict implies.

---

## 5. One methodological point I want to check before the final revision

Section 4.1.5's linearity test is cited in two places as licensing the frequency
estimates of the whole graded series. Recomputing it, the test's resolution is
about **3.6%**, which is larger than three of the four trace-grade shifts it is
invoked to protect (0.97%, 1.20%, 2.29%).

Nothing has to be withdrawn, because those claims are actually controlled by two
other measured quantities: the within-cell tap scatter (below 0.3% at every trace
cell) and the 2σ reassembly floors. So my fix is to re-point the citations rather
than retract anything.

**Question: is re-pointing sufficient, or would you want the trace-grade detection
claims softened as well?** I would rather over-correct here than have an examiner
find that the test cited for a 1% shift cannot resolve better than 3.6%.

# Unverifiable numbers

**Audit target: `df32d53`.** Part 1 scope only.

A number is listed here when it could not be reproduced from committed code and
committed data, and no generator for it could be found. This is a statement about
traceability, not a claim that the number is wrong.

Each entry gives what was searched, so the author can either point at the missing
generator or decide the number cannot be defended.

---

## U1. Table 4.8 and Table 5.1 — the per-run localisation row

**Claim:** "12 of 12 under the per-run rule of Section 4.4.1", shuffled mean 3.03,
p = 0.0001.

**Status: no generator exists in the repository.**

Searched: every file that permutes anything. There are two.
`four_floor/inversion_robustness.py` implements the fixed two-mode and three-mode
tests and contains no per-run scoring. `four_floor/run_experiments.py` permutes for
the lambda sweep, which is unrelated. `four_floor/decision_rule_sweep.py` contains
no permutation code at all.

**Cross-check from a second direction (item 1.4).** A twelve-run per-run scoring
would have to include the three Floor 3 severe replicates. Those records have no
f2: it is voided by the second harmonic of f1 in all three (Appendix A.1,
recomputed and confirmed). So a twelve-run scoring cannot be built from these
captures under any convention that needs three modes.

**Options:** regenerate from committed code, or delete the row from Table 4.8 and
from Table 5.1's "Identify which plate was loosened" entry. The remaining two rows
carry the claim on their own.

---

## U2. Discussion l.2744 — "a largest replicate standard deviation of 1.7"

**Claim:** "separated by 33 floor-units against a largest replicate standard
deviation of 1.7 (Section 4.4.1)".

**Status: no definition tested reproduces 1.7.**

Provenance note, CORRECTED. An earlier draft said the cited section does not
contain the number. **That was wrong**, and Part 2's verification pass caught it:
Section 4.4.1 states both pairs at l.2042, "33 floor-units apart in the
three-mode space against a largest replicate standard deviation of 1.7, and 26.6
against 2.1 in the two-mode projection". The cross-reference is sound. The value
appears at **two** sites, l.2042 (origin, Results) and l.2744 (Discussion), and
both must change together.

Candidates computed for the "largest replicate standard deviation":

| definition | value |
|---|---|
| largest two-mode per-class SD, ddof = 1 | 1.78 |
| mean three-mode run-to-own-mean distance | 1.83 |
| largest three-mode run-to-own-mean distance | 3.09 |
| two-mode equivalent of the last | 2.06 |

Both near candidates round to **1.8**, not 1.7. No script in the repository emits
1.7 for any replicate-spread quantity.

**Consequence:** the 19.4x ratio derived from 33/1.7 has no support. The reconciled
three-mode pair is 33.0 against 3.09, a ratio of 10.7.

---

## U3. Table 4.16 — the per-branch max|Δf| column

**Claim:** eight residuals quoted to two significant figures, from 3.6e-15 to
5.7e-14.

**Status: not reproducible, and not reproducible in principle.**

These are least-squares residuals at convergence from randomly seeded starts. Six
of the eight do not match a re-run: base B2 prints 3.6e-15 against 8.9e-15,
base B3 prints 2.0e-14 against 3.4e-14, F1 B2 prints 8.9e-15 against 5.3e-15,
F2 B2 prints 1.4e-14 against 2.1e-14, F2 B3 prints 1.8e-15 against 3.2e-14.

The order of magnitude is stable and the claim being made, that every branch fits
to machine precision, holds in every run. The individual mantissas are not a
property of the problem. See edit-list item 6c.

---

## Not unverifiable, but flagged for provenance

**`F_MEASURED = [2.94, 8.04, 12.15]`** in `simulation/rig_3dof.py` is hardcoded.
f1 = 2.94 matches the Day-4 baseline (2.9420 recomputed). f2 = 8.04 and f3 = 12.15
match neither Day-4 (8.126, 12.204) nor Day-6 (8.109, 12.187) within tap scatter.
The fitted ratio 1 : 1.192 : 0.983 reproduces exactly from these three numbers, so
nothing downstream is affected, but the sourcing of f2 and f3 is not recorded
anywhere in the repository. Worth a sentence in the methodology if the ratio is
quoted as measured.

---

## Withdrawn

**The "1 : 1.194 : 1.023" stiffness ratio.** Flagged before item 1.6 was run; it
does not exist. Both printed sites (l.1331, l.1487) say 0.983, and
`solve_healthy_stiffness` returns 0.9832. The 1.023 was Table 4.16's base-plate
branch B3 k1, misread by the auditor.

---

## U4. The "18 of 18 at two further sensor positions"

**Claim:** abstract and Conclusion, "18 of 18 at two other sensor positions
against references recorded elsewhere".

**Status: NOT RE-VERIFIED in this pass. Provenance established, score not
recomputed.**

The 18 records exist and were located: `sensorF1_{base,F1,F3}_severe_r{1,2,3}`
and `sensorF2_{base,F1,F3}_severe_r{1,2,3}`, nine at each of two alternate sensor
positions, five taps each. They are mapped in Appendix A.6.

The classification score itself was not recomputed. A first attempt used an
ad-hoc leave-one-out with a broken self-exclusion and returned 8 of 8, which is
an artefact of that attempt and not a finding about the document. It is recorded
here so that the failed attempt is not mistaken for a result.

This claim sits in Part 2 chapter 3, which was never swept. **It is not a known
discrepancy; it is unchecked.** To close it, score the 18 records against the
references named in Section 4.4.2 using the same nearest-class-mean rule as
Table 4.8, taking each alternate position's own baseline as the reference.

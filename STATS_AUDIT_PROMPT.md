# Claude Code prompt — numerical/statistical audit of the GEOL0056 dissertation

Paste everything below the line into Claude Code running at the root of `Building_Sensor`.
Before you run it, copy the dissertation source (`.tex` and/or the compiled `.pdf`) into
`./dissertation/` so the agent can read the claims it is auditing.

---

## Role

You are auditing a submitted-draft MSc dissertation for numerical self-consistency. The
dissertation is "Physics-Informed Neural Networks for Seismic Structural Health Monitoring"
(UCL GEOL0056). Every quantitative claim in it is supposed to be reproducible from the code
and data in this repository. Your job is to prove that, one number at a time, and to build a
reconciliation record showing where the prose and the code disagree.

An external reviewer has already checked the *internal arithmetic* of the PDF and found it
mostly sound. Do not repeat that. Your job is the harder one: regenerate each number **from
the raw data and the actual code path**, and compare it to what the document claims.

## Prime directive

**Never verify a number by re-reading the document. Verify it by re-computing it.**

For every claim, the evidence you produce must be a script in `audit/` that reads from
`four_floor/pi_logs/`, `experiments/`, or the relevant module, prints the recomputed value,
and states whether it matches the document. If a number cannot be regenerated because the
generating code or data is missing, that is itself a finding — record it as
`UNVERIFIABLE` with a note on what is missing. Do not guess, and do not reconstruct a
plausible-looking calculation and then call it verified.

## Repository orientation (verified to exist)

| Path | What it holds |
|---|---|
| `four_floor/pi_logs/run_index.csv` | 42 experimental runs, one row each, with location/grade/excitation in `Ground Truth Notes` |
| `four_floor/pi_logs/Floor4_*/`, `Floor3_*/` | Raw acceleration CSVs per damage cell |
| `four_floor/inversion_robustness.py` | Tap-scatter feature, Kruskal tests, LOO classification, **grouped permutation nulls** (see ~L455–515) |
| `four_floor/ringdown.py` | Per-tap `f_mean`, `f_sd` (`ddof=1`), damping |
| `four_floor/matrix_analysis.py` | Frequency-shift matrices, `nanstd(..., ddof=1)` at ~L243 |
| `four_floor/freq_shift_detector.py`, `toolkit_common.py` | Feature extraction, tap handling |
| `four_floor/linearity_check.py` | Excitation-amplitude linearity test (the `t = −0.63, p = 0.573` claim) |
| `four_floor/make_figures_ch9.py`, `make_ch8_figures.py` | Figure generation for Ch. 8/9 |
| `four_floor/results_decision_rule_sweep.json`, `results_inversion_branches.json` | Cached decision-rule and inversion outputs |
| `four_floor/pinn/`, `four_floor/simulation/` | Network, dataset generation, 3-DOF rig model |
| `four_floor/train.py`, `run_experiments.py` | Training and λ-sweep driver (permutation at ~L390) |
| `experiments/results_summary*.csv`, `loss_log_*.csv` | λ-sweep loss logs and hold-out summaries |

Start by running `git log --oneline -30` and reading `four_floor/CHANGELOG.md` and
`four_floor/DISSERTATION_SUMMARY.md` to understand what was regenerated when. **Flag any case
where a results file predates the code that supposedly produced it** — that is a silent
staleness bug and it is exactly the kind of thing that invalidates a table.

## Part 1 — Five flagged issues (do these first, in order)

For each, produce: the recomputed value, the document's value, a verdict
(`CONFIRMED_ERROR` / `CONFIRMED_CORRECT` / `AMBIGUOUS` / `UNVERIFIABLE`), and a minimal
recommended fix that changes as few downstream numbers as possible.

### 1.1 — Table 4.5 uncertainty column: SD or SEM?

The table says uncertainty is "propagated from the tap standard deviations." The reviewer
believes the printed values are actually propagated *standard errors* — i.e. the SDs divided
by √5.

Find the code that produces the Table 4.5 uncertainty column. Determine empirically whether
it divides by `sqrt(n)` anywhere (check `ringdown.py`, `matrix_analysis.py`,
`freq_shift_detector.py`, `toolkit_common.py`). Then:

- Recompute the full uncertainty column **both ways** — pure SD propagation in quadrature,
  and SEM propagation — from the raw tap frequencies in `pi_logs/`.
- Print a three-column comparison: `document | SD-propagated | SEM-propagated`, for all
  twelve cells.
- State which one the document's numbers match, and confirm `n` really is 5 taps for every
  cell (check this per cell — do not assume it is uniform; report any cell with n ≠ 5).
- Report the recomputed baseline SD and each damaged-set SD to 4 s.f. so the methodology text
  can be corrected against real values.

Also check §3.5, Table 3.7 and Table 4.5 for consistent wording, and list every other place
in the document where "standard deviation" is used to describe a quantity that is actually
a standard error.

### 1.2 — Permutation p-values: enumerate the exact space, do not sample it

This is the highest-priority item. The document reports p = 0.0001, 0.0001 and 0.0042 for the
per-run, fixed-`f1,f3`, and fixed-three-mode localisation tests, from 10,000 Monte Carlo
group-wise permutations. The reviewer argues that if the permutation unit really is the
location group, the exact space for the 12-run severe test has only 4! = 24 distinct
labellings, so the floor is p = 1/24 ≈ 0.0417, and 3! = 6 → p ≥ 0.167 for the three-mode case.

Do this:

1. **Locate the exact code that generated each of the three p-values in Table 4.8.** It may
   not be `inversion_robustness.py` — search the repo for the test, and if you cannot find it,
   say so plainly rather than auditing a lookalike.
2. **Establish the true permutation unit** by reading the code, not the prose. For each test,
   report: how many exchangeable units exist, what the label multiset is, and therefore the
   exact size of the permutation space.
3. **Enumerate that space exhaustively** with `itertools.permutations` and compute the exact
   p-value. These spaces are tiny; there is no reason to sample. Report exact p as a fraction
   *and* a decimal (e.g. `1/24 = 0.0417`).
4. Report the **attainable minimum p-value** for each test, so the document can never again
   claim a resolution finer than the design supports.
5. Separately audit the `p = 0.0075` group-permutation result (Table 4.6). Note that in
   `inversion_robustness.py` the grouping variable is
   `GRP = r[0] * 4 + min(r[1], 3)` — that is **one group per location×grade cell, not per
   location**. Work out what that implies for the exchangeability assumption and the size of
   the permutation space, and whether the resulting p-value is defensible. State clearly
   whether the cell-level grouping still leaks replicate correlation.
6. Give the exact replacement sentences for Table 4.8, its caption, the Discussion, and
   Table 5.1.

Then, importantly: **quantify the descriptive result that survives.** Recompute the 12/12,
11/11, 9/9 and 18/18 counts from source, plus the class-mean separation (reported as 33
floor-units) against the maximum replicate scatter (reported as 1.7 units). If the inferential
claim has to weaken, the descriptive claim needs to be airtight and stated in effect-size
terms.

### 1.3 — Floor 2 localisation scoring rule contradicts itself

Table 3.10 defines the experimental scoring rule as adjacency-based (a plate adjoins two
storeys): Base→k1; Floor 1→k1 or k2; Floor 2→k2 or k3; Floor 3→k3. But §4.6.4 and Figure 4.10
score Floor 2 as requiring k2 exactly, and call it a failure.

- Find the scoring function in code. Determine which rule it actually implements.
- Recompute network localisation accuracy under **both** rules, per record and per location,
  from the Table 4.14 source data.
- Report the two accuracy figures side by side and identify every sentence, table cell and
  figure in the document whose value changes under each choice.
- Check whether the classical method in Table 4.18 is scored under the *same* rule as the
  network. If it is not, the side-by-side comparison is invalid — say so explicitly.

Recommend one rule and apply it consistently. State the recommendation as a rule for the
whole document, not just for Floor 2.

### 1.4 — The "6 of 9" network localisation figure in Table 4.18

Table 4.18 reports "6 of 9 runs (2 of 3 locations)" but the text says the network could not be
evaluated on the same nine severe runs as the classical method, and Table 4.14 appears to
contain 14 records at the three storey locations (6 Floor 1 + 5 Floor 2 + 3 Floor 3).

- Recount the records in the Table 4.14 source data. Confirm or correct the 6/5/3 split.
- Determine, from code, exactly which records the "6 of 9" denominator refers to. If no set of
  nine records can be identified, mark it `UNVERIFIABLE` and say so.
- Compute the correct record-level accuracy over the actual denominator, under whichever
  scoring rule 1.3 settles on.
- State whether the network and classical rows in Table 4.18 are evaluated on comparable
  denominators. If not, propose how the table should be restructured so the comparison is
  honest.

### 1.5 — Statistical wording that overstates

- **Table 4.16:** confirm the Monte Carlo `n` (reported as 1000) from code, then rewrite
  "probability 1.000 / 0.000" as an observed count out of n.
- **Linearity test:** recover from `linearity_check.py` exactly what observations enter the
  test, the degrees of freedom, and the amplitude range. Report as `t(df) = ..., p = ...`.
  Confirm the 2.2× amplitude range from the raw data. Draft a replacement sentence that
  claims *absence of detected dependence*, not linearity — and, if the data allow, add a
  power statement or an equivalence bound so the null result carries weight.
- **Appendix A.1:** recompute the Base-moderate f3 statistics. Confirm whether 0.15% is the
  SD or the range, and reconcile against the 11.965–12.015 Hz endpoints and the downstream
  `12.75 / 0.15 = 85` ratio.

## Part 2 — Full reconciliation sweep

Once Part 1 is done, extract **every** numerical claim in the dissertation body, methodology,
and appendix, and reconcile each one against a recomputed value. Build
`audit/reconciliation.csv` with columns:

```
claim_id, location (§/Table/Figure), claim_text, document_value, recomputed_value,
abs_diff, rel_diff_pct, source_script, source_data, verdict, note
```

Verdicts: `MATCH` (agrees to printed precision) · `ROUNDING` (differs only in last digit,
consistent with computing from unrounded inputs — note this, do not flag as an error) ·
`MISMATCH` · `UNVERIFIABLE` · `STALE` (regenerable but the cached artefact disagrees with
current code).

Priorities within this sweep:

1. **Cross-table consistency.** Any number appearing in more than one place (Ch. 4 → Discussion
   → Table 5.1 → abstract → conclusions) must be identical everywhere. Build a
   value-to-locations index and flag every value that appears with two different renderings.
2. **Derived-quantity chains.** Where a number is computed from other printed numbers
   (percentage shifts from frequencies, detection margins from shifts, ratios against the
   0.30% reassembly floor), verify the whole chain from the unrounded source, and flag
   anywhere the document has propagated a *rounded* intermediate.
3. **λ-sweep claims.** Recompute from `experiments/results_summary*.csv` and the loss logs:
   the 17.75%/17.8% physics-loss reduction, the hold-out MAE range, the fold-to-fold scatter,
   and the sensitivity of `L_phys` across λ ∈ {0, 0.01, 0.1, 1.0}. Confirm whether logged
   "Phys Loss" is pre- or post-λ (the methodology notes `physics_informed_loss` applies λ
   internally) and whether the document's comparison is like-for-like. **If the reported
   reduction is smaller than the fold-to-fold scatter, state that explicitly** with both
   numbers, because that is the honest framing.
4. **Model and dataset arithmetic.** Verify the 4,611 trainable parameters by instantiating
   the model and calling `sum(p.numel() for p in model.parameters() if p.requires_grad)`.
   Verify the 32.8% undamaged fraction by sampling the actual dataset generator, not by
   redoing `30 + 22/8` on paper. Verify 500 × 2 = 1,000 → 10,000 windows → 8,000/2,000 split
   by inspecting the real dataset objects, and confirm the fold split is genuinely grouped
   (no window from one stiffness vector appearing on both sides).
5. **Determinism.** Re-run each analysis twice with the documented seed. Any claim whose value
   moves between runs is `UNVERIFIABLE` until the seed is pinned — report the observed spread.

## Part 3 — Deliverables

Write all of these into `audit/`:

1. `audit/AUDIT_REPORT.md` — Part 1 findings first, each with verdict, evidence, and exact
   replacement text for the document. Then a summary of Part 2 grouped by severity. Open with
   a table of every `MISMATCH` and `UNVERIFIABLE` and nothing else, so the top of the file is
   the action list.
2. `audit/reconciliation.csv` — as specified above.
3. `audit/scripts/` — one runnable script per Part 1 issue plus the sweep driver. Each must
   print recomputed vs. documented and exit non-zero on mismatch, so this can be re-run as a
   regression check after edits.
4. `audit/EDIT_LIST.md` — an ordered, copy-pasteable list of document edits: file, section,
   exact old text, exact new text. Order by blast radius (changes that cascade into other
   tables first). For each edit, list every other location that must change with it.
5. `audit/UNVERIFIABLE.md` — anything you could not regenerate, with the specific missing
   code, data file, or seed, and what would be needed to close it.

## Ground rules

- Work through Part 1 issues one at a time. Finish and write up each before starting the next.
- Read the code before forming a view. Where prose and code disagree, **the code is the
  ground truth for what was computed** — but the code may itself be wrong, so also check the
  code against the stated statistical intent.
- Do not edit the dissertation source. Produce the edit list; the author applies it.
- Do not edit analysis code to make numbers match. If code is wrong, write the fix as a
  *proposal* in the report with a diff, and note every downstream number it would change.
- Prefer exact enumeration over Monte Carlo wherever the space is small enough. State the
  space size before you choose.
- Report negative and inconvenient findings plainly and early. A weakened p-value that is
  correctly derived is worth more than a strong one that an examiner can dismantle. Where a
  claim has to be softened, supply the strongest *defensible* version alongside it, in
  effect-size or descriptive terms.
- If you find a sixth issue the reviewer missed, treat it with the same priority as Part 1.
- Flag anything where the document's statistical *design* — not just its arithmetic — limits
  what can be concluded (replicate correlation, multiple comparisons across the 12 cells,
  n = 5 taps, n = 5 rebuilds).

Begin with repository orientation and Part 1, item 1.1.

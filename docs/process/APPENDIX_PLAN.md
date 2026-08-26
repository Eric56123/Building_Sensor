# What to put in the appendix

Appendices are **uncounted**, so everything here is free against your 12,000-word
cap. The guidelines list three categories explicitly: tables of data summarised
in the main text, derivations of equations, and supporting figures not integral
to the main text. They also say to put a full dataset in an appendix, e.g. a
spreadsheet, and the submission instructions ask for *"the dissertation (PDF)
plus any data appendices"* by email.

You currently have one appendix section (A.1, harmonic contamination).

⚠ **One rule while adding these:** every number must come from
`audit/reconciliation.csv` or be recomputed by a script in `audit/scripts/`.
Adding unverified figures now would undo the audit.

---

## 1. MUST ADD — A.2, Linearity of f₁ in drive amplitude

**Why this one isn't optional.** §4.1.5 now states *"resolve only shifts above
3.6%"* and the assumptions table repeats it as *"bounds any drive-induced shift
at roughly 3.6%"*. That number appears twice and is supported nowhere. It came
out of the audit, and when you dropped the Appendix A.3 citation the supporting
detail went with it. As it stands a marker can see the claim and not its basis.

Draft:

> **A.2 Linearity of f₁ in drive amplitude**
>
> Swept-sine replicates were recorded at three drive gains, n = 3 per gain,
> spanning a factor of 2.2 in amplitude. Regression of f₁ on drive RMS is null
> (t = −0.63, p = 0.573, p = 0.81 on the RMS predictor). The within-gain scatter
> of 1.79% sets the resolution of the test at roughly 3.6%, which exceeds three of
> the four trace-grade shifts it is invoked to license.
>
> A one-way ANOVA across all three gains is significant (F(2,6) = 8.29,
> p = 0.019). The deviating group is the middle gain, which the pairwise
> extreme-gain comparison omits. Absence of a detected trend across the extremes
> therefore does not establish linearity across the range.
>
> The test bounds a drive-induced shift only coarsely. Trace-grade detection rests
> instead on the tap scatter of Table 4.5 (0.26, 0.05, 0.17 and 0.23% at the four
> trace cells) and on the reassembly floors of Section 4.1.4.

**Check before writing:** confirm how 3.59% is derived from the 1.79% scatter —
it looks like 2σ, but take it from the audit script rather than assuming.

---

## 2. HIGH VALUE — A.3, The permutation space

**Why.** §4.4 asserts that no valid permutation test exists. Right now that's a
claim; the arithmetic makes it a demonstration. This is the difference between
looking like you withdrew a result and looking like you diagnosed one — and
"critical evaluation" is named explicitly in the 85–100 band.

Draft:

> **A.3 Why no permutation test of the location effect is valid**
>
> Twelve replicated severe runs sit in four location groups of three. The number
> of distinct label assignments preserving the group sizes is 12!/(3!)⁴ = 369,600.
> In the fixed two-mode space, 11 runs in groups of 3, 3, 3, 2 give
> 11!/(3!3!3!2!) = 92,400; in the three-mode space, 9 runs in three groups of
> three give 9!/(3!)³ = 1,680.
>
> Leave-one-out nearest-class-mean classification is invariant under any
> relabelling that preserves the partition, because each run remains nearest its
> own group mean. Exactly 4! = 24, 3! = 6 and 3! = 6 relabellings preserve the
> partition in the three spaces, so the exact permutation p-values are
> 24/369,600 = 6.5 × 10⁻⁵, 6/92,400 = 6.5 × 10⁻⁵ and 6/1,680 = 0.0036.
>
> Neither test is usable. Permuting at run level treats three replicates of a
> single damage application as independent, which they are not: they share one
> rebuild and are correlated under the null. Permuting whole groups instead leaves
> the classification score unchanged for every one of the 24 labellings, so the
> statistic has no power by construction and its p-value carries no information
> about the data.
>
> Separating location from rebuild requires independent rebuilds within each cell
> rather than repeated taps on one. The result is therefore reported as an effect
> size: the closest pair of class means is separated by 33.0 floor-units against a
> largest within-class distance of 3.09, a ratio of 10.7.

---

## 3. WORTH ADDING — A.4, Per-tap first-mode estimates

Table 4.5 reports cell means and tap standard deviations over five taps. The 65
individual tap values (13 sets × 5) appear nowhere. This is squarely the
guidelines' *"tables of data summarised in simplified tables in the main text"*,
and it makes the standard-error-versus-standard-deviation distinction in Table
4.5's caption legible instead of asserted.

A single table: set · tap 1–5 f₁ (Hz) · mean · SD · SD as % of mean.

---

## 4. WORTH ADDING — A.5, Reassembly replicates

The floors of 0.30, 0.46 and 0.32% carry every detection claim in Chapter 4, and
Table 4.3 gives only the summary. Add the per-rebuild f₁, f₂, f₃ for all five
teardown cycles, with the 2σ derivation shown. Also worth stating plainly that
n = 5 makes these operational rather than formal statistical limits — you already
say this in the body, and repeating it beside the raw numbers costs nothing.

---

## 5. CHEAP — A.6, Run index

A provenance table of all 42 runs: run ID, timestamp, session, sensor position,
damage location, grade, and which analyses each feeds. `pi_logs/run_index.csv`
already has most of it. This demonstrates campaign scope for the 40-mark section
and lets a marker trace any figure back to a capture.

---

## 6. Data appendix — the files you email

The guidelines ask for data appendices alongside the PDF. Send a single zip:

| File | What it is |
|---|---|
| `run_index.csv` | 42 runs, full provenance |
| `pi_logs/**/*.csv` | 85 raw and processed capture files (22 MB) |
| `rig.json` | rig geometry, masses, measured baseline |
| `results_decision_rule_sweep.json` | 20 cells × 40 runs, network calls per cell |
| `results_inversion_branches.json` | every exact inversion branch (Table 4.16) |
| `experiments/results_summary*.csv` | λ-sweep hold-out results |
| `README.txt` | one page: what each file is, which table or figure it produces |

22 MB may bounce on UCL mail. If it does, put the zip in the GitHub repo or on
Zenodo and give the link in the email — you already cite Zenodo DOIs elsewhere,
so the precedent is set.

Add a one-line **data availability statement** in the front matter or at the head
of the appendix pointing at the repository. Uncounted, and it reads as good
practice.

---

## Suggested order, given six days

1. **A.2 linearity** — closes an unsupported number that is currently in the body twice.
2. **A.3 permutation** — converts §4.4's assertion into a demonstration.
3. **Data zip + README** — no LaTeX, no recompile, no risk.
4. **A.4 per-tap table** — mechanical, just needs the numbers pulled.
5. **A.5 rebuild table**, **A.6 run index** — if time allows.

Items 1 and 2 are the ones that change how the work reads. Items 3–6 are
completeness. None of them touches the word count, and none can break the
verified body text — but re-run `audit/scripts/` after any change that pulls
numbers from the analysis, and add each new figure to `reconciliation.csv`.

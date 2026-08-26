# Claude Code prompt — appendix tables and data package

Paste below the line into Claude Code at the root of `Building_Sensor`.

---

## State

The dissertation is finished and verified. All Part 1 audit edits are applied and
the compiled PDF passes a full check: no broken references, no placeholders, no
residual superseded values. **Do not propose changes to the body text.** The word
count sits just under a hard 12,000 cap, so nothing you produce may add counted
words.

`audit/` holds `AUDIT_REPORT.md`, `EDIT_LIST.md`, `UNVERIFIABLE.md`,
`reconciliation.csv` (55 rows) and seven scripts under `audit/scripts/`, all
exiting 0. Those scripts already recompute most of what is needed below — **reuse
them rather than writing new derivations**.

**There is no `.tex` source on this machine.** The dissertation lives on Overleaf.
So every LaTeX deliverable must be a **self-contained, paste-ready block**, not an
edit to a file. State the packages each block needs (`booktabs`, `siunitx`, etc.)
and flag anything that may clash with the existing preamble.

Deadline is 1 September. Six days.

## Constraints

- **Appendices are uncounted**, so length here is free. Body text is not — do not
  suggest body edits.
- **Every number must be recomputed**, not copied from the PDF. Each new figure
  gets a row appended to `audit/reconciliation.csv` in the existing schema
  (`item, location, claim, documented, recomputed, verdict, note`) with verdict
  `NEW`.
- If a number cannot be regenerated from committed code and data, say so and
  leave it out. Do not reconstruct a plausible value.
- Commit after each deliverable.

---

# Deliverable 1 — LaTeX appendix sections

Produce `audit/appendix/A2.tex` … `A6.tex`, each a complete section ready to
paste. Also write `audit/appendix/README.md` explaining insertion order and
required packages.

## A.2 — Linearity of f₁ in drive amplitude *(highest priority)*

§4.1.5 asserts *"resolve only shifts above 3.6%"* and the assumptions table
repeats it as *"bounds any drive-induced shift at roughly 3.6%"*. **That number
is currently supported nowhere in the document.** It came out of audit item 1.8
and the supporting detail was dropped when the Appendix A.3 citation was removed.
This section restores it.

Source: `four_floor/linearity_check.py` and whichever audit script covered item
1.8 (promoted from 1.5b — likely `audit/scripts/audit_1_5_stats_wording.py`).

**First, resolve this explicitly:** confirm how the 3.59% resolution derives from
the 1.79% within-gain scatter. It looks like 2σ, but establish it from the code.
If it is not 2σ, report what it actually is and correct the section accordingly —
and flag that the body's "3.6%" may then need changing, which would be the one
exception to the no-body-edits rule.

Include: number of gains and replicates per gain, the amplitude range, the
regression on drive RMS (t, df, p), the within-gain scatter, the derivation of
the resolution figure, the one-way ANOVA across all three gains
(F(2,6) = 8.29, p = 0.019 — verify), which gain deviates and why the pairwise
extreme comparison misses it, and the tap-scatter values at the four trace cells
that carry trace-grade detection instead.

State the conclusion as absence of a detected dependence, not as linearity.

## A.3 — Why no permutation test of the location effect is valid

§4.4 asserts this; the arithmetic demonstrates it.

Source: `audit/scripts/audit_1_2_permutation.py`, which already enumerates the
spaces.

Include: the three permutation-space sizes with their factorial expressions, the
count of partition-preserving relabellings in each, the resulting exact p-values,
and the invariance argument — that leave-one-out nearest-class-mean is unchanged
under any relabelling preserving the partition, so the group-level test has zero
power by construction rather than a null result. Then the two reasons neither
test is usable (run-level anticonservative through shared rebuild; group-level
degenerate), the design fix (independent rebuilds per cell), and the effect size
that replaces them (33.0 floor-units against a largest within-class distance of
3.09, ratio 10.7).

Frame it as diagnosis, not retraction.

## A.4 — Per-tap first-mode estimates

Table 4.5 reports cell means and tap standard deviations over five taps; the
individual values appear nowhere.

Source: `audit/scripts/audit_1_1_sd_vs_sem.py` already recomputes Table 4.5's
columns from the per-tap data, so the values are in that code path.

One table: set · tap 1–5 f₁ (Hz) · mean · SD · SD as % of mean. Confirm n = 5 for
every cell and flag any cell where it is not. Add a note that the uncertainty
column in Table 4.5 is the standard error of the difference between the damaged
and baseline five-tap means, so a reader can reproduce it from this table.

## A.5 — Reassembly replicates

The floors of 0.30, 0.46 and 0.32% carry every detection claim in Chapter 4;
Table 4.3 gives only the summary.

Per-rebuild f₁, f₂, f₃ for all five teardown cycles, with the 2σ derivation shown.
Add one sentence that n = 5 makes these operational rather than formal
statistical limits.

## A.6 — Run index

Provenance table of all 42 runs from `four_floor/pi_logs/run_index.csv`: run ID,
timestamp, session, sensor position, damage location, grade, and which table or
figure each run feeds. Generate the last column by tracing which analyses consume
which run IDs — if that cannot be established for some runs, mark them rather
than guessing.

This will be long. Use `longtable` and say so in the README.

---

# Deliverable 2 — data package for email

The submission instructions ask for *"the dissertation (PDF) plus any data
appendices"* by email to the module coordinator.

Build `audit/data_package/` containing:

| Item | Source |
|---|---|
| `run_index.csv` | `four_floor/pi_logs/run_index.csv` (42 runs) |
| `captures/` | the 85 CSVs under `four_floor/pi_logs/**` (~22 MB) |
| `rig.json` | `four_floor/rig.json` |
| `results_decision_rule_sweep.json` | `four_floor/` |
| `results_inversion_branches.json` | `four_floor/` |
| `lambda_sweep/` | `experiments/results_summary*.csv` |
| `README.txt` | see below |

`README.txt` must be one page and map **each file to the table or figure it
produces**. A marker should be able to pick any number in Chapter 4 and find the
file behind it. Include the repository URL, the commit SHA the results were
generated at, and a one-line statement of what was measured versus simulated.

Then zip it and report the size. **If it exceeds 20 MB**, say so and propose the
fallback: deposit on Zenodo or point at the GitHub repo, with the link to go in
the submission email. Do not silently drop files to fit.

Also draft a two-sentence **data availability statement** for the front matter or
the head of the appendix.

---

# Verification

- Re-run all seven existing audit scripts. All must still exit 0.
- Every number in A.2–A.6 appears in `reconciliation.csv` with verdict `NEW` and
  a named source script.
- Cross-check A.4's per-tap values against Table 4.5's printed means and SDs;
  they must reproduce to the printed precision. Any that do not is a finding —
  report it prominently rather than adjusting the appendix to match.
- Confirm every capture referenced in `run_index.csv` exists in the data package,
  and that the package contains no file not listed in `README.txt`.
- Confirm no LaTeX block requires a package likely to be missing, and that no
  label you introduce collides with an existing one (`app:linearity`,
  `tab:pertap`, etc. — prefix them all consistently).

# Ground rules

- Do not edit the dissertation body. The only permitted exception is if the 3.59%
  derivation in A.2 turns out not to support the body's "3.6%", in which case
  report it and stop for a decision.
- Do not edit analysis code to make numbers agree. Report the discrepancy.
- Reuse the audit scripts; do not re-derive what they already compute.
- Commit after each deliverable.
- If something cannot be verified, leave it out and list it in
  `audit/UNVERIFIABLE.md`. An appendix with a gap is fine; an appendix with an
  unverified number undoes the audit.

Begin with A.2, and resolve the 3.59% derivation before writing anything else.

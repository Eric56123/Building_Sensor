# Appendix blocks — insertion guide

Five paste-ready sections. **There is no `.tex` source on this machine**, so each
file is self-contained: paste the whole file into the Overleaf project as a new
`.tex` and `\input` it, or paste the body directly into the appendix.

All five are **appendix material and therefore uncounted**. Nothing here adds a
counted word, and no body edit is proposed.

## Insertion order

Insert after the existing Appendix A.1 (the second- and third-mode shift tables):

| Order | File | Section | Approx. length |
|---|---|---|---|
| 1 | `A2.tex` | Linearity of the first mode in drive amplitude | 3 tables, ~1.5 pp |
| 2 | `A3.tex` | Why no permutation test of the location effect is valid | 3 tables, ~1.5 pp |
| 3 | `A4.tex` | Per-tap first-mode estimates | 1 wide table, ~1 pp |
| 4 | `A5.tex` | Reassembly replicates | 2 tables, ~1 pp |
| 5 | `A6.tex` | Capture inventory | 1 longtable, ~2–3 pp |

`A2.tex` and `A3.tex` are the two that carry argument rather than only data, so
they go first. `A6.tex` is much the longest and goes last.

## Required packages

| Package | Needed by | Notes |
|---|---|---|
| `booktabs` | all five | `\toprule`, `\midrule`, `\bottomrule`. Almost certainly already loaded. |
| `amsmath` | A3, A4, A5 | Display equations. Standard. |
| `longtable` | **A6 only** | Must be added if not present. |

**`siunitx` is not required.** All units are written out, so nothing depends on
`\SI` or `S` columns. If your preamble already loads `siunitx` with table
alignment, the plain `r` columns used here still work.

### Clash risks

- **`longtable`**: load it *before* `ltablex` or `tabu` if either is present.
  With a plain `report`/`book` class there is no conflict.
- **`A4.tex` applies `\small`** to fit nine columns. If your text block is narrow
  the table may still overrun; `\footnotesize` or `\begin{adjustbox}{max width=\textwidth}`
  will fix it. No package is added for this by default.
- **No new commands are defined** in any file, so nothing can collide with an
  existing macro.

## Label prefixes

All labels are prefixed so they cannot collide with existing ones:

| Section | Section label | Table labels |
|---|---|---|
| A.2 | `app:lin` | `tab:lin-percapture`, `tab:lin-groups`, `tab:lin-trace` |
| A.3 | `app:perm` | `tab:perm-spaces`, `tab:perm-effect` |
| A.4 | `app:pertap` | `tab:pertap` |
| A.5 | `app:reassembly` | `tab:reassembly-cycles`, `tab:reassembly-floors` |
| A.6 | `app:inventory` | `tab:inventory` |

Check none of these already exists before pasting:

```
grep -rn "app:lin\|app:perm\|app:pertap\|app:reassembly\|app:inventory" .
grep -rn "tab:lin-\|tab:perm-\|tab:pertap\|tab:reassembly-\|tab:inventory" .
```

## Cross-references these blocks make outward

Each section refers to existing body material. Confirm these targets exist under
these names, or adjust the prose:

- A.2 → Sections 4.1.5, 4.3, Table 4.5
- A.3 → Section 4.4, Section 5 (future work)
- A.4 → Table 4.5, Appendix A.1, Section 5.4
- A.5 → Table 4.3, Chapter 4
- A.6 → Section 3 (the retargeting), Appendix A.2

**A.5 contains an author decision** flagged in a comment at the top of the file.
Read it before submitting: the published floors are twice the *rounded* 1σ values,
and A.5 states that convention explicitly rather than printing a second set of
numbers. The alternative is a body change that moves every derived ratio.

## Regenerating every number

| Section | Script |
|---|---|
| A.2 | `audit/scripts/appendix_A2_linearity.py` |
| A.3 | `audit/scripts/appendix_A3_permutation.py` |
| A.4, A.5 | `audit/scripts/appendix_A4_A5_tables.py` |
| A.6 | `audit/scripts/appendix_A6_inventory.py` |

All four exit 0. Each reuses the Part 1 audit scripts rather than re-deriving.
Every figure appears in `audit/reconciliation.csv` with verdict `NEW` and its
source script named.

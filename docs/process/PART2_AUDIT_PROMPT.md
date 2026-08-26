# Claude Code prompt — Part 2 sweep and consolidated edit list

Paste below the line into Claude Code at the root of `Building_Sensor`.

---

## State

Part 1 is complete and committed (`d81c66b`). `audit/` holds `AUDIT_REPORT.md`,
`EDIT_LIST.md` (13 items), `UNVERIFIABLE.md`, `reconciliation.csv` (55 rows),
`QUESTIONS_FOR_SUPERVISOR.md`, and seven scripts under `audit/scripts/` that all exit 0.
None of the 13 edits has been applied to the dissertation yet.

Two things have changed since Part 1 closed:

1. **The supervisor review is cancelled.** No draft is going to Galasso. Every judgment call
   in `QUESTIONS_FOR_SUPERVISOR.md` now needs a decision recorded in the audit instead, with
   the reasoning stated so it can be defended in the document. Do not leave open questions.
2. **The word count is 11,975 against a hard cap of 12,000.** Twenty-five words of headroom.

## The word budget — hard constraint

A penalty of up to 10% applies outside 10,000–12,000 words. That is worth more than every
statistical finding in this audit combined. It governs everything below.

**Counted:** main text, abstract, section headings.
**Not counted:** title page, contents, figure captions, tables, acknowledgements, references,
in-text citations, appendices.

So an edit to a caption, a table cell, or the appendix is **free**. An edit to body text is
not. Establish the authoritative count with `texcount` on the `.tex` source, and record the
exact invocation in the report so it can be re-run.

Every edit you propose, in Part 2 and in the existing 13, must carry:

```
counted: yes|no      words_removed: N      words_added: N      net: ±N
```

and the consolidated list must carry a running net total that **never exceeds +25**.

### Cut-to-fund protocol

Body-text additions are permitted where they earn marks — the item 1.2 limitation paragraph
above all — but each must be funded by an identified cut of at least equal size. When
proposing a cut:

- **Prefer relocation to deletion.** Appendices are uncounted, and the guidelines explicitly
  list equation derivations and supporting detail as appendix material. Methodology detail
  that duplicates what the code already documents can move rather than disappear.
- **Cut where words do least work per mark.** The four marked sections are Extended
  introduction (20), Data collection/analysis/presentation of results (40), Interpretation
  and discussion (30), Conclusions and future work (10). The guidelines name the common
  failure directly: long reviews and data description crowding out analysis. Literature
  detail beyond what establishes the gap, and restatements of results already given, are the
  first candidates.
- **Never cut** interpretation, critical evaluation, limitations, or anything addressing
  whether findings support the stated objectives. Those are where the 85–100 criteria live.
- Rank every cut candidate by words freed against marks risked, and say which addition it
  funds.

## Part 2 — full sweep, every number

Reconcile **every** numerical claim in the abstract, body, methodology and appendix against a
recomputed value, extending `audit/reconciliation.csv` in the existing schema
(`item, location, claim, documented, recomputed, verdict, note`). Verdicts as before:
`CONFIRMED` · `ROUNDING` · `MISMATCH` · `UNVERIFIABLE` · `STALE` · `DECIDED`.

**Prime directive is unchanged: verify by recomputing, never by re-reading.** Every row cites
the script and data that produced its recomputed value. A number you cannot regenerate is
`UNVERIFIABLE`, not a guess.

Work chapter by chapter and **commit after each**, so partial work survives if the sweep runs
long. Order the chapters by how carefully a marker reads them:

1. **Abstract and Conclusions.** Every figure, and check each against its source in the body.
   Confirm the abstract still describes what you found after items 1.2 and 1.4 changed it.
2. **Table 5.1 and the Discussion.** The heaviest concentration of repeated values, and where
   1.2's deleted p-values and 1.4's 3/6 headline have to land consistently.
3. **Chapter 4**, table by table, including every value quoted in surrounding prose.
4. **Methodology**, including all stated parameters, tolerances and thresholds — check each
   against the code that implements it, in the manner of the Part 1 code audits.
5. **Appendix and front matter.**

Throughout, prioritise these three classes, which produced every serious Part 1 finding:

- **Repeated values.** Build a value-to-locations index. Any number appearing in more than one
  place must be identical everywhere and computed on the same basis. Item 1.7 was a value
  quoted on two different bases; item 1.4 was two correct numbers with wrong labels.
- **Cross-references.** For every `\ref` and every "see Section N", confirm the target
  actually contains the claimed figure. Line 2744 cited §4.4.1 for numbers that section does
  not report, and nothing in the code would have caught it.
- **Premises, not just arithmetic.** The two most consequential Part 1 findings were a false
  premise (base excluded from the comparison) and a superseded figure carried forward (the
  10× amplitude range). When a sentence explains *why* something was done, check the
  explanation against what was actually done.

Also close these carry-overs:

- The three `UNVERIFIABLE.md` entries — the per-run row, the "1.7", the Table 4.16 residual
  column. With no supervisor review, decide each: regenerate from committed code, or remove.
  Removal is the default; state the reason.
- The `F_MEASURED` provenance flag (f₂ = 8.04, f₃ = 12.15 matching neither Day-4 nor Day-6).
- **GEOL0038 duplication.** The guidelines warn that identical text between the proposal and
  this submission may be penalised, and list it under the 0–39% band. If the proposal source
  is available, diff them and report any passage reused verbatim. If it is not available, say
  so and flag it for the author to check manually before submission.

## Deliverable — one consolidated edit list

Replace `audit/EDIT_LIST.md` with a single ordered list merging the existing 13 items and
everything Part 2 finds. This is the only document that will be worked from, so it must be
complete and self-contained. For each edit:

```
ID · item · location (file, line, §/Table/Figure)
counted: yes|no   words: −N/+N   net: ±N   running total: ±N
OLD: <exact text>
NEW: <exact text>
Also change: <every other location that must move with it>
Why: <one line>
```

Order by blast radius, as before — edits that cascade into other tables first. Group the
uncounted edits together at the end so they can be applied without word-budget arithmetic.

Open the file with three tables:

1. **Running word budget** — every counted edit, its net, and the cumulative total.
2. **Cut candidates** — ranked, with words freed, marks risked, and which addition each funds.
3. **Everything unresolved** — `MISMATCH` and `UNVERIFIABLE` rows not covered by an edit.

Then update `audit/AUDIT_REPORT.md` with a Part 2 section, and record every decision that
would have gone to the supervisor, with its reasoning.

## Verification

The audit's own output now needs checking, because nothing downstream will catch an error in
it.

- Re-run all seven Part 1 scripts plus everything new. All must exit 0.
- Confirm the running word total is arithmetically correct and ≤ +25.
- Confirm every `OLD:` string appears exactly once in the source, and that no two edits touch
  overlapping text.
- Spot-check ten `CONFIRMED` rows from Part 1's original 55 by recomputing them a second time
  from a different entry point. If any fails, say so prominently — it would mean the Part 1
  method has a flaw and the whole reconciliation needs re-examining.

## Ground rules

- Do not edit the dissertation source. Produce the list; the author applies it.
- Do not edit analysis code to make numbers agree. Propose the fix with a diff and name every
  downstream number it moves.
- Commit after each chapter.
- Report inconvenient findings early and plainly. A weakened claim that is correctly derived
  is worth more than a strong one an examiner can dismantle.
- If the sweep cannot finish, stop and deliver a complete consolidated edit list for what was
  covered, with an explicit statement of what was not. A partial list that is honest about its
  coverage is usable; a complete-looking list that silently omits a chapter is not.

Begin with `texcount`, then the abstract and conclusions.

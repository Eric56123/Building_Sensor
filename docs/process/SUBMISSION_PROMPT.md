# Claude Code prompt — make the code and data submission-ready

Paste below the line into Claude Code at the root of `Building_Sensor`.

---

## Context

The dissertation (UCL GEOL0056) is finished and about to be submitted. It will
cite this repository and a Zenodo deposit as its data availability statement, so
an examiner may clone the repo, read the code, and try to reproduce Chapter 4.
Right now the repo is a working research directory, not something written to be
read by a stranger.

**Do not change any analysis result.** Every number in the dissertation has been
audited and traced to a source script in `audit/scripts/`. If cleanup would alter
a computed value, stop and report it instead.

## Current state, verified

- 208 MB total: `four_floor/characterisation/` 126 MB, `four_floor/pi_logs/` 22 MB, `.git` 53 MB
- No `README.md`, no `requirements.txt`, no `LICENSE` at root
- `Instructions` at root is a scratch note (a list of half-remembered module invocations), not documentation
- 36 Python files in `four_floor/`, plus `audit/scripts/` (14) and `experiments/`
- `four_floor/monitor.py:131` hardcodes `<user>@<host>:~/Building_Sensor/four_floor/`
- Root carries working scaffolding that should not ship: `STATS_AUDIT_PROMPT.md`,
  `PART2_AUDIT_PROMPT.md`, `APPENDIX_PROMPT.md`, `APPENDIX_PLAN.md`,
  `APPLY_CHECKLIST.md`, `CHANGES.md`, and an untracked dissertation PDF
- `four_floor/pi_logs/` is the superseded four-storey campaign; **no Chapter 4
  number derives from it**. Everything in Chapter 4 comes from `characterisation/`

---

# Deliverable 1 — make the repository readable

## `README.md` at root

Write for someone who has read the dissertation and wants to check a number.
Cover, in this order:

1. What the project is, in three or four sentences: a single-accelerometer
   structural health monitoring pipeline on a three-storey shear frame, comparing
   classical modal identification against a physics-informed network.
2. **A number-to-script map.** For each Chapter 4 table and figure, the script
   that produces it and the data it reads. This is the section an examiner will
   actually use. Derive it from `audit/reconciliation.csv`, which already names a
   source script for every figure.
3. How to run it: Python version, install, the entry points that regenerate the
   results, expected runtime.
4. Directory layout, one line each, including an explicit note that `pi_logs/`
   is the superseded four-storey campaign that nothing in the dissertation uses.
5. Hardware: Raspberry Pi 4, ADXL345 over software I2C, and the fact that the
   acquisition code only runs on the node while the analysis runs anywhere.

Keep it plain. No badges, no emoji, no marketing tone.

## Dependencies

Produce `requirements.txt` pinned to the versions actually used. Derive them by
importing, not by guessing: read what the code imports and record the installed
versions. State the Python version. If any package is needed only for the Pi
acquisition path (`rpi_ws281x`, I2C libraries), put those in a separate
`requirements-node.txt` so the analysis path installs cleanly on a laptop.

## Licence

Add one. MIT or BSD-3-Clause is conventional for research code. If any dependency
or reused source imposes a constraint, say so instead of picking silently.

## Housekeeping

- Delete `Instructions` once the README covers it, or move it to `docs/notes/`.
- Move the six working `*_PROMPT.md` / `*_PLAN.md` / `CHANGES.md` files out of
  root. They are scaffolding from the writing process. Either delete or put them
  under `docs/process/` if you want to keep the record.
- Parameterise `monitor.py:131`: read the target host from an environment
  variable or a config entry, with the current value as a documented default.
  This is a personal identifier in a public repo, not a security hole.
- Check every file for anything else personal: absolute home paths, hostnames,
  student number, email addresses. Report what you find rather than deleting
  unilaterally.

---

# Deliverable 2 — decide what ships

`audit/` currently holds two different kinds of thing, and they should not be
treated the same way.

**The verification layer** belongs in the public repo. `audit/scripts/` (14
scripts, all exit 0) and `audit/reconciliation.csv` (92 rows, every number traced
to a source) are exactly what a reproducibility claim means. Keep them, and point
the README at them.

**The editing narrative** is a different matter. `EDIT_LIST.md`,
`QUESTIONS_FOR_SUPERVISOR.md`, `UNVERIFIABLE.md` and much of `AUDIT_REPORT.md`
describe corrections to drafts that no longer exist. They document the writing
process rather than the research.

**This is the author's call, not yours.** Present both options with the trade-off
and stop for a decision:

- *Keep them public.* They demonstrate systematic self-correction, which is
  defensible and arguably a strength. The risk is that an examiner following the
  DOI reads a list of defects in a document they are marking, without the context
  that all of them were fixed.
- *Keep the verification layer public and move the narrative to `docs/process/`
  excluded from the deposit.* The reproducibility claim is unaffected, since it
  rests on the scripts and the reconciliation table.

Recommend the second, but do not act until the author chooses.

---

# Deliverable 3 — the Zenodo deposit

The raw captures are 126 MB, too large to email, so the deposit is the primary
data route and the repository link is secondary.

Structure it so a reader can navigate without the dissertation open:

```
captures/                 four_floor/characterisation/, 354 files
  MANIFEST.txt            already built in audit/data_package/
derived/                  results JSONs, lambda sweep summaries, rig.json
superseded_four_storey/   pi_logs/, with a one-line note that nothing uses it
scripts/                  the audit scripts, so the deposit is self-contained
README.txt                what each directory is, and the number-to-script map
```

Report the total size and the file count. Draft the Zenodo metadata: title,
authors, description, keywords, licence, and the related-identifier link back to
the GitHub repo. Also draft the two-sentence data availability statement for the
dissertation, with a placeholder for the DOI.

**Decide and state whether the 148 MB of data should remain in git at all.** A
code-only repository with the data in Zenodo is the conventional arrangement and
would cut the clone from 208 MB to a few megabytes. Removing it from history is a
rewrite and is probably not worth it now, but the recommendation should be
recorded either way.

---

# Deliverable 4 — prove it reproduces

This is the part that makes the rest meaningful.

1. Clone the repository into a clean directory.
2. Create a fresh virtual environment and install from `requirements.txt` alone.
3. Run the analysis path end to end from that clone.
4. Confirm the regenerated numbers match `audit/reconciliation.csv`.

Report exactly what failed and why. Missing data paths, undeclared dependencies,
hardcoded absolute paths, and scripts that only run from a particular working
directory are all normal findings here. Fix the packaging problems; **do not fix
them by changing an analysis result.**

If full reproduction needs the 126 MB of captures, say so plainly in the README
and give the Zenodo path as the route to them.

---

# Verification

- `requirements.txt` installs cleanly in an empty environment.
- Every script named in the README runs from a clean clone.
- No absolute path beginning `/Users/` or `/home/` survives in any tracked file.
- `git status` is clean and `.gitignore` still excludes the dissertation PDF.
- The number-to-script map in the README covers every Chapter 4 table and figure,
  with no entry pointing at a script that does not exist.

# Ground rules

- Do not change any analysis result. Packaging only.
- Do not rewrite git history without asking.
- Stop for the `audit/` decision in Deliverable 2 rather than choosing.
- Report personal identifiers rather than removing them silently.
- Commit in logical steps, not one large commit.

Begin with the clean-clone reproduction test in Deliverable 4. What it breaks on
should determine the order of everything else.

# Next Steps — Experiment Log updates + Claude Code prompts

Two parts: **A.** what to fix in `Experiment Log.xlsx`, sheet by sheet.
**B.** copy-paste prompts for the code you'll need.

---

# PART A — Experiment Log (Google Sheets / xlsx)

## Sheet 1. Structure Spec

- [ ] **Write the floor-numbering convention down explicitly.** This is what caused
      the mislabelling — the log said "Floor 3" while every filename said "Floor 4".
      State plainly: which physical level is Ground, how the levels are numbered
      (1–4), and that "Floor N" in filenames uses *this* convention.
- [ ] Fill the empty "Connection types by floor" table (Floor / Connection Type).

## Sheet 2. Sensor Config

- [ ] Fill the empty per-test table: **Test ID | Sensor Placement (Floor) |
      Axis Measuring Primary Shake Direction | Notes**.
- [ ] Update "Mounting method" — currently "Blu-Tack / clip-bracket". Record what
      you actually use (rigid bracket) and drop Blu-Tack.
- [ ] Record **which ADXL345 axis** is aligned with the table's motion, and the
      static check (shake-direction axis ≈ 0 g, vertical ≈ 1 g).

## Sheet 3. Excitation Params  ← highest priority

- [ ] Replace "Frequency: 5 Hz (starting recommendation)" with the **measured f₁**
      and the actual protocol (sweep range, or broadband band).
- [ ] Fill in **Function Generator output (Vpp)** — actual value used.
- [ ] Fill in **Power Amplifier Gain (dB)** — currently blank.
- [ ] Fill in **Power Amplifier Current Limit** — currently blank.
- [ ] Add a dated line: *"Settings locked on <date> — must not change for the
      remainder of the campaign."*
- [ ] Add a note that the earlier campaign ran at **~1 Hz** (far below resonance)
      and is superseded.

## Sheet 4. Damage Variable

- [ ] Fill the empty severity table: **Light / Moderate / Severe** each defined
      precisely (e.g. "N turns loosened on the corner screws of floor X").
      Without this the damage states aren't reproducible.
- [ ] Answer "Reversibility check performed?" and record Y/N per severity.

## Sheet 5. Test Matrix

- [ ] **Reconcile with reality.** The sheet plans 117 runs with sensor positions
      Floor 3 → 2 → 1 and damage floors 1–3. Your data and `test_matrix.py` use
      sensor **Floor 4** and damage floors 1–4 (192 runs). Pick one convention and
      make both match.
- [ ] **Consider scoping down.** 117–192 runs at ~5 min each is a lot of bench time
      for a method that still needs revalidating. A defensible reduced matrix
      (one or two sensor positions, all damage floors × 3 severities × 3 repeats)
      is worth more than a large half-trusted one.
- [ ] Update the "Sensor Location (Floor)" column to the agreed convention.

## Sheet 6. Data Recording

- [ ] **Replace the current contents** — from ~R031 the filenames stop matching the
      damage columns, and rows R118–R192 are placeholders that don't correspond to
      any real data.
- [ ] Paste in the actual `run_index.csv` for completed runs (Prompt 1 below exports
      a sheet-ready CSV).
- [ ] **Add columns:** `Excitation settings used`, `RMS (QA)`, `Notes / anomalies`.
- [ ] Mark the existing 42 runs as **superseded** — 1 Hz drive, inconsistent drive
      amplitude (8–10× between groups). Keep them as methodology evidence; exclude
      them from results.

## Sheet 7. Success Criteria

- [ ] Fill the blank classification thresholds. Current code values:
      **DI < 1.5 = Green**, **1.5 ≤ DI < 4.0 = Amber**, **DI ≥ 4.0 = Red**.
- [ ] Note these were fitted for the full-scale benchmark model and **must be
      revisited after retraining** on the rig-matched simulation.

## New sheet: 8. Session Log

- [ ] Add one: **Date | Gain/Vpp | Measured f₁ | Baseline RMS | Runs completed |
      Anomalies**. One row per lab session. This is what catches drive drift
      between sessions.

---

# PART B — Claude Code prompts

## Prompt 1 — QA checker + pilot acceptance gate

Run this first; you need it before the next lab session.

```
In ~/Building_Sensor/four_floor, write two tools that turn our data-quality checks
into automatic pass/fail gates. Context: last campaign the drive amplitude varied
8-10x between run groups without anyone noticing, and spectral peaks wandered
between windows (noise, not modes) - both went undetected for 42 runs.

1. qa_check.py — per-run quality screen. For a given run's detail + _raw CSVs:
   - RMS of each window; flag if a run's mean RMS deviates >20% from a reference
     baseline run (pass the baseline as an argument).
   - Locate the dominant spectral peak per window; report mean and std across
     windows. Flag "peaks wandering" if std > 0.15 Hz (indicates noise, not modes).
   - Report share of energy below 15 Hz and above 150 Hz.
   - Confirm detail and _raw have equal window counts and the expected 12.
   - Print a clear PASS/FAIL per check plus an overall verdict.

2. pilot_gate.py — go/no-go on a pilot set, before committing to a full matrix.
   Takes 3 baseline runs and 1 damaged run. PASS only if ALL hold:
   a) modal peaks repeat within each run (per-window peak std < 0.15 Hz)
   b) baseline RMS consistent across the 3 repeats (within +/-20%)
   c) the damaged run shows a SHIFT in modal peak frequency vs baseline, not just
      an amplitude change - report both the frequency shift and the amplitude
      ratio separately so they can't be confused
   d) baseline and damaged classify differently
   Print a decision table and exit non-zero on FAIL.

3. export_data_recording.py — read logs/run_index.csv and emit a CSV matching my
   Experiment Log's "6. Data Recording" columns (Run ID, Timestamp, Raw Accel File,
   Alpha, DI, Classification, File Naming Convention, Sensor Location, Damage
   Location, Excitation), ready to paste into the sheet.

Use the existing preprocessing functions rather than reimplementing filtering, so
these stay consistent with training. Do not modify anything under logs/. Include a
short usage example for each at the top of the file.
```

## Prompt 2 — assess what's recoverable from the existing 42 runs

Cheap, and settles the question with evidence rather than assumption.

```
In ~/Building_Sensor/four_floor, assess whether the 42 already-recorded runs under
logs/ are salvageable, now that the training bandpass has been restored in
preprocess().

Background: those runs were collected with (a) software-timed I2C sampling with
unknown jitter, (b) a ~1 Hz drive - far below the frame's first mode, and
(c) drive amplitude that varied 8-10x between run groups (baseline RMS ~0.021 g
vs Floor-1 runs ~0.17-0.20 g).

Write reprocess_assessment.py that, for every run:
  - reprocesses the _raw CSV through the CURRENT corrected preprocess()
  - reports per-window dominant peak frequency and its stability across windows
  - reports RMS, and groups runs to show the amplitude inconsistency explicitly
  - tests whether any consistent modal peak exists per damage condition, and
    whether it shifts between baseline and damaged runs
  - re-runs the model and compares the new classifications against the originals

Then give me a written verdict: are these runs usable for damage detection, usable
only as methodology evidence, or not usable? Be specific about which conclusions
the data can and cannot support. Do not modify anything under logs/ - work on copies.
```

## Prompt 3 — retrain against the real rig (run AFTER f₁ is measured)

Do not run this until the sweep has given you a measured f₁.

```
In ~/Building_Sensor/four_floor, retarget the training pipeline from the full-scale
Johnson ASCE benchmark to my physical rig.

Measured rig properties (fill in from the sweep before running this):
  f1 = ___ Hz, damping ratio ~ ___, higher modes ___
  Frame: 4 storeys, 200 x 200 x 130 mm per floor, corner columns only, no beams,
  screwed connections, base-fixed to a shaking table.
  Excitation actually used: ___ (swept sine / band-limited random, range ___ Hz)

Tasks:
1. In simulation/, identify every parameter encoding the benchmark structure
   (mass ~3.4 t/floor, stiffness ~213 MN/m, f1 = 9.42 Hz, 1% damping, broadband
   excitation) and list them with file/line references before changing anything.
2. Propose a mass/stiffness set that reproduces my measured f1 and mode ordering,
   showing the calculation. Flag any assumption you cannot verify from measurement.
3. Update the excitation model to match what the rig actually experiences.
4. Revisit the preprocessing band: the current 0.5-45 Hz bandpass was chosen for a
   9.42 Hz benchmark. Recommend the correct band for my measured f1 and state
   clearly that changing it requires retraining.
5. Regenerate training data and retrain, saving weights to a NEW versioned file
   (e.g. shm_pinn_weights_rig_v1.pth). Do NOT overwrite shm_pinn_weights.pth.
6. Re-derive the DI classification thresholds for the new model rather than
   inheriting 1.5 / 4.0, and explain the basis.
7. Report expected vs achieved validation performance, and be explicit about what
   is verified versus assumed.

Constraint: single accelerometer. Address whether to train a single-channel
global-DI model instead of the 4-channel model, since broadcasting one sensor's
spectrum to four inputs is not physically identifiable. Recommend one and justify it.
```

---

## Order of operations

1. **Prompt 1** now (tools ready before you're at the bench).
2. **Prompt 2** now — cheap, tells you where you stand on the existing data.
3. Lab session: acquisition check → sweep → **measure f₁** → set excitation → pilot.
4. **Prompt 3** only once f₁ is in hand.
5. Update the sheets as you go — especially Excitation Params, while settings are
   fresh and the knobs are still where you left them.

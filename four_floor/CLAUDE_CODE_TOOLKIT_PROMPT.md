# Claude Code prompt — full toolkit

Paste the block below into Claude Code, run from `~/Building_Sensor/four_floor`
(the Pi for anything touching hardware; the Mac copy is fine for analysis-only tools).

---

```
I'm building the tooling for the next phase of my MSc dissertation: a physics-informed
neural network for structural health monitoring on a scaled shaking-table rig.
Repo: ~/Building_Sensor/four_floor. Read four_floor/ACQUISITION_AUDIT.md and
four_floor/PROJECT_PLAN.md first — they contain the full diagnosis and plan.

## Context
A previous session found the pipeline was producing invalid results. Root causes:
software-timed I2C sampling with jitter, a ~1 Hz drive far below the frame's first
mode (so no modal response was excited), drive amplitude varying 8-10x between run
groups, and a model trained on the full-scale Johnson ASCE benchmark (f1 = 9.42 Hz,
3.4 t/floor) being applied to a 200 mm scaled frame.

## Decisions now locked
- Single ADXL345 accelerometer on the top floor.
- DETECTION + SEVERITY only, no localisation. Per-floor alpha from one sensor is not
  identifiable; the model will be retrained as single-channel -> global damage index.
- Excitation moves from a fixed tone to swept sine across the rig's modal range.
- The 42 existing runs under logs/ are compromised. They are methodology evidence,
  not results. Do not delete them.

## Already built — do NOT rebuild
measure_sampling_rate.py, sensor.py (FIFO acquisition + --selftest),
sweep_analysis.py, rebuild_index.py

## Build these, in this order
Each a standalone CLI script, usage example in the docstring, clear PASS/FAIL output
where relevant. Use the EXISTING preprocessing functions rather than reimplementing
filtering, so nothing drifts from what the model was trained on.

1. freq_shift_detector.py  [HIGHEST PRIORITY]
   Classical modal frequency-shift damage detection - no ML. Given a baseline run and
   a test run, estimate f1 for each (with an uncertainty estimate), report the shift
   in Hz and %, and flag damage against a configurable threshold. Also report damping
   change. This is both my fallback result and the benchmark the PINN must beat, so
   it needs to be defensible on its own: document the method and its assumptions.

2. qa_check.py
   Per-run quality screen. For a run's detail + _raw CSVs:
   - RMS per window; flag if mean RMS deviates >20% from a reference baseline run
   - dominant spectral peak per window; report mean and std across windows; flag
     "peaks wandering" if std > 0.15 Hz (indicates noise rather than modes)
   - share of energy below 15 Hz and above 150 Hz
   - detail and _raw have equal window counts, and the expected count
   Print PASS/FAIL per check plus an overall verdict.

3. pilot_gate.py
   Go/no-go before committing to a full campaign. Takes 3 baseline runs + 1 damaged
   run. PASS only if ALL hold:
   a) modal peaks repeat within each run (per-window peak std < 0.15 Hz)
   b) baseline RMS consistent across the 3 repeats (within +/-20%)
   c) the damaged run shows a SHIFT in modal peak frequency, not just an amplitude
      change - report frequency shift and amplitude ratio separately so they cannot
      be conflated
   d) baseline and damaged classify differently
   Print a decision table; exit non-zero on FAIL.

4. linearity_check.py
   Takes sweeps recorded at 2-3 drive amplitudes and reports whether f1 shifts with
   amplitude. My damage mechanism is loosened screws, which can behave nonlinearly
   (friction, slip, rattle) and would break the linear-modal assumption the method
   relies on. Report f1 per amplitude, the trend, and a clear linear / nonlinear
   verdict with the evidence.

5. capture_sweep.py
   Record a raw acceleration capture during a frequency sweep, at a configurable
   duration, saving in the same _raw CSV format the existing tools read. Should work
   without loading the model (acquisition only).

6. export_data_recording.py
   Read logs/run_index.csv and emit a CSV matching my Experiment Log's
   "6. Data Recording" columns (Run ID, Timestamp, Raw Accel File, Alpha, DI,
   Classification, File Naming Convention, Sensor Location, Damage Location,
   Excitation), ready to paste into the spreadsheet.

7. reprocess_assessment.py
   Assess whether the 42 existing runs are salvageable now the training bandpass is
   restored in preprocess(). For each run: reprocess the _raw CSV, report per-window
   peak frequency and stability, report RMS grouped to show the amplitude
   inconsistency, test whether any consistent modal peak exists per damage condition
   and whether it shifts between baseline and damaged. Then give a written verdict:
   usable for damage detection / usable only as methodology evidence / not usable.
   Work on copies; do not modify anything under logs/.

8. results_analysis.py
   Final campaign analysis: detection accuracy vs severity, sensitivity vs damage
   location (does bottom-storey damage shift f1 more than top-storey?), and a direct
   comparison of freq_shift_detector.py against the PINN so I can state whether the
   PINN earns its place. Produce plots suitable for a dissertation.

## Constraints
- Do NOT modify anything under logs/ - those are experimental records.
- Do NOT overwrite shm_pinn_weights.pth. If something requires retraining, say so
  and stop.
- Any change to fs, nperseg, filter band, or NORM_MIN/NORM_MAX breaks the
  training/inference contract - flag it explicitly rather than making it silently.
- Scripts that need hardware must fail cleanly with a clear message when run on a
  machine without the sensor, so I can develop on my Mac.
- Work incrementally and tell me what you verified empirically versus assumed.
- Keep dependencies to what's already installed (numpy, scipy, torch, smbus2).
```

---

## Notes

- **Item 1 first, deliberately.** The frequency-shift detector is your fallback
  result and the benchmark the PINN must beat. If it can't separate healthy from
  damaged, the PINN won't either — and you'll know the problem is the experiment
  rather than the model.
- Items 1, 2, 6, 7, 8 run fine on your Mac. Items 3, 4, 5 need the rig.
- The retraining prompt is separate — see `NEXT_STEPS_SHEETS_AND_PROMPTS.md`
  Prompt 3, and don't run it until the sweep has given you a measured f₁.

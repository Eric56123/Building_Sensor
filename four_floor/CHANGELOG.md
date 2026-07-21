# Changelog — diagnostic and remediation session

Record of everything changed, and why. Sections A–C alter runtime behaviour;
D–E are new tooling; F is data corrections; H lists what remains unverified.

Useful as methodology-chapter material: the diagnosis and the fixes are legitimate
research content in their own right.

---

## Why any of this happened

Undamaged baseline runs were classifying as CRITICAL. Investigation of the recorded
`_raw` CSVs found four independent problems:

1. **Sampling** — `collect_window()` busy-waited in software while reading the
   ADXL345 one sample at a time over I²C. Timing came from Linux scheduling, not the
   sensor clock, producing jitter and an unknown true rate. ~70% of measured energy
   sat above 150 Hz with peaks at Nyquist — the signature of jitter/aliasing.
2. **Preprocessing contract broken** — the training pipeline applied a 0.5–45 Hz
   bandpass before Welch; live inference did not. The model was trained on one input
   distribution and fed another.
3. **Excitation** — the rig was driven at ~1 Hz, far below the frame's first mode.
   Structural modes were never excited, so damage information was never measured.
   Drive amplitude also varied 8–10× between run groups, confounding damage with
   drive level.
4. **Observability** — `to_model_input()` broadcast one sensor's spectrum into all
   four model channels. Per-floor α is not identifiable from a single sensor; the
   asymmetric outputs (α₁ ≈ 0.4–0.8, α₂₋₄ ≈ 0.99) were an artefact.

---

## A. Data acquisition — `four_floor/sensor.py`  *(behaviour-changing)*

- `collect_window()` rewritten to use the **ADXL345 FIFO in Stream mode**. Samples are
  now clocked by the sensor's own oscillator at its ODR (1600 Hz) and drained in
  blocks, then resampled to exactly 1000 Hz. Sample timing no longer depends on OS
  scheduling.
- Signature and return type unchanged (1-D array in g), so `monitor.py` is unaffected.
- Added FIFO overrun detection and `flush_fifo()`.
- Added `python3 sensor.py --selftest` — verifies throughput matches ODR, zero
  overruns, correct output length.

## B. Feature extraction — `four_floor/live_features.py`  *(behaviour-changing)*

- **Restored the training bandpass at inference.** `preprocess()` previously only
  subtracted the mean; `train.py` and `generate_dataset.py` both call
  `sanitize_accelerometer_data` (linear detrend + 6th-order Butterworth 0.5–45 Hz,
  zero-phase). Inference now calls the *same function*, so the two cannot drift.
- Measured effect on one baseline window: energy below 15 Hz rose **3.8% → 55.7%**.

> **Important:** the α/DI values logged in the existing 42 runs were computed with the
> *broken* preprocessing. Reprocessing those raw signals through the corrected path
> gives different numbers. Any comparison must state which pipeline produced it.

## C. Classification refactor — `four_floor/classification.py` *(new)* + `monitor.py`

- Extracted `compute_di` and `classify` into a shared module. `monitor.py` now imports
  it; the local duplicate was deleted. Runtime behaviour unchanged, and
  `monitor.classify` still resolves.
- Motivation: this project had already been bitten by duplicated logic silently
  diverging (`main.py`'s `preprocess()` vs `sensor_driver.py`'s
  `preprocess_for_pinn()` — see the `live_features.py` docstring).

## D. New diagnostic tools — `four_floor/`

| File | Purpose |
|---|---|
| `measure_sampling_rate.py` | Reports I²C read ceiling, achieved fs, inter-sample interval mean/std/min/max + histogram, and a PASS/FAIL verdict on whether `fs=1000` is valid for `welch()`. |
| `sweep_analysis.py` | Estimates natural frequencies two independent ways (PSD peaks, and envelope-vs-frequency with a ζ estimate) and cross-checks them. Validated on a synthetic 7.0 Hz / ζ=3% sweep → recovered 6.90/7.23 Hz. |
| `rebuild_index.py` | Regenerates `run_index.csv` from the intact per-run detail CSVs. Sensor floor is read from each filename, so it works at any sensor position. |
| `ACQUISITION_AUDIT.md` | Full written audit with verified-vs-assumed tables. |

## E. New analysis toolkit — `shm_toolkit/`

Separate folder; imports `four_floor/` via a path shim so it uses the *same* `config`
and preprocessing functions as the Pi code.

| File | Purpose |
|---|---|
| `toolkit_common.py` | Shared engine: contract constants read from `config`; filename parsing; CSV loaders; `training_psd` (contract-preserving) and `raw_psd` (unfiltered, for noise checks); parabolic sub-bin peak refinement; `estimate_modal_frequency`; `half_power_zeta`; `analyze_ringdown`; RMS/energy helpers; `welch_ttest`; `auc_separation`; band/threshold resolution. |
| `freq_shift_detector.py` | Classical modal frequency-shift detection — no ML. The fallback result *and* the benchmark the PINN must beat. |
| `qa_check.py` | Per-run screen: RMS vs baseline, peak stability, energy distribution, window bookkeeping. |
| `pilot_gate.py` | Go/no-go before a campaign. Reports frequency shift and amplitude ratio **separately** so they can't be conflated. |
| `linearity_check.py` | Compares sweeps at 2–3 drive amplitudes; linear/nonlinear verdict (screwed joints can behave nonlinearly). |
| `ringdown.py` | Free-decay log-decrement damping — more reliable than half-power bandwidth, and ζ feeds the simulation retarget. |
| `capture_sweep.py` | Pi-side sweep capture in the standard `_raw` CSV format. Acquisition only, no model. |
| `rig_config.py` | Stores the measured rig f₁/ζ in `rig.json`; every tool reads it. |
| `export_data_recording.py` | `run_index.csv` → Experiment Log "6. Data Recording" columns. |
| `reprocess_assessment.py` | Assesses whether the existing 42 runs are salvageable. |
| `results_analysis.py` | Campaign analysis: detection vs severity, sensitivity vs damage location, PINN vs frequency-shift AUC comparison, plots. |
| `test_toolkit.py` | 11 synthetic-signal tests, all passing. |

### Key corrections made to the toolkit during review

- **Benchmark frequency assumptions removed.** `DEFAULT_BAND = (0.5, 45)` and the
  "<15 Hz = structural / >150 Hz = noise" thresholds were inherited from the
  full-scale Johnson benchmark (f₁ = 9.42 Hz). On a scaled frame whose f₁ may be much
  higher, peak search masked to that band would have returned a *noise* peak and
  reported it as f₁ with an uncertainty — a silent wrong answer. All tools now take
  `--band`/`--full-band`/`--f1`, print the band in use, and warn on band-edge peaks.
  Thresholds can be expressed relative to f₁ (0.2·f₁–3·f₁).
- **A second silent failure was found during this fix:** the `sanitize` bandpass
  itself would delete a >45 Hz mode *before* any search could reach it. A
  detrend-only exploration path was added. Using `--full-band` on the existing
  baselines exposed the true ~478 Hz aliasing.
- **Significance test corrected twice.** Originally used window-to-window spread —
  but windows share a setup and aren't independent samples. Changed to
  between-repeat spread. Then the z-test was replaced with **Welch's t-test** with
  Welch–Satterthwaite degrees of freedom, since a σ estimated from n=3 has 2 dof and
  t(0.975,2) ≈ 4.30, not 1.96. Confidence intervals now reported. CI coverage
  verified by 3000-trial Monte Carlo (95.2% at nominal 95%).

## F. Data and log corrections  *(not code)*

- **Damage labels shifted up one floor** (Floor 1→2, 2→3, 3→4) across folder names,
  filenames and `run_index.csv` — the recorded location was one below the true one.
- **Run IDs renumbered +9** so they align with the Test Matrix (real Floor 2 → R013–21,
  Floor 3 → R022–30, Floor 4 → R031–39), freeing R004–R012 for true Floor 1.
- **R025 re-run** — its `_raw` file had been truncated to 6 of 12 windows.
- **`run_index.csv` repeatedly null-corrupted on write**; `rebuild_index.py` now
  regenerates it cleanly rather than hand-patching.
- Backup tarballs written to the Pi home directory before each bulk operation.

## G. Planning documents — `four_floor/`

`PROJECT_PLAN.md` (phased plan + risk register) · `LAB_SESSION_CHECKLIST.md`
(bench workflow with three go/no-go gates) · `NEXT_STEPS_SHEETS_AND_PROMPTS.md`
(Experiment Log tasks + prompts) · `CLAUDE_CODE_TOOLKIT_PROMPT.md`

---

## H. Still unverified

Everything below has been written and unit-tested but **never run against hardware**:

- `sensor.py` FIFO acquisition and `--selftest` on the real ADXL345
- `measure_sampling_rate.py` on the rig
- `ringdown --capture` and `capture_sweep.py`
- The PINN comparison paths in `reprocess_assessment.py` and `results_analysis.py`
  (need `shm_pinn_weights.pth`, absent from the Mac)

Run these on the Pi **before** the next lab session, not during it.

## Not changed, deliberately

- `shm_pinn_weights.pth` — untouched. Retraining will write a new versioned file.
- Anything under `logs/` — experimental records.
- `config.py` constants `FS`, `NPERSEG`, `NORM_MIN`, `NORM_MAX` — changing any of
  these breaks the training/inference contract and requires retraining.

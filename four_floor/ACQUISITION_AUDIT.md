# Acquisition & Model-Input Audit

Diagnosis and fixes for the "undamaged baseline classified CRITICAL" problem.
Everything below distinguishes **[VERIFIED]** (measured from the recorded
`pi_logs/*_raw.csv` files or reproduced in code on this machine) from
**[TO VERIFY ON PI]** (needs the real ADXL345) and **[ASSUMED]** (engineering
judgement stated as such).

**Nothing under `logs/` or `pi_logs/` was modified. `shm_pinn_weights.pth` was
not touched.** Where a fix would require retraining, this report says so and
stops.

---

## TL;DR

1. The live signal is **not structural** — it is sampling jitter/aliasing.
   ~72% of a baseline window's energy sits above 150 Hz and peaks near Nyquist
   (478/456/484 Hz); the 5 Hz drive frequency does not appear at all.
   **[VERIFIED]**
2. Two independent defects feed the model garbage:
   - **Software-timed sampling** (`collect_window` busy-wait) → real rate drifts
     below 1000 Hz and jitters → aliasing. Fixed by **hardware-timed FIFO**
     acquisition (`sensor.py`).
   - **The inference pipeline skipped the training bandpass.** Training runs
     every window through `sanitize_accelerometer_data` (0.5–45 Hz) before
     Welch; `live_features.preprocess()` did not. Restored. **[VERIFIED]**
3. Even with clean signals, **per-floor damage localisation from one sensor is
   not identifiable**, and the model proves it: it flags Floor 1 in *every*
   run, including undamaged baselines and Floor-4 damage. **[VERIFIED]**
4. The simulation the model was trained on is the **full-scale Johnson ASCE
   benchmark** (3.4 t/floor, f₁ = 9.42 Hz), not a 200 mm tabletop frame.
   Matching the rig **requires retraining** — flagged, not done.

---

## Task 1 — True sampling rate  →  `measure_sampling_rate.py`

`collect_window` used `time.perf_counter()` busy-waiting with one I2C
`read_i2c_block_data` per sample. That can only ever run **slower** than the
1000 Hz target, and the interval is at the mercy of Linux scheduling + I2C
transaction time.

`measure_sampling_rate.py` (run on the Pi) reports:
- the read-only I2C ceiling (fastest the driver can go),
- achieved fs over full windows,
- inter-sample interval mean / std / min / max + an ASCII histogram (**jitter**,
  not just mean rate),
- a PASS/FAIL verdict on whether `fs=1000` is valid for `welch()`.

**Why the recorded data already proves the rate is wrong [VERIFIED]:** a
constant 5 Hz shaking-table drive leaves **no 5 Hz peak** in any recorded
window, and 72% of the energy is > 150 Hz peaking at Nyquist. Uniform 1000 Hz
sampling of a 5 Hz-driven structure cannot produce that — only sub-rate,
jittered (non-uniform) sampling folding high-frequency content down does.
So `fs=1000` passed to `welch()` is **not valid** for the existing records; the
script quantifies by how much on the bench.

---

## Task 2 — Hardware-timed acquisition  →  `sensor.py`

`collect_window` was rewritten to use the **ADXL345 FIFO in Stream mode**:

- The sensor free-runs at its ODR (1600 Hz, `config.ODR_HZ`) off its **own
  clock** and buffers samples in the 32-deep FIFO. Inter-sample spacing is
  therefore exactly `1/ODR` regardless of when we drain — the whole point.
- We drain whole FIFO blocks (`read_fifo_block`), accumulate a window's worth,
  then **resample 1600 → 1000 Hz** (`resample_poly`, factor 5/8) so the returned
  array is uniformly sampled at exactly `config.FS`.
- **Signature and return type are unchanged** (1-D float array in g, length
  `n_samples`), so `monitor.py` and `live_features` need no edits. Verified the
  resample lands on exactly `n_samples` for ODR ∈ {1600, 800, 400}. **[VERIFIED]**
- **FIFO overrun handling:** `INT_SOURCE` bit 0 is checked each drain; overruns
  are counted and the window flagged as non-time-contiguous. `flush_fifo()`
  clears stale samples at window start.
- **Self-test:** `python3 sensor.py --selftest` confirms raw FIFO throughput
  equals the ODR with zero overruns and that the returned window is the right
  length. **[TO VERIFY ON PI]**

If the Pi cannot drain the FIFO fast enough (`throughput << ODR`, or overruns),
the self-test says so and points at `dtparam=i2c_arm_baudrate=400000` or a lower
`config.ODR_HZ`.

---

## Task 3 — Anti-alias / band-limit

Structural band of interest is 0–15 Hz; ~70% of measured energy is >150 Hz.
The fix is applied at **two** points, both consistent with the training
contract:

**(a) Prevent aliasing at capture (hardware).** Sampling the ADXL345 cleanly at
its 1600 Hz ODR (internal bandwidth 800 Hz) means nothing folds during capture.
The polyphase decimation to 1000 Hz applies its own anti-alias FIR. Structural
0–15 Hz content is far below every Nyquist involved and is preserved exactly.
*This is the real cure; a digital filter cannot undo aliasing that already
happened in the old software-timed path.*

**(b) Band-limit before Welch (digital) — restores a broken contract.** Training
passes every window through `sanitize_accelerometer_data` (linear detrend +
0.5–45 Hz zero-phase Butterworth) **before** Welch
(`train.py:118`, `generate_dataset.py:163`). `live_features.preprocess()` was
only mean-subtracting, so the model was fed 15–500 Hz content its training PSDs
never contained. Restored by calling the **same** `sanitize_accelerometer_data`.

Measured effect on one baseline window **[VERIFIED]**:

| pipeline | energy < 15 Hz | energy > 150 Hz |
|---|---|---|
| before (mean-subtract only) | 3.8% | 73.0% |
| after (training bandpass restored) | 55.7% | 0.0% |

### Retraining flag

- Fixes (a) and (b) are **contract-preserving**: `fs` stays 1000, `nperseg`
  stays 2048, the 1025-bin frequency axis and the `NORM_MIN/MAX` scaler bounds
  are unchanged. **No retraining required** for the acquisition/pipeline fix.
- **However**, restoring the bandpass and cleaning the signal will *change the
  numbers the model outputs* on live data — that is expected and correct (it was
  being fed garbage before). It does **not** by itself make the outputs
  *meaningful*, because of Tasks 4 and 6.
- Any future change to `fs`, `nperseg`, the sanitize band, or `NORM_MIN/MAX`
  **does** break the contract and **requires retraining + refitting the scaler**.
  Do not change those silently.

---

## Task 4 — Single sensor → 4 model channels

`to_model_input()` replicates one sensor's PSD into all four CNN input channels;
the PINN was trained on four **distinct** floor signals (y-DOFs 1,4,7,10, each
with a different mode-shape amplitude).

### Is per-floor localisation identifiable from one sensor? No.

- **Structural-dynamics argument [ASSUMED, standard result]:** a single output
  observes the global poles (natural frequencies) but not the per-storey mode-
  shape amplitudes needed to attribute a stiffness loss to a specific storey.
  Many different damage distributions produce near-identical single-point
  responses — localisation from one sensor is ill-posed.
- **Out-of-distribution input:** feeding four identical channels to a network
  trained on four different ones is a regime it never saw. Its output is then a
  near-constant function of the replicated input.
- **Empirical proof from the recorded runs [VERIFIED]** — per-window
  `alpha_1..4` from the detail CSVs:

  | true condition | α₁ | α₂ | α₃ | α₄ |
  |---|---|---|---|---|
  | undamaged baseline | 0.65 | 0.996 | 0.995 | 0.993 |
  | Floor **1** severe | 0.40 | 0.997 | 0.994 | 0.994 |
  | Floor **4** severe | 0.75 | 0.998 | 0.998 | 0.995 |

  The model flags **Floor 1 in every case**, including the undamaged baseline and
  Floor-4 damage. α₂–α₄ are pinned at ~0.99 always. The only thing that moves α₁
  is overall signal **energy** (baseline RMS 0.021 g → α₁ 0.65; Floor-1-severe
  0.20 g → α₁ 0.40), not damage location. "Localisation" here is an artefact.
- **Compounding cause [VERIFIED]:** `train.py` trains on
  `shm_benchmark_data.npy`, the **discrete** 7-pattern / 6-unique-alpha benchmark
  set, not the continuous `generate_dataset.py` output. With ~6 alpha vectors the
  net memorises a handful of answers — exactly the near-constant behaviour above.

**Why baseline reads CRITICAL:** `classify()` takes `max` DI over channels.
α₁ ≈ 0.4–0.75 → DI₁ = (1−α₁)·10 ≈ 2.5–6.0, which crosses `DI_WARN` (1.5) and
often `DI_CRITICAL` (4.0). So the alarm is driven entirely by the always-low
channel 1, independent of real damage.

### Recommendation

| Option | What you get | Cost | Effect on dissertation claim |
|---|---|---|---|
| **(a) Retrain a single-channel model → one global DI** *(recommended minimum)* | An honest, working detector: global stiffness-loss / frequency-shift severity from one sensor. | Moderate, **no hardware**: change model to 1 input channel (or 1 output), regenerate single-DOF PSDs, retrain, refit `NORM_MIN/MAX`, re-derive DI thresholds. | Claim narrows from *per-floor localisation* to *global damage detection + severity*. Defensible. |
| **(b) Keep 4 channels, deploy 4 real sensors** *(recommended if localisation must stay)* | Genuine per-floor localisation, matching the model's design. | High: 3× more ADXL345 + synchronised multi-channel acquisition. Note the ADXL345 has only 2 I2C addresses (0x53/0x1D) per bus → needs multiple buses or a mux. **Still needs Task-6 retraining.** | Preserves the strong localisation claim — the scientifically strongest path. |
| **(c) Reinterpret current 4 outputs** | Nothing usable. | Trivial. | **Not defensible.** The four alphas from a replicated input are not per-floor estimates; the outputs are near-constant and OOD. Cannot support any damage claim, not even as a global anomaly score. |

**Bottom line:** choose (a) for an honest single-sensor system now, or (b) if the
dissertation must keep per-floor localisation. Both still require Task-6
retraining to the rig. Do **not** ship (c).

---

## Task 5 — Frequency-sweep analysis  →  `sweep_analysis.py`

Feed it a `_raw` CSV recorded during a slow 1–15 Hz sine sweep. It estimates the
rig's natural frequencies two independent ways and cross-checks them:

1. **Welch PSD peaks** over the swept band (response energy piles up at
   resonances).
2. **Envelope vs instantaneous-frequency:** in a linear sweep, time ↔ drive
   frequency; the response envelope peaks as the drive passes each resonance, and
   the −3 dB bandwidth gives a rough damping ratio ζ.

If the two disagree by >15% it prints *low confidence*. It also prints the ratio
of measured f₁ to the simulation's 9.42 Hz so the modelling gap is quantified.

**Validation [VERIFIED]:** on a synthetic 1–15 Hz sweep exciting a known 7.0 Hz /
ζ=3% resonator, the tool returns PSD 6.90 Hz and envelope 7.23 Hz (ζ≈4%) → AGREE.
It also parses the real constant-drive `_raw` files without error (and correctly
finds no clean resonance in them, because they are not sweeps).

**Action:** record an actual 1–15 Hz sweep with the fixed acquisition and run
this to get the rig's real f₁, then compare against Task 6.

---

## Task 6 — Scaling / domain-shift gap

The simulation in `simulation/` is the **Johnson et al. (2004) full-scale ASCE
benchmark**, a 12-DOF (x, y, θ per floor) shear building. Measured from the code
**[VERIFIED]**:

| quantity | simulation value | source |
|---|---|---|
| translational mass / floor | ~3430 kg | `matrices.py` `m_undamaged` |
| total mass | ~32.5 t | `matrices.py` |
| storey lateral stiffness | ~213 MN/m | `matrices.py` `k_undamaged` |
| f₁, f₂, f₃ | 9.42, 11.79, 16.53 Hz | eig(K, M) |
| damping | 1% modal, "masonry" | `damping.py` ζ=0.01 |
| excitation | white noise low-passed **20 Hz**, force 150, 40 s @ 1000 Hz | `excitation.py` |

The rig is a 200×200×130 mm scaled frame, corner columns only, **screwed
joints**, driven by a **single 5 Hz sine**. Its mass is grams, its stiffness
kN/m-scale, its joints add friction damping and nonlinearity, and its excitation
is a single tone. **Every parameter the model keys on is different.**

### What must change to match the rig

1. **Mass matrix M** — remeasure floor masses (weigh each floor assembly);
   recompute the θ (rotational-inertia) terms from the 200×200 plate geometry
   `I = m(a²+b²)/12`. If torsion is neither excited (uniaxial shake) nor measured
   (single Z-axis sensor), **collapse to a 4-DOF shear model** and drop the
   x/θ DOFs entirely — simpler and better conditioned. **[ASSUMED]**
2. **Stiffness matrix K** — recompute per-storey stiffness from the actual
   columns: `k_storey = n_col · αEI/L³` with L = 130 mm, E and I from the real
   column section, and α set by the screwed-joint fixity (between 3, pinned, and
   12, fixed — **measure it** via the sweep, don't assume). This is what sets the
   frequencies. Rebuild the `K_story` decomposition used by the physics loss and
   the α→K map. **[ASSUMED]**
3. **Damping C** — 1% is almost certainly too low for screwed joints. Use the ζ
   the sweep tool estimates (likely a few %, possibly amplitude-dependent). If
   damping is non-proportional, the modal-damping construction in `damping.py`
   needs revisiting. **[ASSUMED]**
4. **Excitation** — the biggest mismatch. Training excites **all** modes with
   broadband noise; the rig excites essentially **one** frequency. A model
   trained on broadband PSD shapes cannot interpret single-tone response. Either
   drive the rig with a sweep / broadband input to match the training
   distribution, or regenerate training data using the rig's actual excitation.
   **[VERIFIED as a contract mismatch; remedy ASSUMED]**
5. **Damage model & DI scaling** — "damage" on the rig (loosened screws / removed
   column) must map to the rig's `K_story`; `DI = (1−α)·10` and the thresholds
   (`DI_WARN=1.5`, `DI_CRITICAL=4.0`) were tuned to benchmark magnitudes and need
   re-derivation. **[VERIFIED thresholds are benchmark-tuned]**

### What retraining involves (flagged — NOT done)

1. Measure rig m, k, joint fixity, ζ, and the real f₁ (Task 5).
2. Rewrite `matrices.py` (M, K, `K_story`) and `damping.py` (ζ) for the rig;
   pick an excitation matching the experiment.
3. Regenerate the dataset with `generate_dataset.py` (already continuous-α — good)
   and **switch `train.py` off the discrete `shm_benchmark_data.npy`** onto it.
4. Refit `PSDScaler` → new `NORM_MIN/MAX` in `config.py`.
5. Retrain → a **new** weights file.

> **Constraint honoured:** this produces a new `shm_pinn_weights.pth` and would
> invalidate the current recorded results, so it is **not** performed here.
> When you do retrain, **version the weights** (e.g. `shm_pinn_weights_rig.pth`)
> and keep the existing `.pth` so `pi_logs/` stays reproducible.

---

## Files changed / added

| file | change |
|---|---|
| `sensor.py` | `collect_window` rewritten to hardware-timed FIFO + resample; FIFO driver methods; `--selftest` |
| `config.py` | FIFO register map + `ODR_HZ` |
| `live_features.py` | restored the training `sanitize_accelerometer_data` bandpass before Welch (contract fix) |
| `measure_sampling_rate.py` | **new** — Task 1 timing/jitter audit (run on Pi) |
| `sweep_analysis.py` | **new** — Task 5 natural-frequency estimator |
| `ACQUISITION_AUDIT.md` | this report |

Not modified: anything under `logs/` or `pi_logs/`, and `shm_pinn_weights.pth`.

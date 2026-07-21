# Dissertation write-up summary

A narrative summary of the diagnostic and remediation work, organised for writing
rather than as a technical changelog (see `CHANGELOG.md` for that).

**Before citing any figure below, reproduce it yourself** — these came from analysis
of the synced `pi_logs` copy during the diagnostic session. They should replicate
exactly, but a dissertation number should be one you generated.

---

## 1. The narrative

A physics-informed neural network (SHM_PINN) was trained on the Johnson ASCE
four-storey benchmark and deployed to a Raspberry Pi with an ADXL345 accelerometer on
a scaled shaking-table frame. Initial deployment produced an anomalous result:
**undamaged baseline runs were classified CRITICAL**.

Rather than tuning thresholds, the anomaly was traced systematically through the
measurement chain. Four independent faults were found — three in acquisition and
experimental design, one in problem formulation. The central finding is that
**the failure lay in the measurement chain and experimental design, not primarily in
the model**.

This matters for the write-up: the diagnosis is a result, not an appendix.

---

## 2. Faults identified (with citable evidence)

### 2.1 Sampling — non-uniform, software-timed acquisition

`collect_window()` busy-waited in software, issuing one I²C read per sample. Sample
timing was therefore governed by Linux scheduling rather than the sensor clock.

Evidence from recorded data:
- **69.8%** of measured energy lay above 150 Hz; only **3.4%** in the 0–15 Hz
  structural band.
- Largest spectral peaks at **498, 233, 216 Hz** — the largest at Nyquist, the
  signature of jitter/aliasing.
- Dominant peaks **wandered by 175–199 Hz (std)** between consecutive 4-second windows
  of the *same* undamaged run. A structural mode is a fixed property of the structure;
  peaks that move between windows are not modes.

### 2.2 Preprocessing contract violation

The training pipeline (`train.py`, `generate_dataset.py`) applied
`sanitize_accelerometer_data` — linear detrend plus a 6th-order zero-phase Butterworth
bandpass, 0.5–45 Hz — before the Welch PSD. Live inference (`preprocess()`) applied
only mean subtraction. The model was therefore trained on one input distribution and
evaluated on another.

- Restoring the filter moved in-band (<15 Hz) energy from **3.8% → 55.7%** on a test
  window.
- Normalisation was not clipping (0% at either bound), but the normalised features
  occupied only ~**[0.27, 0.61]** of the trained [0, 1] range — a magnitude
  distribution mismatch.

### 2.3 Excitation — below resonance, and not held constant

The rig was driven at a fixed ~1 Hz tone, far below any plausible first mode for a
200 mm screwed frame. Below resonance the structure translates quasi-statically with
the table; modes are not excited, so stiffness change produces little measurable
effect.

- Only **0.28%** of energy fell in 4–6 Hz; **1.2–1.4%** in 0.5–2 Hz.
- The 1 Hz drive *was* captured cleanly (baseline peak at **0.98 Hz, std 0.000 Hz**
  across all 12 windows), confirming sensor coupling was adequate — the problem was
  the frequency, not the measurement.

Separately, **drive amplitude was not held constant**, confounding damage with
excitation level:

| Condition | RMS (g) | PSD @1 Hz |
|---|---|---|
| Baseline R001 | 0.0208 | 5.9e-06 |
| Baseline R002 | 0.0210 | 6.4e-06 |
| Floor-1 Light | 0.1667 | 1.7e-04 |
| Floor-1 Severe | 0.2041 | 1.8e-04 |
| Floor-4 Severe | 0.0233 | 9.2e-06 |

Baseline → "Light" jumps 8×, but Light → Severe only 1.2×. A graded damage effect
should not present as a step change between run *groups* with little variation within
the severity progression. The Experiment Log itself specifies that gain and EMF must
be held identical for α/DI comparisons to be valid.

### 2.4 Observability — damage localisation is not identifiable from one sensor

`to_model_input()` replicated a single sensor's spectrum across all four model
channels. The PINN was trained on four *distinct* floor signals.

- The model flagged Floor 1 in **every** run — undamaged baseline, Floor-1 damage and
  Floor-4 damage alike — with α₂–α₄ pinned near 0.99.
- α₁ tracked signal *energy*, not damage location.

This is an identifiability argument, not a tuning problem: four unknowns cannot be
recovered from one measurement. It is the formal justification for the design change
in §4.1.

---

## 3. Remediation

**Acquisition.** `collect_window()` rewritten to use the ADXL345 FIFO in stream mode,
so samples are clocked by the sensor's oscillator and drained in blocks. Signature and
return type preserved.

**Preprocessing.** Inference now calls the same `sanitize_accelerometer_data` used in
training, so the two cannot diverge. Both fixes are contract-preserving — no
retraining required.

**Tooling.** A validation toolkit was built (`shm_toolkit/`): per-run QA screening,
a pilot go/no-go gate, classical frequency-shift detection, excitation-linearity
checking, ringdown damping estimation, and campaign analysis. 11 synthetic-signal
tests, all passing.

**Protocol.** Excitation moves to swept sine spanning the modal range; drive settings
locked and recorded per run; baseline re-run each session; automatic RMS screening
against the session baseline.

---

## 4. Design decisions and their justification

### 4.1 Detection and severity, not localisation

Justified by §2.4. Inferring one global damage index from a spectrum containing
several modes is well-posed; inferring four per-floor stiffness parameters from one
sensor is not. **This narrows the claim but makes it defensible** — worth stating
explicitly rather than presenting as a limitation discovered late.

### 4.2 Statistical treatment

Two successive corrections, both worth reporting:

1. Significance was initially assessed using **within-run, window-to-window** spread.
   Windows in a run share a setup, mounting and damage state, so they are not
   independent samples. Changed to **between-repeat** spread.
2. A z-test was then replaced with **Welch's t-test** with Welch–Satterthwaite degrees
   of freedom, since a standard deviation estimated from n=3 carries 2 dof and
   t(0.975, 2) ≈ **4.30**, not 1.96.

Effect on the Floor-1-Severe comparison: **t = 1.59 against t_crit = 4.30 — not
significant**, with a 95% CI on the frequency shift of **[−3.7, +8.1] Hz**.

That interval is the more useful number. Its width (~12 Hz) *is* the current detection
floor: with this data quality and n=3, shifts smaller than roughly 6 Hz cannot be
resolved. Damage-induced shifts in the literature are typically 1–5% of f₁ — so this
quantifies the precision gap directly.

### 4.3 Retraining scope

Retraining is required, but not because of the fixes above — for three separate
reasons: structural domain shift (benchmark f₁ = 9.42 Hz, 3.4 t/floor vs a 200 mm
frame), the single-channel architecture change, and possibly the preprocessing band if
the measured f₁ exceeds 45 Hz.

---

## 5. Data integrity management

Worth a short subsection — it demonstrates rigour:

- **Damage labels were found to be offset by one floor** and corrected across folder
  names, filenames and the run index (Floor 1→2, 2→3, 3→4).
- **Run IDs renumbered** to align with the Test Matrix, so identifiers and conditions
  correspond.
- One run's raw file was found truncated (6 of 12 windows) by an automated audit and
  re-recorded.
- The run index was found to corrupt intermittently on write; a deterministic rebuild
  from the per-run files replaced hand-patching.

---

## 6. Limitations to state

- Single sensor — detection and severity only; no localisation.
- Scaled model in a different material from the training structure; similitude is
  approximate.
- Screwed-joint damage may behave nonlinearly (friction, slip, rattle), which the
  linear-modal assumption does not capture. To be tested by multi-amplitude sweep.
- ADXL345 noise floor (~300–450 µg/√Hz) is marginal at low response amplitudes, and
  precludes ambient/operational modal analysis on this rig.
- The initial 42 runs are superseded (1 Hz drive, drive-amplitude drift, sampling
  jitter) and are reported as methodology development, not results.
- α/DI values logged in those runs were produced by the *pre-fix* preprocessing;
  reprocessing gives different values. Any figure must state which pipeline produced
  it.

---

## 7. What to claim as contribution

1. **A systematic diagnosis of why a benchmark-trained PINN fails on real scaled
   hardware** — traced through sampling, preprocessing, excitation and identifiability,
   with quantitative evidence at each step. Properly diagnosed negative results are a
   legitimate contribution and this chain is more rigorous than most projects manage.
2. **An identifiability analysis** showing per-floor damage localisation is not
   recoverable from a single sensor, motivating a well-posed reformulation.
3. **A validation toolkit and gating protocol** that would have caught these faults
   within four runs rather than forty-two.
4. **A quantified precision floor** for the measurement chain, with a defensible
   statistical treatment (between-repeat variance, Welch's t, confidence intervals
   verified by Monte Carlo coverage).

---

## 8. Suggested section mapping

| Content | Likely chapter |
|---|---|
| §1 narrative, §2 faults | Results / Experimental validation |
| §3 remediation, §4.2 statistics | Methodology |
| §4.1 identifiability, §4.3 retraining | Discussion |
| §5 data integrity | Methodology (or appendix) |
| §6 limitations | Limitations |
| §7 contribution | Introduction + Conclusion |

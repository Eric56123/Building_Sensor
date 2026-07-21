# Project Plan — Single-Sensor PINN Damage Detection

Consolidates the decisions from the diagnostic session. Phased, with gates.
Read the **Risk Register** before committing bench time — several risks can
invalidate whole phases, and two of them are cheap to check early.

---

## Decisions locked

| Decision | Rationale |
|---|---|
| **Detection + severity, not localisation** | Per-floor α from one sensor is not identifiable. One global index from a multi-mode spectrum is well-posed. |
| **Single sensor, top floor** | Max first-mode amplitude, away from nodes. No phase-referenced roving needed. |
| **Broadband / swept excitation, not fixed tone** | Damage appears as modal peak shifts; a 1 Hz tone excites no modes. |
| **Retrain against the rig, not the benchmark** | Johnson benchmark (f₁ = 9.42 Hz, 3.4 t/floor) is nothing like this frame. |
| **Existing 42 runs = methodology evidence, not results** | 1 Hz drive + 8–10× amplitude drift + sampling jitter. |
| **Conditioning / non-dimensionalisation = stretch goal** | Valuable, but only after a working single-structure result. |

---

## Phase 0 — Acquisition validation (bench, ~1 hr)

No data collection until this passes.

1. `python3 measure_sampling_rate.py` — achieved rate + jitter distribution.
2. `python3 sensor.py --selftest` — FIFO throughput, zero overruns.
3. Rigid bracket mount; confirm the recorded axis is the shake direction
   (static ≈ 0 g, not ≈ 1 g).

**GATE 0:** uniform sampling at a known rate. If it fails, everything downstream
is invalid — spectra, f₁, damage indices, all of it.

---

## Phase 1 — Characterise the rig (bench, ~2 hrs)

The measurement the project has never had.

1. Fixed modest drive amplitude. **Record Vpp and gain.**
2. Slow sine sweep, as wide as the shaker allows.
3. `python3 sweep_analysis.py <sweep_raw.csv>` → f₁, ζ, higher modes.
4. **Repeat the sweep at 2–3 amplitudes.** If f₁ shifts with amplitude, the frame
   is behaving nonlinearly (see Risk 2) — this is important to know now.
5. Compare f₁ against the shaker's usable frequency band.

**GATE 1a:** a clean, repeatable f₁.
**GATE 1b:** f₁ sits inside the shaker's range. If not → **add floor masses**
(artificial mass simulation) to bring f₁ down, then re-measure. This is standard
scaled-model practice and also improves similitude with a real building.

**Record:** f₁ = ______ ζ = ______ higher modes = ______ linear? Y/N

---

## Phase 2 — Establish a simple baseline method (analysis, ~half day)

**Do this before touching the PINN.** Take the frequency-shift method — does f₁
drop measurably when damage is introduced? It is the classical approach, it needs
no training, and it gives you:

- a guaranteed dissertation result even if retraining fails,
- a benchmark the PINN must beat to justify its existence.

If a simple frequency-shift detector already separates healthy from damaged, you
have a result. If it *cannot*, the PINN almost certainly won't either — and that
tells you the problem is the experiment, not the model.

---

## Phase 3 — Retarget the model (desk, ~2–3 days)

Only once f₁ and the excitation are fixed. Use **Prompt 3** from
`NEXT_STEPS_SHEETS_AND_PROMPTS.md`.

1. Update `simulation/` mass, stiffness, damping to reproduce the measured f₁.
2. Match the simulated excitation to what the rig actually receives.
3. Set the preprocessing band around the measured f₁ (the 0.5–45 Hz band was
   chosen for a 9.42 Hz benchmark).
4. Retrain a **single-channel → global damage index** model.
5. Save as a **new versioned** weights file. Never overwrite `shm_pinn_weights.pth`.
6. Re-derive DI thresholds; 1.5 / 4.0 do not carry over.

---

## Phase 4 — Pilot (bench, ~1 hr) — the gate that matters

3 × baseline + 1 × obviously-damaged run. `pilot_gate.py` decides.

**PASS requires all four:**
1. Modal peaks repeat within a run (per-window peak std < 0.15 Hz).
2. Baseline RMS consistent across repeats (±20%).
3. Damaged run shows a **frequency shift**, not just an amplitude change.
4. Baseline and damaged classify differently.

**FAIL → stop and diagnose.** Do not proceed to the matrix. Last session, 42 runs
were collected before anyone discovered the chain was broken.

---

## Phase 5 — Campaign (bench, ~4–6 hrs across sessions)

Reduced matrix — the sensor-position axis is gone, so ~192 runs becomes ~39:

- Baseline × 3
- Damage floors 1–4 × {Light, Moderate, Severe} × 3 repeats = 36

Per run: `pgrep` empty → run → RMS QA vs session baseline → rebuild index → sync.
Per session: re-run baseline first to catch drift.

Keep varying damage **location** even though the model reports globally — it lets
you state that detection holds irrespective of position, and quantify whether
sensitivity varies with damage height. That's a real finding, not a limitation.

---

## Phase 6 — Analysis & write-up

- Frequency-shift baseline vs PINN — does the PINN earn its place?
- Detection accuracy vs severity; sensitivity vs damage location.
- Honest limitations section: single sensor, no localisation, scaled model,
  screwed-joint nonlinearity.
- The 42 compromised runs written up as methodology development — the diagnostic
  work is legitimate content.

**Stretch (only if time):** non-dimensionalise by f₁, train across a swept
parameter range, demonstrate the same model on both the rig and the full-scale
benchmark.

---

# RISK REGISTER

### 1. f₁ above the shaker's range — **HIGH impact, check first**
APS 145 is a long-stroke, low-frequency shaker. A small stiff frame may resonate
above what it can deliver, in which case the modes **cannot be excited at all**.
*Mitigation:* check the shaker spec against measured f₁ in Phase 1. If too high,
ballast the floors to lower f₁. Cheap and standard — but it changes the structure,
so do it **before** any campaign runs.

### 2. Screwed joints are nonlinear — **HIGH impact, under-appreciated**
Your damage mechanism is loosened screws. A loose joint doesn't just reduce
stiffness — it adds friction, slip, rattle, and amplitude-dependent behaviour. The
PINN assumes linear modal behaviour. If f₁ shifts with drive amplitude, that
assumption is broken and modal methods get unreliable.
*Mitigation:* the multi-amplitude sweep in Phase 1 detects this. If strongly
nonlinear, consider a cleaner damage mechanism (removable brace, replaceable
thinner column) that reduces stiffness more linearly.

### 3. Damage isn't reproducible / baseline drifts — **MEDIUM–HIGH**
"N turns loosened" is hard to repeat, and re-tightening may not restore the
original state (thread wear, hysteresis). Over ~39 runs the "undamaged" structure
may not stay constant.
*Mitigation:* torque wrench with recorded values; baseline re-run every session;
a reversibility check (damage → repair → does baseline return?) recorded in the
Damage Variable sheet.

### 4. ADXL345 resolution/noise floor — **MEDIUM**
3.9 mg/LSB against ~20 mg of baseline signal is ~5 quantisation steps, with a
noise floor of roughly 6–9 mg RMS across the band.
*Mitigation:* raise drive amplitude (your 0.17 g runs had fine SNR). If low-level
sensitivity is later needed, ADXL355 or an IEPE accelerometer.

### 5. Simulation still won't match reality — **MEDIUM**
Even matched to f₁, the sim won't capture a bolted frame's real damping (likely
2–5%+ and amplitude-dependent, vs 1% assumed) or its joint behaviour.
*Mitigation:* fit damping from the measured sweep rather than assuming; treat
residual mismatch as a stated limitation.

### 6. Breaking the train/inference contract — **MEDIUM, easy to do by accident**
Any change to `fs`, `nperseg`, the filter band, or `NORM_MIN/MAX` invalidates the
trained weights. This bug already existed once (missing bandpass at inference).
*Mitigation:* single shared preprocessing function; version weights alongside the
config that produced them.

### 7. Time — **MEDIUM–HIGH**
Retraining plus revalidation plus ~39 runs is substantial, and the rig has not yet
produced one usable measurement.
*Mitigation:* Phase 2 exists precisely for this. The frequency-shift result is your
floor — secure it early so a dissertation result exists regardless of how the PINN
work lands.

### 8. Arbitrary waveform capability unknown — **LOW–MEDIUM**
Swept sine is native on the TG1010; random/earthquake playback may not be.
*Mitigation:* plan around swept sine; treat earthquake input as optional.

---

## Minimum viable outcome

If everything else slips, this still constitutes a dissertation:

1. A validated acquisition chain (with the diagnostic work that got it there).
2. Measured modal characterisation of the rig.
3. Damage detection demonstrated by frequency shift.
4. An honest account of why the original PINN pipeline failed on real hardware —
   sampling, excitation, domain shift, observability.

That last item is genuine research contribution. Negative results, properly
diagnosed, are publishable; the diagnostic chain here is more rigorous than most
undergraduate projects manage.

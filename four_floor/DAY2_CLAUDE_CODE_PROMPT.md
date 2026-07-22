# Day 2 session prompt — paste into Claude Code (running on the Pi)

```
Run Day 2 of my shaking-table campaign with me. You execute software steps; I do the
physical ones — prompt me and WAIT for confirmation. Interpret every output against the
stated criteria and STOP at any failed gate.

Read four_floor/PROJECT_PLAN.md for context.

=========================================================================
DAY 1 RESULTS (established — use these, do not re-derive)
=========================================================================
f1 = 2.937 Hz, f2 = 8.080 Hz, f3 = 12.160 Hz  (swept sine + ringdown, agreeing)
zeta1 = 6.84% +/- 0.40%, zeta2 = 0.70% +/- 0.15%
Recorded axis = y  (z was the gravity/vertical axis)
Noise floor 12.54 mg broadband / 4.04 mg in-band (0.5-45 Hz), ~30 dB SNR
Shaker usable to ~12 Hz. f3 sits right at that ceiling.
ADXL345_SCALE has been corrected: amplitudes are ~1.224x Day 1 values for identical
physical motion. Frequencies are unaffected.

STRUCTURE IS 3-DOF, NOT 4. Measured modal ratios 1 : 2.751 : 4.141 fit uniform 3-DOF
shear theory (1 : 2.802 : 4.049, 2.1% mean error) far better than 4-DOF
(1 : 2.879 : 4.411, 5.3%). The ground level is bolted to the table, so it is the base,
not a degree of freedom. Three movable storeys, numbered 1-3, sensor on the top
(Floor 3). Use this numbering throughout — the 'Floor4' labels in old data are wrong.

=========================================================================
STEP 0 — Toolkit check and pre-flight
=========================================================================
FIRST: confirm shm_toolkit/ exists ON THE PI:
    ls ~/Building_Sensor/shm_toolkit/
freq_shift_detector.py, ringdown.py, capture_sweep.py, rig_config.py, qa_check.py and
toolkit_common.py all exist on my Mac (built there on 20 July) but may never have been
pushed to the Pi — that is what blocked several Day 1 steps. If they are missing, tell
me and I will rsync them across. DO NOT rebuild anything that already exists.

Then:
- pinn-sensor.service inactive; no main.py running
- confirm config.RECORDED_AXIS = "y" and the corrected ADXL345_SCALE are present on the Pi
- FIFO overruns are a known unresolved issue (ADXL345 is on bit-banged i2c-gpio bus 3,
  only 1.31x headroom). Use the --max-overruns 0 retry workaround. Do NOT spend Day 2
  trying to fix it; note it and move on.

=========================================================================
STEP 1 — Baseline, undamaged   (RINGDOWN IS THE PRIMARY DETECTOR)
=========================================================================
Rig fully undamaged, all screws torqued.

Ringdown is primary because Day 1 measured its resolution at 0.14% on f1, versus 3.59%
for the sweep method — roughly an order of magnitude better. A loosened screw is
expected to shift f1 by only 1-3%, which sweeps would miss entirely.

- Prompt me for 5 ringdown taps (displace-and-release at the top floor), capturing each.
- For EVERY tap, extract f1, f2 AND f3, plus zeta1 and zeta2 — not just f1. See the note
  on modal localisation at the bottom; the extra modes cost nothing to record.
- Report per-tap values, the mean, and the between-tap standard deviation for each mode.
- Then 3 corroborating sweeps at the Day 1 settings.
- Run qa_check.py on the captures.

GATE: between-tap scatter on f1 should be comparable to Day 1 (~0.14%). If it is much
worse, something has changed in the setup — diagnose before continuing.

=========================================================================
STEP 2 — Introduce severe damage
=========================================================================
Prompt me to apply SEVERE damage at the BOTTOM storey (Floor 1). Rationale: first-mode
inter-storey drift is largest at the bottom, so bottom-storey stiffness loss moves f1
most. If severe damage at the most sensitive location is not detectable, nothing
lighter will be.

Ask me to record EXACTLY what was done (which screws, how many turns) and remind me it
goes in the Experiment Log -> 4. Damage Variable, which is currently blank. The damage
states are not reproducible without it.

=========================================================================
STEP 3 — Damaged measurement
=========================================================================
Identical procedure to Step 1: 5 ringdown taps, all three modes plus damping, then
3 corroborating sweeps. Same amplifier settings — do not touch the gain between Steps 1
and 3. Internal consistency within Day 2 is what the comparison rests on.

=========================================================================
STEP 4 — Analysis: is the shift real?
=========================================================================
Run freq_shift_detector.py with --baseline (5 taps) and --test (5 taps).

Report for f1, and separately for f2 and f3:
- shift in Hz and %
- 95% confidence interval on the shift
- t statistic, Welch-Satterthwaite dof, and t_crit
- which variance was used

ALSO report the change in zeta1. Damping usually INCREASES with damage (loosened joints
add friction), so it is a second, independent indicator — flag if it moves.

And report the amplitude ratio separately from the frequency shift, so the two cannot be
conflated.

=========================================================================
STEP 5 — Reversibility check   (currently blank in my Experiment Log)
=========================================================================
Prompt me to repair the damage (re-torque to the recorded value). Then 5 more ringdown
taps.

Report whether f1 returns to the Step 1 baseline, and within what tolerance.

This is critical and not optional: if f1 does NOT return, then "undamaged" is not a
stable reference across the campaign, every later comparison drifts, and the matrix
design needs rethinking. Say so plainly if that happens.

=========================================================================
STEP 6 — GATE: proceed to the matrix, or stop?
=========================================================================
PROCEED only if ALL hold:
  a) severe damage produced a statistically significant f1 shift
  b) the shift is a frequency change, not merely an amplitude change
  c) damage is reversible — baseline f1 returns within scatter
  d) between-tap scatter is consistent with Day 1

If (a) fails, STOP. Do not run the matrix. Report what the confidence interval says
about the smallest shift the setup could have detected, so we know whether the problem
is sensitivity or the damage mechanism.

=========================================================================
STEP 7 — Record
=========================================================================
- Write a session record: date, all settings, every per-tap measurement with
  uncertainties, gate outcomes, anomalies.
- Update rig.json if baseline modal values have shifted from Day 1.
- Remind me to fill Experiment Log -> 4. Damage Variable (severity definitions,
  reversibility Y/N) and 3. Excitation Params (Vpp, gain dB, current limit).

=========================================================================
WHY ALL THREE MODES — read before Step 1
=========================================================================
The structure is 3-DOF, so it has three storey stiffnesses (k1, k2, k3) and you are
measuring three natural frequencies. That is a formally determined inverse problem:
three observations, three unknowns. Damage at different storeys shifts the three modes
in different proportions.

This may be a route back to damage LOCALISATION from a single sensor, which we had
written off. It is ill-conditioned in practice and I am not claiming it works — but
recording f2 and f3 costs nothing beyond what you are already capturing, and without
them the option is closed. Capture all three for every condition.

=========================================================================
CONSTRAINTS
=========================================================================
- Physical steps are mine. Prompt and WAIT — never assume.
- Do NOT change amplifier gain between Steps 1, 3 and 5.
- Do NOT proceed past a failed gate.
- Do NOT modify anything under logs/, or overwrite shm_pinn_weights.pth.
- Do NOT rebuild tools that already exist — check first.
- Record actual numbers as you go; the session record must be citable.
- State clearly what you verified empirically versus assumed.
```

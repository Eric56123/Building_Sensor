# Day 3 session prompt — paste into Claude Code (running on the Pi)

```
Run Day 3 of my shaking-table campaign with me. You execute software steps; I do the
physical ones — prompt me and WAIT for confirmation. Interpret every output against the
stated criteria and STOP at any failed gate. Do NOT rebuild tools that already exist
(check shm_toolkit/ first).

Read four_floor/PROJECT_PLAN.md and the Day 1 + Day 2 session records for context.

=========================================================================
ESTABLISHED (do not re-derive)
=========================================================================
Structure is 3-DOF. Storeys 1-3, ground bolted to table (base). Sensor on top (Floor 3).
Baseline: f1 = 2.909 Hz, f2 = 8.035 Hz, f3 = 12.152 Hz.
Severe bottom-storey damage: f1 -58.5% (-> 1.206 Hz), f2 -15.9%, f3 -1.9%; monotonic
ordering f1 >> f2 >> f3; fully reversible (102% recovery). p < 1e-13.
Ringdown is the PRIMARY detector (0.14% f1 resolution vs 3.59% sweep). Recorded axis y.
Detector: use freq_shift_detector.py with --match-by-order (discovers each set's own
modes and compares by order — required because shifts are too large for fixed anchors).
Capture f1, f2, f3 + zeta1, zeta2 for EVERY condition.

Two things this session must resolve, in priority order. Severe (83% stiffness loss)
is nearly saturated, so the science lives at the LIGHT end and in reassembly scatter.

=========================================================================
STEP 0 — Pre-flight
=========================================================================
- shm_toolkit/ present on the Pi; service inactive; no main.py; axis=y; corrected scale.
- Amplifier settings identical to Day 2. Do not change gain during the session.
- FIFO overruns: known issue, use --max-overruns 0 retry, do not chase it.

=========================================================================
STEP 1 — Reassembly repeatability   (HIGHEST PRIORITY — sets the detection floor)
=========================================================================
This is the number the whole matrix design rests on. Day 2 showed measurement precision
is ~0.6% on f1 but reassembly repeatability is only ~1-2%, and the LARGER governs the
lightest detectable damage grade. That 1-2% is currently an estimate from a single
repair cycle. Pin it down.

Procedure, all UNDAMAGED:
- Take a 5-tap ringdown baseline.
- Then prompt me to FULLY disassemble and reassemble the rig (re-torque all joints to
  the recorded baseline value), and take another 5-tap ringdown.
- Repeat the teardown/rebuild/measure cycle at least 4 times (5 baselines total).

Report: mean and standard deviation of f1 (and f2, f3) ACROSS the rebuilds. The
between-rebuild sd, as a %, is the empirical detection floor. Any damage grade whose
shift does not clearly exceed it cannot be attributed to damage.

GATE: if between-rebuild scatter on f1 is >~2%, the rig is not repeatable enough for a
graded study — stop and tell me; we rethink the damage mechanism or mounting before
spending bench time on a matrix.

=========================================================================
STEP 2 — Light and moderate damage, bottom storey   (does severity RESOLVE?)
=========================================================================
Severe was 83% stiffness loss and likely saturated, so light/moderate must be defined
LOW and biased toward the intact end. I will apply pre-defined, recorded grades
(e.g. light = 1/4-1/2 turn, moderate = 1-2 turns; severe already have).

For each grade (light, then moderate), bottom storey:
- 5-tap ringdown, all three modes + damping.
- Prompt me for the EXACT physical definition and remind me it goes in Experiment Log
  -> 4. Damage Variable.
- Compare against the Step 1 baseline with freq_shift_detector.py --match-by-order.

Report, per grade: f1 shift %, 95% CI, and CRUCIALLY whether the shift exceeds the
Step 1 reassembly floor. Then assess monotonicity across light -> moderate -> severe:
is the f1 shift graded, or does it saturate?

GATE: at least the moderate grade must produce a shift clearly above the reassembly
floor. If even moderate is within the floor, graded severity is not resolvable with
this setup — report that plainly rather than proceeding as if it is.

=========================================================================
STEP 3 — Localisation falsification test   (severe, other storeys)
=========================================================================
Day 2's monotonic f1>>f2>>f3 ordering is CONSISTENT with bottom-storey damage but is a
single data point, not a proven fingerprint. Test it as a hypothesis to FALSIFY.

Apply SEVERE damage (same definition as Day 2) at:
  - the TOP storey (Floor 3), then
  - the MIDDLE storey (Floor 2).
5-tap ringdown each; extract all three modal shifts.

Report the shift pattern (which modes move most) for bottom (Day 2), middle, top.
Theory: bottom-storey damage moves f1 most; top-storey damage should shift the pattern.
State plainly whether the three locations give DISTINGUISHABLE signatures or not.

Do NOT overclaim. Three locations, one repeat each, is a feasibility probe, not proof.
If signatures are distinct, it motivates a localisation study; if not, we keep the
global-detection claim and say so.

=========================================================================
STEP 4 — GATE: what is Day 4?
=========================================================================
Decide from the results:
  - Step 1 floor <~2% AND Step 2 moderate resolvable -> a graded matrix is viable; size
    it using the measured floor.
  - Step 2 saturates or floor too high -> detection-only study (healthy vs damaged),
    not graded severity. Honest and still a result.
  - Step 3 signatures distinct -> add a localisation arm; otherwise drop it cleanly.
Report which branch we are on and why.

=========================================================================
STEP 5 — Record
=========================================================================
Session record: date, all settings, every per-tap measurement + uncertainty, the
reassembly floor, gate outcomes. Update Experiment Log -> 4. Damage Variable (all three
severity definitions + reversibility) and 3. Excitation Params.

=========================================================================
CONSTRAINTS
=========================================================================
- Physical steps are mine — prompt and WAIT.
- Do NOT change amplifier gain during the session.
- Do NOT proceed past a failed gate.
- Do NOT modify logs/ or overwrite shm_pinn_weights.pth; do not rebuild existing tools.
- Record actual numbers as you go; the session record must be citable.
- State what you verified empirically versus assumed, and do not overclaim localisation.
```
```

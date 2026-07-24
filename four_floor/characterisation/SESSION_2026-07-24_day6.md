# Day 6 session record — graded localisation (Arm A) (2026-07-24)

Extended the Day 4 severe-only localisation to a full GRADED sweep at every
plate: trace (⅛ turn), light (½ turn), moderate (1 turn), against the Day 4
severe (3 turn) point. Sensor kept on the top plate throughout. Goal: find the
DETECTABILITY floor and the LOCALISATION floor, and test whether the Day 4
per-storey fingerprint survives to light damage.

Baseline this session (`day6_baseline`): f0 = **2.921 / 8.108 / 12.192 Hz**.

Arm B (sensor-position sensitivity) was NOT started — deferred to a later session.

---

## Correction applied first: one-floor-lower

Every damage set was initially captured one plate BELOW its label (operator
counted the base as "Floor 1"). Caught mid-session. Folders were **renamed to the
correct physical plate** (raw CSV names kept as provenance) and the rename was
**validated** by moderate→severe continuation against Day 4 (see
`DAMAGE_LOCATION_MAP.md` → "Day 6 correction"). Floor 2 and top were captured
after the fix with the plate confirmed aloud.

---

## RESULT — graded localisation matrix (Δf1 / Δf2 / Δf3, %)

| storey | trace ⅛t | light ½t | moderate 1t | severe 3t (Day 4) |
|---|---|---|---|---|
| **BASE**    | −2 / −1 / −0 | −29 / −11 / −1 | −50 / −14 / −2 | −58 / −17 / −2 |
| **FLOOR 1** | −4 / −2 / −2 | −38 / −3 / −5  | −56 / −8 / −9  | −60 / −8 / −10 |
| **FLOOR 2** | −1 / −2 / −3 | −24 / — / −7   | −38 / −26 / −4 | −39 / −28 / −13 |
| **TOP (F3)**| +0 / −1 / −1 | −7 / −24 / −12 | −14 / −34 / −14| −15 / — / −14 |

(— = mode harmonic-voided by `set_mode_frequencies`: 2nd mode collided with 2×f1.)

### Findings

1. **Each storey has a distinct modal fingerprint, and it holds down to light.**
   - **f1 magnitude orders by height** (lower plate → bigger drop):
     Floor 1 ≈ base ≫ Floor 2 ≫ top. This separates *height bands* but
     **conflates base vs Floor 1** (both ~−50/−56 at moderate) — the Day 4 result.
   - **f2 is the upper-storey tell:** top (−34) > Floor 2 (−26) ≫ base (−14) >
     Floor 1 (−8).
   - **f3 resolves the pair f1 cannot:** Floor 1 (−9) and top (−14) move it;
     base (−2) and Floor 2 (−4) barely.
   - So **no single mode localises, but the (f1,f2,f3) pattern separates all four
     storeys at moderate, and all four still separate at light.**

2. **Detectability floor is below trace.** Even ⅛ turn moves at least one mode
   > 1% at every plate — well above the reassembly floor (2σ = 0.30%). Damage is
   detectable at the lightest grade tried.

3. **Localisation floor is between trace and light.** At trace every shift is
   < 4% and the between-storey *pattern* is not separable; at ½ turn it is. The
   method detects finer than it localises.

4. **Damage is highly nonlinear in screw turns, and the saturation rate differs
   by storey.** Top and Floor 2 nearly saturate f1 by 1 turn (moderate ≈ severe);
   base and Floor 1 keep dropping to 3 turns. Consistent with preload collapse
   between ⅛ and ½ turn seen on Day 3/4.

5. **The graded sweep partially rescued the top-floor 2nd mode.** Day 4's
   severe-only top data lost f2 to the 2×f1 harmonic. The graded sweep captured
   f2 *descending* (8.0 → 6.1 → 5.3 Hz at trace/light/moderate) before it
   collides at severe — a cleaner top-storey f2 signature than Day 4 could get.

---

## QA / caveats (honest)

- **Amplitude was not held constant across storeys.** Hand-tap peak response:
  base/Floor 1 sets ~30–150 mg; Floor 2 and top sets ~800–1500 mg (~10×). The
  modal FREQUENCIES analysed here are amplitude-robust, so localisation stands,
  but (a) damping (zeta) is NOT comparable across storeys this session, and
  (b) a 10× amplitude change is a possible small confounder for light-damage
  joint nonlinearity. Trace vectors look clean, so the effect is likely minor.
  A future graded run should use `ringdown.py --target-amp` to fix this.
- **Floor 2 light f2 harmonic-voided** — f1 had dropped to 2.22 Hz and the 2nd-
  mode pick collided; f1 and f3 are clean and place the storey.
- **Top-floor sensor-mount check passed.** `check_axis` after loosening the top
  plate: recorded axis 'y' = −0.010 g, gravity firmly on z (1.002 g) → the plate
  did not tilt, so top-floor numbers are structure, not a mount artifact.
- FIFO overruns on bus 3 present as usual; harmless for ringdown frequencies.
- Each grade is **one cycle (c1), 5 taps**. No within-session damage replicate
  (c2/c3) this session — a single graded curve per storey. Severe replicates
  (r1–r3) come from Day 4.

---

## Verified vs assumed

**Verified:** the full graded matrix above (measured); the rename is correct
(moderate→severe continuation matches Day 4 on all storeys/modes); the top-plate
did not tilt (check_axis); detection at trace; localisation at light; top-floor
f2 descent before harmonic collision.

**Assumed / not established:** amplitude-independence of the light-grade vectors
(not tested — amplitude varied 10× and was not controlled); that a single c1
curve is representative (no c2/c3 replicate this session); Arm B's frequency-
invariance hypothesis (sensor never moved — untested).

---

## Rig state at session end

**Left DAMAGED at the top plate.** Last set was `F3_moderate_c1`; the top-plate
screws are at the moderate (1-turn-loosened) position, with start marks applied.
**Restore to the marked start positions before the next session.**

---

## Experiment Log rows (paste into `Experiment Log.xlsx`)

**Damage Variable sheet** — one row per set (Location = correct physical plate):

    Date, Location, Grade, Turns, f1_Hz, f2_Hz, f3_Hz, dF1%, dF2%, dF3%, Folder
    2026-07-24, Base,    trace,    0.125, 2.855, 8.005, 12.167, -2.3,  -1.3,  -0.2, base_trace_c1
    2026-07-24, Base,    light,    0.5,   2.081, 7.236, 12.033, -28.8, -10.8, -1.3, base_light_c1
    2026-07-24, Base,    moderate, 1.0,   1.466, 6.952, 11.986, -49.8, -14.3, -1.7, base_moderate_c1
    2026-07-24, Floor 1, trace,    0.125, 2.797, 7.972, 12.007, -4.2,  -1.7,  -1.5, F1_trace_c1
    2026-07-24, Floor 1, light,    0.5,   1.820, 7.842, 11.552, -37.7, -3.3,  -5.3, F1_light_c1
    2026-07-24, Floor 1, moderate, 1.0,   1.297, 7.498, 11.085, -55.6, -7.5,  -9.1, F1_moderate_c1
    2026-07-24, Floor 2, trace,    0.125, 2.893, 7.963, 11.877, -0.9,  -1.8,  -2.6, F2_trace_c1
    2026-07-24, Floor 2, light,    0.5,   2.217, NaN,   11.350, -24.1, NaN,   -6.9, F2_light_c1
    2026-07-24, Floor 2, moderate, 1.0,   1.799, 6.013, 11.702, -38.4, -25.8, -4.0, F2_moderate_c1
    2026-07-24, Floor 3, trace,    0.125, 2.921, 8.010, 12.045, +0.0,  -1.2,  -1.2, F3_trace_c1
    2026-07-24, Floor 3, light,    0.5,   2.718, 6.142, 10.763, -6.9,  -24.2, -11.7, F3_light_c1
    2026-07-24, Floor 3, moderate, 1.0,   2.509, 5.338, 10.530, -14.1, -34.2, -13.6, F3_moderate_c1

(f_Hz columns are the set means from `set_mode_frequencies`; dF% vs baseline
2.921 / 8.108 / 12.192 Hz.)

**Excitation Params sheet:** free-decay ringdown (manual tap on top plate), 5
taps/set, 8×4 s windows @ 1000 Hz, axis y. Amplifier gain UNCHANGED all session.
Amplitude NOT targeted — record peak-response spread per set (see QA caveat).

---

## Next

1. **Arm B** (frequency-invariance): move ADXL345 to Floor 2 then Floor 1,
   re-run `check_axis` each move, re-measure the modal vector — natural
   frequencies should be invariant, only observability/amplitude should change.
2. Optional: repeat a graded storey with `--target-amp` to remove the amplitude
   confounder and get comparable graded DAMPING.
3. Restore top-plate screws to marked start; re-baseline before Arm B.

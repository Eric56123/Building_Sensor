# Day 7 session record — label audit + Arm B start (2026-07-24)

Two parts: (1) a full campaign LABEL AUDIT, locking one canonical damage-location
scheme and reconciling every artefact against it; (2) the START of Arm B
(sensor-position sensitivity), stopped after the first position by choice of time.

---

## Step 0 — restore + baseline (GATE: PASS)

Top-plate damage (Day 6, moderate) restored to start marks. Fresh baseline
`day7_baseline` = **2.921 / 8.097 / 12.187 Hz** — f1 within 0.01% of day6.
The restore was clean, which also confirms **the top-plate damage was fully
reversible** (a genuine campaign result: top storey returns to baseline).

---

## Step 1 — LABEL AUDIT (GATE: PASS)

**Physical ground truth confirmed at the bench by the operator (2026-07-24):**
4 plates — base (Plate 1, bolted to table = boundary condition), Floor 1
(Plate 2, lowest movable), Floor 2 (Plate 3), Floor 3 (Plate 4, top, sensor).
Damage = loosening a plate's screws; label by the plate loosened. Written as the
single source of truth at the top of `DAMAGE_LOCATION_MAP.md`.

**Method (objective, not name-based):** every damaged folder's f1/f2/f3 shift was
recomputed vs its own session baseline and grouped by physical location. A folder
whose *signature class* did not match its claimed location would be flagged.

**Outcome — zero mislabels.** Attribution was already correct everywhere; the two
prior corrections (Day 2/3 base-vs-storey; Day 6 one-floor-lower) both hold under
cross-session continuity:

| location | severe Δf1 across sessions | signature class |
|---|---|---|
| BASE    | D2 −58.6, D3 −57.5, D4 −58/−59/−59 (f2≈−17, f3≈−2) | f1-dominant, consistent 4 sessions |
| FLOOR 1 | D4 −60.5/−60.6/−60.5 (f3≈−10); D6 moderate→severe | f1+f3, internally consistent |
| FLOOR 2 | D3 −34, D4 −39.6×3 (f2≈−27 both) | f2-dominant |
| FLOOR 3 | D3 −8.9, D4 −15.5×3 (small f1 + harmonics) | small f1 + harmonic higher modes |

Two documented **magnitude** caveats (NOT mislabels): Day 3's Floor 2 and top
"severe" were loosened ~5–7% less than Day 4's (single replicate, uncontrolled
tap amplitude). Signature class is unambiguous at each.

**Corrections applied — naming only.** Five Day-3 folders whose names implied the
wrong storey were renamed via `git mv` (data verified byte-identical; raw CSV
names kept inside as provenance):

    S1_severe_r1 -> base_severe_D3_r1     S2_severe -> F2_severe_D3
    S1_light     -> base_light_D3         S3_severe -> F3_severe_D3
    S1_moderate  -> base_moderate_D3

All lingering references reconciled (Day 3 record, map history table,
`ringdown.py` and `matrix_analysis.py` usage examples).

Restore point before renames: **0fe33d6**. Renames: **906bb5a**.

**Naming convention locked for Arm B (sensor-position dimension):**
`sensor<POS>_<loc>_<grade>_r<n>` — POS = which floor the SENSOR is on;
loc = which plate is DAMAGED. Top-sensor captures keep their old names (implicit
sensor = F3).

---

## Step 2 — Arm B: sensor-position sensitivity (STARTED — position 1 of 2–3)

Sensor moved from the top plate to **Floor 2 (Plate 3)**, same orientation.
`check_axis`: recorded axis y = −0.098 g, gravity on z (1.001 g) → mount
orientation preserved, y still the horizontal record axis. **Axis for this
position: y.**

Baseline `sensorF2_baseline` (excitation unchanged — tap the top floor):

| sensor position | f1 | f2 | f3 | f2 observability |
|---|---|---|---|---|
| TOP (`day7_baseline`)     | 2.921 | 8.097 | 12.187 | strong (rang 1/5 taps clean) |
| FLOOR 2 (`sensorF2_baseline`) | 2.931 | 8.093 | 12.158 | **weak — 0/5 taps rang it; only recovered in the averaged spectrum** |

**Findings (baseline, no damage yet):**
1. **Frequencies are position-INVARIANT** — f1/f2/f3 change ≤0.3% between the top
   and Floor 2 sensor. Consistent with the "frequencies are global" hypothesis.
2. **Observability is position-DEPENDENT** — from Floor 2, f2 nearly disappears
   (never dominates a tap decay; only the spectral average finds it at 8.093 Hz),
   while f1 and f3 stay strong. Floor 2 sits near the **node of mode 2**, so a
   sensor there is nearly blind to f2. This is the core Arm B mechanism, already
   visible at baseline.

**Implication for localisation (to be tested with damage next):** if f2 is barely
observable from Floor 2, any discrimination that leans on f2 (e.g. Floor 2 damage,
whose tell is a big f2 drop) will be weak from this position — "which mode you
need dictates where the sensor goes." The base-vs-Floor-1 test (needs f3) should
still work from Floor 2, since f3 remains strong here.

---

## Session ended here (operator choice of time). NOT done:

- Arm B severe subset at the Floor-2 sensor position: base, Floor 1, Floor 3
  × 3 replicates each (`sensorF2_<loc>_severe_r<n>`).
- Arm B position 2: move sensor to Floor 1, `check_axis`, baseline, same subset.
- Step 3 completeness verdict; Experiment Log Arm-B rows.

## Rig state at session end
- Rig **healthy** (restored; baseline good).
- **Sensor is now on FLOOR 2** (Plate 3), axis y. Next session resumes Arm B from
  here (damage subset), or moves it to Floor 1.

---

## Verified vs assumed

**Verified:** restore + reversibility of top damage; canonical scheme confirmed at
the bench; zero mislabels by continuity; renames lossless; frequencies invariant
top↔Floor 2 (≤0.3%); f2 observability collapses at Floor 2.

**Assumed / not established:** that f2's weakness at Floor 2 is specifically the
mode-2 node (physically expected, not yet cross-checked against a mode-shape
measurement); that damage-induced *shifts* are position-invariant (only baseline
frequencies tested so far — the damage subset is the actual test); Arm B position 2
(Floor 1) entirely untested.

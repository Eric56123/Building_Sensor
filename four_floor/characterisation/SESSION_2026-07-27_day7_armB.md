# Day 7 (cont.) — Arm B complete: sensor-position sensitivity (2026-07-27)

Completion of Day 7. The label audit + first Floor-2 baseline were done 2026-07-24
(`SESSION_2026-07-24_day7.md`); this session moved the sensor through **two new
positions** and ran the diagnostic damage subset at each. New tool this session:
`interpret_capture.py` (live per-capture sensor/damage/severity read-out + mislabel guard).

Rig re-baseline before starting: `day7_baseline` = 2.921/8.097/12.187 Hz (top damage
from Day 6 fully reversed).

---

## RESULT — the hypothesis holds

**Frequencies (and their damage-induced shifts) are GLOBAL — invariant to sensor
position. Only OBSERVABILITY changes with position. Localisation therefore
survives placement, provided the discriminating mode is observable where the
sensor sits.**

Two sensor positions added (top-sensor reference from Day 4); diagnostic subset
= severe damage at base, Floor 1, Floor 3, ×3 replicates each.
**Classification: 18/18 correct** at the two new positions (`interpret_capture.py`,
signature match vs each position's own baseline).

### 1. Observability moves with position (fig1_observability.png)

Relative modal amplitude (% of the strongest mode) at each baseline:

| sensor on | f1 (2.9 Hz) | f2 (8.1 Hz) | f3 (12.2 Hz) |
|---|---|---|---|
| **Top (F3)** | 53% | 60% | 100% |
| **Floor 2** | 25% | **5% (blind)** | 100% |
| **Floor 1** | **7% (weak)** | 56% | 100% |

Each position has a **different blind spot**, and it tracks the mode shapes:
f2 is blind at Floor 2 (its modal node), returns at Floor 1; f1 is weakest low
down (the fundamental's amplitude shrinks toward the base). **f3 is strong (100%)
from every position** — an acceleration-weighting effect (a = ω²x favours the
high-frequency mode) that turns out to be decisive below.

### 2. Damage shifts are invariant to sensor position (fig2_shift_invariance.png)

Mean Δf1 / Δf2 / Δf3 (%), severe, 3 replicates, vs each position's own baseline:

| damage | sensor | Δf1 | Δf2 | Δf3 |
|---|---|---|---|---|
| base | Top | −58.7 | −17.1 | −1.7 |
| base | Floor 2 | −60.3 | −17.8 | −1.9 |
| base | Floor 1 | −60.7 | −17.5 | −1.7 |
| Floor 1 | Top | −60.5 | −8.1 | −10.0 |
| Floor 1 | Floor 2 | −61.1 | n/a | −9.4 |
| Floor 1 | Floor 1 | −60.6 | −5.9 | −8.2 |
| Floor 3 | Top | −15.5 | n/a | −14.0 |
| Floor 3 | Floor 2 | −15.3 | n/a | −14.0 |
| Floor 3 | Floor 1 | −14.3 | n/a | −14.2 |

Δf1 and Δf3 agree across positions within ~1–2% (mass-shift of the absolute
baseline is removed by comparing each position to its own baseline). Only f2's
OBSERVABILITY varies — its shift is unmeasurable where the mode is blind.

### 3. base-vs-Floor-1 survives from every position (fig3_baseVsF1_discriminator.png)

The hardest pair: base and Floor 1 both crush f1 to ≈ −60%, so f1 cannot tell them
apart. **f3 does** — base Δf3 ≈ −1.8%, Floor 1 Δf3 ≈ −8 to −10% — and because f3
is strong from all three positions, the discrimination holds everywhere, including
from Floor 2 where f2 is blind. This is the crux: **the mode you need dictates
where the sensor goes.** Had the discriminator been f2, a Floor-2 sensor would
have failed; because it is f3 (strong everywhere here), placement did not matter.

Robustness note: the same-plate case (sensor ON the damaged Floor-1 plate) still
classified ✓ F1, and `check_axis` held (y −0.081 g) across all three cycles —
loosening the sensor's own plate did not tilt the mount.

---

## New tool — interpret_capture.py

Run after each ringdown. (1) From the label: sensor position, damage location,
grade. (2) From the data: shifts vs the position-matched baseline, an independent
signature-match location call, severity, and a ✓/⚠ flag if data and label
disagree. Two bugs were found and fixed live (mode-to-slot alignment by frequency;
guard when <2 modes observable). It caught zero mislabels across 20 captures — the
labels were right, which is the point of running it.

---

## Rig specification (Phase 3 — PARTIAL, no scale on hand)

- Raspberry Pi: **Pi 4 Model B Rev 1.5, 4 GB, Debian 13 (trixie)**.
- Plate masses (written on the labelled photo, `rig_photo_day7.jpg`):
  **Floor 3 = 697.6 g, Floor 2 = 696.7 g** (near-equal → supports the equal-mass
  model assumption). Floor 1 + base plate masses, sensor-node mass, column
  material + cross-section, and frame dimensions **still to be measured** (needs a
  scale + calipers). This is the one open bench task.

---

## Step 3 — is the campaign complete?

**Analytically, yes.** Characterisation ✓, detection ✓, gradability ✓ (to light),
graded localisation ✓, PINN honest head-to-head ✓, **position sensitivity ✓**,
audited canonical labels ✓ (with a labelled photo). The experimental story is
complete and self-consistent.

**One bench task remains, and it is bookkeeping not experiment:** the physical rig
spec (Floor 1/base masses, sensor-node mass, column material + section, frame
dimensions) for §8.7.3. No new dynamics needed — just a scale and calipers. After
that, it's writing.

---

## Verified vs assumed

**Verified:** 18/18 localisation across Floor 2 + Floor 1 sensor positions;
shift-invariance (Δf1/Δf3 within ~1–2% across positions); the observability
pattern (f2 blind at Floor 2, f1 weak at Floor 1, f3 strong everywhere);
base-vs-Floor-1 survives from all positions via f3; same-plate case works;
mount stable under its own plate's damage (check_axis).

**Assumed / not established:** that the f2 blind spot at Floor 2 is specifically
the mode-2 node (physically expected; not cross-checked against a measured mode
shape); equal storey masses (two plates weighed, near-equal — the rest unmeasured);
findings are single-rig feasibility, not general proof.

---

## Rig state at session end

Rig restored to **healthy** (Floor 1 re-tightened). **Sensor is on FLOOR 1**
(axis y) — note this for next session; return it to the top (Floor 3) before any
top-sensor work. day7 close-out baseline not separately captured (Floor-1 baseline
this session is clean and on record).

## Experiment Log rows (paste into Experiment Log.xlsx)

    Date, Sensor_pos, Damage, Grade, Turns, dF1%, dF2%, dF3%, Folder_prefix, n
    2026-07-27, Floor2, base,    severe, 3, -60.3, -17.8, -1.9, sensorF2_base_severe_r,  3
    2026-07-27, Floor2, Floor1,  severe, 3, -61.1, n/a,   -9.4, sensorF2_F1_severe_r,    3
    2026-07-27, Floor2, Floor3,  severe, 3, -15.3, n/a,  -14.0, sensorF2_F3_severe_r,    3
    2026-07-27, Floor1, base,    severe, 3, -60.7, -17.5, -1.7, sensorF1_base_severe_r,  3
    2026-07-27, Floor1, Floor1,  severe, 3, -60.6, -5.9,  -8.2, sensorF1_F1_severe_r,    3
    2026-07-27, Floor1, Floor3,  severe, 3, -14.3, n/a,  -14.2, sensorF1_F3_severe_r,    3
    Excitation: manual top-floor tap, 5 taps/set, 8x4 s @ 1000 Hz, axis y, gain unchanged.
    Baselines: sensorF2_baseline_day7b (2.952/8.117/12.180), sensorF1_baseline (2.930/8.060/12.214).

## Figures (characterisation/figures_day7/)

- `fig1_observability.png` — mode observability heatmap vs sensor position.
- `fig2_shift_invariance.png` — Δf1/Δf3 per damage, grouped by position (invariance).
- `fig3_baseVsF1_discriminator.png` — f3 separates base from Floor 1 at every position.

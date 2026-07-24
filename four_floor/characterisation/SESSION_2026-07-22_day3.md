> **CORRECTION (2026-07-22, later):** the damage locations in this record are
> misattributed. What is called "bottom storey / storey 1" was in fact the
> **BASE PLATE** (a boundary-condition change, not storey stiffness), "middle"
> was **Floor 2**, and "top" was **Floor 3**. **Floor 1 was never tested.**
> The measurements are valid; the attribution is not. See
> `characterisation/DAMAGE_LOCATION_MAP.md` for the authoritative mapping and
> what it changes.

# Day 3 session record — 2026-07-22 (matrix feasibility)

Reassembly floor, severity resolution, and localisation feasibility. Captures in
`characterisation/rebuild[1-5]/`, and the graded/localisation sets — **renamed
Day 7 to canonical labels** (raw CSV names inside keep the original S1/S2/S3
provenance): `base_light_D3/` (was `S1_light`), `base_moderate_D3/` (was
`S1_moderate`), `base_severe_D3_r1/` (was `S1_severe_r1`), `F2_severe_D3/` (was
`S2_severe`), `F3_severe_D3/` (was `S3_severe`); base-severe also reuses Day 2
`day2_damaged/`. See `DAMAGE_LOCATION_MAP.md` (canonical scheme, Day 7).
Ringdown primary; `freq_shift_detector --match-by-order`, `matrix_analysis`.

---

## 1. Outcome — Day 4 branch: GRADED MATRIX + LOCALISATION ARM

| Step | Gate | Result |
|---|---|---|
| 1 | reassembly floor < 2% | **PASS — 0.15%** |
| 2 | moderate resolvable, severity graded | **PASS — monotonic** |
| 3 | location signatures distinct | **YES — motivates localisation** |

All three gates pass. The graded matrix is viable AND the three storeys give
distinguishable signatures, so Day 4 runs a graded matrix with a localisation arm
(with the caveats in §4-§5).

---

## 2. Reassembly repeatability (Step 1) — 5 full teardown/rebuilds

```
f1: 2.960 2.958 2.956 2.964 2.967  -> mean 2.961, sd 0.0046 Hz, FLOOR 0.15%
f2: 8.147 8.144 8.128 8.177 8.161  -> floor 0.23%
f3:12.175 12.187 12.193 12.155 12.206 -> floor 0.16%
```

The f1 reassembly floor is **0.15%** — 13x below the 2% gate. Use **0.30% (2σ)**
as the lightest attributable grade. This already includes residual tap-averaging
noise, so it is the true build-to-build reproducibility of a 5-tap measurement.
Supersedes the Day 2 single-cycle ~1-2% estimate.

Healthy f1 has settled to ~2.96 Hz (morning baseline was 2.909; it crept
2.909 -> 2.939 repaired -> 2.960 rebuilt, then stabilised across rebuilds 1-5).

---

## 3. Severity resolution (Step 2) — bottom storey, graded

Grades: light = 4 screws x 1/2 turn; moderate = 4 x 1 turn; severe = 4 x 3 turns
(severe from Day 2). Clean per-mode shifts vs healthy:

| grade | turns | f1 | f2 | f3 |
|---|---|---|---|---|
| light | 0.5 | −14% | −10% | −1.5% |
| moderate | 1 | −46% | −14% | −1.7% |
| severe | 3 | −59% | −17% | −2.4% |

**Severity resolves — every mode monotonic light -> moderate -> severe**, all
shifts >> the 0.30% floor. Light and moderate are clearly distinguishable.

Two findings:
- **Nonlinear in turns.** Sensitivity peaks around 1/2-1 turn then saturates:
  the first 1/2 turn gives f1 −14%, the next 1/2 turn another −32%, then 2 more
  turns only −13%. Monotonic but not proportional — "turns" is not a linear
  damage axis.
- **f2 is the best single gradable detector**, not f1. f1 has the largest
  contrast but goes NONLINEAR at light/moderate: the loosened joint rattles, so
  f1 becomes weak and amplitude-dependent (moved 2.3-2.9 Hz tap-to-tap at light).
  f2 is monotonic and stable; f3 is stable but low-contrast. Recording all three
  is what makes gradation robust. NB severe damage rings CLEANLY at all
  locations (disconnected joint = new linear config), so severe signatures are
  trustworthy; the nonlinearity is a light/moderate phenomenon.

---

## 4. Localisation feasibility (Step 3) — severe at each storey

Sensor fixed on top floor throughout. Robust indicator — the f1 shift:

| damage location | f1 (Hz) | f1 shift |
|---|---|---|
| bottom | 1.206 ± 0.010 | **−59.4%** |
| middle | 1.949 ± 0.001 | **−34.3%** |
| top | 2.699 ± 0.003 | **−9.1%** |

**f1 shift decreases monotonically as damage moves up** — the higher the damaged
storey, the less f1 moves, because f1's inter-storey drift is largest at the base
and smallest at the top. All three f1 values are clean and stable. This single
number distinguishes the three locations, physically correctly.

Full normalised signatures (largest component = 1):

```
bottom  [-1.00, -0.29, -0.04]   f1 dominates          (modes 1.21, 6.76, 11.9 — clean)
middle  [-1.00, -0.79, -0.55]   f1 largest, others up (modes 1.95, 5.9,  9.9  — clean)
top     [-0.15, -1.00, -0.92]   f1 preserved          (higher modes UNRELIABLE — see below)
```

Pairwise angles: bottom-middle 30°, bottom-top 71°, middle-top 41° — all
distinct (>15°).

**Caveat on the top signature.** Under top-storey damage f1 is preserved (2.70 Hz)
but the higher modes do NOT appear cleanly near 8/12 Hz — the top spectrum is
dominated by f1 with features at 3.16 and 5.33 Hz, and 5.33 ≈ 2 x 2.70 is likely
a harmonic of the very strong fundamental, not a real f3. So the top full vector's
f2/f3 components are not trustworthy; only its f1 component (−9%) is. Bottom and
middle full vectors use cleanly identified modes and are sound.

---

## 5. What is verified vs assumed; do not overclaim

**Verified:** reassembly floor 0.15%; severity resolves monotonically (bottom);
severe damage rings cleanly, light/moderate goes nonlinear; f1 shift ranks damage
height (−59/−34/−9%, bottom/middle/top); the three locations give distinct
spectra.

**Not established / caveats:**
- Localisation is MOTIVATED, not proven — one repeat per location. Needs
  replication (>=3 rebuild+damage cycles per location) before any localisation
  claim.
- Top-damage higher modes need careful identification (harmonics vs real modes)
  before the full 3-mode signature can be trusted there.
- **Tap amplitude was not controlled** and drifted harder on damaged sets (light
  1.28x, moderate 1.47x healthy). This inflated f1 nonlinearity at light/moderate.
  A controlled/instrumented tapper is needed for a clean campaign. Severe results
  are robust to this (clean linear modes); light/moderate f1 is not.

---

## 6. Day 4 design implications

- Graded matrix viable: floor 0.30%, severe ~59% on f1 -> ~200x dynamic range.
- Use turns as an ORDINAL grade, not linear — sensitivity saturates past ~1 turn.
- Report per-mode: f1 for contrast/localisation, f2 for stable gradation, f3 as
  the stable low-sensitivity anchor.
- Control tap amplitude (instrumented tapper) to remove the light/moderate
  nonlinearity confound.
- Localisation arm: >=3 replicates per (storey, severe) before claiming
  localisation; refine top-damage higher-mode identification.
- Fill Experiment Log 4. Damage Variable (light/moderate/severe defs +
  reversibility) and 3. Excitation Params.

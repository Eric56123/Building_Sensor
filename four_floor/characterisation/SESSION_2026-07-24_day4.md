# Day 4 session record — localisation arm COMPLETE (2026-07-22 + 2026-07-24)

Replicated four-location localisation. Part 1 (base + Floor 1) on 2026-07-22;
part 2 (Floor 2, Floor 3, reversibility) on 2026-07-24 against the same baseline.
Captures: `characterisation/{base,F1,F2,F3}_severe_r{1,2,3}/`, `day4_baseline/`,
`day5_baseline/`, `day5_reversibility/`.

---

## 1. Headline result

**All four damage locations produce distinct, replicated modal signatures from a
single top-floor sensor.** 3 independent damage/repair replicates per location.

f1 shift vs baseline (2.941 Hz), dominant-peak extraction, 3 replicates each:

| location | damaged f1 | Δf1 | Δf2 | Δf3 |
|---|---|---|---|---|
| base plate (P1) | 1.215 Hz | **−58.7 ± 0.5%** | −17.1 ± 0.4% | −1.7 ± 0.0% |
| Floor 1 (P2) | 1.161 Hz | **−60.5 ± 0.1%** | −8.1 ± 1.2% | −10.0 ± 0.2% |
| Floor 2 (P3) | 1.778 Hz | **−39.6 ± 0.0%** | −27.6 ± 1.2% | −13.2 ± 0.3% |
| Floor 3 (P4, top) | 2.486 Hz | **−15.5 ± 0.0%** | (harmonic-ambiguous) | |

**All six pairs separable.** Five separate on f1 alone at 36–496σ. Base vs
Floor 1 is only 3σ on f1 (both ~−59%) but **53σ on f3** — so the two lowest
joints are told apart by the higher mode, not the fundamental.

### The main methodological finding

**No single mode localises.** f1 conflates the base with Floor 1; f3 separates
them but barely moves for the other locations. Localisation needs the full
three-mode vector. This is why capturing f1, f2, f3 for every condition was
enforced throughout.

Physical picture: the two lowest joints (base, Floor 1) soften the fundamental
most (~−60%); Floor 2 less (−40%); the top least (−15.5%). Roughly monotonic with
damage height, with base ≈ Floor 1 on f1 and separated on f3.

---

## 2. Replicate reproducibility

Within-location scatter across 3 independent damage/repair cycles is excellent:

    base  f1 sd 0.5%   F1 f1 sd 0.1%   F2 f1 sd 0.0%   F3 f1 sd 0.0%

Base also reproduces across sessions: −58.7% today vs Day 2 −58.5% vs Day 3
−59.4%. Tap strength varied 30–115% within sets with no effect on f1 — severe
damage is amplitude-insensitive (confirmed again).

**Between-SESSION damage variability is larger than within-session:** today's F2
(−39.6%) and F3 (−15.5%) are stronger than Day 3's single repeats (−34%, −9%).
Re-applying "4 screws × 3 turns" does not reproduce to better than a few % of f1
across sessions — which is exactly why replication was required, and why
cross-session absolute shifts should not be over-interpreted. Within-session the
comparison is clean (replicate scatter ≤0.5%).

---

## 3. Baseline stability (reversibility)

f1 (ringdown dominant): 2.944 (Day-4 build) → 2.928 (today start) → 2.922 (today
end, after all 12 damage/repair cycles). **Total drift −0.75% over 2 days;
−0.2% within today.** f2/f3 moved <0.15%. ζ1 ≈ 5% throughout (healthy).

day5_baseline drifted only 0.49% from day4_baseline, so day4_baseline was reused
as the common reference for all four locations — valid, and the f3 discriminator
drifted just 0.03%.

The baseline held across the whole campaign. Every localisation comparison rests
on a stable reference.

---

## 4. Caveats — do not overclaim

- **Feasibility, not a general method.** Four locations, 3 replicates, one lab
  rig, severe damage only. This demonstrates single-sensor localisation is
  possible here; it does not establish it for lighter damage or other structures.
- **F3 (top) higher modes are harmonic-ambiguous.** The strong 5.1 Hz peak sits
  near 2×f1 (4.98), so no clean f2/f3 shift is claimed for the top plate. F3
  separates from all others on f1 alone (≥81σ), so this does not affect the
  result.
- **Base-plate damage is a boundary condition**, not storey stiffness — a
  different class of damage from F1/F2/F3, but included as a distinct location.
- **f2/f3 auto-extraction is unreliable** under large damage shifts. All shifts
  in §1 use dominant-peak / anchored-band extraction by eye, NOT
  `matrix_analysis --localisation` auto-discovery, which mislabels modes on F2
  and F3 (spurious low peaks, harmonics). See §5.

---

## 5. Tooling issues this session

- `--target-amp` was wrongly applied to a severe set (band set from the healthy
  rig, unreachable on the damaged one) — 30 taps rejected. Amplitude control is
  for light/moderate only; set the target from the DAMAGED range.
- `set_mode_frequencies` auto-discovery is fooled by spurious low-frequency peaks
  (F2: 1.16 Hz) and harmonics (F3: 5.1 Hz ≈ 2×f1), and even mislabels the healthy
  baseline intermittently (returned 3.033 for a 2.928 Hz baseline). The ringdown
  dominant-mode value and anchored-band extraction are reliable; the multi-mode
  auto-discovery is not. **Fix before any future automated matrix run.**
- Added this session: `ringdown.py --target-amp` (amplitude band) and the per-set
  tap-strength summary.

---

## 6. Verified vs assumed

**Verified:** four locations give distinct, replicated f1 signatures (36–496σ on
f1, plus f3 for base-vs-F1); no single mode localises; severe damage
amplitude-insensitive; baseline stable to <0.75% across the campaign;
within-session replicate scatter ≤0.5%.

**Not established:** localisation for light/moderate damage (severe only);
whether F3's higher modes are real or harmonic; that these signatures generalise
beyond this rig; clean f2/f3 for the top plate.

---

## 7. Next / Day 5 options

1. **PINN arm.** The classical detector now has a strong, replicated benchmark:
   detection (Day 2), gradability (Day 3, base plate), and four-location
   localisation (Day 4). The PINN must beat, or match with less hand-tuning, the
   f1+f3 localisation shown here.
2. **Gradability at real storeys.** Day 3's light/moderate data is base-plate
   only and was mislabelled. Repeat graded severity at F1/F2/F3 if a graded
   localisation matrix is wanted.
3. **Fix `set_mode_frequencies`** before automating any matrix.
4. **Move the ADXL345 to hardware I2C bus 1** (overruns persist, harmless for
   ringdown but needed for clean PSD magnitudes / the PINN's spectral input).
5. Fill Experiment Log → 4. Damage Variable and 3. Excitation Params.

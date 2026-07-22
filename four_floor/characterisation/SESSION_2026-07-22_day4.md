# Day 4 session record — 2026-07-22 (localisation arm, PART 1 of 2)

**INCOMPLETE — 2 of 4 damage locations done.** Floor 2 and Floor 3 remain.
Resume instructions in §7.

Captures: `characterisation/day4_baseline/`, `base_severe_r{1,2,3}/`,
`F1_severe_r{1,2,3}/`. Analysis: `matrix_analysis.py --localisation`.

---

## 1. What this session established

1. **A replicated localisation result for 2 of 4 locations**, with error bars —
   what Day 3 could only motivate from single repeats.
2. **f1 alone cannot localise.** Base-plate and Floor-1 damage differ by only
   ~2 points on f1 but ~8 points on f3. The discriminating information is in the
   higher modes. This is the session's main finding.
3. **The damage locations in Days 2–3 were mislabelled** (see
   `DAMAGE_LOCATION_MAP.md`) — "bottom storey" was the BASE PLATE.
4. **Base stability is a control variable**, discovered by accident (§5).

---

## 2. Baseline

`day4_baseline` (5 taps, amplitude-controlled 1503–1575 mg, ±2.4%):

    f1 = 2.942 Hz   f2 = 8.123 Hz   f3 = 12.204 Hz
    between-tap scatter on f1 = 0.12%  (Day 3 was 0.15%)

Gate PASSED. Day-3-build vs Day-4-build difference was 0.61% on f1 — the
across-session floor, larger than the within-session 0.15%, and still well under
the 2% gate.

---

## 3. Localisation results (severe = 4 screws x 3 turns, 3 replicates each)

| location | n | Δf1 | Δf2 | Δf3 |
|---|---|---|---|---|
| **base plate** (plate 1) | 3 | −58.7 ± 0.5% | −17.1 ± 0.4% | −1.7 ± 0.0% |
| **Floor 1** (plate 2) | 3 | −60.5 ± 0.1% | −8.1 ± 1.2% | −10.0 ± 0.2% |
| Floor 2 (plate 3) | — | *pending* | | |
| Floor 3 (plate 4) | — | *pending* | | |

**Pairwise separability (replicate sigma):** base vs F1 → f1 3σ, f2 7σ,
**f3 53σ** → DISTINCT.

Replicate reproducibility is excellent: 3 independent damage/repair cycles agree
to 0.5 points on a −58.7% shift (base), 0.1 points on −60.5% (F1). Base also
reproduces Day 2 (−58.5%) and Day 3 (−59.4%) across sessions.

### The key finding: f1 alone is not enough

Base and Floor 1 produce nearly the same f1 shift but completely different higher
modes. A localisation method reading only f1 would call them identical. The
ordering is also NOT simply "monotonic with height" as Day 3 suggested — Floor 1
shifts f1 slightly MORE than the base, plausibly because loosening an
intermediate plate affects the storeys both above and below it, whereas the base
plate affects only storey 1's lower end.

---

## 4. Tooling: a metric that gave a wrong negative

`matrix_analysis --signatures` (Day 3) judged locations by the ANGLE between
normalised modal-shift vectors. That metric is dominated by the largest
component: base and F1 both normalise f1 to −1.00, so their vectors sit **11.5°
apart — below the 15° "distinct" threshold, i.e. reported as OVERLAP** — despite
being 53σ apart on f3.

Replaced by `--localisation`, which tests separability PER MODE in units of
replicate scatter (distinct if ANY mode separates by > 3σ). **Any localisation
conclusion drawn from the angle metric should be re-checked with
`--localisation`.**

Also added this session: `ringdown.py --target-amp` (response-amplitude band with
reject-and-retry) and a per-set tap-strength summary.

---

## 5. Anomaly: base instability fabricates a fundamental

The first `day4_baseline` attempt gave **f1 = 3.279 Hz with ζ = 0.88%** — the
fundamental 11% higher and 5× less damped — while f2 and f3 were unchanged. Cause:
the base was unstable. Re-seating it restored f1 = 2.942 Hz, ζ ≈ 3.8%.

Interpretation: with an unstable base the dominant low-frequency response is a
rigid-body rocking mode on the table's elastic support (lightly damped, since it
does not dissipate in bolted joints), which MASKS the true f1. The higher modes
involve little base motion and are unaffected — exactly what was observed.

**Evidence retained** in `day4_baseline_ATTEMPT1/` as a negative control.
**Check base stability before every capture set** — an unstable base produces a
plausible-looking f1 that would corrupt any f1-based comparison.

---

## 6. Amplitude control: needed for light/moderate, NOT for severe

`--target-amp 1400 ±20%` was applied to a severe-damage set and **all 30 taps were
rejected as TOO HARD** — the minimum achievable on a severely damaged rig was
1849 mg, above the band ceiling. The target was set from the healthy rig without
checking it was reachable on a damaged one. Wasted ~15 min of rig time.

Verified from existing data that this control is unnecessary for severe damage:

| condition | amplitude spread | f1 scatter |
|---|---|---|
| bottom severe | 1570–4560 mg (2.9×) | 0.84% |
| middle severe | 1292–2834 mg (2.2×) | 0.06% |
| top severe | 1290–6548 mg (5.1×) | 0.10% |

Severe damage disconnects the joint and the structure rings as a clean linear
system, so f1 is amplitude-insensitive. Today's replicate agreement (0.1–0.5%)
with tap strength varying 51–125% within sets confirms it empirically.

**Rule: amplitude control for light/moderate grades only.** Set any future target
from the DAMAGED state's achievable range, not the healthy one.

---

## 7. RESUME TOMORROW — exact steps

Rig state at session end: **Floor 1 was the last plate damaged — repair it to
healthy before starting.**

1. **Take a fresh baseline.** Day-to-day drift is ~1.2%, so do NOT reuse
   `day4_baseline`:
   ```
   python3 ringdown.py --capture --repeats 5 --duration 20 --label day5_baseline
   ```
   Confirm between-tap f1 scatter ≈ 0.12–0.15% and f1 near 2.94 Hz. If f1 is far
   off, check base stability first (§5).

2. **Floor 2** (plate 3), 3 replicates, repairing between each:
   ```
   python3 ringdown.py --capture --repeats 5 --duration 20 --label F2_severe_r1
   ... _r2, _r3
   ```

3. **Floor 3** (plate 4, top), 3 replicates: `F3_severe_r1..r3`

4. **Full four-way analysis** (use whichever baseline the sets were taken
   against — if a fresh baseline is used, re-run base/F1 against it too, or note
   the mismatch):
   ```
   python3 matrix_analysis.py --localisation \
     --baseline characterisation/day5_baseline \
     --location base=characterisation/base_severe_r\* \
     --location F1=characterisation/F1_severe_r\* \
     --location F2=characterisation/F2_severe_r\* \
     --location F3=characterisation/F3_severe_r\*
   ```
   NOTE: base and F1 were measured against `day4_baseline`. If tomorrow's
   baseline differs materially, either re-measure base/F1 or report the two
   groups against their own baselines and say so.

5. **Reversibility spot-check** — repair everything, 5 captures, confirm f1
   returns to baseline within scatter.

**Prediction to test (recorded in advance):** Day 3 single repeats put Floor 2 at
f1 −34% and Floor 3 at −9%. If the replicates land near those, localisation is
solid. If F2/F3 also separate mainly on f2/f3 rather than f1, that strengthens
the "all three modes needed" conclusion.

---

## 8. Verified vs assumed

**Verified today:** baseline f1 = 2.942 (0.12% tap scatter); base and F1 severe
signatures with 3 replicates each; base vs F1 separable at 53σ on f3; f1 alone
insufficient to localise; severe damage is amplitude-insensitive; an unstable
base fabricates a spurious fundamental.

**Not established:** Floor 2 and Floor 3 replicated signatures; whether all four
locations are mutually separable; reversibility after today's cycles; anything
about light/moderate grades at locations other than the base plate (Day 3's
gradability data is base-plate only, and mislabelled as "storey 1").

**Still outstanding:** Experiment Log → 4. Damage Variable (grade definitions +
reversibility) and 3. Excitation Params (Vpp, gain dB, current limit).

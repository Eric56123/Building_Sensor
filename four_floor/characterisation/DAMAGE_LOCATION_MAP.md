# CANONICAL DAMAGE-LOCATION SCHEME — single source of truth (locked Day 7, 2026-07-24)

Physical ground truth **CONFIRMED at the bench by the operator on 2026-07-24.**
This is the authoritative labelling for the whole campaign; the dated correction
notes further below are the history of how we got here, kept for provenance.

## The rig: 4 plates, 3 storeys (3 DOF), 1 sensor

```
Plate 4  FLOOR 3   TOP — ADXL345 sensor mounted here   [aliases: top, S3, storey 3]
                   ── screws  (storey-3 stiffness)
Plate 3  FLOOR 2   middle movable floor                [aliases: middle, S2, storey 2]
                   ── screws  (storey-2 stiffness)
Plate 2  FLOOR 1   LOWEST movable floor                [alias: storey 1; NOT tested Days 2-3]
                   ── screws  (storey-1 stiffness)
Plate 1  BASE      bolted to the shaking table         [aliases: bottom, S1, "storey 1" MISLABEL]
                   ── screws = BOUNDARY CONDITION (not a storey stiffness)
```

- **Damage = loosening one plate's screws. Label every capture by the PLATE loosened.**
- **BASE is a different damage class** (boundary compliance, not storey stiffness);
  report it separately from the three storeys — pooling it flatters localisation.
- The sensor lives on FLOOR 3 unless a capture name says otherwise (Day 7 Arm B moves it).

## Canonical labels & deprecated aliases

| canonical | plate | same physical thing, other names used in the campaign |
|---|---|---|
| `base`         | 1 | bottom, S1, "storey 1" (Days 2–3 mislabel) |
| `F1` (Floor 1) | 2 | storey 1 (correct sense); **never damaged before Day 4** |
| `F2` (Floor 2) | 3 | middle, S2, storey 2 |
| `F3` (Floor 3) | 4 | top, S3, storey 3 |

## New naming convention — Day 7 Arm B adds a SENSOR-POSITION dimension

    sensor<POS>_<loc>_<grade>_r<n>          e.g.  sensorF1_base_severe_r2
      POS   = F1 | F2 | F3   which floor the SENSOR is on (F3 = default/top)
      loc   = base | F1 | F2 | F3   which plate is DAMAGED
      grade = trace | light | moderate | severe ;  r<n> = replicate
Existing top-sensor captures keep their names (implicit sensor = F3).

## Full campaign reconciliation (audited Day 7 by physical continuity, not just by name)

Method: every damaged folder's f1/f2/f3 shift was recomputed vs its own session
baseline and grouped by physical location. A folder whose *signature class* did
not match its claimed location would be flagged — none were. See
`SESSION_2026-07-24_day7.md` for the numbers.

| Session | Folder(s) | Label as written | Physical | Canonical | Status |
|---|---|---|---|---|---|
| D1 07-21 | `ringdown*`,`sweep*`,`noise*` | healthy characterisation | — | baseline | ✓ char only |
| D2 07-22 | `day2_baseline/damaged/repaired` | "storey 1 (bottom)" | BASE | base | ✓ signature f1 −58.6%; name neutral, kept |
| D3 07-22 | `rebuild1..5` | reassembly cycles | — | baseline | ✓ |
| D3 07-22 | `S1_light/moderate`, `S1_severe_r1` | "bottom / storey 1" | BASE | base | ⚠→✓ misleading name, **renamed `base_*_D3`** |
| D3 07-22 | `S2_severe` | "middle / storey 2" | Floor 2 | F2 | ⚠→✓ **renamed `F2_severe_D3`** |
| D3 07-22 | `S3_severe` | "top / storey 3" | Floor 3 | F3 | ⚠→✓ **renamed `F3_severe_D3`** |
| D4 07-22/24 | `{base,F1,F2,F3}_severe_r1..3` | base/F1/F2/F3 | as named | same | ✓ MATCH |
| D5 07-24 | `day5_baseline`,`day5_reversibility` | PINN / reversibility | — | — | ✓ n/a |
| D6 07-24 | `{base,F1,F2,F3}_{trace,light,moderate}_c1` | base/F1/F2/F3 | as named (post one-floor fix) | same | ✓ MATCH, continuity-validated |
| D7 07-24 | `day7_baseline` | baseline | — | baseline | ✓ f1 2.921 |

**Outcome: zero unresolved MISLABEL rows.** Attribution was already correct
everywhere (the two prior corrections hold up under continuity); Day 7's only
change is renaming the five `S1/S2/S3` folders whose *names* implied the wrong
storey. Raw CSV filenames inside keep their capture-time names as provenance.

---

# Damage location map — CORRECTION, 2026-07-22

The rig has **FOUR plates with screws** but only **THREE storeys** (3 DOF).
Days 2–3 labelled damage by "storey" and got the attribution wrong. The raw
captures are valid; only the naming and interpretation were incorrect. Folder
names are left unchanged so commit history and session records still resolve —
**this file is the authoritative mapping.**

## Geometry

```
Plate 4  Floor 3 (TOP, sensor mounted here)  ── screws
                                              │  storey 3
Plate 3  Floor 2                             ── screws
                                              │  storey 2
Plate 2  Floor 1                             ── screws
                                              │  storey 1
Plate 1  BASE PLATE (bolted to the table)    ── screws
```

Four screw sets; three storeys between plates. 3 DOF is confirmed both by the
storey count and by the spectrum: a search to 60 Hz finds no 4th mode near the
15.9 Hz a 4-DOF frame would predict.

## Corrected mapping of existing captures

| Capture folder | Labelled as | ACTUALLY was | f1 shift |
|---|---|---|---|
| `day2_damaged` | "storey 1 / bottom" | **Plate 1 — BASE PLATE** | −59% |
| `S1_severe` (Day 3) | "bottom storey" | **Plate 1 — BASE PLATE** | −59% |
| `S2_severe` (Day 3) | "middle storey" | **Plate 3 — Floor 2** | −34% |
| `S3_severe` (Day 3) | "top storey" | **Plate 4 — Floor 3 (top)** | −9% |
| — | — | **Plate 2 — Floor 1: NEVER TESTED** | — |

## Why this matters

**Base-plate damage is a boundary-condition change, not a storey stiffness
loss.** Loosening the base screws alters how the structure is held to the table
rather than softening a storey's columns. So Day 2's headline result and Day 3's
"bottom" localisation point are a different class of damage from the other two.

This also unifies two findings that looked separate: the −59% f1 shift from
"bottom damage" and the spurious 3.279 Hz mode seen on 2026-07-22 when the base
was unstable are **both base-condition effects**. f1 is strongly sensitive to how
the rig is held down — a real and reportable result, but not storey localisation.

Consequences for the Day 2/3 records:
- Day 2 "severe storey-1 damage, reversible, −58.5%" -> read as BASE PLATE.
- Day 2's physical explanation ("first-mode drift is largest at the bottom
  storey") does not apply; the mechanism is base compliance.
- Day 3's localisation trend (−59 / −34 / −9%, monotonic with height) stands as
  measured, but spans base + 2 storeys, not 3 comparable storeys, and has a gap
  at Floor 1.

## Day 4 corrected design

All four plates, 3 replicates each, against the Day 4 baseline
(f1 = 2.942, f2 = 8.123, f3 = 12.204 Hz):

    base_severe_r1..r3    Plate 1 (base)     — boundary condition
    F1_severe_r1..r3      Plate 2 (Floor 1)  — fills the gap
    F2_severe_r1..r3      Plate 3 (Floor 2)
    F3_severe_r1..r3      Plate 4 (Floor 3)

The base case is analysed and reported SEPARATELY from the three storey cases:
pooling a boundary-condition change with storey damage would flatter the
localisation claim.

## Day 6 correction — one-floor-lower (2026-07-24)

Day 6 added GRADED damage (trace ⅛t / light ½t / moderate 1t) at each location.
During capture, **every damage set was applied one plate LOWER than the folder
label written at the time** (the operator counted the base plate as "Floor 1").
As on Days 2–3 the raw captures are valid; only the on-the-fly naming was wrong.

**Unlike Days 2–3, the Day 6 folders were RENAMED to the correct physical plate**
(the raw CSV filenames inside keep their capture-time names as provenance). The
authoritative Day 6 mapping is therefore the folder name itself:

| Captured under (wrong) | RENAMED to (correct) | Physical plate |
|---|---|---|
| `F1_{trace,light,moderate}_c1`, `F1_light_r1` | `base_{...}_c1`, `base_light_r1` | Plate 1 — BASE |
| `F2_{trace,light,moderate}_c1` | `F1_{...}_c1` | Plate 2 — Floor 1 |
| `F2_{trace,light,moderate}_c1` (2nd capture round) | *(kept)* `F2_{...}_c1` | Plate 3 — Floor 2 |
| `F3_{trace,light,moderate}_c1` | *(kept)* `F3_{...}_c1` | Plate 4 — Floor 3 (top) |

Floor 2 and Floor 3/top were captured AFTER the error was caught, with the plate
confirmed aloud before each set, so their labels were correct as written.

**Validation the rename is correct (not just assumed):** for every renamed
storey, today's *moderate* modal vector flows smoothly into the Day 4 *severe*
vector of the SAME plate, on all three modes:
- BASE:    moderate −50/−14/−2  →  Day 4 severe −58/−17/−2
- FLOOR 1: moderate −56/−8/−9   →  Day 4 severe −60/−8/−10
- FLOOR 2: moderate −38/−26/−4  →  Day 4 severe −39/−28/−13
- TOP:     moderate −14/−34/−14 →  Day 4 severe −15/ (f2 harmonic-void) /−14

Had the labels been off by one, these continuations would not line up. See
`SESSION_2026-07-24_day6.md` for the full graded matrix and analysis.

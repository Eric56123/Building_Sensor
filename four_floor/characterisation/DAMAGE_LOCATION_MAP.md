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

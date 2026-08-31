# Figure set — working notes

Not part of the submission. These are the open items, audit findings and revision
history behind the Chapter 4 figure set; the submission-ready captions live in
`FIGURE_CAPTIONS.md`.

Section numbering below is as written during the audit and still uses the old
Chapter 9 labels. The figure-number mapping to Chapter 4 is in `FIGURE_CAPTIONS.md`.

---

## Revision history — what changed and why


The chapter this set belongs to is now **Chapter 4** (results) with the
discussion in **Chapter 5**. Sections 3-5 of this document still carry the old
9.x numbering except where a heading says otherwise; the mapping for the figures
touched in this revision is given here, and the rest is a straight relabel of
9.n -> 4.n.

| Chapter 4 | file | change |
|---|---|---|
| 4.2 | `fig02_detection` | panel (b) title 50-200x -> **52-202x**, now computed from the data |
| 4.6 | `fig05_signature_space` | title names the **two-mode projection**; caption 27 -> **26.6** floor-units |
| **4.10** | `fig09_seed_sweep_calls` | **REBUILT** — was `fig09_pinn_alpha` |
| **4.11** | `fig10_inversion_branches` | **REBUILT** — was `fig10_inversion` |
| **4.6.6** | `fig12_plate_hypotheses` | **NEW** |

**4.10 was rebuilt because both its title and one of its five data points were
wrong.** "The argmin is k1 in every case" is false: the network calls k1 at the
base plate and Floor 1, k3 at Floor 3, and k2 essentially never. The old Floor 3
point came from an input whose two unmeasurable frequency ratios were imputed as
1.0 — `SESSION_2026-07-24_day5.md:81` records it as "Floor 3 (2 modes
unmeasurable)". Setting those two ratios to 1.0 reproduces the archived
(0.72, 0.94, 0.98) to (0.72, 0.94, 0.985) over eight retrains, argmin k1 in 8/8.
That input is by construction the signature of storey-1 damage, so the k1 call
was forced by the imputation. Fed the measurable Floor 3 data instead, the model
calls k3 in 100% of 40 runs.

**4.11 lost its residual panel.** The "7e-2, does not fit" bar at Floor 1 encoded
a stalled optimisation, not the absence of a solution: the default start
converges to a point where the Jacobian is rank-deficient (singular values
[0.5, 0.437, 0.0], confirmed analytically). Multi-start enumeration finds exact
branches wherever three modes resolve, all at 1e-13 Hz or better, so the panel
would now be four equal bars.

**4.6.6's "inside the measurement scatter" reading does not survive checking.**
Propagating Table 4.3's per-mode 1-sigma (0.15 / 0.23 / 0.16 %) through the plate
fit, 400 draws per case, the ranked-first hypothesis **never changes** — not even
at Floor 3, whose winner-to-runner-up gap has a 95% interval of
[0.012, 0.043] Hz, strictly positive, with 0 of 400 rank flips. The margins
differ by a factor of thirty (0.794 Hz at the base plate against 0.027 Hz at
Floor 3), but all four rankings are resolved by the data. The figure therefore
shows each gap with its interval instead of a "tie" band, and the title claims
only that the base plate is decided *by a clear margin* — not that the others
are undetermined.

The two figures now read from JSON written by the analysis scripts
(`results_decision_rule_sweep.json`, `results_inversion_branches.json`), so a
figure rebuild does not re-run a six-minute sweep. Regenerate those with
`python -m four_floor.decision_rule_sweep` and
`python -m four_floor.inversion_robustness`.

---

---

## 1. The path conflict, resolved

**`characterisation/figures_day7/` does not exist and never did.** The Arm B session
record (`SESSION_2026-07-27_day7_armB.md`, final section) cites
`figures_day7/fig1..3`; those files were written to `characterisation/figures/` as
`fig06..08` when the set was unified (commit `84e40dd`, "one figures/ dir"). The
session record's citation is stale.

**Canonical location is `characterisation/figures/`.** Cross-reference that path only.
I have not edited the session record — it is a lab notebook and the correction belongs
in a note rather than a rewrite of the entry. Suggested one-line addendum:

> Figures were subsequently moved to `characterisation/figures/` (fig06–08); the
> `figures_day7/` paths above are superseded.


---

## 4. Things to fix in the chapter text

### 4.1 Floor 3's two missing modes have two different causes — settled

This was the blocking conflict: Figure 9.6 marked a Floor 3 run as having Δf₃
unresolved from the 2f₁ harmonic, while Table 9.9 said the unresolved mode at Floor 3
was f₂ with three resolved f₃ replicates at −14.0. Per-replicate extraction:

| F3 severe | f₁ | f₂ | f₃ |
|---|---|---|---|
| r1 | 2.486 | **void** — 5.097 Hz, 2.050 × f₁ | **not detected** |
| r2 | 2.488 | **void** — 5.103 Hz, 2.051 × f₁ | 10.498 → −13.97% |
| r3 | 2.486 | **void** — 5.092 Hz, 2.048 × f₁ | 10.481 → −14.11% |

**Both documents were partly right, and both need a correction.**

1. **Table 9.9 is right that f₂ is the harmonic-void mode**, in all three replicates.
   2f₁ = 4.97 Hz and the observed peak is 5.09–5.10, inside the 3% tolerance.
2. **Figure 9.6 is right that one run has no Δf₃ — but it was wrong about why.** In r1,
   f₃ *was* found, at 10.47 and 10.48 Hz, in **2 of 5 taps**. The rule requires 3 of 5,
   so the slot was dropped. Its frequency agrees with r2 and r3 to 0.2%. This is a
   vote-threshold dropout, not a harmonic collision — f₃ at 10.5 Hz is nowhere near
   2f₁ (4.97) or 3f₁ (7.46).
3. **So the harmonic hits one mode at Floor 3, not two.** Your inference followed from
   the figure's mis-attribution rather than from the data.
4. **Table 9.9's Floor 3 f₃ row is n = 2, not n = 3.** The count and the sd need
   correcting.
5. **The mean does not need recomputing.** The pipeline uses `nanmean`, so r1 was
   already excluded: −14.0 *is* the two-replicate mean (−14.04). Only n and sd change.

**One decision for you.** r1's f₃ is recoverable — it is present at 10.475 Hz, just
below the 3-of-5 vote. Relaxing the threshold for that cell would restore n = 3 and
give a mean of −14.08, still −14.1. I have **not** done this: changing an extraction
rule to rescue a single cell is post-hoc and would have to be applied campaign-wide to
be defensible. Reporting n = 2 is the conservative call. Say if you would rather
recover it, and I will apply the relaxed rule everywhere and report what else moves.

### 4.2 Table 9.15 and the repo's inversion solver disagree at Floor 1

The figure carries Table 9.15's values, as instructed. But
`rig_3dof.solve_healthy_stiffness()` on the measured means does not reproduce them:

| | Table 9.15 | residual | repo solver | residual |
|---|---|---|---|---|
| base | 0.113 / 1.146 / 0.872 | 3e−10 | 0.113 / 1.146 / 0.872 | 2.4e−15 |
| **Floor 1** | **0.107 / 0.895 / 1.124** | **6.7e−2** | **0.158 / 0.844 / 1.041** | **6.8e−1** |
| Floor 2 | 0.271 / 0.913 / 0.581 | 9e−10 | 0.271 / 0.913 / 0.581 | 1.8e−15 |
| Floor 3 | 0.695 / 0.731 / 0.774 | 3e−8 | refuses — no two-mode path | — |

- **They agree exactly at base and Floor 2**, and the residual difference there
  (1e−10 vs 1e−15) is just an iterative solver against a closed-form one.
- **They disagree only at Floor 1 — the case that has no solution.** That is
  self-consistent rather than alarming: when the measured modes are inconsistent with
  every admissible stiffness state, two different least-squares implementations land
  on different points. The table's residual (6.7e−2) is the better fit of the two.
- **The repo has no two-mode path**, which is why it refuses Floor 3 while the table
  reports a two-mode fit.

**This means the code and the chapter have diverged, and the figure is currently
transcribed rather than computed.** Worth closing before submission: either the
table's solver should be brought into the repo, or `solve_healthy_stiffness` should
gain a two-mode branch and a proper nonlinear fit. I have left the discrepancy printed
in the script's stdout so it cannot be forgotten.

### 4.3 Base plate / moderate: −49.8 against Table 9.5's −48.94 — RESOLVED, table was right

Not a baseline and not a dropped tap. **The figure's −49.8 was an extraction artefact
and Table 9.5's −48.94 is correct.** The figure now reads −48.9.

`set_mode_frequencies` picks `f1 = median(dom)` over the taps, then **re-extracts** each
tap's value inside `f1 × (1 ± rel_bw)`, `rel_bw = 0.20`. If a tap's true fundamental
falls outside that window, the re-extraction silently substitutes whatever shoulder is
inside it. That is what happened here, on one tap:

| base_moderate_c1 | tap 1 | tap 2 | tap 3 | tap 4 | tap 5 | mean | Δf₁ |
|---|---|---|---|---|---|---|---|
| true peak (unwindowed) | 1.3345 | 1.4459 | 1.3149 | 1.5966 | **1.7665** | 1.4917 | **−48.94** |
| windowed re-extraction | 1.3345 | 1.4459 | 1.3149 | 1.5966 | **1.6358** | 1.4655 | −49.84 |

- `median(dom)` = 1.4459, so the per-tap window is **[1.1567, 1.7351]**. Tap 5's
  fundamental is at **1.7665 — outside it.** The band maximum inside the window is the
  1.600 Hz bin, which parabolic refinement puts at 1.6349 ≈ the 1.6358 recorded.
- Tap 5's fundamental is genuinely a split, near-flat peak: PSD at 1.5 / 1.6 / 1.7 / 1.8
  Hz is 4.66 / 5.49 / 5.34 / 5.52 (×10⁻⁴). The true maximum at 1.800 is only 0.6% above
  the local maximum at 1.600, so the shoulder was a plausible-looking substitute.
- **Audited across every folder in the campaign: this is the only clipped tap anywhere.**
  Nothing else moved — severe replicates, baselines and the other eleven graded cells are
  bit-identical.
- **The cell that breaks the window is the least repeatable one in the campaign.** Its
  per-tap f₁ spans 1.31–1.77 Hz, a ±15% spread about its own median, which is the only
  place in the campaign that approaches the ±20% window. So the joint slip you cite this
  cell for is the same thing that defeated the extraction — the instability caused the
  artefact.

**What changed.** `make_figures_ch9.py` gains `f1_per_tap()` (the toolkit's own Step-1
rule — most prominent peak in the f₁ band, per tap, unwindowed) and
`f1_window_clipped()`, which reproduces the window and reports how many taps fall
outside it. Any cell with a clipped tap has its Δf₁ recomputed unwindowed, and the
script prints the correction and asserts its footprint:

```
f1 WINDOW CORRECTION  Base plate moderate: 1 tap(s) outside median(dom)±20%
                      -> Δf1 -49.84 => -48.94  (Table 9.5 basis)
```

The assertion fails the build if the set of affected cells ever changes, so this cannot
silently spread. Figure 9.4 now uses the same `f1_per_tap` definition, so the two
figures can no longer disagree about a cell mean — they previously did, since Figure 9.4
was already unwindowed.

**One thing worth knowing for the toolkit, not just this figure.** `rel_bw = 0.20` is a
latent trap for any future cell whose tap-to-tap f₁ scatter exceeds ±20%, and it fails
*silently* — it returns a plausible number rather than a NaN or a warning. Worth either
widening it for the f₁ slot, or having `set_mode_frequencies` warn when a tap's Step-1
`dom` value lies outside the window it then extracts in. That is a change to shared
toolkit code, so I have not made it unasked.

**Not a provenance problem, though it looks like one.** The raw files inside
`base_moderate_c1/` are named `F1_moderate_c1_*`. That is the documented Day 6
one-floor-lower rename: folders were corrected to the physical plate and the raw
filenames kept their capture-time names as provenance
(`DAMAGE_LOCATION_MAP.md`, Day 6 section). Folder name is authoritative. I checked this
before concluding, because it superficially resembles a mix-up.

### 4.4 Figure 9.6's 27 / 13 against §9.4.3's 33 / 1.7 — both reconciled

You were right that neither is wrong. Computed both ways, same runs, same 2σ floors:

| | closest class pair | point-to-class-mean scatter | ratio |
|---|---|---|---|
| **2-mode (f₁, f₃)** — what Figure 9.6 plots | base ↔ F1 = **26.6** | max 2.06, mean 0.71 | 12.9× (max) |
| **3-mode (f₁, f₂, f₃)** — the classifier space | base ↔ F1 = **33.0** | max 3.09, **mean 1.83**, rms 2.04 | 10.7× (max), 18.0× (mean) |

- **Your 33 is exactly the three-mode base ↔ Floor 1 centroid distance** (33.0).
- **Your 1.7 is the mean-basis three-mode scatter** (1.83 — so 1.8 rather than 1.7, but
  the same statistic). The figure used the max basis, which is why it read 2.1.
- The caption now says **"in this (f₁, f₃) projection"** and points at §9.4.3 for the
  three-mode separation, so the two can no longer be read as contradicting.
- **For the chapter, on the point-to-class-mean definition in three dimensions:**
  separation **33.0** floor-units, scatter **3.09** max / **1.83** mean, giving
  **10.7×** or **18.0×**. Pick one aggregation and state it; I would use max for
  consistency with the figure, i.e. 33.0 / 3.09 = **10.7×**.
- **One consequence worth checking.** Floor 3 has no f₂ in any replicate, so it cannot
  enter a three-mode space at all — the 33.0 covers **3 of the 4 classes**. If §9.4.3
  describes the classifier as operating on three modes, it cannot classify Floor 3 on
  that basis, and the two-mode projection is the only space where all four classes are
  representable. That may be worth a sentence.

### 4.5 The 36 Hz peak — annotated as 3f₃ per the chapter, but my test was negative

Now annotated at 36.2 Hz, as you asked, on the chapter's identification. Recording the
caveat because the evidence I can compute does not support it and someone may ask:

- **Quantitatively it is marginal.** 36.245 Hz against 3f₃ = 36.562 predicted (−0.87%),
  at **0.044% of the f₃ peak**, prominence 3.8 over the local median.
- **It does not track f₃ under damage**, which is the test a harmonic must pass:

| capture | f₃ | 3f₃ | strongest 30–42 Hz peak | peak / local median |
|---|---|---|---|---|
| Day-1 ringdown | 12.184 | 36.55 | 36.26 | 3.8 |
| day4_baseline | 12.204 | 36.61 | 34.91 | 2.1 |
| F1 severe | 11.001 | 33.00 | 40.41 | 2.6 |
| F2 severe | 10.569 | 31.71 | 30.03 | 2.8 |

The coincidence on the Day-1 set is close (36.26 against 36.55, 0.9%), but when f₃ drops
to 11.00 the band maximum moves *up* to 40.4, and on an undamaged Day-4 baseline it is
already at 34.9. Prominence over the local median is 2–4 throughout, which is noise for
a spectrum whose real peaks reach 10³–10⁴.

**This does not mean the chapter is wrong** — a genuine harmonic at 0.04% of the
fundamental peak would be near the noise floor and would not survive a peak-tracking
test on ringdown data, which is a weak test at this amplitude. But it does mean the
figure now asserts something the ringdown data alone cannot support. If a reader
challenges it, the defensible test is a swept-sine drive at 12 Hz checking that a 36 Hz
response appears and scales super-linearly with drive amplitude — a nonlinear harmonic
will, a structural mode will not. That is one short capture if you want to close it.

### 4.6 Carried over from the previous review, still applicable

1. **`[X]` = 2%** (1.09% mean, 1.95% worst). §9.1.1.
2. **"swept-sine FRF" is not accurate.** There is no measured input channel — the rig
   records response acceleration only, so what exists is a swept-sine *response
   spectrum*, not a frequency response function. Figure 9.1 is labelled accordingly.
   Recommend the text match.
3. **The fourth-mode frequency.** 15.8 Hz is right, but only against a particular
   baseline: uniform 4-DOF shear theory gives f₄ = 5.411 × f₁, so 15.81 Hz from the
   Table 9.1 / Day 6 f₁ of 2.9216 Hz (what the figure now uses), 15.85 Hz from the
   Day 1 ringdown, and 15.92 Hz from the Day 4 baseline.
   `RESULTS_for_dissertation.md` says 15.9 Hz, your §9.1.2 says 15.8. The figure is now
   self-consistent with 15.8; align the text and results doc.
4. **"Fits them exactly" is true for two of the four cases, not all.** Base and
   Floor 2 fit to machine precision. Floor 1 does not, and Figure 9.11's lower panel
   now shows it. §9.6.4 overstates this.
5. **Baselines are session-matched throughout** (Day 4 severe → `day4_baseline`,
   Day 6 graded → `day6_baseline`, Arm B → each position's own baseline). The
   superseded `make_figures.py` used `day6_baseline` for everything, which shifted the
   Day 4 numbers by 0.1–0.3 pp. **This was the source of the three stale Table 9.9
   cells**, now corrected in the chapter. If any draft text quotes figure values rather
   than table values, check it.

### 4.7 One over-claim I have left alone, for you to rule on

**Figure 9.6's title still says "12/12 runs fall in their own cluster."** Strictly,
only 11 of 12 have both coordinates — `F3_severe_r1` has no Δf₃ and cannot be placed
in the 2-D signature space at all. It *is* correctly classified on f₁ alone (51.7,
unambiguously in Floor 3's cluster), so the claim is defensible on one axis but not on
the plane the figure plots. Given you were corrected on the "same on f₁" wording for
exactly this kind of reason, you may want the same treatment here. Two options:

- "**11/12 runs resolve fully; all 12 classify to their own location**" — precise, and
  keeps the strong point.
- "**12/12 runs classify to their own location**" — true as stated, drops "cluster".

I have not changed it, because it is the figure's headline claim and it is yours to
make.

---
---

## 5. One gap you should decide on

§9.5 makes **three** claims, and the new set covers only one of them:

| §9.5 claim | Figure |
|---|---|
| Observability changes with position (53/60/100, 25/5/100, 7/56/100) | 9.7–9.9 ✅ |
| Damage shifts are invariant to position, agreeing to 1–2% | **none** |
| Base vs Floor 1 separates on f₃ from every position | **none** |

The superseded set had a figure for each of the latter two
(`fig07_shift_invariance.png`, `fig08_baseVsF1_discriminator.png`). Your brief for
figures 6–8 replaced them with the three spectra, so those two arguments now rest on
the text and Table alone. They are recoverable — the old files are in git:

```
git checkout 6078bbc -- four_floor/characterisation/figures/fig07_shift_invariance.png \
                        four_floor/characterisation/figures/fig08_baseVsF1_discriminator.png
```

Better, I can regenerate both in the new house style. They would slot into §9.5 as
Figures 9.10 and 9.11, pushing the two §9.6 figures to 9.12 and 9.13 and taking the
set to thirteen. Say the word — this is the only remaining gap I know of.

Note that the second of these is now *more* worth having, not less: §9.4's base-plate /
Floor 1 separation is 3% on f₁ (not "the same", per Figure 9.6 above), so the claim
that f₃ is what actually separates the pair carries more of the argument than the
earlier wording implied, and it currently has no figure at any sensor position but the
default one.

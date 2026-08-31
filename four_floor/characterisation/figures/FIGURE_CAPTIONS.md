# Chapter 4 — figure captions

Twelve figures, in `four_floor/characterisation/figures/` as PNG (200 dpi) and PDF
(vector). The figures carry no baked-in caption text: everything below the axes was
removed so the caption lives in the document, where it can be numbered and typeset.
The blocks below are therefore the only copy of that text — paste them under each
figure. Everything drawn inside the axes (titles, legends, peak labels, bar values,
cell values, callouts) is already in the image.

| Figure | File | Section |
|---|---|---|
| 4.1 | `fig01_baseline_spectrum` | 4.1.1 |
| 4.2 | `fig02_detection` | 4.2 |
| 4.3 | `fig03_severity_heatmap` | 4.3 |
| 4.4 | `fig11_tap_repeatability` | 4.3.1 |
| 4.5 | `fig04_fingerprints` | 4.4 |
| 4.6 | `fig05_signature_space` | 4.4 |
| 4.7 | `fig06_spectrum_sensor_top` | 4.5 |
| 4.8 | `fig07_spectrum_sensor_floor2` | 4.5 |
| 4.9 | `fig08_spectrum_sensor_floor1` | 4.5 |
| 4.10 | `fig09_seed_sweep_calls` | 4.6.3 |
| 4.11 | `fig10_inversion_branches` | 4.6.5 |
| 4.12 | `fig12_plate_hypotheses` | 4.6.6 |

Filenames do not track figure numbers from 4.4 onward. They are append-only because
the session records cite them by filename.

---

**Figure 4.1** Frequency response of the undamaged frame, 0–60 Hz. Tap-averaged
free-decay ringdown (7 taps, Day 1) and swept-sine response (three 120 s repeats at
1.2 A / 2.2 V, linear 1–15 Hz, scaled to the ringdown's fundamental). The three modes
are annotated with the campaign baseline values f₁ = 2.92 Hz, f₂ = 8.11 Hz and
f₃ = 12.19 Hz; the plotted Day-1 ringdown peaks agree with them to 0.40%. The two
measurement methods agree with each other to 1.09% mean and 1.95% worst. The
four-degree-of-freedom prediction of a fourth mode at 15.8 Hz is marked; no such peak
is present. The feature at 36.2 Hz is the third harmonic of f₃ (36.56 Hz predicted,
−0.9%), at 0.04% of the f₃ peak. Beyond 15 Hz only the ringdown is informative — the
shaker delivers nothing above ≈12 Hz.

**Figure 4.2** Detection of severe damage. **(a)** Undamaged baseline and Floor 1
severe damage spectra overlaid, showing the fundamental migrating from 2.94 Hz to
1.16 Hz (−60.5%). **(b)** |Δf₁| by damage location on a logarithmic axis, against the
0.30% reassembly floor (2σ over five complete teardown/rebuild cycles, shaded). Every
location clears the floor by between 52× and 202×. Error bars are the standard
deviation over three independent damage/repair replicates.

**Figure 4.3** Modal shift by damage location and grade, one panel per mode. Colour
encodes |Δf|; printed values are the signed measured shifts to one decimal. Colour
scales are per panel, rounded up to a labelled tick, because the three modes differ in
range by roughly a factor of four. Grades trace to moderate are single damage cycles
against the Day 6 baseline; severe is the mean of three replicates against the Day 4
baseline. "n/r" marks a mode voided by a harmonic of f₁ — Floor 2 / light by the third
harmonic, Floor 3 / severe by the second.

**Figure 4.4** Tap-to-tap repeatability of Δf₁ by location and grade. Each point is one
of the five individual taps in a cell, differenced against that cell's own mean, so the
spread shown is measurement repeatability rather than damage magnitude. All four panels
share one scale. The shaded band is the ±0.30% reassembly floor. Printed values are the
full range in percentage points. Scatter at the base plate grows with damage grade to
15.5 pp at moderate — 26× the reassembly floor — while Floor 2 and Floor 3 stay inside
1.5 pp at every grade.

**Figure 4.5** Three-mode damage signatures for severe damage at each location, mean ±
standard deviation over three independent damage/repair replicates against the Day 4
baseline. Floor 3's second mode is left empty and marked "n/r": it is voided in all
three replicates by the second harmonic of f₁ at 5.1 Hz. Floor 3's third mode is marked
n = 2 — it resolved in two of the three replicates.

**Figure 4.6** Normalised signature space. Each severe-damage run is plotted as |Δf₁|
and |Δf₃| divided by that mode's 2σ reassembly floor (0.30% and 0.32% respectively).
Upper panel: all four locations, with class means ringed. Lower row: each cluster at
its own scale, resolving every replicate individually. Base plate and Floor 1 lie 3%
apart on f₁ (196× against 202×) and 6× apart on f₃ (5× against 31×). One Floor 3 run
has no Δf₃ coordinate — its third mode fell below the per-tap detection threshold. It
is drawn in a separate strip in both the main panel and its zoom panel, never at a
readable Δf₃ value, and that panel is labelled 2 of 3. In this (f₁, f₃) projection the
closest pair of class means, base plate and Floor 1, are 26.6 floor-units apart — 13×
the largest within-class scatter of 2.1 units, measured point to its own class mean.
The three-mode separation the classifier uses is larger; see §4.4.3.

**Figure 4.7** Measured spectrum with the sensor on Floor 3 (top). Tap-averaged
undamaged ringdown, normalised to the strongest mode at that position. Annotated
percentages are the relative modal amplitudes at that position: 53 / 60 / 100.

**Figure 4.8** As Figure 4.7, sensor on Floor 2: 25 / 5 / 100. The second mode is all
but absent, consistent with the sensor sitting near that mode's node.

**Figure 4.9** As Figure 4.7, sensor on Floor 1: 7 / 56 / 100. The second mode returns;
the fundamental is now the weakest of the three.

*Applying to Figures 4.7–4.9:* mode frequencies differ by at most 0.06 Hz (1.0%)
between the three positions. The frame is unchanged across these three captures, so
that spread is sensor mass loading rather than structural change.

**Figure 4.10** Storey called by the physics-informed network, by damage location and
grade. Each cell is the majority call over a sweep of 20 random seeds × 2 physics-loss
weights, 40 runs per cell; severe cells average the three replicates. Cells are
coloured by the storey stiffness carrying the smallest predicted retention, and where
the call is not unanimous the split is printed with a proportional strip in the
minority colour along the bottom of the cell. Two cells have no record, their modal
vectors having been voided by a harmonic of f₁. The network calls the bottom storey k₁
at the base plate and Floor 1 and the top storey k₃ at Floor 3, and returns the middle
storey k₂ in only 12% of the runs of a single cell — so its calls track the two
extremes of the frame rather than the damaged plate.

**Figure 4.11** Every exact solution branch recovered by multi-start least-squares
inversion of the measured modal vectors through the 3-DOF shear model, with no network
involved. Each panel is one damage case and each group of three bars (B1, B2, …) is a
distinct branch reproducing the measured frequencies. The region above unity is shaded:
a recovered stiffness above the healthy value is physically inadmissible. The base
plate returns four branches and Floor 1 two, none admissible; the base plate's least
inadmissible branch has k₂ = 1.146, and over 1000 draws perturbed by the measurement
scatter its 95% interval is [1.132, 1.160], never crossing unity. Floor 2 returns one
admissible branch of four, and that branch still attributes the softening to k₁, a
storey the loosened plate does not adjoin. Floor 3 is hatched: with only two modes
resolving, its three stiffnesses are under-determined. Branches come from a
random-start search, so the absence of an admissible branch is a recovery result rather
than a proof of non-existence.

**Figure 4.12** Ranking of the four single-plate damage hypotheses against each measured
case. Each row is one measured damage state and each marker the RMS residual of fitting
that row's modal vector with a single loosened plate; the filled marker is the
hypothesis ranked first and the black ring marks the true location. Only the base-plate
case is identified correctly, and it is the only one identified by a large margin:
0.795 Hz, against 0.181, 0.251 and 0.027 Hz for the three storeys. Bracketed intervals
are 95% ranges over 400 draws perturbed by the per-mode reassembly scatter. Every gap
is strictly positive — the ranking is resolved by the data in all four cases, including
Floor 3 at 0.027 Hz — so the three storey misidentifications are failures of the plate
model rather than ties within measurement noise.

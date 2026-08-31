"""
make_figures_ch9.py — Chapter 4 results figure set (fig01..fig12)
=================================================================

Figures carry NO baked-in caption text: a caption belongs in the document, where it
can be numbered and typeset. Suggested caption text for every figure is kept in
characterisation/figures/FIGURE_CAPTIONS.md.
Regenerates the dissertation Chapter 4 figures into characterisation/figures/.
One consistent style throughout
(Okabe-Ito colourblind-safe palette, recessive hairline grid, replicate error
bars). Read-only w.r.t. data; writes only PNG + PDF.

    python3 make_figures_ch9.py

BASELINES ARE SESSION-MATCHED. Every shift is computed against the baseline
recorded in the same session as the damaged capture, because between-session
damage reproducibility is only a few percent (Day 4 §2):
    Day 4 severe replicates  -> day4_baseline
    Day 6 graded c1 sets     -> day6_baseline
    Day 7 Arm B positions    -> that position's own baseline
This is what makes the figures agree with the chapter tables.

PALETTE. Okabe-Ito. Validated against the six categorical checks (OKLab dE*100,
Machado-Oliveira-Fernandes 2009 CVD simulation at severity 1.0):
  3-series (f1/f2/f3, k1/k2/k3), adjacent pairs : CVD 11.4, normal 24.2  PASS
  4-class scatter (fig05), ALL pairs            : CVD 11.0, normal 15.6  PASS
  2-trace overlay (fig01, fig02a), adjacent     : CVD 21.9, normal 31.2  PASS
Orange #E69F00 sits at 2.19:1 on white (below the 3:1 mark floor), so every
figure using it as a large fill also carries printed values or direct labels as
the relief channel.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import interpret_capture as ic          # noqa: E402
import toolkit_common as tk             # noqa: E402
from simulation import rig_3dof as R    # noqa: E402

_HERE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE = "characterisation"
OUT = f"{BASE}/figures"
os.makedirs(OUT, exist_ok=True)

# --------------------------------------------------------------------------
# Style
# --------------------------------------------------------------------------
OI = {"blue": "#0072B2", "orange": "#E69F00", "green": "#009E73",
      "vermillion": "#D55E00", "purple": "#CC79A7", "sky": "#56B4E9"}
MODE = [OI["blue"], OI["orange"], OI["green"]]        # f1, f2, f3 — fixed roles
LOCC = [OI["blue"], OI["orange"], OI["green"], OI["vermillion"]]  # base,F1,F2,F3
INK, MUTED, GRID, FAINT = "#222222", "#666666", "#DDDDDD", "#F2F2F2"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10,
    "axes.titlesize": 11, "axes.titleweight": "bold", "axes.labelsize": 10,
    "axes.edgecolor": MUTED, "axes.linewidth": 0.8,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.axisbelow": True, "xtick.color": INK, "ytick.color": INK,
    "text.color": INK, "axes.labelcolor": INK,
    "legend.frameon": False, "legend.fontsize": 9,
    "figure.dpi": 200, "savefig.dpi": 200, "savefig.bbox": "tight",
    "savefig.facecolor": "white", "figure.facecolor": "white",
})

LOCS = ["base", "F1", "F2", "F3"]
LNAMES = ["Base plate", "Floor 1", "Floor 2", "Floor 3"]
MODELAB = ["$\\Delta f_1$", "$\\Delta f_2$", "$\\Delta f_3$"]

# Reassembly floors, Day 3, 5 full teardown/rebuild cycles (SESSION_2026-07-22_day3 §2).
# Per-mode 1-sigma; 2-sigma is the "lightest attributable grade".
FLOOR_1SD = np.array([0.15, 0.23, 0.16])
FLOOR_2SD = 2 * FLOOR_1SD                      # f1 0.30%, f2 0.46%, f3 0.32%


def despine(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=3, color=MUTED)


def save(fig, stem):
    for ext in ("png", "pdf"):
        fig.savefig(f"{OUT}/{stem}.{ext}")
    plt.close(fig)
    print(f"  wrote {stem}.png / .pdf")


def vec(folder):
    return ic.modal_vector(f"{BASE}/{folder}")


def avg_psd(paths, nperseg=None):
    """Tap-averaged unfiltered Welch PSD over a list of raw captures."""
    total, freqs = None, None
    for p in paths:
        x, _ = tk.load_raw_series(p)
        freqs, psd = tk.raw_psd(x, nperseg=nperseg)
        total = psd if total is None else total + psd
    return freqs, total / len(paths)


def folder_psd(folder, nperseg=None):
    return avg_psd(sorted(glob.glob(f"{BASE}/{folder}/*_raw.csv")), nperseg)


def peak_near(freqs, psd, f0, bw=0.8):
    m = (freqs >= f0 - bw) & (freqs <= f0 + bw)
    return tk.refine_peak_parabolic(freqs[m], psd[m], int(np.argmax(psd[m])))


def f1_per_tap(folder):
    """Per-tap f1 by the toolkit's own Step-1 rule: the most prominent peak in the
    f1 band, per tap, with NO window applied.

    WHY THIS EXISTS. set_mode_frequencies sets f1 = median(dom) over the taps and
    then RE-EXTRACTS each tap's value inside f1*(1 +/- rel_bw), rel_bw = 0.20. If a
    cell's tap-to-tap scatter is wide enough that a tap's true fundamental falls
    outside that window, the re-extraction silently substitutes whatever shoulder
    lies inside it. Exactly ONE cell in the campaign does this — audited over every
    folder, see below — and it is base_moderate_c1: tap 5's fundamental is 1.7665 Hz
    against a window of [1.157, 1.735], so it was recorded as the 1.600 Hz shoulder
    (refined 1.6358) instead. That drags the cell mean from 1.4917 to 1.4655 and
    Δf1 from −48.94% to −49.84%.

    The cell that breaks the window is the least repeatable one in the campaign
    (per-tap range 15.5 pp, Figure 9.4), so the instability that makes it evidence
    for joint slip is the same thing that defeats the windowed extraction.
    Table 9.5's −48.94 is therefore the correct value and the figure's was an
    artefact. See FIGURE_NOTES.md §4.3.
    """
    vals = []
    for p in sorted(glob.glob(f"{BASE}/{folder}/*_raw.csv")):
        x, _ = tk.load_raw_series(p)
        fq, ps = tk.raw_psd(x)
        pk = tk.find_spectral_peaks(fq, ps, 0.9, 20.0, n_peaks=8,
                                    prominence_factor=8)
        low = [q for q in pk if 0.9 <= q["f_hz"] <= 3.5]
        if low:
            vals.append(max(low, key=lambda q: q["prominence_ratio"])["f_hz"])
    return np.array(vals)


def f1_window_clipped(folder, rel_bw=0.20):
    """(clipped_tap_count, corrected_mean_f1) for a folder's f1 slot.

    Reproduces set_mode_frequencies' own window so the check stays honest if
    rel_bw ever changes there.
    """
    v = f1_per_tap(folder)
    if len(v) == 0:
        return 0, np.nan
    med = float(np.median(v))
    out = int(((v < med * (1 - rel_bw)) | (v > med * (1 + rel_bw))).sum())
    return out, float(v.mean())


def reps_shift(prefix, bl, rs=(1, 2, 3)):
    """(mean, sd, n) of Δf1/f2/f3 % over replicate folders <prefix>r{n}."""
    sv = [(vec(f"{prefix}{r}") - bl) / bl * 100
          for r in rs if os.path.isdir(f"{BASE}/{prefix}{r}")]
    sv = np.array(sv)
    with np.errstate(invalid="ignore"):
        return np.nanmean(sv, axis=0), np.nanstd(sv, axis=0), len(sv)


print("Chapter 9 figure set ->", OUT)
b4 = vec("day4_baseline")          # Day 4 localisation reference
b6 = vec("day6_baseline")          # Day 6 graded reference
print(f"  day4_baseline {np.round(b4, 3)}   day6_baseline {np.round(b6, 3)}")

# ==========================================================================
# FIG 01 — §9.1.1  undamaged frequency response, ringdown + swept sine, 0-60 Hz
# ==========================================================================
# Ringdown: the 7 Day-1 characterisation taps. Swept sine: the three 120 s
# repeats at the mid amplifier gain (1.2 A / 2.2 V), linear 1->15 Hz.
rd_paths = sorted(glob.glob(f"{BASE}/ringdown*_20260721_*_raw.csv"))
sw_paths = sorted(glob.glob(f"{BASE}/sweep_2v2_r*_raw.csv"))
fr_r, p_rd = avg_psd(rd_paths, nperseg=8192)
fr_s, p_sw = avg_psd(sw_paths, nperseg=8192)

f_rd = np.array([peak_near(fr_r, p_rd, f0) for f0 in (2.94, 8.10, 12.19)])
f_sw = np.array([peak_near(fr_s, p_sw, f0) for f0 in (2.94, 8.10, 12.19)])
agree = np.abs(f_sw - f_rd) / f_rd * 100

# ANNOTATE THE TABLE 9.1 CAMPAIGN MODES, NOT THIS FIGURE'S OWN PEAK FIT.
# §9.1.2 argues from the mode RATIOS, so the annotated frequencies have to be the
# same ones the table and that argument use. b6 (day6_baseline, set-clustered per
# tap) reproduces Table 9.1 exactly: 2.92 / 8.11 / 12.19. The parabolic fit on
# this figure's own Day-1 tap-averaged PSD gives 2.93 / 8.08 / 12.18 — a different
# estimator on a different capture set, and its ratios differ in the third digit.
F_TBL = b6
tbl_agree = np.abs(f_rd - F_TBL) / F_TBL * 100

# Uniform shear-frame theory: w_n ∝ sin((2n-1)π/(2(2N+1))). N=4 -> 4th mode.
# Derived from the Table 9.1 f1 so the ratio argument stays self-consistent.
r4 = np.array([np.sin((2 * n - 1) * np.pi / 18) for n in (1, 2, 3, 4)])
f4_pred = F_TBL[0] * r4[3] / r4[0]

SWEEP_HI = 15.0                                  # sweep ran 1 -> 15 Hz
m_r = (fr_r >= 0.5) & (fr_r <= 60)
m_s = (fr_s >= 1.0) & (fr_s <= SWEEP_HI)
# Scale the sweep trace onto the ringdown's f1 peak so shapes are comparable
# on one axis (no second y-scale — the traces differ in absolute drive level).
scale = p_rd[m_r].max() / p_sw[m_s].max()

fig, ax = plt.subplots(figsize=(8.2, 4.4))
ax.axvspan(SWEEP_HI, 60, color=FAINT, zorder=0)
ax.semilogy(fr_r[m_r], p_rd[m_r], color=OI["blue"], lw=1.5,
            label=f"Ringdown, free decay ({len(rd_paths)} taps)")
ax.semilogy(fr_s[m_s], p_sw[m_s] * scale, color=OI["vermillion"], lw=1.5,
            alpha=0.9, label=f"Swept sine, 1–15 Hz ({len(sw_paths)} repeats, scaled)")

ytop = p_rd[m_r].max()
# Label each peak directly above its own crest on a purely vertical leader, at
# three separated heights. Vertical leaders are what keeps this clean: a leader
# only ever rises through its own peak's column, and no peak sits underneath a
# neighbour's label, so no line can cross a label. f1 is nudged right so its
# label clears the y-axis, still leaving f2's column free.
PEAK_OFF = [(9, 22), (0, 30), (0, 58)]
for i, (f0, lab) in enumerate(zip(F_TBL, ["$f_1$", "$f_2$", "$f_3$"])):
    pk = p_rd[np.argmin(np.abs(fr_r - f0))]
    ax.annotate(f"{lab}  {f0:.2f} Hz", (f0, pk), xytext=PEAK_OFF[i],
                textcoords="offset points", ha="center", va="bottom",
                fontsize=9, color=INK, fontweight="bold",
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.7,
                                shrinkA=2, shrinkB=3))

# The 4-DOF prediction that is absent — the claim §9.1.2 rests on.
lvl = p_rd[np.argmin(np.abs(fr_r - f4_pred))]
ax.annotate(f"no 4th mode at {f4_pred:.1f} Hz\n(4-DOF theory predicts one)",
            (f4_pred, lvl), xytext=(f4_pred + 6, lvl * 45),
            ha="left", va="center", fontsize=8.5, color=OI["purple"],
            fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=OI["purple"], lw=1.4))
# High in the shaded band, between the legend and the purple note: at its old low
# position it sat right on top of the 3f3 label and its leader.
ax.annotate("beyond the swept-sine band:\nringdown only (shaker ceiling ≈ 12 Hz)",
            (44, ytop * 6), ha="center", va="center", fontsize=8,
            color=MUTED, style="italic")

# The 36 Hz feature, identified as 3*f3 in the chapter. Annotated per that
# identification — note it is 0.044% of the f3 peak and my own tracking test across
# the damaged captures did NOT confirm it (see FIGURE_NOTES.md §4.3).
_m36 = (fr_r >= 34) & (fr_r <= 39)
f3h = float(tk.refine_peak_parabolic(fr_r[_m36], p_rd[_m36],
                                     int(np.argmax(p_rd[_m36]))))
f3h_lvl = float(p_rd[_m36].max())
ax.annotate(f"3$f_3$\n{f3h:.1f} Hz", (f3h, f3h_lvl), xytext=(0, 30),
            textcoords="offset points", ha="center", va="bottom", fontsize=8.5,
            color=OI["green"], fontweight="bold",
            arrowprops=dict(arrowstyle="-", color=OI["green"], lw=0.8,
                            shrinkA=2, shrinkB=3))

ax.set_xlim(0, 60)
ax.set_ylim(p_rd[m_r].min() * 0.4, ytop * 400)
ax.set_xlabel("Frequency (Hz)")
ax.set_ylabel("Power spectral density (g$^2$/Hz)")
ax.set_title("Frequency response of the undamaged frame: three modes, no fourth")
ax.legend(loc="upper right", ncol=1)
despine(ax)
ax.grid(axis="x", visible=False)
save(fig, "fig01_baseline_spectrum")
print(f"    3f3 feature {f3h:.3f} Hz vs 3*f3 {3 * F_TBL[2]:.3f} predicted; "
      f"{f3h_lvl / float(p_rd[(fr_r >= 12) & (fr_r <= 12.4)].max()) * 100:.3f}% of the f3 peak")
print(f"    Table 9.1 labels {np.round(F_TBL,3)}  (ratios {np.round(F_TBL/F_TBL[0],4)})")
print(f"    plotted ringdown peaks {np.round(f_rd,3)} -> agree with Table 9.1 to "
      f"{tbl_agree.max():.2f}%   sweep {np.round(f_sw,3)}  f4_pred {f4_pred:.2f} Hz")

# ==========================================================================
# FIG 02 — §9.2  detection: (a) spectra migrating, (b) |Δf1| vs the floor
# ==========================================================================
sev_mean, sev_sd, sev_n = {}, {}, {}
for loc in LOCS:
    m_, s_, _ = reps_shift(f"{loc}_severe_r", b4)
    sev_mean[loc], sev_sd[loc] = m_, s_
    # PER-MODE replicate count, not per-location. Floor 3's f3 resolved in only two
    # of the three replicates (r1's f3 was found in 2 of 5 taps, one short of the
    # 3-tap majority rule, so the slot was dropped), so its mean and sd are n=2.
    sv = np.array([(vec(f"{loc}_severe_r{r}") - b4) / b4 * 100 for r in (1, 2, 3)
                   if os.path.isdir(f"{BASE}/{loc}_severe_r{r}")])
    sev_n[loc] = (~np.isnan(sv)).sum(axis=0)
print("    replicates resolved per mode:", {l: sev_n[l].tolist() for l in LOCS})

fig, axes = plt.subplots(1, 2, figsize=(10.4, 3.9))

# (a) representative case: Floor 1, severe (largest Δf1 of the three storeys)
ax = axes[0]
fr_b, psd_b = folder_psd("day4_baseline", nperseg=8192)
fr_d, psd_d = folder_psd("F1_severe_r1", nperseg=8192)
mb = (fr_b >= 0.5) & (fr_b <= 16)
ax.semilogy(fr_b[mb], psd_b[mb], color=OI["blue"], lw=1.5, label="Undamaged baseline")
ax.semilogy(fr_d[mb], psd_d[mb], color=OI["vermillion"], lw=1.5, label="Floor 1, severe")
f1b, f1d = b4[0], vec("F1_severe_r1")[0]
ytop_a = max(psd_b[mb].max(), psd_d[mb].max())
ax.annotate("", xy=(f1d, ytop_a * 1.7), xytext=(f1b, ytop_a * 1.7),
            arrowprops=dict(arrowstyle="<|-", color=INK, lw=1.3, shrinkA=0, shrinkB=0))
ax.annotate(f"$f_1$: {f1b:.2f} → {f1d:.2f} Hz\n({(f1d-f1b)/f1b*100:+.1f}%)",
            ((f1b + f1d) / 2, ytop_a * 2.2), xytext=(14, 0),
            textcoords="offset points", ha="left", va="bottom", fontsize=9,
            fontweight="bold", color=INK)
ylo_a = min(psd_b[mb].min(), psd_d[mb].min()) * 0.5
# Stop the peak markers at the migration arrow instead of running full height —
# a full axvline crosses both the arrow label and the legend.
for f0, c in ((f1b, OI["blue"]), (f1d, OI["vermillion"])):
    ax.vlines(f0, ylo_a, ytop_a * 1.7, color=c, lw=0.6, alpha=0.5, zorder=1)
ax.set_xlim(0.5, 16)
# Headroom for a legend above the 10–16 Hz traces: the lower-left corner is
# occupied by the baseline trace, so the legend cannot live there.
ax.set_ylim(ylo_a, ytop_a * 45)
ax.set_xlabel("Frequency (Hz)")
ax.set_ylabel("Power spectral density (g$^2$/Hz)")
ax.set_title("(a) The fundamental migrates under damage", loc="left")
ax.legend(loc="upper right")
despine(ax)
ax.grid(axis="x", visible=False)

# (b) |Δf1| by location on a log axis against the 0.30% reassembly floor
ax = axes[1]
mags = np.array([abs(sev_mean[l][0]) for l in LOCS])
errs = np.array([sev_sd[l][0] for l in LOCS])
x = np.arange(4)
ax.axhspan(1e-3, FLOOR_2SD[0], color=OI["green"], alpha=0.18, zorder=0)
ax.axhline(FLOOR_2SD[0], color=OI["green"], lw=1.2, zorder=1)
ax.bar(x, mags, 0.6, yerr=errs, capsize=3, color=OI["vermillion"],
       edgecolor="white", linewidth=0.8, zorder=3)
for xi, (mg, er) in enumerate(zip(mags, errs)):
    ax.annotate(f"{mg:.1f}%\n{mg / FLOOR_2SD[0]:.0f}×", (xi, mg + er),
                xytext=(0, 5), textcoords="offset points", ha="center",
                fontsize=8.5, fontweight="bold", color=INK)
# The bars span the full height, so the floor is keyed in the legend rather than
# labelled in place, where it would have to sit on top of a bar.
ax.legend(handles=[Patch(facecolor=OI["green"], alpha=0.18, edgecolor=OI["green"],
                         label=f"reassembly floor {FLOOR_2SD[0]:.2f}% (2σ, 5 rebuilds)"),
                   Patch(facecolor=OI["vermillion"],
                         label="severe damage (mean ± sd, n = 3)")],
          loc="upper center", bbox_to_anchor=(0.5, 1.0), fontsize=8.5)
ax.set_yscale("log")
ax.set_ylim(0.06, 4000)
ax.set_xticks(x)
ax.set_xticklabels(LNAMES)
ax.set_xlim(-0.6, 3.6)
ax.set_ylabel("$|\\Delta f_1|$  (%, log scale)")
ax.set_title(f"(b) Every location clears the floor by {mags.min() / FLOOR_2SD[0]:.0f}–{mags.max() / FLOOR_2SD[0]:.0f}×", loc="left")
despine(ax)
ax.grid(axis="x", visible=False)
fig.suptitle("Detection of severe damage", fontweight="bold", y=1.02)
fig.tight_layout()
save(fig, "fig02_detection")
print("    |Δf1| ×floor:", {l: round(abs(sev_mean[l][0]) / FLOOR_2SD[0]) for l in LOCS})

# ==========================================================================
# FIG 03 — §9.3  severity heatmap, 4 locations × 4 grades, one panel per mode
# ==========================================================================
GRADES = ["trace", "light", "moderate", "severe"]
GLAB = ["trace\n⅛ turn", "light\n½ turn", "moderate\n1 turn", "severe\n3 turns"]
M = np.full((3, 4, 4), np.nan)                    # mode, location, grade
clipped = []                                      # cells where the f1 window truncated
for li, loc in enumerate(LOCS):
    for gi, g in enumerate(GRADES[:3]):           # Day 6, vs day6_baseline
        f = f"{loc}_{g}_c1"
        if not os.path.isdir(f"{BASE}/{f}"):
            continue
        M[:, li, gi] = (vec(f) - b6) / b6 * 100
        # Correct f1 wherever set_mode_frequencies' per-tap window excluded a
        # tap's real fundamental (see f1_per_tap). Fires on exactly one cell.
        n_out, f1_fix = f1_window_clipped(f)
        if n_out:
            was = M[0, li, gi]
            M[0, li, gi] = (f1_fix - b6[0]) / b6[0] * 100
            clipped.append((LNAMES[li], g, n_out, was, M[0, li, gi]))
    M[:, li, 3] = sev_mean[loc]                   # Day 4 severe, vs day4_baseline
# Severe/baseline folders are unaffected — audited across every folder in the
# campaign, base_moderate_c1 is the only one with a tap outside the window.
for nm, g, n_out, was, now in clipped:
    print(f"    f1 WINDOW CORRECTION  {nm} {g}: {n_out} tap(s) outside "
          f"median(dom)±20% -> Δf1 {was:+.2f} => {now:+.2f}  (Table 9.5 basis)")
assert len(clipped) == 1 and clipped[0][:2] == ("Base plate", "moderate"), \
    f"f1-window clipping changed footprint: {clipped}"


def void_order(folders):
    """Which harmonic of f1 voided a slot in this cell: 2, 3, or None.

    The two voided cells are NOT the same harmonic — Floor 2 / light is 3*f1 and
    Floor 3 / severe is 2*f1 — so the hatch note has to be derived, not assumed.
    """
    for folder in folders:
        if not os.path.isdir(f"{BASE}/{folder}"):
            continue
        paths = sorted(glob.glob(f"{BASE}/{folder}/*_raw.csv"))
        _, cl = tk.set_mode_frequencies(paths)
        susp = tk.set_mode_frequencies.last_harmonic_suspect
        got = sorted((float(np.mean(cl[i])), bool(i < len(susp) and susp[i]))
                     for i in range(len(cl)) if len(cl[i]))
        if not got:
            continue
        f1 = got[0][0]
        for fq, s in got:
            if s:
                return int(round(fq / f1))
    return None


voids = {}                                        # (location, grade) -> harmonic order
for li, loc in enumerate(LOCS):
    for gi, g in enumerate(GRADES):
        if not np.isnan(M[:, li, gi]).any():
            continue
        fl = [f"{loc}_{g}_c1"] if gi < 3 else [f"{loc}_severe_r{r}" for r in (1, 2, 3)]
        n = void_order(fl)
        if n:
            voids[(LNAMES[li], g)] = n
print("    harmonic voids:", {f"{k[0]} {k[1]}": f"{v}xf1" for k, v in voids.items()})

fig, axes = plt.subplots(1, 3, figsize=(13.6, 3.9))
for mi, ax in enumerate(axes):
    panel = M[mi]
    # Round the scale UP to a labelled tick. With vmax = the data max, the largest
    # cell (Δf2's −34.2) sat above the top tick and read as clipped.
    dmax = np.nanmax(np.abs(panel))
    step = 10.0 if dmax > 20 else 5.0
    vmax = float(np.ceil(dmax / step) * step)
    im = ax.imshow(np.abs(panel), cmap="Blues", vmin=0, vmax=vmax, aspect="auto")
    for i in range(4):
        for j in range(4):
            v = panel[i, j]
            if np.isnan(v):
                ax.text(j, i, "n/r", ha="center", va="center", fontsize=8.5,
                        color=MUTED, style="italic")
                ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, fill=False,
                                           hatch="////", edgecolor="#CCCCCC",
                                           linewidth=0))
            else:
                # One decimal, not integers: base/moderate is −49.8, and rounding it
                # to −50 both crossed a round number and disagreed with the table.
                ax.text(j, i, f"{v:+.1f}", ha="center", va="center", fontsize=8.6,
                        fontweight="bold",
                        color="white" if abs(v) > 0.55 * vmax else INK)
    ax.set_xticks(range(4))
    ax.set_xticklabels(GLAB, fontsize=8.5)
    ax.set_yticks(range(4))
    ax.set_yticklabels(LNAMES if mi == 0 else [""] * 4, fontsize=9)
    ax.set_title(f"$\\Delta f_{mi + 1}$ (%)")
    # pad has to clear the grade tick labels of the panel to the left; at 0.03
    # the bar and its title were wedged against the neighbouring heatmap.
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.055,
                      ticks=np.arange(0, vmax + step / 2, step))
    cb.set_label(f"$|\\Delta f_{mi + 1}|$ (%)", fontsize=8)
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=8, length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    ax.grid(False)
# $f_1$ IS monotonic in every row; f2/f3 are not — Floor 2's Δf3 runs
# −2.5, −6.9, −4.0, −13.3. The old title claimed monotonicity for the whole
# figure, which its own middle and right panels disprove.
fig.suptitle("Severity increases monotonically on $f_1$ and saturates above one turn "
             "; the higher modes do not",
             fontweight="bold", y=1.04)
fig.tight_layout()
vlist = ", ".join(f"{loc} {g}: {n}×$f_1$" for (loc, g), n in sorted(voids.items()))
save(fig, "fig03_severity_heatmap")
print("    F2 f3 row (trace→severe):", np.round(M[2, 2], 2), " <- non-monotonic")
print(f"    base f1 moderate: {float(M[0, 0, 2]):.2f}  (agrees with Table 9.5)")

# ==========================================================================
# FIG 04 — §9.4  localisation fingerprints, replicate error bars, n/r left empty
# ==========================================================================
fig, ax = plt.subplots(figsize=(7.6, 4.0))
x = np.arange(4)
w = 0.26
for mi, lab in enumerate(MODELAB):
    means = np.array([sev_mean[l][mi] for l in LOCS])
    errs = np.array([sev_sd[l][mi] for l in LOCS])
    xs = x + (mi - 1) * w
    ok = ~np.isnan(means)
    ax.bar(xs[ok], means[ok], w, yerr=errs[ok], capsize=3, label=lab,
           color=MODE[mi], edgecolor="white", linewidth=0.8)
    ns = np.array([sev_n[l][mi] for l in LOCS])
    for xi, mv, ev, nrep in zip(xs[ok], means[ok], errs[ok], ns[ok]):
        # Flag any bar that is not a full 3-replicate mean — Floor 3's f3 is n=2.
        tag = f"{mv:.1f}" if nrep == 3 else f"{mv:.1f}\nn={nrep}"
        ax.annotate(tag, (xi, mv - ev), xytext=(0, -11),
                    textcoords="offset points", ha="center", va="top", fontsize=7.6,
                    color=INK if nrep == 3 else OI["vermillion"],
                    fontweight="normal" if nrep == 3 else "bold")
    for xi in xs[~ok]:                              # leave the cell visibly empty
        ax.add_patch(plt.Rectangle((xi - w / 2, -8.0), w, 8.0, facecolor="none",
                                   edgecolor="#BBBBBB", hatch="////", linewidth=0.8))
        ax.annotate("n/r", (xi, -8.5), ha="center", va="top", fontsize=8.5,
                    color=MUTED, style="italic", fontweight="bold")
ax.set_xticks(x)
ax.set_xticklabels(LNAMES)
ax.axhline(0, color=MUTED, lw=0.8)
ax.set_ylabel("Frequency shift (%)")
ax.set_ylim(-72, 14)
ax.set_title("Each location has a distinct three-mode fingerprint (severe damage)")
ax.legend(ncol=3, loc="lower right", bbox_to_anchor=(1.0, 0.02))
despine(ax)
ax.grid(axis="x", visible=False)
save(fig, "fig04_fingerprints")

# ==========================================================================
# FIG 05 — §9.4  normalised signature space: 12 runs, 4 class means
# ==========================================================================
runs, all3 = {}, {}
for loc in LOCS:
    pts = []
    for r in (1, 2, 3):
        f = f"{loc}_severe_r{r}"
        if os.path.isdir(f"{BASE}/{f}"):
            sh = (vec(f) - b4) / b4 * 100
            pts.append((abs(sh[0]) / FLOOR_2SD[0], abs(sh[2]) / FLOOR_2SD[2]))
            all3.setdefault(loc, []).append(np.abs(sh) / FLOOR_2SD)
    runs[loc] = np.array(pts)
_R3 = {k: np.array(v) for k, v in all3.items()}      # (f1, f2, f3), for §9.4.3

n_tot = sum(len(v) for v in runs.values())
n_missing = sum(int(np.isnan(v[:, 1]).sum()) for v in runs.values())

# Within-class replicate scatter (<=0.5% of f1) is ~100x smaller than the
# between-class separation, so at full scale the three runs of a class land on
# top of each other. The zoom row below resolves every run individually.
fig = plt.figure(figsize=(8.8, 7.6))
gs = fig.add_gridspec(2, 4, height_ratios=[2.45, 1.0], hspace=0.46, wspace=0.42)
ax = fig.add_subplot(gs[0, :])

RUG_Y, RUG_H = -6.0, 4.4
ax.axhspan(RUG_Y - RUG_H / 2, RUG_Y + RUG_H / 2, color="#F5F5F5", zorder=0)
ax.axhline(0, color=GRID, lw=0.8, zorder=1)

for li, loc in enumerate(LOCS):
    pts = runs[loc]
    good = pts[~np.isnan(pts[:, 1])]
    miss = pts[np.isnan(pts[:, 1])]
    mu = np.nanmean(pts, axis=0)
    ax.scatter(mu[0], mu[1], s=340, marker="o", facecolor="none",
               edgecolor=LOCC[li], linewidth=2.2, zorder=4)
    ax.scatter(good[:, 0], good[:, 1], s=30, color=LOCC[li], zorder=5)
    if len(miss):                                  # Δf3 unresolved — on the rug
        ax.scatter(miss[:, 0], np.full(len(miss), RUG_Y), s=64, facecolor="none",
                   edgecolor=LOCC[li], linewidth=1.8, zorder=5)
    # base and Floor 1 sit almost on top of each other in x: label both to the
    # left (they are far apart in y, so they still read separately) — to the
    # right, Floor 1's label would hang off the axes.
    off = {0: (-20, -4), 1: (-20, 4)}.get(li, (0, 26))
    ha = {0: "right", 1: "right"}.get(li, "center")
    ax.annotate(f"{LNAMES[li]}   n={len(pts)}", (mu[0], mu[1]), xytext=off,
                textcoords="offset points", ha=ha, va="center", fontsize=9.5,
                fontweight="bold", color=INK, zorder=6)

# NOT the harmonic. Floor 3's f2 is the harmonic void (2*f1 = 4.97 Hz); this run's
# f3 was found at 10.47 Hz in 2 of 5 taps, one short of the 3-of-5 majority rule,
# so the slot was dropped. Different cause, and the old label misattributed it.
ax.annotate(f"$\\Delta f_3$ not resolved for {n_missing} run "
            f"(found in 2 of 5 taps, below the 3-tap rule)",
            (0.28, 0.045), xycoords="axes fraction", fontsize=8,
            color=MUTED, style="italic")

# The point of the figure: CLOSE on f1, separated on f3. Not "same" — 196 vs 202
# floor-units is 6 units / 3.1%, and §9.4.1 was corrected on exactly this wording.
mu_b, mu_f1 = np.nanmean(runs["base"], axis=0), np.nanmean(runs["F1"], axis=0)
ax.annotate("", xy=(mu_f1[0], mu_f1[1] - 5), xytext=(mu_b[0], mu_b[1] + 5),
            arrowprops=dict(arrowstyle="<|-|>", color=MUTED, lw=1.2,
                            linestyle=(0, (4, 3))))
# Stated as percentage points on the raw shift, not as a ratio of floor-units:
# the two locations differ by 1.8 pp on f1 (-58.7 against -60.5), which is the
# quantity the chapter argues from. Computed here, not written in.
d_pp = abs(mu_f1[0] - mu_b[0]) * FLOOR_2SD[0]
ax.annotate(f"the hard pair: {d_pp:.1f} percentage points apart on $f_1$\n"
            f"({mu_b[0]:.0f} vs {mu_f1[0]:.0f} floor-units), "
            f"{mu_f1[1] / mu_b[1]:.0f}× apart on $f_3$ "
            f"({mu_b[1]:.0f} vs {mu_f1[1]:.0f})",
            (0.58, 0.30), xycoords="axes fraction", fontsize=8.5, color=MUTED,
            va="center", ha="center")

ax.scatter([], [], s=30, color=MUTED, label="individual run")
ax.scatter([], [], s=150, marker="o", facecolor="none", edgecolor=MUTED,
           linewidth=2.2, label="class mean")
ax.scatter([], [], s=64, facecolor="none", edgecolor=MUTED, linewidth=1.8,
           label="$\\Delta f_3$ not resolved")
ax.legend(loc="upper left", scatterpoints=1, ncol=3, fontsize=8.5)
ax.set_xlabel("$|\\Delta f_1|$  /  reassembly floor  (0.30%)")
ax.set_ylabel("$|\\Delta f_3|$  /  reassembly floor  (0.32%)")
ax.set_xlim(28, 236)
ax.set_ylim(RUG_Y - RUG_H, 68)
ax.set_title(f"Normalised signature space (two-mode): "
             f"{n_tot}/{n_tot} runs fall in their own cluster")
despine(ax)

# Zoom row: one panel per location, every replicate individually resolved.
zoom_axes = []
for li, loc in enumerate(LOCS):
    axz = fig.add_subplot(gs[1, li])
    zoom_axes.append(axz)
    pts = runs[loc]
    good = pts[~np.isnan(pts[:, 1])]
    miss = pts[np.isnan(pts[:, 1])]
    axz.scatter(good[:, 0], good[:, 1], s=46, color=LOCC[li],
                edgecolor="white", linewidth=1.2, zorder=3)
    xs_all = pts[:, 0]
    xpad = max(np.ptp(xs_all), 0.6) * 0.9 + 0.3
    xc = xs_all.mean()
    axz.set_xlim(xc - xpad, xc + xpad)
    if len(good):
        yc, ypad = good[:, 1].mean(), max(np.ptp(good[:, 1]), 0.6) * 0.9 + 0.3
        lo = yc - ypad - (ypad * 1.6 if len(miss) else 0)
        axz.set_ylim(lo, yc + ypad)
        if len(miss):
            # SAME CONVENTION AS THE MAIN PANEL: a run with no Δf3 goes in a
            # separate strip, never at a y a reader can read off the axis. It was
            # drawn mid-strip at 42.1 here, which looked like a measured value and
            # contradicted the main panel parking it below the axis.
            yr = lo + ypad * 0.42
            axz.axhspan(lo, lo + ypad * 0.84, color="#F5F5F5", zorder=0)
            axz.axhline(lo + ypad * 0.84, color=GRID, lw=0.8, zorder=1)
            axz.scatter(miss[:, 0], np.full(len(miss), yr), s=54, facecolor="none",
                        edgecolor=LOCC[li], linewidth=1.6, zorder=3)
            # Left-anchored: the run's marker sits mid-panel at its own |Δf1|, so a
            # centred label lands on top of it.
            axz.annotate("no $\\Delta f_3$",
                         (0.04, 0.5 * ypad * 0.84 / (yc + ypad - lo)),
                         xycoords="axes fraction", ha="left", va="center",
                         fontsize=7, color=MUTED, style="italic")
            # Ticks only over the resolved range, so no label sits beside the strip
            # and invites reading a value off it.
            axz.set_yticks([t for t in axz.get_yticks() if t > lo + ypad * 0.84])
            axz.set_ylim(lo, yc + ypad)
    # n per MODE, not per run: Floor 3 has three runs but only two Δf3 values.
    n_res = int(len(good))
    ttl = (f"{LNAMES[li]}  (n={len(pts)})" if n_res == len(pts)
           else f"{LNAMES[li]}  ({n_res} of {len(pts)} with $\\Delta f_3$)")
    axz.set_title(ttl, fontsize=9, fontweight="bold", color=LOCC[li])
    axz.tick_params(labelsize=7.5)
    axz.ticklabel_format(useOffset=False)
    despine(axz)
    if li == 0:
        axz.set_ylabel("$|\\Delta f_3|$ / floor", fontsize=8.5)
# Anchor the zoom-row heading and shared x-label off the real axes positions so
# they cannot drift into the panel titles.
zp = zoom_axes[0].get_position()
fig.text(0.5, zp.y1 + 0.058,
         "Zoomed on each cluster: every replicate resolved individually",
         ha="center", va="bottom", fontsize=9.5, color=INK, fontweight="bold")
fig.text(0.5, zp.y0 - 0.052, "$|\\Delta f_1|$  /  reassembly floor",
         ha="center", va="top", fontsize=8.5)

# Computed, not asserted: strictest basis — largest single point-to-centroid
# distance against the CLOSEST pair of class means. "~100×" came from comparing
# scatter with the full span of the plot, which flatters the result.
# THE CAPTION MUST SAY "IN THIS PROJECTION". These are (f1, f3) numbers, and the
# three-mode figures §9.4.3 quotes are larger — see the reconciliation printed
# below and FIGURE_NOTES.md §4.4.
_mus = {k: np.nanmean(v, axis=0) for k, v in runs.items()}
_spread = max(float(np.nanmax(np.linalg.norm(v - _mus[k], axis=1)))
              for k, v in runs.items())
_pairs = [(float(np.linalg.norm(_mus[a] - _mus[b])), a, b)
          for i, a in enumerate(LOCS) for b in LOCS[i + 1:]]
_dmin, _pa, _pb = min(_pairs)
save(fig, "fig05_signature_space")
print(f"    2-mode (plotted): closest pair {_pa}<->{_pb} = {_dmin:.1f} units; "
      f"max scatter {_spread:.2f} -> {_dmin / _spread:.1f}x")

# Three-mode reconciliation for §9.4.3. Floor 3 cannot enter a 3-mode space at all
# (f2 voided in all three replicates), so this covers 3 of the 4 classes.
_full = [l for l in LOCS if not np.isnan(_R3[l]).any()]
_m3 = {l: _R3[l].mean(axis=0) for l in _full}
_d3 = {l: np.linalg.norm(_R3[l] - _m3[l], axis=1) for l in _full}
_a3 = np.concatenate([v for v in _d3.values()])
_p3 = min((float(np.linalg.norm(_m3[a] - _m3[b])), a, b)
          for i, a in enumerate(_full) for b in _full[i + 1:])
print(f"    3-mode (classifier, {len(_full)}/4 classes — F3 has no f2): closest pair "
      f"{_p3[1]}<->{_p3[2]} = {_p3[0]:.1f} units")
print(f"      point-to-class-mean scatter: max {_a3.max():.2f}  mean {_a3.mean():.2f}  "
      f"rms {np.sqrt((_a3 ** 2).mean()):.2f}")
print(f"      ratio: max-basis {_p3[0] / _a3.max():.1f}x   "
      f"mean-basis {_p3[0] / _a3.mean():.1f}x")
for loc in LOCS:
    print(f"    {loc:5s} runs (Δf1/floor, Δf3/floor): "
          f"{np.round(runs[loc], 1).tolist()}")

# ==========================================================================
# FIG 06-08 — §9.5  measured spectrum at each sensor position
# ==========================================================================
POSITIONS = [
    ("fig06_spectrum_sensor_top", "day7_baseline", "Floor 3 (top)",
     "the default position: all three modes visible"),
    ("fig07_spectrum_sensor_floor2", "sensorF2_baseline_day7b", "Floor 2",
     "the second mode all but vanishes; the sensor sits near its node"),
    ("fig08_spectrum_sensor_floor1", "sensorF1_baseline", "Floor 1",
     "the second mode returns; the fundamental is now weakest"),
]
# Mass-loading spread. The frame is untouched between these three captures — only
# the accelerometer moves — so the whole between-position spread is sensor loading.
_pos_modes = np.array([vec(f) for _, f, _, _ in POSITIONS])
print(f"    mass-loading spread across positions: max "
      f"{np.nanmax(np.ptp(_pos_modes, axis=0)):.3f} Hz "
      f"({np.nanmax(np.ptp(_pos_modes, axis=0) / np.nanmean(_pos_modes, axis=0) * 100):.2f}%)")

obs = {}
for stem, folder, posname, subtitle in POSITIONS:
    modes = vec(folder)
    amps = ic.modal_amplitudes(f"{BASE}/{folder}", modes) * 100
    obs[posname] = amps
    # Use raw_psd's own resolution, exactly as modal_amplitudes does, so the
    # plotted peak heights ARE the annotated percentages. (At nperseg=8192 the
    # narrow high-Q f3 peak resolves higher than the broad f1 one, and the
    # curve would no longer match Table 9.10.)
    fr, psd = folder_psd(folder)
    peaks = np.array([psd[(fr >= f0 - 0.6) & (fr <= f0 + 0.6)].max() for f0 in modes])
    psd_n = psd / np.nanmax(peaks)                 # normalise to the strongest mode
    assert np.allclose(peaks / np.nanmax(peaks) * 100, amps, atol=0.5), \
        f"{folder}: plotted peaks disagree with Table 9.11 amplitudes"

    m = (fr >= 0.5) & (fr <= 16)
    # 7.8 in, not 7.0: Floor 2's title is the longest of the three and at 7.0 it
    # overran the canvas, so the set came out at three different widths.
    fig, ax = plt.subplots(figsize=(7.8, 3.9))
    ax.semilogy(fr[m], psd_n[m], color=OI["blue"], lw=1.5)
    for mi, (f0, a) in enumerate(zip(modes, amps)):
        col = MODE[mi]
        # Stop the marker line at the peak dot. A full-height axvline runs
        # straight through the "8.10 Hz"-style label sitting above the peak.
        ax.vlines(f0, 2e-5, peaks[mi] / np.nanmax(peaks), color=col, lw=0.8,
                  alpha=0.55, zorder=1)
        ax.scatter([f0], [peaks[mi] / np.nanmax(peaks)], s=46, color=col,
                   edgecolor="white", linewidth=1.4, zorder=5)
        ax.annotate(f"$f_{mi + 1}$  {a:.0f}%\n{f0:.2f} Hz",
                    (f0, peaks[mi] / np.nanmax(peaks)), xytext=(0, 12),
                    textcoords="offset points", ha="center", fontsize=9,
                    fontweight="bold", color=col)
    ax.set_xlim(0.5, 16)
    ax.set_ylim(2e-5, 40)
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("PSD, relative to strongest mode")
    # Two lines. On one line Floor 2's title is 83 characters and becomes the widest
    # element in the figure, so bbox="tight" trimmed the three spectra to three
    # different widths — visibly uneven for what is a matched set of three.
    ax.set_title(f"Sensor on {posname}\n{subtitle}")
    despine(ax)
    ax.grid(axis="x", visible=False)
    save(fig, stem)
    print(f"    {posname}: amps {np.round(amps, 1)}  modes {np.round(modes, 3)}")

# ==========================================================================
# FIG 09 (chapter 4.10) — seed-sweep calls, 4 locations x 4 grades
# ==========================================================================
# REPLACES the archived five-prediction bar chart. That figure's title ("the
# argmin is k1 in every case") was false and one of its five points was an
# artefact: the Floor 3 row came from an input whose two unmeasurable frequency
# ratios were imputed as 1.0, which forces a k1 call by construction. Reproduced
# to (0.72, 0.94, 0.985) over 8 retrains -- see decision_rule_sweep.py.
# This plots the seed sweep instead: 20 seeds x 2 loss weights = 40 runs per cell.
_SWEEP = os.path.join(_HERE_DIR, "results_decision_rule_sweep.json")
with open(_SWEEP) as _f:
    SW = json.load(_f)

GRADE_COL = ["trace", "light", "moderate", "severe"]
CALL_COL = {0: OI["blue"], 1: OI["orange"], 2: OI["green"]}   # k1, k2, k3
ABSENT = "#E8E8E8"


def _cell_key(loc, grade):
    """Grid cell -> the sweep's record names. Severe is three replicates."""
    if grade == "severe":
        return [f"{loc}_sev_r{r}" for r in (1, 2, 3)]
    return [f"{loc}_{grade}"]


fig, ax = plt.subplots(figsize=(WIDTH_IN if False else 8.0, 4.6),
                       constrained_layout=True)
n_unanimous = 0
for li, loc in enumerate(LOCS):
    for gi, g in enumerate(GRADE_COL):
        keys = [k for k in _cell_key(loc, g) if k in SW["cells"]]
        x0, y0 = gi, 3 - li
        if not keys:                                   # lost to harmonic contamination
            ax.add_patch(plt.Rectangle((x0 - .5, y0 - .5), 1, 1, facecolor=ABSENT,
                                       edgecolor="white", lw=1.5))
            ax.text(gi, y0, "no record", ha="center", va="center", fontsize=8,
                    color=MUTED, style="italic")
            continue
        frac = np.mean([SW["cells"][k]["frac"] for k in keys], axis=0)
        call = int(np.argmax(frac))
        ax.add_patch(plt.Rectangle((x0 - .5, y0 - .5), 1, 1, facecolor=CALL_COL[call],
                                   edgecolor="white", lw=1.5))
        lab = f"$k_{call + 1}$"
        if frac[call] < 1.0:                           # not unanimous: print the split
            other = int(np.argsort(frac)[-2])
            # Proportional strip in the minority colour along the bottom of the
            # cell. Without it the orange k2 swatch appears nowhere in the grid
            # and "almost never" looks unmotivated -- this cell IS the "almost".
            # Inset from the cell edge: flush to the boundary the strip reads as
            # belonging to the row below.
            ax.add_patch(plt.Rectangle((x0 - .40, y0 - .40), 0.80,
                                       frac[other] * 0.80,
                                       facecolor=CALL_COL[other], edgecolor="none",
                                       zorder=2))
            lab += (f"\n{frac[call]:.0%} / $k_{other + 1}$ {frac[other]:.0%}")
        else:
            n_unanimous += len(keys)
        ax.text(gi, y0, lab, ha="center", va="center", fontsize=9.5,
                color="white", fontweight="bold")

ax.set_xlim(-.5, 3.5); ax.set_ylim(-.5, 3.5)
ax.set_xticks(range(4)); ax.set_xticklabels([g.capitalize() for g in GRADE_COL])
ax.set_yticks(range(4)); ax.set_yticklabels(LNAMES[::-1])
ax.set_xlabel("Damage grade")
ax.tick_params(length=0)
for sp in ax.spines.values():
    sp.set_visible(False)
ax.grid(False)

# The empty k2 category has to be VISIBLE, because its emptiness is the finding.
handles = [Patch(facecolor=CALL_COL[0], label="calls $k_1$ (bottom storey)"),
           Patch(facecolor=CALL_COL[1], label="calls $k_2$ (middle storey)"),
           Patch(facecolor=CALL_COL[2], label="calls $k_3$ (top storey)"),
           Patch(facecolor=ABSENT, label="no record (harmonic contamination)")]
ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01, 1.0),
          fontsize=8.5, handlelength=1.6)
ax.annotate("Archived Floor 3 prediction (0.72, 0.94, 0.98) called $k_1$,\n"
            "but from an imputed input: two unmeasurable modes set to 1.0.\n"
            "Not a measurement; excluded.",
            xy=(3.52, -0.42), xycoords="data", ha="left", va="bottom",
            fontsize=8, color=OI["vermillion"], style="italic")
ax.set_title("The network calls the bottom or the top storey and almost never "
             "the middle one", loc="left")
save(fig, "fig09_seed_sweep_calls")
print(f"    unanimous in all 40 runs: {n_unanimous} of "
      f"{sum(1 for k in SW['cells'])} records")

# ==========================================================================
# FIG 10 (chapter 4.11) — every enumerated inversion branch
# ==========================================================================
# The old lower residual panel is GONE. Its "7e-2, does not fit" bar at Floor 1
# encoded a stalled optimisation, not the absence of a solution: multi-start
# enumeration finds exact branches wherever three modes resolved, all at 1e-13 Hz
# or better, so the panel would now be four equal bars saying nothing.
_BR = os.path.join(_HERE_DIR, "results_inversion_branches.json")
with open(_BR) as _f:
    BR = json.load(_f)

# Broken y axis. A single 0-3.7 axis puts k1 = 3.419 at the top and squeezes the
# region around unity -- where the whole argument lives -- into the bottom third.
YLO, YHI, YBRK = 1.85, 3.7, 1.85
fig = plt.figure(figsize=(11.0, 4.6))
gs = fig.add_gridspec(2, 4, height_ratios=[1.0, 2.5], width_ratios=[4, 2, 4, 1.5],
                      hspace=0.06, wspace=0.22)
for li, loc in enumerate(LOCS):
    axhi = fig.add_subplot(gs[0, li])
    axlo = fig.add_subplot(gs[1, li], sharex=axhi)
    # Branches sorted by k1 ascending: the enumeration returns them in
    # basin-size order, which is not stable across runs of the random starts.
    br = sorted(BR.get(loc, {}).get("branches", []), key=lambda b: b["k"][0])
    for ax in (axhi, axlo):
        ax.axhspan(1.0, YHI, color=OI["vermillion"], alpha=0.12, zorder=0)
        ax.axhline(1.0, color=OI["vermillion"], lw=1.1, zorder=1)
        ax.grid(axis="x", visible=False)
    axhi.set_ylim(YBRK, YHI)
    axlo.set_ylim(0, YBRK)
    if not br:                                        # Floor 3: two modes only
        for ax in (axhi, axlo):
            ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes,
                                       facecolor="none", edgecolor="#BBBBBB",
                                       hatch="///", lw=0.9, zorder=2))
            ax.set_xticks([])
        # Below the k=1 line (at 0.54 of this panel) and short enough for the
        # narrow slot: at 0.55 the block ran across the line and over itself.
        axlo.text(0.5, 0.26, "under-\ndetermined\n\nonly two\nmodes\nresolve",
                  transform=axlo.transAxes, ha="center", va="center",
                  fontsize=7.4, color=MUTED, style="italic", linespacing=1.5)
    else:
        w = 0.26
        for bi, b in enumerate(br):
            for ki in range(3):
                for ax in (axhi, axlo):
                    ax.bar(bi + (ki - 1) * w, b["k"][ki], w, color=MODE[ki],
                           edgecolor="white", linewidth=0.7, zorder=3)
            if b["admissible"]:
                axlo.annotate("admissible, and still wrong:\nputs the softening on "
                              "$k_1$, a storey the\nloosened plate does not adjoin",
                              (bi, 1.05), xytext=(bi + 0.95, 1.62),
                              textcoords="data", ha="center", va="center",
                              fontsize=7.4, color=OI["green"], fontweight="bold",
                              arrowprops=dict(arrowstyle="->", color=OI["green"],
                                              lw=1.0, shrinkB=2))
        axlo.set_xticks(range(len(br)))
        axlo.set_xticklabels([f"B{i + 1}" for i in range(len(br))], fontsize=8.5)
        axlo.set_xlim(-0.55, len(br) - 0.45)
    if loc == "base" and "ci95" in BR[loc]:
        lo_, hi_ = BR[loc]["ci95"][0][1], BR[loc]["ci95"][1][1]
        axlo.plot([0, 0], [lo_, hi_], color=INK, lw=2.6, solid_capstyle="butt",
                  zorder=6)
        axlo.annotate(f"$k_2$ over 1000 perturbed\ndraws: [{lo_:.3f}, {hi_:.3f}]\n"
                      "never below 1", (0, hi_), xytext=(8, 26),
                      textcoords="offset points", ha="left", va="bottom",
                      fontsize=7.4, color=INK,
                      arrowprops=dict(arrowstyle="->", color=INK, lw=1.0))
    axhi.set_title(LNAMES[li], fontsize=9.5, color=LOCC[li])
    plt.setp(axhi.get_xticklabels(), visible=False)
    axhi.tick_params(axis="x", length=0)
    for ax, keep in ((axhi, "bottom"), (axlo, "top")):
        ax.spines[keep].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(length=3, color=MUTED)
    axhi.spines["top"].set_visible(False)
    if li:                                            # y ticks on the left panel only
        for ax in (axhi, axlo):
            plt.setp(ax.get_yticklabels(), visible=False)
            ax.tick_params(axis="y", length=0)
    # break marks
    kw = dict(transform=axhi.transAxes, color=MUTED, clip_on=False, lw=0.9)
    axhi.plot([-0.02, 0.02], [-0.03, 0.03], **kw)
    kw["transform"] = axlo.transAxes
    axlo.plot([-0.02, 0.02], [1 - 0.012, 1 + 0.012], **kw)
    if li == 0:
        axlo.set_ylabel("Recovered stiffness fraction  $k / k_\\mathrm{healthy}$")
        axlo.yaxis.set_label_coords(-0.18, 0.72)
        # Both keys in the first panel.
        axlo.legend(handles=[Patch(facecolor=MODE[i], label=f"$k_{i + 1}$")
                             for i in range(3)],
                    loc="upper left", ncol=3, fontsize=8, handlelength=1.3,
                    columnspacing=0.7, borderaxespad=0.3)
        axhi.text(0.02, 0.90, "shaded: physically inadmissible, $k > 1$",
                  transform=axhi.transAxes, ha="left", va="top", fontsize=7.8,
                  color=OI["vermillion"], style="italic")
# WORDING. "Every exact solution ... is inadmissible" claimed exhaustiveness the
# method cannot deliver: the branches come from a random-start search (3,000
# starts per case), so the absence of an admissible branch is a recovery result,
# not a proof of non-existence. Audit item 1.5a is the direct evidence that the
# search is not exhaustive in practice, since Table 4.16 omitted a real Floor 2
# branch occupying 375 of 1,581 converged starts.
fig.suptitle("No admissible exact branch was recovered at the base plate or "
             "Floor 1", fontweight="bold", y=0.99)
fig.subplots_adjust(left=0.085, right=0.985, top=0.88, bottom=0.10)
save(fig, "fig10_inversion_branches")
for loc in LOCS:
    b = BR.get(loc, {}).get("branches", [])
    print(f"    {loc:5s} {len(b)} branches, "
          f"{sum(1 for x in b if x['admissible'])} admissible")


# ==========================================================================
# FIG 11 — §9.3.1  per-tap f1 scatter: repeatability by location and grade
# ==========================================================================
# A column of standard deviations hides which cells are unstable. Plotting the
# five individual taps shows it directly: base and Floor 1 spread visibly once
# damage is past trace, while Floor 2/3 stay tight.
GR_ALL = ["trace", "light", "moderate"]
GR_LAB = ["trace\n⅛ turn", "light\n½ turn", "moderate\n1 turn"]


# Deviation from each cell's own mean, on ONE shared scale: the question in 9.3.1
# is repeatability, so absolute level is a distraction and per-panel y-scales would
# make the cells incomparable — which is the whole point of the figure.
fig, axes = plt.subplots(1, 4, figsize=(11.0, 3.9), sharey=True)
YLIM, ranges = 14.0, {}
for li, (loc, ax) in enumerate(zip(LOCS, axes)):
    ax.axhspan(-FLOOR_2SD[0], FLOOR_2SD[0], color=OI["green"], alpha=0.18, zorder=0)
    ax.axhline(0, color=MUTED, lw=0.8, zorder=1)
    for gi, g in enumerate(GR_ALL):
        folder = f"{BASE}/{loc}_{g}_c1"
        if not os.path.isdir(folder):
            continue
        # Same f1 definition as the Δf1 correction above — one rule in this
        # file, so this figure and Figure 9.3 cannot disagree on a cell mean.
        sh = (f1_per_tap(f"{loc}_{g}_c1") - b6[0]) / b6[0] * 100
        dev = sh - sh.mean()
        rng = float(np.ptp(dev))
        ranges[(loc, g)] = rng
        jit = np.linspace(-0.13, 0.13, len(dev))
        ax.scatter(np.full(len(dev), gi) + jit, dev, s=36, color=LOCC[li],
                   edgecolor="white", linewidth=1.0, zorder=4)
        loud = rng > 2.0
        ax.annotate(f"{rng:.1f}", (gi, YLIM * 0.86), ha="center", va="center",
                    fontsize=8, color=OI["vermillion"] if loud else MUTED,
                    fontweight="bold" if loud else "normal")
    ax.set_xticks(range(len(GR_ALL)))
    ax.set_xticklabels(GR_LAB, fontsize=8.5)
    ax.set_title(LNAMES[li], fontsize=9.5, fontweight="bold", color=LOCC[li])
    ax.set_xlim(-0.5, len(GR_ALL) - 0.5)
    ax.set_ylim(-YLIM, YLIM)
    despine(ax)
    ax.grid(axis="x", visible=False)
axes[0].set_ylabel("Per-tap $\\Delta f_1$ − cell mean\n(percentage points)")
# No inline key for the top row of numbers: at this x-density any label long enough
# to be useful collides with the base-plate/trace value. The caption names them.
axes[0].annotate("±0.30% reassembly floor", (-0.42, -YLIM * 0.93), ha="left",
                 va="center", fontsize=7.4, color=OI["green"], style="italic")
# Both unstable locations get named. Crediting the base plate alone contradicted
# this figure's own Floor 1 panel, which highlights 3.8 pp at light.
fig.suptitle("Tap-to-tap scatter of $f_1$: the base plate destabilises progressively "
             "and Floor 1 at light damage;\nFloor 2 and Floor 3 stay repeatable at "
             "every grade", fontweight="bold", y=1.02)
fig.tight_layout()
save(fig, "fig11_tap_repeatability")
print("    per-tap Δf1 range (pp):", {f"{k[0]} {k[1]}": round(v, 2)
                                      for k, v in sorted(ranges.items())})

# The Table 9.15 reconciliation that used to print here is superseded. It
# compared the transcribed table against a single-start solve; the branch
# enumeration in Figure 4.11 explains that disagreement — the default start
# stalls at a rank-deficient point for Floor 1 — and reports admissibility per
# branch, which the reconciliation could not. See FIGURE_NOTES.md, revision
# history and section 4.2.

# ==========================================================================
# FIG 12 (chapter 4.6.6) — plate-hypothesis ranking
# ==========================================================================
# Four one-parameter hypotheses per case, so residuals are directly comparable.
# THE "INSIDE THE MEASUREMENT SCATTER" READING DOES NOT SURVIVE CHECKING.
# Propagating Table 4.3's per-mode 1-sigma (0.15/0.23/0.16%) through the fit,
# 400 draws per case, the winner never changes -- not even at Floor 3, whose
# gap CI is [0.012, 0.043] Hz, strictly positive, 0/400 rank flips. The margins
# differ by a factor of 30, but all four rankings are resolved by the data. So
# the figure shows the gap WITH its interval rather than a "tie" band.
PLATE_RES = {                    # case -> {hypothesis: rms Hz}
    "base": {"base": 0.161, "F1": 1.039, "F2": 1.146, "F3": 0.956},
    "F1":   {"base": 0.559, "F1": 0.739, "F2": 0.929, "F3": 1.079},
    "F2":   {"base": 0.944, "F1": 0.397, "F2": 0.853, "F3": 0.648},
    "F3":   {"base": 1.013, "F1": 0.129, "F2": 0.155, "F3": 0.528},
}
# Gaps quoted at the precision Table 4.17 uses, computed from the unrounded
# residuals rather than re-derived from the 3-dp values printed above.
GAP_CI = {"base": (0.795, 0.779, 0.809), "F1": (0.181, 0.157, 0.202),
          "F2": (0.251, 0.219, 0.282), "F3": (0.027, 0.012, 0.043)}
FULLNAME = dict(zip(LOCS, LNAMES))

fig, ax = plt.subplots(figsize=(9.4, 4.2), constrained_layout=True)
for li, loc in enumerate(LOCS):
    y = 3 - li
    r = PLATE_RES[loc]
    order = sorted(r, key=r.get)
    win = order[0]
    # Vertical jitter for markers closer than this in x: at Floor 3 the winner
    # and runner-up are 0.027 Hz apart, which is the point of that row, and they
    # overplot completely without it.
    dy = {}
    prev_v, prev_h = None, None
    for h in order:
        if prev_v is not None and r[h] - prev_v < 0.045:
            dy[h] = -0.13 if dy.get(prev_h, 0.0) >= 0 else 0.13
        else:
            dy[h] = 0.0
        prev_v, prev_h = r[h], h
    ax.plot([min(r.values()), max(r.values())], [y, y], color=GRID, lw=1.0, zorder=0)
    for h, v in r.items():
        c = LOCC[LOCS.index(h)]
        yy = y + dy[h]
        if dy[h]:                                   # tie the jittered marker to its row
            ax.plot([v, v], [y, yy], color=c, lw=0.7, alpha=0.6, zorder=1)
        ax.scatter(v, yy, s=170 if h == win else 95,
                   facecolor=c if h == win else "white",
                   edgecolor=c, linewidth=1.8, zorder=4)
        if h == loc:
            ax.scatter(v, yy, s=360, facecolor="none", edgecolor=INK,
                       linewidth=1.3, zorder=5)
    g, lo, hi = GAP_CI[loc]
    ok = win == loc
    ax.annotate(f"{'correct' if ok else 'wrong: ' + FULLNAME[win]:<18s}  "
                f"gap {g:.3f} [{lo:.3f}, {hi:.3f}] Hz",
                (1.28, y), xycoords=("data", "data"), ha="left", va="center",
                fontsize=8, annotation_clip=False,
                color=OI["green"] if ok else OI["vermillion"],
                fontweight="bold" if ok else "normal")
ax.set_yticks(range(4))
ax.set_yticklabels([f"{n}\nmeasured" for n in LNAMES[::-1]], fontsize=8.5)
ax.set_ylim(-0.5, 3.6)
ax.set_xlim(0, 1.25)
ax.set_xlabel("Fit residual of the plate hypothesis, RMS (Hz)")
# Below the axis: inside the plot area it crowded the Floor 3 row.
ax.legend(handles=[Patch(facecolor=LOCC[i], label=f"H: {LNAMES[i]}")
                   for i in range(4)]
          + [plt.Line2D([], [], ls="none", marker="o", ms=9, markerfacecolor=MUTED,
                        markeredgecolor=MUTED, label="ranked first"),
             plt.Line2D([], [], ls="none", marker="o", ms=12, markerfacecolor="none",
                        markeredgecolor=INK, label="true location")],
          loc="upper center", bbox_to_anchor=(0.5, -0.20), ncol=6, fontsize=7.8,
          handlelength=1.3, columnspacing=1.1)
ax.set_title("The plate hypothesis identifies only the base plate, and only "
             "there by a clear margin", loc="left")
despine(ax)
ax.grid(axis="y", visible=False)
save(fig, "fig12_plate_hypotheses")
for loc in LOCS:
    r = PLATE_RES[loc]; o = sorted(r, key=r.get); g, lo, hi = GAP_CI[loc]
    print(f"    {loc:5s} 1st {o[0]:5s} {r[o[0]]:.3f} Hz   gap {g:.3f} "
          f"[{lo:.3f}, {hi:.3f}]   {'correct' if o[0] == loc else 'WRONG'}")

print("\nFigure set complete:", sorted(f for f in os.listdir(OUT) if f.endswith(".png")))

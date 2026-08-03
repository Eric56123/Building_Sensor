"""
make_ch8_figures.py — Chapter 8 figures 8.3, 8.4 and 8.5
========================================================
Regenerates all three Chapter 8 figures from the forward model at run time, and
cross-checks the numbers Section 8.6.3 quotes. Nothing here reads
shm_benchmark_data.npy, data/, or any .npy or .pth file, so it works on a clean
checkout.

    python -m four_floor.make_ch8_figures        # from the repository root
    python four_floor/make_ch8_figures.py        # also works

RANDOM SEED = 42 throughout (SEED below). generate_excitation() seeds numpy's
legacy global RNG internally; the sensor-noise draw uses an explicit
default_rng(SEED + 500_000), matching simulation/generate_dataset.py exactly.
Figure 8.5 is fully deterministic — nothing in it is stochastic.

OUTPUTS (into four_floor/figures/)
    fig8_3_damping_verification.pdf / .png
    fig8_4_preprocessing_chain.pdf / .png
    fig8_5_physics_residual.pdf / .png

WHERE THE CODE DOES NOT SUPPORT THE DRAFT CAPTIONS — all printed at the end of
a run, each explained where it arises:
  1. Fig 8.3: only the four y-direction DOFs participate in mode 1. The eight
     x and rotation DOFs are stationary (|phi| ~ 1e-17), so "all degrees of
     freedom share this envelope" cannot be verified for them.
  2. Fig 8.4: the y-direction modes are 9.42 / 25.60 / 38.85 / 48.37 Hz. Only
     ONE is below 20 Hz, so a 0-20 Hz axis shows a single peak while the
     caption says "peaks". FMAX is set to 30 Hz for that reason.
  3. Fig 8.5: the Frobenius residual varies by 7.41%, not 2.7%, and the
     singular-value ratio by 100%, not 99.6%. The Frobenius residual is also
     strictly MONOTONE in k_hat_1 — its minimum is at the lower bound, not at
     the true value — which is a stronger result than "almost no gradient".
"""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import welch, hilbert

# The simulation modules import each other as `four_floor.*`, so the repository
# root has to be importable regardless of where this is run from.
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

from four_floor.simulation.matrices import k_set, m_set                # noqa: E402
from four_floor.simulation.damping import damping_matrix               # noqa: E402
from four_floor.simulation.excitation import (                         # noqa: E402
    newmark_beta, generate_excitation, D, dt, duration)
from four_floor.preprocessing.cleaning import sanitize_accelerometer_data  # noqa: E402
from four_floor.preprocessing.normalisation import PSDScaler           # noqa: E402
from four_floor.config import FS, NPERSEG, NORM_MIN, NORM_MAX          # noqa: E402

SEED = 42

# Constants the dataset was built with — simulation/generate_dataset.py.
CHUNK_SIZE = 4000
Y_DOFS = [1, 4, 7, 10]
FORCE_INTENSITY = 150.0
NOISE_RATIO = 0.10
DAMPING_RATIO = 0.01

# DOF ordering is per-floor [x1,y1,th1, x2,y2,th2, ...].
X_DOFS = [0, 3, 6, 9]
TH_DOFS = [2, 5, 8, 11]
TRANSLATIONAL = sorted(X_DOFS + Y_DOFS)

DECAY_SECONDS = 10.0
FIT_WINDOW = (0.5, 8.0)      # s, avoids the Hilbert transform's edge transients
ZETA_TOLERANCE = 0.05        # abort if the recovered zeta is >5% off the target

# Panels (b)-(d) of Fig 8.4 are truncated to this frequency.
# 20.0 was requested, on the grounds that all modes sit below it. They do not:
# the y sensors see 9.42 / 25.60 / 38.85 / 48.37 Hz, and the 25.60 Hz mode is
# only 0.58 decades below the fundamental. At 20 Hz the figure shows one peak
# and contradicts its own caption. Above 30 Hz the response really is flat —
# the next mode is >3 decades down — so 30 Hz keeps the axis tight AND honest.
FMAX = 30.0

OUT = os.path.join(_HERE, "figures")
os.makedirs(OUT, exist_ok=True)

# --------------------------------------------------------------------------
# Style — matches the TikZ figures in the chapter
# --------------------------------------------------------------------------
BLUE, GREEN, AMBER, PURPLE, RED = "#4C78A8", "#54A24B", "#E4913B", "#8C6BB1", "#B5495B"
GRID, INK, MUTED = "#D9D9D9", "#222222", "#666666"

MM = 1.0 / 25.4
WIDTH_IN = 150 * MM          # 150 mm, sits at \textwidth

# Saved at native size (no bbox="tight"), so the PDF really is 150 mm wide and
# these point sizes are the point sizes on the page. Nothing is below 8 pt.
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9,
    "axes.labelsize": 9, "axes.titlesize": 9,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
    "axes.edgecolor": MUTED, "axes.linewidth": 0.7,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5,
    "axes.axisbelow": True,
    "xtick.color": INK, "ytick.color": INK, "text.color": INK,
    "axes.labelcolor": INK,
    "legend.frameon": False,
    "figure.dpi": 200, "savefig.dpi": 200,
    "savefig.facecolor": "white", "figure.facecolor": "white",
    "pdf.fonttype": 42,      # embed TrueType, so the PDF has selectable text
})


def despine(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=3, color=MUTED)


def save(fig, stem):
    pdf, png = f"{OUT}/{stem}.pdf", f"{OUT}/{stem}.png"
    fig.savefig(pdf)                       # vector, native size
    fig.savefig(png, dpi=200)
    plt.close(fig)
    w_mm = fig.get_figwidth() / MM
    print(f"  wrote {stem}.pdf / .png   ({w_mm:.1f} mm wide)")


# --------------------------------------------------------------------------
# Newmark-beta with initial conditions
# --------------------------------------------------------------------------
def newmark_beta_free_decay(M, C, K, u0, v0, n_steps, dt_, beta=0.25, gamma=0.5):
    """Newmark-beta from a non-zero initial state.

    WHY THIS IS NOT simulation.excitation.newmark_beta. That function allocates
    u and v as zeros and never writes u[:, 0] or v[:, 0], so its initial state
    is identically zero and it is driven purely by F. With F = 0 it returns an
    all-zero response, which is no use for a free-decay test — there is no way
    to inject an initial displacement through its signature.

    The recurrence below is copied verbatim from that function; the only
    difference is that u[:, 0] and v[:, 0] are seeded before a[:, 0] is formed.
    Same scheme, same beta and gamma, so this still verifies the C that the
    repository builds, integrated the way the repository integrates.
    """
    n = M.shape[0]
    u = np.zeros((n, n_steps))
    v = np.zeros((n, n_steps))
    a = np.zeros((n, n_steps))
    u[:, 0] = u0
    v[:, 0] = v0
    a[:, 0] = np.linalg.solve(M, -C @ v[:, 0] - K @ u[:, 0])   # F = 0

    K_eff = K + gamma / (beta * dt_) * C + 1 / (beta * dt_ ** 2) * M
    K_eff_inv = np.linalg.inv(K_eff)
    for i in range(n_steps - 1):
        F_eff = (M @ (1 / (beta * dt_ ** 2) * u[:, i]
                      + 1 / (beta * dt_) * v[:, i]
                      + (1 / (2 * beta) - 1) * a[:, i])
                 + C @ (gamma / (beta * dt_) * u[:, i]
                        + (gamma / beta - 1) * v[:, i]
                        + dt_ * (gamma / (2 * beta) - 1) * a[:, i]))
        u[:, i + 1] = K_eff_inv @ F_eff
        a[:, i + 1] = (1 / (beta * dt_ ** 2) * (u[:, i + 1] - u[:, i] - dt_ * v[:, i])
                       - (1 / (2 * beta) - 1) * a[:, i])
        v[:, i + 1] = v[:, i] + dt_ * ((1 - gamma) * a[:, i] + gamma * a[:, i + 1])
    return u, v, a


def recover_zeta(signal, t, omega, window=FIT_WINDOW):
    """Damping ratio from the analytic-signal envelope: log|env| is linear in t
    with slope -zeta*omega. Returns (zeta, r_squared)."""
    env = np.abs(hilbert(signal))
    m = (t >= window[0]) & (t <= window[1]) & (env > 0)
    if m.sum() < 10:
        return np.nan, np.nan
    y = np.log(env[m])
    slope, intercept = np.polyfit(t[m], y, 1)
    resid = y - (slope * t[m] + intercept)
    ss = 1.0 - resid.var() / y.var() if y.var() > 0 else np.nan
    return -slope / omega, ss


# ==========================================================================
# FIGURE 8.3 — verification of the modal damping construction
# ==========================================================================
def figure_8_3():
    print("\nFIGURE 8.3 — modal damping verification")
    K = k_set[0] * 1e6                      # undamaged baseline, N/m
    M = m_set[0]                            # consistent mass matrix
    C, freqs_hz, modes = damping_matrix(K / 1e6, M, damping_ratio=DAMPING_RATIO)

    omega1 = 2 * np.pi * freqs_hz[0]
    phi1 = modes[:, 0]
    print(f"  f1 = {freqs_hz[0]:.4f} Hz, omega1 = {omega1:.4f} rad/s, "
          f"target zeta = {DAMPING_RATIO}")

    n_steps = int(DECAY_SECONDS / dt) + 1
    t = np.arange(n_steps) * dt
    u, _, _ = newmark_beta_free_decay(M, C, K, phi1, np.zeros(12), n_steps, dt)

    # Which DOFs actually move in mode 1? A DOF with no modal amplitude has no
    # envelope to share, and fitting one to numerical dust is meaningless.
    amp = np.abs(phi1)
    participates = amp > 1e-6 * amp.max()
    moving = [i for i in TRANSLATIONAL if participates[i]]
    still = [i for i in TRANSLATIONAL if not participates[i]]

    print(f"  translational DOFs participating in mode 1: {moving}")
    print(f"  translational DOFs stationary in mode 1:    {still}"
          f"   (max |phi1| there = {amp[still].max():.2e})" if still else "")

    print("  recovered zeta, by participating translational DOF:")
    zetas = {}
    for i in moving:
        z, r2 = recover_zeta(u[i], t, omega1)
        zetas[i] = z
        print(f"    DOF {i:2d}: zeta = {z:.6f}   (envelope fit R^2 = {r2:.6f})")

    zs = np.array(list(zetas.values()))
    spread = zs.max() - zs.min()
    err = np.abs(zs - DAMPING_RATIO).max() / DAMPING_RATIO
    print(f"  spread across participating DOFs: {spread:.2e} "
          f"({spread / DAMPING_RATIO * 100:.4f}% of target)")
    print(f"  worst deviation from target:      {err * 100:.3f}%")

    if err > ZETA_TOLERANCE:
        raise SystemExit(
            f"\nSTOPPING — recovered zeta is {err * 100:.1f}% from the target "
            f"{DAMPING_RATIO}, outside the {ZETA_TOLERANCE * 100:.0f}% tolerance.\n"
            "The caption claims the response follows the envelope. It does not. "
            "No figure written.")

    # Plot the DOF with the largest mode-1 amplitude: the roof in y.
    dof = int(np.argmax(amp))
    A = float(np.abs(phi1[dof]))
    env = A * np.exp(-DAMPING_RATIO * omega1 * t)
    floor = dof // 3 + 1
    print(f"  plotted DOF {dof} (floor {floor}, y-direction), A = {A:.5f} m")

    fig, ax = plt.subplots(figsize=(WIDTH_IN, 68 * MM), constrained_layout=True)
    ax.plot(t, u[dof], color=BLUE, lw=0.6, ls="-",
            label=f"Simulated free decay, floor {floor}, y direction")
    ax.plot(t, env, color=RED, lw=1.1, ls="--",
            label=r"Envelope $\pm A\,e^{-\zeta\omega_1 t}$, $\zeta = 0.01$")
    ax.plot(t, -env, color=RED, lw=1.1, ls="--")
    ax.axhline(0, color=MUTED, lw=0.5)
    ax.set_xlim(0, DECAY_SECONDS)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Displacement (m)")
    ax.legend(loc="upper right", ncol=1, handlelength=2.6)

    # 10 s at 9.4 Hz is ~94 cycles across 150 mm, so the first seconds render as
    # a solid block. The envelope is the point and it survives, but the waveform
    # is unreadable, so an inset carries the individual cycles.
    axi = ax.inset_axes([0.545, 0.075, 0.42, 0.34])
    zoom = 0.5
    mz = t <= zoom
    axi.plot(t[mz], u[dof][mz], color=BLUE, lw=0.8)
    axi.plot(t[mz], env[mz], color=RED, lw=0.9, ls="--")
    axi.plot(t[mz], -env[mz], color=RED, lw=0.9, ls="--")
    axi.set_xlim(0, zoom)
    axi.tick_params(labelsize=8, length=2)
    axi.set_xticks([0, 0.25, 0.5])
    axi.set_yticks([-A, 0, A])
    axi.set_yticklabels([f"{-A:.2f}", "0", f"{A:.2f}"])
    axi.grid(True, color=GRID, lw=0.4)
    axi.set_facecolor("white")               # sits cleanly over the main gridlines
    for s in ("top", "right"):
        axi.spines[s].set_visible(False)
    # Rectangle only. indicate_inset_zoom's connector lines run from the marked
    # region at the far left across the whole decaying waveform to reach the
    # inset, i.e. two long diagonals straight over the data. The inset's own
    # 0.00-0.50 s axis already identifies the region.
    _, connectors = ax.indicate_inset_zoom(axi, edgecolor=MUTED, lw=0.7, alpha=0.9)
    for c in connectors:
        c.set_visible(False)

    despine(ax)
    save(fig, "fig8_3_damping_verification")
    return zetas, moving, still, amp


# ==========================================================================
# FIGURE 8.4 — the preprocessing chain
# ==========================================================================
def figure_8_4():
    print("\nFIGURE 8.4 — preprocessing chain")
    K = k_set[0] * 1e6
    M = m_set[0]
    C, freqs_hz, modes = damping_matrix(K / 1e6, M, damping_ratio=DAMPING_RATIO)

    # y-direction modes are the only ones the y sensors see.
    p = modes ** 2
    y_frac = p[Y_DOFS, :].sum(axis=0) / p.sum(axis=0)
    y_modes = freqs_hz[y_frac > 0.99]
    print(f"  y-direction modes (Hz): {np.round(y_modes, 3)}")

    # Forward model, identical to generate_dataset.simulate().
    F = D @ (generate_excitation(duration, dt, 4, seed=SEED) * FORCE_INTENSITY)
    _, _, a = newmark_beta(M, C, K, F, dt)
    rng = np.random.default_rng(SEED + 500_000)
    noise_std = NOISE_RATIO * np.max(np.sqrt(np.mean(a ** 2, axis=1)))
    a = a + rng.standard_normal(a.shape) * noise_std

    accel_y = a[Y_DOFS, :]
    window = accel_y[:, :CHUNK_SIZE]                       # one 4 s window
    clean = sanitize_accelerometer_data(window, fs=FS)     # detrend + 0.5-45 Hz
    f, psd = welch(clean, fs=FS, nperseg=NPERSEG, axis=-1)

    ch = 3                                                  # roof, y
    raw, cleaned, psd_1 = window[ch], clean[ch], psd[ch]
    t = np.arange(CHUNK_SIZE) / FS
    print(f"  sanitise removes {np.std(raw - cleaned) / np.std(raw) * 100:.1f}% "
          f"of the raw RMS (broadband sensor noise above 45 Hz)")

    # Panel (d) through the real scaler, with the locked training bounds. The
    # class has no constructor argument for them, so they are set directly —
    # transform() then applies the same epsilon and the same clip to [0, 1]
    # that the network's input goes through.
    scaler = PSDScaler()
    scaler.min_val, scaler.max_val = NORM_MIN, NORM_MAX
    psd_norm = scaler.transform(psd_1)
    psd_log = np.log10(psd_1 + scaler.epsilon)

    lo_all, hi_all = float(psd_log.min()), float(psd_log.max())
    band = f <= FMAX
    lo_b, hi_b = float(psd_log[band].min()), float(psd_log[band].max())
    n_out = int(((psd_log < NORM_MIN) | (psd_log > NORM_MAX)).sum())
    print(f"  log10 PSD, full 0-500 Hz axis : [{lo_all:.3f}, {hi_all:.3f}]")
    print(f"  log10 PSD, plotted 0-{FMAX:.0f} Hz   : [{lo_b:.3f}, {hi_b:.3f}]")
    print(f"  NORM_MIN / NORM_MAX           : [{NORM_MIN:.3f}, {NORM_MAX:.3f}]")
    print(f"  bins clipped by the bounds    : {n_out} of {psd_log.size}")
    print(f"  headroom below NORM_MAX       : {NORM_MAX - hi_all:.3f} decades")
    print(f"  linear peak/median over 0-{FMAX:.0f} Hz: "
          f"{psd_1[band].max() / np.median(psd_1[band]):.0f}x")

    # What is actually above the cut, for the axis note. A third y mode sits at
    # 38.9 Hz, inside the 0.5-45 Hz passband, so the note cannot claim emptiness.
    # Locate that mode specifically: the plain argmax above the cut lands on the
    # skirt of the 25.6 Hz peak instead.
    m3 = (f > y_modes[2] - 2.0) & (f < y_modes[2] + 2.0)
    hi_mode_f = float(f[m3][np.argmax(psd_1[m3])])
    hi_mode_dec = float(psd_log[band].max() - psd_log[m3].max())
    above = (f > FMAX) & (f <= 45.0)
    print(f"  third y mode at {y_modes[2]:.2f} Hz observed at {hi_mode_f:.2f} Hz, "
          f"{hi_mode_dec:.2f} decades below the plotted peak")
    print(f"  strongest bin anywhere above the cut: "
          f"{f[above][np.argmax(psd_1[above])]:.2f} Hz, "
          f"{psd_log[band].max() - psd_log[above].max():.2f} decades down")
    print(f"  y modes inside the 0.5-45 Hz passband: "
          f"{np.round([m for m in y_modes if m < 45.0], 3)}")
    print(f"  raw vs filtered correlation  : "
          f"{np.corrcoef(raw, cleaned)[0, 1]:.4f}")
    print(f"  panel (d) range, plotted band: "
          f"[{psd_norm[band].min():.3f}, {psd_norm[band].max():.3f}]   "
          f"full axis [{psd_norm.min():.3f}, {psd_norm.max():.3f}]")

    fig, axes = plt.subplots(4, 1, figsize=(WIDTH_IN, 175 * MM),
                             constrained_layout=True)

    # Both traces, because the bandpass sits between (a) and (b) and is
    # otherwise invisible in this figure — it removes 21% of the raw RMS, so
    # "(b) its PSD" would be ambiguous about which signal it is the PSD of.
    ax = axes[0]
    ax.plot(t, raw, color=MUTED, lw=0.3, ls="-", alpha=0.85,
            label="Raw record")
    ax.plot(t, cleaned, color=BLUE, lw=0.5, ls="-",
            label="After detrend + 0.5–45 Hz bandpass")
    ax.set_xlim(0, CHUNK_SIZE / FS)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel(r"Acceleration (m/s$^2$)")
    ax.legend(loc="upper left", ncol=2, handlelength=2.2,
              borderaxespad=0.2, columnspacing=1.4)

    # Scaled by 1e3 into the label rather than left to matplotlib's offset text,
    # which renders at the top-left corner and collides with the (b) key.
    ax = axes[1]
    ax.plot(f[band], psd_1[band] * 1e3, color=GREEN, lw=0.9, ls="-")
    ax.set_ylabel(r"PSD ($10^{-3}$ (m/s$^2$)$^2$/Hz)")

    # Solid. Linestyle variation earns its keep when two curves share an axis
    # (Fig 8.5); on a dense single-curve spectral trace it only hurts legibility.
    ax = axes[2]
    ax.plot(f[band], psd_log[band], color=AMBER, lw=0.9, ls="-")
    ax.set_ylabel(r"$\log_{10}$ PSD")

    ax = axes[3]
    ax.plot(f[band], psd_norm[band], color=PURPLE, lw=0.9, ls="-")
    ax.set_ylim(-0.05, 1.05)
    ax.set_ylabel("Normalised input (-)")

    for ax in axes[1:]:
        ax.set_xlim(0, FMAX)
        ax.set_xlabel("Frequency (Hz)")

    # Panel keys, and the axis note — not a title, per the chapter convention.
    for ax, lab in zip(axes, "abcd"):
        ax.text(0.0, 1.02, f"({lab})", transform=ax.transAxes,
                ha="left", va="bottom", fontsize=9, fontweight="bold")
    # Not "nothing above 30 Hz": the third y mode at 38.9 Hz is inside the
    # 0.5-45 Hz passband. It is suppressed because generate_excitation
    # low-passes the forcing at 20 Hz, so it sits 3.6 decades down.
    # Named by its eigenfrequency, not the observed bin: the 0.49 Hz Welch bin
    # puts the peak at 38.6 Hz, but the mode itself is at 38.85 Hz.
    axes[1].text(0.98, 0.95,
                 f"Truncated at {FMAX:.0f} Hz; the third $y$ mode at "
                 f"{y_modes[2]:.1f} Hz is {hi_mode_dec:.1f} decades down",
                 transform=axes[1].transAxes, ha="right", va="top",
                 fontsize=8, color=MUTED, style="italic")

    for ax in axes:
        despine(ax)
    save(fig, "fig8_4_preprocessing_chain")
    return dict(
        y_modes=y_modes, rng_all=(lo_all, hi_all), rng_band=(lo_b, hi_b),
        n_clip=n_out,
        y_in_band=np.round([m for m in y_modes if m < 45.0], 2).tolist(),
        hi_mode_f=hi_mode_f, hi_dec=hi_mode_dec,
        any_dec=float(psd_log[band].max() - psd_log[above].max()),
        corr=float(np.corrcoef(raw, cleaned)[0, 1]),
        rms_pc=float(np.std(raw - cleaned) / np.std(raw) * 100),
        maxdiff_pc=float(np.abs(raw - cleaned).max() / np.abs(raw).max() * 100),
        d_lo=float(psd_norm[band].min()), d_hi=float(psd_norm[band].max()),
        d_full_lo=float(psd_norm.min()))


# ==========================================================================
# FIGURE 8.5 — Frobenius residual vs singular-value ratio
# ==========================================================================
# Deliberately NOT the 12-DOF benchmark. On a uniform shear chain the storey
# superposition K(k) = sum_i k_i K_i is exact, so the comparison isolates the
# two functional forms from the benchmark's representation error, which is a
# separate finding (see the section 8.6.3 block at the end of this script).
# Nothing here is stochastic.
UNI_K_STOREY = 1.0e6      # N/m, every storey
UNI_M_FLOOR = 1.0e3       # kg, every floor
UNI_N = 4
UNI_ALPHA_TRUE = np.array([0.6, 1.0, 1.0, 1.0])   # storey 1 reduced, rest intact
UNI_SWEEP = (0.05, 1.0)   # admissible range of a stiffness fraction; the repo's
                          # own diagnostic grid (diagnose_physics_loss.GRID)
                          # starts at 0.05 and train.py clips alpha at 0.01
N_MODES = 2               # set N in Eq. 8.7


def uniform_storey_components(n=UNI_N, k=UNI_K_STOREY):
    """Physical storey springs for a shear chain fixed at the base.

    Storey i joins floor i-1 to floor i, with floor 0 the ground, so storey 1
    contributes k to the (1,1) entry alone and every storey above contributes
    the 2x2 block k*[[1,-1],[-1,1]]. Each component is positive semi-definite
    and they sum to the tridiagonal K.

    NOTE the earlier version of this figure (fig_production.ipynb,
    storey_stiffness_components) built components that sum to K correctly but
    are individually INDEFINITE — it puts 2k on the lower diagonal entry and
    nothing on the upper one, so K_2..K_4 have a negative eigenvalue of -0.41k
    and are not storey springs. It also indexes the chain from the free end, so
    its swept component sits at the roof rather than at the base. Both are why
    the Frobenius percentage below differs from the one in the draft caption.
    """
    comps = []
    for s in range(n):
        S = np.zeros((n, n))
        if s == 0:
            S[0, 0] = k
        else:
            S[s - 1, s - 1] += k
            S[s, s] += k
            S[s - 1, s] -= k
            S[s, s - 1] -= k
        comps.append(S)
    return comps


def figure_8_5():
    print("\nFIGURE 8.5 — Frobenius vs singular-value physics residual")
    comps = uniform_storey_components()
    M = np.eye(UNI_N) * UNI_M_FLOOR

    def K_of(alpha):
        return sum(a * Si for a, Si in zip(alpha, comps))

    # Exact natural frequencies of the TRUE damaged state, then held fixed
    # while k_hat_1 is swept — this is what puts the minimum on the true value.
    M_isqrt = np.diag(1.0 / np.sqrt(np.diag(M)))
    w2_all = np.sort(np.linalg.eigvalsh(M_isqrt @ K_of(UNI_ALPHA_TRUE) @ M_isqrt))
    w2 = w2_all[:N_MODES]
    print(f"  uniform chain: {UNI_N} storeys, k = {UNI_K_STOREY:.3g} N/m, "
          f"m = {UNI_M_FLOOR:.3g} kg per floor")
    print(f"  true stiffness fraction: k_hat_1 = {UNI_ALPHA_TRUE[0]}, "
          f"storeys 2-4 intact")
    print(f"  swept range: {UNI_SWEEP[0]} to {UNI_SWEEP[1]}")
    print(f"  frequencies held fixed ({N_MODES} modes): "
          f"{np.sqrt(w2) / (2 * np.pi)} Hz = {np.sqrt(w2)} rad/s")

    # Force the true value onto the grid so the sharp minimum is actually sampled.
    # Rounded before uniquing: union1d against a linspace that already lands on
    # the true value otherwise leaves two points ~1e-16 apart, which shows up as
    # a spurious zero step in the monotonicity check below.
    sweep = np.unique(np.round(
        np.union1d(np.linspace(*UNI_SWEEP, 381), [UNI_ALPHA_TRUE[0]]), 12))
    frob, ratio = [], []
    for a1 in sweep:
        K_hat = K_of(np.array([a1, 1.0, 1.0, 1.0]))
        fs, rs = [], []
        for w in w2:                                   # average over set N
            Dn = K_hat - w * M
            fs.append(np.linalg.norm(Dn, "fro"))
            sv = np.linalg.svd(Dn, compute_uv=False)
            rs.append(sv.min() / sv.max())
        frob.append(np.mean(fs))
        ratio.append(np.mean(rs))
    frob, ratio = np.array(frob), np.array(ratio)

    var_f = (frob.max() - frob.min()) / frob.max() * 100
    var_r = (ratio.max() - ratio.min()) / ratio.max() * 100
    print(f"  Frobenius residual varies      : {var_f:.3g}%")
    print(f"  singular-value ratio varies    : {var_r:.4g}%")
    print(f"  ratio minimum                  : {ratio.min():.3e} "
          f"at k_hat_1 = {sweep[np.argmin(ratio)]:.4f}")
    # The stronger result: the Frobenius residual has NO interior minimum. Its
    # gradient is small AND points the wrong way, so descending it drives the
    # prediction to the lower bound instead of to the true fraction.
    d = np.diff(frob)
    print(f"  Frobenius monotone increasing  : {bool(np.all(d > 0))} "
          f"(smallest step {d.min():+.3e})")
    print(f"  Frobenius minimum              : at k_hat_1 = "
          f"{sweep[np.argmin(frob)]:.4f}  (lower bound of the sweep = "
          f"{UNI_SWEEP[0]}) -- no interior minimum")
    # Storey 1 enters K as the rank-one term k_hat_1 * k * e1 e1^T, so the
    # eigenvalue that vanishes at the true fraction crosses zero almost
    # linearly and the ratio is close to piecewise linear -- close to, not
    # exactly: the largest departure from a straight fit is reported here.
    dev = []
    for m in (sweep < UNI_ALPHA_TRUE[0], sweep > UNI_ALPHA_TRUE[0]):
        x, y = sweep[m], ratio[m]
        dev.append(np.abs(y - np.polyval(np.polyfit(x, y, 1), x)).max() / ratio.max())
    print(f"  storey-1 component is rank {np.linalg.matrix_rank(comps[0])} "
          f"(= k*e1 e1^T: {np.allclose(comps[0], UNI_K_STOREY * np.outer(np.eye(UNI_N)[0], np.eye(UNI_N)[0]))})")
    print(f"  departure from piecewise-linear: {dev[0] * 100:.2f}% (left branch), "
          f"{dev[1] * 100:.2f}% (right) of the ratio maximum")

    fig, ax = plt.subplots(figsize=(WIDTH_IN, 78 * MM), constrained_layout=True)
    ax.plot(sweep, frob / frob.max(), color=AMBER, ls="--", lw=1.3,
            label=r"Frobenius residual $\|K(\hat{k}) - \omega_n^2 M\|_F$")
    ax.plot(sweep, ratio / ratio.max(), color=BLUE, ls="-", lw=1.3,
            label=r"Singular-value ratio $\sigma_{\min}/\sigma_{\max}$")
    # No hat: this is the true value, not a prediction. The hat is reserved for
    # predicted quantities throughout.
    ax.axvline(UNI_ALPHA_TRUE[0], color=RED, lw=1.0, ls=":",
               label=f"True fraction, $k_1 = {UNI_ALPHA_TRUE[0]}$")
    ax.set_xlim(*UNI_SWEEP)
    ax.set_ylim(-0.03, 1.05)
    ax.set_xlabel("Predicted first-storey stiffness fraction (–)")
    ax.set_ylabel("Residual, normalised to its\nown maximum (–)")
    # Right-hand mid-height is the only genuinely dead region: the Frobenius
    # curve sits above 0.95 and the ratio's rising branch stays below 0.55, so
    # lower-left would have the descending branch running through the labels.
    ax.legend(loc="upper right", bbox_to_anchor=(0.995, 0.80), handlelength=2.8)
    despine(ax)
    save(fig, "fig8_5_physics_residual")
    return dict(var_f=var_f, var_r=var_r, sweep=sweep, w2=w2,
                dev_l=dev[0] * 100, dev_r=dev[1] * 100,
                monotone=bool(np.all(d > 0)),
                argmin=float(sweep[np.argmin(frob)]))


# ==========================================================================
# Section 8.6.3 cross-checks, on the 12-DOF benchmark
# ==========================================================================
def section_8_6_3():
    """Numbers the chapter quotes from the benchmark, not from Figure 8.5."""
    print("\nSECTION 8.6.3 cross-checks (12-DOF benchmark)")
    from four_floor.diagnose_physics_loss import (                     # noqa: E402
        BASE_STORY, derived_alpha, stored_freqs, phys_loss)
    from four_floor.simulation.matrices import k_set as _k_set         # noqa: E402

    print("  (1) reconstruction error of K(alpha) = sum_i alpha_i K_i")
    rec = {}
    for d in range(len(_k_set)):
        a = derived_alpha(d)
        K_hat = sum(a[i] * BASE_STORY[i] for i in range(4))
        K_true = _k_set[d] * 1e6
        rec[d] = np.linalg.norm(K_hat - K_true) / np.linalg.norm(K_true) * 100
        print(f"      pattern {d} ({'undamaged' if d == 0 else 'damaged  '}): "
              f"{rec[d]:6.3f}%")
    dmg = [rec[d] for d in range(1, len(_k_set))]
    print(f"      range over the 6 DAMAGED patterns : "
          f"{min(dmg):.3f}% to {max(dmg):.3f}%")
    print(f"      undamaged pattern 0               : {rec[0]:.3f}%")

    print("  (2) physics loss at the true fractions")
    worse = []
    for d in range(len(_k_set)):
        w = 2 * np.pi * stored_freqs(d, lumped=False)[:2]
        L_t = phys_loss(derived_alpha(d), w, lumped=False)
        L_1 = phys_loss(np.ones(4), w, lumped=False)
        flag = ""
        if d > 0 and L_1 < L_t:
            worse.append(d)
            flag = "   <-- INTACT SCORES BETTER THAN TRUE"
        print(f"      pattern {d}: L(true) = {L_t:.3e}   L(intact) = {L_1:.3e}{flag}")

    # Sampled-stiffness dataset: K_true is sum_i alpha_i K_i by construction, so
    # the residual at the true alpha is exactly singular.
    rng = np.random.default_rng(SEED)
    Ls = []
    for _ in range(200):
        a = rng.uniform(0.3, 1.0, 4)
        K = sum(a[i] * BASE_STORY[i] for i in range(4))
        f = np.sort(np.sqrt(np.real(np.linalg.eigvals(
            np.linalg.inv(m_set[0]) @ K)))) / (2 * np.pi)
        Ls.append(phys_loss(a, 2 * np.pi * f[:2], lumped=False))
    Ls = np.array(Ls)
    print(f"      sampled-stiffness dataset, L(true) over 200 draws: "
          f"median {np.median(Ls):.3e} (min {Ls.min():.1e}, max {Ls.max():.1e})")
    return rec, worse, float(np.median(Ls))


if __name__ == "__main__":
    print(f"Chapter 8 figures -> {OUT}   (seed {SEED})")
    zetas, moving, still, amp = figure_8_3()
    f4 = figure_8_4()
    f5 = figure_8_5()
    rec, worse, L_sampled = section_8_6_3()
    y_modes, rng_all, rng_band, n_clip = (
        f4["y_modes"], f4["rng_all"], f4["rng_band"], f4["n_clip"])
    var_f = f5["var_f"]
    dev_l, dev_r = f5["dev_l"], f5["dev_r"]
    y_in_band, hi_dec, any_dec = f4["y_in_band"], f4["hi_dec"], f4["any_dec"]
    corr, rms_pc, maxdiff_pc = f4["corr"], f4["rms_pc"], f4["maxdiff_pc"]
    d_lo, d_hi = f4["d_lo"], f4["d_hi"]
    d_top_gap = 1.0 - d_hi

    print("\n" + "=" * 72)
    print("WHERE THE CODE DOES NOT SUPPORT THE DRAFT CAPTIONS")
    print("=" * 72)
    print(f"""
Fig 8.3, second sentence — "All degrees of freedom share this envelope in
single-mode vibration."
  Verified TRUE for the {len(moving)} y-direction DOFs {moving}: recovered zeta agrees
  to {max(abs(z - DAMPING_RATIO) for z in zetas.values()) / DAMPING_RATIO * 100:.3f}% of the target and to
  {(max(zetas.values()) - min(zetas.values())):.1e} between DOFs.
  NOT VERIFIABLE for the other {len(still)} translational DOFs {still}, nor for the
  four rotation DOFs: their mode-1 amplitude is {amp[still].max():.1e}, i.e. zero to
  machine precision. They do not move, so they have no envelope to share.
  Every mode of this model is purely x, y or theta — the benchmark's K and M are
  block-decoupled — and mode 1 is a pure y mode.
  SUGGESTED: "All four y-direction degrees of freedom share this envelope in
  single-mode vibration." (Or "...all degrees of freedom that participate in
  the mode...".)

Fig 8.4, panel (b) — "the resonant peaks are visible"
  The y sensors see modes at {np.round(y_modes, 2).tolist()} Hz.
  Only ONE is below 20 Hz. The 25.60 Hz mode is 0.58 decades below the
  fundamental — a strong, real peak — so at the requested 0-20 Hz axis the
  panel shows a single peak and "peaks" is wrong.
  I set FMAX = {FMAX:.0f} Hz so both dominant peaks are in frame and the caption
  stands. Above 30 Hz the response is >3 decades down, so the axis is still
  tight. Set FMAX = 20.0 at the top of this script to get exactly what was
  asked for, and change "peaks" to "peak" in the caption if you do.

Fig 8.4 — the stated rationale, for the record
  "the modes are all below 20 Hz" is not true of this model: only the first of
  the four y modes is. The rest of the 0-500 Hz axis IS flat, so truncating is
  right; only the cut-off was wrong.

Newmark integration — simulation.excitation.newmark_beta
  It hardcodes zero initial conditions (u[:,0] and v[:,0] are never written),
  so it cannot produce a free decay from an initial displacement: with F = 0 it
  returns an all-zero response. Fig 8.3 therefore uses
  newmark_beta_free_decay() in this script, which is that function's recurrence
  verbatim with the two initial-state lines added. Same scheme, same beta and
  gamma. Worth folding u0/v0 arguments into the repository function.

Fig 8.5 — the model is right; both numbers need changing, and the argument
should be stronger than the draft makes it.
  MODEL: the caption's "uniform four-storey shear model" is correct. The earlier
  figure (fig_production.ipynb, fig_loss_comparison) was already computed on a
  uniform chain, NOT on the 12-DOF benchmark. Nothing to change there.
  "2.7%" -> {var_f:.2f}%. Your revised draft says 7.5%, read off the plot; the
  computed value is {var_f:.2f}%, so 7.4% is the number to quote. The old 2.7% is
  reproducible, but only from the notebook code, which (i) uses ONE frequency,
  the fundamental, not the first two, and (ii) builds storey components that are
  not storey springs -- K_2..K_4 each carry a negative eigenvalue of -0.41k --
  and indexes the chain from the free end, putting the swept storey at the roof.
  "99.6%" -> 100%. Your revised draft keeps 99.6%. With the true fraction on the
  sweep grid the residual is EXACTLY singular there, so sigma_min is 8.7e-17 and
  the variation is 100.000000%. 99.6% is what you get when the grid misses the
  true value. Recommend "varies by 100%, reaching zero at the true fraction".
  MONOTONICITY: confirmed, and it is the stronger result you identified. The
  Frobenius residual is strictly increasing across the whole sweep (smallest
  step positive), so its minimum is at the lower bound {UNI_SWEEP[0]}, not at 0.6.
  Descending it drives k_hat_1 to the boundary. Your revised wording is right.
  PIECEWISE-LINEARITY: the mechanism you give is correct -- storey 1 enters K as
  the rank-one term k_hat_1 * k * e1 e1^T, confirmed rank 1 -- but the curve is
  NOT exactly linear. The largest departure from a straight fit is {dev_l:.1f}% of
  the ratio maximum on the left branch and {dev_r:.1f}% on the right. Safer clause:
  "near-linear on each side because storey 1 enters the stiffness as a rank-one
  term, so the eigenvalue that vanishes at the true fraction crosses zero
  almost linearly".
  LABEL: hat dropped from the dotted-line label, now "True fraction, k_1 = 0.6".

Fig 8.4 — the third y mode is real, and the note now says so.
  There IS a y mode above the 30 Hz cut, at {y_modes[2]:.2f} Hz, and it is inside the
  0.5-45 Hz passband -- three of the four y modes are ({y_in_band}).
  It is suppressed only because generate_excitation low-passes the forcing at
  20 Hz. Measured, it sits {hi_dec:.2f} decades below the plotted peak, and the
  strongest bin anywhere above the cut is {any_dec:.2f} decades down. So "3 decades"
  survives, but the note claimed emptiness where there is a real mode; it now
  names the mode and its level.
  PANEL (a): the two traces do NOT quite coincide. Correlation is {corr:.4f}, but the
  filter removes {rms_pc:.1f}% of the raw RMS and the largest sample difference is
  {maxdiff_pc:.0f}% of the raw peak -- it is stripping the broadband sensor noise above
  45 Hz, which is the point. "Track closely" is defensible; "nearly coincide"
  overstates it.
  PANEL (d): plotted range is [{d_lo:.3f}, {d_hi:.3f}], so there is headroom at the top
  ({d_top_gap:.2f} short of 1.0) and no clipping anywhere. One caveat for that sentence:
  over the FULL 0-500 Hz axis the normalised value does reach 0.000, because the
  PSD there falls below the scaler's 1e-10 epsilon and log10 pins to NORM_MIN
  exactly. Headroom at both ends is true of the plotted band, not of the whole
  spectrum.
  LINESTYLES: panels (c) and (d) are solid now; only Fig 8.5, where two curves
  share an axis, still varies linestyle.

Fig 8.3 — inset added.
  10 s at 9.42 Hz is ~94 cycles across 150 mm, so an inset over the first 0.5 s
  now carries the waveform while the main axis keeps the full decay and the
  0.5-8 s fit window. Legend reads "floor 4, y direction".

Section 8.6.3 — all three quoted numbers check out.
  "0.7% to 5.1%" reconstruction error: CONFIRMED, {min(rec[d] for d in rec if d):.3f}% to
  {max(rec.values()):.3f}% over the six DAMAGED patterns. Note it is six, not seven —
  pattern 0 is undamaged and reconstructs to {rec[0]:.3f}%. If "seven patterns" is
  meant literally the lower bound becomes {rec[0]:.3f}%.
  "order 1e-3" physics loss at the true fractions on the benchmark: CONFIRMED,
  3.8e-04 to 5.2e-03 across the damaged patterns.
  "order 1e-8" on the sampled-stiffness dataset: CONFIRMED as the right
  contrast, though the median is {L_sampled:.1e} — nearer 1e-9 than 1e-8, with a
  spread that straddles both. "Five to six orders of magnitude smaller" is the
  safer phrasing than a single power.
  Patterns where the INTACT state scores better than the true state: {worse}.
  Your chapter claims this happens and it does — for the three mildest
  patterns, whose true alpha_1 is 0.93, 0.976 and 0.976. Load-bearing point
  confirmed.
""")
    print(f"log10 PSD observed: {rng_all[0]:.3f} to {rng_all[1]:.3f} "
          f"(plotted band {rng_band[0]:.3f} to {rng_band[1]:.3f}); "
          f"NORM_MIN/MAX = {NORM_MIN} / {NORM_MAX}; {n_clip} bins clipped.")

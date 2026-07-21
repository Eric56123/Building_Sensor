"""
fig_training_overview — combined methodology figure (9.6)
=============================================================
One figure, two panels, sharing a single caption/label:

  (a) Single training-step schematic — batch -> forward -> alpha_hat,
      splitting into the data branch (MSE vs labels) and the physics
      branch (assemble K(alpha_hat) - omega_n^2 M -> SVD -> sigma_min/
      sigma_max) -> weighted sum -> backward/clip/step. Drawn with
      matplotlib patches so it matches the rest of the figure pipeline
      (no separate TikZ/LaTeX toolchain needed).

  (b) Loss-component curves vs epoch — L_data, lambda*L_phys, and the
      total, read from loss_log.csv (written by the patched train.py).
      Falls back to synthetic placeholder curves so this still runs
      out of the box before you've done a real training run — search
      for >>> REPLACE.

Drop this file's two functions into your existing fig_production
pipeline (it assumes apply_style(), COLORS and save() from there are
already in scope — copy them in if running this file standalone).

    python fig_training_overview.py

Requires: numpy, matplotlib. (csv is stdlib.)
"""

import csv
import os

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch


# ===========================================================================
# Shared style + palette — copy of fig_production.ipynb's apply_style/COLORS
# so this file also runs standalone. Delete this block if you paste the two
# functions below directly into fig_production.ipynb instead.
# ===========================================================================
COLORS = {
    "primary":   "#1f4e79",
    "secondary": "#c0392b",
    "accent":    "#e08a1e",
    "muted":     "#7f7f7f",
    "light":     "#a9c4e0",
    "dark":      "#222222",
}


def apply_style():
    mpl.rcParams.update({
        "font.family":       "serif",
        "font.serif":        ["DejaVu Serif", "Times New Roman", "Times"],
        "font.size":         11,
        "axes.titlesize":    12,
        "axes.labelsize":    11,
        "xtick.labelsize":   10,
        "ytick.labelsize":   10,
        "legend.fontsize":   10,
        "axes.linewidth":    0.9,
        "lines.linewidth":   1.4,
        "axes.spines.top":   False,
        "axes.spines.right": False,
        "axes.grid":         True,
        "grid.alpha":        0.25,
        "grid.linewidth":    0.6,
        "figure.dpi":        120,
        "savefig.dpi":       300,
        "savefig.bbox":      "tight",
        "savefig.pad_inches": 0.03,
    })


def save(fig, name):
    fig.savefig(name + ".png")
    fig.savefig(name + ".pdf")
    plt.close(fig)
    print(f"  saved {name}.{{png,pdf}}")


# ===========================================================================
# Panel (a) — single training-step schematic
# ===========================================================================
def _box(ax, xy, w, h, text, facecolor="white", edgecolor=None, fontsize=8.5):
    edgecolor = edgecolor or COLORS["dark"]
    x, y = xy
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.02",
        linewidth=1.1, edgecolor=edgecolor, facecolor=facecolor,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fontsize, color=COLORS["dark"])
    return x, y, w, h


def _arrow(ax, start, end, color=None, style="-", lw=1.1):
    color = color or COLORS["dark"]
    arrow = FancyArrowPatch(
        start, end, arrowstyle="-|>", mutation_scale=10,
        linewidth=lw, color=color, linestyle=style, shrinkA=0, shrinkB=0,
    )
    ax.add_patch(arrow)


def draw_training_step_schematic(ax):
    """Panel (a): batch -> forward -> split -> weighted sum -> backprop."""
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.set_aspect("equal")
    ax.axis("off")

    # Row y-positions
    y_top = 6.6      # batch / forward / alpha_hat
    y_mid = 4.0       # data branch (left) / physics branch (right)
    y_low = 1.6       # weighted sum
    y_bot = 0.2       # backward

    # --- top row: batch -> forward CNN/MLP -> alpha_hat ---
    b_batch = _box(ax, (0.2, y_top), 1.6, 0.9, "Batch\n(PSD, labels,\n$\\omega_n$, mass type)",
                   facecolor=COLORS["light"])
    b_fwd = _box(ax, (2.4, y_top), 1.8, 0.9, "Forward pass\nCNN + MLP\n(SHM\\_PINN)")
    b_alpha = _box(ax, (4.8, y_top), 1.4, 0.9, r"$\hat{\alpha} \in [0,1]^4$",
                   facecolor=COLORS["light"])

    _arrow(ax, (1.8, y_top + 0.45), (2.4, y_top + 0.45))
    _arrow(ax, (4.2, y_top + 0.45), (4.8, y_top + 0.45))

    # branch down from alpha_hat to the two loss branches
    _arrow(ax, (5.5, y_top), (2.6, y_mid + 0.9), color=COLORS["primary"])
    _arrow(ax, (5.5, y_top), (7.4, y_mid + 0.9), color=COLORS["secondary"])

    # --- data branch (left) ---
    b_data = _box(ax, (1.2, y_mid), 2.8, 0.9,
                  r"Data branch: MSE$(\hat{\alpha}, \alpha_\text{true})$"
                  "\n" r"$\to \mathcal{L}_\text{data}$",
                  edgecolor=COLORS["primary"])

    # --- physics branch (right) ---
    b_phys = _box(ax, (5.9, y_mid), 3.4, 0.9,
                  r"Physics branch: $K(\hat{\alpha})-\omega_n^2 M \to$ SVD"
                  "\n" r"$\to \sigma_{\min}/\sigma_{\max} \to \mathcal{L}_\text{phys}$",
                  edgecolor=COLORS["secondary"])

    _arrow(ax, (2.6, y_mid), (4.0, y_low + 0.9), color=COLORS["primary"])
    _arrow(ax, (7.6, y_mid), (5.6, y_low + 0.9), color=COLORS["secondary"])

    # --- weighted sum ---
    b_sum = _box(ax, (3.4, y_low), 3.2, 0.9,
                 r"$\mathcal{L}_\text{total} = \mathcal{L}_\text{data} + \lambda\,\mathcal{L}_\text{phys}$",
                 facecolor=COLORS["accent"], edgecolor=COLORS["dark"])

    _arrow(ax, (5.0, y_low), (5.0, y_bot + 0.9))

    # --- backward / clip / step ---
    b_back = _box(ax, (3.0, y_bot), 4.0, 0.9,
                  "Backward $\\to$ grad clip (max\\_norm=1.0)\n$\\to$ optimizer.step()",
                  facecolor="white", edgecolor=COLORS["muted"])

    ax.set_title("(a) Single training-step data flow", loc="left", fontsize=11)


# ===========================================================================
# Panel (b) — loss-component curves vs epoch
# ===========================================================================
def _load_loss_log(path="loss_log.csv"):
    """Reads the CSV written by the patched train.py. Returns dict of arrays."""
    if not os.path.exists(path):
        return None
    epochs, data_l, phys_w, phys_u, total_l, lr = [], [], [], [], [], []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            epochs.append(int(row["epoch"]))
            data_l.append(float(row["data_loss"]))
            phys_w.append(float(row["phys_loss_weighted"]))
            phys_u.append(float(row["phys_loss_unweighted"]))
            total_l.append(float(row["total_loss"]))
            lr.append(float(row["lr"]))
    return {
        "epoch": np.array(epochs), "data": np.array(data_l),
        "phys_weighted": np.array(phys_w), "phys_unweighted": np.array(phys_u),
        "total": np.array(total_l), "lr": np.array(lr),
    }


def _make_demo_loss_log(n_epochs=500, seed=0):
    """
    >>> REPLACE with real numbers once loss_log.csv exists (run the patched
    train.py once — see the train.py diff in this session). This synthetic
    version exists only so the script runs before that.
    """
    rng = np.random.default_rng(seed)
    epoch = np.arange(1, n_epochs + 1)
    data = 5e-2 * np.exp(-epoch / 60) + 3e-4 + 5e-5 * rng.standard_normal(n_epochs)
    phys_w = 0.35 * np.exp(-epoch / 120) + 0.02 + 3e-3 * rng.standard_normal(n_epochs)
    data = np.clip(data, 1e-5, None)
    phys_w = np.clip(phys_w, 1e-4, None)
    return {
        "epoch": epoch, "data": data, "phys_weighted": phys_w,
        "phys_unweighted": phys_w / 0.1, "total": data + phys_w,
        "lr": 5e-4 * (1 + np.cos(np.pi * epoch / n_epochs)) / 2,
    }


def draw_loss_curves(ax, log, early_stop_epoch=None):
    """Panel (b): L_data, lambda*L_phys, and total, on a shared log y-axis."""
    ax.semilogy(log["epoch"], log["data"], color=COLORS["primary"],
                label=r"$\mathcal{L}_\text{data}$")
    ax.semilogy(log["epoch"], log["phys_weighted"], color=COLORS["secondary"],
                ls="--", label=r"$\lambda\,\mathcal{L}_\text{phys}$")
    ax.semilogy(log["epoch"], log["total"], color=COLORS["dark"],
                lw=1.0, alpha=0.8, label=r"$\mathcal{L}_\text{total}$")

    # Only draw this if you actually implement early stopping — see the
    # 9.6.4 note: train.py currently has no early-stopping logic, so there
    # is no principled epoch to mark yet.
    if early_stop_epoch is not None:
        ax.axvline(early_stop_epoch, color=COLORS["muted"], lw=1.0, ls=":")
        ax.text(early_stop_epoch, ax.get_ylim()[1], " early stop",
                rotation=90, va="top", ha="left", fontsize=8, color=COLORS["muted"])

    ax.set_xlabel("Epoch")
    ax.set_ylabel("Loss (log scale)")
    ax.legend(frameon=False, loc="upper right")
    ax.set_title("(b) Loss components vs epoch", loc="left", fontsize=11)


# ===========================================================================
# Combined figure
# ===========================================================================
def fig_training_overview(loss_log_path="loss_log.csv", early_stop_epoch=None):
    log = _load_loss_log(loss_log_path)
    if log is None:
        print(f"  [note] {loss_log_path} not found — using placeholder loss "
              "curves. Run the patched train.py once and re-run this script "
              "for the real figure.")
        log = _make_demo_loss_log()

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(11.5, 4.6),
                                      gridspec_kw={"width_ratios": [1.05, 1.0]})
    draw_training_step_schematic(ax_a)
    draw_loss_curves(ax_b, log, early_stop_epoch=early_stop_epoch)

    fig.tight_layout()
    save(fig, "fig_training_overview")


if __name__ == "__main__":
    apply_style()
    fig_training_overview()

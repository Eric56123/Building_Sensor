"""
make_figures.py — regenerate the full dissertation figure set in ONE consistent
style (Okabe-Ito colourblind-safe palette, recessive grid, error bars from
replicate spread). Outputs to characterisation/figures/.
Read-only w.r.t. data; writes only PNGs.
"""
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np, glob, os, sys
sys.path.insert(0, '.')
import interpret_capture as ic, toolkit_common as tk

base = 'characterisation'; OUT = f'{base}/figures'; os.makedirs(OUT, exist_ok=True)

# ---- shared style ----------------------------------------------------------
OI = {'blue': '#0072B2', 'orange': '#E69F00', 'green': '#009E73',
      'vermillion': '#D55E00', 'purple': '#CC79A7', 'sky': '#56B4E9'}
MODE = [OI['blue'], OI['orange'], OI['green']]      # f1, f2, f3  (fixed roles)
POS  = {'top': OI['blue'], 'F2': OI['orange'], 'F1': OI['green']}
INK, MUTED, GRID = '#222222', '#666666', '#DDDDDD'
plt.rcParams.update({
    'font.family': 'DejaVu Sans', 'font.size': 10,
    'axes.titlesize': 11, 'axes.titleweight': 'bold', 'axes.labelsize': 10,
    'axes.edgecolor': MUTED, 'axes.linewidth': 0.8,
    'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.6,
    'axes.axisbelow': True, 'xtick.color': INK, 'ytick.color': INK,
    'text.color': INK, 'axes.labelcolor': INK,
    'legend.frameon': False, 'legend.fontsize': 9,
    'figure.dpi': 200, 'savefig.dpi': 200, 'savefig.bbox': 'tight',
    'savefig.facecolor': 'white', 'figure.facecolor': 'white',
})
def despine(ax, keep_grid_y=True):
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=3, color=MUTED)

def vec(f): return ic.modal_vector(f'{base}/{f}')
fb = vec('day6_baseline')

def reps_shift(prefix, bl_vec, rs=(1, 2, 3)):
    """mean,std of Δf1/f2/f3 over replicate folders <prefix>r{n}."""
    sv = []
    for r in rs:
        f = f'{prefix}{r}'
        if os.path.isdir(f'{base}/{f}'):
            sv.append((vec(f) - bl_vec) / bl_vec * 100)
    sv = np.array(sv)
    return np.nanmean(sv, axis=0), np.nanstd(sv, axis=0), len(sv)

# ===========================================================================
# FIG 01 — baseline spectrum
# ===========================================================================
psd = None
for p in sorted(glob.glob(f'{base}/day6_baseline/*_raw.csv')):
    x, _ = tk.load_raw_series(p); fr, pp = tk.raw_psd(x)
    psd = pp if psd is None else psd + pp
m = (fr >= 0.5) & (fr <= 16)
fig, ax = plt.subplots(figsize=(6.5, 3.4))
ax.semilogy(fr[m], psd[m], color=OI['blue'], lw=1.6)
for f0, lab in zip(fb, ['$f_1$', '$f_2$', '$f_3$']):
    ax.axvline(f0, color=MUTED, ls=':', lw=1)
    ax.annotate(f'{lab}\n{f0:.2f} Hz', (f0, psd[m].max() * 0.6),
                ha='center', fontsize=9, color=INK)
ax.set_xlabel('Frequency (Hz)'); ax.set_ylabel('PSD (g$^2$/Hz)')
ax.set_title('Baseline modal spectrum — three modes (3 DOF)')
ax.set_xlim(0.5, 16); despine(ax)
ax.grid(axis='x', visible=False)
fig.savefig(f'{OUT}/fig01_spectrum.png'); plt.close()

# ===========================================================================
# FIG 02 — detection vs reassembly floor  (error bars = replicate std)
# ===========================================================================
reb = np.array([2.960, 2.958, 2.956, 2.964, 2.967]); mu, sd = reb.mean(), reb.std()
locs = ['base', 'F1', 'F2', 'F3']; lnames = ['Base', 'Floor 1', 'Floor 2', 'Floor 3']
dmg_f1 = {}
for loc in locs:
    vv = [vec(f'{loc}_severe_r{r}')[0] for r in (1, 2, 3) if os.path.isdir(f'{base}/{loc}_severe_r{r}')]
    dmg_f1[loc] = (np.mean(vv), np.std(vv))
fig, ax = plt.subplots(figsize=(6.5, 3.6))
ax.axhspan(mu - 2 * sd, mu + 2 * sd, color=OI['green'], alpha=0.20,
           label='Healthy ±2σ (0.30%)')
ax.axhline(mu, color=OI['green'], lw=1)
ax.scatter(range(5), reb, color=OI['green'], s=22, zorder=4, label='Baseline rebuilds')
for i, loc in enumerate(locs):
    m_, s_ = dmg_f1[loc]
    ax.errorbar(6 + i, m_, yerr=s_, fmt='o', color=OI['vermillion'], ms=8,
                capsize=3, zorder=5)
    ax.annotate(lnames[i], (6 + i, m_), xytext=(0, 9), textcoords='offset points',
                ha='center', fontsize=8, color=INK)
ax.scatter([], [], color=OI['vermillion'], s=60, label='Severe damage (mean ± sd, n=3)')
ax.set_ylabel('$f_1$ (Hz)'); ax.set_ylim(0.9, 3.25)
ax.set_xticks([]); ax.set_xlabel('measurement')
ax.set_title('Detection: severe damage vs the 0.30% reassembly floor')
ax.set_xlim(-0.5, 9.8)
ax.legend(loc='lower left'); despine(ax); ax.grid(axis='x', visible=False)
fig.savefig(f'{OUT}/fig02_detection.png'); plt.close()

# ===========================================================================
# FIG 03 — gradability (error bars on severe, n=3; lighter grades n=1)
# ===========================================================================
grades = ['trace', 'light', 'moderate', 'severe']; gx = np.arange(4)
sevmap = {'base': 'base_severe_r', 'F1': 'F1_severe_r', 'F2': 'F2_severe_r', 'F3': 'F3_severe_r'}
fig, axes = plt.subplots(2, 2, figsize=(8.6, 6.2), sharex=True)
for si, (loc, ax) in enumerate(zip(locs, axes.ravel())):
    lines = {0: [], 1: [], 2: []}
    for g in grades[:3]:
        f = f'{loc}_{g}_c1'; v = vec(f) if os.path.isdir(f'{base}/{f}') else None
        sh = (v - fb) / fb * 100 if v is not None else [np.nan] * 3
        for mi in range(3): lines[mi].append(sh[mi])
    sm, ss, _ = reps_shift(sevmap[loc], fb)
    for mi, lab in enumerate(['$\\Delta f_1$', '$\\Delta f_2$', '$\\Delta f_3$']):
        y = lines[mi] + [sm[mi]]
        ax.plot(gx, y, '-o', color=MODE[mi], ms=6, lw=1.8, label=lab)
        ax.errorbar([3], [sm[mi]], yerr=[ss[mi]], fmt='o', color=MODE[mi], capsize=3, ms=6)
    ax.set_title(lnames[si]); ax.axhline(0, color=MUTED, lw=0.6)
    ax.set_xticks(gx); ax.set_xticklabels(['trace\n⅛t', 'light\n½t', 'mod\n1t', 'severe\n3t'])
    if si % 2 == 0: ax.set_ylabel('Frequency shift (%)')
    if si == 0: ax.legend(ncol=3, loc='lower left')
    despine(ax); ax.grid(axis='x', visible=False)
fig.suptitle('Gradability: modal shift vs damage grade, per storey', fontweight='bold', y=1.0)
fig.text(0.5, -0.02, 'error bars = replicate sd on severe (n=3); lighter grades single-cycle (n=1)',
         ha='center', fontsize=8, color=MUTED)
fig.tight_layout(); fig.savefig(f'{OUT}/fig03_gradability.png'); plt.close()

# ===========================================================================
# FIG 04 — localisation fingerprints (error bars = replicate sd, n=3)
# ===========================================================================
fig, ax = plt.subplots(figsize=(7.0, 3.8)); x = np.arange(4); w = 0.26
for mi, lab in enumerate(['$\\Delta f_1$', '$\\Delta f_2$', '$\\Delta f_3$']):
    means, errs = [], []
    for loc in locs:
        m_, s_, _ = reps_shift(f'{loc}_severe_r', fb); means.append(m_[mi]); errs.append(s_[mi])
    ax.bar(x + (mi - 1) * w, means, w, yerr=errs, capsize=3, label=lab,
           color=MODE[mi], edgecolor='white', linewidth=0.6)
ax.set_xticks(x); ax.set_xticklabels(lnames); ax.axhline(0, color=MUTED, lw=0.6)
ax.set_ylabel('Frequency shift (%)')
ax.set_title('Localisation fingerprints (severe) — the pattern, not one mode')
ax.legend(ncol=3, loc='upper center', bbox_to_anchor=(0.5, -0.12))
despine(ax); ax.grid(axis='x', visible=False)
fig.savefig(f'{OUT}/fig04_fingerprints.png'); plt.close()

# ===========================================================================
# FIG 05 — 3-D signature scatter
# ===========================================================================
from mpl_toolkits.mplot3d import Axes3D  # noqa
fig = plt.figure(figsize=(6.4, 5.2)); ax = fig.add_subplot(111, projection='3d')
for li, loc in enumerate(locs):
    pts = []
    for r in (1, 2, 3):
        f = f'{loc}_severe_r{r}'
        if os.path.isdir(f'{base}/{f}'):
            sh = np.nan_to_num((vec(f) - fb) / fb * 100, nan=0.0); pts.append(sh)
    pts = np.array(pts)
    c = [OI['blue'], OI['orange'], OI['green'], OI['vermillion']][li]
    ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2], color=c, s=55, depthshade=False,
               edgecolor='white', linewidth=0.5, label=lnames[li])
ax.set_xlabel('$\\Delta f_1$ (%)'); ax.set_ylabel('$\\Delta f_2$ (%)'); ax.set_zlabel('$\\Delta f_3$ (%)')
ax.set_title('Damage signatures cluster by location')
ax.legend(loc='upper left', fontsize=8)
ax.view_init(elev=22, azim=-52)
fig.savefig(f'{OUT}/fig05_signature_3d.png'); plt.close()

# ===========================================================================
# FIG 06 — observability heatmap (sequential single hue)
# ===========================================================================
amps = {}
for pos, bl in [('top', 'day7_baseline'), ('F2', 'sensorF2_baseline_day7b'), ('F1', 'sensorF1_baseline')]:
    amps[pos] = ic.modal_amplitudes(f'{base}/{bl}', vec(bl)) * 100
M = np.array([amps['top'], amps['F2'], amps['F1']])
fig, ax = plt.subplots(figsize=(5.6, 3.3))
im = ax.imshow(M, cmap='Blues', aspect='auto', vmin=0, vmax=100)
ax.set_xticks(range(3)); ax.set_xticklabels(['$f_1$ (2.9 Hz)', '$f_2$ (8.1 Hz)', '$f_3$ (12.2 Hz)'])
ax.set_yticks(range(3)); ax.set_yticklabels(['Top (F3)', 'Floor 2', 'Floor 1'])
ax.set_ylabel('Sensor position')
for i in range(3):
    for j in range(3):
        ax.text(j, i, f'{M[i, j]:.0f}%', ha='center', va='center',
                color='white' if M[i, j] > 55 else INK, fontweight='bold')
ax.set_title('Mode observability vs sensor position')
cb = fig.colorbar(im, label='% of strongest mode'); cb.outline.set_visible(False)
for s in ax.spines.values(): s.set_visible(False)
ax.tick_params(length=0)
fig.savefig(f'{OUT}/fig06_observability.png'); plt.close()

# ===========================================================================
# FIG 07 — shift-invariance (error bars = replicate sd, n=3)
# ===========================================================================
BL = {'top': 'day4_baseline', 'F2': 'sensorF2_baseline_day7b', 'F1': 'sensorF1_baseline'}
blv = {k: vec(v) for k, v in BL.items()}
dmgs = ['base', 'F1', 'F3']; dlab = ['Base', 'Floor 1', 'Floor 3']; poss = ['top', 'F2', 'F1']
plab = {'top': 'Top (F3)', 'F2': 'Floor 2', 'F1': 'Floor 1'}
def pos_shift(dmg, pos):
    pre = f'{dmg}_severe_r' if pos == 'top' else f'sensor{pos}_{dmg}_severe_r'
    return reps_shift(pre, blv[pos])
fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.6))
xx = np.arange(3); w = 0.26
for k, (mode, mi) in enumerate([('$\\Delta f_1$', 0), ('$\\Delta f_3$', 2)]):
    ax = axes[k]
    for pi, pos in enumerate(poss):
        vals = [pos_shift(d, pos)[0][mi] for d in dmgs]
        errs = [pos_shift(d, pos)[1][mi] for d in dmgs]
        ax.bar(xx + (pi - 1) * w, vals, w, yerr=errs, capsize=3, label=plab[pos],
               color=list(POS.values())[pi], edgecolor='white', linewidth=0.6)
    ax.set_xticks(xx); ax.set_xticklabels(dlab); ax.set_title(f'{mode} by damage location')
    ax.axhline(0, color=MUTED, lw=0.6); ax.set_ylabel('Frequency shift (%)')
    despine(ax); ax.grid(axis='x', visible=False)
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, title='Sensor on', ncol=3, loc='lower center', bbox_to_anchor=(0.5, -0.06))
fig.suptitle('Damage shifts are invariant to sensor position', fontweight='bold')
fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(f'{OUT}/fig07_shift_invariance.png'); plt.close()

# ===========================================================================
# FIG 08 — base-vs-Floor1 discriminator (error bars, n=3)
# ===========================================================================
fig, ax = plt.subplots(figsize=(5.6, 3.6))
for pi, pos in enumerate(poss):
    bm, bs, _ = pos_shift('base', pos); fm, fs, _ = pos_shift('F1', pos)
    ax.errorbar([0, 1], [bm[2], fm[2]], yerr=[bs[2], fs[2]], fmt='-o',
                color=list(POS.values())[pi], ms=8, lw=2, capsize=3, label=plab[pos])
ax.set_xticks([0, 1]); ax.set_xticklabels(['Base damage', 'Floor 1 damage']); ax.set_xlim(-0.3, 1.3)
ax.set_ylabel('$\\Delta f_3$ (%) — the discriminator')
ax.set_title('Base vs Floor 1 separates by $f_3$ from every position')
ax.legend(title='Sensor on'); despine(ax); ax.grid(axis='x', visible=False)
fig.savefig(f'{OUT}/fig08_baseVsF1_discriminator.png'); plt.close()

print('wrote:', sorted(os.listdir(OUT)))

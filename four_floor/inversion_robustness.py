"""
inversion_robustness.py — robustness checks behind the Chapter 5 claims
=======================================================================
Five analyses, all on the MEASURED rig captures and the 3-DOF shear model in
simulation/rig_3dof.py. Nothing here reads a .npy, .pth or data/ file, so it
runs on a clean checkout.

    python -m four_floor.inversion_robustness

  A  Monte-Carlo perturbation of the storey-parametrised inversion, plus
     Jacobian conditioning and a multi-start uniqueness check.
  B  Leave-one-out runner-up margins behind the 12-of-12 localisation.
  C  Permutation test replacing the binomial bound.
  D  Plate-parametrised inversion: four hypotheses, one and two free
     parameters, fitted to each measured modal vector.
  F  Tap-to-tap f1 scatter as a damage feature, against a permutation null.

SEED = 0 throughout (rng below), so every number here is reproducible.

MEASUREMENT NOISE. Per-mode 1-sigma reassembly scatter, Table 4.3:
sigma = 0.15 / 0.23 / 0.16 % of the mode frequency. These are the 1-sigma
values, NOT the 2-sigma "reassembly floor" used elsewhere as a detection
threshold.
"""
import json
import os
import sys
import itertools

import numpy as np
from scipy.optimize import least_squares

# interpret_capture imports `toolkit_common` bare, so four_floor/ itself has to
# be importable as well as the repository root.
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

import glob                                                # noqa: E402
import toolkit_common as tk                                # noqa: E402
import interpret_capture as ic                             # noqa: E402
from four_floor.simulation import rig_3dof as R            # noqa: E402

SEED = 0
rng = np.random.default_rng(SEED)

BASE = os.path.join(_HERE, "characterisation")
LOCS = ["base", "F1", "F2", "F3"]
LNAMES = ["Base plate", "Floor 1", "Floor 2", "Floor 3"]
SIGMA_PCT = np.array([0.15, 0.23, 0.16])      # Table 4.3, 1-sigma, per cent
FLOOR_2SD = 2 * SIGMA_PCT                      # the detection floor, for B
N_DRAWS = 1000
N_PERM = 10_000
N_STARTS_BR = 3000     # random starts for branch enumeration

_rel = lambda p: os.path.relpath(os.path.join(BASE, p), _HERE)


def vec(folder):
    return ic.modal_vector(os.path.join(BASE, folder))


def f1_per_tap(folder):
    """Per-tap f1 by the toolkit's Step-1 rule: most prominent peak in the f1
    band, unwindowed. Same definition as make_ch8_figures.f1_per_tap, restated
    here with an absolute path so this script does not depend on the cwd."""
    vals = []
    for p in sorted(glob.glob(os.path.join(BASE, folder, "*_raw.csv"))):
        x, _ = tk.load_raw_series(p)
        fq, ps = tk.raw_psd(x)
        pk = tk.find_spectral_peaks(fq, ps, 0.9, 20.0, n_peaks=8,
                                    prominence_factor=8)
        low = [q for q in pk if 0.9 <= q["f_hz"] <= 3.5]
        if low:
            vals.append(max(low, key=lambda q: q["prominence_ratio"])["f_hz"])
    return np.array(vals)


def rule(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


# --------------------------------------------------------------------------
# Measured data
# --------------------------------------------------------------------------
b4 = vec("day4_baseline")                      # session-matched reference
b6 = vec("day6_baseline")
K_H = R.solve_healthy_stiffness(b4)            # healthy storey stiffnesses

RUNS = {}                                      # loc -> list of (name, modal vector)
for loc in LOCS:
    for r in (1, 2, 3):
        f = f"{loc}_severe_r{r}"
        if os.path.isdir(os.path.join(BASE, f)):
            RUNS.setdefault(loc, []).append((f, vec(f)))
MEAN_VEC = {l: np.nanmean(np.array([v for _, v in RUNS[l]]), axis=0) for l in LOCS}


def invert(f_meas):
    """Unconstrained least-squares storey inversion -> (k/k_healthy, residual Hz).

    Same call the chapter uses. Returns (None, nan) if a mode is unmeasurable:
    the square 3-modes-to-3-stiffnesses problem has no two-mode branch.
    """
    if np.isnan(f_meas).any():
        return None, np.nan
    k = R.solve_healthy_stiffness(f_meas)
    return k / K_H, float(np.abs(R.modes_hz(k) - f_meas).max())


# ==========================================================================
# A. PERTURBATION, CONDITIONING, UNIQUENESS
# ==========================================================================
def analysis_A():
    rule("A. PERTURBATION AND CONDITIONING OF THE STOREY INVERSION")
    print(f"  {N_DRAWS} draws per case; per-mode Gaussian noise at Table 4.3 "
          f"1-sigma = {SIGMA_PCT} %")
    print(f"  baseline held at nominal; k_healthy = {np.round(K_H, 2)}\n")

    print(f"  {'case':11s} {'k1 nominal':>11s} {'k2':>8s} {'k3':>8s}   "
          f"{'P(any k>1)':>11s}  95% intervals")
    out = {}
    for loc in LOCS:
        nom, res = invert(MEAN_VEC[loc])
        if nom is None:
            print(f"  {LNAMES[LOCS.index(loc)]:11s} {'--':>11s} {'--':>8s} "
                  f"{'--':>8s}   {'--':>11s}  f2 unmeasurable: the square "
                  f"3-modes-to-3-stiffnesses problem has no solution")
            out[loc] = None
            continue
        draws = []
        for _ in range(N_DRAWS):
            fp = MEAN_VEC[loc] * (1 + rng.normal(0, SIGMA_PCT / 100, 3))
            kk, _ = invert(fp)
            if kk is not None:
                draws.append(kk)
        draws = np.array(draws)
        p_any = float(np.mean((draws > 1.0).any(axis=1)))
        lo, hi = np.percentile(draws, [2.5, 97.5], axis=0)
        ints = "  ".join(f"k{i+1} [{lo[i]:.3f},{hi[i]:.3f}]" for i in range(3))
        print(f"  {LNAMES[LOCS.index(loc)]:11s} {nom[0]:11.3f} {nom[1]:8.3f} "
              f"{nom[2]:8.3f}   {p_any:11.3f}  {ints}")
        out[loc] = dict(nom=nom, draws=draws, p_any=p_any, lo=lo, hi=hi, res=res)

    print("\n  per-stiffness exceedance, P(k_i > 1):")
    for loc in LOCS:
        if out[loc] is None:
            continue
        p = (out[loc]["draws"] > 1.0).mean(axis=0)
        flag = "   <-- inadmissible in essentially every draw" if p.max() > 0.95 else ""
        print(f"    {LNAMES[LOCS.index(loc)]:11s} "
              + "  ".join(f"k{i+1} {p[i]:.3f}" for i in range(3)) + flag)

    # ---- Jacobian conditioning at each nominal solution -------------------
    print("\n  Jacobian conditioning at the nominal solution")
    print("  (log-log Jacobian d ln f / d ln k: dimensionless relative sensitivity)")
    for loc in LOCS:
        if out[loc] is None:
            continue
        k = out[loc]["nom"] * K_H
        J = np.zeros((3, 3))
        for j in range(3):
            h = 1e-6 * k[j]
            kp, km = k.copy(), k.copy()
            kp[j] += h
            km[j] -= h
            J[:, j] = (R.modes_hz(kp) - R.modes_hz(km)) / (2 * h) * k[j] / R.modes_hz(k)
        s = np.linalg.svd(J, compute_uv=False)
        print(f"    {LNAMES[LOCS.index(loc)]:11s} cond = {s[0] / s[-1]:8.2f}   "
              f"singular values {np.round(s, 4)}")

    # ---- Branch enumeration: is the inversion unique? --------------------
    # Three measured eigenvalues do not determine three chain stiffnesses
    # uniquely (a classical inverse-eigenvalue result). Enumerate every branch
    # reachable from random starts and test each for admissibility, rather than
    # trusting whichever one the default start happens to land on.
    print(f"\n  Branch enumeration: {N_STARTS_BR} random starts, "
          f"k/k_healthy ~ U[0.01, 4.0]^3; a branch counts only if it reaches "
          f"max|dw| < 1e-8 rad/s")
    branches, conv = {}, {}
    for loc in LOCS:
        f_meas = MEAN_VEC[loc]
        if np.isnan(f_meas).any():
            print(f"    {LNAMES[LOCS.index(loc)]:11s} skipped (f2 unmeasurable)")
            continue
        w = 2 * np.pi * f_meas
        hits = []
        for _ in range(N_STARTS_BR):
            k0 = rng.uniform(0.01, 4.0, 3) * K_H
            r = least_squares(lambda k: 2 * np.pi * R.modes_hz(k) - w,
                              k0, method="lm")
            if np.all(r.x > 0) and np.max(np.abs(r.fun)) < 1e-8:
                hits.append(r.x / K_H)
        groups = {}
        for h in hits:
            groups.setdefault(tuple(np.round(h, 3)), []).append(h)
        n_adm = 0
        print(f"    {LNAMES[LOCS.index(loc)]:11s} {len(hits)}/{N_STARTS_BR} starts "
              f"reached an exact fit; {len(groups)} distinct branches")
        rows = []
        for key, grp in sorted(groups.items(), key=lambda t: -len(t[1])):
            m = np.mean(grp, axis=0)
            adm = bool(np.all(m <= 1.0))
            n_adm += adm
            rows.append((m, len(grp), adm))
            print(f"        k/kh={np.round(m, 4)}  n={len(grp):4d}  "
                  f"{'ADMISSIBLE' if adm else 'has k>1'}")
        conv[loc] = (len(hits), N_STARTS_BR)
        print(f"        -> {n_adm} of {len(groups)} branches admissible"
              + ("   <-- NO admissible exact solution" if n_adm == 0 else ""))
        branches[loc] = rows
        # Is the default-start answer even one of them?
        nom = out[loc]["nom"]
        near = min((np.abs(m - nom).max(), i) for i, (m, _, _) in enumerate(rows)) \
            if rows else (np.inf, -1)
        if near[0] > 1e-2:
            print(f"        NOTE: the default-start solution {np.round(nom, 4)} is NOT "
                  f"one of these branches\n              (its residual is "
                  f"{out[loc]['res']:.3f} Hz) -- the optimiser stalls at a "
                  f"degenerate point,\n              it is not that the modes are "
                  f"unreachable")
    # k at 6 dp and the residual computed from the UNROUNDED solution. At 4 dp
    # the stored vector no longer reproduces its own frequencies: recomputing
    # max|df| from a 4-dp k gives ~2e-4 Hz instead of ~1e-14, so any table that
    # prints 3-dp stiffnesses cannot be checked against a machine-precision
    # residual column without saying so.
    dump = {}
    for loc in LOCS:
        e = dict(branches=[
            dict(k=list(np.round(m, 6)), n=int(n), admissible=bool(a),
                 max_df_hz=float(np.abs(R.modes_hz(m * K_H) - MEAN_VEC[loc]).max()))
            for m, n, a in branches.get(loc, [])])
        e["converged_starts"] = (list(conv[loc]) if loc in conv else None)
        if out.get(loc):
            e["nominal"] = list(np.round(out[loc]["nom"], 4))
            e["ci95"] = [list(np.round(out[loc]["lo"], 4)),
                         list(np.round(out[loc]["hi"], 4))]
            e["p_any_gt1"] = out[loc]["p_any"]
        dump[loc] = e
    with open(os.path.join(_HERE, "results_inversion_branches.json"), "w") as f:
        json.dump(dump, f, indent=1)
    print("\n  wrote results_inversion_branches.json")
    return out, branches


# ==========================================================================
# B / C. LEAVE-ONE-OUT MARGINS AND PERMUTATION TEST
# ==========================================================================
def _signatures(modes):
    """Normalised signature per run: |shift| / that mode's 2-sigma floor."""
    names, X, y = [], [], []
    for li, loc in enumerate(LOCS):
        for nm, v in RUNS[loc]:
            sh = np.abs((v - b4) / b4 * 100) / FLOOR_2SD
            names.append(nm)
            X.append(sh[modes])
            y.append(li)
    return names, np.array(X), np.array(y)


def _loo(X, y):
    """Leave-one-out nearest-class-mean. Returns (correct, margins)."""
    correct, margins = [], []
    for i in range(len(X)):
        d = {}
        for c in np.unique(y):
            m = (y == c) & (np.arange(len(X)) != i)
            if m.sum() == 0:
                continue
            d[c] = np.linalg.norm(X[i] - X[m].mean(axis=0))
        order = sorted(d, key=d.get)
        correct.append(order[0] == y[i])
        margins.append(d[order[1]] - d[y[i]] if len(order) > 1 else np.nan)
    return np.array(correct), np.array(margins)


def analysis_BC():
    rule("B. LEAVE-ONE-OUT MARGINS BEHIND THE 12-OF-12")
    results = {}
    for label, modes in [("2-mode (f1, f3)", [0, 2]), ("3-mode (f1, f2, f3)", [0, 1, 2])]:
        names, X, y = _signatures(modes)
        keep = ~np.isnan(X).any(axis=1)
        drop = [names[i] for i in range(len(names)) if not keep[i]]
        Xk, yk, nk = X[keep], y[keep], [n for n, k in zip(names, keep) if k]
        ok, mg = _loo(Xk, yk)
        print(f"\n  {label}: {len(Xk)} of {len(X)} runs usable"
              + (f"   dropped {drop} (f2 void)" if drop else ""))
        print(f"    accuracy {ok.sum()}/{len(ok)}")
        print(f"    runner-up margin: min {np.nanmin(mg):.2f}, median "
              f"{np.nanmedian(mg):.2f}, max {np.nanmax(mg):.2f} floor-units")
        worst = nk[int(np.nanargmin(mg))]
        print(f"    tightest run: {worst} at {np.nanmin(mg):.2f} floor-units")
        cents = {c: Xk[yk == c].mean(axis=0) for c in np.unique(yk)}
        pairs = [(float(np.linalg.norm(cents[a] - cents[b])), LNAMES[a], LNAMES[b])
                 for a, b in itertools.combinations(sorted(cents), 2)]
        dmin = min(pairs)
        print(f"    closest class-mean pair: {dmin[1]} <-> {dmin[2]} = "
              f"{dmin[0]:.1f} floor-units")
        results[label] = dict(X=Xk, y=yk, ok=ok, margins=mg, dmin=dmin[0])

    rule("C. PERMUTATION TEST IN PLACE OF THE BINOMIAL BOUND")
    print(f"  {N_PERM} label shuffles, leave-one-out re-run on each.")
    print("  No independence assumption about the twelve runs.\n")
    for label, res in results.items():
        X, y, obs = res["X"], res["y"], res["ok"].sum()
        hits = 0
        best = []
        for _ in range(N_PERM):
            yp = rng.permutation(y)
            ok, _ = _loo(X, yp)
            best.append(ok.sum())
            if ok.sum() >= obs:
                hits += 1
        best = np.array(best)
        p = (hits + 1) / (N_PERM + 1)          # add-one, so p is never zero
        print(f"  {label}: observed {obs}/{len(y)}; shuffled accuracy "
              f"mean {best.mean():.2f}, max {best.max()}")
        print(f"    shuffles reaching >= observed: {hits}/{N_PERM}   p = {p:.5f}"
              f"   ({'p < 1/(N+1), report as p < %.4f' % (1 / (N_PERM + 1)) if hits == 0 else 'exact'})")
    return results


# ==========================================================================
# D. PLATE-PARAMETRISED INVERSION
# ==========================================================================
# Loosening a plate degrades the columns terminating there. Storey i runs from
# plate i-1 to plate i, so:
PLATE = {                       # hypothesis -> which storeys the scalar acts on
    "base": [0],                # storey 1 only (plus boundary fixity)
    "F1":   [0, 1],             # storeys 1 and 2
    "F2":   [1, 2],             # storeys 2 and 3
    "F3":   [2],                # storey 3 only
}


def _fit_plate(f_meas, storeys, n_par):
    """Fit d (or d1,d2) for one plate hypothesis. Returns (d, rms residual Hz)."""
    obs = ~np.isnan(f_meas)
    if obs.sum() < n_par + 1:                  # keep it over-determined
        return None, np.nan

    def resid(p):
        a = np.ones(3)
        for i, s in enumerate(storeys):
            a[s] = p[min(i, len(p) - 1)] if n_par > 1 else p[0]
        return R.modes_hz(a * K_H)[obs] - f_meas[obs]

    # Multi-start: the 2-parameter surface is not convex.
    best = None
    for s0 in (0.3, 0.7, 1.0):
        r = least_squares(resid, np.full(n_par, s0), bounds=(0.01, 1.5))
        if best is None or np.sum(r.fun ** 2) < np.sum(best.fun ** 2):
            best = r
    return best.x, float(np.sqrt(np.mean(best.fun ** 2)))


def analysis_D():
    rule("D. PLATE-PARAMETRISED INVERSION")
    print("  One scalar per plate hypothesis against up to three measured modes,")
    print("  so every fit is over-determined. Lowest residual = the localisation,")
    print("  fitted d = the severity.\n")
    for n_par in (1, 2):
        print(f"  --- {n_par}-parameter variant ---")
        print(f"  {'measured case':12s} " +
              "".join(f"{'H:' + h:>22s}" for h in PLATE) + "   verdict")
        n_right = 0
        for loc in LOCS:
            f_meas = MEAN_VEC[loc]
            cells, best, bestres = [], None, np.inf
            for h, st in PLATE.items():
                npar = n_par if len(st) > 1 else 1
                d, rms = _fit_plate(f_meas, st, npar)
                if d is None:
                    cells.append(f"{'n/a':>22s}")
                    continue
                cells.append(f"{'d=' + '/'.join(f'{x:.2f}' for x in d) + f' r={rms:.3f}':>22s}")
                if rms < bestres:
                    bestres, best = rms, (h, d)
            ok = best[0] == loc
            n_right += ok
            adm = "admissible" if np.all(best[1] <= 1.0) else "d>1 INADMISSIBLE"
            print(f"  {LNAMES[LOCS.index(loc)]:12s} " + "".join(cells) +
                  f"   -> {best[0]} {'CORRECT' if ok else 'WRONG'}, {adm}")
        print(f"  localisation: {n_right}/4 correct")
        if n_par == 2:
            print("  CAVEAT: the 2-parameter F1 and F2 hypotheses NEST the 1-parameter")
            print("  base and F3 ones (set the second scalar to 1), so their residual")
            print("  can never be larger. Comparing raw residuals across unequal")
            print("  parameter counts is biased toward F1 and F2; only the")
            print("  1-parameter block above is a fair comparison.")
        print()


# ==========================================================================
# F. TAP-TO-TAP SCATTER AS A DAMAGE FEATURE
# ==========================================================================
def _cell_scatter(folder):
    """Within-cell tap-to-tap scatter of f1, as a per cent of that cell's own
    mean. Baseline-free by construction, so graded (day6) and severe (day4)
    cells are directly comparable."""
    v = f1_per_tap(folder)
    return (np.std(v, ddof=1) / np.mean(v) * 100.0, len(v))


def analysis_F():
    rule("F. TAP-TO-TAP f1 SCATTER AS A DAMAGE FEATURE")
    from scipy.stats import spearmanr, kruskal
    GRADES = ["trace", "light", "moderate", "severe"]

    # 16 cells: 4 locations x 4 grades. Severe is the mean of its three
    # replicates' within-replicate scatter, each from 5 taps, so every cell's
    # figure rests on the same 5-tap estimate rather than on a pooled 15.
    rows, per_rep = [], []
    for li, loc in enumerate(LOCS):
        for gi, g in enumerate(GRADES):
            if g != "severe":
                f = f"{loc}_{g}_c1"
                if not os.path.isdir(os.path.join(BASE, f)):
                    continue
                sd, n = _cell_scatter(f)
            else:
                reps = [_cell_scatter(f"{loc}_severe_r{r}")[0] for r in (1, 2, 3)
                        if os.path.isdir(os.path.join(BASE, f"{loc}_severe_r{r}"))]
                for r, val in zip((1, 2, 3), reps):
                    per_rep.append((li, gi, val))
                sd, n = float(np.mean(reps)), 5
            rows.append((li, gi, sd))
            if g != "severe":
                per_rep.append((li, gi, sd))
    L = np.array([r[0] for r in rows])
    G = np.array([r[1] for r in rows])
    S = np.array([r[2] for r in rows])

    print(f"  {len(rows)} cells (4 locations x 4 grades), 5 taps each.")
    print("  Feature = within-cell sd of per-tap f1, as % of that cell's mean.\n")
    print(f"  {'':11s}" + "".join(f"{g:>11s}" for g in GRADES))
    for li, loc in enumerate(LOCS):
        cells = ["%11.3f" % S[(L == li) & (G == gi)][0]
                 if ((L == li) & (G == gi)).any() else f"{'--':>11s}"
                 for gi in range(4)]
        print(f"  {LNAMES[li]:11s}" + "".join(cells))

    # ---- does scatter grow with severity? --------------------------------
    print("\n  Trend with grade (Spearman rank correlation):")
    rho, pv = spearmanr(G, S)
    print(f"    all {len(S)} cells:        rho = {rho:+.3f}   p = {pv:.4f}")
    for li, loc in enumerate(LOCS):
        m = L == li
        if m.sum() >= 3:
            r_, p_ = spearmanr(G[m], S[m])
            print(f"    {LNAMES[li]:16s} rho = {r_:+.3f}   p = {p_:.4f}   "
                  f"({m.sum()} cells)")

    print("\n  Kruskal-Wallis:")
    kg = kruskal(*[S[G == g] for g in np.unique(G)])
    kl = kruskal(*[S[L == l] for l in np.unique(L)])
    print(f"    across grades     H = {kg.statistic:.3f}  p = {kg.pvalue:.4f}")
    print(f"    across locations  H = {kl.statistic:.3f}  p = {kl.pvalue:.4f}")

    # ---- classification, with a permutation null -------------------------
    x = np.log10(S)[:, None]
    print("\n  LOO nearest-class-mean on log10(scatter), permutation null:")
    for name, y in [("grade", G), ("location", L)]:
        ok, _ = _loo(x, y)
        obs = ok.sum()
        hits = sum(1 for _ in range(N_PERM)
                   if _loo(x, rng.permutation(y))[0].sum() >= obs)
        pp = (hits + 1) / (N_PERM + 1)
        ch = 1.0 / len(np.unique(y))
        print(f"    {name:9s} {obs}/{len(y)} ({obs / len(y):.0%}), chance {ch:.0%}"
              f"   permutation p = {pp:.4f}"
              + ("   significant" if pp < 0.05 else "   NOT significant"))

    # ---- 24 cells, with the replicate structure respected ----------------
    # The three replicates of a severe cell share a label and are correlated,
    # so a plain leave-one-out lets them vote for each other. Hold out the whole
    # group and permute labels at group level, which removes that leakage.
    L2 = np.array([r[0] for r in per_rep])
    G2 = np.array([r[1] for r in per_rep])
    S2 = np.array([r[2] for r in per_rep])
    GRP = np.array([r[0] * 4 + min(r[1], 3) for r in per_rep])   # one id per cell
    x2 = np.log10(S2)[:, None]

    def loo_grouped(X, y, groups):
        ok = []
        for i in range(len(X)):
            keep = groups != groups[i]
            d = {c: np.linalg.norm(X[i] - X[keep & (y == c)].mean(axis=0))
                 for c in np.unique(y) if (keep & (y == c)).sum()}
            ok.append(min(d, key=d.get) == y[i] if d else False)
        return np.array(ok)

    r2, p2 = spearmanr(G2, S2)
    print(f"\n  {len(S2)} cells (each severe replicate separate), replicate "
          f"structure respected:")
    print(f"    trend with grade  rho = {r2:+.3f}   p = {p2:.4f}")
    ug = np.unique(GRP)
    for name, y in [("grade", G2), ("location", L2)]:
        obs = loo_grouped(x2, y, GRP).sum()
        glab = {g: y[GRP == g][0] for g in ug}
        hits = 0
        for _ in range(N_PERM):
            perm = rng.permutation([glab[g] for g in ug])
            yp = np.array([perm[list(ug).index(g)] for g in GRP])
            if loo_grouped(x2, yp, GRP).sum() >= obs:
                hits += 1
        pp = (hits + 1) / (N_PERM + 1)
        print(f"    {name:9s} grouped LOO {obs}/{len(y)} ({obs / len(y):.0%}), "
              f"chance {1 / len(np.unique(y)):.0%}   group-permutation p = {pp:.4f}"
              + ("   SIGNIFICANT" if pp < 0.05 else "   not significant"))

    # ---- what the feature actually tracks --------------------------------
    base_only = S[L == 0]
    rest = S[L != 0]
    print(f"\n  Base plate cells: {np.round(base_only, 3)}  "
          f"(median {np.median(base_only):.3f})")
    print(f"  All other cells : median {np.median(rest):.3f}, max {rest.max():.3f}")
    print(f"  ratio of medians: {np.median(base_only) / np.median(rest):.1f}x")


if __name__ == "__main__":
    print(f"Chapter 5 robustness checks   (seed {SEED})")
    print(f"  day4_baseline {np.round(b4, 4)} Hz   k_healthy {np.round(K_H, 2)}")
    outA, branches = analysis_A()
    analysis_BC()
    analysis_D()
    analysis_F()

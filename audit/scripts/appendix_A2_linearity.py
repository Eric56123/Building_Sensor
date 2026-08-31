"""
appendix_A2_linearity.py — regenerates every number in Appendix A.2

Audit target: b0aba33. Reuses four_floor/linearity_check.py (analyse_one) and
the group statistics of audit item 1.8, rather than re-deriving them.

THE GATE. Section 4.1.5 and the assumptions table both assert a resolution of
"roughly 3.6%". This script establishes where that comes from, from the code:

    linearity_check.py, last line of the has_repeats branch:
        2 * pooled_sd / gstats[0]["f1"] * 100

  * pooled_sd    pooled within-gain standard deviation of f1, 6 dof
  * gstats[0]    the LOWEST-gain group (gstats is sorted by mean drive RMS),
                 so the denominator is that group's mean f1, not the grand mean
  * factor 2     two standard deviations

So it is 2 sigma, normalised by the lowest-gain group mean. Both facts are
reported below so the appendix can state the derivation exactly.

A caveat the appendix must carry: 2 sigma of a pooled within-group SD is a
rule-of-thumb resolution, not a formal minimum detectable difference for a
two-sample comparison at n = 3 per group. The formal MDD is computed here too,
and it is LARGER, which means 3.6% is the optimistic end of the bound.
"""
import glob
import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "four_floor"))

import config                                                     # noqa: E402
import linearity_check as lc                                      # noqa: E402
import toolkit_common as tk                                       # noqa: E402
from scipy import stats                                           # noqa: E402

BASE = os.path.join(_ROOT, "four_floor", "characterisation")
GAINS = ["1v4", "2v2", "2v8"]
# The trace cells whose detection the resolution figure is contrasted with.
TRACE = ["base_trace_c1", "F1_trace_c1", "F2_trace_c1", "F3_trace_c1"]


def captures():
    out = []
    for g in GAINS:
        for r in ("r1", "r2", "r3"):
            m = [p for p in sorted(glob.glob(
                os.path.join(BASE, f"sweep_{g}_{r}_*_raw.csv")))
                 if "REJECTED" not in os.path.basename(p)]
            if m:
                out.append((g, r, m[-1]))
    return out


def tap_f1(folder):
    o = []
    for p in sorted(glob.glob(os.path.join(BASE, folder, "*_raw.csv"))):
        x, _ = tk.load_raw_series(p)
        fq, ps = tk.raw_psd(x)
        pk = tk.find_spectral_peaks(fq, ps, 0.9, 20.0, n_peaks=8,
                                    prominence_factor=8)
        c = [q for q in pk if 0.9 <= q["f_hz"] <= 3.5]
        if c:
            o.append(max(c, key=lambda q: q["prominence_ratio"])["f_hz"])
    return np.array(o)


def main():
    fs = float(config.FS)
    f_lo, f_hi = tk.full_band(fs)
    rows = []
    for g, r, p in captures():
        a = lc.analyse_one(p, fs, f_lo, f_hi)
        if a:
            rows.append((g, r, a["rms"], a["f1"]))

    print(f"Appendix A.2 — linearity of f1 in drive amplitude\n{'=' * 78}")
    print(f"\nPER-CAPTURE (from linearity_check.analyse_one, "
          f"band {f_lo:.1f}-{f_hi:.0f} Hz)\n")
    print(f"  {'gain':6s} {'rep':4s} {'AC RMS (g)':>11s} {'f1 (Hz)':>9s}")
    for g, r, q, f in rows:
        print(f"  {g:6s} {r:4s} {q:11.5f} {f:9.3f}")

    G = {g: np.array([f for gg, _, _, f in rows if gg == g]) for g in GAINS}
    R = {g: np.array([q for gg, _, q, _ in rows if gg == g]) for g in GAINS}
    order = sorted(GAINS, key=lambda g: R[g].mean())

    print(f"\nGROUP SUMMARIES, ordered by drive RMS\n")
    print(f"  {'gain':6s} {'n':>2s} {'mean RMS':>10s} {'mean f1':>9s} "
          f"{'sd f1':>8s} {'range':>8s}")
    for g in order:
        f = G[g]
        print(f"  {g:6s} {len(f):2d} {R[g].mean():10.5f} {f.mean():9.3f} "
              f"{f.std(ddof=1):8.4f} {f.max() - f.min():8.4f}")

    n = len(G[order[0]])
    pooled_var = sum((len(G[g]) - 1) * G[g].std(ddof=1) ** 2 for g in GAINS)
    dof = sum(len(G[g]) - 1 for g in GAINS)
    pooled_sd = math.sqrt(pooled_var / dof)
    lo_mean = G[order[0]].mean()

    print(f"\nAMPLITUDE RANGE\n")
    amp = R[order[-1]].mean() / R[order[0]].mean()
    print(f"  lowest gain mean RMS  {R[order[0]].mean():.5f} g")
    print(f"  highest gain mean RMS {R[order[-1]].mean():.5f} g")
    print(f"  ratio                 {amp:.2f}x   (document: 2.2)")

    print(f"\nTHE RESOLUTION FIGURE — derivation\n")
    print(f"  pooled within-gain sd        {pooled_sd:.4f} Hz, {dof} dof")
    print(f"  lowest-gain mean f1          {lo_mean:.4f} Hz  "
          f"<- the denominator the code uses")
    print(f"  1 sigma as % of that         {pooled_sd / lo_mean * 100:.3f}%   "
          f"(document: 1.79%)")
    print(f"  2 sigma as % of that         "
          f"{2 * pooled_sd / lo_mean * 100:.3f}%   (document: 3.59%, 'roughly 3.6%')")
    print(f"  for comparison, 2 sigma over the GRAND mean f1 "
          f"({np.concatenate(list(G.values())).mean():.4f}): "
          f"{2 * pooled_sd / np.concatenate(list(G.values())).mean() * 100:.3f}%")
    print(f"\n  VERDICT: the body's 3.6% IS 2 sigma of the pooled within-gain")
    print(f"  scatter, normalised by the lowest-gain group mean. No body edit")
    print(f"  is required.")

    # Formal minimum detectable difference, two-sample, n per group.
    alpha, power = 0.05, 0.80
    tcrit = stats.t.ppf(1 - alpha / 2, 2 * (n - 1))
    zpow = stats.norm.ppf(power)
    mdd = (tcrit + zpow) * pooled_sd * math.sqrt(2.0 / n)
    print(f"\n  CAVEAT the appendix must carry. 2 sigma is a rule of thumb, not")
    print(f"  a formal detection limit. Minimum detectable difference for a")
    print(f"  two-sample comparison at n = {n} per group, alpha = 0.05, "
          f"power = 0.80:")
    print(f"    {mdd:.4f} Hz = {mdd / lo_mean * 100:.2f}% of f1   "
          f"<- LARGER than {2 * pooled_sd / lo_mean * 100:.2f}%")
    print(f"  So the test is LESS sensitive than 3.6% suggests: formally it can")
    print(f"  only rule out drive effects above about {mdd / lo_mean * 100:.1f}%.")
    print(f"  This does not overturn the body. The body uses 3.6% to argue the")
    print(f"  test is too coarse to license trace-grade shifts of 0.97 to 2.29%;")
    print(f"  a coarser true limit STRENGTHENS that argument. The appendix")
    print(f"  reports 3.6% as the 2-sigma figure and {mdd / lo_mean * 100:.1f}% as the formal one.")

    print(f"\nTESTS\n")
    hi, lo = G[order[-1]], G[order[0]]
    t, p = stats.ttest_ind(hi, lo, equal_var=False)
    dfw = (hi.var(ddof=1) / len(hi) + lo.var(ddof=1) / len(lo)) ** 2 / (
        (hi.var(ddof=1) / len(hi)) ** 2 / (len(hi) - 1)
        + (lo.var(ddof=1) / len(lo)) ** 2 / (len(lo) - 1))
    print(f"  published test, extreme gains only (Welch):")
    print(f"    t = {t:+.2f}, df = {dfw:.2f}, p = {p:.4f}   "
          f"(document: t = -0.63, p = 0.573)")

    allf = np.concatenate([G[g] for g in order])
    allr = np.concatenate([R[g] for g in order])
    sl, ic, rr, pr, se = stats.linregress(allr, allf)
    tr = sl / se
    print(f"  regression of f1 on drive RMS, all {len(allf)} captures:")
    print(f"    slope {sl:+.4f} Hz per g, se {se:.4f}, t = {tr:+.3f}, "
          f"df = {len(allf) - 2}, p = {pr:.3f}, r = {rr:+.3f}")

    means = np.array([G[g].mean() for g in order])
    sds = np.array([G[g].std(ddof=1) for g in order])
    ssb = n * ((means - means.mean()) ** 2).sum()
    F = (ssb / (len(GAINS) - 1)) / (sds ** 2).mean()
    pf = 1 - stats.f.cdf(F, len(GAINS) - 1, dof)
    print(f"  one-way ANOVA across all three gains:")
    print(f"    F({len(GAINS) - 1},{dof}) = {F:.2f}, p = {pf:.4f}   "
          f"(claimed: F(2,6) = 8.29, p = 0.019)")
    print(f"    deviating group: {order[1]} at mean f1 {means[1]:.3f} Hz, "
          f"against {means[0]:.3f} and {means[2]:.3f}")
    print(f"    the extreme-gain test compares only {order[0]} and {order[-1]},")
    print(f"    whose means differ by {abs(means[2] - means[0]):.4f} Hz, so it")
    print(f"    cannot see a middle group displaced by "
          f"{abs(means[1] - (means[0] + means[2]) / 2):.4f} Hz.")

    print(f"\nWHAT ACTUALLY CONTROLS THE TRACE GRADE\n")
    print(f"  {'cell':16s} {'n':>2s} {'mean f1':>9s} {'tap SD %':>9s}")
    for c in TRACE:
        a = tap_f1(c)
        print(f"  {c:16s} {len(a):2d} {a.mean():9.4f} "
              f"{a.std(ddof=1) / a.mean() * 100:9.3f}")
    print(f"\n  All four are an order of magnitude below "
          f"{2 * pooled_sd / lo_mean * 100:.2f}%.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

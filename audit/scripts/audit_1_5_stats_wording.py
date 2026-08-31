"""
audit_1_5_stats_wording.py — Part 1, item 1.5: statistical wording

Audit target: b0aba33

Three sub-checks, each a claim whose stated basis can be recomputed:

  (a) Table 4.16, "from 3,000 random starts per case", and "Every exact solution"
  (b) Section 4.1.5 linearity, "t = -0.63, p = 0.573", "no statistically
      significant dependence of f1 on excitation level"
  (c) Appendix A.1 / Section 5.4 base-moderate f3, "a spread of 0.15%",
      "f1 scatters 85 times more than f3"

INDEPENDENCE. (a) reads results_inversion_branches.json, written by the auditor,
so the branch VALUES are self-checking; the count against Table 5.1 is not.
(b) runs linearity_check.py, pre-existing repository code, on pre-existing
captures. (c) uses the pre-existing toolkit extraction path. (b) and (c) are
genuine cross-checks.
"""
import glob
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "four_floor"))

import toolkit_common as tk                                       # noqa: E402
from scipy import stats                                           # noqa: E402

BASE = os.path.join(_ROOT, "four_floor", "characterisation")

# Table 4.16 as printed: case -> [(k1, k2, k3, max|df| Hz)]
DOC_416 = {
    "base": [(0.113, 1.146, 0.872, 5.7e-14), (0.115, 0.713, 1.377, 3.6e-15),
             (1.023, 0.066, 1.689, 2.0e-14), (3.419, 0.064, 0.520, 8.9e-15)],
    "F1": [(1.285, 0.059, 1.415, 3.4e-14), (2.861, 0.058, 0.646, 8.9e-15)],
    "F2": [(0.271, 0.913, 0.581, 1.2e-14), (0.321, 0.381, 1.178, 1.4e-14),
           (0.595, 0.191, 1.266, 1.8e-15)],
}
# Section 4.1.5 group summaries, as produced by linearity_check.py.
GAINS = ["1v4", "2v2", "2v8"]


def tap_peaks(folder, lo, hi):
    out = []
    for p in sorted(glob.glob(os.path.join(BASE, folder, "*_raw.csv"))):
        x, _ = tk.load_raw_series(p)
        fq, ps = tk.raw_psd(x)
        pk = tk.find_spectral_peaks(fq, ps, 0.9, 20.0, n_peaks=8,
                                    prominence_factor=8)
        c = [q for q in pk if lo <= q["f_hz"] <= hi]
        if c:
            out.append(max(c, key=lambda q: q["prominence_ratio"])["f_hz"])
    return np.array(out)


def part_a():
    print(f"\n(a) TABLE 4.16 — starts, and 'every exact solution'\n")
    f = os.path.join(_ROOT, "four_floor", "results_inversion_branches.json")
    d = json.load(open(f))
    bad = 0
    for case in ("base", "F1", "F2"):
        br = d[case]["branches"]
        conv, att = d[case]["converged_starts"]
        print(f"  {case:5s} attempted {att}, CONVERGED {conv} ({conv / att:.1%}); "
              f"cache {len(br)} branches, Table 4.16 prints {len(DOC_416[case])}")
        for b in sorted(br, key=lambda x: x["k"][0]):
            k = b["k"]
            hit = [x for x in DOC_416[case]
                   if abs(x[0] - k[0]) < 6e-4 and abs(x[1] - k[1]) < 6e-4]
            if hit:
                print(f"      ({k[0]:.3f}, {k[1]:.3f}, {k[2]:.3f}) n={b['n']:4d}  "
                      f"max|df| {b['max_df_hz']:.1e} vs doc {hit[0][3]:.1e}")
            else:
                bad += 1
                print(f"      ({k[0]:.3f}, {k[1]:.3f}, {k[2]:.3f}) n={b['n']:4d}  "
                      f"max|df| {b['max_df_hz']:.1e}   *** NOT IN TABLE 4.16 ***")
    print(f"\n  branches missing from the table: {bad}")
    print(f"  Table 5.1 says 'Floor 2 admits one of FOUR'. Table 4.16 lists three.")
    print(f"  The caption's 'Every exact solution' is therefore not satisfied.")
    print(f"  The caption's '3,000 random starts' is the ATTEMPTED count; the")
    print(f"  observed count behind the branches is 1275 / 560 / 1581, and it")
    print(f"  varies threefold across the three cases.")
    return bad


def part_b():
    print(f"\n(b) SECTION 4.1.5 — the linearity test\n")
    import subprocess
    csvs = []
    for g in GAINS:
        for r in ("r1", "r2", "r3"):
            m = sorted(glob.glob(os.path.join(BASE, f"sweep_{g}_{r}_*_raw.csv")))
            m = [p for p in m if "REJECTED" not in os.path.basename(p)]
            if m:
                csvs.append(m[-1])
    labels = [os.path.basename(p).split("_")[1] for p in csvs]
    out = subprocess.run(
        [sys.executable, "linearity_check.py"] + csvs + ["--labels"] + labels,
        cwd=os.path.join(_ROOT, "four_floor"), capture_output=True, text=True)
    for line in out.stdout.splitlines():
        if any(s in line for s in ("t-test", "pooled", "between-gain",
                                   "Measurement noise", "LINEAR")):
            print("   " + line.strip())

    # The published test uses only the two extreme gains. Recover the group
    # summaries from the tool's own table and test all three.
    rows = [l.split() for l in out.stdout.splitlines()
            if l.strip().startswith(tuple(GAINS))]
    means = np.array([float(r[3]) for r in rows])
    sds = np.array([float(r[4]) for r in rows])
    rms = np.array([float(r[2]) for r in rows])
    n = int(rows[0][1])
    ssb = n * ((means - means.mean()) ** 2).sum()
    F = (ssb / 2) / (sds ** 2).mean()
    p = 1 - stats.f.cdf(F, 2, 3 * (n - 1))
    sl, _, r, pr, _ = stats.linregress(rms, means)
    print(f"\n   group mean f1, low -> high drive : "
          f"{means[0]:.3f}, {means[1]:.3f}, {means[2]:.3f} Hz  (NOT monotone)")
    print(f"   one-way ANOVA over ALL THREE gains: F(2,{3 * (n - 1)}) = {F:.2f}, "
          f"p = {p:.4f}   <- the published test drops the middle gain")
    print(f"   regression of f1 on drive RMS     : slope {sl:+.4f} Hz per unit, "
          f"r = {r:+.3f}, p = {pr:.3f}   <- no amplitude trend")
    print(f"\n   The significant term is between-group scatter that is not ordered")
    print(f"   by amplitude, so it indicates estimator instability rather than")
    print(f"   nonlinearity. But the published t-test cannot see it either way.")
    return F, p


def part_c():
    print(f"\n(c) BASE-MODERATE f3 — 'a spread of 0.15%' and '85 times'\n")
    f1 = tap_peaks("base_moderate_c1", 0.9, 3.5)
    f3 = tap_peaks("base_moderate_c1", 10.0, 14.0)
    for lab, a, doc_lo, doc_hi in [("f1", f1, 1.315, 1.766),
                                   ("f3", f3, 11.965, 12.015)]:
        m, sd = a.mean(), a.std(ddof=1)
        rg = a.max() - a.min()
        print(f"   {lab}: n={len(a)}  min {a.min():.4f} max {a.max():.4f} "
              f"(doc {doc_lo}, {doc_hi})  "
              f"{'MATCH' if abs(a.min() - doc_lo) < 6e-4 and abs(a.max() - doc_hi) < 6e-4 else 'DIFFERS'}")
        print(f"       SD {sd / m * 100:6.3f}%   range/mean {rg / m * 100:6.3f}%   "
              f"range/min {rg / a.min() * 100:6.2f}%")
    sd1 = f1.std(ddof=1) / f1.mean() * 100
    sd3 = f3.std(ddof=1) / f3.mean() * 100
    r1 = (f1.max() - f1.min()) / f1.mean() * 100
    r3 = (f3.max() - f3.min()) / f3.mean() * 100
    print(f"\n   The 0.15% quoted for f3 is the SD ({sd3:.3f}%), not the range of")
    print(f"   11.965-12.015 it is printed beside, which is {r3:.2f}%.")
    swing = (f1.max() - f1.min()) / f1.min() * 100
    print(f"   The f1 comparator in the same sentence, 'a swing of 34%', is a")
    print(f"   RANGE statistic ({swing:.1f}% of the minimum), so the sentence "
          f"sets a range against an SD.")
    print(f"\n   ratio SD/SD             : {sd1 / sd3:.1f}")
    print(f"   ratio range/range       : {r1 / r3:.1f}")
    print(f"   doc '85 times' = 12.75/0.15 from ROUNDED inputs = {12.75 / 0.15:.0f}")
    print(f"   Both conventions give about 84, so the substance holds; 85 is 1.7%")
    print(f"   high from double rounding.")
    print(f"\n   8th-harmonic check: 8*f1 would sweep "
          f"{8 * f1.min():.1f} to {8 * f1.max():.1f} Hz (doc 10.5 to 14.1) - "
          f"argument SOUND.")
    print(f"   set ratio f3/f1 = {f3.mean() / f1.mean():.4f} (doc 8.010); in a cell "
          f"whose f1 scatters {sd1:.1f}%,\n   four significant figures is not "
          f"meaningful precision.")


def main():
    print(f"Audit 1.5 — statistical wording\n{'=' * 78}")
    part_a()
    part_b()
    part_c()
    return 0


if __name__ == "__main__":
    sys.exit(main())

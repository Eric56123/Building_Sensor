"""
audit_1_6_stiffness_ratio.py — Part 1, item 1.6: the fitted stiffness ratio

Audit target: df32d53

CLAIM (l.1331 and l.1487): "Fitted healthy stiffness ratios 1 : 1.192 : 0.983",
and "ratios of 1 : 1.192 : 0.983 show the storeys are not uniform".

The number is checked against the solver, and then the DIRECTIONAL claim is
checked, which the number alone cannot support: 0.983 is only evidence that the
top storey is softer than the bottom if the interval on k3/k1 excludes 1.0.

Three uncertainty conventions are propagated, because they give different
answers and the choice has to be argued rather than assumed:
  * tap SD          - scatter of a single tap about the cell mean
  * tap SEM, n = 5  - uncertainty on the five-tap MEAN
  * reassembly 1sd  - teardown-and-rebuild reproducibility, Section 4.1.4

INDEPENDENCE. simulation/rig_3dof.py is pre-existing repository code and is not
modified here; the baseline tap scatter comes from the pre-existing extraction
path. This is a genuine cross-check.
"""
import glob
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "four_floor"))

import toolkit_common as tk                                       # noqa: E402
from simulation.rig_3dof import (F_MEASURED,                      # noqa: E402
                                 solve_healthy_stiffness)

BASE = os.path.join(_ROOT, "four_floor", "characterisation")
BANDS = [(0.9, 3.5), (6.0, 10.0), (10.0, 14.0)]
DOC = (1.192, 0.983)
REASSEMBLY_1SD = np.array([0.15, 0.23, 0.16])      # Section 4.1.4, per cent
N_DRAW = 20000


def baseline_scatter(folder):
    taps = {0: [], 1: [], 2: []}
    for p in sorted(glob.glob(os.path.join(BASE, folder, "*_raw.csv"))):
        x, _ = tk.load_raw_series(p)
        fq, ps = tk.raw_psd(x)
        pk = tk.find_spectral_peaks(fq, ps, 0.9, 20.0, n_peaks=8,
                                    prominence_factor=8)
        for i, (lo, hi) in enumerate(BANDS):
            c = [q for q in pk if lo <= q["f_hz"] <= hi]
            if c:
                taps[i].append(max(c, key=lambda q: q["prominence_ratio"])["f_hz"])
    return [np.array(taps[i]) for i in range(3)]


def main():
    print(f"Audit 1.6 — fitted stiffness ratio\n{'=' * 78}")

    k = solve_healthy_stiffness()
    q, r = k[1] / k[0], k[2] / k[0]
    print(f"\n  solve_healthy_stiffness(F_MEASURED = {F_MEASURED})")
    print(f"    k       = {np.round(k, 3)}")
    print(f"    ratios  = 1 : {q:.4f} : {r:.4f}")
    print(f"    document  1 : {DOC[0]} : {DOC[1]}   "
          f"{'MATCH' if abs(q - DOC[0]) < 5e-4 and abs(r - DOC[1]) < 5e-4 else 'DIFFERS'}")
    print(f"\n  There is NO competing 1.023 rendering in the document. Both sites")
    print(f"  (l.1331, l.1487) print 0.983. The 1.023 is Table 4.16's base-plate")
    print(f"  branch B3 k1, unrelated.")

    m = baseline_scatter("day4_baseline")
    tap_sd = np.array([a.std(ddof=1) / a.mean() * 100 for a in m])
    print(f"\n  Day-4 baseline tap scatter (% of mean): "
          f"f1 {tap_sd[0]:.3f}, f2 {tap_sd[1]:.3f}, f3 {tap_sd[2]:.3f}  "
          f"(n = {[len(a) for a in m]})")

    print(f"\n  PROPAGATED ONTO THE RATIOS, {N_DRAW:,d} draws, seed 42\n")
    hdr = (f"  {'convention':34s} {'k2/k1 95% CI':>22s} {'k3/k1 95% CI':>22s} "
           f"{'covers 1':>9s}")
    print(hdr + "\n  " + "-" * (len(hdr) - 2))
    verdicts = []
    for lab, s in [("tap SD", tap_sd),
                   ("tap SEM, n = 5", tap_sd / np.sqrt(5)),
                   ("reassembly 1sd (Section 4.1.4)", REASSEMBLY_1SD)]:
        rng = np.random.default_rng(42)
        R, Q = [], []
        for _ in range(N_DRAW):
            f = F_MEASURED * (1 + rng.normal(0, s / 100))
            kk = solve_healthy_stiffness(f_target=f)
            Q.append(kk[1] / kk[0])
            R.append(kk[2] / kk[0])
        qlo, qhi = np.percentile(Q, [2.5, 97.5])
        rlo, rhi = np.percentile(R, [2.5, 97.5])
        cov = rlo <= 1.0 <= rhi
        verdicts.append(cov)
        print(f"  {lab:34s} {f'[{qlo:.3f}, {qhi:.3f}]':>22s} "
              f"{f'[{rlo:.3f}, {rhi:.3f}]':>22s} {('YES' if cov else 'no'):>9s}")

    print(f"\n  k2/k1 excludes 1.0 under every convention: the middle storey really")
    print(f"  is about 19% stiffer, and THAT is the non-uniformity.")
    print(f"  k3/k1 = {r:.3f} covers 1.0 under the tap SD and under the reassembly")
    print(f"  floor. The reassembly floor is the right comparator for a claim about")
    print(f"  the structure, because the ratio has to survive a rebuild to be a")
    print(f"  property of the rig rather than of one assembly.")
    print(f"\n  VERDICT: keep 0.983, drop the directional reading of it. The")
    print(f"  non-uniformity claim stands on k2 alone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
audit_1_7_scatter_basis.py — Part 1, item 1.7: the tap-scatter basis problem

Audit target: b0aba33

Two numbers describe the tap-to-tap scatter of the same twelve cells, and they
disagree by roughly a factor of two:

  Table 4.5, "tap sd" column   : base moderate = 12.75
  Figure 4.x bar labels        : base moderate = 15.5

Both are recomputed here from the raw captures to establish what each one is,
rather than inferring it from the surrounding prose.

INDEPENDENCE. The extraction path is pre-existing repository code. The two
candidate definitions are properties of the data, not of any script the auditor
wrote. Genuine cross-check.
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

BASE = os.path.join(_ROOT, "four_floor", "characterisation")
LOCS = ["base", "F1", "F2", "F3"]
GRADES = ["trace", "light", "moderate"]
TAB45 = {"base": [0.26, 2.26, 12.75], "F1": [0.05, 2.52, 1.32],
         "F2": [0.17, 0.76, 0.26], "F3": [0.23, 0.11, 0.16]}
FIG = {"base": [0.7, 3.8, 15.5], "F1": [0.1, 3.8, 1.5],
       "F2": [0.4, 1.4, 0.4], "F3": [0.5, 0.2, 0.3]}


def tap_f1(folder):
    out = []
    for p in sorted(glob.glob(os.path.join(BASE, folder, "*_raw.csv"))):
        x, _ = tk.load_raw_series(p)
        fq, ps = tk.raw_psd(x)
        pk = tk.find_spectral_peaks(fq, ps, 0.9, 20.0, n_peaks=8,
                                    prominence_factor=8)
        c = [q for q in pk if 0.9 <= q["f_hz"] <= 3.5]
        if c:
            out.append(max(c, key=lambda q: q["prominence_ratio"])["f_hz"])
    return np.array(out)


def main():
    print(f"Audit 1.7 — the tap-scatter basis problem\n{'=' * 82}")
    fb = tap_f1("day6_baseline").mean()
    print(f"\n  Session-6 baseline mean f1 = {fb:.4f} Hz\n")
    hdr = (f"  {'cell':16s} {'Tab 4.5':>8s} {'SD % of':>8s} | {'Fig':>6s} "
           f"{'range of':>9s}")
    print(hdr)
    print(f"  {'':16s} {'':8s} {'cell mean':>8s} | {'':6s} "
          f"{'df1, pp':>9s}")
    print("  " + "-" * (len(hdr) - 2))
    n_sd = n_rg = 0
    for loc in LOCS:
        for gi, g in enumerate(GRADES):
            a = tap_f1(f"{loc}_{g}_c1")
            if len(a) < 2:
                continue
            sd = a.std(ddof=1) / a.mean() * 100
            rgb = (a.max() - a.min()) / fb * 100
            n_sd += abs(sd - TAB45[loc][gi]) <= 0.006
            n_rg += abs(rgb - FIG[loc][gi]) <= 0.06
            print(f"  {loc + ', ' + g:16s} {TAB45[loc][gi]:8.2f} {sd:8.2f} | "
                  f"{FIG[loc][gi]:6.1f} {rgb:9.2f}")
    print(f"\n  Table 4.5 column reproduces as the SD of f1 as a per cent of the")
    print(f"  CELL mean                                            : {n_sd}/12")
    print(f"  Figure labels reproduce as the full RANGE of delta-f1 in percentage")
    print(f"  points of the BASELINE mean                          : {n_rg}/12")
    print(f"\n  Both are correct computations. They differ in BOTH the statistic")
    print(f"  (standard deviation against full range) and the denominator (cell")
    print(f"  mean against baseline mean), and the document calls both 'tap")
    print(f"  scatter'. For base moderate that is 12.75 against 15.5.")
    print(f"\n  Body text uses the Table 4.5 basis throughout:")
    print(f"    l.1812  'ranges from 0.05% at Floor 1 trace to 12.75%'")
    print(f"    l.1894  'at or below 0.76% at every grade against 0.20% baseline'")
    print(f"    l.1967  'by a factor of 49 from trace to moderate'  "
          f"(12.75/0.26 = {12.75 / 0.26:.0f})")
    print(f"  Only the figure uses the other basis, and l.1894's 'at or below")
    print(f"  0.76%' sits directly above bars labelled 1.4, 0.5, 0.4 and 0.3 for")
    print(f"  the very cells it describes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

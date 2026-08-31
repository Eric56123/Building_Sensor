"""
appendix_A4_A5_tables.py — regenerates Appendix A.4 (per-tap f1) and A.5
(reassembly replicates), and emits both as LaTeX table bodies.

Audit target: b0aba33. Reuses audit/scripts/audit_1_1_sd_vs_sem.py for the
per-tap extraction (tap_f1) and its Table 4.5 reference values, so A.4 is
cross-checked against the printed table by construction rather than by eye.

A.5 uses the same extraction on the five rebuild folders, extended to f2 and f3.
"""
import glob
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _HERE)
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "four_floor"))

import audit_1_1_sd_vs_sem as a11                                 # noqa: E402
import toolkit_common as tk                                       # noqa: E402

BASE = a11.BASE
BANDS = [(0.9, 3.5), (6.0, 10.0), (10.0, 14.0)]
# Keys match audit_1_1_sd_vs_sem.DOC exactly, so the cross-check covers all 13 sets.
PRETTY = {"base": "Base", "F1": "Floor 1", "F2": "Floor 2", "F3": "Floor 3"}


def taps_mode(folder, mi):
    lo, hi = BANDS[mi]
    out = []
    for p in sorted(glob.glob(os.path.join(BASE, folder, "*_raw.csv"))):
        x, _ = tk.load_raw_series(p)
        fq, ps = tk.raw_psd(x)
        pk = tk.find_spectral_peaks(fq, ps, 0.9, 20.0, n_peaks=8,
                                    prominence_factor=8)
        c = [q for q in pk if lo <= q["f_hz"] <= hi]
        out.append(max(c, key=lambda q: q["prominence_ratio"])["f_hz"] if c
                   else np.nan)
    return np.array(out)


def a4():
    print(f"APPENDIX A.4 — per-tap first-mode estimates\n{'=' * 92}")
    sets = [("day6_baseline", "Session baseline")]
    for k in ("base", "F1", "F2", "F3"):
        for g in ("trace", "light", "moderate"):
            sets.append((f"{k}_{g}_c1", f"{PRETTY[k]}, {g}"))

    rows, bad, oddn = [], [], []
    print(f"  {'set':22s} {'t1':>7s} {'t2':>7s} {'t3':>7s} {'t4':>7s} "
          f"{'t5':>7s} {'mean':>8s} {'SD':>7s} {'SD%':>6s} | "
          f"{'doc mean':>8s} {'doc SD%':>7s}")
    for folder, label in sets:
        a = a11.tap_f1(folder)
        if not len(a):
            continue
        if len(a) != 5:
            oddn.append((label, len(a)))
        m, sd = a.mean(), a.std(ddof=1)
        doc = a11.DOC.get(label)
        dm, ds = (doc[0], doc[1]) if doc else (np.nan, np.nan)
        okm = abs(m - dm) < 5e-4 if doc else None
        oks = abs(sd / m * 100 - ds) < 6e-3 if doc else None
        if doc and not (okm and oks):
            bad.append((label, m, dm, sd / m * 100, ds))
        cells = " ".join(f"{v:7.4f}" for v in a) + "        " * (5 - len(a))
        print(f"  {label:22s} {cells} {m:8.4f} {sd:7.4f} "
              f"{sd / m * 100:6.3f} | {dm:8.4f} {ds:7.2f}"
              f"{'' if doc is None or (okm and oks) else '   <-- DIFFERS'}")
        rows.append((label, a, m, sd))

    print(f"\n  cells with n != 5: {oddn if oddn else 'none'}")
    print(f"  cells disagreeing with Table 4.5 at printed precision: "
          f"{len(bad)}")
    for label, m, dm, s, ds in bad:
        print(f"    {label}: mean {m:.4f} vs {dm}, SD% {s:.3f} vs {ds}")
    return rows, bad, oddn


def a5():
    print(f"\n\nAPPENDIX A.5 — reassembly replicates\n{'=' * 92}")
    folders = [f"rebuild{i}" for i in (1, 2, 3, 4, 5)]
    have = [f for f in folders if os.path.isdir(os.path.join(BASE, f))]
    print(f"  rebuild folders on disk: {have}")
    M = {}
    print(f"\n  {'cycle':10s} {'n':>2s} {'f1 (Hz)':>9s} {'f2 (Hz)':>9s} "
          f"{'f3 (Hz)':>9s}")
    for f in have:
        v = []
        for mi in range(3):
            a = taps_mode(f, mi)
            a = a[~np.isnan(a)]
            v.append(a.mean() if len(a) else np.nan)
        M[f] = v
        n = len(a11.tap_f1(f))
        print(f"  {f:10s} {n:2d} {v[0]:9.4f} {v[1]:9.4f} {v[2]:9.4f}")

    A = np.array([M[f] for f in have])
    print(f"\n  {'mode':6s} {'n cycles':>9s} {'mean (Hz)':>10s} "
          f"{'SD (Hz)':>9s} {'1 sigma %':>10s} {'2 sigma %':>10s} {'doc':>6s}")
    DOC = [0.30, 0.46, 0.32]
    out = []
    for mi in range(3):
        col = A[:, mi]
        col = col[~np.isnan(col)]
        m, sd = col.mean(), col.std(ddof=1)
        s1, s2 = sd / m * 100, 2 * sd / m * 100
        out.append((len(col), m, sd, s1, s2))
        print(f"  f{mi + 1:<5d} {len(col):9d} {m:10.4f} {sd:9.5f} "
              f"{s1:10.3f} {s2:10.3f} {DOC[mi]:6.2f}")
    print(f"\n  The floors are 2 x the across-rebuild standard deviation of each")
    print(f"  mode, as a percentage of that mode's across-rebuild mean.")
    return have, M, out


def main():
    rows, bad, oddn = a4()
    have, M, floors = a5()
    print(f"\n\n{'=' * 92}\nLATEX TABLE BODIES\n{'=' * 92}")
    print("\n% --- A.4 body ---")
    for label, a, m, sd in rows:
        cells = " & ".join(f"{v:.4f}" for v in a)
        print(f"{label} & {cells} & {m:.4f} & {sd:.4f} & "
              f"{sd / m * 100:.3f} \\\\")
    print("\n% --- A.5 body, per cycle ---")
    for f in have:
        v = M[f]
        print(f"{f.replace('rebuild', 'Cycle ')} & {v[0]:.4f} & {v[1]:.4f} & "
              f"{v[2]:.4f} \\\\")
    print("\n% --- A.5 body, floors ---")
    for mi, (n, m, sd, s1, s2) in enumerate(floors):
        print(f"$f_{mi + 1}$ & {n} & {m:.4f} & {sd:.5f} & {s1:.3f} & "
              f"{s2:.2f} \\\\")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

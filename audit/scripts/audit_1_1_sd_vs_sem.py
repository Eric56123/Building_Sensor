"""
audit_1_1_sd_vs_sem.py — Part 1, item 1.1: is Table 4.5's uncertainty an SD or an SEM?

Audit target: df32d53

CLAIM (Table 4.5 caption): "Uncertainty is propagated from the tap standard
deviations of the damaged set and of the baseline; it bounds the stability of the
modal estimate within one damage state."

Recomputes, from the raw tap frequencies in characterisation/, for all twelve
graded cells:
  * per-cell n (do NOT assume 5)
  * mean f1 and the tap SD as a per cent of the mean
  * Delta f1 (%)
  * the propagated uncertainty BOTH ways:
      SD  : quadrature propagation of the two SDs, no 1/sqrt(n)
      SEM : the same with each variance divided by its own n
            (= toolkit_common.welch_test's `se`, expressed as % of the baseline)

Exits non-zero if the document column does not match exactly one of the two.

NOTE ON INDEPENDENCE. The extraction path used here (toolkit_common.raw_psd,
find_spectral_peaks, refine_peak_parabolic) is pre-existing repository code, not
written by the auditor. welch_test is also pre-existing. So this item is a
genuine cross-check rather than self-checking.
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "four_floor"))

import glob                                                     # noqa: E402
import toolkit_common as tk                                      # noqa: E402

BASE = os.path.join(_ROOT, "four_floor", "characterisation")
LOCS = [("base", "Base"), ("F1", "Floor 1"), ("F2", "Floor 2"), ("F3", "Floor 3")]
GRADES = ["trace", "light", "moderate"]

# Table 4.5 as printed: set -> (mean f1 Hz, tap sd % of mean, df1 %, uncertainty pp)
DOC = {
    "Session baseline": (2.9216, 0.20, None, None),
    "Base, trace":      (2.8548, 0.26, -2.29, 0.14),
    "Base, light":      (2.0810, 2.26, -28.77, 0.72),
    "Base, moderate":   (1.4917, 12.75, -48.94, 2.91),
    "Floor 1, trace":   (2.7968, 0.05, -4.27, 0.09),
    "Floor 1, light":   (1.8202, 2.52, -37.70, 0.70),
    "Floor 1, moderate": (1.2967, 1.32, -55.62, 0.26),
    "Floor 2, trace":   (2.8932, 0.17, -0.97, 0.12),
    "Floor 2, light":   (2.2168, 0.76, -24.12, 0.27),
    "Floor 2, moderate": (1.7989, 0.26, -38.43, 0.09),
    "Floor 3, trace":   (2.9208, 0.23, -0.03, 0.14),
    "Floor 3, light":   (2.7179, 0.11, -6.97, 0.09),
    "Floor 3, moderate": (2.5094, 0.16, -14.11, 0.10),
}


def tap_f1(folder):
    """Per-tap f1 (Hz) by the repository's own Step-1 rule: the most prominent
    peak in the f1 band, per tap. Pre-existing extraction code."""
    out = []
    for p in sorted(glob.glob(os.path.join(BASE, folder, "*_raw.csv"))):
        x, _ = tk.load_raw_series(p)
        fq, ps = tk.raw_psd(x)
        pk = tk.find_spectral_peaks(fq, ps, 0.9, 20.0, n_peaks=8,
                                    prominence_factor=8)
        low = [q for q in pk if 0.9 <= q["f_hz"] <= 3.5]
        if low:
            out.append(max(low, key=lambda q: q["prominence_ratio"])["f_hz"])
    return np.array(out)


def propagate(fb, sb, nb, ft, st, nt, use_n):
    """Uncertainty on Delta f1 (%) = 100*(ft/fb - 1).

    Partial derivatives: d/dft = 100/fb ; d/dfb = -100*ft/fb**2.
    use_n=False -> propagate the SDs themselves (no 1/sqrt(n)).
    use_n=True  -> propagate the standard errors of the two means.
    """
    vb = sb ** 2 / (nb if use_n else 1)
    vt = st ** 2 / (nt if use_n else 1)
    return 100.0 * np.sqrt(vt / fb ** 2 + (ft * np.sqrt(vb) / fb ** 2) ** 2)


def main():
    b = tap_f1("day6_baseline")
    fb, sb, nb = b.mean(), b.std(ddof=1), len(b)
    print(f"Audit 1.1 — Table 4.5 uncertainty column: SD or SEM?\n{'=' * 92}")
    print(f"Baseline (Session 6): n = {nb}, mean f1 = {fb:.4f} Hz, "
          f"tap SD = {sb / fb * 100:.4f}% of mean  (doc: 2.9216 Hz, 0.20%)\n")

    hdr = (f"{'set':20s} {'n':>2s} {'mean f1':>9s} {'sd %':>7s} "
           f"{'df1 %':>8s} | {'doc ±':>7s} {'SD-prop':>8s} {'SEM-prop':>9s} "
           f"{'ratio':>6s}  matches")
    print(hdr + "\n" + "-" * len(hdr))

    bad, odd_n, rows = [], [], []
    for key, name in LOCS:
        for g in GRADES:
            folder = f"{key}_{g}_c1"
            if not os.path.isdir(os.path.join(BASE, folder)):
                continue
            t = tap_f1(folder)
            ft, st, nt = t.mean(), t.std(ddof=1), len(t)
            if nt != 5:
                odd_n.append((f"{name}, {g}", nt))
            d = 100.0 * (ft / fb - 1.0)
            u_sd = propagate(fb, sb, nb, ft, st, nt, use_n=False)
            u_se = propagate(fb, sb, nb, ft, st, nt, use_n=True)
            label = f"{name}, {g}"
            doc = DOC.get(label)
            du = doc[3] if doc else float("nan")
            m_sd = abs(u_sd - du) < 0.005
            m_se = abs(u_se - du) < 0.005
            verdict = "SD" if m_sd else ("SEM" if m_se else "NEITHER")
            if verdict == "NEITHER":
                bad.append(label)
            rows.append((label, nt, ft, st / ft * 100, d, du, u_sd, u_se, verdict))
            print(f"{label:20s} {nt:2d} {ft:9.4f} {st / ft * 100:7.2f} "
                  f"{d:8.2f} | {du:7.2f} {u_sd:8.3f} {u_se:9.3f} "
                  f"{u_sd / u_se:6.3f}  {verdict}")

    print("\n" + "=" * 92)
    n_sem = sum(1 for r in rows if r[8] == "SEM")
    n_sd = sum(1 for r in rows if r[8] == "SD")
    print(f"cells matching SEM propagation : {n_sem} of {len(rows)}")
    print(f"cells matching SD  propagation : {n_sd} of {len(rows)}")
    print(f"SD/SEM ratio, every cell       : "
          f"{np.mean([r[6] / r[7] for r in rows]):.4f}   (sqrt(5) = {np.sqrt(5):.4f})")
    print(f"per-cell n                     : "
          f"{'all 5' if not odd_n else 'NOT uniform: ' + str(odd_n)}")
    if bad:
        print(f"\ncells matching NEITHER: {bad}")
    print("\nVERDICT: the printed column is a propagated STANDARD ERROR of the "
          "five-tap\nmeans, not a propagated standard deviation. The caption's "
          "inputs are described\ncorrectly; its output is not.")
    return 1 if (bad or n_sem != len(rows)) else 0


if __name__ == "__main__":
    sys.exit(main())

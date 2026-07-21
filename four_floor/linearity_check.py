"""
linearity_check.py — Does f1 move with drive amplitude?
========================================================
Compare sweeps captured at 2-3 amplifier gains. If the measured f1 shifts with
drive level, the frame is not behaving linearly.

WHY THIS DECIDES THE METHOD
---------------------------
The damage mechanism here is LOOSENED SCREWS, and loose joints are a classic
source of nonlinearity: friction, stick-slip, and rattle all make the effective
stiffness depend on how hard the frame is driven. If f1 falls as amplitude rises,
then:

  * "f1 dropped" no longer means "damage" — it can just mean "driven harder", so
    the damage index is confounded by drive level unless amplitude is held fixed
    to a tolerance you have measured;
  * modal parameters are not properties of the structure alone, and the
    linear-modal assumption underpinning the PINN's physics loss is violated;
  * the previous campaign's 8-10x amplitude variation between run groups could
    have produced apparent "damage" from drive variation alone.

That last point is why this runs on Day 1 rather than later: it tells you whether
the old data's amplitude drift was merely sloppy or actively fatal.

A SHIFT IS NOT AUTOMATICALLY FAILURE. Real structures soften slightly with
amplitude. What matters is whether the shift is small compared with the frequency
change damage produces. This script reports the shift; only a damage run can
supply the comparison.

Usage:
    python3 linearity_check.py sweep_g10_raw.csv sweep_g15_raw.csv sweep_g20_raw.csv
    python3 linearity_check.py *_raw.csv --labels 10dB 15dB 20dB --full-band
"""
import argparse
import os
import sys

import numpy as np

import config
import toolkit_common as tk

# f1 shifting by more than this fraction across the amplitude range is called
# nonlinear. 2% is roughly the point at which the shift becomes comparable with
# the frequency drop a single loosened screw produces, i.e. where it starts to
# confound the measurement rather than merely blur it.
NONLINEAR_TOL = 0.02


def analyse_one(path, fs, f_lo, f_hi):
    x, n_win = tk.load_raw_series(path)
    est = tk.estimate_modal_frequency(x, fs=fs, f_lo=f_lo, f_hi=f_hi, n_peaks=3)
    if not est["peaks"]:
        return None
    strongest = max(est["peaks"], key=lambda p: p["power"])
    zeta = tk.half_power_zeta(est["freqs"], est["psd"], strongest["f_hz"])
    return {
        "path": path,
        "label": os.path.basename(path),
        "f1": est["f1"],                       # lowest peak
        "f_strong": strongest["f_hz"],         # strongest peak
        "rms": tk.rms(x),
        "zeta_hp": zeta,
        "n_peaks": len(est["peaks"]),
        "duration_s": len(x) / fs,
    }


def main():
    ap = argparse.ArgumentParser(description="Check f1 against drive amplitude.")
    ap.add_argument("csvs", nargs="+", help="two or more sweep _raw CSVs")
    ap.add_argument("--labels", nargs="*", default=None,
                    help="a label per CSV (e.g. gain settings)")
    ap.add_argument("--fs", type=float, default=float(config.FS))
    ap.add_argument("--full-band", action="store_true",
                    help="search 0.5 Hz to 0.45*fs instead of the training band")
    ap.add_argument("--f0", type=float, default=None, help="search low edge (Hz)")
    ap.add_argument("--f1", type=float, default=None, help="search high edge (Hz)")
    args = ap.parse_args()

    if len(args.csvs) < 2:
        ap.error("need at least two captures to compare")
    if args.labels and len(args.labels) != len(args.csvs):
        ap.error("--labels must give one label per CSV")

    if args.full_band or (args.f0 is None and args.f1 is None):
        f_lo, f_hi = tk.full_band(args.fs)
        band_desc = f"full band {f_lo:.1f}-{f_hi:.0f} Hz"
    else:
        f_lo = args.f0 if args.f0 is not None else tk.full_band(args.fs)[0]
        f_hi = args.f1 if args.f1 is not None else tk.full_band(args.fs)[1]
        band_desc = f"{f_lo:.1f}-{f_hi:.1f} Hz"

    print("=" * 70)
    print(f"LINEARITY CHECK   {len(args.csvs)} captures, {band_desc}")
    print("=" * 70)

    results = []
    for i, p in enumerate(args.csvs):
        r = analyse_one(p, args.fs, f_lo, f_hi)
        if r is None:
            print(f"\n  {os.path.basename(p)}: no resonance found — skipped.")
            continue
        if args.labels:
            r["label"] = args.labels[i]
        results.append(r)

    if len(results) < 2:
        print("\nFewer than two captures yielded a resonance. Cannot compare.")
        sys.exit(1)

    # ── Group repeats sharing a label ───────────────────────────────────────
    # Repeats at ONE gain measure the estimator's own scatter directly: the drive
    # did not change, so any f1 difference between them is pure noise. That gives
    # a within-group sd to judge the between-group shift against, instead of
    # guessing whether a max-minus-min range is meaningful.
    groups = {}
    for r in results:
        groups.setdefault(r["label"], []).append(r)
    has_repeats = any(len(v) > 1 for v in groups.values())

    if has_repeats:
        print(f"\n  {'gain':<16} {'n':>2} {'mean RMS':>10} {'mean f1':>9} "
              f"{'sd f1':>8} {'spread':>8}")
        print("  " + "-" * 60)
        gstats = []
        for lab, rs in sorted(groups.items(), key=lambda kv: np.mean([r["rms"] for r in kv[1]])):
            f = np.array([r["f1"] for r in rs])
            q = np.array([r["rms"] for r in rs])
            sd = float(f.std(ddof=1)) if len(f) > 1 else float("nan")
            print(f"  {lab[:16]:<16} {len(rs):>2} {q.mean():>10.5f} "
                  f"{f.mean():>9.3f} {sd:>8.4f} "
                  f"{(f.max()-f.min()) if len(f) > 1 else float('nan'):>8.4f}")
            gstats.append({"label": lab, "n": len(rs), "rms": float(q.mean()),
                           "f1": float(f.mean()), "sd": sd, "vals": f})
        print("  " + "-" * 60)

        # Pooled within-gain sd — the measurement noise, measured not assumed.
        pooled_var, dof = 0.0, 0
        for g in gstats:
            if g["n"] > 1:
                pooled_var += (g["n"] - 1) * g["sd"] ** 2
                dof += g["n"] - 1
        pooled_sd = float(np.sqrt(pooled_var / dof)) if dof > 0 else float("nan")
        between = gstats[-1]["f1"] - gstats[0]["f1"]
        print(f"\n  pooled within-gain sd (measurement noise) = {pooled_sd:.4f} Hz "
              f"({dof} dof)")
        print(f"  between-gain change lowest->highest       = {between:+.4f} Hz")

        # Welch t-test between the extreme gains: is the shift bigger than noise?
        if dof > 0 and pooled_sd > 0:
            from scipy.stats import ttest_ind
            lo, hi = gstats[0]["vals"], gstats[-1]["vals"]
            if len(lo) > 1 and len(hi) > 1:
                t, p = ttest_ind(hi, lo, equal_var=False)
                print(f"  t-test (highest vs lowest gain): t = {t:+.2f}, "
                      f"p = {p:.4f}")
                rel_b = abs(between) / gstats[0]["f1"]
                print()
                if p < 0.05 and rel_b > NONLINEAR_TOL:
                    print(f"  [NONLINEAR] f1 changes by {rel_b*100:.2f}% between the "
                          f"extreme gains, and the change is significant "
                          f"(p = {p:.4f}) against the measured noise.")
                    print(f"  f1 {'RISES' if between > 0 else 'FALLS'} with drive — "
                          + ("stiffening (joints bedding in, clearance taking up)."
                             if between > 0 else
                             "softening, the classic friction/slip signature."))
                    print("\n  Hold drive amplitude fixed across ALL runs to a "
                          "tolerance tighter than this, or damage and drive level "
                          "are confounded.")
                elif p < 0.05:
                    print(f"  [LINEAR ENOUGH] The change is statistically real "
                          f"(p = {p:.4f}) but only {rel_b*100:.2f}%, inside the "
                          f"{NONLINEAR_TOL*100:.0f}% tolerance.")
                else:
                    print(f"  [LINEAR] f1 does not change significantly with drive "
                          f"(p = {p:.4f}) across a "
                          f"{gstats[-1]['rms']/gstats[0]['rms']:.1f}x amplitude "
                          "range.")
                    print("  A measured f1 shift can be attributed to damage rather "
                          "than to drive level.")
                print(f"\n  Measurement noise is {pooled_sd:.4f} Hz "
                      f"({pooled_sd/gstats[0]['f1']*100:.2f}%), so this test can "
                      f"only detect shifts above about "
                      f"{2*pooled_sd/gstats[0]['f1']*100:.2f}%.")
                print("=" * 70)
                return

    # Order by drive level (RMS response is the proxy for how hard it was driven).
    results.sort(key=lambda r: r["rms"])

    print(f"\n  {'capture':<26} {'AC RMS (g)':>11} {'f1 (Hz)':>9} "
          f"{'strongest':>10} {'zeta_hp':>9}")
    print("  " + "-" * 68)
    for r in results:
        z = f"{r['zeta_hp'] * 100:.2f}%" if np.isfinite(r["zeta_hp"]) else "n/a"
        print(f"  {r['label'][:26]:<26} {r['rms']:>11.5f} {r['f1']:>9.3f} "
              f"{r['f_strong']:>10.3f} {z:>9}")
    print("  " + "-" * 68)

    f1s = np.array([r["f1"] for r in results])
    rmss = np.array([r["rms"] for r in results])
    f_mean = float(f1s.mean())
    shift = float(f1s.max() - f1s.min())
    rel = shift / f_mean if f_mean > 0 else float("inf")
    amp_ratio = float(rmss.max() / rmss.min()) if rmss.min() > 0 else float("inf")

    print(f"\n  drive amplitude range   {amp_ratio:.1f}x "
          f"({rmss.min():.5f} -> {rmss.max():.5f} g RMS)")
    print(f"  f1 range                {f1s.min():.3f} -> {f1s.max():.3f} Hz")
    print(f"  f1 shift                {shift:.3f} Hz  ({rel * 100:.2f}% of mean)")

    if amp_ratio < 1.5:
        print(f"\n  [INCONCLUSIVE] The captures span only {amp_ratio:.1f}x in "
              "amplitude — too narrow to reveal an amplitude dependence. Repeat "
              "with gains that differ by at least 2-3x in response RMS.")
        sys.exit(0)

    # A max-minus-min shift is not evidence on its own: the f1 estimator has its
    # own scatter, and with a handful of captures the largest and smallest values
    # differ by roughly that scatter whether or not any real trend exists. So test
    # for a MONOTONIC TREND, and size the shift against the scatter about it.
    #
    # (This rig produced 4.76% "nonlinearity" from pure noise: five sweeps gave
    # f1 = 2.84-3.04 Hz with r = +0.195, while ringdown pinned f1 at 2.944 +/-
    # 0.003. Reporting that as a finding would have been wrong.)
    direction = 0.0
    resid_sd = float("nan")
    p_value = float("nan")
    if len(results) >= 3:
        from scipy.stats import pearsonr
        direction, p_value = pearsonr(rmss, f1s)
        direction, p_value = float(direction), float(p_value)
        slope, intercept = np.polyfit(rmss, f1s, 1)
        resid = f1s - (slope * rmss + intercept)
        # ddof=2 for the two fitted parameters
        resid_sd = float(np.sqrt(np.sum(resid ** 2) / max(len(resid) - 2, 1)))
        print(f"  trend correlation       r = {direction:+.3f}   p = {p_value:.3f}"
              f"  (n = {len(results)})")
        print(f"  scatter about the fit     {resid_sd:.4f} Hz")
        if np.isfinite(resid_sd) and resid_sd > 0:
            print(f"  shift / scatter           {shift / resid_sd:.2f}x")
        if len(results) < 5:
            # With n=3 even r=0.99 is not significant (df=1). Three points nearly
            # always look collinear, so a high r from three captures is not
            # evidence — this rig gave r=+0.913 from three sweeps and +0.195 once
            # two more were added.
            print(f"  NOTE: n = {len(results)} is too few to establish a trend. "
                  f"At n=3 even r=0.99 gives p>0.05. Five or more gains, or "
                  "repeats at each gain, are needed for a real verdict.")
    else:
        direction = float(np.sign(f1s[-1] - f1s[0]))
        print("  (only 2 captures — no trend test is possible; treat any shift "
              "as unverified)")

    # A trend must be STATISTICALLY significant, not merely visually monotonic.
    weak_trend = len(results) >= 3 and (abs(direction) < 0.7
                                        or not (p_value < 0.05))
    within_noise = (np.isfinite(resid_sd) and resid_sd > 0
                    and shift < 2.0 * resid_sd)

    print()
    if weak_trend or within_noise:
        print(f"  [INCONCLUSIVE] f1 varies by {rel*100:.2f}%, but this is not "
              "distinguishable from measurement scatter:")
        if weak_trend:
            if abs(direction) < 0.7:
                print(f"    * correlation with drive is only r = {direction:+.3f} "
                      "— the points do not line up with amplitude at all.")
            else:
                print(f"    * the points do line up (r = {direction:+.3f}), but "
                      f"with n = {len(results)} that is not significant "
                      f"(p = {p_value:.3f}). Few points nearly always look "
                      "collinear; this is exactly how a spurious trend appears.")
        if within_noise:
            print(f"    * the shift is {shift/resid_sd:.1f}x the scatter about "
                  "the fit; noise alone routinely produces that.")
        print("\n  To settle it, repeat sweeps AT THE SAME GAIN to measure the")
        print("  estimator's own scatter, then compare. Or use ringdown, which")
        print("  resolves f1 far more precisely than a swept capture does.")
        print("\n  Do NOT report this as nonlinearity — on this evidence the rig is")
        print("  neither shown to be linear nor shown to be nonlinear.")
    elif rel <= NONLINEAR_TOL:
        print(f"  [LINEAR] f1 moves by {rel * 100:.2f}% across a {amp_ratio:.1f}x "
              f"amplitude range — within the {NONLINEAR_TOL * 100:.0f}% tolerance.")
        print("  The linear-modal assumption holds over this range, and a measured "
              "f1 shift can be attributed to damage rather than to drive level.")
    else:
        print(f"  [NONLINEAR] f1 moves by {rel * 100:.2f}% across a "
              f"{amp_ratio:.1f}x amplitude range, exceeding the "
              f"{NONLINEAR_TOL * 100:.0f}% tolerance.")
        if direction < 0:
            print("  f1 FALLS as drive rises — softening, the classic signature of "
                  "friction or slip at the bolted joints.")
        else:
            print("  f1 RISES as drive rises — stiffening, e.g. joints bedding in "
                  "or a mounting taking up clearance.")
        print("\n  Consequences to weigh today:")
        print("    * Drive amplitude must be held fixed across ALL runs, to a "
              "tolerance tighter than this shift, or damage and drive level are "
              "confounded.")
        print("    * The PINN's linear-modal physics loss is only approximate here.")
        print("    * Report the amplitude dependence in the dissertation — it is a "
              "genuine finding about the rig, not a defect in the method.")

    print("\n  Caveat: 'linear' here means only that f1 is amplitude-independent "
          "over the range tested. It says nothing about amplitudes outside it.")
    print("=" * 70)


if __name__ == "__main__":
    main()

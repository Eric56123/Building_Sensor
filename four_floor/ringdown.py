"""
ringdown.py — Damping from free decay (log-decrement)
======================================================
Displace the top floor and let go. The frame rings down, and the rate at which
the oscillation dies away gives the damping ratio zeta directly.

WHY NOT HALF-POWER BANDWIDTH
-----------------------------
The usual alternative reads zeta off the -3 dB width of the resonance peak. On
this rig that is the weaker measurement:

  * Welch smoothing broadens the peak, biasing zeta HIGH, and the bias depends on
    nperseg rather than on the structure.
  * At ~0.1 Hz bin spacing, a lightly damped mode near 10 Hz with zeta ~ 2% has a
    half-power width of only ~0.4 Hz — four bins. Quantisation alone is a large
    fraction of the answer.
  * It needs a clean isolated peak, which a rig with closely spaced modes may not
    give.

Log-decrement uses peak amplitudes in the time domain and has none of those
problems. It is also the standard reported method for scaled-frame experiments,
so the number is comparable with the literature.

zeta feeds the Phase 3 simulation retarget (simulation/damping.py), where it sets
the Rayleigh coefficients — so a biased zeta propagates into every synthetic
training signal.

Usage:
    python3 ringdown.py --capture              # capture on the Pi, then analyse
    python3 ringdown.py --capture --repeats 3  # three taps, with consistency check
    python3 ringdown.py path/to/tap_raw.csv    # analyse an existing capture
    python3 ringdown.py tap_raw.csv --plot
"""
import argparse
import os
import sys

import numpy as np

import config
import toolkit_common as tk


def analyse_file(path, fs, f_lo=None, f_hi=None, quiet=False):
    """Analyse one ringdown capture. Returns the result dict, or None on failure."""
    x, n_win = tk.load_raw_series(path)
    res = tk.analyze_ringdown(x, fs=fs, f_lo=f_lo, f_hi=f_hi)

    if not quiet:
        print(f"\n  {os.path.basename(path)}  "
              f"({n_win} windows, {len(x) / fs:.1f} s)")
    if "error" in res:
        print(f"    FAILED: {res['error']}")
        return None

    zl, ze = res["zeta_logdec"], res["zeta_envfit"]
    print(f"    damped natural freq   f_d  = {res['f_d']:.3f} Hz")
    print(f"    zeta (log-decrement)       = {zl * 100:.3f} %"
          f"   ({res['n_peaks']} peaks used)" if np.isfinite(zl)
          else "    zeta (log-decrement)       = n/a (no usable decaying peaks)")
    print(f"    zeta (envelope fit)        = {ze * 100:.3f} %"
          if np.isfinite(ze) else "    zeta (envelope fit)        = n/a")
    print(f"    fit quality           R^2  = {res['r2']:.4f}")

    if res["agree"]:
        print("    [OK] the two estimates agree within 25% — high confidence.")
    else:
        print("    [WARN] the two estimates DISAGREE by more than 25%. Treat this "
              "tap as low confidence.")

    # R^2 is the single most informative diagnostic here, so interpret it rather
    # than just printing it.
    if np.isfinite(res["r2"]):
        if res["r2"] < 0.90:
            print(f"    [WARN] R^2 = {res['r2']:.3f}: the decay is not a single "
                  "exponential. Usually two modes beating, or the joints are "
                  "behaving nonlinearly (slip/rattle). Inspect with --plot before "
                  "trusting zeta.")
        elif res["r2"] < 0.98:
            print(f"    R^2 = {res['r2']:.3f}: acceptable, mild departure from a "
                  "pure single-mode decay.")
    return res


def summarise(results, rel_tol=0.15):
    """
    Consistency across repeated taps, GROUPED BY MODE.

    A tap excites whichever mode it couples into, and different taps on a
    multi-mode structure ring at different frequencies. Pooling them produces a
    mean that describes no mode at all — on this rig, taps at 8.06 Hz and 2.94 Hz
    averaged to "5.50 Hz, zeta 3.9%", a structure that does not exist, and the
    script then offered to record it.

    So: cluster taps by frequency first, then report statistics WITHIN each
    cluster. Scatter within a mode is a real confidence signal; scatter across
    modes is just evidence that you excited more than one.
    """
    ok = [r for r in results if r and np.isfinite(r["zeta_logdec"])]
    if not ok:
        print("\n  (no taps yielded a usable decay)")
        return None

    # Group by f_d — same fractional-tolerance logic as the spectral peak merge.
    ok.sort(key=lambda r: r["f_d"])
    groups, current = [], [ok[0]]
    for r in ok[1:]:
        if abs(r["f_d"] - current[-1]["f_d"]) <= rel_tol * current[-1]["f_d"]:
            current.append(r)
        else:
            groups.append(current)
            current = [r]
    groups.append(current)

    print("\n" + "=" * 62)
    print(f"{len(ok)} TAP(S) -> {len(groups)} DISTINCT MODE(S)")
    print("=" * 62)
    if len(groups) > 1:
        print("  Different taps rang at different frequencies, so they are grouped")
        print("  by mode. Statistics below are WITHIN each mode, never across.")

    out = []
    for g in groups:
        f = np.array([r["f_d"] for r in g])
        z = np.array([r["zeta_logdec"] for r in g])
        print(f"\n  MODE at {f.mean():.3f} Hz   ({len(g)} tap(s))")
        if len(g) == 1:
            print(f"    f_d  = {f[0]:.3f} Hz")
            print(f"    zeta = {z[0]*100:.3f} %")
            print("    (single tap — no consistency check; repeat to confirm)")
        else:
            print(f"    f_d  = {f.mean():.3f} Hz   sd {f.std(ddof=1):.4f}   "
                  f"spread {f.max()-f.min():.4f} Hz "
                  f"({(f.max()-f.min())/f.mean()*100:.2f}%)")
            print(f"    zeta = {z.mean()*100:.3f} %  sd {z.std(ddof=1)*100:.3f}   "
                  f"spread {(z.max()-z.min())*100:.3f} %")
            cv = float(z.std(ddof=1) / z.mean()) if z.mean() > 0 else float("inf")
            if cv < 0.25:
                print(f"    [OK] zeta scatter {cv*100:.0f}% of the mean — "
                      f"report zeta = {z.mean():.4f} +/- {z.std(ddof=1):.4f}")
            else:
                print(f"    [WARN] zeta scatter {cv*100:.0f}% of the mean — too "
                      "much to quote one value. Inconsistent tap force/location, "
                      "or amplitude-dependent damping (friction at the joints), "
                      "which linearity_check.py would confirm.")
            if f.std(ddof=1) > 0.02 * f.mean():
                print("    [WARN] f_d itself moves between taps — "
                      "amplitude-dependent stiffness.")
        out.append({"f_mean": float(f.mean()), "f_sd": float(f.std(ddof=1)) if len(g) > 1 else 0.0,
                    "zeta_mean": float(z.mean()),
                    "zeta_sd": float(z.std(ddof=1)) if len(g) > 1 else 0.0,
                    "n": len(g)})

    if len(groups) > 1:
        lo, hi = out[0], out[-1]
        print(f"\n  Mode ratio f_hi/f_lo = {hi['f_mean']/lo['f_mean']:.3f}")
        print("  For a uniform 4-storey shear frame the theoretical ratios are")
        print("  1 : 2.88 : 4.41 : 5.41 — a ratio near one of those suggests two")
        print("  modes of the SAME structure; a ratio far from them suggests one")
        print("  of the peaks belongs to something else (mounting, table, rig).")
    return out


def capture_taps(duration_s, repeats, axis, out_dir, fs, label=None,
                 target_amp_mg=None, amp_tol=0.20, amp_retries=5):
    """
    Prompt for each tap, capture it, and analyse as we go.

    With `label`, every tap of this set is written to out_dir/<label>/ and named
    <label>_tapN. That keeps a condition's captures together and removes the
    error-prone post-hoc `mv` glob — which silently failed twice in Day 2, once
    on the damaged set and once on the repaired set, because the timestamp glob
    did not match. For a matrix with many conditions, isolating at capture time
    is the only safe option.

    AMPLITUDE CONTROL (target_amp_mg)
    ---------------------------------
    A loosened joint is NONLINEAR: f1 depends on how hard the rig is struck, so
    uncontrolled tap force confounds a damage comparison. Day 3 showed exactly
    this — damaged sets were tapped 1.3-1.5x harder than the healthy baseline and
    f1 wandered 2.3-2.9 Hz between taps at light damage.

    With target_amp_mg set, a tap whose PEAK RESPONSE falls outside
    target +/- amp_tol is rejected, its file deleted, and the tap re-prompted.
    Only accepted taps reach the analysis, so every condition is measured at the
    same response amplitude.

    Note this deliberately controls RESPONSE amplitude, not tap force: a damaged
    (softer) rig responds more to the same strike, so it must be tapped more
    gently to land in the band. That is the point — the nonlinearity depends on
    how far the joint actually moves.
    """
    from capture_sweep import capture
    import os

    if label:
        out_dir = os.path.join(out_dir, label)
        prefix = label
    else:
        prefix = "ringdown"

    lo_mg = hi_mg = None
    if target_amp_mg:
        lo_mg = target_amp_mg * (1 - amp_tol)
        hi_mg = target_amp_mg * (1 + amp_tol)
        print(f"\n  AMPLITUDE BAND: accept taps peaking {lo_mg:.0f}-{hi_mg:.0f} mg "
              f"(target {target_amp_mg:.0f} +/-{amp_tol*100:.0f}%)")
        print("  Taps outside the band are rejected and re-prompted.")

    paths, amps_mg = [], []
    for i in range(repeats):
        accepted = False
        for attempt in range(amp_retries + 1):
            print("\n" + "-" * 62)
            print(f"TAP {i + 1} of {repeats}" + (f"   [{label}]" if label else "")
                  + (f"   (attempt {attempt + 1})" if attempt else ""))
            print("-" * 62)
            print("  Displace the TOP floor by hand and release cleanly, or tap it once.")
            print("  Release sharply and then DO NOT TOUCH the rig — any contact during")
            print("  the decay adds damping that is yours, not the structure's.")
            print("  The shaker must be OFF.")
            try:
                input(f"\n  Press ENTER, then tap once as the {duration_s:.0f} s "
                      "capture starts... ")
            except (EOFError, KeyboardInterrupt):
                print("\n  Cancelled.")
                return paths
            res = capture(duration_s, axis, f"{prefix}_tap{i + 1}", out_dir,
                          quiet=True, all_axes=False)
            st = next(iter(res.values()))
            peak_mg = st["peak_g"] * 1000.0

            if target_amp_mg is None:
                print(f"    peak {peak_mg:.0f} mg")
                paths.append(st["path"])
                amps_mg.append(peak_mg)
                accepted = True
                break

            if lo_mg <= peak_mg <= hi_mg:
                print(f"    peak {peak_mg:.0f} mg — ACCEPTED (band "
                      f"{lo_mg:.0f}-{hi_mg:.0f})")
                paths.append(st["path"])
                amps_mg.append(peak_mg)
                accepted = True
                break

            # Reject: delete the file so only in-band taps reach the analysis.
            how = "TOO HARD" if peak_mg > hi_mg else "TOO SOFT"
            try:
                os.remove(st["path"])
            except OSError:
                pass
            if attempt < amp_retries:
                print(f"    peak {peak_mg:.0f} mg — REJECTED ({how}, band "
                      f"{lo_mg:.0f}-{hi_mg:.0f}). Tap "
                      f"{'more gently' if peak_mg > hi_mg else 'harder'} "
                      "and repeat this tap.")
            else:
                print(f"    peak {peak_mg:.0f} mg — {how}, and retries exhausted.")
        if not accepted:
            print(f"  ** tap {i + 1} never landed in the amplitude band after "
                  f"{amp_retries + 1} attempts. Set is SHORT by one tap — either "
                  "widen --amp-tol or reconsider the target for this damage "
                  "state (a softer rig responds more to the same strike). **")
    # Per-set amplitude summary. Tap strength is a control variable on a rig with
    # nonlinear joints, so it belongs in the record next to the frequencies — not
    # buried in per-tap chatter. The spread tells you at a glance whether the set
    # is amplitude-consistent enough to compare against another condition.
    if amps_mg:
        a = np.asarray(amps_mg, dtype=float)
        print("\n  " + "-" * 46)
        print("  TAP STRENGTH (peak response, accepted taps)")
        print("  " + "-" * 46)
        for i, v in enumerate(a, 1):
            print(f"    tap {i}: {v:7.0f} mg")
        if len(a) > 1:
            print(f"    mean {a.mean():.0f} mg   sd {a.std(ddof=1):.0f}   "
                  f"range {a.min():.0f}-{a.max():.0f}   "
                  f"spread {(a.max() - a.min()) / a.mean() * 100:.0f}% of mean")
        print("  " + "-" * 46)
    if label:
        print(f"\n  {len(paths)} taps saved to {out_dir}/")
    return paths


def main():
    ap = argparse.ArgumentParser(description="Damping ratio from free decay.")
    ap.add_argument("csv", nargs="?", help="an existing _raw CSV of a tap")
    ap.add_argument("--capture", action="store_true",
                    help="capture on the Pi first (prompts for each tap)")
    ap.add_argument("--repeats", type=int, default=3,
                    help="number of taps when capturing (default: 3)")
    ap.add_argument("--duration", type=float, default=30.0,
                    help="seconds per tap capture (default: 30)")
    ap.add_argument("--axis", default=config.RECORDED_AXIS, choices=["x", "y", "z"])
    ap.add_argument("--fs", type=float, default=float(config.FS))
    ap.add_argument("--f-lo", type=float, default=None,
                    help="low edge of the mode search (default: full band)")
    ap.add_argument("--f-hi", type=float, default=None)
    ap.add_argument("--out-dir", default=tk.CHARACTERISATION_DIR)
    ap.add_argument("--label", default=None,
                    help="name this capture set: taps go to out-dir/<label>/ as "
                         "<label>_tapN. Use for each matrix condition (e.g. "
                         "rebuild1, base_light, F3_severe) so sets never mix.")
    ap.add_argument("--target-amp", type=float, default=None, metavar="MG",
                    help="target PEAK RESPONSE amplitude in mg. Taps outside the "
                         "band are rejected and re-prompted, so every condition is "
                         "measured at the same amplitude. Removes the nonlinear-"
                         "joint confound (f1 depends on how hard the rig is hit).")
    ap.add_argument("--amp-tol", type=float, default=0.20, metavar="FRAC",
                    help="fractional half-width of the amplitude band "
                         "(default 0.20 = +/-20%%)")
    ap.add_argument("--amp-retries", type=int, default=5,
                    help="re-prompts allowed per tap before giving up (default 5)")
    ap.add_argument("--plot", action="store_true",
                    help="write a decay + fit PNG next to each CSV")
    args = ap.parse_args()

    if not args.capture and not args.csv:
        ap.error("give a CSV to analyse, or --capture to record one")

    print("=" * 62)
    print("RINGDOWN — damping by log-decrement")
    print("=" * 62)

    if args.capture:
        try:
            paths = capture_taps(args.duration, args.repeats, args.axis,
                                 args.out_dir, args.fs, label=args.label,
                                 target_amp_mg=args.target_amp,
                                 amp_tol=args.amp_tol,
                                 amp_retries=args.amp_retries)
        except ImportError as e:
            print(f"\nCannot import the hardware driver ({e}). Run on the Pi.")
            sys.exit(1)
    else:
        paths = [args.csv]

    if not paths:
        print("\nNothing captured.")
        sys.exit(1)

    results = []
    for p in paths:
        results.append(analyse_file(p, args.fs, args.f_lo, args.f_hi))
        if args.plot and results[-1]:
            _plot(p, results[-1])

    stats = summarise(results) if len(paths) > 1 else None

    good = [r for r in results if r and np.isfinite(r["zeta_logdec"])]
    if good:
        if stats and len(stats) > 1:
            # More than one mode present: refuse to suggest a single zeta, since
            # which one is mode 1 is a question this script cannot answer.
            print("\n  MORE THAN ONE MODE was excited, so there is no single zeta "
                  "to record. Identify which is mode 1 before recording:")
            for s in stats:
                print(f"    {s['f_mean']:7.3f} Hz -> zeta {s['zeta_mean']:.4f} "
                      f"({s['n']} tap(s))")
        else:
            s = stats[0] if stats else None
            z = s["zeta_mean"] if s else good[0]["zeta_logdec"]
            f = s["f_mean"] if s else good[0]["f_d"]
            n = s["n"] if s else 1
            print(f"\nRecord it:  python3 rig_config.py --set-zeta {z:.4f} "
                  f'--note "ringdown, {n} tap(s), f_d={f:.2f} Hz"')
        print("\nNote f_d is the DAMPED frequency. For zeta below ~5% it differs "
              "from the undamped f1 by under 0.2%, so the sweep's f1 is the value "
              "to record for f1_hz.")
    print("=" * 62)


def _plot(path, res):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(res["t"], res["envelope"], "b", lw=0.8, label="envelope")
    ax.plot(res["t"], res["fit"], "r--", lw=1.5,
            label=f"fit  zeta={res['zeta_envfit'] * 100:.2f}%  R2={res['r2']:.3f}")
    ax.set(xlabel="time since release (s)", ylabel="|analytic| (g)",
           title=f"Ringdown  f_d={res['f_d']:.2f} Hz  {os.path.basename(path)}")
    ax.set_yscale("log")   # a true exponential decay is a straight line here
    ax.legend()
    fig.tight_layout()
    out = os.path.splitext(path)[0] + "_ringdown.png"
    fig.savefig(out, dpi=120)
    print(f"    plot -> {out}")


if __name__ == "__main__":
    main()

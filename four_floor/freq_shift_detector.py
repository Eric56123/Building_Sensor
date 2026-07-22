"""
freq_shift_detector.py — Is the damage-induced modal shift statistically real?
==============================================================================
The classical, no-ML damage detector, and the benchmark the PINN must beat.

Takes a set of BASELINE (undamaged) ringdown captures and a set of TEST (damaged)
captures, extracts each mode from every tap, and asks — per mode — whether the
frequency changed by more than measurement scatter.

WHY RINGDOWN, NOT SWEEP
-----------------------
Day 1 measured the ringdown f1 estimator at 0.14% scatter versus 3.59% for the
sweep. A loosened screw is expected to move f1 by 1-3%. Only the ringdown can see
that, so this tool reads ringdown captures.

WHAT IT REPORTS, PER MODE (f1, f2, f3)
--------------------------------------
  * shift in Hz and %
  * 95% confidence interval on the shift
  * Welch t, Welch-Satterthwaite dof, t_crit, and the significance verdict
  * when NOT significant: the minimum shift the setup could have detected
And separately:
  * the change in zeta1 (damping usually RISES with damage — an independent
    indicator; friction at a loosened joint dissipates more energy)
  * the amplitude ratio, reported apart from the frequency shift so a change in
    how hard the rig was struck cannot be mistaken for a change in frequency

WHY WELCH, NOT STUDENT
----------------------
Damage can change the SCATTER of the measurement, not just its mean (a loose
joint rattles). Welch's test does not assume equal variance between the two sets;
Student's does, and would give a wrong dof and CI here.

Usage:
    python3 freq_shift_detector.py \
        --baseline characterisation/baseline_ringdown*_raw.csv \
        --test     characterisation/damaged_ringdown*_raw.csv \
        --modes 2.937,8.080,12.160
"""
import argparse
import glob
import os
import sys

import numpy as np

import config
import toolkit_common as tk


def find_set_modes(paths, fs, nmodes=3, search=(0.9, 20.0)):
    """
    Discover a capture set's OWN mode frequencies, without assuming Day 1 values.

    Fixed Day-1 anchors fail once damage moves a mode outside its search band —
    severe bottom-storey damage dropped f1 from 2.9 to 1.2 Hz (-59%), far outside
    a +/-25% window, so the anchored search missed it entirely and mislabelled a
    higher mode as f1. This finds each set's modes from the data instead.

    Per tap, take the `nmodes` strongest peaks; the per-tap median of each
    frequency-ordered slot is the set's mode. Returns the mode frequencies,
    lowest first.
    """
    per_tap = []
    for p in paths:
        x, _ = tk.load_raw_series(p)
        freqs, psd = tk.raw_psd(x, fs)
        pk = tk.find_spectral_peaks(freqs, psd, search[0], search[1],
                                    n_peaks=8, prominence_factor=8)
        pk = sorted(pk, key=lambda q: -q["prominence_ratio"])[:nmodes]
        fr = sorted(q["f_hz"] for q in pk)
        if len(fr) == nmodes:
            per_tap.append(fr)
    if not per_tap:
        return []
    return list(np.median(np.array(per_tap), axis=0))


def extract_by_bands(paths, mode_freqs, fs, rel_bw=0.20):
    """
    Strongest peak within a band around each of THIS set's mode frequencies.

    Banding on the set's own modes (not Day 1's) keeps a sideband from being
    picked as the mode — the failure that inflated f2/f3 scatter when modes were
    matched by raw strongest-peak order.
    """
    cols = [[] for _ in mode_freqs]
    for p in paths:
        x, _ = tk.load_raw_series(p)
        freqs, psd = tk.raw_psd(x, fs)
        for i, f0 in enumerate(mode_freqs):
            lo, hi = f0 * (1 - rel_bw), f0 * (1 + rel_bw)
            m = (freqs >= lo) & (freqs <= hi)
            if m.sum() < 3:
                cols[i].append(np.nan)
                continue
            # The set's mode is KNOWN to be in this band, so take the band's
            # argmax and refine it sub-bin. A prominence test would reject a
            # strong peak whose own skirt raises the local median — the failure
            # that lost f1 when banding tightly around a low-frequency mode.
            idx_band = np.where(m)[0]
            j = idx_band[int(np.argmax(psd[m]))]
            cols[i].append(tk.refine_peak_parabolic(freqs, psd, int(j)))
    return [np.array([v for v in c if np.isfinite(v)]) for c in cols]


def extract(paths, targets, fs):
    """
    Per-mode f_d, zeta and peak amplitude for every capture.

    Returns {mode_index: {"f": [...], "zeta": [...]}} plus a parallel list of
    per-file peak amplitudes for the amplitude-ratio check. One row per tap.
    """
    by_mode = {i: {"f": [], "zeta": []} for i in range(len(targets))}
    amps = []
    per_file = []
    for p in paths:
        x, _ = tk.load_raw_series(p)
        amps.append(float(np.abs(x - x.mean()).max()))
        modes = tk.analyze_modes(x, fs=fs, targets=targets)
        row = []
        for i, m in enumerate(modes):
            by_mode[i]["f"].append(m["f_d"])
            # Only keep zeta from a well-resolved decay; a bad fit's zeta is noise.
            by_mode[i]["zeta"].append(m["zeta_logdec"] if m["ok"] else float("nan"))
            row.append(m)
        per_file.append((os.path.basename(p), row))
    return by_mode, amps, per_file


def main():
    ap = argparse.ArgumentParser(description="Statistical modal-shift damage test.")
    ap.add_argument("--baseline", nargs="+", required=True,
                    help="undamaged ringdown _raw CSVs (globs allowed)")
    ap.add_argument("--test", nargs="+", required=True,
                    help="damaged ringdown _raw CSVs (globs allowed)")
    ap.add_argument("--modes", default=None,
                    help="comma-separated expected mode freqs in Hz. Default: "
                         "f1_hz/f2_hz/f3_hz from rig.json.")
    ap.add_argument("--match-by-order", action="store_true",
                    help="discover each set's OWN modes and match baseline mode-k "
                         "to test mode-k by frequency order, instead of anchoring "
                         "on fixed --modes. REQUIRED when damage may shift a mode "
                         "outside a fixed +/-25%% band (e.g. severe damage moved "
                         "f1 -59%%). Use this for damage comparisons.")
    ap.add_argument("--fs", type=float, default=float(config.FS))
    ap.add_argument("--alpha", type=float, default=0.05,
                    help="significance level (default 0.05 -> 95%% CI)")
    ap.add_argument("--floor", type=float, default=None, metavar="PCT",
                    help="reassembly floor in %% (from matrix_analysis "
                         "--repeatability). A shift is only ATTRIBUTABLE to damage "
                         "if it clearly exceeds this, not merely the tap scatter. "
                         "Step 2 uses it to judge whether a light grade resolves.")
    args = ap.parse_args()

    # Globs may arrive pre-expanded by the shell or as literal patterns.
    def expand(pats):
        out = []
        for p in pats:
            g = sorted(glob.glob(p))
            out.extend(g if g else [p])
        return [p for p in out if os.path.exists(p)]

    baseline = expand(args.baseline)
    test = expand(args.test)
    if len(baseline) < 2 or len(test) < 2:
        print(f"ERROR: need >= 2 captures per set (got {len(baseline)} baseline, "
              f"{len(test)} test).")
        sys.exit(2)

    if args.modes:
        targets = [float(v) for v in args.modes.split(",")]
    else:
        rig = tk.load_rig()
        targets = [rig.get(k) for k in ("f1_hz", "f2_hz", "f3_hz")]
        targets = [t for t in targets if t]
        if not targets:
            print("ERROR: no --modes given and rig.json has no f1_hz/f2_hz/f3_hz.")
            sys.exit(2)

    print("=" * 70)
    print("FREQUENCY-SHIFT DAMAGE DETECTOR")
    print(f"  baseline: {len(baseline)} taps   test: {len(test)} taps")
    print(f"  alpha:    {args.alpha}  ({100*(1-args.alpha):.0f}% CI)")

    if args.match_by_order:
        # Each set defines its own modes; match by frequency order. This is the
        # damage-safe path — it does not assume the modes stayed near Day 1.
        b_freqs = find_set_modes(baseline, args.fs)
        t_freqs = find_set_modes(test, args.fs)
        if not b_freqs or not t_freqs:
            print("ERROR: could not identify modes in one set.")
            sys.exit(2)
        nmodes = min(len(b_freqs), len(t_freqs))
        b_freqs, t_freqs = b_freqs[:nmodes], t_freqs[:nmodes]
        print(f"  matched by ORDER (each set's own modes):")
        print(f"    baseline modes: {', '.join(f'{f:.3f}' for f in b_freqs)} Hz")
        print(f"    test     modes: {', '.join(f'{f:.3f}' for f in t_freqs)} Hz")
        print("=" * 70)
        b_cols = extract_by_bands(baseline, b_freqs, args.fs)
        t_cols = extract_by_bands(test, t_freqs, args.fs)
        b_modes = {i: {"f": list(b_cols[i]), "zeta": []} for i in range(nmodes)}
        t_modes = {i: {"f": list(t_cols[i]), "zeta": []} for i in range(nmodes)}
        # damping of mode 1 in each set, from its own f1 band
        for paths, store, f1 in ((baseline, b_modes, b_freqs[0]),
                                 (test, t_modes, t_freqs[0])):
            for p in paths:
                x, _ = tk.load_raw_series(p)
                r = tk.analyze_ringdown(x, fs=args.fs,
                                        f_lo=f1 * 0.8, f_hi=f1 * 1.2)
                store[0]["zeta"].append(
                    r["zeta_logdec"] if "error" not in r and r.get("r2", 0) > 0.85
                    else float("nan"))
        b_amps = [float(np.abs((tk.load_raw_series(p)[0] -
                  tk.load_raw_series(p)[0].mean())).max()) for p in baseline]
        t_amps = [float(np.abs((tk.load_raw_series(p)[0] -
                  tk.load_raw_series(p)[0].mean())).max()) for p in test]
        targets = b_freqs   # for the per-mode header labels
    else:
        print(f"  modes:    {', '.join(f'{t:.3f}' for t in targets)} Hz (fixed)")
        print("  (fixed anchors — if a mode may have shifted >25%, use "
              "--match-by-order)")
        print("=" * 70)
        b_modes, b_amps, _ = extract(baseline, targets, args.fs)
        t_modes, t_amps, _ = extract(test, targets, args.fs)

    any_sig = False
    f1_result = None
    for i, f0 in enumerate(targets):
        name = f"f{i+1}"
        bf = [v for v in b_modes[i]["f"] if np.isfinite(v)]
        tf = [v for v in t_modes[i]["f"] if np.isfinite(v)]
        print(f"\n── {name}  (target {f0:.3f} Hz) " + "─" * 40)
        if len(bf) < 2 or len(tf) < 2:
            print(f"   insufficient resolved taps "
                  f"(baseline {len(bf)}, test {len(tf)}) — mode too weak to test.")
            continue
        r = tk.welch_test(bf, tf, alpha=args.alpha)
        if i == 0:
            f1_result = r
            any_sig = any_sig or r["significant"]
        print(f"   baseline {r['mean_baseline']:.4f} +/- {r['sd_baseline']:.4f} Hz "
              f"(n={r['n_baseline']})")
        print(f"   test     {r['mean_test']:.4f} +/- {r['sd_test']:.4f} Hz "
              f"(n={r['n_test']})")
        print(f"   shift    {r['shift']:+.4f} Hz  ({r['shift_pct']:+.2f}%)")
        print(f"   95% CI   [{r['ci_low']:+.4f}, {r['ci_high']:+.4f}] Hz")
        print(f"   Welch t = {r['t']:+.2f},  dof = {r['dof']:.1f},  "
              f"t_crit = {r['t_crit']:.2f},  p = {r['p']:.4f}")
        print(f"   variance: unequal (Welch) — sd_base={r['sd_baseline']:.4f}, "
              f"sd_test={r['sd_test']:.4f}")
        if r["significant"]:
            print(f"   [SIGNIFICANT] the {name} shift exceeds measurement scatter.")
        else:
            mds = r["t_crit"] * r["se"]
            print(f"   [not significant] a shift would need to exceed "
                  f"{mds:.4f} Hz ({100*mds/r['mean_baseline']:.2f}%) to be caught "
                  "with this scatter and sample size.")
        # Statistical significance vs the tap scatter is necessary but NOT
        # sufficient: a shift smaller than the reassembly floor cannot be told
        # from having taken the rig apart and rebuilt it.
        if args.floor is not None:
            attributable = abs(r["shift_pct"]) > args.floor
            print(f"   vs reassembly floor {args.floor:.2f}%: shift "
                  f"{abs(r['shift_pct']):.2f}% is "
                  + ("ABOVE the floor -> attributable to damage."
                     if attributable else
                     "BELOW/at the floor -> NOT distinguishable from a rebuild."))

    # ── Damping: an independent damage indicator ────────────────────────────
    bz = [v for v in b_modes[0]["zeta"] if np.isfinite(v)]
    tz = [v for v in t_modes[0]["zeta"] if np.isfinite(v)]
    print("\n── zeta1  (independent indicator) " + "─" * 36)
    if len(bz) >= 2 and len(tz) >= 2:
        rz = tk.welch_test(bz, tz, alpha=args.alpha)
        print(f"   baseline {rz['mean_baseline']*100:.3f} +/- "
              f"{rz['sd_baseline']*100:.3f} %")
        print(f"   test     {rz['mean_test']*100:.3f} +/- "
              f"{rz['sd_test']*100:.3f} %")
        print(f"   change   {rz['shift']*100:+.3f} %  (p = {rz['p']:.4f})")
        if rz["significant"]:
            arrow = "ROSE" if rz["shift"] > 0 else "FELL"
            print(f"   [SIGNIFICANT] zeta1 {arrow}. "
                  + ("Rising damping is the expected friction signature of a "
                     "loosened joint — corroborates the frequency evidence."
                     if rz["shift"] > 0 else
                     "Falling damping is unusual for added damage — inspect."))
        else:
            print("   [not significant] no clear damping change.")
    else:
        print("   too few resolved zeta1 values to test.")

    # ── Amplitude ratio, kept separate from frequency ───────────────────────
    print("\n── amplitude (reported apart from frequency) " + "─" * 25)
    ba, ta = np.mean(b_amps), np.mean(t_amps)
    print(f"   baseline peak {ba*1000:.1f} mg, test peak {ta*1000:.1f} mg, "
          f"ratio {ta/ba:.2f}x")
    print("   (A frequency shift is a change in WHERE the energy sits, not how "
          "much. This ratio is shown so the two cannot be conflated — a harder "
          "tap must not read as damage.)")

    print("\n" + "=" * 70)
    if f1_result is not None:
        if f1_result["significant"]:
            print("VERDICT: severe damage produced a significant f1 shift. "
                  "Gate (a) PASSES.")
        else:
            mds = f1_result["t_crit"] * f1_result["se"]
            print("VERDICT: f1 shift NOT significant. Gate (a) FAILS — do not "
                  "run the matrix.")
            print(f"  The setup could detect a shift down to {mds:.4f} Hz "
                  f"({100*mds/f1_result['mean_baseline']:.2f}%). If that floor is "
                  "above the damage effect, the problem is sensitivity; if the "
                  "damage truly moved f1 less than this, it is the mechanism.")
    print("=" * 70)
    sys.exit(0 if any_sig else 1)


if __name__ == "__main__":
    main()

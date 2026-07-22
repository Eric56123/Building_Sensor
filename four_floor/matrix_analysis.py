"""
matrix_analysis.py — Multi-set analyses for the damage campaign
================================================================
Two analyses that compare MANY capture sets, complementing
freq_shift_detector.py (which compares exactly two).

--repeatability  (Day 3 Step 1): the reassembly floor.
    Given N undamaged rebuilds, report the scatter of each mode's mean ACROSS
    rebuilds. That between-rebuild sd (%) is the empirical detection floor: a
    damage grade whose shift does not clearly exceed it cannot be attributed to
    damage rather than to taking the rig apart and putting it back.

    This is NOT the within-set tap scatter (how well one build is measured) —
    it is the build-to-build scatter, which Day 2 could only estimate from a
    single repair cycle. The LARGER of the two floors governs the campaign.

--signatures  (Day 3 Step 3): localisation feasibility.
    Given a baseline and one damaged set per location, report each location's
    modal shift vector (df1, df2, df3) NORMALISED so its largest component is 1.
    If damage at different storeys gives distinguishable normalised vectors, a
    single sensor can localise; if they overlap, it cannot. Reports the pairwise
    angle between signature vectors as the distinguishability measure.

Both use order-matched mode extraction (toolkit_common.set_mode_frequencies),
so they tolerate the large shifts damage produces.

Usage:
    python3 matrix_analysis.py --repeatability \
        characterisation/rebuild1 characterisation/rebuild2 ... [--labels ...]

    python3 matrix_analysis.py --signatures \
        --baseline characterisation/day3_baseline \
        --sets characterisation/S1_severe characterisation/S2_severe characterisation/S3_severe \
        --labels bottom middle top
"""
import argparse
import glob
import os
import sys

import numpy as np

import config
import toolkit_common as tk


def _expand_set(spec):
    """A set may be a directory or a glob; return its _raw CSV list."""
    if os.path.isdir(spec):
        return sorted(glob.glob(os.path.join(spec, "*_raw.csv")))
    g = sorted(glob.glob(spec))
    return g if g else ([spec] if os.path.exists(spec) else [])


def repeatability(set_specs, labels, fs, nmodes=3):
    sets = [_expand_set(s) for s in set_specs]
    labels = labels or [os.path.basename(s.rstrip("/")) for s in set_specs]
    print("=" * 70)
    print(f"REASSEMBLY REPEATABILITY — {len(sets)} rebuilds")
    print("=" * 70)

    # per-rebuild, per-mode mean and within-build sd
    means = {i: [] for i in range(nmodes)}
    print(f"\n  {'rebuild':<16} " + "  ".join(f"f{i+1}(Hz)" for i in range(nmodes)))
    print("  " + "-" * 52)
    for lab, paths in zip(labels, sets):
        if len(paths) < 2:
            print(f"  {lab:<16} (only {len(paths)} taps — skipped)")
            continue
        mfreqs, cols = tk.set_mode_frequencies(paths, fs=fs, nmodes=nmodes)
        row = []
        for i in range(nmodes):
            if i < len(cols) and len(cols[i]):
                mu = float(np.mean(cols[i]))
                means[i].append(mu)
                row.append(f"{mu:7.3f}")
            else:
                row.append("   --  ")
        print(f"  {lab:<16} " + "  ".join(row))

    print("\n  BETWEEN-REBUILD scatter (the reassembly floor):")
    print("  " + "-" * 52)
    floors = {}
    for i in range(nmodes):
        mean, sd, cv = tk.between_group_scatter(means[i])
        floors[i] = cv
        if np.isfinite(sd):
            print(f"    f{i+1}: mean {mean:.3f} Hz, sd {sd:.4f} Hz  "
                  f"-> floor {cv:.2f}%   (n={len(means[i])} rebuilds)")
        else:
            print(f"    f{i+1}: too few rebuilds to estimate")

    f1_floor = floors.get(0, float("nan"))
    print("\n" + "=" * 70)
    if np.isfinite(f1_floor):
        print(f"  f1 reassembly floor = {f1_floor:.2f}%")
        if f1_floor > 2.0:
            print("  GATE FAILS: floor > 2%. The rig is not repeatable enough for "
                  "a graded study — the mounting/damage mechanism needs rethinking "
                  "before spending bench time on a matrix.")
        else:
            print("  GATE PASSES: floor <= 2%. A damage grade must shift f1 by "
                  f"clearly more than {f1_floor:.2f}% to be attributable.")
        print(f"  Use {f1_floor:.2f}% (or {2*f1_floor:.2f}% for a 2-sigma margin) "
              "as the lightest resolvable grade when sizing the matrix.")
    print("=" * 70)
    return floors


def signatures(baseline_spec, set_specs, labels, fs, nmodes=3):
    base = _expand_set(baseline_spec)
    sets = [_expand_set(s) for s in set_specs]
    labels = labels or [os.path.basename(s.rstrip("/")) for s in set_specs]
    if len(base) < 2:
        print("ERROR: baseline set has too few captures.")
        sys.exit(2)

    bfreqs, bcols = tk.set_mode_frequencies(base, fs=fs, nmodes=nmodes)
    bmeans = np.array([np.mean(c) if len(c) else np.nan for c in bcols])

    print("=" * 70)
    print("LOCALISATION SIGNATURES — normalised modal shift per location")
    print("=" * 70)
    print(f"\n  baseline: " + ", ".join(f"f{i+1}={bmeans[i]:.3f}" for i in range(nmodes)) + " Hz")

    vectors = {}
    print(f"\n  {'location':<12} " + "  ".join(f"df{i+1}%" for i in range(nmodes))
          + "   normalised (largest=1)")
    print("  " + "-" * 58)
    for lab, paths in zip(labels, sets):
        if len(paths) < 2:
            print(f"  {lab:<12} (too few taps)")
            continue
        _, cols = tk.set_mode_frequencies(paths, fs=fs, nmodes=nmodes)
        dmeans = np.array([np.mean(c) if len(c) else np.nan for c in cols])
        shifts = (dmeans - bmeans) / bmeans * 100
        norm = shifts / np.max(np.abs(shifts)) if np.any(np.isfinite(shifts)) else shifts
        vectors[lab] = norm
        sh = "  ".join(f"{s:+5.1f}" for s in shifts)
        nm = "  ".join(f"{n:+.2f}" for n in norm)
        print(f"  {lab:<12} {sh}    [{nm}]")

    # Pairwise angle between normalised signature vectors — the distinguishability
    # measure. Near 0 deg = same fingerprint (cannot localise); large = distinct.
    labs = list(vectors)
    if len(labs) >= 2:
        print("\n  Pairwise angle between signatures (0 deg = identical):")
        distinct = True
        for a in range(len(labs)):
            for b in range(a + 1, len(labs)):
                va, vb = vectors[labs[a]], vectors[labs[b]]
                m = np.isfinite(va) & np.isfinite(vb)
                if m.sum() < 2:
                    continue
                cos = float(np.dot(va[m], vb[m]) /
                            (np.linalg.norm(va[m]) * np.linalg.norm(vb[m])))
                cos = max(-1.0, min(1.0, cos))
                ang = np.degrees(np.arccos(cos))
                flag = "distinct" if ang > 15 else "OVERLAP"
                if ang <= 15:
                    distinct = False
                print(f"    {labs[a]:<10} vs {labs[b]:<10}  {ang:5.1f} deg  [{flag}]")
        print("\n" + "=" * 70)
        if distinct:
            print("  Signatures are DISTINGUISHABLE (all pairs > 15 deg). This "
                  "MOTIVATES a localisation study — it does not prove localisation "
                  "(one repeat per location; needs replication).")
        else:
            print("  At least one pair OVERLAPS (< 15 deg). Localisation from these "
                  "modes is not supported — keep the global-detection claim.")
        print("=" * 70)


def main():
    ap = argparse.ArgumentParser(description="Multi-set damage-campaign analyses.")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--repeatability", action="store_true",
                      help="between-rebuild scatter = reassembly floor (Step 1)")
    mode.add_argument("--signatures", action="store_true",
                      help="per-location modal-shift fingerprints (Step 3)")
    ap.add_argument("sets", nargs="*",
                    help="capture sets (dirs or globs) — for --repeatability")
    ap.add_argument("--baseline", help="baseline set (for --signatures)")
    ap.add_argument("--sets", nargs="+", dest="damage_sets",
                    help="damaged sets, one per location (for --signatures)")
    ap.add_argument("--labels", nargs="+", default=None)
    ap.add_argument("--fs", type=float, default=float(config.FS))
    args = ap.parse_args()

    if args.repeatability:
        if len(args.sets) < 2:
            ap.error("--repeatability needs >= 2 rebuild sets")
        repeatability(args.sets, args.labels, args.fs)
    else:
        if not args.baseline or not args.damage_sets:
            ap.error("--signatures needs --baseline and --sets")
        signatures(args.baseline, args.damage_sets, args.labels, args.fs)


if __name__ == "__main__":
    main()

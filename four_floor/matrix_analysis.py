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

    # per-rebuild, per-mode mean; a mode only counts for a rebuild if a majority
    # of that rebuild's taps actually excited it (else its mean is unreliable).
    means = {i: [] for i in range(nmodes)}
    print(f"\n  {'rebuild':<16} " + "  ".join(f"f{i+1}(Hz)" for i in range(nmodes)))
    print("  " + "-" * 52)
    for lab, paths in zip(labels, sets):
        if len(paths) < 2:
            print(f"  {lab:<16} (only {len(paths)} taps — skipped)")
            continue
        mfreqs, cols = tk.set_mode_frequencies(paths, fs=fs, nmodes=nmodes)
        need = max(2, (len(paths) + 1) // 2)   # majority of taps
        row = []
        for i in range(nmodes):
            if i < len(cols) and len(cols[i]) >= need:
                mu = float(np.mean(cols[i]))
                means[i].append(mu)
                row.append(f"{mu:7.3f}")
            elif i < len(cols) and len(cols[i]):
                row.append(f"({len(cols[i])}tap)")   # too weakly excited
            else:
                row.append("   --  ")
        print(f"  {lab:<16} " + "  ".join(row))

    print("\n  BETWEEN-REBUILD scatter (the reassembly floor):")
    print("  " + "-" * 52)
    floors = {}
    for i in range(nmodes):
        mean, sd, cv = tk.between_group_scatter(means[i])
        floors[i] = cv
        if np.isfinite(sd) and len(means[i]) >= 3:
            print(f"    f{i+1}: mean {mean:.3f} Hz, sd {sd:.4f} Hz  "
                  f"-> floor {cv:.2f}%   (n={len(means[i])} rebuilds)")
        elif np.isfinite(sd):
            print(f"    f{i+1}: mean {mean:.3f} Hz, sd {sd:.4f} Hz  "
                  f"-> floor {cv:.2f}%   (n={len(means[i])} — need >=3 to trust)")
        else:
            print(f"    f{i+1}: too few rebuilds with this mode well-excited "
                  f"(n={len(means[i])}) — taps did not consistently ring it")

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


def localisation(baseline_spec, location_specs, fs, nmodes=3, sigma_thresh=3.0):
    """
    Replicated localisation: per-mode shift with replicate error bars, and
    pairwise separability measured in units of that scatter.

    WHY NOT THE NORMALISED-VECTOR ANGLE (--signatures)
    ---------------------------------------------------
    The angle between normalised shift vectors is dominated by whichever mode is
    largest. Base-plate and Floor-1 damage both drive f1 to -1.00 after
    normalisation, so their angle is only 11.5 deg — below the 15 deg
    "distinct" threshold — even though their f3 shifts (-1.7% vs -10.0%) are 41
    replicate-sigma apart. The angle would report OVERLAP on locations that are
    in fact trivially separable.

    So separability is decided PER MODE, in sigma: two locations are
    distinguishable if ANY mode separates by more than `sigma_thresh`. That uses
    the replicate scatter as the yardstick, which is what replication was for.

    location_specs: list of (name, [replicate_dir, ...]).
    """
    base = _expand_set(baseline_spec)
    if len(base) < 2:
        print("ERROR: baseline set has too few captures.")
        sys.exit(2)
    bfreqs, bcols = tk.set_mode_frequencies(base, fs=fs, nmodes=nmodes)
    bm = np.array([np.mean(c) if len(c) else np.nan for c in bcols])

    print("=" * 74)
    print("LOCALISATION — replicated, per-mode separability")
    print("=" * 74)
    print("  baseline: " + ", ".join(f"f{i+1}={bm[i]:.3f}" for i in range(len(bm))) + " Hz")

    results = {}
    print(f"\n  {'location':<10} {'n':>2}  " +
          "  ".join(f"{'df'+str(i+1)+'%':>14}" for i in range(nmodes)))
    print("  " + "-" * 62)
    for name, rep_dirs in location_specs:
        rows = []
        for d in rep_dirs:
            files = _expand_set(d)
            if len(files) < 2:
                continue
            _, cols = tk.set_mode_frequencies(files, fs=fs, nmodes=nmodes)
            susp = getattr(tk.set_mode_frequencies, "last_harmonic_suspect",
                           [False] * len(cols))
            # A set may resolve fewer than nmodes (a top-storey higher mode is a
            # flagged harmonic, or absent). Drop harmonic-suspect modes to NaN so
            # they are NOT reported as real shifts (an f2 read off a 2*f1 harmonic
            # would be a spurious ~-37%), then pad to nmodes.
            row = [(np.mean(c) if (len(c) and not (i < len(susp) and susp[i]))
                    else np.nan) for i, c in enumerate(cols)]
            row += [np.nan] * (nmodes - len(row))
            rows.append(row[:nmodes])
        if not rows:
            print(f"  {name:<10} (no usable replicates)")
            continue
        R = np.array(rows, dtype=float)
        shifts = (R - bm) / bm * 100
        # nan-aware: a mode missing in some replicates still averages over those
        # that have it.
        mu = np.nanmean(shifts, axis=0)
        sd = (np.nanstd(shifts, axis=0, ddof=1) if len(rows) > 1
              else np.zeros(nmodes))
        results[name] = {"mu": mu, "sd": sd, "n": len(rows)}
        cells = "  ".join(
            (f"{mu[i]:+7.1f}+/-{sd[i]:4.1f}" if np.isfinite(mu[i]) else "     --    ")
            for i in range(nmodes))
        print(f"  {name:<10} {len(rows):>2}  {cells}")
    print("  " + "-" * 62)

    names = list(results)
    if len(names) < 2:
        print("\n  (need >= 2 locations to test separability)")
        return results

    print("\n  PAIRWISE SEPARABILITY (per mode, in replicate sigma):")
    print(f"  {'pair':<20} " + "  ".join(f"{'f'+str(i+1):>7}" for i in range(nmodes))
          + "   verdict")
    print("  " + "-" * 62)
    for a in range(len(names)):
        for b in range(a + 1, len(names)):
            A, B = results[names[a]], results[names[b]]
            sig = []
            for i in range(nmodes):
                d = abs(A["mu"][i] - B["mu"][i])
                pooled = float(np.hypot(A["sd"][i], B["sd"][i]))
                sig.append(d / pooled if pooled > 0 else np.inf)
            best = max(sig)
            verdict = ("DISTINCT" if best > sigma_thresh else "not separable")
            cells = "  ".join(f"{s:7.0f}" if np.isfinite(s) else "    inf" for s in sig)
            print(f"  {names[a]+' vs '+names[b]:<20} {cells}   [{verdict}]")
    print("  " + "-" * 62)
    print(f"\n  A pair is DISTINCT if ANY mode separates by > {sigma_thresh:.0f} sigma.")
    print("  Note which mode does the separating — it is often NOT f1. Base-plate")
    print("  and Floor-1 damage differ by only ~4 sigma on f1 but ~41 sigma on f3,")
    print("  so a localisation method using f1 alone would fail to tell them apart.")
    return results


def _parse_location(spec):
    """NAME=GLOB -> (NAME, [dirs...])."""
    if "=" not in spec:
        raise ValueError(f"--location expects NAME=GLOB, got {spec!r}")
    name, pat = spec.split("=", 1)
    dirs = sorted(d for d in glob.glob(pat) if os.path.isdir(d))
    return name, dirs


def main():
    ap = argparse.ArgumentParser(description="Multi-set damage-campaign analyses.")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--repeatability", action="store_true",
                      help="between-rebuild scatter = reassembly floor (Step 1)")
    mode.add_argument("--signatures", action="store_true",
                      help="per-location modal-shift fingerprints (single repeat)")
    mode.add_argument("--localisation", action="store_true",
                      help="REPLICATED localisation: per-mode shift with replicate "
                           "error bars and pairwise separability in sigma. Prefer "
                           "this over --signatures once you have replicates — the "
                           "normalised-vector angle is dominated by the largest "
                           "mode and can report OVERLAP on locations that are "
                           "separable at 40+ sigma on a smaller mode.")
    ap.add_argument("sets", nargs="*",
                    help="capture sets (dirs or globs) — for --repeatability")
    ap.add_argument("--baseline", help="baseline set (for --signatures)")
    ap.add_argument("--sets", nargs="+", dest="damage_sets",
                    help="damaged sets, one per location (for --signatures)")
    ap.add_argument("--location", action="append", default=[], metavar="NAME=GLOB",
                    help="for --localisation: a location and the glob matching its "
                         "replicate directories (repeatable), e.g. "
                         "--location base=characterisation/base_severe_r*")
    ap.add_argument("--sigma", type=float, default=3.0,
                    help="separability threshold in replicate sigma (default 3)")
    ap.add_argument("--labels", nargs="+", default=None)
    ap.add_argument("--fs", type=float, default=float(config.FS))
    args = ap.parse_args()

    if args.localisation:
        if not args.baseline or not args.location:
            ap.error("--localisation needs --baseline and >=1 --location NAME=GLOB")
        locs = [_parse_location(s) for s in args.location]
        localisation(args.baseline, locs, args.fs, sigma_thresh=args.sigma)
    elif args.repeatability:
        if len(args.sets) < 2:
            ap.error("--repeatability needs >= 2 rebuild sets")
        repeatability(args.sets, args.labels, args.fs)
    else:
        if not args.baseline or not args.damage_sets:
            ap.error("--signatures needs --baseline and --sets")
        signatures(args.baseline, args.damage_sets, args.labels, args.fs)


if __name__ == "__main__":
    main()

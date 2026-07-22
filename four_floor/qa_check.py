"""
qa_check.py — Validate a set of captures before trusting them
==============================================================
A gate, not an analysis. Run on the baseline (or damaged) capture set before
feeding it to the detector, to catch problems that would silently corrupt the
comparison: clipping, a bad tap, inconsistent excitation, a missing mode.

Post-hoc it cannot see FIFO overruns (those are only known at capture time and
are not stored in the _raw CSV — watch the capture summary for them). What it can
check from the files:

  * CLIPPING — any samples at the +/-G_RANGE rail. Flattened peaks inject
    harmonics that look like modes.
  * RMS CONSISTENCY — for a set of nominally identical taps/sweeps, a wildly
    different RMS means one capture is not like the others (a mis-tap, a knocked
    cable, a changed gain). That contaminates the between-tap scatter the whole
    detection rests on.
  * DC OFFSET — a large drift means gravity is leaking onto the axis (wrong
    orientation) or the sensor is saturating.
  * MODE PRESENCE — for ringdown captures, that the expected modes actually rang.
    A tap that missed a mode should not silently count as a measurement of it.

Usage:
    python3 qa_check.py characterisation/baseline_ringdown*_raw.csv --ringdown
    python3 qa_check.py characterisation/sweep_*_raw.csv
"""
import argparse
import glob
import os
import sys

import numpy as np

import config
import toolkit_common as tk

# A capture whose RMS is more than this fraction from the set median is an
# outlier — the taps were meant to be alike.
RMS_OUTLIER_FRAC = 0.30
# DC offset above this (g) means the axis is seeing gravity or is saturating.
DC_LIMIT_G = 0.20


def main():
    ap = argparse.ArgumentParser(description="Validate a capture set.")
    ap.add_argument("files", nargs="+", help="_raw CSVs (globs allowed)")
    ap.add_argument("--ringdown", action="store_true",
                    help="also check that expected modes rang (uses --modes)")
    ap.add_argument("--modes", default=None,
                    help="expected mode freqs Hz, comma-separated. "
                         "Default: f1/f2/f3 from rig.json.")
    ap.add_argument("--fs", type=float, default=float(config.FS))
    args = ap.parse_args()

    files = []
    for p in args.files:
        g = sorted(glob.glob(p))
        files.extend(g if g else [p])
    files = [f for f in files if os.path.exists(f)]
    if not files:
        print("ERROR: no matching files.")
        sys.exit(2)

    targets = None
    if args.ringdown:
        if args.modes:
            targets = [float(v) for v in args.modes.split(",")]
        else:
            rig = tk.load_rig()
            targets = [rig[k] for k in ("f1_hz", "f2_hz", "f3_hz") if rig.get(k)]

    print("=" * 70)
    print(f"QA CHECK — {len(files)} capture(s)")
    print("=" * 70)

    rows, problems = [], []
    rail = config.G_RANGE * 0.98
    for p in files:
        x, n = tk.load_raw_series(p)
        rms = tk.rms(x)
        dc = tk.dc_offset(x)
        clip = int(np.sum(np.abs(x) >= rail))
        row = {"file": os.path.basename(p), "rms": rms, "dc": dc, "clip": clip,
               "modes": None}
        if clip:
            problems.append(f"{row['file']}: {clip} clipped samples")
        if abs(dc) > DC_LIMIT_G:
            problems.append(f"{row['file']}: DC offset {dc:+.3f} g "
                            f"(> {DC_LIMIT_G} g)")
        if args.ringdown and targets:
            modes = tk.analyze_modes(x, fs=args.fs, targets=targets)
            resolved = [m["ok"] for m in modes]
            row["modes"] = modes
            missing = [f"f{i+1}" for i, m in enumerate(modes) if not m["ok"]]
            # f3 is expected to be marginal here, so only flag f1/f2 as problems.
            hard = [m for m in missing if m in ("f1", "f2")]
            if hard:
                problems.append(f"{row['file']}: mode(s) {', '.join(hard)} not "
                                "resolved — tap may have missed them")
        rows.append(row)

    # ── table ───────────────────────────────────────────────────────────────
    print(f"\n  {'file':<40} {'RMS(g)':>9} {'DC(g)':>8} {'clip':>5}"
          + ("  modes" if args.ringdown else ""))
    print("  " + "-" * (66 if args.ringdown else 58))
    for r in rows:
        line = f"  {r['file'][:40]:<40} {r['rms']:>9.5f} {r['dc']:>+8.3f} {r['clip']:>5}"
        if args.ringdown and r["modes"]:
            tags = "".join("." if m["ok"] else "x" for m in r["modes"])
            line += f"  [{tags}]"
        print(line)
    if args.ringdown:
        print("  (modes: . = resolved, x = not resolved; order f1 f2 f3)")

    # ── RMS consistency ─────────────────────────────────────────────────────
    rmss = np.array([r["rms"] for r in rows])
    med = float(np.median(rmss))
    print(f"\n  RMS: median {med:.5f} g, "
          f"spread {(rmss.max()-rmss.min())/med*100:.1f}% of median")
    for r in rows:
        if med > 0 and abs(r["rms"] - med) / med > RMS_OUTLIER_FRAC:
            problems.append(f"{r['file']}: RMS {r['rms']:.5f} is "
                            f"{(r['rms']-med)/med*100:+.0f}% from the set median "
                            "— not like the others")

    # ── verdict ─────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    if not problems:
        print("PASS — captures are consistent and clean.")
        print("(Overruns are not visible post-hoc; confirm the capture summaries "
              "reported them handled.)")
    else:
        print(f"{len(problems)} PROBLEM(S):")
        for pr in problems:
            print(f"  - {pr}")
        print("\nDecide per problem whether to drop that capture and re-take it. "
              "An outlier tap left in the set inflates the scatter and raises the "
              "smallest shift you can detect.")
    print("=" * 70)
    sys.exit(0 if not problems else 1)


if __name__ == "__main__":
    main()

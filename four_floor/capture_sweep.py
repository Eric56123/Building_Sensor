"""
capture_sweep.py — Pi-side acquisition in the standard _raw CSV format
=======================================================================
Acquisition ONLY. No model, no classification, no damage index. It records what
the accelerometer saw and writes it where the analysis tools expect to find it.

Keeping capture separate from analysis matters here: a capture that also scored a
damage index would tempt you to read a result off a run whose timing had not yet
been verified. Capture first, then analyse deliberately.

Used for every Day-1 measurement:
    swept sine (GATE 1)   python3 capture_sweep.py --duration 120 --label sweep_g20
    noise floor           python3 capture_sweep.py --duration 60  --label noise --quiet
    axis check            python3 capture_sweep.py --duration 20  --label axis --all-axes

Output goes to characterisation/<label>_<timestamp>_raw.csv — NEVER into pi_logs/,
which holds the damage campaign and must not be mixed with characterisation runs.

Each window is written as it completes, so an interrupted capture still leaves
valid data. Timing health (FIFO throughput, overruns) is reported per window and
summarised at the end: a capture with overruns is not time-contiguous and any
spectrum from it is suspect.
"""
import argparse
import os
import sys
import time

import numpy as np

import config
import toolkit_common as tk


def capture(duration_s, axis, label, out_dir, quiet=False, all_axes=False,
            max_overruns=None, max_retries=3, wall_limit=None):
    """
    Record `duration_s` of acceleration and write the standard _raw CSV.

    Returns (path, stats). With all_axes, one file per axis is written and a dict
    of {axis: (path, stats)} is returned instead — used by the axis check, where
    the whole point is comparing axes under identical excitation.

    OVERRUN REJECTION (max_overruns)
    --------------------------------
    A FIFO overrun drops up to FIFO_DEPTH raw samples mid-block, leaving a gap of
    ~20 ms. Sample spacing WITHIN the surviving stretches is still exact (the
    sensor's own ODR clock sets it), so a gap does not shift a spectral peak — it
    adds broadband leakage around it. Tolerable for finding f1; not for PSD
    magnitudes feeding the model.

    With max_overruns set, any window exceeding it is DISCARDED and re-captured,
    up to max_retries times. Only accepted windows are written, so the CSV
    contains no known-corrupt data.

    If the retries are exhausted the window is kept and loudly flagged rather than
    dropped: silently discarding it would shorten the record while still reporting
    the requested duration, which is a worse failure than a declared bad window.

    WALL-CLOCK LIMIT (wall_limit)
    -----------------------------
    duration_s counts SIGNAL, not elapsed time: a re-captured window adds ~4 s of
    wall clock without adding data. That matters when an external instrument is
    running to its own schedule — a swept-sine generator does not pause for our
    retries, so a capture that overruns its wall-clock budget keeps recording
    after the sweep has ended and restarted, splicing the top of one sweep onto
    the bottom of the next. The frequency axis is then meaningless.

    wall_limit stops the capture at a hard elapsed-time deadline, yielding fewer
    windows but a record that stays inside one sweep. The shortfall is reported,
    never silent.
    """
    from sensor import ADXL345, collect_window

    axes = ("x", "y", "z") if all_axes else (axis,)
    window_s = config.N_SAMPLES / config.FS
    n_windows = max(1, int(round(duration_s / window_s)))

    tk.ensure_dir(out_dir)
    stamp = tk.timestamp_slug()

    print(f"  {n_windows} windows x {window_s:.1f} s = "
          f"{n_windows * window_s:.1f} s per axis, at {config.FS} Hz")
    if all_axes:
        print("  Capturing x, y and z SEQUENTIALLY — keep the excitation steady "
              "throughout so the three are comparable.")

    results = {}
    accel = ADXL345()
    try:
        for ax in axes:
            path = os.path.join(out_dir, f"{label}_{ax}_{stamp}_raw.csv"
                                if all_axes else f"{label}_{stamp}_raw.csv")
            windows, overruns, throughputs = [], 0, []
            retried, kept_bad = 0, 0
            clipped_windows, clipped_samples, peak_g = 0, 0, 0.0
            print(f"\n  [{ax}] -> {os.path.basename(path)}")
            with open(path, "w") as fh:
                fh.write(tk.raw_csv_header() + "\n")
                t0 = time.time()
                stopped_early = False
                for i in range(n_windows):
                    # A window takes ~window_s to record; if there is not enough
                    # of the budget left for it, stop rather than run past the
                    # deadline and out of sync with the external sweep.
                    if wall_limit is not None and (time.time() - t0) + window_s > wall_limit:
                        stopped_early = True
                        print(f"    ** wall-clock limit {wall_limit:.0f} s reached "
                              f"after {i} of {n_windows} windows — stopping so the "
                              "record stays inside one sweep. **")
                        break
                    # Re-capture while the window exceeds the overrun budget. Only
                    # the accepted attempt is written, so rejected blocks never
                    # reach the CSV.
                    for attempt in range(max_retries + 1):
                        w = collect_window(accel, n_samples=config.N_SAMPLES,
                                           sample_rate=config.FS, axis=ax)
                        ov = getattr(collect_window, "last_dropouts", 0)
                        tp = getattr(collect_window, "last_raw_throughput_hz",
                                     float("nan"))
                        if max_overruns is None or ov <= max_overruns:
                            break
                        if attempt < max_retries:
                            retried += 1
                            print(f"    window {i + 1}: {ov} overrun(s) > "
                                  f"{max_overruns} — re-capturing "
                                  f"({attempt + 1}/{max_retries})")
                    if max_overruns is not None and ov > max_overruns:
                        kept_bad += 1
                        print(f"    ** window {i + 1}: still {ov} overrun(s) after "
                              f"{max_retries} retries — KEEPING it so the record "
                              "stays the requested length, but this window has "
                              "gaps. **")
                    # Clipping check. A sample at the rail is not a measurement:
                    # the peak is flattened, odd harmonics appear that look like
                    # extra modes, and amplitude/damping estimates are ruined. It
                    # is silent in the RMS, so it must be tested for explicitly.
                    rail = config.G_RANGE * 0.98
                    n_clip = int(np.sum(np.abs(w) >= rail))
                    if n_clip:
                        clipped_windows += 1
                        clipped_samples += n_clip
                        print(f"    ** window {i + 1}: {n_clip} sample(s) at the "
                              f"+/-{config.G_RANGE} g rail — REDUCE THE AMPLIFIER "
                              f"GAIN or widen config.G_RANGE. This window's peak "
                              "is flattened. **")
                    tk.append_window(fh, f"{time.time():.3f}", w)
                    windows.append(w)
                    overruns += ov
                    throughputs.append(tp)
                    peak_g = max(peak_g, float(np.abs(w).max()))
                    if not quiet:
                        elapsed = time.time() - t0
                        remaining = (n_windows - i - 1) * window_s
                        print(f"    window {i + 1}/{n_windows}  "
                              f"rms={tk.rms(w):.4f} g  dc={tk.dc_offset(w):+.3f} g  "
                              f"[{elapsed:.0f}s elapsed, ~{remaining:.0f}s left]")
            series = np.concatenate(windows)
            stats = {
                "path": path,
                "n_windows": len(windows),
                "duration_s": len(series) / config.FS,
                "rms_g": tk.rms(series),
                "dc_g": tk.dc_offset(series),
                "overruns": overruns,
                "throughput_hz": float(np.nanmean(throughputs)),
                "retried": retried,
                "kept_bad": kept_bad,
                "max_overruns": max_overruns,
                "peak_g": peak_g,
                "clipped_windows": clipped_windows,
                "clipped_samples": clipped_samples,
                "wall_s": time.time() - t0,
                "requested_windows": n_windows,
                "stopped_early": stopped_early,
            }
            results[ax] = stats
    finally:
        accel.close()

    return results


def report(results):
    print("\n" + "=" * 62)
    print("CAPTURE SUMMARY")
    print("=" * 62)
    for ax, s in results.items():
        print(f"\n  axis {ax}:  {os.path.basename(s['path'])}")
        print(f"    {s['n_windows']} windows, {s['duration_s']:.1f} s of signal")
        # Elapsed vs signal length is the number that matters when an external
        # instrument is running to its own schedule.
        drift = s["wall_s"] - s["duration_s"]
        print(f"    wall clock  {s['wall_s']:.1f} s  ({drift:+.1f} s vs signal)")
        if drift > 0.5 * (s["duration_s"] / max(s["n_windows"], 1)):
            print("      ^ elapsed exceeds the signal length: an external swept "
                  "source has advanced further than the record. Check the sweep "
                  "did not wrap.")
        if s.get("stopped_early"):
            print(f"    ** stopped at {s['n_windows']} of "
                  f"{s['requested_windows']} requested windows (wall-clock "
                  "limit). The record is SHORTER than requested — if you are "
                  "analysing a sweep, the covered frequency range is "
                  "correspondingly reduced. **")
        print(f"    AC RMS      {s['rms_g']:.5f} g")
        head = config.G_RANGE / s['peak_g'] if s['peak_g'] > 0 else float('inf')
        print(f"    peak        {s['peak_g']:.4f} g  "
              f"({s['peak_g']/config.G_RANGE*100:.1f}% of the +/-{config.G_RANGE} g "
              f"range, {head:.1f}x headroom)")
        if s['clipped_samples']:
            print(f"    ** CLIPPED: {s['clipped_samples']} sample(s) across "
                  f"{s['clipped_windows']} window(s) hit the rail. Peaks are "
                  "flattened and harmonics injected — amplitude and damping from "
                  "this record are INVALID. Reduce gain or widen config.G_RANGE, "
                  "then re-capture. **")
        elif head < 1.5:
            print(f"    NOTE: only {head:.1f}x headroom to the rail — a slightly "
                  "stronger resonance would clip.")
        print(f"    DC offset   {s['dc_g']:+.4f} g")
        print(f"    FIFO tput   {s['throughput_hz']:.0f} Hz "
              f"(ODR {config.ODR_HZ} Hz)")
        if s.get("retried"):
            print(f"    re-captured {s['retried']} window(s) that exceeded the "
                  f"--max-overruns {s['max_overruns']} budget")
        if s["overruns"]:
            if s.get("kept_bad"):
                print(f"    ** {s['kept_bad']} window(s) STILL exceed the budget "
                      f"after retries ({s['overruns']} overruns total). Those "
                      "windows have ~20 ms gaps: peak FREQUENCIES are still "
                      "valid, but PSD magnitudes and the noise floor are not. **")
            elif s["max_overruns"] is not None:
                print(f"    overruns    {s['overruns']} total, all within the "
                      f"--max-overruns {s['max_overruns']} budget per window")
            else:
                print(f"    ** {s['overruns']} FIFO OVERRUN(S) — the record has "
                      "gaps. Peak frequencies survive this; PSD magnitudes do "
                      "not. Re-run with --max-overruns 0 to reject and retry. **")
        else:
            print("    overruns    0  (timing contiguous)")
    print("=" * 62)


def main():
    ap = argparse.ArgumentParser(description="Capture acceleration to a _raw CSV.")
    ap.add_argument("--duration", type=float, default=120.0,
                    help="seconds to record (default: 120, a full sweep)")
    ap.add_argument("--axis", default=config.RECORDED_AXIS,
                    choices=["x", "y", "z"],
                    help=f"axis to record (default: {config.RECORDED_AXIS}, "
                         "from config.RECORDED_AXIS)")
    ap.add_argument("--all-axes", action="store_true",
                    help="capture x, y and z in turn — for the axis check")
    ap.add_argument("--label", default="capture",
                    help="filename prefix, e.g. sweep_g20 or noise")
    ap.add_argument("--out-dir", default=tk.CHARACTERISATION_DIR,
                    help="output directory (never pi_logs/)")
    ap.add_argument("--quiet", action="store_true",
                    help="suppress the per-window line")
    ap.add_argument("--max-overruns", type=int, default=None, metavar="N",
                    help="discard and re-capture any window with more than N FIFO "
                         "overruns (0 = accept only perfectly contiguous windows). "
                         "Omit to keep every window regardless.")
    ap.add_argument("--max-retries", type=int, default=3, metavar="M",
                    help="attempts per window before keeping a bad one and "
                         "flagging it (default: 3)")
    ap.add_argument("--repeats", type=int, default=1, metavar="R",
                    help="run the capture R times back-to-back, writing "
                         "<label>_rN_<stamp>_raw.csv each time. Repeats at ONE "
                         "gain measure the estimator's own scatter, which is what "
                         "lets linearity_check judge a between-gain shift against "
                         "measured noise instead of a guessed tolerance.")
    ap.add_argument("--wall-limit", type=float, default=None, metavar="SECONDS",
                    help="hard elapsed-time deadline. Use when an external swept "
                         "source runs to its own clock: retries add wall time "
                         "without adding signal, and overrunning splices two "
                         "sweeps together. Fewer windows, but valid ones.")
    args = ap.parse_args()

    if os.path.abspath(args.out_dir).startswith(
            os.path.join(tk.HERE, "pi_logs")):
        print("ERROR: refusing to write into pi_logs/ — that is campaign data.")
        sys.exit(2)

    print("=" * 62)
    print(f"CAPTURE  '{args.label}'   {args.duration:.0f} s")
    print("=" * 62)

    try:
        if args.repeats > 1:
            # Note on phase: with a free-running generator each repeat starts at a
            # different point in the sweep cycle. That is fine for PSD-based
            # analysis (linearity_check), which is phase-independent provided each
            # capture spans a whole sweep period — so do NOT truncate below one
            # full period here.
            print(f"  {args.repeats} repeats back-to-back. Keep the amplifier "
                  "UNTOUCHED throughout — the repeats must differ only by chance.")
            all_results = {}
            for rep in range(args.repeats):
                print("\n" + "-" * 62)
                print(f"REPEAT {rep + 1} of {args.repeats}")
                print("-" * 62)
                r = capture(args.duration, args.axis, f"{args.label}_r{rep + 1}",
                            args.out_dir, quiet=args.quiet, all_axes=args.all_axes,
                            max_overruns=args.max_overruns,
                            max_retries=args.max_retries,
                            wall_limit=args.wall_limit)
                for k, v in r.items():
                    all_results[f"{k}_r{rep + 1}"] = v
            report(all_results)
            rmss = [v["rms_g"] for v in all_results.values()]
            if len(rmss) > 1:
                spread = (max(rmss) - min(rmss)) / np.mean(rmss)
                print(f"\n  RMS spread across repeats: {spread*100:.1f}%")
                if spread > 0.05:
                    print("  ** >5% spread between repeats at the SAME gain — "
                          "something changed that should not have (drive drift, "
                          "rig settling). The within-gain scatter these are meant "
                          "to measure is contaminated. **")
                else:
                    print("  (consistent — these repeats are a clean noise estimate)")
            return
        results = capture(args.duration, args.axis, args.label, args.out_dir,
                          quiet=args.quiet, all_axes=args.all_axes,
                          max_overruns=args.max_overruns,
                          max_retries=args.max_retries,
                          wall_limit=args.wall_limit)
    except ImportError as e:
        print(f"\nCannot import the hardware driver ({e}). Run this on the Pi.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nInterrupted — windows completed so far are on disk and valid.")
        sys.exit(130)

    report(results)

    if len(results) == 1:
        path = next(iter(results.values()))["path"]
        print(f"\nNext:  python3 sweep_analysis.py {path} --full-band")


if __name__ == "__main__":
    main()

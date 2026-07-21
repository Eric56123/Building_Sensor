"""
measure_sampling_rate.py — GATE 0: is the acquisition timing trustworthy?
==========================================================================
Verifies the FIFO acquisition path actually delivers what welch() is told it
delivers. Run before any measurement that becomes a spectrum.

WHAT CHANGED, AND WHY THIS SCRIPT WAS REWRITTEN
------------------------------------------------
The original version measured a COPY of the old software-timed collect_window:
one I2C read per sample, paced by a busy-wait. It reported per-sample jitter
because, on that path, jitter was the dominant risk — Linux scheduling decided
when each sample was taken, so the interval wandered and welch's uniform-sampling
assumption broke.

collect_window no longer works that way. The ADXL345 samples on its OWN clock at
config.ODR_HZ and buffers into a 32-deep FIFO; we drain the FIFO and resample the
block to config.FS. Sample spacing is therefore set by the sensor's crystal, not
by when Python got scheduled. Per-sample jitter is not merely small on this path,
it is NOT A VARIABLE.

That made the old script actively misleading: it exercised code that no longer
runs, so it would report PASS even if the FIFO path were completely broken. A
gate that cannot fail is worse than no gate.

WHAT ACTUALLY DETERMINES THE FREQUENCY AXIS NOW
------------------------------------------------
1. TRUE ODR. collect_window resamples by FS/ODR_HZ assuming the sensor runs at
   exactly ODR_HZ. It does not — crystals are not exact. If the true rate is
   1596 Hz and we resample as though it were 1600, the returned window is at
   997.6 Hz, not 1000, and every frequency welch reports is high by that ratio.
   This is a SYSTEMATIC scale error on the frequency axis, and it is measurable.

2. FIFO OVERRUNS. An overrun drops up to FIFO_DEPTH samples, leaving a ~20 ms
   gap. Spacing within the surviving stretches is still exact, so a gap does not
   shift a peak — it leaks energy around it. Tolerable for locating f1, not for
   PSD magnitudes.

3. I2C HEADROOM. If the bus cannot be drained faster than the ODR produces,
   overruns are guaranteed rather than occasional.

Usage (on the Pi):
    python3 measure_sampling_rate.py                  # the real FIFO gate
    python3 measure_sampling_rate.py --odr-seconds 30 # longer ODR calibration
    python3 measure_sampling_rate.py --legacy         # also run the OLD software-
                                                      #   timed measurement, for
                                                      #   before/after comparison
"""
import argparse
import statistics
import sys
import time

import numpy as np
from smbus2 import SMBus

import config

# The measured ODR may differ from nominal by this much before we call it a fault
# rather than normal crystal tolerance. The ADXL345 datasheet permits considerably
# more than 2%; this is tight enough to catch a MISCONFIGURED rate (e.g. the
# register left at 800 Hz while the code believes 1600), which is the failure that
# matters, since it would be a 2x error rather than a fraction of a percent.
ODR_TOL = 0.02

# How far the effective returned rate may sit from config.FS before the bias
# stops being negligible against a typical sweep's +/-0.5 Hz resolution.
FS_TOL = 0.01


def _time_read_only(accel, n_samples, axis_idx):
    """Back-to-back read_xyz() with no pacing — the raw I2C ceiling."""
    dt_read = np.empty(n_samples)
    vals = np.empty(n_samples)
    for i in range(n_samples):
        t0 = time.perf_counter()
        vals[i] = accel.read_xyz()[axis_idx]
        dt_read[i] = time.perf_counter() - t0
    return dt_read, vals


def measure_true_odr(seconds=20.0, bus_id=None, addr=0x53):
    """
    Measure the sensor's ACTUAL output data rate.

    Drain the FIFO continuously for `seconds`. If no overrun occurs, not one
    sample was lost, so drained_count / elapsed IS the true ODR — the sensor
    produced exactly that many samples in that wall-clock interval.

    An overrun invalidates the count (samples were discarded before we read
    them), so the result is reported as a LOWER BOUND rather than silently
    returned as if exact.

    Returns (odr_hz, n_samples, elapsed_s, overrun_events).
    """
    bus_id = config.ADXL345_I2C_BUS if bus_id is None else bus_id
    b = SMBus(bus_id)
    try:
        b.write_byte_data(addr, config.REG_POWER_CTL, 0x00)
        b.write_byte_data(addr, config.REG_BW_RATE,
                          config.BW_RATE_CODES[config.ODR_HZ])
        b.write_byte_data(addr, config.REG_DATA_FORMAT,
                          config.DATA_FORMAT)
        b.write_byte_data(addr, config.REG_FIFO_CTL, config.FIFO_MODE_BYPASS)
        b.write_byte_data(addr, config.REG_FIFO_CTL, config.FIFO_MODE_STREAM)
        b.write_byte_data(addr, config.REG_POWER_CTL, config.POWER_CTL_MEASURE)
        time.sleep(0.3)                       # let the ODR settle

        # Start from a known-empty FIFO with no pending overrun flag.
        b.write_byte_data(addr, config.REG_FIFO_CTL, config.FIFO_MODE_BYPASS)
        b.write_byte_data(addr, config.REG_FIFO_CTL, config.FIFO_MODE_STREAM)
        b.read_byte_data(addr, config.REG_INT_SOURCE)

        n, overruns = 0, 0
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < seconds:
            cnt = b.read_byte_data(addr, config.REG_FIFO_STATUS) & 0x3F
            for _ in range(cnt):
                b.read_i2c_block_data(addr, config.REG_DATAX0, 6)
                n += 1
                time.sleep(6e-6)              # datasheet: >5 us between FIFO reads
            if b.read_byte_data(addr, config.REG_INT_SOURCE) & 0x01:
                overruns += 1
        elapsed = time.perf_counter() - t0
        b.write_byte_data(addr, config.REG_POWER_CTL, 0x00)
        return n / elapsed, n, elapsed, overruns
    finally:
        b.close()


def _report_intervals(name, intervals_ms, target_dt_ms):
    print(f"\n  [{name}] inter-sample interval (ms):")
    print(f"    mean   {statistics.mean(intervals_ms):8.4f}   (target {target_dt_ms:.4f})")
    print(f"    std    {statistics.pstdev(intervals_ms):8.4f}   <- jitter")
    print(f"    min    {min(intervals_ms):8.4f}")
    print(f"    max    {max(intervals_ms):8.4f}")


def _legacy_software_timed(accel, n_samples, sample_rate, axis_idx):
    """
    The OLD software-timed loop, kept only for before/after comparison.

    This is what acquisition used to do: one I2C read per sample, paced by a
    busy-wait. Its jitter is the thing the FIFO rewrite eliminated, so running it
    alongside quantifies what the rewrite bought.
    """
    dt = 1.0 / sample_rate
    stamps = np.empty(n_samples)
    t_window = time.perf_counter()
    for i in range(n_samples):
        t_start = time.perf_counter()
        try:
            accel.read_xyz()[axis_idx]
        except OSError:
            pass
        stamps[i] = time.perf_counter()
        while time.perf_counter() - t_start < dt:
            pass
    return stamps, time.perf_counter() - t_window


def main():
    ap = argparse.ArgumentParser(
        description="GATE 0 — verify FIFO acquisition timing.")
    ap.add_argument("--n", type=int, default=config.N_SAMPLES)
    ap.add_argument("--fs", type=int, default=config.FS)
    ap.add_argument("--axis", default=config.RECORDED_AXIS, choices=["x", "y", "z"],
                    help=f"axis to sample (default: {config.RECORDED_AXIS}, "
                         "from config.RECORDED_AXIS)")
    ap.add_argument("--repeats", type=int, default=3,
                    help="collect_window calls to check (default: 3)")
    ap.add_argument("--odr-seconds", type=float, default=20.0,
                    help="duration of the ODR calibration (default: 20 s; longer "
                         "is more precise)")
    ap.add_argument("--legacy", action="store_true",
                    help="also run the OLD software-timed loop for comparison")
    ap.add_argument("--dump", default=None,
                    help="optional CSV of legacy intervals (never under logs/)")
    args = ap.parse_args()

    try:
        from sensor import ADXL345, collect_window
    except Exception as e:
        print(f"Cannot import hardware driver ({e}). This script must run on the Pi.")
        sys.exit(1)

    axis_idx = {"x": 0, "y": 1, "z": 2}[args.axis]

    print("=" * 70)
    print(f"GATE 0 — ACQUISITION TIMING   axis={args.axis}  "
          f"ODR={config.ODR_HZ} Hz -> fs={args.fs} Hz")
    print("=" * 70)

    accel = ADXL345()
    failures = []

    # ── 1. I2C ceiling ──────────────────────────────────────────────────────
    print("\n[1] I2C read ceiling (can we drain faster than the ODR produces?)")
    dt_read, _ = _time_read_only(accel, min(args.n, 2000), axis_idx)
    ceiling = 1.0 / float(np.mean(dt_read))
    headroom = ceiling / config.ODR_HZ
    print(f"    single 6-byte read: mean {np.mean(dt_read)*1e3:.4f} ms, "
          f"max {np.max(dt_read)*1e3:.4f} ms")
    print(f"    sustained ceiling : {ceiling:.0f} reads/s")
    print(f"    headroom over ODR : {headroom:.2f}x")
    if headroom < 1.0:
        failures.append(f"I2C ceiling {ceiling:.0f} Hz is BELOW ODR "
                        f"{config.ODR_HZ} Hz — overruns are unavoidable")
    elif headroom < 1.5:
        print(f"    NOTE: under 1.5x headroom. Draining occupies "
              f"{100/headroom:.0f}% of the time budget, so any scheduling "
              "preemption overruns the FIFO. Expect intermittent gaps.")

    # ── 2. True ODR ─────────────────────────────────────────────────────────
    print(f"\n[2] TRUE ODR calibration ({args.odr_seconds:.0f} s continuous drain)")
    accel.close()          # measure_true_odr drives the bus itself
    odr, n_drained, el, ovr = measure_true_odr(seconds=args.odr_seconds)
    print(f"    drained {n_drained} samples in {el:.4f} s, overrun events = {ovr}")
    odr_err = (odr - config.ODR_HZ) / config.ODR_HZ
    if ovr:
        print(f"    !! {ovr} overrun(s) during calibration — samples were lost, so")
        print(f"       {odr:.2f} Hz is a LOWER BOUND, not the true ODR.")
    print(f"    measured ODR      : {odr:.2f} Hz   (nominal {config.ODR_HZ})")
    print(f"    deviation         : {odr_err*100:+.3f}%")
    if abs(odr_err) > ODR_TOL:
        failures.append(f"measured ODR {odr:.1f} Hz is {odr_err*100:+.1f}% from "
                        f"nominal {config.ODR_HZ} Hz — check BW_RATE is set for "
                        "the rate the code believes")

    # Effective rate of the RETURNED window, and the bias it implies.
    eff_fs = odr * (float(args.fs) / config.ODR_HZ)
    fs_err = (args.fs - eff_fs) / eff_fs
    print(f"\n    collect_window resamples by {args.fs}/{config.ODR_HZ}, so the "
          f"returned window is really at {eff_fs:.2f} Hz.")
    print(f"    Telling welch fs={args.fs} biases every frequency "
          f"{fs_err*100:+.3f}%")
    print(f"      -> a true 10 Hz mode reads {10*args.fs/eff_fs:.4f} Hz")
    print(f"      -> a true 30 Hz mode reads {30*args.fs/eff_fs:.4f} Hz")
    if abs(fs_err) > FS_TOL:
        failures.append(f"effective fs {eff_fs:.1f} Hz differs from the declared "
                        f"{args.fs} Hz by {fs_err*100:+.2f}% — correct it or "
                        "record it as a systematic")

    # ── 3. The REAL collect_window ──────────────────────────────────────────
    print(f"\n[3] Real collect_window() x{args.repeats} "
          "(the function that produces your data)")
    accel = ADXL345()
    tot_ovr, tps = 0, []
    for r in range(args.repeats):
        w = collect_window(accel, n_samples=args.n, sample_rate=args.fs,
                           axis=args.axis)
        ov = getattr(collect_window, "last_dropouts", 0)
        tp = getattr(collect_window, "last_raw_throughput_hz", float("nan"))
        tot_ovr += ov
        tps.append(tp)
        print(f"    [{r+1}] len={len(w)} (want {args.n})  "
              f"raw throughput {tp:.0f} Hz  overruns={ov}  "
              f"rms={float(np.sqrt(np.mean((w-w.mean())**2))):.5f} g")
        if len(w) != args.n:
            failures.append(f"collect_window returned {len(w)} samples, not {args.n}")

    print(f"\n    total overruns over {args.repeats} windows: {tot_ovr}")
    if tot_ovr:
        print("    Each overrun drops up to "
              f"{config.FIFO_DEPTH} samples (~"
              f"{config.FIFO_DEPTH/config.ODR_HZ*1e3:.0f} ms). Peak FREQUENCIES "
              "survive that; PSD magnitudes and noise floors do not.")
        print("    Mitigate with:  capture_sweep.py --max-overruns 0")

    # ── 4. Jitter is not a variable here ────────────────────────────────────
    print("\n[4] Per-sample jitter")
    print("    Not measured, and not measurable from the returned window: the")
    print("    ADXL345 timestamps samples with its own clock and collect_window")
    print("    resamples to a uniform grid. Spacing within a window is exact by")
    print(f"    construction ({1e3/eff_fs:.4f} ms), so the old jitter histogram no")
    print("    longer describes this path. The failure modes that remain are the")
    print("    ODR scale error in [2] and the dropped-sample gaps in [3].")

    # ── 5. Legacy comparison ────────────────────────────────────────────────
    if args.legacy:
        print("\n[5] LEGACY software-timed loop (what the FIFO rewrite replaced)")
        stamps, elapsed = _legacy_software_timed(accel, args.n, args.fs, axis_idx)
        iv = np.diff(stamps) * 1000.0
        _report_intervals("legacy", iv, 1000.0 / args.fs)
        jit = 100 * np.std(iv) / np.mean(iv)
        print(f"    achieved {args.n/elapsed:.1f} Hz, jitter CoV {jit:.1f}%")
        print(f"    FIFO path jitter for comparison: 0% by construction.")
        if args.dump:
            np.savetxt(args.dump, iv, delimiter=",", header="interval_ms")
            print(f"    raw intervals -> {args.dump}")

    accel.close()

    # ── Verdict ─────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)
    if not failures:
        print(f"  PASS: fs={args.fs} is defensible for welch().")
        print(f"    ODR {odr:.2f} Hz ({odr_err*100:+.3f}%), effective fs "
              f"{eff_fs:.2f} Hz ({fs_err*100:+.3f}% bias), {tot_ovr} overruns.")
        if tot_ovr:
            print("    Overruns occurred but do not shift peak frequencies. Use "
                  "--max-overruns 0 when PSD magnitudes matter.")
        print(f"\n  Record the calibration:")
        print(f"    python3 rig_config.py --set odr_measured_hz={odr:.2f} "
              f"--set fs_effective_hz={eff_fs:.2f}")
    else:
        print(f"  FAIL ({len(failures)} problem(s)):")
        for f in failures:
            print(f"    - {f}")
    print("=" * 70)
    sys.exit(0 if not failures else 1)


if __name__ == "__main__":
    main()

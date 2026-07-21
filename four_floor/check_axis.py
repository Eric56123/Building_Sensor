"""
check_axis.py — Accelerometer axis alignment check
====================================================
Confirms the ADXL345 is logging the SAME direction the shake table moves in,
before you commit a run to it.

WHY THIS MATTERS
----------------
The table shakes HORIZONTALLY. Gravity (1 g) points DOWN. So with the rig sitting
still:

  * the axis aligned with the table's motion is horizontal  -> reads ~0 g
  * the axis pointing up/down (gravity)       is vertical    -> reads ~1 g

monitor.py records ONE axis (see `axis=` in _make_live_source(), currently "z").
If that recorded axis reads ~1 g when static, you have mounted the sensor so the
LOGGED axis points up — you would be recording gravity + vertical wobble, not the
horizontal excitation the PINN expects. The fix is to change `axis=` in monitor.py
to whichever axis this test reports as horizontal (or physically re-mount the
sensor). This script tells you which.

USAGE (run on the Pi, rig sitting STILL and level)
--------------------------------------------------
    python3 check_axis.py                 # static gravity check on the recorded axis
    python3 check_axis.py --axis y        # check a different recorded axis
    python3 check_axis.py --shake         # static check, then a live shake test to
                                          #   confirm the recorded axis is the one that
                                          #   actually moves when you drive the table
    python3 check_axis.py --calibrate-scale  # derive config.ADXL345_SCALE from the
                                          #   known 1 g gravity reference

SCALE vs TILT
-------------
Orientation is judged from DIRECTION COSINES (each axis / |total|), not from raw
g values. This matters: |total| is 1 g for a static rig at ANY orientation, so
tilting redistributes gravity between axes but never changes the total. It
follows that:

  * |total| != 1 g  =>  the SCALE is wrong (config.ADXL345_SCALE). Tilt cannot
                        cause it, and no amount of levelling will fix it.
  * gravity split across axes with |total| == 1 g  =>  genuinely TILTED.

Judging orientation on raw g conflates the two, and a low scale factor can drag
a true 1.00 g vertical axis below a "is it vertical?" threshold and report it as
merely ambiguous — hiding a wrong-axis mounting behind a bogus "level the rig"
message. Dividing by |total| removes the scale entirely from that decision.

Exit code is 0 if the recorded axis is correctly horizontal, 1 otherwise — so it
can gate the lab-session checklist.
"""

import argparse
import sys
import time

import numpy as np

import config

# The axis monitor.py records. Single source of truth lives in config so the two
# modules cannot silently drift apart; --axis overrides it for one-off checks.
RECORDED_AXIS_DEFAULT = config.RECORDED_AXIS

AXES = ("x", "y", "z")
AXIS_IDX = {"x": 0, "y": 1, "z": 2}

# Orientation thresholds as a FRACTION of the measured gravity vector's length
# (a direction cosine), not as absolute g. Dividing by |total| cancels the scale
# factor, so these stay valid even when config.ADXL345_SCALE is wrong — which is
# the whole point (see SCALE vs TILT in the module docstring).
VERTICAL_FRAC = 0.85     # |component| / |total| above this  -> along gravity
HORIZONTAL_FRAC = 0.25   # below this                        -> level with ground

# How far |total| may stray from 1 g before we call the scale factor wrong.
SCALE_TOL_G = 0.10


def read_static(accel, n_reads: int = 200, settle_s: float = 0.5) -> tuple:
    """
    Average many single-shot X/Y/Z reads with the rig held still.

    Returns (mean_g, std_g), each a length-3 array indexed [x, y, z] in g.
    Averaging beats one read: it smooths sensor noise so the ~1 g vs ~0 g call is
    unambiguous, and the per-axis std doubles as a "is the rig actually still?"
    check (a large std means something is vibrating and the static test is
    invalid).
    """
    time.sleep(settle_s)   # let the rig settle after you let go of it
    samples = np.empty((n_reads, 3), dtype=float)
    for i in range(n_reads):
        samples[i] = accel.read_xyz()
        time.sleep(0.005)
    return samples.mean(axis=0), samples.std(axis=0)


def _label(frac: float) -> str:
    """Orientation from a direction cosine (component / |total|), scale-free."""
    mag = abs(frac)
    if mag >= VERTICAL_FRAC:
        return "VERTICAL (gravity)"
    if mag <= HORIZONTAL_FRAC:
        return "horizontal"
    return "TILTED"


def check_alignment(accel, recorded_axis: str, n_reads: int = 200) -> bool:
    """
    Static gravity check. Prints a per-axis table and a verdict for the recorded
    axis. Returns True iff the recorded axis is correctly horizontal.
    """
    recorded_axis = recorded_axis.lower()
    idx = AXIS_IDX[recorded_axis]

    print("\nHold the rig STILL and LEVEL — reading gravity...")
    mean_g, std_g = read_static(accel, n_reads=n_reads)
    total_g = float(np.linalg.norm(mean_g))

    # Direction cosines: the orientation call is made on these, never on raw g,
    # so a wrong ADXL345_SCALE cannot influence it. Guard against a zero vector
    # (sensor asleep / all-zero reads) rather than dividing by it.
    if total_g < 1e-6:
        print("\n  [FAIL] Gravity vector is ~zero — the sensor is returning no "
              "signal. Check wiring and that it is in measurement mode.")
        return False
    frac = mean_g / total_g

    print("\n  axis    mean (g)   frac of g   std (g)    orientation")
    print("  " + "-" * 58)
    for ax in AXES:
        j = AXIS_IDX[ax]
        mark = " <- recorded" if ax == recorded_axis else ""
        print(f"   {ax}     {mean_g[j]:+7.3f}     {frac[j]:+6.3f}     "
              f"{std_g[j]:6.3f}    {_label(frac[j])}{mark}")
    print("  " + "-" * 58)
    print(f"  |total| = {total_g:.3f} g (should be ~1.00 g when static)")

    # Sanity: if the rig is not actually still, the whole test is meaningless.
    if float(std_g.max()) > 0.05:
        print("\n  NOTE: one or more axes are noisy (std > 0.05 g) — the rig may "
              "still be moving. Let it settle fully and re-run.")

    # A |total| away from 1 g is a SCALE fault and nothing else. Tilt cannot cause
    # it — the gravity vector has length 1 g at every orientation — so this is
    # reported as a definite finding, not as a "maybe the rig is moving" hedge.
    if abs(total_g - 1.0) > SCALE_TOL_G:
        implied = config.ADXL345_SCALE / total_g
        print(f"\n  [SCALE] |total| = {total_g:.3f} g, not 1 g. Tilt cannot cause "
              "this (the gravity vector is 1 g at any orientation), so "
              "config.ADXL345_SCALE is wrong.")
        print(f"          Configured: {config.ADXL345_SCALE:.5f} g/LSB   "
              f"implied: {implied:.5f} g/LSB  ({1.0 / implied:.1f} LSB/g)")
        print("          Every recorded amplitude — and so every PSD magnitude and "
              "the NORM bounds — is scaled by "
              f"{total_g:.3f}. Fix with: python3 check_axis.py --calibrate-scale")
        print("          (The orientation verdict below is unaffected: it uses "
              "direction cosines, which divide the scale out.)")

    rec_frac = float(frac[idx])
    rec = mean_g[idx]
    rec_mag = abs(rec_frac)

    # Which axis is currently the vertical (gravity) one — useful when the recorded
    # axis is wrong and you need to know what to switch monitor.py to.
    vertical_axes = [ax for ax in AXES if abs(frac[AXIS_IDX[ax]]) >= VERTICAL_FRAC]
    horizontal_axes = [ax for ax in AXES if abs(frac[AXIS_IDX[ax]]) <= HORIZONTAL_FRAC]

    print()
    if rec_mag <= HORIZONTAL_FRAC:
        print(f"  [OK] Recorded axis '{recorded_axis}' reads {rec:+.3f} g "
              f"({rec_frac:+.3f} of g) — it is horizontal, aligned with the "
              "table's motion, not gravity.")
        if vertical_axes:
            print(f"       (Gravity is on: {', '.join(vertical_axes)}.)")
        print("       Static gravity cannot tell the two horizontal axes apart — "
              "run --shake to confirm this is the one that actually moves.")
        return True

    if rec_mag >= VERTICAL_FRAC:
        print(f"  [WRONG] Recorded axis '{recorded_axis}' reads {rec:+.3f} g, which "
              f"is {rec_frac:+.3f} of the gravity vector — it points along GRAVITY, "
              "i.e. it logs the vertical direction, not the table's horizontal "
              "motion.")
        if horizontal_axes:
            print(f"       Fix: set  RECORDED_AXIS = \"{horizontal_axes[0]}\"  in "
                  "config.py (monitor.py reads it from there), or re-mount the "
                  "sensor so the recorded axis lies in the plane of motion.")
            if len(horizontal_axes) > 1:
                print(f"       Both {' and '.join(horizontal_axes)} are horizontal; "
                      "run --shake to see which one the table actually moves along.")
        else:
            print("       Fix: no axis is horizontal — re-mount the sensor so one "
                  "axis lies in the plane of the table's motion, then set "
                  "RECORDED_AXIS in config.py to it.")
        return False

    print(f"  [TILTED] Recorded axis '{recorded_axis}' is {rec_frac:+.3f} of the "
          "gravity vector — neither along it nor square to it. Since |total| is "
          "orientation-independent, this really is a tilt: the rig is not level. "
          "Level it and re-run; each axis should sit near 0 or 1 of g, not between.")
    return False


def calibrate_scale(accel, n_reads: int = 500) -> None:
    """
    Derive ADXL345_SCALE from gravity, which is a free 1 g reference.

    With the rig static, the acceleration vector has length exactly 1 g whatever
    the orientation — so the rig does NOT need to be level for this, only still.
    The driver already multiplies raw LSB by config.ADXL345_SCALE, so:

        |total|_g = |total|_LSB * configured_scale
        true_scale = 1 g / |total|_LSB = configured_scale / |total|_g

    Prints the value to paste into config.py; does not write it, so a calibration
    taken while something was vibrating cannot silently corrupt the config.
    """
    print(f"\nSCALE CALIBRATION — hold the rig STILL ({n_reads} samples).")
    print("It need not be level: gravity is 1 g at any orientation.")

    mean_g, std_g = read_static(accel, n_reads=n_reads)
    total_g = float(np.linalg.norm(mean_g))
    if total_g < 1e-6:
        print("\n  [FAIL] Gravity vector is ~zero — no signal from the sensor.")
        return

    configured = config.ADXL345_SCALE
    implied = configured / total_g
    total_lsb = total_g / configured

    print(f"\n  measured |total|  = {total_g:.4f} g  ({total_lsb:.1f} LSB)")
    print(f"  configured scale  = {configured:.5f} g/LSB  ({1.0 / configured:.1f} LSB/g)")
    print(f"  implied scale     = {implied:.5f} g/LSB  ({1.0 / implied:.1f} LSB/g)")
    print(f"  error             = {(total_g - 1.0) * 100:+.1f}%")

    if float(std_g.max()) > 0.05:
        print("\n  [ABORT] std > 0.05 g — the rig was moving, so this calibration is "
              "not trustworthy. Let it settle and re-run.")
        return

    if abs(total_g - 1.0) <= SCALE_TOL_G:
        print(f"\n  [OK] Within {SCALE_TOL_G * 100:.0f}% of 1 g — the configured "
              "scale is fine, no change needed.")
        return

    print("\n  [ACTION] Set this in config.py:")
    print(f"\n      ADXL345_SCALE = {implied:.6g}   # g per LSB, measured on this part")
    print("\n  Then re-derive anything computed from recorded amplitudes: PSDs "
          "shift by this factor, so NORM_MIN/MAX must come from a retrain, and "
          "DI thresholds calibrated under the old scale no longer apply.")


def shake_test(accel, recorded_axis: str, duration_s: float = 6.0) -> None:
    """
    Live motion check: while you DRIVE the table, sample all three axes and report
    which one moves the most. Static gravity alone only proves the recorded axis
    is horizontal — it cannot tell the two horizontal axes apart. This does: the
    axis with the largest motion (std) IS the table's motion axis, and it should
    be the recorded one.
    """
    recorded_axis = recorded_axis.lower()
    print(f"\nSHAKE TEST — drive the table now for ~{duration_s:.0f}s "
          "(swaying it by hand is fine)...")

    samples = []
    t0 = time.time()
    while time.time() - t0 < duration_s:
        samples.append(accel.read_xyz())
        time.sleep(0.005)
    samples = np.asarray(samples, dtype=float)

    # std about the mean removes the static gravity offset, leaving pure motion.
    motion = samples.std(axis=0)
    print("\n  axis    motion std (g)")
    print("  " + "-" * 26)
    for ax in AXES:
        mark = " <- recorded" if ax == recorded_axis else ""
        print(f"   {ax}      {motion[AXIS_IDX[ax]]:6.4f}{mark}")
    print("  " + "-" * 26)

    order = np.argsort(motion)[::-1]
    mover = AXES[int(order[0])]
    best, runner_up = float(motion[order[0]]), float(motion[order[1]])

    if mover == recorded_axis:
        print(f"\n  [OK] The recorded axis '{recorded_axis}' moves the most — it is "
              "aligned with the table's motion.")
    else:
        print(f"\n  [MISMATCH] Axis '{mover}' moves the most, but you are recording "
              f"'{recorded_axis}'. Set  RECORDED_AXIS = \"{mover}\"  in config.py "
              "to log the direction the table actually moves in.")

    # A weak margin means the excitation is splitting across two axes — i.e. the
    # sensor is mounted rotated relative to the table's motion. The winner is then
    # only the larger of two projections of the same motion, and recording it
    # throws away the component on the other axis.
    if runner_up > 0 and best / runner_up < 2.0:
        print(f"\n  NOTE: '{mover}' leads the next axis by only "
              f"{best / runner_up:.1f}x — the motion is splitting across axes, so "
              "the sensor is probably mounted rotated relative to the table's "
              "travel. Re-seat it square to the motion if you can.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check the ADXL345 records the table's horizontal motion axis.")
    parser.add_argument("--axis", choices=AXES, default=RECORDED_AXIS_DEFAULT,
                        help=f"Axis monitor.py records (default: "
                             f"{RECORDED_AXIS_DEFAULT}, from config.RECORDED_AXIS).")
    parser.add_argument("--samples", type=int, default=200,
                        help="Number of static reads to average (default: 200).")
    parser.add_argument("--shake", action="store_true",
                        help="After the static check, run a live shake test to "
                             "confirm the recorded axis is the one that moves.")
    parser.add_argument("--calibrate-scale", action="store_true",
                        help="Derive config.ADXL345_SCALE from gravity as a 1 g "
                             "reference and print the value to set. Does not run "
                             "the alignment check.")
    args = parser.parse_args()

    print("=" * 50)
    print("Axis alignment check")
    print("=" * 50)
    print(f"Recorded axis (config.RECORDED_AXIS): '{args.axis}'")

    try:
        from sensor import ADXL345
    except Exception as e:
        print(f"\nCannot import the hardware driver ({e}). "
              "Run this on the Pi with the ADXL345 wired up.")
        sys.exit(1)

    accel = None
    try:
        accel = ADXL345()
        if args.calibrate_scale:
            calibrate_scale(accel)
            ok = True   # calibration is advisory; it is not a checklist gate
        else:
            ok = check_alignment(accel, args.axis, n_reads=args.samples)
            if args.shake:
                shake_test(accel, args.axis)
    except Exception as e:
        print(f"\nADXL345 error: {e}")
        sys.exit(1)
    finally:
        if accel is not None:
            accel.close()

    print("\n" + "=" * 50)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

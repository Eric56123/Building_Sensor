"""
rig_config.py — Store the rig's MEASURED modal properties
==========================================================
Single source of truth for what this physical frame actually does, kept in
rig.json next to the code.

WHY THIS EXISTS
---------------
The previous campaign inherited f1 = 9.42 Hz from the Johnson ASCE benchmark — a
full-scale 3.4 t/floor building — and applied it to a 200 mm scaled frame. Nothing
flagged it, because the number lived in code as a plausible-looking constant.

So: measured values live here, and here only. A tool that needs f1 calls
toolkit_common.rig_value("f1_hz") and gets None when the rig has never been
measured. None is loud; a wrong constant is silent.

Every value carries provenance — how it was measured, when, and by which script —
so the dissertation can cite it and a later reader can tell a real measurement
from a placeholder.

Usage:
    python3 rig_config.py                       # show current values
    python3 rig_config.py --set-f1 12.4 --set-zeta 0.021 --note "2026-07-21, sweep"
    python3 rig_config.py --set f1_hz=12.4 --set damping_zeta=0.021
    python3 rig_config.py --clear               # wipe (asks first)
"""
import argparse
import sys
from datetime import datetime

import toolkit_common as tk

# Keys with a defined meaning. Free-form keys are allowed via --set but warned
# about, so a typo ("f1_Hz") cannot quietly create a second, ignored field.
KNOWN = {
    "f1_hz":          "first natural frequency, Hz (GATE 1, sweep)",
    "f2_hz":          "second natural frequency, Hz, if resolved",
    "f3_hz":          "third natural frequency, Hz, if resolved",
    "damping_zeta":   "damping ratio of mode 1 (ringdown log-decrement)",
    "noise_rms_g":    "broadband noise floor, g RMS (shaker off)",
    "noise_rms_inband_g": "noise floor inside the 0.5-45 Hz training band, g RMS "
                          "— the SNR reference that matters after preprocessing",
    "recorded_axis":  "accelerometer axis aligned with table motion",
    "linear":         "true if f1 is amplitude-independent (linearity check)",
    # ── instrument calibration (properties of THIS sensor, not the structure) ──
    "odr_measured_hz":   "true ADXL345 output data rate (measure_sampling_rate.py)",
    "fs_effective_hz":   "actual rate of the returned window; welch is told "
                         "config.FS, so the difference is a frequency-axis bias",
    "freq_bias_pct":     "systematic % error on every reported frequency",
    "adxl345_scale_g_per_lsb": "measured sensitivity (check_axis.py "
                               "--calibrate-scale); nominal is 0.0039",
    "note":           "free-text provenance",
    "measured_at":    "ISO timestamp of the last update",
}


def show(rig):
    print("=" * 62)
    print(f"RIG CONFIGURATION   ({tk.RIG_JSON})")
    print("=" * 62)
    if not rig:
        print("\n  (empty — this rig has NOT been characterised)")
        print("  Nothing may assume an f1. Run GATE 1 (capture_sweep.py +")
        print("  sweep_analysis.py --full-band) and record the result here.")
        print("=" * 62)
        return
    width = max(len(k) for k in rig)
    for k in sorted(rig):
        desc = KNOWN.get(k, "(unrecognised key)")
        print(f"  {k:<{width}} = {str(rig[k]):<12}  # {desc}")
    missing = [k for k in ("f1_hz", "damping_zeta", "noise_rms_g") if k not in rig]
    if missing:
        print(f"\n  Not yet measured: {', '.join(missing)}")
    print("=" * 62)


def main():
    ap = argparse.ArgumentParser(description="Read/write the measured rig properties.")
    ap.add_argument("--set-f1", type=float, metavar="HZ",
                    help="first natural frequency in Hz")
    ap.add_argument("--set-zeta", type=float, metavar="Z",
                    help="damping ratio of mode 1 (e.g. 0.021 for 2.1%%)")
    ap.add_argument("--set-noise", type=float, metavar="G",
                    help="measured noise floor, g RMS")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="set any key (repeatable)")
    ap.add_argument("--note", help="provenance note stored alongside the values")
    ap.add_argument("--clear", action="store_true", help="delete all stored values")
    args = ap.parse_args()

    rig = tk.load_rig()

    if args.clear:
        if not rig:
            print("Already empty.")
            return
        show(rig)
        if input("\nDelete all of the above? [y/N] ").strip().lower() != "y":
            print("Cancelled.")
            return
        tk.save_rig({})
        print(f"Cleared {tk.RIG_JSON}")
        return

    updates = {}
    if args.set_f1 is not None:
        updates["f1_hz"] = args.set_f1
    if args.set_zeta is not None:
        updates["damping_zeta"] = args.set_zeta
    if args.set_noise is not None:
        updates["noise_rms_g"] = args.set_noise
    for pair in args.set:
        if "=" not in pair:
            print(f"ERROR: --set expects KEY=VALUE, got {pair!r}")
            sys.exit(2)
        k, v = pair.split("=", 1)
        k = k.strip()
        v = v.strip()
        # Keep numbers numeric so downstream arithmetic does not need to parse.
        try:
            updates[k] = float(v) if "." in v or v.lstrip("-").isdigit() else v
        except ValueError:
            updates[k] = v
        if k not in KNOWN:
            print(f"  NOTE: '{k}' is not a recognised key — storing it anyway.")
    if args.note:
        updates["note"] = args.note

    if not updates:
        show(rig)
        return

    # Sanity-check the physics rather than storing anything typed.
    f1 = updates.get("f1_hz")
    if f1 is not None:
        if not 0 < f1 < 0.5 * tk.config.FS:
            print(f"ERROR: f1 = {f1} Hz is outside (0, Nyquist={0.5 * tk.config.FS:.0f}).")
            sys.exit(2)
        if f1 > 0.45 * tk.config.FS:
            print(f"  WARNING: f1 = {f1} Hz sits above 90% of Nyquist — likely an "
                  "artefact of the resample filter rather than a mode.")
    z = updates.get("damping_zeta")
    if z is not None and not 0 < z < 1:
        print(f"ERROR: zeta = {z} is not in (0, 1). Give a RATIO, not a percentage "
              "(2.1% -> 0.021).")
        sys.exit(2)

    for k, v in updates.items():
        if k in rig and rig[k] != v:
            print(f"  {k}: {rig[k]} -> {v}")
    rig.update(updates)
    rig["measured_at"] = datetime.now().isoformat(timespec="seconds")
    tk.save_rig(rig)
    print()
    show(rig)


if __name__ == "__main__":
    main()

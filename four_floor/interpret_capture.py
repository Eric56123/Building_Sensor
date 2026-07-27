"""
interpret_capture.py — plain-language read-out of a ringdown capture
====================================================================
Run AFTER a ringdown set. Two independent statements, so a mislabel is caught
on the spot (the recurring theme of this campaign):

  1. FROM THE LABEL (deterministic): where the sensor is, where the damage is,
     and the grade — decoded from the folder name's naming convention
     `sensor<POS>_<loc>_<grade>_r<n>` (top-sensor legacy names also handled).

  2. FROM THE DATA (independent): modal shifts vs the correct baseline, a guess
     of the damage LOCATION from the signature, and the SEVERITY — then a
     ✓ / ⚠ flag on whether the data agrees with the label.

READ-ONLY: never writes, never touches weights or logs. Uses the shared
set_mode_frequencies engine so it cannot drift from the other tools.

Usage:
    python3 interpret_capture.py sensorF2_base_severe_r1
    python3 interpret_capture.py characterisation/F1_light_c1 --baseline day7_baseline
"""
import argparse
import glob
import os
import sys

import numpy as np

import toolkit_common as tk

CH = tk.CHARACTERISATION_DIR

# Reference SEVERE fingerprints, TOP sensor, measured Day 4 (Δf1,Δf2,Δf3 %).
# f2 for F3 is NaN: top-storey 2nd mode collides with 2*f1 (harmonic-void).
REF = {
    "base": (-58.7, -17.1, -1.7),
    "F1":   (-60.5, -7.9, -10.0),
    "F2":   (-39.6, -27.5, -13.2),
    "F3":   (-15.5, np.nan, -14.0),
}
# f1 shift (%) by (location, grade), top sensor, measured Days 4+6 — for grading.
GRADE_F1 = {
    "base": {"trace": -2, "light": -29, "moderate": -50, "severe": -59},
    "F1":   {"trace": -4, "light": -38, "moderate": -56, "severe": -60},
    "F2":   {"trace": -1, "light": -24, "moderate": -38, "severe": -40},
    "F3":   {"trace": 0,  "light": -7,  "moderate": -14, "severe": -15},
}
LOC_NAME = {"base": "BASE plate (boundary)", "F1": "FLOOR 1", "F2": "FLOOR 2",
            "F3": "FLOOR 3 (top)"}
POS_NAME = {"F1": "FLOOR 1", "F2": "FLOOR 2", "F3": "FLOOR 3 (top)"}


# Healthy campaign modes — anchors for assigning found peaks to f1/f2/f3 slots.
NOMINAL = np.array([2.93, 8.10, 12.18])


def modal_vector(folder):
    """(f1,f2,f3) set-mean Hz for a folder. Found modes are aligned to the
    f1/f2/f3 SLOTS by nearest nominal frequency, preserving ascending order —
    so when a mode is unobservable (e.g. f2 near a node), a higher mode does not
    slide into its slot. Harmonic-suspect modes void their slot (NaN)."""
    paths = sorted(glob.glob(os.path.join(folder, "*_raw.csv")))
    if not paths:
        return None
    _, clusters = tk.set_mode_frequencies(paths)
    susp = tk.set_mode_frequencies.last_harmonic_suspect
    found = [(float(np.mean(clusters[i])), bool(i < len(susp) and susp[i]))
             for i in range(len(clusters)) if len(clusters[i])]
    found.sort(key=lambda t: t[0])
    slots = [np.nan, np.nan, np.nan]
    prev = -1
    for freq, suspect in found:
        cands = [i for i in range(3) if i > prev]
        if not cands:
            break
        j = min(cands, key=lambda i: abs(freq - NOMINAL[i]))
        slots[j] = np.nan if suspect else freq
        prev = j
    return np.array(slots)


def modal_amplitudes(folder, freqs, bw=0.6):
    """Relative modal peak amplitude (observability) at each freq, averaged over
    taps: mean Welch PSD peak in +/-bw Hz of each mode, normalised to the
    strongest mode. This is what changes with sensor position."""
    psd_sum, fr = None, None
    for path in sorted(glob.glob(os.path.join(folder, "*_raw.csv"))):
        try:
            x, _ = tk.load_raw_series(path)
        except Exception:
            continue
        fr, p = tk.raw_psd(x)
        psd_sum = p if psd_sum is None else psd_sum + p
    if psd_sum is None:
        return None
    amps = []
    for f0 in freqs:
        if np.isnan(f0):
            amps.append(np.nan); continue
        m = (fr >= f0 - bw) & (fr <= f0 + bw)
        amps.append(float(psd_sum[m].max()) if m.any() else np.nan)
    amps = np.array(amps)
    peak = np.nanmax(amps)
    return amps / peak if peak else amps


def parse_label(label):
    """Decode sensor position, damage location, grade, replicate from a name."""
    name = os.path.basename(label.rstrip("/"))
    toks = name.split("_")
    info = {"name": name, "pos": "F3", "pos_explicit": False,
            "loc": None, "grade": None, "rep": None, "is_baseline": False}
    if "baseline" in toks:
        info["is_baseline"] = True
    for t in toks:
        tl = t.lower()
        if t.startswith("sensor") and len(t) > 6:   # sensorF2 -> pos F2
            info["pos"] = t[6:]
            info["pos_explicit"] = True
        elif tl == "base":                          # damage location = base
            info["loc"] = "base"
        elif t in ("F1", "F2", "F3"):               # a bare Fx token = damage loc
            info["loc"] = t
        elif tl in ("trace", "light", "moderate", "severe"):
            info["grade"] = tl
        elif (tl.startswith("r") or tl.startswith("c")) and tl[1:].isdigit():
            info["rep"] = int(tl[1:])               # r2 / c1 -> replicate
    return info


def cosine_to_refs(shift):
    """Angle-based nearest fingerprint over MUTUALLY observable modes."""
    scores = {}
    for loc, ref in REF.items():
        r = np.array(ref, float)
        mask = ~np.isnan(shift) & ~np.isnan(r)
        if mask.sum() < 1:
            continue
        a, b = shift[mask], r[mask]
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        scores[loc] = float(np.dot(a, b) / denom) if denom else 0.0
    return dict(sorted(scores.items(), key=lambda kv: -kv[1]))


def nearest_grade(loc, df1):
    if loc not in GRADE_F1 or np.isnan(df1):
        return None
    return min(GRADE_F1[loc], key=lambda g: abs(GRADE_F1[loc][g] - df1))


def find_baseline(info, override):
    if override:
        return override if os.path.isdir(override) else os.path.join(CH, override)
    # position-matched baseline (shifts MUST be vs the same sensor position)
    if info["pos_explicit"]:
        for c in sorted(glob.glob(os.path.join(CH, f"sensor{info['pos']}_baseline*")),
                        reverse=True):
            return c
    for c in ("day7_baseline", "day6_baseline", "day4_baseline"):
        if os.path.isdir(os.path.join(CH, c)):
            return os.path.join(CH, c)
    return None


def resolve(label):
    p = label if os.path.isdir(label) else os.path.join(CH, os.path.basename(label))
    return p if os.path.isdir(p) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("label", help="capture folder or label (under characterisation/)")
    ap.add_argument("--baseline", default=None, help="override baseline folder/label")
    args = ap.parse_args()

    folder = resolve(args.label)
    if not folder:
        sys.exit(f"no such capture folder: {args.label}")
    info = parse_label(folder)

    print("=" * 60)
    print(f"CAPTURE: {info['name']}")
    print("=" * 60)

    # 1. FROM THE LABEL
    print("FROM THE LABEL (what you intended):")
    print(f"  sensor on : {POS_NAME.get(info['pos'], info['pos'])}"
          + ("" if info["pos_explicit"] else "  (implicit — top)"))
    if info["is_baseline"]:
        print("  this is a BASELINE (undamaged reference) — no damage claimed.")
    else:
        print(f"  damage at : {LOC_NAME.get(info['loc'], info['loc'] or '??')}")
        print(f"  grade     : {(info['grade'] or '??').upper()}"
              + (f"   replicate {info['rep']}" if info["rep"] else ""))

    # measured vector
    v = modal_vector(folder)
    if v is None:
        sys.exit("  (no raw CSVs found)")
    fmt = lambda a: " / ".join("  --  " if np.isnan(x) else f"{x:7.3f}" for x in a)
    print(f"\n  measured f : {fmt(v)} Hz")

    bl = find_baseline(info, args.baseline)
    if not bl:
        print("  (no baseline found — cannot compute shifts)")
        return
    b = modal_vector(bl)
    print(f"  baseline   : {fmt(b)} Hz   [{os.path.basename(bl)}]")

    if info["is_baseline"]:
        print("\nFROM THE DATA — mode observability from this sensor position:")
        amps = modal_amplitudes(folder, v)
        labels = ["f1", "f2", "f3"]
        if amps is not None:
            for i, lab in enumerate(labels):
                if np.isnan(amps[i]):
                    print(f"  {lab} ({v[i] if not np.isnan(v[i]) else '?':>6}) : not found")
                    continue
                bar = "#" * max(1, int(round(amps[i] * 30)))
                tag = "strong" if amps[i] > 0.33 else ("WEAK" if amps[i] > 0.05 else "≈node/blind")
                print(f"  {lab} ({v[i]:6.2f} Hz) : {amps[i]*100:5.1f}% {bar:30s} {tag}")
            print("  (amplitude relative to the strongest mode; low = sensor near that mode's node)")
        return

    # 2. FROM THE DATA
    shift = (v - b) / b * 100.0
    cell = lambda x: " n/a " if np.isnan(x) else f"{x:+5.1f}%"
    n_obs = int(np.sum(~np.isnan(shift)))
    print("\nFROM THE DATA (independent of the label):")
    print(f"  shifts     : Δf1 {cell(shift[0])}   Δf2 {cell(shift[1])}   Δf3 {cell(shift[2])}"
          f"   ({n_obs}/3 modes observable)")

    grade = nearest_grade(info["loc"], shift[0]) if info["loc"] else None
    peak = np.nanmax(np.abs(shift))

    if n_obs < 2:
        # one mode can't localise: every damage lowers f1, so cosine is degenerate
        print("  location   : NOT DETERMINABLE — only 1 mode observable "
              "(need ≥2 to separate locations)")
        print(f"  severity   : Δf1 {cell(shift[0])}, peak modal shift {peak:.0f}%")
        print("\n  -> cannot check the label from data with <2 modes; trust the "
              "capture only if the plate was confirmed at the rig.")
        return

    scores = cosine_to_refs(shift)
    best = list(scores)[0]
    second = list(scores)[1] if len(scores) > 1 else None
    margin = scores[best] - (scores[second] if second else -1)
    grade = nearest_grade(best, shift[0])
    print(f"  location   : {LOC_NAME[best]}   (match {scores[best]:.3f}"
          + (f"; next {second} {scores[second]:.3f})" if second else ")"))
    print(f"  severity   : Δf1 {cell(shift[0])}, peak modal shift {peak:.0f}%"
          + (f"  -> ~{grade.upper()}" if grade else ""))

    # 3. AGREEMENT
    ambiguous = margin < 0.02
    if info["loc"] is None:
        print("\n  (no damage location in the label to check against.)")
    elif best == info["loc"]:
        print(f"\n  -> LABEL ✓  data signature matches '{info['loc']}'.")
    elif ambiguous:
        print(f"\n  -> ~ label '{info['loc']}' vs best '{best}' are too close to "
              f"separate here (margin {margin:.3f}); not a confident mismatch.")
    else:
        print(f"\n  -> ⚠ MISMATCH: label says '{info['loc']}' but the signature "
              f"best matches '{best}' (margin {margin:.3f}). Check the plate.")
    if info["grade"] and grade and grade != info["grade"]:
        print(f"     note: label grade '{info['grade']}' vs data ~'{grade}' "
              f"(Δf1 depends on location; treat as approximate).")

    if np.isnan(shift[1]):
        print("\n  observability: f2 weak/unobserved from this sensor position "
              "(near the mode-2 node) — location leans on f1 + f3.")


if __name__ == "__main__":
    main()

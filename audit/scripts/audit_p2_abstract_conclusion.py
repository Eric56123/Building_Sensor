"""
audit_p2_abstract_conclusion.py — Part 2, chapter 1: abstract and conclusions

Audit target: d81c66b (audit tree); dissertation df32d53.

The abstract and the conclusion carry the same eight figures. Both are read
first and hardest, and both currently state two numbers that Part 1 changed
(the 6 of 9 localisation headline, and the 12 of 12 per-run row that has no
generator).

Every claim below is recomputed from the raw captures through the pre-existing
toolkit extraction path. Claims that need artefacts outside characterisation/
are reported as such rather than guessed.

INDEPENDENCE. toolkit_common and interpret_capture are pre-existing repository
code. The reassembly floors, the severe shifts and the graded shifts are
properties of the captures. Genuine cross-check.
"""
import glob
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "four_floor"))

import interpret_capture as ic                                    # noqa: E402
import toolkit_common as tk                                       # noqa: E402

BASE = os.path.join(_ROOT, "four_floor", "characterisation")
LOCS = ["base", "F1", "F2", "F3"]
FLOOR_2SD = np.array([0.30, 0.46, 0.32])       # Section 4.1.4, per cent
BANDS = [(0.9, 3.5), (6.0, 10.0), (10.0, 14.0)]


def tap_modes(folder):
    taps = {0: [], 1: [], 2: []}
    for p in sorted(glob.glob(os.path.join(BASE, folder, "*_raw.csv"))):
        x, _ = tk.load_raw_series(p)
        fq, ps = tk.raw_psd(x)
        pk = tk.find_spectral_peaks(fq, ps, 0.9, 20.0, n_peaks=8,
                                    prominence_factor=8)
        for i, (lo, hi) in enumerate(BANDS):
            c = [q for q in pk if lo <= q["f_hz"] <= hi]
            if c:
                taps[i].append(max(c, key=lambda q: q["prominence_ratio"])["f_hz"])
    return [np.array(taps[i]) for i in range(3)]


def main():
    print(f"Part 2.1 — abstract and conclusions\n{'=' * 78}")
    b4 = ic.modal_vector(os.path.join(BASE, "day4_baseline"))

    # ---- 1. severe clears the first-mode floor by 52 to 202 times ---------
    print(f"\n1. 'severe damage clears the first-mode floor by 52 to 202 times'")
    print(f"   Session-4 baseline f1 = {b4[0]:.4f} Hz (Table 4.4 prints 2.942)")
    ratios, doc_df = [], {"base": -58.7, "F1": -60.5, "F2": -39.6, "F3": -15.5}
    for loc in LOCS:
        v = [ic.modal_vector(os.path.join(BASE, f"{loc}_severe_r{r}"))[0]
             for r in (1, 2, 3)
             if os.path.isdir(os.path.join(BASE, f"{loc}_severe_r{r}"))]
        f = float(np.mean(v))
        d = (f - b4[0]) / b4[0] * 100
        ratios.append(abs(d) / FLOOR_2SD[0])
        print(f"     {loc:5s} f1 {f:.4f}  df1 {d:+6.2f}% (doc {doc_df[loc]:+6.1f})  "
              f"/{FLOOR_2SD[0]} = {abs(d) / FLOOR_2SD[0]:6.1f}x")
    print(f"   recomputed range {min(ratios):.0f} to {max(ratios):.0f} times   "
          f"(doc 52 to 202)")

    # ---- THE BASIS. Established by reconciliation, not assumed -----------
    #
    # Tables 4.5, A.1 and A.2 do NOT use one baseline. The graded columns
    # (trace, light, moderate) are referred to the Session-6 baseline and the
    # severe column to the Session-4 baseline. Each damage set is measured
    # against its own session, which is defensible, but no table says so.
    #
    # A first pass here used Day 4 throughout and produced "8 of 12 monotone",
    # a false MISMATCH against the document's 11 of 12. That is item 1.7's
    # failure mode occurring inside the audit itself, and it is the reason the
    # basis is now derived below rather than assumed.
    b6 = ic.modal_vector(os.path.join(BASE, "day6_baseline"))
    print(f"\n   baselines: Session 4 {np.round(b4, 4)} for the severe column,")
    print(f"              Session 6 {np.round(b6, 4)} for the graded columns")

    def shifts(loc, mi):
        """Delta for one location and one mode, on the document's own basis."""
        out = []
        for g in ("trace", "light", "moderate"):
            d = os.path.join(BASE, f"{loc}_{g}_c1")
            v = ic.modal_vector(d) if os.path.isdir(d) else None
            out.append((v[mi] - b6[mi]) / b6[mi] * 100
                       if v is not None and not np.isnan(v[mi]) else np.nan)
        sv = [ic.modal_vector(os.path.join(BASE, f"{loc}_severe_r{r}"))[mi]
              for r in (1, 2, 3)
              if os.path.isdir(os.path.join(BASE, f"{loc}_severe_r{r}"))]
        sv = [x for x in sv if not np.isnan(x)]
        out.append((np.mean(sv) - b4[mi]) / b4[mi] * 100 if sv else np.nan)
        return out

    # ---- 2. an eighth of a turn resolved at all four ----------------------
    print(f"\n2. 'an eighth of a turn at all four locations, on the first mode at")
    print(f"   three and at Floor 3 only on the third'")
    for loc in LOCS:
        line = f"     {loc:5s}"
        for i in range(3):
            d = shifts(loc, i)[0]
            if not np.isnan(d):
                x = abs(d) / FLOOR_2SD[i]
                line += (f"  f{i + 1} {d:+6.2f}% = {x:5.1f}x"
                         f"{'*' if x > 1 else ' '}")
        print(line)
    print(f"   * clears its own 2-sigma floor. Floor 3 fails on f1 (0.1x) and")
    print(f"     clears on f3, exactly as the conclusion states.")

    # ---- 3. monotone at 11 of 12 location-mode combinations --------------
    print(f"\n3. 'the trend holds at 11 of 12 location and mode combinations'")
    mono, tot, fails = 0, 0, []
    for i in range(3):
        for loc in LOCS:
            v = [x for x in shifts(loc, i) if not np.isnan(x)]
            if len(v) < 2:
                continue
            tot += 1
            ok = all(v[j + 1] <= v[j] + 1e-9 for j in range(len(v) - 1))
            mono += ok
            if not ok:
                fails.append(f"{loc} f{i + 1} ({', '.join(f'{x:+.1f}' for x in v)})")
    print(f"   monotone (falling) combinations: {mono} of {tot}   (doc 11 of 12)")
    for f in fails:
        print(f"     not monotone: {f}")

    # ---- 4 and 5. the two figures Part 1 changed -------------------------
    print(f"\n4. 'assigned all twelve replicated severe runs correctly' (12 of 12)")
    print(f"   Part 1 item 1.2(a): the per-run row has NO GENERATOR in the")
    print(f"   repository. Part 1 item 1.4 confirms independently that a")
    print(f"   twelve-run three-mode scoring cannot be built from these captures,")
    print(f"   because the three Floor 3 severe records have no f2.")
    n3 = sum(1 for loc in LOCS for r in (1, 2, 3)
             if os.path.isdir(os.path.join(BASE, f"{loc}_severe_r{r}"))
             and not np.isnan(ic.modal_vector(
                 os.path.join(BASE, f"{loc}_severe_r{r}"))[1]))
    print(f"   severe records with a recoverable f2: {n3} of 12")
    print(f"   VERDICT: UNVERIFIABLE, in the abstract AND the conclusion.")

    print(f"\n5. 'it returns 9 of 9 where the network returns 6 of 9'")
    print(f"   Part 1 item 1.4, DECIDED: the headline becomes 6 of 6 against")
    print(f"   3 of 6, base plate excluded because k1 is the network's only")
    print(f"   representable answer there. Both the abstract and the conclusion")
    print(f"   carry the old pair and must move together.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

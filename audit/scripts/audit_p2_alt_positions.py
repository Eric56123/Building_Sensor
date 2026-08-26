"""
audit_p2_alt_positions.py — closes UNVERIFIABLE U4: the "18 of 18" claim

Audit target: df32d53.

CLAIM (abstract, Conclusion, Section 4.5 l.2140, Table 5.1):
  "All eighteen damaged cases recorded at the two new positions (3 locations x
   3 replicates x 2 positions) were assigned to the correct location by the
   nearest signature rule of Section 4.4.1, under the per-run convention, using
   the top-storey replicate means as reference signatures. Those references were
   recorded at a different sensor position from the runs being classified, so no
   run contributes to the signature it is tested against."

METHOD, as stated by the document:
  * signature = |modal shift| vs a POSITION-SPECIFIC baseline, normalised by the
    mode-specific 2-sigma reassembly floor (the Section 4.4.1 convention)
  * references = the top-storey severe replicate MEANS
  * rule      = nearest reference under the per-run convention, i.e. RMS over the
    modes shared by the run and the reference
  * NO leave-one-out. The references come from a different sensor position, so
    there is nothing to exclude. An earlier attempt at this figure applied a
    self-exclusion and returned 8 of 8; that was an artefact of the attempt, not
    a property of the data. The self-exclusion was the wrong construct.

INDEPENDENCE. interpret_capture.modal_vector and the FLOOR_2SD normalisation are
pre-existing repository code; the per-run RMS rule is taken from
audit_1_2_permutation.loo_perrun. Genuine cross-check.
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _HERE)
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "four_floor"))

import interpret_capture as ic                                    # noqa: E402

BASE = os.path.join(_ROOT, "four_floor", "characterisation")
FLOOR_2SD = 2 * np.array([0.15, 0.23, 0.16])
ALT_LOCS = ["base", "F1", "F3"]          # Floor 2 was not repeated at the new positions
ALL_LOCS = ["base", "F1", "F2", "F3"]


def mv(folder):
    p = os.path.join(BASE, folder)
    return ic.modal_vector(p) if os.path.isdir(p) else None


def signature(folder, baseline):
    v, b = mv(folder), mv(baseline)
    if v is None or b is None:
        return None
    return np.abs((v - b) / b * 100.0) / FLOOR_2SD


def per_run_distance(x, ref):
    """Section 4.4.1 per-run convention: RMS over the modes shared by the run
    and the reference. Taken from audit_1_2_permutation.loo_perrun."""
    sh = ~np.isnan(x) & ~np.isnan(ref)
    return float(np.sqrt(np.mean((x[sh] - ref[sh]) ** 2))) if sh.any() else np.inf


def top_storey_references(locs):
    """Top-storey severe replicate means, one per location, vs the Session-4
    top-sensor baseline. These are the reference signatures."""
    refs = {}
    for loc in locs:
        sig = [signature(f"{loc}_severe_r{r}", "day4_baseline") for r in (1, 2, 3)]
        sig = [s for s in sig if s is not None]
        if sig:
            refs[loc] = np.nanmean(np.array(sig), axis=0)
    return refs


def main():
    print(f"Part 2 — the 18 alternate-position records (U4)\n{'=' * 82}")

    # Which baseline belongs to each alternate position.
    pos_baseline = {"sensorF1": "sensorF1_baseline",
                    "sensorF2": "sensorF2_baseline"}
    alt_b = "sensorF2_baseline_day7b"
    print(f"\nBASELINES")
    for p, b in pos_baseline.items():
        v = mv(b)
        print(f"  {p:9s} {b:26s} f = {np.round(v, 4)}")
    if mv(alt_b) is not None:
        print(f"  {'sensorF2':9s} {alt_b:26s} f = {np.round(mv(alt_b), 4)}"
              f"   <- alternative, tested below")

    for nclass, locs in (("3-class", ALT_LOCS), ("4-class", ALL_LOCS)):
        refs = top_storey_references(locs)
        print(f"\n{'=' * 82}\n{nclass.upper()} — references from the top storey: "
              f"{sorted(refs)}")
        for loc in sorted(refs):
            print(f"  ref {loc:5s} {np.round(refs[loc], 2)}")

        total = correct = 0
        rows = []
        for pos in ("sensorF1", "sensorF2"):
            for loc in ALT_LOCS:
                for r in (1, 2, 3):
                    f = f"{pos}_{loc}_severe_r{r}"
                    x = signature(f, pos_baseline[pos])
                    if x is None:
                        continue
                    d = {c: per_run_distance(x, refs[c]) for c in refs}
                    call = min(d, key=d.get)
                    total += 1
                    ok = call == loc
                    correct += ok
                    margin = (sorted(d.values())[1] - sorted(d.values())[0]
                              if len(d) > 1 else np.nan)
                    rows.append((f, loc, call, ok, d[loc], margin))

        print(f"\n  {'record':30s} {'truth':6s} {'call':6s} {'ok':3s} "
              f"{'d(own)':>7s} {'margin':>7s}")
        for f, loc, call, ok, dn, m in rows:
            print(f"  {f:30s} {loc:6s} {call:6s} {'yes' if ok else 'NO ':3s} "
                  f"{dn:7.2f} {m:7.2f}")
        print(f"\n  SCORE: {correct} of {total}   (document claims 18 of 18)")
        if nclass == "4-class":
            print(f"  4-class is the harder problem: Floor 2 is offered as a")
            print(f"  candidate even though it was not repeated at the new")
            print(f"  positions, so a run can be misassigned to it.")

    # Sensitivity to the sensorF2 baseline choice.
    if mv(alt_b) is not None:
        refs = top_storey_references(ALL_LOCS)
        print(f"\n{'=' * 82}\nSENSITIVITY: sensorF2 scored against {alt_b}")
        tot = cor = 0
        for loc in ALT_LOCS:
            for r in (1, 2, 3):
                x = signature(f"sensorF2_{loc}_severe_r{r}", alt_b)
                if x is None:
                    continue
                d = {c: per_run_distance(x, refs[c]) for c in refs}
                tot += 1
                cor += min(d, key=d.get) == loc
        print(f"  sensorF2 alone: {cor} of {tot} "
              f"(4-class, day7b baseline)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

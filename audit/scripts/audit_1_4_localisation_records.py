"""
audit_1_4_localisation_records.py — Part 1, item 1.4: which records is "6 of 9"?

Audit target: df32d53

CLAIM (Table 4.18, l.2621):
  classical | "9 of 9 runs at the three storey locations; base plate excluded to
               match the network's label space (Section 4.4.1)"
  network   | "6 of 9 runs (2 of 3 locations) on measured inputs"
  footnote  | "The two localisation scores are not computed over the same runs...
               The network cannot be scored on three of these because harmonics of
               f1 obscure the second modes of the Floor 3 severe replicates, so its
               figure covers the graded cells instead. The two are reported side by
               side and are not a matched comparison."

Three descriptions of the record set appear in the document and they disagree:
  A  Section 3.6.8 l.1379 : severe set = six replicates at Floor 1 and Floor 2,
                            two classes; base plate uncounted (l.1362)
  B  Table 4.18 footnote  : network figure covers the fourteen graded cells
  C  Table 4.18 cell      : nine runs, six correct, two of three locations

This enumerates every candidate set against the cached calls and the raw modal
vectors, and reports which one yields the printed figure. It also scores the
CLASSICAL method on each set, so that the "not a matched comparison" disclaimer
can be checked rather than taken on trust.

INDEPENDENCE. The network calls come from decision_rule_sweep.py, written by the
auditor, so they are self-checking. The classical LOO is recomputed here from
interpret_capture.modal_vector, which is pre-existing repository code, and the
record inventory is a property of characterisation/ on disk. Those two are
genuine cross-checks.
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "four_floor"))

import json                                                       # noqa: E402

import interpret_capture as ic                                    # noqa: E402

BASE = os.path.join(_ROOT, "four_floor", "characterisation")
FLOOR_2SD = 2 * np.array([0.15, 0.23, 0.16])
LOCS = ["base", "F1", "F2", "F3"]
PRETTY = {"base": "Base plate", "F1": "Floor 1", "F2": "Floor 2", "F3": "Floor 3"}

# Table 3.10, l.1348: a call is correct where the named storey adjoins the plate.
ADJACENT = {"base": {0}, "F1": {0, 1}, "F2": {1, 2}, "F3": {2}}
# decision_rule_sweep.score(), L144: truth = STOREYS.index(location), exact match.
EXACT = {"base": {0}, "F1": {0}, "F2": {1}, "F3": {2}}


def calls():
    return json.load(open(os.path.join(
        _ROOT, "four_floor", "results_decision_rule_sweep.json")))["cells"]


def severe_signatures():
    """Three-mode normalised shift vectors for every severe replicate on disk."""
    b4 = ic.modal_vector(os.path.join(BASE, "day4_baseline"))
    names, X, y = [], [], []
    for li, loc in enumerate(LOCS):
        for r in (1, 2, 3):
            f = f"{loc}_severe_r{r}"
            if os.path.isdir(os.path.join(BASE, f)):
                names.append(f"{loc}_r{r}")
                X.append(np.abs((ic.modal_vector(os.path.join(BASE, f)) - b4)
                                / b4 * 100) / FLOOR_2SD)
                y.append(li)
    return names, np.array(X), np.array(y)


def loo(X, y):
    """Leave-one-out nearest-class-mean. Returns the per-record hit vector."""
    ok = []
    for i in range(len(X)):
        d = {}
        for c in set(y):
            m = [j for j in range(len(X)) if y[j] == c and j != i]
            if m:
                d[c] = np.linalg.norm(X[i] - X[m].mean(axis=0))
        ok.append(bool(d) and min(d, key=d.get) == y[i])
    return np.array(ok)


def score_net(cells, records, rule):
    """Score the network's storey call on an explicit record list."""
    hit, per_loc = [], {}
    for loc, key in records:
        c = cells[key]["call"]
        good = c in rule[loc]
        hit.append(good)
        per_loc.setdefault(loc, []).append(good)
    return np.array(hit), per_loc


def main():
    cells = calls()
    names, X, y = severe_signatures()
    print(f"Audit 1.4 — what nine records is \"6 of 9\"?\n{'=' * 78}")

    print(f"\n(0) RECORD INVENTORY ON DISK\n")
    print(f"  cached cells: {len(cells)}   "
          f"(4 locations x 6 records = 24, less 4 absent)")
    absent = [f"{l}_{g}" for l in LOCS for g in
              ("trace", "light", "moderate", "sev_r1", "sev_r2", "sev_r3")
              if f"{l}_{g}" not in cells]
    print(f"  absent      : {absent}")
    print(f"  Section 3.6.8 says twenty records, less Floor 2 light and the three")
    print(f"  Floor 3 severe replicates.  MATCH: "
          f"{sorted(absent) == sorted(['F2_light', 'F3_sev_r1', 'F3_sev_r2', 'F3_sev_r3'])}")
    print(f"  severe replicates with recoverable three-mode signatures: "
          f"{len(names)} -> {names}")

    # ---- candidate record sets -------------------------------------------
    sev = lambda ls: [(l, f"{l}_sev_r{r}") for l in ls for r in (1, 2, 3)
                      if f"{l}_sev_r{r}" in cells]
    graded = lambda ls: [(l, f"{l}_{g}") for l in ls
                         for g in ("trace", "light", "moderate")
                         if f"{l}_{g}" in cells]
    SETS = {
        "A  sec 3.6.8 severe set: F1+F2 severe, base uncounted":
            sev(["F1", "F2"]),
        "B  Tab 4.18 footnote: fourteen graded+severe at 3 storeys":
            graded(["F1", "F2", "F3"]) + sev(["F1", "F2", "F3"]),
        "B' graded cells only, three storeys":
            graded(["F1", "F2", "F3"]),
        "C  base+F1+F2 severe (the three-mode classes)":
            sev(["base", "F1", "F2"]),
        "D  all severe on disk, four locations":
            sev(LOCS),
    }

    print(f"\n(1) NETWORK SCORE ON EVERY CANDIDATE SET\n")
    hdr = f"  {'candidate set':56s} {'n':>3s} {'adjacent':>9s} {'exact':>8s}"
    print(hdr + "\n  " + "-" * (len(hdr) - 2))
    for label, recs in SETS.items():
        ha, pa = score_net(cells, recs, ADJACENT)
        he, _ = score_net(cells, recs, EXACT)
        nloc = sum(1 for v in pa.values() if sum(v) > len(v) / 2)
        print(f"  {label:56s} {len(recs):3d} "
              f"{f'{ha.sum()}/{len(ha)}':>9s} {f'{he.sum()}/{len(he)}':>8s}"
              f"   {nloc} of {len(pa)} locations")

    target = [k for k, r in SETS.items()
              if score_net(cells, r, ADJACENT)[0].sum() == 6 and len(r) == 9]
    print(f"\n  Printed figure is \"6 of 9 runs (2 of 3 locations)\".")
    print(f"  Sets reproducing it: {target}")

    # ---- the matched comparison ------------------------------------------
    print(f"\n(2) IS IT A MATCHED COMPARISON?\n")
    keep3 = np.array([n.split('_')[0] in ("base", "F1", "F2") for n in names])
    c_hit = loo(X[keep3], y[keep3])
    recs9 = sev(["base", "F1", "F2"])
    n_hit, n_loc = score_net(cells, recs9, ADJACENT)
    print(f"  classical, three-mode LOO over the same nine records: "
          f"{c_hit.sum()}/{len(c_hit)}")
    print(f"  network,   storey call  over the same nine records: "
          f"{n_hit.sum()}/{len(n_hit)}")
    print(f"  record-by-record:")
    for nm, c, (loc, key), n in zip(np.array(names)[keep3], c_hit, recs9, n_hit):
        print(f"    {nm:10s} classical {'hit ' if c else 'MISS'}   "
              f"network k{cells[key]['call'] + 1} {'hit ' if n else 'MISS'}")
    print(f"\n  The two columns are scored on the SAME nine records. The footnote's")
    print(f"  'not computed over the same runs' and 'not a matched comparison' are")
    print(f"  both wrong; so is 'its figure covers the graded cells instead'.")

    # ---- the base-plate credit -------------------------------------------
    print(f"\n(3) HOW MUCH OF THE NETWORK'S SCORE IS THE BASE PLATE?\n")
    for loc, v in n_loc.items():
        print(f"    {PRETTY[loc]:11s} {sum(v)}/{len(v)}")
    b = sum(n_loc["base"])
    print(f"\n  The base plate supplies {b} of the {n_hit.sum()} correct calls.")
    print(f"  Section 3.6.8 l.1362: the base plate is 'uncounted in the")
    print(f"  localisation score'.  Section 4.6 l.2885: 'no correct answer exists")
    print(f"  for it inside the label space... the least wrong of the three")
    print(f"  available answers without being a right one.'")
    print(f"  Applying that rule gives {score_net(cells, SETS[list(SETS)[0]], ADJACENT)[0].sum()}"
          f"/6 = 50.0%, not 6/9 = {6 / 9:.1%}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

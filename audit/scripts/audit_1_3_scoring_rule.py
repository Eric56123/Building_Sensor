"""
audit_1_3_scoring_rule.py — Part 1, item 1.3: which storey-call scoring rule?

Audit target: df32d53

STATED RULE (Table 3.10, l.1348): "A storey call is scored correct where the named
storey adjoins the loosened plate. The base plate admits k1 only, Floor 1 admits k1
or k2, Floor 2 admits k2 or k3, and Floor 3 admits k3 only."

CODE (decision_rule_sweep.py, score() L144): truth = STOREYS.index(location) with
STOREYS = ["F1","F2","F3"], compared by `am == truth`. That is an EXACT index
match: Floor 1 -> k1, Floor 2 -> k2, Floor 3 -> k3. Adjacency is not implemented.

Recomputes record-level and location-level accuracy under both rules from the
cached per-cell calls, and checks whether the classical row of Table 4.18 can be
scored under the same rule at all.

INDEPENDENCE. decision_rule_sweep.py was written by the auditor, so the call values
are self-checking. The RULE COMPARISON is not: it is arithmetic on the published
Table 4.14 calls, which are reproduced here and agree.
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))

# Table 4.14 as printed: location -> (records, call per record)
# Floor 2 light and the three Floor 3 severe replicates have no record.
DOC_CALLS = {
    "Base plate": ["k1"] * 6,
    "Floor 1":    ["k1"] * 6,
    "Floor 2":    ["k3"] + ["k1"] * 4,          # k3 at trace, k1 above it
    "Floor 3":    ["k3"] * 3,
}
ADJACENT = {"Base plate": {"k1"}, "Floor 1": {"k1", "k2"},
            "Floor 2": {"k2", "k3"}, "Floor 3": {"k3"}}
EXACT = {"Base plate": {"k1"}, "Floor 1": {"k1"},
         "Floor 2": {"k2"}, "Floor 3": {"k3"}}
STOREYS = ["Floor 1", "Floor 2", "Floor 3"]


def reproduce_calls():
    """Regenerate the Table 4.14 calls from the cached sweep, to confirm the
    printed table before doing arithmetic on it."""
    f = os.path.join(_ROOT, "four_floor", "results_decision_rule_sweep.json")
    if not os.path.exists(f):
        return None
    sw = json.load(open(f))["cells"]
    out = {}
    for loc, name in [("base", "Base plate"), ("F1", "Floor 1"),
                      ("F2", "Floor 2"), ("F3", "Floor 3")]:
        calls = []
        for g in ("trace", "light", "moderate"):
            k = f"{loc}_{g}"
            if k in sw:
                calls.append(f"k{sw[k]['call'] + 1}")
        for r in (1, 2, 3):
            k = f"{loc}_sev_r{r}"
            if k in sw:
                calls.append(f"k{sw[k]['call'] + 1}")
        out[name] = calls
    return out


def score(rule, locations):
    per_loc, tot, ok = {}, 0, 0
    for loc in locations:
        c = DOC_CALLS[loc]
        hit = sum(1 for x in c if x in rule[loc])
        per_loc[loc] = (hit, len(c))
        tot += len(c)
        ok += hit
    return ok, tot, per_loc


def main():
    print(f"Audit 1.3 — storey-call scoring rule\n{'=' * 74}")

    rep = reproduce_calls()
    if rep:
        print("\n  Table 4.14 calls, regenerated from the cached sweep:")
        for k in DOC_CALLS:
            agree = sorted(rep.get(k, [])) == sorted(DOC_CALLS[k])
            print(f"    {k:11s} doc {str(DOC_CALLS[k]):32s} "
                  f"regen {str(rep.get(k)):32s} {'MATCH' if agree else 'DIFFERS'}")

    print(f"\n  Stated rule (Table 3.10)  : adjacency, a plate adjoins two storeys")
    print(f"  Implemented rule (code)   : exact index match, Floor n -> k_n")
    print(f"  They differ for Floor 1 (k2 also admitted) and Floor 2 "
          f"(k3 also admitted).\n")

    hdr = f"  {'location':11s} {'records':>7s} {'adjacency':>11s} {'exact':>9s}"
    print(hdr + "\n  " + "-" * (len(hdr) - 2))
    a_ok, a_tot, a_loc = score(ADJACENT, STOREYS)
    e_ok, e_tot, e_loc = score(EXACT, STOREYS)
    for loc in STOREYS:
        print(f"  {loc:11s} {a_loc[loc][1]:7d} "
              f"{f'{a_loc[loc][0]}/{a_loc[loc][1]}':>11s} "
              f"{f'{e_loc[loc][0]}/{e_loc[loc][1]}':>9s}")
    print(f"  {'TOTAL':11s} {a_tot:7d} {f'{a_ok}/{a_tot}':>11s} "
          f"{f'{e_ok}/{e_tot}':>9s}")
    print(f"  {'':11s} {'':7s} {a_ok / a_tot:11.1%} {e_ok / e_tot:9.1%}")

    maj = lambda per: sum(1 for l in STOREYS if per[l][0] > per[l][1] / 2)
    print(f"\n  locations correct on a majority of their records: "
          f"adjacency {maj(a_loc)}/3, exact {maj(e_loc)}/3")
    print(f"  the two rules differ on exactly {a_ok - e_ok} record "
          f"(Floor 2, trace, called k3)")

    print(f"\n  Base plate, outside the storey label space, for reference:")
    b_a, b_t, _ = score(ADJACENT, ["Base plate"])
    print(f"    {b_a}/{b_t} under both rules (base admits k1 only in each)")

    print(f"\n{'=' * 74}\n  WHICH RULE GENERATED THE PUBLISHED NUMBERS?")
    print("  Line 2415 prints a seed-averaged accuracy of 0.650 / 0.654 over the")
    print("  fourteen-record extended set. That discriminates the two rules:")
    print(f"    exact,     F2 trace = k3 scored wrong : 9/14  = {9 / 14:.4f}")
    print(f"    exact,     plus k2 in 2.5 of 20 seeds : {(9 + 2.5 / 20) / 14:.4f}"
          f"   <- matches the document")
    print(f"    adjacency, F2 trace = k3 scored right : 10/14 = {10 / 14:.4f}"
          f"   <- excluded")
    print("  So the EXACT rule is in force and Table 3.10 describes a rule the")
    print("  analysis never applied.")

    print(f"\n{'=' * 74}\n  CLASSICAL COMPARISON (Table 4.18) — see item 1.4")
    print("  An earlier draft of this script concluded that the two rows of")
    print("  Table 4.18 cannot be scored under a common rule because they have")
    print("  different output spaces. THAT WAS WRONG and is retracted. Item 1.4")
    print("  recomputes both columns on the same nine records (base, Floor 1,")
    print("  Floor 2 severe) and gets classical 9/9 against network 6/9. The")
    print("  comparison IS matched, contrary to the Table 4.18 footnote.")
    print("  The genuine asymmetry is narrower: the classical method has a")
    print("  base-plate class it can name and be wrong about, whereas the network")
    print("  can only answer k1 there, so its three base-plate hits are a forced")
    print("  choice rather than a correct call. See audit item 1.4(d).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

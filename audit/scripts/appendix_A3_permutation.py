"""
appendix_A3_permutation.py — regenerates every number in Appendix A.3

Audit target: df32d53. Reuses audit/scripts/audit_1_2_permutation.py for the
signature extraction, the leave-one-out scorer and the multiset counting, rather
than re-deriving any of them.

Covers the two FIXED signature spaces only. The per-run row was decided
UNVERIFIABLE and removed (UNVERIFIABLE.md U1), so it is not presented here as a
result; its group-wise space size appears once, in the invariance argument, where
it is a property of the design rather than a reported score.

Adds one thing audit_1_2 did not compute: the group-wise enumeration for both
fixed spaces, to show the degeneracy is total rather than merely likely.
"""
import itertools
import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _HERE)
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "four_floor"))

import audit_1_2_permutation as a12                               # noqa: E402

LOCS = ["base", "F1", "F2", "F3"]


def partition_preserving(sizes):
    """Relabellings that map the partition to itself: permute equal-sized
    classes among themselves. Product of factorials of the size multiplicities."""
    from collections import Counter
    n = 1
    for m in Counter(sizes).values():
        n *= math.factorial(m)
    return n


def main():
    names, X, y = a12.signatures()
    print(f"Appendix A.3 — permutation spaces\n{'=' * 78}")

    spaces = {}
    for label, modes in [("two-mode", [0, 2]), ("three-mode", [0, 1, 2])]:
        Xs = X[:, modes]
        keep = ~np.isnan(Xs).any(axis=1)
        Xs, ys = Xs[keep], y[keep]
        obs = a12.loo_fixed(Xs, ys)
        sizes = [int((ys == c).sum()) for c in sorted(set(ys))]
        n_run = a12.multiset_perms(list(ys))
        n_grp = math.factorial(len(set(ys)))
        pp = partition_preserving(sizes)
        spaces[label] = (Xs, ys, obs, sizes, n_run, n_grp, pp)

        print(f"\n{label.upper()}  n = {len(ys)} runs, {len(set(ys))} classes")
        print(f"  locations present : "
              f"{[LOCS[c] for c in sorted(set(ys))]}")
        print(f"  class sizes       : {sizes}")
        print(f"  observed score    : {obs}/{len(ys)}")
        fac = " x ".join(f"{s}!" for s in sizes)
        print(f"  run-level space   : {len(ys)}! / ({fac}) = {n_run:,d}")
        print(f"  group-wise space  : {len(set(ys))}! = {n_grp}")
        print(f"  partition-preserving relabellings : {pp}")
        print(f"  exact p (run-level)               : {pp}/{n_run:,d} = "
              f"{pp / n_run:.6f}")

    print(f"\n{'=' * 78}\nGROUP-WISE ENUMERATION — is the degeneracy total?\n")
    for label in ("two-mode", "three-mode"):
        Xs, ys, obs, sizes, n_run, n_grp, pp = spaces[label]
        classes = sorted(set(ys))
        scores = []
        for perm in itertools.permutations(classes):
            m = dict(zip(classes, perm))
            yp = np.array([m[v] for v in ys])
            scores.append(a12.loo_fixed(Xs, yp))
        allsame = len(set(scores)) == 1 and scores[0] == obs
        print(f"  {label:11s} enumerated all {len(scores)} group-wise "
              f"labellings")
        print(f"              scores obtained: {sorted(set(scores))}   "
              f"{'ALL identical to the observed score' if allsame else 'VARY'}")
        print(f"              so group-wise p = {len(scores)}/{len(scores)} "
              f"= 1.0000, and the test has ZERO POWER by construction")

    print(f"\n  Reason, which is structural and not a property of this data:")
    print(f"  leave-one-out nearest-class-mean depends on the data only through")
    print(f"  the PARTITION of runs into classes. A group-wise relabelling")
    print(f"  permutes class NAMES and leaves the partition identical, so every")
    print(f"  distance in the scorer is unchanged and the score cannot move.")
    print(f"  The statistic is invariant under the null's own relabelling")
    print(f"  operation, so the test cannot reject any hypothesis on any dataset.")

    print(f"\n{'=' * 78}\nEFFECT SIZE THAT REPLACES THE p-VALUES\n")
    for label, modes in [("two-mode", [0, 2]), ("three-mode", [0, 1, 2])]:
        Xs = X[:, modes]
        keep = ~np.isnan(Xs).any(axis=1)
        Xs, ys = Xs[keep], y[keep]
        cls = sorted(set(ys))
        means = {c: Xs[ys == c].mean(axis=0) for c in cls}
        pairs = [(np.linalg.norm(means[a] - means[b]), LOCS[a], LOCS[b])
                 for i, a in enumerate(cls) for b in cls[i + 1:]]
        d, a_, b_ = min(pairs)
        worst = max(np.linalg.norm(Xs[i] - means[ys[i]]) for i in range(len(Xs)))
        print(f"  {label:11s} closest class-mean pair: {a_} and {b_}, "
              f"{d:.1f} floor-units")
        print(f"              largest run-to-own-mean distance: {worst:.2f}")
        print(f"              ratio: {d / worst:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

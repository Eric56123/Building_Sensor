"""
audit_1_2_permutation.py — Part 1, item 1.2: the Table 4.8 p-values

Audit target: b0aba33

CLAIM (Table 4.8 + caption): three localisation scorings, all perfect;
"Significance is by permutation of the location labels, replicates permuted as a
group, 10,000 shuffles"; p = 0.0001 (per-run, 12/12), 0.0001 (two-mode, 11/11),
0.0042 (three-mode, 9/9).

Two questions, in order:
  (a) Does a generator exist in the repository for each of the three rows?
  (b) What is the true permutation unit, hence the exact space size and the
      attainable minimum p?

Where the space is small enough, enumerate it exhaustively instead of sampling.

INDEPENDENCE. inversion_robustness.py was written by the auditor in the same
session, so (a) is self-checking. (b) is not: the size of a permutation space is
a property of the design, not of the implementation.
"""
import itertools
import math
import os
import sys
from collections import Counter

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "four_floor"))

import interpret_capture as ic                                   # noqa: E402

BASE = os.path.join(_ROOT, "four_floor", "characterisation")
LOCS = ["base", "F1", "F2", "F3"]
FLOOR_2SD = 2 * np.array([0.15, 0.23, 0.16])
DOC = {"per-run": (12, 12, 3.03, 0.0001),
       "two-mode": (11, 11, 2.78, 0.0001),
       "three-mode": (9, 9, 2.99, 0.0042)}


def vec(f):
    return ic.modal_vector(os.path.join(BASE, f))


def signatures():
    b4 = vec("day4_baseline")
    names, X, y = [], [], []
    for li, loc in enumerate(LOCS):
        for r in (1, 2, 3):
            f = f"{loc}_severe_r{r}"
            if os.path.isdir(os.path.join(BASE, f)):
                sh = np.abs((vec(f) - b4) / b4 * 100) / FLOOR_2SD
                names.append(f"{loc}_r{r}")
                X.append(sh)
                y.append(li)
    return names, np.array(X), np.array(y)


def loo_fixed(X, y):
    """Leave-one-out nearest-class-mean, fixed feature space."""
    ok = 0
    for i in range(len(X)):
        d = {}
        for c in set(y):
            m = [j for j in range(len(X)) if y[j] == c and j != i]
            if m:
                d[c] = np.linalg.norm(X[i] - X[m].mean(axis=0))
        if d and min(d, key=d.get) == y[i]:
            ok += 1
    return ok


def loo_perrun(X, y):
    """Per-run: RMS over the modes shared by the run and the class reference."""
    ok = 0
    for i in range(len(X)):
        d = {}
        for c in set(y):
            m = [j for j in range(len(X)) if y[j] == c and j != i]
            if not m:
                continue
            ref = np.nanmean(X[m], axis=0)
            sh = ~np.isnan(X[i]) & ~np.isnan(ref)
            d[c] = np.sqrt(np.mean((X[i][sh] - ref[sh]) ** 2)) if sh.any() else np.inf
        if d and min(d, key=d.get) == y[i]:
            ok += 1
    return ok


def multiset_perms(y):
    """Distinct labellings of the label multiset = n! / prod(count!)."""
    c = Counter(y)
    n = math.factorial(len(y))
    for v in c.values():
        n //= math.factorial(v)
    return n


def exact_p(X, y, scorer, obs):
    """Exhaustive enumeration over DISTINCT labellings of the multiset."""
    seen, hits, tot, best = set(), 0, 0, []
    for p in itertools.permutations(y):
        if p in seen:
            continue
        seen.add(p)
        s = scorer(X, np.array(p))
        best.append(s)
        tot += 1
        if s >= obs:
            hits += 1
    return hits, tot, float(np.mean(best))


def main():
    names, X, y = signatures()
    print(f"Audit 1.2 — Table 4.8 permutation p-values\n{'=' * 78}")

    print("\n(a) DOES A GENERATOR EXIST?\n")
    src = os.path.join(_ROOT, "four_floor", "inversion_robustness.py")
    txt = open(src).read()
    has_fixed = "C. PERMUTATION TEST" in txt
    has_perrun = ("loo_perrun" in txt) or ("per-run" in txt)
    print(f"  inversion_robustness.py, fixed-space tests (2-mode, 3-mode): "
          f"{'FOUND' if has_fixed else 'ABSENT'}")
    print(f"  per-run test, anywhere in the repository:                    "
          f"{'FOUND' if has_perrun else 'ABSENT'}")
    print("  the only two files that permute anything are")
    print("    four_floor/inversion_robustness.py   (this test)")
    print("    four_floor/run_experiments.py        (lambda sweep, unrelated)")

    print("\n(b) WHAT IS THE PERMUTATION UNIT?\n")
    print("  Code, analysis_BC:  yp = rng.permutation(y)   with y a PER-RUN label")
    print("  vector. Runs are shuffled freely; the three replicates of a location")
    print("  are NOT held together. The caption's 'replicates permuted as a group'")
    print("  describes a different, more conservative test than the one run.\n")

    spaces = {}
    for label, modes, scorer in [("two-mode", [0, 2], loo_fixed),
                                 ("three-mode", [0, 1, 2], loo_fixed),
                                 ("per-run", [0, 1, 2], loo_perrun)]:
        Xs = X[:, modes]
        if scorer is loo_fixed:
            keep = ~np.isnan(Xs).any(axis=1)
            Xs, ys = Xs[keep], y[keep]
        else:
            ys = y
        n_run = multiset_perms(list(ys))
        n_grp = math.factorial(len(set(ys)))
        obs = scorer(Xs, ys)
        spaces[label] = (Xs, ys, obs, n_run, n_grp)
        d = DOC[label]
        print(f"  {label:11s} n={len(ys):2d}  observed {obs}/{len(ys)} "
              f"(doc {d[1]}/{d[0]})")
        print(f"              run-level space  {n_run:>8,d}   min p = "
              f"1/{n_run} = {1 / n_run:.6f}")
        print(f"              group-wise space {n_grp:>8,d}   min p = "
              f"1/{n_grp} = {1 / n_grp:.4f}   <- what the caption describes")

    print("\n(c) EXACT p BY EXHAUSTIVE ENUMERATION (run-level unit, as coded)\n")
    for label in ("three-mode", "two-mode", "per-run"):
        Xs, ys, obs, n_run, _ = spaces[label]
        scorer = loo_perrun if label == "per-run" else loo_fixed
        if n_run > 200_000:
            print(f"  {label:11s} space {n_run:,d} too large to enumerate here; "
                  f"MC floor 1/(10000+1) = 0.0001 applies")
            continue
        hits, tot, mean = exact_p(Xs, ys, scorer, obs)
        print(f"  {label:11s} enumerated {tot:,d} distinct labellings; "
              f"{hits} reached >= {obs}/{len(ys)}")
        print(f"              exact p = {hits}/{tot} = {hits / tot:.6f}   "
              f"shuffled mean {mean:.2f}   (doc p = {DOC[label][3]}, "
              f"mean {DOC[label][2]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

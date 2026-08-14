"""
decision_rule_sweep.py — objective E: decision rules, seed stability, physics weight
====================================================================================
Retrains RigPINN over a seed sweep and scores the MEASURED rig captures under two
decision rules. Exploratory: this is a fresh model reproducing the Table 3.10
procedure, NOT a re-scoring of the deployed run (no weights are archived).

    python -m four_floor.decision_rule_sweep

WRITES NOTHING. No weights, no sidecar. train_rig_pinn.py's --out renames the
weights AND its provenance sidecar follows, so any retrain at the default path
clobbers shm_pinn_rig3dof_v1.json. The training loop is replicated inline here
instead, so nothing tracked is touched.

DESIGN, fixed before looking at any number:
  * Base plate EXCLUDED from rule scoring. It is a boundary condition with no
    correct answer inside a three-storey label space; scoring it would put
    unanswerable items into the tally. Reported separately.
  * PAIRED comparison. Both rules read the same predicted vectors, so the
    quantity with power is the per-seed difference, not two marginals.
  * Argmin reproducibility across seeds, per case.
  * lam_phys = 0.0 against 1.0 on the rig cases (Tables 3.9/3.11 ablate on
    synthetic held-out data only).

PRE-REGISTERED READINGS
  1. Both rules fail alike  -> the rule was never the problem; the failure is
     representational. Strongest outcome: 5.3.3's hedge can be replaced.
  2. Nearest-signature much better -> argmin was discarding information.
     Exploratory.
  3. Nearest-signature worse -> argmin was adequate; failure entirely
     representational.

DATA CONSTRAINT found before running, which changes the specified design:
  All three Floor 3 SEVERE captures have f2 voided by the 2f1 harmonic, so they
  cannot enter a 3-input network. The nine storey captures are really six, over
  two classes. The graded (Day 6) cells DO resolve Floor 3, so an extended set
  of every complete storey cell is scored alongside, restoring three classes.
"""
import json
import os
import sys
import warnings

import numpy as np
import torch

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

import interpret_capture as ic                              # noqa: E402
from pinn.rig_pinn import RigPINN, pinn_loss                # noqa: E402
from simulation.rig_3dof import (                           # noqa: E402
    generate_dataset, modes_hz, apply_damage, K_HEALTHY)

warnings.filterwarnings("ignore")
BASE = os.path.join(_HERE, "characterisation")
N_SEEDS = 20
EPOCHS = 600
N_TRAIN = 16000
LAMBDAS = (0.0, 1.0)
STOREYS = ["F1", "F2", "F3"]          # the three-storey label space
LOCS = ["base"] + STOREYS


def vec(f):
    return ic.modal_vector(os.path.join(BASE, f))


def rule(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


# --------------------------------------------------------------------------
# Measured inputs. The network's feature is damaged/healthy modal ratio, so the
# measured vectors are divided by their OWN session-matched baseline — the same
# quantity, not the model's healthy modes.
# --------------------------------------------------------------------------
b4, b6 = vec("day4_baseline"), vec("day6_baseline")

SEVERE, GRADED = [], []
for loc in LOCS:
    for r in (1, 2, 3):
        f = f"{loc}_severe_r{r}"
        if os.path.isdir(os.path.join(BASE, f)):
            SEVERE.append((loc, f"{loc}_sev_r{r}", vec(f) / b4))
    for g in ("trace", "light", "moderate"):
        f = f"{loc}_{g}_c1"
        if os.path.isdir(os.path.join(BASE, f)):
            GRADED.append((loc, f"{loc}_{g}", vec(f) / b6))


def usable(items, locs):
    return [(l, n, x) for l, n, x in items if l in locs and not np.isnan(x).any()]


SEV_STOREY = usable(SEVERE, STOREYS)          # 6 items, F1/F2 only
ALL_STOREY = usable(SEVERE + GRADED, STOREYS)  # + graded, restores F3
SEV_BASE = usable(SEVERE, ["base"])


# --------------------------------------------------------------------------
# Train / predict
# --------------------------------------------------------------------------
def train(seed, lam):
    torch.manual_seed(seed)
    d = generate_dataset(n=N_TRAIN, seed=seed)
    X, A = torch.tensor(d["X"]), torch.tensor(d["alpha"])
    ntr = int(0.8 * len(X))
    Xtr, Atr = X[:ntr], A[:ntr]
    m = RigPINN()
    opt = torch.optim.Adam(m.parameters(), lr=2e-3)
    for _ in range(EPOCHS):
        m.train(); opt.zero_grad()
        loss, _, _ = pinn_loss(m(Xtr), Xtr, Atr, lam_phys=lam)
        loss.backward(); opt.step()
    m.eval()
    return m


def predict(m, feats):
    with torch.no_grad():
        return m(torch.tensor(np.asarray(feats), dtype=torch.float32)).numpy()


def references(m, seed):
    """Class references for nearest-signature, from HELD-OUT simulated
    single-storey damage. Built from the model's own predictions, because that
    is the space the measured predictions live in."""
    rng = np.random.RandomState(seed + 90_000)
    feats, lab = [], []
    for s in range(3):
        for _ in range(300):
            a = np.ones(3)
            a[s] = rng.uniform(0.15, 0.98)
            f = modes_hz(apply_damage(a)) / modes_hz(K_HEALTHY)
            feats.append(f * (1 + 0.5 / 100 * rng.randn(3)))
            lab.append(s)
    P = predict(m, feats)
    lab = np.array(lab)
    return np.array([P[lab == s].mean(axis=0) for s in range(3)])


def score(P, truth, refs):
    """(argmin correct, nearest-signature correct) as boolean arrays."""
    am = P.argmin(axis=1)
    ns = np.array([np.argmin([np.linalg.norm(p - r) for r in refs]) for p in P])
    return am == truth, ns == truth


# ==========================================================================
if __name__ == "__main__":
    print(f"Objective E — decision-rule sweep   ({N_SEEDS} seeds x "
          f"{len(LAMBDAS)} lambda, {EPOCHS} epochs, n={N_TRAIN})")
    print(f"  severe storey captures usable: {len(SEV_STOREY)} of 9 "
          f"({sorted({l for l, _, _ in SEV_STOREY})}) — Floor 3 severe has f2 voided")
    print(f"  extended storey set:           {len(ALL_STOREY)} items "
          f"({ {l: sum(1 for a, _, _ in ALL_STOREY if a == l) for l in STOREYS} })")

    SETS = {"severe only (2 classes)": SEV_STOREY,
            "severe + graded (3 classes)": ALL_STOREY}
    res = {k: {lam: {"am": [], "ns": []} for lam in LAMBDAS} for k in SETS}
    argmin_hist = {lam: {n: [] for _, n, _ in SEVERE + GRADED} for lam in LAMBDAS}
    base_pred = {lam: [] for lam in LAMBDAS}

    for lam in LAMBDAS:
        for seed in range(N_SEEDS):
            m = train(seed, lam)
            refs = references(m, seed)
            for key, items in SETS.items():
                truth = np.array([STOREYS.index(l) for l, _, _ in items])
                P = predict(m, [x for _, _, x in items])
                a, n = score(P, truth, refs)
                res[key][lam]["am"].append(a.mean())
                res[key][lam]["ns"].append(n.mean())
            for l, nm, x in SEVERE + GRADED:              # argmin stability
                if not np.isnan(x).any():
                    argmin_hist[lam][nm].append(int(predict(m, [x])[0].argmin()))
            if SEV_BASE:
                base_pred[lam].append(predict(m, [x for _, _, x in SEV_BASE]))
        print(f"  lambda={lam}: {N_SEEDS} seeds trained")

    # ---- paired rule comparison ------------------------------------------
    rule("E1. DECISION RULES, PAIRED PER SEED")
    for key in SETS:
        nc = 2 if "2 classes" in key else 3
        print(f"\n  {key}   n={len(SETS[key])} items, chance {1/nc:.0%}")
        for lam in LAMBDAS:
            am = np.array(res[key][lam]["am"])
            ns = np.array(res[key][lam]["ns"])
            d = ns - am
            wins = int((d > 0).sum()); ties = int((d == 0).sum())
            # two-sided sign test on the non-tied pairs
            nt = N_SEEDS - ties
            from scipy.stats import binomtest
            p = binomtest(wins, nt, 0.5).pvalue if nt else 1.0
            print(f"    lambda={lam}: argmin {am.mean():.3f}+-{am.std():.3f}   "
                  f"nearest-sig {ns.mean():.3f}+-{ns.std():.3f}")
            print(f"              paired diff {d.mean():+.3f} "
                  f"[{np.percentile(d,2.5):+.3f}, {np.percentile(d,97.5):+.3f}]   "
                  f"NS wins {wins}, ties {ties}, losses {nt-wins}   sign p={p:.4f}")

    # ---- lambda ablation on the rig --------------------------------------
    rule("E2. PHYSICS WEIGHT ON THE MEASURED CASES (lambda 0 vs 1)")
    from scipy.stats import mannwhitneyu
    for key in SETS:
        for r_ in ("am", "ns"):
            a = np.array(res[key][0.0][r_]); b = np.array(res[key][1.0][r_])
            u = mannwhitneyu(a, b).pvalue
            nm = "argmin     " if r_ == "am" else "nearest-sig"
            print(f"  {key:30s} {nm}  lam0 {a.mean():.3f}  lam1 {b.mean():.3f}"
                  f"   diff {b.mean()-a.mean():+.3f}   p={u:.4f}")

    # ---- argmin reproducibility ------------------------------------------
    rule("E3. ARGMIN REPRODUCIBILITY ACROSS SEEDS")
    print("  How often the argmin lands on each storey, per measured case.")
    for lam in LAMBDAS:
        print(f"\n  lambda={lam}")
        print(f"    {'case':16s} {'k1':>6s} {'k2':>6s} {'k3':>6s}   modal argmin")
        for l, nm, x in SEVERE + GRADED:
            h = argmin_hist[lam][nm]
            if not h:
                continue
            c = np.bincount(h, minlength=3) / len(h)
            star = "  <-- always k1" if c[0] == 1.0 else ""
            print(f"    {nm:16s} {c[0]:6.2f} {c[1]:6.2f} {c[2]:6.2f}   "
                  f"k{int(np.argmax(c))+1}{star}")

    # ---- machine-readable dump for the figure scripts --------------------
    calls = {}
    for _, nm, x in SEVERE + GRADED:
        h = argmin_hist[0.0][nm] + argmin_hist[1.0][nm]
        if not h:
            continue
        c = np.bincount(h, minlength=3)
        calls[nm] = dict(n_runs=len(h), frac=(c / len(h)).round(4).tolist(),
                         call=int(c.argmax()), unanimous=bool(c.max() == len(h)))
    out_json = os.path.join(_HERE, "results_decision_rule_sweep.json")
    with open(out_json, "w") as f:
        json.dump(dict(n_seeds=N_SEEDS, lambdas=list(LAMBDAS), epochs=EPOCHS,
                       cells=calls,
                       archived_f3=dict(alpha=[0.72, 0.94, 0.98], argmin=0,
                                        note="imputed input: two unmeasurable "
                                             "modes set to 1.0")), f, indent=1)
    print(f"\n  wrote {os.path.basename(out_json)}  ({len(calls)} cells)")

    rule("E4. BASE PLATE, REPORTED SEPARATELY")
    for lam in LAMBDAS:
        P = np.concatenate(base_pred[lam], axis=0)
        print(f"  lambda={lam}: mean predicted alpha over {len(P)} "
              f"(3 captures x {N_SEEDS} seeds) = {np.round(P.mean(axis=0), 3)}"
              f"   argmin k{int(np.bincount(P.argmin(axis=1), minlength=3).argmax())+1}"
              f" in {np.bincount(P.argmin(axis=1), minlength=3).max()}/{len(P)}")
    print("\n  The base plate is a boundary condition. Analysis A showed it has NO"
          "\n  admissible exact solution in the storey parametrisation, so no label"
          "\n  in a three-storey space is correct for it. Excluded from E1-E3.")

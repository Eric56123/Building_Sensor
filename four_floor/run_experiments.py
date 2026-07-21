"""
run_experiments.py
==================
Run from the repository root, with the venv active:

    # the sampled-alpha dataset (default) -- 20% of alphas held out
    python -m four_floor.run_experiments --dataset continuous --mode holdout

    # 5-fold group CV over alphas
    python -m four_floor.run_experiments --dataset continuous --mode kfold --k 5

    # the old 7-pattern benchmark, for the comparison figure
    python -m four_floor.run_experiments --dataset benchmark --mode locv

Outputs to ./experiments/:
    loss_log_lam{L}_{fold}_{dataset}.csv   per-epoch L_data, L_phys (UNWEIGHTED),
                                           lam*L_phys, total, lr
    results_summary_{dataset}.csv          held-out metrics for every (lambda, fold)

WHY THERE ARE TWO DATASETS
--------------------------
`--dataset benchmark` is the original 7 Johnson damage patterns. It has two fatal
properties, both established by `four_floor/diagnose_physics_loss.py`:

  (a) It contains only 6 unique alpha vectors (k_v and k_vi are bit-identical in
      matrices.py), i.e. ~5 per training fold. That is not a training set for a
      4-D continuous inverse map.
  (b) Its damage patterns are NOT in the span of K(alpha) = sum_i alpha_i K_i.
      The Frobenius-derived alpha reconstructs K to only 0.7-5.1% error, so the
      residual (K(alpha) - w^2 M) is never singular at the truth:
      L_phys(alpha_true) ~ 1e-3, and on the mild-damage cases the physics loss
      scores the INTACT structure BETTER than the true alpha. The physics term
      cannot reward a correct answer, which is why the lambda sweep on this data
      was inert.

`--dataset continuous` samples alpha and BUILDS K(alpha) by the same
superposition the physics loss assumes, so alpha_true is exact,
L_phys(alpha_true) ~ 1e-8 (verified), and the physics term finally has a global
minimum at the answer. The benchmark set is retained as an out-of-distribution
test and as the "before" half of the comparison.

WHAT DIFFERS FROM four_floor/train.py -- and why
------------------------------------------------
1. PATTERN-LEVEL SPLIT.
   train.py shuffles `items` at SCENARIO level and then cuts at 80%, so the split
   is already roughly scenario-wise. But each damage pattern appears TWICE (once
   consistent-mass, once lumped-mass), and the shuffle can place one variant in
   train and the other in test: same alpha vector, near-identical spectrum =>
   leakage. Here the split is by DAMAGE PATTERN (`damage_idx`), holding out both
   mass variants of a pattern together, so held-out alphas are genuinely unseen.
   The mid-scenario boundary cut in train.py (112/140 lands inside a scenario,
   splitting it ~2/8 across train and test) also disappears, because we split on
   group membership rather than index position.

2. UNWEIGHTED PHYSICS LOGGING.
   `physics_informed_loss` applies lambda INTERNALLY (lambda_weight=LAMBDA_PHYS),
   so the "Phys Loss" printed by train.py is already lam*L_phys, not L_phys.
   Recovering L_phys by dividing by lam breaks at lam=0. Here we always call with
   lambda_weight=1.0 and apply lam ourselves, so L_phys is logged unweighted at
   every lambda -- including lam=0, where we can watch what the physics residual
   does when it is NOT being enforced. That contrast is itself a figure.

3. LAMBDA SWEEP + SEEDED INIT.
   train.py never calls torch.manual_seed. Fine for a single run, fatal for an
   ablation: different lambdas would get different weight initialisations and you
   could not separate the effect of physics from the effect of luck. Seeded here
   so that lambda is the only thing that varies.

4. SCALER REFIT PER FOLD.
   PSDScaler is fit on training data only (as train.py correctly does). The fold
   changes which samples are training data, so it is refit per fold.
"""

import argparse
import csv
import os
import time

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from scipy.signal import welch

from four_floor.simulation.matrices import k_set, m_set, m_lump
from four_floor.preprocessing.cleaning import sanitize_accelerometer_data
from four_floor.preprocessing.normalisation import PSDScaler
from four_floor.pinn.pinn_model import SHM_PINN, physics_informed_loss_batched
from four_floor.pinn.pinn_utils import decompose_stiffness_matrix, prepare_physics_tensors
from four_floor.simulation.generate_dataset import load_dataset

# ---------------------------------------------------------
# HYPERPARAMETERS (mirrors train.py)
# ---------------------------------------------------------
FS = 1000.0
NPERSEG = 2048
CHUNK_SIZE = 4000
EPOCHS = 500          # overridden by --epochs; 500 is train.py's fixed budget
BATCH_SIZE = 16
LEARNING_RATE = 5e-4
CLIP_NORM = 1.0
Y_DOFS = [1, 4, 7, 10]

LAMBDAS = [0.0, 0.01, 0.1, 1.0]
OUTDIR = "experiments"
SEED = 0

DEVICE = torch.device("mps" if torch.backends.mps.is_available() else "cpu")


# ---------------------------------------------------------
# PHASE 1b: the CONTINUOUS-ALPHA dataset
# ---------------------------------------------------------
def load_continuous(path=os.path.join("data", "continuous")):
    """
    The dataset produced by `four_floor.simulation.generate_dataset`.

    Crucially, alpha here is SAMPLED and K(alpha) = sum_i alpha_i K_i is BUILT
    from it -- the exact superposition the physics loss assumes. So L_phys is
    ~1e-8 at the true alpha (verified) instead of ~1e-3 as on the benchmark
    patterns, where the Frobenius-derived alpha reconstructs K only to 0.7-5.1%
    and the physics term therefore cannot reward a correct answer.

    The grouping key is `alpha_id`, so both mass variants of an alpha are held
    out together and every test alpha is genuinely unseen.
    """
    d = load_dataset(path)
    psd, alpha, omega = d["psd"], d["alpha"], d["omega"]
    mass, group = d["mass_flag"], d["alpha_id"]

    print(f"[data] {len(psd)} windows | {len(np.unique(group))} alpha groups | "
          f"{len(np.unique(alpha, axis=0))} unique alpha vectors")
    print(f"[data] mass split: {np.sum(mass == 0)} consistent, {np.sum(mass == 1)} lumped")
    print(f"[data] intact windows: {int((alpha == 1).all(1).sum())} "
          f"({100 * (alpha == 1).all(1).mean():.0f}%)")

    return psd, alpha, omega, mass, group


# ---------------------------------------------------------
# PHASE 1: extraction -- identical to train.py, plus pattern_id
# ---------------------------------------------------------
def load_windows():
    if not os.path.exists("shm_benchmark_data.npy"):
        raise FileNotFoundError("Run simulation script first!")

    all_results = np.load("shm_benchmark_data.npy", allow_pickle=True).item()

    K_baseline_global = k_set[0] * 1e6
    baseline_story_matrices = decompose_stiffness_matrix(K_baseline_global)

    accel_l, alpha_l, omega_l, mass_l, patt_l = [], [], [], [], []

    items = list(all_results.items())
    np.random.seed(42)
    np.random.shuffle(items)          # kept for parity; irrelevant under a grouped split

    for key, data in items:
        m_type = 1 if "Lumped" in key or "Case4" in key else 0
        damage_idx = int(key.split("_")[-1])        # <-- this IS the pattern id

        K_current_global = k_set[damage_idx] * 1e6
        current_story_matrices = decompose_stiffness_matrix(K_current_global)

        alphas = []
        for i in range(4):
            k_curr_norm = np.linalg.norm(current_story_matrices[i])
            k_base_norm = np.linalg.norm(baseline_story_matrices[i])
            ratio = k_curr_norm / k_base_norm if k_base_norm > 1e-3 else 1.0
            alphas.append(np.clip(ratio, 0.01, 1.0))

        accel_4dof_y = data['accel'][Y_DOFS, :]
        w_peaks = 2 * np.pi * np.array(data['freqs'][:2])

        n_steps = accel_4dof_y.shape[1]
        for start in range(0, n_steps, CHUNK_SIZE):
            end = start + CHUNK_SIZE
            if end <= n_steps:
                accel_l.append(accel_4dof_y[:, start:end])
                alpha_l.append(alphas)
                omega_l.append(w_peaks)
                mass_l.append(m_type)
                patt_l.append(damage_idx)

    raw   = np.array(accel_l)
    alpha = np.array(alpha_l)
    omega = np.array(omega_l)
    mass  = np.array(mass_l)
    patt  = np.array(patt_l)

    # Poison purge -- purge pattern ids in lockstep
    valid = ~np.isnan(alpha).any(axis=1) & \
            ~np.isnan(raw.reshape(len(raw), -1)).any(axis=1)
    raw, alpha, omega, mass, patt = (
        raw[valid], alpha[valid], omega[valid], mass[valid], patt[valid]
    )

    print(f"[data] {len(raw)} windows after purge")
    print(f"[data] patterns present: {sorted(set(patt.tolist()))}")
    print(f"[data] unique alpha vectors: {len(np.unique(alpha, axis=0))}")
    print(f"[data] mass split: {np.sum(mass == 0)} consistent, {np.sum(mass == 1)} lumped")

    # Welch is a per-sample transform, so computing it once introduces no leakage.
    # The *scaling* is what must be fit on training data only -- done per fold below.
    clean = sanitize_accelerometer_data(raw, fs=FS)
    _, psd = welch(clean, fs=FS, nperseg=NPERSEG, axis=-1)

    return psd, alpha, omega, mass, patt


def make_loaders(psd, alpha, omega, mass, tr, te):
    """Refit the PSD scaler on THIS fold's training data only."""
    scaler = PSDScaler()
    Xtr = scaler.fit_transform(psd[tr])
    Xte = scaler.transform(psd[te])

    def ds(X, idx):
        return TensorDataset(
            torch.tensor(X, dtype=torch.float32),
            torch.tensor(alpha[idx], dtype=torch.float32),
            torch.tensor(omega[idx], dtype=torch.float32),
            torch.tensor(mass[idx], dtype=torch.long),
        )

    return (
        DataLoader(ds(Xtr, tr), batch_size=BATCH_SIZE, shuffle=True),
        DataLoader(ds(Xte, te), batch_size=BATCH_SIZE, shuffle=False),
        Xtr.shape[-1],
    )


# ---------------------------------------------------------
# Train one model at one lambda
# ---------------------------------------------------------
def train_one(lam, train_loader, test_loader, n_bins, K_story, M_cons, M_lump, tag,
              epochs=EPOCHS):
    torch.manual_seed(SEED)

    model = SHM_PINN(n_frequency_bins=n_bins).to(DEVICE)
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)
    mse = nn.MSELoss()

    rows = []
    t0 = time.time()

    for epoch in range(epochs):
        model.train()
        rd, rp, nb = 0.0, 0.0, 0

        for x, y, w, m in train_loader:
            x, y, w, m = x.to(DEVICE), y.to(DEVICE), w.to(DEVICE), m.to(DEVICE)

            optimizer.zero_grad()
            preds = model(x)

            d_loss = mse(preds, y)

            # lambda_weight=1.0 => p_loss is the UNWEIGHTED L_phys.
            # We apply lam ourselves so it stays loggable even at lam == 0.
            # Batched form: identical maths, one SVD kernel launch per batch
            # instead of 2*B round-trips to the CPU (see pinn_model.py).
            p_loss = physics_informed_loss_batched(
                preds, w, M_cons, M_lump, m, K_story, lambda_weight=1.0
            )

            total = d_loss + lam * p_loss
            total.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=CLIP_NORM)
            optimizer.step()

            rd += d_loss.item()
            rp += p_loss.item()
            nb += 1

        avg_d, avg_p = rd / nb, rp / nb
        lr = scheduler.get_last_lr()[0]
        scheduler.step()

        rows.append({
            "epoch": epoch + 1,
            "data_loss": avg_d,
            "phys_loss_unweighted": avg_p,
            "phys_loss_weighted": lam * avg_p,
            "total_loss": avg_d + lam * avg_p,
            "lr": lr,
        })

        if epoch == 0 or (epoch + 1) % 100 == 0:
            print(f"    ep {epoch + 1:3d} | L_data {avg_d:.6f} | "
                  f"L_phys {avg_p:.6f} | lam*L_phys {lam * avg_p:.6f}")

    wall = time.time() - t0

    with open(os.path.join(OUTDIR, f"loss_log_{tag}.csv"), "w", newline="") as fh:
        wtr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wtr.writeheader()
        wtr.writerows(rows)

    # ---- held-out evaluation ----
    model.eval()
    P, T = [], []
    with torch.no_grad():
        for x, y, w, m in test_loader:
            P.append(model(x.to(DEVICE)).cpu().numpy())
            T.append(y.numpy())
    P, T = np.concatenate(P), np.concatenate(T)

    mae = float(np.abs(P - T).mean())
    per_storey = np.abs(P - T).mean(axis=0)

    # ---- BASELINES ------------------------------------------------------
    # The old experiment reported MAE 0.014 and called it good. It was not:
    # most alphas sat near 1.0, so "predict roughly intact everywhere" scores
    # well on MAE and is useless for SHM. Any headline MAE is meaningless
    # unless it beats these two, so they are computed every time.
    #   - trivial_mae: always predict alpha = 1 (intact)
    #   - mean_mae:    always predict the TRAINING mean alpha (per storey)
    y_train = np.concatenate([y.numpy() for _, y, _, _ in train_loader])
    trivial_mae = float(np.abs(np.ones_like(T) - T).mean())
    mean_mae = float(np.abs(y_train.mean(axis=0)[None, :] - T).mean())

    # Localisation: does the lowest predicted alpha land on the truly weakest
    # storey? Evaluated on damaged samples only. Chance = 0.25 for 4 storeys.
    dmg = T.min(axis=1) < 0.99
    loc = (float((P[dmg].argmin(axis=1) == T[dmg].argmin(axis=1)).mean())
           if dmg.any() else float("nan"))

    # Detection: can it tell damaged from intact at all? (alpha_min < 0.9)
    pred_dmg = P.min(axis=1) < 0.9
    true_dmg = T.min(axis=1) < 0.9
    detect = float((pred_dmg == true_dmg).mean())

    # Is the model actually using its input, or emitting a constant?
    pred_spread = float(P.std(axis=0).mean())

    return {
        "lambda": lam,
        "mae": mae,
        "trivial_mae_alpha1": round(trivial_mae, 4),
        "mean_predictor_mae": round(mean_mae, 4),
        "per_storey_mae": np.round(per_storey, 4).tolist(),
        "localisation_acc": loc,
        "detection_acc": round(detect, 4),
        "pred_std": round(pred_spread, 4),
        "final_L_data": rows[-1]["data_loss"],
        "final_L_phys_unweighted": rows[-1]["phys_loss_unweighted"],
        "final_lam_L_phys": rows[-1]["phys_loss_weighted"],
        "n_train": len(train_loader.dataset),
        "n_test": len(test_loader.dataset),
        "wall_clock_s": round(wall, 1),
        "device": str(DEVICE),
    }


# ---------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=["benchmark", "continuous"], default="continuous",
                    help="'benchmark' = the 7 Johnson patterns (6 unique alphas); "
                         "'continuous' = the sampled-alpha dataset")
    ap.add_argument("--mode", choices=["holdout", "locv", "kfold"], default="holdout")
    ap.add_argument("--holdout", type=int, nargs="+", default=[3, 6],
                    help="damage-pattern ids to hold out (benchmark + --mode holdout)")
    ap.add_argument("--k", type=int, default=5, help="folds for --mode kfold")
    ap.add_argument("--epochs", type=int, default=None)
    ap.add_argument("--lambdas", type=float, nargs="+", default=LAMBDAS)
    args = ap.parse_args()

    os.makedirs(OUTDIR, exist_ok=True)

    if args.dataset == "benchmark":
        psd, alpha, omega, mass, group = load_windows()
        epochs = args.epochs or 500
    else:
        psd, alpha, omega, mass, group = load_continuous()
        epochs = args.epochs or 200      # 10k windows: 200 epochs is already 10x
                                         # the gradient steps of the old 500-epoch run

    groups = sorted(set(group.tolist()))
    K_story, M_cons, M_lump = prepare_physics_tensors(k_set, m_set, m_lump, DEVICE)

    # ---- fold construction: ALWAYS group-wise, so no alpha is in train and test
    rng = np.random.default_rng(SEED)
    if args.mode == "holdout":
        if args.dataset == "benchmark":
            folds = [("h", args.holdout)]
        else:
            shuf = rng.permutation(groups)
            n_te = max(1, int(0.2 * len(groups)))
            folds = [("h", shuf[:n_te].tolist())]      # 20% of alphas held out
    elif args.mode == "locv":
        folds = [(f"p{g}", [g]) for g in groups]
    else:  # kfold, group-wise
        shuf = rng.permutation(groups)
        folds = [(f"k{i}", chunk.tolist())
                 for i, chunk in enumerate(np.array_split(shuf, args.k))]

    results = []
    for fold_name, hold in folds:
        te = np.flatnonzero(np.isin(group, hold))
        tr = np.flatnonzero(~np.isin(group, hold))
        print(f"\n=== fold {fold_name}: {len(hold)} held-out alpha group(s) | "
              f"{len(tr)} train / {len(te)} test windows ===")

        train_loader, test_loader, n_bins = make_loaders(psd, alpha, omega, mass, tr, te)

        for lam in args.lambdas:
            tag = f"lam{lam}_{fold_name}_{args.dataset}"
            print(f"\n  -- lambda = {lam}")
            r = train_one(lam, train_loader, test_loader, n_bins,
                          K_story, M_cons, M_lump, tag, epochs=epochs)
            r["fold"] = fold_name
            r["holdout"] = str(hold) if len(hold) <= 8 else f"{len(hold)} groups"
            r["dataset"] = args.dataset
            results.append(r)
            print(f"     held-out MAE {r['mae']:.4f} "
                  f"(trivial alpha=1: {r['trivial_mae_alpha1']:.4f}, "
                  f"mean-predictor: {r['mean_predictor_mae']:.4f}) | "
                  f"localisation {r['localisation_acc']:.2f} | "
                  f"detection {r['detection_acc']:.2f} | "
                  f"pred_std {r['pred_std']:.3f} | {r['wall_clock_s']}s")

    keys = ["dataset", "lambda", "fold", "holdout", "mae", "trivial_mae_alpha1",
            "mean_predictor_mae", "per_storey_mae", "localisation_acc", "detection_acc",
            "pred_std", "final_L_data", "final_L_phys_unweighted", "final_lam_L_phys",
            "n_train", "n_test", "wall_clock_s", "device"]
    out_csv = os.path.join(OUTDIR, f"results_summary_{args.dataset}.csv")
    with open(out_csv, "w", newline="") as fh:
        wtr = csv.DictWriter(fh, fieldnames=keys)
        wtr.writeheader()
        for r in results:
            wtr.writerow({k: r[k] for k in keys})

    print(f"\n=== held-out metrics by lambda ({args.dataset}, group-wise split) ===")
    print(f"  {'lambda':<8} {'MAE':>16} {'localisation':>16} {'L_phys':>12}")
    for lam in args.lambdas:
        sub = [r for r in results if r["lambda"] == lam]
        if not sub:
            continue
        m = [r["mae"] for r in sub]
        l = [r["localisation_acc"] for r in sub]
        p = [r["final_L_phys_unweighted"] for r in sub]
        print(f"  {lam:<8} {np.mean(m):.4f} +/- {np.std(m):.4f}   "
              f"{np.mean(l):.3f} +/- {np.std(l):.3f}   {np.mean(p):.2e}")
    if results:
        print(f"  {'--':<8} trivial (alpha=1) MAE {results[0]['trivial_mae_alpha1']:.4f}; "
              f"chance localisation 0.25")

    print(f"\n[out] {out_csv}")
    print("\nlambda=0 is the ablation. Beating the trivial and mean-predictor MAEs is "
          "the minimum bar; localisation must beat 0.25 to mean anything for SHM.")


if __name__ == "__main__":
    main()
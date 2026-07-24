"""
train_rig_pinn.py — Day 5 Step 3: train the retargeted 3-DOF PINN
=================================================================
Trains RigPINN (modal vector -> storey stiffness fractions) on the retargeted
simulation (simulation/rig_3dof). Saves to a NEW versioned file with a sidecar;
NEVER touches shm_pinn_weights.pth.

The model is tiny (3->64->64->3) over 3-number modal vectors, so this trains on
CPU in seconds — the old CNN-over-spectra needed a GPU and the 150 MB shard.
"""
import argparse
import json
import subprocess
import sys

import numpy as np
import torch

from pinn.rig_pinn import RigPINN, pinn_loss, interpret
from simulation.rig_3dof import generate_dataset, F_MEASURED, K_HEALTHY


def _git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       text=True).strip()
    except Exception:
        return "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--epochs", type=int, default=300)
    ap.add_argument("--lam-phys", type=float, default=1.0)
    ap.add_argument("--out", default="shm_pinn_rig3dof_v1.pth")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    d = generate_dataset(n=args.n, seed=args.seed)
    X = torch.tensor(d["X"]); AL = torch.tensor(d["alpha"])
    ntr = int(0.8 * len(X))
    Xtr, Xva = X[:ntr], X[ntr:]
    Atr, Ava = AL[:ntr], AL[ntr:]

    model = RigPINN()
    opt = torch.optim.Adam(model.parameters(), lr=2e-3)
    print(f"training on {ntr} sim samples, {args.epochs} epochs, lam_phys={args.lam_phys}")
    for ep in range(args.epochs):
        model.train(); opt.zero_grad()
        pred = model(Xtr)
        loss, dloss, ploss = pinn_loss(pred, Xtr, Atr, lam_phys=args.lam_phys)
        loss.backward(); opt.step()
        if (ep + 1) % 50 == 0 or ep == 0:
            model.eval()
            with torch.no_grad():
                vp = model(Xva)
                vloss, vd, vph = pinn_loss(vp, Xva, Ava, lam_phys=args.lam_phys)
            print(f"  ep {ep+1:4d}  train {loss:.4f} (data {dloss:.4f} phys {ploss:.4f})"
                  f"  val {vloss:.4f}")

    # Held-out SIMULATED performance
    model.eval()
    with torch.no_grad():
        ap_va = model(Xva).numpy()
    # Calibrate the detection threshold from the model's OWN severity output on
    # UNDAMAGED held-out samples (99th percentile), rather than a fixed 0.05. This
    # sets the false-positive rate by construction — the principled analogue of
    # the classical reassembly floor.
    gt0 = interpret(Ava.numpy())
    sev_all = 1 - ap_va.min(axis=1)
    undmg = gt0["damaged"] == 0
    thr = float(np.percentile(sev_all[undmg], 99)) if undmg.any() else 0.05
    print(f"\n  calibrated detection threshold = {thr:.3f} "
          f"(99th pct of healthy severity)")
    gt = interpret(Ava.numpy(), thr=thr)
    pr = interpret(ap_va, thr=thr)
    det_acc = (pr["damaged"] == gt["damaged"]).mean()
    dmask = gt["damaged"] == 1
    loc_acc = (pr["location"][dmask] == gt["location"][dmask]).mean()
    sev_mae = np.abs(pr["severity"][dmask] - gt["severity"][dmask]).mean()
    print("\n  HELD-OUT SIMULATED:")
    print(f"    detection accuracy   {det_acc*100:.1f}%")
    print(f"    localisation accuracy {loc_acc*100:.1f}%  (of truly-damaged)")
    print(f"    severity MAE          {sev_mae:.3f} (stiffness-loss fraction)")

    torch.save(model.state_dict(), args.out)
    sidecar = {
        "produced_by": "train_rig_pinn.py",
        "git_commit": _git_commit(),
        "architecture": "RigPINN 3->64->64->3 sigmoid",
        "input": "modal vector [f1/f1_0, f2/f2_0, f3/f3_0]",
        "output": "storey stiffness fractions [a1,a2,a3]",
        "f_healthy_hz": list(map(float, F_MEASURED)),
        "k_healthy_ratio": [1.0, float(K_HEALTHY[1]/K_HEALTHY[0]),
                            float(K_HEALTHY[2]/K_HEALTHY[0])],
        "n_train": ntr, "epochs": args.epochs, "lam_phys": args.lam_phys,
        "heldout_sim": {"detection_acc": float(det_acc),
                        "localisation_acc": float(loc_acc),
                        "severity_mae": float(sev_mae),
                        "det_threshold": thr},
        "note": "NOT the Johnson benchmark. Retargeted to the measured 3-DOF rig.",
    }
    with open(args.out.replace(".pth", ".json"), "w") as f:
        json.dump(sidecar, f, indent=2)
    print(f"\n  saved {args.out} (+ sidecar). git {sidecar['git_commit']}")


if __name__ == "__main__":
    main()

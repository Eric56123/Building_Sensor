"""
rig_pinn.py — Single-sensor 3-DOF PINN (modal vector -> storey stiffnesses)
===========================================================================
Day 5 Step 1. Replaces SHM_PINN (pinn/pinn_model.py), which mapped a 4-channel
spectrum broadcast from one sensor to 4 per-floor alphas — not identifiable from
one sensor. This model does the identifiable problem the Day 4 data proved
tractable: the modal vector -> the 3 storey-stiffness fractions.

INPUT   x = [f1/f1_0, f2/f2_0, f3/f3_0]   (modes as fractions of healthy)
OUTPUT  alpha = [a1,a2,a3] in (0,1]        (per-storey stiffness fraction; 1=healthy)
DERIVED damage present = min(alpha) < thr ; location = argmin(alpha) ;
        severity = 1 - min(alpha)

WHY THIS IS A PINN, AND WELL-POSED
----------------------------------
3 observed modes -> 3 unknown stiffnesses is a formally determined inverse. The
PHYSICS LOSS enforces the eigenvalue equation of the retargeted 3-DOF model
(simulation/rig_3dof): the modes of K_healthy*alpha_pred must reproduce the input
modal vector. This is the same det(K-w^2 M)=0 idea as the old model but on the
CORRECT structure, and differentiable through torch.linalg.eigh (3x3, CPU).

The data loss (supervised on the retargeted simulation) and the physics loss use
the SAME modal representation, so there is no train/inference mismatch — the bug
that sank the original deployment.
"""
import numpy as np
import torch
import torch.nn as nn

from simulation.rig_3dof import K_HEALTHY, M_STOREY, modes_hz


# Torch constants (healthy stiffness template, masses, healthy modes) as buffers
# so a single differentiable eigen-solve maps alpha -> modes.
_KH = torch.tensor(K_HEALTHY, dtype=torch.float32)
_M = torch.tensor(np.diag(M_STOREY), dtype=torch.float32)
_F0 = torch.tensor(modes_hz(K_HEALTHY), dtype=torch.float32)


def _stiffness_batch(alpha):
    """K(alpha) for a batch: (B,3) fractions -> (B,3,3) shear-stiffness matrices."""
    k = alpha * torch.tensor(K_HEALTHY, dtype=alpha.dtype, device=alpha.device)
    k1, k2, k3 = k[:, 0], k[:, 1], k[:, 2]
    z = torch.zeros_like(k1)
    row0 = torch.stack([k1 + k2, -k2, z], dim=1)
    row1 = torch.stack([-k2, k2 + k3, -k3], dim=1)
    row2 = torch.stack([z, -k3, k3], dim=1)
    return torch.stack([row0, row1, row2], dim=1)


def modes_from_alpha(alpha):
    """
    Differentiable modes-as-fractions for a batch of stiffness fractions.
    Returns (B,3) = sqrt(eig(K(alpha), M)) / (2 pi) / f0, ascending.
    """
    K = _stiffness_batch(alpha)
    M = _M.to(alpha.device).unsqueeze(0).expand(K.shape[0], -1, -1)
    # generalised eig via Cholesky of M (M=I here, but keep it general/stable)
    L = torch.linalg.cholesky(M)
    Linv = torch.linalg.inv(L)
    A = Linv @ K @ Linv.transpose(-1, -2)
    w2 = torch.linalg.eigvalsh(A)                       # ascending, real (symmetric)
    f = torch.sqrt(torch.clamp(w2, min=1e-9)) / (2 * np.pi)
    return f / _F0.to(alpha.device)


class RigPINN(nn.Module):
    """Modal vector -> storey stiffness fractions. Small MLP; the physics is in
    the loss, not the architecture."""

    def __init__(self, hidden=64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(3, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, 3),
        )
        self.apply(self._init)

    @staticmethod
    def _init(m):
        if isinstance(m, nn.Linear):
            nn.init.xavier_uniform_(m.weight)
            nn.init.zeros_(m.bias)

    def forward(self, x):
        # alpha in (0,1]: sigmoid keeps stiffness fractions physical.
        return torch.sigmoid(self.net(x))


def pinn_loss(alpha_pred, x_input, alpha_true=None, lam_phys=1.0):
    """
    data + physics loss.
      data:    MSE(alpha_pred, alpha_true)  (supervised on the simulation)
      physics: MSE(modes_from_alpha(alpha_pred), x_input) — the predicted
               stiffnesses must reproduce the OBSERVED modes (eigenvalue residual).
    The physics term needs no labels, so it also regularises on real captures.
    Returns (total, data_term, phys_term).
    """
    phys = ((modes_from_alpha(alpha_pred) - x_input) ** 2).mean()
    data = (((alpha_pred - alpha_true) ** 2).mean()
            if alpha_true is not None else torch.tensor(0.0))
    return data + lam_phys * phys, data, phys


def interpret(alpha, thr=0.05):
    """alpha (B,3) -> dict of {damaged, location, severity} for reporting."""
    a = np.asarray(alpha)
    loss = 1 - a
    sev = loss.max(axis=1)
    return {
        "damaged": (sev > thr).astype(int),
        "location": np.where(sev > thr, loss.argmax(axis=1), -1),
        "severity": sev,
    }

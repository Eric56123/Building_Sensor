"""
rig_3dof.py — Retargeted 3-DOF shear model of the MEASURED rig
==============================================================
Day 5 Step 2. Replaces the Johnson 4-storey / 12-DOF ASCE benchmark
(simulation/matrices.py, f1=9.42 Hz, 3.4 t/floor, 1% damping) with a 3-DOF
shear model whose UNDAMAGED modes reproduce the measured rig.

Structure (see characterisation/DAMAGE_LOCATION_MAP.md):
    base plate (ground)  --k1--  Floor 1  --k2--  Floor 2  --k3--  Floor 3 (sensor)
Three storeys, three storey stiffnesses k1,k2,k3, one sensor on the top floor.

WHY THIS IS WELL-POSED (and the old model was not)
--------------------------------------------------
One sensor observes the MODAL VECTOR [f1,f2,f3], not per-floor spectra. A 3-DOF
structure has exactly 3 storey stiffnesses. So mapping 3 measured modes -> 3
stiffnesses is a formally determined inverse problem. The old model tried to
predict 4 per-floor alphas from a 1-sensor spectrum broadcast to 4 channels,
which is not identifiable. This module + rig_pinn.py do the identifiable version.

INVERSE SOLUTION (foundation)
-----------------------------
Given measured f1=2.94, f2=8.04, f3=12.15 Hz and EQUAL storey masses (assumed;
absolute mass is unmeasured, so only k RATIOS are physical), solving the 3x3
eigenproblem for k1,k2,k3 is exact (residual ~1e-15 Hz):
    k1 : k2 : k3  =  1 : 1.192 : 0.983      (close to uniform)
Mode shapes are textbook shear-building (0,1,2 sign changes).

VALIDATED against Day 4: reducing k1/k2/k3 reproduces the measured
location-specific signatures — f1 shift ranks bottom>middle>top, and top-storey
damage shifts f2 most (model -38%, rig measured -37%).

ASSUMPTIONS (flagged; not verified from measurement)
- Equal storey masses (uniform frame). Absolute mass unmeasured.
- Ideal shear behaviour (no rotation/torsion; the rig is 3-DOF per Day 1).
- Damage = fractional storey-stiffness reduction (screws loosen -> softer storey).
- Base-plate damage is a boundary condition; here approximated as a k1 reduction
  (k1 is the ground->Floor1 stiffness). Flagged as approximate in validation.
"""
import numpy as np
from scipy.linalg import eigh

# Measured undamaged modes (Hz) the model is fitted to.
F_MEASURED = np.array([2.94, 8.04, 12.15])

# Equal storey masses (assumption). Absolute value is arbitrary — set to 1; it
# cancels from the mode frequencies once k is scaled to match F_MEASURED.
M_STOREY = np.ones(3)

# Measured damping ratios (ringdown, Days 1-4). Mode 1 ~5-7%, mode 2 ~0.7%.
# NOT the benchmark's 1%.
ZETA = np.array([0.06, 0.007, 0.003])


def _stiffness_matrix(k):
    """3-DOF shear-building stiffness matrix from storey stiffnesses k=[k1,k2,k3]."""
    k1, k2, k3 = k
    return np.array([[k1 + k2, -k2,      0.0],
                     [-k2,      k2 + k3, -k3],
                     [0.0,     -k3,       k3]])


def modes_hz(k, m=M_STOREY):
    """Natural frequencies (Hz), ascending, for storey stiffnesses k."""
    w2 = np.sort(eigh(_stiffness_matrix(k), np.diag(m), eigvals_only=True))
    return np.sqrt(np.abs(w2)) / (2 * np.pi)


def mode_shapes(k, m=M_STOREY):
    """(freqs_hz, phi): phi columns are mass-normalised mode shapes."""
    w2, phi = eigh(_stiffness_matrix(k), np.diag(m))
    order = np.argsort(w2)
    return np.sqrt(np.abs(w2[order])) / (2 * np.pi), phi[:, order]


def solve_healthy_stiffness(f_target=F_MEASURED, m=M_STOREY):
    """
    Recover k1,k2,k3 reproducing the measured undamaged modes (the inverse
    problem). Returns k. Residual is machine-precision for a determined fit.
    """
    from scipy.optimize import least_squares
    w = 2 * np.pi * f_target

    def resid(k):
        return np.sqrt(np.sort(eigh(_stiffness_matrix(k), np.diag(m),
                                    eigvals_only=True))) - w

    k0 = np.ones(3) * w[0] ** 2
    return least_squares(resid, k0, method="lm").x


# The healthy storey stiffnesses (computed once).
K_HEALTHY = solve_healthy_stiffness()


def rayleigh_damping(k, m=M_STOREY, zeta=ZETA):
    """
    Rayleigh C = a*M + b*K fitting the measured zeta at modes 1 and 2, so
    simulated decays match the rig's damping (feeds any time-domain synthesis).
    """
    f, _ = mode_shapes(k, m)
    w1, w2 = 2 * np.pi * f[0], 2 * np.pi * f[1]
    # zeta_i = a/(2 w_i) + b w_i / 2  ; solve for a,b from modes 1,2
    A = np.array([[1 / (2 * w1), w1 / 2], [1 / (2 * w2), w2 / 2]])
    a, b = np.linalg.solve(A, zeta[:2])
    return a * np.diag(m) + b * _stiffness_matrix(k)


# ─────────────────────────────────────────────
#  Damage parameterisation + training-set synthesis
# ─────────────────────────────────────────────
def apply_damage(alpha):
    """
    Damaged storey stiffnesses from reduction factors alpha=[a1,a2,a3], each in
    (0,1]: k_i_damaged = alpha_i * k_i_healthy. alpha=1 is undamaged; alpha->0 is
    a fully disconnected storey.
    """
    return K_HEALTHY * np.asarray(alpha, dtype=float)


def modal_features(alpha):
    """
    The observable the PINN consumes: modal frequencies as FRACTIONS of the
    healthy modes (what damage moves), matching the ringdown modal vector used by
    the classical detector. Returns [f1/f1_0, f2/f2_0, f3/f3_0].
    """
    f0 = modes_hz(K_HEALTHY)
    return modes_hz(apply_damage(alpha)) / f0


def generate_dataset(n=20000, seed=0, noise_pct=0.5):
    """
    Training set: modal-feature vectors labelled with the storey-damage state.

    Samples span undamaged, single-storey, and multi-storey stiffness loss over
    the full severity range, plus measurement noise at the observed replicate
    scatter (~0.5% on a mode). Returns dict of arrays:
        X        (n,3)  modal features [f1/f1_0, f2/f2_0, f3/f3_0]
        alpha    (n,3)  ground-truth storey stiffness fractions
        damaged  (n,)   0/1 any-storey-damaged flag
        location (n,)   argmax-damaged storey 0..2, or -1 if undamaged
        severity (n,)   max stiffness loss (1 - min alpha)

    The absolute-mass and uniform-mass assumptions mean this trains the model on
    RELATIVE modal shifts, which is what the rig measures.
    """
    rng = np.random.RandomState(seed)
    X, AL = [], []
    for _ in range(n):
        r = rng.rand()
        alpha = np.ones(3)
        if r < 0.15:
            pass                                   # undamaged
        elif r < 0.75:                             # single-storey damage
            s = rng.randint(3)
            alpha[s] = rng.uniform(0.15, 0.98)     # 2-85% stiffness loss
        else:                                      # multi-storey damage
            for s in range(3):
                if rng.rand() < 0.5:
                    alpha[s] = rng.uniform(0.15, 0.98)
        feat = modes_hz(apply_damage(alpha)) / modes_hz(K_HEALTHY)
        feat = feat * (1 + noise_pct / 100 * rng.randn(3))   # measurement noise
        X.append(feat)
        AL.append(alpha)
    X = np.array(X)
    AL = np.array(AL)
    loss = 1 - AL
    return {
        "X": X.astype(np.float32),
        "alpha": AL.astype(np.float32),
        "damaged": (loss.max(axis=1) > 0.02).astype(np.int64),
        "location": np.where(loss.max(axis=1) > 0.02, loss.argmax(axis=1), -1),
        "severity": loss.max(axis=1).astype(np.float32),
    }


if __name__ == "__main__":
    f0 = modes_hz(K_HEALTHY)
    print(f"K_HEALTHY = {np.round(K_HEALTHY, 2)}  (ratios 1:{K_HEALTHY[1]/K_HEALTHY[0]:.3f}:{K_HEALTHY[2]/K_HEALTHY[0]:.3f})")
    print(f"healthy modes = {np.round(f0,3)} Hz  (target {F_MEASURED})")
    print(f"residual = {np.max(np.abs(f0 - F_MEASURED)):.2e} Hz")
    d = generate_dataset(n=2000)
    print(f"dataset: X{d['X'].shape}, damaged frac {d['damaged'].mean():.2f}, "
          f"loc counts {np.bincount(d['location']+1)}")

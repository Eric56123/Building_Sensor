"""
Continuous-alpha dataset generator.
=========================================================================

WHY THIS EXISTS
---------------
The original dataset (`shm_benchmark_data.npy`) contains 7 Johnson-benchmark
damage patterns, which collapse to only 6 unique alpha vectors (k_v and k_vi are
bit-identical in matrices.py). That is not a training set for a 4-D continuous
inverse map -- the network memorises the handful of alphas it saw.

Worse, those benchmark stiffness matrices are NOT in the span of the storey
superposition model K(alpha) = sum_i alpha_i * K_i. The alpha labels are derived
by a Frobenius-norm ratio, which reconstructs K to only 0.7-5.1% relative error.
Consequently the physics residual (K(alpha) - w^2 M) is never singular at the
true alpha: L_phys(alpha_true) ~ 1e-3 instead of 0, and for the mild damage
cases the loss actually scores the INTACT structure better than the truth. The
physics term therefore cannot reward a correct answer -- see
`four_floor/diagnose_physics_loss.py`.

This generator fixes both problems at the source. Alpha is SAMPLED, and the
stiffness matrix is BUILT from it via exactly the same superposition the physics
loss assumes:

    K(alpha) = sum_i alpha_i * K_story_i

so alpha_true is exact by construction, L_phys(alpha_true) = 0 to machine
precision, and the physics loss finally has its global minimum at the answer.
The Johnson benchmark cases are retained as an out-of-distribution test set.

SAMPLING PRIOR (mixed, SHM-realistic)
-------------------------------------
    20%  intact          alpha = [1,1,1,1]
    50%  single-storey   one alpha_i ~ U[0.2, 1.0], rest = 1
    30%  multi-storey    2-4 storeys damaged, each ~ U[0.2, 1.0]

FORWARD MODEL (unchanged, reused as-is)
---------------------------------------
    damping_matrix -> newmark_beta -> 10% RMS sensor noise -> y-DOF extraction
    -> windowing -> sanitize (bandpass) -> Welch PSD (4, 1025)

OUTPUT
------
Sharded .npz files in data/continuous/ (sharded to keep each file small):
    psd        float32 (n, 4, 1025)   scaled? NO -- raw PSD, scaler is fit per fold
    alpha      float32 (n, 4)         ground truth, exact
    omega      float32 (n, 2)         first 2 natural freqs, rad/s
    mass_flag  int64   (n,)           0 = consistent, 1 = lumped asymmetric
    alpha_id   int64   (n,)           grouping key for a leak-free split

Usage
-----
    python -m four_floor.simulation.generate_dataset --n-alpha 500 --workers 4
"""
import argparse
import os
from multiprocessing import Pool

import numpy as np
from scipy.signal import welch

from four_floor.simulation.matrices import k_set, m_set, m_lump
from four_floor.simulation.damping import damping_matrix
from four_floor.simulation.excitation import newmark_beta, generate_excitation, D, dt, duration
from four_floor.preprocessing.cleaning import sanitize_accelerometer_data

# --- constants, kept identical to train.py so the pipeline is unchanged -------
FS = 1.0 / dt              # 1000 Hz
NPERSEG = 2048
CHUNK_SIZE = 4000          # 10 windows per 40 s simulation
FORCE_INTENSITY = 150.0
NOISE_RATIO = 0.10         # 10% RMS sensor noise, as in validation.py
DAMPING_RATIO = 0.01
Y_DOFS = [1, 4, 7, 10]     # y-direction DOFs in [x1,y1,th1, x2,y2,th2, ...]
OUT_DIR = os.path.join("data", "continuous")
SHARD_SIZE = 1000          # samples per .npz shard


# -----------------------------------------------------------------------------
# Storey decomposition (pure numpy; mirrors pinn_utils.decompose_stiffness_matrix
# but imported from there so there is a single source of truth when torch exists)
# -----------------------------------------------------------------------------
def _decompose(K_global):
    K_story = [np.zeros((12, 12)) for _ in range(4)]
    floor_idx = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]]
    k3 = [np.zeros((3, 3)) for _ in range(4)]
    for i in range(3, 0, -1):
        k3[i] = -K_global[np.ix_(floor_idx[i], floor_idx[i - 1])]
    k3[0] = K_global[np.ix_(floor_idx[0], floor_idx[0])] - k3[1]
    for i in range(4):
        ic = floor_idx[i]
        K_story[i][np.ix_(ic, ic)] += k3[i]
        if i > 0:
            ip = floor_idx[i - 1]
            K_story[i][np.ix_(ip, ip)] += k3[i]
            K_story[i][np.ix_(ic, ip)] -= k3[i]
            K_story[i][np.ix_(ip, ic)] -= k3[i]
    return K_story


try:
    from four_floor.pinn.pinn_utils import decompose_stiffness_matrix as _decompose_torch
    decompose = _decompose_torch          # single source of truth when torch present
except ImportError:
    decompose = _decompose

K_STORY = decompose(k_set[0] * 1e6)       # baseline storey matrices, N/m


# -----------------------------------------------------------------------------
# Alpha sampling
# -----------------------------------------------------------------------------
def sample_alphas(n, rng, a_min=0.2):
    """Mixed prior: 20% intact, 50% single-storey, 30% multi-storey."""
    alphas = np.ones((n, 4))
    kinds = rng.choice(["intact", "single", "multi"], size=n, p=[0.20, 0.50, 0.30])
    for j, kind in enumerate(kinds):
        if kind == "intact":
            continue
        if kind == "single":
            n_dmg = 1
        else:
            n_dmg = rng.integers(2, 5)  # 2, 3 or 4 storeys
        storeys = rng.choice(4, size=n_dmg, replace=False)
        alphas[j, storeys] = rng.uniform(a_min, 1.0, size=n_dmg)
    return alphas, kinds


def build_K(alpha):
    """K(alpha) = sum_i alpha_i * K_story_i  -- exactly what the physics loss assumes."""
    return sum(alpha[i] * K_STORY[i] for i in range(4))


# -----------------------------------------------------------------------------
# One simulation
# -----------------------------------------------------------------------------
def simulate(job):
    alpha_id, alpha, mass_flag, seed = job
    M = m_lump[1] if mass_flag == 1 else m_set[0]
    K = build_K(alpha)                       # N/m
    C, _, _ = damping_matrix(K / 1e6, M, damping_ratio=DAMPING_RATIO)  # expects MN/m

    F = D @ (generate_excitation(duration, dt, 4, seed=seed) * FORCE_INTENSITY)
    _, _, a = newmark_beta(M, C, K, F, dt)

    # 10% RMS sensor noise
    rng = np.random.default_rng(seed + 500_000)
    noise_std = NOISE_RATIO * np.max(np.sqrt(np.mean(a ** 2, axis=1)))
    a = a + rng.standard_normal(a.shape) * noise_std

    # true natural frequencies (rad/s), first 2 modes -- same recipe as validation.py
    f_hz = np.sort(np.sqrt(np.real(np.linalg.eigvals(np.linalg.inv(M) @ K)))) / (2 * np.pi)
    omega = 2 * np.pi * f_hz[:2]

    # y-direction sensors -> windows -> clean -> PSD
    accel_y = a[Y_DOFS, :]
    windows = [accel_y[:, s:s + CHUNK_SIZE]
               for s in range(0, accel_y.shape[1], CHUNK_SIZE)
               if s + CHUNK_SIZE <= accel_y.shape[1]]
    if not windows:
        return None
    windows = np.stack(windows)                                   # (w, 4, 4000)
    clean = sanitize_accelerometer_data(windows, fs=FS)
    _, psd = welch(clean, fs=FS, nperseg=NPERSEG, axis=-1)        # (w, 4, 1025)

    n_w = psd.shape[0]
    return dict(
        psd=psd.astype(np.float32),
        alpha=np.tile(alpha, (n_w, 1)).astype(np.float32),
        omega=np.tile(omega, (n_w, 1)).astype(np.float32),
        mass_flag=np.full(n_w, mass_flag, dtype=np.int64),
        alpha_id=np.full(n_w, alpha_id, dtype=np.int64),
    )


# -----------------------------------------------------------------------------
def job_seed(master_seed, alpha_id, mflag):
    """Deterministic per-simulation seed: chunking must not change the dataset."""
    ss = np.random.SeedSequence([master_seed, alpha_id, mflag])
    return int(ss.generate_state(1)[0] % (2 ** 31 - 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-alpha", type=int, default=500,
                    help="total number of unique alpha vectors (x2 mass formulations)")
    ap.add_argument("--alpha-start", type=int, default=0,
                    help="generate only alphas [start, start+count) -- for chunked runs")
    ap.add_argument("--alpha-count", type=int, default=None)
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", type=str, default=OUT_DIR)
    args = ap.parse_args()

    # The FULL alpha set is always drawn from the master seed, then sliced, so
    # the dataset is identical whether generated in one run or twenty chunks.
    rng = np.random.default_rng(args.seed)
    alphas, kinds = sample_alphas(args.n_alpha, rng)

    lo = args.alpha_start
    hi = args.n_alpha if args.alpha_count is None else min(lo + args.alpha_count, args.n_alpha)

    jobs = [(i, alphas[i], mflag, job_seed(args.seed, i, mflag))
            for i in range(lo, hi) for mflag in (0, 1)]

    os.makedirs(args.out, exist_ok=True)
    print(f"[gen] alphas [{lo}:{hi}) of {args.n_alpha} -> {len(jobs)} simulations "
          f"on {args.workers} workers")
    print(f"[gen] full-set prior: {np.sum(kinds=='intact')} intact, "
          f"{np.sum(kinds=='single')} single-storey, {np.sum(kinds=='multi')} multi-storey")

    with Pool(args.workers) as pool:
        results = [r for r in pool.imap_unordered(simulate, jobs, chunksize=4) if r is not None]

    keys = ["psd", "alpha", "omega", "mass_flag", "alpha_id"]
    chunk = {k: np.concatenate([r[k] for r in results]) for k in keys}
    order = np.argsort(chunk["alpha_id"], kind="stable")
    chunk = {k: v[order] for k, v in chunk.items()}

    shard_name = f"shard_a{lo:05d}_{hi:05d}.npz"
    np.savez_compressed(os.path.join(args.out, shard_name), **chunk)

    np.savez(os.path.join(args.out, "meta.npz"),
             alphas=alphas.astype(np.float32), kinds=np.array(kinds),
             n_alpha=args.n_alpha, seed=args.seed)

    print(f"[gen] wrote {shard_name}: {chunk['psd'].shape[0]} windows, "
          f"{len(np.unique(chunk['alpha_id']))} alpha groups")


def load_dataset(path=OUT_DIR):
    """Convenience loader: concatenates all shards back into arrays."""
    shards = sorted(f for f in os.listdir(path) if f.startswith("shard_"))
    keys = ["psd", "alpha", "omega", "mass_flag", "alpha_id"]
    parts = [np.load(os.path.join(path, f)) for f in shards]
    return {k: np.concatenate([p[k] for p in parts]) for k in keys}


if __name__ == "__main__":
    main()

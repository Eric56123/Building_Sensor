"""
Diagnostic: can the sigma_min/sigma_max physics loss reward the TRUE alpha?

NumPy-only replication of `physics_informed_loss` (float32, identical arithmetic:
K_hat = sum_i a_i * K_story_i ; L = sum over first 2 modes of
sigma_min(K_hat - w^2 M) / sigma_max(K_hat - w^2 M)). No torch dependency.

The omegas are regenerated exactly as `simulation/validation.py` stores them
(sqrt(eig(inv(M) @ K_damaged))/2pi, in Hz, first 5 sorted), so this needs no
access to shm_benchmark_data.npy.

Checks:
  A. Units of 'freqs' (Hz vs rad/s) and the 1e6 scaling -- by construction.
  B. Reconstruction error of the alpha parametrisation:
     does K(alpha_true) = sum_i alpha_i * K_story_i reproduce K_damaged?
  C. Physics loss AT ground-truth alpha  <-- the key number.
  D. Loss landscape along alpha_1, others held at truth: is there a descent
     direction pointing at the truth?

Run from repo root:  python -m four_floor.diagnose_physics_loss
"""
import numpy as np

from four_floor.simulation.matrices import k_set, m_set, m_lump

try:
    from four_floor.pinn.pinn_utils import decompose_stiffness_matrix
except ImportError:  # torch absent in this env; mirror the pure-numpy routine
    def decompose_stiffness_matrix(K_global):
        K_story_global = [np.zeros((12, 12)) for _ in range(4)]
        floor_idx = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]]
        k3 = [np.zeros((3, 3)) for _ in range(4)]
        for i in range(3, 0, -1):
            k3[i] = -K_global[np.ix_(floor_idx[i], floor_idx[i - 1])]
        k3[0] = K_global[np.ix_(floor_idx[0], floor_idx[0])] - k3[1]
        for i in range(4):
            ic = floor_idx[i]
            K_story_global[i][np.ix_(ic, ic)] += k3[i]
            if i > 0:
                ip = floor_idx[i - 1]
                K_story_global[i][np.ix_(ip, ip)] += k3[i]
                K_story_global[i][np.ix_(ic, ip)] -= k3[i]
                K_story_global[i][np.ix_(ip, ic)] -= k3[i]
        return K_story_global

np.set_printoptions(precision=4, suppress=True)

BASE_STORY = decompose_stiffness_matrix(k_set[0] * 1e6)
K_STORY = [m.astype(np.float32) for m in BASE_STORY]
M_CONS = np.asarray(m_set[0], dtype=np.float32)
M_LUMP = np.asarray(m_lump[1], dtype=np.float32)
GRID = np.linspace(0.05, 1.0, 20)


def derived_alpha(didx):
    """Exactly the alpha train.py derives: Frobenius-norm ratio, clipped."""
    cur = decompose_stiffness_matrix(k_set[didx] * 1e6)
    return np.array([
        np.clip(np.linalg.norm(cur[i]) / np.linalg.norm(BASE_STORY[i]), 0.01, 1.0)
        for i in range(4)
    ])


def stored_freqs(didx, lumped):
    """Reproduces validation.py exactly: sqrt(eig(inv(M) @ K))/2pi, sorted, in Hz."""
    M = m_lump[1] if lumped else m_set[0]
    f = np.sqrt(np.real(np.linalg.eigvals(np.linalg.inv(M) @ (k_set[didx] * 1e6))))
    return np.array(sorted(f / (2 * np.pi)))[:5]


def phys_loss(alpha, omegas, lumped):
    M = M_LUMP if lumped else M_CONS
    K_hat = sum(np.float32(alpha[i]) * K_STORY[i] for i in range(4))
    tot = 0.0
    for w in omegas:
        s = np.linalg.svd(K_hat - np.float32(w ** 2) * M, compute_uv=False)
        tot += s[-1] / (s[0] + 1e-8)
    return float(tot)


def main():
    scenarios = [(f"{'Lumped' if lu else 'Consistent'}_Damage_{i}", i, lu)
                 for lu in (False, True) for i in range(len(k_set))]

    print("=" * 78)
    print("A. FREQUENCY UNITS / SCALING")
    print("=" * 78)
    print("  validation.py stores freqs = sqrt(eig(inv(M) @ K*1e6)) / (2*pi)  -> HERTZ,")
    print("  using the same *1e6 stiffness and the same M as the physics loss.")
    print("  train.py then applies w = 2*pi*f.  CONSISTENT: no double-count, no 1e6 gap.")
    for key, didx, lumped in scenarios[:2]:
        f = stored_freqs(didx, lumped)
        print(f"  {key:24s} f[:2] = {f[:2]} Hz -> w = {2*np.pi*f[:2]} rad/s")

    print()
    print("=" * 78)
    print("B. CAN K(alpha) EVEN REPRESENT THE DAMAGE?")
    print("=" * 78)
    for _, didx, _ in scenarios[:len(k_set)]:
        a = derived_alpha(didx)
        K_hat = sum(a[i] * BASE_STORY[i] for i in range(4))
        K_true = k_set[didx] * 1e6
        rel = np.linalg.norm(K_hat - K_true) / np.linalg.norm(K_true)
        print(f"  case {didx}: alpha={a}   rel. reconstruction error = {rel:7.3%}")

    print()
    print("=" * 78)
    print("C. PHYSICS LOSS AT GROUND-TRUTH ALPHA  (lambda = 1)")
    print("=" * 78)
    print(f"  {'scenario':24s} {'L(a_true)':>10s} {'L(a=1)':>10s} {'L(a=0.5)':>10s} "
          f"{'best uniform a':>18s}")
    for key, didx, lumped in scenarios:
        w = 2 * np.pi * stored_freqs(didx, lumped)[:2]
        a_t = derived_alpha(didx)
        L_t = phys_loss(a_t, w, lumped)
        L_1 = phys_loss(np.ones(4), w, lumped)
        L_h = phys_loss(np.full(4, 0.5), w, lumped)
        best = min((phys_loss(np.full(4, g), w, lumped), g) for g in GRID)
        print(f"  {key:24s} {L_t:10.6f} {L_1:10.6f} {L_h:10.6f} "
              f"{best[0]:10.6f} @ a={best[1]:.2f}")

    print()
    print("=" * 78)
    print("D. LOSS LANDSCAPE ALONG alpha_1 (alpha_2..4 fixed at truth)")
    print("=" * 78)
    for key, didx, lumped in [scenarios[1], scenarios[len(k_set) + 1]]:
        w = 2 * np.pi * stored_freqs(didx, lumped)[:2]
        a_t = derived_alpha(didx)
        vals = [phys_loss(np.r_[a1, a_t[1:]], w, lumped) for a1 in GRID]
        lo, hi = min(vals), max(vals)
        print(f"\n  {key}   true alpha_1 = {a_t[0]:.4f}")
        for a1, L in zip(GRID, vals):
            n = int(40 * (L - lo) / (hi - lo + 1e-12))
            mark = "  <-- TRUE" if abs(a1 - a_t[0]) < (GRID[1] - GRID[0]) / 2 else ""
            print(f"    a1={a1:5.3f}  L={L:.6f}  {'#' * n}{mark}")
        print(f"    range {lo:.6f} -> {hi:.6f}   argmin at a1={GRID[int(np.argmin(vals))]:.3f}")


if __name__ == "__main__":
    main()

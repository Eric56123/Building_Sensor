import torch
import torch.nn as nn

class SHM_PINN(nn.Module):
    def __init__(self, n_frequency_bins):
        super(SHM_PINN, self).__init__()
        
        self.cnn = nn.Sequential(
            # in_channels=4 (one per sensor/floor)
            nn.Conv1d(4, 16, kernel_size=5, stride=1, padding=2),
            nn.BatchNorm1d(16),
            nn.ReLU(),
            nn.MaxPool1d(2),
            
            nn.Conv1d(16, 32, kernel_size=5, stride=1, padding=2),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.MaxPool1d(2),

            nn.Conv1d(32, 64, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(16)  # Fixed output size regardless of input length
        )
       
        
        # Flattened size is now 64 channels * 16 bins = 1024
        self.flattened_size = 64 * 16
        
        self.mlp = nn.Sequential(
            nn.Linear(self.flattened_size, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 4),
            nn.Sigmoid() # Alphas must be [0, 1]
        )

        # Apply Xavier Initialization for stability
        self.apply(self._init_weights)

    def _init_weights(self, m):
        if isinstance(m, nn.Linear) or isinstance(m, nn.Conv1d):
            torch.nn.init.xavier_uniform_(m.weight)
            if m.bias is not None:
                nn.init.constant_(m.bias, 0)

    def forward(self, x):
        x = self.cnn(x)
        x = x.view(x.size(0), -1)
        return self.mlp(x)


def physics_informed_loss(alpha_preds, omega_peaks, M_consistent, M_lumped, m_flags, K_story_tensors, lambda_weight=0.1):
    """
    Physics loss based on the eigenvalue condition: at a natural frequency,
    det(K - omega^2 * M) = 0, meaning the minimum singular value of the
    dynamic stiffness matrix should vanish.
    
    We minimise sigma_min(K_hat - omega^2 * M), normalised by sigma_max
    for scale invariance. This gives the network a meaningful gradient
    that actually responds to changes in the predicted alphas.
    """
    if lambda_weight == 0:
        return torch.tensor(0.0, device=alpha_preds.device, requires_grad=True)

    batch_size = alpha_preds.shape[0]
    p_loss = 0.0

    for b in range(batch_size):
        # 1. Select the correct Mass Matrix for this specific sample
        M_tensor = M_lumped if m_flags[b] == 1 else M_consistent
        
        # 2. Reconstruct the Global Stiffness Matrix from Predicted Alphas
        K_hat = torch.zeros_like(M_tensor)
        for i in range(4):
            K_hat += alpha_preds[b, i] * K_story_tensors[i]

        # 3. For each measured resonant peak, the minimum singular value
        #    of (K_hat - omega^2 * M) should be zero
        for j in range(2):  # First 2 modes
            w2 = omega_peaks[b, j] ** 2
            dyn_stiffness = K_hat - (w2 * M_tensor)
            
            # Compute singular values (sorted descending)
            # SVD is not supported on MPS, so fall back to CPU and return
            s = torch.linalg.svdvals(dyn_stiffness.cpu()).to(alpha_preds.device)
            
            # Normalise by the largest singular value for scale invariance
            # This makes the loss ~O(1) and comparable to the data loss
            p_loss += s[-1] / (s[0] + 1e-8)

    return (p_loss / batch_size) * lambda_weight


def physics_informed_loss_batched(alpha_preds, omega_peaks, M_consistent, M_lumped,
                                  m_flags, K_story_tensors, lambda_weight=0.1,
                                  n_modes=2):
    """
    Vectorised, numerically identical replacement for `physics_informed_loss`.

    The original loops over the batch and calls torch.linalg.svdvals once per
    (sample, mode), each time round-tripping a 12x12 matrix to the CPU because
    MPS has no SVD kernel. At 140 windows that is tolerable; at 10,000 windows
    x 500 epochs it is ~10^7 individual SVDs and the run never finishes.

    Here every (sample, mode) dynamic-stiffness matrix is stacked into one
    (B * n_modes, 12, 12) tensor and a single batched svdvals call handles the
    lot. Same maths, same gradients -- just one kernel launch instead of 2B.

    Returns lambda * mean_b [ sum_j sigma_min / sigma_max ], matching the
    original's convention (the original SUMS over modes and MEANS over the
    batch), so numbers remain comparable with previously logged runs.
    """
    if lambda_weight == 0:
        return torch.tensor(0.0, device=alpha_preds.device, requires_grad=True)

    B = alpha_preds.shape[0]

    # K_hat[b] = sum_i alpha[b,i] * K_story[i]      -> (B, 12, 12)
    K_stack = torch.stack(K_story_tensors, dim=0)              # (4, 12, 12)
    K_hat = torch.einsum("bi,ijk->bjk", alpha_preds, K_stack)

    # per-sample mass matrix, selected by the scenario's formulation flag
    M_sel = torch.where(
        m_flags.view(B, 1, 1).bool(),
        M_lumped.unsqueeze(0).expand(B, -1, -1),
        M_consistent.unsqueeze(0).expand(B, -1, -1),
    )                                                          # (B, 12, 12)

    w2 = omega_peaks[:, :n_modes] ** 2                         # (B, n_modes)

    # (B, n_modes, 12, 12): K_hat - w^2 M, one slab per measured resonance
    dyn = K_hat.unsqueeze(1) - w2.view(B, n_modes, 1, 1) * M_sel.unsqueeze(1)
    dyn = dyn.reshape(B * n_modes, 12, 12)

    # single batched SVD (still on CPU: MPS has no svdvals kernel; gradients
    # flow back through the device transfer unchanged)
    s = torch.linalg.svdvals(dyn.cpu()).to(alpha_preds.device)  # (B*n_modes, 12)

    ratio = s[:, -1] / (s[:, 0] + 1e-8)
    p_loss = ratio.view(B, n_modes).sum(dim=1).mean()

    return p_loss * lambda_weight

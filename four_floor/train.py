import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import os
from scipy.signal import welch

# ---------------------------------------------------------
# DEPENDENCIES
# ---------------------------------------------------------
from four_floor.simulation.matrices import k_set, m_set, m_lump
from four_floor.preprocessing.cleaning import sanitize_accelerometer_data
from four_floor.preprocessing.normalisation import PSDScaler
from four_floor.pinn.pinn_model import SHM_PINN, physics_informed_loss
from four_floor.pinn.pinn_dataset import create_dataloaders
from four_floor.pinn.pinn_utils import decompose_stiffness_matrix, prepare_physics_tensors

# ---------------------------------------------------------
# HYPERPARAMETERS
# ---------------------------------------------------------
FS = 1000.0
NPERSEG = 2048
CHUNK_SIZE = 4000
EPOCHS = 500
BATCH_SIZE = 16
LEARNING_RATE = 5e-4
LAMBDA_PHYS = 0.1

# y-DOF indices in per-floor ordering: [x1,y1,θ1, x2,y2,θ2, ...]
# y1=1, y2=4, y3=7, y4=10
Y_DOFS = [1, 4, 7, 10]

def main():
    print("==================================================")
    print(" SHM PINN: MULTI-PHYSICS TRAINING (CONSISTENT & LUMPED)")
    print("==================================================")

    # ---------------------------------------------------------
    # PHASE 1: DATA EXTRACTION & DUAL-MASS TAGGING
    # ---------------------------------------------------------
    if not os.path.exists("shm_benchmark_data.npy"):
        raise FileNotFoundError("Run simulation script first!")
        
    all_results = np.load("shm_benchmark_data.npy", allow_pickle=True).item()
    
    # Pre-calculate baseline for damage ratios
    K_baseline_global = k_set[0] * 1e6
    baseline_story_matrices = decompose_stiffness_matrix(K_baseline_global)

    raw_accel_list, true_alphas_list, omega_peaks_list, mass_type_list = [], [], [], []

    print(" -> Extracting and Tagging Multi-Physics Data...")
    items = list(all_results.items())
    np.random.seed(42)
    np.random.shuffle(items)

    for key, data in items:
        # Determine Mass Type from Key (Generated in simulation script)
        # Consistent = 0, Lumped = 1
        m_type = 1 if "Lumped" in key or "Case4" in key else 0
        damage_idx = int(key.split("_")[-1])
        
        # Calculate Alphas
        K_current_global = k_set[damage_idx] * 1e6
        current_story_matrices = decompose_stiffness_matrix(K_current_global)
        
        # --- ROBUST MAGNITUDE-BASED ALPHA ---
        alphas = []
        for i in range(4):
            # Compare the total energy/magnitude of the story matrix
            # This catches damage in X, Y, or Theta (Rotation)
            k_curr_norm = np.linalg.norm(current_story_matrices[i])
            k_base_norm = np.linalg.norm(baseline_story_matrices[i])
            
            ratio = k_curr_norm / k_base_norm if k_base_norm > 1e-3 else 1.0
            
            # Use a slightly wider clip to allow the model to see the 71Hz shift
            alphas.append(np.clip(ratio, 0.01, 1.0))
            
        # Extract the 4 y-direction accelerations using correct DOF indices
        accel_4dof_y = data['accel'][Y_DOFS, :] 
        w_peaks = 2 * np.pi * np.array(data['freqs'][:2])
        
        # Windowing
        n_steps = accel_4dof_y.shape[1]
        for start in range(0, n_steps, CHUNK_SIZE):
            end = start + CHUNK_SIZE
            if end <= n_steps:
                raw_accel_list.append(accel_4dof_y[:, start:end])
                true_alphas_list.append(alphas)
                omega_peaks_list.append(w_peaks)
                mass_type_list.append(m_type)

    # Convert to Numpy
    raw_accel_data = np.array(raw_accel_list)
    true_alphas_data = np.array(true_alphas_list)
    omega_peaks_data = np.array(omega_peaks_list)
    mass_type_data = np.array(mass_type_list)

    # Standard Poison Purge
    valid_indices = ~np.isnan(true_alphas_data).any(axis=1) & \
                    ~np.isnan(raw_accel_data.reshape(len(raw_accel_data), -1)).any(axis=1)
    
    raw_accel_data = raw_accel_data[valid_indices]
    true_alphas_data = true_alphas_data[valid_indices]
    omega_peaks_data = omega_peaks_data[valid_indices]
    mass_type_data = mass_type_data[valid_indices]

    print(f" -> Dataset Purged. Total Samples: {len(raw_accel_data)}")
    print(f" -> Unique Alphas: {np.unique(true_alphas_data, axis=0)}")
    print(f" -> Mass Distribution: {np.sum(mass_type_data==0)} Consistent, {np.sum(mass_type_data==1)} Lumped")

    # ---------------------------------------------------------
    # PHASE 2: PROCESSING
    # ---------------------------------------------------------
    clean_accel_data = sanitize_accelerometer_data(raw_accel_data, fs=FS)
    freqs, psd_arrays = welch(clean_accel_data, fs=FS, nperseg=NPERSEG, axis=-1)
    N_BINS = psd_arrays.shape[-1]
    
    split_idx = int(raw_accel_data.shape[0] * 0.8)
    scaler = PSDScaler()
    train_psd = scaler.fit_transform(psd_arrays[:split_idx])
    test_psd = scaler.transform(psd_arrays[split_idx:])

    train_loader, test_loader = create_dataloaders(
        train_psd, true_alphas_data[:split_idx], omega_peaks_data[:split_idx],
        test_psd, true_alphas_data[split_idx:], omega_peaks_data[split_idx:],
        batch_size=BATCH_SIZE,
        extra_data={'mass_type': [mass_type_data[:split_idx], mass_type_data[split_idx:]]}
    )

    # ---------------------------------------------------------
    # PHASE 3: MULTI-PHYSICS SETUP
    # ---------------------------------------------------------
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    
    # Single call returns all three: story tensors + both mass matrices
    K_story_tensors, M_consistent, M_lumped = prepare_physics_tensors(
        k_set, m_set, m_lump, device
    )
    
    model = SHM_PINN(n_frequency_bins=N_BINS).to(device)
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    mse_criterion = nn.MSELoss()
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)

    # ---------------------------------------------------------
    # PHASE 4: TRAINING
    # ---------------------------------------------------------
    for epoch in range(EPOCHS):
        model.train()
        r_data_loss, r_phys_loss = 0.0, 0.0
        
        for batch in train_loader:
            x_psd = batch['psd'].to(device)
            y_true = batch['alpha_true'].to(device)
            y_omega = batch['omega_peak'].to(device)
            m_flags = batch['mass_type'].to(device) # Flag 0 or 1
            
            optimizer.zero_grad()
            preds = model(x_psd)
            
            # Loss 1: Data
            d_loss = mse_criterion(preds, y_true)
            
            # Loss 2: Multi-Mass Physics
            p_loss = physics_informed_loss(
                preds, y_omega, 
                M_consistent, M_lumped, m_flags, 
                K_story_tensors, lambda_weight=LAMBDA_PHYS
            )
            
            total_loss = d_loss + p_loss
            total_loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            
            r_data_loss += d_loss.item()
            r_phys_loss += p_loss.item()
            
        avg_d, avg_p = r_data_loss/len(train_loader), r_phys_loss/len(train_loader)
        scheduler.step()
        
        if (epoch + 1) % 10 == 0 or epoch == 0:
            print(f"Epoch [{epoch+1:03d}] | Data Loss: {avg_d:.6f} | Phys Loss: {avg_p:.6f}")

    torch.save(model.state_dict(), "shm_pinn_weights.pth")
    print("\n[SUCCESS] Training Complete.")

if __name__ == "__main__":
    main()
import numpy as np
import os
from four_floor.simulation.matrices import k_set, m_set, m_lump
from four_floor.simulation.damping import damping_matrix
from four_floor.simulation.excitation import newmark_beta, F_total, dt

# y-DOF indices in per-floor ordering: [x1,y1,θ1, x2,y2,θ2, ...]
# y1=1, y2=4, y3=7, y4=10
Y_DOFS = [1, 4, 7, 10]

# Compares the consistent vs lumped mass formulations across damage patterns
def main():
    print("==================================================")
    print(" SHM PINN: DATA GENERATION ENGINE (CONSISTENT vs LUMPED)")
    print("==================================================")

    all_results = {}
    fs = 1.0 / dt
    
    # We will generate data for all 7 stiffness patterns defined in k_set
    n_damage_patterns = len(k_set) # 1 undamaged + 6 damage patterns = 7 total scenarios per mass type

    # ---------------------------------------------------------
    # PART A: CONSISTENT MASS (CASE 1-3 STYLE)
    # ---------------------------------------------------------
    print(f"\n[Phase 1] Generating {n_damage_patterns} Consistent Mass Cases...")
    
    # We use m_set[0] (Undamaged Consistent) as the baseline mass for Phase 1
    M_consist = m_set[0] 

    for i in range(n_damage_patterns):
        K_curr = k_set[i] * 1e6  # MN/m to N/m
        
        # Calculate fresh damping for this specific K/M pair
        # Calculates damping matrix from the stiffness and mass matrices 
        C_curr, _, _ = damping_matrix(k_set[i], M_consist, damping_ratio=0.01)
        
        # 1. Run Newmark-Beta Solver
        # Gives us the full dynamic simulation
        # Returns 12 degrees of freedom (x,y,theta for each floor) over 40000 time steps (40s at 1000Hz)
        u, v, a = newmark_beta(M_consist, C_curr, K_curr, F_total, dt)
        
        # 2. Inject 10% RMS Noise (Real-world sensor simulation)
        max_rms = np.max(np.sqrt(np.mean(a**2, axis=1))) # RMS of acceleration is typical magnitude of motion 
        noise_std = 0.10 * max_rms # 10% Noise ratio is realistic sensor error 
        np.random.seed(42 + i) #Different noise for every case
        a_noisy = a + np.random.randn(*a.shape) * noise_std 
        
        # 3. Calculate True Natural Frequencies for the Physics-Loss labels
        # Solves the undamped eigenvalue problem to find the natural frequencies of the structure with the current stiffness and mass matrices. This is important for the physics-based loss in the PINN, which compares predicted frequencies to these true values.
        freqs = np.sqrt(np.real(np.linalg.eigvals(np.linalg.inv(M_consist) @ K_curr))) / (2*np.pi)
        
        # 4. Save with "Consistent" tag
        case_label = f"Consistent_Damage_{i}"
        all_results[case_label] = {
            'accel': a_noisy, 
            'freqs': sorted(freqs)[:5], # Save first 5 modes
            'mass_type': 'consistent'
        }
        print(f"  -> Generated {case_label} | F1: {sorted(freqs)[0]:.2f}Hz")

    # ---------------------------------------------------------
    # PART B: LUMPED MASS (CASE 4 STYLE)
    # ---------------------------------------------------------
    print(f"\n[Phase 2] Generating {n_damage_patterns} Lumped Asymmetric Mass Cases...")
    
    # Use the asymmetric lumped mass matrix for complex coupling
    M_lumped = m_lump[1] 

    for i in range(n_damage_patterns):
        K_curr = k_set[i] * 1e6
        
        # Calculate fresh damping
        C_curr, _, _ = damping_matrix(k_set[i], M_lumped, damping_ratio=0.01)
        
        # 1. Run Solver
        u, v, a = newmark_beta(M_lumped, C_curr, K_curr, F_total, dt)
        
        # 2. Inject Noise
        max_rms = np.max(np.sqrt(np.mean(a**2, axis=1)))
        noise_std = 0.10 * max_rms
        np.random.seed(100 + i)
        a_noisy = a + np.random.randn(*a.shape) * noise_std 
        
        # 3. Calculate Frequencies
        freqs = np.sqrt(np.real(np.linalg.eigvals(np.linalg.inv(M_lumped) @ K_curr))) / (2*np.pi)
        
        # 4. Save with "Lumped" tag
        case_label = f"Lumped_Damage_{i}"
        all_results[case_label] = {
            'accel': a_noisy, 
            'freqs': sorted(freqs)[:5],
            'mass_type': 'lumped'
        }
        print(f"  -> Generated {case_label} | F1: {sorted(freqs)[0]:.2f}Hz")

    # ---------------------------------------------------------
    # SAVE EVERYTHING
    # ---------------------------------------------------------
    output_file = "shm_benchmark_data.npy"
    if os.path.exists(output_file):
        os.remove(output_file) # Ensure clean overwrite
        
    np.save(output_file, all_results)
    print(f"\n[SUCCESS] Saved {len(all_results)} total scenarios to {output_file}")

if __name__ == "__main__":
    main()
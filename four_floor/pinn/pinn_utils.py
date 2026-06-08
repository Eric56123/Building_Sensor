import numpy as np
import torch
"""
Assumes that the benchmark acts as a shear model, where floors are rigid and the only things which bend is the columns/braces
Therefore the only things that floor 3 are floor 4 and floor 2 and will have not connection to floor 1 

"""


def decompose_stiffness_matrix(K_global):
    """
    Decomposes a 12x12 global stiffness matrix (ordered per-floor:
    [x1,y1,θ1, x2,y2,θ2, x3,y3,θ3, x4,y4,θ4]) into 4 separate 12x12
    matrices representing the individual story contributions.
    """
    # Pre-allocate the 4 global matrices (12x12) filled with zeros
    K_story_global = [np.zeros((12, 12)) for _ in range(4)]
    
    # DOF ordering is per-floor:
    # Floor 1 = indices [0, 1, 2]   (x1, y1, theta1)
    # Floor 2 = indices [3, 4, 5]   (x2, y2, theta2)
    # Floor 3 = indices [6, 7, 8]   (x3, y3, theta3)
    # Floor 4 = indices [9, 10, 11] (x4, y4, theta4)
    floor_idx = [
        [0, 1, 2],
        [3, 4, 5],
        [6, 7, 8],
        [9, 10, 11]
    ]
    
    k_story_3x3 = [np.zeros((3, 3)) for _ in range(4)]
    
    # 1. Extract Top-Down (Stories 4, 3, 2)
    # The interaction force between floor i and floor i-1 is strictly equal to -k_story.
    for i in range(3, 0, -1):
        idx_current = floor_idx[i]
        idx_below = floor_idx[i-1]
        
        # Extract the 3x3 block connecting this floor to the one below it
        # Since K_ij = -k_story, we take the negative to get the positive story stiffness
        k_story_3x3[i] = -K_global[np.ix_(idx_current, idx_below)]
        
    # 2. Extract Story 1
    # Story 1 connects to the ground (which has no DOFs), so we cannot use off-diagonals.
    # But we know K_11 (the diagonal block for Floor 1) = k_story_1 + k_story_2
    k_story_3x3[0] = K_global[np.ix_(floor_idx[0], floor_idx[0])] - k_story_3x3[1]
    
    # 3. Assemble the 12x12 Global Tensors for the PINN Superposition
    for i in range(4):
        idx_curr = floor_idx[i]
        
        # Add the +k components to the current floor's diagonal
        K_story_global[i][np.ix_(idx_curr, idx_curr)] += k_story_3x3[i]
        
        if i > 0:
            idx_prev = floor_idx[i-1]
            # Add the +k components to the lower floor's diagonal
            K_story_global[i][np.ix_(idx_prev, idx_prev)] += k_story_3x3[i]
            # Add the -k components to the off-diagonals bridging the two floors
            K_story_global[i][np.ix_(idx_curr, idx_prev)] -= k_story_3x3[i]
            K_story_global[i][np.ix_(idx_prev, idx_curr)] -= k_story_3x3[i]
            
    return K_story_global


def prepare_physics_tensors(k_set, m_set, m_lump, device='cpu'):
    """
    Executes the decomposition and converts all physics arrays 
    to PyTorch tensors so they are ready for the loss function.
    
    Now returns BOTH mass matrices so the physics loss can switch per sample.
    """
    # 1. Grab the Undamaged Baseline Matrix (Case 1, k_set[0])
    # Ensure it is in N/m by multiplying by 1e6
    K_undamaged_raw = k_set[0] * 1e6 
    
    # 2. Decompose it into the 4 sub-matrices
    K_story_matrices = decompose_stiffness_matrix(K_undamaged_raw)
    
    # 3. Convert to PyTorch 32-bit float tensors and move to GPU/CPU
    K_story_tensors = [torch.tensor(mat, dtype=torch.float32).to(device) for mat in K_story_matrices]
    
    # 4. Prepare BOTH Mass Tensors
    M_consistent = torch.tensor(m_set[0], dtype=torch.float32).to(device)
    M_lumped = torch.tensor(m_lump[1], dtype=torch.float32).to(device)  # Asymmetric lumped
    
    return K_story_tensors, M_consistent, M_lumped

# ---------------------------------------------------------
# HOW TO CALL THIS IN YOUR MAIN SCRIPT
# ---------------------------------------------------------
if __name__ == "__main__":
    from four_floor.simulation.matrices import k_set, m_set, m_lump
    
    # Run the decomposition
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    K_story_tensors, M_consistent, M_lumped = prepare_physics_tensors(k_set, m_set, m_lump, device)
    
    print(f"Successfully decomposed {len(K_story_tensors)} story stiffness tensors.")
    print(f"Shape of Story 1 Tensor: {K_story_tensors[0].shape}")
    
    # Quick physics check: If we add all 4 together, it should exactly equal the original
    K_reconstructed = K_story_tensors[0] + K_story_tensors[1] + K_story_tensors[2] + K_story_tensors[3]
    K_original_tensor = torch.tensor(k_set[0] * 1e6, dtype=torch.float32).to(device)
    
    error = torch.max(torch.abs(K_reconstructed - K_original_tensor))
    print(f"Reconstruction Error: {error.item()} (Should be exactly 0.0)")
    
    # Verify extracted story stiffnesses make physical sense
    for i, Ks in enumerate(K_story_tensors):
        print(f"\nStory {i+1} diagonal block (3x3):")
        floor_idx = [0, 1, 2] if i == 0 else [3*i, 3*i+1, 3*i+2]
        print(Ks[floor_idx][:, floor_idx])
import torch
import numpy as np
import matplotlib.pyplot as plt
from four_floor.pinn.pinn_model import SHM_PINN

def evaluate_and_plot():
    # 1. Load Model and Data
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    all_results = np.load("/Users/erictan/Documents/GEOL0066/Dissertation/PINN_Development/shm_benchmark_data.npy", allow_pickle=True).item()
    
    # Use the number of bins from your training (usually 1025 for 2048 NPERSEG)
    model = SHM_PINN(n_frequency_bins=1025).to(device)
    # Change map_state_dict to map_location
    model.load_state_dict(torch.load("/Users/erictan/Documents/GEOL0066/Dissertation/PINN_Development/shm_pinn_weights.pth", map_location=device))
    model.eval()

    # 2. Pick a random "Lumped" and "Consistent" case to test
    test_keys = ["Consistent_Damage_2", "Lumped_Damage_2"] 
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    for idx, key in enumerate(test_keys):
        # This part mimics the train.py preprocessing
        data = all_results[key]
        # (Add your PSD calculation/Scaling here if not already saved)
        # For now, let's assume we are testing the Alphas
        
        # MENTOR NOTE: Replace the lines below with actual predictions 
        # once you pass a sample through your PSDScaler
        true_alphas = [0.71, 1.0, 0.71, 1.0] # Example for Damage_2
        pred_alphas = [0.75, 0.98, 0.72, 0.99] # Placeholder for model.forward()
        
        floors = ["Floor 1", "Floor 2", "Floor 3", "Floor 4"]
        x = np.arange(len(floors))
        
        axes[idx].bar(x - 0.2, true_alphas, 0.4, label='True Alpha', color='black', alpha=0.7)
        axes[idx].bar(x + 0.2, pred_alphas, 0.4, label='Predicted Alpha', color='red', alpha=0.7)
        
        axes[idx].set_title(f"Results for {key}")
        axes[idx].set_xticks(x)
        axes[idx].set_xticklabels(floors)
        axes[idx].set_ylim(0, 1.1)
        axes[idx].legend()
        axes[idx].grid(axis='y', linestyle='--', alpha=0.6)

    plt.tight_layout()
    plt.show()
def get_damage_status(pred_alphas):
    """
    Translates PINN stiffness ratios into a 0-10 scale and a safety color.
    """
    damage_indices = (1.0 - pred_alphas) * 10
    
    # Calculate the 'Global' damage as the worst-performing floor
    global_di = np.max(damage_indices)
    
    if global_di < 1.5:
        color = "GREEN"
        signal = "🟢"
    elif global_di < 4.0:
        color = "YELLOW"
        signal = "🟡"
    elif global_di < 7.0:
        color = "ORANGE"
        signal = "🟠"
    else:
        color = "RED"
        signal = "🔴"
        
    return damage_indices, color, signal, global_di

test_keys = ["Consistent_Damage_0", "Consistent_Damage_1", "Lumped_Damage_2"]

# Example Usage:
# preds = model(psd_tensor) -> [0.75, 0.98, 0.72, 0.99]
# indices, col, sig, g_di = get_damage_status(preds)
if __name__ == "__main__":
    evaluate_and_plot()
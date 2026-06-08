import torch
import numpy as np
import os
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import matplotlib.cm as cm
from scipy.signal import welch

# ---------------------------------------------------------
# DEPENDENCIES
# ---------------------------------------------------------
from four_floor.pinn.pinn_model import SHM_PINN
from four_floor.preprocessing.cleaning import sanitize_accelerometer_data

# y-DOF indices in per-floor ordering: [x1,y1,θ1, x2,y2,θ2, ...]
# y1=1, y2=4, y3=7, y4=10
Y_DOFS = [1, 4, 7, 10]

def get_damage_status(pred_alphas):
    """
    Translates PINN stiffness ratios into a 0-10 scale and a safety color.
    """
    damage_indices = (1.0 - pred_alphas) * 10
    global_di = np.max(damage_indices)
    
    if global_di < 1.5:
        color, signal = "green", "🟢"
    elif global_di < 4.0:
        color, signal = "orange", "🟡" 
    elif global_di < 7.0:
        color, signal = "darkorange", "🟠"
    else:
        color, signal = "red", "🔴"
        
    return damage_indices, color, signal, global_di

def main():
    print("==================================================")
    print(" SHM PINN: BUILDING HEALTH DASHBOARD (CALIBRATED)")
    print("==================================================")

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    
    # 1. LOAD DATA AND MODEL
    if not os.path.exists("shm_benchmark_data.npy"):
        print("Error: shm_benchmark_data.npy not found.")
        return
        
    all_results = np.load("shm_benchmark_data.npy", allow_pickle=True).item()
    
    model = SHM_PINN(n_frequency_bins=1025).to(device)
    model.load_state_dict(torch.load("shm_pinn_weights.pth", map_location=device))
    model.eval()

    # 2. SELECT A TEST CASE (Try Damage_2 for clear results)
    key = "Lumped_Damage_2" 
    data = all_results[key]
    
    # 3. PRE-PROCESS RAW DATA
    # Extract 4-floor Y-accel using correct DOF indices
    accel_raw = data['accel'][Y_DOFS, :4000] 
    
    clean_accel = sanitize_accelerometer_data(np.expand_dims(accel_raw, axis=0), fs=1000.0)
    _, psd = welch(clean_accel, fs=1000.0, nperseg=2048, axis=-1)
    
    # --- CALIBRATED NORMALIZATION ---
    # We use the Min/Max values found during your training session
    psd_log = np.log10(psd + 1e-10)
    psd_norm = (psd_log - (-10.00)) / (-2.09 - (-10.00))
    psd_norm = np.clip(psd_norm, 0, 1) # Ensure values are in [0, 1] range
    
    psd_tensor = torch.tensor(psd_norm, dtype=torch.float32).to(device)

    # 4. RUN PINN INFERENCE
    with torch.no_grad():
        pred_alpha = model(psd_tensor).cpu().numpy()[0]
    
    # 5. CALCULATE DAMAGE INDEX
    di_indices, color, signal, global_di = get_damage_status(pred_alpha)

    # ---------------------------------------------------------
    # 6. VISUALIZATION
    # ---------------------------------------------------------
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(3, 4)

    # A. Time-History Plot
    ax_accel = fig.add_subplot(gs[0:2, 0:2])
    time = np.linspace(0, 4.0, 4000)
    ax_accel.plot(time, accel_raw[3, :], color='black', alpha=0.6, label="Roof (F4)")
    ax_accel.plot(time, accel_raw[0, :], color='blue', alpha=0.4, label="Floor 1")
    ax_accel.set_title(f"Input Signal: {key}", fontsize=14)
    ax_accel.set_ylabel("Accel (m/s^2)")
    ax_accel.set_xlabel("Time (s)")
    ax_accel.legend()
    ax_accel.grid(True, ls='--', alpha=0.3)

    # B. Heatmap
    ax_map = fig.add_subplot(gs[0:2, 2:4])
    ax_map.set_axis_off()
    cmap = cm.get_cmap('RdYlGn_r')

    b_w, f_h, fnd = 10, 15, 5
    for i in range(4):
        di = di_indices[i]
        floor_color = cmap(di / 10.0)
        f_y = fnd + i * (f_h + 2)
        
        rect = Rectangle((-b_w/2, f_y), b_w, f_h, facecolor=floor_color, edgecolor='black', lw=2)
        ax_map.add_patch(rect)
        ax_map.text(-b_w/2 - 2, f_y + f_h/2, f"Floor {i+1}", ha='right', va='center', weight='bold', fontsize=12)
        ax_map.text(b_w/2 + 2, f_y + f_h/2, f"DI: {di:.1f}/10", ha='left', va='center', fontsize=12)

    ax_map.set_xlim(-25, 25)
    ax_map.set_ylim(-5, 80)
    ax_map.set_title("Damage Localization Heatmap", fontsize=16, pad=20)

    # Colorbar
    sm = cm.ScalarMappable(norm=plt.Normalize(vmin=0, vmax=10), cmap=cmap)
    cbar_ax = fig.add_axes([0.92, 0.4, 0.015, 0.4])
    plt.colorbar(sm, cax=cbar_ax, label="Damage Index (0=Healthy, 10=Critical)")

    # C. Decision Dashboard
    ax_dash = fig.add_subplot(gs[2, :])
    ax_dash.set_axis_off()
    ax_dash.add_patch(Rectangle((0.05, 0.1), 0.9, 0.8, fill=None, edgecolor='black', lw=2, transform=ax_dash.transAxes))
    
    display_color = color if color != 'yellow' else 'orange'
    ax_dash.text(0.5, 0.65, f"SAFETY STATUS: {color.upper()} {signal}", 
                 ha='center', va='center', fontsize=28, color=display_color, weight='bold', transform=ax_dash.transAxes)
    ax_dash.text(0.5, 0.35, f"MAX FLOOR DAMAGE INDEX: {global_di:.2f} / 10.0", 
                 ha='center', va='center', fontsize=20, transform=ax_dash.transAxes)

    plt.tight_layout(rect=[0, 0, 0.9, 1])
    plt.savefig("final_building_dashboard.png", dpi=300)
    plt.show()

if __name__ == "__main__":
    main()
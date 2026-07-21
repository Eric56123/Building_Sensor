import numpy as np
from scipy.signal import butter, lfilter, welch
from four_floor.simulation.damping import M, Cd, K

# matplotlib is imported inside __main__ only -- see the note in
# preprocessing/cleaning.py. A module-scope pyplot import makes every consumer
# of this module pay the font-cache cost on a fresh venv.


# 1. Gaussian White Noise Excitation Generator
def generate_excitation(duration, dt, n_floors, seed=123):
    np.random.seed(seed)
    n_samples = int(duration / dt) 
    raw = np.random.randn(n_floors, n_samples) #Creates white noise n_floors independent time series with n_samples points each. (n_floors, n_samples) shape. One excitation signal per floor
    fs = 1.0 / dt # Sampling Frequency 
    b, a = butter(6, 20.0, btype='low', fs=fs) # 6th order Butterworth low-pass filter with cutoff at 100 Hz. For masonry buildings (1-10Hz Natural frequencies)
    filtered = np.array([lfilter(b, a, raw[i]) for i in range(n_floors)]) #Applies filter to floor independently. Each row of raw is filtered and keeps the frequencies low and seismic like
    return filtered

"""
Newmark-beta integration for MDOF system.

Parameters
M : Mass matrix (n x n)
C : Damping matrix (n x n)
K : Stiffness matrix (n x n)
F : Force matrix (n x nt)
dt : Time step
beta : Newmark-beta parameter (default 0.25 for average acceleration)
gamma : Newmark-beta parameter (default 0.5 for average acceleration)

Returns
u : Displacement array (n x nt)
v : Velocity array (n x nt)
a : Acceleration array (n x nt)

"""

#The Newmark-beta method is a numerical integration technique which is preferred over the RK45
def newmark_beta(M, C, K, F, dt, beta=0.25, gamma=0.5):
    """
    Newmark-beta integration for MDOF system.
    Returns displacement, velocity, acceleration arrays
    """
    n = M.shape[0] # Number of DOFs
    nt = F.shape[1] # Number of Time Steps from the force matrix shape (n x nt)
    
    #Initialising arrays (12 DOF x nt time steps)
    u = np.zeros((n, nt))   # displacement
    v = np.zeros((n, nt))   # velocity
    a = np.zeros((n, nt))   # acceleration
    
    # Initial acceleration
    # From equation of motion Ma + Cv + Ku = F, at t=0, u and v are zero, so a[:, 0] = M^-1 * F[:, 0]
    a[:, 0] = np.linalg.solve(M, F[:, 0] - C @ v[:, 0] - K @ u[:, 0])
    
    # Effective stiffness matrix
    # K_eff combines mass, damping and stiffness weighted by time discretisation parameters. It is used to solve for the next displacement u[:, i+1] at each time step.
    # Beta = 0.25 and Gamma = 0.5 are average acceleration parameters that provide unconditional stability for linear problems. The effective stiffness matrix is derived from the Newmark-beta method's discretisation of the equations of motion.
    K_eff = K + gamma/(beta*dt) * C + 1/(beta*dt**2) * M
    K_eff_inv = np.linalg.inv(K_eff)  # precompute for efficiency
    
    # Time-stepping loop 
    # Includes contributions from the applied force, intertial terms and damping terms 
    # This is correction that accounts for past motion
    for i in range(nt - 1):
        # Effective force
        F_eff = F[:, i+1] \
            + M @ (1/(beta*dt**2) * u[:, i] + 1/(beta*dt) * v[:, i] + (1/(2*beta) - 1) * a[:, i]) \
            + C @ (gamma/(beta*dt) * u[:, i] + (gamma/beta - 1) * v[:, i] + dt*(gamma/(2*beta) - 1) * a[:, i])

        # Solve for new displacement 
        u[:, i+1] = K_eff_inv @ F_eff
        a[:, i+1] = 1/(beta*dt**2) * (u[:, i+1] - u[:, i] - dt*v[:, i]) - (1/(2*beta) - 1) * a[:, i] #Calculates new acceleration from displacement change using Newmark's kinematic realtion
        v[:, i+1] = v[:, i] + dt * ((1-gamma)*a[:, i] + gamma*a[:, i+1]) #Updates velocity using weighted average of new and old acceleration (Gamma = 0.5) means that they weigh equally
    
    return u, v, a

# ---------------------------------------------------------
# 2. BENCHMARK PARAMETERS
# ---------------------------------------------------------
duration = 40.0 #40 seconds of shaking 
dt = 0.001 #Sampling rate of 1000Hz, well above the Nyquist frequency (Maximum frequency we can represent given sampling rate)
n_floors = 4 # Four Storey Building
force_intensity = 150.0 #Reasonable force magnitude for lab-scale masonry building

# ---------------------------------------------------------
# 3. PREPARE THE EXCITATION MATRIX
# ---------------------------------------------------------
# Generate 4 rows of white noise
# Input white noise (4 x 40000) samples
# Outputs band-limited seismic-like excitation (4 x 40000), one force series per floor 
# Multiplies by 150 to scale from noise to physical forces
f_y_history = generate_excitation(duration, dt, n_floors) * force_intensity

# Create the spatial routing matrix D (12x4)
# DOF ordering is per-floor: [x1,y1,θ1, x2,y2,θ2, x3,y3,θ3, x4,y4,θ4]
# y-DOFs are at indices [1, 4, 7, 10]
D = np.zeros((12, 4)) #12 DOFs, 4 force channels (one per floor)
D[1,  0] = 1.0   # y1 <- force channel 0 
D[4,  1] = 1.0   # y2 <- force channel 1
D[7,  2] = 1.0   # y3 <- force channel 2
D[10, 3] = 1.0   # y4 <- force channel 3

# Converts the 4-floor forces into a 12-DOF space 
#Result is F_total containing floor 1 y force at DOF 1, floor 2 y force at DOF 4, floor 3 y force at DOF 7, and floor 4 y force at DOF 10. All other DOFs have zero force.
F_total = D @ f_y_history 

# ---------------------------------------------------------
# 4. RUN THE SIMULATION  (demo only -- see note)
# ---------------------------------------------------------
# This ran a full 40 s Newmark solve AT IMPORT. Every consumer of this module
# (train.py, run_experiments.py, generate_dataset.py) imports it only for
# `newmark_beta`, `generate_excitation`, `D` and `dt` -- and paid for a whole
# simulation it then threw away. Moved under __main__.
if __name__ == "__main__":
    import matplotlib.pyplot as plt

    # Run Newmark-beta. It natively returns u (disp), v (vel), and a (accel)
    u, v, a = newmark_beta(M, Cd, K, F_total, dt)

    # -----------------------------------------------------
    # 5. POST-PROCESSING & PSD PLOTTING
    # -----------------------------------------------------
    # Extract the roof y-direction acceleration (y4 = index 10)
    roof_y_accel = a[10, :]

    # Convert m/s^2 to cm/s^2 to match the benchmark visual scale
    roof_y_accel_cm = roof_y_accel * 100.0

    # Welch PSD: which frequencies carry the energy in the roof acceleration
    fs = 1.0 / dt
    frequencies, psd = welch(roof_y_accel_cm, fs=fs, nperseg=2048)

    plt.figure(figsize=(10, 5))
    plt.semilogy(frequencies, psd, color='black', linewidth=1, label='Case 1, undamaged')
    plt.title("PSD of East Y Roof Acceleration (Newmark-Beta)")
    plt.xlabel("Frequency [Hz]")
    plt.ylabel("PSD")
    plt.xlim(0, 100)
    plt.ylim(1e-2, 1e4)
    plt.grid(True, which="both", ls="--", alpha=0.5)
    plt.legend()
    plt.show()
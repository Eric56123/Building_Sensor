#Second File to Run for Damping Matrix Calculation

import numpy as np
from scipy.linalg import eigh
from four_floor.simulation.matrices import k_set, m_set, m_lumped_13
import scipy.linalg as la
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt



def damping_matrix(K_MNm, M, damping_ratio=0.01):
    """
    Compute physical damping matrix C from modal damping.

    Parameters
    K_MNm : Stiffness matrix in MN/m.
    M_kg : Mass matrix in kg.
    damping_ratio : Modal damping ratio. Benchmark uses 0.01 = 1%.

    Returns
    -------
    C : Damping matrix in SI units.
    frequencies_hz :Natural frequencies in Hz.
    modes : Mass-normalised mode shapes.
    """

    # Convert stiffness from MN/m to N/m
    K = K_MNm * 1e6
    
    # Computes the natural frequencies and mode shapes of a structure given stiffness and mass matrices
    # Generalised eigenvalue problem:
    # K phi = lambda M phi
    eigvals, modes = eigh(K, M)

    # Takes only the real part of the eigenvalue. Imaginary parts are usually negilible and are typically noise
    eigvals = np.real(eigvals)

    #Validation check that all eigenvalues are strictly positive. If any natural frequencies or modes are zero or negative 
    # then the system is rigid or unstable, which is unphysical for a well-defined building model. This check helps catch issues with the input K and M matrices.
    if np.any(eigvals <= 0):
        raise ValueError("Non-positive eigenvalue found. Check K and M.")

    # Converts the eigenvalues into natural frequencies in two forms 
    # Angular Frequency (rad/s) = sqrt(eigvals) (since eigvals = omega^2)
    # This is the fundamental frequnecy used in vibration analysis
    omega = np.sqrt(eigvals)           # rad/s

    # Converts angular frequency to Hz
    #Used to compare with experimental measurements and for results and plotting 
    frequencies_hz = omega / (2*np.pi)

    # scipy.linalg.eigh(K, M) returns mass-normalised modes:
    # modes.T @ M @ modes = I
    # Calculates the damping coefficients for each mode (2 * damping_ratio * omega) 
    # damping ratio is typically 0.01 - 0.1 
    modal_damping = np.diag(2 * damping_ratio * omega)

    # Transform modal damping back to physical coordinates
    # modes.T @ M multiplies the modal damping by the mass matrix
    # modal_damping @ modes.T transforms this back into physical coordinates
    #M @ modes post multiples by the mass matrix to get the final damping matrix in physical coordinates
    C = M @ modes @ modal_damping @ modes.T @ M

    # Symmetrise to remove tiny numerical noise
    # Removes numerical errors accumulating during arithematic and multiplication
    # Should be symmetrical as damping does not favour any direction 
    C = 0.5 * (C + C.T)

    return C, frequencies_hz, modes


c_consistent = []
freq_consistent = []
mode_consistent = []

# Compute damping matrices for consistent mass cases 
# Finds the Damping matrix, natural frequencies and mode shapes for the 3 consistent mass cases in Johnson 2004
# Masonry buildings have low damping 0.5 - 5%, so 0.01 is conservative but reasonable for a benchmark test. This allows us to verify that the damping matrix is correctly implemented and produces physically meaningful results.
for i in range(len(m_set)):
    C, freqs, modes = damping_matrix(k_set[i], m_set[i], damping_ratio=0.01)
    #print(f"Case {i+1}:")
    #print("Frequencies (Hz):", np.round(freqs, 2))
    #print("Damping matrix shape:", C.shape)
    #print("C symmetric:", np.allclose(C, C.T))
    #print()
    c_consistent.append(C)
    freq_consistent.append(freqs)
    mode_consistent.append(modes)


c_lumped = []
freq_lumped = []
mode_lumped = []

# Compute damping matrices for consistent mass cases 
for i in range(len(k_set)):
    C, freqs, modes = damping_matrix(k_set[i], m_lumped_13, damping_ratio=0.01)
    #print(f"Case {i+1}:")
    #print("Frequencies (Hz):", np.round(freqs, 2))
    #print("Damping matrix shape:", C.shape)
    #print("C symmetric:", np.allclose(C, C.T))
    #print()
    c_lumped.append(C)
    freq_lumped.append(freqs)
    mode_lumped.append(modes)




#STRESS TEST: Simulate Free Vibration of an Isolated Mode: Testing Case 1 (Undamaged, Consistent Mass)
case_idx = 0  # Uses the first undamaged case from dataset
mode_to_test = 0 
n_dof = 12 #(x,y,z for each of the 4 floors)
zeta = 0.01 # Damping Ratio of 1% for the test case, which is typical for masonry buildings and allows us to verify that the damping matrix produces a physically meaningful response.

#Matrices for the case 1 
Phi = mode_consistent[case_idx] # Mode shapes for the consistent mass case 1
Cd = c_consistent[case_idx]
M = m_set[case_idx]
K = k_set[case_idx] * 1e6  # Scale MN/m to N/m to match Cd's physical units!

# Convert the Hz frequencies back to rad/s 
omega_n = freq_consistent[case_idx] * 2 * np.pi  

# 2. Initial Conditions: Displace exactly in the shape of Mode 1
x0 = Phi[:, mode_to_test]  # Initial displacement is the entire row 1 of the mode shape matrix, which corresponds to the first mode shape. This means we are exciting only the first mode, which allows us to verify that the damping matrix correctly produces a response that decays according to the 1% damping envelope for that specific mode.
v0 = np.zeros(n_dof) # All degrees of freedom start at rest, so initial velocity is zero

# 3. State-space formulation for numerical integration
M_inv = la.inv(M)

# Defines the system of first-order ODEs for the state vector z = [x; v], where x is displacement and v is velocity. The function returns the time derivative of the state vector, which includes the velocity (dx/dt = v) and the acceleration (dv/dt = M^-1 * (-C * v - K * x)).
def system_dynamics(t, z):
    x = z[:n_dof] # Extracts the displacement components from the state vector
    v = z[n_dof:] # Extracts the velocity components from the state vector
    dxdt = v # The time derivative of displacement is velocity
    dvdt = -M_inv @ (Cd @ v + K @ x) # Rearranged the equation of motio. CD is the damping force which is proportional to velocity, and K is the stiffness force which is proportional to displacement. The negative sign indicates that these forces oppose the motion. M_inv is used to convert the force into acceleration. 
    return np.concatenate((dxdt, dvdt)) #Returns the full state derivative with both dispplacement and velocity

# Time span for simulation (10 seconds)
t_span = (0, 10) 
t_eval = np.linspace(t_span[0], t_span[1], 2000) # Request solution at 2000 evenly spaced time points 
z0 = np.concatenate((x0, v0))

# Solve the initial value problem
# Solves the ODE using 4th/5th order Runge-Kutta Method (RK45)
sol = solve_ivp(system_dynamics, t_span, z0, t_eval=t_eval, method='RK45')

# 4. Verification: Compare response of DOF 1 to the theoretical envelope
time = sol.t # Time points at which the solution was evaluated
dof_to_plot = 7 # Plot the response of the 8th DOF (index 7) which corresponds to the first mode shape's contribution to that DOF. This allows us to verify that the damping matrix correctly produces a response that decays according to the 1% damping envelope for that specific mode.
x_response = sol.y[dof_to_plot, :] 

# Scale the envelope by the initial amplitude of THAT specific DOF

initial_amp = x0[dof_to_plot] # Extracts the initial displacement 
envelope_upper = initial_amp * np.exp(-zeta * omega_n[mode_to_test] * time) #For damping free vibration x = A * exp(-zeta * omega_n * t) * cos(omega_d * t + phi), where A is the initial amplitude, zeta is the damping ratio, omega_n is the natural frequency, and t is time. The envelope of the response is given by A * exp(-zeta * omega_n * t), which represents the exponential decay of the amplitude over time due to damping. By plotting this envelope alongside the simulated response, we can visually verify that the damping matrix produces a response that decays according to the expected 1% damping behavior for that specific mode.
envelope_lower = -initial_amp * np.exp(-zeta * omega_n[mode_to_test] * time)

# 5. Plot the results
plt.figure(figsize=(10, 5))
plt.plot(time, x_response, label=f'Simulated Response (DOF {dof_to_plot+1}, Mode {mode_to_test+1})', color='black')
plt.plot(time, envelope_lower, 'r--', linewidth=2)
plt.plot(time, envelope_upper, 'r--', label='1% Damping Envelope', linewidth=2)
plt.title(f'Verification of 1% Damping Matrix (Case {case_idx+1}, Mode {mode_to_test+1} Isolation)')
plt.xlabel('Time [s]')
plt.ylabel('Displacement [m]')
plt.legend()
plt.grid(True)
plt.show()
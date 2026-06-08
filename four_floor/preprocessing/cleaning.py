import numpy as np
from scipy.signal import butter, sosfiltfilt, detrend
import matplotlib.pyplot as plt
from scipy.signal import welch

def sanitize_accelerometer_data(raw_data, fs=1000.0, low_cut=0.5, high_cut=45.0, order=6):
    """
    Cleans raw field accelerometer data by removing baseline drift and electrical noise.
    Parameters:
    raw_data : numpy array (1D or 2D). If 2D, expects shape (n_sensors, n_samples)
    fs       : Sampling frequency in Hz
    low_cut  : High-pass cutoff to remove thermal/sensor drift (Hz)
    high_cut : Low-pass cutoff to remove electrical grid hum (50/60 Hz)
    order    : Filter roll-off steepness
    
    Returns:
    clean_data : The sanitized zero-phase array ready for PSD extraction
    """
    
    # Removes the slow baseline drift
    detrended_data = detrend(raw_data, type='linear', axis=-1)
    
    # Removes the noise
    # We use Second-Order Sections (sos) because standard 'b, a' polynomials become highly numerically unstable at 6th order with high sampling rates.
    nyquist = 0.5 * fs
    low = low_cut / nyquist
    high = high_cut / nyquist
    
    sos = butter(order, [low, high], btype='bandpass', output='sos')
    
    # sosfiltfilt applies the filter forward, then backward. 
    # This perfectly cancels out phase shift, keeping your time-domain peaks exactly where they belong.
    clean_data = sosfiltfilt(sos, detrended_data, axis=-1)
    
    return clean_data

# ---------------------------------------------------------
#TEST
# ---------------------------------------------------------
if __name__ == "__main__":
    #Simulate 40 seconds of Corrupted Field Data
    fs = 1000.0
    dt = 1.0 / fs
    time = np.arange(0, 40.0, dt)
    
    # The Physics: Two real structural resonances at 9.41 Hz and 25.60 Hz
    true_signal = np.sin(2 * np.pi * 9.41 * time) + 0.5 * np.sin(2 * np.pi * 25.60 * time)
    
    # The Corruption: 
    # - Massive slow thermal drift (0.05 Hz)
    # - Sharp electrical grid hum (50.0 Hz)
    # - General high-frequency sensor static (white noise)
    thermal_drift = 5.0 * np.sin(2 * np.pi * 0.05 * time) 
    electrical_hum = 2.0 * np.sin(2 * np.pi * 50.0 * time)
    static_noise = np.random.randn(len(time)) * 0.5
    
    corrupted_signal = true_signal + thermal_drift + electrical_hum + static_noise
    
    # 2. Run the Sanitization Pipeline
    clean_signal = sanitize_accelerometer_data(corrupted_signal, fs=fs)
    
    # 3. Prove it with a PSD Plot
    freqs_bad, psd_bad = welch(corrupted_signal, fs=fs, nperseg=2048)
    freqs_clean, psd_clean = welch(clean_signal, fs=fs, nperseg=2048)
    
    plt.figure(figsize=(12, 6))
    
    # Plot the raw, corrupted data
    plt.semilogy(freqs_bad, psd_bad, color='red', alpha=0.5, label='Raw Field Data (Corrupted)')
    
    # Plot the sanitized data
    plt.semilogy(freqs_clean, psd_clean, color='black', linewidth=2, label='Sanitized Data (PINN Ready)')
    
    plt.title("Sanitization Pipeline: Stripping Drift and Electrical Hum")
    plt.xlabel("Frequency [Hz]")
    plt.ylabel("PSD")
    plt.xlim(0, 60)
    plt.ylim(1e-4, 1e2)
    
    # Annotate the specific corruptions we killed
    plt.axvline(x=50.0, color='gray', linestyle='--', alpha=0.5)
    plt.text(50.5, 1e1, '50 Hz Electrical Grid Hum', color='gray', rotation=90)
    
    plt.grid(True, which="both", ls="--", alpha=0.5)
    plt.legend()
    plt.tight_layout()
    plt.show()
    
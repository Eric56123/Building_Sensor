import time
import numpy as np
import torch
from scipy.signal import welch
from four_floor.pinn.pinn_model import SHM_PINN
# Assuming you use an MPU6050 or similar accelerometer via a library
# from smbus2 import SMBus 

# ---------------------------------------------------------
# 1. LOAD PRE-TRAINED WEIGHTS
# ---------------------------------------------------------
DEVICE = torch.device("cpu") # Microcontrollers usually lack GPUs
MODEL = SHM_PINN(n_frequency_bins=1025).to(DEVICE)
MODEL.load_state_dict(torch.load("shm_pinn_weights.pth", map_location=DEVICE))
MODEL.eval()

def read_accelerometer_channels():
    """
    Mock-up: In a real building, this function reads 
    4 sensors via I2C/SPI and returns [4, 4000] array.
    """
    # Replace with your actual sensor driver code
    return np.random.normal(0, 0.1, (4, 4000))

def process_and_alert():
    print("Monitoring Started... [CTRL+C to Stop]")
    
    while True:
        # A. DATA ACQUISITION
        raw_data = read_accelerometer_channels()
        
        # B. SIGNAL PROCESSING (DSP)
        # 1. Zero-center the data (Remove Gravity)
        clean_data = raw_data - np.mean(raw_data, axis=1, keepdims=True)
        
        # 2. Domain Transform (FFT / Welch)
        _, psd = welch(clean_data, fs=1000.0, nperseg=2048, axis=-1)
        
        # 3. Normalization (Must match your 'Calibration' fix)
        psd_log = np.log10(psd + 1e-10)
        psd_norm = (psd_log - (-10.00)) / (-2.09 - (-10.00))
        psd_norm = np.clip(psd_norm, 0, 1)
        
        # C. AI INFERENCE
        psd_tensor = torch.tensor(psd_norm, dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            alphas = MODEL(psd_tensor).numpy()[0]
        
        # D. DECISION LOGIC
        damage_indices = (1.0 - alphas) * 10
        global_di = np.max(damage_indices)
        
        # E. PHYSICAL OUTPUT (The Light)
        if global_di < 1.5:
            set_led("GREEN")
            status = "HEALTHY"
        elif global_di < 4.0:
            set_led("YELLOW")
            status = "WARNING"
        else:
            set_led("RED")
            status = "CRITICAL"
            
        print(f"Status: {status} | Max DI: {global_di:.2f}")
        
        # Wait for the next window of data (e.g., 5 seconds)
        time.sleep(5)

def set_led(color):
    """
    Pseudo-code for GPIO control
    e.g., GPIO.output(RED_PIN, GPIO.HIGH)
    """
    pass

if __name__ == "__main__":
    process_and_alert()
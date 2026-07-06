"""
main.py — PINN Structural Health Monitor
=========================================
Run from Building_Sensor/four_floor/:
    python3 main.py            # simulation mode (no hardware needed)
    python3 main.py --live     # live mode (requires ADXL355 + DS3231 wired up)

Data is saved to logs/shm_log_YYYYMMDD_HHMMSS.csv each run.
"""

import sys
import csv
import time
import argparse
from pathlib import Path
from datetime import datetime

import numpy as np
import torch
from scipy.signal import welch

from pinn.pinn_model import SHM_PINN


# ── Arguments ──────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--live", action="store_true",
                    help="Use real hardware (ADXL355 + DS3231)")
args = parser.parse_args()
LIVE = args.live


# ── Configuration ──────────────────────────────────────────────────────────────
WEIGHTS_PATH = Path(__file__).parent / "shm_pinn_weights.pth"
LOG_DIR      = Path(__file__).parent / "logs"

FS          = 1000
N_SAMPLES   = 4000
NPERSEG     = 2048
N_FREQ_BINS = NPERSEG // 2 + 1   # 1025

NORM_MIN = -10.00
NORM_MAX =  -2.09

DI_WARN     = 1.5
DI_CRITICAL = 4.0

GREEN = (0,   255, 0)
AMBER = (255, 165, 0)
RED   = (255, 0,   0)
BLUE  = (0,   0,   255)

REG_POWER_CTL = 0x2D
REG_FILTER    = 0x28
ODR_1000HZ    = 0x02


# ── LED ────────────────────────────────────────────────────────────────────────
LED_AVAILABLE = False
try:
    import board
    import neopixel
    pixel = neopixel.NeoPixel(board.D18, 1, brightness=0.4)
    LED_AVAILABLE = True
    print("LED: neopixel OK")
except Exception as e:
    print(f"LED: unavailable ({type(e).__name__}). Terminal output only.")


def set_led(colour: tuple) -> None:
    if not LED_AVAILABLE:
        return
    try:
        pixel[0] = colour
        pixel.show()
    except Exception:
        pass


# ── CSV logging setup ──────────────────────────────────────────────────────────
LOG_DIR.mkdir(exist_ok=True)
run_start  = datetime.now().strftime("%Y%m%d_%H%M%S")
log_path   = LOG_DIR / f"shm_log_{run_start}.csv"

CSV_HEADER = [
    "timestamp", "mode", "status",
    "global_DI",
    "alpha_1", "alpha_2", "alpha_3", "alpha_4",
    "DI_1", "DI_2", "DI_3", "DI_4",
]

log_file   = open(log_path, "w", newline="")
csv_writer = csv.writer(log_file)
csv_writer.writerow(CSV_HEADER)
log_file.flush()
print(f"Logging to: {log_path}")


def log_row(timestamp, status, global_di, alphas, dis):
    row = [
        timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "LIVE" if LIVE else "SIM",
        status,
        f"{global_di:.4f}",
        f"{alphas[0]:.4f}", f"{alphas[1]:.4f}",
        f"{alphas[2]:.4f}", f"{alphas[3]:.4f}",
        f"{dis[0]:.4f}", f"{dis[1]:.4f}",
        f"{dis[2]:.4f}", f"{dis[3]:.4f}",
    ]
    csv_writer.writerow(row)
    log_file.flush()   # write immediately so data isn't lost on Ctrl+C


# ── Hardware or simulation ─────────────────────────────────────────────────────
print("=" * 60)
print(f"PINN Structural Health Monitor  "
      f"[{'LIVE' if LIVE else 'SIMULATION'} MODE]")
print("=" * 60)

if LIVE:
    from sensor_driver import ADXL355, DS3231, collect_window

    print("\n[1] Initialising ADXL355...")
    accel = ADXL355(bus=0, device=0, speed_hz=1_000_000)
    accel._write(REG_POWER_CTL, 0x01)
    accel._write(REG_FILTER,    ODR_1000HZ)
    accel._write(REG_POWER_CTL, 0x00)
    time.sleep(0.1)
    print("    ODR set to 1000 Hz")

    print("[2] Initialising DS3231 RTC...")
    rtc = DS3231(bus=1)
    try:
        rtc.sync_to_system_time()
    except Exception:
        print("    Warning: RTC sync skipped.")

    def get_window():
        return collect_window(accel, n_samples=N_SAMPLES,
                              sample_rate=FS, axis="z")

    def get_timestamp():
        return rtc.get_datetime()

    def close_hardware():
        accel.close()
        rtc.close()

else:
    print("\nSimulation mode — synthetic building vibration data.")
    print("Run with --live once hardware is connected.\n")

    def get_window():
        t = np.linspace(0, N_SAMPLES / FS, N_SAMPLES)
        signal = (0.002 * np.sin(2 * np.pi * 2.0 * t) +
                  0.001 * np.sin(2 * np.pi * 5.0 * t) +
                  0.0005 * np.sin(2 * np.pi * 8.5 * t) +
                  np.random.normal(0, 0.0003, N_SAMPLES))
        return signal

    def get_timestamp():
        return datetime.now()

    def close_hardware():
        pass


# ── Load PINN ──────────────────────────────────────────────────────────────────
step = 3 if LIVE else 1
print(f"[{step}] Loading SHM_PINN from {WEIGHTS_PATH.name}...")
if not WEIGHTS_PATH.exists():
    raise FileNotFoundError(
        f"\nWeights file not found: {WEIGHTS_PATH}\n"
        "Copy from your Mac:\n"
        "  scp /path/to/shm_pinn_weights.pth "
        "eric56123@sensor.local:~/Building_Sensor/four_floor/"
    )

model = SHM_PINN(n_frequency_bins=N_FREQ_BINS)
model.load_state_dict(torch.load(str(WEIGHTS_PATH), map_location="cpu"))
model.eval()
print(f"    Loaded — {sum(p.numel() for p in model.parameters()):,} parameters")

set_led(BLUE)


# ── Preprocessing ──────────────────────────────────────────────────────────────
def preprocess(signal: np.ndarray) -> np.ndarray:
    signal   = signal - signal.mean()
    _, psd   = welch(signal, fs=FS, nperseg=NPERSEG)
    psd_log  = np.log10(psd + 1e-10)
    psd_norm = (psd_log - NORM_MIN) / (NORM_MAX - NORM_MIN)
    return np.clip(psd_norm, 0, 1).astype(np.float32)


# ── Classification ─────────────────────────────────────────────────────────────
def classify(alphas: np.ndarray) -> tuple:
    dis       = (1.0 - alphas) * 10
    global_di = float(np.max(dis))
    if global_di < DI_WARN:
        return GREEN, "HEALTHY",  global_di, dis
    elif global_di < DI_CRITICAL:
        return AMBER, "WARNING",  global_di, dis
    else:
        return RED,   "CRITICAL", global_di, dis


# ── Main loop ──────────────────────────────────────────────────────────────────
print("\nRunning — press Ctrl+C to stop.\n")
print(f"{'Timestamp':<22} {'Status':<10} {'Max DI':<8} "
      f"{'a1':<8} {'a2':<8} {'a3':<8} {'a4':<8}")
print("-" * 72)

try:
    while True:
        t0 = time.time()

        window    = get_window()
        timestamp = get_timestamp()
        features  = preprocess(window)

        x4       = np.stack([features] * 4, axis=0)
        x_tensor = torch.tensor(x4).unsqueeze(0)

        with torch.no_grad():
            alphas = model(x_tensor).numpy()[0]

        colour, status, global_di, dis = classify(alphas)
        set_led(colour)

        # Print to terminal
        ts = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        print(f"{ts}  {status:<10} {global_di:<8.2f} "
              f"{alphas[0]:<8.4f} {alphas[1]:<8.4f} "
              f"{alphas[2]:<8.4f} {alphas[3]:<8.4f}")

        # Save to CSV
        log_row(timestamp, status, global_di, alphas, dis)

        elapsed = time.time() - t0
        if elapsed < 5.0:
            time.sleep(5.0 - elapsed)

except KeyboardInterrupt:
    print("\nStopping.")

finally:
    set_led((0, 0, 0))
    log_file.close()
    close_hardware()
    print(f"Data saved to: {log_path}")
    print("Done.")
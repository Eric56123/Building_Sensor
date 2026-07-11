"""
config.py — Shared configuration for the Raspberry Pi SHM deployment
======================================================================
Single source of truth for hardware, model and signal-processing
constants. Every other module imports from here instead of
redefining these values, so a change (e.g. a new calibration
constant after retraining) only has to be made once.
"""

from pathlib import Path

# ── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).parent
WEIGHTS_PATH = BASE_DIR / "shm_pinn_weights.pth"
LOG_DIR      = BASE_DIR / "logs"
RUN_INDEX_CSV = LOG_DIR / "run_index.csv"   # mirrors "6. Data Recording" sheet

# ── Building geometry ───────────────────────────────────────────────────────
MAX_FLOORS = 4   # SHM_PINN is trained with a fixed 4-channel input;
                 # experiments may use fewer physical floors, never more.

# ── Sensor / acquisition ────────────────────────────────────────────────────
FS          = 1000     # sample rate (Hz)
N_SAMPLES   = 4000      # samples per acquisition window (4 s @ 1000 Hz)
NPERSEG     = 2048      # Welch PSD segment length
N_FREQ_BINS = NPERSEG // 2 + 1   # 1025 — must match SHM_PINN(n_frequency_bins=...)

# PSD normalisation constants (fit during training — do not change without
# retraining, or model outputs will be meaningless)
NORM_MIN = -10.00
NORM_MAX = -2.09

# ADXL345 (I2C) register map (see sensor.py)
ADXL345_I2C_ADDR = 0x53   # 0x1D if the SDO/ALT-ADDRESS pin is tied high instead of low/GND
ADXL345_I2C_BUS   = 3     # a SEPARATE I2C bus from the DS3231 (which is on bus 1) — this
                          # rig has the ADXL345 wired to a second I2C interface (e.g. a
                          # dtoverlay=i2c3 on different GPIO pins), confirmed via
                          # `i2cdetect -y 3` showing 0x53. Check `dtoverlay` in
                          # /boot/firmware/config.txt if this ever needs re-confirming.

DS3231_I2C_BUS = 1   # confirmed separately — DS3231 is on the Pi's default I2C1

REG_DEVID       = 0x00   # should read 0xE5
REG_BW_RATE     = 0x2C   # output data rate / power mode
REG_POWER_CTL   = 0x2D   # measurement mode
REG_DATA_FORMAT = 0x31   # resolution + g-range
REG_DATAX0      = 0x32   # first of 6 data bytes (X0,X1,Y0,Y1,Z0,Z1), 16-bit little-endian per axis

POWER_CTL_MEASURE   = 0x08   # POWER_CTL: bit3 set = measurement mode (0x00 = standby)
DATA_FORMAT_FULL_RES_2G = 0x08   # full-resolution mode, +/-2 g range
BW_RATE_1600HZ = 0x0E   # closest standard ODR above config.FS=1000 Hz (ADXL345 has no
                        # exact 1000 Hz option — see sensor.py for why 1600 Hz was picked)

# Scale factor in full-resolution mode is fixed at ~3.9 mg/LSB regardless of g-range
ADXL345_SCALE = 3.9e-3   # g per LSB

# ── Classification thresholds (from Experiment Log "7. Success Criteria") ──
DI_WARN     = 1.5   # DI < this           -> HEALTHY  (Green)
DI_CRITICAL = 4.0   # this <= DI < below  -> WARNING  (Amber); >= -> CRITICAL (Red)

GREEN = (0,   255, 0)
AMBER = (255, 165, 0)
RED   = (255, 0,   0)
BLUE  = (0,   0,   255)   # "initialising" status colour

# ── Experiment defaults (from Experiment Log "3. Excitation Params") ───────
DEFAULT_RUN_DURATION_S = 60
INFERENCE_PERIOD_S     = 5   # how often a window is captured + classified

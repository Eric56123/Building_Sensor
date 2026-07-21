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
REG_INT_SOURCE  = 0x30   # bit1 = watermark, bit0 = FIFO overrun (read-to-clear)
REG_POWER_CTL   = 0x2D   # measurement mode
REG_DATA_FORMAT = 0x31   # resolution + g-range
REG_DATAX0      = 0x32   # first of 6 data bytes (X0,X1,Y0,Y1,Z0,Z1), 16-bit little-endian per axis
REG_FIFO_CTL    = 0x38   # FIFO mode (bits7:6) + watermark samples (bits4:0)
REG_FIFO_STATUS = 0x39   # bits5:0 = number of entries currently in the FIFO (0..32)

POWER_CTL_MEASURE   = 0x08   # POWER_CTL: bit3 set = measurement mode (0x00 = standby)
DATA_FORMAT_FULL_RES_2G = 0x08   # full-resolution mode, +/-2 g range (legacy name)

# ── Measurement range ───────────────────────────────────────────────────────
# DATA_FORMAT bits1:0 select the g-range; bit3 (FULL_RES) is set regardless.
#
# In FULL_RES mode the ADXL345 keeps a CONSTANT ~3.9 mg/LSB scale factor at every
# range, adding bits instead of coarsening the step (10-bit at +/-2 g up to 13-bit
# at +/-16 g). Widening the range therefore costs nothing in resolution or noise —
# it is pure headroom.
#
# This matters because the rig clipped at +/-2 g: driven through resonance at only
# a moderate amplifier setting, both the 2.9 Hz and 8.0 Hz peaks hit the rail
# (109 and 203 samples respectively). Clipped peaks are flattened, spawn harmonics
# that look like extra modes, and corrupt every amplitude and damping estimate.
G_RANGE_CODES = {2: 0x00, 4: 0x01, 8: 0x02, 16: 0x03}
G_RANGE = 16     # full-scale range in g
DATA_FORMAT = 0x08 | G_RANGE_CODES[G_RANGE]   # FULL_RES + range bits
BW_RATE_1600HZ = 0x0E   # closest standard ODR above config.FS=1000 Hz (ADXL345 has no
                        # exact 1000 Hz option — see sensor.py for why 1600 Hz was picked)

# ADXL345 BW_RATE codes -> output data rate. sensor.py looks the register value up
# from ODR_HZ through this table rather than writing a fixed constant, so changing
# ODR_HZ alone cannot leave the sensor running at a different rate than the code
# believes — a desync that would silently corrupt every sample interval.
BW_RATE_CODES = {
    3200: 0x0F, 1600: 0x0E, 800: 0x0D, 400: 0x0C,
    200:  0x0B, 100:  0x0A,  50: 0x09,
}

# ── FIFO acquisition (hardware-timed) ───────────────────────────────────────
# The ADXL345 samples internally at its ODR from its own clock and buffers the
# results in a 32-deep FIFO. Reading the FIFO decouples sample TIMING from Linux
# scheduling: inter-sample spacing is exactly 1/ODR regardless of when we drain.
FIFO_MODE_BYPASS = 0x00   # FIFO disabled (old per-sample polling path)
FIFO_MODE_STREAM = 0x80   # bits7:6 = 10 -> Stream: newest sample overwrites oldest on overrun
FIFO_DEPTH       = 32     # hardware FIFO size (samples)

# The ODR the sensor actually runs at when FIFO acquisition is used. The ADXL345
# has no 1000 Hz ODR, so we run it at 1600 Hz (BW_RATE_1600HZ, internal
# anti-alias bandwidth = ODR/2 = 800 Hz) and resample the captured block down to
# exactly FS (1000 Hz) so the model's fs=1000 / welch contract is preserved
# WITHOUT retraining. Change ODR_HZ + the BW_RATE code together if you ever want
# the sensor's internal low-pass to pre-filter harder (e.g. 400 Hz ODR -> 200 Hz
# bandwidth) — that is a stronger analogue anti-alias for the 0–15 Hz band.
ODR_HZ = 1600

# Scale factor in full-resolution mode is nominally ~3.9 mg/LSB (256 LSB/g)
# regardless of g-range. Parts vary, though, and clone breakouts vary a lot: this
# rig's sensor measured 209.5 LSB/g (4.77 mg/LSB), ~18% low, with FULL_RES set,
# offset trims at zero and DEVID reading 0xE5 — i.e. correctly configured and
# genuinely out of spec. A wrong scale silently rescales every amplitude, and so
# every PSD magnitude and the NORM_MIN/MAX bounds derived from them.
# Re-measure with:  python3 check_axis.py --calibrate-scale
#
# MEASURED 2026-07-21 on this part, replacing the 3.9e-3 datasheet nominal.
# Gravity used as a 1 g reference: |total| read 0.8167 g at the old value, i.e.
# 209.4 LSB/g against the datasheet's 256. Verified identical at +/-2 g and
# +/-16 g (211.1 vs 211.0 LSB/g), and cross-checked against a raw-register probe
# (209.5 LSB/g) through a separate code path.
#
# Everything recorded BEFORE this change is 82% of true amplitude. Frequencies
# are unaffected — they depend on sample timing, not on this factor — so the
# 2026-07-21 modal results stand. But PSD magnitudes shift by 1/0.8167 = 1.224,
# so config.NORM_MIN/MAX must come from a retrain, and any DI threshold
# calibrated under the old scale no longer applies.
ADXL345_SCALE = 0.00477503   # g per LSB, measured on this part

# ── Recorded axis ──────────────────────────────────────────────────────────
# The single accelerometer axis monitor.py logs and the PINN consumes. The table
# shakes HORIZONTALLY, so this MUST be a horizontal axis (~0 g at rest); if it is
# the vertical one (~1 g at rest) you are recording gravity, not excitation.
# Static gravity proves an axis is horizontal but cannot tell the two horizontal
# axes apart — use `check_axis.py --shake` to pick the one that actually moves.
# monitor.py and check_axis.py both read this, so it is the only place to change.
# Measured 2026-07-21 with check_axis.py: static gravity put z at 0.998 of the
# gravity vector (vertical — it had been recording gravity, not excitation),
# leaving x and y horizontal. The shake test then separated the two: driving the
# table gave motion std y=0.1129 g vs x=0.0249 g and z=0.0199 g, so y is the
# direction the table actually moves in.
RECORDED_AXIS = "y"

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

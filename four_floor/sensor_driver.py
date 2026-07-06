"""
sensor_driver.py
================
Data acquisition and preprocessing for the PINN seismic sensor.

Components:
  - ADXL355BEZ accelerometer (SPI0, GPIO 10/9/11/8)
  - DS3231M real-time clock (I2C1, GPIO 2/3)

Pipeline:
  1. Collect a window of Z-axis acceleration samples at 500 Hz
  2. Timestamp the measurement via the RTC
  3. Detrend, window, and FFT the signal
  4. Extract the structural frequency range (0–15 Hz, 128 bins)
  5. Normalise for PINN input

Usage:
  from sensor_driver import ADXL355, DS3231, collect_window, preprocess_for_pinn
"""

import time
import numpy as np
import spidev
import smbus2
from datetime import datetime
from scipy.signal import resample


# ─────────────────────────────────────────────
#  ADXL355 register map
# ─────────────────────────────────────────────
REG_DEVID_AD   = 0x00   # Should return 0xAD
REG_POWER_CTL  = 0x2D   # 0x01 = standby, 0x00 = measurement
REG_FILTER     = 0x28   # ODR and HPF settings
REG_RANGE      = 0x2C   # Measurement range
REG_XDATA3     = 0x08   # First data register (X MSB)

# Scale factor for ±2 g range: 3.9 µg per LSB
SCALE_2G = 3.9e-6


# ─────────────────────────────────────────────
#  ADXL355 driver
# ─────────────────────────────────────────────
class ADXL355:
    """
    SPI driver for the ADXL355 3-axis MEMS accelerometer.
    Communicates via SPI0 on the Raspberry Pi 4.
    SPI mode 0 (CPOL=0, CPHA=0) as specified in the datasheet.
    """

    def __init__(self, bus: int = 0, device: int = 0, speed_hz: int = 1_000_000):
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.max_speed_hz = speed_hz
        self.spi.mode = 0b00          # Mode 0: CPOL=0, CPHA=0 (ADXL355 datasheet p.28)
        self.scale = SCALE_2G
        self._initialise()

    def _read(self, reg: int, n_bytes: int = 1) -> list:
        """Read n_bytes from register. Address byte = (reg << 1) | 1 for read."""
        response = self.spi.xfer2([reg << 1 | 0x01] + [0x00] * n_bytes)
        return response[1:]

    def _write(self, reg: int, value: int) -> None:
        """Write a single byte to register. Address byte = (reg << 1) | 0 for write."""
        self.spi.xfer2([reg << 1 | 0x00, value])

    def _initialise(self) -> None:
        """Verify device ID, configure ODR, and enter measurement mode."""
        dev_id = self._read(REG_DEVID_AD)[0]
        if dev_id != 0xAD:
            raise RuntimeError(
                f"ADXL355 not detected. Expected device ID 0xAD, got {hex(dev_id)}. "
                "Check SPI wiring and that SPI is enabled in raspi-config."
            )
        print(f"ADXL355 detected (device ID: {hex(dev_id)})")

        # ODR = 500 Hz, low-pass filter corner = 125 Hz (FILTER register 0x03)
        # This matches the PINN's expected input frequency range (0–15 Hz structural)
        self._write(REG_FILTER, 0x03)

        # Set measurement range to ±2 g (RANGE register 0x01)
        self._write(REG_RANGE, 0x01)

        # Exit standby → enter measurement mode
        self._write(REG_POWER_CTL, 0x00)
        time.sleep(0.1)   # Allow first sample to settle

    def read_xyz(self) -> tuple:
        """
        Read a single X, Y, Z sample.
        Returns acceleration in g (±2 g range).
        Each axis is 20-bit two's complement, MSB first.
        """
        raw = self._read(REG_XDATA3, 9)

        # Reconstruct 20-bit integers (3 bytes per axis, top 20 bits used)
        x_raw = (raw[0] << 12) | (raw[1] << 4) | (raw[2] >> 4)
        y_raw = (raw[3] << 12) | (raw[4] << 4) | (raw[5] >> 4)
        z_raw = (raw[6] << 12) | (raw[7] << 4) | (raw[8] >> 4)

        # Two's complement sign extension from 20-bit to Python int
        if x_raw >= (1 << 19): x_raw -= (1 << 20)
        if y_raw >= (1 << 19): y_raw -= (1 << 20)
        if z_raw >= (1 << 19): z_raw -= (1 << 20)

        return (
            x_raw * self.scale,
            y_raw * self.scale,
            z_raw * self.scale,
        )

    def close(self) -> None:
        self.spi.close()


# ─────────────────────────────────────────────
#  DS3231 driver
# ─────────────────────────────────────────────
DS3231_I2C_ADDR = 0x68   # Fixed I2C address for DS3231

def _bcd_to_int(bcd: int) -> int:
    return (bcd >> 4) * 10 + (bcd & 0x0F)

def _int_to_bcd(n: int) -> int:
    return (n // 10 << 4) | (n % 10)


class DS3231:
    """
    I2C driver for the DS3231M real-time clock.
    Communicates via I2C1 on the Raspberry Pi 4 (GPIO 2/3).
    Used to timestamp each measurement window.
    """

    def __init__(self, bus: int = 1):
        self.bus = smbus2.SMBus(bus)
        self.addr = DS3231_I2C_ADDR

    def get_datetime(self) -> datetime:
        """Read current date and time from the RTC."""
        data = self.bus.read_i2c_block_data(self.addr, 0x00, 7)
        seconds = _bcd_to_int(data[0] & 0x7F)
        minutes = _bcd_to_int(data[1] & 0x7F)
        hours   = _bcd_to_int(data[2] & 0x3F)
        day     = _bcd_to_int(data[4] & 0x3F)
        month   = _bcd_to_int(data[5] & 0x1F)
        year    = _bcd_to_int(data[6]) + 2000
        return datetime(year, month, day, hours, minutes, seconds)

    def get_temperature_c(self) -> float:
        """Read the DS3231's onboard temperature sensor (±3°C accuracy)."""
        msb = self.bus.read_byte_data(self.addr, 0x11)
        lsb = self.bus.read_byte_data(self.addr, 0x12)
        temp = msb + (lsb >> 6) * 0.25
        if msb > 127:
            temp -= 256
        return temp

    def sync_to_system_time(self) -> None:
        """
        Set RTC from the Pi's system clock.
        Run this once after booting with internet access so the RTC
        holds the correct time for offline deployments.
        """
        now = datetime.now()
        data = [
            _int_to_bcd(now.second),
            _int_to_bcd(now.minute),
            _int_to_bcd(now.hour),
            0x01,                           # day-of-week (not used)
            _int_to_bcd(now.day),
            _int_to_bcd(now.month),
            _int_to_bcd(now.year - 2000),
        ]
        self.bus.write_i2c_block_data(self.addr, 0x00, data)
        print(f"RTC synchronised to system time: {now.strftime('%Y-%m-%d %H:%M:%S')}")

    def close(self) -> None:
        self.bus.close()


# ─────────────────────────────────────────────
#  Data collection
# ─────────────────────────────────────────────
def collect_window(
    accel: ADXL355,
    n_samples: int = 256,
    sample_rate: int = 500,
    axis: str = "z",
) -> np.ndarray:
    """
    Collect a fixed-length window of acceleration samples.

    Args:
        accel:       Initialised ADXL355 instance.
        n_samples:   Number of samples per window (default 256).
        sample_rate: Target sample rate in Hz (default 500).
        axis:        Which axis to record: 'x', 'y', or 'z'.

    Returns:
        1-D NumPy array of acceleration values in g.
    """
    dt = 1.0 / sample_rate
    buffer = np.empty(n_samples)
    axis_idx = {"x": 0, "y": 1, "z": 2}[axis.lower()]

    for i in range(n_samples):
        t_start = time.perf_counter()
        sample = accel.read_xyz()[axis_idx]
        buffer[i] = sample
        # Busy-wait to maintain timing accuracy
        while time.perf_counter() - t_start < dt:
            pass

    return buffer


# ─────────────────────────────────────────────
#  Preprocessing pipeline
# ─────────────────────────────────────────────
def preprocess_for_pinn(
    signal: np.ndarray,
    sample_rate: int = 500,
    n_bins: int = 128,
    freq_max: float = 15.0,
) -> np.ndarray:
    """
    Convert a raw acceleration window into a normalised frequency-domain
    vector suitable for PINN input.

    Pipeline:
      1. Remove DC offset (detrend)
      2. Apply Hanning window (reduce spectral leakage)
      3. Compute one-sided FFT magnitude
      4. Extract structural frequency band (0–freq_max Hz)
      5. Resample to n_bins (fixed-length PINN input)
      6. Zero-mean, unit-variance normalisation

    Args:
        signal:      Raw acceleration window from collect_window().
        sample_rate: Sample rate used during collection.
        n_bins:      Number of frequency bins for PINN input (default 128).
        freq_max:    Upper frequency limit in Hz (default 15.0).

    Returns:
        Normalised 1-D NumPy array of length n_bins.
    """
    # 1. Detrend
    signal = signal - signal.mean()

    # 2. Hanning window
    signal = signal * np.hanning(len(signal))

    # 3. One-sided FFT magnitude
    fft_mag = np.abs(np.fft.rfft(signal))
    freqs   = np.fft.rfftfreq(len(signal), d=1.0 / sample_rate)

    # 4. Extract structural band
    mask = freqs <= freq_max
    fft_structural = fft_mag[mask]

    # 5. Resample to fixed length
    fft_resampled = resample(fft_structural, n_bins)

    # 6. Normalise
    mean, std = fft_resampled.mean(), fft_resampled.std()
    fft_norm = (fft_resampled - mean) / (std + 1e-8)

    return fft_norm.astype(np.float32)


# ─────────────────────────────────────────────
#  Quick hardware test
# ─────────────────────────────────────────────
def run_hardware_test():
    """
    Verifies that both sensors are wired correctly and responding.
    Run this first after connecting the hardware.
    """
    print("=" * 50)
    print("Hardware test")
    print("=" * 50)

    # Test ADXL355
    print("\n[1] ADXL355 accelerometer")
    try:
        accel = ADXL355()
        x, y, z = accel.read_xyz()
        print(f"    X = {x*1000:.2f} mg  Y = {y*1000:.2f} mg  Z = {z*1000:.2f} mg")
        print("    (Z should be close to ±1000 mg when the sensor is flat)")
        accel.close()
        print("    ADXL355 OK")
    except Exception as e:
        print(f"    ADXL355 FAILED: {e}")

    # Test DS3231
    print("\n[2] DS3231 real-time clock")
    try:
        rtc = DS3231()
        now = rtc.get_datetime()
        temp = rtc.get_temperature_c()
        print(f"    Time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"    Temperature: {temp:.2f} °C")
        rtc.close()
        print("    DS3231 OK")
    except Exception as e:
        print(f"    DS3231 FAILED: {e}")

    # Test preprocessing pipeline
    print("\n[3] Preprocessing pipeline (synthetic signal)")
    try:
        accel = ADXL355()
        print("    Collecting 256-sample window at 500 Hz (~0.5 s)...")
        window = collect_window(accel, n_samples=256, sample_rate=500)
        features = preprocess_for_pinn(window)
        print(f"    Output shape: {features.shape}  "
              f"mean={features.mean():.4f}  std={features.std():.4f}")
        accel.close()
        print("    Pipeline OK")
    except Exception as e:
        print(f"    Pipeline FAILED: {e}")

    print("\n" + "=" * 50)


if __name__ == "__main__":
    accel_sensor = None
    try:
        # Drop the speed to 50 kHz to punch through wire noise
        accel_sensor = ADXL355(bus=0, device=0, speed_hz=50_000) 
        stress_test_pipeline(accel_sensor)
    except Exception as e:
        print(f"Hardware initialization failed: {e}")
    finally:
        if accel_sensor:
            accel_sensor.close()
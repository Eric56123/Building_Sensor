"""
sensor.py — Hardware drivers for the PINN seismic sensor
==========================================================
Components:
  - ADXL345 accelerometer (I2C bus 3 on this rig — a second I2C interface,
    separate from the DS3231's bus; confirmed via i2cdetect, see config.py)
  - DS3231M real-time clock (I2C bus 1, the Pi's default I2C, GPIO 2/3)

This module only talks to hardware. Signal processing (Welch PSD,
normalisation) lives in live_features.py so the two concerns don't
drift out of sync the way they had before (see git history for the
old sensor_driver.py, which had its own — different — preprocessing
pipeline that no longer matched what the model was trained on).

Note: an earlier version of this file drove an ADXL355 over SPI —
that was based on a stale assumption in the original code. The actual
rig uses an ADXL345 over I2C (per the Experiment Log's "2. Sensor
Config" sheet), which is what's implemented here.

Usage:
    from sensor import ADXL345, DS3231, collect_window
"""

import time
import numpy as np
import smbus2
from datetime import datetime

import config


# ─────────────────────────────────────────────
#  ADXL345 driver (I2C)
# ─────────────────────────────────────────────
class ADXL345:
    """
    I2C driver for the ADXL345 3-axis MEMS accelerometer.
    On this rig it's on a separate I2C bus from the DS3231 (see config.py —
    ADXL345_I2C_BUS vs DS3231_I2C_BUS), not the Pi's default I2C1.

    ADXL345 has no exact 1000 Hz output-data-rate setting — the standard
    rate codes jump 800 Hz -> 1600 Hz -> 3200 Hz. We configure the sensor
    for 1600 Hz (comfortably above config.FS's 1000 Hz software polling
    rate in collect_window) so a fresh sample is always available when
    polled; sampling *timing* is still governed in software, not by the
    sensor's internal rate.
    """

    def __init__(self, bus: int = config.ADXL345_I2C_BUS,
                 address: int = config.ADXL345_I2C_ADDR):
        self.bus = smbus2.SMBus(bus)
        self.addr = address
        self.scale = config.ADXL345_SCALE
        self._initialise()

    def _read_byte(self, reg: int) -> int:
        return self.bus.read_byte_data(self.addr, reg)

    def _write_byte(self, reg: int, value: int) -> None:
        self.bus.write_byte_data(self.addr, reg, value)

    def _initialise(self) -> None:
        """Verify device ID, configure ODR/range, and enter measurement mode."""
        dev_id = self._read_byte(config.REG_DEVID)
        if dev_id != 0xE5:
            raise RuntimeError(
                f"ADXL345 not detected. Expected device ID 0xE5, got {hex(dev_id)}. "
                "Check I2C wiring (SDA->GPIO2/pin3, SCL->GPIO3/pin5) and that "
                "I2C is enabled in raspi-config. Also check the address — this "
                f"driver is using {hex(self.addr)}; try 0x1D if your board's "
                "SDO/ALT-ADDRESS pin is tied high instead of low/GND."
            )
        print(f"ADXL345 detected (device ID: {hex(dev_id)})")

        # Must be in standby (POWER_CTL Measure bit = 0) while changing settings
        self._write_byte(config.REG_POWER_CTL, 0x00)
        self._write_byte(config.REG_BW_RATE, config.BW_RATE_1600HZ)
        self._write_byte(config.REG_DATA_FORMAT, config.DATA_FORMAT_FULL_RES_2G)
        self._write_byte(config.REG_POWER_CTL, config.POWER_CTL_MEASURE)
        time.sleep(0.1)   # allow first sample to settle

    def read_xyz(self) -> tuple:
        """Read a single X, Y, Z sample. Returns acceleration in g."""
        raw = self.bus.read_i2c_block_data(self.addr, config.REG_DATAX0, 6)

        # Each axis: 2 bytes, little-endian, already in a 16-bit two's
        # complement field (13-bit value, sign-extended by the sensor).
        # np.uint16(...).view(np.int16) reinterprets the raw bit pattern as
        # signed — plain np.int16(value) raises OverflowError for values
        # above 32767 instead of doing that reinterpretation.
        raw_u16 = np.array([
            (raw[1] << 8) | raw[0],
            (raw[3] << 8) | raw[2],
            (raw[5] << 8) | raw[4],
        ], dtype=np.uint16)
        x, y, z = raw_u16.view(np.int16)

        return (int(x) * self.scale, int(y) * self.scale, int(z) * self.scale)

    def close(self) -> None:
        self.bus.close()


# ─────────────────────────────────────────────
#  DS3231 driver
# ─────────────────────────────────────────────
DS3231_I2C_ADDR = 0x68


def _bcd_to_int(bcd: int) -> int:
    return (bcd >> 4) * 10 + (bcd & 0x0F)


def _int_to_bcd(n: int) -> int:
    return (n // 10 << 4) | (n % 10)


class DS3231:
    """I2C driver for the DS3231M real-time clock (timestamps each window)."""

    def __init__(self, bus: int = config.DS3231_I2C_BUS):
        self.bus = smbus2.SMBus(bus)
        self.addr = DS3231_I2C_ADDR

    def get_datetime(self) -> datetime:
        data = self.bus.read_i2c_block_data(self.addr, 0x00, 7)
        seconds = _bcd_to_int(data[0] & 0x7F)
        minutes = _bcd_to_int(data[1] & 0x7F)
        hours   = _bcd_to_int(data[2] & 0x3F)
        day     = _bcd_to_int(data[4] & 0x3F)
        month   = _bcd_to_int(data[5] & 0x1F)
        year    = _bcd_to_int(data[6]) + 2000
        return datetime(year, month, day, hours, minutes, seconds)

    def get_temperature_c(self) -> float:
        msb = self.bus.read_byte_data(self.addr, 0x11)
        lsb = self.bus.read_byte_data(self.addr, 0x12)
        temp = msb + (lsb >> 6) * 0.25
        if msb > 127:
            temp -= 256
        return temp

    def sync_to_system_time(self) -> None:
        """Set RTC from the Pi's system clock (run once with internet access)."""
        now = datetime.now()
        data = [
            _int_to_bcd(now.second),
            _int_to_bcd(now.minute),
            _int_to_bcd(now.hour),
            0x01,
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
    accel: ADXL345,
    n_samples: int = config.N_SAMPLES,
    sample_rate: int = config.FS,
    axis: str = "z",
) -> np.ndarray:
    """
    Collect a fixed-length window of acceleration samples.

    Args:
        accel:       Initialised ADXL345 instance.
        n_samples:   Number of samples per window.
        sample_rate: Target sample rate in Hz.
        axis:        Which axis to record: 'x', 'y', or 'z'.

    Returns:
        1-D NumPy array of acceleration values in g.

    Note: this busy-waits to hit `sample_rate` in software. I2C reads are
    slower than the SPI reads this code originally assumed — if a single
    read_xyz() call takes longer than 1/sample_rate, the achieved rate will
    silently fall below the target. Worth verifying empirically (e.g. time
    collect_window() for a known n_samples) if this matters for your welch()
    frequency resolution.
    """
    dt = 1.0 / sample_rate
    buffer = np.empty(n_samples)
    axis_idx = {"x": 0, "y": 1, "z": 2}[axis.lower()]

    for i in range(n_samples):
        t_start = time.perf_counter()
        buffer[i] = accel.read_xyz()[axis_idx]
        while time.perf_counter() - t_start < dt:   # busy-wait for timing accuracy
            pass

    return buffer

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

import math
import time
from datetime import datetime
from fractions import Fraction

import numpy as np
import smbus2
from scipy.signal import resample_poly

import config


# ─────────────────────────────────────────────
#  ADXL345 driver (I2C)
# ─────────────────────────────────────────────
class ADXL345:
    """
    I2C driver for the ADXL345 3-axis MEMS accelerometer.
    On this rig it's on a separate I2C bus from the DS3231 (see config.py —
    ADXL345_I2C_BUS vs DS3231_I2C_BUS), not the Pi's default I2C1.

    ACQUISITION TIMING (this is the important part)
    -----------------------------------------------
    The ADXL345 samples internally at its ODR from its OWN clock and stores each
    sample in a 32-deep hardware FIFO. This driver runs the sensor at 1600 Hz
    (config.ODR_HZ; the ADXL345 has no exact 1000 Hz code — the ladder is
    800 -> 1600 -> 3200) in *Stream* FIFO mode and reads whole blocks out of the
    FIFO. Because the sensor timestamps samples on its own clock, the
    inter-sample interval is exactly 1/ODR no matter how irregularly Linux lets
    us drain the buffer. That is the fix for the old software busy-wait, whose
    achieved rate and jitter were at the mercy of the scheduler and the I2C
    transaction time (see measure_sampling_rate.py).

    read_xyz() (single-shot, non-FIFO) is retained for device checks and the
    self-test; the streaming path used by collect_window() is read_fifo_block().
    """

    def __init__(self, bus: int = config.ADXL345_I2C_BUS,
                 address: int = config.ADXL345_I2C_ADDR):
        self.bus = smbus2.SMBus(bus)
        self.addr = address
        self.scale = config.ADXL345_SCALE
        self.odr_hz = config.ODR_HZ
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
        # Derive the rate code from ODR_HZ instead of writing a fixed constant.
        # Hardcoding BW_RATE_1600HZ here meant changing config.ODR_HZ left the
        # sensor still running at 1600 Hz while collect_window resampled as though
        # it were the new rate — a silent, uniform error in every sample interval.
        try:
            bw_code = config.BW_RATE_CODES[config.ODR_HZ]
        except KeyError:
            raise ValueError(
                f"config.ODR_HZ = {config.ODR_HZ} is not an ADXL345 output data "
                f"rate. Valid: {sorted(config.BW_RATE_CODES)}"
            )
        self._write_byte(config.REG_BW_RATE, bw_code)
        self._write_byte(config.REG_DATA_FORMAT, config.DATA_FORMAT)
        # Enable Stream-mode FIFO so samples are buffered at the hardware ODR.
        # (FIFO_CTL must be set while in/after entering measurement is fine; the
        #  FIFO only actually runs once Measure is on, which we do next.)
        self._write_byte(config.REG_FIFO_CTL, config.FIFO_MODE_STREAM)
        self._write_byte(config.REG_POWER_CTL, config.POWER_CTL_MEASURE)
        time.sleep(0.1)   # allow the ODR to start and the FIFO to begin filling

    def read_xyz(self, retries: int = 3) -> tuple:
        """
        Read a single X, Y, Z sample. Returns acceleration in g.

        Retries on OSError. A vibrating rig with Dupont jumpers throws the odd
        [Errno 5] I/O error — a NAK on the bus, usually a marginal contact. One
        such glitch used to propagate up and kill an entire run mid-window; a
        60s experiment should not be lost to one bad byte. If every retry fails
        the OSError is still raised, and collect_window() decides what to do
        about it.
        """
        last_err = None
        for _ in range(retries):
            try:
                raw = self.bus.read_i2c_block_data(self.addr, config.REG_DATAX0, 6)
                break
            except OSError as e:
                last_err = e
                time.sleep(0.0005)
        else:
            raise last_err

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

    # ── FIFO (hardware-timed) path ───────────────────────────────────────────
    def _fifo_entries(self) -> int:
        """Number of samples currently sitting in the FIFO (0..32)."""
        return self._read_byte(config.REG_FIFO_STATUS) & 0x3F

    def _overrun(self) -> bool:
        """
        True if the FIFO overran since the last read of INT_SOURCE. Overrun means
        the sensor produced samples faster than we drained them and the oldest
        were overwritten — the captured block is then NOT contiguous in time.
        Reading INT_SOURCE clears the flag.
        """
        return bool(self._read_byte(config.REG_INT_SOURCE) & 0x01)

    def flush_fifo(self) -> None:
        """
        Drop stale samples and clear the overrun flag so a fresh window starts
        from a known-empty buffer. Toggling Bypass->Stream clears the FIFO.
        """
        self._write_byte(config.REG_FIFO_CTL, config.FIFO_MODE_BYPASS)
        self._write_byte(config.REG_FIFO_CTL, config.FIFO_MODE_STREAM)
        self._read_byte(config.REG_INT_SOURCE)   # clear a pending overrun bit

    def read_fifo_block(self, axis_idx: int) -> tuple:
        """
        Drain every sample currently in the FIFO for one axis.

        Returns (values_in_g:list, overran:bool). Each 6-byte read of the data
        registers pops exactly one FIFO entry (the datasheet requires >5 us
        between successive FIFO reads; the I2C transaction itself already exceeds
        that, and we add a small guard). Timing of these samples is set by the
        sensor's ODR clock, not by when this function runs.
        """
        n = self._fifo_entries()
        vals = []
        for _ in range(n):
            for _retry in range(3):
                try:
                    raw = self.bus.read_i2c_block_data(self.addr, config.REG_DATAX0, 6)
                    break
                except OSError:
                    time.sleep(0.0005)
            else:
                # Give up on this entry; leave the rest of the FIFO for next call.
                break
            raw_u16 = np.array([
                (raw[1] << 8) | raw[0],
                (raw[3] << 8) | raw[2],
                (raw[5] << 8) | raw[4],
            ], dtype=np.uint16)
            axes = raw_u16.view(np.int16)
            vals.append(int(axes[axis_idx]) * self.scale)
            time.sleep(6e-6)   # datasheet: >5 us between FIFO reads
        return vals, self._overrun()

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
    Collect a fixed-length window of acceleration samples — HARDWARE-TIMED.

    Args:
        accel:       Initialised ADXL345 instance.
        n_samples:   Number of samples in the RETURNED window.
        sample_rate: Effective sample rate of the RETURNED window (Hz). The model
                     was trained at fs=1000, so this stays config.FS.
        axis:        Which axis to record: 'x', 'y', or 'z'.

    Returns:
        1-D NumPy array of length `n_samples`, acceleration in g, uniformly
        sampled at `sample_rate`. Signature and return type are unchanged, so
        monitor.py and live_features.preprocess() need no edits.

    How the timing works
    --------------------
    The sensor free-runs at accel.odr_hz (1600 Hz) and buffers samples in its
    FIFO on its own clock, so their spacing is exactly 1/ODR. We capture
    `duration = n_samples / sample_rate` seconds of that stream, then resample
    the block from ODR to `sample_rate` (1600 -> 1000 by default). The returned
    window is therefore uniformly sampled at exactly `sample_rate`, which is the
    contract welch() relies on — no dependence on Linux scheduling and no
    silent rate drift.

    ANTI-ALIASING: the ADXL345's internal bandwidth at 1600 Hz ODR is 800 Hz, and
    we sample it cleanly at 1600 Hz, so nothing folds during capture. The
    polyphase resample to 1000 Hz applies its own low-pass at the new Nyquist
    (500 Hz). Structural energy of interest (0–15 Hz) is far below both, so it
    is preserved exactly; the out-of-band mechanical/electrical hash is then
    removed downstream by the training bandpass in live_features.preprocess().
    """
    axis_idx = {"x": 0, "y": 1, "z": 2}[axis.lower()]
    odr = accel.odr_hz
    duration_s = n_samples / sample_rate
    n_raw_target = int(math.ceil(duration_s * odr)) + odr // 100  # small margin

    accel.flush_fifo()
    raw = []
    overrun_events = 0
    t_window = time.perf_counter()
    # Drain the FIFO repeatedly until we have a full window's worth of samples.
    # We cannot pull faster than the ODR produces, so the loop's wall-clock is
    # governed by the sensor, not by us — that is the point.
    while len(raw) < n_raw_target:
        vals, overran = accel.read_fifo_block(axis_idx)
        raw.extend(vals)
        if overran:
            overrun_events += 1
        if not vals:
            # FIFO briefly empty: sleep ~half a fill so we don't spin the CPU.
            time.sleep(0.5 * config.FIFO_DEPTH / odr)
    elapsed = time.perf_counter() - t_window

    raw = np.asarray(raw[:n_raw_target], dtype=float)
    raw_throughput = len(raw) / elapsed        # should sit at ~ODR if healthy

    # Resample ODR -> sample_rate. Fraction keeps the up/down factors small
    # (1600->1000 is 5/8). resample_poly applies an anti-alias FIR internally.
    frac = Fraction(int(sample_rate), int(odr)).limit_denominator(1000)
    up, down = frac.numerator, frac.denominator
    resampled = resample_poly(raw, up, down)

    # Land on exactly n_samples (resample_poly's length is round(len*up/down)).
    if len(resampled) >= n_samples:
        window = resampled[:n_samples]
    else:
        window = np.pad(resampled, (0, n_samples - len(resampled)), mode="edge")

    # A healthy FIFO delivers at the ODR. A raw throughput well below ODR means
    # we could not drain fast enough (I2C too slow / CPU starved) and the FIFO
    # was overrunning — the captured block is then not time-contiguous.
    if raw_throughput < 0.9 * odr:
        print(f"  WARNING: FIFO throughput {raw_throughput:.0f} Hz << ODR {odr} Hz "
              f"— cannot drain fast enough; samples are being lost. Raise "
              f"i2c_arm_baudrate (dtparam=i2c_arm_baudrate=400000) or lower ODR_HZ.")
    if overrun_events:
        print(f"  WARNING: {overrun_events} FIFO overrun event(s) during this "
              f"window — captured samples are NOT time-contiguous; discard/repeat "
              f"this window if timing matters.")

    collect_window.last_achieved_fs = float(sample_rate)   # returned window IS at sample_rate
    collect_window.last_raw_throughput_hz = float(raw_throughput)
    collect_window.last_dropouts = int(overrun_events)

    return window


# ─────────────────────────────────────────────
#  Self-test (run on the Pi):  python3 sensor.py --selftest
# ─────────────────────────────────────────────
def _selftest(n_samples: int = config.N_SAMPLES, sample_rate: int = config.FS,
              repeats: int = 3) -> None:
    """
    Verify the FIFO acquisition path on real hardware: that the RAW capture runs
    at the sensor ODR (not the scheduler), that there are no overruns, and that
    the returned window is the requested length at the requested rate.

    Independent timing check: we capture a raw FIFO block ourselves and confirm
    its throughput equals the ODR to within a few percent. Because FIFO samples
    are clocked by the sensor, their spacing is 1/ODR by construction — the thing
    we actually verify is that we can DRAIN at ODR without overrunning, which is
    what makes the captured block time-contiguous.
    """
    print("=" * 64)
    print(f"FIFO ACQUISITION SELF-TEST  (ODR={config.ODR_HZ} Hz -> return fs={sample_rate} Hz)")
    print("=" * 64)
    accel = ADXL345()

    # Raw-throughput check straight off the FIFO.
    accel.flush_fifo()
    got, t0 = [], time.perf_counter()
    overruns = 0
    while len(got) < config.ODR_HZ:          # ~1 s of raw samples
        vals, ov = accel.read_fifo_block(2)
        got.extend(vals)
        overruns += int(ov)
        if not vals:
            time.sleep(0.5 * config.FIFO_DEPTH / config.ODR_HZ)
    raw_fs = len(got) / (time.perf_counter() - t0)
    print(f"[raw FIFO] drained {len(got)} samples at {raw_fs:.0f} Hz "
          f"(ODR {config.ODR_HZ} Hz), overruns={overruns}")
    ok_raw = abs(raw_fs - config.ODR_HZ) / config.ODR_HZ < 0.05 and overruns == 0

    # Full collect_window path.
    for r in range(repeats):
        w = collect_window(accel, n_samples=n_samples, sample_rate=sample_rate)
        print(f"[collect_window {r+1}] len={len(w)} (want {n_samples}) | "
              f"raw throughput {collect_window.last_raw_throughput_hz:.0f} Hz | "
              f"overruns={collect_window.last_dropouts} | "
              f"RMS={np.sqrt(np.mean((w-w.mean())**2)):.4f} g")
    accel.close()

    ok_len = len(w) == n_samples
    print("-" * 64)
    if ok_raw and ok_len:
        print("PASS: hardware-timed acquisition healthy. Sample spacing is set by "
              "the sensor ODR; welch(fs=%d) is valid." % sample_rate)
    else:
        print("FAIL:")
        if not ok_raw:
            print("  - Raw FIFO throughput is not at ODR / overruns occurred: the "
                  "Pi cannot drain the FIFO fast enough. Raise i2c_arm_baudrate to "
                  "400000, or lower config.ODR_HZ (e.g. 400 Hz).")
        if not ok_len:
            print("  - Returned window length wrong — resample math off.")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print("sensor.py — hardware driver module. Run with --selftest on the Pi.")

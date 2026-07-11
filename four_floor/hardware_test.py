"""
hardware_test.py — Wiring/sanity checks
==========================================
Run this FIRST after wiring up the Pi, before main.py --live.

Replaces the old loopback.py (SPI-based — no longer relevant now that both
the ADXL345 and DS3231 are on I2C) and the ad-hoc test block that used to
live at the bottom of sensor_driver.py.

    python3 hardware_test.py         # full test: I2C scan + both sensors
    python3 hardware_test.py --scan  # just the I2C bus scan
"""

import argparse

import config


def _scan_bus(bus: int) -> list:
    import smbus2

    found = []
    with smbus2.SMBus(bus) as i2c:
        for addr in range(0x03, 0x78):
            try:
                i2c.read_byte(addr)
                found.append(addr)
            except OSError:
                pass
    return found


def i2c_scan() -> dict:
    """
    Lists every I2C address that ACKs on each relevant bus — the I2C
    equivalent of the old SPI loopback test. The ADXL345 and DS3231 are on
    DIFFERENT I2C buses on this rig (bus 3 and bus 1 respectively — see
    config.py), so both get scanned separately.
    """
    results = {}
    for label, bus, expected_addrs, name in [
        ("ADXL345", config.ADXL345_I2C_BUS,
         {config.ADXL345_I2C_ADDR, 0x1D}, "ADXL345"),
        ("DS3231", config.DS3231_I2C_BUS, {0x68}, "DS3231"),
    ]:
        print(f"Scanning I2C bus {bus} (expect {name})...")
        found = _scan_bus(bus)
        results[label] = found
        if found:
            print("  Found devices at: " + ", ".join(hex(a) for a in found))
        if any(a in expected_addrs for a in found):
            print(f"  [OK] {name} responding.")
        else:
            print(f"  [MISSING] No {name} found on bus {bus}. Check that I2C "
                  "is enabled (sudo raspi-config -> Interface Options -> I2C), "
                  "any required dtoverlay for this bus in "
                  "/boot/firmware/config.txt, and the wiring "
                  "(SDA/SCL/VCC/GND).")

    return results


def sensor_test() -> bool:
    """Confirms the ADXL345 and DS3231 are wired correctly and responding."""
    from sensor import ADXL345, DS3231, collect_window
    from live_features import preprocess

    all_ok = True
    accel = None

    print("\n[1] ADXL345 accelerometer")
    try:
        accel = ADXL345()
        x, y, z = accel.read_xyz()
        print(f"    X={x*1000:.2f}mg  Y={y*1000:.2f}mg  Z={z*1000:.2f}mg  "
              f"(Z should be ~1000mg when flat)")
        print("    ADXL345 OK")
    except Exception as e:
        print(f"    ADXL345 FAILED: {e}")
        all_ok = False

    print("\n[2] DS3231 real-time clock")
    try:
        rtc = DS3231()
        now = rtc.get_datetime()
        temp = rtc.get_temperature_c()
        print(f"    Time: {now.strftime('%Y-%m-%d %H:%M:%S')}   Temp: {temp:.2f}C")
        print("    DS3231 OK")
        rtc.close()
    except Exception as e:
        print(f"    DS3231 FAILED: {e}")
        all_ok = False

    if accel is not None:
        print("\n[3] Preprocessing pipeline (short live window)")
        try:
            window = collect_window(accel, n_samples=1000, sample_rate=config.FS)
            features = preprocess(window)
            print(f"    Output shape: {features.shape}  "
                  f"min={features.min():.3f}  max={features.max():.3f}")
            print("    Pipeline OK")
        except Exception as e:
            print(f"    Pipeline FAILED: {e}")
            all_ok = False
        finally:
            accel.close()

    return all_ok


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan", action="store_true",
                         help="Only run the I2C bus scan")
    args = parser.parse_args()

    print("=" * 50)
    print("Hardware test")
    print("=" * 50)

    if args.scan:
        i2c_scan()
        return

    i2c_scan()
    sensor_test()
    print("\n" + "=" * 50)


if __name__ == "__main__":
    main()

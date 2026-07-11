"""
DEPRECATED — superseded by hardware_test.py, which includes an I2C bus
scan plus the ADXL345/DS3231 sensor tests in one place (this SPI
loopback check is no longer relevant now that both sensors are on I2C).

Run instead:

    python3 hardware_test.py --scan

Safe to delete:

    rm four_floor/loopback.py

Kept only as a placeholder because this environment couldn't delete the
file directly — your Terminal can.
"""

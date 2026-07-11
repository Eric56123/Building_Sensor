"""
DEPRECATED — superseded by sensor.py (hardware drivers) and
preprocessing.py (the canonical, model-matching signal-processing
pipeline). This file's own preprocess_for_pinn() used a different
FFT/normalisation method that no longer matched what SHM_PINN was
trained on — that's why it's been retired rather than kept as a
second, disagreeing implementation.

Safe to delete:

    rm four_floor/sensor_driver.py

Kept only as a placeholder because this environment couldn't delete the
file directly — your Terminal can.
"""

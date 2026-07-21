"""
live_features.py — Signal -> PINN input features (RPi live pipeline)
========================================================================
The ONE canonical feature-extraction pipeline used at inference time on
the Pi. Named distinctly from the existing preprocessing/ package (which
holds offline training-data cleaning/normalisation) to avoid a module
name collision — Python would otherwise prefer the preprocessing/
package over a same-named preprocessing.py module and silently break
these imports.

Previously this logic existed in two different, disagreeing places
(main.py's preprocess() and sensor_driver.py's preprocess_for_pinn()) —
the second used a different FFT/normalisation method entirely and no
longer matched what the model was actually trained on. That duplicate
has been removed; everything now goes through here.

Pipeline (must match training exactly — see train.py PHASE 2 and
simulation/generate_dataset.py):
  1. sanitize_accelerometer_data: linear detrend + 0.5–45 Hz zero-phase
     Butterworth bandpass  <-- this step was MISSING at inference; see note.
  2. Welch PSD estimate (fs=config.FS, nperseg=config.NPERSEG)
  3. log10 compression
  4. Min-max normalisation using the fitted training constants (NORM_MIN/MAX,
     which ARE the PSDScaler bounds from training)
  5. Clip to [0, 1]

CONTRACT FIX (2026-07): the training pipeline runs every window through
`sanitize_accelerometer_data` (detrend + 0.5–45 Hz bandpass) BEFORE Welch —
train.py:118 and generate_dataset.py:163. This inference path used to only
mean-subtract, so the model was being fed PSDs that still contained all the
15–500 Hz content the training PSDs never had (on a recorded baseline window
that is ~73% of the total energy). Restoring the identical bandpass here does
NOT invent a new contract — it makes inference match what the network was
actually trained on, using the SAME function so the two cannot drift apart.
It is contract-restoring, not contract-changing, so it needs no retraining.
"""

import numpy as np
from scipy.signal import welch

import config
from preprocessing.cleaning import sanitize_accelerometer_data


def preprocess(signal: np.ndarray) -> np.ndarray:
    """
    Convert a raw single-channel acceleration window into the normalised
    PSD feature vector the SHM_PINN model expects.

    Args:
        signal: 1-D array of raw acceleration samples at config.FS
                (see sensor.collect_window — now hardware-timed and resampled to
                config.FS, so passing fs=config.FS below is valid).

    Returns:
        1-D float32 array of length config.N_FREQ_BINS, values in [0, 1].
    """
    # Same detrend + 0.5–45 Hz bandpass the training data went through. This
    # both matches training and band-limits away the out-of-band hash; it does
    # NOT undo aliasing that happened at acquisition — that is prevented earlier,
    # in sensor.collect_window's hardware-timed FIFO capture.
    cleaned = sanitize_accelerometer_data(signal, fs=config.FS)
    _, psd = welch(cleaned, fs=config.FS, nperseg=config.NPERSEG)
    psd_log = np.log10(psd + 1e-10)
    psd_norm = (psd_log - config.NORM_MIN) / (config.NORM_MAX - config.NORM_MIN)
    return np.clip(psd_norm, 0, 1).astype(np.float32)


def to_model_input(signal: np.ndarray, n_floors: int = config.MAX_FLOORS) -> np.ndarray:
    """
    Build the (MAX_FLOORS, N_FREQ_BINS) array SHM_PINN expects (add a batch
    dimension with .unsqueeze(0) before feeding it to the model).

    The rig currently has one physical accelerometer, moved between floors
    between runs (see Experiment Log, "2. Sensor Config" — one placement per
    test), rather than four simultaneous sensors. So every channel is fed the
    same single-sensor feature vector; this mirrors what the original main.py
    already did and keeps the model's fixed 4-channel input satisfied
    regardless of how many floors are physically present in a given rig
    configuration.

    Args:
        signal:   Raw acceleration window from the single deployed sensor.
        n_floors: Informational only for now (validated elsewhere) — kept as
                  a parameter so a future multi-sensor deployment can pass
                  per-floor signals here instead of broadcasting one.

    Returns:
        NumPy array of shape (config.MAX_FLOORS, config.N_FREQ_BINS).
    """
    features = preprocess(signal)
    return np.stack([features] * config.MAX_FLOORS, axis=0)

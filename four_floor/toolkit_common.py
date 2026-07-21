"""
toolkit_common.py — Shared engine for the characterisation toolkit
===================================================================
One implementation of every calculation the characterisation scripts share, so
capture_sweep / sweep_analysis / ringdown / linearity_check cannot drift apart in
how they load data, compute spectra, or find peaks.

Contract constants come from `config` — never hardcoded here — so a change to FS
or N_SAMPLES propagates everywhere.

THE _raw CSV FORMAT
-------------------
Written by monitor.py and capture_sweep.py, read by every analysis tool:

    timestamp,sample_0,sample_1,...,sample_{N-1}

One ROW per acquisition window of config.N_SAMPLES samples at config.FS. During a
sweep the drive frequency changes across rows, so analysis treats all rows as one
continuous series: samples are contiguous *within* a window, and between windows
there may be a sub-millisecond gap. That gap limits absolute phase but not
resonance estimation, which is what these tools measure.

TWO PSD PATHS, DELIBERATELY
---------------------------
  training_psd() — applies the same bandpass the model was trained under, for
                   anything the PINN will consume. Preserves the training
                   contract.
  raw_psd()      — no filtering at all, for noise-floor and full-band searches
                   where a filter would hide the very thing you are looking for.

Using training_psd() to hunt for an unknown f1 would band-limit the search and
can return a filter edge artefact as if it were a resonance. Using raw_psd() on
model input would break the training contract. Pick deliberately.
"""
import json
import os
import time
from datetime import datetime

import numpy as np
from scipy.signal import (butter, detrend, find_peaks, hilbert, sosfiltfilt,
                          welch)

import config

# ─────────────────────────────────────────────
#  Paths — never inside logs/ or pi_logs/
# ─────────────────────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))
RIG_JSON = os.path.join(HERE, "rig.json")
# Captures and session records land here, kept clearly apart from the campaign
# data in pi_logs/ so characterisation runs can never be mistaken for damage runs.
CHARACTERISATION_DIR = os.path.join(HERE, "characterisation")

# Bands used for reporting energy distribution. STRUCTURAL is the range a scaled
# 4-storey frame's modes are expected in; the rest exist to expose contamination.
REPORT_BANDS = (
    ("DC-0.5",     0.0,   0.5),    # drift, thermal, tilt
    ("0.5-5",      0.5,   5.0),
    ("5-15",       5.0,  15.0),    # the old assumed band
    ("15-50",     15.0,  50.0),    # where an unexpectedly stiff f1 may sit
    ("50-mains",  50.0,  55.0),    # 50 Hz mains pickup
    ("55-Nyq",    55.0,  np.inf),
)


# ─────────────────────────────────────────────
#  CSV I/O
# ─────────────────────────────────────────────
def load_raw_series(path):
    """
    Concatenate every window row of a _raw CSV into one 1-D series.

    Returns (series, n_windows). Rows with fewer than 10 parsed values are
    skipped as malformed rather than silently corrupting the series with a short
    window — a truncated final row is common if a capture is interrupted.
    """
    windows = []
    with open(path) as f:
        next(f)   # header
        for line in f:
            parts = line.rstrip("\n").split(",")
            vals = [p for p in parts[1:] if p != ""]
            if len(vals) > 10:
                windows.append(np.asarray(vals, dtype=float))
    if not windows:
        raise ValueError(f"No data rows parsed from {path}")
    return np.concatenate(windows), len(windows)


def raw_csv_header(n_samples=None):
    n = config.N_SAMPLES if n_samples is None else n_samples
    return "timestamp," + ",".join(f"sample_{i}" for i in range(n))


def append_window(fh, timestamp, window):
    """Append one window row in the standard format and flush it to disk."""
    fh.write(timestamp + "," + ",".join(f"{v:.6g}" for v in window) + "\n")
    fh.flush()   # a mid-capture crash then still leaves every completed window


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


def timestamp_slug():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ─────────────────────────────────────────────
#  Spectra
# ─────────────────────────────────────────────
def bandpass(x, fs, lo, hi, order=4):
    ny = 0.5 * fs
    hi = min(hi, 0.99 * ny)
    lo = max(lo, 1e-6)
    sos = butter(order, [lo / ny, hi / ny], btype="bandpass", output="sos")
    return sosfiltfilt(sos, x)


def raw_psd(x, fs=None, nperseg=None):
    """
    Unfiltered Welch PSD. Use for noise floors and unknown-f1 searches.

    Detrended only — a DC offset (gravity leaking onto the axis, sensor bias)
    would otherwise dominate the lowest bins and skew any median-based threshold.
    """
    fs = float(config.FS) if fs is None else float(fs)
    x = detrend(np.asarray(x, dtype=float))
    if nperseg is None:
        nperseg = int(min(len(x), max(4096, fs * 10)))   # ~0.1 Hz resolution
    return welch(x, fs=fs, nperseg=int(nperseg))


def training_psd(x, fs=None, nperseg=None):
    """
    PSD under the training contract — the same bandpass live_features.preprocess()
    applies. Use ONLY for anything the PINN consumes, so live and training
    features stay comparable.
    """
    fs = float(config.FS) if fs is None else float(fs)
    lo, hi = training_band(fs)
    xb = bandpass(np.asarray(x, dtype=float), fs, lo, hi)
    nperseg = int(config.NPERSEG) if nperseg is None else int(nperseg)
    return welch(xb, fs=fs, nperseg=min(nperseg, len(xb)))


def training_band(fs=None):
    """
    The bandpass the model was trained under, read from config where available so
    this cannot drift from live_features.py. Falls back to the documented 0.5-45 Hz
    only if config does not define it.
    """
    fs = float(config.FS) if fs is None else float(fs)
    lo = float(getattr(config, "BANDPASS_LO", 0.5))
    hi = float(getattr(config, "BANDPASS_HI", 45.0))
    return lo, min(hi, 0.45 * fs)


def full_band(fs=None):
    """
    The widest defensible search band: 0.5 Hz up to 90% of Nyquist.

    Below 0.5 Hz is drift, not structure. Stopping short of Nyquist avoids the
    resample filter's transition region, where roll-off can look like a broad
    peak. Use when f1 is UNKNOWN — a narrow assumed band cannot find a resonance
    outside itself, and will happily return the largest noise peak inside it.
    """
    fs = float(config.FS) if fs is None else float(fs)
    return 0.5, 0.45 * fs


# ─────────────────────────────────────────────
#  Peak handling
# ─────────────────────────────────────────────
def refine_peak_parabolic(freqs, psd, i):
    """
    Sub-bin peak location by fitting a parabola to the log-PSD at (i-1, i, i+1).

    Welch bin spacing is fs/nperseg — around 0.1-0.25 Hz here — so the true peak
    can sit up to half a bin from the largest sample. For an f1 near 10 Hz that is
    a ~1% error before any physics enters. Interpolating in log space suits the
    roughly Lorentzian shape of a lightly damped resonance.
    """
    if i <= 0 or i >= len(psd) - 1:
        return float(freqs[i])
    a, b, c = np.log(psd[i - 1] + 1e-300), np.log(psd[i] + 1e-300), np.log(psd[i + 1] + 1e-300)
    denom = a - 2 * b + c
    if abs(denom) < 1e-12:
        return float(freqs[i])
    delta = 0.5 * (a - c) / denom          # in bins, |delta| <= 0.5 when i is a true peak
    delta = float(np.clip(delta, -0.5, 0.5))
    df = float(freqs[1] - freqs[0])
    return float(freqs[i]) + delta * df


def find_spectral_peaks(freqs, psd, f_lo, f_hi, n_peaks=5, prominence_factor=5.0,
                        min_separation_hz=0.5):
    """
    Peaks standing clearly above the local median, strongest first.

    Returns a list of dicts: {f_hz, power, bin_index, prominence_ratio}.
    Thresholding on the MEDIAN rather than the mean keeps a single huge resonance
    from raising the bar so far that genuine higher modes are missed.
    """
    band = (freqs >= f_lo) & (freqs <= f_hi)
    if not band.any():
        return []
    fb, pb = freqs[band], psd[band]
    base = float(np.median(pb))
    if base <= 0:
        base = float(np.mean(pb)) or 1e-300
    df = float(fb[1] - fb[0]) if len(fb) > 1 else 1.0
    idx, _ = find_peaks(pb, height=base * prominence_factor,
                        distance=max(1, int(min_separation_hz / df)))
    if len(idx) == 0:
        return []
    order = np.argsort(pb[idx])[::-1][:n_peaks]
    out = []
    for i in idx[order]:
        out.append({
            "f_hz": refine_peak_parabolic(fb, pb, int(i)),
            "power": float(pb[i]),
            "bin_index": int(i),
            "prominence_ratio": float(pb[i] / base),
        })
    return out


def group_peaks_into_modes(peaks, rel_tol=0.15):
    """
    Collapse spectral peaks that belong to the SAME resonance into one mode.

    A single lightly damped mode does not produce a single PSD peak: Welch
    leakage, sweep sidebands and noise put several local maxima within a few
    percent of each other. Treating each as a separate mode makes "the lowest
    peak is f1" pick a sideband — a systematic underestimate of f1, which is
    exactly the sort of quiet 1-3% error that is impossible to spot later.

    Peaks within `rel_tol` of each other (fractionally, since resonance width
    scales with frequency) are grouped; the strongest in each group represents
    the mode. Returns groups sorted by frequency, lowest first.
    """
    if not peaks:
        return []
    ordered = sorted(peaks, key=lambda p: p["f_hz"])
    groups, current = [], [ordered[0]]
    for p in ordered[1:]:
        if abs(p["f_hz"] - current[-1]["f_hz"]) <= rel_tol * current[-1]["f_hz"]:
            current.append(p)
        else:
            groups.append(current)
            current = [p]
    groups.append(current)
    modes = []
    for g in groups:
        rep = max(g, key=lambda p: p["power"])
        modes.append({**rep, "n_peaks_merged": len(g),
                      "f_span": (min(p["f_hz"] for p in g),
                                 max(p["f_hz"] for p in g))})
    return modes


def near_band_edge(f, f_lo, f_hi, rel_margin=0.10):
    """
    Is a peak close enough to a search edge that the true mode may lie outside?

    The margin is a fraction of the PEAK's OWN frequency, not of the band span.
    Span-relative margins break under a wide search: with --full-band spanning
    0.5-450 Hz, 10% of the span is 45 Hz, so every real mode below 45 Hz would be
    flagged as "near the low edge" and the warning becomes noise.

    Returns None, "low" or "high".
    """
    margin = rel_margin * max(f, 1e-9)
    if f - f_lo < margin:
        return "low"
    if f_hi - f < margin:
        return "high"
    return None


def half_power_zeta(freqs, psd, f_peak):
    """
    Damping from the -3 dB (half-power) bandwidth: zeta ~ (f_hi - f_lo) / (2 f_n).

    Returns nan if either half-power crossing runs off the end of the band, which
    happens when the peak is too close to a band edge or too broad to resolve —
    better to report nothing than a number silently truncated by the window.

    NOTE this estimator is biased by Welch smoothing and by any nonlinearity, and
    is why ringdown log-decrement is preferred where a free decay is available.
    """
    i = int(np.argmin(np.abs(freqs - f_peak)))
    half = psd[i] / 2.0     # power halves at -3 dB
    lo = i
    while lo > 0 and psd[lo] > half:
        lo -= 1
    hi = i
    while hi < len(psd) - 1 and psd[hi] > half:
        hi += 1
    if lo == 0 or hi == len(psd) - 1:
        return float("nan")
    bw = float(freqs[hi] - freqs[lo])
    return bw / (2.0 * f_peak) if f_peak > 0 else float("nan")


def estimate_modal_frequency(x, fs=None, f_lo=None, f_hi=None, n_peaks=5):
    """
    Primary modal estimate: refined peaks of the unfiltered PSD in [f_lo, f_hi].

    Returns {peaks, modes, f1, freqs, psd, band}.

    f1 is the lowest MODE, where sidebands of one resonance have been merged
    first (group_peaks_into_modes). Taking the lowest raw peak instead picks a
    sideband and biases f1 low by a few percent.

    The lowest mode, not the strongest: a higher mode is often driven harder than
    the fundamental, depending on where the shaker couples in.
    """
    fs = float(config.FS) if fs is None else float(fs)
    if f_lo is None or f_hi is None:
        f_lo, f_hi = full_band(fs)
    freqs, psd = raw_psd(x, fs)
    peaks = find_spectral_peaks(freqs, psd, f_lo, f_hi, n_peaks=n_peaks)
    modes = group_peaks_into_modes(peaks)
    f1 = modes[0]["f_hz"] if modes else float("nan")
    return {"peaks": peaks, "modes": modes, "f1": f1, "freqs": freqs, "psd": psd,
            "band": (f_lo, f_hi)}


# ─────────────────────────────────────────────
#  Amplitude / energy helpers
# ─────────────────────────────────────────────
def rms(x):
    """AC RMS — mean removed, so gravity on the axis does not inflate it."""
    x = np.asarray(x, dtype=float)
    return float(np.sqrt(np.mean((x - x.mean()) ** 2)))


def dc_offset(x):
    return float(np.mean(np.asarray(x, dtype=float)))


def band_energy(x, fs=None, bands=REPORT_BANDS):
    """
    Fraction of total PSD energy in each named band.

    Returns list of (name, f_lo, f_hi, fraction). Fractions sum to ~1 over the
    covered range; they make contamination obvious at a glance (a big 50-mains
    share means electrical pickup, a big DC-0.5 share means drift or tilt).
    """
    fs = float(config.FS) if fs is None else float(fs)
    freqs, psd = raw_psd(x, fs)
    total = float(np.trapezoid(psd, freqs)) if hasattr(np, "trapezoid") else float(np.trapz(psd, freqs))
    if total <= 0:
        return [(n, lo, hi, float("nan")) for n, lo, hi in bands]
    out = []
    for name, lo, hi in bands:
        hi_eff = min(hi, freqs[-1])
        m = (freqs >= lo) & (freqs <= hi_eff)
        if m.sum() < 2:
            out.append((name, lo, hi, 0.0))
            continue
        e = float(np.trapezoid(psd[m], freqs[m])) if hasattr(np, "trapezoid") else float(np.trapz(psd[m], freqs[m]))
        out.append((name, lo, hi, e / total))
    return out


def band_share(x, fs, f_lo, f_hi):
    """Fraction of energy inside one arbitrary band — used for the axis check."""
    fs = float(fs)
    freqs, psd = raw_psd(x, fs)
    total = float(np.trapezoid(psd, freqs)) if hasattr(np, "trapezoid") else float(np.trapz(psd, freqs))
    m = (freqs >= f_lo) & (freqs <= f_hi)
    if total <= 0 or m.sum() < 2:
        return float("nan")
    e = float(np.trapezoid(psd[m], freqs[m])) if hasattr(np, "trapezoid") else float(np.trapz(psd[m], freqs[m]))
    return e / total


def snr_db(signal_rms, noise_rms):
    if noise_rms <= 0 or signal_rms <= 0:
        return float("nan")
    return float(20.0 * np.log10(signal_rms / noise_rms))


# ─────────────────────────────────────────────
#  Ringdown / free decay
# ─────────────────────────────────────────────
def analyze_ringdown(x, fs=None, f_lo=None, f_hi=None, min_cycles=5):
    """
    Damping from a free decay, by two independent routes.

    Returns a dict with:
        f_d            damped natural frequency (Hz), from the decay's PSD peak
        zeta_logdec    log-decrement over successive envelope peaks
        zeta_envfit    slope of a least-squares line through log(envelope)
        r2             fit quality of that line (1.0 = perfect exponential decay)
        n_peaks        peaks used by the log-decrement
        agree          True if the two estimates are within 25% of each other
        start_idx      where the decay was judged to begin

    WHY TWO: log-decrement uses only peak amplitudes and is robust to a poor
    envelope, while the envelope fit uses every sample and is robust to a single
    mis-detected peak. Agreement is the confidence signal. A low r2 means the
    decay is not a single exponential — usually two modes beating, or the tap
    excited a nonlinearity (loose joints rattling).

    The signal is bandpassed around the dominant mode first, because a raw tap
    excites many modes and the log-decrement assumes ONE decaying sinusoid.
    """
    fs = float(config.FS) if fs is None else float(fs)
    x = detrend(np.asarray(x, dtype=float))

    # Find the dominant mode of the decay to know what to filter around.
    if f_lo is None or f_hi is None:
        f_lo, f_hi = full_band(fs)
    freqs, psd = raw_psd(x, fs)
    peaks = find_spectral_peaks(freqs, psd, f_lo, f_hi, n_peaks=1)
    if not peaks:
        return {"error": "no spectral peak in the decay — was the rig actually struck?"}
    f_d = peaks[0]["f_hz"]

    # Isolate that mode. A +/-30% window is wide enough to keep the resonance and
    # its sidebands but narrow enough to reject neighbouring modes.
    xb = bandpass(x, fs, max(0.3, f_d * 0.7), f_d * 1.3)
    env = np.abs(hilbert(xb))

    # The decay starts at the largest envelope value (the strike); everything
    # before it is pre-tap quiet and would flatten the fit.
    start = int(np.argmax(env))
    env_d = env[start:]
    period_samples = max(1, int(fs / max(f_d, 1e-6)))
    if len(env_d) < period_samples * min_cycles:
        return {"error": f"decay too short: need >= {min_cycles} cycles after the strike"}

    # Cut where the decay reaches the noise floor, estimated from the last 10% of
    # the record. Fitting into the floor biases zeta DOWN, because the flat noise
    # tail drags the log-linear slope toward zero.
    #
    # Take the FIRST sustained crossing, not the last one above the floor: noise
    # spikes late in the record cross back over it, so "last above" returns almost
    # the whole record and defeats the cut entirely. Smoothing over one period
    # first stops a single dip in the ripple from truncating a live decay.
    floor = float(np.median(env[-max(1, len(env) // 10):])) * 3.0
    kernel = np.ones(period_samples) / period_samples
    env_smooth = np.convolve(env_d, kernel, mode="same")
    below = env_smooth < floor
    if below.any():
        stop = int(np.argmax(below))          # first True
    else:
        stop = len(env_d)
    stop = max(stop, period_samples * min_cycles)   # keep a usable minimum
    stop = min(stop, len(env_d))
    env_d = env_d[:stop]
    if len(env_d) < 10:
        return {"error": "decay drops into the noise floor almost immediately"}

    t = np.arange(len(env_d)) / fs

    # --- Route 1: envelope fit. log(env) = log(A) - zeta*2*pi*f_d*t
    log_env = np.log(np.maximum(env_d, 1e-12))
    A = np.vstack([t, np.ones_like(t)]).T
    slope, intercept = np.linalg.lstsq(A, log_env, rcond=None)[0]
    pred = A @ np.array([slope, intercept])
    ss_res = float(np.sum((log_env - pred) ** 2))
    ss_tot = float(np.sum((log_env - log_env.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    zeta_envfit = float(-slope / (2 * np.pi * f_d)) if f_d > 0 else float("nan")

    # --- Route 2: log-decrement over successive peaks of the OSCILLATION.
    # delta = (1/n) * ln(x_0 / x_n);  zeta = delta / sqrt(4*pi^2 + delta^2)
    #
    # These must be peaks of the bandpassed SIGNAL, one per cycle. Peaks of the
    # envelope are wrong: the envelope of a decaying sinusoid is smooth and
    # monotonic, so it has no per-cycle peaks at all and find_peaks would return
    # noise ripple instead of the decay.
    sig_d = xb[start:start + stop]
    pk, _ = find_peaks(sig_d, distance=max(1, int(0.8 * period_samples)))
    zeta_logdec, n_used, logdec_r2 = float("nan"), 0, float("nan")
    if len(pk) >= 2:
        amps = sig_d[pk]
        amps = amps[amps > 0]

        # Least-squares fit through log(peak amplitude) vs peak index. For a decay
        # x_n = x_0 * exp(-delta*n), log(x_n) is linear in n with slope -delta.
        #
        # Do NOT truncate at the first non-monotonic peak. Real decays tick upward
        # by fractions of a percent from noise and mode beating; on this rig that
        # guard cut a 94-peak decay down to 3, because peak 4 exceeded peak 3 by
        # 0.16%. Nor use delta = ln(x_0/x_n)/n directly: it depends on just two
        # endpoint amplitudes, so one noisy peak sets the whole answer. The fit
        # uses every peak and reports its own R^2, which exposes a decay that is
        # not a single exponential instead of hiding it.
        if len(amps) >= 3:
            idx = np.arange(len(amps), dtype=float)
            log_a = np.log(amps)
            A = np.vstack([idx, np.ones_like(idx)]).T
            slope, intercept = np.linalg.lstsq(A, log_a, rcond=None)[0]
            resid = log_a - (A @ np.array([slope, intercept]))
            ss_tot = float(np.sum((log_a - log_a.mean()) ** 2))
            logdec_r2 = 1.0 - float(np.sum(resid ** 2)) / ss_tot if ss_tot > 0 else float("nan")
            delta = float(-slope)                       # log-decrement per cycle
            if delta > 0:
                zeta_logdec = float(delta / np.sqrt(4 * np.pi ** 2 + delta ** 2))
            n_used = len(amps)

    agree = (np.isfinite(zeta_logdec) and np.isfinite(zeta_envfit)
             and zeta_envfit > 0
             and abs(zeta_logdec - zeta_envfit) / zeta_envfit < 0.25)

    return {"f_d": f_d, "zeta_logdec": zeta_logdec, "zeta_envfit": zeta_envfit,
            "r2": r2, "logdec_r2": logdec_r2, "n_peaks": n_used,
            "agree": bool(agree), "start_idx": start,
            "n_used_samples": len(env_d),
            "envelope": env_d, "t": t, "fit": np.exp(pred)}


# ─────────────────────────────────────────────
#  rig.json — measured rig properties
# ─────────────────────────────────────────────
def load_rig():
    """Measured rig properties, or an empty dict if never measured."""
    if not os.path.exists(RIG_JSON):
        return {}
    try:
        with open(RIG_JSON) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_rig(d):
    with open(RIG_JSON, "w") as f:
        json.dump(d, f, indent=2, sort_keys=True)
        f.write("\n")


def rig_value(key, default=None):
    """
    One measured property, or `default` if the rig has not been characterised.

    Tools call this instead of hardcoding f1 so that an uncharacterised rig is a
    visible None rather than a plausible-looking inherited constant (the Johnson
    benchmark's 9.42 Hz caused exactly that failure once already).
    """
    return load_rig().get(key, default)

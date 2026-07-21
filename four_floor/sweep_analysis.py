"""
sweep_analysis.py — Estimate the rig's natural frequencies from a swept-sine run
================================================================================
Task 5 of the acquisition audit.

Feed it a _raw CSV recorded by monitor.py during a slow 1–15 Hz sine sweep of the
shaking table. It estimates the rig's actual resonant frequencies so you can
compare the measured f1 against the simulation's assumption (the Johnson
benchmark f1 = 9.42 Hz; see simulation/matrices.py).

The _raw CSV layout (from monitor.py):
    row = timestamp, sample_0, ..., sample_{N-1}
Each row is one acquisition window (config.N_SAMPLES samples at config.FS). During
a sweep the excitation frequency changes across rows, so we treat all rows as one
continuous time series (they are contiguous within a window; between windows there
may be a small gap — that only limits absolute phase, not the resonance estimate).

Two INDEPENDENT estimators (they should agree; disagreement = low confidence):
  1. Spectral peaks of the whole record (Welch PSD). A structure driven through
     its resonance responds most strongly there, so response energy piles up at
     the natural frequencies -> PSD peaks.
  2. Envelope-vs-instantaneous-frequency. In a linear sweep the drive frequency
     rises ~linearly with time, so time maps to frequency. The response envelope
     (|analytic signal|) peaks when the drive passes each resonance; mapping that
     peak time back to frequency gives an independent estimate and, from the
     peak sharpness, a rough damping ratio (zeta ~ half-power bandwidth / 2 f_n).

Nothing is written unless you pass --plot (a PNG next to the CSV, never in logs/).

Usage:
    python3 sweep_analysis.py path/to/R0xx_sweep_raw.csv
    python3 sweep_analysis.py sweep_raw.csv --f0 1 --f1 15 --fs 1000 --plot
"""
import argparse
import os

import numpy as np
from scipy.signal import welch, hilbert, find_peaks, detrend, butter, sosfiltfilt

import config
import toolkit_common as tk


def load_raw_series(path):
    """Concatenate every window row into one 1-D series; return (series, n_windows)."""
    windows = []
    with open(path) as f:
        header = next(f)
        for line in f:
            parts = line.rstrip("\n").split(",")
            vals = [p for p in parts[1:] if p != ""]
            if len(vals) > 10:
                windows.append(np.asarray(vals, dtype=float))
    if not windows:
        raise ValueError(f"No data rows parsed from {path}")
    return np.concatenate(windows), len(windows)


def bandpass(x, fs, lo, hi, order=4):
    ny = 0.5 * fs
    hi = min(hi, 0.99 * ny)
    sos = butter(order, [lo / ny, hi / ny], btype="bandpass", output="sos")
    return sosfiltfilt(sos, x)


def estimate_by_psd(x, fs, f0, f1, n_expected=3):
    """Peaks of the Welch PSD inside the swept band."""
    x = detrend(x)
    # nperseg: long enough for ~0.1 Hz resolution but not longer than the record
    nperseg = int(min(len(x), max(4096, fs * 10)))
    freqs, psd = welch(x, fs=fs, nperseg=nperseg)
    band = (freqs >= f0) & (freqs <= f1)
    fb, pb = freqs[band], psd[band]
    # peaks that stand clearly above the local median
    thr = np.median(pb) * 5
    idx, props = find_peaks(pb, height=thr, distance=int(0.5 / (fb[1] - fb[0])))
    order = np.argsort(pb[idx])[::-1]
    peaks = [(float(fb[i]), float(pb[i])) for i in idx[order][:n_expected]]
    return peaks, (fb, pb)


def estimate_by_envelope(x, fs, f0, f1, sweep_type="linear"):
    """
    Map response-envelope peaks to frequency via the sweep's time->freq law.

    THE LAW MUST MATCH THE GENERATOR. A linear sweep advances f(t) at a constant
    Hz/s; a logarithmic one advances at constant decades/s, dwelling far longer at
    low frequencies. Inverting the wrong law maps peak times to wrong frequencies
    — on a 1-100 Hz log sweep read as linear, a true 2.9 Hz resonance is reported
    near 9 Hz. The PSD estimate is unaffected either way, so a large PSD/envelope
    disagreement is often this, not a bad measurement.

    Returns list of (f_n_hz, zeta_estimate).
    """
    xb = bandpass(x, fs, f0, f1)
    env = np.abs(hilbert(xb))
    # light smoothing of the envelope (moving average ~0.25 s)
    w = max(1, int(0.25 * fs))
    env_s = np.convolve(env, np.ones(w) / w, mode="same")
    t = np.arange(len(xb)) / fs
    T = t[-1] if t[-1] > 0 else 1.0
    if sweep_type == "log":
        # f(t) = f0 * (f1/f0)^(t/T)  -- constant decades per second
        f_of_t = f0 * (f1 / max(f0, 1e-9)) ** (t / T)
    else:
        # f(t) = f0 + (f1-f0) * t/T  -- constant Hz per second
        f_of_t = f0 + (f1 - f0) * t / T

    thr = np.median(env_s) + 3 * np.std(env_s)
    idx, _ = find_peaks(env_s, height=thr, distance=int(0.5 * fs))
    order = np.argsort(env_s[idx])[::-1]
    out = []
    for i in idx[order][:3]:
        fn = float(f_of_t[i])
        # half-power (-3 dB, i.e. amplitude/sqrt2) bandwidth around this peak -> zeta
        half = env_s[i] / np.sqrt(2)
        lo = i
        while lo > 0 and env_s[lo] > half:
            lo -= 1
        hi = i
        while hi < len(env_s) - 1 and env_s[hi] > half:
            hi += 1
        bw = abs(f_of_t[hi] - f_of_t[lo])
        zeta = bw / (2 * fn) if fn > 0 else float("nan")
        out.append((fn, zeta))
    return out, (f_of_t, env_s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="a _raw CSV recorded during a 1–15 Hz sweep")
    ap.add_argument("--fs", type=float, default=float(config.FS),
                    help="effective sample rate of the record (Hz)")
    ap.add_argument("--f0", type=float, default=1.0, help="sweep start freq (Hz)")
    ap.add_argument("--f1", type=float, default=15.0, help="sweep end freq (Hz)")
    ap.add_argument("--full-band", action="store_true",
                    help="search 0.5 Hz to 0.45*fs instead of --f0/--f1. Use when "
                         "f1 is UNKNOWN: a narrow assumed band cannot find a mode "
                         "outside itself and will return the largest peak inside "
                         "it as though it were the answer.")
    ap.add_argument("--sweep-type", choices=["linear", "log"], default="linear",
                    help="the generator's sweep law. MUST match what the generator "
                         "did: a log sweep read as linear maps resonances to the "
                         "wrong frequencies (a 2.9 Hz mode reads near 9 Hz on a "
                         "1-100 Hz log sweep). Only affects the envelope method; "
                         "the PSD is independent of the sweep law.")
    ap.add_argument("--plot", action="store_true")
    args = ap.parse_args()

    # --full-band overrides the assumed sweep range for the SEARCH. The envelope
    # method still needs the true drive range, since it maps time to frequency
    # via the sweep law — so f0/f1 are kept separately for that.
    sweep_f0, sweep_f1 = args.f0, args.f1
    if args.full_band:
        args.f0, args.f1 = tk.full_band(args.fs)

    x, n_win = load_raw_series(args.csv)
    dur = len(x) / args.fs
    print("=" * 64)
    print(f"SWEEP ANALYSIS  {os.path.basename(args.csv)}")
    print(f"  {n_win} windows, {len(x)} samples, {dur:.1f} s @ {args.fs:.0f} Hz")
    print(f"  drive sweep  {sweep_f0}–{sweep_f1} Hz ({args.sweep_type})")
    if args.full_band:
        print(f"  SEARCH BAND  {args.f0:.1f}–{args.f1:.0f} Hz (--full-band): f1 is "
              "not assumed to lie in the drive range.")
    else:
        print(f"  search band  {args.f0}–{args.f1} Hz")
    print("=" * 64)

    psd_peaks, (fb, pb) = estimate_by_psd(x, args.fs, args.f0, args.f1)
    # The envelope method inverts the sweep law f(t) = f0 + (f1-f0)*t/T, so it
    # must use the ACTUAL drive range, not the search band — feeding it the full
    # band would map every peak time to the wrong frequency.
    env_peaks, (fmap, env) = estimate_by_envelope(x, args.fs, sweep_f0, sweep_f1,
                                                 sweep_type=args.sweep_type)

    print("\n[PSD peaks]        (strongest response frequencies)")
    for f, p in psd_peaks:
        print(f"    f = {f:6.2f} Hz   power {p:.2e}")
    print("\n[Envelope method]  (freq at response peak; zeta from -3 dB bandwidth)")
    for f, z in env_peaks:
        print(f"    f = {f:6.2f} Hz   zeta ≈ {z*100:5.2f} %")

    # Confidence: compare the STRONGEST response peak found by each method
    # (robust to spurious weak sidebands). psd_peaks / env_peaks are already
    # sorted strongest-first.
    if psd_peaks and env_peaks:
        # Compare each PSD mode with its NEAREST envelope estimate, not strongest
        # against strongest. With two modes present the two methods can rank them
        # differently — PSD weights total energy, the envelope weights peak
        # amplitude — so a strongest-vs-strongest test compares different modes
        # and reports DISAGREE on data where every mode actually matches.
        f_psd = psd_peaks[0][0]
        env_fs = [f for f, _ in env_peaks]
        matched = []
        for f, _ in psd_peaks:
            nearest = min(env_fs, key=lambda e: abs(e - f))
            matched.append((f, nearest, abs(nearest - f) / f))
        f_env = min(env_fs, key=lambda e: abs(e - f_psd))
        agree = all(rel < 0.15 for _, _, rel in matched)
        print("\n[Cross-check]      (each PSD mode vs its nearest envelope estimate)")
        for fp, fe, rel in matched:
            mark = "OK" if rel < 0.15 else "MISMATCH"
            print(f"    PSD {fp:6.2f} Hz  vs  envelope {fe:6.2f} Hz   "
                  f"{rel*100:5.1f}%  [{mark}]")

        # Group sidebands of the same resonance before calling anything "the
        # fundamental". Taking the raw lowest peak picks a sideband and biases f1
        # low by a few percent (see toolkit_common.group_peaks_into_modes).
        modes = tk.group_peaks_into_modes(
            [{"f_hz": f, "power": p} for f, p in psd_peaks])
        f_fundamental = modes[0]["f_hz"] if modes else f_psd
        if modes:
            print("\n[Modes]            (sidebands of one resonance merged)")
            for m in modes:
                extra = (f"  [{m['n_peaks_merged']} peaks merged, "
                         f"{m['f_span'][0]:.2f}-{m['f_span'][1]:.2f} Hz]"
                         if m["n_peaks_merged"] > 1 else "")
                print(f"    f = {m['f_hz']:6.2f} Hz{extra}")
        print("\n" + "-" * 64)
        print(f"  Dominant resonance:  PSD {f_psd:.2f} Hz | envelope {f_env:.2f} Hz"
              f"  -> {'AGREE (high confidence)' if agree else 'DISAGREE (treat as low confidence; inspect --plot)'}")
        print(f"  Lowest detected peak (candidate fundamental f1): {f_fundamental:.2f} Hz")
        print(f"  Simulation assumes f1 = 9.42 Hz (Johnson benchmark, matrices.py).")
        print(f"  Ratio measured/simulated ≈ {f_fundamental / 9.42:.2f}  "
              f"(!= 1 quantifies the modelling gap; see the scaling report).")

        # A peak close to a search edge is suspect: the true resonance may lie
        # outside the window with only its flank visible inside. The margin is
        # relative to the peak's own frequency, not the band span.
        for f, _ in psd_peaks:
            edge = tk.near_band_edge(f, args.f0, args.f1)
            if edge == "low":
                print(f"\n  ** WARNING: peak at {f:.2f} Hz sits near the LOW edge "
                      f"({args.f0:.2f} Hz). The real mode may be below the search "
                      "band. Re-run with a lower --f0. **")
                break
            if edge == "high":
                print(f"\n  ** WARNING: peak at {f:.2f} Hz sits near the HIGH edge "
                      f"({args.f1:.2f} Hz). The real mode may be above the search "
                      "band — this is the failure --full-band exists to prevent. **")
                break

        if not args.full_band:
            print("\n  Note: this was a BAND-LIMITED search. If f1 has never been "
                  "measured on this rig, re-run with --full-band before trusting "
                  "the number above.")

        print(f"\n  Record it:  python3 rig_config.py --set-f1 {f_fundamental:.3f} "
              f'--note "sweep {sweep_f0}-{sweep_f1} Hz"')

    if args.plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(2, 1, figsize=(10, 7))
        ax[0].semilogy(fb, pb, "k")
        for f, _ in psd_peaks:
            ax[0].axvline(f, color="r", ls="--", alpha=0.6)
        ax[0].set(title="Welch PSD over swept band", xlabel="Hz", ylabel="PSD")
        ax[1].plot(fmap, env, "b", lw=0.8)
        for f, _ in env_peaks:
            ax[1].axvline(f, color="r", ls="--", alpha=0.6)
        ax[1].set(title="Response envelope vs swept frequency",
                  xlabel="drive freq (Hz)", ylabel="|analytic|")
        fig.tight_layout()
        out = os.path.splitext(args.csv)[0] + "_sweep.png"
        fig.savefig(out, dpi=120)
        print(f"\nPlot written to {out}")


if __name__ == "__main__":
    main()

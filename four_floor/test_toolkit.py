"""
test_toolkit.py — Known-answer tests for the characterisation toolkit
======================================================================
Every test builds a synthetic signal whose true answer is known ANALYTICALLY,
independently of the code under test, then checks the toolkit recovers it. A pass
means the maths is right, not merely that it ran without raising.

This exists because two of these tests failed on first write and caught real
bugs:
  * log-decrement was reading peaks of the Hilbert ENVELOPE, which is smooth and
    monotonic for a decaying sinusoid and therefore has no per-cycle peaks at
    all — it was measuring noise ripple;
  * the noise-floor cut took the LAST sample above the floor, but late noise
    spikes cross back over it, so ~16 s of pure noise entered a fit of a 3.6 s
    decay and biased zeta down by 3x.

Neither was visible from reading the output on real data, where the true zeta is
unknown. Run after any change to toolkit_common.py:

    python3 test_toolkit.py            # exit 0 = all pass
"""
import sys

import numpy as np
from scipy.signal import bilinear, chirp, lfilter

import config
import toolkit_common as tk

FS = config.FS
fails = []


def check(name, got, want, tol, unit=""):
    ok = np.isfinite(got) and abs(got - want) <= tol
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: got {got:.4f}{unit}, "
          f"want {want:.4f}{unit} (+/-{tol}{unit})")
    if not ok:
        fails.append(name)


def section(title):
    print("\n" + "=" * 68)
    print(title)
    print("=" * 68)


# ─────────────────────────────────────────────
section("1. PEAK LOCATION — tone deliberately BETWEEN Welch bins")
# 12.37 Hz falls between bins, so a bin-snapped answer is visibly wrong and only
# sub-bin parabolic interpolation recovers it.
t = np.arange(60 * FS) / FS
F_TRUE = 12.37
x = np.sin(2 * np.pi * F_TRUE * t) + 0.01 * np.random.RandomState(0).randn(len(t))
est = tk.estimate_modal_frequency(x, fs=FS)
bin_hz = float(est["freqs"][1] - est["freqs"][0])
print(f"  Welch bin spacing = {bin_hz:.4f} Hz")
check("refined peak", est["f1"], F_TRUE, 0.02, " Hz")

# ─────────────────────────────────────────────
section("2. RINGDOWN — synthetic free decay with KNOWN zeta")
for ZETA_TRUE, FN in ((0.02, 11.0), (0.05, 8.0), (0.01, 20.0), (0.025, 28.0)):
    t = np.arange(20 * FS) / FS
    wn = 2 * np.pi * FN
    wd = wn * np.sqrt(1 - ZETA_TRUE ** 2)
    decay = np.exp(-ZETA_TRUE * wn * t) * np.sin(wd * t)
    sig = np.concatenate([np.zeros(2 * FS), decay])          # quiet before the tap
    sig = sig + 1e-4 * np.random.RandomState(1).randn(len(sig))
    r = tk.analyze_ringdown(sig, fs=FS)
    print(f"\n  --- true zeta={ZETA_TRUE}, fn={FN} Hz ---")
    if "error" in r:
        print(f"  FAIL  {r['error']}")
        fails.append(f"ringdown zeta={ZETA_TRUE}")
        continue
    check("  f_d", r["f_d"], FN * np.sqrt(1 - ZETA_TRUE ** 2), 0.15, " Hz")
    check("  zeta_logdec", r["zeta_logdec"], ZETA_TRUE, ZETA_TRUE * 0.25)
    check("  zeta_envfit", r["zeta_envfit"], ZETA_TRUE, ZETA_TRUE * 0.25)
    print(f"        R^2 = {r['r2']:.4f} (want > 0.98), "
          f"agree = {r['agree']}, peaks = {r['n_peaks']}")
    if r["r2"] < 0.98:
        fails.append(f"r2 zeta={ZETA_TRUE}")

# ─────────────────────────────────────────────
section("2b. RINGDOWN with a NON-MONOTONIC decay (real-data regression)")
# Real decays tick upward by fractions of a percent from noise and mode beating.
# A "strictly monotonic leading run" guard truncated a 94-peak decay from this rig
# to 3 peaks, because peak 4 exceeded peak 3 by 0.16%, and zeta came out 2.2x too
# high. This reproduces that shape: a clean decay plus a weak second mode that
# makes the peak envelope beat.
ZETA_TRUE, FN = 0.006, 8.11
t = np.arange(30 * FS) / FS
wn = 2 * np.pi * FN
main = np.exp(-ZETA_TRUE * wn * t) * np.sin(wn * np.sqrt(1 - ZETA_TRUE ** 2) * t)
beat = 0.04 * np.exp(-0.02 * 2 * np.pi * 8.6 * t) * np.sin(2 * np.pi * 8.6 * t)
sig = np.concatenate([np.zeros(FS), main + beat])
sig = sig + 2e-4 * np.random.RandomState(7).randn(len(sig))
r = tk.analyze_ringdown(sig, fs=FS)
if "error" in r:
    print(f"  FAIL  {r['error']}")
    fails.append("non-monotonic ringdown")
else:
    check("f_d", r["f_d"], FN, 0.2, " Hz")
    check("zeta_logdec", r["zeta_logdec"], ZETA_TRUE, ZETA_TRUE * 0.35)
    print(f"        peaks used = {r['n_peaks']} (a monotonic-run guard would use ~3)")
    if r["n_peaks"] < 20:
        print(f"  FAIL  only {r['n_peaks']} peaks used — the decay was truncated")
        fails.append("ringdown peak truncation")

section("3. HALF-POWER ZETA on a true 2nd-order resonance")
# White noise through a resonance gives a physically correct response spectrum.
ZETA_TRUE, FN = 0.03, 10.0
wn = 2 * np.pi * FN
b, a = bilinear([wn ** 2], [1, 2 * ZETA_TRUE * wn, wn ** 2], fs=FS)
resp = lfilter(b, a, np.random.RandomState(2).randn(120 * FS))
freqs, psd = tk.raw_psd(resp, FS)
pk = tk.find_spectral_peaks(freqs, psd, 1, 100, n_peaks=1)
z_hp = tk.half_power_zeta(freqs, psd, pk[0]["f_hz"])
check("peak freq", pk[0]["f_hz"], FN, 0.3, " Hz")
# Welch smoothing biases half-power HIGH by design; assert the ballpark only.
# This bias is exactly why ringdown is the primary damping estimator.
check("half-power zeta", z_hp, ZETA_TRUE, ZETA_TRUE * 0.8)
print(f"  (bias vs true: {(z_hp - ZETA_TRUE) / ZETA_TRUE * 100:+.0f}% — expected)")

# ─────────────────────────────────────────────
section("4. RMS / DC / band energy")
t = np.arange(10 * FS) / FS
x = 0.5 + 2.0 * np.sin(2 * np.pi * 7 * t)       # DC 0.5 g, amp 2 -> AC RMS 2/sqrt2
check("rms (AC only)", tk.rms(x), 2 / np.sqrt(2), 0.01, " g")
check("dc offset", tk.dc_offset(x), 0.5, 0.001, " g")
check("7 Hz share of 5-15 Hz", tk.band_share(x, FS, 5, 15), 1.0, 0.02)

# ─────────────────────────────────────────────
section("5. CSV round-trip in the standard _raw format")
import os
p = os.path.join(tk.HERE, ".test_roundtrip_raw.csv")
w = [np.random.RandomState(3).randn(config.N_SAMPLES) for _ in range(3)]
with open(p, "w") as fh:
    fh.write(tk.raw_csv_header() + "\n")
    for i, ww in enumerate(w):
        tk.append_window(fh, f"{1000.0 + i:.3f}", ww)
series, n = tk.load_raw_series(p)
os.remove(p)
if n != 3 or len(series) != 3 * config.N_SAMPLES:
    fails.append("csv round-trip shape")
    print("  FAIL shape")
else:
    err = float(np.max(np.abs(series - np.concatenate(w))))
    print(f"  PASS  3 windows round-tripped, max error {err:.2e} (6 sig-fig storage)")
    if err > 1e-4:
        fails.append("csv round-trip precision")

# ─────────────────────────────────────────────
section("6. SIDEBAND MERGING — the lowest PEAK is not the lowest MODE")
# One resonance produces several PSD maxima. Ungrouped, "lowest peak = f1" picks
# a sideband and biases f1 low by a few percent.
peaks = [{"f_hz": 27.3, "power": 6.7e-3}, {"f_hz": 28.3, "power": 8.8e-3},
         {"f_hz": 30.0, "power": 1.4e-3}, {"f_hz": 51.0, "power": 4.0e-3}]
modes = tk.group_peaks_into_modes(peaks)
print(f"  4 peaks -> {len(modes)} modes: {[round(m['f_hz'], 2) for m in modes]}")
check("lowest mode (not lowest peak)", modes[0]["f_hz"], 28.3, 0.01, " Hz")
if len(modes) != 2:
    fails.append("mode grouping count")

# ─────────────────────────────────────────────
section("7. BAND-EDGE TEST is relative to the peak, not the span")
# Under --full-band (0.5-450 Hz), 10% of the SPAN is 45 Hz, which would flag
# every real mode below 45 Hz as 'near the low edge'.
check_cases = [
    ("28 Hz in 0.5-450 (full band)", tk.near_band_edge(28.0, 0.5, 450.0), None),
    # "Near" means the peak's own flank is clipped by the edge, i.e. the gap is
    # small relative to the peak frequency. 0.52 Hz against a 0.5 Hz edge is a gap
    # of 0.02 Hz on a 0.052 Hz margin -> clipped. A peak at 1.0 Hz sits 50% of its
    # own frequency clear of the same edge and is NOT clipped.
    ("0.52 Hz in 0.5-450 (truly low)", tk.near_band_edge(0.52, 0.5, 450.0), "low"),
    ("1.0 Hz in 0.5-450 (clear of edge)", tk.near_band_edge(1.0, 0.5, 450.0), None),
    ("440 Hz in 0.5-450 (truly high)", tk.near_band_edge(440.0, 0.5, 450.0), "high"),
]
for name, got, want in check_cases:
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: got {got!r}, want {want!r}")
    if not ok:
        fails.append(name)

# ─────────────────────────────────────────────
section("8. FULL-BAND recovery — the failure --full-band exists to prevent")
# A rig whose real f1 is 28 Hz, searched with the old 1-15 Hz assumption.
t = np.arange(60 * FS) / FS
x = np.sin(2 * np.pi * 28.0 * t) + 0.05 * np.random.RandomState(4).randn(len(t))
narrow = tk.estimate_modal_frequency(x, fs=FS, f_lo=1, f_hi=15)
wide = tk.estimate_modal_frequency(x, fs=FS)          # defaults to full_band()
print(f"  band-limited 1-15 Hz -> f1 = {narrow['f1']:.2f} Hz "
      f"({len(narrow['peaks'])} peaks)   <- misses it entirely")
print(f"  --full-band          -> f1 = {wide['f1']:.2f} Hz   <- correct (28.00)")
check("full-band f1", wide["f1"], 28.0, 0.1, " Hz")

# ─────────────────────────────────────────────
section("9. SWEPT capture end-to-end — chirp through a known resonance")
# Uses scipy.chirp, which integrates phase properly. Writing sin(2*pi*f(t)*t) by
# hand gives instantaneous frequency f(t) + t*f'(t) — DOUBLE the intended rate.
T = 120.0
t = np.arange(int(T * FS)) / FS
drive = chirp(t, f0=1.0, f1=40.0, t1=T, method="linear")
FN, ZETA = 28.0, 0.03
wn = 2 * np.pi * FN
b, a = bilinear([wn ** 2], [1, 2 * ZETA * wn, wn ** 2], fs=FS)
resp = lfilter(b, a, drive) + 0.02 * np.random.RandomState(5).randn(len(t))
est = tk.estimate_modal_frequency(resp, fs=FS)
check("swept f1", est["f1"], FN, 0.5, " Hz")
print(f"  ({len(est['peaks'])} peaks -> {len(est['modes'])} modes)")
print("  NOTE: a 120 s sweep resolves f1 to roughly +/-0.5 Hz here (~2%), which is "
      "the same order as the linearity tolerance — so a marginal linearity "
      "verdict needs repeat sweeps, not one capture.")

# ─────────────────────────────────────────────
section("10. MULTI-MODE extraction — all three modes from one tap")
t = np.arange(20 * FS) / FS
true_modes = [(2.94, 0.06), (8.08, 0.02), (12.16, 0.04)]
sig = np.zeros_like(t)
for f, z in true_modes:
    wn = 2 * np.pi * f
    sig += np.exp(-z * wn * t) * np.sin(wn * np.sqrt(1 - z ** 2) * t)
sig = np.concatenate([np.zeros(FS), sig]) + 2e-4 * np.random.RandomState(11).randn(len(t) + FS)
got = tk.analyze_modes(sig, fs=FS, targets=[2.94, 8.08, 12.16])
for m, (f, z) in zip(got, true_modes):
    check(f"mode {f} Hz", m["f_d"], f, f * 0.01, " Hz")
    if not m["ok"]:
        print(f"  FAIL  mode {f} not resolved")
        fails.append(f"mode {f} unresolved")

# ─────────────────────────────────────────────
section("11. WELCH TEST — detects a real shift, ignores none")
rng = np.random.RandomState(12)
base = 2.940 + 0.003 * rng.randn(5)
shifted = 2.880 + 0.003 * rng.randn(5)
r = tk.welch_test(base, shifted)
check("detected shift", r["shift"], -0.060, 0.01, " Hz")
if not r["significant"]:
    print("  FAIL  real -0.06 Hz shift called not significant")
    fails.append("welch missed real shift")
# no-shift case must NOT flag
null = tk.welch_test(2.94 + 0.05 * rng.randn(5), 2.94 + 0.05 * rng.randn(5))
print(f"  null case: shift {null['shift']:+.4f} Hz, significant={null['significant']} "
      f"(want False), min-detectable {null['t_crit']*null['se']:.4f} Hz")
if null["significant"]:
    fails.append("welch false positive on null")

# ─────────────────────────────────────────────
print("\n" + "=" * 68)
print(f"RESULT: {'ALL PASS' if not fails else f'{len(fails)} FAILURE(S): ' + ', '.join(fails)}")
print("=" * 68)
sys.exit(1 if fails else 0)

"""
monitor.py — Acquisition + inference loop
============================================
Runs for a fixed duration (from the experiment session), sampling a window
every config.INFERENCE_PERIOD_S seconds, classifying it with SHM_PINN, and
logging:

  1. A detailed per-window CSV (one row per inference) — logs/<run filename>
  2. A raw-signal CSV (one row per inference, full raw window) —
     logs/<run filename, "_raw" suffix> — kept separate from (1) so the
     DI/alpha summary stays easy to skim while the full window is still
     available for offline PSD work (different nperseg, windowing
     function, multitaper, etc.).
  3. One summary row appended to logs/run_index.csv, mirroring the columns
     of the Experiment Log's "6. Data Recording" sheet, so results can be
     copy-pasted straight back into the spreadsheet.
"""

import csv
import os
import time
from datetime import datetime

import numpy as np
import torch

import config
from classification import classify   # shared policy — also used by shm_toolkit

# Where the acquisition node lives, used only to print a helpful scp command when
# the weights file is missing. Override with SHM_NODE_TARGET. The default is the
# host this project was developed against.
NODE_TARGET = os.environ.get(
    "SHM_NODE_TARGET", "pi@sensor.local:~/Building_Sensor/four_floor/")

from experiment_session import RunConfig
from live_features import to_model_input
from pinn.pinn_model import SHM_PINN

# The neopixel/rpi_ws281x LED library needs direct /dev/mem access, which
# only root has. If it's denied, the underlying C driver SEGFAULTS instead
# of raising a catchable Python exception (this bit us once already — the
# process crashed mid-run rather than printing a clean error). So check for
# root FIRST and skip the LED entirely rather than let that driver run
# without permission at all.
LED_AVAILABLE = False
if os.geteuid() != 0:
    print("LED: unavailable (not running as root — LED needs /dev/mem access; "
          "run with sudo for LED support). Terminal output only.")
else:
    try:
        import board
        import neopixel
        pixel = neopixel.NeoPixel(board.D18, 1, brightness=0.4)
        LED_AVAILABLE = True
    except Exception as e:
        print(f"LED: unavailable ({type(e).__name__}). Terminal output only.")


def set_led(colour: tuple) -> None:
    if not LED_AVAILABLE:
        return
    try:
        pixel[0] = colour
        pixel.show()
    except Exception:
        pass


def _make_simulated_source():
    """Synthetic building-vibration signal — no hardware required."""
    def get_window():
        t = np.linspace(0, config.N_SAMPLES / config.FS, config.N_SAMPLES)
        return (0.002 * np.sin(2 * np.pi * 2.0 * t) +
                0.001 * np.sin(2 * np.pi * 5.0 * t) +
                0.0005 * np.sin(2 * np.pi * 8.5 * t) +
                np.random.normal(0, 0.0003, config.N_SAMPLES))

    def get_timestamp():
        return datetime.now()

    def close():
        pass

    return get_window, get_timestamp, close


def _make_live_source():
    """Real ADXL345 + DS3231 hardware source."""
    from sensor import ADXL345, DS3231, collect_window

    print("Initialising ADXL345...")
    accel = ADXL345()

    print("Initialising DS3231 RTC...")
    rtc = DS3231(bus=config.DS3231_I2C_BUS)
    try:
        rtc.sync_to_system_time()
    except Exception:
        print("  Warning: RTC sync skipped (no accurate time source available).")

    def get_window():
        return collect_window(accel, n_samples=config.N_SAMPLES,
                               sample_rate=config.FS, axis=config.RECORDED_AXIS)

    rtc_warned = False

    def get_timestamp():
        # Falls back to the Pi's system clock if the RTC drops out mid-run
        # (e.g. a loose I2C connection) rather than crashing the whole run —
        # timestamps still get logged, just from a less independent source.
        nonlocal rtc_warned
        try:
            return rtc.get_datetime()
        except Exception as e:
            if not rtc_warned:
                print(f"  Warning: DS3231 read failed ({e}). "
                      "Falling back to system clock for timestamps.")
                rtc_warned = True
            return datetime.now()

    def close():
        accel.close()
        try:
            rtc.close()
        except Exception:
            pass

    return get_window, get_timestamp, close


def _load_model() -> SHM_PINN:
    if not config.WEIGHTS_PATH.exists():
        raise FileNotFoundError(
            f"\nWeights file not found: {config.WEIGHTS_PATH}\n"
            "Copy it to the node, e.g.:\n"
            f"  scp /path/to/shm_pinn_weights.pth {NODE_TARGET}\n"
            "Set the SHM_NODE_TARGET environment variable to change the host "
            "shown here."
        )
    model = SHM_PINN(n_frequency_bins=config.N_FREQ_BINS)
    model.load_state_dict(torch.load(str(config.WEIGHTS_PATH), map_location="cpu"))
    model.eval()
    print(f"Loaded SHM_PINN — {sum(p.numel() for p in model.parameters()):,} parameters")
    return model


def _append_run_index_row(run_cfg: RunConfig, run_start: datetime,
                           mean_alpha_at_sensor: float, worst_di: float,
                           worst_status: str) -> None:
    is_new = not config.RUN_INDEX_CSV.exists()
    with open(config.RUN_INDEX_CSV, "a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow([
                "Run ID", "Timestamp", "Raw Accel File",
                "Alpha (a)", "DI", "Classification",
                "File Naming Convention", "Ground Truth Notes",
            ])
        writer.writerow([
            run_cfg.run.run_id_str,
            run_start.strftime("%Y-%m-%d %H:%M:%S"),
            run_cfg.run.filename,
            f"{mean_alpha_at_sensor:.4f}",
            f"{worst_di:.4f}",
            worst_status,
            run_cfg.run.filename,
            run_cfg.run.ground_truth_notes,
        ])


def run_experiment(run_cfg: RunConfig, live: bool, no_model: bool = False,
                    period_s: float = None) -> None:
    """
    Execute one full experiment run per the Experiment Log's Test Matrix.

    Args:
        no_model:  ACQUISITION-ONLY mode. Skips loading SHM_PINN, skips inference
                   and the LED, and just records raw acceleration windows +
                   timestamps. Use this when you are collecting data to process
                   later and there are no trained weights on the Pi — the model
                   is not needed to capture raw signal, and a run should not be
                   blocked by its absence. The detail CSV keeps its full header
                   so downstream code sees a consistent schema; the alpha/DI
                   columns are simply written empty.
        period_s:  Seconds between the START of consecutive windows. Defaults to
                   config.INFERENCE_PERIOD_S (5 s). Note a window is
                   config.N_SAMPLES/config.FS = 4 s long, so the default leaves a
                   1 s GAP between windows — fine for per-window Welch PSDs (each
                   window is independent), wrong if you later want a continuous
                   time series. Pass --period 4 for back-to-back windows.
    """
    config.LOG_DIR.mkdir(exist_ok=True)

    if period_s is None:
        period_s = config.INFERENCE_PERIOD_S

    print("=" * 60)
    print(f"{run_cfg.run.run_id_str}  [{'LIVE' if live else 'SIMULATION'} MODE"
          f"{' | ACQUISITION ONLY' if no_model else ''}]")
    print(f"{run_cfg.run.ground_truth_notes}")
    print("=" * 60)

    get_window, get_timestamp, close_source = (
        _make_live_source() if live else _make_simulated_source()
    )

    if no_model:
        model = None
        print("No-model mode — recording raw acceleration only. "
              "No inference, no LED, no alpha/DI.")
    else:
        model = _load_model()
        set_led(config.BLUE)

    detail_path = run_cfg.filepath
    detail_file = open(detail_path, "w", newline="")
    writer = csv.writer(detail_file)
    writer.writerow([
        "timestamp", "mode", "status", "global_DI",
        "alpha_1", "alpha_2", "alpha_3", "alpha_4",
        "DI_1", "DI_2", "DI_3", "DI_4",
    ])
    detail_file.flush()
    print(f"Logging detailed samples to: {detail_path}")

    # Raw signal file — one row per inference window: timestamp + every raw
    # sample in that window (config.N_SAMPLES columns, ~4000 for the default
    # config). Separate file from the detail CSV above.
    raw_path = detail_path.with_name(detail_path.stem + "_raw" + detail_path.suffix)
    raw_file = open(raw_path, "w", newline="")
    raw_writer = csv.writer(raw_file)
    raw_writer.writerow(["timestamp"] + [f"sample_{i}" for i in range(config.N_SAMPLES)])
    raw_file.flush()
    print(f"Logging raw signal windows to: {raw_path}")

    sensor_idx = run_cfg.run.sensor_floor - 1
    run_start = datetime.now()
    alpha_history, di_history, status_history = [], [], []
    n_windows = 0          # counted separately from alpha_history, which stays
                           # empty in no-model mode

    print(f"\nRunning for {run_cfg.duration_s}s — press Ctrl+C to stop early.")
    print(f"Window: {config.N_SAMPLES / config.FS:.1f}s @ {config.FS}Hz | "
          f"period: {period_s:.1f}s\n")
    if no_model:
        print(f"{'Timestamp':<22} {'Window':<8} {'RMS (g)':<10} {'Peak (g)':<10}")
        print("-" * 52)
    else:
        print(f"{'Timestamp':<22} {'Status':<10} {'Max DI':<8} "
              f"{'a1':<8} {'a2':<8} {'a3':<8} {'a4':<8}")
        print("-" * 72)

    try:
        while (datetime.now() - run_start).total_seconds() < run_cfg.duration_s:
            t0 = time.time()

            window = get_window()
            timestamp = get_timestamp()
            ts = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            n_windows += 1

            if no_model:
                # No inference. Print a cheap live health readout instead, so you
                # can see on the bench that the rig is actually shaking and the
                # sensor is not railed or dead.
                rms = float(np.sqrt(np.mean(np.square(window))))
                peak = float(np.max(np.abs(window)))
                print(f"{ts}  {n_windows:<8} {rms:<10.4f} {peak:<10.4f}")

                # Same 12-column schema, alpha/DI left empty.
                writer.writerow([ts, "LIVE" if live else "SIM", "NO_MODEL", ""]
                                + [""] * 8)
            else:
                x = to_model_input(window, n_floors=run_cfg.n_floors)
                x_tensor = torch.tensor(x).unsqueeze(0)

                with torch.no_grad():
                    alphas = model(x_tensor).numpy()[0]

                colour, status, global_di, dis = classify(alphas)
                set_led(colour)

                print(f"{ts}  {status:<10} {global_di:<8.2f} "
                      f"{alphas[0]:<8.4f} {alphas[1]:<8.4f} "
                      f"{alphas[2]:<8.4f} {alphas[3]:<8.4f}")

                writer.writerow([
                    ts, "LIVE" if live else "SIM", status, f"{global_di:.4f}",
                    f"{alphas[0]:.4f}", f"{alphas[1]:.4f}",
                    f"{alphas[2]:.4f}", f"{alphas[3]:.4f}",
                    f"{dis[0]:.4f}", f"{dis[1]:.4f}",
                    f"{dis[2]:.4f}", f"{dis[3]:.4f}",
                ])

                alpha_history.append(alphas[sensor_idx])
                di_history.append(global_di)
                status_history.append(status)

            detail_file.flush()

            raw_writer.writerow([ts] + window.tolist())
            raw_file.flush()

            elapsed = time.time() - t0
            if elapsed < period_s:
                time.sleep(period_s - elapsed)

    except KeyboardInterrupt:
        print("\nStopped early.")

    finally:
        set_led((0, 0, 0))
        detail_file.close()
        raw_file.close()
        close_source()

    if no_model:
        # The run_index row is built from alpha/DI, which do not exist here.
        # Record the run anyway — a raw-only run is still a run, and the Test
        # Matrix bookkeeping is the whole point of the logged mode.
        if n_windows and not run_cfg.is_test:
            _append_run_index_row(
                run_cfg, run_start,
                mean_alpha_at_sensor=float("nan"),
                worst_di=float("nan"),
                worst_status="NO_MODEL",
            )
            print(f"\n{n_windows} raw windows -> {raw_path}")
            print(f"Summary row appended to: {config.RUN_INDEX_CSV}")
        elif n_windows:
            print(f"\n{n_windows} raw windows -> {raw_path}")
            print("Test run — not added to run_index.csv.")
        else:
            print("\nNo samples were collected — nothing logged.")
        return

    if alpha_history and run_cfg.is_test:
        print("\nTest run — not added to run_index.csv.")
    elif alpha_history:
        worst_idx = int(np.argmax(di_history))
        _append_run_index_row(
            run_cfg, run_start,
            mean_alpha_at_sensor=float(np.mean(alpha_history)),
            worst_di=di_history[worst_idx],
            worst_status=status_history[worst_idx],
        )
        print(f"\nSummary row appended to: {config.RUN_INDEX_CSV}")
    else:
        print("\nNo samples were collected — nothing logged.")

    print(f"Detailed data saved to: {detail_path}")
    print(f"Raw signal windows saved to: {raw_path}")
    print("Done.")

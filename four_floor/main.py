"""
main.py — PINN Structural Health Monitor (entry point)
=========================================================
Run from Building_Sensor/four_floor/:

    python3 main.py            # simulation mode (no hardware needed)
    python3 main.py --live     # live mode (requires ADXL345 + DS3231 wired up)
    python3 main.py --live --test          # quick sanity-check run, no Test Matrix bookkeeping
    python3 main.py --live --test --duration 10   # even shorter test run

Before acquisition starts you'll be asked whether this is a test run or a
logged experiment run. Experiment runs ask a few more questions (how many
floors, which floor the sensor is on, where the damage is, severity) so the
run is automatically matched up against the Experiment Log's Test Matrix
and named consistently (see experiment_session.py / test_matrix.py). Test
runs skip all of that — just sensor floor + duration — and are saved to
logs/test_runs/ instead of touching run_index.csv.

Everything else — hardware drivers, signal processing, the acquisition
loop — lives in sensor.py / preprocessing.py / monitor.py. This file just
wires them together.
"""

import argparse

from experiment_session import prompt_experiment_setup
from monitor import run_experiment


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true",
                         help="Use real hardware (ADXL345 + DS3231)")
    parser.add_argument("--test", action="store_true",
                         help="Skip straight into a quick test run "
                              "(no Test Matrix bookkeeping)")
    parser.add_argument("--duration", type=int, default=None,
                         help="Override run duration in seconds "
                              "(skips the duration prompt)")
    args = parser.parse_args()

    run_cfg = prompt_experiment_setup(force_test=args.test,
                                       duration_override=args.duration)
    run_experiment(run_cfg, live=args.live)


if __name__ == "__main__":
    main()

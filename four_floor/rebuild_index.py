#!/usr/bin/env python3
"""
rebuild_index.py — Regenerate run_index.csv from the intact per-run detail CSVs.

Run it from inside the logs/ directory (or pass the logs path as arg 1):
    cd ~/Building_Sensor/four_floor/logs && python3 rebuild_index.py

Why: run_index.csv occasionally gets null-corrupted or loses a row when the Pi
writes it under load. The per-run detail CSVs are the source of truth, so this
rebuilds a clean, complete, correctly-sorted index from them at any time.

Assumes single-floor damage or baseline. The sensor floor is read from each
filename (R###_Floor<SENSOR>_...), so it works for any sensor position. If
multi-floor combos are added later, extend the phase/notes logic below.
"""
import os, csv, glob, re, statistics, sys

HEADER = ["Run ID", "Timestamp", "Raw Accel File", "Alpha (a)", "DI",
          "Classification", "File Naming Convention", "Ground Truth Notes"]

logs_dir = sys.argv[1] if len(sys.argv) > 1 else "."
os.chdir(logs_dir)

rows = []
for f in sorted(g for g in glob.glob("*/R*_*.csv") if not g.endswith("_raw.csv")):
    base = os.path.basename(f)
    parts = base.split("_")
    rid = parts[0]
    sensor = int(parts[1].replace("Floor", ""))   # sensor floor from R###_Floor<S>_...
    with open(f, newline="") as fh:
        data = list(csv.reader(fh))[1:]          # skip header
    if not data:
        print(f"  skip {rid}: no data rows"); continue
    alpha_sensor = [float(r[3 + sensor]) for r in data]   # alpha_<sensor>
    gdi = [float(r[3]) for r in data]                      # global_DI column
    worst = max(range(len(gdi)), key=lambda i: gdi[i])
    if "None-NoneBaseline" in base:
        note = (f"Baseline; Sensor at Floor {sensor}; "
                f"Damage: None (None (Baseline)); "
                f"Excitation: constant (see Excitation Params)")
    else:
        m = re.search(r"Floor(\d)-(\w+)", base.split("_", 2)[2])
        note = (f"Progressive - Single Floor; Sensor at Floor {sensor}; "
                f"Damage: Floor {m.group(1)} ({m.group(2)}); "
                f"Excitation: constant (see Excitation Params)")
    rows.append([rid, data[0][0], base,
                 f"{statistics.mean(alpha_sensor):.4f}",
                 f"{gdi[worst]:.4f}", data[worst][2], base, note])

rows.sort(key=lambda r: r[0])
with open("run_index.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(HEADER)
    w.writerows(rows)

nulls = open("run_index.csv", "rb").read().count(0)
print(f"Rebuilt run_index.csv: {len(rows)} rows, {nulls} null bytes")

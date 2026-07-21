# Lab Session Checklist — Shaking Table / PINN SHM Rig

Work top to bottom. **Do not skip the GATES** — each one exists because something
went wrong last session. If a gate fails, stop and fix it rather than collecting
more data.

---

## 0. Before touching the rig (5 min)

- [ ] Power up the Pi, connect (ethernet or hotspot), SSH in.
- [ ] Confirm the rogue service is still down:
      `systemctl is-enabled pinn-sensor.service ; systemctl is-active pinn-sensor.service`
      → must read `disabled` / `inactive`. If not: `sudo systemctl stop pinn-sensor.service && sudo systemctl mask pinn-sensor.service`
- [ ] Confirm nothing is running: `pgrep -af main.py` → must be empty.
- [ ] Start the Mac-side sync in a separate terminal (or plan to pull manually after each set).
- [ ] Check the Pi clock is right (`date`) — timestamps were 2 days out last time.

---

## 1. Hardware setup

- [ ] **Replace Blu-Tack with the rigid clip/screw bracket.** Compliant mounting
      attenuates low-frequency coupling and adds its own resonance.
- [ ] **Align the sensor axis with the shake direction.** Identify which ADXL345
      axis lies along the table's motion.
- [ ] Verify statically: the shake-direction axis should read **~0 g** at rest;
      the vertical axis reads ~1 g. If the recorded axis reads ~1 g, you're
      logging the wrong direction.
- [ ] Record the axis in the Experiment Log → *2. Sensor Config* →
      "Axis Measuring Primary Shake Direction" (currently blank).
- [ ] Update `monitor.py` / `collect_window(axis=...)` if the correct axis isn't `z`.
- [ ] Return the frame to **fully undamaged** (all screws torqued) for baseline.

---

## 2. Verify acquisition — GATE 1

- [ ] `python3 measure_sampling_rate.py`
- [ ] `python3 sensor.py --selftest`

**PASS if:** achieved rate ≈ the configured rate, inter-sample jitter is small
(std well under one sample interval), zero FIFO overruns.

**FAIL → stop.** Every spectrum you compute is invalid if sample timing isn't
uniform. Fix acquisition before anything else.

---

## 3. Find the rig's first mode — GATE 2

This is the measurement you have never made, and everything downstream depends on it.

- [ ] Set a **modest, fixed** drive amplitude. Write down Vpp and amplifier gain.
- [ ] Run a slow sine sweep as wide as the shaker allows (start 1 Hz → as high as
      it will go). Record it.
- [ ] `python3 sweep_analysis.py <sweep_raw.csv>`

**PASS if:** a clear resonance is identified, and both estimation methods
(PSD peak + envelope) agree.

**Record:** f₁ = ______ Hz, ζ ≈ ______ , higher modes = ______

**FAIL → adjust amplitude/band and repeat.** Do not proceed on a guessed f₁.

---

## 4. Set the excitation protocol

- [ ] Choose the drive to span the modal range — **swept sine ≈ 0.5×f₁ → 3×f₁**,
      or band-limited random. **Not a fixed 1 Hz tone** (far below resonance =
      quasi-static = no damage information).
- [ ] Set Vpp and amplifier gain. **Write them down. Mark the knobs. Do not touch
      them again for the whole campaign.**
- [ ] Enter both into Experiment Log → *3. Excitation Params*.
- [ ] Decide and record the damage mechanism precisely (e.g. "N turns loosened"),
      and fill in Experiment Log → *4. Damage Variable* (currently blank).

---

## 5. Pilot run — GATE 3 (the important one)

**Do not run the full matrix until this passes.** Last session 42 runs were
collected before the chain was found to be broken.

- [ ] 3 × baseline runs (undamaged), new excitation.
- [ ] 1 × obviously-damaged run (severe, single floor).

**PASS if all four hold:**
1. Modal peaks appear at the **same frequency in every window** of a run
   (wandering peaks = still measuring noise).
2. Baseline RMS is consistent across the 3 repeats (within ~±20%).
3. The damaged run shows a **shift in modal peak frequency** — not merely a
   change in amplitude.
4. Baseline and damaged classify **differently**.

**FAIL → stop and diagnose.** Collecting more runs will not fix it.

---

## 6. Only then: the damage matrix

Per run:
- [ ] `pgrep -af main.py` empty before launching (single-launch discipline).
- [ ] Enter the **true** floor numbers (sensor and damage).
- [ ] Run the set, wait for `=== ALL 3 RUNS COMPLETE ===`.
- [ ] RMS check vs the session baseline — flag anything beyond ±20%.
- [ ] Rebuild the index (`rebuild_index.py`) and sync to the Mac.
- [ ] Log excitation settings + any anomalies in the sheet.

Per session:
- [ ] Re-run a baseline at the **start of every session** to catch drift.

---

## 7. Data hygiene (lessons from last session)

- After **any disconnect**: `pgrep -af main.py` *before* relaunching — never start a
  second loop on top of a live one (this caused corrupted, out-of-order runs).
- The `run_index.csv` corrupts on write fairly often; don't hand-patch it, just run
  `rebuild_index.py` — it regenerates cleanly from the detail CSVs.
- Verify a set landed (12 windows in **both** detail and `_raw`) before moving the rig.
- Never edit anything under `logs/` by hand.

---

## Notes for this session

f₁ measured: ____________  Excitation: ____________  Gain/Vpp: ____________

Pilot result: PASS / FAIL — ______________________________________________

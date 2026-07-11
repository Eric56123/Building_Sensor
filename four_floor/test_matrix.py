"""
test_matrix.py — Programmatic version of the Experiment Log's "5. Test Matrix"
================================================================================
Regenerates the run plan (Run ID, sensor floor, damage floor(s), severity,
filename, ground-truth notes) from the same rules used to build the Excel
sheet, parameterised by n_floors so a rig running with fewer than 4 floors
still gets a sensible, consistent plan.

For n_floors=4 this reproduces the exact 192-row matrix in the Experiment
Log (verified row-for-row against R001, R004, R040, R046, R049 and R192).

This is deliberately independent of any Excel/pandas dependency — it's
pure Python so it runs on the Pi with nothing extra installed.
"""

from dataclasses import dataclass, field
from typing import Optional

import config


@dataclass
class TestRun:
    run_id: int
    phase: str
    sensor_floor: int
    damage_label: str      # e.g. "None", "Floor 1", "Floor 1+2", "Floor 1-4 (all)"
    severity: str           # "None (Baseline)", "Light", "Moderate", "Severe"
    repeat: int             # 1, 2 or 3
    repeats_total: int = 3
    is_test: bool = False    # True for ad-hoc test runs — not part of the Test Matrix
    is_custom: bool = False  # True for a user-chosen multi-floor combo not in the sheet
    timestamp_suffix: str = ""   # set for test/custom runs, keeps filenames unique

    @property
    def run_id_str(self) -> str:
        if self.is_test:
            return "TEST"
        if self.is_custom:
            return f"CUSTOM_{self.timestamp_suffix}"
        return f"R{self.run_id:03d}"

    @staticmethod
    def _compact(label: str) -> str:
        return (label.replace(" ", "")
                     .replace("(", "")
                     .replace(")", "")
                     .replace("+", "-"))

    @property
    def _has_reference_damage(self) -> bool:
        """True when a test run was given optional damage info (not N/A/None)."""
        return self.damage_label not in ("N/A", "None")

    @property
    def filename(self) -> str:
        if self.is_test:
            base = f"TEST_{self.timestamp_suffix}_Floor{self.sensor_floor}"
            if self._has_reference_damage:
                base += (f"_{self._compact(self.damage_label)}"
                         f"-{self._compact(self.severity)}")
            return base + ".csv"
        return (f"{self.run_id_str}_Floor{self.sensor_floor}_"
                 f"{self._compact(self.damage_label)}-{self._compact(self.severity)}.csv")

    @property
    def variable_group(self) -> str:
        """
        Folder name grouping every run that shares the same sensor floor +
        damage location + severity — real repeats, custom repeats, and
        (separately) test runs all land in a consistent, predictable place
        instead of one flat logs/ directory.
        """
        if self.is_test:
            return "test_runs"
        return (f"Floor{self.sensor_floor}_"
                 f"{self._compact(self.damage_label)}-{self._compact(self.severity)}")

    @property
    def ground_truth_notes(self) -> str:
        if self.is_test:
            base = (f"Test run (not part of the Test Matrix) — "
                    f"Sensor at Floor {self.sensor_floor}")
            if self._has_reference_damage:
                base += f"; Damage: {self.damage_label} ({self.severity})"
            return base
        return (f"{self.phase}; Sensor at Floor {self.sensor_floor}; "
                f"Damage: {self.damage_label} ({self.severity}); "
                f"Excitation: constant (see Excitation Params)")

    @property
    def notes(self) -> str:
        if self.is_test:
            return "Test run"
        if self.is_custom:
            return "Custom combination (not in original Test Matrix)"
        return f"Repeat {self.repeat}/{self.repeats_total}"


def make_test_run(sensor_floor: int, damage_label: str = "N/A",
                   severity: str = "N/A") -> TestRun:
    """
    A one-off run used for quick sanity checks — no Test Matrix bookkeeping,
    no run_index.csv entry. damage_label/severity are optional and purely
    for your own reference (shown in the console summary and folded into
    the filename) — they're never looked up against the Test Matrix.
    """
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return TestRun(run_id=0, phase="Test Run", sensor_floor=sensor_floor,
                   damage_label=damage_label, severity=severity,
                   repeat=1, repeats_total=1, is_test=True, timestamp_suffix=ts)


def floors_to_damage_label(damage_floors: list) -> str:
    """e.g. [1, 3] -> 'Floor 1+3' — the same label style used throughout."""
    return "Floor " + "+".join(str(f) for f in sorted(damage_floors))


def make_custom_run(sensor_floor: int, damage_label: str, severity: str) -> TestRun:
    """
    A real, logged run for a (sensor floor, damage location, severity)
    combination that isn't one of the 192 rows in the Experiment Log's Test
    Matrix — either because the damage location itself is a combination the
    operator picked directly (e.g. Floor 1+3, use floors_to_damage_label()
    to build the label), or because it's a location that IS in the sheet
    but at a severity the sheet didn't test (e.g. the sheet only tests
    Floor 1+2 at Moderate — this covers Floor 1+2 at Light or Severe too).
    """
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return TestRun(run_id=0, phase="Custom", sensor_floor=sensor_floor,
                   damage_label=damage_label, severity=severity,
                   repeat=1, repeats_total=1, is_custom=True, timestamp_suffix=ts)


def _multi_floor_combos(n_floors: int) -> list:
    """Damage-floor combinations used in the 'Progressive - Multi Floor' block."""
    combos = []
    if n_floors >= 2:
        combos.append("Floor 1+2")
    if n_floors >= 4:
        combos.append(f"Floor {n_floors - 1}+{n_floors}")
    if n_floors >= 2:
        combos.append(f"Floor 1-{n_floors} (all)")
    # de-duplicate while preserving order (matters for n_floors < 4, e.g. n=2
    # or n=3 where the pair combos can coincide with each other or with "all")
    seen, unique = set(), []
    for c in combos:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique


def build_test_matrix(n_floors: int = config.MAX_FLOORS) -> list:
    """
    Build the full run plan for a rig with `n_floors` floors.

    Sensor placement iterates top-down (n_floors, n_floors-1, ..., 1), matching
    the Experiment Log's convention of starting at the top floor.
    """
    if not (1 <= n_floors <= config.MAX_FLOORS):
        raise ValueError(f"n_floors must be between 1 and {config.MAX_FLOORS}")

    matrix = []
    run_id = 1
    severities = ["Light", "Moderate", "Severe"]

    for sensor_floor in range(n_floors, 0, -1):
        # 1. Baseline (3 repeats)
        for repeat in (1, 2, 3):
            matrix.append(TestRun(run_id, "Baseline", sensor_floor,
                                   "None", "None (Baseline)", repeat))
            run_id += 1

        # 2. Progressive - Single Floor
        for damage_floor in range(1, n_floors + 1):
            for severity in severities:
                for repeat in (1, 2, 3):
                    matrix.append(TestRun(run_id, "Progressive - Single Floor",
                                           sensor_floor, f"Floor {damage_floor}",
                                           severity, repeat))
                    run_id += 1

        # 3. Progressive - Multi Floor (Moderate only, per Experiment Log)
        for damage_label in _multi_floor_combos(n_floors):
            for repeat in (1, 2, 3):
                matrix.append(TestRun(run_id, "Progressive - Multi Floor",
                                       sensor_floor, damage_label, "Moderate", repeat))
                run_id += 1

    return matrix


def find_candidates(matrix: list, sensor_floor: int, damage_label: str,
                     severity: str) -> list:
    """All TestRuns (the 3 repeats) matching a given (sensor, damage, severity)."""
    return [r for r in matrix
            if r.sensor_floor == sensor_floor
            and r.damage_label == damage_label
            and r.severity == severity]


def damage_options(matrix: list, sensor_floor: int) -> list:
    """Ordered, de-duplicated damage-floor labels valid for this sensor floor."""
    seen, options = set(), []
    for r in matrix:
        if r.sensor_floor == sensor_floor and r.damage_label not in seen:
            seen.add(r.damage_label)
            options.append(r.damage_label)
    return options


def severity_options(matrix: list, sensor_floor: int, damage_label: str) -> list:
    """Ordered, de-duplicated severities valid for this sensor/damage combo."""
    seen, options = set(), []
    for r in matrix:
        if (r.sensor_floor == sensor_floor and r.damage_label == damage_label
                and r.severity not in seen):
            seen.add(r.severity)
            options.append(r.severity)
    return options


if __name__ == "__main__":
    # Quick self-check against the Experiment Log's 192-row matrix.
    m = build_test_matrix(4)
    print(f"Generated {len(m)} runs (expected 192)")
    checks = {1: "R001", 4: "R004", 40: "R040", 46: "R046", 49: "R049", 192: "R192"}
    for run_id, expected in checks.items():
        run = m[run_id - 1]
        status = "OK" if run.run_id_str == expected else "MISMATCH"
        print(f"  [{status}] run #{run_id}: {run.filename}  ({run.ground_truth_notes})")

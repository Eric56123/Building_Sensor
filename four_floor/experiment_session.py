"""
experiment_session.py — Interactive pre-run setup
====================================================
First asks whether this is a quick test run or a logged experiment run.

Test run: just asks sensor floor + duration, skips the Test Matrix
lookup entirely, and doesn't touch run_index.csv. For checking wiring,
LED behaviour, or that inference runs at all before committing to a
real, logged run.

Experiment run: asks the full set of questions needed to identify which
row of the Experiment Log's Test Matrix this run corresponds to:

  1. How many floors does the rig currently have? (<= 4)
  2. Which floor is the sensor mounted on?
  3. Where is the damage (if any)?
  4. What severity?

From those answers it looks up the matching entry in test_matrix.py,
auto-picks the next unused repeat (1/2/3) by checking what's already
in logs/, and returns a RunConfig with the exact filename and
ground-truth notes ready to drop into "6. Data Recording".
"""

from dataclasses import dataclass
from pathlib import Path

import config
from test_matrix import (TestRun, build_test_matrix, find_candidates,
                          damage_options, make_test_run,
                          make_custom_run, floors_to_damage_label)

CUSTOM_DAMAGE_OPTION = "Custom combination (choose specific floors)"


@dataclass
class RunConfig:
    run: TestRun
    n_floors: int
    duration_s: int
    is_test: bool = False

    @property
    def filepath(self) -> Path:
        """
        Every CSV lands in logs/<variable_group>/ — runs that share the same
        sensor floor + damage location + severity (real repeats, custom
        repeats, or the test_runs/ catch-all) end up grouped in the same
        folder instead of one flat logs/ directory.
        """
        group_dir = config.LOG_DIR / self.run.variable_group
        group_dir.mkdir(parents=True, exist_ok=True)
        return group_dir / self.run.filename


def _ask_int(prompt: str, low: int, high: int, default: int = None) -> int:
    suffix = f" [{default}]" if default is not None else ""
    while True:
        raw = input(f"{prompt}{suffix}: ").strip()
        if raw == "" and default is not None:
            return default
        if raw.isdigit() and low <= int(raw) <= high:
            return int(raw)
        print(f"  Please enter a number between {low} and {high}.")


def _ask_choice(prompt: str, options: list) -> str:
    print(prompt)
    for i, opt in enumerate(options, start=1):
        print(f"  {i}. {opt}")
    while True:
        raw = input(f"Choice [1-{len(options)}]: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print(f"  Please enter a number between 1 and {len(options)}.")


def _ask_multi_choice(prompt: str, options: list, min_choices: int = 2) -> list:
    """Same numbered-menu style as _ask_choice, but pick several by number."""
    print(prompt)
    for i, opt in enumerate(options, start=1):
        print(f"  {i}. {opt}")
    while True:
        raw = input(f"Choices (comma-separated, at least {min_choices}) "
                     f"[1-{len(options)}]: ").strip()
        try:
            idxs = sorted(set(int(x.strip()) for x in raw.split(",") if x.strip()))
        except ValueError:
            print(f"  Please enter comma-separated numbers, e.g. 1,3")
            continue
        if len(idxs) < min_choices:
            print(f"  Please choose at least {min_choices} options.")
            continue
        if any(i < 1 or i > len(options) for i in idxs):
            print(f"  Please enter numbers between 1 and {len(options)}.")
            continue
        return [options[i - 1] for i in idxs]


def _ask_yes_no(prompt: str, default: bool = True) -> bool:
    suffix = " [Y/n]" if default else " [y/N]"
    raw = input(f"{prompt}{suffix}: ").strip().lower()
    if raw == "":
        return default
    return raw.startswith("y")


def _already_logged_run_ids() -> set:
    """Run IDs that already have a CSV in logs/ (from a previous session)."""
    config.LOG_DIR.mkdir(exist_ok=True)
    done = set()
    for f in config.LOG_DIR.rglob("R*_*.csv"):   # rglob: files now live in
        run_id_str = f.name.split("_")[0]        # logs/<variable_group>/, not flat logs/
        done.add(run_id_str)
    return done


def _ask_multi_floor(n_floors: int) -> list:
    """
    Prompt for 2+ specific floors for a custom multi-floor damage combo —
    a numbered menu of floors, same style as every other choice in this
    session, just letting you pick several instead of one.
    """
    floor_options = [f"Floor {i}" for i in range(1, n_floors + 1)]
    chosen = _ask_multi_choice("Which floors are damaged?", floor_options,
                                min_choices=2)
    return sorted(int(label.split()[1]) for label in chosen)


def _prompt_test_run(default_duration: int = 15,
                      duration_override: int = None) -> RunConfig:
    """Minimal Q&A for a quick, unlogged sanity-check run."""
    print("\n" + "-" * 60)
    print("Test run — not logged to the Test Matrix or run_index.csv")
    print("-" * 60)

    n_floors = _ask_int(
        "How many floors does the rig currently have?",
        1, config.MAX_FLOORS, default=config.MAX_FLOORS,
    )
    sensor_floor = _ask_int(
        "Which floor is the sensor mounted on?", 1, n_floors, default=1,
    )

    damage_options_list = (["None"] + [f"Floor {i}" for i in range(1, n_floors + 1)]
                            + [CUSTOM_DAMAGE_OPTION])
    damage_label = _ask_choice(
        "Where is the damage for this run? (optional — for reference only, "
        "not logged to the Test Matrix)",
        damage_options_list,
    )
    if damage_label == "None":
        severity = "N/A"
    else:
        if damage_label == CUSTOM_DAMAGE_OPTION:
            damage_floors = _ask_multi_floor(n_floors)
            damage_label = "Floor " + "+".join(str(f) for f in damage_floors)
        severity = _ask_choice("Damage severity?", ["Light", "Moderate", "Severe"])

    if duration_override is not None:
        duration_s = duration_override
        print(f"Run duration: {duration_s}s (from --duration)")
    else:
        duration_s = _ask_int(
            "Run duration in seconds?", 1, 3600, default=default_duration,
        )

    run = make_test_run(sensor_floor, damage_label=damage_label, severity=severity)

    print("\n" + "-" * 60)
    print(f"Run ID:        {run.run_id_str}")
    print(f"Sensor floor:  {run.sensor_floor}  (of {n_floors})")
    if damage_label != "None":
        print(f"Damage:        {damage_label}  ({severity})")
    print(f"Filename:      logs/test_runs/{run.filename}")
    print(f"Duration:      {duration_s}s")
    print("-" * 60)

    return RunConfig(run=run, n_floors=n_floors, duration_s=duration_s, is_test=True)


def prompt_experiment_setup(force_test: bool = False,
                             duration_override: int = None) -> RunConfig:
    """
    Run the interactive Q&A and return a confirmed RunConfig.

    Args:
        force_test:        skip the "test or experiment?" question and go
                            straight into a test run (used by `main.py --test`).
        duration_override:  skip the duration prompt and use this value
                            instead (used by `main.py --duration N`).
    """
    print("=" * 60)
    print("Experiment setup")
    print("=" * 60)

    if force_test:
        return _prompt_test_run(duration_override=duration_override)

    run_type = _ask_choice(
        "Is this a test run or a logged experiment run?",
        ["Test run (quick check, not logged to the Test Matrix)",
         "Experiment run (logged against the Test Matrix)"],
    )
    if run_type.startswith("Test run"):
        return _prompt_test_run(duration_override=duration_override)

    while True:
        n_floors = _ask_int(
            "How many floors does the rig currently have?",
            1, config.MAX_FLOORS, default=config.MAX_FLOORS,
        )
        matrix = build_test_matrix(n_floors)

        sensor_floor = _ask_int(
            "Which floor is the sensor mounted on?", 1, n_floors
        )

        damage_label = _ask_choice(
            "Where is the damage for this run?",
            damage_options(matrix, sensor_floor) + [CUSTOM_DAMAGE_OPTION],
        )

        if damage_label == CUSTOM_DAMAGE_OPTION:
            # A combo the operator picks directly (e.g. Floor 1+3) rather
            # than one of the Test Matrix's fixed combos (1+2, top two, all).
            damage_floors = _ask_multi_floor(n_floors)
            damage_label = floors_to_damage_label(damage_floors)

        if damage_label == "None":
            # Baseline has no severity concept — it's just "undamaged".
            severity = "None (Baseline)"
        else:
            # Always offer all three severities — including for the fixed
            # multi-floor combos (Floor 1+2, etc.), which the Experiment Log
            # only tested at Moderate. Picking Light/Severe there (or any
            # combination the 192-row plan didn't cover) falls through to a
            # custom, ad-hoc logged run below rather than being blocked.
            severity = _ask_choice("Damage severity?", ["Light", "Moderate", "Severe"])

        candidates = find_candidates(matrix, sensor_floor, damage_label, severity)

        if not candidates:
            print(f"\n'{damage_label}' at '{severity}' isn't one of the Test "
                  "Matrix's 192 planned rows — logging this as a custom run "
                  "instead (still saved to run_index.csv, still grouped by "
                  "these same variables).")
            run = make_custom_run(sensor_floor, damage_label, severity)
        else:
            done_ids = _already_logged_run_ids()
            remaining = [r for r in candidates if r.run_id_str not in done_ids]

            if remaining:
                run = remaining[0]
            else:
                print("\nAll 3 repeats for this exact combination already have logs:")
                for r in candidates:
                    print(f"  {r.run_id_str}  ->  {r.filename}")
                if not _ask_yes_no("Re-run repeat 1 anyway and overwrite it?", default=False):
                    print("\nLet's pick a different combination.\n")
                    continue
                run = candidates[0]

        if duration_override is not None:
            duration_s = duration_override
            print(f"Run duration: {duration_s}s (from --duration)")
        else:
            duration_s = _ask_int(
                "Run duration in seconds?", 5, 3600,
                default=config.DEFAULT_RUN_DURATION_S,
            )

        print("\n" + "-" * 60)
        print(f"Run ID:        {run.run_id_str}")
        print(f"Phase:         {run.phase}")
        print(f"Sensor floor:  {run.sensor_floor}  (of {n_floors})")
        print(f"Damage:        {run.damage_label}  ({run.severity})")
        print(f"Repeat:        {run.notes}")
        print(f"Folder:        logs/{run.variable_group}/")
        print(f"Filename:      {run.filename}")
        print(f"Ground truth:  {run.ground_truth_notes}")
        print(f"Duration:      {duration_s}s")
        print("-" * 60)

        if _ask_yes_no("Start this run?", default=True):
            return RunConfig(run=run, n_floors=n_floors, duration_s=duration_s)

        print("\nLet's set it up again.\n")

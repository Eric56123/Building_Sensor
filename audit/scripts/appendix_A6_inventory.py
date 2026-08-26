"""
appendix_A6_inventory.py — compiles the capture inventory for Appendix A.6 and
the manifest for the data package.

Audit target: df32d53.

SCOPE. The inventory covers four_floor/characterisation/, which is the dataset
Chapter 4 is computed from: 354 raw captures in 78 folders, 21 to 27 July 2026.
It does NOT cover four_floor/pi_logs/, which is the earlier four-storey campaign
(42 indexed runs, 15 July 2026, sensor at Floor 4). No number in Chapter 4
derives from pi_logs; that dataset is carried in the deposit for the record only.

The "feeds" column is derived by tracing which analyses read which folders:
  * the audit scripts' own folder references (authoritative, they are executable)
  * the figure and table generators in four_floor/
Folders that no analysis reads are marked as such rather than guessed at.
"""
import os
import re
import sys
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
BASE = os.path.join(_ROOT, "four_floor", "characterisation")

# Which analysis consumes which folder pattern. Derived by grepping the
# repository for folder references; see verify() below, which re-checks it.
FEEDS = [
    (r"^day6_baseline$", "Table 4.5 baseline; Tables A.1, A.2 graded columns"),
    (r"^day4_baseline$", "Table 4.4; Tables A.1, A.2 severe column; Table 4.8"),
    (r"^day2_baseline$", "Session record only"),
    (r"^day5_baseline$", "Session record only"),
    (r"^day7_baseline$", "Session record only"),
    (r"^rebuild[1-5]$", "Table 4.3 reassembly floors; Appendix A.5"),
    (r"^(base|F1|F2|F3)_(trace|light|moderate)_c1$",
     "Tables 4.5, A.1, A.2; Table 4.14; Appendix A.4"),
    (r"^(base|F1|F2|F3)_severe_r[1-3]$",
     "Tables 4.4, 4.8, 4.18; Appendix A.3"),
    (r"^sensorF[12]_(base|F1|F3)_severe_r[1-3]$",
     "The 18 alternate-position severe records (abstract, Conclusion, Table 4.9)"),
    (r"^day2_damaged$", "Reversibility check, Section 4.2"),
    (r"^day2_repaired$", "Reversibility check, Section 4.2"),
    (r"^day5_reversibility$", "Reversibility check, Section 4.2"),
    (r".*_D3(_r1)?$", "Day-3 pilot captures, superseded, not read by any analysis"),
    (r"^base_light_r1$", "Extra base-plate light replicate, not read by any analysis"),
    (r"^sensorF1_baseline$", "Table 4.9 alternate sensor position"),
    (r"^sensorF2_baseline$", "Table 4.9 alternate sensor position"),
    (r"^sensorF2_baseline_day7b$", "Table 4.9 alternate sensor position"),
    (r"^day4_baseline_ATTEMPT1$", "Superseded, not read by any analysis"),
]


def classify(name):
    for pat, feed in FEEDS:
        if re.match(pat, name):
            return feed
    return None


def folders():
    out = []
    for d in sorted(os.listdir(BASE)):
        p = os.path.join(BASE, d)
        if not os.path.isdir(p):
            continue
        caps = sorted(f for f in os.listdir(p) if f.endswith("_raw.csv"))
        if caps:
            out.append((d, caps))
    return out


def verify(fold):
    """Re-check the FEEDS map against what the repository actually references."""
    refs = defaultdict(list)
    roots = [os.path.join(_ROOT, "four_floor"), _HERE]
    for root in roots:
        for dp, _, fns in os.walk(root):
            if "characterisation" in dp or "__pycache__" in dp:
                continue
            for fn in fns:
                if not fn.endswith(".py"):
                    continue
                try:
                    txt = open(os.path.join(dp, fn), errors="ignore").read()
                except OSError:
                    continue
                for name, _ in fold:
                    if name in txt:
                        refs[name].append(fn)
    return refs


def main():
    fold = folders()
    total = sum(len(c) for _, c in fold)
    print(f"Appendix A.6 — capture inventory\n{'=' * 96}")
    print(f"\n  folders with captures : {len(fold)}")
    print(f"  raw captures          : {total}")

    refs = verify(fold)
    unmapped, unreferenced = [], []
    print(f"\n  {'folder':30s} {'n':>3s} {'feeds':46s} {'referenced by'}")
    print("  " + "-" * 94)
    for name, caps in fold:
        feed = classify(name)
        if feed is None:
            unmapped.append(name)
            feed = "*** UNMAPPED ***"
        r = sorted(set(refs.get(name, [])))
        if not r and "Not read" not in feed and "Session record" not in feed \
                and "Superseded" not in feed:
            unreferenced.append(name)
        print(f"  {name:30s} {len(caps):3d} {feed[:46]:46s} "
              f"{','.join(x.replace('.py', '') for x in r[:2]) or '-'}")

    print(f"\n  folders with no FEEDS entry            : "
          f"{unmapped if unmapped else 'none'}")
    print(f"  folders claimed to feed an analysis but")
    print(f"  not referenced by name in any .py       : "
          f"{unreferenced if unreferenced else 'none'}")
    print(f"\n  NOTE: reference-by-name is a lower bound. Folders are also")
    print(f"  reached by glob patterns (e.g. f'{{loc}}_severe_r{{r}}'), which this")
    print(f"  check cannot see. Absence from the last column is not evidence")
    print(f"  that a folder is unused.")

    # Manifest for the data package.
    man = os.path.join(_ROOT, "audit", "data_package", "MANIFEST.txt")
    os.makedirs(os.path.dirname(man), exist_ok=True)
    with open(man, "w") as fh:
        fh.write("# characterisation/ capture manifest\n")
        fh.write(f"# {len(fold)} folders, {total} raw captures\n")
        for name, caps in fold:
            fh.write(f"\n{name}\t{len(caps)}\t{classify(name) or 'unmapped'}\n")
            for c in caps:
                fh.write(f"\t{c}\n")
    print(f"\n  manifest written: {man}")
    return 1 if unmapped else 0


if __name__ == "__main__":
    sys.exit(main())

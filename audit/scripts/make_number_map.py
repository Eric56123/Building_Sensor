"""
make_number_map.py — generates the number-to-script map used in README.md

Reads audit/reconciliation.csv and emits, for each dissertation table, figure or
section that the audit checked, the script that recomputes it and the data it
reads. Run it after adding reconciliation rows to keep the README honest.

    python audit/scripts/make_number_map.py > /tmp/map.md
"""
import collections
import csv
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV = os.path.join(_ROOT, "audit", "reconciliation.csv")

# Item-ID prefix -> the script that recomputes it. Deterministic by construction:
# each audit item was implemented in exactly one script.
ITEM_SCRIPT = [
    ("1.1", "audit_1_1_sd_vs_sem.py"),
    ("1.2", "audit_1_2_permutation.py"),
    ("1.3", "audit_1_3_scoring_rule.py"),
    ("1.4", "audit_1_4_localisation_records.py"),
    ("1.5", "audit_1_5_stats_wording.py"),
    ("1.6", "audit_1_6_stiffness_ratio.py"),
    ("1.7", "audit_1_7_scatter_basis.py"),
    ("1.8", "audit_1_5_stats_wording.py, appendix_A2_linearity.py"),
    ("A.2", "appendix_A2_linearity.py"),
    ("A.3", "appendix_A3_permutation.py"),
    ("A.4", "appendix_A4_A5_tables.py"),
    ("A.5", "appendix_A4_A5_tables.py"),
    ("A.6", "appendix_A6_inventory.py"),
    ("U4", "audit_p2_alt_positions.py"),
    ("P2", "audit_p2_abstract_conclusion.py"),
]

# What each script reads. Kept short; the scripts' docstrings give detail.
READS = {
    "audit_1_1_sd_vs_sem.py": "characterisation/{loc}_{grade}_c1, day6_baseline",
    "audit_1_2_permutation.py": "characterisation/{loc}_severe_r{1..3}, day4_baseline",
    "audit_1_3_scoring_rule.py": "results_decision_rule_sweep.json",
    "audit_1_4_localisation_records.py": "results_decision_rule_sweep.json, characterisation severe cells",
    "audit_1_5_stats_wording.py": "results_inversion_branches.json, sweep_*.csv, base_moderate_c1",
    "audit_1_6_stiffness_ratio.py": "simulation/rig_3dof.py, day4_baseline",
    "audit_1_7_scatter_basis.py": "characterisation/{loc}_{grade}_c1, day6_baseline",
    "audit_p2_abstract_conclusion.py": "characterisation graded + severe cells, day4/day6 baselines",
    "audit_p2_alt_positions.py": "characterisation/sensorF{1,2}_* severe cells and baselines",
    "appendix_A2_linearity.py": "characterisation/sweep_{1v4,2v2,2v8}_r{1..3}",
    "appendix_A3_permutation.py": "characterisation/{loc}_severe_r{1..3}, day4_baseline",
    "appendix_A4_A5_tables.py": "characterisation graded cells, rebuild{1..5}",
    "appendix_A6_inventory.py": "characterisation/ folder structure",
}


def script_for(item):
    for pre, s in ITEM_SCRIPT:
        if item.startswith(pre):
            return s
    return None


def key_for(location):
    """Reduce a location string to the dissertation object it names."""
    for pat in (r"Table (?:\d+\.\d+|[A-Z]\.\d+)", r"Figure \d+\.\d+",
                r"Appendix A\.\d+", r"Section \d+\.\d+(?:\.\d+)?"):
        m = re.search(pat, location)
        if m:
            return m.group(0)
    if location.startswith("l."):
        return "prose, " + location
    return location.split(",")[0][:40] or "other"


def main():
    rows = list(csv.DictReader(open(CSV)))
    m = collections.defaultdict(set)
    for r in rows:
        s = script_for(r["item"] or "")
        if s:
            m[key_for(r["location"] or "")].add(s)

    def sk(k):
        mm = re.search(r"(\d+)\.(\d+)", k)
        pri = 0 if k.startswith("Table") else 1 if k.startswith("Figure") else \
            2 if k.startswith("Section") else 3 if k.startswith("Appendix") else 4
        return (pri, int(mm.group(1)), int(mm.group(2))) if mm else (pri, 99, 99)

    print("| Dissertation object | Recomputed by | Reads |")
    print("|---|---|---|")
    for k in sorted(m, key=sk):
        scripts = sorted(m[k])
        first = scripts[0].split(", ")[0]
        print(f"| {k} | `{'`, `'.join(scripts)}` | {READS.get(first, '')} |")
    print(f"\nCovered objects: {len(m)}   "
          f"reconciliation rows: {len(rows)}")
    missing = [s for s in READS if not os.path.exists(
        os.path.join(_ROOT, "audit", "scripts", s))]
    print(f"Scripts named but absent from audit/scripts/: "
          f"{missing if missing else 'none'}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())

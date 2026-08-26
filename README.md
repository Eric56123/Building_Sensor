# Single-accelerometer modal damage identification for a low-rise frame

Supporting code and data for an MSc dissertation (UCL GEOL0056). One low-cost
accelerometer is mounted on a three-storey steel shear frame, and damage is
introduced by loosening the screws at one of four plates in four graded amounts.
The question is how much damage information a single sensor establishes, and
whether embedding the equation of motion in a learned inverse model improves on
classical modal analysis of the same measurement.

The whole chain runs on the node: acquisition, feature extraction and inference
on a Raspberry Pi. The analysis in this repository reproduces the published
results from the recorded captures and runs on any machine.

## Reproducing a number from Chapter 4

Every figure in the dissertation was recomputed from the raw captures and traced
to a script. `audit/reconciliation.csv` lists all 92 checks: what the document
claims, what the recomputation gives, and the verdict. The table below maps each
dissertation object to the script that regenerates it.

| Dissertation object | Recomputed by | Reads |
|---|---|---|
| Table 3.10 | `audit_1_3_scoring_rule.py` | results_decision_rule_sweep.json |
| Table 4.5 | `audit_1_1_sd_vs_sem.py`, `audit_1_7_scatter_basis.py` | characterisation/{loc}_{grade}_c1, day6_baseline |
| Table 4.6 | `audit_1_2_permutation.py` | characterisation/{loc}_severe_r{1..3}, day4_baseline |
| Table 4.8 | `audit_1_2_permutation.py` | characterisation/{loc}_severe_r{1..3}, day4_baseline |
| Table 4.16 | `audit_1_5_stats_wording.py` | results_inversion_branches.json, sweep_*.csv, base_moderate_c1 |
| Table 4.18 | `audit_1_4_localisation_records.py` | results_decision_rule_sweep.json, characterisation severe cells |
| Table 5.1 | `audit_1_5_stats_wording.py` | results_inversion_branches.json, sweep_*.csv, base_moderate_c1 |
| Section 4.1.5 | `audit_1_5_stats_wording.py, appendix_A2_linearity.py` | results_inversion_branches.json, sweep_*.csv, base_moderate_c1 |
| Section 4.4.1 | `audit_1_2_permutation.py` | characterisation/{loc}_severe_r{1..3}, day4_baseline |
| Section 4.5 | `audit_p2_alt_positions.py` | characterisation/sensorF{1,2}_* severe cells and baselines |
| Appendix A.1 | `audit_1_4_localisation_records.py` | results_decision_rule_sweep.json, characterisation severe cells |
| Appendix A.2 | `appendix_A2_linearity.py` | characterisation/sweep_{1v4,2v2,2v8}_r{1..3} |
| Appendix A.3 | `appendix_A3_permutation.py` | characterisation/{loc}_severe_r{1..3}, day4_baseline |
| Appendix A.4 | `appendix_A4_A5_tables.py` | characterisation graded cells, rebuild{1..5} |
| Appendix A.5 | `appendix_A4_A5_tables.py` | characterisation graded cells, rebuild{1..5} |
| Appendix A.6 | `appendix_A6_inventory.py` | characterisation/ folder structure |
| Discussion l.2744 | `audit_1_2_permutation.py` | characterisation/{loc}_severe_r{1..3}, day4_baseline |
| prose, l.2415 | `audit_1_3_scoring_rule.py` | results_decision_rule_sweep.json |
| severe records | `audit_1_3_scoring_rule.py` | results_decision_rule_sweep.json |
| prose, l.3092 | `audit_1_5_stats_wording.py` | results_inversion_branches.json, sweep_*.csv, base_moderate_c1 |
| prose, l.2937 | `audit_1_5_stats_wording.py` | results_inversion_branches.json, sweep_*.csv, base_moderate_c1 |
| prose, l.3093 | `audit_1_5_stats_wording.py` | results_inversion_branches.json, sweep_*.csv, base_moderate_c1 |
| prose, l.3094 | `audit_1_5_stats_wording.py` | results_inversion_branches.json, sweep_*.csv, base_moderate_c1 |
| prose, l.1331 and l.1487 | `audit_1_6_stiffness_ratio.py` | simulation/rig_3dof.py, day4_baseline |
| prose, l.1487 | `audit_1_6_stiffness_ratio.py` | simulation/rig_3dof.py, day4_baseline |
| scatter figure labels | `audit_1_7_scatter_basis.py` | characterisation/{loc}_{grade}_c1, day6_baseline |
| prose, l.1894 | `audit_1_7_scatter_basis.py` | characterisation/{loc}_{grade}_c1, day6_baseline |
| prose, l.1967 | `audit_1_7_scatter_basis.py` | characterisation/{loc}_{grade}_c1, day6_baseline |
| prose, l.1801 | `audit_1_5_stats_wording.py, appendix_A2_linearity.py` | results_inversion_branches.json, sweep_*.csv, base_moderate_c1 |
| prose, l.1515 | `audit_1_5_stats_wording.py, appendix_A2_linearity.py` | results_inversion_branches.json, sweep_*.csv, base_moderate_c1 |
| prose, l.1936 | `audit_1_5_stats_wording.py, appendix_A2_linearity.py` | results_inversion_branches.json, sweep_*.csv, base_moderate_c1 |

Regenerate this table with `python audit/scripts/make_number_map.py`.

To check one number, run its script. Each prints the recomputed value against the
printed one and exits non-zero if they disagree:

```
python audit/scripts/audit_1_1_sd_vs_sem.py     # Table 4.5, every cell
python audit/scripts/appendix_A4_A5_tables.py   # per-tap values, reassembly floors
```

## How to run it

Python 3.11 or newer. The results were produced under 3.11.5.

```
git clone https://github.com/Eric56123/Building_Sensor
cd Building_Sensor
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
```

That is enough for all verification. **torch is not required**: the network
predictions are cached in `four_floor/results_*.json` and the audit scripts read
the cache. Install `requirements-train.txt` only to retrain.

| Entry point | What it does | Runtime |
|---|---|---|
| `audit/scripts/*.py` (15 scripts) | Recompute and check every published number | under 4 min total |
| `four_floor/make_figures_ch9.py` | Regenerate the Chapter 4 figure set | ~1 min |
| `four_floor/make_ch8_figures.py` | Regenerate Figures 8.3 to 8.5 | ~30 s |
| `four_floor/decision_rule_sweep.py` | Retrain 20 seeds x 2 loss weights (needs torch) | ~25 min CPU |
| `four_floor/inversion_robustness.py` | Branch enumeration, 3000 starts per case | ~5 min |
| `four_floor/monitor.py` | Live acquisition and inference (**Pi only**) | continuous |

### Verified reproduction

A clean clone was installed from `requirements.txt` alone and all 15 audit
scripts were run. Output was compared line by line against the reference
environment:

| | Reference | Clean clone |
|---|---|---|
| Python | 3.11.5 | 3.13.5 |
| numpy | 1.26.3 | 2.5.2 |
| scipy | 1.11.4 | 1.18.1 |

**Zero numeric differences** across all 15 scripts. The only diffs were absolute
paths in warning messages. This is why `requirements.txt` gives minimum versions
rather than exact pins: the exact pins do not install on Python 3.13, and the
analysis does not need them.

## Directory layout

| Path | Contents |
|---|---|
| `four_floor/` | Acquisition, feature extraction, models, figure generators |
| `four_floor/characterisation/` | **The measurement campaign.** 354 raw captures, 21 to 27 July 2026. Every Chapter 4 number comes from here |
| `four_floor/simulation/` | Forward models: the 3-DOF rig chain and the 12-DOF benchmark |
| `four_floor/pinn/` | Network definition, dataset and training utilities |
| `four_floor/pi_logs/` | **Superseded.** An earlier four-storey campaign, 15 July 2026, sensor at Floor 4, with a damage index that was abandoned. Nothing in the dissertation uses it; retained for the research record |
| `audit/scripts/` | The verification layer: one script per audited claim |
| `audit/reconciliation.csv` | 92 rows, every checked number and its verdict |
| `audit/appendix/` | Paste-ready LaTeX for the appendix tables |
| `audit/data_package/` | Small derived-results bundle, with a file-to-table map |
| `experiments/` | Physics-loss ablation sweep summaries |
| `docs/process/` | Working documents from writing and verification, not research output |

## Hardware

- Raspberry Pi 4 as the acquisition node
- ADXL345 accelerometer read over **software** I2C, 1000 Hz
- WS2812 status LEDs
- Excitation by manual tap; swept-sine and ringdown captures for the linearity
  and damping checks

The acquisition path (`monitor.py`, `hardware_test.py`, `live_features.py`) only
runs on the node and needs `requirements-node.txt`. Everything else runs
anywhere. `monitor.py` prints an scp hint for copying weights to the node; set
`SHM_NODE_TARGET` to change the host it names.

## Data

The 354 raw captures are tracked in this repository (126 MB) and are also
deposited at Zenodo with a DOI, which is the citable route. `audit/data_package/`
holds the derived results and a manifest mapping every capture set to the tables
it feeds.

## Licence

MIT, see `LICENSE`. All dependencies are BSD or MIT, so there is no copyleft
constraint.

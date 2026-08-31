DATA PACKAGE — GEOL0056 dissertation
Single-Accelerometer Modal Damage Identification for a Low-Rise Frame
Eric Tan, 22008822

--------------------------------------------------------------------------------
PROVENANCE
--------------------------------------------------------------------------------
Repository   : https://github.com/Eric56123/Building_Sensor
Results SHA  : b0aba33   (all analysis outputs below were generated at this commit)
Appendix SHA : 898ac4c   (appendix tables and this package)

MEASURED vs SIMULATED. Every number in Chapter 4 is measured on the physical
three-storey rig. The simulated data appears only in Chapter 3 and in the
lambda-sweep files below: the network is trained on synthetic modal vectors from
the 3-DOF shear-chain model and then applied to the measured rig frequencies.
No measured quantity in this dissertation is model-generated.

--------------------------------------------------------------------------------
WHAT IS IN THIS PACKAGE
--------------------------------------------------------------------------------
This package holds the derived results and the capture manifest. The raw
captures are 124 MB and are deposited separately; see RAW CAPTURES below.

MANIFEST.txt
    Every capture folder in the measured campaign, its tap count, and the tables
    it feeds. 65 measurement sets, 326 tap captures. Use this to locate the file
    behind any Chapter 4 number.
    -> Appendix A.6 (Table A.6)

rig.json
    Rig geometry, masses, sensor positions and the damage-location map.
    -> Section 3 rig description; Table 3.1

results_decision_rule_sweep.json
    Per-cell storey calls from the retrained network across 20 seeds at each of
    two loss weights. 20 measured records.
    -> Table 4.14 (calls and stability), Table 4.18 (localisation row),
       Figure 4.9 (seed sweep grid)

results_inversion_branches.json
    Every exact solution of the three-parameter inversion per damage case, with
    basin sizes, admissibility and converged-start counts.
    -> Table 4.16 (branch enumeration), Figure 4.10 (branch plot),
       Table 5.1 (inversion row)

lambda_sweep/results_summary.csv
lambda_sweep/results_summary_continuous.csv
lambda_sweep/results_summary_continuous_holdout.csv
    Physics-loss ablation. Columns: lambda, fold, holdout, mae,
    per_storey_mae, localisation_acc, final_L_data, final_L_phys_unweighted,
    final_lam_L_phys, n_train, n_test, wall_clock_s, device.
    Three files are the three synthetic datasets, discrete and continuous and
    continuous-with-holdout.
    -> Section 4.5 physics-term ablation; the 17.8% residual reduction;
       Table 5.1 (physics-loss row)

superseded_four_storey_campaign/run_index.csv
    42 runs recorded 15 July 2026 on an earlier FOUR-storey configuration, with
    the sensor at Floor 4 and a damage index that was abandoned.
    NO NUMBER IN THIS DISSERTATION DERIVES FROM THIS CAMPAIGN. It is included
    for the research record only. The retargeting from four storeys to three is
    described in Section 3.

--------------------------------------------------------------------------------
RAW CAPTURES (deposited separately, 124 MB)
--------------------------------------------------------------------------------
354 raw tap captures, 21 to 27 July 2026, at:

    Zenodo DOI: [TO BE INSERTED BEFORE SUBMISSION]

Layout of the deposit:

    characterisation/           326 captures in 65 measurement sets, plus 28
                                top-level swept-sine, ringdown and noise-floor
                                recordings. This is the Chapter 4 dataset.
    superseded_four_storey_campaign/
                                85 captures from the 15 July four-storey
                                campaign. Not used for any result.

Each capture is a CSV of one tap: time and single-axis acceleration, 1000 Hz.
Folder names encode sensor position, damage location and grade, and are decoded
in MANIFEST.txt and in Appendix A.6.

The GitHub repository above also contains the raw captures and every analysis
script, so the results can be regenerated end to end without the deposit.

--------------------------------------------------------------------------------
REGENERATING ANY NUMBER
--------------------------------------------------------------------------------
Clone the repository at b0aba33 and run the scripts under audit/scripts/. Each
prints its recomputed values against the printed ones. audit/reconciliation.csv
lists every number checked, its recomputed value and the script that produced it.

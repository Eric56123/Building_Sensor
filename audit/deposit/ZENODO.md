# Zenodo deposit — structure, metadata and recommendations

## Structure

Build this tree, then upload. Sizes and counts measured, not estimated.

```
captures/                       126 MB   391 files   the Chapter 4 dataset
  MANIFEST.txt                            (copy from audit/data_package/)
  <65 measurement-set folders>            326 tap captures, 5 taps each
  <28 top-level captures>                 swept-sine, ringdown, noise floor
derived/                         28 KB     6 files
  results_decision_rule_sweep.json        network calls, 20 seeds x 2 weights
  results_inversion_branches.json         branch enumeration
  rig.json                                geometry, masses, sensor positions
  results_summary*.csv                    physics-loss ablation, 3 datasets
superseded_four_storey/          22 MB    85 files
  run_index.csv                           42 runs, 15 July 2026
  NOTE.txt                                "nothing in the dissertation uses this"
scripts/                        180 KB    15 files
  <the audit scripts>                     so the deposit verifies itself
README.txt                                (adapt audit/data_package/README.txt)
```

**Total: ~295 MB, 497 files.** Zenodo's per-file limit is 50 GB and the default
per-record limit is 50 GB, so this needs no special handling. Compressing
`captures/` to a single zip would cut transfer time; leaving it expanded lets a
reader fetch one capture without downloading everything. Expanded is preferable
here, because the point of the manifest is selective checking.

## Metadata

**Title**
> Single-accelerometer modal measurements of a three-storey steel shear frame with graded screwed-joint damage

**Authors**
> Tan, Eric — University College London

Add Carmine Galasso as a contributor with role *Supervisor* if he agrees; do not
list a supervisor as an author without asking.

**Resource type**: Dataset

**Description**
> Measurements and analysis code supporting an MSc dissertation (UCL GEOL0056)
> on single-sensor structural health monitoring. A three-storey steel shear
> frame was instrumented with one low-cost ADXL345 accelerometer on a Raspberry
> Pi 4, sampling at 1000 Hz. Damage was introduced by loosening the screws at
> one of four plates (a base plate and three storey plates) in four graded
> amounts, from an eighth of a turn to fully loosened, with the most severe
> grade replicated three times at each location. Five complete teardown and
> rebuild cycles establish the reassembly reproducibility against which damage
> is judged. The deposit contains 354 raw tap captures from the three-storey
> campaign, the derived modal results, the physics-loss ablation summaries, and
> the verification scripts that recompute every figure reported in the
> dissertation. An earlier four-storey campaign is included for the research
> record and is not used for any reported result.
>
> All measurements are physical. Simulated data appears only in the network
> training, which uses synthetic modal vectors from a 3-DOF shear-chain model.

**Keywords**
> structural health monitoring; modal analysis; damage detection; damage
> localisation; low-cost sensing; MEMS accelerometer; Raspberry Pi;
> physics-informed neural network; inverse eigenvalue problem; shear frame

**Licence**: CC-BY-4.0 for the data. The code is MIT (see the repository).
Confirm UCL imposes nothing stricter before publishing.

**Related identifiers**
| Relation | Identifier |
|---|---|
| *is supplemented by* | https://github.com/Eric56123/Building_Sensor |
| *is supplement to* | the dissertation, once it has a persistent identifier |

Record the repository commit SHA in the description so the code state is pinned.

## Data availability statement

Two sentences for the front matter. Insert the DOI once minted.

> All measurements, analysis code and derived results are openly available. The
> 354 raw tap captures, the analysis scripts, and a reconciliation listing every
> reported figure against its recomputed value are deposited at Zenodo
> (DOI: [INSERT]) and mirrored at https://github.com/Eric56123/Building_Sensor.

## Recommendation: should the data stay in git?

**Measured impact.** The working tree is 208 MB and `.git` is 52 MB, so a fresh
clone moves roughly 150 MB before checkout. The code, the audit layer and the
derived results together are **3.5 MB**. So the data is about 98% of the clone.

**Recommendation: leave it, and do not rewrite history now.**

Reasons, in order:

1. The conventional arrangement is code in git and data in the archive, and by
   that standard the data should come out. But removing it from *history* needs
   `filter-repo` or equivalent, which rewrites every commit SHA. The
   dissertation's data availability statement cites a specific SHA, and the
   audit's 92 reconciliation rows are anchored to `df32d53`. Rewriting would
   invalidate both a week before submission.
2. Deleting the files in a new commit without rewriting history frees nothing:
   the objects stay in `.git`, so the clone stays the same size and the working
   tree loses the ability to reproduce anything offline.
3. A 150 MB clone is unusual but not obstructive, and it has a real benefit: the
   repository reproduces the entire dissertation with no external fetch. For an
   examiner checking a number under time pressure, that is worth more than a
   fast clone.

**If you want it cleaned up after the result is confirmed**, the sequence is: mint
the Zenodo DOI, wait for the mark, then `git filter-repo --path
four_floor/characterisation --path four_floor/pi_logs --invert-paths` on a fresh
clone, force-push, and update the availability statement to cite the DOI alone
rather than a SHA. Not before.

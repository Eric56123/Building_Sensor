# Day 5 session record — the PINN arm (2026-07-24)

Retargeted, reformulated, trained and honestly validated the physics-informed
neural network for the measured 3-DOF rig. New code: `simulation/rig_3dof.py`,
`pinn/rig_pinn.py`, `train_rig_pinn.py`. Weights: `shm_pinn_rig3dof_v1.pth`
(+ sidecar). `shm_pinn_weights.pth` untouched.

---

## VERDICT (Step 5)

**On this well-characterised 3-DOF rig, the classical modal-vector method matches
or beats the PINN. The PINN does not manufacture a win, and it should not:
classical modal analysis suffices here.**

| task | classical (Day 4) | PINN | winner |
|---|---|---|---|
| detection | flags 4/4, healthy clean | flags 4/4, healthy clean | **tie** |
| severity | modal shift magnitude | graded alpha 0.06->0.72 | tie |
| localise PLATE | 4 plates distinct, 3-496 sigma | collapses base/F1/F2 to "k1" | **classical** |
| interpretability | shift pattern (opaque) | storey stiffness (physical) | PINN |
| cost | none (closed form) | retarget + train per rig | **classical** |

The PINN adds cost without beating classical on the localisation task the
campaign was built around. But the *reason* it does not localise the plate is
not a model failure — see below.

---

## Step 0b — input modality (decided)

Modal vector [f1/f1_0, f2/f2_0, f3/f3_0], option (iii). Reasons: it is the same
representation as the classical benchmark (apples-to-apples); Day 4 proved it
separates the locations; and it sidesteps the bus-3 FIFO-overrun PSD-magnitude
problem (ringdown frequencies are unaffected by overruns). Training and inference
use the identical representation — the old deployment's fatal train/inference
mismatch is not reintroduced.

## Step 1 — architecture

`RigPINN`: modal vector -> storey stiffness fractions [a1,a2,a3], a small MLP
(3->64->64->3, sigmoid). 3 observed modes -> 3 unknown stiffnesses is a formally
determined inverse — the identifiable problem, unlike the old 4-alpha-from-
1-sensor-broadcast CNN. Physics loss = eigenvalue residual of the retargeted
3-DOF model (the modes of K_healthy*alpha must reproduce the observed modes),
differentiable through torch.linalg.eigvalsh.

## Step 2 — retarget (VALIDATED against real data)

3-DOF shear model replacing the 12-DOF Johnson benchmark. Inverse problem solved
EXACTLY (residual 1e-15 Hz) from the measured f1/f2/f3:
    k1 : k2 : k3 = 1 : 1.19 : 0.98   (close to uniform)
Damping set to measured zeta (~5-7% mode 1), not the benchmark's 1%.

The forward model reproduces the Day 4 damage signatures:
- f1 shift ranks bottom > middle > top (model and rig agree);
- top-storey damage shifts f2 most: model -38%, rig measured -37%.

Assumptions flagged: equal storey masses (absolute mass unmeasured, so only k
ratios are physical); ideal shear behaviour; damage = fractional storey-stiffness
loss; base-plate damage approximated as a k1 reduction.

## Step 3 — training

Tiny MLP over modal vectors -> trains on CPU in seconds (the old CNN-over-spectra
needed a GPU + the 150 MB shard; the reformulation removed that entirely). 16000
sim samples, 600 epochs. Detection threshold calibrated from the model's own
severity output on held-out UNDAMAGED samples (99th pct = 0.064) — the principled
analogue of the classical reassembly floor.

Held-out SIMULATED: detection 97.3%, localisation 93.9%, severity MAE 0.047.

## Step 4 — validation on REAL Day 4 captures

| location | PINN alpha [k1 k2 k3] | detect | k-argmin | classical / true |
|---|---|---|---|---|
| healthy | 0.96 0.97 0.95 | undamaged | - | undamaged |
| base | 0.06 0.93 0.93 | DAMAGED | k1 | base plate |
| F1 | 0.20 0.52 0.98 | DAMAGED | k1 | Floor 1 |
| F2 | 0.26 0.85 0.80 | DAMAGED | k1 | Floor 2 |
| F3 | 0.72 0.94 0.98 | DAMAGED | k1 | Floor 3 (2 modes unmeasurable) |

Detection: 5/5 correct after calibration (the first pass false-positived on
healthy at alpha~0.93; fixed by more healthy training samples + the calibrated
threshold). Localisation-by-plate: fails for F1/F2/F3 (all read k1-dominant).

## WHY the PINN does not localise the plate (the real finding)

Direct PHYSICS inversion of the real modal vectors (no neural net) fits them
EXACTLY and its argmin agrees with the PINN — so the PINN is not mis-trained; it
recovers the storey-stiffness pattern the data actually implies. Two structural
reasons the plate is nonetheless not identified:

1. **The plate->stiffness map is many-to-many.** Each plate bolts the columns
   above AND below it, so loosening one plate changes two adjacent storey
   stiffnesses. base->k1 is clean, but F1/F2 reduce k1 substantially too (F2
   inverts exactly to k1=0.27, k3=0.58). "Which storey stiffness dropped" is not
   "which plate was loosened."
2. **F3 is data-limited.** Under top-storey damage the 2nd mode falls near 2*f1
   and collides with the fundamental's harmonic (Day 4 flagged this; the fixed
   set_mode_frequencies voids it). So f2 is physically unmeasurable with one
   sensor + tap excitation, leaving F3 under-determined (only f1).

The classical method sidesteps both: it distinguishes plates by the full modal-
vector FINGERPRINT without interpreting it as stiffness, so the many-to-many map
does not hurt it, and it uses whatever modes are clean.

---

## Verified vs assumed

**Verified:** retarget reproduces measured modes exactly and predicts the Day 4
signatures; the model trains and runs; detection matches classical on real data
(5/5); the physics inversion of the real vectors is exact; the plate->stiffness
ambiguity is real (F2 inverts to k1+k3).

**Assumed / not established:** equal/uniform storey masses; that severe-damage
findings extend to light/moderate (Day 3 gradability was base-plate only); that a
different damage protocol (mid-column stiffness loss, giving a 1:1 plate->stiffness
map) would let the PINN localise — untested.

---

## What would make the PINN add value (further work)

The PINN loses here because the rig is 3-DOF, well-characterised, and closed-form
inversion is exact — there is nothing for a network to add. It could add value
where classical modal analysis struggles:
- many structures with NO per-rig retargeting (train once, generalise);
- damage applied as clean single-storey stiffness loss (1:1 map), removing the
  plate ambiguity so localisation becomes identifiable;
- richer input (mode shapes from multiple sensors) breaking the single-sensor
  limits;
- conditioning on f1 to separate base vs Floor 1, which even the classical method
  needed f3 for.

Do NOT claim the PINN as the contribution. The defensible dissertation story is:
a fully characterised rig, a replicated classical localisation result, and an
honest head-to-head showing the PINN does not beat it here — with a clear account
of why (identifiability + the plate->stiffness map) and when it would.

---

## Next

1. `shm_pinn_rig3dof_v1.pth` + sidecar are the deployable retargeted model IF the
   modal-vector pipeline is wanted live (it needs only ringdown, not clean PSDs).
2. Gradability at real storeys (Day 3 was base-plate only) if a graded matrix is
   pursued.
3. Move ADXL345 to hardware bus 1 only matters if driven-PSD input is ever chosen
   (it is not, for the modal-vector model).
4. Fill Experiment Log -> Damage Variable + Excitation Params.

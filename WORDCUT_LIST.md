# Word reduction — 12,293 → target ~11,900

Need 293 words minimum. The edits below give **about 400**, which leaves margin.

Work top to bottom. Part A costs nothing and fixes real errors; Part B does the cutting.

---

# PART A — errors to fix first (no word change)

Four unclosed parentheses in body text, and one garbled table row.

## ☐ A1 · §3.2
**Find:** `(Table 3.12.`
**Replace:** `(Table 3.12).`

## ☐ A2 · §3.6.4
**Find:** `the answer is the same (Table 4.12.`
**Replace:** `the answer is the same (Table 4.12).`

## ☐ A3 · §4.6.6
**Find:** `being under-determined (Section 4.6.5.`
**Replace:** `being under-determined (Section 4.6.5).`

## ☐ A4 · §5.1, first sentence
**Find:** `cannot be attributed (Section 3.5.1.`
**Replace:** `cannot be attributed (Section 3.5.1).`

## ☐ A5 · Table 3.1, objective 4 row

The left-hand cell has words transposed. It currently reads:

> Assess whether per-storey stiffness can be recovered from the rig, and establish the limit

with the middle column running `Retargeted three-degree-of-freedom model and network
(Sections 3.6.5 to 3.6.7), and direct inversion (Section 3.7)`.

Read this row in the compiled PDF. The phrase order suggests the objective text and the
method text have partly swapped across the column break. *(Uncounted — it is a table.)*

---

# PART B — the cuts

## B1 · §3.6.1 and §3.6.4, the four-storey stage — about 200 words

This describes a model you superseded. §3.6.4 says so outright: three findings
"determined that a retargeted model was required". The stage produced no reported
result and its architecture was incompatible with the rig. It has to be recorded, but
it does not need four subsections and three display equations.

### ☐ B1a — move the derivation to an appendix

In §3.6.1, the three display equations and their connecting prose:

> ...configured as Table 3.8 records and governed by:
>
> **(3.6)**  M ü + C u̇ + K u = f
>
> whose global stiffness matrix is a linear combination of per storey contributions,
>
> **(3.7)**  K(k) = Σ kᵢ Kᵢ
>
> linear and differentiable in k and appearing directly in the physics loss. Damping is
> modal, neither Rayleigh nor numerically imposed:
>
> **(3.8)**  C = MΦ diag(2ζₙωₙ) ΦᵀM
>
> with Φ the mass-normalised modal matrix, so that each mode receives exactly the
> prescribed damping which Figure 3.3 verifies. The spectrum is finally compressed
> logarithmically and rescaled onto fixed bounds derived from the training set
> (Figure 3.4),
>
> **(3.9)**  P̂ = min(1, max(0, (log₁₀(P + ε) − P_min)/(P_max − P_min)))
>
> stored and reused at inference.

**Move all of this to a new Appendix A.7** ("Four-storey development model"), inside the
`%TC:ignore` block so it stops counting. In §3.6.1 leave:

> Data was therefore generated from a forward model of the four-storey IASC-ASCE Phase I
> benchmark structure (Johnson et al., 2004), configured as Table 3.8 records. The global
> stiffness matrix is a linear combination of per-storey contributions, linear and
> differentiable in k so that it enters the physics loss directly; damping is modal rather
> than Rayleigh, and the spectrum is log-compressed onto fixed bounds derived from the
> training set. Appendix A.7 gives the equations. With 313,172 parameters fitted to 100
> training windows and a benchmark that publishes seven damage patterns and no more, that
> shortage is a property of the data source and bounds what any result from this stage can
> establish.

*Saves roughly 120 counted words. The content survives; it just stops counting.*

### ☐ B1b — compress §3.6.4

**Find** the whole of §3.6.4 after its opening line, currently:

> The physics weight does not change held-out performance. On the benchmark patterns, the
> ablation left localisation at or below the 0.25 chance rate, a result that is uninformative
> for the reason given in Section 3.6.3. On the sampled-stiffness data the ablation is well
> posed and the answer is the same (Table 4.12.
>
> Representation error on the benchmark is carried forward as a limitation rather than
> repaired.
>
> Architectural mismatch with the rig. The architecture assumes four simultaneous
> channels, one per floor. The rig carries one accelerometer, so a four-channel input can
> only be formed by replicating a single measurement, which supplies no information the
> network can use to distinguish storeys.

**Replace with:**

> The physics weight did not change held-out performance: on the benchmark patterns the
> ablation left localisation at or below the 0.25 chance rate, uninformative for the reason
> given in Section 3.6.3, and on the sampled-stiffness data, where the ablation is well
> posed, the answer was the same (Table 4.12). Representation error on the benchmark is
> carried forward as a limitation rather than repaired. The architecture also assumes four
> simultaneous channels, one per floor, so on a rig carrying one accelerometer a
> four-channel input can only be formed by replicating a single measurement, which supplies
> nothing the network can use to distinguish storeys.

*Saves about 30 words, fixes the unclosed parenthesis from A2, and removes the orphan
one-line paragraph.*

## B2 · §5.1, restated Results — about 55 words

The Discussion should interpret Chapter 4, not re-report it. Three instances:

### ☐ B2a
**Find:** `Five teardown and rebuild cycles put the floor at the values of Table 4.3, and every margin below is a multiple of the floor for its own mode.`
**Replace:** `Every margin below is a multiple of the floor for its own mode (Table 4.3).`
*−13*

### ☐ B2b
**Find:** `Against that floor, severe damage is unambiguous, clearing it by 52 to 202 times, with the fundamental shifting from the Session 4 baseline of 2.94 Hz to 1.16 Hz for Floor 1 damage.`
**Replace:** `Against that floor, severe damage is unambiguous, clearing it by two orders of magnitude.`
*−19. The 52-to-202 range and the 2.94→1.16 Hz shift are both in Chapter 4 and in the abstract.*

### ☐ B2c
**Find:** `The first-mode shift falls monotonically with grade at all four locations and the trend holds at 11 of 12 location and mode combinations but it saturates above one turn, moving 9.8% at the base between moderate and severe against 1.2% at Floor 2.`
**Replace:** `The first-mode shift falls monotonically with grade at all four locations but saturates above one turn, moving 9.8% at the base between moderate and severe against 1.2% at Floor 2.`
*−12. The 11-of-12 count appears in the abstract, the conclusion and §4.3.2.*

## B3 · §5.2, restated Results — about 25 words

### ☐ B3a
**Find:** `Repeating the damage with the accelerometer on Floor 2 and Floor 1 gave 18 of 18 correct against references recorded at a different position from the runs being tested.`
**Replace:** `Relocating the accelerometer gave 18 of 18 correct against references recorded elsewhere (Section 4.5).`
*−14. §4.5 states the position detail in full.*

**Keep** the sentence immediately before it — `The closest pair of class means is separated
by 33.0 floor-units against a largest within-class distance of 3.09, a ratio of 10.7`.
With the p-values withdrawn, that ratio is the effect size carrying the localisation
result, so it has to stay in the Discussion.

---

# Running total

| | words |
|---|---|
| B1a, derivation to Appendix A.7 | **−120** |
| B1b, §3.6.4 compressed | **−30** |
| B2a–c, §5.1 restatements | **−44** |
| B3a, §5.2 restatement | **−14** |
| | **−208** |

That leaves you at about **12,085** — still over. Two further options, in the order I
would take them:

## ☐ B4 · §3.6.1 opening sentence — −10

**Find:** `Training a network to solve the inverse problem requires responses whose stiffness state is known exactly, which field measurement cannot supply.`
**Replace:** `Training the network requires responses whose stiffness state is known exactly, which field measurement cannot supply.`

## ☐ B5 · Chapter 2 — the remaining ~200

Sections 2.1, 2.2 and 2.5 are the three largest at roughly 300 words each. The guidelines
name long literature reviews as the common failure, and Chapter 2 carries 20 marks against
the 70 in Results and Discussion, so this is where the marks-per-word is lowest.

Do not cut the research gap in §2.7, and do not cut anything §5.2 or §5.5 later cites back
to (Cawley and Adams 1979, Farrar and Jauregui 1998, Morassi and Rollo 2001, Sohn 1999,
Peeters and De Roeck 2001). Target instead any passage that describes a method the
dissertation does not use.

---

# After editing

Re-run `texcount`. Target **11,900 or below**, not 11,999 — the count moves slightly with
hyphenation and float placement, and going over 12,000 costs up to 10%.

# Second reduction pass — 12,221 → target ~11,900

Need 221 minimum. Below gives about **250** from caption relocation alone, plus 44 from
two duplications still outstanding, plus 30 from §3.6.4.

**Check this first.** Confirm your `texcount` invocation actually excludes captions. Run
`texcount -inc main.tex` and look at the *"words outside text"* line — that is caption
text. If your 12,221 includes it, moving prose into captions saves nothing and you should
stop here. The marking guidelines exclude captions, so the count you report should too.

---

# PART A — prose that belongs in a caption

Each of these is a self-contained note about one float. They read as caption material
already, which is why they move cleanly. Delete from the body, append to the caption of
the float named.

## ☐ A1 · → Table 3.10 caption — **−23**
**Remove from body:**
> The threshold is constructed as Table 3.10 records, giving 𝜃 = 0.064, so damage is declared when any predicted fraction falls below 0.936.

**Append to Table 3.10's caption:**
> The threshold constructed here is 𝜃 = 0.064; damage is declared when any predicted fraction falls below 0.936.

## ☐ A2 · → Table 3.11 caption — **−20**
**Remove:**
> The solution set is therefore enumerated by multi-start rather than taken from one optimisation, under the settings of Table 3.11.

**Append to Table 3.11's caption:**
> Branches are enumerated by multi-start rather than taken from a single optimisation.

## ☐ A3 · → Table 3.13 caption — **−26**
**Remove:**
> Modal signature was used only as an independent check on that attribution, under the audit Table 3.13: records and no capture disagreed with its recorded location.

*(This sentence is also garbled — "under the audit Table 3.13: records and no capture" has
words out of order.)*

**Append to Table 3.13's caption:**
> Modal signature was used only as an independent check on plate attribution under this audit; no capture disagreed with its recorded location.

## ☐ A4 · → Figure 4.3 caption — **−14**
**Remove:**
> Apart from the two cells hatched in Figure 4.3, no cell is contaminated.

**Append to Figure 4.3's caption:**
> Apart from the two hatched cells, no cell is contaminated.

## ☐ A5 · → Table 4.12 caption — **−25**
**Remove:**
> No unweighted physics residual was logged for this model, so the residual reduction reported for the sampled-stiffness dataset in Table 4.12 has no counterpart here.

**Append to the caption of the table this sits beneath (the retargeted-model ablation):**
> No unweighted physics residual was logged for this model, so the residual reduction reported in Table 4.12 has no counterpart here.

## ☐ A6 · → Table 4.15 caption — **−23**
**Remove:**
> Re-scoring by nearest signature agrees on all six severe captures across all forty runs and is worse on the graded cells (Table 4.15).

**Append to Table 4.15's caption:**
> Re-scoring by nearest signature agrees on all six severe captures across all forty runs and is worse on the graded cells.

## ☐ A7 · two λ-ablation notes — **−26**
Both are pure table notes:

> All rows use the protocol of Table 3.9 and differ only in 𝜆.

> All rows use the configuration of Table 3.10 and differ only in 𝜆.

**Remove both** and append `All rows use the protocol of Table 3.9 and differ only in 𝜆.`
(and the 3.10 equivalent) to the caption of the ablation table each precedes.

## ☐ A8 · §3.1 signpost — **−17, delete outright**
**Remove:**
> The work has two halves set out in Figure 3.1 and mapped to objectives in Table 3.1.

Figure 3.1 and Table 3.1 are both on the page and captioned. The sentence announces them
rather than saying anything.

## ☐ A9 · Table 2.1 lead-in — **−20 by compression**
**Find:**
> Frequency shifts caused by damage compete with shifts caused by the environment, and Table 2.1 shows the comparison is unfavourable: the nuisance is one to two orders of magnitude larger than the change of interest.

**Replace:**
> Frequency shifts caused by damage compete with shifts caused by the environment, and the nuisance is the larger by one to two orders of magnitude (Table 2.1).

**Part A total: about −194**

---

# PART B — still outstanding from the last list

## ☐ B1 · §2.3, the I-40 sentence — **−24, delete**
> In a comparative study on the I-40 bridge, the methods trialled located damage only at the most severe of four levels (Farrar and Jauregui, 1998).

§5.2 makes the same point and does more with it, using I-40 as the published comparison for
your own localisation result. Here it is illustration, and the sentence before already
establishes that multi-point methods need sensors you do not have.

## ☐ B2 · §2.1, masonry failure — **−20 by compression**
**Find:**
> Such buildings fail under lateral loading through in-plane diagonal shear cracking (Hafner et al., 2023) and through out-of-plane mechanisms, among the most dangerous in earthquakes, whose activation depends on the strength of connections between walls, floors and roofs (Destro Bisol et al., 2024).

**Replace:**
> Such buildings fail through in-plane shear cracking and through out-of-plane mechanisms whose activation depends on wall-to-floor connections (Hafner et al., 2023; Destro Bisol et al., 2024).

§5.5 repeats this near-verbatim, where it carries the transfer-limitation argument.

## ☐ B3 · §3.6.4 compression — **−30**
Still has the orphan one-line paragraph. Replacement text is in `WORDCUT_LIST.md` item B1b.

**Part B total: about −74**

---

# Running total

| | words |
|---|---|
| Part A, caption relocation | **−194** |
| Part B, duplications and §3.6.4 | **−74** |
| | **−268** |

12,221 − 268 = **about 11,953**. That clears the cap with 47 words of margin.

If you want more headroom, the §3.6.1 relocation to Appendix A.7 from the first list is
still available and worth roughly another 120.

---

# One error still outstanding

**§3.3 has a truncated sentence.** *"The measurement programme is given in"* — the
reference never resolves. Should presumably be `Table 3.5`. This was on the last list and
has not been applied.

"""
word_budget.py — exact word deltas for every proposed edit

THE BASELINE CANNOT BE VERIFIED HERE. There is no .tex source on this machine
(searched: the repository, ~/Documents, ~/Desktop, ~/Downloads, iCloud Drive, and
the connected Google Drive; only the compiled PDF and unrelated .tex files exist),
and texcount is not installed. So the author's 11,975 is taken as given.

What IS computable, and what the <= +25 constraint actually needs, is the DELTA
of each edit. Deltas are exact: they are counted on the literal OLD and NEW
strings of the edit list, under texcount's convention.

Counting convention, matched to texcount -brief:
  * a word is a whitespace-separated token containing at least one letter or digit
  * inline maths ($...$) counts as one word, as texcount does by default
  * citation keys inside \\cite{} are not counted (uncounted per the guidelines)
  * a token that is pure punctuation is not counted

AUTHORITATIVE INVOCATION, for the author to run on the real source:

    texcount -inc -sum -brief main.tex

  and for the per-section breakdown used to target cuts:

    texcount -inc -sub=section main.tex

  texcount excludes floats (table and figure environments) and their captions by
  default, which matches the marking guidelines. Verify with:

    texcount -inc -sum -brief -v3 main.tex | head -40
"""
import re
import sys

# Each edit: (id, location, counted, old_text, new_text)
# counted=False for tables, captions, appendices and front matter, which the
# guidelines exclude from the count.
EDITS = [
    ("E1", "Abstract, localisation sentence", True,
     "The network inherits the same parametrisation and reaches 6 of 9 against "
     "the classical rule's of 9 of 9.",
     "The network inherits the same parametrisation and calls 3 of 6 against the "
     "classical rule's 6 of 6, scored on the records where both can be wrong."),

    ("E2", "Abstract, per-run claim", True,
     "nearest-signature matching on floor-normalised shifts assigned all twelve "
     "replicated severe runs correctly and 18 of 18 at two further sensor positions.",
     "nearest-signature matching on floor-normalised shifts assigned every "
     "replicated severe run correctly in both fixed signature spaces, and 18 of 18 "
     "at two further sensor positions."),

    ("E3", "Abstract, grammar", True,
     "Its physics term cut the residual it penalises by 17.8% and moved on task "
     "metric beyond fold and seed scatter.",
     "Its physics term cut the residual it penalises by 17.8% and moved no task "
     "metric beyond fold and seed scatter."),

    ("E4", "Abstract, typo", True,
     "how much damage information a single-low cost accelerometer establishes",
     "how much damage information a single low-cost accelerometer establishes"),

    ("E5", "Conclusion, localisation", True,
     "Localisation is the strongest positive result: 12 of 12 replicated severe "
     "runs correct, and 18 of 18 at two other sensor positions against references "
     "recorded elsewhere.",
     "Localisation is the strongest positive result: every replicated severe run "
     "correct in both fixed signature spaces, and 18 of 18 at two other sensor "
     "positions against references recorded elsewhere."),

    ("E6", "Conclusion, comparison", True,
     "The classical route is the one to put on a low-cost node: it returns 9 of 9 "
     "where the network returns 6 of 9, and needs no forward model and no "
     "retargeting per structure.",
     "The classical route is the one to put on a low-cost node: on the six severe "
     "records where both methods can be wrong it returns 6 of 6 where the network "
     "returns 3 of 6, and needs no forward model and no retargeting per structure."),

    ("E7", "Section 4.1.5, linearity (item 1.8)", True,
     "Swept-sine replicates at three drive amplitudes spanning a factor of 2.2 "
     "showed no statistically significant dependence of f1 on excitation level "
     "(t = -0.63, p = 0.573).",
     "Swept-sine replicates at three drive amplitudes spanning a factor of 2.2 "
     "gave no detectable dependence of f1 on excitation level, comparing the "
     "extreme gains (Welch t = -0.63, p = 0.573, n = 3 per group). The within-gain "
     "scatter of the estimate is 1.79% of f1, so the test bounds any drive-induced "
     "shift at roughly 3.6% and cannot resolve effects below that. The trace-grade "
     "shifts are instead controlled by the within-cell tap scatter of Table 4.5, "
     "below 0.3% at every trace cell."),

    ("E8", "Section 4.3 opening (item 1.8)", True,
     "Tap amplitude varied by roughly a factor of ten across sets, which Section "
     "4.1.5 shows does not affect the frequency estimates, though the damping "
     "estimates from this series are not comparable.",
     "Tap amplitude varied by a factor of 2.5 across sets, comparable to the 2.2 "
     "range tested in Section 4.1.5, and within-cell tap scatter is below 0.3% at "
     "every trace cell, though the damping estimates from this series are not "
     "comparable."),

    ("E9", "l.1894, scatter ceiling", True,
     "Floor 3 stay at or below 0.76% at every grade against 0.20% on the baseline "
     "(Table 4.5)",
     "Floor 3 stay at or below 0.76% at every grade against 0.20% on the baseline "
     "(Table 4.5; the figure below plots a wider statistic, see its caption)"),

    ("E10", "l.1487, stiffness ratio (item 1.6)", True,
     "of 1 : 1.192 : 0.983 show the storeys are not uniform, which is",
     "of 1 : 1.192 : 0.983 show the middle storey is about 19% stiffer than the "
     "lower, while the upper and lower are not separated (k3/k1 95% interval "
     "0.960 to 1.006), which is"),

    ("E11", "l.2744, Discussion separation (items 1.2g, 1.7b)", True,
     "separated by 33 floor-units against a largest replicate standard deviation "
     "of 1.7 (Section 4.4.1)",
     "separated by 33.0 floor-units against a largest run-to-own-mean distance of "
     "3.09 in the same three-mode space, a ratio of 10.7"),

    ("E12", "Section 4.4, permutation limitation (item 1.2f)", True,
     "",
     "No permutation test of the location effect is valid for this design. "
     "Permuting individual runs would treat three replicates of one damage "
     "application as independent, and permuting intact replicate groups leaves the "
     "leave-one-out statistic unchanged by construction, so it has no power. "
     "Separating location from rebuild would require independent rebuilds within a "
     "cell rather than repeated taps."),

    ("E13", "l.2937 and l.2947, Section 5.4 (item 1.5c)", True,
     "f1 scatters 85 times more than f3 so the instability is",
     "f1 scatters about 84 times more than f3 by standard deviation so the "
     "instability is"),

    ("E14", "Section 4.6, network localisation prose", True,
     "The network cannot be scored on three of these because",
     "Floor 3 is absent from both methods because"),

    # ---- uncounted: tables, captions, appendices ----
    ("U1", "Table 4.18, localisation row and footnote (item 1.4)", False, "", ""),
    ("U2", "Table 4.8, p column and caption (item 1.2)", False, "", ""),
    ("U3", "Table 4.6 caption (item 1.2e)", False, "", ""),
    ("U4", "Table 5.1, two rows (items 1.2, 1.4)", False, "", ""),
    ("U5", "Table 3.10, scoring rule (item 1.3)", False, "", ""),
    ("U6", "Table 4.5 caption (item 1.1) and Floor 3 light cell (1.1b)", False, "", ""),
    ("U7", "Table 4.16, add branch, fix n, drop residual column (1.5a)", False, "", ""),
    ("U8", "Scatter figure caption (item 1.7)", False, "", ""),
    ("U9", "Appendix A.1 note (b), 4.98 and 5.2 (item 1.4g)", False, "", ""),
    ("U10", "Appendix A.1/A.2 captions, state the two baselines (Part 2)", False, "", ""),
    ("U11", "l.1515 assumptions table, 'bounds' (item 1.8)", False, "", ""),
    ("U12", "l.3092 appendix, spread and 8.010 (item 1.5c)", False, "", ""),
]

# LEAN VARIANT. Same substance, with every detail that does not have to be in
# body text relocated to a caption, a table footnote or the appendix, all of
# which the guidelines exclude from the count. Only the item 1.2 limitation
# paragraph (E12) is kept at full length in the body, because it is the one
# addition that earns marks under "limitations and critical evaluation".
LEAN = {
    "E2": ("nearest-signature matching on floor-normalised shifts assigned all "
           "twelve replicated severe runs correctly and 18 of 18 at two further "
           "sensor positions.",
           "nearest-signature matching on floor-normalised shifts assigned every "
           "replicated severe run correctly and 18 of 18 at two further sensor "
           "positions."),
    "E5": ("Localisation is the strongest positive result: 12 of 12 replicated "
           "severe runs correct, and 18 of 18 at two other sensor positions "
           "against references recorded elsewhere.",
           "Localisation is the strongest positive result: every replicated severe "
           "run correct, and 18 of 18 at two other sensor positions against "
           "references recorded elsewhere."),
    "E12": ("",
            "No permutation test of the location effect is valid here. Permuting "
            "runs treats three replicates of one damage application as "
            "independent; permuting intact groups leaves the leave-one-out "
            "statistic unchanged by construction, so it has no power. Separating "
            "location from rebuild needs independent rebuilds per cell."),
    "E1": ("The network inherits the same parametrisation and reaches 6 of 9 "
           "against the classical rule's of 9 of 9.",
           "The network inherits the same parametrisation and calls 3 of 6 "
           "against the classical rule's 6 of 6."),
    "E6": ("The classical route is the one to put on a low-cost node: it returns "
           "9 of 9 where the network returns 6 of 9, and needs no forward model "
           "and no retargeting per structure.",
           "The classical route is the one to put on a low-cost node: it returns "
           "6 of 6 where the network returns 3 of 6, and needs no forward model "
           "and no retargeting per structure."),
    "E7": ("Swept-sine replicates at three drive amplitudes spanning a factor of "
           "2.2 showed no statistically significant dependence of f1 on "
           "excitation level (t = -0.63, p = 0.573).",
           "Swept-sine replicates at three drive amplitudes spanning a factor of "
           "2.2 gave no detectable dependence of f1 on excitation level "
           "(t = -0.63, p = 0.573); the test bounds a drive-induced shift at "
           "roughly 3.6% and no lower, so the trace grade rests on the tap "
           "scatter of Table 4.5 (Appendix A.3)."),
    "E8": ("Tap amplitude varied by roughly a factor of ten across sets, which "
           "Section 4.1.5 shows does not affect the frequency estimates, though "
           "the damping estimates from this series are not comparable.",
           "Tap amplitude varied by a factor of 2.5 across sets, inside the range "
           "tested in Section 4.1.5, though the damping estimates from this "
           "series are not comparable."),
    "E9": ("Floor 3 stay at or below 0.76% at every grade against 0.20% on the "
           "baseline (Table 4.5)",
           "Floor 3 stay at or below 0.76% at every grade against 0.20% on the "
           "baseline (Table 4.5)"),          # basis note moves to the caption
    "E10": ("of 1 : 1.192 : 0.983 show the storeys are not uniform, which is",
            "of 1 : 1.192 : 0.983 show the middle storey is the stiffest, which is"),
    "E11": ("separated by 33 floor-units against a largest replicate standard "
            "deviation of 1.7 (Section 4.4.1)",
            "separated by 33.0 floor-units against a largest run-to-own-mean "
            "distance of 3.09, a ratio of 10.7"),
    "E13": ("f1 scatters 85 times more than f3 so the instability is",
            "f1 scatters about 84 times more than f3 so the instability is"),
}


# Cuts that fund the additions. Each is a relocation or a deletion of text that
# repeats something already stated, per the guidelines' "restatements of results"
# and "long reviews" categories. None touches interpretation or limitations.
CUTS = [
    ("C1", "Section 5.4, restates its own opening two sentences earlier",
     "A first mode that moves 12.75% across five nominally identical taps on a "
     "fixed physical state, while the third mode holds to 0.15%, points to an "
     "amplitude-dependent contact condition",
     "That points to an amplitude-dependent contact condition"),
    ("C2", "l.1978, p clause deleted by item 1.2e anyway",
     "at a group permutation p = 0.0075; the base-plate median is 1.967% against "
     "0.198% elsewhere",
     "the base-plate median is 1.967% against 0.198% elsewhere"),
    ("C3", "l.2942, the same p clause in the Discussion",
     "against a chance rate of 25%, at a group permutation p = 0.0075, and the "
     "effect is driven",
     "against a chance rate of 25%, and the effect is driven"),
    ("C4", "Abstract, restates the conclusion's closing sentence",
     "The obstacle is the shear-chain model those routes share rather than the "
     "resolution of the measurement.",
     "The obstacle is the shear-chain model those routes share."),
]

TOKEN = re.compile(r"[A-Za-z0-9]")


def count(text):
    """texcount -brief convention: whitespace tokens containing a letter or digit."""
    if not text.strip():
        return 0
    text = re.sub(r"\\cite\{[^}]*\}", "", text)
    text = re.sub(r"\$[^$]*\$", " MATH ", text)
    return sum(1 for t in text.split() if TOKEN.search(t))


def main():
    print("Word budget — exact deltas per edit\n" + "=" * 78)
    print("BASELINE UNVERIFIED: no .tex source on this machine, texcount not")
    print("installed. 11,975 is taken from the author. Deltas below are exact.\n")
    hdr = f"  {'ID':4s} {'location':46s} {'-':>4s} {'+':>4s} {'net':>5s} {'run':>5s}"
    print(hdr + "\n  " + "-" * (len(hdr) - 2))
    run = 0
    for eid, loc, counted, old, new in EDITS:
        if not counted:
            print(f"  {eid:4s} {loc[:46]:46s} {'-':>4s} {'-':>4s} "
                  f"{'n/c':>5s} {run:+5d}")
            continue
        o, n = count(old), count(new)
        run += n - o
        print(f"  {eid:4s} {loc[:46]:46s} {o:4d} {n:4d} {n - o:+5d} {run:+5d}")
    print("  " + "-" * (len(hdr) - 2))
    print(f"  {'':4s} {'RUNNING NET TOTAL':46s} {'':4s} {'':4s} {'':5s} {run:+5d}")
    print(f"\n  headroom stated by the author : +25")
    print(f"  net of all counted edits      : {run:+d}")
    print(f"  {'WITHIN BUDGET' if run <= 25 else 'OVER BUDGET by ' + str(run - 25) + ' words'}")

    print(f"\n\nLEAN VARIANT — same substance, detail relocated to captions,\n"
          f"table footnotes and the appendix, which are uncounted\n" + "=" * 78)
    print(hdr + "\n  " + "-" * (len(hdr) - 2))
    lean = 0
    for eid, loc, counted, old, new in EDITS:
        if not counted:
            continue
        o_t, n_t = LEAN.get(eid, (old, new))
        o, n = count(o_t), count(n_t)
        lean += n - o
        flag = "  <- relocated" if eid in LEAN else ""
        print(f"  {eid:4s} {loc[:46]:46s} {o:4d} {n:4d} {n - o:+5d} "
              f"{lean:+5d}{flag}")
    print("  " + "-" * (len(hdr) - 2))
    print(f"  {'':4s} {'LEAN NET TOTAL':46s} {'':4s} {'':4s} {'':5s} {lean:+5d}")
    print(f"\n  saved by relocation           : {run - lean} words")
    print(f"  lean net                      : {lean:+d}  against +25 headroom")
    if lean <= 25:
        print(f"  WITHIN BUDGET with {25 - lean} words to spare. No cuts required.")
    else:
        print(f"  STILL OVER by {lean - 25}. Cuts required; see EDIT_LIST.md table 2.")
    print(f"\n\nCUTS THAT FUND THE ADDITIONS\n" + "=" * 78)
    print(f"  {'ID':4s} {'what':56s} {'-':>4s} {'+':>4s} {'saves':>6s}")
    print("  " + "-" * 76)
    saved = 0
    for cid, what, old, new in CUTS:
        o, n = count(old), count(new)
        saved += o - n
        print(f"  {cid:4s} {what[:56]:56s} {o:4d} {n:4d} {o - n:6d}")
    print("  " + "-" * 76)
    print(f"  {'':4s} {'TOTAL FREED':56s} {'':4s} {'':4s} {saved:6d}")
    final = lean - saved
    print(f"\n  FINAL BUDGET")
    print(f"    lean net of all counted edits   {lean:+5d}")
    print(f"    less cuts                       {-saved:+5d}")
    print(f"    NET AGAINST THE 11,975 BASELINE {final:+5d}")
    print(f"    headroom                          +25")
    print(f"    {'WITHIN BUDGET, ' + str(25 - final) + ' words to spare' if final <= 25 else 'OVER by ' + str(final - 25)}")
    return 0 if final <= 25 else 1


if __name__ == "__main__":
    sys.exit(main())
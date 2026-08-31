# Data availability statement

Two sentences, for the front matter or the head of the appendix. Insert the DOI
once the Zenodo deposit mints one.

## Front matter version (uncounted if placed with the front matter)

> All measurements, analysis code and derived results are openly available. The
> 354 raw tap captures, the analysis scripts and the reconciliation of every
> reported figure are deposited at Zenodo (DOI: [INSERT]) and mirrored at
> https://github.com/Eric56123/Building_Sensor at commit `b0aba33`.

## Appendix version, if a little more detail is wanted

> All measurements, analysis code and derived results are openly available. The
> 354 raw tap captures from the three-storey campaign, the 85 captures from the
> superseded four-storey campaign, all analysis scripts, and a reconciliation
> listing every reported figure against its recomputed value are deposited at
> Zenodo (DOI: [INSERT]) and mirrored at
> https://github.com/Eric56123/Building_Sensor at commit `b0aba33`; the capture
> inventory of Appendix A.6 maps each measurement set to the tables it feeds.

## Zenodo deposit checklist

Do this early. Minting can take a little while and the link has to be in the
submission email.

1. Zenodo → New upload. Upload two folders: `characterisation/` (124 MB) and
   `superseded_four_storey_campaign/` (22 MB).
2. Upload type **Dataset**. Title: "Single-accelerometer modal measurements of a
   three-storey steel shear frame with graded screwed-joint damage".
3. Include `README.txt` and `MANIFEST.txt` from `audit/data_package/` at the top
   level of the deposit.
4. Licence: CC-BY-4.0 unless UCL requires otherwise.
5. Under Related identifiers, add the GitHub repository URL as *is supplemented
   by this upload*.
6. Publish, then paste the DOI into the statement above and into
   `audit/data_package/README.txt` where it says `[TO BE INSERTED]`.
7. Re-zip `audit/data_package/` so the emailed copy carries the DOI.

Zenodo's per-file limit is 50 GB, so 146 MB needs no special handling.

## What goes in the submission email

- The dissertation PDF.
- `audit/data_package.zip` (15 KB): derived results, the capture manifest, and
  the file-to-table map.
- The Zenodo DOI for the raw captures.

The raw captures are 124 MB and were never going to attach. The package above is
deliberately small and self-describing: a marker can open `README.txt`, pick any
Chapter 4 number, and see which file produces it, then fetch only that file from
the deposit if they want to check it.

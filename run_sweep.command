#!/usr/bin/env bash
# Double-click this file in Finder to launch the pilot sweep in Terminal.
# It is just a wrapper around run_sweep.sh so no typing is needed.
cd "$(dirname "$0")"
bash run_sweep.sh pilot
echo ""
echo "----------------------------------------------------------"
echo "Pilot finished. Results: experiments/results_summary_continuous.csv"
echo "For the full sweep + 5-fold CV, run:  bash run_sweep.sh full"
echo "----------------------------------------------------------"
echo "Press any key to close."
read -n 1 -s

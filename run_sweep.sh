#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# run_sweep.sh -- lambda sweep on the continuous-alpha dataset
#
#   bash run_sweep.sh            # pilot (100 epochs) then full holdout + 5-fold
#   bash run_sweep.sh pilot      # pilot only  -- ~minutes, tells you if lambda matters
#   bash run_sweep.sh full       # skip the pilot, go straight to the real runs
#
# Outputs land in ./experiments/:
#   loss_log_lam{L}_{fold}_continuous.csv
#   results_summary_continuous.csv
# ---------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")"

STAGE="${1:-all}"

# Torch has no MPS kernel for SVD; the physics loss falls back to CPU for that
# op. This env var stops the fallback from raising instead of falling back.
export PYTORCH_ENABLE_MPS_FALLBACK=1

# --- venv -------------------------------------------------------------------
if [ ! -d .venv ]; then
  echo "ERROR: no .venv here. Create it, then: pip install torch numpy scipy"
  exit 1
fi
# shellcheck disable=SC1091
source .venv/bin/activate
echo "[env] python: $(which python)"
python - <<'PY'
import torch, numpy, scipy
print(f"[env] torch {torch.__version__} | numpy {numpy.__version__} | scipy {scipy.__version__}")
print(f"[env] MPS available: {torch.backends.mps.is_available()}")
PY

# --- dataset sanity ---------------------------------------------------------
if [ ! -d data/continuous ]; then
  echo "ERROR: data/continuous missing. Regenerate with:"
  echo "  python -m four_floor.simulation.generate_dataset --n-alpha 500"
  exit 1
fi
python - <<'PY'
import numpy as np
from four_floor.simulation.generate_dataset import load_dataset
d = load_dataset()
n, g = len(d["psd"]), len(np.unique(d["alpha_id"]))
u = len(np.unique(d["alpha"], axis=0))
print(f"[data] {n} windows | {g} alpha groups | {u} unique alpha vectors")
assert n == 10000 and g == 500, "dataset looks incomplete -- regenerate it"
assert not np.isnan(d["psd"]).any(), "NaNs in PSD"
print("[data] OK")
PY

# --- pilot: 100 epochs, cheap read on whether lambda moves anything ----------
if [ "$STAGE" = "all" ] || [ "$STAGE" = "pilot" ]; then
  echo ""
  echo "=========================================================="
  echo " PILOT  --  100 epochs, holdout, lambda in {0, 0.1}"
  echo " If lambda=0.1 is no better than lambda=0 here, stop and think"
  echo " before spending hours on the full sweep."
  echo "=========================================================="
  python -m four_floor.run_experiments \
      --dataset continuous --mode holdout --epochs 100 --lambdas 0.0 0.1
  [ "$STAGE" = "pilot" ] && exit 0
fi

# --- full holdout sweep -----------------------------------------------------
echo ""
echo "=========================================================="
echo " HOLDOUT  --  200 epochs, lambda in {0, 0.01, 0.1, 1.0}"
echo "=========================================================="
python -m four_floor.run_experiments --dataset continuous --mode holdout

# --- 5-fold group CV: the numbers that go in the dissertation ---------------
echo ""
echo "=========================================================="
echo " 5-FOLD GROUP CV  --  the numbers for Results"
echo "=========================================================="
python -m four_floor.run_experiments --dataset continuous --mode kfold --k 5

echo ""
echo "[done] see experiments/results_summary_continuous.csv"

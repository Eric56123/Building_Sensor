"""
classification.py — the ONE damage-index classification policy
==============================================================
DI = (1 - alpha) * 10 per channel; the global index is the worst (max) channel;
the status/colour come from the config.DI_WARN / config.DI_CRITICAL thresholds.

This lived inline in monitor.py and was re-implemented a second time in the
analysis toolkit. This project has already been bitten by exactly that pattern:
main.py's preprocess() and sensor_driver.py's preprocess_for_pinn() silently
diverged (see the live_features.py docstring). To make a repeat impossible, the
policy now lives here and both monitor.py and the toolkit import it. Changing a
threshold or the DI formula is a one-file edit that both consumers pick up.

`classify()` keeps monitor.py's exact return signature and behaviour
(colour, status, global_DI, dis) so the deployment is unchanged.
"""
import numpy as np

import config


def compute_di(alphas):
    """Per-channel damage index DI = (1 - alpha) * 10, as a float array."""
    return (1.0 - np.asarray(alphas, dtype=float)) * 10.0


def classify(alphas):
    """
    Returns (colour, status, global_DI, dis) — identical to the original
    monitor.classify:
        dis        : per-channel DI array
        global_DI  : max over channels (worst floor drives the alarm)
        status     : "HEALTHY" / "WARNING" / "CRITICAL"
        colour     : the matching config LED colour tuple
    """
    dis = compute_di(alphas)
    global_di = float(np.max(dis))
    if global_di < config.DI_WARN:
        return config.GREEN, "HEALTHY", global_di, dis
    elif global_di < config.DI_CRITICAL:
        return config.AMBER, "WARNING", global_di, dis
    return config.RED, "CRITICAL", global_di, dis

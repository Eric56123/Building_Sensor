"""
REMOVED — this filename collided with the existing preprocessing/ package
(training-data cleaning/normalisation) in this same directory. Python
would prefer that package over this module, silently breaking any import
of this file — so the live signal-processing pipeline was moved to
live_features.py instead.

Safe to delete:

    rm four_floor/preprocessing.py

Kept only as a placeholder because this environment couldn't delete the
file directly — your Terminal can. (The preprocessing/ directory next to
it is the original training package and should stay.)
"""

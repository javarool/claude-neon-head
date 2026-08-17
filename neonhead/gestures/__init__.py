"""Gesture presets, one module per gesture.

Unlike emotions/ (a static pose), a gesture is a short animation: a few
cycles of motion on one head axis, then it clears itself. Each module
exposes NAME, ALIASES, AXIS (a rig.NEUTRAL key), AMPLITUDE, PERIOD_S and
CYCLES. This file scans the package directory and collects them into
GESTURES/GESTURE_ALIASES — drop a new gesture_name.py in here and it's
usable with no other edits.
"""

import importlib
import pkgutil

_modules = []
for _info in pkgutil.iter_modules(__path__):
    if _info.name.startswith("_"):
        continue
    _mod = importlib.import_module(f".{_info.name}", package=__name__)
    if hasattr(_mod, "NAME") and hasattr(_mod, "AXIS"):
        _modules.append(_mod)

_modules.sort(key=lambda m: m.NAME)

GESTURES = {
    m.NAME.lower(): {"axis": m.AXIS, "amp": m.AMPLITUDE, "period_s": m.PERIOD_S,
                     "cycles": m.CYCLES}
    for m in _modules
}

# Lookups are case-insensitive, so both sides of the alias map are folded
# to lowercase regardless of how a module's NAME/ALIASES are cased.
GESTURE_ALIASES = {}
for _m in _modules:
    for _alias in getattr(_m, "ALIASES", ()):
        GESTURE_ALIASES[_alias.lower()] = _m.NAME.lower()

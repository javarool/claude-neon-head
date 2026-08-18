"""Gesture presets, one module per gesture.

Unlike emotions/ (a static pose), a gesture is a short animation, then it
clears itself. Each module exposes NAME, ALIASES, AXIS (a rig.NEUTRAL key),
AMPLITUDE, and one of two timing shapes:

- oscillating (most gestures — nod, shake): PERIOD_S + CYCLES. rig.py
  drives `sin(t/period*tau)*amp`, so it bounces both directions each cycle.
- rise/hold/fall (e.g. flip): RISE_S, HOLD_S, FALL_S. Eases up to `amp`,
  sits there for HOLD_S, eases back to 0 — for a gesture that needs to
  *stay* at its peak for a beat instead of bouncing straight through it.
  A module using this shape omits PERIOD_S/CYCLES; rig.py picks the mode
  by which attrs are present.

This file scans the package directory and collects them into
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
    m.NAME.lower(): {
        "axis": m.AXIS, "amp": m.AMPLITUDE,
        "period_s": getattr(m, "PERIOD_S", None),
        "cycles": getattr(m, "CYCLES", None),
        "rise_s": getattr(m, "RISE_S", None),
        "hold_s": getattr(m, "HOLD_S", None),
        "fall_s": getattr(m, "FALL_S", None),
    }
    for m in _modules
}

# Lookups are case-insensitive, so both sides of the alias map are folded
# to lowercase regardless of how a module's NAME/ALIASES are cased.
GESTURE_ALIASES = {}
for _m in _modules:
    for _alias in getattr(_m, "ALIASES", ()):
        GESTURE_ALIASES[_alias.lower()] = _m.NAME.lower()

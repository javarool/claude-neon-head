"""Emotion presets, one module per emotion.

Each module exposes NAME, ALIASES (Russian names the net protocol accepts)
and PRESET (offsets from the neutral pose, see rig.NEUTRAL). This file
scans the package directory for such modules and collects them into the
two dicts rig.py consumes — drop a new emotion_name.py in here and it
shows up in EMOTIONS (and the demo cycle) with no other edits.
"""

import importlib
import pkgutil

_modules = []
for _info in pkgutil.iter_modules(__path__):
    if _info.name.startswith("_"):
        continue
    _mod = importlib.import_module(f".{_info.name}", package=__name__)
    if hasattr(_mod, "NAME") and hasattr(_mod, "PRESET"):
        _modules.append(_mod)

# Neutral first, then alphabetical — stable order for hotkeys and the demo.
_modules.sort(key=lambda m: (m.NAME != "neutral", m.NAME))

EMOTIONS = {m.NAME.lower(): dict(m.PRESET) for m in _modules}

# Lookups are case-insensitive, so both sides of the alias map are folded
# to lowercase regardless of how a module's NAME/ALIASES are cased.
EMOTION_ALIASES = {}
for _m in _modules:
    for _alias in getattr(_m, "ALIASES", ()):
        EMOTION_ALIASES[_alias.lower()] = _m.NAME.lower()

import math

NAME = "flip"
ALIASES = ("upside_down", "somersault", "перевернуться")

# Spins the whole head 180 degrees, holds upside down for a beat, then
# spins back — works on top of whatever emotion is currently set, same as
# every other gesture. head_roll is the one gesture axis that's a genuine
# rotation (radians) of the whole frame, not a small screen-offset
# fraction of R like head_yaw/head_pitch (see rig.NEUTRAL), so AMPLITUDE
# here is math.pi rather than the usual ~0.02-0.09.
#
# RISE_S/HOLD_S/FALL_S instead of PERIOD_S/CYCLES: this is the "ease up,
# sit, ease back" gesture shape (see gestures/__init__.py), not an
# oscillating bounce — the flip needs to actually stay upside down for a
# second, not swing straight through it.
AXIS = "head_roll"
AMPLITUDE = math.pi
RISE_S = 0.30
HOLD_S = 1.0
FALL_S = 0.30

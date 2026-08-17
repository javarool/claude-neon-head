NAME = "no"
ALIASES = ("нет", "отказ", "несогласие", "disapprove", "disagree")

# Shake: head_yaw oscillates a few times, eased in/out by rig.Rig.
# head_yaw is a fraction of head radius R (see geometry.build: cx = ... +
# p["head_yaw"] * R), same units as idle sway (~0.02-0.04 peak) — keep
# gesture amplitude in that same small range or the head flies off screen.
AXIS = "head_yaw"
AMPLITUDE = 0.09
PERIOD_S = 0.42
CYCLES = 3

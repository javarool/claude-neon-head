NAME = "yes"
ALIASES = ("да", "согласие", "кивок", "agree", "approve")

# Nod: head_pitch oscillates a few times, eased in/out by rig.Rig.
# head_pitch is a fraction of head radius R (see geometry.build: cy = ... +
# p["head_pitch"] * R), same units as idle sway (~0.02-0.04 peak) — keep
# gesture amplitude in that same small range or the head flies off screen.
AXIS = "head_pitch"
AMPLITUDE = 0.07
PERIOD_S = 0.55
CYCLES = 3

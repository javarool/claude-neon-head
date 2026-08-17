NAME = "shrug"
ALIASES = ("dunno", "idk", "unsure")

# Unlike yes/no (head_pitch/head_yaw), this rocks a single brow up and
# down a couple of times — a raised-eyebrow "hm, dunno" tell instead of a
# head motion, so it reads as puzzlement rather than agreement/disagreement.
# brow_tilt_l lives in the same small offset range emotion presets use for
# it (see doubt.py/anxiety.py), not the head-radius-fraction range yes/no
# use, since this axis is a brow param, not a head position.
AXIS = "brow_tilt_l"
AMPLITUDE = 0.35
PERIOD_S = 0.5
CYCLES = 2

NAME = "sleep"
ALIASES = ("sleeping", "asleep", "sleepy", "спать", "сон", "спит")

# Lids drop shut (plain eye_h collapse, no eye_dead) and everything slows
# down and dims a notch — alive, just resting, content (small mouth_curve
# lift), with drifting "Zzz" glyphs (see geometry._letter_z) to sell it.
# `dead` is the same lid collapse plus eye_dead, but reads as gone.
PRESET = {
    "eye_h": -0.95,
    "brow_y_l": -0.05, "brow_y_r": -0.05, "brow_tilt_l": -0.15, "brow_tilt_r": -0.15,
    "mouth_curve": 0.18, "glow_gain": -0.30, "ring_spread": -0.08,
    "orbit_speed": 0.35, "zzz": 1.0,
}

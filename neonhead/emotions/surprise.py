NAME = "surprise"
ALIASES = ("amazement", "shock", "wow")

# Brows jump straight up and arch, eyes go round (eye_oval, not just wide —
# a full circle reads more "startled" than the usual dome), mouth drops
# into an egg-shaped "O" (mouth_oval — the same uncropped-ellipse tell
# fear uses) with top AND bottom teeth hanging into the gap — the
# jaw-dropped look, not a smile (mouth_smile here only unlocks the teeth
# bands, same trick joy uses). Planet flinches outward and speeds up,
# whole head flashes brighter — reaction to the unexpected, gone as fast
# as it arrives.
PRESET = {
    "brow_y_l": 1.40, "brow_y_r": 1.40, "brow_tilt_l": -0.10,
    "brow_tilt_r": -0.10, "brow_bend_l": 0.15, "brow_bend_r": 0.15,
    "eye_h": 0.755, "eye_w": -0.028, "eye_oval": 1.0, "pupil_scale": 1.0,
    "mouth_oval": 1.0, "mouth_smile": 0.80, "mouth_oval_tint": 1.0,
    "exclaim": 1.0,
    "orbit_r": 0.10, "orbit_speed": 1.6, "glow_gain": 0.35, "ring_spread": 0.10,
}

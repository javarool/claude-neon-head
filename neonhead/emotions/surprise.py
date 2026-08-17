NAME = "surprise"
ALIASES = ("amazement", "shock", "wow")

# Brows jump straight up and arch, eyes pop wide, mouth drops into an open
# "o" gasp (mouth_ap is otherwise viseme-only — surprise is the one emotion
# that reaches for it directly), the planet flinches outward and speeds up,
# and the whole head flashes brighter — reaction to the unexpected, gone as
# fast as it arrives.
PRESET = {
    "brow_y_l": 1.00, "brow_y_r": 1.00, "brow_tilt_l": -0.10,
    "brow_tilt_r": -0.10, "brow_bend_l": 0.15, "brow_bend_r": 0.15,
    "eye_h": 0.95, "eye_w": 1.15,
    "mouth_open": 0.55, "mouth_curve": 0.0,
    "orbit_r": 0.10, "orbit_speed": 1.6, "glow_gain": 0.35, "ring_spread": 0.10,
}

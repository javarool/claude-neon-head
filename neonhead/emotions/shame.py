NAME = "shame"
ALIASES = ("embarrassment",)

# Head/gaze drop and brows fall with it, eyes wide (whites showing, caught
# off guard) but averted, mouth pursed into a small "o" rather than curling
# down — withdrawal, not sadness's collapse.
PRESET = {
    "brow_y_l": -0.20, "brow_y_r": -0.20, "brow_tilt_l": -0.30,
    "brow_tilt_r": -0.30, "eye_h": -0.15, "eye_gaze_y": 0.35,
    "mouth_curve": -0.20, "glow_gain": -0.15, "ring_spread": -0.05,
    "blush": 1.0,
    # a small pursed "o" — mouth_oval_scale shrinks fear's full-scream
    # ellipse down to shame's little mouth
    "mouth_oval": 1.0, "mouth_oval_scale": -0.65,
}

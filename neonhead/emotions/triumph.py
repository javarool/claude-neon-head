NAME = "triumph"
ALIASES = ("victory",)

# Joy pushed into a short celebratory spike: bigger orbit/glow burst than
# laugh_to_tears's giddy overload — meant for a one-off "done!" moment
# (e.g. TaskCompleted). No ring_spread here (unlike most "burst" emotions)
# — that grows the outer contour itself, i.e. the head visibly gets
# bigger, which reads wrong for this one. "Like a boss": black sunglasses
# instead of eyes (no arms, just lenses + a glare streak), sharply peaked
# static brows (brow_bend, no brow_wink — a continuous wiggle read as the
# brows "pulsing" rather than reading as a fixed cocky arch), whole face
# sitting a bit higher (head_lift) — proud.
PRESET = {
    "brow_y_l": 0.35, "brow_y_r": 0.35, "brow_tilt_l": -0.20,
    "brow_tilt_r": -0.20, "brow_bend_l": 1.5, "brow_bend_r": 1.5,
    "eye_h": -0.55, "eye_slant": -10.0,
    "mouth_curve": 1.00, "mouth_smile": 1.0,
    "orbit_speed": 1.5, "glow_gain": 0.40,
    "core_glow": 0.20,
    "sunglasses": 1.0, "head_lift": -0.12, "dollar": 1.0,
}

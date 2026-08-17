NAME = "disgust"
ALIASES = ("revulsion", "gross", "ew")

# FACS' disgust markers, approximated with what this rig has: brows drop
# in/down with none of anger's forehead tension (small brow_y), but
# `brow_tilt`/`brow_bend` are flipped negative — inverted from anger's
# knit — so they angle into a sharp downward-pointing V instead of a
# gentle scowl arc. No nose/cheek geometry to wrinkle, so the "recoiling
# sneer" tell is carried by `eye_angry` (a sharp inward-pointing chevron
# replacing the eye dome, geometry._chevron) and `mouth_saw` (the lip line
# rippled into a zigzag of bared points, geometry.build) instead of anger's
# flat scowl or anxiety's round pursed "o". A recoil, not a confrontation.
PRESET = {
    "brow_y_l": -0.45, "brow_y_r": -0.45, "brow_tilt_l": -0.35,
    "brow_tilt_r": -0.35, "brow_bend_l": -0.45, "brow_bend_r": -0.45,
    "eye_angry": 1.0,
    "mouth_narrow": -0.15, "mouth_curve": -0.15,
    "mouth_saw": 1.0,
    "ring_spread": -0.10, "glow_gain": -0.10,
}

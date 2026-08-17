NAME = "disgust"
ALIASES = ("revulsion", "gross", "ew")

# FACS' disgust markers, approximated with what this rig has: brows drop
# only slightly, in/down but with none of anger's forehead tension (small
# brow_y/tilt); eyes narrow more than anger's glare (deep eye_h); no
# nose/cheek geometry to wrinkle, so the "raised upper lip baring teeth"
# tell is carried entirely by the mouth — a tight, slightly open sneer
# (mouth_narrow + mouth_open) with partial teeth reveal (mouth_smile,
# below the full-grin threshold) instead of anger's flat scowl or
# anxiety's round pursed "o". A recoil, not a confrontation.
PRESET = {
    "brow_y_l": -0.15, "brow_y_r": -0.15, "brow_tilt_l": 0.20,
    "brow_tilt_r": 0.20, "eye_h": -0.45, "eye_slant": 14.0,
    "mouth_open": 0.30, "mouth_narrow": -0.20, "mouth_curve": -0.15,
    "mouth_smile": 0.90,
    "ring_spread": -0.10, "glow_gain": -0.10,
}

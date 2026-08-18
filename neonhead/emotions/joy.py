NAME = "joy"
ALIASES = ("smile",)

PRESET = {
    "brow_y_l": 0.25, "brow_y_r": 0.25, "brow_tilt_l": -0.20,
    "brow_tilt_r": -0.20, "eye_h": -0.45, "eye_slant": -8.0,
    "mouth_curve": 1.05, "mouth_smile": 1.0, "hearts": 1.0,
    # mouth_narrow/mouth_open, not mouth_w/mouth_ap directly — those are
    # viseme-owned (see rig.Rig.update), a preset write to them is dead.
    # narrow: +1.25 doubles the resting width (mw formula is 0.60+0.80*w).
    # open: wide enough to clear the ap > R*0.012 teeth-band threshold, so
    # the grin reads as an open crescent with the white teeth strip below.
    "mouth_narrow": 1.25, "mouth_open": 0.40,
    # flat-top-lip/round-bottom grin shape, joy-only (see geometry.build's
    # mouth section) rather than the generic lens all other emotions share
    "mouth_grin": 1.0,
}

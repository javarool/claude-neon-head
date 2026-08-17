NAME = "anxiety"
ALIASES = ("unease", "nervous")

# The "worried" brow: inner corners pulled UP (negative tilt — the opposite
# of anger/disgust's inward-dropping knit), raised and bent into a pleading
# arch. Eyes are blown wide (eye_h > baseline — "cornered prey" stare, not
# a squint) and dart rapidly side to side (eye_dart), blinking twice as
# often (blink_rate) — can't hold still, can't hold a gaze. Mouth purses
# into a small round "o" (narrow + slightly open) rather than curling —
# tense, not recoiling. `shake` adds a high-frequency head judder (see
# rig.update) and `sweat` drips a manga-style droplet off the temple
# (geometry.build) — both are generic channels any emotion can reuse. The
# nose spins at double speed (orbit_speed baseline is 1.0) for fidgety
# energy, the opposite of disgust's pulled-in stillness.
PRESET = {
    "brow_y_l": 0.55, "brow_y_r": 0.55, "brow_tilt_l": -0.35,
    "brow_tilt_r": -0.35, "brow_bend_l": 0.25, "brow_bend_r": 0.25,
    "eye_h": 1.35, "eye_dart": 0.55, "blink_rate": 1.2,
    "mouth_curve": -0.05, "mouth_open": 0.12, "mouth_narrow": -0.30,
    "glow_gain": 0.08, "orbit_speed": 1.0,
    "shake": 0.6, "sweat": 1.0,
}

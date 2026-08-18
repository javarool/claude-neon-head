NAME = "laugh_to_tears"
ALIASES = ("crying with laughter", "cracking up", "lol")

# Everything joy does, pushed past the point of control: eyes squeezed
# almost shut, mouth wide open and curved hard, brows thrown up, plus
# a burst of glow/orbit/ring energy — the "shaking with laughter" tell
# that a calm smile doesn't have.
PRESET = {
    # brows pressed down close to the squeezed eyes, not thrown up — the
    # "can't see straight, wheezing" look rather than surprised-happy
    # brow_y's per-unit move is small (R*0.10 per 1.0) — needs a big
    # offset to actually reach down to pupil height, not the +0.1..0.4
    # range the other emotions use
    "brow_y_l": -3.6, "brow_y_r": -3.6, "brow_tilt_l": -0.35,
    "brow_tilt_r": -0.35, "eye_h": -0.85, "eye_slant": -14.0,
    "mouth_curve": 1.05, "mouth_smile": 1.0, "mouth_open": 0.35, "mouth_narrow": 0.20,
    "ring_spread": 0.12, "orbit_speed": 1.3, "glow_gain": 0.30,
    # joy's grin, dialled up: 5% bigger, 50% wider, thicker teeth (all
    # 1.0-baseline multipliers, offsets here), plus droplets flying off
    # the eye corners — the tells joy doesn't have.
    "mouth_grin": 1.0, "mouth_grin_scale": 0.05, "mouth_grin_width": 0.60,
    "mouth_grin_teeth": 0.17, "tears": 1.0,
    # slow vertical bob — laughing-with-your-whole-body, not shake's fast
    # judder (that's anxiety's tell)
    "bob": 1.0,
}

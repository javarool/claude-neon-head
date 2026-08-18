NAME = "fear"
ALIASES = ("fright",)

# Brows shoot up and pull together. Eyes and mouth both switch to full,
# uncropped ellipses (`eye_oval`/`mouth_oval` — see geometry.build) instead
# of the usual clipped dome/lens shapes: white with a small centred pupil
# (not gaze-driven — a fixed dead-ahead stare) and a screaming "O" mouth
# sized to match. Both are pinned off `eye_h_base` (pre-blink) rather than
# `eye_h`, so the blink collapse — which reads as a twitch, wrong for a
# frozen stare — never touches them. `head_scale`/`head_stretch` bump the
# whole head slightly larger and taller — a face straining, not composed.
# `sausages` pushes two thick capsules up from the bottom of frame against
# the cheeks — something else climbing into view, beyond the face itself.
PRESET = {
    "brow_y_l": 0.65, "brow_y_r": 0.65, "brow_tilt_l": 0.30,
    "brow_tilt_r": 0.30, "eye_h": 0.95, "eye_oval": 1.0,
    "mouth_oval": 1.0,
    "ring_spread": -0.05, "head_scale": 0.10, "head_stretch": 0.12,
    "sausages": 1.0,
    "orbit_speed": 1.4, "glow_gain": -0.10,
}

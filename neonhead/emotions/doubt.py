NAME = "doubt"
ALIASES = ("uncertainty", "skepticism", "suspicious")

# Cartoon skepticism, played all the way to the wall: one "Rock brow" shot
# straight up, the other dropped and knit toward the nose; the eye under
# the raised brow blown wide (eye_h_l), the one under the dropped brow
# squeezed to a sliver (eye_h_r); gaze skewed toward the squint; the mouth
# corner on the squint side dragged down (mouth_tilt) on top of a downward
# curve; head leaning off-centre toward the lowered-brow side; a thin
# monocle ring on the wide eye for good measure. No chin/jaw geometry to
# jut forward or wrinkle, so the mouth carries that read alone.
PRESET = {
    "brow_y_l": 1.00, "brow_y_r": -0.55, "brow_tilt_l": -0.25,
    "brow_tilt_r": 0.55, "brow_bend_r": 0.35,
    "eye_h_l": 0.55, "eye_h_r": -0.70, "eye_gaze_x": -0.45,
    "mouth_curve": -0.30, "mouth_tilt": 0.45,
    "head_tilt": 0.30, "monocle": 1.0,
}

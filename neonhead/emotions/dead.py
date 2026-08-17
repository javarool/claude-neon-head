NAME = "dead"
ALIASES = ("death", "dying", "мертвый", "мёртвый", "смерть")

# eye_dead cross-fades the eyes to a glowing X (see geometry._cross) instead
# of layering it over a closed lid — that closed look is `sleep`'s job.
# orbit_still freezes the planet in place instead of merely slowing it —
# a face can be angry-fast or bored-slow, but the dead don't breathe at all.
# The mouth stays shut (mouth_open at neutral, clamped to 0 by geometry
# anyway) but curls into a big goofy grin (mouth_curve strongly positive —
# same sign joy uses) with a "blep" tongue poking from the corner
# (`tongue`, independent of aperture) — the classic silly-dead look rather
# than a slack open jaw.
PRESET = {
    "eye_dead": 1.0,
    "brow_y_l": -0.15, "brow_y_r": -0.15, "brow_tilt_l": -0.10, "brow_tilt_r": -0.10,
    "brow_bend_l": -0.20, "brow_bend_r": -0.20,
    "mouth_curve": 0.55, "tongue": 1.0,
    "ring_spread": -0.20, "glow_gain": -0.60,
    "orbit_still": 1.0,
}


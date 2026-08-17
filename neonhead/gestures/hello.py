NAME = "hello"
ALIASES = ("привет", "здравствуй", "hi", "wave")

# Same axis as "no" (head_yaw), but a single slow tilt-and-return instead
# of three brisk shakes, so it reads as a friendly greeting nod rather than
# disagreement. Pair with a brief joy/interest emotion (e.g. from the
# SessionStart hook) for the "smiling as it waves" effect — this gesture
# only covers the head motion, same as yes/no leave the face expression
# to the emotion layer.
AXIS = "head_yaw"
AMPLITUDE = 0.08
PERIOD_S = 0.7
CYCLES = 1

"""The rig: ~20 numbers that fully describe the face at any instant.

Three independent layers are summed every frame:

    base emotion   -> brows, eyes, mouth curve, orbit tension
    prosody        -> brow lift, eye openness, core glow, orbit speed
    visemes        -> mouth aperture / width / curve only

Keeping them separate is what lets the head talk and be angry at the same time.
"""

from __future__ import annotations

import math
import random
from typing import Dict

# Emotion presets now live one-per-file in emotions/, each an OFFSET added
# to the neutral pose — that is what lets two emotions be blended by weight.
from .emotions import EMOTIONS, EMOTION_ALIASES

# Gestures (short head-motion animations, e.g. a nod or a shake) live
# one-per-file in gestures/, same scan-the-directory pattern as emotions.
from .gestures import GESTURES, GESTURE_ALIASES

# --------------------------------------------------------------------------
# Visemes: aperture, width, curve. Only these three touch the mouth.
# --------------------------------------------------------------------------

VISEMES: Dict[str, tuple] = {
    "X": (0.00, 0.50, 0.00),   # silence
    "A": (0.00, 0.42, -0.10),  # m b p
    "B": (0.15, 0.78, 0.00),   # s z t d n k i y
    "C": (0.45, 0.60, 0.00),   # e (front)
    "D": (0.90, 0.55, 0.00),   # a
    "E": (0.70, 0.30, 0.00),   # o
    "F": (0.45, 0.18, 0.00),   # u
    "G": (0.20, 0.62, -0.20),  # f v
    "H": (0.50, 0.50, 0.00),   # l r
}

# Russian grapheme -> viseme. Good enough for a stylised head; Russian
# orthography is phonetic enough that letter-level mapping reads correctly.
LETTER_VISEME = {}
for _letters, _shape in (
    ("мбп", "A"), ("сзтднкгхцчшщйиыь", "B"), ("эе", "C"), ("ая", "D"),
    ("оё", "E"), ("ую", "F"), ("фв", "G"), ("лр", "H"), (" ,.!?—-", "X"),
):
    for _c in _letters:
        LETTER_VISEME[_c] = _shape

NEUTRAL: Dict[str, float] = {
    # rings
    "ring_spread": 1.00, "ring_tilt": 0.0,
    # eyes (per-eye eye_h_l/_r offsets stack on the shared eye_h — that's
    # what lets one eye go wide while the other squints, e.g. skepticism)
    "eye_h": 1.00, "eye_slant": 0.0, "eye_gaze_x": 0.0, "eye_gaze_y": 0.0,
    "eye_w": 1.00, "eye_dead": 0.0, "eye_dart": 0.0,
    "eye_h_l": 0.0, "eye_h_r": 0.0, "monocle": 0.0, "eye_angry": 0.0,
    # brows (left / right kept separate — asymmetry is the cheapest nuance)
    "brow_y_l": 0.0, "brow_y_r": 0.0,
    "brow_tilt_l": 0.0, "brow_tilt_r": 0.0,
    "brow_bend_l": 0.0, "brow_bend_r": 0.0,
    # mouth
    "mouth_ap": 0.0, "mouth_w": 0.50, "mouth_curve": 0.05, "mouth_smile": 0.0,
    "mouth_open": 0.0, "mouth_narrow": 0.0, "mouth_tilt": 0.0, "mouth_saw": 0.0,
    # idle
    "blink_rate": 1.0,
    # orbit / core
    "orbit_r": 0.0, "orbit_speed": 1.0, "core_glow": 1.0, "orbit_still": 0.0,
    # global
    "head_yaw": 0.0, "head_pitch": 0.0, "head_tilt": 0.0,
    "glow_gain": 0.0, "zzz": 0.0, "shake": 0.0, "sweat": 0.0, "tongue": 0.0,
}


# Per-channel cross-fade speed, in fractions of blend_ms. <1 arrives early,
# >1 lags — a real face never moves all muscles at the same rate.
CHANNEL_SPEED: Dict[str, float] = {
    "brow_y_l": 0.55, "brow_y_r": 0.55,        # brows lead
    "brow_tilt_l": 0.55, "brow_tilt_r": 0.55,
    "eye_h": 0.75, "eye_slant": 0.75,
    "mouth_curve": 1.25, "mouth_smile": 1.35,  # mouth trails
    "ring_spread": 1.6, "glow_gain": 1.4,      # rings arrive last
}

# Channels allowed to overshoot the target and settle back. Kept off
# mouth_smile / glow_gain, where it reads as jitter rather than life.
OVERSHOOT_CHANNELS = {"brow_y_l", "brow_y_r", "brow_tilt_l", "brow_tilt_r", "eye_slant"}


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _smoothstep(e: float) -> float:
    return e * e * (3 - 2 * e)


def _ease_back(e: float, overshoot: float = 1.7) -> float:
    e = e - 1.0
    return e * e * ((overshoot + 1.0) * e + overshoot) + 1.0


class Rig:
    def __init__(self, cfg):
        self.cfg = cfg
        self.p: Dict[str, float] = dict(NEUTRAL)      # smoothed, what we draw
        self.emotion: Dict[str, float] = {}           # current emotion offsets
        self._emotion_from: Dict[str, float] = {}
        self._emotion_t = 1.0
        self._emotion_dur = 0.001
        self.emotion_name = "neutral"

        # prosody inputs, written by the speech player or `level` commands
        self.rms = 0.0
        self.f0 = 0.0
        self.speaking = False

        # viseme target, driven by the timeline
        self._vis = [0.0, 0.50, 0.05]
        self._vis_target = [0.0, 0.50, 0.05]

        # idle bookkeeping
        self.t = 0.0
        self.silence_t = 0.0
        self._blink_at = random.uniform(2.0, 5.0)
        self._blink_phase = -1.0
        self.orbit_phase = 0.0
        self.precession = 0.0
        self.spin = [0.0, 0.0, 0.0]
        self.overrides: Dict[str, float] = {}
        self.gesture: Dict[str, float] | None = None

    # -- commands ----------------------------------------------------------

    def set_emotion(self, name: str, weight: float = 1.0, blend_ms: float | None = None):
        key = EMOTION_ALIASES.get(name.strip().lower(), name.strip().lower())
        preset = EMOTIONS.get(key)
        if preset is None:
            return False
        self._emotion_from = dict(self.emotion)
        self.emotion = {k: v * weight for k, v in preset.items()}
        self.emotion_name = key
        self._emotion_dur = max(0.001, (blend_ms if blend_ms is not None
                                        else self.cfg.get("speech.emotion_blend_ms", 260)) / 1000.0)
        self._emotion_t = 0.0
        return True

    def set_gesture(self, name: str):
        key = GESTURE_ALIASES.get(name.strip().lower(), name.strip().lower())
        g = GESTURES.get(key)
        if g is None:
            return False
        self.gesture = {"axis": g["axis"], "amp": g["amp"], "period": g["period_s"],
                        "dur": g["cycles"] * g["period_s"], "t": 0.0}
        return True

    def set_viseme(self, shape: str):
        v = VISEMES.get(shape.upper())
        if v:
            self._vis_target = list(v)

    def set_params(self, **kw):
        """Hard override of individual rig values until `clear` is sent."""
        for k, v in kw.items():
            if k in NEUTRAL:
                self.overrides[k] = float(v)

    def clear_overrides(self):
        self.overrides.clear()

    # -- per-frame ---------------------------------------------------------

    def update(self, dt: float):
        self.t += dt
        idle = self.cfg["idle"]

        # emotion cross-fade: each channel runs its own timeline, so brows can
        # lead the mouth instead of every feature sliding in lockstep.
        if self._emotion_t < 1.0:
            self._emotion_t = min(1.0, self._emotion_t + dt / self._emotion_dur)
        keys = set(self.emotion) | set(self._emotion_from)
        emo = {}
        for k in keys:
            e_k = min(1.0, self._emotion_t / CHANNEL_SPEED.get(k, 1.0))
            ease = _ease_back(e_k) if k in OVERSHOOT_CHANNELS else _smoothstep(e_k)
            emo[k] = _lerp(self._emotion_from.get(k, 0.0), self.emotion.get(k, 0.0), ease)

        # viseme smoothing: fast attack, slower release
        att = max(1e-4, self.cfg.get("speech.attack_ms", 45) / 1000.0)
        rel = max(1e-4, self.cfg.get("speech.release_ms", 85) / 1000.0)
        for i in range(3):
            tgt = self._vis_target[i]
            tau = att if tgt > self._vis[i] else rel
            self._vis[i] += (tgt - self._vis[i]) * min(1.0, dt / tau)

        # silence bookkeeping
        if self.speaking or self.rms > 0.04:
            self.silence_t = 0.0
        else:
            self.silence_t += dt

        # blink: the dome collapses down onto the lid line
        blink = 0.0
        if self._blink_phase >= 0.0:
            self._blink_phase += dt
            d = self._blink_phase
            if d < 0.06:
                blink = d / 0.06
            elif d < 0.15:
                blink = 1.0 - (d - 0.06) / 0.09
            else:
                self._blink_phase = -1.0
                # self.p is last frame's smoothed values, one frame stale —
                # fine for a rate multiplier, not worth reordering for
                rate = max(0.2, self.p.get("blink_rate", 1.0))
                self._blink_at = self.t + random.uniform(
                    idle["blink_min_s"], idle["blink_max_s"]) / rate
        elif self.t >= self._blink_at:
            self._blink_phase = 0.0
        if self.silence_t > 0.30 and self._blink_phase < 0 and random.random() < dt * 0.6:
            self._blink_phase = 0.0

        # ambient sway and breathing — a perfectly still head reads as dead
        sway = idle["sway_amount"]
        yaw = math.sin(self.t * 0.31) * 0.6 + math.sin(self.t * 0.11 + 1.7) * 0.4
        pitch = math.sin(self.t * 0.23 + 0.5) * 0.7 + math.sin(self.t * 0.07) * 0.3
        breath = math.sin(self.t * 0.9) * idle["breath_amount"]

        # prosody
        rms = self.rms
        f0 = self.f0

        p = dict(NEUTRAL)
        for k, v in emo.items():
            p[k] = p.get(k, 0.0) + v

        p["ring_spread"] += 0.06 * rms + breath
        p["ring_tilt"] += 4.0 * f0 + math.sin(self.t * 0.17) * 2.0
        p["core_glow"] = 0.30 + 0.70 * rms + 0.25 * emo.get("glow_gain", 0.0)
        # eye_h_base: pre-blink height, for anything that shouldn't jump
        # around on every blink (the monocle ring — it sits on the socket,
        # not the eyelid)
        p["eye_h_base"] = p["eye_h"]
        p["eye_h"] = max(0.02, p["eye_h"] * (1.0 - blink) + 0.02 * blink)
        p["eye_gaze_x"] += math.sin(self.t * 0.13) * 0.35 + math.sin(self.t * 0.41) * 0.1
        dart = emo.get("eye_dart", 0.0)
        if dart:
            # a snapping square wave, not a smooth sine — darts side to
            # side rather than drifting, the anxious "checking exits" look
            p["eye_gaze_x"] += dart * math.copysign(1.0, math.sin(self.t * 6.0))
        p["brow_y_l"] += max(-0.6, min(0.9, f0 * 0.5))
        p["brow_y_r"] += max(-0.6, min(0.9, f0 * 0.5))
        # head_yaw itself is idle-sway-owned (same reason mouth_ap is
        # viseme-owned), so a cocked-head pose needs its own additive
        # channel rather than being overwritten here
        p["head_yaw"] = yaw * sway + emo.get("head_tilt", 0.0)
        p["head_pitch"] = pitch * sway

        # shake: high-frequency judder on top of the slow idle sway — the
        # manga "vibrating in fear/cold" tell. Two mutually-irrational
        # frequencies so it doesn't read as a metronomic wobble. Amplitude
        # is boosted to survive the per-frame smoothing below, which acts
        # as a low-pass filter and would otherwise flatten anything this
        # fast almost to nothing.
        shake = emo.get("shake", 0.0)
        if shake:
            p["head_yaw"] += shake * 0.14 * (
                math.sin(self.t * 47.0) + math.sin(self.t * 71.0 + 1.1)) * 0.5
            p["head_pitch"] += shake * 0.10 * (
                math.sin(self.t * 59.0 + 0.4) + math.sin(self.t * 83.0)) * 0.5

        # gesture: a few cycles of head motion on one axis, eased in/out so
        # it doesn't snap on top of the idle sway
        if self.gesture is not None:
            g = self.gesture
            g["t"] += dt
            if g["t"] >= g["dur"]:
                self.gesture = None
            else:
                edge = min(1.0, g["t"] / 0.12) * min(1.0, (g["dur"] - g["t"]) / 0.12)
                p[g["axis"]] += math.sin(g["t"] / g["period"] * math.tau) * g["amp"] * edge

        # visemes own the mouth — but a resting emotion still needs to be
        # able to hold a mouth pose (surprise's gasp, dead's slack jaw,
        # anxiety's pursed "o") without speech visemes ever running, so
        # mouth_open/mouth_narrow are emotion-only channels that add on top
        # rather than being overwritten, same pattern as glow_gain feeding
        # core_glow below.
        ap, w, curve = self._vis
        p["mouth_ap"] = max(0.0, emo.get("mouth_open", 0.0)
                            + ap * (0.55 + 0.45 * min(1.0, rms * 1.6)))
        p["mouth_w"] = max(0.05, w + emo.get("mouth_narrow", 0.0))
        p["mouth_curve"] += curve
        p["mouth_smile"] = emo.get("mouth_smile", 0.0)

        p.update(self.overrides)

        # smooth everything so no command can snap the face
        k = min(1.0, dt * 18.0)
        for key, val in p.items():
            self.p[key] = _lerp(self.p.get(key, val), val, k)

        # ring spin: mutually irrational speeds so the rings never re-align
        base = 0.55 * (1.0 + 0.5 * rms) * (1.0 + 0.6 * abs(emo.get("orbit_speed", 0.0)))
        for i, mult in enumerate((1.0, 0.618, 0.382)):
            self.spin[i] = (self.spin[i] + dt * base * mult) % (math.pi * 2)

        # orbiting planet — the nose. `orbit_still` (e.g. the `dead` preset)
        # freezes it in place instead of merely slowing it, since orbit_speed
        # can only ever approach zero asymptotically via the divide below.
        if self.p["orbit_still"] < 0.5:
            period = idle["orbit_period_s"]
            if self.silence_t > idle["bored_after_s"]:
                bored = min(1.0, (self.silence_t - idle["bored_after_s"]) / 8.0)
                period = _lerp(period, idle["orbit_idle_period_s"], bored)
            period /= max(0.15, self.p["orbit_speed"] * (1.0 - 0.45 * rms))
            self.orbit_phase = (self.orbit_phase + dt * math.tau / period) % math.tau
            self.precession = (self.precession
                               + dt * math.tau / idle["precession_period_s"]) % math.tau

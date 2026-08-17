"""Window, command dispatch and the frame loop."""

from __future__ import annotations

import math
import sys
import time

import glfw
import moderngl

from .config import Config
from .geometry import build
from .net import Listener
from .render import Renderer
from .rig import EMOTIONS, EMOTION_ALIASES, GESTURES, LETTER_VISEME, Rig
from .speak import Player

HELP = """
commands (one JSON object per UDP datagram, or per line over TCP)

  {"type":"emotion","name":"anger","weight":1.0,"blend_ms":250}
  {"type":"viseme","shape":"D"}
  {"type":"level","rms":0.7,"f0":0.3}
  {"type":"say","text":"привет, я слушаю"}
  {"type":"speak","timeline":"out.json","wav":"out.wav"}
  {"type":"set","params":{"eye_gaze_x":-0.8,"brow_y_l":0.6}}
  {"type":"clear"}
  {"type":"demo","on":true,"hold_s":2.0}
  {"type":"gesture","name":"yes"}
  {"type":"config","patch":{"palette":{"contour":"#3FB8C8"}}}
  {"type":"title","text":"neonhead: /path/to/project"}
  {"type":"quit"}

emotions: """ + ", ".join(EMOTIONS) + """
gestures: """ + ", ".join(GESTURES) + """
keys: 1..9 emotions, d demo (cycles every emotion), y/n gestures,
      space test phrase, c clear, esc quit
"""

_EMO_KEYS = list(EMOTIONS)


def text_to_timeline(text: str, cps: float = 12.0) -> dict:
    """Rough viseme schedule straight from text, for testing without audio."""
    t = 0.0
    visemes = []
    rms = []
    for ch in text.lower():
        shape = LETTER_VISEME.get(ch)
        if shape is None:
            continue
        dur = (0.11 if shape in "CDEF" else 0.06) * (12.0 / cps)
        visemes.append({"t": round(t, 4), "shape": shape})
        steps = max(1, int(dur / 0.02))
        level = 0.0 if shape == "X" else (0.85 if shape in "CDE" else 0.55)
        rms.extend([level] * steps)
        t += dur
    return {"visemes": visemes, "duration": t,
            "prosody": {"hop": 0.02, "rms": rms,
                        "f0": [math.sin(i * 0.07) * 0.5 for i in range(len(rms))]}}


class App:
    def __init__(self, config_path: str | None = None):
        self.cfg = Config.load(config_path)
        self.rig = Rig(self.cfg)
        self.player = Player()
        self.listener = Listener(self.cfg)
        self.running = True
        self.demo: dict | None = None
        self.window = None  # set once run() creates the glfw window

    # -- demo mode -----------------------------------------------------------

    def start_demo(self, hold_s: float = 2.0):
        """Cycle through every known emotion, a few seconds each.

        Reads straight from EMOTIONS, which the emotions package builds by
        scanning its own directory — new emotion files join the cycle with
        no changes here.
        """
        names = list(EMOTIONS)
        if not names:
            return
        self.demo = {"names": names, "idx": 0, "t": 0.0, "hold": max(0.1, hold_s)}
        self.rig.set_emotion(names[0])

    def stop_demo(self):
        self.demo = None

    def _advance_demo(self, dt: float):
        if self.demo is None:
            return
        self.demo["t"] += dt
        if self.demo["t"] >= self.demo["hold"]:
            self.demo["t"] = 0.0
            self.demo["idx"] = (self.demo["idx"] + 1) % len(self.demo["names"])
            self.rig.set_emotion(self.demo["names"][self.demo["idx"]])

    # -- commands ----------------------------------------------------------

    def handle(self, msg: dict):
        kind = str(msg.get("type", "")).lower()
        if kind == "emotion":
            self.stop_demo()
            if not self.rig.set_emotion(str(msg.get("name", "neutral")),
                                        float(msg.get("weight", 1.0)),
                                        msg.get("blend_ms")):
                print(f"unknown emotion: {msg.get('name')!r}", file=sys.stderr)
        elif kind == "demo":
            if msg.get("on", True):
                self.start_demo(float(msg.get("hold_s", 2.0)))
            else:
                self.stop_demo()
        elif kind == "gesture":
            if not self.rig.set_gesture(str(msg.get("name", ""))):
                print(f"unknown gesture: {msg.get('name')!r}", file=sys.stderr)
        elif kind == "viseme":
            self.rig.set_viseme(str(msg.get("shape", "X")))
        elif kind == "level":
            self.rig.rms = max(0.0, min(1.0, float(msg.get("rms", 0.0))))
            self.rig.f0 = max(-2.0, min(2.0, float(msg.get("f0", 0.0))))
            self.rig.speaking = self.rig.rms > 0.04
        elif kind == "say":
            self.player.load_data(text_to_timeline(str(msg.get("text", "")),
                                                   float(msg.get("cps", 12.0))),
                                  None, False)
        elif kind == "speak":
            tl = msg.get("timeline")
            if tl:
                try:
                    self.player.load(tl, msg.get("wav"),
                                     bool(msg.get("audio", self.cfg.get(
                                         "speech.audio_output", True))))
                except Exception as exc:
                    print(f"speak failed: {exc}", file=sys.stderr)
        elif kind == "set":
            self.rig.set_params(**(msg.get("params") or {}))
        elif kind == "clear":
            self.stop_demo()
            self.rig.clear_overrides()
            self.rig.set_emotion("neutral")
            self.player.stop()
        elif kind == "config":
            patch = msg.get("patch") or {}
            try:
                self.cfg.apply(patch)
            except Exception as exc:
                print(f"bad config patch: {exc}", file=sys.stderr)
        elif kind == "title":
            if self.window is not None:
                glfw.set_window_title(self.window, str(msg.get("text", "")))
        elif kind == "quit":
            self.running = False

    def _key(self, window, key, scancode, action, mods):
        if action != glfw.PRESS:
            return
        if key == glfw.KEY_ESCAPE:
            self.running = False
        elif key == glfw.KEY_SPACE:
            self.handle({"type": "say",
                         "text": "привет, я тебя слышу и говорю с интонацией"})
        elif key == glfw.KEY_C:
            self.handle({"type": "clear"})
        elif key == glfw.KEY_D:
            self.handle({"type": "demo", "on": self.demo is None})
        elif key == glfw.KEY_Y:
            self.handle({"type": "gesture", "name": "yes"})
        elif key == glfw.KEY_N:
            self.handle({"type": "gesture", "name": "no"})
        elif glfw.KEY_1 <= key <= glfw.KEY_9:
            i = key - glfw.KEY_1
            if i < len(_EMO_KEYS):
                self.handle({"type": "emotion", "name": _EMO_KEYS[i]})

    # -- loop --------------------------------------------------------------

    def run(self):
        # Bind the network ports before touching glfw at all: if another
        # instance already owns them, listener.start() raises SystemExit
        # and we never open a window for a doomed second instance.
        where = self.listener.start()

        if not glfw.init():
            raise SystemExit("glfw init failed")
        win_cfg = self.cfg["window"]
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.RESIZABLE, glfw.TRUE if win_cfg.get("resizable", True) else glfw.FALSE)
        glfw.window_hint(glfw.FLOATING, glfw.TRUE if win_cfg.get("floating", True) else glfw.FALSE)
        window = glfw.create_window(int(win_cfg["width"]), int(win_cfg["height"]),
                                    str(win_cfg["title"]), None, None)
        if not window:
            glfw.terminate()
            raise SystemExit("could not create window")
        self.window = window
        glfw.make_context_current(window)
        glfw.swap_interval(1 if win_cfg.get("vsync", True) else 0)
        glfw.set_key_callback(window, self._key)

        ctx = moderngl.create_context()
        renderer = Renderer(ctx, self.cfg)

        if where:
            print(f"listening on udp {where[0]}:{where[1]} / tcp {where[0]}:{where[2]}")
        print(HELP)

        last = time.perf_counter()
        while self.running and not glfw.window_should_close(window):
            glfw.poll_events()
            now = time.perf_counter()
            dt = min(0.1, now - last)
            last = now

            for msg in self.listener.drain():
                self.handle(msg)

            self._advance_demo(dt)

            sampled = self.player.sample()
            if sampled is not None:
                shape, rms, f0 = sampled
                if shape:
                    self.rig.set_viseme(shape)
                self.rig.rms = rms
                self.rig.f0 = f0
                self.rig.speaking = True
            elif self.rig.speaking:
                self.rig.speaking = False
                self.rig.rms = 0.0
                self.rig.set_viseme("X")

            fw, fh = glfw.get_framebuffer_size(window)

            # cursor-follow gaze only applies when nothing else is driving the
            # face — an incoming speech/network stream owns eye_gaze instead.
            if not self.rig.speaking:
                R = min(fw, fh) * self.cfg["head"]["radius_frac"]
                mx, my = glfw.get_cursor_pos(window)
                gaze_x = max(-1.0, min(1.0, (mx - fw * 0.5) / (R * 1.4)))
                gaze_y = max(-1.0, min(1.0, (my - fh * 0.5) / (R * 1.4)))
                self.rig.set_params(eye_gaze_x=gaze_x, eye_gaze_y=gaze_y)
            elif "eye_gaze_x" in self.rig.overrides:
                del self.rig.overrides["eye_gaze_x"]
                self.rig.overrides.pop("eye_gaze_y", None)

            self.rig.update(dt)

            renderer.resize(fw, fh)
            ctx.viewport = (0, 0, fw, fh)

            frame = build(self.cfg, self.rig, fw, fh)
            renderer.draw(frame, now % 3600.0, ctx.screen)
            glfw.swap_buffers(window)

        self.listener.stop()
        self.player.stop()
        glfw.terminate()

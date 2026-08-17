#!/usr/bin/env python3
"""Send commands to a running neon head.

    python client.py emotion anger
    python client.py say "привет, я слушаю"
    python client.py level 0.8 0.3
    python client.py speak out.json out.wav
    python client.py set eye_gaze_x=-0.9 brow_y_l=0.7
    python client.py config palette.contour=#3FB8C8
    python client.py demo 2.0
    python client.py demo off
    python client.py gesture yes
    python client.py title "neonhead: /home/me/project"
    python client.py raw '{"type":"viseme","shape":"D"}'

Or from Python:

    from client import Head
    head = Head()
    head.emotion("joy")
    head.speak("out.json", "out.wav")
"""

from __future__ import annotations

import json
import socket
import sys


class Head:
    def __init__(self, host="127.0.0.1", port=9955):
        self.addr = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, **msg):
        self.sock.sendto(json.dumps(msg, ensure_ascii=False).encode("utf-8"), self.addr)

    def emotion(self, name, weight=1.0, blend_ms=None):
        self.send(type="emotion", name=name, weight=weight, blend_ms=blend_ms)

    def viseme(self, shape):
        self.send(type="viseme", shape=shape)

    def level(self, rms, f0=0.0):
        self.send(type="level", rms=rms, f0=f0)

    def say(self, text, cps=12.0):
        self.send(type="say", text=text, cps=cps)

    def speak(self, timeline, wav=None, audio=True):
        self.send(type="speak", timeline=timeline, wav=wav, audio=audio)

    def set(self, **params):
        self.send(type="set", params=params)

    def config(self, patch):
        self.send(type="config", patch=patch)

    def clear(self):
        self.send(type="clear")

    def demo(self, on=True, hold_s=2.0):
        self.send(type="demo", on=on, hold_s=hold_s)

    def gesture(self, name):
        self.send(type="gesture", name=name)

    def title(self, text):
        self.send(type="title", text=text)


def _nest(dotted: str, value):
    parts = dotted.split(".")
    node = out = {}
    for p in parts[:-1]:
        node[p] = {}
        node = node[p]
    node[parts[-1]] = value
    return out


def _deep(a, b):
    for k, v in b.items():
        a[k] = _deep(a.get(k, {}), v) if isinstance(v, dict) else v
    return a


def _print_emotions():
    from neonhead.emotions import EMOTIONS, EMOTION_ALIASES

    aliases_by_name: dict[str, list] = {}
    for alias, name in EMOTION_ALIASES.items():
        aliases_by_name.setdefault(name, []).append(alias)

    width = max(len(name) for name in EMOTIONS) + 2
    print("Available emotions:")
    for name in EMOTIONS:
        aliases = ", ".join(aliases_by_name.get(name, []))
        print(f"  {name:<{width}}{aliases}")


def main(argv):
    if len(argv) < 2:
        _print_emotions()
        return 0
    head = Head()
    cmd, rest = argv[1], argv[2:]

    if cmd == "emotion":
        head.emotion(rest[0], float(rest[1]) if len(rest) > 1 else 1.0)
    elif cmd == "say":
        head.say(" ".join(rest))
    elif cmd == "viseme":
        head.viseme(rest[0])
    elif cmd == "level":
        head.level(float(rest[0]), float(rest[1]) if len(rest) > 1 else 0.0)
    elif cmd == "speak":
        head.speak(rest[0], rest[1] if len(rest) > 1 else None)
    elif cmd == "set":
        head.set(**{k: float(v) for k, v in (a.split("=", 1) for a in rest)})
    elif cmd == "config":
        patch: dict = {}
        for a in rest:
            k, v = a.split("=", 1)
            try:
                v = float(v)
            except ValueError:
                pass
            _deep(patch, _nest(k, v))
        head.config(patch)
    elif cmd == "clear":
        head.clear()
    elif cmd == "demo":
        arg = rest[0] if rest else "2.0"
        if arg.lower() in ("off", "false", "0"):
            head.demo(on=False)
        else:
            head.demo(on=True, hold_s=float(arg))
    elif cmd == "gesture":
        head.gesture(rest[0])
    elif cmd == "title":
        head.title(" ".join(rest))
    elif cmd == "raw":
        head.sock.sendto(rest[0].encode("utf-8"), head.addr)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

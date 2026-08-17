# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A procedural talking head: three rotating rings, a neon contour, clipped eyes
with sclera/pupil, brows, a mouth with teeth, and a planet orbiting in place
of a nose. No 3D models or textures — all geometry is generated in numpy
every frame and rendered via moderngl (OpenGL). It's controlled entirely at
runtime over the network (UDP/TCP JSON), driven by an external process (e.g.
a Chatterbox TTS pipeline) or the bundled CLI client.

## Commands

```bash
make install     # create venv/, pip install -r requirements.txt
make run          # python run.py — opens the window, starts listening
./run.sh          # same, without make (activates venv itself)

python client.py emotion anger              # one-shot commands to a running head
python client.py say "привет, как слышно"
python client.py speak out.json out.wav
./client.sh emotion anger                   # same, via venv wrapper
```

There is no test suite, linter, or build step — this is a small runtime
toy/tool, not a package. Verify changes by running `make run` and driving it
with `client.py` (or the `Makefile`'s `emotion-*`/`say`/`level`/`speak`
targets) in a second terminal.

## Architecture

Everything is driven by one JSON-over-UDP(9955)/TCP(9956) protocol (see
README.md for the full message list: `emotion`, `viseme`, `level`, `say`,
`speak`, `set`, `clear`, `demo`, `gesture`, `config`, `title`, `quit`). Order and
delivery reliability don't matter — state is always interpolated, so no
command can snap the face.

Data flow per frame (`neonhead/app.py: App.run`):

1. `net.Listener` drains queued JSON messages from its UDP/TCP threads.
2. `App.handle` applies them to the `Rig`.
3. `Rig.update(dt)` advances all smoothing/idle/gesture state.
4. `geometry.build` turns the rig's ~20 numbers into vertex data.
5. `render.Renderer.draw` renders it (afterglow → additive HDR → bloom →
   tonemap → solids on top).

**`rig.py`** is the center of the system: `NEUTRAL` is the dict of every
param the face has. Three independent layers sum into it each frame:
*base emotion* (offsets from neutral), *prosody* (rms/f0-driven: brow lift,
eye openness, glow, orbit speed), and *visemes* (mouth aperture/width/curve
only). Keeping visemes and prosody off different channels than emotion is
what lets the head talk and be angry at the same time. Gestures
(`head_yaw`/`head_pitch` animation) layer on top of all three and self-clear
after a few cycles, unlike emotions which persist until replaced.
`CHANNEL_SPEED`/`OVERSHOOT_CHANNELS` give per-channel cross-fade timing so
brows lead and mouth trails, instead of every feature moving in lockstep.

**`neonhead/emotions/`** and **`neonhead/gestures/`** are plugin
directories, scanned by their `__init__.py` via `pkgutil.iter_modules` —
dropping a new `foo.py` with the right module-level attributes
(`NAME`/`ALIASES`/`PRESET` for emotions; `NAME`/`ALIASES`/`AXIS`/
`AMPLITUDE`/`PERIOD_S`/`CYCLES` for gestures) makes it available by name
and joins the demo cycle / hotkeys automatically, with no edits elsewhere.
Emotion presets are offsets from `rig.NEUTRAL`, which is what allows
blending by weight. Russian aliases are folded to lowercase and map back to
the canonical (also lowercase) `NAME`.

**`geometry.py`** builds the frame's vertex data from the rig's numbers:
rings are 3D circles projected to screen; the face is a handful of
parametric curves. Anything glowing becomes ribbon quads (a brightness
profile across the width); anything non-glowing becomes plain triangles.

**`render.py`** implements the visual pipeline: afterglow (phosphor trail),
additive HDR accumulation, threshold-based bloom, tonemapping, then solid
objects (teeth, sclera) drawn last so they read as objects inside the light
rather than another light source.

**`speak.py`**'s `Player` syncs lip-sync to the *actual audio playhead*
(via `sounddevice`, when available), never wall-clock time since `play()` —
that avoids drift. Without `sounddevice` the timeline still animates off a
monotonic clock, just silently. A timeline is
`{"visemes": [{"t":.., "shape":..}], "duration":.., "prosody": {"hop":..,
"rms":[...], "f0":[...]}}` — `rms` normalized 0…1, `f0` in standard
deviations from the median pitch. `tools/make_timeline.py` generates one
from a wav + known text (letter-to-viseme), for use with Chatterbox TTS
(which gives no phoneme timings itself).

**`config.py`** loads `config.json` (defaults) deep-merged with an optional
`--config` file, and again at runtime via the `config` network command
(`Config.apply`); colors are hex strings in `palette`, pre-parsed to RGB
floats in `Config.rgb`. See README.md's "Конфиг" section for what each
config section (`palette`, `brightness`, `widths`, `head`, `idle`, `post`,
`speech`) controls — in particular, `brightness` values relative to
`post.bloom_threshold` are what decide which layers actually glow.

**`net.py`**'s `Listener` runs UDP/TCP servers on daemon threads and feeds
one shared queue; `app.py` drains it once per frame on the main/render
thread, so all state mutation happens in one place.

**`client.py`** is both a CLI (`python client.py <cmd> ...`) and an
importable `Head` class for scripting from Python — see its module
docstring for the full command list.

## Notes for changes

- New rig params must be added to `rig.NEUTRAL` to be recognized by
  `set_params`/overrides, emotion presets, and the smoothing loop.
- Comments in this codebase explain *why*, not *what* — match that density
  when adding non-obvious behavior (e.g. blend timing constants, drift
  avoidance in `speak.py`).
- CPU-side frame assembly is ~2ms; vsync is the bottleneck, not Python — no
  need to optimize `geometry.build` for speed.
- Be emotional through the `neonhead-react` skill — react to conversation
  content, not just hook events (e.g. `laugh_to_tears` on a joke that
  lands, `disgust` on genuinely ugly code, `triumph` on a hard-won fix).
